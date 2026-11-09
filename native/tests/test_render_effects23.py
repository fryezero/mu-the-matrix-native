"""RENDER-EFFECTS-023: remaining mace consumers, textures and viewer owners. Original checks use pinned captures."""
import io
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
GAME = os.environ.get('MU_GAME_ROOT')


def build_host(tmp):
    """effects23_host.c against the native libraries."""
    native = ROOT/'native'
    subprocess.run(['make', '-s', '-C', str(native), 'build/libmunative.a', 'build/libmusession_world.a'],
                   check=True, capture_output=True)
    host, obj = Path(tmp)/'host', Path(tmp)/'host.o'
    command = ['clang', '-std=c11', '-O2', '-ffp-contract=off', '-I', str(native/'build/gen'), '-I', str(native/'session'),
               '-iquote', str(native/'core'), '-c', str(native/'tests/effects23_host.c'), '-o', str(obj)]
    p = subprocess.run(command, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr)
    command = ['clang++', str(obj), str(native/'build/libmunative.a'), str(native/'build/libmusession_world.a'), '-lm',
               '-o', str(host)]
    if sys.platform == 'darwin':
        command += ['-L/opt/homebrew/opt/cryptopp/lib', '-lcryptopp', '-L/opt/homebrew/opt/jpeg-turbo/lib', '-ljpeg',
                    '-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation']
    else:
        command += ['-lcryptopp', '-ljpeg']
    p = subprocess.run(command, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr)
    return host


FILES = ['flare03', 'flare01_red', 'smoke_line03_red', 'magic_ground12_red', 'firehik01', 'firehik02',
         'firehik03', 'Shockwave', 'Glow_26', 'smoke01_strong', 'pin_star02_red', 'smokelines01',
         'smokelines02', 'smokelines03']


class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.host = build_host(cls.tmp.name)
        subprocess.run(["make", "-s", "-C", str(ROOT/"native"), "build/mu-render"],
                       check=True, capture_output=True)
        cls.renderer = Path(cls.tmp.name)/'mu-render'
        shutil.copy2(ROOT/'native/build/mu-render', cls.renderer)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_host(self, *args):
        p = subprocess.run([str(self.host), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('mace consumers, bitmap files and point generations OK', p.stdout)
        return p.stdout

    def test_point_generations_without_assets(self):
        self.run_host()

    def test_character_item_object_registry(self):
        import re
        import native_fixtures as nf
        # Named-bone strings are authored metadata from the generated table, no private captures required.
        header = (ROOT/'reconstructed/renderchar/item_owner_fx.h').read_text()
        ops = [tuple(int(x.strip().rstrip('u'), 0) for x in row.split(',')) for row in
               re.findall(r'^    \{([^{}]+)\},', header.split('mu_rc_fx_ops[] = {')[1].split('};')[0], re.M)]
        rows = [tuple(int(x.strip(), 0) for x in row.split(',')) for row in
                re.findall(r'^    \{([^{}]+)\},', header.split('mu_rc_fx_pre_types[] = {')[1].split('};')[0], re.M)]
        row = next(row for row in rows if row[0] == 0x0f1f)
        names = re.findall(r'"([^"]+)"', header.split('mu_rc_fx_names[] = {')[1])
        needed = list(dict.fromkeys(names[op[-1]] for op in ops[row[1]:row[1]+row[2]] if op[0] == 16))
        player, item = Path(self.tmp.name)/'player.bmd', Path(self.tmp.name)/'mace.bmd'
        player.write_bytes(nf.character_layout(230, bones=64, actions=2, keys=(2, 2)))
        raw = nf.character_layout(231, bones=64, meshes=2)
        for i, name in enumerate(needed):
            raw = raw.replace(nf.name32(f'cbone{i}'), nf.name32(name), 1)
        item.write_bytes(raw)
        p = subprocess.run([str(self.renderer), 'character', str(player), '--weapon', '0', str(item),
                            '--world-render', '--no-textures', '--width', '160', '--height', '120', '--item-type',
                            'weapon0=0xf1f', '--frame-counter', '3', '--out', str(Path(self.tmp.name)/'viewer.png')],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(result['pre_refused'], 0)
        self.assertEqual(result['particles_created'], 1)


    def test_synthetic_bitmap_files_and_wrap(self):
        if 'jpeg=1' not in self.run_host():
            self.skipTest('native build has no JPEG decoder')
        root = Path(self.tmp.name)/'game'
        effect = root/'Data/Effect'
        effect.mkdir(parents=True, exist_ok=True)
        for i, name in enumerate(FILES + ['Snow_Chip02_red', 'Smoke_line', 'pin_star02', 'lighting_mega01',
                                         'lighting_mega02', 'lighting_mega03']):
            grey = 12 + (i % 14) * 16
            b = io.BytesIO()
            Image.new('RGB', (32, 32), (grey, grey, grey)).save(b, format='JPEG', quality=100)
            (effect/(name+'.OZJ')).write_bytes(bytes(24) + b.getvalue())
        self.run_host(root)


@unittest.skipUnless(PRIVATE, 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects23.py'), '--cases', '20',
                            '--output', str(out)], check=True, capture_output=True)
            report = json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertEqual(report['instruction_cases'], 1174)


@unittest.skipUnless(PRIVATE and GAME, 'requires MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class World(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/mu-walk', 'build/mu-render'],
                       check=True, capture_output=True)

    def test_mace_world_requests_are_consumed(self):
        import re
        header = (ROOT/'reconstructed/renderchar/item_owner_fx.h').read_text()
        table = header.split('mu_rc_fx_pre_types[] = {')[1].split('};')[0]
        admitted = {int(t, 0) for t in re.findall(r'^    \{([^,]+),', table, re.M)}
        self.assertTrue({0xf1f, 0xf20, 0xf24, 0xf28, 0xf29, 0xf2a, 0xf2b, 0xf2c} <= admitted)
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp)/'mu-walk'
            shutil.copy2(ROOT/'native/build/mu-walk', binary)
            players = Path(tmp)/'players.txt'
            players.write_text(''.join(f'player Demo{i} class=0x01 at={126+i%4},{123+i//4} dir=3 pk=3 '
                                       f'level=400 weapon0=2:{index}:9\n'
                                       for i, index in enumerate((57, 58, 62, 66, 67, 68, 69, 70))))
            p = subprocess.run([str(binary), '--game-root', GAME, '--headless', '--backend',
                                'soft', '--no-audio', '--width', '320', '--height', '240', '--every', '1',
                                '--out-dir', tmp, '--hero-name', 'DemoKnight', '--tile', '128,124', '--frames',
                                '61', '--quiet', '--players', str(players), '--player-range', '20'],
                               capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        rows = [json.loads(s) for s in p.stdout.splitlines() if s.startswith('{')]
        pre = next(r for r in rows if r.get('item_pre_draw'))['players']
        particles = next(r for r in rows if r.get('particles') is True)
        # Hammer14 has 'up01 ' (trailing space); its program requests exact 'up01'.
        # Keep that one bone-sprite refusal per draw rather than inventing a bone match.
        self.assertEqual(pre['pre_refused'], 61)
        self.assertGreater(pre['pre_effects'], 0)
        self.assertEqual(particles['unsupported'], 0)
        self.assertGreater(particles['drawn_particles'], 0)


if __name__ == '__main__':
    unittest.main()
