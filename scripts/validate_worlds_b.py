#!/usr/bin/env python3
"""RENDER-WORLDS-B: compiled per-world C versus pinned x86 instructions.

Eight families compare object bytes, ordered engine-call arguments, placement records,
weather bytes and rand consumption. Engine allocations/render/audio are recording stubs.
Devias/Tarkan start at their post-tick switch branches with an explicit caller frame.
No live client or installed data is needed. Reports and generated libraries stay local.
"""

import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import validate_object_render as v
import actor_machine as am
import pins

ROOT = Path(__file__).resolve().parents[1]
O = v.OBJECTS
POOL = 0x0BDB75C8
TYPES = {
    2: [0x14, 0x1E, 0x41, 0x42, 0x4E, 0x56, 0x58, 0x13, 422, 423, 424],
    8: [2, 4, 7, 0xB, 0xC, 0xD, 0x3D, 0x3F, 0x40, 0x41, 0x42, 0x48, 0x49, 0x4B, 0x4F, 0x52, 0x5D, 0x5E, 99],
    51: [0, 2, 0x35, 0x36, 0x37, 0x38, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x55, 0x59, 0x6E, 99],
    57: [0x16, 0x46, 0x50, 0, 0x10, 424, 427],
}
BODIES = {
    "devias": (0x17FFFDA, 0x18006E2),
    "tarkan": (0x1800BF8, 0x18013A5),
    "elbeland": (0xE30B86, 0xE3116A),
    "elbeland_sound": (0xE34169, 0xE342F7),
    "raklion": (0xE94619, 0xE946A6),
    "raklion_create": (0xE943C0, 0xE94617),
    "snow": (0xE9EC6A, 0xE9EE78),
    "devias_records": (0x18394D3, 0x1839797),
    "raklion_records": (0x183F710, 0x183FA87),
}


def bind(lib):
    d = lib.dll
    for n in ("devias", "tarkan", "elbeland"):
        getattr(d, "mu_" + n + "_move").argtypes = [C.c_void_p, C.c_int32, C.POINTER(v.MoveInputs), C.POINTER(v.Log)]
    d.mu_raklion_move.argtypes = [C.c_void_p, C.c_float]
    d.mu_raklion_create.argtypes = [C.c_void_p, C.c_int32, C.POINTER(v.Log)]
    d.mu_devias_records.argtypes = [C.POINTER(v.Record)]
    d.mu_raklion_records.argtypes = [C.c_int32, C.POINTER(v.Record)]
    return lib


