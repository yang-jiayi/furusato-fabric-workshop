"""An old real image may illustrate unchanged UI, never prove changed instructions."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from furusato_docs.capture_policy import capture_problems, ci_instruction_digest

TEXT = "CURRENT\nCODE INTERPRETER: BOUNDED, EXECUTED, SECONDARY\nRead actual inputs.\n\nFINAL CHECK\nKeep evidence.\n"
HASHES = {tag: hashlib.sha256(tag.encode()).hexdigest() for tag in ("16-30", "18-30", "17-40")}


class CapturePolicyTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "schemaVersion": "furusato-real-ui-captures/v1",
            "pixelsEdited": False,
            "instructionRevision": 6,
            "globalInstructionsSha256": hashlib.sha256(b"prior instructions").hexdigest(),
            "usage": {
                "mode": "ci-illustration-only", "activeTags": ["17-40"],
                "retainedOnlyTags": ["16-30", "18-30"], "currentConfigurationCaptured": False,
                "ciInstructionsSha256": ci_instruction_digest(TEXT),
            },
            "captures": {
                tag: {"path": f"screenshots/{tag}.png", "sha256": digest, "originalSha256": digest}
                for tag, digest in HASHES.items()
            },
        }

    def check(self, registry=None, text=TEXT, embedded=None, enabled=True, preview=True):
        return capture_problems(
            self.registry if registry is None else registry, text, HASHES,
            {HASHES["17-40"]} if embedded is None else embedded,
            code_interpreter_enabled=enabled, preview_enabled=preview,
        )

    def test_unchanged_ci_illustration_keeps_prior_profile_identity(self):
        before = copy.deepcopy(self.registry)
        self.assertEqual(self.check(), [])
        self.assertEqual(self.registry, before)
        self.assertNotEqual(self.registry["globalInstructionsSha256"], hashlib.sha256(TEXT.encode()).hexdigest())

    def test_obsolete_configuration_images_cannot_be_embedded(self):
        for tag in ("16-30", "18-30"):
            with self.subTest(tag=tag):
                self.assertTrue(self.check(embedded={HASHES["17-40"], HASHES[tag]}))

    def test_ci_changes_or_disabled_tools_invalidate_reuse(self):
        self.assertTrue(self.check(text=TEXT.replace("actual inputs", "other inputs")))
        self.assertTrue(self.check(enabled=False))
        self.assertTrue(self.check(preview=False))

    def test_missing_active_or_corrupted_retained_image_fails(self):
        self.assertTrue(self.check(embedded=set()))
        broken = copy.deepcopy(self.registry)
        broken["captures"]["16-30"]["originalSha256"] = "altered"
        self.assertTrue(self.check(registry=broken))

    def test_usage_cannot_claim_current_configuration_or_unknown_tags(self):
        for key, value in (("currentConfigurationCaptured", True), ("activeTags", ["16-30"]), ("mode", "trust-me")):
            broken = copy.deepcopy(self.registry)
            broken["usage"][key] = value
            with self.subTest(key=key):
                self.assertTrue(self.check(registry=broken))

    def test_full_configuration_mode_still_requires_current_hash_and_all_images(self):
        full = copy.deepcopy(self.registry)
        full.pop("usage")
        self.assertTrue(self.check(registry=full, embedded=set(HASHES.values())))
        full["globalInstructionsSha256"] = hashlib.sha256(TEXT.encode()).hexdigest()
        self.assertEqual(self.check(registry=full, embedded=set(HASHES.values())), [])
        self.assertTrue(self.check(registry=full))

    def test_missing_ci_section_is_not_a_silent_fallback(self):
        with self.assertRaises(ValueError):
            self.check(text="No CI section")
        with self.assertRaises(ValueError):
            ci_instruction_digest("\nFINAL CHECK\nCODE INTERPRETER: BOUNDED, EXECUTED, SECONDARY\nRead actual inputs.")

    def test_reuse_cannot_erase_captured_profile_identity(self):
        for key in ("instructionRevision", "globalInstructionsSha256"):
            broken = copy.deepcopy(self.registry)
            broken.pop(key)
            with self.subTest(key=key):
                self.assertTrue(self.check(registry=broken))


if __name__ == "__main__":
    unittest.main()
