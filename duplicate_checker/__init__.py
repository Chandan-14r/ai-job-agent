"""Duplicate Checker and Canonical URL Normalization Module."""

from .deduplicator import DuplicateChecker, DuplicateCheckResult, canonicalize_url

__all__ = ["DuplicateChecker", "DuplicateCheckResult", "canonicalize_url"]
