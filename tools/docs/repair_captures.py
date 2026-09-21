"""Repair the shipped screenshot carrier, idempotently and verifiably.

Four captures in ``tools/docs/assets/style-carrier.zip`` needed work that cannot
be redone by hand each time the carrier is regenerated:

* four Instances captures had been replaced by frames taken while the grid was
  still painting, and the authentic settled captures live in an earlier commit;
* the Activator Rules capture had likewise regressed to a blank frame;
* three captures carry a person's name, an internal folder or a licence state.

Every repair below is declarative: a source commit, an operation, and the SHA-256
the result must have. Running the tool twice changes nothing, and ``--check``
fails when the carrier no longer holds the repaired bytes - which is what stops a
carrier rebuild from quietly reintroducing a blank or unredacted capture.

    python tools/docs/repair_captures.py           # repair in place
    python tools/docs/repair_captures.py --check   # fail if a repair is missing
"""

from __future__ import annotations

import argparse
import hashlib
import io
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

#: The neutral fill used for every redaction, so a covered region reads as
#: removed rather than as a plausible substitute.
REDACTION = (217, 217, 217)

#: Commit holding the v2.7.0 release carrier, the last state in which the four
#: Instances captures and the Activator Rules capture were settled and populated.
RELEASE = "c6e4060"

#: Commit holding the already-restored and redacted Activator Rules capture.
REPAIRED_RULES = "795d5cc0"

#: Baseline commit for this fix loop. The three redaction repairs read their
#: source from here rather than from the working carrier, so re-running the tool
#: redacts the original pixels once instead of stacking a second grey block on
#: top of the first.
BASELINE = "d4f483c"


@dataclass(frozen=True)
class Repair:
    """One capture, where its authentic pixels come from, and what to remove."""

    tag: str
    source: str
    reason: str
    #: Crop box applied to the source capture, if any.
    crop: tuple[int, int, int, int] | None = None
    #: Redaction boxes as fractions of the (post-crop) size.
    redact: tuple[tuple[float, float, float, float], ...] = ()
    #: Source geometry the crop was measured against; a mismatch aborts.
    expect_size: tuple[int, int] | None = None
    #: SHA-256 the repaired PNG must have.
    digest: str = ""
    notes: str = field(default="")


#: The Premium-trial banner occupies rows 1-32 and the navigation rail columns
#: 0-67 in every capture from that session, measured rather than assumed.
INSTANCES_CROP = (68, 33, 1600, 903)

