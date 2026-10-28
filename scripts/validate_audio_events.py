#!/usr/bin/env python3
"""AUDIO-002: compare event music decisions with pinned x86, not FMOD mixing.

String lifetime, the music pointer table and the Kanturu singleton getter are
modelled. World predicates execute unchanged. Uncaptured event bytes are explicit
synthetic inputs. No original client is started. --mutations compiles wrong C.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import sys
import pins
from validate_audio import Machine, FAKE, MUSIC_TABLE, MUSIC_FAKE, MUSIC_COUNT, WORLD

ROOT = Path(__file__).resolve().parents[1]
MANAGERS = [0xdb3e26, 0xe8e857, 0xe84474, 0xd557af, 0xdb7501, 0xe9e9c5,
            0xe42ad0, 0xe92fc8, 0xdd306c, 0xdd8891, 0xdde543, 0xde5467,
            0xe6dd22, 0xe189e4, 0xd73c38]
ENDS = [0xdb40f5, 0xe8eb21, 0xe84513, 0xd558c3, 0xdb7656, 0xe9ead6,
        0xe42b35, 0xe93061, 0xdd30d1, 0xdd88f6, 0xdde5a8, 0xde54cc,
        0xe6dd2b, 0xe18ae9, 0xd73cd7]
class State(C.Structure):
    _fields_ = [(k, C.c_int32) for k in ('world', 'crywolf', 'crywolf_result', 'kanturu', 'temple', 'raklion')] + [('known', C.c_uint32)]
EVENT = C.CFUNCTYPE(None, C.c_void_p, C.c_int, C.c_int32, C.c_int32)
class Hooks(C.Structure):
    _fields_ = [('ctx', C.c_void_p), ('rand', C.c_void_p), ('boss', C.c_void_p), ('event', EVENT)]

class Oracle:
    def __init__(self, text, data):
        self.m = m = Machine(text, data)
        self.events = []
        for i in range(MUSIC_COUNT): m.write32(MUSIC_TABLE + 4*i, MUSIC_FAKE + 64*i)
        def ctor(m):
            m.write32(m.reg('ecx'), m.arg(0))
            return m.reg('ecx'), 4
        m.hook(0x94997e, ctor)
        m.hook(0x8e83a0, lambda m: (0, 0))
        for address, kind in ((0x120f602, 3), (0x120f5a0, 4)):
            def music(m, kind=kind):
                pointer = m.read32(m.arg(0))
                index, rem = divmod(pointer - MUSIC_FAKE, 64)
                assert rem == 0 and 0 <= index < MUSIC_COUNT
                self.events.append((kind, index, 0))
                return 0, 0
            m.hook(address, music)
        def sound(m):
            assert m.arg(1) == 0
            self.events.append((1, m.arg(0), m.arg(2)))
            return 1, 0
        m.hook(0xa6ac96, sound)
        m.hook(0x9a6ef3, lambda m: (FAKE + 0x1000, 0))
    def run(self, address, s):
        m = self.m
        self.events.clear()
        m.write32(WORLD, s.world)
        m.write(0x1ec90af, bytes([s.crywolf]))
        m.write32(0x1cf0e78, s.crywolf_result)
        m.write32(FAKE + 0x107c, s.kanturu)
        m.write32(FAKE + 0x2014, s.temple)
        m.write(FAKE + 0x2024, bytes([s.raklion]))
        m.call(address, [s.world] if address in MANAGERS[:2] else [], this=FAKE + 0x2000)
        return list(self.events)

def native(lib, address, s):
    out = []
    cb = EVENT(lambda ctx, k, a, b: out.append((k, a, b)))
    lib.mu_event_music(C.c_uint32(address), C.byref(s), C.byref(Hooks(None, None, None, cb)))
    return out

def cases():
    # Every world, all event phases, result branches, equality-vs-truth byte tests.
    for w in [-1] + list(range(167)) + [0x7fffffff]:
        for phase in range(7):
            for flag in (0, 1, 2, 255):
                yield State(w, phase, 10 if flag == 1 else 9, phase, phase, flag, 15)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report'); p.add_argument('--mutations', action='store_true')
    a = p.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    oracle = Oracle(text, data)
    lib = C.CDLL(str(ROOT/'reconstructed/audio'/('libclient_audio.dylib' if sys.platform == 'darwin' else 'libclient_audio.so')))
    report = {'families': {}, 'mismatches': 0, 'mutants': {}}
    corpus = list(cases())
    for address, end in zip(MANAGERS, ENDS):
        expected = [oracle.run(address, s) for s in corpus]
        for s, want in zip(corpus, expected):
            got = native(lib, address, s)
            if got != want: raise AssertionError((hex(address), tuple(getattr(s,k) for k,_ in s._fields_), want, got))
        report['families'][hex(address)] = {'cases': len(corpus), 'mismatches': 0,
            'body_sha256': hashlib.sha256(text[address-0x401000:end-0x401000]).hexdigest()}
        print(f'{address:08x}: {len(corpus)} cases, 0 mismatches', flush=True)
    if a.mutations:
        source = (ROOT/'reconstructed/audio/audio_world.c').read_text()
        mutations = {
            'crywolf-result': ('s->crywolf_result == 10', 's->crywolf_result == 9'),
            'kanturu-order': ('mp3stop(&e, 26); mp3stop(&e, 24)', 'mp3stop(&e, 24); mp3stop(&e, 26)'),
            'temple-phase': ('s->temple == 2 || s->temple == 3', 's->temple == 2'),
            'raklion-equality': ('s->raklion == 1', 's->raklion != 0'),
            'imperial-range': ('w >= 72 && w <= 74', 'w >= 72 && w < 74'),
            'kanturu-world': ('w == 38 || w == 137', 'w == 38'),
            'balgas-index': ('if (w == 41) mp3(&e, 27)', 'if (w == 41) mp3(&e, 28)'),
            'duel-world': ('w == 63) mp3(&e, 38)', 'w == 64) mp3(&e, 38)'),
            'imperial1-index': ('w == 69) mp3(&e, 39)', 'w == 69) mp3(&e, 40)'),
            'imperial2-index': ('w == 70) mp3(&e, 40)', 'w == 70) mp3(&e, 41)'),
            'imperial3-index': ('w == 71) mp3(&e, 41)', 'w == 71) mp3(&e, 42)'),
            'karutan-index': ('w == 80) mp3(&e, 45)', 'w == 80) mp3(&e, 46)'),
            'acheron-world': ('w == 91 || w == 92', 'w == 91'),
            'empty-manager': ('case 0x00e6dd22: break;', 'case 0x00e6dd22: mp3(&e, 45); break;'),
            'santa-stop': ('if (w == 62) mp3(&e, 36);', 'if (w == 62) mp3(&e, 36); else mp3stop(&e, 36);'),
        }
        small = [State(w, phase, r, phase, phase, flag, 15) for w in (0,34,38,39,41,58,62,63,69,70,71,74,80,92,137)
                 for phase in range(6) for r in (9,10) for flag in (1,2)]
        with tempfile.TemporaryDirectory(prefix='audio-events-mutants-') as tmp:
            for name, (old,new) in mutations.items():
                assert old in source
                src, dll = Path(tmp)/'mutant.c', Path(tmp)/f'{name}.dylib'
                src.write_text(source.replace(old,new,1))
                subprocess.run(['clang','-shared','-fPIC','-I',str(ROOT/'reconstructed/audio'),str(src),'-o',str(dll)],check=True)
                bad = C.CDLL(str(dll))
                caught = any(native(bad, addr,s) != native(lib,addr,s) for addr in MANAGERS for s in small)
                assert caught, name
                report['mutants'][name] = 'caught'
    report['cases'] = sum(f['cases'] for f in report['families'].values())
    print(json.dumps(report, indent=2))
    if a.report: Path(a.report).write_text(json.dumps(report, indent=2)+'\n')
if __name__ == '__main__': main()
