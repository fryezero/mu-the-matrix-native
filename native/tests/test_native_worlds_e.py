"""RENDER-WORLDS-E authored host checks; no original client needed."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import native_fixtures as nf
from test_native_particles import ozj_jpeg

NATIVE = Path(__file__).resolve().parents[1]

class WorldsEHost(unittest.TestCase):
    def test_event_lifecycle_dispatch_and_elbeland_model_loading(self):
        subprocess.run(['make','-s','-C',str(NATIVE),'build/worlds-e-host'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root/'Data/Object52'
            folder.mkdir(parents=True)
            for n,name in enumerate(['sos3bi01','typhoonall']):
                nf.write_textured_model(folder,n+1).rename(folder/(name+'.bmd'))
            effect = root/'Data/Effect';effect.mkdir()
            (effect/'Map_Smoke1.OZJ').write_bytes(ozj_jpeg(16,16))
            subprocess.run([str(NATIVE/'build/worlds-e-host'),str(root)],check=True,capture_output=True)
