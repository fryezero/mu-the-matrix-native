"""RENDER-EFFECTS-002: session casts reach the fixed effect/particle pools and draw."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from test_native_combat import write_combat_world
from test_native_particles import ozj_jpeg
import native_fixtures as nf


class RenderEffects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT/'native'), 'build/mu-walk'], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.tmp.name)
        cls.root = write_combat_world(cls.directory/'game')
        skill = cls.root/'Data/Skill'; skill.mkdir(exist_ok=True)
        for i, name in enumerate(('Ice01.bmd', 'Ice02.bmd', 'Magic02.bmd')):
            (skill/name).write_bytes(nf.synthetic_layout(100+i, actions=1, keys=(8,)))
        effect = cls.root/'Data/Effect'; effect.mkdir(exist_ok=True)
        (effect/'smoke01.OZJ').write_bytes(ozj_jpeg(32, 32))
        cls.placement = cls.directory/'actors.txt'
        cls.placement.write_text('actor 3 122 120 0 label spider\n')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def cast(self, skill, particles=True):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [str(ROOT/'native/build/mu-walk'), '--game-root', str(self.root), '--headless',
                   '--backend', 'soft', '--no-audio', '--no-items', '--no-players', '--tile', '120,120',
                   '--placement', str(self.placement), '--combat', '--combat-weapon', 'staff', '--class', '0',
                   '--combat-script', f'2:skill:{skill}:spider;3:stop', '--frames', '36', '--every', '1',
                   '--width', '160', '--height', '100', '--out-dir', tmp]
            if not particles: cmd += ['--no-particles']
            p = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            rows = [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
            images = [hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(Path(tmp).glob('*.png'))]
        return rows, images

    def test_fixture_casts_create_draw_and_leave_unsent_damage_unchanged(self):
        for skill, types in [(1, []), (7, [0x412] + [0x41b]*5), (11, [0x41f])]:
            with self.subTest(skill=skill):
                rows, images = self.cast(skill)
                summary = next(r for r in rows if r.get('combat') is True)
                self.assertEqual(summary['requests_unsent'], 1)
                self.assertEqual((summary['hits'], summary['kills'], summary['unsupported']), (0, 0, 0))
                self.assertEqual(summary['models_loaded'], 3)
                frames = [r for r in rows if 'combat_frame' in r]
                self.assertTrue(any(sorted(f['effect_types']) == sorted(types) for f in frames[14:]))
                self.assertTrue(all(f['monsters'][0]['hp'] == frames[0]['monsters'][0]['hp'] for f in frames))
                self.assertEqual(summary['fx_created'], len(types))
                self.assertGreater(summary['particles_created'], 0)
                self.assertGreater(next(r['session_skills']['learned'] for r in rows if 'session_skills' in r), 0)
                # Render removal changes pixels: model loads/call counts alone cannot pass this assertion.
                if skill == 1:
                    _, absent = self.cast(skill, particles=False)
                else:
                    files = ['Ice01.bmd', 'Ice02.bmd'] if skill == 7 else ['Magic02.bmd']
                    for name in files: (self.root/'Data/Skill'/name).rename(self.root/'Data/Skill'/(name+'.off'))
                    try: _, absent = self.cast(skill)
                    finally:
                        for name in files: (self.root/'Data/Skill'/(name+'.off')).rename(self.root/'Data/Skill'/name)
                self.assertTrue(images)
                self.assertNotEqual(images, absent)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
    def test_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects.py'), '--cases', '60',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            r = json.loads(report.read_text())
            self.assertTrue(r['all_equal'])
            self.assertEqual(len(r['mutants']), 8)
            self.assertTrue(all(m['caught'] for m in r['mutants'].values()))
