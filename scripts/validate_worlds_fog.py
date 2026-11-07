#!/usr/bin/env python3
"""RENDER-WORLDS-FOG instruction comparisons (docs/research/client-worlds-fog.md).

Families (reconstructed/environment/env_fog.c compiled here, via ctypes, against the pinned original under the strict
Unicorn machine of actor_machine.py):
  begin      RenderMainScene's test before the scene, 0x018596b4..0x01859797, run as client code from the
             frame-local state it builds (EBP frame entered mid-routine); StartFog 0x00d8cca8 runs as client code. The
             world global 0x01cf15fc, the Hero pointer 0x0a39d754 and the hero OBJECT's Position (+0x33ac) are the
             only defined inputs. The four GL imports it reaches (glEnable 0x01a7c75c, glDisable 0x01a7c758, glFogf
             0x01a7c724, glFogfv 0x01a7c69c) are stubs that log their arguments as bit patterns (glFogfv: the first
             three floats it is handed; the fourth is the caller's stale stack dword, which only the fog alpha takes).
             The native side is mu_env_scene_fog_begin, its answer turned into the same GL calls as
             native/world/world_rt.c issues them.
  end        The test after the scene, 0x01859bfa..0x01859cb3, with EndFog 0x00d8cd12 as client code; native
             mu_env_scene_fog_end.
  placement  Static: every draw anchor of reconstructed/world-order/parts_order.py is called inside RenderMainScene
             0x0185916b..0x01859d89 either between StartFog's call 0x01859783 and EndFog's 0x01859cad (fogged) or
             after it; the native parts it stands for must be fogged exactly when their draw order (parts.def,
             draw_gl and draw_soft) is below the boundary part world_rt.c's fog_end_here names. One case per
             (anchor call site, native part, column).
  sites      Static: StartFog and EndFog have exactly one caller each (rel32 calls, and no other reference to either
             address as a dword in the text or the image data).
The first 146 begin/end cases sweep the world id 0..145 with the hero inside the box; the rest draw world 0x1e three
times in four and coordinates around the box edges (each edge exactly, one ulp either side), anywhere, NaN, +-inf,
-0.0 or any bit pattern.
"""
import argparse, ctypes as C, json, math, random, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path

import actor_machine as am

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'

BEGIN, BEGIN_END = 0x018596b4, 0x01859797
END, END_END = 0x01859bfa, 0x01859cb3
SCENE, SCENE_END = 0x0185916b, 0x01859d89
START_FOG, END_FOG = 0x00d8cca8, 0x00d8cd12
START_SITE, END_SITE = 0x01859783, 0x01859cad
WORLD, HERO_PTR, HERO, POSITION = 0x01cf15fc, 0x0a39d754, 0x2a000000, 0x33ac
STUBS = 0x36000000
GL_IMPORTS = {0x01a7c75c: 'glEnable', 0x01a7c758: 'glDisable', 0x01a7c724: 'glFogf', 0x01a7c69c: 'glFogfv'}
GL_FOG, GL_FOG_COLOR, GL_FOG_MODE, GL_FOG_START, GL_FOG_END = 0x0b60, 0x0b66, 0x0b65, 0x0b63, 0x0b64
BOX = ((16100.0, 19000.0), (18900.0, 21700.0))
FRAME = (0x200, {})


def fbits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def from_bits(value):
    return struct.unpack('<f', struct.pack('<I', value & 0xffffffff))[0]


def ulp(value, up):
    b = fbits(value)
    if value == 0.0:
        return 0x00000001 if up else 0x80000001
    return b + 1 if (value > 0) == up else b - 1


# ---------------------------------------------------------------- original side
class Machine(am.ActorMachine):
    """The actor machine with the GL import slots pointed at a stub page."""

    def __init__(self, text, data):
        patched = bytearray(data)
        self.import_stubs = {}
        for index, (slot, name) in enumerate(sorted(GL_IMPORTS.items())):
            address = STUBS + 0x10 * index
            patched[slot - am.DATA_BASE:slot - am.DATA_BASE + 4] = struct.pack('<I', address)
            self.import_stubs[address] = name
        super().__init__(text, bytes(patched))
        from unicorn import UC_PROT_ALL
        self.uc.mem_map(STUBS, am.PAGE, UC_PROT_ALL)
        self.uc.mem_write(STUBS, b'\xcc' * am.PAGE)


class EndHook:
    """Stops a fragment at its end address."""

    def __init__(self, machine, end):
        self.machine, self.reached = machine, None
        self.hook = machine.uc.hook_add(machine.UC_HOOK_CODE, self.hit, begin=end, end=end)
        machine.uc.ctl_flush_tb()

    def hit(self, uc, address, size, ignored):
        self.reached = address
        uc.emu_stop()

    def close(self):
        self.machine.uc.hook_del(self.hook)


