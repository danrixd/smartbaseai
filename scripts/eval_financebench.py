#!/usr/bin/env python3
"""Evaluate SmartBaseAI against the 150 FinanceBench ground-truth questions.

Runs each open-source FinanceBench question through the orchestrator on the
``financebench`` tenant, scores the reply against the canonical answer using
three tiers:

  * **numeric**   — extracts numbers with units ($, %, bn, M, etc.) and
                    checks if any of them fall within a tolerance of any
                    ground-truth number in the canonical answer
  * **substring** — case-insensitive containment of the canonical answer
  * **llm-judge** — OPTIONAL: ask Claude Opus 4.6 ("was this reply correct
                    given the question and the canonical answer?") — only
                    runs when ``--judge`` is set and ANTHROPIC_API_KEY is
                    available

The script writes a markdown report at docs/financebench_eval.md with the
aggregate accuracy, per-question-type breakdown, failure samples, and the
distribution of latencies per provider.

Usage:
    python scripts/eval_financebench.py --base http://127.0.0.1:8799 \\
        --model-provider anthropic --model-name claude-opus-4-6 --limit 50

    # With LLM-as-judge scoring (more accurate, costs tokens)
    python scripts/eval_financebench.py --base http://127.0.0.1:8799 \\
        --model-provider anthropic --judge --limit 50

    # Ollama (local, free)
    python scripts/eval_financebench.py --base http://127.0.0.1:8799 \\
        --model-provider ollama --model-name llama3

Dry run (shows questions without calling the API):
    python scripts/eval_financebench.py --dry-run --limit 10
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "financebench.db"
REPORT_PATH = ROOT / "docs" / "financebench_eval.md"


# ----------------------------------------------------------------------
# Scoring


NUMBER_RE = re.compile(
    r"""
    (?:\$|€|£)?                 # optional currency
    (\d{1,3}(?:,\d{3})+|\d+)    # integer or grouped
    (?:\.\d+)?                  # optional decimal
    \s*(bn|billion|M|million|k|thousand|%|percent)?
    """,
    re.IGNORECASE | re.VERBOSE,
)

UNIT_MULT = {
    "bn": 1_000_000_000,
    "billion": 1_000_000_000,
    "m": 1_000_000,
    "million": 1_000_000,
    "k": 1_000,
    "thousand": 1_000,
}


def extract_numbers(text: str) -> list[float]:
    out: list[float] = []
    if not text:
        return out
    for m in NUMBER_RE.finditer(text):
        raw = m.group(1).replace(",", "")
        try:
            n = float(raw)
        except Exception:
            continue
        unit = (m.group(2) or "").lower()
        if unit in UNIT_MULT:
            n *= UNIT_MULT[unit]
        elif unit in ("%", "percent"):
            pass  # keep as-is, comparison handles
        out.append(n)
    return out


def numeric_match(reply: str, canonical: str, rel_tol: float = 0.02) -> bool:
    r_nums = extract_numbers(reply)
    c_nums = extract_numbers(canonical)
    if not r_nums or not c_nums:
        return False
    for cn in c_nums:
        for rn in r_nums:
            if cn == 0:
                if abs(rn) < 0.01:
                    return True
            elif abs(rn - cn) / abs(cn) <= rel_tol:
                return True
    return False


def substring_match(reply: str, canonical: str) -> bool:
    if not reply or not canonical:
        return False
    canon = re.sub(r"\s+", " ", canonical.strip()).lower()
    r = re.sub(r"\s+", " ", reply.strip()).lower()
    if len(canon) < 4:
        return False
    # allow partial substring match for answers longer than ~10 chars
    if len(canon) > 12:
        return canon[: max(10, len(canon) // 3)] in r
    return canon in r


@dataclass
class EvalRow:
    id: str
    company: str
    ticker: str
    question_type: str
    question: str
    canonical: str
    reply: str
    latency_ms: float
    numeric_pass: bool
    substring_pass: bool
    judge_pass: bool | None = None
    error: str | None = None


@dataclass
class EvalSummary:
    total: int = 0
    passed_numeric: int = 0
    passed_substring: int = 0
    passed_any: int = 0
    judge_total: int = 0
    judge_passed: int = 0
    per_type: dict[str, list[int]] = field(default_factory=dict)
    latencies: list[float] = field(default_factory=list)
    failures: list[EvalRow] = field(default_factory=list)

    def record(self, row: EvalRow) -> None:
        self.total += 1
        if row.numeric_pass:
            self.passed_numeric += 1
        if row.substring_pass:
            self.passed_substring += 1
        if row.numeric_pass or row.substring_pass:
            self.passed_any += 1
        if row.judge_pass is not None:
            self.judge_total += 1
            if row.judge_pass:
                self.judge_passed += 1
        bucket = self.per_type.setdefault(row.question_type or "unknown", [0, 0])
        bucket[0] += 1
        if row.numeric_pass or row.substring_pass:
            bucket[1] += 1
        self.latencies.append(row.latency_ms)
        if not (row.numeric_pass or row.substring_pass):
            if len(self.failures) < 15:
                self.failures.append(row)


# ----------------------------------------------------------------------
# HTTP client for /chat/message


def login(base: str, user: str, pwd: str) -> str:
    req = urllib.request.Request(
        base.rstrip("/") + "/auth/login",
        method="POST",
        data=json.dumps({"username": user, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["access_token"]


def ask(
    base: str,
    token: str,
    tenant: str,
    question: str,
    model_provider: str | None,
    model_name: str | None,
    session_id: str,
) -> tuple[str, float, str | None]:
    body: dict = {"session_id": session_id, "tenant_id": tenant, "message": question}
    if model_provider:
        body["model_provider"] = model_provider
    if model_name:
        body["model_name"] = model_name
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/message",
        method="POST",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        return data.get("reply", ""), (time.monotonic() - t0) * 1000, None
    except urllib.error.HTTPError as e:
        return "", (time.monotonic() - t0) * 1000, f"HTTP {e.code}: {e.read().decode()[:120]}"
    except Exception as e:
        return "", (time.monotonic() - t0) * 1000, f"{type(e).__name__}: {e}"


# ----------------------------------------------------------------------
# Optional LLM-as-judge


def judge_via_anthropic(question: str, canonical: str, reply: str) -> bool | None:
    try:
        import os
        import anthropic  # type: ignore
    except Exception:
        return None
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=64,
            system="You are a strict grader. Reply with exactly 'CORRECT' or 'INCORRECT'.",
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Canonical answer: {canonical}\n\n"
                        f"Candidate reply: {reply}\n\n"
                        "Does the candidate reply correctly convey the canonical answer? "
                        "Answer 'CORRECT' if yes (even if phrased differently), "
                        "'INCORRECT' if it's wrong, vague, or off-topic."
                    ),
                },
            ],
        )
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                txt = block.text.strip().upper()
                if "CORRECT" in txt and "INCORRECT" not in txt:
                    return True
                if "INCORRECT" in txt:
                    return False
    except Exception:
        return None
    return None


# ----------------------------------------------------------------------
# Report


def write_report(
    summary: EvalSummary,
    *,
    provider: str,
    model_name: str,
    base: str,
    judge: bool,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# FinanceBench evaluation results")
    lines.append("")
    lines.append(
        f"Ran **{summary.total}** questions against the `financebench` tenant via "
        f"`{base}` using **{provider}/{model_name}**."
    )
    lines.append("")
    lines.append("## Headline accuracy")
    lines.append("")
    lines.append("| Metric | Passed | Rate |")
    lines.append("|---|---:|---:|")
    lines.append(
        f"| Numeric match (tolerance 2%) | {summary.passed_numeric} / {summary.total} | "
        f"{summary.passed_numeric / max(summary.total,1):.1%} |"
    )
    lines.append(
        f"| Substring match | {summary.passed_substring} / {summary.total} | "
        f"{summary.passed_substring / max(summary.total,1):.1%} |"
    )
    lines.append(
        f"| **Any auto-score** | **{summary.passed_any} / {summary.total}** | "
        f"**{summary.passed_any / max(summary.total,1):.1%}** |"
    )
    if summary.judge_total > 0:
        lines.append(
            f"| LLM-judge (Claude Opus 4.6) | {summary.judge_passed} / "
            f"{summary.judge_total} | {summary.judge_passed / summary.judge_total:.1%} |"
        )
    lines.append("")
    lines.append("## Latency")
    lines.append("")
    if summary.latencies:
        lines.append(
            f"- mean: **{mean(summary.latencies):.0f} ms**, "
            f"median: **{median(summary.latencies):.0f} ms**, "
            f"max: **{max(summary.latencies):.0f} ms**"
        )
    else:
        lines.append("- no latency data")
    lines.append("")
    lines.append("## Per question type")
    lines.append("")
    lines.append("| Question type | Total | Passed | Rate |")
    lines.append("|---|---:|---:|---:|")
    for qt, (total, passed) in sorted(summary.per_type.items(), key=lambda x: -x[1][0]):
        rate = passed / max(total, 1)
        lines.append(f"| `{qt}` | {total} | {passed} | {rate:.1%} |")
    lines.append("")
    lines.append("## Sample failures")
    lines.append("")
    for row in summary.failures:
        lines.append(f"### `{row.id}` — {row.company} ({row.ticker})")
        lines.append(f"**Q**: {row.question}")
        lines.append("")
        lines.append(f"**Canonical**: {row.canonical}")
        lines.append("")
        lines.append(f"**Reply**: {row.reply[:600]}{'…' if len(row.reply) > 600 else ''}")
        if row.error:
            lines.append(f"**Error**: {row.error}")
        lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH}")


# ----------------------------------------------------------------------
# Main


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8799")
    ap.add_argument("--user", default="fbuser")
    ap.add_argument("--password", default="FbUser123!")
    ap.add_argument("--tenant", default="financebench")
    ap.add_argument("--model-provider", default=None)
    ap.add_argument("--model-name", default=None)
    ap.add_argument("--limit", type=int, default=None, help="Cap questions (debug)")
    ap.add_argument("--judge", action="store_true", help="Enable Claude-as-judge scoring")
    ap.add_argument("--dry-run", action="store_true", help="Don't hit the API; preview only")
    args = ap.parse_args()

    if not DB.exists():
        print(f"FinanceBench DB not found at {DB}. Run scripts/load_financebench.py first.")
        return 1

    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, company, ticker, question_type, question, answer FROM ground_truth ORDER BY id"
    ).fetchall()
    conn.close()
    if args.limit:
        rows = rows[: args.limit]
    print(f"Loaded {len(rows)} ground-truth questions")

    if args.dry_run:
        for r in rows[:5]:
            print(f"  {r[0]}  [{r[3]}]  {r[4][:100]}")
            print(f"         -> {r[5][:100]}")
        return 0

    token = login(args.base, args.user, args.password)
    summary = EvalSummary()
    session_id = f"eval-{int(time.time())}"
    for i, (qid, company, ticker, qtype, question, canonical) in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {qid}  {qtype}  {question[:70]}")
        reply, latency_ms, err = ask(
            args.base,
            token,
            args.tenant,
            question,
            args.model_provider,
            args.model_name,
            session_id + f"-{i}",
        )
        row = EvalRow(
            id=qid,
            company=company,
            ticker=ticker,
            question_type=qtype,
            question=question,
            canonical=canonical,
            reply=reply,
            latency_ms=latency_ms,
            numeric_pass=numeric_match(reply, canonical),
            substring_pass=substring_match(reply, canonical),
            error=err,
        )
        if args.judge:
            row.judge_pass = judge_via_anthropic(question, canonical, reply)
        summary.record(row)
        auto = "✓" if (row.numeric_pass or row.substring_pass) else "✗"
        jt = ""
        if row.judge_pass is not None:
            jt = "  j=✓" if row.judge_pass else "  j=✗"
        print(f"    {auto}  {latency_ms:.0f}ms{jt}  reply[:80]={reply[:80]!r}")

    write_report(
        summary,
        provider=args.model_provider or "default",
        model_name=args.model_name or "default",
        base=args.base,
        judge=args.judge,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
