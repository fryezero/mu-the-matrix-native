"""Lang.mpr tables read from the client (NATIVE-LANG-001) checks.

Portable (synthetic data only): a synthetic langread snapshot (the
script-table manager 0x06fbaa60 with MSVC std::map trees, inline and heap
std::strings, EnchantEffect vectors) goes through
scripts/live_lang_to_plain.py; `mu-lang` answers from the plaintext as the
client's consumers would (GlobalText, GetSkillInformation's master-skill
mana/AG rule against an independent float32 statement, map names through the
generated world table, EnchantEffect first/mesh lookups and the default
colour, gates, moves, NPC names); malformed snapshots and lines are refused;
and the consumers use the tables: the GFx layer's labels (menu, inventory and
character InitText, chat InitData) through a GlobalText provider, the login
overlay strings, the character-select tip, the EnchantEffect colour in the
world render (equal to the same colour given as a parameter) and the skill
distance and log line in combat.  Without MU_LANG_DIR every consumer keeps
its placeholder.
Private (MU_RECOVERY_INTEGRATION=1, MU_LANG_DIR with the local plaintext):
table sizes and invariants; with MU_LANG_SNAPSHOT, Unicorn and the pinned
captures, scripts/validate_lang.py runs the client's consumers over the live
snapshot and compares them with the native module.
"""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT/'scripts'))
import live_lang_to_plain as plain  # noqa: E402

LANG = NATIVE/'build/mu-lang'
RENDER = NATIVE/'build/mu-render'
CONVERT = ROOT/'scripts/live_lang_to_plain.py'
CC = shutil.which(os.environ.get('CC', 'cc')) or shutil.which('clang')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
LANG_DIR = os.environ.get('MU_LANG_DIR', '')
SNAPSHOT = os.environ.get('MU_LANG_SNAPSHOT', '')


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


# --------------------------------------------------------------------------- synthetic snapshot

class Memory:
    """Blocks of a synthetic client address space, written as a MULANGV1 snapshot."""

    def __init__(self):
        self.blocks = {}
        self.manager = bytearray(0x2320)
        self.next = 0x13000000

    def alloc(self, data, align=8):
        address = self.next
        self.blocks[address] = bytes(data)
        self.next = (address + len(data) + 0x20 + align - 1) & ~(align - 1)
        return address

    def string(self, raw):
        """24-byte MSVC std::string for raw (buffer inline below 16 bytes)."""
        raw = bytes(raw)
        if len(raw) < 16:
            return raw.ljust(16, b'\0') + struct.pack('<II', len(raw), 15)
        pointer = self.alloc(raw + b'\0')
        return struct.pack('<I', pointer) + bytes(12) + struct.pack('<II', len(raw), len(raw))

    def map(self, container, items):
        """std::map<int, T> at container (head, size); items: key -> value bytes (T)."""
        keys = sorted(items)
        head = self.next
        self.next += 0x40
        nodes = {k: self.next + i*0x200 for i, k in enumerate(keys)}
        self.next += 0x200*len(keys) + 0x40

        def build(lo, hi, parent):
            if lo >= hi:
                return head
            mid = (lo + hi)//2
            k = keys[mid]
            left, right = build(lo, mid, nodes[k]), build(mid + 1, hi, nodes[k])
            value = items[k]
            self.blocks[nodes[k]] = struct.pack('<IIIBB2xi', left, parent, right, 1, 0, k) + value
            return nodes[k]
        root = build(0, len(keys), head)
        leftmost = nodes[keys[0]] if keys else head
        rightmost = nodes[keys[-1]] if keys else head
        self.blocks[head] = struct.pack('<IIIBB2x', leftmost, root, rightmost, 1, 1)
        offset = container - plain.MANAGER
        struct.pack_into('<II', self.manager, offset, head, len(keys))

    def snapshot(self):
        blocks = dict(self.blocks)
        blocks[plain.MANAGER] = bytes(self.manager)
        out = bytearray(b'MULANGV1' + struct.pack('<I', len(blocks)))
        for address, data in blocks.items():
            out += struct.pack('<II', address, len(data)) + data
        return bytes(out)