def move(machine, lib, g, cases, world):
    name = {2: "devias", 8: "tarkan", 51: "elbeland", 57: "raklion"}[world]
    tally = v.Tally(name)
    for n in range(cases):
        typ = TYPES[world][n % len(TYPES[world])]
        o = v.move_object(g, 0, "full")
        v.put_i(o, 0x5C, typ)
        v.put_f(o, 0x17C, 1000, 2000, 100)
        v.put_f(o, 0x158, 1000, 2000, 100)
        v.put_f(o, 0x164 + 8, g.choice([0, 90, 180, 270, 45, -90]))
        v.put_f(o, 0x170 + 8, g.choice([0, 90, 180, 270, 45, -90]))
        hero = (v.f32(1000 + g.choice([0, 199.9, 200, 201, 400])), v.f32(2000 + g.choice([0, 10, 200])), 100.0)
        time = v.f32(g.uniform(-20000, 3e6))
        seed = g.getrandbits(32)
        rnd = v.MsvcRand(seed)
        calls = []
        safe = n % 2
        bounds = n % 7 == 0
        pool = bytearray(v.OBJ_SIZE)
        pool[0] = (n // len(TYPES[world])) % 2

        def light(m):
            a = [m.argument(k) for k in range(5)]
            calls.append((0x16CACFC, 0, a[0], a[1]) + v.read_vec(m, a[2]) + (a[3],))
            assert a[4] == v.FRAME_LIGHT
            return 0

        def particle(m):
            a = [m.argument(k) for k in range(8)]
            calls.append(
                (0x168FAFD, 0, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) + (a[4], a[5])
            )
            assert a[6:] == [0, 0]
            return 0

        def sound(m):
            owner = m.argument(1)
            calls.append((0xA6AC96, 0, m.argument(0), 1 if owner == O else owner, m.argument(2)))
            return 0

        stubs = {
            0x1989721: lambda m: rnd(),
            0x16CACFC: light,
            0x168FAFD: particle,
            0xA6AC96: sound,
            0xEA233C: lambda m: 1,
            0xE309A7: lambda m: 1,
            0xE309D9: lambda m: 0,
            0x16D34DB: lambda m: 0,
        }
        regs = v.global_regions(
            world,
            6,
            [
                am.defined_region("object", O, bytes(o)),
                am.defined_region("handler", v.FAKE, bytes(0x40)),
                am.defined_region("pool", POOL, bytes(pool)),
                am.defined_region("time", v.TIME, v.pack_f(time), writable=False),
                am.defined_region("bounds", v.BOUNDS, struct.pack("<i", bounds), writable=False),
                am.defined_region("hero-pointer", v.HERO_PTR, struct.pack("<I", v.HERO), writable=False),
                am.defined_region(
                    "hero",
                    v.HERO,
                    bytes(0x180) + struct.pack("<ii", 10, 20) + bytes(0x3224) + v.pack_f(*hero),
                    writable=False,
                ),
                am.defined_region("att", 0xB795420, struct.pack("<H", safe), writable=False),
            ],
        )
        if world in (2, 8):
            stubs[0x1801662] = lambda m: m.stop(("end",))
            result = machine.execute(BODIES[name][0], [O], regs, stubs, frame=(0x180, {}))
            stop = None if result["stopped"] == ("end",) else v.stopped_reason(result)
        else:
            result = v.run(machine, BODIES[name][0], [O], regs, stubs, cleanup=4 if world == 57 else 0, ecx=v.FAKE)
            stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {"case": n, "type": typ}, stop)
            continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        cp = C.create_string_buffer(bytes(pool), v.OBJ_SIZE)
        cr = v.MsvcRand(seed)
        fn = v.RAND_FN(lambda ctx: cr())
        speed = v.SPEED_FN(lambda ctx, t, a: 0)
        inputs = v.MoveInputs(
            world, 6, 0, time, (C.c_float * 3)(*hero), 1, 1, speed, fn, None, 0, bounds, safe, C.addressof(cp)
        )
        log = v.new_log()
        if world == 57:
            lib.dll.mu_raklion_move(co, time)
        else:
            getattr(lib.dll, "mu_" + name + "_move")(co, 0, C.byref(inputs), C.byref(log))
        diff = [hex(k) for k in range(v.OBJ_SIZE) if co.raw[k] != result["regions"]["object"][k]]
        tally.count("type " + hex(typ))
        tally.count("events", len(calls))
        tally.add(
            not diff and cp.raw == result["regions"]["pool"] and calls == v.log_events(log) and rnd.seed == cr.seed,
            {
                "case": n,
                "type": typ,
                "diff": diff[:8],
                "calls": calls,
                "c": v.log_events(log),
                "pool_equal": cp.raw == result["regions"]["pool"],
                "rand_equal": rnd.seed == cr.seed,
            },
        )
    return tally


def records(machine, lib, g, cases, world):
    tally = v.Tally("devias_records" if world == 2 else "raklion_records")
    for n in range(cases):
        w = 2 if world == 2 else (57 + n % 2)
        calls = []
        slots = {}

        def constructor(m):
            a = [m.argument(k) for k in range(10)]
            r = v.Record()
            r.type = a[0]
            r.position[:] = [v.from_bits(x) for x in v.read_vec(m, a[1])]
            r.angle[:] = [v.from_bits(x) for x in v.read_vec(m, a[2])]
            r.scale = v.from_bits(a[3])
            r.flag_2c = a[4]
            r.flag_2d = a[5]
            r.flag_2e = a[6]
            r.hidden = a[7]
            r.value_30 = v.from_bits(a[8])
            r.value_34 = v.from_bits(a[9])
            calls.append(bytes(r))
            return (v.RECORD, 40)

        start, end = (0x18394D3, 0x1839797) if w == 2 else (0x183F710, 0x183FA87)
        stubs = {
            0xD7FB55: constructor,
            0x16D8538: lambda m: 0,
            0x18202B4: lambda m: 0,
            0x181FBE9: lambda m: 0,
            end: lambda m: m.stop(("end",)),
        }
        result = machine.execute(start, [], v.global_regions(w), stubs, frame=(0x2500, slots))
        if result["stopped"] != ("end",):
            tally.add(False, {"case": n}, v.stopped_reason(result))
            continue
        r = (v.Record * 3)()
        count = lib.dll.mu_devias_records(r) if w == 2 else lib.dll.mu_raklion_records(w, r)
        expected = [bytes(r[k]) for k in range(count)]
        tally.add(calls == expected, {"world": w, "calls": [x.hex() for x in calls], "c": [x.hex() for x in expected]})
    return tally


