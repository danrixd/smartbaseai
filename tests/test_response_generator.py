"""Tests for the combined ResponseGenerator logic."""

import os
import sqlite3

from chatbot.response_generator import ResponseGenerator

TENANT = "respgen"
DATE_STR = "2024-01-02 03:04"


def setup_module(module):
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(f"data/{TENANT}.db")
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS market_data (date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    cursor.execute(
        "INSERT INTO market_data VALUES (?, ?, ?, ?, ?, ?)",
        (DATE_STR, 1.0, 2.0, 0.5, 1.5, 50.0),
    )
    conn.commit()
    conn.close()


def _build_rg(monkeypatch, rag_text=""):
    rg = ResponseGenerator(TENANT, model_type="openai")
    monkeypatch.setattr(rg, "_search_rag", lambda message: rag_text)
    # Echo the prompt for assertions
    monkeypatch.setattr(rg.model, "generate", lambda prompt: prompt)
    return rg


def test_db_and_rag_combined(monkeypatch):
    rg = _build_rg(monkeypatch, rag_text="context")
    prompt = rg.generate_response(f"stats at {DATE_STR}?", [{"role": "user", "text": "hi"}])
    assert "Close value for" in prompt  # DB data included
    assert "Additional context" in prompt  # RAG context fused in
    assert "context" in prompt  # RAG text included
    assert "user: hi".lower() in prompt.lower()


def test_db_only(monkeypatch):
    rg = _build_rg(monkeypatch, rag_text="")
    prompt = rg.generate_response(f"stats at {DATE_STR}?")
    assert "Close value for" in prompt
    assert "Additional context" not in prompt


def test_rag_only(monkeypatch):
    rg = _build_rg(monkeypatch, rag_text="rag info")
    prompt = rg.generate_response("general question")
    assert "rag info" in prompt
    assert "Close value" not in prompt
    assert "Additional context" not in prompt


def test_no_results(monkeypatch):
    rg = _build_rg(monkeypatch, rag_text="")
    # Message without date and RAG returns nothing
    result = rg.generate_response("what is up?")
    assert result == "No information"


