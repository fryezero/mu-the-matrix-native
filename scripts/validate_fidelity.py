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


# ---------------------------------------------------------------- object_screen
ROS = 0x016c2d82
ROS_PATCH_SITE, ROS_PATCH = 0x016c2ed6, bytes.fromhex('813d243b5e0bf2260000')   # cmp [0x0b5e3b24], 0x26f2
ITEM_ANGLE, ITEM_HEAD, ITEM_VEC = 0x0b5e3c2c, 0x0b5e3c38, 0x0b5e3c20
POS, STATE, ANIMREC = 0x2d000000, 0x2d000100, 0x2d000200


class RosIn(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int32), ('level_word', ctypes.c_int32), ('excellent', ctypes.c_int32),
                ('set_bits', ctypes.c_int32), ('position', ctypes.c_float * 3), ('select', ctypes.c_int32),
                ('held', ctypes.c_uint8), ('a2c', ctypes.c_int32), ('a30', ctypes.c_int32), ('scale', ctypes.c_float),
                ('has_state', ctypes.c_int32), ('state_prior_action', ctypes.c_uint16), ('state_frame', ctypes.c_float),
                ('state_prior_frame', ctypes.c_float), ('tick', ctypes.c_uint8), ('time', ctypes.c_float),
                ('has_record', ctypes.c_int32), ('kind_a', ctypes.c_int32), ('item_kind', ctypes.c_int32),
                ('anim_present', ctypes.c_int32), ('anim_action', ctypes.c_uint16), ('anim_speed', ctypes.c_float),
                ('pose_model_exists', ctypes.c_int32), ('object_alpha', ctypes.c_float)]


class RosOut(ctypes.Structure):
    _fields_ = [('drawn', ctypes.c_int32), ('spin', ctypes.c_int32), ('spin_angle', ctypes.c_float),
                ('pose_model', ctypes.c_int32), ('render_type', ctypes.c_int32), ('height', ctypes.c_float),
                ('action', ctypes.c_uint16), ('anim_frame', ctypes.c_float), ('anim_prior_frame', ctypes.c_float),
                ('anim_prior_action', ctypes.c_uint16), ('ticked', ctypes.c_int32), ('tick_speed', ctypes.c_float),
                ('position', ctypes.c_float * 3), ('scale', ctypes.c_float), ('alpha', ctypes.c_float),
                ('light', ctypes.c_float * 3), ('lighting', ctypes.c_uint8), ('level_word', ctypes.c_int32),
                ('excellent', ctypes.c_int32), ('set_bits', ctypes.c_int32), ('a2c', ctypes.c_int32),
                ('a30', ctypes.c_int32)]


def ros_client(world_args, case):
    import validate_renderchar as vr
    w = vr.World(*world_args)
    m = w.m
    m.write(ROS_PATCH_SITE, ROS_PATCH)
    pose = 0xa91 if (0x18e6 <= case['type'] < 0x22e6 or case['type'] in (0xace, 0xacf, 0xad0, 0xae5)) else case['type']
    level = (case['level_word'] >> 3) & 0xf
    if case['type'] == 0x26f2 and level in (0, 2):
        pose = 0x3890 if level == 0 else 0x3891
    if case['pose_exists']:
        w.add_model(pose, vr.MODEL, bones=4, meshes=1, actions=4)
    if case['record'] is not None:
        w.add_record(case['type'] - 0xae6, case['record'][0], 0, case['record'][1])
    m.ensure(0x06fce370, 4)
    m.w32(0x06fce370, case['time'])
    m.map(POS, 0x1000)
    m.write(POS, struct.pack('<3I', *case['position']))
    m.write(STATE, struct.pack('<HHII', 0, case['state'][0], case['state'][1], case['state'][2]))
    m.write(ANIMREC, struct.pack('<iiHHI', 20, 0, case['anim'][0], 0, case['anim'][1]) if case['anim'] else b'')
    for address in (ITEM_ANGLE, ITEM_HEAD, ITEM_VEC):
        m.ensure(address, 12)
    m.write(ITEM_ANGLE, struct.pack('<3I', *case['angle']))
    rec = []
    m.stub(0x0111d824, lambda mm: (rec.append(('anim_lookup', mm.ecx(), mm.arg(0))) or
                                   (ANIMREC if case['anim'] else 0)), 4)

    def animation(mm):
        model = mm.ecx()
        a = [mm.arg(i) for i in range(8)]
        rec.append(('animation', model, a, mm.r32(model + 0x90), struct.unpack('<H', mm.read(model + 0xa8, 2))[0]))
        return 0
    m.stub(0x012b5064, animation, 0x20)
    m.stub(0x012b4dd3, lambda mm: rec.append(('tick', mm.ecx(), [mm.arg(i) for i in range(6)])) or 0, 0x18)
    m.stub(0x0184a244, lambda mm: rec.append(('project',)) or 0, 0)

    def rpo(mm):
        a = [mm.arg(i) for i in range(16)]
        o = a[0]
        rec.append(('rpo', a, mm.read(o + 5, 1)[0], mm.r32(o + 0xa0), [mm.r32(o + 0x158 + 4 * k) for k in range(3)],
                    mm.r32(o + 0xdc), mm.r32(o + 0x5c), [mm.r32(a[3] + 4 * k) for k in range(3)]))
        return 0
    m.stub(0x017e63f4, rpo, 0)
    args = [case['type'], case['level_word'], case['excellent'], case['set_bits'], POS, case['select'], case['held'],
            case['a2c'], case['a30'], case['scale'], STATE if case['has_state'] else 0, case['tick']]
    result = m.run(ROS, args)
    angle1 = m.r32(ITEM_ANGLE + 4)
    return result, rec, angle1


