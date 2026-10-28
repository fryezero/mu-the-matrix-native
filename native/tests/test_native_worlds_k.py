"""Built-in world emitters run through production preparation and movement."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE=Path(__file__).resolve().parents[1]
class WorldsKHost(unittest.TestCase):
    def test_current_pose_model_guards_emitters_and_move_helper(self):
        subprocess.run(['make','-s','-C',str(NATIVE),'build/worlds-k-host'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            chunks=[b'BMD\x0a',b'worlds-k'.ljust(32,b'\0'),struct.pack('<HHH',0,4,1),struct.pack('<hB',2,0)]
            for k,name in enumerate(['light02','light01','Bone01','Bone02']):
                chunks += [b'\0'+name.encode().ljust(32,b'\0')+struct.pack('<h',-1),struct.pack('<6f',k*5,2,3,k*5+4,2,3),bytes(24)]
            model=Path(td)/'lamps.bmd';model.write_bytes(b''.join(chunks))
            subprocess.run([str(NATIVE/'build/worlds-k-host'),str(model)],check=True)
