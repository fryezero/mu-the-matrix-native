"""Authored textured skin sprites in software inventory and the real GFx icon FBO."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_native_hud import synthetic_root, run, TOOL
from native_fixtures import write_textured_model, synthetic_layout

NATIVE = Path(__file__).resolve().parents[1]


def skin_root(folder):
    root = synthetic_root(folder)
    path = write_textured_model(root/'Data/Item',seed=11)
    # Static geometry isolates the sprite clock from the cached model pose lifecycle.
    path.write_bytes(synthetic_layout(11, actions=0))
    path.rename(root/'Data/Item/QuestItem3RD00.bmd')
    return root


def add_spark(root):
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB',(32,32),(48,48,48)).save(buf,'JPEG')
    payload = buf.getvalue()
    effect = root/'Data/Effect'
    effect.mkdir(parents=True,exist_ok=True)
    (effect/'Spark03.OZJ').write_bytes(payload[:24]+payload)


class InventorySkin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import PIL.Image
        except ImportError:
            raise unittest.SkipTest('Pillow needed for authored JPEG')
        subprocess.run(['make','-s','-C',str(NATIVE)],check=True,capture_output=True)

    def test_software_inventory_sprite_pixels_and_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = skin_root(tmp)
            args = ('inventory','--root',root,'--items','7191:1','--size','1024x768')
            plain = run(*args,'--time','0')
            self.assertEqual((plain['models_drawn'],plain['models_missing']),(1,0))
            add_spark(root)
            start = run(*args,'--time','0')
            later = run(*args,'--time','500')
            self.assertNotEqual(start['framebuffer_sha256'],plain['framebuffer_sha256'])
            self.assertNotEqual(later['framebuffer_sha256'],start['framebuffer_sha256'])

    @unittest.skipUnless(sys.platform=='darwin','offscreen GL host requires macOS')
    def test_gfx_icon_sprite_pixels_clock_and_frame_isolation(self):
        subprocess.run(['make','-s','-C',str(NATIVE),'build/inventory-skin-host'],check=True,capture_output=True)
        host = NATIVE/'build/inventory-skin-host'
        with tempfile.TemporaryDirectory() as tmp:
            root = skin_root(tmp)
            def capture():
                result = subprocess.run([str(host),str(root)],capture_output=True,text=True)
                if result.returncode==3:
                    self.skipTest(result.stderr.strip())
                self.assertEqual(result.returncode,0,result.stderr)
                return json.loads(result.stdout)
            plain = capture()
            add_spark(root)
            drawn = capture()
            self.assertEqual((drawn['drawn'],drawn['missing'],drawn['icons']),(4,0,4))
            a,b,c,d = drawn['hashes']
            self.assertEqual((a,b),(b,d))
            self.assertNotEqual(a,plain['hashes'][0])
            self.assertNotEqual(a,c)
