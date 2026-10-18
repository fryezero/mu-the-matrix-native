"""Portable checks of reconstructed/combat (NATIVE-COMBAT-001).

Worked examples and independent Python statements of the client rules,
without client bytes. The instruction-level comparison with the client is
scripts/validate_combat.py (Unicorn); a short private run of it, and the
regeneration of attack_speed_table.h by scripts/combat_static.py, are gated on
MU_RECOVERY_INTEGRATION=1 with the pinned evidence present.
"""
import ctypes
import math
import os
from pathlib import Path
import random
import re
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
TEXT = ROOT/'evidence/x86-text-capture-09/client-text.bin'
DATA = ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class Point(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('value', ctypes.c_int32), ('extra', ctypes.c_int32),
                ('scale', ctypes.c_float), ('position', ctypes.c_float * 3), ('color', ctypes.c_float * 3),
                ('delay', ctypes.c_int32), ('render_arg', ctypes.c_float), ('move', ctypes.c_uint8),
                ('gravity', ctypes.c_float), ('floor_test', ctypes.c_uint8), ('floor', ctypes.c_float)]


class NumberCall(ctypes.Structure):
    _fields_ = [('index', ctypes.c_int32), ('position', ctypes.c_float * 3), ('value', ctypes.c_int32),
                ('color', ctypes.c_float * 3), ('alpha', ctypes.c_float), ('scale', ctypes.c_float),
                ('render_arg', ctypes.c_float)]


class SpriteCall(ctypes.Structure):
    _fields_ = [('bitmap', ctypes.c_int32), ('position', ctypes.c_float * 3), ('width', ctypes.c_float),
                ('height', ctypes.c_float), ('uv', ctypes.c_float * 8), ('light', ctypes.c_float * 12),
                ('alpha', ctypes.c_float), ('skew', ctypes.c_float)]


class DamageInfo(ctypes.Structure):
    _fields_ = [('damage', ctypes.c_int32), ('type', ctypes.c_int32), ('flag8', ctypes.c_uint8),
                ('flag9', ctypes.c_uint8), ('flag_a', ctypes.c_uint8), ('flag_b', ctypes.c_uint8),
                ('flag_c', ctypes.c_uint8), ('flag_d', ctypes.c_uint8)]


class AttackInput(ctypes.Structure):
    _fields_ = [('object_type', ctypes.c_int32), ('class_byte', ctypes.c_uint8), ('safe_zone', ctypes.c_uint8),
                ('counter', ctypes.c_uint8), ('weapon', ctypes.c_int16 * 2), ('wing', ctypes.c_int16),
                ('attr_present', ctypes.c_uint8 * 2), ('two_handed', ctypes.c_uint8), ('bow_kind', ctypes.c_int32),
                ('dual', ctypes.c_uint8), ('state_72', ctypes.c_uint8),
                ('rand_values', ctypes.POINTER(ctypes.c_int32)), ('rand_count', ctypes.c_int32)]


class AttackResult(ctypes.Structure):
    _fields_ = [('action', ctypes.c_int32), ('speed_update', ctypes.c_int32), ('attack_start', ctypes.c_int32),
                ('rand_used', ctypes.c_int32), ('fault', ctypes.c_int32)]


class FadeState(ctypes.Structure):
    _fields_ = [('timer', ctypes.c_float), ('alpha', ctypes.c_float), ('z', ctypes.c_float),
                ('model', ctypes.c_int32), ('world', ctypes.c_int32), ('o6c', ctypes.c_int32),
                ('is_hero', ctypes.c_uint8), ('removed', ctypes.c_uint8)]


class SkillVisual(ctypes.Structure):
    _fields_ = [('skill', ctypes.c_int32), ('name', ctypes.c_char_p), ('receive', ctypes.c_int32),
                ('action', ctypes.c_int32), ('effect', ctypes.c_int32), ('effect_subtype', ctypes.c_int32),
                ('effect_count', ctypes.c_int32), ('arrows', ctypes.c_int32), ('sound', ctypes.c_int32),
                ('end_sound', ctypes.c_int32)]


