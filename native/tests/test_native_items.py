"""Dropped items in the walk-around world (NATIVE-ITEMS-001) checks.

Portable (synthetic data only), through `mu-walk --items` (headless, software
rasterizer) on the synthetic combat world of test_native_combat.py with a
synthetic Item.bmd (zen, a sword, a jewel, a helm) and synthetic item models:
  * a scripted item viewport message creates the item 180 units above the
    terrain with gravity 20; it falls 6 slower per step and lands at the
    terrain + 30 (weapons + 70), with the spin until it lands and the resting
    pose of ItemAngle (weapons 60 degrees);
  * the name builder's label text and colour class (zen "%s %d", +levels);
  * the sparkle every 48 steps (two Shiny01 particles);
  * a click on the item walks the hero there and the demo server's answer
    removes it; the space bar takes the nearest item; Alt toggles the labels;
  * a monster killed in --combat drops a demo item; runs are deterministic.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): a Lorencia fight drops
items whose models and labels resolve from the installed Item.bmd.
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
from test_native_combat import write_combat_world  # noqa: E402
from test_native_data import item_file, item_record  # noqa: E402

WALK = NATIVE/'build/mu-walk'
PLACEMENT = NATIVE/'world/lorencia-demo-placement.txt'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def write_items_world(root):
    write_combat_world(root)
    local = Path(root)/'Data'/'Local'
    local.mkdir(parents=True, exist_ok=True)
    records = []
    for code, file, name in ((0x1c0f, b'Gold01.bmd', b'Zen'), (0x0001, b'Sword02.bmd', b'Short Sword'),
                             (0x1c0d, b'Jewel01.bmd', b'Jewel of Bless'), (0x0e05, b'HelmMale06.bmd', b'Leather Helm')):
        r = bytearray(item_record(code, b'Data\\Item\\', file, name))
        r[0x250] = r[0x251] = r[0x252] = 0
        records.append(bytes(r))
    (local/'item.bmd').write_bytes(item_file(records))
    item = Path(root)/'Data'/'Item'
    item.mkdir(parents=True, exist_ok=True)
    for i, file in enumerate(('Gold01.bmd', 'Sword02.bmd', 'Jewel01.bmd', 'HelmMale06.bmd')):
        (item/file).write_bytes(nf.synthetic_layout(20 + i, actions=1, keys=(1,)))
    return root


def run(root, *args, placement=None, check=True, tool=WALK):
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [str(tool), '--game-root', str(root), '--headless', '--backend', 'soft', '--no-audio', '--width', '64',
               '--height', '64', '--every', '1', '--out-dir', tmp, '--tile', '120,120', *[str(a) for a in args]]
        if placement:
            cmd += ['--placement', str(placement)]
        result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'frames': [r for r in rows if 'items_frame' in r],
            'summary': next((r for r in rows if r.get('items') is True), None),
            'combat': next((r for r in rows if r.get('combat') is True), None),
            'particles': next((r for r in rows if r.get('particles') is True), None), 'result': result}


@unittest.skipUnless(WALK.exists(), 'native/build/mu-walk not built')
class ItemsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_items_world(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_ground_player_folder_fallback_keeps_effect_textures(self):
        import io
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow is needed for authored glow textures')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(write_items_world(tmp))
            model = nf.write_textured_model(root/'Data/Player', 7)
            (root/'Data/Item/HelmMale10.bmd').write_bytes(model.read_bytes())
            record = bytearray(item_record(7*512+9, b'Data\\Item\\', b'HelmMale10.bmd', b'Demo helm'))
            record[0x250:0x253] = bytes(3)
            (root/'Data/Local/item.bmd').write_bytes(item_file([bytes(record)]))
            effect = root/'Data/Effect'
            effect.mkdir(exist_ok=True)
            for name in ('Chrome02', '2', 'flame_chrome', 'Chrome06', 'Chrome01', 'Shiny01'):
                jpeg = io.BytesIO()
                Image.new('RGB', (8,8), (40,80,120)).save(jpeg, format='JPEG')
                (effect/(name+'.ozj')).write_bytes(bytes(24)+jpeg.getvalue())
            probe = root/'probe.tga'
            probe.write_bytes(nf.tga(2,2,5))
            capability = subprocess.run([str(NATIVE/'build/mu-render'),'image',str(probe)],
                                        check=True,capture_output=True,text=True)
            if not json.loads(capability.stdout)['jpeg']:
                self.skipTest('native renderer was built without JPEG')
            result = run(root, '--items', '--frames', '4', '--item-script', '1:drop:3593:88:120,120')
            self.assertEqual(result['summary']['model_missing'], 0)
            self.assertEqual(result['summary']['effect_textures_loaded'], 6)

    def test_fall_land_pose_and_label(self):
        out = run(self.root, '--items', '--frames', '70', '--item-script', '2:drop:0x1c0f:0:122,120;3:drop:1:0x48:120,122')
        s = out['summary']
        self.assertEqual((s['drops'], s['creates'], s['no_record'], s['model_missing']), (2, 2, 0, 0))
        by_frame = {f['items_frame']: {i['slot']: i for i in f['list']} for f in out['frames']}
        floor = 40 * 1.5
        zen = [by_frame[f][0] for f in sorted(by_frame) if 0 in by_frame[f]]
        # created on the step of frame 2: z = floor + 180, then z += gravity (20, 14, 8, ...) until the floor + 30
        z, g, expected = f32(floor + 180.0), 20.0, []
        for _ in range(len(zen)):
            expected.append(z)
            z, g = f32(z + g), f32(g - 6.0)
            if z <= floor + 30.0:
                z = f32(floor + 30.0)
        self.assertEqual(zen[-1]['z'], round(floor + 30.0, 2))
        self.assertEqual(zen[-1]['name'], 'Zen 1234')
        self.assertEqual(zen[-1]['class'], 3)
        self.assertEqual(zen[-1]['angle'], [0.0, 0.0, -45.0])
        sword = by_frame[max(by_frame)][1]
        self.assertEqual((sword['z'], sword['angle'][0], sword['name'], sword['class']),
                         (round(floor + 70.0, 2), 60.0, 'Short Sword +9', 3))
        self.assertEqual(s['sparkles'], 2)                       # once each, 48 steps after creation
        self.assertEqual(out['particles']['created'], 4)        # two Shiny01 per sparkle
        self.assertGreater(s['labels'], 0)

    def test_pick_up_space_and_alt(self):
        out = run(self.root, '--items', '--frames', '140',
                  '--item-script', '2:drop:0x1c0f:0:124,121;3:drop:0x1c0d:0:123,122;30:pick:0;100:space;110:alt')
        s = out['summary']
        self.assertEqual(s['picks_done'], 2)
        self.assertEqual((s['space_picks'], s['alt_toggles'], s['view']), (1, 1, 0))
        self.assertEqual(s['live'], 0)
        self.assertTrue(any('walk to item 0' in line for line in s['log']))

    def test_combat_kill_drops(self):
        out = run(self.root, '--frames', '360', '--combat-script', '4:attack:spider', '--item-seed', '5',
                  placement=self.placement())
        self.assertGreaterEqual(out['combat']['kills'], 1)
        self.assertEqual(out['summary']['kills_seen'], 0)  # local kill observer was removed
        self.assertGreaterEqual(out['summary']['drops'], 1)
        again = run(self.root, '--frames', '360', '--combat-script', '4:attack:spider', '--item-seed', '5',
                    placement=self.placement())
        self.assertEqual(out['summary'], again['summary'])

    def placement(self):
        path = Path(self.tmp.name)/'placement.txt'
        path.write_text('# demo\nactor 3 122 120 6 label spider\n')
        return path


@unittest.skipUnless(PRIVATE and WALK.exists(), 'private installed data (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT)')
class PrivateItemsTest(unittest.TestCase):
    def test_lorencia_fight_drops(self):
        out = run(os.environ['MU_GAME_ROOT'], '--frames', '500', '--tile', '182,127', '--class', '1',
                  '--combat-weapon', 'sword', '--combat-script', '6:attack:hound', placement=PLACEMENT)
        s = out['summary']
        self.assertGreaterEqual(s['drops'], 1)
        self.assertEqual((s['no_record'], s['model_missing']), (0, 0))
        self.assertGreater(s['render_calls'], 0)
        self.assertGreater(out['combat']['monster_voices'], 0)


if __name__ == '__main__':
    unittest.main()
