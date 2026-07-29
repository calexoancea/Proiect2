"""
load_corpus.py — walks data/, parses each Markdown document's YAML front-matter,
and ingests it into the RAG backend via POST /ingest.

Usage:
    uv run python scripts/load_corpus.py
    uv run python scripts/load_corpus.py --base-url http://localhost:7799 --strategy dynamic
    uv run python scripts/load_corpus.py --dry-run
"""

import argparse
import re
import sys
from pathlib import Path

import requests

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse_front_matter(raw_text: str) -> tuple[dict, str]:
    """Split a Markdown file into (metadata dict, body text)."""
    match = FRONT_MATTER_RE.match(raw_text)
    if not match:
        return {}, raw_text.strip()

    header_block, body = match.groups()
    metadata = {}
    for line in header_block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        metadata[key.strip()] = value.strip()

    return metadata, body.strip()


def find_documents(data_dir: Path) -> list[Path]:
    skip = {"readme.md", "questions.md"}
    return sorted(
        p for p in data_dir.glob("*.md")
        if p.name.lower() not in skip
    )


def ingest_document(base_url: str, strategy: str, source: str, text: str,
                     metadata: dict, dry_run: bool) -> dict:
    payload = {
        "text": text,
        "strategy": strategy,
        "source": source,
        "metadata": metadata,
    }

    if dry_run:
        print(f"  [dry-run] would POST {len(text)} chars, source={source!r}, "
              f"metadata={metadata}")
        return {"dry_run": True}

    resp = requests.post(f"{base_url}/ingest", json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Load data/*.md into the RAG backend")
    parser.add_argument("--base-url", default="http://localhost:7799")
    parser.add_argument("--strategy", default="dynamic",
                         choices=["static", "sentence", "dynamic", "semantic"])
    parser.add_argument("--data-dir", default=None,
                         help="Defaults to <repo-root>/data")
    parser.add_argument("--dry-run", action="store_true",
                         help="Parse and print without calling the API")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]  # code/backend/scripts -> repo root
    data_dir = Path(args.data_dir) if args.data_dir else repo_root / "data"

    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}", file=sys.stderr)
        return 1

    documents = find_documents(data_dir)
    if not documents:
        print(f"No .md documents found in {data_dir}", file=sys.stderr)
        return 1

    print(f"Found {len(documents)} documents in {data_dir}")
    print(f"Strategy: {args.strategy} | Base URL: {args.base_url}\n")

    total_chunks = 0
    failures = []

    for doc_path in documents:
        raw_text = doc_path.read_text(encoding="utf-8")
        metadata, body = parse_front_matter(raw_text)

        title = metadata.get("title", doc_path.stem)
        source = doc_path.stem

        print(f"- {doc_path.name}: title={title!r}, product={metadata.get('product')}, "
              f"version={metadata.get('version')}")

        try:
            result = ingest_document(
                base_url=args.base_url,
                strategy=args.strategy,
                source=source,
                text=body,
                metadata=metadata,
                dry_run=args.dry_run,
            )
            chunk_count = result.get("count", "?")
            print(f"    -> ok, chunks: {chunk_count}")
            if isinstance(chunk_count, int):
                total_chunks += chunk_count
        except Exception as exc:  # noqa: BLE001
            print(f"    -> FAILED: {exc}", file=sys.stderr)
            failures.append((doc_path.name, str(exc)))

    print(f"\nDone. {len(documents) - len(failures)}/{len(documents)} documents ingested.")
    if not args.dry_run:
        print(f"Total chunks reported: {total_chunks}")
    if failures:
        print("\nFailures:", file=sys.stderr)
        for name, err in failures:
            print(f"  - {name}: {err}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
