#!/usr/bin/env python3
"""Compare what a numbered teleport clears with reconstructed/map/map_clear.c (PLAY-FIX-001).

Families (original instructions under Unicorn, the authored C through ctypes):
  teleport_clears   ReceiveTeleport 0x0128136d..0x012818ac (the height block 0x0128152c..0x012816f2 skipped as in
                    validate_map_polish.py): the order of ClearItems 0x017ea38b, ClearCharacters 0x0137c276 and
                    its argument (HeroKey 0x06fca288), 0x00fcf496, ClearWorldMap 0x00c6b292 and LoadWorld.
  plates_hidden     0x009dacb8 over worlds -16..1023 and random words.
  clear_characters  ClearCharacters 0x0137c276 over 400 CharactersClient records and the 10 owned objects: every
                    Live store (0x009b0451 calls), removeInfo 0x009a176b, 0x0098294d, 0x00c9321b and the 16-call
                    tail per record, with their this/arguments, and the Live bytes afterwards.
  clear_items       ClearItems 0x017ea38b with hudPlayerName's 0x00c841cf executed: clearAllItem and the list
                    clears for each handler/list state, the 1,000 item Live stores.

Modelled (stubs): the CharactersClient getter 0x0095f6db, the object release 0x009b0451, removeInfo, the
release/detach/tail callees, the smart-pointer getter of 0x01d22c60, the item list emptiness tests 0x00c898d9 /
0x00c89902, the movie invoke 0x00c8f9e8 and list clears.  The original instructions make every compared decision.
No client bytes are embedded or modified.
"""
import argparse
import ctypes
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402
import client_ui_machine as cm  # noqa: E402
import validate_lang as vl  # noqa: E402
import validate_map as vm  # noqa: E402

MAPDIR = ROOT / 'reconstructed/map'
CHARS, HOLDER, GETTER = 0x08000000, 0x07f00000, 0x07f01000
RECORD, OBJECT = 0x3670, 0x3254
OWNED, OWNED_SIZE = 0x0bdc3220, 0x3d8
ITEMS, ITEM_SIZE = 0x0b4781f8, 0x560
HERO_KEY, SCENE = 0x06fca288, 0x01d1df70
HANDLER = 0x07f02000
TAIL = ((0x00b990b0, 'get'), (0x00eb1015, 8), (0x009c2aea, 'get'), (0x009b9f1f, 8), (0x00a0b72b, 0),
        (0x009c104e, 'get'), (0x0106ba49, 4), (0x013bb41e, 4), (0x013bb435, 4), (0x0137aafe, 0), (0x009ebf04, 0),
        (0x0142ec9d, 0), (0x01553af0, 0), (0x015ae627, 4), (0x016928cd, 4), (0x01536055, 0))
TAIL_ARGS = {0x00eb1015: 2, 0x009b9f1f: 2, 0x00a0b72b: 0, 0x0106ba49: 1, 0x013bb41e: 1, 0x013bb435: 1,
             0x0137aafe: 3, 0x009ebf04: 1, 0x0142ec9d: 1, 0x01553af0: 1, 0x015ae627: 1, 0x016928cd: 1,
             0x01536055: 2}
THIS = {0x00eb1015, 0x009b9f1f, 0x00a0b72b, 0x0106ba49, 0x013bb41e, 0x013bb435, 0x015ae627, 0x016928cd}
KILL, REMOVE, RELEASE, OWN, DETACH, RESET = range(1, 7)


class Slot(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('key', ctypes.c_int16)]


class Owned(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('owner', ctypes.c_int32)]


class Event(ctypes.Structure):
    _fields_ = [('kind', ctypes.c_int32), ('slot', ctypes.c_int32), ('index', ctypes.c_int32)]


