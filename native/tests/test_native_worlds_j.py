"""Authored posed lamps and primary emitter callbacks in the production host."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]

class WorldsJHost(unittest.TestCase):
    def test_poses_emitters_model_gates_and_explicit_refusals(self):
        subprocess.run(['make','-s','-C',str(NATIVE),'build/worlds-j-host'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            # Fifteen root bones, two keys, distinct translations and no meshes.
            chunks=[b'BMD\x0a',b'worlds-j'.ljust(32,b'\0'),struct.pack('<HHH',0,15,1),struct.pack('<hB',2,0)]
            for bone in range(15):
                chunks += [b'\0'+f'bone{bone}'.encode().ljust(32,b'\0')+struct.pack('<h',-1),
                           struct.pack('<6f',bone*10,2,3,bone*10+4,2,3),bytes(24)]
            model=Path(td)/'lamps.bmd';model.write_bytes(b''.join(chunks))
            subprocess.run([str(NATIVE/'build/worlds-j-host'),str(model)],check=True)
