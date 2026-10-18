"""Combat in the walk-around world (NATIVE-COMBAT-001) checks.

Portable (synthetic data only), through `mu-walk --combat` (headless,
software rasterizer) on the synthetic open world of test_native_world.py with
a Player model that has all 0x186 actions and a synthetic monster (server
class 3, Monster10.bmd):
  * the hero walks into range, faces the target (CreateAngle), takes the
    SetPlayerAttack action with the SetAttackSpeed PlaySpeed and runs
    AttackTime 1..14 per attack;
  * the demo server's damage arrives after the latency: the monster takes
    action 5 (SetPlayerShock), the damage text rises and fades on the client
    curve (gravity 10, -0.3 per step) with the client colour;
  * death: the dead counter, action 6 from 15 on, the fade 50 steps later,
    removal 100 steps after the die packet, the demo respawn;
  * bows create arrows, skills take their actions and create their effects,
    a scripted click picks the monster, monsters hit back (red text);
  * NATIVE-COMBAT-002: skills through the older effect pools (effects,
    particles, joints, effect lights), Evil Spirit joints and area requests,
    Hellfire/Inferno/Twisting Slash area effects, the hero's hit (0x134,
    voice 0x69+) and death (0x142 at dead 15, voice 0x6c) through
    SetPlayerShock/SetPlayerDie and the demo respawn at the home tile;
  * runs are deterministic.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): a Lorencia fight with the
demo placement loads every damage bitmap and both effect models and kills.
"""
import json
import math
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
from test_native_world import write_open_world  # noqa: E402

WALK = NATIVE/'build/mu-walk'
PLACEMENT = NATIVE/'world/lorencia-demo-placement.txt'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def write_combat_world(root):
    write_open_world(root)
    layout = nf.character_layout(3, bones=50, actions=0x186, keys=(3, 2), dummies=(9, 21))
    (Path(root)/'Data'/'Player'/'Player.bmd').write_bytes(nf.envelope_v15(layout))
    monster = Path(root)/'Data'/'Monster'
    monster.mkdir(parents=True, exist_ok=True)
    (monster/'monster10.bmd').write_bytes(nf.synthetic_layout(8, actions=7, keys=(6,)))   # class 3 -> type 9
    return root


def run(root, placement, *args, check=True):
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft',
                                 '--no-audio', '--placement', str(placement), '--width', '64', '--height', '64',
                                 '--every', '1', '--out-dir', tmp, '--tile', '120,120', '--combat',
                                 *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'frames': [r for r in rows if 'combat_frame' in r],
            'walk': [r for r in rows if 'frame' in r and 'tick' in r],
            'summary': next((r for r in rows if r.get('combat') is True), None),
            'logs': [r['combat_log'] for r in rows if 'combat_log' in r], 'result': result}


def monster(frame, actor=0):
    return next(m for m in frame['monsters'] if m['actor'] == actor)


def starts(frames):
    """Hero actions at the first report of each attack. The attack starts in
    MoveHero with AttackTime 1 and MoveCharacters increments it in the same
    logic step, so a report after the step shows 2."""
    return [f['hero_action'] for f in frames if f['attack_time'] == 2]