def ros_compare(lib, world_args, case):
    result, rec, angle1 = ros_client(world_args, case)
    if not result['ok']:
        return ('stopped', result['stopped'], result['error']), None, None
    anim = [r for r in rec if r[0] == 'animation']
    ticks = [r for r in rec if r[0] == 'tick']
    rpos = [r for r in rec if r[0] == 'rpo']
    client = {'drawn': int(bool(anim)), 'spin': angle1 != case['angle'][1]}
    alpha_bits = None
    if anim:
        a = anim[0]
        client.update(height=a[3], action=a[4], anim=(a[2][1], a[2][2], a[2][3] & 0xffff),
                      animation_tail=(a[2][0], a[2][4], a[2][5], a[2][6], a[2][7]))
        client['ticked'] = ticks[0][2][3] if ticks else None
    if rpos:
        r = rpos[0]
        alpha_bits = r[5]
        client.update(rpo_args=(r[1][1], r[1][2], r[1][4], r[1][5], r[1][6], r[1][7]) + tuple(r[1][8:16]),
                      lighting=r[2], scale=r[3], position=tuple(r[4]), object_type=r[6], light=tuple(r[7]))
    client['spin_angle'] = angle1 if client['spin'] else None
    c = RosIn(type=case['type'], level_word=case['level_word'], excellent=case['excellent'], set_bits=case['set_bits'],
              select=case['select'], held=case['held'], a2c=case['a2c'], a30=case['a30'], scale=u2f(case['scale']),
              has_state=case['has_state'], state_prior_action=case['state'][0], state_frame=u2f(case['state'][1]),
              state_prior_frame=u2f(case['state'][2]), tick=case['tick'], time=u2f(case['time']),
              has_record=int(case['record'] is not None), kind_a=(case['record'] or (0, 0))[0],
              item_kind=(case['record'] or (0, 0))[1], anim_present=int(bool(case['anim'])),
              anim_action=(case['anim'] or (0, 0))[0], anim_speed=u2f((case['anim'] or (0, 0))[1]),
              pose_model_exists=case['pose_exists'], object_alpha=u2f(alpha_bits or 0))
    for k in range(3):
        c.position[k] = u2f(case['position'][k])
    out = RosOut()
    lib.mu_hud_object_screen(ctypes.byref(c), ctypes.byref(out))
    native = {'drawn': out.drawn, 'spin': bool(out.spin)}
    if out.drawn:
        native.update(height=f2u(out.height), action=out.action,
                      anim=(f2u(out.anim_frame), f2u(out.anim_prior_frame), out.anim_prior_action),
                      animation_tail=(0x06fce398, ITEM_ANGLE, ITEM_HEAD, 0, 0))
        native['ticked'] = f2u(out.tick_speed) if out.ticked else None
        native.update(rpo_args=(out.render_type, 0, f2u(out.alpha), out.level_word & 0xffffffff, out.excellent,
                                out.set_bits, 1, 1, 1,
                                0, 2, out.a2c & 0xffffffff, out.a30 & 0xffffffff, 0),
                      lighting=out.lighting, scale=f2u(out.scale), position=tuple(f2u(v) for v in out.position),
                      object_type=out.render_type, light=tuple(f2u(v) for v in out.light))
    native['spin_angle'] = f2u(out.spin_angle) if out.spin else None
    return client, native, rec


