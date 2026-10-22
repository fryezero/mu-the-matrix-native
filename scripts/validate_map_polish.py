#!/usr/bin/env python3
"""Compare bounded teleport and Move registry instructions with the native map code.

The teleport prefix 0x0128136d..0x012818ac runs with the height block
0x0128152c..0x012816f2 explicitly skipped. Stops are the zero-number branch
0x0128174b, same-world branch 0x01281ca2 and immediately after LoadWorld.
Only tile/XY/angle, number/world decisions, ClearWorldMap and LoadWorld order
are compared. Height, later cleanup, effects and other handler branches are
not claimed. LoadingWorld's store is executed separately at 0x01281d28.

Modelled: GFx getter/reset, smart-pointer getters, character cleanup helpers
and LoadWorld. Original instructions perform all compared decisions/stores.
The actual MoveCommand registration argument slice is executed independently.
No client bytes are embedded or modified.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import random
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import client_ui_machine as cm
import validate_gfx3 as gfx
import validate_map as vm
import validate_lang as vl


class Teleport(ctypes.Structure):
    _fields_ = [('number', ctypes.c_uint16), ('world', ctypes.c_uint16),
                ('x', ctypes.c_uint8), ('y', ctypes.c_uint8), ('dir', ctypes.c_uint8)]


def redirect(m, address):
    m.uc.reg_write(cm.UC_X86_REG_EIP, address)
    return cm.REDIRECT


def run_teleports(text, data, native, cases, seed):
    m = cm.Machine(text, data)
    m.allow((0x0128136d, 0x012818ac), (0x01281d28, 0x01281d43),
            (0x0191c5a0, cm.function_extent(text, 0x0191c5a0)),
            (0x00cfc922, cm.function_extent(text, 0x00cfc922)))
    m.stub(0x00ac3bf7, lambda mm: vm.FAKE, 0)
    for address, cleanup in ((0x00c0818e, 0), (0x017ea38b, 0), (0x0137c276, 0),
                             (0x00fcfca4, 0), (0x00fcf496, 0)):
        m.stub(address, lambda mm: 0, cleanup)
    m.stub(0x0128152c, lambda mm: redirect(mm, 0x012816f2))
    log = []

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
    for address in (0x0128174b, 0x01281ca2, 0x012818ac, 0x01281d43):
        m.stub(address, lambda mm: redirect(mm, cm.RETURN_SENTINEL))
    L = native.L
    L.mu_teleport_parse.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(Teleport)]
    L.mu_teleport_position.argtypes = [ctypes.POINTER(Teleport), ctypes.POINTER(ctypes.c_float)]
    L.mu_teleport_angle.argtypes = [ctypes.POINTER(Teleport)]
    L.mu_teleport_angle.restype = ctypes.c_float
    L.mu_teleport_changes_world.argtypes = [ctypes.POINTER(Teleport), ctypes.c_int32]
    rng = random.Random(seed)
    fam = vl.Family('teleport_core')
    for k in range(cases):
        m.reset()
        log.clear()
        vl.crt_state(m)
        current = rng.choice([0, 3, 8, 10, 132, 142, rng.randrange(65536)])
        world = current if k % 3 == 0 else rng.randrange(65536)
        number = 0 if k % 4 == 0 else rng.randrange(1, 65536)
        x, y, direction = (rng.randrange(256) for _ in range(3))
        p = struct.pack('<4BHH3B', 0xc3, 11, 0x1c, 0, number, world, x, y, direction)
        packet = m.alloc(len(p), define=True)
        m.write(packet, p)
        hero = m.alloc(0x3800, define=True)
        obj = hero + 0x3254
        m.put32(vm.HERO_PTR, hero)
        m.put32(vm.WORLD, current)
        m.put32(0x01cf1600, current)
        m.put32(0x06fca288, 0)
        m.put32(vm.FAKE + 0xd4, vm.FAKE + 0x400)
        m.call(0x0128136d, (packet, 1))
        t, pos = Teleport(), (ctypes.c_float * 2)()
        assert L.mu_teleport_parse(p, len(p), ctypes.byref(t))
        L.mu_teleport_position(ctypes.byref(t), pos)
        changed = bool(L.mu_teleport_changes_world(ctypes.byref(t), current))
        client = (m.u32(hero + 0x180), m.u32(hero + 0x184),
                  m.read(obj + 0x158, 8).hex(), m.read(obj + 0x16c, 4).hex(),
                  m.u32(vm.WORLD), m.u32(0x01cf1600), list(log))
        expected = (t.x, t.y, bytes(pos).hex(), struct.pack('<f', L.mu_teleport_angle(ctypes.byref(t))).hex(),
                    t.world if changed else current, t.world if changed else current,
                    [('clear',), ('load', t.world)] if changed else [])
        fam.check(k, client, expected)
        # A numbered reply reaches this store even if the world was unchanged.
        if number:
            m.call(0x01281d28)
            fam.check(('loading', k), m.u32(vm.LOADING_WORLD), 30)
    return fam


def registration(text, data):
    """Run the actual pushes, name construction and registry call at 0x00ac66f8."""
    m = cm.Machine(text, data)
    m.allow((0x00ac66f8, 0x00ac6722))
    m.reset()
    manager = m.alloc(0x400, define=True)
    m.put32(manager + 0x11c, 0x12345678)
    ebp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000
    m.put32(ebp - 0x10, manager)
    m.uc.reg_write(cm.UC_X86_REG_EBP, ebp)
    m.uc.reg_write(cm.UC_X86_REG_ESP, ebp - 0x1000)
    names, result = [], []
    def name(mm):
        names.append(gfx.Values(mm, text).cstr(mm.args(1)[0]))
        mm.put32(mm.uc.reg_read(cm.UC_X86_REG_ECX), 0xabcdef)
        return mm.uc.reg_read(cm.UC_X86_REG_ECX)
    def register(mm):
        result.append(mm.args(5))
        return 1
    m.stub(0x0040c8d0, name, 4)
    m.stub(0x00ac9e28, register, 20)
    m.uc.emu_start(0x00ac66f8, 0x00ac6722, count=100)
    assert not m.errors, m.errors
    assert names == ['MoveCommand'] and result == [[0x12345678, 0, 0xabcdef, 0, 10]], (names, result)
    return {'cases': 1, 'alignment': result[0][-1], 'window': names[0]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(vl.DEFAULT_TEXT)))
    p.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(vl.DEFAULT_DATA)))
    p.add_argument('--cases', type=int, default=500)
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    for path, digest in ((a.text, vl.TEXT_SHA256), (a.data, vl.DATA_SHA256)):
        if vl.sha256_file(path) != digest:
            raise SystemExit(f'{path}: unexpected SHA-256')
    text, data = Path(a.text).read_bytes(), Path(a.data).read_bytes()
    fam = run_teleports(text, data, vm.Native(), a.cases, a.seed)
    report = {'text_sha256': vl.TEXT_SHA256, 'data_sha256': vl.DATA_SHA256,
              'teleport_core': fam.summary(), 'registration': registration(text, data)}
    if a.mutations:
        with tempfile.TemporaryDirectory() as work:
            report['mutations'] = {str(k): run_teleports(text, data, vm.Native(k, work), 60, a.seed).mismatches > 0
                                   for k in (11, 12, 13)}
        assert all(report['mutations'].values()), report['mutations']
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return int(fam.mismatches != 0)


if __name__ == '__main__':
    sys.exit(main())
