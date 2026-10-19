"""Portable checks of reconstructed/names (NATIVE-NAMES-001).

Worked examples of the hudPlayerName game side without client bytes: the
handler's height table and head height, the name builder, the colour
tables, gens frames, addInfo's member order and gates, the per-frame
update's operations over a few frames, setHp / removeInfo / setTopMovie,
the chat bubble and the chat prefix rules, and spot checks of the monster
kind table.  The instruction-level comparison with the client is
scripts/validate_names.py (Unicorn); a short private run of it is gated on
MU_RECOVERY_INTEGRATION=1 with the pinned evidence present.
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_names as vn  # noqa: E402  (ctypes layouts and the library loader; no client bytes)

TEXT = ROOT/'evidence/x86-text-capture-09/client-text.bin'
DATA = ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


def character(**kw):
    c = vn.Character()
    c.guild, c.wing, c.ride, c.monster_class, c.live, c.pk = -1, -1, 0xffff, -1, 1, 3
    for k, v in kw.items():
        if k in ('name', 'server', 'duel_name'):
            setattr(c, k, v.encode())
        elif k == 'position':
            c.position[:] = v
        else:
            setattr(c, k, v)
    return c


class Lib(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.lib = vn.load_library(HERE/f'libnames.{vn.SUFFIX}')

    def window(self):
        w = vn.Window()
        self.lib.mu_hn_window_init(ctypes.byref(w))
        return w

    def env(self, keep, hero=None, **kw):
        e = vn.Env()
        proj = vn.PROJECT(lambda _, p, x, y: (x.__setitem__(0, p[0] / 10.0), y.__setitem__(0, 500.0 - p[2])))
        keep.append(proj)
        e.project = proj
        e.duel_key = -1
        e.name_option = 1
        if hero is not None:
            e.hero = ctypes.pointer(hero)
        for k, v in kw.items():
            setattr(e, k, v)
        return e

    def test_constructor_heights(self):
        w = self.window()
        self.assertEqual([w.item_height, w.item_offset, w.height_player, w.height_wing, w.height_ride_a,
                          w.height_ride_b, w.height_ride_c, w.height_ride, w.height_state, w.height_ride_d],
                         [35, 5, 180, 205, 220, 225, 280, 240, 300, 320])
        self.assertEqual((w.monster_view, w.selected, w.item_view), (1, -1, 1))

    def test_head_height(self):
        w, keep = self.window(), []
        e = self.env(keep)
        h = lambda c: self.lib.mu_hn_head_height(ctypes.byref(w), ctypes.byref(c), ctypes.byref(e))  # noqa: E731
        self.assertEqual(h(character(kind=2, height=210)), 210)              # monsters: the name height
        self.assertEqual(h(character(kind=1)), 180)
        self.assertEqual(h(character(kind=1, wing=3)), 205)
        self.assertEqual(h(character(kind=1, class_byte=6)), 200)           # base classes 6, 11: +20
        self.assertEqual(h(character(kind=1, class_byte=0x1f)), 210)        # base class 15: +30
        self.assertEqual(h(character(kind=1, ride=0x1a02)), 220)
        self.assertEqual(h(character(kind=1, ride=0x1834)), 320)
        self.assertEqual(h(character(kind=1, ride=0x1234)), 240)            # any other ride
        self.assertEqual(h(character(kind=1, monster_class=0x271, height=300)), 300)
        self.assertEqual(h(character(kind=1, ride=0x1a03, monster_class=0x272, height=181)), 225)   # (181-180)/2 = 0

    def test_name_text_and_colours(self):
        keep, buf = [], ctypes.create_string_buffer(256)
        e = self.env(keep)
        for kind, want in ((0, b'Hound'), (1, b'Hound[37]'), (2, b'Hound[637]')):
            self.lib.mu_hn_name_text(ctypes.byref(character(name='Hound', level=37, name_kind=kind)),
                                     ctypes.byref(e), buf, 256)
            self.assertEqual(buf.value, want)
        self.assertEqual([self.lib.mu_hn_pk_color(i) for i in range(8)],
                         [b'#96FFF0', b'#568CEE', b'#8CB1EE', b'#FFDC00', b'#FF9600', b'#FF4400', b'#FF0000',
                          b'#FF0000'])
        self.assertEqual(self.lib.mu_hn_class_color(2), b'#FF3319')
        self.assertEqual(self.lib.mu_hn_class_color(22), b'#FFFFFF')
        hero = character(name='Me')
        e2 = self.env(keep, hero=hero)
        self.assertEqual(self.lib.mu_hn_guild_color(ctypes.byref(hero), ctypes.byref(e2)), b'#C8FF00')
        self.assertEqual(self.lib.mu_hn_guild_color(ctypes.byref(character(guild_relation=2)), ctypes.byref(e2)),
                         b'#FF0000')

    def test_gens_frame(self):
        keep = []
        hero = character(guild=4, gens=1)
        e = self.env(keep, hero=hero)
        g = lambda c: self.lib.mu_hn_gens_frame(ctypes.byref(c), ctypes.byref(e))  # noqa: E731
        self.assertEqual(g(character(gens=0)), 29)
        self.assertEqual(g(character(gens=2, gens_rank=3)), 17)
        self.assertEqual(g(character(gens=1, gens_rank=99)), 14)
        e.gens_option = 1
        self.assertEqual(g(character(gens=1, gens_rank=3, guild=5)), 29)

    def test_add_info_members_and_gates(self):
        w, keep = self.window(), []
        hero = character(key=7, kind=1, name='Nighty', level=400, hp=50, max_hp=200, position=(1000.0, 0.0, 20.0))
        e = self.env(keep, hero=hero, hero_level=400)
        info = vn.Info()
        self.assertEqual(self.lib.mu_hn_add_info(ctypes.byref(w), ctypes.byref(hero), ctypes.byref(e),
                                                 ctypes.byref(info)), 1)
        out = ctypes.create_string_buffer(4096)
        self.lib.mu_hn_info_json(ctypes.byref(info), out, 4096)
        got = json.loads(out.value)
        self.assertEqual(list(got), ['key', 'type', 'name', 'GuildName', 'ServerName', 'elemental', 'mark', 'x', 'y',
                                     'hp', 'isShow', 'isPlayerHpShow', 'isPlayerNameShow', 'isStrifeGens',
                                     'GensFrame', 'attArray', 'damageTypeArray'])
        self.assertEqual(got['name'], "<font color='#FFDC00' size='14'>Nighty</font>")
        self.assertEqual((got['x'], got['y'], got['hp']), (100, 480, 25))   # z = 20 + name height 0
        w2 = self.window()
        ground = character(key=11, kind=1, name='Low', hp=1, max_hp=3, position=(55.0, 0.0, 0.0))
        self.lib.mu_hn_add_info(ctypes.byref(w2), ctypes.byref(ground), ctypes.byref(e), ctypes.byref(info))
        self.assertEqual((info.x, info.y, info.hp), (5.0, 320.0, 33))   # z 0 -> the player height 180
        self.assertEqual(self.lib.mu_hn_add_info(ctypes.byref(w), ctypes.byref(hero), ctypes.byref(e), None), 0)
        npc = character(key=8, kind=4, name='Smith')
        self.assertEqual(self.lib.mu_hn_add_info(ctypes.byref(w), ctypes.byref(npc), ctypes.byref(e), None), 0)
        strong = character(key=9, kind=2, name='Kundun', level=401, hp=1, max_hp=1)
        self.lib.mu_hn_add_info(ctypes.byref(w), ctypes.byref(strong), ctypes.byref(e), ctypes.byref(info))
        self.assertEqual(info.name, b"<font color='#FF3319' size='12'>Kundun</font>")   # above the hero's level
        e.world = 0x8b
        weak = character(key=10, kind=2, name='Spider', level=2, hp=1, max_hp=1)
        self.lib.mu_hn_add_info(ctypes.byref(w), ctypes.byref(weak), ctypes.byref(e), ctypes.byref(info))
        self.assertEqual((info.name, info.is_show), (b'Spider', 0))
        self.assertEqual(vn.entry_from_ctypes(w.entries[[w.entries[i].key for i in range(w.count)].index(10)])['show'], 1)

    def test_update_operations(self):
        w, keep = self.window(), []
        hero = character(key=7, kind=1, name='Nighty', position=(1000.0, 0.0, 0.0))
        mob = character(key=3, kind=2, name='Hound', height=200, position=(2000.0, 0.0, 0.0))
        e = self.env(keep, hero=hero)
        for c in (hero, mob):
            self.lib.mu_hn_add_info(ctypes.byref(w), ctypes.byref(c), ctypes.byref(e), None)
            self.lib.mu_hn_set_mc(ctypes.byref(w), c.key, 1)
        chars = {3: mob, 7: hero}
        look = vn.LOOKUP(lambda _, k: ctypes.addressof(chars[k]) if k in chars else None)
        ops = (vn.Op * 64)()
        n = self.lib.mu_hn_update(ctypes.byref(w), look, ctypes.byref(e), ops, 64)
        self.assertEqual(vn.lib_ops(ops, n), [])          # nothing moved since addInfo
        mob.position[0] = 2100.0
        e.name_option = 0
        w.monster_view = 0
        n = self.lib.mu_hn_update(ctypes.byref(w), look, ctypes.byref(e), ops, 64)
        self.assertEqual(vn.lib_ops(ops, n), [(3, 'info_visible', 0), (3, 'position', (210.0, 300.0)),
                                              (7, 'name_show', 0)])
        op = (vn.Op * 2)()
        self.assertEqual(self.lib.mu_hn_select(ctypes.byref(w), 3, op), 0)    # monster view off: no setTopMovie
        n = self.lib.mu_hn_update(ctypes.byref(w), look, ctypes.byref(e), ops, 64)
        self.assertEqual(vn.lib_ops(ops, n), [(3, 'info_visible', 1)])       # the selection shows it anyway
        self.assertEqual(self.lib.mu_hn_set_hp(ctypes.byref(w), 3, 1, 4, op), 1)
        self.assertEqual(vn.lib_ops(op, 1), [(3, 'set_hp', 25)])
        self.assertEqual(self.lib.mu_hn_remove(ctypes.byref(w), ctypes.byref(mob), op), 1)
        self.assertEqual(vn.lib_ops(op, 1), [(3, 'remove', 2)])
        self.assertEqual(w.count, 1)

    def test_chat_bubble_and_route(self):
        w, keep = self.window(), []
        hero = character(key=7, kind=1, name='Nighty')
        e = self.env(keep, hero=hero)
        self.lib.mu_hn_add_info(ctypes.byref(w), ctypes.byref(hero), ctypes.byref(e), None)
        self.lib.mu_hn_set_mc(ctypes.byref(w), 7, 1)
        arr = (ctypes.POINTER(vn.Character) * 1)(ctypes.pointer(hero))
        op = (vn.Op * 1)()
        self.assertEqual(self.lib.mu_hn_chat_bubble(ctypes.byref(w), arr, 1, b'Nighty', b'hi', 1, op), 1)
        self.assertEqual(vn.lib_ops(op, 1), [(7, 'message', ('Nighty: hi', 40000))])
        self.assertEqual(self.lib.mu_hn_chat_bubble(ctypes.byref(w), arr, 1, b'Other', b'hi', 0, op), 0)
        route = self.lib.mu_hn_chat_route
        route.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32)]
        flag, skip = ctypes.c_int32(), ctypes.c_int32()
        cases = {b'hello': (1, 0, 0), b'#all': (1, 1, 1), b'~party': (5, -1, 1), b'@@ally': (7, -1, 2),
                 b'@guild': (6, -1, 1), b'$gens': (9, -1, 1)}
        for text, want in cases.items():
            t = route(text, 0, ctypes.byref(flag), ctypes.byref(skip))
            self.assertEqual((t, flag.value, skip.value), want, text)
        self.assertEqual(route(b'#all', 1, ctypes.byref(flag), ctypes.byref(skip)), 8)

    def test_monster_kind(self):
        k = self.lib.mu_hn_monster_kind
        self.assertEqual([k(c) for c in (0, 3, 99, 100, 110, 111, 150, 200, 201, 240, 259, 260, 368, 451, 492, 873)],
                         [2, 2, 2, 8, 8, 2, 2, 2, 4, 4, 4, 2, 4, 128, 4, 4])


@unittest.skipUnless(PRIVATE and TEXT.exists() and DATA.exists(), 'private: MU_RECOVERY_INTEGRATION=1 and the pinned captures')
class Private(unittest.TestCase):
    def test_unicorn_comparison(self):
        try:
            import unicorn  # noqa: F401
        except ImportError:
            self.skipTest('unicorn is not installed')
        r = subprocess.run([sys.executable, str(ROOT/'scripts/validate_names.py'), '--cases', '20', '--negative', '100'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-3000:])


if __name__ == '__main__':
    unittest.main()