HEIGHT_FN = ctypes.CFUNCTYPE(ctypes.c_float, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)


def load():
    subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
    lib = ctypes.CDLL(str(HERE/f'libcombat.{SUFFIX}'))
    F, I, U8, P, V = ctypes.c_float, ctypes.c_int32, ctypes.c_uint8, ctypes.POINTER, ctypes.c_void_p
    for name, args, result in [
            ('mu_damage_color', [I, I, I, U8, U8, P(F)], None), ('mu_damage_scale', [I], F),
            ('mu_point_create', [P(Point), P(F), I, P(F), F, U8, U8, F, I, HEIGHT_FN, V], I),
            ('mu_points_move', [P(Point)], None), ('mu_points_render', [P(Point), U8, P(NumberCall), I], I),
            ('mu_render_number', [P(F), I, P(F), F, F, F, P(SpriteCall), I], I),
            ('mu_format_thousands', [I, ctypes.c_char_p, ctypes.c_size_t], I),
            ('mu_show_damage', [P(Point), I, I, P(F), P(F), F, P(DamageInfo), HEIGHT_FN, V], I),
            ('mu_set_attack_speed', [F, F, P(F)], None), ('mu_attack_speed_writes', [I], ctypes.c_int),
            ('mu_player_attack_action', [P(AttackInput), P(AttackResult)], None),
            ('mu_monster_attack_action', [U8, ctypes.c_int], I),
            ('mu_player_magic_action', [U8, ctypes.c_int, I], I),
            ('mu_in_range', [I, I, I, I, F], ctypes.c_int), ('mu_hero_attack_range', [I, ctypes.c_int, ctypes.c_int,
                                                                                         ctypes.c_int16], F),
            ('mu_attack_direction', [F], U8), ('mu_monster_shock_allowed', [I, I], ctypes.c_int),
            ('mu_shock_action', [U8, I, I, I, I, I], I),
            ('mu_dead_step', [U8, P(ctypes.c_int)], U8), ('mu_dead_fade', [U8, P(FadeState)], None),
            ('mu_attack_time_step', [P(U8), I], ctypes.c_int),
            ('mu_skill_visual_find', [I], P(SkillVisual)), ('mu_skill_visual_count', [], I),
            ('mu_sprite_corners', [P(F), P(F), F, F, F, P(F)], None)]:
        function = getattr(lib, name)
        function.argtypes, function.restype = args, result
    return lib


def floats(*values):
    return (ctypes.c_float*len(values))(*values)


def no_height():
    return HEIGHT_FN(lambda ctx, x, y: 25.0)


class CombatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = load()
        cls.height = no_height()

    # -- damage colour and scale -------------------------------------------------
    def color(self, t, key=1, hero=2, fa=0, fb=0):
        c = (ctypes.c_float*3)()
        self.lib.mu_damage_color(t, key, hero, fa, fb, c)
        return tuple(round(x, 3) for x in c)

    def test_damage_colours_by_type(self):
        self.assertEqual(self.color(0, key=5, hero=5), (1.0, 0.0, 0.0))        # damage on the hero: red
        self.assertEqual(self.color(0), (1.0, 0.6, 0.0))                       # on others: orange
        self.assertEqual(self.color(1), (0.0, 1.0, 1.0))
        self.assertEqual(self.color(2), (0.0, 1.0, 0.6))
        self.assertEqual(self.color(3), (0.0, 0.6, 1.0))
        self.assertEqual(self.color(4), (1.0, 0.0, 1.0))
        self.assertEqual(self.color(5), (0.0, 1.0, 0.0))
        self.assertEqual(self.color(6), (0.7, 0.4, 1.0))
        self.assertEqual(self.color(11), (0.5, 0.5, 0.75))
        self.assertEqual(self.color(7), (1.0, 1.0, 1.0))
        self.assertEqual(self.color(3, fa=1), (1.0, 1.0, 0.0))
        self.assertEqual(self.color(3, fa=1, fb=1), (0.99, 0.89, 0.98))
        self.assertEqual(self.color(2, fb=1), (0.97, 0.58, 0.93))
        self.assertEqual(self.color(3, fb=1), (1.0, 0.96, 0.59))
        self.assertEqual(self.color(0, fa=2, fb=1), (0.99, 0.89, 0.98))   # flag_a must equal 1

    def test_damage_scales(self):
        self.assertEqual([self.lib.mu_damage_scale(t) for t in range(13)],
                         [15, 50, 50, 50, 15, 15, 15, 15, 15, 15, 15, 80, 15])

    # -- the points pool -------------------------------------------------------------
    def pool(self):
        return (Point*1000)()

    def test_create_point_takes_the_first_free_record(self):
        pts = self.pool()
        for i in range(5):
            pts[i].live = 1
        index = self.lib.mu_point_create(pts, floats(10, 20, 30), 77, floats(1, 0.6, 0), 15.0, 1, 1, 3.0, 9,
                                         self.height, None)
        self.assertEqual(index, 5)
        p = pts[5]
        self.assertEqual((p.live, p.value, p.extra, p.delay, p.move, p.floor_test), (1, 77, 9, 0, 1, 1))
        self.assertEqual((p.position[2], p.floor, p.gravity, p.scale, p.render_arg), (170.0, 165.0, 10.0, 15.0, 3.0))
        for i in range(1000):
            pts[i].live = 1
        self.assertEqual(self.lib.mu_point_create(pts, floats(0, 0, 0), 1, floats(1, 1, 1), 15.0, 1, 1, 0.0, 0,
                                                  self.height, None), -1)

    def test_rise_fade_and_shrink_curve(self):
        """Independent statement: z += gravity, gravity -= 0.3 (binary32) until
        0 >= gravity; the scale drops by 5 per step to 15; alpha = gravity * 0.4."""
        pts = self.pool()
        self.lib.mu_point_create(pts, floats(0, 0, 0), 1234, floats(1, 1, 1), 50.0, 1, 0, 0.0, 0, self.height, None)
        z, g, s, steps = f32(140.0), f32(10.0), f32(50.0), 0
        while pts[0].live:
            self.lib.mu_points_move(pts)
            steps += 1
            z, g = f32(z+g), f32(g-f32(0.3))
            s = max(f32(15.0), f32(s-5.0))
            self.assertEqual((pts[0].position[2], pts[0].gravity, pts[0].scale), (z, g, s))
            calls = (NumberCall*4)()
            if pts[0].live:
                self.assertEqual(self.lib.mu_points_render(pts, 0, calls, 4), 1)
                self.assertEqual(calls[0].alpha, f32(g*f32(0.4)))
        self.assertEqual(steps, 34)            # 10 / 0.3 rounded up
        self.assertAlmostEqual(z, 140+sum(10-0.3*k for k in range(34)), delta=0.01)

    def test_hit_text_keeps_its_scale_and_delay_holds_it(self):
        pts = self.pool()
        self.lib.mu_point_create(pts, floats(0, 0, 0), -2, floats(1, 1, 1), 1.0, 1, 0, 0.0, 0, self.height, None)
        self.lib.mu_point_create(pts, floats(0, 0, 0), 5, floats(1, 1, 1), 1.0, 0, 0, 0.0, 0, self.height, None)
        pts[1].delay = 3
        self.lib.mu_points_move(pts)
        self.assertEqual(pts[0].scale, 1.0)                 # value -2 (HIT) never shrinks or floors
        self.assertEqual((pts[1].delay, pts[1].gravity), (2, 10.0))
        for _ in range(3):
            self.lib.mu_points_move(pts)
        self.assertEqual((pts[1].position[2], pts[1].scale), (140.0, 15.0))   # move off: no rise; floor 15

    def test_render_modes_filter_by_height(self):
        pts = self.pool()
        for i, z in enumerate((200.0, 320.0, 400.0)):
            self.lib.mu_point_create(pts, floats(0, 0, z-140), i, floats(1, 1, 1), 15.0, 1, 1, 0.0, 0, self.height,
                                     None)
        calls = (NumberCall*8)()
        self.assertEqual(self.lib.mu_points_render(pts, 1, calls, 8), 2)     # z <= 350
        self.assertEqual(self.lib.mu_points_render(pts, 2, calls, 8), 2)     # z > 300
        self.assertEqual(self.lib.mu_points_render(pts, 0, calls, 8), 3)     # floor 165 < z
        pts[0].position[2] = 165.0
        self.assertEqual(self.lib.mu_points_render(pts, 0, calls, 8), 2)     # floor >= z hides it

    # -- RenderNumber ------------------------------------------------------------------
    def number(self, value, scale=15.0, pos=(0.0, 0.0, 0.0), arg6=0.0):
        sprites = (SpriteCall*32)()
        n = self.lib.mu_render_number(floats(*pos), value, floats(1, 0.6, 0), 2.0, scale, arg6, sprites, 32)
        return sprites[:n]

    def test_thousands_formatter(self):
        buf = ctypes.create_string_buffer(32)
        for value, text in [(0, '0'), (7, '7'), (999, '999'), (1000, '1,000'), (1005, '1,005'), (12345, '12,345'),
                            (1234567, '1,234,567'), (2147483647, '2,147,483,647')]:
            self.assertEqual(self.lib.mu_format_thousands(value, buf, 32), len(text))
            self.assertEqual(buf.value.decode(), text)

    def test_digits_are_laid_out_diagonally(self):
        """Independent statement of the digit branch: start x - L*5 - L*s/8,
        y - L*s/8; each digit a s x 1.5s sprite of font_damage at u = d/11; the
        position moves by s/2 in x and y."""
        s, sprites = 20.0, self.number(305, 20.0, (100.0, 50.0, 7.0))
        self.assertEqual(len(sprites), 3)
        x, y, du = f32(f32(100.0-f32(15.0))-f32(f32(3*s)*0.125)), f32(50.0-f32(f32(3*s)*0.125)), f32(1/11)
        for sp, digit in zip(sprites, (3, 0, 5)):
            self.assertEqual(sp.bitmap, 0x7534)
            self.assertEqual((sp.position[0], sp.position[1], sp.position[2]), (x, y, 7.0))
            self.assertEqual((sp.width, sp.height), (s, f32(s*1.5)))
            u = f32(digit*du)
            self.assertEqual(list(sp.uv), [u, 1.0, f32(u+du), 1.0, f32(u+du), 0.0, u, 0.0])
            self.assertEqual(sp.alpha, 2.0)
            x, y = f32(f32(s*0.5)+x), f32(f32(s*0.5)+y)

    def test_comma_uses_fontsc(self):
        sprites = self.number(1500)
        self.assertEqual([sp.bitmap for sp in sprites], [0x7534, 0x7dfe, 0x7534, 0x7534, 0x7534])
        comma = sprites[1]
        self.assertEqual((comma.width, comma.height), (f32(15*0.375), f32(15*1.5)))

    def test_special_values_draw_one_bitmap(self):
        expected = {-1: (0x7df4, 3.4, 1.7), -2: (0x7df3, 3.4, 1.7), -3: (0x7df5, 5.4, 1.7), -4: (0x7df6, 5.4, 1.7),
                    -5: (0x7df7, 5.4, 1.7), -6: (0x7df8, 5.4, 1.7), -7: (0x7dfd, 6.4, 1.6), -8: (0x7dfc, 3.2, 1.6),
                    -9: (0x7dfb, 3.2, 1.6), -10: (0x7dfa, 6.4, 1.6), -11: (0x7df9, 3.2, 1.6)}
        for value, (bitmap, w, h) in expected.items():
            sprites = self.number(value, 10.0)
            self.assertEqual(len(sprites), 1)
            self.assertEqual(sprites[0].bitmap, bitmap)
            self.assertEqual((sprites[0].width, sprites[0].height), (f32(10*f32(w)), f32(10*f32(h))))
            self.assertEqual(list(sprites[0].uv), [0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0])

    def test_sprite_corners_in_eye_space(self):
        camera = floats(1, 0, 0, 10, 0, 1, 0, 20, 0, 0, 1, -500)
        out = (ctypes.c_float*12)()
        self.lib.mu_sprite_corners(camera, floats(1, 2, 3), 4.0, 6.0, 0.5, out)
        self.assertEqual(list(out), [8.5, 19.0, -497.0, 12.5, 19.0, -497.0, 13.5, 25.0, -497.0, 9.5, 25.0, -497.0])

    # -- ShowDamage --------------------------------------------------------------------------
    def show(self, **fields):
        pts = self.pool()
        info = DamageInfo(**{'damage': 100, 'type': 0, **fields})
        color = floats(1.0, 0.6, 0.0)
        n = self.lib.mu_show_damage(pts, 3, 4, floats(0, 0, 0), color, 15.0, ctypes.byref(info), self.height, None)
        return n, [pts[i] for i in range(1000) if pts[i].live], list(color)

    def test_show_damage_stacks(self):
        n, live, _ = self.show()
        self.assertEqual((n, live[0].value, live[0].scale, live[0].floor_test), (1, 100, 15.0, 1))
        n, live, _ = self.show(flag8=1)
        self.assertEqual(n, 3)
        self.assertEqual([p.scale for p in live], [15.0, 30.0, 40.0])
        self.assertEqual([p.position[2] for p in live], [140.0, 147.0, 154.0])
        self.assertEqual([round(p.color[0], 3) for p in live], [0.6, 0.8, 0.8])
        self.assertEqual([p.render_arg for p in live], [3.0, 3.0, 3.0])
        n, live, _ = self.show(flag_a=1)
        self.assertEqual(([p.scale for p in live], [p.floor_test for p in live]), ([15.0, 30.0, 40.0], [0, 0, 1]))
        n, live, _ = self.show(flag9=1)
        self.assertEqual([p.scale for p in live], [15.0, 35.0])
        n, live, _ = self.show(flag_b=1, flag_c=1, type=5)
        self.assertEqual((live[0].scale, live[0].position[0], live[0].position[2]), (22.5, -70.0, 152.0))

    def test_zero_damage_shows_a_word(self):
        for t, value in [(0, -1), (7, -3), (8, -4), (9, -5), (10, -6), (3, -1)]:
            n, live, color = self.show(damage=0, type=t)
            self.assertEqual((n, live[0].value, live[0].scale), (1, value, 1.0))
            self.assertEqual(color, [0.5, 0.5, 0.5])     # not the hero: grey (written into the caller's colour)
        n, live, color = self.show(damage=0, type=12)
        self.assertEqual((n, live), (0, []))

    # -- attack speed --------------------------------------------------------------------
    def speeds(self, a, m):
        out = (ctypes.c_float*0x186)(*([-1.0]*0x186))
        self.lib.mu_set_attack_speed(a, m, out)
        return out

    def test_fist_and_weapon_attack_speeds(self):
        s = self.speeds(100.0, 50.0)
        self.assertEqual(s[0x6f], f32(f32(0.6)+f32(100*f32(0.004))))
        self.assertEqual(s[0x71], f32(f32(0.25)+f32(100*f32(0.004))))
        capped = self.speeds(400.0, 50.0)
        self.assertEqual(capped[0x6f], f32(f32(0.6)+f32(1.148)))
        self.assertEqual(sum(1 for i in range(0x186) if self.lib.mu_attack_speed_writes(i)), 175)

    def test_generated_table_matches_an_independent_evaluation(self):
        """Evaluates every statement of attack_speed_table.h in Python with
        binary32 rounding and compares with the compiled C."""
        text = (HERE/'attack_speed_table.h').read_text()
        stores = re.findall(r's\[0x([0-9a-f]+)\] = (.*);', text)
        self.assertEqual(len(stores), 179)
        rng = random.Random(7)
        for _ in range(30):
            a, m = f32(rng.choice([rng.uniform(0, 600), 288.0, 287.0])), f32(rng.uniform(0, 600))
            s = self.speeds(a, m)
            mine = {}
            for action, expr in stores:
                mine[int(action, 16)] = evaluate(expr, a, m)
            for action, value in mine.items():
                self.assertEqual(s[action], value, hex(action))

    # -- attack actions ------------------------------------------------------------------------
    def attack(self, weapon=(-1, -1), class_byte=1, counter=0, attr=(1, 0), two=0, bow=0, wing=-1, dual=0, s72=0,
               rands=(0, 0, 0, 0), safe=0):
        inp = AttackInput(object_type=0xa91, class_byte=class_byte, safe_zone=safe, counter=counter, wing=wing,
                          two_handed=two, bow_kind=bow, dual=dual, state_72=s72)
        inp.weapon[0], inp.weapon[1] = weapon
        inp.attr_present[0], inp.attr_present[1] = attr
        inp.rand_values = (ctypes.c_int32*len(rands))(*rands)
        inp.rand_count = len(rands)
        r = AttackResult()
        self.lib.mu_player_attack_action(ctypes.byref(inp), ctypes.byref(r))
        return r

    def test_attack_action_by_weapon(self):
        a = self.attack
        self.assertEqual(a().action, 0x6f)                                       # fists
        self.assertEqual(a(class_byte=7).action, 0x70)
        self.assertEqual([a(weapon=(0xae6, -1), counter=k).action for k in range(3)], [0x71, 0x72, 0x71])
        self.assertEqual([a(weapon=(0xae6, 0xaf0), counter=k).action for k in range(4)], [0x71, 0x73, 0x72, 0x74])
        self.assertEqual(a(weapon=(0xae6, -1), class_byte=9).action, 0x82)
        self.assertEqual([a(weapon=(0xaef, -1), two=1, counter=k).action for k in range(3)], [0x75, 0x76, 0x77])
        self.assertEqual(a(weapon=(0xafb, -1), two=1).action, 0x78)
        self.assertEqual(a(weapon=(-1, 0xae6), rands=(5,)).action, 0x74)          # left hand: 0x73 + rand % 2
        self.assertEqual(a(weapon=(0x14e6, -1), rands=(1,)).action, 0x72)         # staff
        self.assertEqual(a(weapon=(0x14e6, -1), class_byte=12).action, 0x70)
        self.assertEqual(a(weapon=(0x14e6, -1), s72=1).action, 0x88)
        self.assertEqual(a(weapon=(0x14e6, -1), two=1, rands=(0,)).action, 0xa3)
        self.assertEqual(a(weapon=(0x10e7, -1)).action, 0x79)
        self.assertEqual([a(weapon=(0x10f0, -1), counter=k).action for k in range(3)], [0x7b, 0x7c, 0x7d])
        self.assertEqual(a(weapon=(0x10f0, -1), class_byte=7).action, 0x7a)
        self.assertEqual((a(weapon=(0x12e6, 0x12f5), bow=1).action, a(weapon=(0x12e6, -1), bow=1, wing=3).action),
                         (0x7e, 0x80))
        self.assertEqual((a(weapon=(0x12ee, -1), bow=2).action, a(weapon=(0x12ee, -1), bow=2, wing=0).action),
                         (0x7f, 0x81))
        self.assertEqual(a(weapon=(0x2000, 0x2001), dual=1, attr=(1, 1), rands=(10,)).action, 0x84)
        self.assertEqual(a(weapon=(0x2000, 0x2001), dual=1, attr=(1, 0)).action, 0x84)
        self.assertEqual(a(weapon=(0x2000, 0x2001), dual=1, attr=(0, 1)).action, -1)
        self.assertEqual(a(weapon=(0x2000, -1), s72=1).action, 0x6f)
        self.assertEqual(a(weapon=(-1, 0x2000), s72=1).action, 0x87)
        r = a(safe=1)
        self.assertEqual((r.speed_update, r.attack_start), (1, 0))

    def test_monster_and_magic_actions(self):
        self.assertEqual([self.lib.mu_monster_attack_action(k, 0) for k in range(6)], [3, 4, 4, 3, 4, 4])
        self.assertEqual(self.lib.mu_monster_attack_action(0, 1), -1)
        self.assertEqual((self.lib.mu_player_magic_action(0, 0, 3), self.lib.mu_player_magic_action(14, 1, 0),
                          self.lib.mu_player_magic_action(1, 1, 0)), (0xa2, 0x10e, 0xa5))

    # -- range, facing, hit reaction, death --------------------------------------------------
    def test_range_and_direction(self):
        self.assertTrue(self.lib.mu_in_range(10, 10, 11, 11, f32(1.4142135)))
        self.assertFalse(self.lib.mu_in_range(10, 10, 11, 11, 1.0))
        self.assertTrue(self.lib.mu_in_range(10, 10, 16, 10, 6.0))
        self.assertFalse(self.lib.mu_in_range(10, 10, 16, 11, 6.0))
        self.assertFalse(self.lib.mu_in_range(10, 10, 10, 10, float('nan')))
        r = self.lib.mu_hero_attack_range
        self.assertEqual((r(0, 0, 0, 0), r(0x600, 0, 0, 0), r(0x600, 1, 0, 0), r(0, 1, 1, 0), r(0, 0, 0, 9)),
                         (1.0, 2.0, 6.0, 8.0, 7.0))
        self.assertEqual([self.lib.mu_attack_direction(a) for a in (0, 22, 23, 90, 180, 337, 338, 359)],
                         [1, 1, 2, 3, 5, 0, 1, 1])

    def test_hit_reaction(self):
        allowed = self.lib.mu_monster_shock_allowed
        self.assertEqual([allowed(0, a) for a in range(8)], [1, 1, 1, 0, 0, 1, 1, 1])
        self.assertEqual([allowed(0x2fb, a) for a in (0, 3, 4, 7, 8, 9)], [1, 1, 0, 1, 0, 0])
        shock = self.lib.mu_shock_action
        self.assertEqual(shock(0, 0x7a5, 0, 0, 10, 0), 5)
        self.assertEqual(shock(0, 0x7a5, 3, 0, 10, 0), -1)        # attacking
        self.assertEqual(shock(1, 0x7a5, 0, 0, 10, 0), -1)        # dead
        self.assertEqual(shock(0, 0x7a5, 0, 0, 0, 0), -1)         # no damage
        self.assertEqual(shock(0, 0x7a5, 0, 0, 0, 12), 5)         # types 12 / 15 react without damage

    def test_death_timeline(self):
        """Dead counter: SetPlayerDie from 15 on; fade: alpha 1 for 50 steps
        (timer 0.02 per step), then 1 - (t - 1), sinking 0.4 per step, removed
        once alpha < 0.01."""
        dead, die_steps = 1, []
        die = ctypes.c_int()
        for step in range(1, 30):
            dead = self.lib.mu_dead_step(dead, ctypes.byref(die))
            if die.value:
                die_steps.append(step)
        self.assertEqual(die_steps[0], 14)                 # counter reaches 15 on the 14th step after the packet
        s = FadeState(alpha=1.0, z=100.0, model=0x7a5)
        steps, first_fade = 0, None
        while not s.removed and steps < 200:
            alpha_before = s.alpha
            self.lib.mu_dead_fade(1, ctypes.byref(s))
            steps += 1
            if first_fade is None and s.alpha < alpha_before:
                first_fade = steps
        self.assertEqual(first_fade, 51)
        self.assertEqual(steps, 100)
        self.assertAlmostEqual(s.z, 100.0-0.4*49, places=3)
        hero = FadeState(timer=1.995, alpha=1.0, model=0x7a5, is_hero=1)
        self.lib.mu_dead_fade(1, ctypes.byref(hero))
        self.assertEqual(hero.removed, 0)                  # the hero is never removed by the fade

    def test_attack_timer(self):
        t, ends = ctypes.c_uint8(1), []
        for step in range(1, 40):
            if self.lib.mu_attack_time_step(ctypes.byref(t), 15):
                ends.append(step)
        self.assertEqual(ends, [14])
        self.assertEqual(t.value, 0)

    def test_skill_table(self):
        find = self.lib.mu_skill_visual_find
        self.assertEqual(find(22).contents.action, 0x8c)
        self.assertEqual(find(41).contents.action, 0x8e)
        self.assertEqual((find(4).contents.effect, find(4).contents.effect_subtype), (0x413, 1))
        self.assertEqual(find(17).contents.effect, 0x437)
        self.assertEqual(find(24).contents.arrows, 2)
        self.assertEqual(find(26).contents.effect, 0x7f84)
        self.assertFalse(find(9999))
        self.assertGreaterEqual(self.lib.mu_skill_visual_count(), 15)

    # -- private -------------------------------------------------------------------------------
    @unittest.skipUnless(PRIVATE and TEXT.exists() and DATA.exists(), 'set MU_RECOVERY_INTEGRATION=1 with the evidence')
    def test_client_comparison_and_generated_table(self):
        python = sys.executable
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'table.h'
            subprocess.run([python, str(ROOT/'scripts/combat_static.py'), '--text', str(TEXT), '--data', str(DATA),
                            '--emit-c', str(out)], check=True, capture_output=True)
            self.assertEqual(out.read_bytes(), (HERE/'attack_speed_table.h').read_bytes())
            try:
                import unicorn  # noqa: F401
            except ImportError:
                self.skipTest('Unicorn is not installed')
            result = subprocess.run([python, str(ROOT/'scripts/validate_combat.py'), '--text', str(TEXT), '--data',
                                     str(DATA), '--cases', '60', '--heavy-cases', '4'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])


