#!/usr/bin/env python3
"""Load FinanceBench 10-Ks + S&P 500 daily bars/profiles into a new tenant.

Idempotent: skips anything already on disk. Three scale tiers:

    --scale small    FinanceBench companies only (~60 files, ~10 min)
    --scale medium   FB + bars + profiles for all S&P 500 (~1200 files, ~25 min)
    --scale large    Medium + latest 10-K for every non-FB SP500 (~1600 files, ~2h)

Run:
    python scripts/load_financebench.py --scale large --sec-user-agent \\
        "Dan Ringart <yomik@medbit.co.il>"

Outputs:
    data/financebench/<TICKER>/10k_<year>.md          10-K filings (text)
    data/financebench/<TICKER>/bars.csv               10-year daily OHLCV
    data/financebench/<TICKER>/profile.md             Company overview
    data/financebench.db                              SQLite: daily_bars + ground_truth
    vector_store/financebench/                        Chroma collection
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TENANT_ID = "financebench"
TENANT_NAME = "S&P 500 Fundamentals"
TENANT_DESCRIPTION = (
    "SEC 10-K filings + daily bars + company profiles for S&P 500 companies, "
    "anchored on the FinanceBench ground-truth benchmark."
)
DEMO_USER = ("fbuser", "FbUser123!")
DATA = ROOT / "data" / "financebench"
DOWNLOADS = ROOT / "data" / "_downloads"
FB_REPO = DOWNLOADS / "financebench"
STRUCTURED_DB = ROOT / "data" / "financebench.db"

# FinanceBench company name -> ticker. Verified against the 40 companies
# in financebench_document_information.jsonl.
FB_TICKER_MAP = {
    "3M": "MMM",
    "AES Corporation": "AES",
    "AMD": "AMD",
    "Activision Blizzard": "ATVI",  # delisted 2023; yf will say so, we still pull historical
    "Adobe": "ADBE",
    "Amazon": "AMZN",
    "Amcor": "AMCR",
    "American Express": "AXP",
    "American Water Works": "AWK",
    "Apple": "AAPL",
    "Best Buy": "BBY",
    "Block": "SQ",
    "Boeing": "BA",
    "CVS Health": "CVS",
    "Coca-Cola": "KO",
    "Corning": "GLW",
    "Costco": "COST",
    "FedEx": "FDX",
    "Foot Locker": "FL",
    "General Mills": "GIS",
    "Intel": "INTC",
    "JPMorgan": "JPM",
    "Johnson & Johnson": "JNJ",
    "Kraft Heinz": "KHC",
    "Lockheed Martin": "LMT",
    "MGM Resorts": "MGM",
    "McDonalds": "MCD",
    "Microsoft": "MSFT",
    "Netflix": "NFLX",
    "Nike": "NKE",
    "Oracle": "ORCL",
    "PG&E Corporation": "PCG",
    "Paypal": "PYPL",
    "PepsiCo": "PEP",
    "Pfizer": "PFE",
    "Salesforce": "CRM",
    "Ulta Beauty": "ULTA",
    "Verizon": "VZ",
    "Walmart": "WMT",
    "eBay": "EBAY",
}


# ----------------------------------------------------------------------
# Phase 0: ensure the FinanceBench repo is present


def ensure_fb_repo() -> None:
    if FB_REPO.exists() and (FB_REPO / "pdfs").exists():
        print(f"[fb-repo] already present at {FB_REPO}")
        return
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    print("[fb-repo] cloning patronus-ai/financebench ...")
    subprocess.run(
        ["git", "clone", "--depth", "1", "https://github.com/patronus-ai/financebench.git", str(FB_REPO)],
        check=True,
    )


# ----------------------------------------------------------------------
# Phase 1: parse FinanceBench metadata + convert PDFs to section-split MD


SECTION_HEADERS = [
    ("income_statement", re.compile(r"consolidated\s+statements?\s+of\s+(income|operations|earnings)", re.I)),
    ("balance_sheet", re.compile(r"consolidated\s+balance\s+sheet", re.I)),
    ("cash_flow", re.compile(r"consolidated\s+statements?\s+of\s+cash\s+flow", re.I)),
    ("stockholders_equity", re.compile(r"consolidated\s+statements?\s+of\s+(stockholders|shareholders)", re.I)),
    ("md_and_a", re.compile(r"management\W?s\s+discussion\s+and\s+analysis", re.I)),
    ("risk_factors", re.compile(r"\brisk\s+factors\b", re.I)),
    ("notes", re.compile(r"notes?\s+to\s+(consolidated\s+)?financial\s+statements", re.I)),
]


def extract_pdf_text(pdf_path: Path) -> str:
    """Fast text extraction via pypdf. Returns the whole document as one string."""
    import pypdf

    try:
        reader = pypdf.PdfReader(str(pdf_path))
    except Exception as e:
        print(f"  [pdf-error] {pdf_path.name}: {e}")
        return ""
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n\n<!-- PAGE BREAK -->\n\n".join(pages)


def load_fb_documents() -> list[dict]:
    """Return one dict per FB document: {company, ticker, year, doc_name, pdf_path}."""
    jsonl = FB_REPO / "data" / "financebench_document_information.jsonl"
    docs: list[dict] = []
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d.get("doc_type") != "10k":
                continue
            company = d["company"]
            ticker = FB_TICKER_MAP.get(company)
            if not ticker:
                continue
            pdf = FB_REPO / "pdfs" / f"{d['doc_name']}.pdf"
            if not pdf.exists():
                continue
            docs.append(
                {
                    "company": company,
                    "ticker": ticker,
                    "year": d.get("doc_period"),
                    "doc_name": d["doc_name"],
                    "pdf": pdf,
                }
            )
    return docs


def phase_fb_parse(docs: list[dict], tqdm) -> int:
    """Parse every FB PDF into a markdown file under data/financebench/<TICKER>/."""
    n_written = 0
    for d in tqdm(docs, desc="[parse-fb]"):
        out = DATA / d["ticker"] / f"10k_{d['year']}.md"
        if out.exists() and out.stat().st_size > 0:
            continue
        text = extract_pdf_text(d["pdf"])
        if not text.strip():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        header = (
            f"# {d['company']} — 10-K FY{d['year']}\n\n"
            f"Ticker: {d['ticker']}\n\n"
            f"Source: FinanceBench ({d['doc_name']}.pdf)\n\n"
            "---\n\n"
        )
        out.write_text(header + text, encoding="utf-8")
        n_written += 1
    return n_written


def phase_fb_groundtruth() -> int:
    """Load the 150 open-source Q&A rows into data/financebench.db#ground_truth."""
    jsonl = FB_REPO / "data" / "financebench_open_source.jsonl"
    STRUCTURED_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(STRUCTURED_DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ground_truth (
            id TEXT PRIMARY KEY,
            company TEXT,
            ticker TEXT,
            doc_name TEXT,
            question TEXT,
            answer TEXT,
            question_type TEXT,
            justification TEXT
        )
        """
    )
    conn.execute("DELETE FROM ground_truth")
    n = 0
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            ticker = FB_TICKER_MAP.get(d["company"], "")
            conn.execute(
                "INSERT INTO ground_truth VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    d["financebench_id"],
                    d["company"],
                    ticker,
                    d.get("doc_name", ""),
                    d.get("question", ""),
                    str(d.get("answer", "")),
                    d.get("question_type", ""),
                    d.get("justification", ""),
                ),
            )
            n += 1
    conn.commit()
    conn.close()
    return n


# ----------------------------------------------------------------------
# Phase 2: S&P 500 universe (Wikipedia)


def load_sp500_universe() -> list[dict]:
    """Fetch the current S&P 500 constituents. Returns [{ticker, name, sector}].

    Tries the datasets/s-and-p-500-companies CSV on GitHub first (stable,
    permissively hosted, no UA blocking). Falls back to scraping Wikipedia
    with a real browser User-Agent if the CSV is unreachable.
    """
    import csv
    import io
    import urllib.request

    # Primary: GitHub CSV (no UA shenanigans)
    csv_url = (
        "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
        "main/data/constituents.csv"
    )
    try:
        req = urllib.request.Request(
            csv_url,
            headers={"User-Agent": "Mozilla/5.0 (SmartBaseAI loader)"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        out = []
        for row in reader:
            sym = (row.get("Symbol") or "").strip().replace(".", "-")
            name = (row.get("Name") or "").strip()
            sector = (row.get("Sector") or "").strip()
            if sym and name:
                out.append({"ticker": sym, "name": name, "sector": sector})
        if out:
            print(f"[sp500] loaded {len(out)} constituents from datasets.io CSV")
            return out
    except Exception as e:
        print(f"[sp500] CSV fetch failed ({type(e).__name__}: {str(e)[:80]}); trying Wikipedia fallback")

    # Fallback: Wikipedia with a real UA (pandas.read_html doesn't let us set UA
    # directly, so we fetch the HTML via requests and pass the text to pandas).
    try:
        import pandas as pd
        import requests

        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        tables = pd.read_html(io.StringIO(r.text))
        df = tables[0]
        out = []
        for _, row in df.iterrows():
            sym = str(row.get("Symbol", "")).strip().replace(".", "-")
            name = str(row.get("Security", "")).strip()
            sector = str(row.get("GICS Sector", "")).strip()
            if sym and name:
                out.append({"ticker": sym, "name": name, "sector": sector})
        print(f"[sp500] scraped {len(out)} constituents from Wikipedia (fallback)")
        return out
    except Exception as e:
        print(f"[sp500] all sources failed ({type(e).__name__}: {str(e)[:80]}); FB-only universe")
        return []


# ----------------------------------------------------------------------
# Phase 3: daily bars (yfinance)


def phase_bars(tickers: list[str], tqdm) -> int:
    """Download 10y of daily bars for each ticker. Write CSV and load into SQLite."""
    import yfinance as yf

    conn = sqlite3.connect(STRUCTURED_DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_bars (
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (ticker, date)
        )
        """
    )

    def load_one(ticker: str) -> int:
        out_csv = DATA / ticker / "bars.csv"
        if out_csv.exists() and out_csv.stat().st_size > 0:
            # Idempotent: trust existing CSVs, skip re-download.
            return 0
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="10y", interval="1d", auto_adjust=False)
        except Exception as e:
            print(f"  [bars-error] {ticker}: {type(e).__name__}: {str(e)[:80]}")
            return 0
        if hist is None or hist.empty:
            return 0
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        hist.to_csv(out_csv)
        rows = []
        for idx, r in hist.iterrows():
            try:
                rows.append(
                    (
                        ticker,
                        idx.strftime("%Y-%m-%d"),
                        float(r["Open"]),
                        float(r["High"]),
                        float(r["Low"]),
                        float(r["Close"]),
                        float(r["Volume"] or 0),
                    )
                )
            except Exception:
                pass
        conn.executemany(
            "INSERT OR REPLACE INTO daily_bars VALUES (?, ?, ?, ?, ?, ?, ?)", rows
        )
        conn.commit()
        return len(rows)

    total_rows = 0
    for ticker in tqdm(tickers, desc="[bars]"):
        total_rows += load_one(ticker)
    conn.close()
    return total_rows


