"""
AI Providers module for EDEN Asset Library.

This module provides a modular interface for AI-powered data extraction.
Currently supports OpenAI, with architecture designed for future providers (Anthropic, etc.)
"""

from .openai import extract_eden_asset_data, OpenAIProvider
from .document_extractor import (
    extract_all_document_text,
    extract_text_from_url,
    extract_text_from_file,
    can_extract_text,
    is_skipped_file,
)
from .merge_logic import (
    merge_extracted_data,
    build_field_updates,
    is_empty_value,
)

__all__ = [
    "extract_eden_asset_data",
    "OpenAIProvider",
    "extract_all_document_text",
    "extract_text_from_url",
    "extract_text_from_file",
    "can_extract_text",
    "is_skipped_file",
    "merge_extracted_data",
    "build_field_updates",
    "is_empty_value",
]
