from .tenant_storage import TenantStorage


class TenantManager:
    """Utility class for creating and managing tenants.

    Reads ``tenants.json`` on every call so that multiple ``TenantManager``
    instances (e.g. one in ``routes_admin`` and one in ``routes_chat``) always
    see the latest state. Previously each instance cached the file at
    construction time, which caused tenants created via the admin API to be
    invisible to the chat route until the process restarted.
    """

    def _load(self) -> dict:
        data = TenantStorage.load()
        return {k.strip(): v for k, v in data.items()}

    def create(self, tenant_id: str, config: dict) -> None:
        """Create a tenant with the given configuration."""
        tid = tenant_id.strip()
        tenants = self._load()
        if tid in tenants:
            raise ValueError(f"Tenant '{tid}' already exists")
        tenants[tid] = config
        TenantStorage.save(tenants)

    def update(self, tenant_id: str, config: dict) -> None:
        """Replace an existing tenant's configuration."""
        tid = tenant_id.strip()
        tenants = self._load()
        if tid not in tenants:
            raise KeyError(f"Tenant '{tid}' does not exist")
        tenants[tid] = config
        TenantStorage.save(tenants)

    def delete(self, tenant_id: str) -> None:
        """Delete a tenant by identifier."""
        tid = tenant_id.strip()
        tenants = self._load()
        if tid in tenants:
            tenants.pop(tid)
            TenantStorage.save(tenants)

    def get(self, tenant_id: str) -> dict | None:
        """Retrieve a tenant configuration (always fresh from disk)."""
        return self._load().get(tenant_id.strip())

    def list(self) -> list:
        """Return a list of tenant identifiers."""
        return list(self._load().keys())