# ----------------------------------------------------------------------
# Phase 4: profiles (yfinance.info)


def phase_profiles(universe: list[dict], tqdm) -> int:
    """Write one profile.md per company."""
    import yfinance as yf

    n = 0
    for u in tqdm(universe, desc="[profiles]"):
        ticker = u["ticker"]
        out = DATA / ticker / "profile.md"
        if out.exists() and out.stat().st_size > 0:
            continue
        try:
            info = yf.Ticker(ticker).info
        except Exception:
            info = {}
        name = info.get("longName") or u["name"]
        sector = info.get("sector") or u.get("sector") or ""
        industry = info.get("industry") or ""
        website = info.get("website") or ""
        country = info.get("country") or ""
        city = info.get("city") or ""
        employees = info.get("fullTimeEmployees")
        mcap = info.get("marketCap")
        exch = info.get("exchange") or ""
        summary = info.get("longBusinessSummary") or ""
        body = [
            f"# {name} ({ticker})",
            "",
            f"- **Ticker:** {ticker}",
            f"- **Exchange:** {exch}",
            f"- **Sector:** {sector}",
            f"- **Industry:** {industry}",
            f"- **HQ:** {city}, {country}".strip(", ").strip(),
            f"- **Employees:** {employees:,}" if isinstance(employees, int) else "- **Employees:** —",
            f"- **Market cap:** ${mcap:,}" if isinstance(mcap, int) else "- **Market cap:** —",
            f"- **Website:** {website}",
            "",
            "## Business description",
            "",
            summary or "(no summary available from yfinance)",
            "",
        ]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(body), encoding="utf-8")
        n += 1
    return n


