#!/usr/bin/env python3
"""Run the client's skill packet handlers and the managers they update in Unicorn and compare them with
reconstructed/skill/skill_list.c (NATIVE-SKILL-002).

Same machine as scripts/validate_skill.py (the pinned restored text and second section, the langread snapshot
of the Lang.mpr tables mapped at their addresses).  The C side is libclientskill through ctypes.

Families:

* list: the skill list handler 0x0126176e (opcode 0xA0 sub 0x20: a full list, one skill added (0xFE) or removed
  (0xFF)) over the snapshot's Skill(Kor) records, with random learned lists, CurrentSkill, Skill Imprint (stamp)
  managers and hotkey managers.  The stamp manager (0x01095f5c add, 0x010960a8 remove, 0x010961b0 the imprint
  refresh), the hotkey manager (0x00a07a11 / 0x00a07c8a / 0x00a07ebb / 0x00a08330 / 0x00a081eb / 0x00a079d2)
  and the master manager's table walks (0x00bb1c32, 0x00bb1c10) run for real; read back: the learned list,
  its count, CurrentSkill, every stamp entry, the stamp slots, the hotkeys' selection, learned map and slot map,
  and the boundary calls in order;
* keys: the saved-hotkey packet 0x0126f225 (opcode 0xA0 sub 0x03) up to the end of its skill part (0x0126f2fa:
  the ten keys, Save 0x01096d2a, the CurrentSkill rule 0x01096f37), then the bar rebuild 0x00a08330 the handler
  ends with;
* stamp: the stamp manager's reset 0x01095c77 (0x01095f20: the basic tab built for a class byte 0x01095d30 /
  0x0109630b, or the learned skills forgotten; the special tab 0x01096710) over synthetic Skill(Kor) tables
  with class maps (+0x6c) written at the table object 0x06fbb138, then the imprint refresh 0x010961b0.

Modelled (not client code): import calls stop a case; operator new/delete are the machine's heap; the debug-log
switch 0x0095fbdc answers 0; the GfxMgr and the windows it reaches (0x00c26ad8, 0x00ba7366, 0x00b40380), the
hotkey listener [0x01d22c60] (0x00c5e991, 0x00c5ea96) and the usability check (0x010918c7, 0x01096e55) are
recording stubs answering with case values.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import pins  # noqa: E402
import client_ui_machine as cm  # noqa: E402
import live_lang_to_plain as plain  # noqa: E402
import validate_lang as vl  # noqa: E402
import validate_skill as vs  # noqa: E402
from validate_skill import I32, U8, U16, s32  # noqa: E402

HERO, ATTR, HOTKEYS = vs.HERO, vs.ATTR, vs.HOTKEYS
DUMMY = vl.DUMMY
LISTENER_OBJ = DUMMY + 0x400
STAMP_GET, LIST_RECV, KEYS_RECV, KEYS_STOP, KEYS_REBUILD = 0x0095f861, 0x0126176e, 0x0126f225, 0x0126f2fa, 0x00a08330
STAMP_RESET, STAMP_REFRESH = 0x01095c77, 0x010961b0
SKILL_TABLE = vs.SKILL_TABLE
EV = {'tree_add': 1, 'keys_all': 2, 'keys_add': 3, 'master_add': 4, 'select': 5, 'usable': 6}


# ---- ctypes ------------------------------------------------------------------------------------------

class EntryC(ctypes.Structure):
    _fields_ = [('base', I32), ('learned', I32), ('imprint', U8)]


class TabC(ctypes.Structure):
    _fields_ = [('items', ctypes.c_void_p*1024), ('count', ctypes.c_int), ('pool', EntryC*1024)]


class StampC(ctypes.Structure):
    _fields_ = [('class_byte', I32), ('elemental', I32), ('basic', TabC), ('special', TabC),
                ('edit', ctypes.c_void_p*10), ('slots', ctypes.c_void_p*10), ('saved', I32*10),
                ('special_slot', I32)]


class KeysC(ctypes.Structure):
    _fields_ = [('selected', I32), ('learned', I32*1024), ('nlearned', ctypes.c_int), ('has_slot', U8*10),
                ('slot', I32*10)]


class EventsC(ctypes.Structure):
    _fields_ = [('count', ctypes.c_int), ('kind', I32*64), ('arg', I32*64)]


class WorldC(ctypes.Structure):
    _fields_ = [('env', ctypes.POINTER(vs.EnvC)), ('hero', ctypes.POINTER(vs.HeroC)), ('stamp', ctypes.POINTER(StampC)),
                ('keys', ctypes.POINTER(KeysC)), ('usable', vs.USABLE_FN), ('usable_user', ctypes.c_void_p)]


class ServerNative(vs.SkillNative):
    def __init__(self, work, lib=None):
        super().__init__(work, lib)
        L = self.lib
        L.mu_skill_stamp_init.argtypes = [ctypes.POINTER(StampC)]
        L.mu_skill_stamp_push.argtypes = [ctypes.POINTER(StampC), ctypes.c_int, I32, I32]
        L.mu_skill_stamp_push.restype = ctypes.c_void_p
        L.mu_skill_stamp_reset.argtypes = [ctypes.POINTER(vs.EnvC), ctypes.POINTER(StampC), I32]
        L.mu_skill_stamp_refresh.argtypes = [ctypes.POINTER(vs.EnvC), ctypes.POINTER(StampC), I32]
        L.mu_skill_list_receive.argtypes = [ctypes.POINTER(WorldC), ctypes.c_char_p, ctypes.c_size_t,
                                            ctypes.POINTER(EventsC)]
        L.mu_skill_can_use.argtypes = [ctypes.POINTER(UseEnvC), ctypes.POINTER(vs.HeroC), I32]
        L.mu_skill_world_ok.argtypes = [ctypes.POINTER(UseEnvC), I32]
        L.mu_skill_stamp_marker.argtypes = [I32, ctypes.POINTER(EntryC)] + [ctypes.c_float]*6 + [ctypes.POINTER(QuadC)]
        L.mu_skill_damage_type_icon.argtypes = [I32, I32] + [ctypes.c_float]*6 + [ctypes.POINTER(QuadC)]
        L.mu_skill_keys_receive.argtypes = [ctypes.POINTER(WorldC), ctypes.c_char_p, ctypes.c_size_t,
                                            ctypes.POINTER(EventsC)]


def master_env(table):
    """An env whose base-skill answer is the C table walk (the client's 0x00bb1c32 runs for real)."""
    env = vs.EnvC()
    env.table = ctypes.pointer(table)
    return env


# ---- the state of a case -------------------------------------------------------------------------------

class State:
    """A case's starting state, written into both machines: hero list, stamp manager, hotkeys."""

    def __init__(self):
        self.count = 0
        self.skills = [0]*256
        self.current = 0
        self.elemental = 0
        self.class_byte = 0
        self.basic = []        # [base, learned, imprint]
        self.special = []
        self.edit = [None]*10  # ('b'|'s', index) or None
        self.slots = [None]*10
        self.saved = [0]*10
        self.special_slot = -1
        self.stamp_class = 0
        self.stamp_elem = 0
        self.selected = 0
        self.learned_keys = []
        self.slot_map = {}


def chains(records):
    """skill -> brand for chain-following picks."""
    return {r.index: r.brand for r in records}


def random_state(rng, keys, by_brand, records, n_entries=None):
    st = State()
    pick = lambda: rng.choice(keys) if rng.random() < 0.9 else rng.choice([0, 0x43, 0x45, 0x48, rng.randint(1, 3000)])
    st.count = rng.choice([0, 1, rng.randint(0, 12), rng.randint(0, 40)])
    for i in range(st.count):
        st.skills[i] = pick() if rng.random() < 0.85 else 0
    for i in range(st.count, min(256, st.count + rng.choice([0, 0, 3]))):   # stale entries past the count
        st.skills[i] = pick()
    st.current = rng.choice([0, rng.randint(0, max(0, st.count)), rng.randint(0, 255)])
    st.elemental = rng.randint(0, 6)
    st.class_byte = rng.randint(0, 255)
    bases = sorted({vs_master_base(by_brand, k) for k in rng.sample(keys, min(30, len(keys)))})
    for b in bases[:rng.randint(0, len(bases))] if n_entries is None else bases[:n_entries]:
        chain = [b] + [k for k in rng.sample(keys, min(40, len(keys))) if vs_master_base(by_brand, k) == b]
        st.basic.append([b, rng.choice([0, rng.choice(chain), rng.choice(keys)]), rng.randint(0, 1)])
    for b in rng.sample(keys, rng.randint(0, 4)):
        st.special.append([vs_master_base(by_brand, b), rng.choice([0, b]), rng.randint(0, 1)])
    refs = [('b', i) for i in range(len(st.basic))] + [('s', i) for i in range(len(st.special))]
    for arr in (st.edit, st.slots):
        for i in range(10):
            if refs and rng.random() < 0.6:
                arr[i] = rng.choice(refs)
    st.saved = [rng.choice([0, rng.choice(keys)]) for _ in range(10)]
    st.special_slot = rng.choice([-1, rng.randint(0, 9)])
    st.stamp_class = rng.choice([0, st.class_byte])
    st.stamp_elem = rng.randint(0, 6)
    pool = [s for s in st.skills[:st.count] if s] + rng.sample(keys, min(10, len(keys)))
    st.selected = rng.choice([0, rng.choice(pool)])
    st.learned_keys = sorted({rng.choice(pool) for _ in range(rng.randint(0, 20))} |
                             ({st.selected} if st.selected and rng.random() < 0.8 else set()))
    for i in range(10):
        if rng.random() < 0.7:
            st.slot_map[i] = rng.choice([0, rng.choice(pool)])
    return st


_base_cache = {}


def vs_master_base(by_brand, skill):
    """0x00bb1c32 over the snapshot (Python statement for the case generator only)."""
    if skill not in by_brand:
        return skill
    key = (id(by_brand), skill)
    if key not in _base_cache:
        last, b, n = skill, by_brand[skill], 0
        while b not in (0, 0x4b) and n < 64:
            last = b if b in by_brand else 0
            b = by_brand.get(b, 0)
            n += 1
        _base_cache[key] = last
    return _base_cache[key]


# client side

def build_string_map(m, keys):
    """std::map<int, std::string> (node 0x2c: key +0x10, string +0x14) of empty strings."""
    head = vs.empty_map(m, 0x2c)
    items = sorted(keys)

    def build(lo, hi, parent):
        if lo >= hi:
            return head
        mid = (lo + hi) // 2
        node = m.alloc(0x2c, define=True)
        left = build(lo, mid, node)
        right = build(mid + 1, hi, node)
        m.write(node, struct.pack('<III', left, parent, right) + b'\x01\x00\0\0' + struct.pack('<i', items[mid]) +
                bytes(16) + struct.pack('<II', 0, 15))
        return node
    root = build(0, len(items), head)
    if items:
        lm = root
        while m.u32(lm) != head:
            lm = m.u32(lm)
        rm = root
        while m.u32(rm + 8) != head:
            rm = m.u32(rm + 8)
        m.write(head, struct.pack('<III', lm, root, rm))
    return head, len(items)


def write_client(m, st):
    """The hero, the attributes (via validate_skill.write_hero), the stamp manager and the hotkeys."""
    hero = vs.HeroC()
    hero.count = st.count
    hero.current = st.current
    hero.elemental = st.elemental
    case = argparse.Namespace()
    h, a = vs.write_hero(m, case, hero)
    for i in range(256):
        m.write(a + 0x1e6 + 2*i, struct.pack('<H', st.skills[i]))
    m.write(a + 0x1e6 + 2*256, bytes(2*(0x3a1 - 256)))
    m.write(a + 0x187, bytes([st.class_byte]))
    stamp = m.alloc(0xb0, define=True)
    m.put32(stamp + 4, st.stamp_class)
    m.put32(stamp + 8, st.stamp_elem)
    ptrs = {}
    for tag, lst, off in (('b', st.basic, 0xc), ('s', st.special, 0x18)):
        entries = []
        for i, (base, learned, imprint) in enumerate(lst):
            e = m.alloc(0xc, define=True)
            m.write(e, struct.pack('<ii', base, learned) + bytes([imprint, 0, 0, 0]))
            ptrs[(tag, i)] = e
            entries.append(e)
        if entries:
            block = m.alloc(4*len(entries), define=True)
            m.write(block, b''.join(struct.pack('<I', e) for e in entries))
            m.write(stamp + off, struct.pack('<III', block, block + 4*len(entries), block + 4*len(entries)))
        else:
            m.write(stamp + off, bytes(12))
    for i in range(10):
        m.put32(stamp + 0x24 + 4*i, ptrs[st.edit[i]] if st.edit[i] else 0)
        m.put32(stamp + 0x4c + 4*i, ptrs[st.slots[i]] if st.slots[i] else 0)
        m.put32(stamp + 0x80 + 4*i, st.saved[i])
    m.put32(stamp + 0xa8, st.special_slot)
    m.put32(HOTKEYS, st.selected)
    head, size = build_string_map(m, st.learned_keys)
    m.write(HOTKEYS + 4, struct.pack('<II', head, size))
    head, size = vs.build_map(m, list(st.slot_map.items()))
    m.write(HOTKEYS + 0xc, struct.pack('<II', head, size))
    return h, a, stamp


def read_client(m, h, a, stamp):
    out = {'count': m.read(a + 0x1e4, 1)[0], 'skills': list(struct.unpack('<256H', m.read(a + 0x1e6, 512))),
           'current': m.read(h + 0x32, 1)[0]}
    ident = {}
    tabs = {}
    for tag, off in (('b', 0xc), ('s', 0x18)):
        begin, end, _ = struct.unpack('<III', m.read(stamp + off, 12))
        items = []
        for i, p in enumerate(range(begin, end, 4) if begin else []):
            e = m.u32(p)
            ident[e] = (tag, i)
            base, learned = struct.unpack('<ii', m.read(e, 8))
            items.append((base, learned, m.read(e + 8, 1)[0]))
        tabs[tag] = items
    out['basic'], out['special'] = tabs['b'], tabs['s']
    out['class'], out['elemental'] = s32(m.u32(stamp + 4)), s32(m.u32(stamp + 8))
    out['edit'] = [ident.get(m.u32(stamp + 0x24 + 4*i), 'stale') if m.u32(stamp + 0x24 + 4*i) else None
                   for i in range(10)]
    out['slots'] = [ident.get(m.u32(stamp + 0x4c + 4*i), 'stale') if m.u32(stamp + 0x4c + 4*i) else None
                    for i in range(10)]
    out['saved'] = [s32(m.u32(stamp + 0x80 + 4*i)) for i in range(10)]
    out['special_slot'] = s32(m.u32(stamp + 0xa8))
    out['selected'] = s32(m.u32(HOTKEYS))
    learned, _ = vs.read_tree(m, HOTKEYS + 4)
    out['learned_keys'] = [k for k, _ in learned]
    slots, _ = vs.read_tree(m, HOTKEYS + 0xc)
    out['slot_map'] = {k: s32(m.u32(node + 0x14)) for k, node in slots}
    return out


# native side

def write_native(nat, st):
    hero = vs.HeroC()
    hero.count = st.count
    for i in range(256):
        hero.skills[i] = st.skills[i]
    hero.current = st.current
    hero.elemental = st.elemental
    stamp = StampC()
    nat.lib.mu_skill_stamp_init(ctypes.byref(stamp))
    stamp.class_byte = st.stamp_class
    stamp.elemental = st.stamp_elem
    ptrs = {}
    for tag, lst in (('b', st.basic), ('s', st.special)):
        for i, (base, learned, imprint) in enumerate(lst):
            p = nat.lib.mu_skill_stamp_push(ctypes.byref(stamp), int(tag == 's'), base, learned)
            ctypes.cast(p, ctypes.POINTER(EntryC))[0].imprint = imprint
            ptrs[(tag, i)] = p
    for i in range(10):
        stamp.edit[i] = ptrs[st.edit[i]] if st.edit[i] else None
        stamp.slots[i] = ptrs[st.slots[i]] if st.slots[i] else None
        stamp.saved[i] = st.saved[i]
    stamp.special_slot = st.special_slot
    keys = KeysC()
    keys.selected = st.selected
    for i, k in enumerate(st.learned_keys):
        keys.learned[i] = k
    keys.nlearned = len(st.learned_keys)
    for i, v in st.slot_map.items():
        keys.has_slot[i] = 1
        keys.slot[i] = v
    return hero, stamp, keys


def read_native(hero, stamp, keys, class_byte=None):
    out = {'count': hero.count, 'skills': [hero.skills[i] for i in range(256)], 'current': hero.current}
    ident = {}
    for tag, tab in (('b', stamp.basic), ('s', stamp.special)):
        items = []
        for i in range(tab.count):
            e = ctypes.cast(tab.items[i], ctypes.POINTER(EntryC))[0]
            ident[tab.items[i]] = (tag, i)
            items.append((e.base, e.learned, e.imprint))
        out['basic' if tag == 'b' else 'special'] = items
    out['class'], out['elemental'] = stamp.class_byte, stamp.elemental
    out['edit'] = [ident.get(stamp.edit[i], 'stale') if stamp.edit[i] else None for i in range(10)]
    out['slots'] = [ident.get(stamp.slots[i], 'stale') if stamp.slots[i] else None for i in range(10)]
    out['saved'] = [stamp.saved[i] for i in range(10)]
    out['special_slot'] = stamp.special_slot
    out['selected'] = keys.selected
    out['learned_keys'] = [keys.learned[i] for i in range(keys.nlearned)]
    out['slot_map'] = {i: keys.slot[i] for i in range(10) if keys.has_slot[i]}
    return out


class Recorder:
    """The boundary stubs of the handlers (see the module docstring)."""

    def __init__(self, m, stamp, usable=None):
        self.events = []
        arg = lambda mm: s32(mm.args(1)[0])
        m.stub(STAMP_GET, lambda mm: stamp, 0)
        m.stub(vs.GFX_MGR, lambda mm: DUMMY, 0)
        m.put32(DUMMY + 0x1f8, DUMMY + 0x200)
        for getter in (0x0095f998, 0x0095f986, 0x00995257):
            m.stub(getter, lambda mm: DUMMY, 0)
        m.stub(0x0095fbdc, lambda mm: 0, 0)
        m.stub(0x00c26ad8, lambda mm: self.events.append((EV['tree_add'], arg(mm))) or 0, 4)
        m.stub(0x00ba7366, lambda mm: self.events.append((EV['master_add'], arg(mm))) or 0, 4)
        m.stub(0x00b40380, lambda mm: self.events.append((EV['select'], s32(mm.u32(HOTKEYS)))) or 0, 0)

        def lock(mm):
            out = mm.args(1)[0]
            mm.write(out, struct.pack('<II', LISTENER_OBJ, 0))
            return out
        m.stub(0x00a087dd, lock, 4)
        m.stub(0x00a097c7, lambda mm: 1, 0)
        m.stub(0x00a09802, lambda mm: LISTENER_OBJ, 0)
        m.stub(0x00a095ce, lambda mm: 0, 0)

        def keys_all(mm):
            v = mm.args(1)[0]
            begin, end = struct.unpack('<II', mm.read(v, 8))
            self.events.append((EV['keys_all'], (end - begin)//4))
            return 0
        m.stub(0x00c5e991, keys_all, 4)
        m.stub(0x00c5ea96, lambda mm: self.events.append((EV['keys_add'], arg(mm))) or 0, 4)
        if usable is not None:
            m.stub(0x0107e918, lambda mm: DUMMY, 0)

            def use(mm):
                s = arg(mm)
                self.events.append((EV['usable'], s))
                return int(usable(s))
            m.stub(0x010918c7, use, 4)
            m.stub(0x01096e55, lambda mm: 1, 4)


def native_events(ev):
    return [(ev.kind[i], ev.arg[i]) for i in range(ev.count)]


# ---- families ------------------------------------------------------------------------------------------

def list_packet(rng, keys, st, by_brand, records):
    use3 = [r.index for r in records if r.use_type == 3]
    branded = [r.index for r in records if r.brand not in (0, 0x4b)]
    pool = keys + use3*3 + branded*2
    learned = [s for s in st.skills[:st.count] if s]
    r = rng.random()
    if r < 0.34:
        n = rng.choice([0, 1, rng.randint(0, 10), rng.randint(0, 60)])
        skills = [rng.choice(pool) if rng.random() < 0.9 else rng.choice([0, 0x43, rng.randint(1, 65535)])
                  for _ in range(n)]
        kind = n
    else:
        kind = 0xfe if r < 0.67 else 0xff
        cand = [rng.choice(pool), rng.choice(pool), rng.randint(1, 65535)]
        if learned:
            cand += [rng.choice(learned)]*3
        if kind == 0xfe:      # a skill whose brand is learned (CurrentSkill moves to it)
            cand += [k for k in rng.sample(branded, 3)]
        skills = [rng.choice(cand)]
    body = bytearray(7 + 4*len(skills))
    body[0], body[1], body[2], body[3] = 0xc1, len(body) & 0xff, 0xa0, 0x20
    body[5] = kind
    for i, s in enumerate(skills):
        body[7 + 4*i] = i & 0xff
        body[8 + 4*i:10 + 4*i] = struct.pack('<H', s & 0xffff)
        body[10 + 4*i] = rng.randint(0, 255)
    return bytes(body)


def run_list(m, nat, table, records, keys, rng, fam, cases):
    by_brand = chains(records)
    for n in range(cases):
        st = random_state(rng, keys, by_brand, records)
        packet = list_packet(rng, keys, st, by_brand, records)
        if packet[5] == 0xfe and rng.random() < 0.3:   # add a skill below an entry's learned one in its chain
            branded = [r.index for r in records if r.brand not in (0, 0x4b) and r.brand in by_brand]
            if branded:
                top = rng.choice(branded)
                low = by_brand[top] if rng.random() < 0.7 else by_brand.get(by_brand[top], by_brand[top])
                st.basic.append([vs_master_base(by_brand, top), top, 0])
                st.basic.insert(0, st.basic.pop())
                st.edit = [(r[0], r[1] + 1) if r and r[0] == 'b' else r for r in st.edit]
                st.slots = [(r[0], r[1] + 1) if r and r[0] == 'b' else r for r in st.slots]
                packet = packet[:8] + struct.pack('<H', low & 0xffff) + packet[10:]
        if packet[5] == 0xfe and rng.random() < 0.5 and st.count:   # make the current entry the brand
            target = packet[8] | packet[9] << 8
            brand = by_brand.get(target, 0)
            if brand:
                st.skills[0] = brand
                st.current = 0
        m.prepare(force=True)
        vs.common_stubs(m)
        h, a, stamp = write_client(m, st)
        rec = Recorder(m, stamp)
        pk = m.alloc(len(packet), define=True)
        m.write(pk, packet)
        m.call(LIST_RECV, [pk])
        client = read_client(m, h, a, stamp)
        client['events'] = rec.events
        hero, nstamp, nkeys = write_native(nat, st)
        env = master_env(table)
        world = WorldC(ctypes.pointer(env), ctypes.pointer(hero), ctypes.pointer(nstamp), ctypes.pointer(nkeys),
                       vs.USABLE_FN(lambda u, s: 0), None)
        ev = EventsC()
        nat.lib.mu_skill_list_receive(ctypes.byref(world), packet, len(packet), ctypes.byref(ev))
        native = read_native(hero, nstamp, nkeys)
        native['events'] = native_events(ev)
        fam.check((n, packet[5]), client, native)


def keys_packet(rng, keys, st):
    body = bytearray(4 + 20 + 16)
    body[0], body[1], body[2], body[3] = 0xc1, len(body), 0xa0, 0x03
    pool = [e[0] for e in st.basic] + [e[1] for e in st.basic if e[1]] + [e[0] for e in st.special] + keys[:5]
    for i in range(10):
        r = rng.random()
        v = 0xffff if r < 0.25 else 0x12a if r < 0.3 else rng.choice(pool) if pool and r < 0.9 else rng.randint(0, 3000)
        body[4 + 2*i:6 + 2*i] = struct.pack('>H', v)
    return bytes(body)


def run_keys(m, nat, table, records, keys, rng, fam, cases):
    by_brand = chains(records)
    for n in range(cases):
        st = random_state(rng, keys, by_brand, records, n_entries=rng.randint(0, 20))
        if rng.random() < 0.5:     # learned entries the hero has
            for e in st.basic:
                if e[1] and rng.random() < 0.5 and st.count < 255:
                    st.skills[st.count] = e[1]
                    st.count += 1
        packet = keys_packet(rng, keys, st)
        if rng.random() < 0.2:     # no keys and no window slots: the usability and special-tab branches
            packet = packet[:4] + b'\xff' * 20 + packet[24:]
            st.edit = [None]*10
        usable = {s: rng.random() < 0.5 for s in keys + [0]}
        m.prepare(force=True)
        vs.common_stubs(m)
        h, a, stamp = write_client(m, st)
        rec = Recorder(m, stamp, usable=lambda s: usable.get(s, False))

        def stop(mm):
            mm.uc.reg_write(cm.UC_X86_REG_EIP, cm.RETURN_SENTINEL)
            return cm.REDIRECT
        m.stub(KEYS_STOP, stop, 0)
        pk = m.alloc(len(packet), define=True)
        m.write(pk, packet)
        m.call(KEYS_RECV, [pk])
        m.call(KEYS_REBUILD, [], ecx=HOTKEYS)
        client = read_client(m, h, a, stamp)
        client['events'] = rec.events
        hero, nstamp, nkeys = write_native(nat, st)
        env = master_env(table)
        world = WorldC(ctypes.pointer(env), ctypes.pointer(hero), ctypes.pointer(nstamp), ctypes.pointer(nkeys),
                       vs.USABLE_FN(lambda u, s: int(usable.get(s, False))), None)
        ev = EventsC()
        nat.lib.mu_skill_keys_receive(ctypes.byref(world), packet, len(packet), ctypes.byref(ev))
        native = read_native(hero, nstamp, nkeys)
        native['events'] = native_events(ev)
        fam.check(n, client, native)


def synthetic_records(rng, count):
    """Skill(Kor) records for the stamp family: random use types, brands (0, 0x4b, chains) and class maps."""
    idx = sorted(rng.sample(range(1, 1200), count) + rng.sample([0x42, 0x12a, 0x4b], rng.randint(0, 3)))
    idx = sorted(set(idx))
    out = []
    for i in idx:
        r = vs.RecordC()
        r.index = i
        r.name = b'S%d' % i
        r.use_type = rng.choice([0, 0, 1, 2, 3, 4, 4, 7, 8, 14, 14, 5])
        r.brand = rng.choice([0, 0, 0, 0x4b, 0x4b, rng.choice(idx)])
        r.mastery = rng.randint(0, 7)
        for c in range(16):
            r.classes[c] = rng.choice([0, 0, 1, 2, -1])
        out.append(r)
    return out


def write_table(m, records):
    """The records as the row parser leaves them: map at 0x06fbb138 + 0x108 (node 0x14 + 0xd0)."""
    head = vs.empty_map(m, 0x14 + 0xd0)
    items = [(r.index, r) for r in records]

    def node_for(r, left, parent, right):
        node = m.alloc(0x14 + 0xd0, define=True)
        rec = node + 0x14
        m.write(node, struct.pack('<III', left, parent, right) + b'\x01\x00\0\0' + struct.pack('<i', r.index))
        m.write(rec, bytes(0xd0))
        name = vs.std_string(m, bytes(r.name))
        m.write(rec + 8, m.read(name, 0x18))
        for name, off, kind in vs.RECORD_FIELDS:
            v = getattr(r, name)
            m.write(rec + off, struct.pack('<i', v) if kind == 'i' else bytes([v & 0xff]))
        h1, n1 = vs.build_map(m, [(0x80, r.rank[0]), (0x40, r.rank[1]), (0x20, r.rank[2])])
        m.write(rec + 0x64, struct.pack('<II', h1, n1))
        h2, n2 = vs.build_map(m, [(c, r.classes[c]) for c in range(16)])
        m.write(rec + 0x6c, struct.pack('<II', h2, n2))
        m.write(rec + 0xb8, bytes(12))
        return node

    def build(lo, hi, parent):
        if lo >= hi:
            return head
        mid = (lo + hi) // 2
        node = node_for(items[mid][1], 0, parent, 0)
        left = build(lo, mid, node)
        right = build(mid + 1, hi, node)
        m.write(node, struct.pack('<II', left, parent))
        m.put32(node + 8, right)
        return node
    root = build(0, len(items), head)
    if items:
        lm = root
        while m.u32(lm) != head:
            lm = m.u32(lm)
        rm = root
        while m.u32(rm + 8) != head:
            rm = m.u32(rm + 8)
        m.write(head, struct.pack('<III', lm, root, rm))
    m.write(SKILL_TABLE + 0x108, struct.pack('<II', head, len(items)))


def run_stamp(m, nat, rng, fam, cases):
    for n in range(cases):
        records = synthetic_records(rng, rng.randint(5, 60))
        keys = [r.index for r in records]
        table = nat.table(records)
        by_brand = chains(records)
        st = random_state(rng, keys, by_brand, records, n_entries=rng.randint(0, 12))
        st.class_byte = rng.choice([rng.randint(0, 255), rng.choice([0x0a, 0x1b, 0x2f, 0x03, 0x10])])
        st.stamp_class = rng.choice([st.class_byte, rng.randint(0, 255)])
        m.prepare(force=True)
        vs.common_stubs(m)
        write_table(m, records)
        h, a, stamp = write_client(m, st)
        Recorder(m, stamp)
        m.call(STAMP_RESET, [], ecx=stamp)
        m.call(STAMP_REFRESH, [], ecx=stamp)
        client = read_client(m, h, a, stamp)
        hero, nstamp, nkeys = write_native(nat, st)
        env = master_env(table)
        nat.lib.mu_skill_stamp_reset(ctypes.byref(env), ctypes.byref(nstamp), st.class_byte)
        nat.lib.mu_skill_stamp_refresh(ctypes.byref(env), ctypes.byref(nstamp), st.elemental)
        native = read_native(hero, nstamp, nkeys)
        fam.check((n, st.class_byte, st.stamp_class), client, native)


# ---- the usability check (skill_canuse) --------------------------------------------------------------------

CAN_USE, WORLD_OK, MARKER, DAMAGE_TYPE = 0x010918c7, 0x00a9b235, 0x0109750c, 0x01097601
WORLD, SIEGE, CONFUSION, EVENT_FLAG = 0x01cf15fc, 0x01ec8ee7, 0x0a39d761, 0x01d1e028 + 4


class ItemC(ctypes.Structure):
    _fields_ = [('code', I32), ('level_bits', I32), ('byte1a', U8)]


KIND_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
INT1_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, I32)
INT0_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
REQ_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, I32, ctypes.POINTER(I32), ctypes.POINTER(I32),
                          ctypes.POINTER(I32))


class UseEnvC(ctypes.Structure):
    _fields_ = [('skills', ctypes.POINTER(vs.EnvC)), ('user', ctypes.c_void_p), ('item_kind', KIND_FN),
                ('special_item', INT1_FN), ('arrows', INT1_FN), ('party', INT0_FN), ('map_open', INT0_FN),
                ('it_relic', INT0_FN), ('event_map', INT1_FN), ('confusion_world', INT1_FN), ('skill_require', REQ_FN),
                ('master_level', INT1_FN), ('world', I32), ('siege', U8), ('confusion_flag', U8), ('event_flag', I32),
                ('transform', U16), ('part_model', I32*2), ('items', ItemC*15)]


class QuadC(ctypes.Structure):
    _fields_ = [('bitmap', I32), ('x', ctypes.c_float), ('y', ctypes.c_float), ('w', ctypes.c_float),
                ('h', ctypes.c_float), ('u', ctypes.c_float), ('v', ctypes.c_float), ('uw', ctypes.c_float),
                ('vh', ctypes.c_float)]


SPECIAL_BASES = [0x3e, 0x7ef, 0x4d, 0xe9, 0x7de, 0x7df, 0x82a, 0x33b, 0x127, 0x31a, 0x3f, 0xd4, 0x26c, 0x1e, 0x22,
                 0x1b0, 0x282, 0x31, 0x4c]
WORLDS = [0, 2, 0xa, 0x84, 0x1e, 0x12, 0x17, 0x35, 0x61, 0x2d, 0x32, 0x62, 0x63, 0x52, 0x5a, 0x73, 0xb, 0x34, 0x40]


class UseCase:
    def __init__(self, rng, records, reqs):
        self.world = rng.choice(WORLDS)
        self.siege = rng.choice([0, 1, 1, 2])
        self.confusion_flag = rng.choice([0, 0, 1])
        self.event_flag = rng.choice([0, 0, 0, 1])
        self.transform = rng.choice([0xffff, 0xffff, 3])
        self.parts = [rng.choice([0x28f8, 0x28f9, 0x28fa, 0x2900, 0x28f7, 5]), rng.choice([0x28f7, 0x28f8, 0])]
        self.kinds = {(slot, k) for slot in (0, 1) for k in rng.sample([1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xd,
                                                                       0xe, 0xf, 0x4b, 0x4e, 0x51, 0x54, 0x5a, 0x73,
                                                                       0x7b], rng.randint(0, 3))}
        ring = lambda: rng.choice([-1, -1, -1, -1, rng.randint(0, 0x2c00), 0x1a0a, 0x1a44])
        self.items = [(ring() if i in (10, 11) else rng.choice([-1, rng.randint(0, 0x2c00)]), rng.choice([0x10, 0x18, rng.randint(0, 0xff)]),
                       rng.randint(0, 2)) for i in range(15)]
        self.buffs = set(rng.sample([0x13, 0xcf, 0x1ae, 0x199, 6, 0x8f, 0x52, 0x8a, 0x8b, 0x1bb], rng.randint(0, 4)))
        self.world = rng.choice(WORLDS + [0, 0, 0, 2, 2])
        self.special = rng.random() < 0.8
        self.arrows = rng.random() < 0.7
        self.party = (rng.random() < 0.5, rng.random() < 0.5)
        self.map = (rng.random() < 0.6, rng.random() < 0.5)
        self.relic = rng.random() < 0.5
        self.event_map = rng.choice([0, 0, 1, 2])
        self.confusion_world = rng.random() < 0.5
        self.master_level = rng.randint(0, 20)
        self.tree_learned = rng.random() < 0.6
        self.reqs = reqs


def use_env(case, table, keepalive):
    env = vs.EnvC()
    env.table = ctypes.pointer(table)
    env.buff = vs.BUFF_FN(lambda u, l, b: int(b in case.buffs))
    env.tree_learned = vs.HAS_FN(lambda u, s: int(case.tree_learned))
    ue = UseEnvC()
    ue.skills = ctypes.pointer(env)

    def req(u, base, p1, p2, p3):
        r = case.reqs.get(base)
        if not r or r[1] == 0:
            return 0
        p1[0], p2[0], p3[0] = r[4], r[5], r[6]
        return 1
    cbs = (KIND_FN(lambda u, slot, k: int((slot, k) in case.kinds)), INT1_FN(lambda u, s: int(case.special)),
           INT1_FN(lambda u, a: int(case.arrows)), INT0_FN(lambda u: int(case.party[0] or case.party[1])),
           INT0_FN(lambda u: int(not (case.map[0] and not case.map[1]))), INT0_FN(lambda u: int(case.relic)),
           INT1_FN(lambda u, w: case.event_map), INT1_FN(lambda u, w: int(case.confusion_world)), REQ_FN(req),
           INT1_FN(lambda u, s: case.master_level))
    (ue.item_kind, ue.special_item, ue.arrows, ue.party, ue.map_open, ue.it_relic, ue.event_map, ue.confusion_world,
     ue.skill_require, ue.master_level) = cbs
    ue.world, ue.siege, ue.confusion_flag, ue.event_flag = case.world, case.siege, case.confusion_flag, case.event_flag
    ue.transform = case.transform
    ue.part_model[0], ue.part_model[1] = case.parts
    for i, (code, lv, b) in enumerate(case.items):
        ue.items[i] = ItemC(code, lv, b)
    keepalive.extend([env, cbs])
    return ue


def use_stubs(m, case, h, a):
    """The client side of a UseCase: globals, hero fields, items, and the boundary stubs."""
    arg = lambda mm, i: mm.args(i + 1)[i]
    a8 = a - 8
    m.put32(WORLD, case.world)
    m.put32(0x01cf115c, 0xffffffff)                    # the pending-action state ArrowCheck gets
    m.write(SIEGE, bytes([case.siege]))
    m.write(CONFUSION, bytes([case.confusion_flag]))
    m.put32(EVENT_FLAG - 4, 0)
    m.put32(EVENT_FLAG, case.event_flag)
    m.write(h + 0x322e, struct.pack('<H', case.transform))
    m.put32(h + 0x31f4 + 4, case.parts[0])
    m.put32(h + 0x31f4 + 0x1c + 4, case.parts[1])
    for i, (code, lv, b) in enumerate(case.items):
        it = a8 + 0x1b58 + i*0x12c
        m.put32(it + 0x10, code)
        m.put32(it + 0x14, lv)
        m.write(it + 0x1a, bytes([b]))
    slot_of = lambda item: (item - (a8 + 0x1b58)) // 0x12c
    m.stub(0x00987982, lambda mm: int((slot_of(mm.uc.reg_read(cm.UC_X86_REG_ECX)), s32(arg(mm, 0))) in case.kinds), 4)
    m.stub(0x01295ade, lambda mm: int(s32(arg(mm, 0)) in case.buffs), 4)
    m.stub(0x0109260c, lambda mm: int(case.special), 4)
    m.stub(0x0169da9c, lambda mm: int(case.arrows), 0)
    m.stub(0x0129deaa, lambda mm: 7, 0)

    def sp(mm):
        out = arg(mm, 0)
        mm.write(out, struct.pack('<II', DUMMY + 0x300, 0))
        return out
    calls = {'party': 0}

    def party(i):
        def handler(mm):
            return int(case.party[i])
        return handler
    m.stub(0x0095c595, sp, 8)
    m.stub(0x0095f16e, lambda mm: DUMMY + 0x300, 0)
    m.stub(0x00c7974e, party(0), 4)
    m.stub(0x00c79662, party(1), 4)
    m.stub(0x0095ebbb, lambda mm: 0, 0)
    m.stub(0x009fd699, lambda mm: (mm.write(arg(mm, 0), bytes(8)), arg(mm, 0))[1], 4)
    m.stub(0x009fe103, lambda mm: int(case.map[0]), 0)
    m.stub(0x009fe126, lambda mm: DUMMY + 0x380, 0)
    m.stub(0x01094029, lambda mm: int(case.map[1]), 0)
    m.stub(0x009fdf2d, lambda mm: 0, 0)
    m.stub(0x00db747f, lambda mm: DUMMY, 0)
    m.stub(0x009fa30a, lambda mm: DUMMY, 0)
    m.stub(0x009fbb31, lambda mm: int(case.relic), 4)
    m.stub(0x0095c652, lambda mm: DUMMY + 0x3c0, 0)
    m.stub(0x00d7b35d, lambda mm: case.event_map, 4)
    m.stub(0x00a9a686, lambda mm: DUMMY, 0)
    m.stub(0x010e6e74, lambda mm: int(case.confusion_world), 4)
    m.stub(0x00bb1d9d, lambda mm: case.master_level & 0xff, 4)
    m.stub(0x0095fb49, lambda mm: DUMMY, 0)
    m.stub(0x00c2a37a, lambda mm: int(case.tree_learned), 4)
    m.stub(vs.GFX_MGR, lambda mm: DUMMY, 0)
    m.stub(0x0095f998, lambda mm: DUMMY, 0)
    m.stubs.pop(0x00bb1c32, None)                       # the base skill walk runs for real


def run_canuse(m, nat, table, records, keys, reqs, rng, fam, cases):
    by = {r.index: r for r in records}
    weapons = {}
    for r in records:
        weapons.setdefault(r.weapon, []).append(r.index)
    interesting = [k for k in SPECIAL_BASES if k in by] + [r.index for r in records if r.use_type in (2, 7, 8, 9)
                                                             or r.xb0 in (1, 2) or r.brand == 0x4b] + list(reqs)
    for n in range(cases):
        r = rng.random()
        if r < 0.4:
            skill = rng.choice(interesting)
        elif r < 0.8:
            w = rng.choice(list(weapons))
            skill = rng.choice(weapons[w])
        else:
            skill = rng.choice(keys)
        case = UseCase(rng, records, reqs)
        if skill in by:            # bias the weapon kinds toward the skill's rule
            w = by[skill].weapon
            pool = {2: [1, 2, 3, 7, 0x51], 3: [1, 2], 4: [7], 6: [0xc, 0xd, 0xe], 7: [3], 8: [0xf], 9: [0x4e],
                    10: [0xd], 11: [0xe], 12: [0x51], 13: [0x54], 14: [0x5a], 17: [0x73], 18: [0x7b], 1: [8, 9],
                    5: [8, 9]}.get(w, [])
            if pool and rng.random() < 0.6:
                case.kinds.add((rng.choice([0, 1]), rng.choice(pool)))
        m.prepare(force=True)
        vs.common_stubs(m)
        hcase = vs.Case(rng, keys)
        hero = vs.random_hero(rng, keys, hcase)
        hcase.class_index = rng.randint(0, 7)
        hero.class_index = hcase.class_index
        if rng.random() < 0.75:
            for name in ('strength', 'agility', 'vitality', 'energy', 'command'):
                setattr(hero, name, 65535)
        if reqs and rng.random() < 0.4 and hero.count:
            hero.skills[0] = rng.choice([v[4] for v in reqs.values()])
        h, a = vs.write_hero(m, hcase, hero)
        m.stub(vs.CLASS_INDEX, lambda mm: hcase.class_index, 0)
        use_stubs(m, case, h, a)
        t = m.alloc(0x20, define=True)
        m.write(t, struct.pack('<II', h, h + 0x3254))
        client = m.call(CAN_USE, [skill], ecx=t) & 0xff
        keep = []
        ue = use_env(case, table, keep)
        ue.skills[0].class_index = hcase.class_index
        native = nat.lib.mu_skill_can_use(ctypes.byref(ue), ctypes.byref(hero), skill)
        fam.check((n, skill, by[skill].weapon if skill in by else None), client, native)

    # This branch was misread in the first static notes: 0x01092042 accepts an absent 0x1bb buff.
    # Exercise every combination at the actual caller with the weapon/stat/ring gates satisfied.
    if 0x82a in by:
        for world_has in (False, True):
            for flag in (0, 1):
                for has_buff in (False, True):
                    case = UseCase(rng, records, reqs)
                    case.world, case.siege, case.event_flag, case.transform = 0, 0, 0, 0xffff
                    case.kinds = {(0, 0x73)}
                    case.items = [(-1, 0, 0)] * 15
                    case.buffs = {0x1bb} if has_buff else set()
                    case.confusion_world, case.confusion_flag = world_has, flag
                    m.prepare(force=True)
                    vs.common_stubs(m)
                    hcase = vs.Case(rng, keys)
                    hcase.class_index = 5
                    hero = vs.HeroC()
                    hero.class_index = 5
                    for name in ('strength', 'agility', 'vitality', 'energy', 'command'):
                        setattr(hero, name, 65535)
                    h, a = vs.write_hero(m, hcase, hero)
                    m.stub(vs.CLASS_INDEX, lambda mm: 5, 0)
                    use_stubs(m, case, h, a)
                    obj = m.alloc(0x20, define=True)
                    m.write(obj, struct.pack('<II', h, h + 0x3254))
                    client = m.call(CAN_USE, [0x82a], ecx=obj) & 0xff
                    keep = []
                    ue = use_env(case, table, keep)
                    ue.skills[0].class_index = 5
                    native = nat.lib.mu_skill_can_use(ctypes.byref(ue), ctypes.byref(hero), 0x82a)
                    fam.check(('confusion', world_has, flag, has_buff), client, native)


def run_world(m, nat, table, records, keys, reqs, rng, fam, cases):
    for n in range(cases):
        case = UseCase(rng, records, reqs)
        base = rng.choice(SPECIAL_BASES + [rng.randint(0, 0x300)])
        m.prepare(force=True)
        vs.common_stubs(m)
        hcase = vs.Case(rng, keys)
        h, a = vs.write_hero(m, hcase, vs.HeroC())
        use_stubs(m, case, h, a)
        m.stubs.pop(WORLD_OK, None)
        client = m.call(WORLD_OK, [base], ecx=DUMMY) & 0xff
        keep = []
        ue = use_env(case, table, keep)
        fam.check((n, case.world, base), client, nat.lib.mu_skill_world_ok(ctypes.byref(ue), base))


def run_marker(m, nat, rng, fam, cases):
    for n in range(cases):
        elem = rng.randint(0, 7)
        entry = (rng.choice([0, 300, 41]), rng.choice([0, 0, 41, 330]), rng.choice([0, 1]))
        dtype, learned = rng.choice([0, 0, 1, 2, 3, -1]), rng.choice([0, 41])
        x, y, w, h = (vs.cm.f32(rng.uniform(0, 600)) for _ in range(4))
        cw, ch = rng.choice([(17.0, 17.0), (21.0, 23.0), (20.0, 28.0)])
        m.prepare(force=True)
        vs.common_stubs(m)
        draws = []
        m.stub(0x0184a990, lambda mm: 0, 0)
        m.stub(0x0184a7f3, lambda mm: 0, 0)
        m.stub(0x0184dcb1, lambda mm: draws.append((s32(mm.args(1)[0]),) + tuple(round(cm.bits_f(v), 6)
                                                                                for v in mm.args(9)[1:9])) or 0, 0)
        mgr = m.alloc(0x100, define=True)
        m.put32(mgr + 8, elem)
        e = m.alloc(0x10, define=True)
        m.write(e, struct.pack('<ii', entry[0], entry[1]) + bytes([entry[2]]) + bytes(7))
        fl = [cm.fbits(v) for v in (x, y, cw, ch, w, h)]
        m.call(MARKER, [e] + fl, ecx=mgr)
        tp, ln = m.alloc(8, define=True), m.alloc(8, define=True)
        m.put32(tp, dtype)
        m.put32(ln, learned)
        m.call(DAMAGE_TYPE, [tp, ln] + fl, ecx=mgr)
        native = []
        q = QuadC()
        ent = EntryC(entry[0], entry[1], entry[2])
        if nat.lib.mu_skill_stamp_marker(elem, ctypes.byref(ent), x, y, cw, ch, w, h, ctypes.byref(q)):
            native.append((q.bitmap,) + tuple(round(cm.f32(v), 6) for v in (q.x, q.y, q.w, q.h, q.u, q.v, q.uw, q.vh)))
        if nat.lib.mu_skill_damage_type_icon(dtype, learned, x, y, cw, ch, w, h, ctypes.byref(q)):
            native.append((q.bitmap,) + tuple(round(cm.f32(v), 6) for v in (q.x, q.y, q.w, q.h, q.u, q.v, q.uw, q.vh)))
        fam.check(n, draws, native)


FAMILIES = ['list', 'keys', 'stamp', 'canuse', 'world', 'marker']
MUTANTS = {12: 'list', 13: 'stamp', 14: 'list', 15: 'list', 19: 'canuse', 20: 'canuse'}


def run_all(m, nat, snap, args, families, report, rng, quiet=False):
    records = vs.snapshot_records(snap)
    keys = [r.index for r in records]
    table = nat.table(records)
    reqs = {row[0]: row for row in plain.read_skillreq(snap)}     # key, +0, +4 skill, +8, +0xc, +0x10, +0x14, +0x18
    reqs = {k: (v[0], v[2], v[3], v[4], v[5], v[6], v[7]) for k, v in reqs.items()}
    for name in families:
        # prepare() restores memory, not hooks. The packet families replace CAN_USE with a case answer;
        # without clearing client stubs, a later canuse family compares C with that old answer instead of
        # executing 0x010918c7. Each family must establish its own modelled boundaries.
        m.stubs = {address: entry for address, entry in m.stubs.items() if entry[0] == 'import'}
        fam = vs.Family(name)
        if name == 'list':
            run_list(m, nat, table, records, keys, rng, fam, args.cases)
        elif name == 'keys':
            run_keys(m, nat, table, records, keys, rng, fam, args.cases)
        elif name == 'stamp':
            run_stamp(m, nat, rng, fam, args.cases)
        elif name == 'canuse':
            run_canuse(m, nat, table, records, keys, reqs, rng, fam, args.cases*4)
        elif name == 'world':
            run_world(m, nat, table, records, keys, reqs, rng, fam, args.cases)
        elif name == 'marker':
            run_marker(m, nat, rng, fam, args.cases)
        else:
            raise SystemExit(f'unknown family {name}')
        report['families'][fam.name] = fam.summary()
        if not quiet:
            print(fam.name, json.dumps({k: v for k, v in fam.summary().items()
                                        if k not in ('examples', 'samples') or args.verbose}), flush=True)


def mutations(m, snap, args, families, work):
    out = {}
    for number, family in MUTANTS.items():
        if family not in families:
            continue
        ext = 'dylib' if sys.platform == 'darwin' else 'so'
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/skill'), f'mutant{number}.{ext}'], check=True)
        nat = ServerNative(work, ROOT/f'reconstructed/skill/mutant{number}.{ext}')
        report = {'families': {}}
        small = argparse.Namespace(**vars(args))
        small.cases = min(args.cases, 200)
        run_all(m, nat, snap, small, [family], report, random.Random(args.seed + number), quiet=True)
        out[f'mutant{number}:{family}'] = sum(f['mismatches'] for f in report['families'].values()) > 0
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--snapshot', default=os.environ.get('SNAP'), help='langread snapshot (local)')
    parser.add_argument('--text', default=pins.TEXT.default_str())
    parser.add_argument('--data', default=pins.DATA.default_str())
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--cases', type=int, default=500)
    parser.add_argument('--families', default=','.join(FAMILIES))
    parser.add_argument('--mutations', action='store_true', help='check that planted mistakes are caught')
    parser.add_argument('--output')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    text = pins.TEXT.read(args.text, exit=True)
    data = pins.DATA.read(args.data, exit=True)
    if not args.snapshot:
        raise SystemExit('--snapshot (or SNAP) is required')
    snap = plain.Snapshot.load(args.snapshot)
    m = vl.LangMachine(text, data, snap)
    families = [f for f in args.families.split(',') if f]
    report = {'text_sha256': vl.TEXT_SHA256, 'data_sha256': vl.DATA_SHA256, 'seed': args.seed, 'families': {}}
    with tempfile.TemporaryDirectory() as work:
        nat = ServerNative(work)
        run_all(m, nat, snap, args, families, report, random.Random(args.seed))
        if args.mutations:
            report['mutations'] = mutations(m, snap, args, families, work)
            print('mutations', json.dumps(report['mutations']))
    report['mismatches'] = sum(f['mismatches'] for f in report['families'].values())
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    for name, fam in report['families'].items():
        if fam['mismatches']:
            print(name, json.dumps(fam['examples'][:2])[:3000])
    print('total cases', sum(f['cases'] for f in report['families'].values()), 'mismatches', report['mismatches'])
    if report['mismatches'] or (args.mutations and not all(report['mutations'].values())):
        sys.exit(1)


if __name__ == '__main__':
    main()
