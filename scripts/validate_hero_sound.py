#!/usr/bin/env python3
"""Compare the authored hero footstep routines with the client (NATIVE-WORLD-002).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py: declared regions with a defined-byte mask;
an undefined read, an undeclared access or an unmapped access stops a case):

* PlayWalkSound 0x013b1f61 from its entry. The world predicates 0x016a88d3,
  0x016a88ae, 0x00ea233c, 0x00e42f6d, the safe-zone getter 0x0095fb27 and the
  tile index 0x016d34db run as client code. Stubs: the singleton getter
  0x009c104e and its predicate 0x0106b9f7(hero, 2, 1) (an external character
  state manager; the stub records the arguments and returns the case's AL),
  and SND_Play 0x00a6ac96 (records id, object, loop).
* the footstep trigger 0x013b8090..0x013b8187 inside 0x013b23f8, entered with
  that routine's frame built ([ebp+8] = character, [ebp+0xc] = object) and
  stopped at its end. PlayWalkSound underneath runs as client code with the
  stubs above, so the comparison covers the foot flags and the SND_Play ids.
* the foot reset 0x013a773c..0x013a777e inside 0x013a763e; the animation step
  0x013960d2 is a stub that returns the case's AL (upper EAX bits poisoned).
* the HeroTile tail of MoveHero 0x016ad7a5..0x016ad81f with MoveHero's frame;
  the vector accessor 0x00cfc922 runs as client code.

The authored C (reconstructed/audio/hero_sound.c, in libclient_audio) runs on
the same inputs. Negative controls (Python statements with one planted
mistake each) must disagree with the client on some cases.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'

PLAY_WALK_SOUND = 0x013b1f61
TRIGGER = (0x013b8090, 0x013b8187)
RESET = (0x013a773c, 0x013a777e, 0x013a7800)   # start, end of the reset, target of its skip
HERO_TILE = (0x016ad7a5, 0x016ad81f)
SINGLETON, MANAGER_STATE, SND_PLAY, ANIMATION_STEP = 0x009c104e, 0x0106b9f7, 0x00a6ac96, 0x013960d2
HERO_PTR, WORLD, HERO_TILE_GLOBAL = 0x0a39d754, 0x01cf15fc, 0x0b437c10
ATTRIBUTES, LAYER1 = 0x0b795420, 0x0b735420
HERO, OTHER = 0x22000000, 0x22100000
OBJECT = 0x3254
FAKE_MANAGER = 0x20000000
BODIES = {  # start, exclusive end, SHA-256 of the captured bytes
    'play_walk_sound': (0x013b1f61, 0x013b2160,
                     'e9d13625342d6c99e65800ceb1ebc10bc9f46035b22c154193150a4cbed54c2f'),
    'footstep_trigger': (0x013b8090, 0x013b8187,
                     '2e591bc4ce071a9cd42d9f8e545719568daa2a2a5d46e2b82885e0941a225883'),
    'foot_reset': (0x013a773c, 0x013a777e,
                     'b12e66aa42ff2b091ab40dbaf22f8609f0f3804399f003b2b7a16b3c6eda28a6'),
    'hero_tile_tail': (0x016ad7a5, 0x016ad81f,
                     '1f08994b84af38c3ef73044ef4ba4600545d93e9bbf3431bfdde147d13bcbe40'),
    'water_world': (0x016a88d3, 0x016a8904,
                     'a9c1a24bbf8f6691a629aa21dada57bb6617b739d9d4f99f23ca49683101c0e9'),
    'atlans_world': (0x016a88ae, 0x016a88d3,
                     'c953585e6f69bbe54ac140794ee02a0181ea763c1ab5e01811bdd57c552c44f4'),
    'raklion_world': (0x00ea233c, 0x00ea2359,
                     '17ba886f5c9e2df07d15d6f6c7874d2e21fed5fa91cc51ce724e2c7032cdc336'),
    'santa_world': (0x00e42f6d, 0x00e42f81,
                     '5ef4890e11ec8e3c41cc13a4774415419f9ae7312f0f2e1e90cb4a28e1300b5c'),
    'safe_zone_getter': (0x0095fb27, 0x0095fb37,
                     '3927f59e7cd6ea52bf9ef85c8c29e1c9dfa93fd5a1c18c17a69f38179b6627f4'),
    'tile_index': (0x016d34db, 0x016d34f6,
                     '0d1422308044ba115f6abd792d16efda7d30c1b55b539b7d2394281e0325e9ff'),
    'vector_at': (0x00cfc922, 0x00cfc936,
                     '0518ccd07aae2d4de135e2ab9c0b1c22e7898200e3c42fd1db23a397871043b5'),
}


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def load_library(path):
    lib = ctypes.CDLL(str(path))
    lib.mu_hero_tile.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.c_float]
    lib.mu_hero_tile.restype = ctypes.c_int32
    lib.mu_hero_tile_index.argtypes = [ctypes.c_float, ctypes.c_float]
    lib.mu_hero_tile_index.restype = ctypes.c_int32
    lib.mu_walk_sound_id.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.mu_walk_sound_id.restype = ctypes.c_int32
    lib.mu_footstep_trigger.argtypes = [ctypes.c_int32, ctypes.c_int, ctypes.c_uint16, ctypes.c_float,
                                        ctypes.c_void_p]
    lib.mu_footstep_trigger.restype = ctypes.c_int
    lib.mu_footstep_reset.argtypes = [ctypes.c_uint8, ctypes.c_void_p, ctypes.c_void_p]
    lib.mu_footstep_reset.restype = ctypes.c_int
    return lib


class WalkSoundState(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('hero_tile', ctypes.c_int32), ('hero_action', ctypes.c_uint16),
                ('hero_safe_zone', ctypes.c_uint8), ('hero_x', ctypes.c_int32), ('hero_y', ctypes.c_int32),
                ('manager_state', ctypes.c_uint8)]


# --------------------------------------------------------------------------
# Client side.

def hero_regions(case, character=HERO, object_fields=True):
    """The hero record with only the fields the routines read defined."""
    hero = am.undefined_region('hero', HERO, 0x3400)
    hero.define(HERO+4, bytes([case['safe']]))
    hero.define(HERO+0x180, struct.pack('<ii', case['x'], case['y']))
    if object_fields:
        hero.define(HERO+OBJECT+0x2a, struct.pack('<H', case['action']))
    return hero


def walk_sound_regions(case):
    return [am.defined_region('hero-pointer', HERO_PTR, struct.pack('<I', HERO), writable=False),
            am.defined_region('world', WORLD, struct.pack('<i', case['world']), writable=False),
            am.defined_region('hero-tile', HERO_TILE_GLOBAL, struct.pack('<i', case['tile']), writable=False),
            am.defined_region('attributes', ATTRIBUTES, case['attributes'], writable=False)]


def walk_sound_stubs(case, record):
    def singleton(m):
        record.append(('singleton',))
        return FAKE_MANAGER

    def manager_state(m):
        this = m.uc.reg_read(m.x86.UC_X86_REG_ECX)
        record.append(('manager', this, m.argument(0), m.argument(1), m.argument(2)))
        return (0xdeadbe00 | case['manager']), 0xc

    def snd_play(m):
        record.append(('snd_play', m.argument(0), m.argument(1), m.argument(2)))
        return 0

    return {SINGLETON: singleton, MANAGER_STATE: manager_state, SND_PLAY: snd_play}


class EndHook:
    """Stops a fragment at its end address."""

    def __init__(self, machine, ends):
        self.machine, self.reached = machine, None
        self.hooks = [machine.uc.hook_add(machine.UC_HOOK_CODE, self.hit, begin=end, end=end) for end in ends]
        machine.uc.ctl_flush_tb()

    def hit(self, uc, address, size, ignored):
        self.reached = address
        uc.emu_stop()

    def close(self):
        for hook in self.hooks:
            self.machine.uc.hook_del(hook)


def run_fragment(machine, span, arguments, regions, stubs, frame):
    end = EndHook(machine, span[1:])
    try:
        result = machine.execute(span[0], arguments, regions, stubs, frame=frame)
    finally:
        end.close()
    ok = end.reached is not None and result['stopped'] is None and result['error'] is None
    result['end'] = end.reached
    return ok, result


def client_walk_sound(machine, case):
    record = []
    regions = [*walk_sound_regions(case), hero_regions(case)]
    result = machine.execute(PLAY_WALK_SOUND, [], regions, walk_sound_stubs(case, record))
    return {'ok': result['ok'], 'stopped': str(result['stopped']), 'error': result['error'], 'calls': record}


def client_trigger(machine, case):
    record = []
    hero = hero_regions(case)
    if case['is_hero']:
        character, obj = HERO, HERO+OBJECT
        regions = [*walk_sound_regions(case), hero]
        hero.define(HERO+0xc, bytes(case['foot']))
        hero.define(obj+0x5c, struct.pack('<I', case['type']))
        hero.define(obj+0xd0, struct.pack('<f', case['frame']))
    else:
        character, obj = OTHER, OTHER+OBJECT
        other = am.undefined_region('character', OTHER, 0x3400)
        other.define(OTHER+0xc, bytes(case['foot']))
        other.define(obj+0x5c, struct.pack('<I', case['type']))
        other.define(obj+0x2a, struct.pack('<H', case['action']))
        other.define(obj+0xd0, struct.pack('<f', case['frame']))
        regions = [*walk_sound_regions(case), hero, other]
    ok, result = run_fragment(machine, TRIGGER, [character, obj], regions, walk_sound_stubs(case, record),
                              (0x5c8+0x10, {}))
    name = 'hero' if case['is_hero'] else 'character'
    data = result['regions'][name]
    return {'ok': ok, 'stopped': str(result['stopped']), 'error': result['error'],
            'foot': list(data[0xc:0xe]), 'calls': record}


def client_reset(machine, case):
    record = []
    character = am.undefined_region('character', OTHER, 0x3400)
    character.define(OTHER+0xc, bytes(case['foot']))
    character.define(OTHER+0x168, struct.pack('<i', case['field']))

    def step(m):
        record.append(('step', m.argument(0), m.argument(1)))
        return 0xdeadbe00 | case['al']

    ok, result = run_fragment(machine, RESET, [OTHER, OTHER+OBJECT], [character], {ANIMATION_STEP: step}, (8, {}))
    data = result['regions']['character']
    return {'ok': ok, 'stopped': str(result['stopped']), 'error': result['error'], 'foot': list(data[0xc:0xe]),
            'field': struct.unpack_from('<i', data, 0x168)[0], 'calls': record, 'reset': result['end'] == RESET[1]}


def client_tile(machine, case):
    hero = am.undefined_region('hero', HERO, 0x3400)
    hero.define(HERO+OBJECT+0x158, struct.pack('<ff', case['px'], case['py']))
    regions = [am.defined_region('hero-pointer', HERO_PTR, struct.pack('<I', HERO), writable=False), hero,
               am.defined_region('layer1', LAYER1, case['layer1'], writable=False),
               am.undefined_region('hero-tile', HERO_TILE_GLOBAL, 4)]
    ok, result = run_fragment(machine, HERO_TILE, [], regions, {}, (0x5e74+0x10, {}))
    tile = struct.unpack('<i', result['regions']['hero-tile'])[0]
    return {'ok': ok, 'stopped': str(result['stopped']), 'error': result['error'], 'tile': tile}


# --------------------------------------------------------------------------
# Authored side and negative controls.

def authored_walk_sound(lib, case, attributes):
    state = WalkSoundState(case['world'], case['tile'], case['action'], case['safe'], case['x'], case['y'],
                           case['manager'])
    return lib.mu_walk_sound_id(ctypes.byref(state), attributes)


def expected_calls(case, sound_id):
    """Boundary calls PlayWalkSound makes for a sound id (as the C decides it)."""
    calls = []
    if not (0x59 <= case['action'] <= 0x5f):
        calls += [('singleton',), ('manager', FAKE_MANAGER, HERO, 2, 1)]
    if sound_id >= 0:
        calls.append(('snd_play', sound_id, 0, 0))
    return calls


def model_sound(case, mistake=None):
    """Python statement of PlayWalkSound with an optional planted mistake."""
    a, w, t = case['action'], case['world'], case['tile']
    if 0x59 <= a <= 0x5f and mistake != 'no-action-gate':
        return -1
    if case['manager'] and mistake != 'no-manager':
        return -1
    if w == 2 and t != 3 and (t < 10 if mistake != 'snow-le' else t <= 10):
        return 10
    if w == 0 and t == 0:
        return 9
    if w == 3 and t == 0 and mistake != 'noria-soil':
        return 9
    water = w in (7, 0x80, 0x81, 0x82) or 0x18 <= w <= 0x1d or w == 0x24
    if water and (not case['safe'] or mistake == 'swim-safe'):
        return 11
    if 0x39 <= w <= 0x3a or w == 0x79 or w == 0x3e:
        return 10
    if w == 0x7a:
        index = ((case['y'] & 0xff) << 8) + (case['x'] & 0xff)
        if mistake == 'bridge-xy':
            index = ((case['x'] & 0xff) << 8) + (case['y'] & 0xff)
        value = struct.unpack_from('<H', case['attributes'], 2*index)[0]
        return 0x4d1 if value & 0x8000 else 8
    return 8


def model_trigger(case, mistake=None):
    foot = list(case['foot'])
    calls = 0
    if case['type'] != 0xa91 or not case['is_hero']:
        return foot, calls
    a = case['action']
    hi = 0x6f if mistake != 'run-inclusive' else 0x70
    if not ((0x32 <= a <= 0x3e) or (0x4f <= a < hi)):
        return foot, calls
    first, second = (1.0, 4.0) if mistake == 'thresholds' else (1.5, 4.5)
    frame = case['frame']
    ge = (lambda v, k: v > k) if mistake == 'strict' else (lambda v, k: v >= k)
    if mistake == 'nan-passes':
        ge = lambda v, k: not (v < k)  # noqa: E731
    if ge(frame, first) and not foot[0]:
        foot[0] = 1
        calls += 1
    if ge(frame, second) and not foot[1]:
        foot[1] = 1
        calls += 1
    return foot, calls


def model_tile(case, mistake=None):
    def trunc(v):
        if not (-2147483648.0 <= v < 2147483648.0):
            return -2147483648
        return int(v)

    def div(a):
        if mistake == 'floor':
            return math.floor(a/100)
        q = abs(a)//100
        return q if a >= 0 else -q
    x, y = trunc(case['px']), trunc(case['py'])
    if mistake == 'swap':
        x, y = y, x
    index = ((div(y) << 8) + div(x)) & 0xffffffff
    if index >= 0x80000000:
        index -= 1 << 32
    if index < 0:
        index = 0 if mistake != 'wrap' else index & 0xffff
    elif index > 0xffff:
        index = 0xffff if mistake != 'wrap' else index & 0xffff
    return case['layer1'][index]


# --------------------------------------------------------------------------
# Cases.

WORLDS = [0, 1, 2, 3, 7, 0x18, 0x1b, 0x1d, 0x1e, 0x24, 0x39, 0x3a, 0x3e, 0x79, 0x7a, 0x80, 0x82, 0x83, 0x17, 0x25]


def attribute_grid(rng):
    words = [rng.choice((0, 1, 0x8000, 0x8001, 0x4, rng.randrange(0x10000))) for _ in range(0x10000)]
    return struct.pack('<65536H', *words)


def walk_sound_cases(rng, count, grids):
    cases = []
    for index in range(count):
        world = rng.choice(WORLDS) if index % 4 else rng.randrange(-2, 0x100)
        cases.append({
            'world': world,
            'tile': rng.choice((0, 1, 2, 3, 4, 9, 10, 11, 12, -1, rng.randrange(0, 256), rng.randrange(-300, 300))),
            'action': rng.choice((0x32, 0x33, 0x4f, 0x58, 0x59, 0x5c, 0x5f, 0x60, rng.randrange(0x186),
                                  rng.randrange(0x10000))),
            'safe': rng.choice((0, 1, 2, 0xff)),
            'x': rng.choice((rng.randrange(256), rng.randrange(-600, 600), rng.randrange(-2**31, 2**31))),
            'y': rng.choice((rng.randrange(256), rng.randrange(-600, 600), rng.randrange(-2**31, 2**31))),
            'manager': rng.choice((0, 0, 0, 1)),
            'attributes': grids[index % len(grids)]})
        if index % 10 == 0:   # the tile-dependent worlds on their boundary tiles
            cases[-1].update({'world': rng.choice((0, 2, 3, 0x7a)), 'tile': rng.choice((0, 3, 9, 10, 11)),
                              'manager': 0, 'action': 0x32})
    return cases


def frame_value(rng):
    return f32(rng.choice((0.0, 1.0, 1.49, 1.5, 1.51, 4.49, 4.5, 4.51, 7.9, -1.0, float('nan'), float('inf'),
                           rng.uniform(-2, 12))))


def trigger_cases(rng, count, grids):
    cases = []
    for case in walk_sound_cases(rng, count, grids):
        case.update({
            'is_hero': rng.choice((1, 1, 1, 0)),
            'type': rng.choice((0xa91, 0xa91, 0xa91, 0x7a5, 0xa90, 0xa92)),
            'action': rng.choice((0x31, 0x32, 0x33, 0x3e, 0x3f, 0x4e, 0x4f, 0x59, 0x6e, 0x6f, 0x70, 0x1,
                                  rng.randrange(0x186))),
            'frame': frame_value(rng),
            'foot': [rng.randrange(2) if rng.random() < 0.8 else rng.randrange(256) for _ in range(2)]})
        cases.append(case)
    return cases


def reset_cases(rng, count):
    return [{'al': rng.choice((0, 1, 2, 0xff)), 'foot': [rng.randrange(256), rng.randrange(256)],
             'field': rng.randrange(-2**31, 2**31)} for _ in range(count)]


def tile_cases(rng, count):
    layers = [bytes(rng.randrange(256) for _ in range(0x10000)) for _ in range(3)]
    cases = []
    for index in range(count):
        def coordinate():
            return f32(rng.choice((rng.uniform(0, 25600), rng.uniform(-500, 26000), rng.uniform(-300, 0), rng.randrange(0, 256)*100.0,
                                   rng.randrange(0, 256)*100.0 - 0.001, rng.uniform(-1e10, 1e10), -0.5, 99.99,
                                   float('nan'), float('inf'), -float('inf'), 3e9, -3e9)))
        cases.append({'px': coordinate(), 'py': coordinate(), 'layer1': layers[index % 3]})
    return cases


# --------------------------------------------------------------------------

def compare(machine, lib, args):
    rng = random.Random(args.seed)
    grids = [attribute_grid(rng) for _ in range(3)]
    grid_buffers = [ctypes.create_string_buffer(g, len(g)) for g in grids]
    report = {}

    sound_mistakes = ['no-action-gate', 'no-manager', 'snow-le', 'noria-soil', 'swim-safe', 'bridge-xy']
    cases = walk_sound_cases(rng, args.cases, grids)
    mismatches, failures, ids, detected = [], [], {}, {m: 0 for m in sound_mistakes}
    for case in cases:
        client = client_walk_sound(machine, case)
        if not client['ok']:
            failures.append({'case': summary(case), 'stopped': client['stopped'], 'error': client['error']})
            continue
        sound = authored_walk_sound(lib, case, grid_buffers[grids.index(case['attributes'])])
        if client['calls'] != expected_calls(case, sound) or model_sound(case) != sound:
            mismatches.append({'case': summary(case), 'client': client['calls'], 'authored': sound})
        ids[sound] = ids.get(sound, 0)+1
        for mistake in sound_mistakes:
            if expected_calls(case, model_sound(case, mistake)) != client['calls']:
                detected[mistake] += 1
    report['play_walk_sound'] = {'cases': len(cases), 'failures': failures[:20], 'failure_count': len(failures),
                                 'mismatches': mismatches[:20], 'mismatch_count': len(mismatches),
                                 'ids': {str(k): v for k, v in sorted(ids.items())},
                                 'negative_controls_detected': detected}

    trigger_mistakes = ['thresholds', 'strict', 'nan-passes', 'run-inclusive']
    cases = trigger_cases(rng, args.cases, grids)
    mismatches, failures, detected, played = [], [], {m: 0 for m in trigger_mistakes}, 0
    for case in cases:
        client = client_trigger(machine, case)
        if not client['ok']:
            failures.append({'case': summary(case), 'stopped': client['stopped'], 'error': client['error']})
            continue
        foot = (ctypes.c_uint8*2)(*case['foot'])
        calls = lib.mu_footstep_trigger(case['type'], case['is_hero'], case['action'], case['frame'], foot)
        sound = authored_walk_sound(lib, case, grid_buffers[grids.index(case['attributes'])])
        expected = []
        for _ in range(calls):
            expected += expected_calls(case, sound)
        if client['foot'] != list(foot) or client['calls'] != expected or model_trigger(case) != (list(foot), calls):
            mismatches.append({'case': summary(case), 'client': client, 'authored': [list(foot), calls, sound]})
        played += calls
        for mistake in trigger_mistakes:
            wrong_foot, wrong_calls = model_trigger(case, mistake)
            wrong = []
            for _ in range(wrong_calls):
                wrong += expected_calls(case, sound)
            if wrong_foot != client['foot'] or wrong != client['calls']:
                detected[mistake] += 1
    report['footstep_trigger'] = {'cases': len(cases), 'failures': failures[:20], 'failure_count': len(failures),
                                  'mismatches': mismatches[:20], 'mismatch_count': len(mismatches),
                                  'play_walk_sound_calls': played, 'negative_controls_detected': detected}

    cases = reset_cases(rng, max(200, args.cases//8))
    mismatches, failures, detected = [], [], {'reset-on-nonzero': 0}
    for case in cases:
        client = client_reset(machine, case)
        if not client['ok']:
            failures.append({'case': case, 'stopped': client['stopped'], 'error': client['error']})
            continue
        foot = (ctypes.c_uint8*2)(*case['foot'])
        field = ctypes.c_int32(case['field'])
        reset = lib.mu_footstep_reset(case['al'], foot, ctypes.byref(field))
        if client['foot'] != list(foot) or client['field'] != field.value or client['reset'] != bool(reset) or \
                client['calls'] != [('step', OTHER, OTHER+OBJECT)]:
            mismatches.append({'case': case, 'client': client, 'authored': [list(foot), field.value]})
        wrong = case['al'] != 0   # planted: reset when the step returned non-zero
        if (client['field'] == -1 and client['foot'] == [0, 0]) != wrong:
            detected['reset-on-nonzero'] += 1
    report['foot_reset'] = {'cases': len(cases), 'failures': failures[:20], 'failure_count': len(failures),
                            'mismatches': mismatches[:20], 'mismatch_count': len(mismatches),
                            'negative_controls_detected': detected}

    tile_mistakes = ['floor', 'swap', 'wrap']
    cases = tile_cases(rng, args.cases)
    layer_buffers = {}
    mismatches, failures, detected = [], [], {m: 0 for m in tile_mistakes}
    for case in cases:
        client = client_tile(machine, case)
        if not client['ok']:
            failures.append({'case': [case['px'], case['py']], 'stopped': client['stopped'], 'error': client['error']})
            continue
        key = id(case['layer1'])
        if key not in layer_buffers:
            layer_buffers[key] = ctypes.create_string_buffer(case['layer1'], 0x10000)
        tile = lib.mu_hero_tile(layer_buffers[key], case['px'], case['py'])
        if client['tile'] != tile or model_tile(case) != tile:
            mismatches.append({'case': [case['px'], case['py']], 'client': client['tile'], 'authored': tile})
        for mistake in tile_mistakes:
            if model_tile(case, mistake) != client['tile']:
                detected[mistake] += 1
    report['hero_tile'] = {'cases': len(cases), 'failures': failures[:20], 'failure_count': len(failures),
                           'mismatches': mismatches[:20], 'mismatch_count': len(mismatches),
                           'negative_controls_detected': detected}
    return report


def summary(case):
    return {k: (v if k != 'attributes' else hashlib.sha256(v).hexdigest()[:12]) for k, v in case.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--library', default=str(ROOT/f'reconstructed/audio/libclient_audio.{SUFFIX}'))
    parser.add_argument('--cases', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=20261017)
    parser.add_argument('--output')
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second image section')
    bodies = {}
    for name, (start, end, digest) in BODIES.items():
        observed = hashlib.sha256(text[start-am.TEXT_BASE:end-am.TEXT_BASE]).hexdigest()
        if observed != digest:
            raise SystemExit(f'{name}: captured body differs from the pinned digest')
        bodies[name] = {'start': hex(start), 'end_exclusive': hex(end), 'sha256': observed}
    machine = am.ActorMachine(text, data)
    lib = load_library(Path(args.library))
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'bodies': bodies,
              'library_sha256': hashlib.sha256(Path(args.library).read_bytes()).hexdigest(), 'seed': args.seed}
    report.update(compare(machine, lib, args))
    sections = ('play_walk_sound', 'footstep_trigger', 'foot_reset', 'hero_tile')
    ok = all(report[s]['mismatch_count'] == 0 and report[s]['failure_count'] == 0 for s in sections) and \
        all(all(v > 0 for v in report[s]['negative_controls_detected'].values()) for s in sections)
    report['ok'] = ok
    text_out = json.dumps(report, indent=1, default=str)
    if args.output:
        Path(args.output).write_text(text_out)
    for s in sections:
        r = report[s]
        print(f"{s}: {r['cases']-r['failure_count']-r['mismatch_count']}/{r['cases']} equal, "
              f"{r['failure_count']} stopped, negative controls {r['negative_controls_detected']}")
    print('ALL PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