class Native:
    def __init__(self, mutation=0, work=None):
        suffix = 'dylib' if sys.platform == 'darwin' else 'so'
        if mutation:
            lib = Path(work) / f'libmapclear-m{mutation}.{suffix}'
            subprocess.run(['cc', '-std=c11', '-O2', '-fPIC', '-shared', f'-DMU_MAP_CLEAR_MUTATION={mutation}',
                            str(MAPDIR / 'map_gate.c'), str(MAPDIR / 'map_clear.c'), '-o', str(lib)], check=True)
        else:
            subprocess.run(['make', '-s', '-C', str(MAPDIR)], check=True)
            lib = MAPDIR / f'libmap.{suffix}'
        L = self.L = ctypes.CDLL(str(lib))
        L.mu_map_plates_hidden.argtypes = [ctypes.c_int32]
        L.mu_teleport_parse.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(vm_teleport())]
        L.mu_teleport_clears.argtypes = [ctypes.POINTER(vm_teleport()), ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
        L.mu_map_clear_characters.argtypes = [ctypes.POINTER(Slot), ctypes.c_int32, ctypes.POINTER(Owned),
                                              ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
                                              ctypes.c_int32, ctypes.POINTER(Event), ctypes.c_int32]
        L.mu_map_clear_items.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_uint8),
                                         ctypes.c_int32]


_TELEPORT = None


def vm_teleport():
    global _TELEPORT
    if _TELEPORT is None:
        class Teleport(ctypes.Structure):
            _fields_ = [('number', ctypes.c_uint16), ('world', ctypes.c_uint16),
                        ('x', ctypes.c_uint8), ('y', ctypes.c_uint8), ('dir', ctypes.c_uint8)]
        _TELEPORT = Teleport
    return _TELEPORT


def redirect(m, address):
    m.uc.reg_write(cm.UC_X86_REG_EIP, address)
    return cm.REDIRECT


def ecx(m):
    return m.uc.reg_read(cm.UC_X86_REG_ECX)


# ---- teleport_clears ------------------------------------------------------------------------------------------

def run_teleports(text, data, native, cases, seed):
    m = cm.Machine(text, data)
    m.allow((0x0128136d, 0x012818ac), (0x0191c5a0, cm.function_extent(text, 0x0191c5a0)),
            (0x00cfc922, cm.function_extent(text, 0x00cfc922)))
    log = []
    m.stub(0x00ac3bf7, lambda mm: vm.FAKE, 0)
    m.stub(0x00c0818e, lambda mm: 0, 0)
    m.stub(0x017ea38b, lambda mm: log.append(('items',)) or 0, 0)
    m.stub(0x0137c276, lambda mm: log.append(('chars', mm.args(1)[0])) or 0, 0)
    m.stub(0x00fcfca4, lambda mm: 0x07f03000, 0)
    m.stub(0x00fcf496, lambda mm: log.append(('others', ecx(mm))) or 0, 0)
    m.stub(0x0128152c, lambda mm: redirect(mm, 0x012816f2))

    def map_getter(mm):
        out, = mm.args(1)
        mm.put32(out, vm.FAKE + 0x500)
        return out
    m.stub(0x009fd699, map_getter, 4)

    def other_getter(mm):
        out, = mm.args(1)
        mm.put32(out, 0)
        return out
    m.stub(0x00a980e8, other_getter, 4)
    m.stub(0x00c6b292, lambda mm: log.append(('clear',)) or 0, 0)
    m.stub(0x0182876e, lambda mm: log.append(('load', mm.args(1)[0])) or 0, 0)
    for address in (0x0128174b, 0x01281ca2, 0x012818ac):
        m.stub(address, lambda mm: redirect(mm, cm.RETURN_SENTINEL))
    L, T = native.L, vm_teleport()
    rng = random.Random(seed)
    fam = vl.Family('teleport_clears')
    names = {1: 'items', 2: 'chars', 3: 'others', 4: 'clear', 5: 'load'}
    for k in range(cases):
        m.reset()
        log.clear()
        vl.crt_state(m)
        current = rng.choice([0, 2, 3, 8, 10, 132, 142, rng.randrange(65536)])
        world = current if k % 3 == 0 else rng.randrange(65536)
        number = 0 if k % 4 == 0 else rng.randrange(1, 65536)
        hero_key = rng.choice([0, 1, 0x1234, 0x7fff, 0x8000, 0xffff, rng.randrange(1 << 32)])
        x, y, direction = (rng.randrange(256) for _ in range(3))
        p = struct.pack('<4BHH3B', 0xc3, 11, 0x1c, 0, number, world, x, y, direction)
        packet = m.alloc(len(p), define=True)
        m.write(packet, p)
        hero = m.alloc(0x3800, define=True)
        m.put32(vm.HERO_PTR, hero)
        m.put32(vm.WORLD, current)
        m.put32(0x01cf1600, current)
        m.put32(HERO_KEY, hero_key)
        m.put32(vm.FAKE + 0xd4, vm.FAKE + 0x400)
        m.call(0x0128136d, (packet, 1))
        t = T()
        assert L.mu_teleport_parse(p, len(p), ctypes.byref(t))
        kinds = (ctypes.c_int32 * 5)()
        n = L.mu_teleport_clears(ctypes.byref(t), current, kinds)
        expected = []
        for kind in kinds[:n]:
            expected.append({'chars': ('chars', hero_key), 'others': ('others', 0x07f03000),
                             'load': ('load', t.world)}.get(names[kind], (names[kind],)))
        fam.check(k, log[:], expected)
    return fam