# ----------------------------------------------------------------------
# Phase 5 (LARGE only): latest 10-K for non-FB SP500 via SEC EDGAR


def phase_extra_10ks(tickers: list[str], user_agent: str, tqdm) -> int:
    """Download the latest 10-K for each non-FB SP500 ticker via SEC EDGAR."""
    from sec_edgar_downloader import Downloader

    sec_dir = DOWNLOADS / "sec"
    sec_dir.mkdir(parents=True, exist_ok=True)
    # sec-edgar-downloader requires (company, email, download_path)
    name, _, email = user_agent.partition("<")
    email = email.rstrip(">").strip() or user_agent
    dl = Downloader(name.strip() or "SmartBaseAI", email, str(sec_dir))

    n_parsed = 0
    for ticker in tqdm(tickers, desc="[sec-10k]"):
        target = DATA / ticker / "10k_latest.md"
        if target.exists() and target.stat().st_size > 0:
            continue
        try:
            dl.get("10-K", ticker, limit=1, download_details=False)
        except Exception as e:
            print(f"  [sec-error] {ticker}: {type(e).__name__}: {str(e)[:80]}")
            continue
        # sec-edgar-downloader lays out files at:
        #   sec_dir/sec-edgar-filings/{ticker}/10-K/{accession}/full-submission.txt
        base = sec_dir / "sec-edgar-filings" / ticker / "10-K"
        if not base.exists():
            continue
        accessions = sorted(base.iterdir(), reverse=True)
        if not accessions:
            continue
        submission = accessions[0] / "full-submission.txt"
        if not submission.exists():
            continue
        try:
            raw = submission.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Very coarse filter: strip HTML/XBRL tags to recover prose.
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"&#?\w+;", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Trim to a reasonable size — EDGAR submissions are enormous.
        text = text[:400_000]
        # Preserve ONLY the accession number (the stable public identifier),
        # not the absolute filesystem path. The accession looks like
        # "0001234567-25-000001" and is the last-but-one path segment.
        accession = submission.parent.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"# {ticker} — latest 10-K (SEC EDGAR)\n\n"
            f"Source: SEC EDGAR filing {accession}\n\n"
            f"---\n\n{text}\n",
            encoding="utf-8",
        )
        n_parsed += 1
        # Clean up the giant full-submission.txt after we've extracted text
        try:
            submission.unlink()
        except Exception:
            pass
    return n_parsed


