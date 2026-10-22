"""Portable checks of reconstructed/skill (NATIVE-SKILL-001): independent Python statements of the client
routines over synthetic data (no client bytes).  The client comparison is scripts/validate_skill.py.
"""
import ctypes
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_skill as vs  # noqa: E402  (the ctypes mirrors; Unicorn is not needed for them)

EXT = 'dylib' if sys.platform == 'darwin' else 'so'
LIB = HERE/f'libclientskill.{EXT}'


def build():
    subprocess.run(['make', '-s', '-C', str(HERE)], check=True)
    return vs.SkillNative(None, LIB)


def lex_int(text):
    """boost::lexical_cast<int>: optional sign, decimal digits, int range."""
    if not text:
        return None
    body = text[1:] if text[:1] in (b'+', b'-') else text
    if not body or not body.isdigit() or not all(48 <= c <= 57 for c in body):
        return None
    value = int(body)
    if text[:1] == b'-':
        return -value if value <= 2**31 else None
    return value if value < 2**31 else None


def lex_bool(text):
    """boost::lexical_cast<bool>: ends in 0/1, an optional + (or - before 0), then zeros."""
    if not text or text[-1:] not in (b'0', b'1'):
        return None
    value = text[-1:] == b'1'
    rest = text[:-1]
    if rest[:1] == b'+' or (rest[:1] == b'-' and not value):
        rest = rest[1:]
    return int(value) if all(c == 48 for c in rest) else None