def create(machine, lib, g, cases):
    tally = v.Tally("raklion_create")
    for n in range(cases):
        o = v.move_object(g, 0, "full")
        v.put_i(o, 0x5C, [424, 427, 428, 0][n % 4])
        calls = []

        def effect(m):
            a = [m.argument(k) for k in range(14)]
            calls.append(
                (0x13C0EAA, 0, a[0]) + v.read_vec(m, a[1]) + tuple((x - O) & 0xFFFFFFFF for x in a[2:4]) + tuple(a[4:])
            )
            return 0

        result = v.run(
            machine, 0xE943C0, [O], [am.defined_region("object", O, bytes(o))], {0x13C0EAA: effect}, cleanup=4
        )
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {"case": n}, stop)
            continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        log = v.new_log()
        lib.dll.mu_raklion_create(co, 0, C.byref(log))
        tally.add(
            calls == v.log_events(log) and result["regions"]["object"] == co.raw,
            {"case": n, "calls": calls, "c": v.log_events(log)},
        )
    return tally


def snow_library(directory):
    src = ROOT / "reconstructed/environment"
    adapter = directory / "snow_host.c"
    adapter.write_text("""#include "env_internal.h"
void snow_image(uint32_t *seed,const float *hero,uint8_t *image) {
    mu_env e={0};mu_env_inputs in={0};mu_env_leaf l;
    e.rand_state=*seed;for(int k=0;k<3;++k)in.hero_position[k]=hero[k];
    mu_env_leaf_load(&l,image);mu_env_raklion_snow(&e,&in,&l);mu_env_leaf_store(&l,image);*seed=e.rand_state;
}""")
    out = directory / ("snow." + v.SUFFIX)
    subprocess.run(
        [
            "clang",
            "-std=c11",
            "-O2",
            "-shared",
            "-fPIC",
            "-ffp-contract=off",
            "-I",
            str(src),
            str(adapter),
            str(src / "raklion_snow.c"),
            str(src / "env_core.c"),
            str(ROOT / "reconstructed/record-math/record_math.c"),
            "-lm",
            "-o",
            str(out),
        ],
        check=True,
    )
    lib = C.CDLL(str(out))
    lib.snow_image.argtypes = [C.POINTER(C.c_uint32), C.POINTER(C.c_float), C.c_void_p]
    return lib


def snow(machine, lib, g, cases):
    tally = v.Tally("snow")
    for n in range(cases):
        raw = bytes(g.getrandbits(8) for _ in range(0xB4))
        hero = [v.f32(g.uniform(-1000, 25000)) for _ in range(3)]
        seed = g.getrandbits(32)
        rnd = v.MsvcRand(seed)
        result = v.run(
            machine,
            0xE9EC6A,
            [O],
            v.global_regions(
                57,
                6,
                [
                    am.defined_region("leaf", O, raw),
                    am.defined_region("hero-pointer", v.HERO_PTR, struct.pack("<I", v.HERO), writable=False),
                    am.defined_region("hero", v.HERO + 0x33AC, v.pack_f(*hero), writable=False),
                ],
            ),
            {0x1989721: lambda m: rnd()},
            cleanup=4,
        )
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {"case": n}, stop)
            continue
        co = C.create_string_buffer(raw, 0xB4)
        cs = C.c_uint32(seed)
        lib.snow_image(C.byref(cs), (C.c_float * 3)(*hero), co)
        diff = [hex(k) for k in range(0xB4) if co.raw[k] != result["regions"]["leaf"][k]]
        tally.add(not diff and cs.value == rnd.seed, {"case": n, "diff": diff[:8]})
    return tally


