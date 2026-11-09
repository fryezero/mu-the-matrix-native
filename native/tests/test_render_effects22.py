"""RENDER-EFFECTS-022: native mace particles and rank-5 world callers. Original checks use pinned captures."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
GAME = os.environ.get('MU_GAME_ROOT')


def build_host(tmp):
    """effects22_host.c against the native libraries."""
    native = ROOT/'native'
    subprocess.run(['make', '-s', '-C', str(native), 'build/libmunative.a', 'build/libmusession_world.a'],
                   check=True, capture_output=True)
    host, obj = Path(tmp)/'host', Path(tmp)/'host.o'
    command = ['clang', '-std=c11', '-O2', '-ffp-contract=off', '-I', str(native/'build/gen'), '-I', str(native/'session'),
               '-iquote', str(native/'core'), '-c', str(native/'tests/effects22_host.c'), '-o', str(obj)]
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


class Native(unittest.TestCase):
    def test_mace_argument_points_and_generations(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = build_host(tmp)
            p = subprocess.run([str(host)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('mace argument, points and generations OK', p.stdout)


@unittest.skipUnless(PRIVATE, 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        # The registry runs compiled mutants once. This private module checks the original without repeating them.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects22.py'), '--cases', '20',
                            '--output', str(out)], check=True, capture_output=True)
            report = json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertEqual(report['instruction_cases'], 202)


@unittest.skipUnless(PRIVATE and GAME, 'requires MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class World(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/mu-walk'], check=True, capture_output=True)

    def scene(self, text, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            players = Path(tmp)/'players.txt'
            players.write_text(text)
            r = subprocess.run([str(ROOT/'native/build/mu-walk'), '--game-root', GAME, '--headless', '--backend',
                                'soft', '--no-audio', '--width', '320', '--height', '240', '--every', '1000',
                                '--out-dir', tmp, '--tile', '128,124', '--frames', '61', '--quiet', '--players',
                                str(players), '--player-range', '20', *extra], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return [json.loads(s) for s in r.stdout.splitlines() if s.startswith('{')]

    def test_maces_create_the_counter_gated_particles(self):
        rows = self.scene('player Ember class=0x04 at=129,124 dir=3 pk=3 level=400 weapon0=2:57:9\n'
                          'player Glimmer class=0x01 at=127,125 dir=1 pk=3 level=400 weapon0=2:58:9\n',
                          '--every', '10')
        pre = next(r for r in rows if r.get('item_pre_draw'))['players']
        self.assertGreater(pre['pre_effects'], 0)
        self.assertEqual(pre['pre_refused'], 0)
        particles = next(r for r in rows if r.get('particles') is True)
        self.assertEqual(particles['unsupported'], 0)

    def test_rank5_runs_for_players(self):
        rows = self.scene('player Azure class=0x01 at=129,124 dir=3 pk=3 level=400 armor=8:320:9\n'
                          'player Bronze class=0x04 at=127,125 dir=1 pk=3 level=400 armor=8:319:9\n')
        owner = next(r for r in rows if r.get('item_owner_fx'))['players']
        self.assertGreater(owner['owner_effects'], 0)
        self.assertEqual(owner['owner_refused'], 0)

    def test_rank5_runs_for_the_hero(self):
        rows = self.scene('', '--hero-item', 'armor=Item/ArmorMale161_elf.bmd@8:320:9')
        owner = next(r for r in rows if r.get('item_owner_fx'))['hero']
        self.assertGreater(owner['owner_effects'], 0)
        self.assertEqual(owner['owner_refused'], 0)


if __name__ == '__main__':
    unittest.main()
