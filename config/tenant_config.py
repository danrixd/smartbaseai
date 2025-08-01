"""Placeholder tenant configuration storage."""

TENANT_CONFIGS = {
    "default": {
        "name": "Default Tenant",
        "plan": "basic",
        # retrieval augmented generation disabled by default
        "rag_enabled": False,
        # default embedder and vector store names
        "embedder": "local",
        "vector_store": "faiss",
    }
}

class TenantConfig:
    """Access tenant configuration."""

    @staticmethod
    def get(tenant_id: str):
        """Return configuration for a tenant."""
        return TENANT_CONFIGS.get(tenant_id, TENANT_CONFIGS["default"])
