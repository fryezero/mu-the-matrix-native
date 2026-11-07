"""RENDER-ITEMS-CLOAK / CLOAK-002: the wings' physics capes (reconstructed/cloth, native/world/world_cloak.c).

Portable: the authored cloth alone (CreateCloth's cases, grid, springs, spheres, the fixed top row, a step, the GL
stream of a render with its glow pass, the angle-matrix variant, the draw test's sub-types, the wind walk's clamp,
the cloth flag of RenderCharacter's block).
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

    def wing(self, wing, level=0, arg4=0, scene=6, scale=0.9):
        cloths = (vc.CCloth * 3)()
        h = host(self.bones)
        n = self.lib.mu_cloth_wing_create(cloths, ctypes.byref(vc.CWingIn(wing, level, arg4, scene, scale)),
                                          ctypes.byref(h))
        return n, cloths, h

    def stream(self, cloth, h, light=None, time=0.0):
        side = vc.CSide.__new__(vc.CSide)
        side.stream = []
        side._sink()
        g = vc.CGlobals()
        self.lib.mu_cloth_default_globals(ctypes.byref(g))
        g.time = time
        light = light or (ctypes.c_float * 3)(1.0, 1.0, 1.0)
        result = self.lib.mu_cloth_render(ctypes.byref(cloth), ctypes.byref(h), ctypes.byref(g), light,
                                          ctypes.byref(side.sink))
        return result, side.stream

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
        for wing in (-1, 0x22ee, 0x239a, 0x239f, 0x23a2, 0x2400):
            self.assertEqual(self.wing(wing)[0], 0)

    def test_every_case(self):
        counts = {0x230e: 3, 0x2498: 3, 0x2317: 1, 0x2318: 3, 0x2368: 1, 0x236d: 1, 0x2380: 1, 0x2381: 1, 0x2386: 2,
                  0x2387: 2, 0x2392: 1, 0x2393: 1, 0x2396: 1, 0x2398: 1, 0x239e: 3, 0x23a0: 1, 0x23a1: 1, 0x23a5: 2,
                  0x23a7: 1, 0x23ec: 3, 0x23fd: 3, 0x2402: 3, 0x23f1: 1, 0x2401: 1, 0x23f3: 1, 0x23f4: 1, 0x23fc: 1,
                  0x2488: 3, 0x248a: 1, 0x248b: 1, 0x2490: 1, 0x2504: 1, 0x24c6: 2, 0x34e6: 1, 0x34e7: 1, 0x34e8: 1,
                  0x34e9: 1, 0x34eb: 1}
        for wing, count in counts.items():
            n, cloths, _ = self.wing(wing, level=13)
            self.assertEqual(n, count, hex(wing))
            for i in range(n):
                self.assertEqual(cloths[i].owner, 1, hex(wing))
                self.assertEqual([cloths[i].vertices[k].flags for k in range(cloths[i].columns)],
                                 [1] * cloths[i].columns, hex(wing))
        # arg 4 = 1: the robe whatever the wing (Robe01 front, Robe02 back)
        for wing in (-1, 0x2382):
            n, cloths, _ = self.wing(wing, arg4=1)
            self.assertEqual((n, cloths[0].texture_front, cloths[0].texture_back, cloths[0].type),
                             (1, 0x790b, 0x790c, 0x405))

    def test_level_glows(self):
        self.assertEqual(self.wing(0x2396, level=8)[1][0].glow_texture, -1)
        self.assertEqual(self.wing(0x2396, level=9)[1][0].glow_texture, 0x846d)
        self.assertEqual(self.wing(0x239e, level=10)[1][2].glow_texture, -1)
        self.assertEqual([self.wing(0x239e, level=11)[1][i].glow_texture for i in range(3)], [0x8503, 0x8504, 0x8502])
        self.assertEqual(self.wing(0x2381, level=0)[1][0].glow_texture, 0x83f5)   # always

    def test_scaled_case(self):
        _, game, _ = self.wing(0x23ec, scene=6, scale=0.9)
        _, select, _ = self.wing(0x23ec, scene=5, scale=1.2)
        self.assertEqual((game[0].width, game[0].height), (170.0, 160.0))   # 0.9 / 0.9
        self.assertEqual((select[0].width, select[0].height), (170.0, 160.0))   # 1.2 / 1.2
        _, big, _ = self.wing(0x23ec, scene=6, scale=1.8)
        self.assertAlmostEqual(big[1].height, 340.0, places=3)
        self.assertEqual((big[1].type, big[2].type), (0x9000, 0x11000))

    def test_angle_matrix_variant(self):
        n, cloths, _ = self.wing(0x24c6)
        self.assertEqual((n, cloths[0].custom, cloths[0].bone, cloths[1].texture_front), (2, 1, 47, 0x830d))
        m = list(cloths[0].matrix)   # AngleMatrix(0, 90, 0): x -> -z
        self.assertAlmostEqual(m[2], 1.0, places=5)
        self.assertAlmostEqual(m[8], -1.0, places=5)

    def test_glow_pass(self):
        n, cloths, h = self.wing(0x2381)
        result, s = self.stream(cloths[0], h, time=1234.0)
        self.assertEqual(result, 1)
        glow = s[s.index(('state', 3)):]   # after the two faces: EnableAlphaBlend, the glow bitmap, one quad stream
        self.assertEqual(glow[1], ('bind', 0x83f5))
        self.assertEqual(glow[2][0], 'glColor4f')
        self.assertEqual(sum(1 for x in glow if x[0] == 'glVertex3f'), 81 * 4)
        self.assertEqual(sum(1 for x in s if x[0] == 'glVertex3f'), 3 * 81 * 4)
        bright = [vc.u2f(self.stream(cloths[0], h, time=t)[1][-1 - 2 * 81 * 4 - 2][1]) for t in (0.0, 400.0, 785.0)]
        for b in bright:
            self.assertTrue(0.0 <= b <= 1.0)
        self.assertNotEqual(bright[0], bright[2])   # pulsed by WorldTime (speed 4: 0x0185bdc4(-4, 0))

    def test_draw_test_subtypes(self):
        allowed = self.lib.mu_cloth_draw_allowed
        self.assertEqual(allowed(0x00, 0, 1, 1, 0), 1)
        self.assertEqual(allowed(0x00, 0x431, 1, 1, 0), 0)
        self.assertEqual(allowed(0x03, 0x5bc, 1, 1, 0), 0)   # skin 3 under a sub-type of 0x009a0989
        self.assertEqual(allowed(0x00, 0x5bc, 1, 1, 0), 1)
        self.assertEqual(allowed(0x00, 0, 0xe4, 0xe4, 0), 0)
        self.assertEqual(allowed(0x00, 0, 1, 1, 0x271), 0)

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
        result, s = self.stream(cloths[1], h, (ctypes.c_float * 3)(1.0, 0.1, 0.1))
        self.assertEqual(result, 1)
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

    def test_more_cases(self):
        # CLOAK-002: 0x239e +13 (three cloths with level glows), 0x2381 (one, always glowing), 0x24c6 on a Dark Knight
        # (the angle-matrix variant; its wing sets the flag for any class), 0x2398 on a Dark Knight (gated)
        players = ('player A class=0x00 at=127,126 dir=5 pk=3 level=400 armor=8:10:7 wing=12:184:13 idle=20\n'
                   'player B class=0x00 at=125,126 dir=5 pk=3 level=400 armor=8:10:7 wing=12:155:0 idle=20\n'
                   'player C class=0x01 at=129,126 dir=5 pk=3 level=400 armor=8:10:7 wing=12:480:0 idle=20\n'
                   'player D class=0x01 at=127,128 dir=5 pk=3 level=400 armor=8:10:7 wing=12:178:0 idle=20\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'players.txt'
            path.write_text(players)
            result = subprocess.run([str(WALK), '--game-root', GAME, '--headless', '--backend', 'soft', '--no-audio',
                                     '--width', '320', '--height', '240', '--every', '10', '--out-dir', tmp, '--tile',
                                     '128,124', '--class', '1', '--players', str(path), '--player-range', '20',
                                     '--frames', '21', '--quiet'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        row = next(json.loads(line) for line in result.stdout.splitlines() if '"cloak"' in line)
        self.assertEqual(row['created'], 3 + 1 + 2)
        self.assertEqual(row['gated'], 3)          # D on each of the three drawn frames
        self.assertEqual(row['drawn'], 6 * 3)


if __name__ == '__main__':
    unittest.main()