TEXTS = {
    0: b'Gulim', 30: b'Synthetic Lorencia', 454: b'Native Title / ', 455: b' Synthetic copyright line',
    456: b'Ver %s', 0x6ae: b'Synthetic tip one', 0x6cb: b'Synthetic tip two', 0x6cc: b'Synthetic tip three',
    100: b'Tab\there\nnew line \\ back \x95 end', 6336: b'Storm Isle', 0xd5d: b'Item Shop', 0xd5c: b'X',
    3453: b'Bag', 3406: b'Everyone', 4853: b'Stats!', 200: b'A string longer than fifteen bytes, on the heap',
}


def skill_record(m, index, name, *, level=0, damage=0, mana=0, ag=0, distance=0, delay=0, mastery=0, use_type=0,
                 brand=0, master_bonus=0, icon=0, type_=0, skip=0):
    r = bytearray(0xd0)
    r[0] = skip
    struct.pack_into('<i', r, 4, index)
    r[8:0x20] = m.string(name)
    struct.pack_into('<4i', r, 0x20, level, damage, mana, ag)
    struct.pack_into('<2i', r, 0x34, distance, delay)
    struct.pack_into('<i', r, 0x50, mastery)
    struct.pack_into('<2i', r, 0x58, use_type, brand)
    r[0x7c] = master_bonus
    struct.pack_into('<2i', r, 0x8c, icon, type_)
    return bytes(r)


SKILLS = (
    dict(index=1, name=b'Poison', level=30, damage=12, mana=42, distance=6, icon=1, mastery=6),
    dict(index=4, name=b'Fire Ball', mana=3, distance=1, icon=4),
    dict(index=9, name=b'Hidden Skill', mana=10, distance=6, skip=1),
    dict(index=310, name=b'Master Burst', mana=100, ag=50, distance=4, use_type=3, brand=0, master_bonus=20,
         icon=310),
    dict(index=311, name=b'Master Aura', mana=77, ag=33, distance=2, use_type=4, brand=0, master_bonus=9),
    dict(index=312, name=b'Branded', mana=61, ag=17, distance=3, use_type=3, brand=7, master_bonus=30),
)
ENCHANT = {14: [(-1, 0.0, 0.5, 1.0)], 0x1000: [(2, 1.0, 0.0, 0.0), (-1, 0.0, 1.0, 0.0)], 20: [],
           0x0c00: [(-1, 0.25, 0.75, 0.125)]}
ENCHANT_DEFAULT = (1.0, 0.5, 0.0)

# NATIVE-LANG-002 tables: BuffEffect (index, group, item group/index, name, type, x2c, x30, lines, value kind)
BUFFS = {1: (1, 255, 255, b'Buff One', 0, 1, 1, [b'Line one.'], 0),
         11: (11, 255, 255, b'Buff Eleven', 0, 0, 1, [b'Short +8', b'A line longer than fifteen bytes'], 0),
         29: (60, 13, 43, b'Cash Buff', 2, 0, 1, [b'Gain 50%%'], 0),
         35: (0xf6, 14, 46, b'Group F6', 0, 0, 1, [], 0),
         55: (55, 255, 255, b'Debuff', 1, 1, 1, [b'Drops.'], 0),
         320: (299, 255, 255, b'Valued', 0, 1, 1, [b'Value %d here.'], 1)}
# CharacterInfoSetup rows: id -> (colour, label, group, class flags, type, sort, value colour, prefix, suffix, button)
CHARINFO = {1: (20, b'Row A', 1, [1]*16, 1, 0, 3, b'', b'', 0),
            2: (20, b'Row B', 1, [1]*16, 1, 1, 3, b'', b'', 0),
            8: (20, b'Stat One', 6, [1]*16, 2, 0, 3, b'', b'', 1),
            9: (12, b'* Class One Row', 7, [0, 1] + [0]*14, 2, 1, 12, b'', b'', 0),
            10: (20, b'* Row C', 10, [1]*16, 2, 2, 3, b'', b'', 0),
            13: (20, b'Stat Two', 6, [1]*16, 2, 1, 3, b'', b'', 1),
            43: (20, b'* Rate Row', 9, [1]*16, 3, 0, 3, b'', b'%', 0),
            80: (20, b'Tab Four Row', 11, [1]*16, 4, 0, 3, b'', b'', 0)}
SOULCONV = (7628, 7630)


