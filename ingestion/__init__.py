"""Utilities for ingesting and preparing data."""

from .cleaners import clean_text, remove_stopwords
from .metadata_generator import generate_metadata
from .etl_manager import ETLManager

__all__ = [
    "clean_text",
    "remove_stopwords",
    "generate_metadata",
    "ETLManager",
]
