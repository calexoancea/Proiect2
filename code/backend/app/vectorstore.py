"""Qdrant wrapper — collection lifecycle, upsert, similarity search.

The collection is created lazily with the dimension of the first embedding that
arrives. If a later embedding model produces a different dimension, we refuse
loudly: vectors from different models live in different spaces and comparing
them is meaningless — reset the collection and re-ingest instead.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from qdrant_client import QdrantClient, models

from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

from .config import settings


class DimensionMismatch(Exception):
    def __init__(self, existing: int, incoming: int) -> None:
        self.existing = existing
        self.incoming = incoming
        super().__init__(
            f"Collection stores {existing}-dimensional vectors but the current embedding "
            f"model produces {incoming} dimensions. Vectors from different embedding models "
            f"are not comparable — DELETE /collection and re-ingest."
        )


class VectorStore:
    # Fixed namespace so chunk ids are deterministic across runs (Improvement #1:
    # re-ingesting the same document REPLACES its chunks instead of duplicating them).
    ID_NAMESPACE = uuid.UUID("7b1e6b2a-9c4d-4a3e-8f1a-6d2c9e0b5a11")

    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url, timeout=10)
        self.collection = settings.qdrant_collection

    # --- lifecycle -----------------------------------------------------------
    def ensure_collection(self, dim: int) -> None:
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            )
            return
        existing = self._vector_size()
        if existing != dim:
            raise DimensionMismatch(existing, dim)

    def reset(self) -> bool:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
            return True
        return False

    # --- data ----------------------------------------------------------------
    def upsert(self, chunks: list[str], vectors: list[list[float]], strategy: str,
               source: str | None, metadata: dict | None = None) -> list[str]:
        """Store chunks with STABLE ids (derived from source+index) so a document
        can be re-ingested to replace its old chunks, and with any extra
        `metadata` (title, product, effective, version, ...) merged into the
        payload so it becomes filterable and comes back in /search results."""
        src = source or "adhoc"
        ids = [str(uuid.uuid5(self.ID_NAMESPACE, f"{src}:{i}")) for i in range(len(chunks))]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        meta = metadata or {}

        self.client.upsert(
            collection_name=self.collection,
            points=[
                models.PointStruct(
                    id=pid,
                    vector=vec,
                    payload={
                        "text": text,
                        "index": i,
                        "strategy": strategy,
                        "source": src,
                        "ingested_at": now,
                        **meta,
                    },
                )
                for i, (pid, text, vec) in enumerate(zip(ids, chunks, vectors))
            ],
        )
        return ids

    def search(self, query_vector: list[float], top_k: int = 5,
           filters: dict | None = None, score_threshold: float | None = None) -> list[dict]:
        """Embed-space nearest neighbours, optionally restricted by exact metadata
        match (Improvement #2) and/or a minimum cosine score (Improvement #1) —
        below the threshold, a hit is treated as noise, not evidence.

        Numeric-looking filter values are matched against BOTH the native type and
        its string form via a nested `should` (OR) filter: metadata such as
        `version` can end up stored as a string depending on how it was ingested.
        Qdrant's MatchAny requires a type-homogeneous list, so mixed int/str
        values must be expressed as two separate FieldConditions, not one
        MatchAny(any=[2, "2"]) — that combination is rejected server-side (500).
        """
        query_filter = None
        if filters:
            must_conditions = []
            for key, value in filters.items():
                if isinstance(value, (int, float)):
                    must_conditions.append(
                        Filter(
                            should=[
                                FieldCondition(key=key, match=MatchValue(value=value)),
                                FieldCondition(key=key, match=MatchValue(value=str(value))),
                            ]
                        )
                    )
                else:
                    must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            query_filter = Filter(must=must_conditions)

        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            score_threshold=score_threshold,
        )

        return [
            {
                "score": r.score,
                "text": r.payload.get("text", ""),
                "index": r.payload.get("index"),
                "strategy": r.payload.get("strategy"),
                "source": r.payload.get("source"),
                "id": str(r.id),
                "metadata": {
                    k: v for k, v in r.payload.items()
                    if k not in {"text", "index", "strategy", "source", "ingested_at"}
                },
            }
            for r in response.points
        ]
    # --- introspection --------------------------------------------------------
    def info(self) -> dict:
        if not self.client.collection_exists(self.collection):
            return {"exists": False, "name": self.collection, "points_count": 0,
                    "vector_dimension": None, "distance": None}
        c = self.client.get_collection(self.collection)
        return {
            "exists": True,
            "name": self.collection,
            "points_count": c.points_count or 0,
            "vector_dimension": self._vector_size(),
            "distance": "cosine",
        }

    def ping(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def _vector_size(self) -> int:
        cfg = self.client.get_collection(self.collection).config.params.vectors
        return cfg.size if hasattr(cfg, "size") else next(iter(cfg.values())).size