def random_ros_case(rng):
    def fb(lo, hi):
        return f2u(rng.uniform(lo, hi))
    group = rng.choice([0, 1, 2, 4, 5, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 13, 14, 15])
    index = rng.randrange(0, 64) if rng.random() < 0.8 else rng.randrange(512)
    t = 0xae6 + group * 512 + index
    t = rng.choice([t] * 8 + [0x26f2, 0x26f2, 0xace, 0xacf, 0xad0, 0xae5, 0x1927, 0x192c, 0x193c, 0x1b3a, 0x1b40,
                              0x1b3f, rng.randrange(0x18e6, 0x22e6)])
    anim = None if rng.random() < 0.6 else (rng.randrange(0, 6), fb(0.05, 0.6))
    return {'type': t, 'level_word': rng.choice([rng.randrange(16) << 3, 0, 16, rng.randrange(0x100)]),
            'excellent': rng.choice([0, 0, 1, rng.randrange(64)]), 'set_bits': rng.choice([0, 0, 1, 5, 0x22]),
            'position': [fb(0, 1700), fb(0, 1000), rng.choice([f2u(-100.0), f2u(-130.0), f2u(-140.0)])],
            'select': rng.choice([0, 0, 1, 2]), 'held': rng.choice([0, 0, 0, 1]), 'a2c': rng.choice([0, -1, 7]) & 0xffffffff,
            'a30': rng.choice([0, -1, 3]) & 0xffffffff, 'scale': fb(0.0005, 1.5),
            'has_state': rng.choice([0, 1, 1]), 'state': (rng.randrange(0, 6), fb(0, 9), fb(0, 9)),
            'tick': rng.choice([0, 1, 1]), 'time': fb(0, 3e6),
            'record': None if rng.random() < 0.15 or t < 0xae6 else (rng.choice([0, 0, 0xc, rng.randrange(256)]),
                                                         rng.choice([0, 0, 4, 4, rng.randrange(16)])),
            'anim': anim, 'pose_exists': int(rng.random() < 0.95), 'angle': [fb(-90, 90), fb(-180, 180), fb(-90, 90)]}


def object_screen_section(text, data, args):
    lib = build('reconstructed/hud', f'libmu_hud.{SUFFIX}')
    lib.mu_hud_object_screen.argtypes = [ctypes.POINTER(RosIn), ctypes.POINTER(RosOut)]
    flag = default_evidence('trig-state-15/captures/late/math-dispatch-flag.bin').read_bytes()[:4]
    feature = default_evidence('x86-math-capture-09/cpu-features.bin').read_bytes()[:4]
    world_args = (text, data, flag, feature)
    rng = random.Random(args.seed + 5)
    tally = Tally()
    cover = {'armour_on_player': 0, 'box_remap': 0, 'animated': 0, 'ticked': 0, 'held': 0, 'spin': 0, 'kind_a_0c': 0,
             'no_model': 0, 'height_nonzero': 0}
    control = 0
    for i in range(args.cases):
        case = random_ros_case(rng)
        client, native, rec = ros_compare(lib, world_args, case)
        tally.check(i, client, native)
        if native and native.get('drawn'):
            cover['armour_on_player'] += 0x18e6 <= case['type'] < 0x22e6
            cover['box_remap'] += case['type'] == 0x26f2 and native['rpo_args'][0] != 0x26f2
            cover['animated'] += native['action'] != 0
            cover['ticked'] += native['ticked'] is not None
            cover['height_nonzero'] += native['height'] != 0
            cover['kind_a_0c'] += bool(case['record'] and case['record'][0] == 0xc)
            # negative control: NATIVE-GFX-003's stand-in (armour centred, own skeleton: height 0 on the item model)
            control += 0x18e6 <= case['type'] < 0x22e6 and isinstance(client, dict) and client.get('height') != 0
        elif native:
            cover['no_model'] += 1
        cover['held'] += case['held']
        cover['spin'] += case['select'] == 1
    return tally.report(coverage=cover, patched_site=hex(ROS_PATCH_SITE), patch_bytes=ROS_PATCH.hex(),
                        control_armour_height_detected=control)


