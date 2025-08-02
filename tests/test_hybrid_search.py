from ai.vector_stores.chroma_store import TenantVectorStore


def test_tenant_vector_store_hybrid_query_keyword(tmp_path):
    store = TenantVectorStore("tenant", persist_dir=str(tmp_path))
    store.add_document("1", "alpha", {})
    store.add_document("2", "event on 2024-05-01", {})

    results = store.hybrid_query("2024-05-01", n_results=2)
    docs = results.get("documents", [[]])[0]
    assert "event on 2024-05-01" in docs
