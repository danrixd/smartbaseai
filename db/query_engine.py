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


def exact_lookup(date_str: str, tenant_id: str, table: str = "market_data") -> dict:
    """Retrieve exact row from the tenant's database by date.

    Args:
        date_str: Date-time string in ISO format "YYYY-MM-DD HH:MM"
        tenant_id: Current tenant identifier
        table: Target table name

    Returns:
        dict: Matching row or {} if not found
    """
    import sqlite3

    db_path = f"data/{tenant_id}.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = f"SELECT * FROM {table} WHERE date = ? LIMIT 1"
        cursor.execute(query, (date_str,))
        row = cursor.fetchone()
        conn.close()
    except Exception:
        return {}

    if not row:
        return {}

    columns = ["date", "open", "high", "low", "close", "volume"]
    return dict(zip(columns, row))
