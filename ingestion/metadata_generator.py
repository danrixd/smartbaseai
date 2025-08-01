from datetime import datetime


def generate_metadata(record: dict) -> dict:
    """Create metadata information for an ingested record."""
    metadata = {
        "length": len(record.get("text", "")),
        "timestamp": datetime.utcnow().isoformat(),
    }
    source = record.get("source")
    if source:
        metadata["source"] = source
    return metadata
