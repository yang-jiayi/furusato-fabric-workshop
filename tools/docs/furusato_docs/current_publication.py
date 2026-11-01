"""Versioned standalone publication, independent of historical Word approvals."""
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class CurrentPublication:
    version: str

    def __post_init__(self):
        if not re.fullmatch(r"[1-9]\d*\.\d+\.\d+", self.version):
            raise ValueError("Current publication requires a numeric workshop version")

    @property
    def html_name(self):
        return "furusato-workshop-v" + self.version.replace(".", "-") + "-complete.html"

    @property
    def package_name(self):
        return "Furusato_Workshop_v" + self.version + "_current.zip"

    @property
    def title(self):
        return "Furusato Workshop " + self.version

    @property
    def display_version(self):
        return "v" + self.version

    @property
    def is_release(self):
        return True


def current_publication(root):
    return CurrentPublication((Path(root) / "WORKSHOP_VERSION").read_text(encoding="utf-8").strip())


def publication_for_model(root, metadata, word_sha, release_profile):
    profile = current_publication(root)
    if (release_profile is not None or word_sha is not None
            or metadata.get("participantEdition") is not True
            or metadata.get("deliveryMode") != "html-lab"
            or metadata.get("version") != profile.version
            or metadata.get("currentArtifactSet", {}).get("workshopVersion") != profile.version):
        raise ValueError("HTML+Lab delivery requires its current version and artifact binding, not a Word release profile")
    return profile
