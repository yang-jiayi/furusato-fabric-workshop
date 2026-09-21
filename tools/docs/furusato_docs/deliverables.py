"""Shared filenames for the original release and separately named corrections."""

from __future__ import annotations

import re
from dataclasses import dataclass


def validate_edition(value: str) -> str:
    if value and not re.fullmatch(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", value):
        raise ValueError("edition must contain lowercase letters, digits, hyphens or underscores")
    if len(value) > 40:
        raise ValueError("edition must not exceed 40 characters")
    return value


@dataclass(frozen=True)
class DeliverableNames:
    participant: str
    validation: str
    workbook: str
    html: str

    @property
    def office(self) -> tuple[str, str, str]:
        return self.participant, self.validation, self.workbook

    def selected_office(self, public_documents_only: bool = False) -> tuple[str, ...]:
        return (self.participant,) if public_documents_only else self.office

    @property
    def public_pair(self) -> tuple[str, str]:
        return self.participant, self.html


def deliverable_names(version: str, edition: str = "") -> DeliverableNames:
    suffix = f"_{validate_edition(edition)}" if edition else ""
    return DeliverableNames(
        participant=f"Fabric_IQ_Ontology_Workshop_Furusato_Participant_v{version}{suffix}.docx",
        validation=f"Furusato_Data_Agent_Validation_10_v{version}{suffix}.docx",
        workbook=f"Furusato_Notebook_01-05_Processing_Specification_v{version}{suffix}.xlsx",
        html=f"furusato-workshop-v{version.replace('.', '-')}-complete{suffix}.html",
    )