# ---- plates_hidden --------------------------------------------------------------------------------------------

def run_hidden(text, data, native, seed):
    m = cm.Machine(text, data)
    m.allow((0x009dacb8, 0x009dacdb))
    fam = vl.Family('plates_hidden')
    rng = random.Random(seed)
    for world in [*range(-16, 1024), *(rng.randrange(1 << 32) for _ in range(500))]:
        m.reset()
        client = m.call(0x009dacb8, (world,)) & 0xff
        fam.check(world, client, native.L.mu_map_plates_hidden(ctypes.c_int32(world).value))
    return fam


# ---- clear_characters -----------------------------------------------------------------------------------------

def char(i):
    return CHARS + i * RECORD


def run_characters(text, data, native, cases, seed):
    m = cm.Machine(text, data)
    m.heap_checks(False)
    m.allow((0x0137c276, 0x0137c457), (0x009a13f4, 0x009a1421), (0x0095f977, 0x0095f986),
            (0x0129f4a5, 0x0129f4cb), (0x009b0bc1, 0x009b0bcf), (0x009dacb8, 0x009dacdb))
    log = []
    m.stub(0x0095f6db, lambda mm: HOLDER, 0)
    m.stub(0x009b0451, lambda mm: log.append(('off', ecx(mm))) or 0, 0)
    m.stub(0x009a176b, lambda mm: log.append(('remove', ecx(mm), mm.args(1)[0])) or 0, 4)
    m.stub(0x0098294d, lambda mm: log.append(('release', mm.args(1)[0])) or 0, 0)
    m.stub(0x00c9321b, lambda mm: log.append(('detach', mm.args(1)[0])) or 0, 0)
    for address, kind in TAIL:
        if kind == 'get':
            m.stub(address, lambda mm, a=address: log.append(('get', a)) or GETTER, 0)
        else:
            def tail(mm, a=address):
                log.append(('tail', a, ecx(mm) if a in THIS else None, tuple(mm.args(TAIL_ARGS[a]))))
                return 0
            m.stub(address, tail, kind)
    rng = random.Random(seed)
    fam = vl.Family('clear_characters')
    fam.coverage = {'kills': 0, 'remove_info': 0, 'owned_kills': 0, 'resets': 0, 'remove_hidden_world': 0}
    hidden = [0x12, 0x15, 0x17, 0x35, 0x61]
    for k in range(cases):
        m.reset()
        log.clear()
        density = rng.choice([0.0, 0.05, 0.3, 0.9, 1.0])
        keys = [rng.choice([rng.randrange(-40, 40), rng.randrange(-32768, 32768), 0x1234 - 0x10000 * 0])
                for _ in range(cm_slots())]
        live = [1 if rng.random() < density else 0 for _ in keys]
        hero_slot = rng.randrange(400)
        param = rng.choice([keys[hero_slot], keys[hero_slot] & 0xffff, rng.randrange(-70000, 70000)])
        scene = rng.choice([6, 6, 6, 2, 4, 5, 0])
        world = rng.choice([0, 2, 3, 0x11, 0x18, rng.randrange(300), *hidden])
        for i in range(400):
            m.write(char(i) + 0x3e, struct.pack('<h', keys[i]))
            m.write(char(i) + OBJECT, bytes([live[i]]))
            m.put32(char(i) + 0x31e4, 0x0be10000 + i)
        m.put32(HOLDER + 8, CHARS)
        m.put32(vm.HERO_PTR, char(hero_slot))
        m.put32(vm.WORLD, world)
        m.put32(SCENE, scene)
        owners = []
        for j in range(10):
            kind = rng.random()
            owner = rng.randrange(400) if kind < 0.6 else -1
            ptr = char(owner) + OBJECT if owner >= 0 else (0 if kind < 0.8 else char(rng.randrange(400)) + 4)
            olive = 1 if rng.random() < 0.7 else 0
            m.write(OWNED + j * OWNED_SIZE, bytes([olive]))
            m.put32(OWNED + j * OWNED_SIZE + 0x34c, ptr)
            owners.append((olive, owner))
        m.call(0x0137c276, (param,))
        client = (log[:], [m.read(char(i) + OBJECT, 1)[0] for i in range(400)],
                  [m.read(OWNED + j * OWNED_SIZE, 1)[0] for j in range(10)])
        slots = (Slot * 400)(*[Slot(live[i], keys[i]) for i in range(400)])
        owned = (Owned * 10)(*[Owned(o, w) for o, w in owners])
        events = (Event * 8000)()
        n = native.L.mu_map_clear_characters(slots, 400, owned, 10, param, scene, world, keys[hero_slot], events, 8000)
        expected = []
        for e in events[:n]:
            c, o = char(e.slot), char(e.slot) + OBJECT
            if e.kind == KILL:
                expected.append(('off', o))
            elif e.kind == REMOVE:
                expected.append(('remove', HOLDER, c))
            elif e.kind == RELEASE:
                expected.append(('release', c))
            elif e.kind == OWN:
                expected.append(('off', OWNED + e.index * OWNED_SIZE))
            elif e.kind == DETACH:
                expected.append(('detach', c))
            elif e.kind == RESET:
                args = {0x00eb1015: (c, 0xffffffff), 0x009b9f1f: (c, 0xffffffff), 0x00a0b72b: (),
                        0x0106ba49: (c,), 0x013bb41e: (0,), 0x013bb435: (0,), 0x0137aafe: (c, o, 0),
                        0x009ebf04: (c,), 0x0142ec9d: (o,), 0x01553af0: (o,), 0x015ae627: (o,), 0x016928cd: (o,),
                        0x01536055: (o, 0)}
                this = {0x00eb1015: GETTER, 0x009b9f1f: GETTER, 0x00a0b72b: 0x0be10000 + e.slot,
                        0x0106ba49: GETTER, 0x013bb41e: c, 0x013bb435: c, 0x015ae627: 0x0a3a9adc,
                        0x016928cd: 0x0a3da070}
                for address, kind in TAIL:
                    expected.append(('get', address) if kind == 'get' else
                                    ('tail', address, this.get(address), args[address]))
        native_state = (expected, [s.live for s in slots], [o.live for o in owned])
        cov = fam.coverage
        cov['kills'] += sum(1 for e in events[:n] if e.kind == KILL)
        cov['remove_info'] += sum(1 for e in events[:n] if e.kind == REMOVE)
        cov['remove_hidden_world'] += sum(1 for e in events[:n] if e.kind == REMOVE and world in hidden)
        cov['owned_kills'] += sum(1 for e in events[:n] if e.kind == OWN)
        cov['resets'] += sum(1 for e in events[:n] if e.kind == RESET)
        fam.check(k, client, native_state)
    return fam