# ----------------------------------------------------------------------
# Phase 6: ingest into tenant


MAX_CHUNK_CHARS = 2000  # Hard cap so the embedder never sees anything it can't handle.


def _hard_split(s: str, max_chars: int) -> list[str]:
    """Force-split a blob that has no paragraph breaks into max_chars slices."""
    parts: list[str] = []
    i = 0
    while i < len(s):
        end = min(i + max_chars, len(s))
        # Try to break on a whitespace inside the last 10% of the window.
        if end < len(s):
            window_start = end - max_chars // 10
            slice_ = s[window_start:end]
            m = re.search(r"\s(?=\S*$)", slice_)
            if m:
                end = window_start + m.start()
        parts.append(s[i:end].strip())
        i = end
    return [p for p in parts if p]


def chunk_text(text: str, target_tokens: int = 500) -> list[str]:
    """Chunker with a hard MAX_CHUNK_CHARS cap so no single chunk is enormous.

    1. Split on blank lines (paragraphs).
    2. Hard-split any individual paragraph longer than MAX_CHUNK_CHARS.
    3. Pack paragraphs into chunks of ~target_tokens words, but never exceed
       MAX_CHUNK_CHARS characters per chunk.

    This is the fix for the ingest-phase segfault — extracted 10-K text from
    pypdf can contain giant "paragraphs" (tables merged into one blob,
    missing line breaks) that blow up the tokenizer. Capping at 2K chars
    bounds what sentence-transformers ever sees.
    """
    paragraphs: list[str] = []
    for p in re.split(r"\n\s*\n", text):
        p = p.strip()
        if not p:
            continue
        if len(p) > MAX_CHUNK_CHARS:
            paragraphs.extend(_hard_split(p, MAX_CHUNK_CHARS))
        else:
            paragraphs.append(p)

    chunks: list[str] = []
    buf: list[str] = []
    size_words = 0
    size_chars = 0
    for p in paragraphs:
        words = len(p.split())
        added_chars = len(p) + 2  # for the "\n\n" joiner
        if buf and (size_words + words > target_tokens or size_chars + added_chars > MAX_CHUNK_CHARS):
            chunks.append("\n\n".join(buf))
            buf = [p]
            size_words = words
            size_chars = len(p)
        else:
            buf.append(p)
            size_words += words
            size_chars += added_chars
    if buf:
        chunks.append("\n\n".join(buf))
    # Belt-and-braces — drop any empty chunks or anything over the cap.
    return [c[:MAX_CHUNK_CHARS] for c in chunks if c.strip()]