def evaluate(expr, a, m):
    """Binary32 evaluation of one generated C expression (a recursive parser
    over the generator's grammar: literals, a, m, + - * / and ?:)."""
    tokens = re.findall(r'mu_f32\(0x[0-9a-f]{8}u\)|/\*.*?\*/|>=|[()+\-*/?:]|[am]', expr)
    tokens = [t for t in tokens if not t.startswith('/*')]
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take():
        pos[0] += 1
        return tokens[pos[0]-1]

    def atom():
        t = take()
        if t == '(':
            value = conditional()
            assert take() == ')'
            return value
        if t == 'a':
            return a
        if t == 'm':
            return m
        return struct.unpack('<f', struct.pack('<I', int(t[7:17], 16)))[0]

    def binary():
        left = atom()
        while peek() in ('+', '-', '*', '/'):
            op = take()
            right = atom()
            left = f32({'+': left+right, '-': left-right, '*': left*right,
                        '/': left/right if right else math.copysign(math.inf, left)}[op])
        return left

    def conditional():
        left = binary()
        if peek() == '>=':
            take()
            right = binary()
            assert take() == '?'
            yes = binary()
            assert take() == ':'
            no = binary()
            return yes if left >= right else no
        return left
    return conditional()


if __name__ == '__main__':
    unittest.main()
