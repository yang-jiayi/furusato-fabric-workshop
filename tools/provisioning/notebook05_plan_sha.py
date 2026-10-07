"""Compute Notebook05 PLAN_SHA256 offline from the notebook's own ``build_plan``.

No Spark, network or Fabric call. The hash covers ALLOW_AUTOMATED_APPLY and,
when it is true, EXPECTED_WORKSPACE_NAME: compute it with exactly the values
of the planned apply run. Compare it with the PLAN_SHA256 printed by the real
preview run before passing it as CONFIRMED_PLAN_SHA256; never skip the preview.
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path
from typing import Any

NOTEBOOK = (Path(__file__).resolve().parents[2] / "workshop" / "v3.0.0-preview" / "notebooks"
            / "Notebook_05_Furusato_Analytics_Quality_and_BI.ipynb")


def build_plan(
    participant_id: str, workspace_name: str, *, increment_path: str = "Files/increment",
    automated_apply: bool = True, notebook: Path = NOTEBOOK,
) -> dict[str, Any]:
    cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
    runtime = [
        "".join(cell["source"]) for cell in cells
        if cell.get("cell_type") == "code" and "def build_plan(" in "".join(cell["source"])
    ]
    if len(runtime) != 1:
        raise ValueError("Notebook05 must contain exactly one build_plan runtime cell.")
    name = "notebook05_runtime"
    module = types.ModuleType(name)
    sys.modules[name] = module  # dataclasses resolve annotations through sys.modules
    try:
        exec(compile(runtime[0], str(notebook), "exec"), module.__dict__)
        config = module.AnalyticsExtensionConfig(
            participant_id=participant_id, expected_workspace_name=workspace_name,
            increment_path=increment_path, apply_changes=False,
            allow_automated_apply=automated_apply, confirmed_plan_sha256="",
            exclusive_apply_window_confirmed=False, strict_synthetic_contract=True,
            operator_recover_interrupted_run=False, interrupted_run_id="",
        )
        return module.build_plan(config)
    finally:
        sys.modules.pop(name, None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--participant-id", required=True)
    parser.add_argument("--workspace-name", default="", help="Exact name; required for automated apply.")
    parser.add_argument("--increment-path", default="Files/increment")
    parser.add_argument("--manual-apply", action="store_true",
                        help="Plan for ALLOW_AUTOMATED_APPLY=False (portal-run apply).")
    args = parser.parse_args(argv)
    plan = build_plan(args.participant_id, args.workspace_name, increment_path=args.increment_path,
                      automated_apply=not args.manual_apply)
    print(json.dumps(plan["document"], ensure_ascii=False, indent=2))
    print(f"PLAN_SHA256={plan['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
