"""APP-POLISH-007: every offline demo character's join vitals, current = maximum.

Portable: the seed (fixture/hero_join.h through native/session/domains/hero.c, compiled from their source text)
gives the five demo characters the values below, keeps the recorded level-1 Dark Knight, applies the join
answer's copy rule (a maximum below 1 becomes 1, 16-bit words), and the world's combat HP input follows the hero's
join HP instead of a Dark Knight constant. Private (MU_RECOVERY_INTEGRATION=1): the original join block under
Unicorn (scripts/validate_app_polish7.py).
"""
import os
from pathlib import Path
import random
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_app_polish7 as v  # noqa: E402

# hp, mp, sd, ag (current = maximum) and the source of each character's values
EXPECTED = {
    'Nightfall': ([600, 600, 51, 39], 'demo rule, class 0 start stats at level 1'),
    'Ironclad': ([1100, 200, 52, 25], 'recorded level-1 Dark Knight'),
    'Windleaf': ([1119, 778, 1775, 284], 'demo rule, level 320, 22/1302/20/15'),
    'Spellblade': ([1100, 600, 65, 41], 'demo rule, class 3 start stats at level 1'),
    'Crownlord': ([900, 400, 66, 28], 'demo rule, class 4 start stats at level 1'),
}


class AppPolish7(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        join, seed = v.native(Path(cls.tmp.name))
        cls.join, cls.seed = staticmethod(join), staticmethod(seed)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_demo_characters(self):
        for name, cls, has, level, stats in v.DEMO:
            with self.subTest(name=name):
                vitals, fields = self.seed(cls, has, level, stats)
                self.assertEqual(vitals, EXPECTED[name][0])
                self.assertEqual(fields, [x for w in vitals for x in (w, w)])

    def test_recorded_dark_knight_agrees_with_the_demo_rule(self):
        """The recorded profile wins, and the demo rule gives the same numbers for it."""
        recorded, _ = self.seed(1, 1, 1, (28, 20, 25, 10, 0))
        self.assertEqual(recorded, [1100, 200, 52, 25])
        evolved, _ = self.seed(0x11, 1, 1, (28, 20, 25, 10, 0))   # demo rule (not the recorded class byte)
        self.assertEqual(evolved, recorded)
        self.assertEqual(self.seed(1, 1, 2, (28, 20, 25, 10, 0))[0], [1102, 200, 55, 25])

    def test_every_profile_is_consistent(self):
        rng = random.Random(7)
        for cls, has, level, stats in v.seed_cases(rng, 300):
            vitals, fields = self.seed(cls, has, level, stats)
            self.assertTrue(all(1 <= x <= 0xffff for x in vitals), (cls, has, level, stats, vitals))
            self.assertEqual(fields[0::2], fields[1::2])

    def test_join_copy_rule(self):
        attr = bytes([0xee]) * v.ATTR_SIZE
        out = self.join(attr, v.answer_words([0, 0, 0, 0, 0, 0, 0, 0]))
        self.assertEqual(v.fields(out), [0, 1, 0, 1, 0, 1, 0, 1])
        out = self.join(attr, v.answer_words([0xffff, 2, 3, 4, 5, 6, 7, 8]))
        self.assertEqual(v.fields(out), [0xffff, 2, 3, 4, 5, 6, 7, 8])
        changed = [i for i in range(v.ATTR_SIZE) if out[i] != attr[i]]
        self.assertTrue(all(any(o <= i < o + 4 for o in v.VITALS) for i in changed))

    def test_combat_hp_follows_the_join(self):
        world = (ROOT / 'native/world/world_rt.c').read_text()
        self.assertRegex(world, r'o->combat_config\.hero_hp = MU_WORLD_HERO_HP_JOIN;')
        self.assertIn('a->combat_config.hero_hp = world_rt_hero_join_hp(a);', world)
        self.assertNotRegex(world, r'o->combat_config\.hero_hp = \d+;')
        skills = (ROOT / 'native/world/parts/skills.c').read_text()
        self.assertRegex(skills, r'return seed\.vitals\[0\];')
        for part in ('actors.c', 'characters.c', 'skills.c'):
            text = (ROOT / 'native/world/parts' / part).read_text()
            self.assertNotIn('mu_fixture_hero_join(&seed)', text)
            self.assertTrue(re.search(r'world_rt_hero_join\(a, ?&seed\)', text), part)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private original instructions')
    def test_original_instructions(self):
        from types import SimpleNamespace
        r = v.run(SimpleNamespace(text=None, data=None, cases=64, mutants=False))
        self.assertEqual(r['mismatches'], 0, r['first_mismatches'])
        self.assertEqual({k: [x[0] for x in d.values()] for k, d in r['demo'].items()},
                         {k: e[0] for k, e in EXPECTED.items()})


if __name__ == '__main__':
    unittest.main()
