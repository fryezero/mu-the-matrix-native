#!/usr/bin/env python3
"""AUDIO-003: original object callers through the production sound adapter.

Reuse the unchanged full caller corpora and their explicit model/render hosts.
Wrap the original SND_Play boundary to capture return addresses and arguments
independently. Compare every emitted native cue, including silent cases, while
the owning comparisons still check OBJECT/AL/RNG/full call order. No live input.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess
import tempfile
import pins
import validate_object_render as v
import validate_worlds_b as b
import validate_worlds_i as i
import validate_worlds_r2 as r2

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT/'native/core/mu_object_audio.h'
WRAPPER = r'''
#include "core/mu_object_audio.h"
typedef struct decision { uint32_t handler,site; int32_t id,key,loop; } decision;
static decision rows[64]; static int count;
void mu_session_sound_emit(mu_session *s,uint32_t handler,uint32_t site,int32_t id,int16_t key,int loop)
{ (void)s; rows[count++]=(decision){handler,site,id,key,loop}; }
int mu_audio_host_cue(mu_audio_host *h,const mu_cue *c,uint32_t tick)
{ (void)h;(void)tick;rows[count++]=(decision){c->handler,c->u.sound.site,c->u.sound.id,c->u.sound.at_key,c->u.sound.loop};return 1; }
int decode(int world,const int32_t *ids,int n,decision *out) {
    count=0;
    for(int k=0;k<n;++k) mu_object_audio_deliver((mu_session *)1,0,world,ids[k]);
    for(int k=0;k<count;++k)out[k]=rows[k];return count;
}
'''

class Decision(C.Structure):
    _fields_ = [('handler', C.c_uint32), ('site', C.c_uint32), ('id', C.c_int32),
                ('key', C.c_int32), ('loop', C.c_int32)]


def build(folder, header):
    (folder/'core').mkdir(parents=True)
    for path in (ROOT/'native/core').glob('*.h'):
        if path.name != HEADER.name:
            (folder/'core'/path.name).symlink_to(path)
    (folder/'core'/HEADER.name).write_text(header)
    (folder/'session').symlink_to(ROOT/'native/session')
    (folder.parent/'reconstructed').symlink_to(ROOT/'reconstructed') if not (folder.parent/'reconstructed').exists() else None
    source = folder/'wrapper.c'; source.write_text(WRAPPER)
    target = folder/'adapter.dylib'
    subprocess.run(['clang', '-std=c11', '-O2', '-shared', '-I', str(folder),
                    '-I', str(ROOT/'native/build/gen'), '-I', str(ROOT/'native/session'), str(source), '-o', str(target)], check=True)
    lib = C.CDLL(str(target))
    lib.decode.argtypes = [C.c_int, C.POINTER(C.c_int32), C.c_int, C.POINTER(Decision)]
    return lib


def decode(lib, world, ids):
    rows = (Decision*64)()
    count = lib.decode(world, (C.c_int32*len(ids))(*ids), len(ids), rows)
    return [tuple(getattr(row, name) for name, _ in Decision._fields_) for row in rows[:count]]


class Original(v.Machine):
    def execute(self, start, arguments, regions, stubs, **kwargs):
        self.sounds = []
        original = stubs.get(0xa6ac96)
        if original:
            def sound(machine):
                ret = struct_u32(machine.uc.mem_read(machine.uc.reg_read(machine.x86.UC_X86_REG_ESP), 4))
                site = ret - 5
                handler = 0x17ff238 if 0x1800000 <= site < 0x18006e2 else \
                          0xe34169 if 0xe34169 <= site < 0xe342f7 else \
                          0xe0ed1c if 0xe0ed1c <= site < 0xe0f4bc else 0xe6f3d5
                owner = machine.argument(1)
                assert owner in (0, v.OBJECTS)
                self.sounds.append((handler, site, machine.argument(0), -3 if owner else -2, machine.argument(2)))
                return original(machine)
            stubs = dict(stubs)
            stubs[0xa6ac96] = sound
        return super().execute(start, arguments, regions, stubs, **kwargs)


def struct_u32(raw):
    return int.from_bytes(raw, 'little')


class Calls:
    def __init__(self, dll, machine, adapter, corpus):
        self.dll, self.machine, self.adapter, self.corpus = dll, machine, adapter, corpus
        self.failures = []

    def __getattr__(self, name):
        fn = getattr(self.dll, name)
        if name not in ('mu_devias_move', 'mu_elbeland_move', 'mu_kardamahal_move', 'mu_uruk_visual'):
            return fn
        def call(*args):
            answer = fn(*args)
            world = args[2] if name == 'mu_uruk_visual' else C.cast(args[2], C.POINTER(v.MoveInputs)).contents.world
            log = C.cast(args[-1], C.POINTER(v.Log)).contents
            ids = [event.args[0] for event in log.events[:log.count] if event.call == 0xa6ac96]
            expected = list(self.machine.sounds)
            actual = decode(self.adapter, world, ids)
            self.corpus.append((world, ids, expected))
            if actual != expected:
                self.failures.append({'world': world, 'expected': expected, 'actual': actual})
            return answer
        return call


def check(cases, adapter, text, data):
    machine = Original(text, data)
    lib = v.Library(ROOT/f'reconstructed/objects/libobjects.{v.SUFFIX}')
    b.bind(lib); i.bind(lib); r2.bind(lib)
    corpus = []
    proxy = Calls(lib.dll, machine, adapter, corpus)
    lib.dll = proxy
    families = {}
    for world, name in [(2, 'devias'), (51, 'elbeland')]:
        families[name] = b.move(machine, lib, random.Random(0xBED), cases, world).report()
    families['kardamahal'] = r2.family(machine, lib, 'kardamahal_move', cases)
    families['uruk'] = i.family(machine, lib, 'uruk_visual', cases)
    return families, corpus, proxy.failures


MUTANTS = [
    ('world', 'world == 51', 'world == 52'),
    ('devias site', '0x0180041bu', '0x018005beu'),
    ('elbeland site', '0x00e3425fu', '0x00e3427cu'),
    ('loop', 'loop = 1;', 'loop = 0;'),
    ('object', 'owner = -3;', 'owner = -2;'),
    ('uruk alias', 'world == 100 || world == 101', 'world == 100'),
    ('random branch', 'case 0x5a7:', 'case 0x5aa:'),
    ('action site', '0x00e0f43du', '0x00e0f465u'),
    ('id', 'cue->u.sound.id = id;', 'cue->u.sound.id = id + 1;'),
    ('order', 'for(int k=0;k<n;++k)', 'for(int k=n-1;k>=0;--k)'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=1000)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    subprocess.run(['make', '-s', '-j4', '-C', str(ROOT/'reconstructed/objects')], check=True)
    text, data = pins.TEXT.read(), pins.DATA.read()
    with tempfile.TemporaryDirectory(prefix='audio-objects-') as temp:
        folder = Path(temp)
        header = HEADER.read_text()
        adapter = build(folder/'base', header)
        families, corpus, errors = check(args.cases, adapter, text, data)
        # Cross-world/id refusals and ordered multi-event delivery supplement
        # the actual callers, whose current cases emit at most one request.
        for world, ids in [(51, [0x317, 0x318, 0x313]), (143, [0x5a7, 0x5a8]),
                           (0, [0x317, 0x5a5]), (80, [0x5a5]), (138, [0x570])]:
            expected = decode(adapter, world, ids)
            corpus.append((world, ids, expected))
        seen = {row[1] for _, _, rows in corpus for row in rows}
        if len(seen) != 16:
            errors.append({'site_coverage': len(seen), 'expected': 16})
        mutations = []
        if args.mutations:
            for n, (label, old, new) in enumerate(MUTANTS):
                if label == 'order':
                    global WRAPPER
                    saved = WRAPPER
                    assert old in saved
                    WRAPPER = saved.replace(old, new)
                    mutant = build(folder/str(n), header)
                    WRAPPER = saved
                else:
                    assert old in header, old
                    mutant = build(folder/str(n), header.replace(old, new, 1))
                caught = sum(decode(mutant, world, ids) != expected for world, ids, expected in corpus)
                mutations.append({'name': label, 'detected': caught})
        report = {'cases': sum(f['cases'] for f in families.values()), 'sites': len(seen),
                  'families': families, 'mismatches': len(errors), 'examples': errors[:8], 'mutants': mutations}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))
        return int(bool(errors) or any(f['mismatch_count'] or f['stopped'] for f in families.values())
                   or any(not m['detected'] for m in mutations))


if __name__ == '__main__':
    raise SystemExit(main())
