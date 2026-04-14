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
    """Scrape Wikipedia for current S&P 500 constituents. Returns [{ticker, name, sector}]."""
    import pandas as pd

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        tables = pd.read_html(url)
        df = tables[0]
        out = []
        for _, row in df.iterrows():
            sym = str(row.get("Symbol", "")).strip().replace(".", "-")
            name = str(row.get("Security", "")).strip()
            sector = str(row.get("GICS Sector", "")).strip()
            if sym and name:
                out.append({"ticker": sym, "name": name, "sector": sector})
        print(f"[sp500] scraped {len(out)} constituents from Wikipedia")
        return out
    except Exception as e:
        print(f"[sp500] Wikipedia scrape failed ({e}); falling back to FB-only universe")
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
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"# {ticker} — latest 10-K (SEC EDGAR)\n\n"
            f"Source: {submission}\n\n"
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


def chunk_text(text: str, target_tokens: int = 500) -> list[str]:
    """Very rough chunker: split on blank lines, pack until ~target_tokens words."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for p in paragraphs:
        words = len(p.split())
        if size + words > target_tokens and buf:
            chunks.append("\n\n".join(buf))
            buf = [p]
            size = words
        else:
            buf.append(p)
            size += words
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def phase_ingest(tqdm) -> tuple[int, int]:
    """Walk data/financebench/ and push every .md into the tenant Chroma collection."""
    from ai.vector_stores.chroma_store import TenantVectorStore

    store = TenantVectorStore(TENANT_ID)
    # Fresh ingest: drop any previous financebench vectors so reruns are idempotent.
    try:
        existing = store.collection.get(include=[])
        if existing and existing.get("ids"):
            store.collection.delete(ids=existing["ids"])
    except Exception:
        pass

    md_files = sorted(DATA.rglob("*.md"))
    n_files = 0
    n_chunks = 0
    for path in tqdm(md_files, desc="[ingest]"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if not text.strip():
            continue
        ticker = path.parent.name
        filename = path.name
        base_id = f"{TENANT_ID}:{ticker}/{filename}"
        chunks = chunk_text(text, target_tokens=500)
        for i, chunk in enumerate(chunks):
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
            except Exception as e:
                print(f"  [ingest-error] {doc_id}: {e}")
        n_files += 1
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
        "db_config": {"path": str(STRUCTURED_DB)},
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
