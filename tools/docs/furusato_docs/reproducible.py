"""One fixed instant and one deterministic ZIP writer for every Office package.

Two builds of unchanged sources must produce byte-identical deliverables, so that
a reviewer can verify a published file simply by rebuilding it. Two things
otherwise defeat that:

* ``datetime.now()`` in the core properties, which changes every second; and
* ``zipfile.writestr(name, ...)`` with a plain string, which stamps each member
  with the machine's *local* time — so the same bytes differ between two runs,
  between two machines and across a daylight-saving boundary.

Both are removed here. The build instant is fixed by :data:`RELEASE_EPOCH` and can
be overridden with the reproducible-builds standard ``SOURCE_DATE_EPOCH``
environment variable; every archive member is written through
:func:`write_package` with that same instant, a fixed compression method and
fixed permissions.
"""

from __future__ import annotations

import os
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

#: The declared v2.7.0 release instant, in seconds since the Unix epoch
#: (2026-08-14T00:00:00Z). It is deliberately the same instant the Purview label
#: ``SetDate`` uses, so every timestamp in a delivered package tells one story.
RELEASE_EPOCH = 1786665600

#: Members that must stay at the head of the archive. Several OOXML readers, and
#: the ECMA-376 packaging conventions, expect the content-type map first.
_LEADING_MEMBERS = ("[Content_Types].xml",)

#: ``rw-r--r--`` for a regular file, as a ZIP external attribute.
_FILE_ATTRIBUTES = (0o100644 << 16)


def build_epoch() -> int:
    """The build instant, honouring ``SOURCE_DATE_EPOCH`` when it is usable."""
    raw = os.environ.get("SOURCE_DATE_EPOCH")
    if raw:
        try:
            value = int(raw.strip())
        except ValueError:
            return RELEASE_EPOCH
        # A ZIP timestamp cannot predate 1980; anything earlier would be silently
        # clamped by ``zipfile`` and would stop being reproducible.
        if value >= 315532800:
            return value
    return RELEASE_EPOCH


def build_datetime() -> datetime:
    return datetime.fromtimestamp(build_epoch(), tz=timezone.utc)


def build_timestamp() -> str:
    """The build instant as an OOXML ``dcterms:W3CDTF`` string."""
    return build_datetime().strftime("%Y-%m-%dT%H:%M:%SZ")


def zip_date_time() -> tuple[int, int, int, int, int, int]:
    """The build instant as the 6-tuple ``ZipInfo.date_time`` expects."""
    moment = build_datetime()
    return (moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second)


def member_order(names: list[str]) -> list[str]:
    """A stable member order: the content-type map first, then sorted."""
    leading = [name for name in _LEADING_MEMBERS if name in names]
    return leading + sorted(name for name in names if name not in leading)


