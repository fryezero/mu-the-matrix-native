"""Synthetic integration of class visuals with the production native host."""
from pathlib import Path
import subprocess
import unittest

NATIVE = Path(__file__).resolve().parents[1]


class WorldsHHost(unittest.TestCase):
    def test_hidden_emitters_and_model_gate_reach_native_hooks(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-h-host'], check=True)
        subprocess.run([str(NATIVE / 'build/worlds-h-host')], check=True, capture_output=True)
