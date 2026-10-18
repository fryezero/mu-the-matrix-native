"""Native inventory and tooltip renders (NATIVE-HUD-001).

Portable: a synthetic game root authored here (Item.bmd, itemtrsdata.bmd,
itemtooltip.bmd, itemtooltiptext.bmd and a textured synthetic BMD model) is
rendered by `mu-render ui inventory|tooltip`: placement by the Item.bmd sizes,
the slot pass and RenderItem3D, the orthographic model pass and the
table-driven tooltip through the reconstructed formatter cases and HTML
assembly.  Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): the installed
tables and models.  Renders stay in temporary directories.
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from native_fixtures import write_textured_model
from test_native_data import KEY3, checksum, item_record, xor3

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent/'build/mu-render'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def run(*args):
    result = subprocess.run([str(TOOL), 'ui', *[str(a) for a in args]], capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def counted(records, codec):
    payload = b''.join(codec(r) for r in records)
    return struct.pack('<I', len(records)) + payload + struct.pack('<I', checksum(payload, 0xe2f1))


def synthetic_root(folder):
    root = Path(folder)
    (root/'Data/Local').mkdir(parents=True)
    (root/'Data/Item').mkdir(parents=True)
    model = write_textured_model(root/'Data/Item', seed=3)
    records = []
    for code, w, h, name, strength in ((0, 1, 2, b'Test Blade', 120), (513, 2, 2, b'Test Shield', 40),
                                       (7181, 1, 1, b'Test Jewel', 0)):
        r = bytearray(item_record(code, b'Data\\Item\\', model.name.encode(), name))
        r[0x25a], r[0x25b] = w, h
        r[0x266] = 25                                  # attack speed
        struct.pack_into('<H', r, 0x27c, strength)     # required strength
        records.append(bytes(r))
    (root/'Data/Local/item.bmd').write_bytes(counted(records, xor3))
    trs = [struct.pack('<I7f', code, 0.5, 0.6, 2000.0, 270.0, -10.0, 0.0, 0.003) for code in (0, 513)]
    (root/'Data/Local/itemtrsdata.bmd').write_bytes(counted(trs, xor3))
    texts = []
    for i, (text, kind) in enumerate([(b'Speed %d', 101), (b'Str %d', 6), (b'(need %d str)', 202), (b'Plain', -1)]):
        t = bytearray(260)
        struct.pack_into('<H', t, 0, i)
        t[2:2+len(text)] = text
        struct.pack_into('<h', t, 0x102, kind)
        texts.append(bytes(t))
    (root/'Data/Local/itemtooltiptext.bmd').write_bytes(
        counted(texts, lambda r: bytes(b ^ KEY3[k % 3] ^ 0xf1 for k, b in enumerate(r))))
    tips = []
    for code in (0, 513):
        t = bytearray(136)
        t[0], t[2:4], t[4:4+6] = code // 512, struct.pack('<h', code % 512), b'Tip%03d' % code
        t[0x44], t[0x48] = 3, 1                        # name colour yellow, show level
        struct.pack_into('<h', t, 0x4a, -1)            # name from Item.bmd
        for k in range(15):
            struct.pack_into('<hBB', t, 0x4c + 4*k, k if k < 4 else -1, 0, 0)
        tips.append(bytes(t))
    tips += [bytes(136)]*(11264 - len(tips))
    payload = b''.join(xor3(t) for t in tips)
    (root/'Data/Local/itemtooltip.bmd').write_bytes(payload + struct.pack('<I', checksum(payload, 0xe2f1)))
    return root


class NativeHudTests(unittest.TestCase):
    def test_synthetic_root_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = synthetic_root(folder)
            out = Path(folder)/'inv.png'
            a = run('inventory', '--root', root, '--items', '0:7,513:2,7181,0,99999', '--hover', '0', '--out', out)
            b = run('inventory', '--root', root, '--items', '0:7,513:2,7181,0,99999', '--hover', '0')
            self.assertTrue(out.exists())
            self.assertEqual(a['framebuffer_sha256'], b['framebuffer_sha256'])
            # 99999 has no Item.bmd record: placed with the default 1 x 2 cells, no model
            self.assertEqual((a['items_placed'], a['items_rejected'], a['slot_calls']), (5, 0, 5))
            self.assertEqual((a['models_drawn'], a['models_missing'], a['special']), (4, 1, 0))
            self.assertGreater(a['triangles'], 0)
            self.assertEqual(a['render_info'], 'itemtrsdata')
            # name, "Speed 25", "Str 120", "Plain": the default hero meets the requirement
            self.assertEqual(a['tooltip_lines'], 4)

    def test_synthetic_root_tooltip(self):
        with tempfile.TemporaryDirectory() as folder:
            root = synthetic_root(folder)
            html = Path(folder)/'tip.html'
            r = run('tooltip', '--root', root, '--item', '0:7', '--hero', '100,100,100,50', '--html-out', html,
                    '--size', '320x200')
            self.assertEqual((r['lines'], r['unsupported'], r['from_tables']), (5, 0, 1))
            text = html.read_text()
            self.assertEqual(text.count('<font'), 5)
            self.assertIn("<font color='#FFCC19'>Test Blade +7</font><br>", text)
            # the lacking line turns itself and the requirement line above red
            self.assertIn("<font color='#FF3319'>Str 120</font><br><font color='#FF3319'>(need 20 str)</font>", text)
            self.assertIn("<font color='#FFFFFF'>Speed 25</font>", text)

    def test_no_root(self):
        r = run('inventory', '--no-root', '--size', '1024x768')
        self.assertEqual((r['items_placed'], r['models_drawn'], r['render_info']), (12, 0, 'default'))
        t = run('tooltip', '--no-root', '--item', '12:5', '--size', '320x200')
        self.assertEqual((t['lines'], t['from_tables']), (4, 0))

    @unittest.skipUnless(PRIVATE, 'installed client data')
    def test_installed_inventory(self):
        r = run('inventory', '--hover', '0')
        self.assertEqual((r['items_placed'], r['models_missing'], r['render_info']), (12, 0, 'itemtrsdata'))
        self.assertGreater(r['tooltip_lines'], 2)


if __name__ == '__main__':
    unittest.main()