# ---------------------------------------------------------------- special_models
LOADER, ACCESS_MODEL = 0x0183220e, 0x018202b4
SPECIAL_HEADER = ROOT / 'reconstructed/items/special_models.h'


def loader_calls(world_args):
    """The item-model loader 0x0183220e executed: its AccessModel(model, dir, name, number) calls in order."""
    import validate_renderchar as vr
    w = vr.World(*world_args)
    m = w.m
    calls = []

    def access(mm):
        calls.append((mm.arg(0), cstring(mm, mm.arg(1)), cstring(mm, mm.arg(2)), mm.arg(3) - (1 << 32)
                      if mm.arg(3) & 0x80000000 else mm.arg(3)))
        return 0
    m.stub(ACCESS_MODEL, access, 0)
    m.stub(0x0181fbe9, lambda mm: 0, 0)              # OpenTexture (recorded by World otherwise)
    m.stub(0x0185baac, lambda mm: 1, 0)              # LoadBitmap
    m.stub(0x00eaaa75, lambda mm: 0, 8)              # model mesh-flag getter: no model
    m.stub(0x00d2b17c, lambda mm: 0, 0)              # item render registry fill
    m.stub(0x0121d5cd, lambda mm: 0x01ec3030, 0)     # a singleton getter
    m.stub(0x00a92b5d, lambda mm: 0, 0)
    m.stub(0x009619dd, lambda mm: 0, 0)              # sprintf of the bitmap names (LoadBitmap is stubbed)
    result = m.run(LOADER, [])
    return result, calls


def cstring(mm, address):
    out = bytearray()
    while len(out) < 256:
        b = mm.read(address + len(out), 1)
        if b == b'\0':
            break
        out += b
    return out.decode('latin1')


def access_model_name(world_args, name, number):
    """AccessModel 0x018202b4 executed: the file name it passes to the BMD open 0x012b3812."""
    import validate_renderchar as vr
    w = vr.World(*world_args)
    m = w.m
    w.add_model(0x3890, vr.MODEL)
    m.uc.hook_del(m.hooks.pop(ACCESS_MODEL))       # World records AccessModel: execute it here
    m.stubs.pop(ACCESS_MODEL)
    m.map(0x2e000000, 0x1000)
    m.write(0x2e000000, b'Data\\Item\\\0')
    m.write(0x2e000100, name.encode() + b'\0')
    seen = []

    def sprintf(mm):
        # the C library sprintf with the client's own format string (%s, %d only in these formats)
        fmt, args, k = cstring(mm, mm.arg(1)), [], 2
        for spec in re.findall(r'%[sd]', fmt):
            value = mm.arg(k)
            args.append(cstring(mm, value) if spec == '%s' else value - (1 << 32) if value & 0x80000000 else value)
            k += 1
        text_out = (fmt % tuple(args)).encode('latin1') + b'\0'
        mm.write(mm.arg(0), text_out)
        return len(text_out) - 1
    m.stub(0x009619dd, sprintf, 0)
    m.stub(0x012b3812, lambda mm: seen.append((cstring(mm, mm.arg(0)), cstring(mm, mm.arg(1)))) or 1, 0xc)
    result = m.run(ACCESS_MODEL, [0x3890, 0x2e000000, 0x2e000100, number & 0xffffffff])
    return result, seen


def emit_special_models(path, calls):
    lines = ['/* Generated by scripts/validate_fidelity.py --emit-special-models (NATIVE-FIDELITY-001): the',
             ' * AccessModel(model, folder, name, number) calls of the item-model loader 0x0183220e, executed under',
             ' * Unicorn, in call order. The file is folder + name + (number < 0 ? "" : number < 10 ? "0<n>" : "<n>")',
             ' * + ".bmd" (AccessModel 0x018202b4\'s sprintf formats, also executed). */',
             '#ifndef MU_GI_SPECIAL_MODELS_H', '#define MU_GI_SPECIAL_MODELS_H', '',
             'static const struct { int32_t model; const char *folder, *name; int32_t number; } mu_gi_special_models[] = {']
    for model, folder, name, number in calls:
        lines.append('    {0x%04x, "%s", "%s", %d},' % (model, folder.replace('\\', '\\\\'), name, number))
    lines += ['};', '', '#endif', '']
    path.write_text('\n'.join(lines))


