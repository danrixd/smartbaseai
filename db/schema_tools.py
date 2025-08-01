"""Helpers for schema introspection and management."""

from typing import Any


def list_objects(connector: Any):
    """Return a list of database objects using the connector."""
    return connector.execute("LIST OBJECTS")


def describe_object(connector: Any, name: str):
    """Return schema information for a database object."""
    return connector.execute(f"DESCRIBE {name}")


def create_object(connector: Any, definition: str):
    """Create a database object using a schema definition."""
    return connector.execute(f"CREATE {definition}")


def drop_object(connector: Any, name: str):
    """Drop a database object."""
    return connector.execute(f"DROP {name}")