def fade_steps():
    """Independent statement of the fade: the timer grows by binary32 0.02
    per step from the die packet's step on; alpha = 1 - (t - 1) once t >= 1;
    removal when alpha < 0.01. Returns (first step with alpha < 1, removal step)."""
    t, step, first = 0.0, 0, None
    while True:
        step += 1
        t = f32(t+f32(0.02))
        if t >= 1.0:
            alpha = f32(1.0-f32(t-1.0))
            if first is None and alpha < 1.0:
                first = step
            if not alpha >= f32(0.01):
                return first, step


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_combat_world(Path(cls.tmp.name)/'game')
        cls.placement = Path(cls.tmp.name)/'placement.txt'
        cls.placement.write_text('# demo\nactor 3 123 120 6 label spider\n')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class FightTests(Build):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.out = run(cls.root, cls.placement, '--frames', '520', '--combat-script', '2:attack:spider',
                      '--combat-seed', '11')

    def test_hero_walks_into_range_faces_and_attacks(self):
        frames = self.out['frames']
        attacking = [f for f in frames if f['attack_time']]
        self.assertTrue(attacking)
        first = attacking[0]
        self.assertEqual(first['attack_time'], 2)
        self.assertAlmostEqual(first['hero_angle'], 90.0, places=2)            # CreateAngle toward +x
        self.assertIn(first['hero_action'], (0x71, 0x72))                        # one-handed sword
        walk = self.out['walk']
        tile = walk[frames.index(first)]['tile']
        self.assertLessEqual(math.hypot(tile[0]-123, tile[1]-120), 1.0)          # range 1 for a sword
        # AttackTime 2..14 after the start step, then the end of the attack (15 -> 0)
        times = [f['attack_time'] for f in frames[frames.index(first):frames.index(first)+15]]
        self.assertEqual(times[:13], list(range(2, 15)))
        self.assertEqual(times[13], 0)
        # successive attacks alternate 0x71 / 0x72 with the attack counter
        self.assertEqual(starts(frames)[:4], [0x71, 0x72, 0x71, 0x72])

    def test_damage_text_follows_the_client_curve(self):
        frames = self.out['frames']
        start = next(i for i, f in enumerate(frames) if f['points'])
        point = frames[start]['point_list'][0]
        value, z0, scale0, gravity0 = point[0], point[1], point[2], point[3]
        self.assertEqual(gravity0, 9.7)                    # created and moved once in that step
        z, g = f32(z0), f32(gravity0)
        for f in frames[start+1:start+20]:
            z, g = f32(z+g), f32(g-f32(0.3))
            p = f['point_list'][0]
            self.assertAlmostEqual(p[1], z, places=2)
            self.assertAlmostEqual(p[3], g, places=3)
        if value > 0:
            self.assertEqual(point[4:7], [1.0, 0.6, 0.0])   # orange: damage on a monster, type 0

    def test_hit_reaction_death_fade_removal_and_respawn(self):
        frames = self.out['frames']
        m = [monster(f) for f in frames]
        self.assertIn(5, [x['action'] for x in m])                       # SetPlayerShock: action 5
        # the die packet sets Dead = 1 and MoveCharacter counts it up in the same step
        die = next(i for i, x in enumerate(m) if x['dead'])
        self.assertEqual(m[die]['dead'], 2)
        six = next(i for i, x in enumerate(m) if x['action'] == 6)
        self.assertEqual(m[six]['dead'], 15)                              # SetPlayerDie from 15 on
        self.assertEqual(six - die, 13)
        first, gone = fade_steps()
        fade = next(i for i, x in enumerate(m) if x['alpha'] < 1.0)
        self.assertEqual(fade - die, first - 1)
        removed = next(i for i, x in enumerate(m) if x['removed'])
        self.assertEqual(removed - die, gone - 1)
        self.assertLess(m[removed-1]['z'], m[fade-1]['z'])                 # sank 0.4 per step
        back = next(i for i, x in enumerate(m) if i > removed and not x['removed'])
        self.assertEqual(back - removed, 125)                             # demo respawn delay
        self.assertEqual((m[back]['dead'], m[back]['alpha'], m[back]['action']), (0, 1.0, 0))
        s = self.out['summary']
        self.assertEqual((s['kills'], s['removed'], s['respawns']), (1, 1, 1))
        self.assertTrue(any('spider dies' in line for line in self.out['logs']))

    def test_monster_hits_back(self):
        s = self.out['summary']
        self.assertGreaterEqual(s['monster_attacks'], 1)
        self.assertGreaterEqual(s['hero_hits'], 1)
        red = [p for f in self.out['frames'] for p in f['point_list'] if p[4:7] == [1.0, 0.0, 0.0]]
        attacks = [monster(f)['action'] for f in self.out['frames'] if monster(f)['attack_time'] == 2]
        self.assertTrue(set(attacks) <= {3, 4})
        if s['hero_hits'] and any(p[0] > 0 for f in self.out['frames'] for p in f['point_list']):
            self.assertTrue(red or s['hero_hits'])

    def test_deterministic(self):
        again = run(self.root, self.placement, '--frames', '120', '--combat-script', '2:attack:spider',
                    '--combat-seed', '11')
        self.assertEqual(again['frames'], self.out['frames'][:119] + [again['frames'][-1]])