def header_calls(path):
    out = []
    for m in re.finditer(r'\{0x([0-9a-f]+), "([^"]*)", "([^"]*)", (-?\d+)\}', path.read_text()):
        out.append((int(m.group(1), 16), m.group(2).replace('\\\\', '\\'), m.group(3), int(m.group(4))))
    return out


def special_models_section(text, data, args):
    flag = default_evidence('trig-state-15/captures/late/math-dispatch-flag.bin').read_bytes()[:4]
    feature = default_evidence('x86-math-capture-09/cpu-features.bin').read_bytes()[:4]
    world_args = (text, data, flag, feature)
    result, calls = loader_calls(world_args)
    if args.emit_special_models:
        emit_special_models(args.emit_special_models, calls)
    tally = Tally()
    tally.check('loader', calls, header_calls(SPECIAL_HEADER))
    lib = build('reconstructed/items', f'libclient_items.{SUFFIX}')
    lib.mu_gi_special_model_file.argtypes = [ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t]
    lib.mu_gi_special_model_file.restype = ctypes.c_int
    names = 0
    for number in (-1, 0, 2, 9, 10, 13, 99):
        r, seen = access_model_name(world_args, 'MagicBox', number)
        expected = None
        if number == -1:
            expected = 'MagicBox.bmd'
        else:
            expected = 'MagicBox%s%d.bmd' % ('0' if number < 10 else '', number)
        tally.check(('format', number), seen[0][1] if seen else r['stopped'], expected)
    for model, folder, name, number in calls:
        buf = ctypes.create_string_buffer(256)
        ok = lib.mu_gi_special_model_file(model, buf, 256)
        expected = folder + name + ('' if number < 0 else ('0%d' % number if number < 10 else '%d' % number)) + '.bmd'
        tally.check(('file', hex(model)), buf.value.decode() if ok else None, expected)
        names += 1
    installed = None
    if args.game_root:
        installed = sum((args.game_root / (folder + name + ('' if number < 0 else ('0%d' % number if number < 10 else
                                                                                 '%d' % number)) + '.bmd'
                                           ).replace('\\', '/')).exists() for _, folder, name, number in calls)
    return tally.report(loader_ok=result['ok'], access_model_calls=len(calls), installed_files=installed,
                        control_loader_ran=result['ok'] and len(calls) > 30)


# ---------------------------------------------------------------- set_prefix and lang_tables (snapshot machine)
SET_MANAGER_PTR, SET_MANAGER_CTOR, SET_MANAGER_SIZE = 0x01d1dcc0, 0x009e00d8, 0x8dcfc
SET_LOAD, SET_PREFIX = 0x009e02a8, 0x009e0551
CRT_FOPEN, CRT_FREAD, CRT_FCLOSE = 0x01988f83, 0x01989230, 0x01988c95
CRT_NEW, CRT_MALLOC, CRT_FREE, CRT_DELETE = 0x0191ba7b, 0x0191bab9, 0x0191bac2, 0x0191ba5f
ITEM_TABLE, ITEM_FIND = 0x00cd4ea8, 0x00cd5d29
PENTAGRAM_LOOKUP, INVENANIM_LOOKUP, LEGENDARY_LOOKUP = 0x011447ac, 0x0111d824, 0x011288c7


def item_kinds(game_root):
    """code -> kind B (+0x251) of the installed Item.bmd (native/build/mu-data dump)."""
    out = subprocess.run([str(ROOT / 'native/build/mu-data'), 'dump', str(game_root / 'Data/Local/item.bmd')],
                         check=True, capture_output=True, text=True).stdout
    return {row['code']: row['attributes']['kind_b'] for row in json.loads(out)['items']}


def find_file(game_root, client_path):
    target = game_root
    for part in client_path.replace('\\', '/').split('/'):
        if not part or part == '.':
            continue
        names = {p.name.lower(): p for p in target.iterdir()} if target.is_dir() else {}
        if part.lower() not in names:
            return None
        target = names[part.lower()]
    return target


