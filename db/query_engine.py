"""Utility for routing queries to the correct connector."""

from config.tenant_config import TenantConfig
from .connectors import (
    PostgresConnector,
    MySQLConnector,
    MongoDBConnector,
    APIConnector,
)


class QueryEngine:
    """Route queries to the appropriate connector based on tenant config."""

    CONNECTOR_MAP = {
        "postgres": PostgresConnector,
        "mysql": MySQLConnector,
        "mongodb": MongoDBConnector,
        "api": APIConnector,
    }

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self.config = TenantConfig.get(tenant_id)
        db_type = self.config.get("db_type", "postgres")
        connector_cls = self.CONNECTOR_MAP.get(db_type)
        if connector_cls is None:
            raise ValueError(f"Unsupported db type: {db_type}")
        self.connector = connector_cls(self.config.get("db_config", {}))
        self.connector.connect()

    def execute(self, query: str, params=None):
        """Execute a query using the tenant's connector."""
        return self.connector.execute(query, params)

    def close(self) -> None:
        """Close the active connector."""
        self.connector.close()