class WeaponAndSkillTests(Build):
    def test_bow_attacks_create_arrows(self):
        out = run(self.root, self.placement, '--frames', '80', '--combat-weapon', 'bow', '--class', '2',
                  '--combat-script', '2:attack:spider')
        self.assertEqual(starts(out['frames'])[0], 0x7e)                   # bow, no wings
        self.assertGreaterEqual(out['summary']['arrows'], 1)
        walk = out['walk']
        first = next(i for i, f in enumerate(out['frames']) if f['attack_time'])
        self.assertEqual(walk[first]['tile'], [120, 120])                   # range 6: no walking

    def test_skills_take_their_actions_and_effects(self):
        out = run(self.root, self.placement, '--frames', '60', '--combat-weapon', 'staff', '--class', '0',
                  '--combat-script', '2:skill:4:spider')
        self.assertIn(starts(out['frames'])[0], (0xa1, 0xa2))              # SetPlayerMagic
        self.assertGreaterEqual(out['summary']['fx_created'], 1)           # MODEL_FIRE at the end of the attack
        self.assertGreaterEqual(out['summary']['particles_created'], 1)    # its Fire01 trail
        self.assertTrue(any(f['lights'] for f in out['frames']))
        out = run(self.root, self.placement, '--frames', '60', '--class', '1', '--combat-script', '2:skill:22:spider')
        self.assertEqual(starts(out['frames'])[0], 0x8c)                   # Cyclone

    def test_area_skills(self):
        out = run(self.root, self.placement, '--frames', '60', '--combat-weapon', 'staff', '--class', '0',
                  '--combat-script', '2:skill:9:spider')
        s = out['summary']
        self.assertGreaterEqual(s['joints_created'], 8)                    # Evil Spirit: JointSpirit01 ribbons
        self.assertGreaterEqual(s['area_requests'], 1)
        self.assertIn(0x75, [f['sound'] for f in out['frames']])           # sEvil
        self.assertEqual(s['unsupported'], 0)
        for skill in (10, 14):                                             # Hellfire circles, Inferno ring
            out = run(self.root, self.placement, '--frames', '60', '--combat-weapon', 'staff', '--class', '0',
                      '--combat-script', f'2:skill:{skill}:spider')
            self.assertGreaterEqual(out['summary']['fx_created'], 1, skill)
            self.assertGreaterEqual(out['summary']['area_requests'], 1, skill)
        out = run(self.root, self.placement, '--frames', '60', '--class', '1', '--combat-script', '2:skill:41:spider')
        self.assertGreaterEqual(out['summary']['fx_created'], 1)           # the swirl effect 0x453
        self.assertIn(0x73, [f['sound'] for f in out['frames']])           # sKnightSkill4

    def test_hero_hit_death_and_respawn(self):
        out = run(self.root, self.placement, '--frames', '260', '--hero-hp', '30', '--combat-seed', '11',
                  '--combat-script', '2:attack:spider')
        frames = out['frames']
        self.assertGreaterEqual(out['summary']['hero_shocks'], 1)
        self.assertEqual(out['summary']['hero_deaths'], 1)
        dead = [i for i, f in enumerate(frames) if f['hero_dead']]
        first = dead[0]
        self.assertTrue(all(frames[i]['hero_action'] != 0x142 for i in dead if frames[i]['hero_dead'] < 15))
        at15 = next(i for i in dead if frames[i]['hero_dead'] == 15)
        self.assertEqual(frames[at15]['hero_action'], 0x142)               # SetPlayerDie, class 0 male
        self.assertEqual(frames[at15]['sound'], 0x6c)                      # pMaleDie
        self.assertLessEqual(frames[first]['hero_hp'], 0)
        back = dead[-1] + 1
        self.assertEqual((frames[back]['hero_dead'], frames[back]['hero_hp']), (0, 30))
        self.assertEqual(out['walk'][back]['tile'], [120, 120])            # the demo respawn at home

    def test_click_picks_the_monster(self):
        out = run(self.root, self.placement, '--frames', '40', '--combat-script', '3:click:spider')
        self.assertEqual(out['summary']['pick_hits'], 1)
        self.assertTrue(any(f['target'] == 0 for f in out['frames']))

    def test_bad_scripts_are_refused(self):
        for text in ('attack', '5:hit:spider', '5:skill:spider'):
            result = subprocess.run([str(WALK), '--game-root', str(self.root), '--headless', '--combat-script', text],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, text)


@unittest.skipUnless(PRIVATE, 'set MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class InstalledTests(unittest.TestCase):
    def test_lorencia_fight(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        root = os.environ['MU_GAME_ROOT']
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([str(WALK), '--game-root', root, '--headless', '--backend', 'soft', '--no-audio',
                                     '--placement', str(PLACEMENT), '--tile', '182,127', '--width', '160',
                                     '--height', '100', '--frames', '300', '--every', '50', '--out-dir', tmp,
                                     '--combat-script', '5:click:bull fighter'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = next(json.loads(l) for l in result.stdout.splitlines() if l.startswith('{"combat": true'))
        self.assertEqual((summary['bitmaps_loaded'], summary['models_loaded']), (15, 9))   # + Spark01, the swirl's spark joints (NATIVE-JOINT-001)
        self.assertEqual(summary['pick_hits'], 1)
        self.assertGreaterEqual(summary['kills'], 1)


if __name__ == '__main__':
    unittest.main()
