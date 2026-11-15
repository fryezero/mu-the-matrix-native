"""Fixture-only receive-slice requests of catalogue skills outside the learned demo set."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'native/tests'))
from test_native_combat import write_combat_world
import native_fixtures as nf
from test_native_particles import ozj_jpeg

# skill: (class, weapon, hero requests, hero refused, remote requests, remote refused, remote pose action)
# The counts are the effect/joint/arrow requests of one cast with the default target record.
ROWS = {
    740: (1, 'sword', 0, 0, 1, 1, 0x9a), 77: (2, 'bow', 1, 1, 1, 1, None), 652: (2, 'bow', 1, 1, 1, 1, None),
    651: (2, 'bow', 0, 0, 0, 0, None), 727: (2, 'bow', 0, 0, 1, 1, 'attack'),
    2023: (2, 'bow', 1, 0, 1, 0, 0x107), 2025: (2, 'bow', 1, 1, 1, 1, 'magic'),
    2047: (2, 'bow', 2, 2, 2, 2, 'magic'),
    1125: (1, 'sword', 3, 3, 3, 3, None), 1126: (2, 'bow', 3, 3, 3, 3, None), 1127: (1, 'sword', 3, 3, 3, 3, None),
    425: (2, 'bow', 1, 1, 2, 2, 0xd9), 430: (2, 'bow', 1, 1, 2, 2, 0xd9), 2024: (2, 'bow', 2, 2, 2, 2, 0x106),
    432: (2, 'bow', 1, 0, 1, 0, 'magic'), 2026: (2, 'bow', 1, 0, 1, 0, 'magic'),
    2027: (2, 'bow', 6, 6, 6, 6, 'magic'),
}
BONE_ROWS = (1500, 1502, 1503)


class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-j2', '-C', str(ROOT / 'native'), 'build/mu-walk'], check=True,
                       capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tmp.name) / 'mu-walk'
        shutil.copy2(ROOT / 'native/build/mu-walk', cls.binary)
        cls.root = Path(write_combat_world(Path(cls.tmp.name) / 'game'))
        effect = cls.root / 'Data/Effect'
        effect.mkdir(exist_ok=True)
        (effect / 'smoke01.OZJ').write_bytes(ozj_jpeg(32, 32))
        skill = cls.root / 'Data/Skill'
        skill.mkdir(exist_ok=True)
        (skill / 'Arrow01.bmd').write_bytes(nf.synthetic_layout(400, actions=1, keys=(8,)))
        cls.placement = Path(cls.tmp.name) / 'actors.txt'
        cls.placement.write_text('actor 3 122 120 0 label DemoTarget\n')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def cast(self, skill, cls=1, weapon='sword', context=None, learn=True, frames=50, bow_item=None):
        env = dict(os.environ)
        env.pop('MU_SKILL35_CONTEXT', None)
        if context is not None:
            env['MU_SKILL35_CONTEXT'] = context
        with tempfile.TemporaryDirectory() as tmp:
            args = [str(self.binary), '--game-root', str(self.root), '--headless', '--backend', 'soft',
                    '--no-audio', '--no-items', '--no-players', '--tile', '120,120', '--placement',
                    str(self.placement), '--combat', '--class', str(cls), '--combat-weapon', weapon,
                    '--combat-script', f'2:skill:{skill}:DemoTarget;3:stop', '--frames', str(frames),
                    '--every', '1', '--width', '240', '--height', '160', '--out-dir', tmp]
            if learn:   # the authored learned entry: a fixture skills file, never a default list
                demo = Path(tmp) / 'skills.txt'
                demo.write_text(f'list {cls} {skill}\n')
                env['MU_SKILL_DEMO'] = str(demo)
            else:
                env.pop('MU_SKILL_DEMO', None)
            if bow_item is not None:
                args.extend(['--combat-bow', str(bow_item)])
            p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
            rows = [json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]
        return rows

    def assert_safe(self, rows):
        summary = next(r for r in rows if r.get('combat') is True)
        self.assertEqual((summary['requests_sent'], summary['requests_unsent'], summary['hits'], summary['kills']),
                         (0, 1, 0, 0))
        frames = [r for r in rows if 'combat_frame' in r]
        self.assertTrue(all(r['monsters'][0]['hp'] == frames[0]['monsters'][0]['hp'] for r in frames))
        return frames

    def plan(self, rows):
        return next((r for r in rows if r.get('skill35')), None)

    def test_hero_source_runs_the_guarded_slice(self):
        for skill, (cls, weapon, requests, refused, _rr, _rf, _pose) in ROWS.items():
            rows = self.cast(skill, cls, weapon)
            frames = self.assert_safe(rows)
            plan = self.plan(rows)
            self.assertIsNotNone(plan, skill)
            self.assertEqual((plan['casts'], plan['requests'], plan['refused'], plan['context_refused'],
                              plan['remote'], plan['self']), (1, requests, refused, 0, 0, 0), skill)
            if refused == requests:   # nothing was created: the pools stay empty
                self.assertTrue(all((r['fx'], r['joints']) == (0, 0) for r in frames), skill)

    def test_remote_source_context_takes_the_other_branch(self):
        for skill, (cls, weapon, _r, _f, requests, refused, pose) in ROWS.items():
            rows = self.cast(skill, cls, weapon, context='1,0')
            frames = self.assert_safe(rows)
            plan = self.plan(rows)
            self.assertEqual((plan['casts'], plan['requests'], plan['refused'], plan['remote']),
                             (1, requests, refused, 1), skill)
            if isinstance(pose, int):
                self.assertTrue(any(r['hero_action'] == pose for r in frames), (skill, pose))

    def test_existing_consumers_draw(self):
        for skill in (2023, 432, 2026):
            rows = self.cast(skill, 2, 'bow', frames=120)
            frames = self.assert_safe(rows)
            self.assertTrue(any(r['fx'] for r in frames), skill)
            self.assertEqual((frames[-1]['fx'], frames[-1]['joints'], frames[-1]['particles']), (0, 0, 0), skill)
        rows = self.cast(432, 2, 'bow', frames=80)
        self.assertTrue(any(r['joints'] for r in self.assert_safe(rows)))
        frames = self.assert_safe(self.cast(2023, 2, 'bow', frames=40))
        self.assertTrue(any(r['hero_action'] == 0x107 for r in frames))
        self.assertTrue(any(0x70a in r['effect_types'] for r in frames))

    def test_self_context_binds_the_target_to_the_source(self):
        rows = self.cast(2026, 2, 'bow', context='0,1', frames=80)
        self.assert_safe(rows)
        plan = self.plan(rows)
        self.assertEqual((plan['requests'], plan['refused'], plan['self']), (1, 0, 1))

    def test_bone_rows_use_only_the_hero_bone_service(self):
        # 1500 and 1503 read the source's bone 17; 1502 reads the target's. Only the hero's bones exist
        # natively, so 1502 is a counted context refusal unless the authored record targets the source.
        for skill, context, expected in [(1500, None, (1, 1, 1, 0)), (1503, None, (1, 1, 1, 0)),
                                         (1502, None, (1, 0, 0, 1)), (1502, '0,1', (1, 1, 1, 0)),
                                         (1500, '0,1', (1, 1, 1, 0))]:
            rows = self.cast(skill, 1, 'sword', context=context)
            frames = self.assert_safe(rows)
            plan = self.plan(rows)
            self.assertEqual((plan['casts'], plan['requests'], plan['refused'], plan['context_refused']),
                             expected, (skill, context))
            if expected[3] == 0:
                self.assertTrue(any(r['hero_action'] == 0x9c for r in frames), skill)

    def test_unlearned_wrong_class_and_outside_rows_stay_refused(self):
        for skill, (cls, weapon, *_rest) in ROWS.items():
            self.assertIsNone(self.plan(self.cast(skill, cls, weapon, learn=False, frames=6)), skill)
        for skill, cls in [(1500, 2), (77, 1), (2023, 1), (425, 1), (432, 1)]:
            self.assertIsNone(self.plan(self.cast(skill, cls, 'bow', frames=6)), skill)
        for skill, cls in [(46, 2), (76, 1), (232, 1), (235, 2), (426, 2), (427, 2), (723, 1), (813, 1),
                           (1501, 1), (2040, 1), (2043, 1), (441, 2), (801, 1), (1129, 1)]:
            self.assertIsNone(self.plan(self.cast(skill, cls, 'bow' if cls == 2 else 'sword', frames=6)), skill)

    def test_invalid_context_keeps_the_default(self):
        for context in ['1', '2,0', '1,2', '1,0x', '-1,0', '1,0,0']:
            plan = self.plan(self.cast(740, 1, 'sword', context=context, frames=6))
            self.assertEqual((plan['remote'], plan['self'], plan['requests']), (0, 0, 0), context)

    def test_exceptional_item_is_outside_admission(self):
        self.assertIsNone(self.plan(self.cast(77, 2, 'bow', frames=6, bow_item=0x12fb)))
        self.assertIsNotNone(self.plan(self.cast(77, 2, 'bow', frames=6, bow_item=0x12fa)))

    def buff(self, skill, ticks=None, frames=140):
        env = dict(os.environ)
        env.pop('MU_AURA_FIXTURE_TICKS', None)
        if ticks is not None:
            env['MU_AURA_FIXTURE_TICKS'] = str(ticks)
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.run([str(self.binary), '--game-root', str(self.root), '--headless', '--backend', 'soft',
                                '--no-audio', '--no-items', '--no-players', '--tile', '120,120', '--placement',
                                str(self.placement), '--combat', '--class', '2', '--combat-weapon', 'bow',
                                '--combat-script', f'2:skill:{skill}:DemoTarget;3:stop', '--frames', str(frames),
                                '--every', '1', '--width', '240', '--height', '160', '--out-dir', tmp],
                               cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        return [json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]

    def test_learned_buff_end_bodies(self):
        # 28 Greater Damage: 0x7f84/3 on the buffed hero, an existing consumer.
        rows = self.buff(28)
        frames = self.assert_safe(rows)
        end = next(r for r in rows if r.get('buff_end'))
        self.assertEqual((end['requests'], end['refused']), (1, 0))
        self.assertTrue(any(0x7f84 in r['effect_types'] for r in frames))
        self.assertEqual((frames[-1]['fx'], frames[-1]['joints']), (0, 0))
        # 27 Greater Defense without the authored presence clock: ground 0x7f84/2 and five joints, all refused.
        rows = self.buff(27)
        self.assert_safe(rows)
        end = next(r for r in rows if r.get('buff_end'))
        self.assertEqual((end['requests'], end['refused']), (6, 6))
        self.assertFalse(any(r.get('aura_fixture') for r in rows))
        unsupported = next(r for r in rows if 'combat_unsupported' in r)['combat_unsupported']
        self.assertIn(['e', 0x7f84, 2, 1], unsupported)
        # With the presence clock the aura's own joints already exist at the end body: only the ground is asked.
        rows = self.buff(27, ticks=60)
        self.assert_safe(rows)
        end = next(r for r in rows if r.get('buff_end'))
        self.assertEqual((end['requests'], end['refused']), (1, 1))

    def test_default_lists_have_no_catalogue_row(self):
        text = (ROOT / 'native/client/demo-skills.txt').read_text() + (ROOT / 'native/fixture/skills_model.c').read_text()
        listed = set()
        for line in text.splitlines():
            if line.startswith('list ') or 'static const int32_t' in line:
                listed |= {int(t.strip('{},;')) for t in line.replace('{', ' ').replace(',', ' ').split()
                           if t.strip('{},;').isdigit()}
        self.assertFalse(listed & (set(ROWS) | set(BONE_ROWS)))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
class Original(unittest.TestCase):
    def test_original_receive_slices(self):
        subprocess.run(['make', '-s', '-j2', '-C', str(ROOT / 'reconstructed/combat')], check=True,
                       capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_render_effects35.py'), '--cases', '40',
                            '--output', str(output)], check=True, cwd=ROOT, capture_output=True)
            report = json.loads(output.read_text())
        self.assertTrue(report['all_equal'])

    def test_census_matches_the_committed_tables(self):
        subprocess.run(['make', '-s', '-j2', '-C', str(ROOT / 'reconstructed/combat')], check=True,
                       capture_output=True)
        p = subprocess.run([sys.executable, str(ROOT / 'scripts/skill_catalogue_census.py'), '--check'], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout[-2000:] + p.stderr[-2000:])
        report = json.loads(p.stdout)
        self.assertEqual((report['rows'], report['dk'], report['elf'], report['default_step_and_ends']),
                         (37, 14, 23, 27))


class Tables(unittest.TestCase):
    """The committed classification is readable without private inputs."""

    def test_classification_shape(self):
        import csv
        with (ROOT / 'docs/research/skill-catalogue-classification.csv').open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 37)
        self.assertEqual(sum(r['class'] == 'DK' for r in rows), 14)
        groups = {}
        for r in rows:
            groups[r['group'][0]] = groups.get(r['group'][0], 0) + 1
        self.assertEqual(groups, {'A': 8, 'B': 3, 'C': 6, 'D': 4, 'E': 3, 'F': 4, 'G': 5, 'H': 2, 'I': 2})
        with (ROOT / 'docs/research/skill-catalogue-missing-consumers.csv').open() as f:
            missing = list(csv.DictReader(f))
        self.assertEqual(len(missing), 39)
        self.assertEqual(sum(m['kind'] == 'joint' for m in missing), 5)


if __name__ == '__main__':
    unittest.main()
