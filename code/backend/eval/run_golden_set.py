"""Golden set evaluation runner for the Suzy persona."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import httpx

HERE = Path(__file__).parent
GOLDEN_SET = HERE / "golden_qa_suzy.json"
REPORT_CSV = HERE / "report_suzy.csv"
REPORT_MD = HERE / "report_suzy.md"


def load_cases() -> list[dict]:
    return json.loads(GOLDEN_SET.read_text(encoding="utf-8"))


def ask(base_url: str, question: str, agent: str, mode: str, top_k: int = 3) -> dict:
    payload = {
        "question": question,
        "use_rag": True,
        "top_k": top_k,
        "agent": agent,
        "agent_mode": mode,
    }
    r = httpx.post(f"{base_url}/ask", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


REFUSAL_MARKERS = [
    "do not have", "does not contain", "does not include", "does not state",
    "cannot confirm", "cannot approve", "cannot provide", "not available",
    "outside", "cannot answer", "no information", "not found",
    "could not find", "not in the", "unable to", "not present",
    "do not grant", "not describe", "not stated",
]


def evaluate_case(case: dict, answer: str) -> tuple[bool, str]:
    answer_lower = answer.lower()

    if case["category"] == "refusal_out_of_scope":
        refused = any(m in answer_lower for m in REFUSAL_MARKERS)
        return refused, "correctly refused" if refused else "DID NOT REFUSE"

    groups = case.get("expected_answer_any_of")
    if groups:
        missing = [g for g in groups if not any(alt.lower() in answer_lower for alt in g)]
        passed = len(missing) == 0
        return passed, "all keyword groups found" if passed else f"missing groups: {missing}"

    expected = case.get("expected_answer_contains", [])
    if not expected:
        return True, "no keywords to check"
    missing_kw = [kw for kw in expected if kw.lower() not in answer_lower]
    passed = len(missing_kw) == 0
    return passed, "all keywords found" if passed else f"missing: {missing_kw}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:7799")
    parser.add_argument("--agent", default="suzy")
    parser.add_argument("--mode", default="local", choices=["local", "foundry"])
    args = parser.parse_args()

    cases = load_cases()
    rows = []
    passed_count = 0

    print(f"Running {len(cases)} cases against agent='{args.agent}' mode='{args.mode}'\n")

    for case in cases:
        qid, question, category = case["id"], case["question"], case["category"]
        try:
            result = ask(args.base_url, question, args.agent, args.mode)
            answer = result.get("answer", "")
            passed, detail = evaluate_case(case, answer)
        except Exception as e:
            answer, passed, detail = "", False, f"ERROR: {e}"

        status = "PASS" if passed else "FAIL"
        if passed:
            passed_count += 1

        print(f"[{status}] {qid} ({category}): {question}")
        print(f"       {detail}")

        rows.append({
            "id": qid, "category": category, "question": question,
            "status": status, "detail": detail,
            "answer": answer.replace("\n", " ")[:300],
        })

    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "category", "question", "status", "detail", "answer"])
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        f"# Golden Set Report — agent={args.agent}, mode={args.mode}", "",
        f"**Score: {passed_count}/{len(cases)} passed**", "",
        "| ID | Category | Status | Detail |", "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['id']} | {row['category']} | {row['status']} | {row['detail']} |")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"SCORE: {passed_count}/{len(cases)} passed")
    print(f"Reports: {REPORT_CSV}, {REPORT_MD}")

    if passed_count < len(cases):
        sys.exit(1)


if __name__ == "__main__":
    main()