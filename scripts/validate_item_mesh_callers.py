#!/usr/bin/env python3
"""RENDER-ITEMS-002AB: nine low-level callers that draw two meshes themselves below glow level three."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess

import item_mesh_callers as callers
import pins
import validate_item_direct_bodies as direct
import validate_item_groups as groups
import validate_item_quality as quality
import validate_renderchar as v
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = list(callers.TYPES) + list(callers.HELPER_TYPES)
PACKED_WORDS = tuple(range(128)) + (-1, -128, -2147483648, 128, 129, 255, 256, 257, 2147483647)
MUTANTS = {
    'mesh-level': ('} else if (level < 3 && mesh_caller(it->type)) {', '} else if (level < 4 && mesh_caller(it->type)) {'),
    'mesh-level-low': ('} else if (level < 3 && mesh_caller(it->type)) {', '} else if (level < 2 && mesh_caller(it->type)) {'),
    'mesh-texture': ('pass ? mesh_caller(it->type) : -1);', '-1);'),
    'mesh-blend': ('d->blend_mesh = -2;', 'd->blend_mesh = -1;'),
    'mesh-uv': ('d->u = d->v = 0.0f;', 'd->u = 0.0f;'),
    'mesh-alpha': ('emit(&s, MU_RC_ENTRY_MESH, 0, 2u, it->object_alpha, 0, pass ?', 'emit(&s, MU_RC_ENTRY_MESH, 0, 2u, it->alpha, 0, pass ?'),
    'mesh-flags': ('emit(&s, MU_RC_ENTRY_MESH, 0, 2u, it->object_alpha, 0, pass ?', 'emit(&s, MU_RC_ENTRY_MESH, 0, it->render_type, it->object_alpha, 0, pass ?'),
    'helper-light': ('model->body_light[k] = L[k];\n        part_body(&s, it->alpha, rt, 3, -1);\n        emit(',
                     'model->body_light[k] = L[k] * 0.9f;\n        part_body(&s, it->alpha, rt, 3, -1);\n        emit('),
    # The helper's last two arguments (3, -1) do not reach its default body draw, so they have no mutant.
    'helper-flags': ('part_body(&s, it->alpha, rt, 3, -1);\n        emit(', 'part_body(&s, it->alpha, rt | 0x40u, 3, -1);\n        emit('),
    'helper-body-alpha': ('part_body(&s, it->alpha, rt, 3, -1);\n        emit(', 'part_body(&s, it->object_alpha, rt, 3, -1);\n        emit('),
    'helper-texture': ('emit(&s, MU_RC_ENTRY_MESH, 1, 0x46u, 0.7f, 0, it->object_hidden);', 'emit(&s, MU_RC_ENTRY_MESH, 1, 0x46u, 0.7f, 0, -1);'),
    'helper-texture-zero': ('emit(&s, MU_RC_ENTRY_MESH, 1, 0x46u, 0.7f, 0, it->object_hidden);', 'emit(&s, MU_RC_ENTRY_MESH, 1, 0x46u, 0.7f, 0, 0);'),
    'helper-alpha': ('emit(&s, MU_RC_ENTRY_MESH, 1, 0x46u, 0.7f, 0, it->object_hidden);', 'emit(&s, MU_RC_ENTRY_MESH, 1, 0x46u, it->object_alpha, 0, it->object_hidden);'),
    'helper-swap': ('helper_mesh_caller(it->type) == 2 && s.count', 'helper_mesh_caller(it->type) == 3 && s.count'),
    'mesh-order': ('for (int pass = 0; pass < 2; ++pass) {\n            emit(&s, MU_RC_ENTRY_MESH',
                   'for (int pass = 1; pass >= 0; --pass) {\n            emit(&s, MU_RC_ENTRY_MESH'),
}


def original_sites(wa):
    """Each type's two draws return to its own read case below glow level three, and to no case from it on."""
    sites = {}
    for start, body, end, members, texture in callers.GROUPS:
        for t in members:
            sites[t] = (body, end)
    seen = []

    class World(quality.RandomWorld):
        def install(self):
            super().install()
            old, cleanup = self.m.stubs[0x00966e4a]

            def mesh(m, old=old):
                seen.append(m.r32(m.uc.reg_read(m.x86.UC_X86_REG_ESP)))
                return old(m)
            self.m.stub(0x00966e4a, mesh, cleanup)
    reset = ResetWorld(wa, World)
    lib = C.CDLL(str(v.LIBRARY))
    rows = []
    textures = callers.read(wa)
    for start, end, t, swap in callers.HELPER_GROUPS:
        sites[t] = (start, end)
    for t in TYPES:
        body, end = sites[t]
        sides = set()
        for packed, record, q, render_type in ((0, (0, 0, 0), 9, 2), (16, (0, 0, 0), 9, 2),
                                               (23, (0, 0, 0), 9, 0x102), (24, (0, 0, 0), 9, 2),
                                               (56, (0, 0, 0), 9, 2), (104, (0, 0, 0), 9, 2),
                                               (104, (0, 0, 0), 9, 0x402), (0, (0, 0x26, 0), 9, 2),
                                               (0, (0, 0x26, 0), 0, 2)):
            case = v.classify_case(t, v.CLASSIFY[0])
            case.update(item_level=packed, record=record, quality=q, render_type=render_type)
            seen.clear()

            def factory(*args):
                world = reset(*args)
                world.sequence, world.drawn = [0] * 64, 0
                return world
            result, stream, other, _ = v.client_stream(wa, case, factory)
            inside = [site for site in seen if body <= site < end]
            status, actual = v.c_stream(lib, case)
            # The C stream holds the case's textured second draw exactly when the original ran the case.
            low = (len(actual) >= 2 and actual[1][0] == 'MESH' and actual[1][1][7] == textures[t]
                   if t in textures else
                   len(actual) >= 3 and [draw[0] for draw in actual[:3]] == ['BODY', 'MESH', 'MESH'] and
                   actual[2][1][1] == 0x46)
            if (not result['ok'] or other or status or actual != stream or
                    len(inside) != (2 if low else 0) or inside != seen[:len(inside)]):
                raise AssertionError(('original site', hex(t), packed, record, q, render_type, low,
                                      [hex(site) for site in seen], status))
            sides.add(low)
            rows.append({'type': hex(t), 'packed': packed, 'quality': q, 'record': record[1],
                         'render_type': render_type, 'low': low, 'draws': len(stream)})
        if sides != {True, False}:
            raise AssertionError(('one-sided caller probes', hex(t)))
    return {'cases': len(rows), 'mismatches': 0, 'rows': rows}


