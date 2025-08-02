import os
import sqlite3

from chatbot.response_generator import ResponseGenerator
from db.query_engine import exact_lookup


TENANT = "testtenant"
DATE_STR = "2023-07-09 22:01"


def setup_module(module):
    """Create a temporary SQLite DB for the tenant."""
    os.makedirs("data", exist_ok=True)
    db_path = f"data/{TENANT}.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS market_data (date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    cursor.execute(
        "INSERT INTO market_data VALUES (?, ?, ?, ?, ?, ?)",
        (DATE_STR, 10.0, 12.0, 9.0, 11.0, 1000.0),
    )
    conn.commit()
    conn.close()


def test_exact_lookup_function():
    row = exact_lookup(DATE_STR, TENANT)
    assert row["close"] == 11.0


def test_response_generator_exact_lookup(monkeypatch):
    """Ensure DB rows are incorporated in the generated prompt."""
    rg = ResponseGenerator(TENANT, model_type="openai")

    # Avoid RAG context and echo the prompt for inspection
    monkeypatch.setattr(rg, "_search_rag", lambda message: "")
    monkeypatch.setattr(rg.model, "generate", lambda prompt: prompt)

    exact_msg = f"What is the close value for date: {DATE_STR}?"
    prompt = rg.generate_response(exact_msg, [{"role": "user", "text": "hi"}])
    assert "Close value for" in prompt
    assert "user: hi".lower() in prompt.lower()

    # When no date is present the DB section should be empty
    general_msg = "What happened on 2023-07-09?"
    prompt = rg.generate_response(general_msg)
    assert "Close value" not in prompt

