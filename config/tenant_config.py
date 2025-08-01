"""Placeholder tenant configuration storage."""

TENANT_CONFIGS = {
    "default": {
        "name": "Default Tenant",
        "plan": "basic",
    }
}

class TenantConfig:
    """Access tenant configuration."""

    @staticmethod
    def get(tenant_id: str):
        """Return configuration for a tenant."""
        return TENANT_CONFIGS.get(tenant_id, TENANT_CONFIGS["default"])
