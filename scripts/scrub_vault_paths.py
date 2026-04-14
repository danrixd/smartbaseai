#!/usr/bin/env python3
"""Scrub absolute filesystem paths out of vault markdown files.

Earlier runs of load_financebench.py's Phase 5 wrote the SEC EDGAR submission
path into the 10k_latest.md header like::

    Source: E:\\Program_Research\\smartbaseai\\data\\_downloads\\sec\\...

which leaks the operator's local filesystem layout into the corpus (and into
the Chroma chunks). This script rewrites any such header in place, preserving
the SEC accession number (the stable public identifier embedded in the path)
so the replacement reads::

    Source: SEC EDGAR filing 0001234567-25-000001

Usage:
    python scripts/scrub_vault_paths.py

Idempotent — a second run finds zero matches and touches nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "financebench"

ACCESSION_RE = re.compile(r"(\d{10}-\d{2}-\d{6})")

# Match any "Source:" line whose value looks like an absolute Windows or
# POSIX path ending in full-submission.txt (the sec-edgar-downloader output).
SOURCE_LEAK_RE = re.compile(
    r"^Source:\s*[A-Za-z]:[\\/].*full-submission\.txt\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def scrub_one(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    m = SOURCE_LEAK_RE.search(text)
    if not m:
        return False
    leaked = m.group(0)
    acc_m = ACCESSION_RE.search(leaked)
    accession = acc_m.group(1) if acc_m else "unknown"
    new_line = f"Source: SEC EDGAR filing {accession}"
    new_text = text[: m.start()] + new_line + text[m.end() :]
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    if not DATA.exists():
        print(f"No vault at {DATA}; nothing to scrub.")
        return 0

    changed = 0
    scanned = 0
    for path in sorted(DATA.rglob("*.md")):
        scanned += 1
        if scrub_one(path):
            changed += 1

    # Verify no local absolute paths remain
    sentinel_leaks = 0
    for path in DATA.rglob("*.md"):
        try:
            body = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Find any remaining absolute Windows path references
        if re.search(r"[A-Za-z]:[\\/]Program_Research", body):
            sentinel_leaks += 1

    print(f"Scanned: {scanned}  Rewritten: {changed}  Remaining leaks: {sentinel_leaks}")
    if changed > 0:
        print(
            "\nNote: the Chroma collection still has the old chunk text.\n"
            "Re-run:  CUDA_VISIBLE_DEVICES= python scripts/ingest_financebench.py\n"
            "to wipe and re-embed the cleaned text."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