def synthetic_snapshot():
    m = Memory()
    m.map(plain.TEXT + 0x38, {k: struct.pack('<Bxxxi', 0, k) + m.string(v) for k, v in TEXTS.items()})
    m.map(plain.SKILL + 0x108, {s['index']: skill_record(m, **{('type_' if k == 'type' else k): v
                                                                for k, v in s.items()}) for s in SKILLS})
    gate = lambda index, world, x, y: struct.pack('<Bxxx12i', 0, index, 1, world, x, y, x + 2, y + 2, 0, 0, 10, -1, 0)
    m.map(plain.GATE + 0x38, {17: gate(17, 0, 133, 118), 900: gate(900, 79, 50, 60)})
    move = struct.pack('<i', 4) + m.string(b'Lorencia') + m.string(b'Lorencia') + \
        struct.pack('<8i', 2000, 10, -1, 17, 3, 17, 7, 0)
    m.map(plain.MOVEREQ + 0x38, {2: move})
    npc = lambda index, name, a: struct.pack('<i', index) + m.string(name) + struct.pack('<iiB3x', a, 0, 1)
    m.map(plain.NPCNAME + 0x38, {0: npc(0, b'Bull Fighter', 210), 249: npc(249, b'Guard', 0)})
    m.map(plain.DIALOG + 0x38, {1: struct.pack('<i', 1) + m.string(b'Welcome, traveller. ' * 3)})
    items = {}
    for code, entries in ENCHANT.items():
        data = b''.join(struct.pack('<i3f', *e) for e in entries)
        begin = m.alloc(data) if data else 0
        items[code] = struct.pack('<III', begin, begin + len(data), begin + len(data))
    m.map(plain.ENCHANT + 0x38, items)
    struct.pack_into('<3f', m.manager, plain.ENCHANT - plain.MANAGER + 0x50, *ENCHANT_DEFAULT)

    def buff(index, group, item_group, item_index, name, type_, x2c, x30, lines, kind):
        data = b''.join(m.string(line) for line in lines)
        begin = m.alloc(data) if data else 0
        return (struct.pack('<4i', index, group, item_group, item_index) + m.string(name) +
                struct.pack('<3i', type_, x2c, x30) + struct.pack('<3I', begin, begin + len(data), begin + len(data)) +
                struct.pack('<i', kind))
    m.map(plain.BUFF + 0x38, {k: buff(k, *v) for k, v in BUFFS.items()})
    m.manager[plain.BUFF - plain.MANAGER + 0x40:plain.BUFF - plain.MANAGER + 0x84] = buff(
        0, 0, -1, -1, b'null', -1, -1, -1, [], 0)

    def row(key, colour, label, group, classes, type_, sort, value_colour, prefix, suffix, button):
        flags = struct.pack(f'<{len(classes)}i', *classes)
        begin = m.alloc(flags)
        r = bytearray(0xa4)
        struct.pack_into('<2i', r, 0, key, colour)
        r[8:0x20] = m.string(label)
        struct.pack_into('<i3I', r, 0x20, group, begin, begin + len(flags), begin + len(flags))
        struct.pack_into('<3i', r, 0x30, type_, sort, value_colour)
        r[0x3c:0x54] = m.string(prefix)
        r[0x54:0x6c] = m.string(suffix)
        r[0x70:0x88] = m.string(b'')
        r[0x88:0xa0] = m.string(b'')
        struct.pack_into('<i', r, 0xa0, button)
        return bytes(r)
    m.map(plain.CHARINFO + 0x38, {k: row(k, *v) for k, v in CHARINFO.items()})
    default = bytearray(row(0, 0, b'null', 0, [], 0, 0, 0, b'null', b'null', 0))
    struct.pack_into('<3I', default, 0x24, 0, 0, 0)
    m.manager[plain.CHARINFO - plain.MANAGER + 0x44:plain.CHARINFO - plain.MANAGER + 0x44 + 0xa4] = default
    m.map(plain.SOULCONV + 0x44, {c: struct.pack('<3i', i + 1, c, 1) for i, c in enumerate(SOULCONV)})
    m.map(plain.SKILLREQ + 0x54, {243: struct.pack('<7i', 0, 243, 15, 49, 242, 847, 10)})
    return m.snapshot()


def client_scaled(value, level):
    """GetSkillInformation's master-skill factor: float(value) * (float)(level*0.005+1.0), rounded
    half away from zero through float (0x00d01e8c)."""
    x = f32(f32(value) * f32(level*0.005 + 1.0))
    return int(f32(x + 0.5)) if x > 0 else int(f32(x - 0.5))