def cm_slots():
    return 400


# ---- clear_items ----------------------------------------------------------------------------------------------

def run_items(text, data, native, rounds):
    m = cm.Machine(text, data)
    m.heap_checks(False)
    m.allow((0x017ea38b, 0x017ea422), (0x00c841cf, 0x00c84222), (0x009a1a51, 0x009a1a74),
            (0x009a1a74, 0x009a1a82), (0x0129f4a5, 0x0129f4cb))
    log, state = [], {}

    def getter(mm):
        out, = mm.args(1)
        mm.put32(out, HANDLER if state['handler'] else 0)
        return out
    m.stub(0x009a19ae, getter, 4)
    m.stub(0x009a1a3c, lambda mm: 0, 0)
    m.stub(0x00c898d9, lambda mm: log.append(('empty_a', ecx(mm))) or state['a'], 0)
    m.stub(0x00c89902, lambda mm: log.append(('empty_b', ecx(mm))) or state['b'], 0)

    def invoke(mm):
        name = bytes(mm.read(mm.args(1)[0], 32)).split(b'\0')[0].decode('latin1')
        log.append(('invoke', ecx(mm), name))
        return 0
    m.stub(0x00c8f9e8, invoke, 4)
    m.stub(0x00c89828, lambda mm: log.append(('clear_a', ecx(mm))) or 0, 0)
    m.stub(0x00afe908, lambda mm: log.append(('clear_b', ecx(mm))) or 0, 0)
    m.stub(0x009b0451, lambda mm: log.append(('off', ecx(mm))) or 0, 0)
    fam = vl.Family('clear_items')
    rng = random.Random(7)
    for r in range(rounds):
        for handler in (0, 1):
            for a in (0, 1):
                for b in (0, 1):
                    m.reset()
                    log.clear()
                    state.update(handler=handler, a=a, b=b)
                    for k in rng.sample(range(1000), 50):
                        m.write(ITEMS + k * ITEM_SIZE, bytes([rng.randrange(2)]))
                    m.call(0x017ea38b)
                    seen = [e for e in log if e[0] != 'off']
                    offs = [e[1] for e in log if e[0] == 'off']
                    lives = [m.read(ITEMS + k * ITEM_SIZE, 1)[0] for k in range(1000)]
                    client = (seen, offs, sum(lives))
                    buf = (ctypes.c_uint8 * 1000)(*([1] * 1000))
                    invoked = native.L.mu_map_clear_items(handler, a, b, buf, 1000)
                    expected = []
                    if handler:
                        expected.append(('empty_a', HANDLER + 0x60))
                        if a:
                            expected.append(('empty_b', HANDLER + 0x68))
                    if invoked:
                        expected += [('invoke', HANDLER, 'clearAllItem'), ('clear_a', HANDLER + 0x60),
                                     ('clear_b', HANDLER + 0x68)]
                    fam.check((r, handler, a, b), client,
                              (expected, [ITEMS + k * ITEM_SIZE for k in range(1000)], sum(buf)))
    return fam


