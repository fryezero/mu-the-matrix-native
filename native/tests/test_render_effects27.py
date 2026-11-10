"""Death Stab's offline DK trails, refusal controls and original instruction checks."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'native/tests'))
from test_native_combat import write_combat_world
from test_native_particles import ozj_jpeg
import native_fixtures as nf

PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/mu-walk'], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(write_combat_world(Path(cls.tmp.name)/'game'))
        item = cls.root/'Data/Item'
        item.mkdir(exist_ok=True)
        (item/'Sword01.bmd').write_bytes(nf.synthetic_layout(200, actions=1, keys=(8,)))
        effect = cls.root/'Data/Effect'
        effect.mkdir(exist_ok=True)
        for name in ('NSkill.OZJ', 'Flare.OZJ'):
            (effect/name).write_bytes(ozj_jpeg(32, 32))
        cls.placement = Path(cls.tmp.name)/'actors.txt'
        cls.placement.write_text('actor 3 122 120 0 label DemoSpider\n')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def cast(self, cls=1, frames=48, weapon='sword'):
        with tempfile.TemporaryDirectory() as out:
            run = subprocess.run([str(ROOT/'native/build/mu-walk'), '--game-root', str(self.root),
                '--headless', '--backend', 'soft', '--no-audio', '--no-items', '--no-players',
                '--tile', '120,120', '--placement', str(self.placement), '--combat', '--combat-weapon', weapon,
                '--class', str(cls), '--combat-script', '2:skill:43:DemoSpider;3:stop', '--frames', str(frames),
                '--every', '1', '--width', '240', '--height', '160', '--out-dir', out],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr[-2000:])
            rows = [json.loads(s) for s in run.stdout.splitlines() if s.startswith('{')]
            images = [hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(out).glob('*.png'))]
        return rows, images

    def test_dk_trails_draw_and_leave_session_state_unchanged(self):
        rows, images = self.cast()
        combat = next(r for r in rows if r.get('combat') is True)
        stab = next(r for r in rows if r.get('death_stab') is True)
        self.assertEqual((combat['requests_sent'], combat['requests_unsent'], combat['hits'], combat['kills']), (0, 1, 0, 0))
        self.assertEqual((stab['steps'], stab['refused'], stab['context_refused'], combat['unsupported']), (12, 0, 0, 0))
        self.assertEqual(combat['fx_created'], 14)
        self.assertEqual(combat['joints_created'], 175)
        self.assertEqual(stab['requests'], 189)
        self.assertEqual(combat['sounds'], 1)
        frames = [r for r in rows if 'combat_frame' in r]
        self.assertTrue(any(r['joints'] > 0 for r in frames))
        self.assertTrue(any(0x10e6 in r['effect_types'] for r in frames))
        self.assertTrue(all(r['monsters'][0]['hp'] == frames[0]['monsters'][0]['hp'] for r in frames))
        self.assertEqual(frames[-1]['joints'], 0)
        self.assertEqual(frames[-1]['fx'], 0)
        _, repeat = self.cast()
        self.assertEqual(images, repeat)
        # Removing the two served trail textures must change the same DK render.
        paths = [self.root/'Data/Effect'/name for name in ('NSkill.OZJ', 'Flare.OZJ')]
        for p in paths: p.rename(p.with_suffix('.off'))
        try:
            _, absent = self.cast()
        finally:
            for p in paths: p.with_suffix('.off').rename(p)
        self.assertNotEqual(images, absent)

    def test_other_class_and_missing_weapon_context_are_refused(self):
        for cls, weapon in [(0, 'sword'), (0x11, 'sword'), (1, 'none')]:
            with self.subTest(cls=cls, weapon=weapon):
                rows, _ = self.cast(cls=cls, weapon=weapon)
                stab = next(r for r in rows if r.get('death_stab') is True)
                self.assertGreater(stab['context_refused'], 0)
                self.assertEqual(stab['requests'], 0)
                combat = next(r for r in rows if r.get('combat') is True)
                self.assertEqual((combat['joints_created'], combat['fx_created'], combat['requests_sent']), (0, 0, 0))


@unittest.skipUnless(PRIVATE, 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        for directory in ('reconstructed/combat', 'reconstructed/joints'):
            subprocess.run(['make', '-s', '-C', str(ROOT/directory)], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects27.py'), '--cases', '60',
                            '--output', str(out)], check=True, capture_output=True, cwd=ROOT)
            report = json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertEqual(report['cases'], 424)
