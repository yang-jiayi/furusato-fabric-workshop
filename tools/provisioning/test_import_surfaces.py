"""The resealer remains importable outside its command-line directory."""

import json
from pathlib import Path
import subprocess
import sys
import unittest


class ImportSurfacesTests(unittest.TestCase):
    def test_direct_file_import_resolves_the_resealers_sibling_modules(self):
        path = Path(__file__).resolve().with_name("reseal_runtime.py")
        script = (
            "import importlib.util,json,sys;"
            "spec=importlib.util.spec_from_file_location('isolated_resealer',sys.argv[1]);"
            "module=importlib.util.module_from_spec(spec);"
            "spec.loader.exec_module(module);"
            "print(json.dumps([module.VERSION,module.reference_assets.SCHEMA]))"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", script, str(path)],
            check=True, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(
            ["2.7.0", "furusato-ai-reference-runtime/v1"],
            json.loads(result.stdout),
        )


if __name__ == "__main__":
    unittest.main()