def write_lang(directory):
    snap = Path(directory)/'snap.bin'
    snap.write_bytes(synthetic_snapshot())
    out = Path(directory)/'lang'
    subprocess.run([sys.executable, str(CONVERT), str(snap), '--out', str(out)], check=True, capture_output=True)
    return out


def lang(directory, *args, check=True):
    result = subprocess.run([str(LANG), str(directory), *[str(a) for a in args]], capture_output=True)
    if check and result.returncode:
        raise AssertionError(f'mu-lang {args} failed: {result.stderr!r}')
    return result


def lang_json(directory, *args):
    return json.loads(lang(directory, *args).stdout)


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.lang = write_lang(cls.dir)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class ConverterAndLoader(Build):
    def test_files_and_counts(self):
        names = sorted(p.name for p in self.lang.iterdir())
        self.assertEqual(names, ['buffs.tsv', 'charinfo.tsv', 'dialog.tsv', 'enchant.tsv', 'gates.tsv', 'globaltext.txt',
                                 'guidequest.tsv', 'mapnames.tsv', 'moves.tsv', 'npcnames.tsv', 'skillreq.tsv', 'skills.tsv',
                                 'skills_ext.tsv', 'soulconv.tsv'])   # skills_ext.tsv: NATIVE-SKILL-001
        self.assertEqual(lang_json(self.lang, 'summary'),
                         {'text': len(TEXTS), 'skills': len(SKILLS), 'gates': 2, 'moves': 1, 'npcs': 2, 'dialog': 1,
                          'enchant_codes': len(ENCHANT), 'enchant_entries': 4, 'enchant_default': 1,
                          'buffs': len(BUFFS), 'charinfo': len(CHARINFO), 'skillreq': 1, 'soulconv': len(SOULCONV),
                          'questtext': 0})
        for path in self.lang.iterdir():
            self.assertIn('never commit', path.read_text().split('\n')[1])

    def test_globaltext_bytes_round_trip(self):
        for key, raw in TEXTS.items():
            self.assertEqual(lang(self.lang, 'text', key).stdout, raw + b'\n', key)
        self.assertEqual(lang(self.lang, 'text', 101, check=False).returncode, 1)
        line = next(l for l in (self.lang/'globaltext.txt').read_text().splitlines() if l.startswith('100\t'))
        self.assertEqual(line, '100\tTab\\there\\nnew line \\\\ back \\x95 end')
        self.assertEqual(plain.unescape(line.split('\t', 1)[1]), TEXTS[100])

    def test_skill_information_follows_the_client_rule(self):
        for spec in SKILLS:
            for master in (0, 1, 7, 33):
                got = lang_json(self.lang, 'skill', spec['index'], master)
                index, mana, ag = spec['index'], spec.get('mana', 0), spec.get('ag', 0)
                if 300 <= index <= 929:
                    level = spec['master_bonus'] if spec['brand'] == 0 and master == 0 else master
                    mana = client_scaled(mana, level)
                    if not (spec['use_type'] == 4 and spec['brand'] == 0):
                        ag = client_scaled(ag, master)
                self.assertEqual((got['name'], got['mana'], got['ag'], got['distance']),
                                 (spec['name'].decode(), mana, ag, spec['distance']), (index, master))
        self.assertEqual(lang_json(self.lang, 'skill', 9)['skip'], 1)
        self.assertEqual(lang(self.lang, 'skill', 5, check=False).returncode, 1)

    def test_map_names_through_the_world_table(self):
        self.assertEqual(lang_json(self.lang, 'map', 141), {'world': 141, 'globaltext': 6336, 'name': 'Storm Isle'})
        self.assertEqual(lang_json(self.lang, 'map', 0)['name'], 'Synthetic Lorencia')   # default: 30 + world
        self.assertEqual(lang_json(self.lang, 'map', 115), {'world': 115, 'globaltext': -1, 'name': None})
        self.assertIsNone(lang_json(self.lang, 'map', 200)['name'])                      # GlobalText 230 absent
        rows = [l.split('\t') for l in (self.lang/'mapnames.tsv').read_text().splitlines() if not l.startswith('#')]
        self.assertIn(['141', '6336', 'Storm Isle'], rows)

    def test_enchant_lookups(self):
        def rgb(*args):
            return lang_json(self.lang, 'enchant', *args)['rgb']
        self.assertEqual(rgb(0x1000), [1, 0, 0])            # 0x010ffd7a: the first entry
        self.assertEqual(rgb(0x1000, 2), [1, 0, 0])         # 0x010ffddb: mesh 2 matches entry 0
        self.assertEqual(rgb(0x1000, 5), [0, 1, 0])         # entry 1 has mesh -1
        self.assertEqual(rgb(14, 3), [0, 0.5, 1])
        self.assertEqual(rgb(99), list(ENCHANT_DEFAULT))    # absent code: the table colour +0x50
        self.assertEqual(rgb(99, 1), list(ENCHANT_DEFAULT))
        self.assertEqual(rgb(20), list(ENCHANT_DEFAULT))    # empty vector
        self.assertEqual(lang_json(self.lang, 'enchant', 0x1000)['entries'], 2)

    def test_gates_moves_npcs_dialog(self):
        self.assertEqual(lang_json(self.lang, 'move', 2),
                         {'index': 2, 'name': 'Lorencia', 'server_name': 'Lorencia', 'zen': 2000, 'min_level': 10,
                          'max_level': -1, 'gate': 17, 'world': 0})
        gate = lang_json(self.lang, 'gate', 900)
        self.assertEqual((gate['world'], gate['x1'], gate['y2'], gate['min_level']), (79, 50, 62, 10))
        self.assertEqual(lang_json(self.lang, 'npc', 0), {'index': 0, 'name': 'Bull Fighter', 'x1c': 210, 'x20': 0,
                                                          'x24': 1})
        self.assertEqual(lang(self.lang, 'dialog', 1).stdout.decode().strip(), ('Welcome, traveller. ' * 3).strip())

    def test_malformed_snapshots_are_refused(self):
        good = synthetic_snapshot()
        bad = {'magic': b'MULANGV0' + good[8:], 'truncated': good[:len(good)//2]}
        # a map whose stored size disagrees with its tree
        blocks = bytearray(good)
        manager_at = good.index(struct.pack('<II', plain.MANAGER, 0x2320)) + 8
        offset = manager_at + plain.TEXT + 0x38 - plain.MANAGER + 4
        struct.pack_into('<I', blocks, offset, len(TEXTS) + 1)
        bad['size'] = bytes(blocks)
        for name, data in bad.items():
            path = self.dir/f'bad-{name}.bin'
            path.write_bytes(data)
            r = subprocess.run([sys.executable, str(CONVERT), str(path), '--out', str(self.dir/f'out-{name}')],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, name)
            self.assertIn('live_lang_to_plain:', r.stderr)

    def test_loader_skips_bad_lines_and_needs_a_table(self):
        d = self.dir/'partial'
        d.mkdir(exist_ok=True)
        (d/'globaltext.txt').write_text('# header\n7\tseven\nx\tnot a number\n8 no tab\n9\tnine\\x41\n')
        self.assertEqual(lang_json(d, 'summary')['text'], 2)
        self.assertEqual(lang(d, 'text', 9).stdout, b'nineA\n')
        empty = self.dir/'empty'
        empty.mkdir(exist_ok=True)
        r = lang(empty, 'summary', check=False)
        self.assertEqual(r.returncode, 1)


# --------------------------------------------------------------------------- consumers

def build_layer_host(tmp):
    host = tmp/'gfx-layer-host'
    lib = tmp/('libmugfx_stub.dylib' if sys.platform == 'darwin' else 'libmugfx_stub.so')
    hud = ROOT/'reconstructed/hud'
    subprocess.run([CC, '-std=c11', '-O1', '-shared', '-fPIC', '-o', str(lib), str(HERE/'gfx_stub_mugfx.c')], check=True)
    subprocess.run([CC, '-std=c11', '-O1', '-Wall', '-Wextra', '-DMU_GFX_NO_GL', '-I', str(NATIVE/'gfx'), '-I', str(hud),
                    str(HERE/'gfx_layer_host.c'), str(NATIVE/'gfx/mu_gfx_layer.c'), str(hud/'inv_grid.c'),
                    str(hud/'item_slots.c'), str(hud/'tooltip_html.c'), '-lm'] +
                   ([] if sys.platform == 'darwin' else ['-ldl']) + ['-o', str(host)], check=True)
    movies = tmp/'movies'
    movies.mkdir(exist_ok=True)
    for name in ('base', 'ImageData', 'Tooltip', 'Popups', 'main', 'ItemDurability', 'Chat', 'AlarmFrame', 'topmenu',
                 'bufflist', 'hudPlayerName', 'hudMap', 'hudNotice', 'InventoryFrame', 'InfoPopup',
                 'CharacterInfoFrame'):
        (movies/f'{name}.swf').write_bytes(b'')
    return host, lib, movies


def layer_invokes(host, lib, movies, log, **env):
    if log.exists():
        log.unlink()
    subprocess.run([str(host), str(movies), str(lib), 'print'], check=True, capture_output=True,
                   env={**os.environ, 'MUGFX_STUB_LOG': str(log), **env})
    out = {}
    for line in log.read_text().splitlines():
        head, _, args = line.partition(' ')
        path, _, rest = args.partition(' ')
        out.setdefault(path.rsplit('.', 1)[-1], json.loads(rest) if rest.startswith('[') else rest)
    return out


@unittest.skipUnless(CC, 'no C compiler')
class GfxLabels(unittest.TestCase):
    def test_labels_come_from_the_text_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            host, lib, movies = build_layer_host(tmp)
            base = layer_invokes(host, lib, movies, tmp/'a.log')
            texts = layer_invokes(host, lib, movies, tmp/'b.log', MU_GFX_HOST_TEXT='1')
        shop = base['InitMenuInfo'][0]['IngameShop']
        self.assertEqual((shop['key'], shop['label']), ('X', 'In-game shop'))      # stand-ins
        shop = texts['InitMenuInfo'][0]['IngameShop']
        self.assertEqual((shop['key'], shop['label']), ('T3420', 'T3421'))        # GlobalText 0xd5c / 0xd5d
        quest = texts['InitMenuInfo'][0]['Quest']['subMenu'][1]
        self.assertEqual((quest['key'], quest['label']), ('CTRL+T', 'T6459'))      # literal key kept
        self.assertEqual(base['InitText'][0]['Title'], 'Inventory')
        self.assertEqual(texts['InitText'][0]['Title'], 'T3453')
        self.assertEqual(texts['InitText'][0]['Bundle'], 'T5823')
        self.assertEqual((base['InitData'][0]['strNormal'], texts['InitData'][0]['strNormal']), ('All', 'T3406'))
        self.assertEqual(texts['InitData'][0]['typeFormatUNION'], 'T1295')


class ConsumerTools(Build):
    def run_tool(self, *args, lang=None):
        env = dict(os.environ)
        env.pop('MU_LANG_DIR', None)
        if lang:
            env['MU_LANG_DIR'] = str(lang)
        return subprocess.run([str(a) for a in args], capture_output=True, text=True, env=env)

    def test_login_overlay_strings(self):
        outs = {}
        for name, lang_dir in (('plain', None), ('lang', self.lang)):
            out = self.dir/f'login-{name}.png'
            r = self.run_tool(RENDER, 'ui', 'login', '--size', '320x240', '--out', out, lang=lang_dir)
            self.assertEqual(r.returncode, 0, r.stderr)
            outs[name] = (r.stdout + r.stderr, out.read_bytes())
        self.assertIn('GlobalText (MU_LANG_DIR)', outs['lang'][0])
        self.assertNotEqual(outs['plain'][1], outs['lang'][1])
        forced = self.dir/'login-forced.png'
        r = self.run_tool(RENDER, 'ui', 'login', '--size', '320x240', '--text454',
                          'Native Title / ', '--text455', ' Synthetic copyright line', '--format456', 'Ver %s',
                          '--out', forced)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(forced.read_bytes(), outs['lang'][1])   # the table strings, as options

    def test_charsel_tip(self):
        from test_native_charsel import write_world94, MARKER
        root = write_world94(self.dir/'charsel-game')
        frames = {}
        for name, extra, lang_dir in (('plain', (), None), ('lang', (), self.lang),
                                      ('option', ('--tip', 'Synthetic tip one'), None)):
            out = self.dir/f'charsel-{name}'
            r = self.run_tool(NATIVE/'build/mu-charsel', '--game-root', root, '--headless', '--marker',
                              f'{MARKER[0]},{MARKER[1]}', '--frames', '1', '--every', '1', '--width', '320',
                              '--height', '200', '--out-dir', out, *extra, lang=lang_dir)
            self.assertEqual(r.returncode, 0, r.stderr)
            frames[name] = sorted(out.glob('*.png'))[-1].read_bytes()
        self.assertNotEqual(frames['plain'], frames['lang'])
        self.assertEqual(frames['lang'], frames['option'])          # random 0 picks GlobalText 0x6ae

    def test_world_render_enchant_colour(self):
        from test_native_character import synthetic_set
        player, raws = synthetic_set(11)
        paths = {}
        for index, raw in raws.items():
            paths[index] = self.dir/f'item{index}.bmd'
            paths[index].write_bytes(raw)
        (self.dir/'player.bmd').write_bytes(player)

        def render(name, *extra, lang_dir=None):
            args = [RENDER, 'character', self.dir/'player.bmd', '--world-render', '--no-textures', '--width', '160',
                    '--height', '120', '--action', '1', '--frame', '0.5', '--part', '2', paths[2],
                    '--item-type', 'armor=0x1ae6', '--item-level', 'all=9', '--out', self.dir/f'{name}.png', *extra]
            r = self.run_tool(*args, lang=lang_dir)
            self.assertEqual(r.returncode, 0, r.stderr)
            return (self.dir/f'{name}.png').read_bytes()
        white = render('white')
        table = render('table', lang_dir=self.lang)                     # code 0x1000: first entry (1, 0, 0)
        param = render('param', '--glow-color', '1,0,0')
        override = render('override', '--glow-color', '1,1,1', lang_dir=self.lang)
        self.assertNotEqual(white, table)
        self.assertEqual(table, param)
        self.assertEqual(override, white)

    def test_combat_skill_distance_and_log(self):
        from test_native_combat import write_combat_world, run as combat_run
        root = write_combat_world(self.dir/'combat-game')
        placement = self.dir/'placement.txt'
        placement.write_text('# demo\nactor 3 126 120 6 label spider\n')
        os.environ.pop('MU_LANG_DIR', None)
        demo = combat_run(root, placement, '--frames', '160', '--combat-script', '2:skill:4:spider')
        os.environ['MU_LANG_DIR'] = str(self.lang)
        try:
            table = combat_run(root, placement, '--frames', '160', '--combat-script', '2:skill:4:spider')
        finally:
            os.environ.pop('MU_LANG_DIR', None)
        self.assertEqual(demo['summary']['skill_table'], 0)
        self.assertEqual(table['summary']['skill_table'], len(SKILLS))
        self.assertIn('skill 4 Fire Ball: mana 3, AG 0, distance 1', table['logs'])

        def first_attack(out):
            return next(f['combat_frame'] for f in out['frames'] if f['attack_time'] == 2)
        self.assertGreater(first_attack(table), first_attack(demo))   # distance 1 tile instead of the demo 6


# --------------------------------------------------------------------------- private

@unittest.skipUnless(PRIVATE and LANG_DIR and Path(LANG_DIR, 'globaltext.txt').exists(),
                     'needs MU_RECOVERY_INTEGRATION=1 and MU_LANG_DIR')
class PrivateTables(unittest.TestCase):
    def test_sizes_and_invariants(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        c = lang_json(LANG_DIR, 'summary')
        self.assertGreater(c['text'], 5000)
        self.assertGreater(c['skills'], 500)
        self.assertGreater(c['enchant_codes'], 1000)
        self.assertEqual(c['enchant_default'], 1)
        for world in (0, 2, 3, 141):
            self.assertTrue(lang_json(LANG_DIR, 'map', world)['name'], world)
        for move in range(1, 5):
            m = lang_json(LANG_DIR, 'move', move)
            self.assertGreaterEqual(m['world'], 0)
        self.assertTrue(lang_json(LANG_DIR, 'skill', 1)['name'])


@unittest.skipUnless(PRIVATE and SNAPSHOT and Path(SNAPSHOT).exists() and CC,
                     'needs MU_RECOVERY_INTEGRATION=1, MU_LANG_SNAPSHOT, Unicorn and the captures')
class PrivateValidator(unittest.TestCase):
    def test_client_consumers_equal_the_native_module(self):
        try:
            import unicorn  # noqa: F401
        except ImportError:
            self.skipTest('needs Unicorn')
        r = subprocess.run([sys.executable, str(ROOT/'scripts/validate_lang.py'), '--snapshot', SNAPSHOT,
                            '--mutations'], capture_output=True, text=True, timeout=3600)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertIn('all cases match', r.stdout)


if __name__ == '__main__':
    unittest.main()