def run_original(machine, start, end, world, position):
    log = []

    def gl(name):
        def handler(m):
            if name == 'glFogfv':
                pointer = m.argument(1)
                words = struct.unpack('<3I', bytes(m.uc.mem_read(pointer, 12)))
                log.append((name, m.argument(0), *words))
            else:
                log.append((name,) + tuple(m.argument(k) for k in range(2 if name == 'glFogf' else 1)))
            return (0, 8 if name in ('glFogf', 'glFogfv') else 4)
        return handler
    hero = am.undefined_region('hero', HERO, 0x3400)
    hero.define(HERO + POSITION, struct.pack('<3I', *position))
    regions = [am.defined_region('world', WORLD, struct.pack('<i', world), writable=False),
               am.defined_region('hero-pointer', HERO_PTR, struct.pack('<I', HERO), writable=False), hero]
    stubs = {address: gl(name) for address, name in machine.import_stubs.items()}
    hook = EndHook(machine, end)
    try:
        result = machine.execute(start, [], regions, stubs, frame=FRAME)
    finally:
        hook.close()
    ok = hook.reached == end and result['stopped'] is None and result['error'] is None
    return ok, log, (result['stopped'], result['error'], hook.reached)


# ---------------------------------------------------------------- native side
class Fog(C.Structure):
    _fields_ = [('color', C.c_float * 4), ('mode', C.c_float), ('start', C.c_float), ('end', C.c_float)]


def build(source_dir, out_dir):
    out = Path(out_dir) / ('libenv_fog.' + SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-fPIC',
                    '-ffp-contract=off', '-fno-fast-math', '-shared', str(Path(source_dir) / 'env_fog.c'),
                    '-o', str(out)], check=True)
    lib = C.CDLL(str(out))
    lib.mu_env_scene_fog_begin.argtypes = [C.c_int32, C.POINTER(C.c_float), C.POINTER(Fog)]
    lib.mu_env_scene_fog_begin.restype = C.c_int
    lib.mu_env_scene_fog_end.argtypes = [C.c_int32, C.POINTER(C.c_float)]
    lib.mu_env_scene_fog_end.restype = C.c_int
    return lib


def floats(words):
    raw = (C.c_uint32 * 3)(*words)
    return C.cast(raw, C.POINTER(C.c_float)), raw


def native_begin(lib, world, position):
    pointer, keep = floats(position)
    fog = Fog()
    state = lib.mu_env_scene_fog_begin(world, pointer, C.byref(fog))
    if state == 2:   # world_rt.c: glEnable, glFogfv(color), glFogf(mode), glFogf(start), glFogf(end)
        return [('glEnable', GL_FOG), ('glFogfv', GL_FOG_COLOR, *(fbits(fog.color[k]) for k in range(3))),
                ('glFogf', GL_FOG_MODE, fbits(fog.mode)), ('glFogf', GL_FOG_START, fbits(fog.start)),
                ('glFogf', GL_FOG_END, fbits(fog.end))]
    return [('glDisable', GL_FOG)] if state == 1 else [] if state == 0 else [('state', state)]


def native_end(lib, world, position):
    pointer, keep = floats(position)
    return [('glDisable', GL_FOG)] if lib.mu_env_scene_fog_end(world, pointer) else []


# ---------------------------------------------------------------- cases
def coordinate(rng, low, high):
    pick = rng.randrange(12)
    if pick == 0:
        return fbits(low)
    if pick == 1:
        return fbits(high)
    if pick == 2:
        return ulp(low, rng.random() < 0.5)
    if pick == 3:
        return ulp(high, rng.random() < 0.5)
    if pick in (4, 5, 6):
        return fbits(rng.uniform(low - 300.0, high + 300.0))
    if pick == 7:
        return fbits(rng.uniform(0.0, 25600.0))
    if pick == 8:
        return rng.choice([0x7fc00000, 0xffc00000, 0x7f800001, 0x7fa00000 | rng.getrandbits(20)])
    if pick == 9:
        return rng.choice([0x7f800000, 0xff800000, 0x80000000, 0x00000000])
    return rng.getrandbits(32)


def cases(rng, count):
    inside = (fbits(17500.0), fbits(20000.0), fbits(170.0))
    for k in range(count):
        if k < 146:
            yield k, inside
            continue
        world = 0x1e if rng.random() < 0.75 else rng.choice([rng.randrange(146), rng.getrandbits(32) - 2**31])
        yield world, (coordinate(rng, *BOX[0]), coordinate(rng, *BOX[1]), rng.getrandbits(32))


