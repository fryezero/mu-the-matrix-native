#!/usr/bin/env python3
"""Compare the NATIVE-FIDELITY-001 reconstructions with the client's own instructions under Unicorn.

Sections (docs/research/client-fidelity.md):

* env_light: the body light of the ambient creatures. The C environment module (libclient_env, its test host)
  runs MoveBoids/MoveFishs for a few hundred steps in Lorencia, Dungeon, Noria and Atlans; for every live object
  the client's OBJECT constructor 0x0129e792 and ObjectInit 0x0129eb81 run on a 0x3d8-byte object, the modelled fields of the C object are
  written over it (mu_env_object_mask), and the client's body light 0x017ec3d8 (RenderObject's setup) runs on it
  with a random frame-light grid at 0x0b9f5430. The model's lighting byte +0x50 and colour +0x54 must equal
  mu_env_body_light on the C object with RequestTerrainLight's value from reconstructed/objects
  (mu_obj_terrain_light, verified by NATIVE-OBJECTS-002). A byte scan of the environment routines
  (0x00c9e24a..0x00ca5000) lists their writes to object +5/+6/+7.
* object_screen: RenderObjectScreen 0x016c2d82 (the inventory/hotkey item model) with its callees recorded;
  compared with reconstructed/hud mu_hud_object_screen (pose model, model height, action and animation
  arguments, the tick, the object state and RenderPartObject's arguments).
* special_models: the item-model loader 0x0183220e with AccessModel 0x018202b4 recorded; the (model, file)
  list must equal reconstructed/items/special_models.h, and AccessModel's file-name rule
  (mu_gi_special_model_file) its sprintf formats.

The restored text and second section are pinned (scripts/renderchar_machine.py). Inputs stay local.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import renderchar_machine as rmach  # noqa: E402
from renderchar_machine import f2u, u2f  # noqa: E402

SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


def default_evidence(relative):
    local = ROOT / 'evidence' / relative
    return local if local.exists() else Path.home() / 'Documents/main-exe-study/evidence' / relative


def build(directory, target):
    subprocess.run(['make', '-s', '-C', str(ROOT / directory)], check=True)
    return ctypes.CDLL(str(ROOT / directory / target))


ROUTINES = {
    'ObjectConstructor': (0x0129e792, 0x0129eb81),
    'ObjectInit': (0x0129eb81, 0x0129f0a0),
    'BodyLight': (0x017ec3d8, 0x017ec896),
    'RequestTerrainLightFrame': (0x016cb08d, 0x016cb2f7),
    'RenderObjectScreen': (0x016c2d82, 0x016c33f6),
    'ItemModelLoader': (0x0183220e, 0x018329fa),
    'AccessModel': (0x018202b4, 0x018203f0),
}


class Tally:
    def __init__(self):
        self.cases = self.matches = 0
        self.failures = []

    def check(self, label, client, native):
        self.cases += 1
        if client == native:
            self.matches += 1
        elif len(self.failures) < 8:
            self.failures.append({'case': label, 'client': repr(client)[:300], 'native': repr(native)[:300]})

    def report(self, **extra):
        out = {'cases': self.cases, 'matches': self.matches, 'failures': self.failures}
        out.update(extra)
        out['ok'] = self.cases > 0 and self.matches == self.cases and all(
            v for k, v in extra.items() if k.startswith('control'))
        return out


# ---------------------------------------------------------------- env_light
OBJ_BYTES, LEAF_BYTES = 0x3d8, 0xb4
OBJ, MODEL = 0x20000000, 0x21000000
FRAME_LIGHT, SCENE_STATE, TERRAIN_READY = 0x0b9f5430, 0x01d1df70, 0x0b5e3ea4


class EnvInputs(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('hero_position', ctypes.c_float * 3), ('hero_tile', ctypes.c_int32 * 2),
                ('hero_action', ctypes.c_uint16), ('hero_safe_zone', ctypes.c_uint8),
                ('camera_position', ctypes.c_float * 3), ('world_time', ctypes.c_float),
                ('frame_time', ctypes.c_float), ('event_state', ctypes.c_int32), ('login_scene', ctypes.c_int32),
                ('attributes', ctypes.c_void_p), ('layer1', ctypes.c_void_p)]


def env_objects(env, world, seed, steps, layer1_value):
    """Live boids and fish of the C module after `steps` logic steps: (which, index, client-layout bytes)."""
    h = env.mu_env_test_new(seed)
    inputs = EnvInputs.from_address(env.mu_env_test_inputs(h))
    attributes = ctypes.create_string_buffer(256 * 256 * 2)
    layer1 = ctypes.create_string_buffer(bytes([layer1_value]) * (256 * 256))
    inputs.attributes = ctypes.cast(attributes, ctypes.c_void_p).value
    inputs.layer1 = ctypes.cast(layer1, ctypes.c_void_p).value
    inputs.world = world
    rng = random.Random(seed)
    hero = [12800.0, 12800.0 if world != 7 else 9000.0, 0.0]
    out = []
    for step in range(steps):
        hero[0] += rng.uniform(-40, 40)
        hero[1] += rng.uniform(-40, 40)
        for k in range(3):
            inputs.hero_position[k] = hero[k]
            inputs.camera_position[k] = hero[k]
        inputs.hero_tile[0], inputs.hero_tile[1] = int(hero[0] / 100), int(hero[1] / 100)
        inputs.world_time = float(step * 40)
        inputs.frame_time = 0.1
        env.mu_env_test_run(h, 2)
        env.mu_env_test_run(h, 3)
    boids = ctypes.create_string_buffer(40 * OBJ_BYTES)
    fishs = ctypes.create_string_buffer(10 * OBJ_BYTES)
    env.mu_env_test_store(h, boids, fishs, None)
    for which, raw, count in ((0, boids.raw, 40), (1, fishs.raw, 10)):
        for i in range(count):
            record = raw[i * OBJ_BYTES:(i + 1) * OBJ_BYTES]
            if record[0]:
                out.append((which, i, record))
    return h, out


def client_body_light(text, data, record, mask, grid_bytes, scene_state):
    m = rmach.RenderMachine(text, data)
    m.map(OBJ, 0x1000)
    m.map(MODEL, 0x1000)
    init = m.run(0x0129e792, [], ecx=OBJ)          # the OBJECT constructor (the static arrays are constructed)
    if init['ok']:
        init = m.run(0x0129eb81, [], ecx=OBJ)      # ObjectInit, as the spawn of MoveBoids/MoveFishs calls it
    if not init['ok']:
        return ('ObjectInit stopped', init)
    current = bytearray(m.read(OBJ, OBJ_BYTES))
    flags_after_init = bytes(current[5:8])
    for k in range(OBJ_BYTES):
        if mask[k]:
            current[k] = record[k]
    m.write(OBJ, bytes(current))
    m.ensure(FRAME_LIGHT, len(grid_bytes))
    m.write(FRAME_LIGHT, grid_bytes)
    m.ensure(SCENE_STATE, 4)
    m.w32(SCENE_STATE, scene_state)
    m.ensure(TERRAIN_READY, 4)
    m.write(TERRAIN_READY, b'\1')
    result = m.run(0x017ec3d8, [OBJ, MODEL])
    if not result['ok']:
        return ('body light stopped', result)
    return m.read(MODEL + 0x50, 1)[0], struct.unpack('<3I', m.read(MODEL + 0x54, 12)), flags_after_init


def scan_flag_writes(text):
    """Writes of an immediate to a byte at +5/+6/+7 of a register in the environment routines (static)."""
    md = rmach.capstone_x86() if hasattr(rmach, 'capstone_x86') else None
    if md is None:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32)
    lo, hi = 0x00c9e24a, 0x00ca5000
    found = {5: [], 6: [], 7: []}
    for ins in md.disasm(text[lo - rmach.TEXT_BASE:hi - rmach.TEXT_BASE], lo):
        if ins.mnemonic == 'mov' and ins.op_str.startswith('byte ptr ['):
            for off in (5, 6, 7):
                if re.match(r'byte ptr \[e[a-z]{2} \+ %d\],' % off, ins.op_str):
                    found[off].append(hex(ins.address))
    return found


def env_section(text, data, args):
    env = build('reconstructed/environment', f'libclient_env.{SUFFIX}')
    objects = build('reconstructed/objects', f'libobjects.{SUFFIX}')
    env.mu_env_test_new.argtypes = [ctypes.c_uint32]
    env.mu_env_test_new.restype = ctypes.c_void_p
    env.mu_env_test_free.argtypes = [ctypes.c_void_p]
    env.mu_env_test_inputs.argtypes = [ctypes.c_void_p]
    env.mu_env_test_inputs.restype = ctypes.c_void_p
    env.mu_env_test_run.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    env.mu_env_test_store.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    env.mu_env_object_mask.argtypes = [ctypes.c_char_p]
    env.mu_env_test_body_light.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32,
                                           ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                                           ctypes.POINTER(ctypes.c_uint8)]
    objects.mu_obj_terrain_light.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint8, ctypes.c_float,
                                             ctypes.c_float, ctypes.POINTER(ctypes.c_float)]
    mask_buffer = ctypes.create_string_buffer(OBJ_BYTES)
    env.mu_env_object_mask(mask_buffer)
    mask = mask_buffer.raw
    rng = random.Random(args.seed)
    grid = struct.pack('<%df' % (256 * 256 * 3), *[rng.uniform(0, 1.2) for _ in range(256 * 256 * 3)])
    grid_c = ctypes.create_string_buffer(grid, len(grid))
    tally, control = Tally(), 0
    kinds = {}
    after_init = set()
    worlds = ((0, 5), (1, 0), (3, 0), (7, 0), (4, 0))
    for world, layer1 in worlds:
        for run in range(args.env_runs):
            h, live = env_objects(env, world, args.seed * 31 + world * 7 + run, args.env_steps, layer1)
            for which, index, record in live:
                o_type = struct.unpack_from('<i', record, 0x5c)[0]
                x, y = struct.unpack_from('<2f', record, 0x158)
                frame = (ctypes.c_float * 3)()
                objects.mu_obj_terrain_light(ctypes.cast(grid_c, ctypes.c_void_p), 6, 1, x, y, frame)
                color = (ctypes.c_float * 3)()
                lighting = ctypes.c_uint8()
                env.mu_env_test_body_light(h, which, index, frame, color, ctypes.byref(lighting))
                native = (lighting.value, tuple(f2u(v) for v in color))
                client = client_body_light(text, data, record, mask, grid, 6)
                if isinstance(client[0], str):
                    tally.check((world, which, index), client[0], native)
                    continue
                after_init.add(client[2])
                kinds[hex(o_type)] = kinds.get(hex(o_type), 0) + 1
                tally.check((world, which, index, hex(o_type)), (client[0], client[1]), native)
                # negative control: the NATIVE-ENV-001 colour (object light only)
                old = (lighting.value, tuple(f2u(v) for v in struct.unpack_from('<3f', record, 0xec)))
                control += old != (client[0], client[1])
            env.mu_env_test_free(h)
    writes = scan_flag_writes(text)
    return tally.report(objects_by_type=kinds, flags_after_object_init=[list(f) for f in sorted(after_init)],
                        flag_writes_static=writes, control_old_colour_differs=control,
                        control_no_flag6_flag7_writes=not writes[6] and not writes[7])


# ---------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--text', type=Path, default=default_evidence('x86-text-capture-09/client-text.bin'))
    parser.add_argument('--data', type=Path,
                        default=default_evidence('image-data-run10/data-capture-10/client-image-data.bin'))
    parser.add_argument('--sections', default='env_light,object_screen,special_models')
    parser.add_argument('--seed', type=int, default=20261018)
    parser.add_argument('--env-runs', type=int, default=2)
    parser.add_argument('--env-steps', type=int, default=200)
    parser.add_argument('--cases', type=int, default=400)
    parser.add_argument('--game-root', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = rmach.load_pinned(args.text, rmach.TEXT_BYTES, rmach.TEXT_SHA256, 'text')
    data = rmach.load_pinned(args.data, rmach.DATA_BYTES, rmach.DATA_SHA256, 'data')
    report = {'text_sha256': rmach.TEXT_SHA256, 'data_sha256': rmach.DATA_SHA256,
              'routines': {name: [hex(a), hex(b), hashlib.sha256(text[a - rmach.TEXT_BASE:b - rmach.TEXT_BASE]).hexdigest()]
                           for name, (a, b) in ROUTINES.items()}}
    sections = args.sections.split(',')
    if 'env_light' in sections:
        report['env_light'] = env_section(text, data, args)
    if 'object_screen' in sections and 'object_screen_section' in globals():
        report['object_screen'] = globals()['object_screen_section'](text, data, args)
    if 'special_models' in sections and 'special_models_section' in globals():
        report['special_models'] = globals()['special_models_section'](text, data, args)
    if args.output:
        args.output.write_text(json.dumps(report, indent=1, default=str))
    summary = {k: {kk: vv for kk, vv in v.items() if kk != 'failures' or vv} for k, v in report.items()
               if isinstance(v, dict) and 'ok' in v}
    print(json.dumps(summary, default=str)[:6000])
    return 0 if summary and all(v['ok'] for v in summary.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
