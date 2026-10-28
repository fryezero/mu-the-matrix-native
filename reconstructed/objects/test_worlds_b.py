"""RENDER-WORLDS-B instruction comparison; private captures are explicitly opt-in."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class WorldsBTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("MU_RECOVERY_INTEGRATION") == "1", "private instruction captures required")
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix="worlds-b-test-") as directory:
            report = Path(directory) / "report.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/validate_worlds_b.py"),
                    "--cases",
                    "500",
                    "--mutations",
                    "--output",
                    str(report),
                ],
                check=True,
                capture_output=True,
            )
            result = json.loads(report.read_text())
            self.assertEqual(sum(r["cases"] for r in result["families"].values()), 4000)
            self.assertEqual(len(result["mutants"]), 10)
            self.assertTrue(all(m["detected"] > 0 and m["stopped"] == 0 for m in result["mutants"]))
