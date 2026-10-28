"""Synthetic event-to-native-host integration for RENDER-WORLDS-C."""
from pathlib import Path
import subprocess
import unittest
import os
import json
import sys
import tempfile

NATIVE=Path(__file__).resolve().parents[1]

class IcarusHost(unittest.TestCase):
    def test_sky_and_object_events_reach_native_hooks(self):
        subprocess.run(['make','-s','-C',str(NATIVE),'build/icarus-host'],check=True,capture_output=True)
        subprocess.run([str(NATIVE/'build/icarus-host')],check=True,capture_output=True)

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private instruction captures are opt-in')
class IcarusInstructions(unittest.TestCase):
    def test_compiled_c_matches_client_and_mutants_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)/'icarus.json'
            subprocess.run([sys.executable,str(NATIVE.parent/'scripts/validate_icarus.py'),'--cases','1000','--mutations','--output',str(report)],check=True,capture_output=True)
            r=json.loads(report.read_text())
            self.assertTrue(all(t['cases']==t['equal'] and not t['stopped'] for t in r['families'].values()))
            self.assertTrue(all(m['caught'] for m in r['mutants']))
