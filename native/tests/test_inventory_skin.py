"""Authored textured skin sprites in software inventory and the real GFx icon FBO."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from test_native_hud import synthetic_root, run, TOOL
from native_fixtures import write_textured_model, synthetic_layout, tga

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
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp)/'probe.tga'
            probe.write_bytes(tga(2,2,5))
            result = subprocess.run([str(TOOL),'image',str(probe)],check=True,capture_output=True,text=True)
            if not json.loads(result.stdout)['jpeg']:
                raise unittest.SkipTest('native renderer built without JPEG support')

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


class GroundSkin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(NATIVE)],check=True,capture_output=True)

    def ground_sprites(self, backend):
        from test_native_items import write_items_world, run as ground_run
        from test_native_data import item_file, item_record
        tool = NATIVE/'build'/('mu-world' if backend == 'gl' else 'mu-walk')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(write_items_world(tmp))
            records = []
            for i in range(2):
                name = f'QuestItem3RD0{i}.bmd'
                (root/'Data/Item'/name).write_bytes(synthetic_layout(11, actions=0))
                record = bytearray(item_record(0x1c17+i, b'Data\\Item\\', name.encode(), b'Test Quest'))
                record[0x250:0x253] = bytes(3)
                records.append(bytes(record))
            (root/'Data/Local/item.bmd').write_bytes(item_file(records))
            # No weather, actors or item sparkles in this four-step scene.
            plain = ground_run(root, '--backend', backend, '--items', '--frames', '4', check=False, tool=tool)
            if plain['result'].returncode and backend == 'gl' and 'headless GL' in plain['result'].stderr:
                self.skipTest(plain['result'].stderr.strip())
            self.assertEqual(plain['result'].returncode, 0, plain['result'].stderr)
            self.assertEqual(plain['particles']['sprites_created'], 0)
            for code in (0x1c17, 0x1c18):
                with self.subTest(code=hex(code)):
                    drawn = ground_run(root, '--backend', backend, '--items', '--frames', '4',
                                       '--item-script', f'1:drop:{code}:8:120,120', tool=tool)
                    summary = drawn['summary']
                    self.assertEqual((summary['creates'], summary['no_record'], summary['model_missing']),
                                     (1, 0, 0))
                    self.assertEqual(summary['render_calls'], 3)
                    self.assertEqual(drawn['particles']['sprites_created'], summary['render_calls'])
                    self.assertEqual(drawn['particles']['rand_calls'], plain['particles']['rand_calls'])

    def test_ground_software_skin_sprites(self):
        self.ground_sprites('soft')

    @unittest.skipUnless(sys.platform=='darwin', 'offscreen GL host requires macOS')
    def test_ground_gl_skin_sprites(self):
        if not shutil.which('sdl2-config'):
            self.skipTest('mu-world requires SDL2')
        subprocess.run(['make','-s','-C',str(NATIVE),'world'],check=True,capture_output=True)
        self.ground_sprites('gl')
