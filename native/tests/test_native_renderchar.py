"""Native world-path character rendering (NATIVE-RENDERCHAR-001).

Portable (synthetic models only): `mu-render character --world-render` draws the
reconstructed world-render passes (item level glow, excellent, back carry);
renders are deterministic, the pass counts follow the reconstructed rules,
back carry changes the weapon placement, unknown item types fall back to one
plain pass, and malformed world options are refused. `mu-render actor` with
--actor-weapon is covered by the private test (needs installed monsters).
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): an installed Dark Knight
with item levels, +15 attachments and back carry, and a monster with its
class weapon, render with every texture found.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
from test_native_character import synthetic_set  # noqa: E402

TOOL = NATIVE/'build/mu-render'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
GAME_ROOT = os.environ.get('MU_GAME_ROOT', '')


def run(*args, check=True):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-render failed: {result.stderr}')
    return result


class WorldRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.directory = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls.directory.name)
        player, raws = synthetic_set(11)
        cls.player = cls.tmp/'player.bmd'
        cls.player.write_bytes(player)
        cls.paths = {}
        for index, raw in raws.items():
            cls.paths[index] = cls.tmp/f'item{index}.bmd'
            cls.paths[index].write_bytes(raw)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def render(self, *extra):
        args = ['character', self.player, '--world-render', '--no-textures', '--width', '160', '--height', '120',
                '--action', '1', '--frame', '0.5']
        for slot in (1, 2, 3):
            args += ['--part', str(slot), self.paths[slot]]
        args += ['--weapon', '0', self.paths[6], '--weapon', '1', self.paths[7]]
        args += ['--item-type', 'helm=0x18e6', '--item-type', 'armor=0x1ae6', '--item-type', 'pants=0x1ce6',
                 '--item-type', 'weapon0=0xae6', '--item-type', 'weapon1=0x10e6']
        out = self.tmp/'world.png'
        result = run(*args, *extra, '--out', out)
        return json.loads(result.stdout.strip().splitlines()[-1]), out.read_bytes()

    def test_deterministic_and_levels(self):
        base, png = self.render()
        again, png2 = self.render()
        self.assertEqual(base['sha256'], again['sha256'])
        self.assertEqual(png, png2)
        self.assertEqual(base['passes'], 5)                       # one textured body per item at level 0
        high, _ = self.render('--item-level', 'all=13', '--world-time', '500')
        self.assertEqual(high['passes'], 25)                      # 2, 0x240, 0x1040, 0x48, 0x44 per item
        self.assertNotEqual(high['sha256'], base['sha256'])
        capped, _ = self.render('--item-level', 'all=13', '--quality', '1')
        self.assertEqual(capped['passes'], 10)                    # level capped at 7: body + 0x44
        exc, _ = self.render('--excellent', 'weapon0=1', '--world-time', '300')
        self.assertEqual(exc['passes'], 6)

    def test_back_carry_and_fallback(self):
        base, _ = self.render()
        carried, _ = self.render('--safe-zone')
        self.assertEqual(carried['carried'], 2)
        self.assertNotEqual(carried['sha256'], base['sha256'])
        unknown, _ = self.render('--item-type', 'weapon1=0x100')
        self.assertEqual(unknown['special'], 1)

    def test_special_wing_uses_shared_body_renderer(self):
        info, _ = self.render('--item-type', 'weapon1=0x22ea', '--item-level', 'all=13', '--world-time', '700')
        self.assertEqual((info['special'], info['passes']), (0, 21))

    def test_native_link_saved_pose_and_capacity(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/item-render-host'], check=True, capture_output=True)
        result = subprocess.run([str(NATIVE/'build/item-render-host')], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout),
                         dict(created=13, random_calls=4, missing_bones_skipped=5, full=True))

    def test_refuses_malformed_options(self):
        for bad in (('--item-level', 'nine'), ('--item-level', 'sleeve=3'), ('--glow-color', '1,2'),
                    ('--actor-weapon', 'x')):
            result = run('character', self.player, *bad, '--out', self.tmp/'x.png', check=False)
            self.assertNotEqual(result.returncode, 0, bad)

    @unittest.skipUnless(PRIVATE and GAME_ROOT, 'installed client renders are opt-in')
    def test_private_installed_world_renders(self):
        # monster class 0 carries item 0x0cec (group 1, index 6: Axe07) in weapon slot 0
        root = Path(GAME_ROOT)
        result = run('character', '--game-root', root, '--class', '1', '--weapon', '0', root/'Data/Item/Sword01.bmd',
                     '--weapon', '1', root/'Data/Item/Shield01.bmd', '--world-render', '--item-level', 'all=15',
                     '--attachments', '--world-time', '900', '--out', self.tmp/'dk.png')
        info = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(info['attachments'], 9)
        self.assertEqual(info['special'], 0)
        result = run('character', '--game-root', root, '--class', '1', '--weapon', '0', root/'Data/Item/Sword01.bmd',
                     '--world-render', '--safe-zone', '--out', self.tmp/'carry.png')
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1])['carried'], 1)
        result = run('actor', '--game-root', root, '--type', '0', '--world-render', '--actor-weapon',
                     f"0={root/'Data/Item/Axe07.bmd'}", '--out', self.tmp/'monster.png')
        info = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual((info['weapons'], info['listed']), (1, 1))


if __name__ == '__main__':
    unittest.main()
