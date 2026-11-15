"""INNER-004 alpha reference through the actual scene driver and raster/GL backends."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_native_worlds_inner import synthetic_bmd
NATIVE=Path(__file__).resolve().parents[1]
@unittest.skipUnless(sys.platform=="darwin","macOS offscreen GL host")
class AlphaReference(unittest.TestCase):
    def test_greater_reference_and_restore_in_all_backends(self):
        subprocess.run(['make','-s','-j4','-C',str(NATIVE),'build/worlds-inner4-alpha-host'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'alpha.bmd';path.write_bytes(synthetic_bmd())
            r=subprocess.run([str(NATIVE/'build/worlds-inner4-alpha-host'),str(path)],capture_output=True,text=True)
            if r.returncode==3:self.skipTest(r.stderr)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertIn('15 scene cases',r.stdout)
if __name__=='__main__':unittest.main()