def write_package(path: Path, parts: Mapping[str, bytes]) -> None:
    """Write ``parts`` to ``path`` as a reproducible ZIP package.

    Every member gets the fixed build instant, deflate compression and identical
    permissions, and the members are written in a stable order, so the resulting
    file depends only on the content.

    The archive is built beside the target and moved into place, so a failure part
    way through cannot leave a truncated deliverable behind, and the target is only
    held open for the instant of the move. Word and Excel release a document
    asynchronously when their COM server quits, so that move is retried briefly
    rather than failing the build on a lock that clears in a moment.
    """
    stamp = zip_date_time()
    staged = path.with_name(path.name + ".building")
    with zipfile.ZipFile(staged, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in member_order(list(parts)):
            info = zipfile.ZipInfo(name, date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0  # MS-DOS, so the host OS cannot leak in
            info.external_attr = _FILE_ATTRIBUTES
            archive.writestr(info, parts[name])
    _replace_when_unlocked(staged, path)


def _replace_when_unlocked(source: Path, target: Path, *, attempts: int = 20, delay: float = 0.5) -> None:
    for remaining in range(attempts - 1, -1, -1):
        try:
            os.replace(source, target)
            return
        except OSError:
            if not remaining:
                source.unlink(missing_ok=True)
                raise
            time.sleep(delay)


def save_atomically(save: Callable[[Path], None], target: Path) -> None:
    """Run ``save`` against a staging path, then move the result into place.

    ``python-docx`` and ``openpyxl`` both truncate the destination before they
    start writing, so a transient lock — an on-access virus scanner reading the
    file the build just produced, or an Office COM server that has not finished
    releasing it — fails the build and destroys the previous output. Writing
    beside the target and moving keeps the destination untouched until the new
    file is complete.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + ".building")
    save(staged)
    _replace_when_unlocked(staged, target)


def rewrite_package(path: Path) -> None:
    """Re-emit an existing package deterministically, leaving its content alone."""
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    write_package(path, parts)


#: A single fixed revision-save id. Word writes a fresh random one on every save
#: and scatters it across every paragraph and run; collapsing them to one value
#: costs nothing (they only hint at which editing session produced a run) and
#: removes the largest source of build-to-build noise.
_FIXED_RSID = "00A17E3C"

#: Sequential identifier bases. Word requires these to be unique and non-zero; it
#: does not require any particular value, so counting from a fixed base makes two
#: builds agree without changing how the document behaves.
_ID_BASE = 0x10000000
_DURABLE_BASE = 1000000001


def canonicalise_office_identifiers(path: Path) -> dict[str, int]:
    """Replace Office's per-save random identifiers with deterministic ones.

    Word assigns fresh random values to ``w14:paraId``, ``w14:textId``,
    ``w14:docId``, ``wp14:anchorId``, ``wp14:editId``, ``w16cid:durableId``, the
    ``w:rsid*`` table and the ``_Toc*`` bookmark names every time it saves, and
    Excel does the same for ``xr:uid``. None of them describe content — they are
    bookkeeping for revision merging, co-authoring and cross-references — but they
    make two builds of identical sources differ.

    Each family is renumbered in document order from a fixed base, so the values
    stay unique and well-formed while depending only on the content. ``_Toc``
    bookmarks are remapped globally because hyperlinks and ``PAGEREF`` fields
    reference them by name; renumbering them per-part would break the contents
    listing.
    """
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}

    xml_parts = [name for name in member_order(list(parts)) if name.endswith((".xml", ".rels"))]
    counters = {"id": 0, "durable": 0, "uid": 0}
    toc_map: dict[str, str] = {}
    changed = 0

    def next_id() -> str:
        counters["id"] += 1
        return f"{_ID_BASE + counters['id']:08X}"

    def next_durable() -> str:
        counters["durable"] += 1
        return str(_DURABLE_BASE + counters["durable"])

    def next_uid() -> str:
        counters["uid"] += 1
        return f"{{00000000-0000-0000-0000-{_ID_BASE + counters['uid']:012X}}}"

    # The contents listing is renumbered first and globally, so every reference to
    # a bookmark resolves to the same new name in every part.
    for name in xml_parts:
        for match in re.finditer(r"_Toc\d+", parts[name].decode("utf-8", "ignore")):
            toc_map.setdefault(match.group(0), f"_Toc{90000000 + len(toc_map)}")

    for name in xml_parts:
        text = parts[name].decode("utf-8")
        original = text
        if toc_map:
            text = re.sub(r"_Toc\d+", lambda m: toc_map.get(m.group(0), m.group(0)), text)
        text = re.sub(r'(w14:(?:paraId|textId)=")[0-9A-Fa-f]+(")', lambda m: m.group(1) + next_id() + m.group(2), text)
        text = re.sub(r'(wp14:(?:anchorId|editId)=")[0-9A-Fa-f]+(")', lambda m: m.group(1) + next_id() + m.group(2), text)
        text = re.sub(r'(w16cid:durableId=")\d+(")', lambda m: m.group(1) + next_durable() + m.group(2), text)
        text = re.sub(r'(xr:uid=")\{[0-9A-Fa-f-]+\}(")', lambda m: m.group(1) + next_uid() + m.group(2), text)
        text = re.sub(r'(w14:docId w14:val=")[0-9A-Fa-f]+(")', r"\g<1>" + _FIXED_RSID + r"\g<2>", text)
        text = re.sub(r'(w:rsid[A-Za-z]*=")[0-9A-Fa-f]+(")', r"\g<1>" + _FIXED_RSID + r"\g<2>", text)
        text = re.sub(
            r"<w:rsids>.*?</w:rsids>",
            f'<w:rsids><w:rsidRoot w:val="{_FIXED_RSID}"/><w:rsid w:val="{_FIXED_RSID}"/></w:rsids>',
            text,
            flags=re.DOTALL,
        )
        if text != original:
            parts[name] = text.encode("utf-8")
            changed += 1

    write_package(path, parts)
    return {
        "partsRewritten": changed,
        "identifiersRenumbered": counters["id"],
        "durableIdsRenumbered": counters["durable"],
        "bookmarksRenumbered": len(toc_map),
    }