def phase_ingest(tqdm, force_cpu: bool = True) -> tuple[int, int]:
    """Walk data/financebench/ and push every .md into the tenant Chroma collection.

    ``force_cpu=True`` (default) pins sentence-transformers to CPU for this
    phase. The Large-tier first run crashed with a CUDA segfault during the
    first batch; CPU is slower but stable. Set force_cpu=False to use GPU.
    """
    if force_cpu:
        # Must be set before chromadb instantiates the embedding function.
        import os as _os
        _os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    from ai.vector_stores.chroma_store import TenantVectorStore

    store = TenantVectorStore(TENANT_ID)
    # Fresh ingest: drop any previous financebench vectors so reruns are idempotent.
    try:
        existing = store.collection.get(include=["metadatas"])
        if existing and existing.get("ids"):
            store.collection.delete(ids=existing["ids"])
            print(f"[ingest] wiped {len(existing['ids'])} stale vectors")
    except Exception as e:
        print(f"[ingest] wipe step skipped: {type(e).__name__}: {e}")

    md_files = sorted(DATA.rglob("*.md"))
    n_files = 0
    n_chunks = 0
    n_skipped_files = 0
    for path in tqdm(md_files, desc="[ingest]"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"  [read-error] {path.name}: {e}")
            n_skipped_files += 1
            continue
        if not text.strip():
            n_skipped_files += 1
            continue
        ticker = path.parent.name
        filename = path.name
        base_id = f"{TENANT_ID}:{ticker}/{filename}"
        try:
            chunks = chunk_text(text, target_tokens=500)
        except Exception as e:
            print(f"  [chunk-error] {ticker}/{filename}: {e}")
            n_skipped_files += 1
            continue
        file_chunks_ok = 0
        for i, chunk in enumerate(chunks):
            if not chunk.strip() or len(chunk) > MAX_CHUNK_CHARS:
                continue
            doc_id = f"{base_id}#{i}"
            meta = {
                "tenant": TENANT_ID,
                "ticker": ticker,
                "filename": filename,
                "path": f"{ticker}/{filename}",
                "chunk_idx": i,
                "source": "financebench-loader",
            }
            try:
                store.add_document(doc_id, chunk, meta)
                n_chunks += 1
                file_chunks_ok += 1
            except Exception as e:
                print(f"  [embed-error] {doc_id}: {type(e).__name__}: {str(e)[:100]}")
        if file_chunks_ok > 0:
            n_files += 1
        else:
            n_skipped_files += 1
    print(f"[ingest] files ingested: {n_files}, chunks: {n_chunks}, skipped: {n_skipped_files}")
    return n_files, n_chunks


# ----------------------------------------------------------------------
# Phase 7: tenant + user + reports


def ensure_tenant() -> None:
    from tenants.tenant_manager import TenantManager

    tm = TenantManager()
    models = [
        {"provider": "ollama", "name": "llama3", "label": "Local Llama 3"},
        {"provider": "openai", "name": "gpt-4o-mini", "label": "GPT-4o mini"},
        {"provider": "anthropic", "name": "claude-opus-4-6", "label": "Claude Opus 4.6"},
    ]
    config = {
        "name": TENANT_NAME,
        "description": TENANT_DESCRIPTION,
        "db_type": "sqlite",
        # Store as a repo-relative path so tenants.json doesn't leak the
        # operator's filesystem layout when it's committed.
        "db_config": {"path": "data/financebench.db"},
        "models": models,
        "model_type": models[0]["provider"],
        "model_name": models[0]["name"],
    }
    if tm.get(TENANT_ID) is None:
        tm.create(TENANT_ID, config)
        print(f"[tenant] created '{TENANT_ID}'")
    else:
        tm.update(TENANT_ID, config)
        print(f"[tenant] updated '{TENANT_ID}'")


def ensure_user() -> None:
    from db import user_repository

    u, p = DEMO_USER
    if user_repository.get_user(u) is not None:
        print(f"[user] '{u}' already exists")
        return
    user_repository.create_user(u, p, "user", TENANT_ID)
    print(f"[user] created '{u}' / '{p}'")