class Lexical(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nat = build()

    def test_int_and_bool(self):
        rng = random.Random(3)
        cases = [b'0', b'-0', b'+7', b'007', b' 1', b'1 ', b'', b'-', b'2147483647', b'2147483648', b'-2147483648',
                 b'-2147483649', b'0x10', b'4294967296', b'00000000000000000000042']
        cases += [str(rng.randint(-2**33, 2**33)).encode() for _ in range(300)]
        cases += [bytes(rng.choice(b'01+- 9a') for _ in range(rng.randint(0, 6))) for _ in range(300)]
        for text in cases:
            got = self.nat.lexical('int', text)
            want = lex_int(text)
            self.assertEqual(got, (0, None) if want is None else (1, want), text)
            got = self.nat.lexical('bool', text)
            want = lex_bool(text)
            self.assertEqual(got, (0, None) if want is None else (1, want), text)


def row(index=7, name=b'"Fire Ball"', **over):
    cols = [str(index).encode(), name] + [str(10 + i).encode() for i in range(2, 61)]
    cols[45] = b'1'
    for k, v in over.items():
        cols[int(k[1:])] = v
    return cols


class RowParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nat = build()

    def test_column_order(self):
        status, r = self.nat.parse(row())
        self.assertEqual(status, 1)
        rec = vs.native_record(r)
        self.assertEqual(rec['index'], 7)
        self.assertEqual(rec['name'], b'Fire Ball')
        # columns 2..17 in the parser's order: energy (8) precedes strength (9)
        self.assertEqual([rec[k] for k in ('level', 'damage', 'mana', 'ag', 'distance', 'delay', 'req_energy',
                                           'req_strength', 'req_dexterity', 'req_command', 'req_vitality',
                                           'mastery', 'x54', 'use_type', 'brand', 'x60')], list(range(12, 28)))
        self.assertEqual(rec['rank'], {0x80: 28, 0x40: 29, 0x20: 30})
        self.assertEqual(rec['classes'], {i: 31 + i for i in range(16)})
        self.assertEqual((rec['icon'], rec['type'], rec['x94'], rec['weapon']), (53, 54, 1, 63))
        self.assertEqual(rec['pairs'], [(64, 65), (66, 67)])
        self.assertEqual((rec['imprint'], rec['xc8'], rec['damage_type']), (68, 1, 70))

    def test_pairs_quotes_and_rejects(self):
        _, r = self.nat.parse(row(c54=b'-1', c55=b'not read'))
        self.assertEqual(vs.native_record(r)['pairs'], [(66, 67)])        # the second column is skipped
        for name, want in ((b'Plain', b'null'), (b'"A"b"', b'A"b'), (b'x"y"', b'null'), (b'""', b''), (b'"', b'null')):
            _, r = self.nat.parse(row(name=name))
            self.assertEqual(r.name, want, name)
        self.assertEqual(self.nat.parse(row()[:51])[0], 0)                  # fewer than 52 columns
        self.assertEqual(self.nat.parse(row()[:55])[0], -2)                 # 52..60: the client reads past the row
        self.assertEqual(self.nat.parse(row(c9=b'1.5'))[0], -1)             # a lexical_cast failure
        self.assertEqual(self.nat.parse(row(c45=b'2'))[0], -1)
        self.assertEqual(self.nat.parse(row() + [b'x'])[0], 1)              # extra columns are ignored

    def test_table_keeps_the_first_record(self):
        t = vs.TableC()
        for name in (b'"First"', b'"Second"'):
            _, r = self.nat.parse(row(index=9, name=name))
            self.nat.lib.mu_skill_table_add(ctypes.byref(t), ctypes.byref(r))
        rec = ctypes.cast(t.records, ctypes.POINTER(vs.RecordC))[0]
        self.assertEqual((t.count, rec.name), (1, b'First'))


def record(index, **fields):
    r = vs.RecordC()
    r.index = index
    for k, v in fields.items():
        setattr(r, k, v)
    return r


class Use(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nat = build()
        cls.records = [record(1, req_strength=100, req_energy=50, delay=3000, damage_type=2),
                       record(2, req_dexterity=40, use_type=3, icon=455), record(0xdd, delay=1000),
                       record(0xde, delay=1000), record(0x7a, use_type=0, icon=300)]
        cls.table = cls.nat.table(cls.records)

    def env(self, cls_index=0, **case):
        c = vs.Case(random.Random(1), [r.index for r in self.records])
        c.class_index = cls_index
        for k, v in case.items():
            setattr(c, k, v)
        return vs.make_env(self.table, c), c

    def test_stats(self):
        for cls_index, s, e, want in ((0, 100, 50, 1), (0, 99, 50, 0), (0, 100, 49, 0), (1, 99, 50, 1), (1, 99, 49, 0)):
            env, _ = self.env(cls_index)
            h = vs.HeroC(class_index=cls_index, strength=s, energy=e)
            self.assertEqual(self.nat.lib.mu_skill_stats_ok(env, h, 1), want, (cls_index, s, e))
        env, _ = self.env()
        self.assertEqual(self.nat.lib.mu_skill_stats_ok(env, vs.HeroC(), 99), 0)    # absent: the default record

    def test_mana_and_potion(self):
        env, case = self.env()
        h = vs.HeroC(mana=10, ag=5)
        p = ctypes.c_int()
        self.assertEqual(self.nat.lib.mu_skill_mana_ok(env, h, 5, 5, 10, 5, ctypes.byref(p)), 1)
        self.assertEqual((self.nat.lib.mu_skill_mana_ok(env, h, 5, 5, 11, 5, ctypes.byref(p)), p.value), (0, 1))
        case.buffs[0].add(0x126)                                                   # AG + 2
        self.assertEqual((self.nat.lib.mu_skill_mana_ok(env, h, 5, 5, 10, 4, ctypes.byref(p)), p.value), (0, 0))
        self.assertEqual(self.nat.lib.mu_skill_mana_ok(env, h, 0x28, 0x28, 10, 99, ctypes.byref(p)), 1)   # AG 0

    def test_delay_start_pair_ready_tick(self):
        env, case = self.env(base={0xdd: 0xdd, 0xde: 0xde})
        h = vs.HeroC(count=3)
        h.skills[0], h.skills[1], h.skills[2] = 0xdd, 0xde, 1
        out = (vs.I32*4)()
        n = self.nat.lib.mu_skill_delay_start(env, h, 0xdd, ctypes.byref(out))
        self.assertEqual((n, list(out)[:4], list(h.timers)[:3]), (2, [0xdd, 1000, 0xde, 1000], [1000, 1000, 0]))
        self.assertEqual((self.nat.lib.mu_skill_ready(env, h, 0), self.nat.lib.mu_skill_ready(env, h, 2)), (0, 1))
        self.nat.lib.mu_skill_delay_tick(h, 600)
        self.nat.lib.mu_skill_delay_tick(h, 600)
        self.assertEqual(list(h.timers)[:3], [0, 0, 0])
        case.tree_node[1] = 1
        case.tree_values[(1, 0x3fa)] = 2500
        h.timers[2] = 0
        n = self.nat.lib.mu_skill_delay_start(env, h, 1, ctypes.byref(out))
        self.assertEqual((n, h.timers[2]), (1, 500))                                # the skill tree's 0x3fa
        case.tree_values[(1, 0x3fb)] = 1
        h.timers[2] = 0
        self.assertEqual(self.nat.lib.mu_skill_delay_start(env, h, 1, ctypes.byref(out)), 0)

    def test_feed_and_select(self):
        env, case = self.env()
        h = vs.HeroC(count=2, elemental=3)
        h.skills[0], h.skills[1] = 1, 2
        hot = vs.HotkeysC(selected=2)
        hot.slots[4], hot.slots[6] = 1, 2
        bar = vs.BarC()
        usable = vs.USABLE_FN(lambda u, s: int(s == 1))
        buf = ctypes.create_string_buffer(4096)
        self.assertEqual(self.nat.lib.mu_skill_bar_feed(env, bar, h, hot, usable, None, buf, 4096), 1)
        msg = json.loads(buf.value)
        self.assertEqual((msg['Elemental'], msg['SelectSlot'], msg['SelectSkill'], msg['SelectUseSkill']),
                         (3, 6, 2, False))
        self.assertEqual(msg['arrSlots'][4], {'slot': 4, 'skill': 1, 'isUse': True, 'damageType': 2})
        self.assertEqual(self.nat.lib.mu_skill_bar_feed(env, bar, h, hot, usable, None, buf, 4096), 0)   # unchanged

    def test_icon(self):
        env, case = self.env()
        icon = vs.IconC()
        self.assertEqual(self.nat.lib.mu_skill_icon_of(env, 1, 1, 1, 20.0, 28.0, ctypes.byref(icon)), 1)
        self.assertEqual(icon.bitmap, 0x7c40)
        self.nat.lib.mu_skill_icon_of(env, 1, 0, 1, 20.0, 28.0, ctypes.byref(icon))
        self.assertEqual(icon.bitmap, 0x7c43)                                      # not learned: the grey sheet
        self.nat.lib.mu_skill_icon_of(env, 2, 2, 1, 20.0, 28.0, ctypes.byref(icon))
        self.assertEqual((icon.bitmap, round(icon.u * 512 / 20), round(icon.v * 512 / 28)), (0x7e19, 5, 0))   # 455 = 450 + 5
        self.nat.lib.mu_skill_icon_of(env, 0x7a, 0x7a, 1, 20.0, 28.0, ctypes.byref(icon))
        self.assertEqual((round(icon.u * 512 / 20), round(icon.v * 512 / 28)), (0x7a % 25, 0x7a // 25))   # skill as cell


class Tooltip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nat = build()
        cls.records = [record(4, req_energy=40, mana=3, mastery=1, imprint=120, type=0, delay=1500),
                       record(5, type=1)]
        cls.table = cls.nat.table(cls.records)

    def test_lines(self):
        texts = {0x18c4: b'Energy %d', 0x18c6: b' / ', 0x12b0: b'Mana %d', 0x12b1: b'AG %d', 0x12b2: b'Range %d',
                 0x12b3: b'Cooldown: %.1f sec.', 0x12b4: b'Damage %d', 0x12b6: b'(Bonus %d%%)', 0xe99: b'(Fire)'}
        keep = {k: ctypes.c_char_p(v) for k, v in texts.items()}
        tip = vs.TipTextC(skill=4, name=b'Fire Ball', name_color=3, condition1=0, text1=b'Burns#the target.',
                          color1=0, condition2=2, text2=b'Learn it.', color2=2, value_a=-1, value_b=-1)
        c = vs.Case(random.Random(1), [4, 5])
        env = vs.make_env(self.table, c)
        cbs = [vs.TEXT_FN(lambda u, i: ctypes.cast(keep[i], ctypes.c_void_p).value if i in keep else None),
               vs.TIP_FN(lambda u, k: ctypes.addressof(tip) if k == 4 else None),
               vs.INFO_FN(lambda u, s, m, d, a: (m.__setitem__(0, 3), d.__setitem__(0, 6), a.__setitem__(0, 0))),
               vs.HAS_FN(), vs.HAS_FN(), vs.FLOAT1_FN(), vs.FORMULA_FN(),
               vs.MEASURE_FN(lambda u, t, k: 6 * k)]
        tenv = vs.TipEnvC(ctypes.pointer(env), None, *cbs, 1.0)
        inp = vs.TipInputC(base=4, learned=0, energy=30, skill_damage=8, weapon_index=-1)
        out = vs.TipC()
        self.assertEqual(self.nat.lib.mu_skill_tooltip_build(ctypes.byref(tenv), ctypes.byref(inp), ctypes.byref(out)), 1)
        lines = [bytes(out.lines[i]).split(b'\0')[0] for i in range(out.count)]
        self.assertEqual(lines, [b'Fire Ball', b'Energy 40', b'  ', b'Mana 3', b'Range 6 / Cooldown: 1.5 sec.',
                                 b'Damage 8 (Bonus 120%)', b'(Fire)', b'\n', b' Burns', b' the target.', b'\n',
                                 b' Learn it.'])
        self.assertEqual([out.color[i] for i in (0, 1, 3)], [3, 2, 1])            # energy 30 < 40: red
        title, body = ctypes.create_string_buffer(4096), ctypes.create_string_buffer(16384)
        self.nat.lib.mu_skill_tooltip_html(ctypes.byref(out), title, 4096, body, 16384)
        self.assertEqual(title.value, b"<font color='#FFCC19'>Fire Ball</font><br>")
        self.assertTrue(body.value.startswith(b"<font color='#FF3319'>Energy 40</font><br>"))
        self.assertIn(b'<BR>', body.value)

    def test_wrap(self):
        cbs = vs.TipEnvC(None, None, vs.TEXT_FN(), vs.TIP_FN(), vs.INFO_FN(), vs.HAS_FN(), vs.HAS_FN(),
                         vs.FLOAT1_FN(), vs.FORMULA_FN(), vs.MEASURE_FN(lambda u, t, k: 10 * k), 1.0)
        buf = ctypes.create_string_buffer(11*256)
        n = self.nat.lib.mu_skill_wrap(ctypes.byref(cbs), b'abcdefghijklmnopqrstuvwxyz#xy', 100, buf, 10, 256)
        lines = [buf.raw[256*i:256*(i+1)].split(b'\0')[0] for i in range(n)]
        self.assertEqual(lines, [b' abcdefgh', b'ijklmnopq', b'rstuvwxyz', b' xy'])     # width < 100 per line

    def test_format(self):
        out = ctypes.create_string_buffer(64)
        self.nat.lib.mu_skill_format.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_int,
                                                 vs.I32, ctypes.c_double, ctypes.c_char_p]
        self.nat.lib.mu_skill_format(out, 64, b'Rate %d%% / %5.1f', ord('i'), 42, 0.0, None)
        self.assertEqual(out.value, b'Rate 42% /   0.0')


if __name__ == '__main__':
    unittest.main()
