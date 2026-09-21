"""Deterministic builder for the self-contained bilingual v2.7.0 HTML guide."""

from __future__ import annotations

__all__ = ["__version_of_record__"]

#: The HTML deliverable always mirrors the workshop release named in ``VERSION``;
#: this constant only records which release the source tree was written for so a
#: mismatch is caught at build time rather than shipped.
__version_of_record__ = "2.7.0"
