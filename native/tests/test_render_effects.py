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

    def cast(self, skill, particles=True, frames=36):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [str(ROOT/'native/build/mu-walk'), '--game-root', str(self.root), '--headless',
                   '--backend', 'soft', '--no-audio', '--no-items', '--no-players', '--tile', '120,120',
                   '--placement', str(self.placement), '--combat', '--combat-weapon', 'staff', '--class', '0',
                   '--combat-script', f'2:skill:{skill}:spider;3:stop', '--frames', str(frames), '--every', '1',
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

    def test_meteorite_and_inferno_session_pixels(self):
        assets = self.root/'Data/Skill'
        names = ('Fire01.bmd', 'Stone01.bmd', 'Stone02.bmd', 'Inferno01.bmd')
        for i, name in enumerate(names):
            (assets/name).write_bytes(nf.synthetic_layout(200+i, actions=1, keys=(8,)))
        effect = self.root/'Data/Effect'
        for name in ('Spark02.OZJ', 'Explotion01.OZJ', 'Fire01.OZJ'):
            (effect/name).write_bytes(ozj_jpeg(32, 32))
        try:
            for skill in (2, 12, 14):
                with self.subTest(skill=skill):
                    rows, images = self.cast(skill, frames=48)
                    summary = next(r for r in rows if r.get('combat') is True)
                    self.assertEqual(summary['requests_unsent'], 1)
                    self.assertEqual((summary['hits'], summary['kills'], summary['unsupported']), (0, 0, 0))
                    self.assertGreaterEqual(summary['fx_created'], 7 if skill == 2 else (1 if skill == 12 else 17))
                    self.assertGreater(summary['sprites'] if skill == 12 else summary['particles_created'], 0)
                    frames = [r for r in rows if 'combat_frame' in r]
                    self.assertTrue(any(0x413 in f['effect_types'] for f in frames) if skill == 2 else
                                    any((0x7f4e if skill == 12 else 0x457) in f['effect_types'] for f in frames))
                    self.assertTrue(all(f['monsters'][0]['hp'] == frames[0]['monsters'][0]['hp'] for f in frames))
                    _, absent = self.cast(skill, particles=False, frames=48)
                    self.assertNotEqual(images, absent)
        finally:
            for name in names: (assets/name).unlink()
            for name in ('Spark02.OZJ', 'Explotion01.OZJ', 'Fire01.OZJ'): (effect/name).unlink()

    def cast_as(self, skill, weapon, cls, frames, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [str(ROOT/'native/build/mu-walk'), '--game-root', str(self.root), '--headless',
                   '--backend', 'soft', '--no-audio', '--no-items', '--no-players', '--tile', '120,120',
                   '--placement', str(self.placement), '--combat', '--combat-weapon', weapon, '--class', str(cls),
                   '--combat-script', f'2:skill:{skill}:spider;3:stop', '--frames', str(frames), '--every', '1',
                   '--width', '160', '--height', '100', '--out-dir', tmp, *extra]
            p = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            rows = [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
            images = [hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(Path(tmp).glob('*.png'))]
        return rows, images

    def test_rageful_blow_session_pixels(self):
        """RENDER-EFFECTS-004: the flying weapon 0x461, its impact pieces, quake ring and tails."""
        assets = self.root/'Data/Skill'
        names = ['EarthQuake0%d.bmd' % i for i in (1, 2, 3, 4, 5, 7, 8)] + ['flashing.bmd', 'tail.bmd']
        for i, name in enumerate(names):
            (assets/name).write_bytes(nf.synthetic_layout(300+i, actions=1, keys=(8,)))
        try:
            rows, images = self.cast_as(42, 'sword', 1, 48)
            summary = next(r for r in rows if r.get('combat') is True)
            self.assertEqual(summary['requests_unsent'], 1)
            self.assertEqual((summary['hits'], summary['kills'], summary['unsupported']), (0, 0, 0))
            self.assertEqual(summary['joints_created'], 8)   # the impact's eight 0x7fd5 sparks
            frames = [r for r in rows if 'combat_frame' in r]
            seen = set().union(*(set(f['effect_types']) for f in frames))
            self.assertTrue({0x461, 0x462, 0x463, 0x464, 0x465, 0x466, 0x468, 0x469, 0x46a, 0x46b} <= seen, seen)
            self.assertTrue(any(f['effect_types'].count(0x468) == 20 for f in frames))   # 4 rings x 5, open walls
            self.assertTrue(all(f['monsters'][0]['hp'] == frames[0]['monsters'][0]['hp'] for f in frames))
            for name in names: (assets/name).rename(assets/(name+'.off'))
            try: _, absent = self.cast_as(42, 'sword', 1, 48)
            finally:
                for name in names: (assets/(name+'.off')).rename(assets/name)
            self.assertTrue(images)
            self.assertNotEqual(images, absent)
        finally:
            for name in names: (assets/name).unlink()

    def test_triple_shot_verified_fan(self):
        """RENDER-EFFECTS-004: CreateArrows' default fan, three Arrow01 shots at 0, +15 and -15 degrees."""
        arrow = self.root/'Data/Skill/Arrow01.bmd'
        arrow.write_bytes(nf.synthetic_layout(400, actions=1, keys=(8,)))
        try:
            rows, images = self.cast_as(24, 'bow', 2, 30)
            summary = next(r for r in rows if r.get('combat') is True)
            self.assertEqual(summary['requests_unsent'], 1)
            self.assertEqual((summary['arrows'], summary['unsupported']), (3, 0))
            frames = [r for r in rows if 'combat_frame' in r]
            self.assertTrue(any(f['effect_types'].count(0x43b) == 3 for f in frames))
        finally:
            arrow.unlink()

    def test_other_bows_arrows_session(self):
        """RENDER-EFFECTS-007: the crossbow fires ArrowSteel (0x43c), another bow its own arrow; the bow's arrow
        model loads in its own slot and draws (removing it changes pixels)."""
        rows, _ = self.cast_as(24, 'crossbow', 2, 30)
        summary = next(r for r in rows if r.get('combat') is True)
        self.assertEqual((summary['arrows'], summary['unsupported']), (3, 0))
        frames = [r for r in rows if 'combat_frame' in r]
        self.assertTrue(any(f['effect_types'].count(0x43c) == 3 for f in frames))
        arrow = self.root/'Data/Skill/LaceArrow.bmd'
        arrow.write_bytes(nf.synthetic_layout(401, actions=1, keys=(8,)))
        try:
            rows, images = self.cast_as(24, 'bow', 2, 30, ('--combat-bow', '0x12fa'))
            summary = next(r for r in rows if r.get('combat') is True)
            self.assertEqual(summary['arrows'], 3)
            frames = [r for r in rows if 'combat_frame' in r]
            self.assertTrue(any(f['effect_types'].count(0x47f) == 3 for f in frames))
            arrow.rename(arrow.with_suffix('.off'))
            try: _, absent = self.cast_as(24, 'bow', 2, 30, ('--combat-bow', '0x12fa'))
            finally: arrow.with_suffix('.off').rename(arrow)
            self.assertTrue(images)
            self.assertNotEqual(images, absent)
        finally:
            arrow.unlink()

    def test_guardian_wing_pet_effect_pixels(self):
        """RENDER-EFFECTS-004: Spirit of Guardian's effect 0x460/4 is created, kept and drawn."""
        from test_native_pets import write_pet_models
        with tempfile.TemporaryDirectory() as tmp:
            root = write_combat_world(Path(tmp)/'game')
            write_pet_models(root, with_data=False)
            item = root/'Data/Item'
            nf.write_textured_model(item, 45).rename(item/'maria.bmd')
            skill = root/'Data/Skill'; skill.mkdir(exist_ok=True)
            wing = skill/'darkwing_hetachi.bmd'
            nf.write_textured_model(skill, 46).rename(wing)

            def run():
                with tempfile.TemporaryDirectory() as out:
                    p = subprocess.run([str(ROOT/'native/build/mu-walk'), '--game-root', str(root), '--headless',
                                        '--backend', 'soft', '--no-audio', '--no-env', '--no-items', '--no-players',
                                        '--tile', '120,120', '--helper', 'spirit', '--frames', '30', '--every', '1',
                                        '--width', '160', '--height', '100', '--out-dir', out],
                                       capture_output=True, text=True)
                    self.assertEqual(p.returncode, 0, p.stderr)
                    stats = [json.loads(x) for x in p.stdout.splitlines() if '"effects_created"' in x]
                    images = [hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(Path(out).glob('*.png'))]
                return stats[-1], images
            stats, images = run()
            self.assertEqual(stats['effects_created'], 30)    # one wing per drawn frame
            self.assertEqual(stats['effects_unsupported'], 0)
            self.assertEqual(stats['effects_live'], 25)       # lifetime 25
            wing.rename(skill/'off.bmd')
            _, absent = run()
            self.assertNotEqual(images, absent)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
    def test_rageful_blow_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects4.py'), '--cases', '60',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            r = json.loads(report.read_text())
            self.assertTrue(r['all_equal'])
            self.assertTrue(r['all_mutants_caught'])
            self.assertEqual(len(r['mutants']), 15)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
    def test_rank5_owner_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects5.py'), '--cases', '10',
                            '--particle-cases', '200', '--stone-cases', '200', '--mutations', '--output', str(report)],
                           check=True, capture_output=True)
            r = json.loads(report.read_text())
            self.assertTrue(r['all_equal'])
            self.assertTrue(r['all_mutants_caught'])
            self.assertEqual(len(r['mutants']), 25)
            self.assertEqual(r['instruction_cases'], 1190)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
    def test_other_bows_arrows_original_instructions_and_compiled_mutants(self):
        """RENDER-EFFECTS-007: 30 arrow types x subtypes 0/2/0x63 (+ Arrow01/0x63), CreateEffect and MoveEffect; bow
        0x12f9's sparks; the rank-5 pants' group-9 path has no owner effects."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects7.py'), '--cases', '2',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            r = json.loads(report.read_text())
            self.assertTrue(r['all_equal'])
            self.assertTrue(r['all_mutants_caught'])
            self.assertEqual(len(r['mutants']), 24)
            self.assertEqual(r['instruction_cases'], 432)

    def test_world_particle_consumers_and_sprite_registrations(self):
        subprocess.run(['make', '-C', str(ROOT/'native'), 'build/particle-consumers-host'], check=True,
                       capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            effect = Path(tmp)/'Data/Effect'
            effect.mkdir(parents=True)
            for name in ('flare01.OZJ', 'smoke01.OZJ', 'Magic_Ground2.OZJ', 'lightning3.OZJ', 'Impack03.OZJ', 'Explotion01.OZJ'):
                (effect/name).write_bytes(ozj_jpeg(32, 32))
            p = subprocess.run([str(ROOT/'native/build/particle-consumers-host'), tmp], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn('nine quads, exact sampling: OK', p.stdout)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
    def test_priority_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects3.py'), '--cases', '60',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            r = json.loads(report.read_text())
            self.assertTrue(r['all_equal'])
            self.assertTrue(r['all_mutants_caught'])
            self.assertEqual(len(r['mutants']), 10)

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
