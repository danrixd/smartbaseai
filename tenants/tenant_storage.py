import json
from pathlib import Path


TENANT_FILE = Path(__file__).with_name("tenants.json")


class TenantStorage:
    """Persistence layer for tenant configurations."""

    @staticmethod
    def load() -> dict:
        """Load tenant configurations from disk."""
        if TENANT_FILE.exists():
            with TENANT_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    @staticmethod
    def save(data: dict) -> None:
        """Save tenant configurations to disk."""
        with TENANT_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
