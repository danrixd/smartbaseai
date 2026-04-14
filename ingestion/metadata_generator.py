from datetime import datetime, timezone


def generate_metadata(record: dict) -> dict:
    """Create metadata information for an ingested record."""
    metadata = {
        "length": len(record.get("text", "")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    source = record.get("source")
    if source:
        metadata["source"] = source
    return metadata
