from .tenant_storage import TenantStorage


class TenantManager:
    """Utility class for creating and managing tenants."""

    def __init__(self) -> None:
        # Normalize keys to avoid mismatches caused by stray whitespace
        data = TenantStorage.load()
        self._tenants = {k.strip(): v for k, v in data.items()}

    def create(self, tenant_id: str, config: dict) -> None:
        """Create a tenant with the given configuration."""
        tid = tenant_id.strip()
        if tid in self._tenants:
            raise ValueError(f"Tenant '{tid}' already exists")
        self._tenants[tid] = config
        TenantStorage.save(self._tenants)

    def delete(self, tenant_id: str) -> None:
        """Delete a tenant by identifier."""
        tid = tenant_id.strip()
        if tid in self._tenants:
            self._tenants.pop(tid)
            TenantStorage.save(self._tenants)

    def get(self, tenant_id: str) -> dict:
        """Retrieve a tenant configuration."""
        return self._tenants.get(tenant_id.strip())

    def list(self) -> list:
        """Return a list of tenant identifiers."""
        return list(self._tenants.keys())
