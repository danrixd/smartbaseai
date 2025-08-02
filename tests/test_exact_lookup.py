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


def test_response_generator_exact_and_rag():
    rg = ResponseGenerator(TENANT)

    def fake_query_rag(self, user_message, history=None):
        return "RAG"

    # Replace query_rag to avoid actual model calls
    rg.query_rag = fake_query_rag.__get__(rg, ResponseGenerator)

    exact_msg = f"What is the close value for date: {DATE_STR}?"
    response = rg.generate_response(exact_msg)
    assert "Close value for" in response

    general_msg = "What happened on 2023-07-09?"
    assert rg.generate_response(general_msg) == "RAG"

