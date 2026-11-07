"""RENDER-ITEMS-CLOAK: the capes of wings 0x2382..0x2385, 0x2394, 0x2395 (reconstructed/cloth, native/world/world_cloak.c).

Portable: the authored cloth alone (grid, springs, spheres, the fixed top row, a step, the GL stream of a render, the
wind walk's clamp, the cloth flag of RenderCharacter's block).
Private, pinned client (MU_RECOVERY_INTEGRATION=1, MU_SECTION3): scripts/validate_item_cloak.py (the registry row).
Private, installed data (MU_GAME_ROOT): Lorencia through mu-walk with a class-0 hero wearing InnocenceCape.bmd and
players wearing 0x2382 (class 0x00: a cloth; class 0x01: none, as the client's flag), and the same frame whatever
the capture cadence.
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parents[1]
ROOT = NATIVE.parent
sys.path.insert(0, str(ROOT/'scripts'))
import validate_item_cloak as vc  # noqa: E402

WALK = NATIVE/'build/mu-walk'
GAME = os.environ.get('MU_GAME_ROOT')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
IDENTITY = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]


def host(bones):
    h = vc.CHost()
    h.bones = ctypes.cast(bones, ctypes.POINTER(ctypes.c_float))
    h.bone_count = 60
    h.has_model = 1
    h.body_scale = 1.0
    h.alpha = 1.0
    return h


class Cloth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib, error = vc.build(vc.DIR, Path(cls.tmp.name), 'cloth_test')
        if cls.lib is None:
            raise AssertionError(error)
        cls.bones = (ctypes.c_float * (12 * 60))(*(IDENTITY * 60))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def wing(self, wing):
        cloths = (vc.CCloth * 2)()
        h = host(self.bones)
        n = self.lib.mu_cloth_wing_create(cloths, wing, ctypes.byref(h))
        return n, cloths, h

    def test_wing_cases(self):
        for wing, count, textures in ((0x2382, 1, [0x83f6]), (0x2383, 1, [0x83f6]), (0x2384, 2, [0x83f7, 0x83f8]),
                                      (0x2385, 2, [0x83f7, 0x83f8]), (0x2394, 1, [0x846b]), (0x2395, 1, [0x846b])):
            n, cloths, _ = self.wing(wing)
            self.assertEqual(n, count)
            self.assertEqual([cloths[i].texture_front for i in range(n)], textures)
            for i in range(n):
                c = cloths[i]
                self.assertEqual((c.columns, c.rows, c.vertex_count, c.type, c.bone), (10, 10, 100, 0x1005, 19))
                # vertical 90, horizontal 90, one diagonal 81, the other from row 2 on (72)
                self.assertEqual(c.spring_count, 333)
                self.assertEqual([c.vertices[k].flags for k in range(10)], [1] * 10)   # the top row hangs
                self.assertEqual(sum(c.vertices[k].flags for k in range(10, 100)), 0)
            self.assertEqual(cloths[0].sphere_count, 4 if count == 1 else 2)
        for wing in (-1, 0x22ee, 0x2381, 0x2386):
            self.assertEqual(self.wing(wing)[0], 0)

    def test_step_keeps_the_top_row_and_drops_the_rest(self):
        n, cloths, h = self.wing(0x2382)
        g = vc.CGlobals()
        self.lib.mu_cloth_default_globals(ctypes.byref(g))
        top = [list(cloths[0].vertices[k].position) for k in range(10)]
        low = list(cloths[0].vertices[95].position)
        for _ in range(10):
            self.assertEqual(self.lib.mu_cloth_move2(ctypes.byref(cloths[0]), ctypes.byref(h), ctypes.byref(g),
                                                     ctypes.c_float(0.005), 5), 1)
        self.assertEqual([list(cloths[0].vertices[k].position) for k in range(10)], top)
        self.assertNotEqual(list(cloths[0].vertices[95].position), low)   # the free vertices move
        cloths[0].owner = 0
        self.assertEqual(self.lib.mu_cloth_move2(ctypes.byref(cloths[0]), ctypes.byref(h), ctypes.byref(g),
                                                 ctypes.c_float(0.005), 5), 0)

    def test_render_stream(self):
        n, cloths, h = self.wing(0x2384)
        side = vc.CSide.__new__(vc.CSide)
        side.stream = []
        side._sink()
        light = (ctypes.c_float * 3)(1.0, 0.1, 0.1)
        self.assertEqual(self.lib.mu_cloth_render(ctypes.byref(cloths[1]), ctypes.byref(h), light,
                                                  ctypes.byref(side.sink)), 1)
        s = side.stream
        self.assertEqual(s[0], ('state', 2))   # EnableAlphaTest(1): type 0x1000
        self.assertEqual(s[1][0], 'glColor4f')
        self.assertEqual([x for x in s if x[0] == 'bind'], [('bind', 0x83f8), ('bind', 0x83f8)])
        self.assertEqual(sum(1 for x in s if x[0] == 'glVertex3f'), 2 * 81 * 4)
        us = [vc.u2f(x[1]) for x in s if x[0] == 'glTexCoord2f']
        vs = [vc.u2f(x[2]) for x in s if x[0] == 'glTexCoord2f']
        self.assertAlmostEqual(min(us), -1.0)   # the right half: uv scale 0.5, offset 1
        self.assertAlmostEqual(max(us), 1.0)
        self.assertLessEqual(max(vs), vc.u2f(vc.f2u(0.99)))

    def test_wind_walk_clamp(self):
        g = vc.CGlobals()
        self.lib.mu_cloth_default_globals(ctypes.byref(g))
        seen = []
        for _ in range(4000):
            self.lib.mu_cloth_wind_step(ctypes.byref(g))
            seen.append(g.wind)
        self.assertGreaterEqual(min(seen), vc.u2f(vc.f2u(-0.2)))
        self.assertLessEqual(max(seen), 1.0)

    def test_cloth_flag(self):
        def gate(cls, wing=0x2382, world=0, pk=0, c0e=0, index=-1):
            gi = vc.CGateIn(cls, c0e, pk, wing, index, 0xa91, 0xa91, world)
            go = vc.CGateOut()
            self.lib.mu_cloth_gate(ctypes.byref(gi), ctypes.byref(go))
            return go.render, [round(v, 3) for v in go.light]
        self.assertEqual(gate(0x00)[0], 1)   # Dark Wizard
        self.assertEqual(gate(0x04)[0], 1)   # Dark Lord
        self.assertEqual(gate(0x01)[0], 0)   # Dark Knight: the client makes no cloth
        self.assertEqual(gate(0x02)[0], 0)   # Elf
        self.assertEqual(gate(0x03)[0], 1)   # skin 3
        self.assertEqual(gate(0x13)[0], 0)   # skin 0x13
        self.assertEqual(gate(0x01, wing=0x23f1)[0], 1)
        self.assertEqual(gate(0x00, world=0x12)[0], 0)
        self.assertEqual(gate(0x00, c0e=2)[0], 0)
        self.assertEqual(gate(0x00, index=0x211)[0], 0)
        self.assertEqual(gate(0x00, pk=6)[1], [1.0, 0.1, 0.1])


@unittest.skipUnless(PRIVATE and os.environ.get('MU_SECTION3'), 'needs MU_RECOVERY_INTEGRATION=1 and MU_SECTION3')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_item_cloak.py'), '--cases', '12', '--frames',
                            '4', '--gate-cases', '64', '--wind-cases', '20', '--output', str(out)], check=True,
                           capture_output=True)
            report = json.loads(out.read_text())
        for name, family in report['families'].items():
            self.assertEqual((family['mismatches'], family['stopped']), (0, 0), name)
        self.assertEqual(report['families']['create']['cases'], 12)
        self.assertEqual(report['families']['step']['cases'], 48)


PLAYERS = ('player Velvet class=0x00 at=126,126 dir=7 pk=3 level=400 armor=8:10:7 pants=9:10:7 gloves=10:10:7 '
           'boots=11:10:7 helm=7:10:7 weapon0=0:102:7 wing=12:156:0 route=124,123;126,126 idle=20\n'
           'player Bastion class=0x01 at=129,121 dir=7 pk=3 level=400 armor=8:9:7 pants=9:9:7 gloves=10:9:7 '
           'boots=11:9:7 helm=7:9:7 weapon0=0:65:9 wing=12:156:0\n')


def walk(tmp, every, frames=46):
    players = Path(tmp)/'players.txt'
    players.write_text(PLAYERS)
    out = Path(tmp)/f'every{every}'
    result = subprocess.run([str(WALK), '--game-root', GAME, '--headless', '--backend', 'soft', '--no-audio',
                             '--width', '320', '--height', '240', '--every', str(every), '--out-dir', str(out),
                             '--tile', '128,124', '--class', '0', '--players', str(players), '--player-range', '20',
                             '--frames', str(frames), '--quiet', '--hero-item', 'wing=Item/InnocenceCape.bmd',
                             '--walk', '131,127'], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr[-2000:]}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return next(r for r in rows if r.get('cloak') is True), out


@unittest.skipUnless(PRIVATE and GAME, 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class WorldScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-walk'], check=True, capture_output=True)

    def test_wearers_and_cadence(self):
        with tempfile.TemporaryDirectory() as tmp:
            dense, a = walk(tmp, 15)
            sparse, b = walk(tmp, 45)
            # the hero and Velvet make a cloth each; Bastion (class 0x01) is gated on every drawn frame
            self.assertEqual(dense['created'], 2)
            self.assertEqual(dense['steps'], 2 * 46)
            self.assertEqual(dense['gated'], 4)
            self.assertEqual(dense['drawn'], 2 * 4)
            self.assertEqual(sparse['steps'], dense['steps'])
            self.assertEqual(sparse['wind'], dense['wind'])
            # the cloths step every rendered frame, drawn or not: the same frame 45 at either cadence
            self.assertEqual((a/'frame-0045.png').read_bytes(), (b/'frame-0045.png').read_bytes())


if __name__ == '__main__':
    unittest.main()
