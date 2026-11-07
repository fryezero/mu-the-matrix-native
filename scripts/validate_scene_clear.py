#!/usr/bin/env python3
"""REGRESS-001: compare the render scene's clear colour (reconstructed/environment/env_world.c,
mu_env_world_info_get(...).clear) with the client's instructions in Unicorn.

The main render scene RenderMainScene 0x0185916b picks glClearColor in 0x01859419..0x0185967b from the world
[0x01cf15fc], before BeginOpengl 0x0184adc7 and CreateFrustrum 0x016cba24. Whatever RenderTerrain's culls
(CreateFrustrum2D 0x016d20d9, TestFrustrum2D 0x016ccce7) leave undrawn shows this colour, so it is what the
client draws beyond the terrain cull. The block runs unpatched from the pinned text, image data (its float
constants) and third section (the page of the world global, which each case then sets), and with the two world
predicates it calls (0x009dacb8, 0x00e0558b) executing unpatched too. The glClearColor import slot 0x01a7c6cc
points at a recording stub (stdcall, 16 bytes). A case compares the four argument bit patterns and the call
count with the C table (alpha 1); every one of the eight glClearColor call sites must be reached.

Mutants (--mutations): textual planted mistakes in a temporary copy of env_world.c, compiled with the
directory's sources; each must make at least one case differ.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402

ENV_DIR = ROOT / 'reconstructed/environment'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
BLOCK, JOIN = 0x01859419, 0x0185967c
BODY_SHA256 = 'f06d5daf3f5c48562d0c4d2c27a278f32eeef05d7f0bf24a4de0ecb10bffe738'
PREDICATES = {0x009dacb8: 0x23, 0x00e0558b: 0x14}   # start: length (to the ret) of the two world predicates
WORLD = 0x01cf15fc
GL_CLEAR_SLOT = 0x01a7c6cc
CALL_SITES = [0x0185945a, 0x0185949d, 0x018594ea, 0x01859533, 0x01859589, 0x018595f9, 0x01859643, 0x01859675]
STUB, STACK = 0x20000000, 0x30000000
MUTANTS = {
    'lorencia_world': ('    if (w == 0) {', '    if (w == 1) {'),
    'lorencia_green': ('        rgb[1] = 0.078125f;     /* 20/256 */', '        rgb[1] = 0.08203125f;'),
    'devias_channel': ('    } else if (w == 2) {\n        rgb[2] = 0.0390625f;',
                       '    } else if (w == 2) {\n        rgb[1] = 0.0390625f;'),
    'icarus_world': ('    } else if (w == 0xa) {', '    } else if (w == 0xb) {'),
    'event_range': ('    } else if (w >= 0x2d && w <= 0x32) {', '    } else if (w >= 0x2d && w <= 0x31) {'),
    'red_smoke_world': ('    } else if (w == 0x84) {', '    } else if (w == 0x85) {'),
}


class Info(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('clear', ctypes.c_float * 3), ('rest', ctypes.c_int32 * 9)]   # fog .. leaf_billboard (env.h)


def load_c(lib_path):
    lib = ctypes.CDLL(str(lib_path))
    lib.mu_env_world_info_get.argtypes = [ctypes.c_int32, ctypes.POINTER(Info)]
    lib.mu_env_world_info_get.restype = None

    def clear(world):
        info = Info()
        lib.mu_env_world_info_get(world, ctypes.byref(info))
        words = [struct.unpack('<I', struct.pack('<f', v))[0] for v in info.clear]
        return [(1, words + [0x3f800000])]
    return clear


class Guest:
    def __init__(self, text, data, section3):
        import unicorn as u
        import unicorn.x86_const as x
        self.u, self.x = u, x
        uc = self.uc = u.Uc(u.UC_ARCH_X86, u.UC_MODE_32)
        tb = pins.TEXT.base
        uc.mem_map(tb, (len(text) + 0xfff) & ~0xfff, u.UC_PROT_READ | u.UC_PROT_EXEC)
        uc.mem_write(tb, text)
        db = pins.DATA.base
        uc.mem_map(db, (len(data) + 0xfff) & ~0xfff, u.UC_PROT_READ | u.UC_PROT_WRITE)
        uc.mem_write(db, data)
        page = WORLD & ~0xfff   # only the world global's page of the third section: anything else stops
        offset = page - pins.SECTION3.base
        uc.mem_map(page, 0x1000, u.UC_PROT_READ | u.UC_PROT_WRITE)
        uc.mem_write(page, section3[offset:offset + 0x1000])
        uc.mem_map(STUB, 0x1000, u.UC_PROT_READ | u.UC_PROT_EXEC)
        uc.mem_write(STUB, b'\xc2\x10\x00')   # ret 0x10 (glClearColor is stdcall)
        uc.mem_write(GL_CLEAR_SLOT, struct.pack('<I', STUB))
        uc.mem_map(STACK, 0x10000, u.UC_PROT_READ | u.UC_PROT_WRITE)
        self.calls, self.sites, self.reads = [], set(), set()
        uc.hook_add(u.UC_HOOK_CODE, self._gl, begin=STUB, end=STUB)
        uc.hook_add(u.UC_HOOK_MEM_READ, self._read, begin=page, end=page + 0xfff)
        allowed = [(BLOCK, JOIN)] + [(a, a + n) for a, n in PREDICATES.items()] + [(STUB, STUB + 3)]

        self.left = None

        def fence(uc_, address, size, ignored):   # never raise inside a hook: stop and report
            if not any(lo <= address < hi for lo, hi in allowed):
                self.left = address
                uc_.emu_stop()
        uc.hook_add(u.UC_HOOK_CODE, fence)

    def _gl(self, uc, address, size, ignored):
        esp = uc.reg_read(self.x.UC_X86_REG_ESP)
        ret, *args = struct.unpack('<5I', uc.mem_read(esp, 20))
        self.sites.add(ret - 6)   # call dword ptr [imm32] is 6 bytes
        self.calls.append((1, list(args)))

    def _read(self, uc, access, address, size, value, ignored):
        self.reads.add(address)

    def run(self, world):
        x = self.x
        self.calls = []
        self.uc.mem_write(WORLD, struct.pack('<i', world))
        frame = STACK + 0x8000
        self.uc.mem_write(STACK, bytes(0x10000))
        self.uc.reg_write(x.UC_X86_REG_EBP, frame)
        self.uc.reg_write(x.UC_X86_REG_ESP, frame - 0xd0)
        self.left = None
        self.uc.emu_start(BLOCK, JOIN)
        if self.left is not None or self.uc.reg_read(x.UC_X86_REG_EIP) != JOIN:
            raise RuntimeError(f'world {world}: stopped at {self.uc.reg_read(x.UC_X86_REG_EIP):#010x} '
                               f'(left the block at {self.left})')
        return list(self.calls)


def worlds(cases, seed):
    rng = random.Random(seed)
    out = list(range(-16, 321))
    out += [-2 ** 31, 2 ** 31 - 1, 0x7fffff84, -0x7c, 0x10084]
    while len(out) < cases:
        out.append(rng.randrange(-2 ** 31, 2 ** 31))
    return out[:cases]


def compare(guest, clear, cases):
    mismatches = []
    for w in cases:
        got, want = guest.run(w), clear(w)
        if got != want:
            mismatches.append({'world': w, 'client': got, 'c': want})
    return mismatches


def build_mutant(name, work):
    old, new = MUTANTS[name]
    src = (ENV_DIR / 'env_world.c').read_text()
    if src.count(old) != 1:
        raise SystemExit(f'mutant {name}: anchor not found once in env_world.c')
    d = Path(work) / name
    shutil.copytree(ENV_DIR, d, ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d', '__pycache__'))
    (d / 'env_world.c').write_text(src.replace(old, new))
    rm = Path(work) / 'record-math'
    if not rm.exists():
        shutil.copytree(ROOT / 'reconstructed/record-math', rm,
                        ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d', '*.o', '__pycache__'))
    subprocess.run(['make', '-s', '-C', str(d), f'libclient_env.{SUFFIX}'], check=True, capture_output=True)
    return d / f'libclient_env.{SUFFIX}'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--text')
    ap.add_argument('--data')
    ap.add_argument('--section3')
    ap.add_argument('--cases', type=int, default=4000)
    ap.add_argument('--seed', type=lambda s: int(s, 0), default=0x20261106)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--output')
    a = ap.parse_args(argv)
    text = pins.TEXT.read(a.text, exit=True)
    data = pins.DATA.read(a.data, exit=True)
    section3 = pins.SECTION3.read(a.section3, exit=True)
    body = text[BLOCK - pins.TEXT.base:JOIN - pins.TEXT.base]
    body_sha = hashlib.sha256(body).hexdigest()
    if body_sha != BODY_SHA256:
        raise SystemExit(f'clear-colour block {BLOCK:#x}..{JOIN:#x}: SHA-256 {body_sha}, expected {BODY_SHA256}')
    subprocess.run(['make', '-s', '-C', str(ENV_DIR)], check=True, capture_output=True)
    guest = Guest(text, data, section3)
    cases = worlds(a.cases, a.seed)
    mismatches = compare(guest, load_c(ENV_DIR / f'libclient_env.{SUFFIX}'), cases)
    world_reads = sorted(hex(r) for r in guest.reads)
    report = {
        'family': 'scene_clear RenderMainScene 0x01859419..0x0185967b (glClearColor by world)',
        'pins': {p.name: p.sha256 for p in (pins.TEXT, pins.DATA, pins.SECTION3)},
        'body_sha256': body_sha, 'cases': len(cases), 'mismatches': len(mismatches),
        'first_mismatches': mismatches[:5],
        'call_sites': {hex(s): s in guest.sites for s in CALL_SITES},
        'third_section_reads': world_reads,
        'c_sha256': hashlib.sha256((ENV_DIR / 'env_world.c').read_bytes()).hexdigest(),
    }
    ok = not mismatches and all(report['call_sites'].values()) and world_reads == [hex(WORLD)]
    if a.mutations:
        report['mutations'] = {}
        with tempfile.TemporaryDirectory() as work:
            for name in MUTANTS:
                found = compare(guest, load_c(build_mutant(name, work)), cases)
                report['mutations'][name] = {'detected': bool(found), 'differing_cases': len(found)}
        ok = ok and all(m['detected'] for m in report['mutations'].values())
    report['ok'] = ok
    text_out = json.dumps(report, indent=1)
    if a.output:
        Path(a.output).write_text(text_out + '\n')
    sites = sum(report['call_sites'].values())
    print(f"scene_clear: cases {len(cases) - len(mismatches)}/{len(cases)} equal, {len(mismatches)} mismatches, "
          f"call sites {sites}/{len(CALL_SITES)}"
          + (f", mutants {sum(m['detected'] for m in report['mutations'].values())}/{len(MUTANTS)} detected"
             if a.mutations else ''))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