def snapshot_machine(text, data, snap, game_root, kinds):
    import client_ui_machine as cm
    import validate_lang as vl
    m = vl.LangMachine(text, data, snap)
    m.prepare(force=True)
    m.heap_checks(False)
    # the CRT's memset/memcpy feature words: __favor 0x0bdcb284 (no ERMS) and the captured math feature word
    m.put32(0x0bdcb284, 0)
    m.write(0x01cf6618, default_evidence('x86-math-capture-09/cpu-features.bin').read_bytes()[:4])
    m.write(0x01cf0448, bytes([0xfc, 0xcf, 0xab, 0]))   # the record key global (as scripts/validate_data_tables.py)
    m.put32(0x01cf65c0, 0xc179bffe)                       # __security_cookie (any value; Linux capture's)
    files, records = {}, {}

    def arg(k):
        return m.args(k + 1)[k]

    def new(mm):
        return mm.alloc(arg(0), define=True)
    m.stub(CRT_NEW, new)
    m.stub(CRT_MALLOC, new)
    m.stub(CRT_FREE, lambda mm: 0)
    m.stub(CRT_DELETE, lambda mm: 0)
    m.stub(0x019a4d50, lambda mm: 0)                     # _free_base

    def option_text(mm):
        # 0x009df67e(out, option, value): the set option's description (sprintf over ItemSetOptionText); the
        # prefix never reads it: an empty MSVC std::string (buffer 0, size 0, capacity 15)
        out = arg(0)
        mm.write(out, bytes(16) + struct.pack('<II', 0, 15))
        return out
    m.stub(0x009df67e, option_text, 0xc)

    def fopen(mm):
        path = mm.cstr(arg(0)).decode('latin1')
        found = find_file(game_root, path)
        if found is None:
            return 0
        handle = 0x100 + len(files)
        files[handle] = [found.read_bytes(), 0, path]
        return handle

    def fread(mm):
        buf, size, count, handle = mm.args(4)
        f = files[handle]
        n = min(size * count, len(f[0]) - f[1])
        mm.write(buf, f[0][f[1]:f[1] + n])
        f[1] += n
        return n // size if size else 0
    m.stub(CRT_FOPEN, fopen)
    m.stub(CRT_FREAD, fread)
    m.stub(CRT_FCLOSE, lambda mm: 0)
    m.stub(ITEM_TABLE, lambda mm: 0x0bf00000)

    def find(mm):
        code = arg(0)
        if code not in kinds:
            return 0
        if code not in records:
            r = mm.alloc(0x2c4, define=True)
            mm.write(r, bytes(0x2c4))
            mm.write(r + 0x251, bytes([kinds[code] & 0xff]))
            records[code] = r
        return records[code]
    m.stub(ITEM_FIND, find, 4)
    return m, files


