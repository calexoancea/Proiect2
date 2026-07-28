# data/ — Libra Bank fictional knowledge base

All documents in this folder are entirely fictional, created for Assignment 3 of the
AI Engineering on Azure module. No real customer data or real internal bank documents
are used.

## Domain

The corpus covers a narrow slice of retail banking: **cards, mortgages, deposits,
accounts, and onboarding**, with one document on complaints and one listing products
the bank deliberately does not offer.

## Documents and which "breaking" case they cover

| Document | Case covered |
|---|---|
| `mortgage-fees-2025.md` / `mortgage-fees-2026.md` | Near-duplicates that differ (same topic, different year, different numbers) |
| `mortgage-fees-2026.md` | A precise number (1% early repayment fee, 0.4% origination fee) |
| `mortgage-eligibility.md` + `mortgage-fees-2026.md` | Two documents that must be combined (eligibility criteria in one file, the fee schedule it references in another) |
| `mortgage-fees-2025.md` vs `mortgage-fees-2026.md` | Contradiction across versions (down payment 15% → 20%, origination fee 0.5% → 0.4%) |
| `card-blocking-procedure.md` / `card-replacement-procedure.md` | A long procedure with numbered steps |
| `account-fee-table.md` | A table (fees per account type) |
| `products-not-offered.md` | Something deliberately absent — the assistant must refuse, not invent |
| `mortgage-early-repayment-calc.md` | Multi-step reasoning (retrieval + arithmetic) |

## Full document list

1. card-blocking-procedure.md
2. card-replacement-procedure.md
3. mortgage-fees-2025.md
4. mortgage-fees-2026.md
5. mortgage-eligibility.md
6. mortgage-early-repayment-calc.md
7. account-fee-table.md
8. term-deposits.md
9. complaints-procedure.md
10. products-not-offered.md
11. onboarding-new-customer.md
12. premium-account-eligibility.md
13. iban-format.md
14. overdraft-facility.md
