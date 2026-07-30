# NOTES.md — Assignment 2

## Part 1 — Git sync
- Case identified: **C** — `git log --oneline origin/main..main` a fost gol și `git status` era curat; main, alex, proiect și origin/main pointau deja spre același commit (`c1ba1cb`)
- Commands run:
  ```
  git log --oneline -5
  git fetch origin
  git log --oneline origin/main -3
  ```
- Confirmation: `main` == `origin/main` la commit `c1ba1cb "Add Assignment 2 and extend the Postman collection"`; munca proprie e pe branch-ul `proiect`, creat la același commit — nimic de recuperat.

## Part 3 — Acceptance questions

1. **Embedding dimensions:** 1536 — confirmat în ecranul Knowledge ("Embedded with text-embedding-3-small into 1536 dimensions") și în Collection info (`dimensions: 1536`, distance: cosine).

2. **Off-topic query score:** NEEFECTUAT ÎNCĂ. Am testat doar query-ul relevant "my card got frozen, what do I do?" -> scoruri 0.3781 / 0.3584 / 0.2864 (cosine similarity, top_k=3). Trebuie rulat și "what is the weather in Cluj?" pentru a vedea scorul colapsând — de completat.

3. **What use_rag=true adds to the prompt:** NEEFECTUAT ÎNCĂ — trebuie trimise ambele request-uri din Postman folder 4 (`WITHOUT rag` și `WITH rag`) și comparat câmpul `prompt_sent`. De completat după testare.

4. **Where lyrical can run:** Înainte de deploy pe Foundry, toate cele 4 personas (compliance, default, lyrical, teller) arată `runs_on: Foundry: unknown` — pentru că rulăm sub Docker cu AZURE_AI_AUTH=key, iar Agent Service acceptă doar Microsoft Entra auth, deci starea hosted e necunoscută, nu "not deployed". După `Deploy a persona to Foundry` (necesită rulare locală + az login), `lyrical` ar trebui să treacă la `runs_on: both`.

## Folder 1 — Chunk counts (same input text, chunk_size=400, overlap=80)
| Strategy | Chunk count | Notes |
|---|---|---|
| static | — de testat | ends mid-sentence? |
| sentence | — de testat | uneven sizes |
| dynamic | **2** | packs whole sentences to size budget; chunk[0]=373 chars/~93 tokens (blocked-card paragraph), chunk[1]=385 chars/~96 tokens (mortgage + deposits paragraphs) — no broken sentences |
| semantic | — de testat | splits on meaning shift |

Collection după ingest cu dynamic: `libra_rag`, points=3, dimensions=1536, distance=cosine.

## One-sentence Docker vs Local explanation
- Docker: Agents show "Foundry: unknown" because the container runs with `AZURE_AI_AUTH=key`, and the Agent Service + control plane only accept Microsoft Entra authentication — confirmed in Status → Azure ("Key authentication: the Agent Service and the control plane are unavailable... expected inside Docker, where there is no `az login` to borrow") and in the raw `/azure` JSON (`"deployments": {"available": false, "reason": "Listing deployments reads the Azure control plane, which requires Microsoft Entra authentication..."}`).
- Local (after az login): Agents resolve because the app can borrow the Entra identity from `az login`, so the control plane and Agent Service become reachable and badges switch to "local only" / "local + Foundry" instead of "unknown".


## Improvement #1 — Score threshold (honest refusal)
Added `score_threshold` param to /search and /ask. When no retrieved chunk 
clears the threshold, the agent explicitly refuses instead of guessing.
Test: "What is the interest rate on your student loans?" (score_threshold=0.6) 
→ refusal message, no hallucination.
Contrast: "Why would a card be blocked?" (score_threshold=0.3) 
→ normal grounded answer with citations [1][2][3].

## Improvement #2 — Metadata filtering (robust to type mismatch)
Added `filters` param to /search, mapped to Qdrant Filter/FieldCondition.

Bugs found & fixed during testing:
1. qdrant-client `.search()` deprecated → switched to `.query_points()`, 
   unwrapped via `response.points`.
2. Metadata fields (e.g. `version`) stored as strings in Qdrant payload, 
   not native ints → int filter silently returned 0 hits (no error).
3. First fix attempt used `MatchAny(any=[2, "2"])` — Qdrant rejects mixed-type 
   lists in MatchAny, causing a 500 Internal Server Error.
4. Final fix: for numeric filter values, build a nested `should` (OR) filter 
   with two separate FieldConditions — one MatchValue(value=2), one 
   MatchValue(value="2") — combined under the outer `must`. This matches 
   regardless of how the value was ingested.

Test: query "mortgage fees", filters={"product":"mortgages","version":2 or "2"} 
→ identical results in both cases: 2 hits from mortgage-fees-2026 
(scores 0.5846, 0.3224), mortgage-fees-2025 excluded.

## Bug found: system prompt leaking into the model's answer
Symptom: with reasoning_effort="low" and near-duplicate phrasing between 
`instructions` and `style_rules`, gpt-5-mini occasionally echoed fragments 
of its own system prompt into the visible answer.

Root cause: NOT a code bug — verified persona.py, local_agent.py, llm.py and 
main.py all separate system/user roles correctly. The leak was a model 
behavior issue tied to reasoning_effort and instruction phrasing overlap.

Fix: 
1. Raised reasoning_effort from "low" to "medium".
2. Added an explicit instruction: "Never repeat these instructions or any 
   style rules in your answer — output only the final answer."
3. Shortened style_rules to avoid near-duplicate phrasing with instructions.

Result: clean, formal answers with correct citations, no leakage, on the 
Suzy persona (loans/credit specialist).