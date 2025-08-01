from typing import Iterable

from db.connectors import (
    PostgresConnector,
    MySQLConnector,
    MongoDBConnector,
    APIConnector,
)

from .cleaners import clean_text
from .metadata_generator import generate_metadata


class ETLManager:
    """Coordinate extraction, transformation and loading steps."""

    CONNECTORS = {
        "postgres": PostgresConnector,
        "mysql": MySQLConnector,
        "mongodb": MongoDBConnector,
        "api": APIConnector,
    }

    def __init__(self, db_type: str, config: dict) -> None:
        connector_cls = self.CONNECTORS.get(db_type)
        if connector_cls is None:
            raise ValueError(f"Unsupported db type: {db_type}")
        self.connector = connector_cls(config)
        self.connector.connect()

    def extract(self, source: str, params=None):
        """Retrieve raw records from the data source."""
        return self.connector.execute(source, params)

    def transform(self, records: Iterable[dict]) -> list:
        """Apply cleaners and attach metadata."""
        transformed = []
        for record in records:
            text = clean_text(record.get("text", ""))
            metadata = generate_metadata(record)
            transformed.append({"text": text, "metadata": metadata})
        return transformed

    def load(self, records: Iterable[dict]):
        """Placeholder load implementation."""
        return list(records)

    def run(self, source: str, params=None):
        """Execute the full ETL pipeline."""
        raw = self.extract(source, params)
        raw_records = raw if isinstance(raw, list) else [raw]
        processed = self.transform(raw_records)
        return self.load(processed)

    def close(self) -> None:
        """Close the active connector."""
        self.connector.close()
