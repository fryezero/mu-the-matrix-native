"""RENDER-EFFECTS-021: the item pre-draw programs' particles without an owner that had no native kind, and the
armour owner-effect programs in the world.

Portable: reconstructed/particles (item_predraw_kinds.inc) through a C shim: Clud64 0x7ffd/0x1b (bow 0x1316) lives
15 steps, fades by LifeTime / 15 and grows 0.04 per step; Shiny01 0x7f66/5 (0x230c, 0x2496) rises along its negative
gravity and dims by 1.02 per step; shiny06 0x8180/5 (0x23ef, 0x2400, 0x2405) keeps the common record, lives two
steps and draws no sprite.

Private, original instructions (MU_RECOVERY_INTEGRATION=1): scripts/validate_render_effects21.py with its mutants
(validator row validate_render_effects21).

Private, installed data (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): Lorencia through `mu-walk`:
  * players wearing the five wings whose programs create 0x7f66/5 and 0x8180/5: nothing is refused;
  * players and the hero wearing armour with an owner-effect program (0x1bc3 Manticore Knight, 0x1bc4, 0x1bde,
    0x1c41, 0x1c78): the programs run with the character's posed skeleton as the OBJECT owner; their sprites and
    particles are created and nothing is refused;
  * the CALLERS-001 crowd (no such armour) prints no item_owner_fx line.
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
ROOT = NATIVE.parent
WALK = NATIVE/'build/mu-walk'
GAME = os.environ.get('MU_GAME_ROOT')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'

SHIM = r'''
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "reconstructed/particles/particles.h"

static int32_t values[64], used;
static int32_t next(void *c) { (void)c; return values[used++ % 64]; }

static int check(int ok, const char *what)
{
    if (!ok) printf("FAIL %s\n", what);
    return ok;
}

int main(void)
{
    for (int i = 0; i < 64; ++i) values[i] = 7 * i + 3;
    mu_pt_host h;
    memset(&h, 0, sizeof h);
    h.rand = next;
    h.frame_time = 0.1f;
    const float at[3] = {12800.0f, 12400.0f, 150.0f}, angle[3] = {0.0f, 0.0f, 0.0f}, light[3] = {1.0f, 0.5f, 0.25f};
    int ok = 1;
    ok &= check(mu_pt_kind_supported(0x7ffd, 0x1b) && mu_pt_kind_supported(0x7f66, 5) &&
                mu_pt_kind_supported(0x8180, 5), "admitted");
    ok &= check(!mu_pt_kind_supported(0x7ffd, 0x1c) && !mu_pt_kind_supported(0x7f66, 6) &&
                !mu_pt_kind_supported(0x8180, 4), "neighbours stay out");
    mu_pt_bitmap b = {64.0f, 64.0f, 3};
    mu_pt_render_call r;
    mu_pt_particle p;
    /* Clud64/0x1b: rotation rand() % 360, three rands for a zero velocity */
    memset(&p, 0, sizeof p);
    used = 0;
    ok &= check(mu_pt_create_record(&p, &h, 0x7ffd, at, angle, light, 0x1b, 1.5f, MU_PT_NO_OWNER, 0) == 1, "clud");
    ok &= check(used == 4 && p.lifetime == 15 && p.initial_lifetime == 15 && p.alpha == 1.0f &&
                p.rotation == 3.0f && p.velocity[0] == 0.0f && p.scale == 1.5f, "clud create");
    int steps = 0;
    while (mu_pt_move_record(&p, &h)) {
        if (steps == 0)
            ok &= check(p.alpha == 1.0f && fabsf(p.scale - 1.54f) < 1e-6f, "clud first step");
        ++steps;
    }
    ok &= check(steps == 15, "clud lives 15 steps");
    p.live = 1;
    p.lifetime = 5;
    p.alpha = 5.0f / 15.0f;
    ok &= check(mu_pt_render_record(&p, &b, 0, 0.0f, 0, &r) == 1 && r.sprites == 1 &&
                r.sprite.light[0] == 1.0f * p.alpha && r.sprite.bitmap == 0x7ffd, "clud render");
    /* Shiny01/5 */
    memset(&p, 0, sizeof p);
    used = 0;
    ok &= check(mu_pt_create_record(&p, &h, 0x7f66, at, angle, light, 5, 0.5f, MU_PT_NO_OWNER, 0) == 1, "shiny");
    ok &= check(used == 5 && p.lifetime == 13 && p.angle[0] == 45.0f && p.scale == 0.5f &&
                p.position[0] == at[0] + 2.0f && p.position[1] == at[1] - 1.0f &&
                p.gravity == -(float)(31 % 10) * 0.3f, "shiny create");   /* rands 3, 10, 17, 24, 31 */
    const float z = p.position[2], g = p.gravity;
    ok &= check(mu_pt_move_record(&p, &h) && p.position[2] == z + g && p.rotation == 10.0f &&
                p.light[0] == 1.0f / 1.02f, "shiny move");
    ok &= check(mu_pt_render_record(&p, &b, 0, 0.0f, 0, &r) == 1 && r.sprites == 1 &&
                r.sprite.light[0] == p.light[0], "shiny render");
    /* shiny06/5: the common record only, two steps, no sprite */
    memset(&p, 0, sizeof p);
    used = 0;
    ok &= check(mu_pt_create_record(&p, &h, 0x8180, at, angle, light, 5, 1.0f, MU_PT_NO_OWNER, 0) == 1 &&
                used == 0 && p.lifetime == 2, "shiny06 create");
    ok &= check(mu_pt_render_record(&p, &b, 0, 0.0f, 0, &r) == 1 && r.sprites == 0 && r.state_count == 1,
                "shiny06 render");
    steps = 0;
    while (mu_pt_move_record(&p, &h)) ++steps;
    ok &= check(steps == 2, "shiny06 lives two steps");
    if (ok) printf("pre-draw kinds OK\n");
    return !ok;
}
'''


class Kinds(unittest.TestCase):
    def test_the_three_kinds(self):
        with tempfile.TemporaryDirectory() as tmp:
            shim, exe = Path(tmp)/'shim.c', Path(tmp)/'shim'
            shim.write_text(SHIM)
            p = ROOT/'reconstructed/particles'
            sources = [p/f for f in ('particles.c', 'world_flames.c', 'elbeland.c', 'sprites.c', 'shadow.c',
                                     'visual.c', 'layout.c')] + [ROOT/'reconstructed/record-math/record_math.c']
            subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-ffp-contract=off',
                            '-fno-fast-math', '-I', str(ROOT), str(shim), *map(str, sources), '-lm', '-o', str(exe)],
                           check=True, capture_output=True)
            r = subprocess.run([str(exe)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('pre-draw kinds OK', r.stdout)


@unittest.skipUnless(PRIVATE, 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects21.py'),
                            '--cases', '20', '--mutations', '--output', str(out)], check=True, capture_output=True)
            report = json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertTrue(report['all_mutants_caught'])
        self.assertEqual(report['instruction_cases'], CASES)
        self.assertEqual(len(report['mutants']), MUTANTS)


CASES, MUTANTS = 267, 19   # the registry row (scripts/validators.toml)

WINGS = (
    'player WingA class=0x01 at=129,124 dir=3 pk=3 level=400 helm=7:9:7 armor=8:9:7 pants=9:9:7 gloves=10:9:7 '
    'boots=11:9:7 weapon0=0:65:9 wing=12:38:0\n'
    'player WingB class=0x02 at=127,125 dir=1 pk=3 level=400 helm=7:3:5 armor=8:3:5 pants=9:3:5 wing=12:432:0\n'
    'player WingC class=0x04 at=130,122 dir=5 pk=3 level=400 armor=8:4:7 pants=9:4:7 wing=12:265:0\n'
    'player WingD class=0x00 at=126,122 dir=2 pk=3 level=400 helm=7:10:7 armor=8:10:7 wing=12:282:0\n'
    'player WingE class=0x01 at=128,126 dir=4 pk=3 level=400 helm=7:9:7 armor=8:9:7 wing=12:287:0\n')
ARMOUR = (
    'player ArmA class=0x01 at=129,124 dir=3 pk=3 level=400 armor=8:221:0 pants=9:221:0 helm=7:221:0\n'
    'player ArmB class=0x02 at=127,125 dir=1 pk=3 level=400 armor=8:222:0 pants=9:222:0\n'
    'player ArmC class=0x04 at=130,122 dir=5 pk=3 level=400 armor=8:235:0\n'
    'player ArmD class=0x00 at=126,122 dir=2 pk=3 level=400 armor=8:347:0\n'
    'player ArmE class=0x01 at=128,126 dir=4 pk=3 level=400 armor=8:402:0\n')


def walk(players_text, *args, frames=60):
    with tempfile.TemporaryDirectory() as tmp:
        command = [str(WALK), '--game-root', GAME, '--headless', '--backend', 'soft', '--no-audio', '--width', '320',
                   '--height', '240', '--every', '1000', '--out-dir', tmp, '--tile', '128,124', '--frames',
                   str(frames), '--quiet', *args]
        if players_text:
            players = Path(tmp)/'players.txt'
            players.write_text(players_text)
            command += ['--players', str(players), '--player-range', '20']
        else:
            command += ['--no-players']
        result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr[-2000:]}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    pick = lambda key: next((r for r in rows if r.get(key) is True), None)
    return pick('item_pre_draw'), pick('item_owner_fx'), pick('particles')


@unittest.skipUnless(PRIVATE and GAME, 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class WorldScenes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-walk'], check=True, capture_output=True)

    def test_wing_programs_refuse_nothing(self):
        pre, owner, particles = walk(WINGS)
        self.assertEqual(pre['players'], WINGS_PRE)
        self.assertIsNone(owner)
        self.assertEqual((particles['created'], particles['unsupported']), WINGS_CREATED)

    def test_player_armour_programs_run_with_the_wearer(self):
        pre, owner, particles = walk(ARMOUR)
        self.assertIsNone(pre)
        self.assertEqual(owner['players'], ARMOUR_PLAYERS)
        self.assertEqual(owner['hero'], {'owner_effects': 0, 'owner_refused': 0})
        self.assertEqual((particles['created'], particles['sprites_created'], particles['unsupported']),
                         ARMOUR_CREATED)

    def test_hero_armour_programs_run_with_the_hero(self):
        _, owner, particles = walk(None, '--hero-item', 'armor=Item/ArmorMale135.bmd')
        self.assertEqual(owner['hero'], HERO)
        self.assertEqual(owner['players'], {'owner_effects': 0, 'owner_refused': 0})
        self.assertEqual(particles['unsupported'], 0)


WINGS_PRE = {'pre_effects': 142, 'pre_refused': 0, 'hidden': 0}   # before: 138 / 3 refused (0x7f66/5, 0x8180/5)
WINGS_CREATED = (4, 0)
ARMOUR_PLAYERS = {'owner_effects': 41, 'owner_refused': 0}   # before: no owner programs ran
ARMOUR_CREATED = (7, 34, 0)
HERO = {'owner_effects': 20, 'owner_refused': 0}


if __name__ == '__main__':
    unittest.main()
