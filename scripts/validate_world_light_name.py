#!/usr/bin/env python3
"""Primary terrain-light file of the Kubera Mine worlds (RENDER-WORLDS-Q) against pinned instructions.

OpenWorld 0x0182876e, after the world-30 (0x0095fb7c) and world-0x22 branches, asks the Kubera Mine
predicate 0x00e1e4b6 for the world global. When it holds, the light path is sprintf("%s\\%s", folder,
name) with the name the Kubera handler's routine 0x00e18e27(out, world) builds; otherwise it is
"%s\\TerrainLight.bmp". Both routines run here as original instructions for every world -5..300. In
0x00e18e27 the std::string helpers are recording stubs: the constructor 0x008e6d00 and destructor
0x008e83a0 do nothing, the assignment 0x0094afda records its C string and the copy into the result
0x008e7410 is recorded. The expected stem must equal mu_terrain_light_name(world) (reconstructed/terrain).
Worlds 30 and 0x22 take earlier branches (event and Crywolf variants, not modelled) and are reported apart.
--mutations plants compiled changes in reconstructed/terrain/terrain.c and requires each to be detected.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import actor_machine as am
import validate_object_render as v
import pins
ROOT = Path(__file__).resolve().parents[1]
NAME, KUBERA, WORLD30 = 0x00e18e27, 0x00e1e4b6, 0x0095fb7c
CTOR, ASSIGN, COPY, DTOR = 0x008e6d00, 0x0094afda, 0x008e7410, 0x008e83a0
BODIES = {'light_name': (0x00e18e27, 0x00e18efb), 'kubera_predicate': (0x00e1e4b6, 0x00e1e4cd),
          'world30_predicate': (0x0095fb7c, 0x0095fb99), 'open_world_light': (0x01828dc7, 0x01828f13)}
OUT = v.OUT
NOT_MODELLED = (30, 0x22)


def read_string(m, address, limit=260):
    return bytes(m.uc.mem_read(address, limit)).split(b'\0', 1)[0].decode('latin-1')


def predicate(machine, start, world):
    r = v.run(machine, start, [world & 0xffffffff], v.global_regions(world), {}, cleanup=0)
    return (r['eax'] & 255 if r['ok'] else None), v.stopped_reason(r)


def light_name(machine, world):
    calls = []
    stubs = {CTOR: lambda m: 0, DTOR: lambda m: 0,
             ASSIGN: lambda m: calls.append(('assign', read_string(m, m.argument(0)))) or 0,
             COPY: lambda m: calls.append(('copy',)) or OUT}
    r = v.run(machine, NAME, [OUT, world & 0xffffffff], v.global_regions(world,
              extra=[am.undefined_region('out', OUT, 0x20)]), stubs, ecx=v.FAKE, cleanup=8)
    if not r['ok']:
        return None, v.stopped_reason(r)
    assigned = [c[1] for c in calls if c[0] == 'assign']
    assert calls[-1] == ('copy',) and len(assigned) <= 1, calls
    return (assigned[0] if assigned else ''), None


MUTANTS = [('case 0x7b: return "TerrainLight_Fire"', 'case 0x7a: return "TerrainLight_Fire"'),
           ('case 0x7c: return "TerrainLight_Water"', 'case 0x7c: return "TerrainLight_Earth"'),
           ('case 0x7f: return "TerrainLight_Dark"', 'case 0x80: return "TerrainLight_Dark"'),
           ('default: return "TerrainLight";', 'default: return "TerrainLight_2";')]


def compare(machine, lib, observed):
    """One pass over worlds -5..300 against `lib`; observed caches the original's answers."""
    tally = v.Tally('light_name')
    names, old_rule_mismatches, skipped = {}, 0, []
    for world in range(-5, 301):
        if world not in observed:
            kubera, stop = predicate(machine, KUBERA, world)
            early, stop2 = predicate(machine, WORLD30, world)
            name, stop3 = light_name(machine, world)
            observed[world] = (kubera, early, name, stop or stop2 or stop3)
        kubera, early, name, stop = observed[world]
        if None in (kubera, early, name):
            tally.add(False, {'world': world}, stop)
            continue
        if early or world in NOT_MODELLED:
            skipped.append(world)
            continue
        expected = (name.rsplit('.', 1)[0] if kubera else 'TerrainLight')
        c = lib.mu_terrain_light_name(world).decode()
        tally.count('kubera', int(bool(kubera)))
        tally.count('named', int(bool(name)))
        old_rule_mismatches += expected != 'TerrainLight'   # the pre-Q native rule: TerrainLight for every world
        if expected != 'TerrainLight':
            names[world] = name
        tally.add(c == expected, {'world': world, 'client': expected, 'c': c})
    return tally.report(), names, old_rule_mismatches, skipped


def load(directory):
    lib = C.CDLL(str(directory / f'libterrain.{v.SUFFIX}'))
    lib.mu_terrain_light_name.argtypes = [C.c_int32]
    lib.mu_terrain_light_name.restype = C.c_char_p
    return lib


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output')
    ap.add_argument('--mutations', action='store_true')
    a = ap.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    machine = v.Machine(text, data)
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/terrain')], check=True)
    lib = load(ROOT / 'reconstructed/terrain')
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'bodies': {n: {'start': hex(s), 'end': hex(e),
                             'sha256': hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for n, (s, e) in BODIES.items()},
              'families': {}}
    observed = {}
    r, names, old_rule_mismatches, skipped = compare(machine, lib, observed)
    report['mutants'] = []
    if a.mutations:
        with tempfile.TemporaryDirectory(prefix='light-name-') as tmp:
            for n, (old, new) in enumerate(MUTANTS):
                dest = Path(tmp) / str(n)
                for directory in ('terrain', 'record-math'):
                    shutil.copytree(ROOT / 'reconstructed' / directory, dest / directory,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '__pycache__'))
                p = dest / 'terrain' / 'terrain.c'
                src = p.read_text()
                assert old in src, old
                p.write_text(src.replace(old, new, 1))
                subprocess.run(['make', '-s', '-C', str(dest / 'terrain')], check=True)
                mr = compare(machine, load(dest / 'terrain'), observed)[0]
                m = {'change': new, 'detected': mr['mismatch_count'], 'stopped': mr['stopped']}
                report['mutants'].append(m)
                print('mutant', m, flush=True)
    report['families']['light_name'] = r
    report['kubera_names'] = names
    report['old_rule_mismatches'] = old_rule_mismatches
    report['not_modelled'] = skipped
    print('light_name', {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, flush=True)
    print('names', names, 'old-rule mismatches', old_rule_mismatches, 'not modelled', skipped)
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    return int(r['equal'] != r['cases'] or old_rule_mismatches != 5 or skipped != [30, 0x22] or
               sorted(names) != [0x7b, 0x7c, 0x7d, 0x7e, 0x7f] or
               any(not m['detected'] or m['stopped'] for m in report['mutants']))


if __name__ == '__main__':
    raise SystemExit(main())
