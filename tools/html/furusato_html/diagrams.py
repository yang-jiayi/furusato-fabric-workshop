"""Bilingual diagram artwork.

The diagrams under ``docs/assets/v2.7.0`` are authored in Japanese. Some
labels already carry an English sibling line, but the bullets, decision
questions and boundary labels inside the artwork are Japanese only, so an
English reader switching the page to English still met a Japanese diagram.

This module derives an English variant of each diagram *at build time* from a
maintained translation map. The shipped SVG assets are never modified: they stay
the Japanese source of record and are embedded byte-fresh for Japanese readers.

Three structural facts about the artwork drive the implementation:

* Long labels are wrapped by hand across sibling ``<text>`` elements rather than
  with ``tspan``. A group of consecutive elements sharing an x coordinate and a
  font size, stepping down by roughly one line height, is one logical sentence.
  Translating those lines individually produces fragments such as ``を辿る。``,
  so groups are joined before translation and re-wrapped afterwards.
* Headings appear as a Japanese line immediately followed by a smaller English
  line. For those the English is already present, so the variant promotes it
  into the prominent slot and blanks the now-redundant second line.
* The Japanese line count is not an English capacity limit. Installed font
  metrics, the owning shape and neighbouring labels determine wrapping. Only
  small label backplates may grow; cards, relationship paths and markers stay put.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

JAPANESE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")
TEXT_ELEMENT = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)
MAP_PATH = Path(__file__).with_name("i18n") / "diagrams.json"

#: Japanese that may legitimately remain visible in the English artwork: proper
#: nouns and domain identifiers that the guide keeps in Japanese everywhere.
ALLOWED_JAPANESE = (
    "ふるさと納税",
    "宮崎県",
    "都城市",
    "東京都",
    "静岡県産",
    "温室メロン",
)


def _attr(attrs: str, name: str, default: float = 0.0) -> float:
    found = re.search(rf'{name}="([-\d.]+)"', attrs)
    return float(found.group(1)) if found else default


@dataclass
class Line:
    """One ``<text>`` element: where it sits and what it says."""

    start: int
    end: int
    attrs: str
    inner: str
    x: float
    y: float
    size: float

    @property
    def text(self) -> str:
        # Unescape on read so the round-trip through _retext is lossless: the
        # source markup already contains &amp;, and escaping it a second time
        # would render a literal "&amp;" in the artwork.
        stripped = re.sub(r"<[^>]+>", "", self.inner).strip()
        return (
            stripped.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        )


@dataclass
class Group:
    """One logical label: a single line, or several hand-wrapped lines."""

    lines: list[Line] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(line.text for line in self.lines)

    @property
    def needs_english(self) -> bool:
        return bool(JAPANESE.search(self.text))


def parse_lines(svg: str) -> list[Line]:
    lines: list[Line] = []
    for match in TEXT_ELEMENT.finditer(svg):
        attrs = match.group(1)
        lines.append(
            Line(
                start=match.start(),
                end=match.end(),
                attrs=attrs,
                inner=match.group(2),
                x=_attr(attrs, "x"),
                y=_attr(attrs, "y"),
                size=_attr(attrs, "font-size", 12.0),
            )
        )
    return lines


def group_lines(lines: list[Line]) -> list[Group]:
    """Fold hand-wrapped continuation lines into one group."""
    groups: list[Group] = []
    index = 0
    while index < len(lines):
        group = Group([lines[index]])
        cursor = index + 1
        while cursor < len(lines):
            previous, candidate = lines[cursor - 1], lines[cursor]
            same_column = abs(candidate.x - group.lines[0].x) < 0.6
            same_size = abs(candidate.size - group.lines[0].size) < 0.1
            step = candidate.y - previous.y
            # A hand-wrapped continuation is the same sentence, so it is the same
            # script. A Japanese line followed by a Latin one is the author's
            # bilingual heading pair, which english_sibling handles instead.
            same_script = bool(JAPANESE.search(previous.text)) == bool(
                JAPANESE.search(candidate.text)
            )
            if same_column and same_size and same_script and 0 < step <= group.lines[0].size * 1.9:
                group.lines.append(candidate)
                cursor += 1
                continue
            break
        groups.append(group)
        index = cursor
    return groups


def english_sibling(groups: list[Group], position: int) -> Group | None:
    """The English line that already follows a Japanese heading, if any.

    Headings are authored as a Japanese line and a smaller English line a few
    pixels below. Detecting that pair means the variant can reuse the author's
    own English instead of inventing a second translation.
    """
    if position + 1 >= len(groups):
        return None
    current, following = groups[position], groups[position + 1]
    if len(current.lines) != 1 or len(following.lines) != 1:
        return None
    head, tail = current.lines[0], following.lines[0]
    if JAPANESE.search(tail.text) or not tail.text:
        return None
    # Require a phrase, not a bare token: "Star schema" and "JOIN implementation"
    # are author-supplied translations, whereas "SQL" or "Lakehouse" is a label in
    # its own right that must survive in both languages.
    if " " not in tail.text or len(tail.text) < 8:
        return None
    # A translation sits *under* its Japanese line in smaller or equal type. A
    # larger following line is the next item's heading -- as with the boundary
    # list, where a Japanese description is followed by "Donor - Supplier".
    if tail.size > head.size + 0.05:
        return None
    if abs(tail.x - head.x) > 0.6:
        return None
    if not 0 < tail.y - head.y <= head.size * 2.4:
        return None
    return following


@lru_cache(maxsize=2)
def _font(bold: bool = False) -> ImageFont.FreeTypeFont:
    """Use the artwork's installed typeface, not a characters-per-line guess.

    Yu Gothic UI Regular is face 1 of *YuGothM*, not YuGothR (Semilight).
    Measuring at a large size avoids integer-size rounding in the SVG's small
    labels. Pillow is already a build dependency; Chromium remains test-only.
    """
    candidates = (
        ("YuGothB.ttc" if bold else "YuGothM.ttc", 1),
        ("meiryob.ttc" if bold else "meiryo.ttc", 0),
        ("segoeuib.ttf" if bold else "segoeui.ttf", 0),
        ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", 0),
        ("Arial Bold.ttf" if bold else "Arial.ttf", 0),
    )
    for name, index in candidates:
        try:
            return ImageFont.truetype(name, 1000, index=index)
        except OSError:
            continue
    raise RuntimeError("Diagram layout needs an installed Yu Gothic UI, Meiryo, Segoe UI, DejaVu Sans or Arial font.")


def _bold(line: Line) -> bool:
    return bool(re.search(r'font-weight="(?:bold|[6-9]00)"', line.attrs))


def _width(text: str, size: float, bold: bool = False) -> float:
    """Font advance plus a small allowance for browser/FreeType rounding."""
    return _font(bold).getlength(text) * size / 1000 + 0.75


def wrap_to(text: str, size: float, budget: float, lines: int = 1, *, bold: bool = False) -> list[str]:
    """Wrap whole words; ``lines`` is a minimum, never an overflow-producing cap."""
    words = text.split(" ")
    out: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and _width(candidate, size, bold) > budget:
            out.append(current)
            current = word
        else:
            current = candidate
    out.append(current)
    while len(out) < lines:
        out.append("")
    return out


@dataclass
class _Shape:
    start: int
    end: int
    tag: str
    attrs: str
    x: float
    y: float
    width: float
    height: float

    @property
    def backplate(self) -> bool:
        # Connector masks and small count/status badges can gain label height.
        # Filled header strips (rx=0) and the actual entity cards cannot.
        return (self.tag == "rect" and self.height <= 40 and self.width >= 30
                and _attr(self.attrs, "rx") > 0)


def _shapes(svg: str) -> list[_Shape]:
    result = []
    for match in re.finditer(r"<(rect|circle|polygon)\b([^>]*)/?>", svg):
        tag, attrs = match.group(1), match.group(2)
        if 'fill="none"' in attrs:
            continue
        if tag == "circle":
            radius = _attr(attrs, "r")
            x, y = _attr(attrs, "cx") - radius, _attr(attrs, "cy") - radius
            width = height = radius * 2
        elif tag == "polygon":
            points = re.search(r'points="([^"]+)"', attrs)
            if not points:
                continue
            numbers = [float(n) for n in re.findall(r"[-\d.]+", points.group(1))]
            xs, ys = numbers[::2], numbers[1::2]
            x, y, width, height = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
        else:
            x, y, width, height = (_attr(attrs, a) for a in ("x", "y", "width", "height"))
        result.append(_Shape(match.start(), match.end(), tag, attrs, x, y, width, height))
    return result


def _owner(line: Line, shapes: list[_Shape]) -> _Shape | None:
    candidates = [
        shape for shape in shapes
        if shape.start < line.start
        and shape.x <= line.x <= shape.x + shape.width
        and shape.y <= line.y - line.size * 1.08 + 2
        and shape.y + shape.height >= line.y + line.size * .25 - 2
    ]
    return min(candidates, key=lambda s: s.width * s.height, default=None)


def _set_attr(attrs: str, name: str, value: str) -> str:
    if re.search(rf'\b{name}="[^"]*"', attrs):
        return re.sub(rf'\b{name}="[^"]*"', lambda _: f'{name}="{value}"', attrs)
    return attrs + f' {name}="{value}"'


def _layout(
    group: Group,
    english: str,
    shape: _Shape,
    neighbours: list[Line],
    shapes: list[_Shape],
) -> list[tuple[str, float, float]]:
    """Use available whitespace before considering a local type-size reduction."""
    head = group.lines[0]
    centred = 'text-anchor="middle"' in head.attrs
    padding = 4 if shape.backplate else min(12, max(4, head.x - shape.x))
    left = shape.x + padding
    right = shape.x + shape.width - padding
    if not centred:
        left = head.x
    if shape.x == 0 and head.size >= 20:
        # The heading must not run under the version badge, even if wrapping
        # would put part of the sentence vertically below it.
        for badge in shapes:
            if badge.backplate and badge.x > head.x and badge.y < head.y < badge.y + badge.height + 10:
                right = min(right, badge.x - 16)
    text_width = min(_width(english, head.size, _bold(head)), right - left)
    scan_left = head.x - text_width / 2 if centred else left
    scan_right = head.x + text_width / 2 if centred else left + text_width

    top, bottom = shape.y + 3, shape.y + shape.height - 4
    if not shape.backplate:
        for other in neighbours:
            if other in group.lines or not other.text:
                continue
            if shape.tag == "polygon" and other.text.isdigit():
                continue
            other_width = _width(other.text, other.size, _bold(other))
            other_left = other.x - (other_width / 2 if 'text-anchor="middle"' in other.attrs else 0)
            if other_left >= scan_right or other_left + other_width <= scan_left:
                continue
            if other.y > group.lines[-1].y + 1:
                bottom = min(bottom, other.y - other.size * 1.08 - 3)
            elif other.y < head.y - 1:
                top = max(top, other.y + other.size * .25 + 3)
        for child in shapes:
            if (child is not shape and child.width > 40 and child.height > 40
                    and child.x < right and child.x + child.width > left
                    and child.y > group.lines[-1].y + 1):
                bottom = min(bottom, child.y - 4)

    for scale in (1.0, .98, .96, .94, .92, .90, .88, .86, .84, .82, .80, .78):
        size = round(head.size * scale, 2)
        budget = 2 * min(head.x - left, right - head.x) if centred else right - left
        # A diamond narrows above and below its centre. Its numbered badge also
        # occupies the left half; keep the author's question anchor unchanged.
        if shape.tag == "polygon":
            centre_y = shape.y + shape.height / 2
            distance = abs(head.y - size * .4 - centre_y) + size * .7
            half_width = shape.width / 2 * max(0, 1 - distance / (shape.height / 2))
            centre_x = shape.x + shape.width / 2
            budget = min(budget, 2 * (half_width - abs(head.x - centre_x) - 4))
        pieces = wrap_to(english, size, budget, bold=_bold(head))
        if ((shape.backplate or (head.size >= 20 and len(group.lines) == 1)) and len(pieces) > 1
                and _width(english, head.size * .90, _bold(head)) <= budget):
            continue  # Avoid growing a mask or orphaning one word in a heading.
        if any(_width(piece, size, _bold(head)) > budget for piece in pieces):
            continue  # Never split or hyphenate a technical identifier.
        step = max(size * 1.5, 15 if head.size >= 10 else size * 1.5)
        height = size * 1.33 + (len(pieces) - 1) * step
        if shape.backplate or height <= bottom - top:
            y = head.y if shape.backplate else max(top + size * 1.08, min(head.y, bottom - size * .25 - (len(pieces) - 1) * step))
            if shape.tag == "polygon":
                fits = True
                for index, piece in enumerate(pieces):
                    baseline = y + index * step
                    distance = max(abs(baseline - size * 1.08 - centre_y),
                                   abs(baseline + size * .25 - centre_y))
                    half_width = shape.width / 2 * (1 - distance / (shape.height / 2))
                    if _width(piece, size, _bold(head)) > 2 * (half_width - abs(head.x - centre_x) - 4):
                        fits = False
                        break
                if not fits:
                    continue
            return [(piece, size, y + index * step) for index, piece in enumerate(pieces)]
    raise ValueError(f"English diagram label has no readable layout inside its shape: {english!r}")


def _expand_bullet_rows(
    groups: list[Group], produced: dict[int, str], shapes: list[_Shape],
    owners: dict[int, _Shape | None],
) -> list[tuple[int, int, str]]:
    """Keep circular bullets aligned when a translated list gains a line."""
    changes = []
    columns: dict[tuple[int, float], list[tuple[Group, str, _Shape]]] = {}
    for position, english in produced.items():
        group = groups[position]
        head = group.lines[0]
        owner = owners[head.start]
        if owner is None or owner.backplate:
            continue
        bullet = next((
            s for s in shapes if s.tag == "circle" and s.width <= 10
            and abs(head.x - (s.x + s.width / 2) - 12) < 1
            and abs(head.y - (s.y + s.height / 2) - 4) < 1
        ), None)
        if bullet:
            columns.setdefault((owner.start, head.x), []).append((group, english, bullet))
    for column in columns.values():
        offset = 0.0
        for group, english, bullet in sorted(column, key=lambda item: item[0].lines[0].y):
            head = group.lines[0]
            owner = owners[head.start]
            assert owner is not None
            count = len(wrap_to(english, head.size, owner.x + owner.width - head.x - 12, bold=_bold(head)))
            if offset:
                for line in group.lines:
                    line.y += offset
                attrs = _set_attr(bullet.attrs, "cy", f"{bullet.y + bullet.height / 2 + offset:.2f}")
                changes.append((bullet.start, bullet.end, f"<circle{attrs}>"))
                bullet.y += offset
            offset += max(0, count - len(group.lines)) * head.size * 1.5
    return changes


def load_map() -> dict[str, str]:
    if not MAP_PATH.is_file():
        return {}
    return json.loads(MAP_PATH.read_text(encoding="utf-8"))


def _normalize(value: str) -> str:
    """Loose comparison key for detecting a duplicated label."""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def units(svg: str) -> list[str]:
    """Every Japanese label in one diagram, as translation units."""
    groups = group_lines(parse_lines(svg))
    return [group.text for group in groups if group.needs_english]


def seed_from_siblings(svg: str) -> dict[str, str]:
    """English the diagram author already supplied, keyed by its Japanese line.

    Headings are drawn as a Japanese line with an English line beside it. Reusing
    that text keeps the English artwork in the author's own words and means the
    translation map does not have to restate it.
    """
    groups = group_lines(parse_lines(svg))
    seeded: dict[str, str] = {}
    for position, group in enumerate(groups):
        if not group.needs_english or position + 1 >= len(groups):
            continue
        following = groups[position + 1]
        if following.needs_english or not following.text:
            continue
        if len(group.lines) != 1 or len(following.lines) != 1:
            continue
        head, tail = group.lines[0], following.lines[0]
        if " " not in tail.text or len(tail.text) < 8:
            continue
        if abs(tail.x - head.x) > 0.6:
            continue
        if not 0 < tail.y - head.y <= head.size * 2.4:
            continue
        seeded[group.text] = tail.text
    return seeded


def to_english(svg: str, mapping: dict[str, str], strict: bool = True) -> tuple[str, list[str]]:
    """Render the English variant of one diagram.

    Returns the rewritten SVG and the list of Japanese units that had no English
    entry, so the caller can fail the build rather than ship a half-translated
    picture.
    """
    groups = group_lines(parse_lines(svg))
    replacements: list[tuple[int, int, str]] = []
    missing: list[str] = []
    produced: dict[int, str] = {}

    for position, group in enumerate(groups):
        if not group.needs_english:
            continue

        english = mapping.get(group.text)
        if not english:
            missing.append(group.text)
            continue
        produced[position] = english

    # Where the author already drew the English beside the Japanese, translating
    # the Japanese leaves the same sentence twice. Comparing the text that was
    # actually produced is more reliable than guessing from position and type
    # size: one diagram sets the translation smaller than its Japanese heading,
    # another sets it larger, and a third follows a description with the next
    # item's heading, which only looks like a translation.
    redundant: set[int] = set()
    for position, english in produced.items():
        following = position + 1
        if following >= len(groups):
            continue
        neighbour = groups[following]
        if neighbour.needs_english or not neighbour.text:
            continue
        if _normalize(neighbour.text) != _normalize(english):
            continue
        for line in neighbour.lines:
            redundant.add(line.start)

    if missing and strict:
        return svg, missing

    shapes = _shapes(svg)
    lines = [line for group in groups for line in group.lines]
    neighbours = [line for line in lines if line.start not in redundant]
    owners = {line.start: _owner(line, shapes) for line in lines}
    replacements.extend(_expand_bullet_rows(groups, produced, shapes, owners))
    laid_out: dict[int, list[tuple[str, float, float]]] = {start: [] for start in redundant}
    for position, english in produced.items():
        group = groups[position]
        head = group.lines[0]
        owner = owners[head.start]
        if owner is None:
            # Small synthetic SVGs without a viewBox or shapes still support
            # lossless translation; workshop artwork always has an owner.
            laid_out[head.start] = [(english, head.size, head.y)]
        else:
            laid_out[head.start] = _layout(group, english, owner, neighbours, shapes)
        for line in group.lines[1:]:
            laid_out[line.start] = []

    arrow_tips = []
    for match in re.finditer(r"<(line|path)\b([^>]*)>", svg):
        attrs = match.group(2)
        if 'marker-end="' not in attrs:
            continue
        if match.group(1) == "line":
            arrow_tips.append((_attr(attrs, "x2"), _attr(attrs, "y2")))
        else:
            path = re.search(r'\bd="([^"]+)"', attrs)
            if path:
                coordinates = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path.group(1))]
                arrow_tips.append(tuple(coordinates[-2:]))

    for shape in shapes:
        if not shape.backplate:
            continue
        members = [line for line in lines if owners[line.start] is shape]
        if not any(len(laid_out.get(line.start, [])) > 1 for line in members):
            continue
        rows = [
            row for line in members
            for row in laid_out.get(line.start, [(line.text, line.size, line.y)])
            if row[0]
        ]
        low = min(y - size * 1.08 for _, size, y in rows)
        high = max(y + size * .25 for _, size, y in rows)
        offset = shape.y + shape.height / 2 - (low + high) / 2
        for x, y in arrow_tips:
            if shape.x - 10 < x < shape.x + shape.width + 10:
                # A taller transition label must not paint over the arrowhead
                # immediately underneath it. The connector itself never moves.
                if shape.y + shape.height <= y and high + offset + 3 > y - 8:
                    offset = y - 8 - high - 3
        for other in lines:
            if other in members:
                continue
            for text, size, y in laid_out.get(other.start, [(other.text, other.size, other.y)]):
                if not text:
                    continue
                width = _width(text, size, _bold(other))
                left = other.x - (width / 2 if 'text-anchor="middle"' in other.attrs else 0)
                if left >= shape.x + shape.width or left + width <= shape.x:
                    continue
                top = y - size * 1.08
                if top >= shape.y + shape.height - 2 and high + offset + 3 > top - 3:
                    offset = top - 6 - high
        for line in members:
            laid_out[line.start] = [
                (text, size, y + offset)
                for text, size, y in laid_out.get(line.start, [(line.text, line.size, line.y)])
            ]
        attrs = _set_attr(shape.attrs, "y", f"{low + offset - 3:.2f}")
        attrs = _set_attr(attrs, "height", f"{high - low + 6:.2f}")
        replacements.append((shape.start, shape.end, f"<rect{attrs}>"))

    for line in lines:
        if line.start in laid_out:
            replacements.append((line.start, line.end, _retext(line, laid_out[line.start])))

    out = svg
    for start, end, payload in sorted(replacements, key=lambda item: item[0], reverse=True):
        out = out[:start] + payload + out[end:]
    return out, missing


def _retext(line: Line, rows: list[tuple[str, float, float]]) -> str:
    """Keep one source text element per line, with explicit wrapped baselines."""
    def escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    attrs = line.attrs
    if not rows:
        return f"<text{attrs}></text>"
    attrs = _set_attr(attrs, "font-size", f"{rows[0][1]:g}")
    family = ", ".join(dict.fromkeys((
        _font(_bold(line)).getname()[0], "Yu Gothic UI", "Meiryo", "Segoe UI", "sans-serif",
    )))
    attrs = _set_attr(attrs, "font-family", family)
    attrs = _set_attr(attrs, "y", f"{rows[0][2]:.2f}")
    if len(rows) == 1:
        return f"<text{attrs}>{escape(rows[0][0])}</text>"
    content = "\n".join(
        f'<tspan x="{line.x:g}" y="{y:.2f}">{escape(text)}</tspan>'
        for text, _, y in rows
    )
    return f"<text{attrs}>{content}</text>"


def residual_japanese(svg: str) -> list[str]:
    """Japanese still visible in an English variant, ignoring allowed proper nouns."""
    found: list[str] = []
    for line in parse_lines(svg):
        text = line.text
        if not text or not JAPANESE.search(text):
            continue
        stripped = text
        for allowed in ALLOWED_JAPANESE:
            stripped = stripped.replace(allowed, "")
        if JAPANESE.search(stripped):
            found.append(text)
    return found