def reader_refusals(wa):
    refused = 0

    def patched(address, payload):
        copy = bytearray(wa[0])
        copy[address - 0x401000:address - 0x401000 + len(payload)] = payload
        return (bytes(copy),) + tuple(wa[1:])
    start, body, end, members, texture = callers.GROUPS[0]
    trials = [patched(callers.LEVEL_GATE[0] + 6, b'\x04'),                      # cmp level, 4
              patched(start + 6, (members[0] + 1).to_bytes(4, 'little')),      # another dispatch member
              patched(body + 1, b'\xfe'),                                      # first texture -2
              patched(body + 0x3c + 1, b'\x03'),                               # flags 3
              patched(end - 5, b'\xe9\x00\x00\x00\x00')]                       # another join
    for trial in trials:
        try:
            callers.read(trial)
        except ValueError:
            refused += 1
        else:
            raise AssertionError('mesh caller reader accepted a neighbouring form')
    start, end, t, swap = callers.HELPER_GROUPS[0]
    code = wa[0][start - 0x401000:end - 0x401000]
    helper = [patched(start + code.index(b'\x6a\x03'), b'\x6a\x02'),               # helper flag argument 2
              patched(start + code.index(b'\x6a\x46'), b'\x6a\x42'),               # second draw flags 0x42
              patched(start + 3, (t + 1).to_bytes(4, 'little')),                     # another type
              (wa[0], wa[1][:0x1a7e918 - 0x1a7c000] + b'\0\0\0\x3f' + wa[1][0x1a7e918 - 0x1a7c000 + 4:]) + tuple(wa[2:])]
    for trial in helper:
        try:
            callers.read_helpers(trial)
        except ValueError:
            refused += 1
        else:
            raise AssertionError('helper mesh caller reader accepted a neighbouring form')
    return {'cases': refused, 'mismatches': 0}