MUTANTS = [
    ("devias.c", "200.0f > distance", "190.0f > distance", "devias"),
    ("devias.c", "% 4 + 4", "% 4 + 3", "devias"),
    ("devias.c", "position[1] = 1700", "position[1] = 1800", "devias_records"),
    ("tarkan.c", "l, l * 0.6f, l * 0.2f, 2", "l, l * 0.6f, l * 0.2f, 4", "tarkan"),
    ("elbeland.c", "+ 0.015f", "+ 0.025f", "elbeland"),
    ("elbeland.c", "if (p[MU_OBJF_LIVE])\n        return;", "if(0)return;", "elbeland"),
    ("raklion.c", "time * 0.001f", "time * 0.002f", "raklion"),
    ("raklion.c", "p[2] += 520", "p[2] += 510", "raklion_create"),
    ("raklion.c", "position[0] = 17000", "position[0] = 17100", "raklion_records"),
    ("raklion_snow.c", "% 20 + 30", "% 20 + 20", "snow"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases", type=int, default=500)
    ap.add_argument("--mutations", action="store_true")
    ap.add_argument("--output")
    ap.add_argument("--only")
    a = ap.parse_args()
    text = pins.TEXT.read()
    data = pins.DATA.read()
    machine = v.Machine(text, data)
    subprocess.run(["make", "-s", "-C", str(ROOT / "reconstructed/objects")], check=True)
    lib = bind(v.Library(ROOT / f"reconstructed/objects/libobjects.{v.SUFFIX}"))
    with tempfile.TemporaryDirectory(prefix="worlds-b-") as temp:
        td = Path(temp)
        sl = snow_library(td)

        def run(name, lib=lib, sl=sl):
            g = random.Random(0xBED)
            if name in ("devias", "tarkan", "elbeland", "raklion"):
                return move(machine, lib, g, a.cases, {"devias": 2, "tarkan": 8, "elbeland": 51, "raklion": 57}[name])
            if name == "raklion_create":
                return create(machine, lib, g, a.cases)
            if name == "snow":
                return snow(machine, sl, g, a.cases)
            return records(machine, lib, g, a.cases, 2 if name == "devias_records" else 57)

        names = (
            a.only.split(",")
            if a.only
            else [
                "devias",
                "tarkan",
                "elbeland",
                "raklion",
                "devias_records",
                "raklion_records",
                "raklion_create",
                "snow",
            ]
        )
        report = {
            "text_sha256": pins.TEXT.sha256,
            "data_sha256": pins.DATA.sha256,
            "bodies": {
                n: {
                    "start": hex(s),
                    "end": hex(e),
                    "sha256": hashlib.sha256(text[s - am.TEXT_BASE : e - am.TEXT_BASE]).hexdigest(),
                }
                for n, (s, e) in BODIES.items()
            },
            "families": {},
            "mutants": [],
        }
        for name in names:
            r = run(name).report()
            report["families"][name] = r
            print(name, r, flush=True)
        if a.mutations:
            for idx, (file, old, new, family) in enumerate(MUTANTS):
                if family not in names:
                    continue
                dest = td / str(idx)
                dest.mkdir()
                for directory in ("objects", "terrain", "model-codec", "record-math", "movement", "environment"):
                    shutil.copytree(
                        ROOT / "reconstructed" / directory,
                        dest / directory,
                        ignore=shutil.ignore_patterns("*.dylib", "*.so", "__pycache__"),
                    )
                p = dest / ("environment" if family == "snow" else "objects") / file
                s = p.read_text()
                assert old in s
                (p).write_text(s.replace(old, new, 1))
                if family == "snow":
                    # Build the adapter against the mutated file, preserving the same production entry point.
                    out = dest / f"snow.{v.SUFFIX}"
                    subprocess.run(
                        [
                            "clang",
                            "-std=c11",
                            "-O2",
                            "-shared",
                            "-fPIC",
                            "-ffp-contract=off",
                            "-I",
                            str(dest / "environment"),
                            str(td / "snow_host.c"),
                            str(dest / "environment/raklion_snow.c"),
                            str(dest / "environment/env_core.c"),
                            str(dest / "record-math/record_math.c"),
                            "-lm",
                            "-o",
                            str(out),
                        ],
                        check=True,
                    )
                    ml = C.CDLL(str(out))
                    ml.snow_image.argtypes = sl.snow_image.argtypes
                    r = run(family, sl=ml).report()
                else:
                    ml = bind(v.Library(v.build_library(dest)))
                    r = run(family, lib=ml).report()
                report["mutants"].append(
                    {
                        "file": file,
                        "change": new,
                        "family": family,
                        "detected": r["mismatch_count"],
                        "stopped": r["stopped"],
                    }
                )
                print("mutant", report["mutants"][-1], flush=True)
        if a.output:
            Path(a.output).write_text(json.dumps(report, indent=2) + "\n")
        return (
            0
            if all(r["equal"] == r["cases"] and not r["stopped"] for r in report["families"].values())
            and all(m["detected"] > 0 and not m["stopped"] for m in report["mutants"])
            else 1
        )


if __name__ == "__main__":
    sys.exit(main())
