"""Optional Excel COM post-processing: calculate the workbook and cache results.

openpyxl writes formulas without cached values, so any viewer that does not
recalculate (Explorer preview, OneDrive/SharePoint preview, most PDF exporters)
shows the summary cells as empty. Opening the workbook once in Excel and saving
it stores the cached values alongside the formulas.

The step stays deterministic: the cached values are a pure function of the
formulas and the cell values the build already wrote. It is best effort - when
Excel is unavailable the caller reports the limitation and ships the formula-only
workbook, which Excel still recalculates on open.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExcelResult:
    ok: bool
    detail: str
    sheets: int | None = None


def refresh_with_excel(path: Path) -> ExcelResult:
    """Open the workbook in Excel, recalculate every formula and save."""
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except Exception as error:  # pragma: no cover - depends on the host
        return ExcelResult(False, f"pywin32 unavailable ({error.__class__.__name__}); formulas stay uncached")

    pythoncom.CoInitialize()
    application = None
    try:
        application = win32com.client.DispatchEx("Excel.Application")
        application.Visible = False
        application.DisplayAlerts = False
        workbook = application.Workbooks.Open(str(path.resolve()))
        try:
            application.CalculateFullRebuild()
            sheets = int(workbook.Worksheets.Count)
            workbook.Save()
        finally:
            workbook.Close(SaveChanges=0)
        return ExcelResult(True, "formulas recalculated and cached by Excel", sheets)
    except Exception as error:  # pragma: no cover - depends on the host
        return ExcelResult(False, f"Excel automation failed: {error}")
    finally:
        if application is not None:
            with contextlib.suppress(Exception):
                application.Quit()
        with contextlib.suppress(Exception):
            pythoncom.CoUninitialize()
