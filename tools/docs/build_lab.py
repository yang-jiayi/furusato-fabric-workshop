"""Build or validate the complete current participant Lab Markdown guide."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/docs"), str(ROOT / "tools/html")]

from furusato_docs.lab import load_model, validate_lab, write_lab


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="New Lab directory; never overwrites existing files")
    parser.add_argument("--receipt", required=True, type=Path, help="Separate source coverage JSON file")
    parser.add_argument("--artifact-manifest", type=Path, help="Verified manifest; omit to verify current source in memory")
    parser.add_argument("--check", action="store_true", help="Validate an existing Lab against its coverage receipt")
    args = parser.parse_args(argv)
    model = load_model(ROOT, args.artifact_manifest)
    if args.check:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    else:
        receipt = write_lab(ROOT, args.out, model=model)
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = validate_lab(ROOT, args.out, receipt, model=model)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
