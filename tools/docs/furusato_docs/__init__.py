"""Deterministic builders and validators for the Furusato workshop Office deliverables.

The package never invents values. Every number, name, path, parameter default,
hash, instruction text and KQL/SQL snippet that reaches a deliverable is read
from the v2.7.0 runtime assets under ``workshop/v2.7.0`` at build time.
"""

__all__ = [
    "context",
    "parameters",
    "tests10",
    "docx_kit",
    "oox",
    "participant_guide",
    "validation_doc",
    "workbook",
    "validators",
]

PACKAGE_VERSION = "2.7.0"
