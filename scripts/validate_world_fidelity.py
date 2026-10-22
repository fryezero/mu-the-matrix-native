#!/usr/bin/env python3
"""Compare NATIVE-FIDELITY-002's world reconstructions with the client's instructions in Unicorn.

Sections:
  scene   the terrain and first object passes of the main render scene 0x0185916b, the slice
          0x018597c2..0x0185985e: which of RenderTerrain(0) 0x016cd468 and RenderObjects 0x016d5020 run, in which
          order, per world (Icarus, world 10, draws no terrain). Executed as client code: the predicates 0x00deeaff
          ([0x01ec9188]), 0x00e94004 (world 0x3f) and 0x00e3068f (0x52..0x5a). Stubs (recorded): RenderTerrain,
          RenderObjects, the Kanturu event singleton 0x009a6ef3 and its state 0x009a645f (answer chosen per case).
          C: reconstructed/terrain mu_terrain_scene_passes.

Each section also runs planted mistakes (--mutations): a library built with one deliberate change must disagree.

Usage:
  scripts/validate_world_fidelity.py [--text client-text.bin --data client-image-data.bin] [--cases N]
      [--only scene] [--mutations] [--output report.json]
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import actor_machine as am  # noqa: E402
import validate_object_render as vor  # noqa: E402

SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
WORLD = 0x01cf15fc
TOP_FLAG = 0x01ec9188
FAKE = 0x41004000
RENDER_TERRAIN, RENDER_OBJECTS = 0x016cd468, 0x016d5020
SCENE_SLICE = (0x018597c2, 0x0185985e)
BODIES = {
    'render_scene_terrain_slice': SCENE_SLICE,
    'top_flag_0x00deeaff': (0x00deeaff, 0x00deeb13),
    'world_3f_0x00e94004': (0x00e94004, 0x00e94018),
    'world_52_5a_0x00e3068f': (0x00e3068f, 0x00e306b5),
}


class Libraries:
    def __init__(self, terrain):
        self.terrain = ctypes.CDLL(str(terrain))
        self.terrain.mu_terrain_scene_passes.argtypes = [ctypes.c_int32, ctypes.c_int, ctypes.c_int]
        self.terrain.mu_terrain_scene_passes.restype = ctypes.c_uint32


def decode_calls(packed):
    out = []
    while packed:
        out.append({1: 'terrain', 2: 'objects'}.get(packed & 3, f'?{packed & 3}'))
        packed >>= 2
    return out


# ---------------------------------------------------------------- scene

INTERESTING_WORLDS = [-1, 0, 1, 2, 3, 4, 7, 8, 9, 10, 0x27, 0x3e, 0x3f, 0x40, 0x51, 0x52, 0x56, 0x5a, 0x5b, 0x83,
                      0x84, 0x85, 0x8d]


def family_scene(machine, libs, g, cases):
    t = vor.Tally('scene')
    for n in range(cases):
        world = g.choice(INTERESTING_WORLDS + [g.randrange(-3, 260), g.randrange(-2**31, 2**31)])
        top = g.choice([0, 0, 0, 1, g.randrange(1, 2**32)])
        kanturu = g.choice([0, 1])
        calls = []

        def record(name, cleanup=0):
            def stub(m):
                calls.append((name, m.argument(0) if name == 'terrain' else None))
                return (0, cleanup)
            return stub

        def kanturu_state(m):
            calls.append(('kanturu-state', m.uc.reg_read(m.x86.UC_X86_REG_ECX)))
            return kanturu   # al: 1 hides the terrain
        stubs = {RENDER_TERRAIN: record('terrain'), RENDER_OBJECTS: record('objects'),
                 0x009a6ef3: lambda m: (calls.append(('kanturu-singleton', None)), FAKE)[1],
                 0x009a645f: kanturu_state}
        regions = [am.defined_region('world', WORLD, struct.pack('<i', world), writable=False),
                   am.defined_region('top-flag', TOP_FLAG, struct.pack('<I', top & 0xffffffff), writable=False)]
        result = vor.run(machine, SCENE_SLICE[0], [], regions, stubs, until=SCENE_SLICE[1])
        stop = vor.stopped_reason(result)
        detail = {'case': n, 'world': world, 'top_flag': top, 'kanturu_hides': kanturu}
        if stop:
            t.add(False, detail, stop)
            continue
        client = [c[0] for c in calls if c[0] in ('terrain', 'objects')]
        terrain_args = {c[1] for c in calls if c[0] == 'terrain'}
        native = decode_calls(libs.terrain.mu_terrain_scene_passes(world, 1 if top else 0, kanturu))
        ok = client == native and terrain_args <= {0}
        detail.update({'client': client, 'native': native})
        t.count('terrain drawn' if 'terrain' in client else 'no terrain')
        t.count(f'world {world:#x}' if world in (10, 0x84, -1, 0x27, 0x3f, 0x52) else 'other world')
        if any(c[0] == 'kanturu-state' for c in calls):
            t.count('kanturu state asked')
        t.add(ok, detail)
    return t


FAMILIES = {'scene': family_scene}

MUTATIONS = [
    ('Icarus draws the terrain', 'terrain/terrain.c', '} else if (w != 0xa && w != 0x84 && w != -1) {',
     '} else if (w != 0x84 && w != -1) {', 'scene'),
    ('objects first only in 0x3f', 'terrain/terrain.c',
     'const int objects_first = w == 0x3f || (w >= 0x52 && w <= 0x5a);', 'const int objects_first = w == 0x3f;',
     'scene'),
]


def build(directory):
    subprocess.run(['make', '-s', '-C', str(directory / 'terrain')], check=True)
    return directory / 'terrain' / f'libterrain.{SUFFIX}'


def mutations(machine, args):
    out = []
    for label, file, old, new, family in MUTATIONS:
        scratch = Path(tempfile.mkdtemp(prefix='worldfid-mut-'))
        try:
            for name in ('terrain', 'record-math'):
                shutil.copytree(ROOT / 'reconstructed' / name, scratch / name,
                                ignore=shutil.ignore_patterns('*.dylib', '*.so', '__pycache__'))
            path = scratch / file
            source = path.read_text()
            if old not in source:
                out.append({'mutation': label, 'error': 'pattern not found'})
                continue
            path.write_text(source.replace(old, new, 1))
            libs = Libraries(build(scratch))
            tally = FAMILIES[family](machine, libs, random.Random(args.seed + 17), args.mutation_cases)
            out.append({'mutation': label, 'family': family, 'cases': tally.cases,
                        'detected': tally.cases - tally.equal - tally.stopped})
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    evidence = ROOT / 'evidence'
    if not evidence.exists():   # a worktree: the main checkout keeps the pinned captures
        evidence = Path.home() / 'Documents/main-exe-study/evidence'
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(evidence / 'x86-text-capture-09/client-text.bin')))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(
        evidence / 'image-data-run10/data-capture-10/client-image-data.bin')))
    parser.add_argument('--cases', type=int, default=500)
    parser.add_argument('--seed', type=int, default=0x0f1d)
    parser.add_argument('--only', default=None)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--mutation-cases', type=int, default=300)
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second image section')
    bodies = {name: {'start': hex(s), 'end_exclusive': hex(e),
                     'sha256': hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
              for name, (s, e) in BODIES.items()}
    machine = vor.Machine(text, data)
    libs = Libraries(build(ROOT / 'reconstructed'))
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'bodies': bodies, 'seed': args.seed,
              'families': {}}
    names = args.only.split(',') if args.only else list(FAMILIES)
    ok = True
    for name in names:
        tally = FAMILIES[name](machine, libs, random.Random(args.seed + zlib.crc32(name.encode()) % 1000), args.cases)
        r = tally.report()
        report['families'][name] = r
        ok = ok and r['mismatch_count'] == 0 and r['stopped'] == 0
        print(f"{name}: {r['equal']}/{r['cases']} equal, {r['stopped']} stopped, coverage {r['coverage']}")
        if r['examples']:
            print('  example:', json.dumps(r['examples'][0], default=str)[:600])
    if args.mutations:
        report['mutations'] = mutations(machine, args)
        for m in report['mutations']:
            print(f"mutation '{m['mutation']}': {m.get('detected')}/{m.get('cases')} detected {m.get('error', '')}")
        ok = ok and all(m.get('detected', 0) > 0 for m in report['mutations'] if m.get('family') in names)
    report['ok'] = ok
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    print('ALL PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
