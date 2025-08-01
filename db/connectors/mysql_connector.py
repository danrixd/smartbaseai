class MySQLConnector:
    """Placeholder MySQL connector."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.connected = False

    def connect(self) -> None:
        """Establish connection to MySQL database."""
        self.connected = True

    def execute(self, query: str, params=None):
        """Execute a query against MySQL."""
        if not self.connected:
            raise RuntimeError("Connector not connected")
        return {"db": "mysql", "query": query, "params": params}

    def close(self) -> None:
        """Close the MySQL connection."""
        self.connected = False
