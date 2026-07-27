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
