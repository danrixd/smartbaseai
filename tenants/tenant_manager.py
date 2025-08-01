from .tenant_storage import TenantStorage


class TenantManager:
    """Utility class for creating and managing tenants."""

    def __init__(self) -> None:
        self._tenants = TenantStorage.load()

    def create(self, tenant_id: str, config: dict) -> None:
        """Create a tenant with the given configuration."""
        if tenant_id in self._tenants:
            raise ValueError(f"Tenant '{tenant_id}' already exists")
        self._tenants[tenant_id] = config
        TenantStorage.save(self._tenants)

    def delete(self, tenant_id: str) -> None:
        """Delete a tenant by identifier."""
        if tenant_id in self._tenants:
            self._tenants.pop(tenant_id)
            TenantStorage.save(self._tenants)

    def get(self, tenant_id: str) -> dict:
        """Retrieve a tenant configuration."""
        return self._tenants.get(tenant_id)

    def list(self) -> list:
        """Return a list of tenant identifiers."""
        return list(self._tenants.keys())