def compare(wa, lib, count):
    rows = callers.read(wa)
    if (ROOT/'reconstructed/renderchar/item_mesh_callers.h').read_text() != callers.render(rows, callers.read_helpers(wa)):
        raise AssertionError('item_mesh_callers.h differs from the pinned instructions')
    groups.TYPES = TYPES
    families, vectors = groups.compare(wa, lib, count)
    reset = ResetWorld(wa, quality.RandomWorld)
    before = len(vectors)
    words = PACKED_WORDS if count == 292 else (0, 8, 16, 23, 24, 31, 56, 72, 104, 127, -1)
    for t in TYPES:
        rng = random.Random(0x200b0 + t)
        for packed in words:
            for q in (0, 1, 2, 9):
                for b in (0, 0x26, 0x5b):
                    case = v.random_case_any(rng, t)
                    case.update(item_level=packed, quality=q, record=((packed & 1) * 6, b, 0),
                                render_type=(2, 0x102, 0x40042, 0x402)[(packed + q + b) % 4],
                                a10=0xffffffff, a11=0xffffffff, object_hidden=(0, -1)[(packed >> 1) & 1])
                    sequence = quality.sequence_for(rng)
                    ok, expected, detail = quality.compare(wa, lib, reset, case, sequence)
                    if not ok:
                        raise AssertionError(('levels', hex(t), packed, q, b, case, expected, detail))
                    vectors.append((case, sequence, expected))
    families['levels'] = {'cases': len(vectors) - before, 'mismatches': 0}
    exits = []
    for t in TYPES:
        for _, case in list(quality.state_cases(t))[:64]:
            def factory(*args):
                world = reset(*args)
                world.sequence, world.drawn = [0] * 64, 0
                return world
            result, original_stream, other, machine = v.client_stream(wa, case, factory)
            expected = (tuple(machine.r32(v.MODEL + 0x54 + 4*k) for k in range(3)) +
                        (machine.r32(v.MODEL + 0x40),) +
                        tuple(machine.r32(v.MODEL + 0x44 + 4*k) for k in range(3)) +
                        (machine.read(v.MODEL + 0xca, 1)[0],))
            status, stream, actual = direct.c_model(lib, case)
            if not result['ok'] or other or status or stream != original_stream or actual != expected:
                raise AssertionError(('exits', hex(t), case, expected, actual))
            exits.append((case, expected))
    families['exits'] = {'cases': len(exits), 'mismatches': 0}
    families['original_sites'] = original_sites(wa)
    families['reader_refusals'] = reader_refusals(wa)
    return families, vectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=292)
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.cases <= 292:
        parser.error('--cases must be in 1..292')
    subprocess.run(['make', '-s', '-j2', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    families, vectors = compare(wa, C.CDLL(str(v.LIBRARY)), args.cases)
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': families}
    if args.mutations:
        groups.MUTANTS = MUTANTS
        report['mutants'] = groups.mutations(vectors)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: (val if k != 'families' else {n: {a: b for a, b in f.items() if a != 'rows'}
                                                      for n, f in val.items()}) for k, val in report.items()}))


if __name__ == '__main__':
    main()