def wire_vault_root() -> None:
    """Make routes_files.VAULT_ROOTS include the new tenant at import time.

    This is a no-op at script runtime; the backend server picks up the new
    tenant root the next time it imports routes_files. Documented here for
    clarity — the seeded tenants all fall back to data/vaults/{id}/ if not
    explicitly mapped, so financebench WILL work without editing VAULT_ROOTS.
    We only need the directory to exist.
    """
    DATA.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------
# Main


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", choices=["small", "medium", "large"], default="medium")
    ap.add_argument(
        "--sec-user-agent",
        default="SmartBaseAI <yomik@medbit.co.il>",
        help="Required by SEC EDGAR policy. Name + email.",
    )
    ap.add_argument("--skip-sp500", action="store_true", help="Force FB-only universe")
    ap.add_argument("--max-extra-10k", type=int, default=None, help="Debug: cap SEC downloads")
    args = ap.parse_args()

    try:
        from tqdm import tqdm
    except Exception:
        def tqdm(it, **_):
            return it

    t0 = time.monotonic()
    print(f"\n==> FinanceBench loader — scale={args.scale}")
    print(f"    Target tenant: {TENANT_ID}\n")

    wire_vault_root()

    # Phase 0-1: FinanceBench PDFs
    ensure_fb_repo()
    fb_docs = load_fb_documents()
    print(f"[fb] {len(fb_docs)} FinanceBench 10-K documents identified")
    n_fb_md = phase_fb_parse(fb_docs, tqdm)
    print(f"[fb] wrote {n_fb_md} new 10-K markdown files")
    n_gt = phase_fb_groundtruth()
    print(f"[fb] loaded {n_gt} ground-truth Q&A rows")

    # Phase 2: universe
    fb_tickers = sorted({d["ticker"] for d in fb_docs})
    if args.scale == "small" or args.skip_sp500:
        universe = [
            {"ticker": t, "name": t, "sector": ""} for t in fb_tickers
        ]
    else:
        sp = load_sp500_universe()
        known = {u["ticker"] for u in sp}
        # Ensure all FB tickers are included even if the scraper missed one
        for t in fb_tickers:
            if t not in known:
                sp.append({"ticker": t, "name": t, "sector": ""})
        universe = sp
    print(f"[universe] {len(universe)} tickers in scope")

    # Phase 3: bars
    tickers = [u["ticker"] for u in universe]
    n_bar_rows = phase_bars(tickers, tqdm)
    print(f"[bars] inserted {n_bar_rows} new daily-bar rows")

    # Phase 4: profiles
    n_profiles = phase_profiles(universe, tqdm)
    print(f"[profiles] wrote {n_profiles} new profile files")

    # Phase 5 (large only): non-FB latest 10-K
    n_extra = 0
    if args.scale == "large":
        extra = [t for t in tickers if t not in set(fb_tickers)]
        if args.max_extra_10k:
            extra = extra[: args.max_extra_10k]
        print(f"[sec-10k] will download latest 10-K for {len(extra)} non-FB tickers")
        try:
            n_extra = phase_extra_10ks(extra, args.sec_user_agent, tqdm)
        except Exception as e:
            print(f"[sec-10k] aborted: {type(e).__name__}: {e}")
            traceback.print_exc()

    # Phase 7: tenant + user
    ensure_tenant()
    ensure_user()

    # Phase 6: ingest
    n_files, n_chunks = phase_ingest(tqdm)

    # Final report
    elapsed = time.monotonic() - t0
    print("\n" + "=" * 60)
    print("LOADER SUMMARY")
    print("=" * 60)
    print(f"Scale:              {args.scale}")
    print(f"Companies:          {len(universe)}")
    print(f"FB 10-Ks:           {n_fb_md} new + {len(fb_docs)-n_fb_md} cached = {len(fb_docs)} total")
    print(f"Non-FB latest 10-Ks:{n_extra}")
    print(f"Profiles written:   {n_profiles}")
    print(f"Bar rows inserted:  {n_bar_rows}")
    print(f"Ground-truth Q&A:   {n_gt}")
    print(f"Ingested files:     {n_files}")
    print(f"Embedded chunks:    {n_chunks}")
    print(f"Tenant:             {TENANT_ID} ({DEMO_USER[0]} / {DEMO_USER[1]})")
    print(f"Elapsed:            {elapsed/60:.1f} min")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
