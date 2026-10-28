"""Synthetic event-to-native-host integration for RENDER-WORLDS-C."""
from pathlib import Path
import subprocess
import unittest

NATIVE=Path(__file__).resolve().parents[1]

class IcarusHost(unittest.TestCase):
    def test_sky_and_object_events_reach_native_hooks(self):
        subprocess.run(['make','-s','-C',str(NATIVE),'build/icarus-host'],check=True,capture_output=True)
        subprocess.run([str(NATIVE/'build/icarus-host')],check=True,capture_output=True)
