"""Portable native haze integration and opt-in original-instruction checks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

NATIVE=Path(__file__).resolve().parents[1]

class WorldsFHost(unittest.TestCase):
    def test_additive_pixels_and_unaffected_world_and_absent_textures(self):
        subprocess.run(['make','-s','-C',str(NATIVE),'build/world-haze-host'],check=True,capture_output=True)
        subprocess.run([str(NATIVE/'build/world-haze-host')],check=True,capture_output=True)

    def test_screen_pass_reaches_world_runtime_on_both_backends(self):
        from test_native_world import write_open_world
        from test_native_terrain import write_world
        from PIL import Image
        import io
        with tempfile.TemporaryDirectory() as tmp:
            root=write_open_world(Path(tmp)/'game')
            for folder in (9,58,59):write_world(root,folder,seed=3)
            jpeg=io.BytesIO();Image.new('RGB',(16,16),(100,100,100)).save(jpeg,format='JPEG',quality=100)
            for name in ('Object9/sand01.OZJ','Object9/sand02.OZJ','Effect/Map_Smoke1.OZJ'):
                p=root/'Data'/name;p.parent.mkdir(exist_ok=True);p.write_bytes(bytes(24)+jpeg.getvalue())
            for backend in ('soft','gl'):
                for world in (8,57,58):
                    out=Path(tmp)/f'{backend}-{world}'
                    result=subprocess.run([str(NATIVE/'build/mu-world'),'--game-root',str(root),'--world',str(world),
                        '--tile','128,128','--headless','--frames','1','--width','120','--height','80',
                        '--backend',backend,'--no-audio','--no-items','--no-names','--no-map','--out-dir',str(out)],capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertNotIn('world haze:',result.stderr)
                    im=Image.open(out/'frame-0000.png').convert('RGB')
                    # These source textures contribute a uniform positive amount
                    # even over the sky, through the real runtime's screen pass.
                    floor=(60,60,50) if world==8 else (80,80,90)
                    self.assertTrue(all(min(p[k] for p in im.getdata())>=floor[k]-2 for k in range(3)))

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private instruction captures are opt-in')
class WorldsFInstructions(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(NATIVE.parent/'scripts/validate_worlds_f.py'),'--cases','600',
                '--mutations','--output',str(out)],check=True,capture_output=True)
            r=json.loads(out.read_text())
            self.assertEqual(sum(t['cases'] for t in r['families'].values()),1818)
            self.assertTrue(all(t['equal']==t['cases'] and not t['stopped'] for t in r['families'].values()))
            self.assertTrue(all(m['caught'] and not m['stopped'] for m in r['mutants']))