def set_prefix_section(text, data, args):
    import live_lang_to_plain as plain
    if not args.snapshot or not args.game_root:
        return {'skipped': 'needs --snapshot and --game-root', 'ok': True}
    snap = plain.Snapshot.load(args.snapshot)
    kinds = item_kinds(args.game_root)
    m, files = snapshot_machine(text, data, snap, args.game_root, kinds)
    obj = m.alloc(SET_MANAGER_SIZE, define=True)
    m.call(SET_MANAGER_CTOR, [], ecx=obj)
    m.put32(SET_MANAGER_PTR, obj)
    loaded = m.call(SET_LOAD, [], ecx=obj) & 0xff
    # the native side: the same installed files, the plaintext tables of the same snapshot
    import tempfile
    work = Path(tempfile.mkdtemp())
    plain.convert(snap, work)
    lib = build('reconstructed/items', f'libclient_items.{SUFFIX}')
    decoded = {}
    for name, size, count in (('itemsettype.bmd', 10, 0x2c00), ('itemsetoption.bmd', 0x1d4, 1000)):
        raw = find_file(args.game_root, 'Data/Local/' + name).read_bytes()
        key = bytes([0xfc, 0xcf, 0xab])
        decoded[name] = bytes(b ^ key[i % size % 3] for i, b in enumerate(raw[:size * count]))
    legendary, legendary_default = {}, [-1] * 4
    for line in (work / 'legendary.tsv').read_text().splitlines():
        if line and not line.startswith('#'):
            f = line.split('\t')
            if f[0] == 'default':
                legendary_default = [int(x) for x in f[1:5]]
            else:
                legendary[int(f[0])] = [int(x) for x in f[1:5]]
    cash_names, cash_items = [], []
    for line in (work / 'cashsets.tsv').read_text().splitlines():
        f = line.split('\t')
        if f[0] == 'set':
            cash_names.append((plain.unescape(f[2]), plain.unescape(f[3])))
        elif f[0] == 'item':
            cash_items.extend(int(x) for x in f[1:4])
    HAS = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32)
    LEG = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32))

    class Inputs(ctypes.Structure):
        _fields_ = [('set_type', ctypes.c_char_p), ('set_option', ctypes.c_char_p), ('context', ctypes.c_void_p),
                    ('has_record', HAS), ('legendary', LEG), ('cash_set_count', ctypes.c_size_t),
                    ('cash_names', ctypes.POINTER(ctypes.c_char_p)), ('cash_names2', ctypes.POINTER(ctypes.c_char_p)),
                    ('cash_item_count', ctypes.c_size_t), ('cash_items', ctypes.POINTER(ctypes.c_int32))]

    def has_record(ctx, code):
        return int(code in kinds)

    def legend(ctx, type_, out):
        for k, v in enumerate(legendary.get(type_, legendary_default)):
            out[k] = v
        return 1
    has_cb, leg_cb = HAS(has_record), LEG(legend)
    names1 = (ctypes.c_char_p * max(1, len(cash_names)))(*[n[0] for n in cash_names])
    names2 = (ctypes.c_char_p * max(1, len(cash_names)))(*[n[1] for n in cash_names])
    items_c = (ctypes.c_int32 * max(1, len(cash_items)))(*cash_items)
    inputs = Inputs(decoded['itemsettype.bmd'], decoded['itemsetoption.bmd'], None, has_cb, leg_cb, len(cash_names),
                    names1, names2, len(cash_items) // 3, items_c)
    lib.mu_gi_sets_build.restype = ctypes.c_void_p
    lib.mu_gi_sets_build.argtypes = [ctypes.POINTER(Inputs)]
    lib.mu_gi_set_prefix.restype = ctypes.c_char_p
    lib.mu_gi_set_prefix.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint8, ctypes.c_uint8]
    lib.mu_gi_sets_count.restype = ctypes.c_size_t
    lib.mu_gi_sets_count.argtypes = [ctypes.c_void_p]
    sets = lib.mu_gi_sets_build(ctypes.byref(inputs))
    # queries: every code with a set word, the legendary and cash codes, random others; set bits of each kind
    st = decoded['itemsettype.bmd']
    codes = {c for c in range(0x2c00) if any(st[c * 10 + 2 * k] | st[c * 10 + 2 * k + 1] for k in range(4))}
    codes |= {c for v in legendary.values() for c in v if c >= 0}
    codes |= {cash_items[3 * i] * 512 + cash_items[3 * i + 1] for i in range(len(cash_items) // 3)}
    rng = random.Random(args.seed + 9)
    codes |= {rng.randrange(0x2c00) for _ in range(200)}
    tally, prefixed, kind79 = Tally(), 0, 0
    out = m.alloc(0x40, define=True)
    bit_choices = (0, 1, 2, 5, 6, 0x10, 0x20, 0x21, 0x33, 0x44, 0xff)
    for code in sorted(codes):
        for bits in (rng.sample(bit_choices, args.set_bits) if args.set_bits < len(bit_choices) else bit_choices):
            m.call(SET_PREFIX, [out, code, bits], ecx=obj)
            client = m.std_string(out)
            native = lib.mu_gi_set_prefix(sets, code, bits, kinds.get(code, 0) & 0xff)
            tally.check((code, bits), client, native)
            prefixed += bool(client)
            kind79 += bool(client) and kinds.get(code) == 0x79
    # negative controls: the kind B 0x79 rule left out; the legendary table left out (informational)
    control = sum(lib.mu_gi_set_prefix(sets, c, b, 0) != lib.mu_gi_set_prefix(sets, c, b, kinds.get(c, 0) & 0xff)
                  for c in sorted(codes) for b in (0, 1, 2))
    inputs.legendary = LEG(lambda ctx, t, o: 0)
    plain_sets = lib.mu_gi_sets_build(ctypes.byref(inputs))
    legendary_diff = sum(lib.mu_gi_set_prefix(plain_sets, c, b, kinds.get(c, 0) & 0xff) !=
                         lib.mu_gi_set_prefix(sets, c, b, kinds.get(c, 0) & 0xff)
                         for c in sorted(codes) for b in (0, 1, 2, 0x10, 0x20))
    return tally.report(loaded=loaded, files=[f[2] for f in files.values()], native_sets=lib.mu_gi_sets_count(sets),
                        codes=len(codes), prefixed_answers=prefixed, kind_b_79_answers=kind79,
                        control_without_kind_b_79_differs=control, legendary_table_changes_answers=legendary_diff)


def lang_tables_section(text, data, args):
    """PentagramOption 0x011447ac and InvenItemAnimation 0x0111d824 over the snapshot against mu_lang."""
    import live_lang_to_plain as plain
    import validate_lang as vl
    if not args.snapshot:
        return {'skipped': 'needs --snapshot', 'ok': True}
    snap = plain.Snapshot.load(args.snapshot)
    m = vl.LangMachine(text, data, snap)
    import tempfile
    work = Path(tempfile.mkdtemp())
    plain.convert(snap, work)
    nat = vl.Native(work)
    L = nat.lib
    L.mu_lang_pentagram_tier.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
    L.mu_lang_inven_anim.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_uint16),
                                     ctypes.POINTER(ctypes.c_float)]
    L.mu_lang_legendary.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
    h = nat.load(work)
    tally = Tally()
    pent = [k for k, _ in snap.tree(plain.PENTAGRAM + 0x3c)]
    anim = [k for k, _ in snap.tree(plain.INVENANIM + 0x38)]
    leg = [k for k, _ in snap.tree(plain.LEGENDARY + 0x38)]
    rng = random.Random(args.seed + 13)
    for code in pent + [rng.randrange(0x2c00) for _ in range(100)]:
        m.prepare()
        record = m.call(PENTAGRAM_LOOKUP, [code], ecx=plain.PENTAGRAM)
        tier = ctypes.c_int32()
        L.mu_lang_pentagram_tier(h, code, ctypes.byref(tier))
        tally.check(('pentagram', code), struct.unpack('<i', m.read(record + 0x24, 4))[0], tier.value)
    for code in anim + [rng.randrange(0x2c00) for _ in range(100)]:
        m.prepare()
        record = m.call(INVENANIM_LOOKUP, [code], ecx=plain.INVENANIM)
        action, speed = ctypes.c_uint16(), ctypes.c_float()
        ok = L.mu_lang_inven_anim(h, code, ctypes.byref(action), ctypes.byref(speed))
        client = None if not record else (struct.unpack('<H', m.read(record + 8, 2))[0], m.u32(record + 0xc))
        tally.check(('invenanim', code), client, (action.value, f2u(speed.value)) if ok else None)
    for type_ in leg + [rng.randrange(1000) for _ in range(100)]:
        m.prepare()
        record = m.call(LEGENDARY_LOOKUP, [type_], ecx=plain.LEGENDARY)
        codes = (ctypes.c_int32 * 4)()
        L.mu_lang_legendary(h, type_, codes)
        tally.check(('legendary', type_), list(struct.unpack('<4i', m.read(record + 4, 16))), list(codes))
    return tally.report(pentagram_keys=len(pent), invenanim_keys=len(anim), legendary_keys=len(leg))


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
    parser.add_argument('--emit-special-models', type=Path)
    parser.add_argument('--snapshot', type=Path, help='langread snapshot (set_prefix, lang_tables)')
    parser.add_argument('--set-bits', type=int, default=3, help='set-bit values tried per code')
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
    if 'set_prefix' in sections:
        report['set_prefix'] = set_prefix_section(text, data, args)
    if 'lang_tables' in sections:
        report['lang_tables'] = lang_tables_section(text, data, args)
    if args.output:
        args.output.write_text(json.dumps(report, indent=1, default=str))
    summary = {k: {kk: vv for kk, vv in v.items() if kk != 'failures' or vv} for k, v in report.items()
               if isinstance(v, dict) and 'ok' in v}
    print(json.dumps(summary, default=str)[:6000])
    return 0 if summary and all(v['ok'] for v in summary.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
