import pytest

from ingestion.etl_manager import ETLManager
from ai.rag_pipeline import RAGPipeline
from ai.embeddings import LocalEmbeddings
from ai.vector_stores import FaissStore
from ai.models import OpenAIModel
from chatbot.response_generator import ResponseGenerator
from config import tenant_config


class DummyConnector:
    def __init__(self, config):
        self.connected = False
        self.config = config

    def connect(self):
        self.connected = True

    def execute(self, source, params=None):
        # Return sample records with text and source
        return [
            {"text": " Hello World ", "source": source},
            {"text": "Another Document", "source": source},
        ]

    def close(self):
        self.connected = False


def test_etl_manager_run(monkeypatch):
    monkeypatch.setitem(ETLManager.CONNECTORS, "dummy", DummyConnector)
    manager = ETLManager("dummy", {})
    records = manager.run("src")
    manager.close()

    assert len(records) == 2
    first = records[0]
    assert first["text"] == "hello world"
    assert first["metadata"]["source"] == "src"
    assert "timestamp" in first["metadata"]
    assert first["metadata"]["length"] == len(" Hello World ")


def test_etl_manager_invalid_type():
    with pytest.raises(ValueError):
        ETLManager("unknown", {})


def test_rag_pipeline_query_and_answer():
    pipeline = RAGPipeline(
        embedder=LocalEmbeddings(),
        vector_store=FaissStore(),
        model=OpenAIModel(),
    )
    pipeline.add_documents(["alpha", "beta"], [{"text": "alpha"}, {"text": "beta"}])

    query_emb = pipeline.embedder.embed(["alpha"])[0]
    results = pipeline.vector_store.query(query_emb, top_k=1)
    assert results[0][0]["text"] == "alpha"

    answer = pipeline.answer("alpha", top_k=1)
    expected = "[OpenAI] Response to: alpha\nQuestion: alpha\nAnswer:"
    assert answer == expected


def test_response_generator_rag_integration(monkeypatch):
    monkeypatch.setitem(
        tenant_config.TENANT_CONFIGS,
        "rag",
        {"model": "openai", "rag_enabled": True},
    )
    gen = ResponseGenerator("rag")
    gen.pipeline.add_documents(["info"], [{"text": "info"}])

    reply = gen.generate("info?")
    assert reply == "[OpenAI] Response to: info\nQuestion: info?\nAnswer:"