class Tally:
    def __init__(self):
        self.cases = self.equal = self.stopped = 0
        self.mismatches, self.stops, self.outcomes = [], [], {}

    def add(self, ok, same, detail, outcome):
        self.cases += 1
        if not ok:
            self.stopped += 1
            if len(self.stops) < 5:
                self.stops.append(detail)
        elif same:
            self.equal += 1
        elif len(self.mismatches) < 5:
            self.mismatches.append(detail)
        self.outcomes[outcome] = self.outcomes.get(outcome, 0) + 1

    def report(self):
        return {'cases': self.cases, 'equal': self.equal, 'stopped': self.stopped,
                'mismatch_count': self.cases - self.equal - self.stopped, 'mismatches': self.mismatches,
                'stops': self.stops, 'outcomes': self.outcomes}


def fragment_family(start, end, native):
    def run(machine, lib, rng, count):
        tally = Tally()
        for world, position in cases(rng, count):
            ok, client, why = run_original(machine, start, end, world, position)
            mine = native(lib, world, position)
            outcome = '+'.join(c[0] for c in client) or 'none'
            tally.add(ok, client == mine, {'world': world, 'position': [hex(p) for p in position],
                                           'client': [list(map(str, c)) for c in client],
                                           'native': [list(map(str, c)) for c in mine], 'why': str(why)}, outcome)
        return tally
    return run