def run_all(text, data, native, cases, seed):
    return [run_teleports(text, data, native, cases, seed), run_hidden(text, data, native, seed),
            run_characters(text, data, native, max(cases // 5, 20), seed), run_items(text, data, native, 3)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text', default=pins.TEXT.default_str())
    p.add_argument('--data', default=pins.DATA.default_str())
    p.add_argument('--cases', type=int, default=500)
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    text, data = pins.TEXT.read(a.text, exit=True), pins.DATA.read(a.data, exit=True)
    families = run_all(text, data, Native(), a.cases, a.seed)
    report = {'text_sha256': vl.TEXT_SHA256, 'data_sha256': vl.DATA_SHA256,
              **{f.name: {**f.summary(), **({'coverage': f.coverage} if hasattr(f, 'coverage') else {})}
                 for f in families}}
    mismatches = sum(f.mismatches for f in families)
    if a.mutations:
        with tempfile.TemporaryDirectory() as work:
            report['mutations'] = {}
            for k in range(1, 7):
                fams = run_all(text, data, Native(k, work), 100, a.seed)
                report['mutations'][str(k)] = sum(f.mismatches for f in fams) > 0
        mismatches += sum(1 for v in report['mutations'].values() if not v)
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return int(mismatches != 0)


if __name__ == '__main__':
    sys.exit(main())
