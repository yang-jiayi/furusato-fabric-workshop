"""Optional Word COM post-processing: refresh fields, TOC and page-count metadata.

The step is best-effort. If Word is unavailable, busy or slow it is skipped and
the build still produces a valid document; the caller reports the limitation.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WordResult:
    ok: bool
    detail: str
    pages: int | None = None
    words: int | None = None


def refresh_with_word(path: Path, *, timeout_seconds: int = 240) -> WordResult:
    """Open the document in Word, update all fields and the TOC, then save.

    Returns a result object instead of raising so a missing Word installation
    never fails the deterministic build.
    """
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except Exception as error:  # pragma: no cover - depends on the host
        return WordResult(False, f"pywin32 unavailable ({error.__class__.__name__}); fields stay unresolved")

    pythoncom.CoInitialize()
    application = None
    try:
        application = win32com.client.DispatchEx("Word.Application")
        application.Visible = False
        application.DisplayAlerts = 0
        document = application.Documents.Open(
            str(path.resolve()), ConfirmConversions=False, ReadOnly=False, AddToRecentFiles=False
        )
        try:
            document.Fields.Update()
            for index in range(1, document.TablesOfContents.Count + 1):
                document.TablesOfContents(index).Update()
            document.Repaginate()
            pages = int(document.ComputeStatistics(2))  # wdStatisticPages
            words = int(document.ComputeStatistics(0))  # wdStatisticWords
            document.Save()
        finally:
            document.Close(SaveChanges=0)
        return WordResult(True, "fields, TOC and page statistics refreshed by Word", pages, words)
    except Exception as error:  # pragma: no cover - depends on the host
        return WordResult(False, f"Word automation failed: {error}")
    finally:
        if application is not None:
            with contextlib.suppress(Exception):
                application.Quit()
        with contextlib.suppress(Exception):
            pythoncom.CoUninitialize()
