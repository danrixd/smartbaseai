class APIConnector:
    """Placeholder external API connector."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.connected = False

    def connect(self) -> None:
        """Establish connection to an API endpoint."""
        self.connected = True

    def execute(self, endpoint: str, payload=None):
        """Execute an API request."""
        if not self.connected:
            raise RuntimeError("Connector not connected")
        return {"api": endpoint, "payload": payload}

    def close(self) -> None:
        """Close the API connection."""
        self.connected = False
