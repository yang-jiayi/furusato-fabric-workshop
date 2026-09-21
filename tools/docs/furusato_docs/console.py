"""Make the standard streams safe for Japanese output on any console.

These tools print Japanese chapter titles, table captions and validator messages.
On Windows the default console code page is cp932 or cp1252 depending on the
locale, and a redirected stream inherits the ANSI code page, so a plain
``print()`` of a Japanese string raises ``UnicodeEncodeError`` and the tool dies
with a traceback instead of reporting its result.

Callers should not have to set ``PYTHONIOENCODING`` by hand, so every entry point
calls :func:`use_utf8_streams` before it prints anything.
"""

from __future__ import annotations

import sys
from typing import IO


def use_utf8_streams() -> None:
    """Switch ``stdout``/``stderr`` to UTF-8, degrading rather than failing.

    ``errors="replace"`` is deliberate: a console that genuinely cannot render a
    glyph should show a replacement character, not abort a validation run that has
    already done its work.
    """
    for stream in (sys.stdout, sys.stderr):
        _reconfigure(stream)


def _reconfigure(stream: IO[str] | None) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        # A stream replaced by a plain object or a pipe wrapper: nothing to do,
        # and failing here would be worse than the encoding problem itself.
        return
    try:
        reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, OSError, AttributeError):
        return
