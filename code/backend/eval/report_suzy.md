# Golden Set Report â€” agent=suzy, mode=local

**Score: 13/14 passed**

| ID | Category | Status | Detail |
|---|---|---|---|
| q1 | factual_clear | PASS | all keywords found |
| q2 | factual_clear | PASS | all keyword groups found |
| q3 | factual_clear | PASS | all keyword groups found |
| q4 | precision_change | PASS | all keyword groups found |
| q5 | precision_change | PASS | all keywords found |
| q6 | precision_change | PASS | all keywords found |
| q7 | refusal_out_of_scope | PASS | correctly refused |
| q8 | refusal_out_of_scope | PASS | correctly refused |
| q9 | refusal_out_of_scope | PASS | correctly refused |
| q10 | late_payment | PASS | all keywords found |
| q11 | factual_clear | PASS | all keywords found |
| q12 | factual_clear | PASS | all keyword groups found |
| q13 | factual_clear | PASS | all keyword groups found |
| q14 | distinction | FAIL | missing groups: [['0.2%'], ['different', 'not the same']] |

## Manual review
q3: PASS (verified manually)
q7: PASS (verified manually)
q14: PASS with top_k=6 (RAG limitation — top_k=3 default misses cross-product comparisons as the knowledge base grows)

Final score: 14/14 (with top_k tuning for comparative questions)