def calls_in(text, low, high):
    """rel32 call sites in [low, high) -> target (linear sweep; the routine has no inline data)."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    out = []
    for ins in md.disasm(text[low - am.TEXT_BASE:high - am.TEXT_BASE], low):
        if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
            out.append((ins.address, int(ins.op_str, 16)))
    return out


def parts_orders(root):
    rows = {}
    for m in re.finditer(r'^MU_PART\(\s*(\w+),\s*\w+,\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)',
                         (root / 'native/world/parts.def').read_text(), re.M):
        rows[m.group(1)] = {'draw_gl': int(m.group(5)), 'draw_soft': int(m.group(6))}
    return rows


def boundary(root):
    names = set(re.findall(r'ROWS\[MU_PART_(\w+)\]\.order\[col\]', (root / 'native/world/world_rt.c').read_text()))
    return names.pop() if len(names) == 1 else None


def placement_family(text, root):
    sys.path.insert(0, str(ROOT / 'reconstructed/world-order'))
    import parts_order
    tally = Tally()
    rows, edge = parts_orders(root), boundary(root)
    sites = calls_in(text, SCENE, SCENE_END)
    for address, target in sites:
        parts = parts_order.ANCHORS['draw'].get(target)
        if not parts:
            continue
        fogged = START_SITE < address < END_SITE
        for part in parts:
            for column in ('draw_gl', 'draw_soft'):
                order = rows.get(part, {}).get(column, 0)
                ok = edge in rows and order > 0
                native = ok and order < rows[edge][column]
                tally.add(ok, native == fogged, {'site': hex(address), 'target': hex(target), 'part': part,
                                                 'column': column, 'client_fogged': fogged, 'boundary': edge},
                          'fogged' if fogged else 'after')
    return tally


def sites_family(text, data):
    tally = Tally()
    for target, site in ((START_FOG, START_SITE), (END_FOG, END_SITE)):
        calls = [i + am.TEXT_BASE for i in range(len(text) - 5) if text[i] == 0xe8 and
                 (i + am.TEXT_BASE + 5 + struct.unpack('<i', text[i + 1:i + 5])[0]) & 0xffffffff == target]
        word = struct.pack('<I', target)
        refs = [m.start() + am.TEXT_BASE for m in re.finditer(re.escape(word), text)] + \
               [m.start() + am.DATA_BASE for m in re.finditer(re.escape(word), data)]
        tally.add(True, calls == [site], {'target': hex(target), 'calls': [hex(c) for c in calls]}, 'calls')
        tally.add(True, refs == [], {'target': hex(target), 'dword_refs': [hex(r) for r in refs]}, 'dwords')
    return tally


FAMILIES = ['begin', 'end', 'placement', 'sites']
RUN = {'begin': fragment_family(BEGIN, BEGIN_END, native_begin), 'end': fragment_family(END, END_END, native_end)}

F = 'reconstructed/environment/env_fog.c'
W = 'native/world/world_rt.c'
MUTATIONS = [
    ('Box x low edge exclusive', F, 'p[0] >= 16100.0f', 'p[0] > 16100.0f', ['begin', 'end']),
    ('Box x high edge exclusive', F, '19000.0f >= p[0]', '19000.0f > p[0]', ['begin', 'end']),
    ('Box y low edge exclusive', F, 'p[1] >= 18900.0f', 'p[1] > 18900.0f', ['begin', 'end']),
    ('Box y high edge exclusive', F, '21700.0f >= p[1]', '21700.0f > p[1]', ['begin', 'end']),
    ('Box y tested on z', F, 'p[1] >= 18900.0f', 'p[2] >= 18900.0f', ['begin', 'end']),
    ('NaN inside the box', F, 'return p[0] >= 16100.0f && 19000.0f >= p[0] &&',
     'return !(p[0] < 16100.0f) && !(19000.0f < p[0]) &&', ['begin', 'end']),
    ('Fog in world 0x1f', F, 'if (world != 0x1e)', 'if (world != 0x1f)', ['begin']),
    ('No glDisable outside the box', F, 'return MU_ENV_FOG_OFF;', 'return MU_ENV_FOG_KEEP;', ['begin']),
    ('glDisable in every world', F, 'return MU_ENV_FOG_KEEP;', 'return MU_ENV_FOG_OFF;', ['begin']),
    ('GL_EXP instead of GL_LINEAR', F, 'fog->mode = 9729.0f;', 'fog->mode = 2048.0f;', ['begin']),
    ('Fog start 1900', F, 'fog->start = 2000.0f;', 'fog->start = 1900.0f;', ['begin']),
    ('Fog end 2800', F, 'fog->end = 2700.0f;', 'fog->end = 2800.0f;', ['begin']),
    ('Fog colour not black', F, 'memset(fog, 0, sizeof *fog);',
     'memset(fog, 0, sizeof *fog); fog->color[2] = 0.0625f;', ['begin']),
    ('EndFog without the box test', F, 'return world == 0x1e && in_box(hero);', 'return world == 0x1e && hero != NULL;',
     ['end']),
    ('EndFog in every world', F, 'return world == 0x1e && in_box(hero);', 'return world != -1 && in_box(hero);',
     ['end']),
    ('Fog ends before the combat effects', W, 'ROWS[MU_PART_haze].order[col]', 'ROWS[MU_PART_combat].order[col]',
     ['placement']),
    ('Fog ends after the names', W, 'ROWS[MU_PART_haze].order[col]', 'ROWS[MU_PART_names].order[col]',
     ['placement']),
]


def run_family(name, machine, text, data, root, lib, cases_count):
    if name in RUN:
        return RUN[name](machine, lib, random.Random(0xf06 + FAMILIES.index(name)), cases_count)
    if name == 'placement':
        return placement_family(text, root)
    return sites_family(text, data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=2000)
    p.add_argument('--only')
    p.add_argument('--text', default=am.pins.TEXT.default_str())
    p.add_argument('--data', default=am.pins.DATA.default_str())
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    text = am.load_pinned(a.text, am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(a.data, am.DATA_BYTES, am.DATA_SHA256, 'data')
    machine = Machine(text, data)
    names = a.only.split(',') if a.only else FAMILIES
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': []}
    with tempfile.TemporaryDirectory(prefix='worlds-fog-') as td:
        lib = build(ROOT / 'reconstructed/environment', td)
        for name in names:
            tally = run_family(name, machine, text, data, ROOT, lib, a.cases)
            report['families'][name] = tally.report()
            print(name, json.dumps(tally.report())[:1200], flush=True)
        if a.mutations:
            for label, file, old, new, families in MUTATIONS:
                with tempfile.TemporaryDirectory(prefix='worlds-fog-mut-') as mtmp:
                    root = Path(mtmp)
                    for rel in (F, W, 'native/world/parts.def'):
                        (root / rel).parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(ROOT / rel, root / rel)
                    shutil.copy(ROOT / 'reconstructed/environment/env_fog.h', root / 'reconstructed/environment')
                    path = root / file
                    source = path.read_text()
                    assert source.count(old) == 1, (label, 'anchor must match exactly once')
                    path.write_text(source.replace(old, new))
                    mlib = build(root / 'reconstructed/environment', mtmp)
                    for fam in families:
                        if fam not in names:
                            continue
                        tally = run_family(fam, machine, text, data, root, mlib, a.cases)
                        item = {'name': label, 'family': fam, 'cases': tally.cases,
                                'detected': tally.cases - tally.equal - tally.stopped, 'stopped': tally.stopped}
                        report['mutants'].append(item)
                        print(item, flush=True)
    report['ok'] = all(x['mismatch_count'] == 0 and x['stopped'] == 0 for x in report['families'].values()) and \
        all(x['detected'] > 0 and x['stopped'] == 0 for x in report['mutants'])
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=1))
    print('ok' if report['ok'] else 'FAILED', flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