REPAIRS: tuple[Repair, ...] = (
    Repair(
        "7-14",
        RELEASE,
        "the shipped capture was taken while the grid was still loading",
        crop=INSTANCES_CROP,
        expect_size=(1600, 903),
        digest="869c4e63952844735859c9f8f34d63d2770d467ec07b13f776189d33422b92f1",
    ),
    Repair(
        "7-17",
        RELEASE,
        "the shipped capture was taken while the grid was still loading",
        crop=INSTANCES_CROP,
        expect_size=(1600, 903),
        digest="a9dff65322a1f2386aef2a1d81082cec6e0013b038864389b9fae8b32e45a9bf",
    ),
    Repair(
        "7-20",
        RELEASE,
        "the shipped capture was taken while the grid was still loading",
        crop=INSTANCES_CROP,
        expect_size=(1600, 903),
        digest="7b30292638a8253d5dd8bf62dbcd9d20cd9d5f82dbf6eb24cd3ec9264b684d29",
    ),
    Repair(
        "7-26",
        RELEASE,
        "the shipped capture was taken while the grid was still loading",
        crop=INSTANCES_CROP,
        expect_size=(1600, 903),
        digest="472ab1f90310eab8e1db947c5d1bb5b81eba68690f47eeeadc84f37272cdcc49",
    ),
    Repair(
        "11-24",
        REPAIRED_RULES,
        "the shipped capture is a blank frame; the caption promises a Running rule",
        expect_size=(1600, 903),
        digest="8681118a2136fcf8f257b3c04c8d61513807ad558d9b8866ba5e2c7832026611",
        notes="already cropped and redacted in the source commit; taken verbatim",
    ),
    Repair(
        "5-1",
        BASELINE,
        "the Location combo names an internal folder",
        redact=((0.335, 0.52, 0.86, 0.62),),
        digest="87a0bfcbe53c76a77f67221c5b79f1346ee106d2f409c36bd3a53bdf955ee180",
    ),
    Repair(
        "6-2",
        BASELINE,
        "the Location combo names an internal folder",
        # Measured on the capture: the Location label occupies rows 0.547-0.584
        # and the combo box text - the chevron and the folder name - rows
        # 0.644-0.696. The first attempt covered the label instead of the value.
        redact=((0.335, 0.633, 0.86, 0.706),),
        digest="11be401a3f2060542c336e774a5dc98f8a0558095342b3bdaa1ae2ca54603db8",
    ),
    Repair(
        "10-1",
        BASELINE,
        "licence banner, workspace title, owner column and stage badge",
        redact=(
            (0.0, 0.0, 1.0, 0.037),
            (0.055, 0.055, 0.35, 0.10),
            (0.27, 0.058, 0.345, 0.088),
            (0.495, 0.265, 0.565, 0.80),
            (0.055, 0.203, 0.180, 0.238),
            (0.0, 0.455, 0.042, 0.53),
        ),
        digest="ecb9a6803f55e4d564c9c53f39bf5d9db21b33b50c4ae8cf24ba175f5d624a92",
    ),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def carrier_path(root: Path) -> Path:
    return root / "tools" / "docs" / "assets" / "style-carrier.zip"


def read_from_commit(root: Path, commit: str, tag: str) -> bytes:
    blob = subprocess.run(
        ["git", "show", f"{commit}:tools/docs/assets/style-carrier.zip"],
        cwd=root,
        capture_output=True,
    ).stdout
    if not blob:
        raise SystemExit(f"cannot read the carrier from {commit}")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        return archive.read(f"screenshots/{tag}.png")


def apply(repair: Repair, original: bytes) -> bytes:
    image = Image.open(io.BytesIO(original)).convert("RGB")
    if repair.crop:
        if repair.expect_size and image.size != repair.expect_size:
            raise SystemExit(f"{repair.tag}: expected {repair.expect_size}, found {image.size}")
        image = image.crop(repair.crop)
    if repair.redact:
        width, height = image.size
        draw = ImageDraw.Draw(image)
        for left, top, right, bottom in repair.redact:
            draw.rectangle(
                (int(width * left), int(height * top), int(width * right), int(height * bottom)),
                fill=REDACTION,
            )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def repaired_bytes(root: Path, repair: Repair, current: dict[str, bytes]) -> bytes:
    name = f"screenshots/{repair.tag}.png"
    if repair.digest and hashlib.sha256(current.get(name, b"")).hexdigest() == repair.digest:
        return current[name]
    source = read_from_commit(root, repair.source, repair.tag) if repair.source else current[name]
    return apply(repair, source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail instead of writing")
    args = parser.parse_args()

    root = repo_root()
    carrier = carrier_path(root)
    with zipfile.ZipFile(carrier) as archive:
        entries = [(item, archive.read(item.filename)) for item in archive.infolist()]
    current = {name: data for (info, data) in entries for name in (info.filename,)}

    replacements: dict[str, bytes] = {}
    drift: list[str] = []
    for repair in REPAIRS:
        name = f"screenshots/{repair.tag}.png"
        if name not in current:
            drift.append(f"{repair.tag}: missing from the carrier")
            continue
        wanted = repaired_bytes(root, repair, current)
        digest = hashlib.sha256(wanted).hexdigest()
        if repair.digest and digest != repair.digest:
            drift.append(f"{repair.tag}: repaired to {digest[:12]}, pinned {repair.digest[:12]}")
        if current[name] != wanted:
            replacements[name] = wanted
            drift.append(f"{repair.tag}: carrier holds unrepaired bytes ({repair.reason})")
        print(f"{repair.tag}: {len(wanted):,} bytes  sha256 {digest}")

    if args.check:
        if drift:
            print("\ndrift:\n  " + "\n  ".join(drift))
            return 1
        print(f"\nall {len(REPAIRS)} repaired captures present and pinned")
        return 0

    if not replacements:
        print(f"\nall {len(REPAIRS)} captures already repaired; carrier untouched")
        return 0

    staging = carrier.with_suffix(".zip.new")
    with zipfile.ZipFile(staging, "w", zipfile.ZIP_DEFLATED) as archive:
        for info, data in entries:
            archive.writestr(info, replacements.get(info.filename, data))
    carrier.unlink()
    staging.rename(carrier)
    print(f"\nrewrote {carrier.name}: {len(replacements)} capture(s) repaired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
