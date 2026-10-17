#!/usr/bin/env python3
"""Compare the authored actor routines with the client (NATIVE-ACTOR-001).

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/actor_machine.py):

* OpenMonsterModel 0x0180b0f4 from its entry, for every monster type
  0 .. 0x258 under several fixtures (action counts, worlds, already-loaded and
  mesh-less models). The model container getter 0x00966cc4, the model lookup
  0x00eaa8cf, AccessModel 0x018202b4, OpenTexture 0x0181fbe9, the std::string
  constructor/destructor 0x0094997e/0x008e83a0 and the sound/bitmap loaders
  0x00a6ab76, 0x0185baac, 0x018329fa are stubs that record their arguments;
  everything else (SetActionSpeed, SetActionLoop, GetAction, ActionAt, the
  world predicates, _chkstk) runs as client code. The authored mu_monster_open
  (reconstructed/actors, libactors) runs on copies of the same regions. Every
  model and action-array byte, the AccessModel call for the opened model and
  its OpenTexture call must agree.
* the character animation speed 0x013960d2 (see run_character_speed).

Modelled explicitly (not client code): the stubs above, the model records
(only +0x24, +0x26, +0x30 are defined before AccessModel; the stub fills them),
the action arrays (defined, capacity 32 records), and the world global
0x01cf15fc as a read-only declared value.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
OPEN_MONSTER = 0x0180b0f4
MANAGER, MODEL_AT, ACCESS_MODEL, OPEN_TEXTURE = 0x00966cc4, 0x00eaa8cf, 0x018202b4, 0x0181fbe9
STRING_CTOR, STRING_DTOR = 0x0094997e, 0x008e83a0
LOAD_WAVE, LOAD_BITMAP, ACTION_SOUNDS = 0x00a6ab76, 0x0185baac, 0x018329fa
WORLD = 0x01cf15fc
MANAGER_ADDRESS = 0x20000000
MODEL_BASE, MODEL_SLOT = 0x21000000, 0x1000
ACTION_CAPACITY = 32
MONSTER_TYPES = 0x259
BODIES = {  # start, exclusive end
    'open_monster': (0x0180b0f4, 0x0181f25c),
    'set_action_speed': (0x012bd437, 0x012bd471),
    'set_action_loop': (0x012bd471, 0x012bd4a4),
    'get_action': (0x012bcf9d, 0x012bcfca),
    'action_at': (0x00eaaa44, 0x00eaaa73),
    'npc_texture_world': (0x009dacb8, 0x009dacdb),
    'character_speed': (0x013960d2, 0x013966a8),
}


# --------------------------------------------------------------------------
# Monster opener fixtures.

def action_records(slot, salt):
    data = bytearray()
    generator = random.Random(salt)
    for action in range(ACTION_CAPACITY):
        speed = am.f32(generator.uniform(-1.0, 3.0))
        data += struct.pack('<BBBBfhBBI', generator.randrange(256), 0xee, 0xee, 0xee, speed,
                            generator.randrange(1, 40), generator.randrange(2), 0xee, 0x41414141+slot)
    return bytes(data)


def monster_case(label, type_, *, actions=12, meshes=1, world=0, preloaded=None, other_actions=12, salt=0):
    """Regions and the fixture for one opener call. Slot 0 is the opened model."""
    regions = []
    for slot in range(5):
        base = MODEL_BASE+slot*MODEL_SLOT
        model = am.undefined_region(f'model{slot}', base, 0xd0)
        if slot == 0:
            counts = preloaded if preloaded is not None else (0, 0)
            model.define(base+0x24, struct.pack('<hh', *counts))
        else:
            model.define(base+0x24, struct.pack('<hhI', 1, other_actions, 0))
            model.define(base+0x30, struct.pack('<I', base+0x100))
        regions.append(model)
        regions.append(am.defined_region(f'actions{slot}', base+0x100, action_records(slot, salt*31+slot)))
    regions.append(am.defined_region('world', WORLD, struct.pack('<i', world), writable=False))
    return {'label': label, 'type': type_, 'actions': actions, 'meshes': meshes, 'world': world,
            'regions': regions}


def copy_regions(regions):
    return [am.Region(r.name, r.base, r.data, r.defined, r.writable) for r in regions]


class Fixture:
    """Shared model-container behaviour for the client stubs and the C services."""

    def __init__(self, case):
        self.case = case
        self.own = case['type']+0x7a5
        self.models = {self.own: MODEL_BASE}
        self.free = [MODEL_BASE+slot*MODEL_SLOT for slot in range(1, 5)]
        self.calls = []

    def model_at(self, index):
        if index not in self.models:
            if not self.free:
                return None
            self.models[index] = self.free.pop(0)
        return self.models[index]

    def access(self, index, directory, name, number, write):
        self.calls.append(('access', index, directory, name, number))
        if index == self.own:
            write(MODEL_BASE+0x24, struct.pack('<hh', self.case['meshes'], self.case['actions']))
            write(MODEL_BASE+0x30, struct.pack('<I', MODEL_BASE+0x100))

    def texture(self, index, directory, wrap, filt):
        self.calls.append(('texture', index, directory, wrap, filt))


def run_client_open(machine, case):
    fixture = Fixture(case)
    loaders = []

    def model_at(m):
        address = fixture.model_at(m.argument(0))
        if address is None:
            m.stop(('model-pool-empty', hex(m.argument(0))))
            return 0, 4
        return address, 4

    def access(m):
        fixture.access(m.argument(0), m.cstring(m.argument(1)), m.cstring(m.argument(2)),
                       struct.unpack('<i', struct.pack('<I', m.argument(3)))[0], m.write)
        return 0

    def texture(m):
        fixture.texture(m.argument(0), m.cstring(m.argument(1)), m.argument(2), m.argument(3))
        return 0

    def string_ctor(m):
        this = m.uc.reg_read(m.x86.UC_X86_REG_ECX)
        m.uc.mem_write(this, struct.pack('<I', m.argument(0)))
        return this, 4

    def wave(m):
        loaders.append(('wave', m.argument(0), m.cstring(m.read32(m.argument(1))), m.argument(2), m.argument(3)))
        return 0

    def bitmap(m):
        loaders.append(('bitmap', m.cstring(m.argument(0)), m.argument(1)))
        return 0

    def action_sounds(m):
        loaders.append(('action_sounds',)+tuple(m.argument(i) for i in range(11)))
        return 0

    stubs = {MANAGER: lambda m: MANAGER_ADDRESS, MODEL_AT: model_at, ACCESS_MODEL: access, OPEN_TEXTURE: texture,
             STRING_CTOR: string_ctor, STRING_DTOR: lambda m: (0, 0), LOAD_WAVE: wave, LOAD_BITMAP: bitmap,
             ACTION_SOUNDS: action_sounds}
    result = machine.execute(OPEN_MONSTER, [case['type']], copy_regions(case['regions']), stubs)
    result['calls'] = fixture.calls
    result['loaders'] = loaders
    return result


class Authored:
    class Image(ctypes.Structure):
        _fields_ = [('bytes', ctypes.c_void_p), ('base', ctypes.c_uint32), ('size', ctypes.c_uint32)]

    class Memory(ctypes.Structure):
        pass

    MODEL_AT = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32)
    ACCESS = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int32)
    TEXTURE = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32,
                               ctypes.c_uint32)

    class Services(ctypes.Structure):
        pass

    def __init__(self, library):
        self.Memory._fields_ = [('regions', ctypes.POINTER(self.Image)), ('count', ctypes.c_uint32)]
        self.Services._fields_ = [('context', ctypes.c_void_p), ('model_at', self.MODEL_AT),
                                  ('access_model', self.ACCESS), ('open_texture', self.TEXTURE)]
        handle = self.handle = ctypes.CDLL(str(library))
        self.open = handle.mu_monster_open
        self.open.argtypes = [ctypes.POINTER(self.Memory), ctypes.c_int32, ctypes.c_int32,
                              ctypes.POINTER(self.Services)]
        self.open.restype = ctypes.c_int
        self.model_file = handle.mu_monster_model_file
        self.model_file.argtypes = [ctypes.c_int32, ctypes.c_char_p, ctypes.c_uint32]
        self.model_file.restype = ctypes.c_int

    def memory(self, regions):
        buffers = [(r, (ctypes.c_uint8*len(r.data)).from_buffer_copy(bytes(r.data))) for r in regions]
        images = (self.Image*len(buffers))(*[self.Image(ctypes.addressof(b), r.base, len(r.data))
                                              for r, b in buffers])
        return buffers, self.Memory(images, len(buffers)), images

    def run_open(self, case):
        regions = [r for r in case['regions'] if r.writable]
        buffers, memory, images = self.memory(case['regions'])
        fixture = Fixture(case)

        def write(address, payload):
            for region, buffer in buffers:
                if region.base <= address and address+len(payload) <= region.base+len(region.data):
                    ctypes.memmove(ctypes.addressof(buffer)+address-region.base, payload, len(payload))
                    return
            raise ValueError(hex(address))

        model_at = self.MODEL_AT(lambda context, index: fixture.model_at(index) or 0)
        access = self.ACCESS(lambda context, index, d, n, number:
                             fixture.access(index, d.decode('latin1'), n.decode('latin1'), number, write))
        texture = self.TEXTURE(lambda context, index, d, wrap, filt:
                               fixture.texture(index, d.decode('latin1'), wrap, filt))
        services = self.Services(None, model_at, access, texture)
        status = self.open(ctypes.byref(memory), case['type'], case['world'], ctypes.byref(services))
        del regions
        return {'status': status, 'calls': fixture.calls,
                'regions': {r.name: bytes(b) for r, b in buffers if r.writable}}

    def file_for(self, type_):
        buffer = ctypes.create_string_buffer(64)
        return buffer.value.decode() if self.model_file(type_, buffer, 64) else None


# --------------------------------------------------------------------------
# Independent Python model of the opener (from the static lifter's operations,
# not from the C table), with negative-control variants.

def python_open(case, lifted, variant='faithful'):
    regions = {r.name: bytearray(r.data) for r in case['regions'] if r.writable}
    bases = {r.name: r.base for r in case['regions'] if r.writable}
    fixture = Fixture(case)

    def locate(address, size):
        for name, data in regions.items():
            if bases[name] <= address and address+size <= bases[name]+len(data):
                return data, address-bases[name]
        raise IndexError(hex(address))

    def get(address, fmt):
        data, offset = locate(address, struct.calcsize(fmt))
        return struct.unpack_from(fmt, data, offset)[0]

    def put(address, fmt, value):
        data, offset = locate(address, struct.calcsize(fmt))
        struct.pack_into(fmt, data, offset, value)

    def write(address, payload):
        data, offset = locate(address, len(payload))
        data[offset:offset+len(payload)] = payload

    def checked(model, action, field, fmt, value):
        if variant == 'unchecked-defaults' or 0 <= action < get(model+0x26, '<h'):
            put(get(model+0x30, '<I')+16*action+field, fmt, value)

    type_ = case['type']
    own = fixture.own
    model = fixture.model_at(own)
    if get(model+0x26, '<h') > 0 or get(model+0x24, '<h') > 0:
        return {'status': 0, 'regions': {k: bytes(v) for k, v in regions.items()}, 'calls': fixture.calls}
    fixture.access(own, 'Data\\Monster\\', 'Monster', type_+1, write)
    if get(model+0x24, '<h') == 0:
        return {'status': 0, 'regions': {k: bytes(v) for k, v in regions.items()}, 'calls': fixture.calls}
    world = case['world']
    if (0x12 <= world <= 0x17 or world in (0x35, 0x61)) and 0x46 <= type_ <= 0x48:
        directory = 'Npc\\'
    elif world == 30 and type_ == 0x4a:
        directory = 'Object31\\'
    else:
        directory = 'Monster\\'
    fixture.texture(own, directory, 0x2901, 0x2600)
    for action, speed in enumerate((0.25, 0.2, 0.34, 0.33, 0.33, 0.5, 0.55)):
        checked(model, action, 4, '<f', am.f32(speed))
    checked(model, 6, 0, '<B', 1)
    scale = {3: 1.2, 5: 0.7, 25: 0.7, 37: 0.4, 42: 0.4, 0x1ab: 0.4}.get(type_)
    if scale is not None and variant != 'no-scale':
        for action in range(6):
            address = get(model+0x30, '<I')+16*action+4
            put(address, '<f', am.f32(get(address, '<f')*am.f32(scale)))
    for op in lifted[type_]['ops']:
        kind = op[0]
        if kind in ('speed', 'loop'):
            target = fixture.model_at(op[1])
            checked(target, op[2], 4 if kind == 'speed' else 0, '<I' if kind == 'speed' else '<B', op[3])
        elif kind == 'action_speed':
            target = fixture.model_at(op[1])
            if not target or not 0 <= op[2] < get(target+0x26, '<h'):
                return {'status': 3, 'regions': {k: bytes(v) for k, v in regions.items()}, 'calls': fixture.calls}
            put(get(target+0x30, '<I')+16*op[2]+4, '<I', op[3])
        elif kind == 'raw':
            _, index, action, field, size, value = op
            target = fixture.model_at(index)
            if variant == 'checked-direct' and not 0 <= action < get(target+0x26, '<h'):
                continue
            put(get(target+0x30, '<I')+16*action+field, '<I' if size == 'u32' else '<B', value)
        else:
            _, index, offset, size, value = op
            put(fixture.model_at(index)+offset, '<I' if size == 'u32' else '<B', value)
    return {'status': 0, 'regions': {k: bytes(v) for k, v in regions.items()}, 'calls': fixture.calls}


def own_calls(calls, own):
    return [c for c in calls if c[1] == own]


def compare_open(machine, authored, case, lifted):
    client = run_client_open(machine, case)
    mine = authored.run_open(case)
    own = case['type']+0x7a5
    differences = []
    # Both sides fault: the client writes through a null action pointer (address 4) exactly where
    # the authored routine reports MU_ACTOR_CLIENT_FAULT; the regions up to that store must agree.
    fault = (not client['ok'] and client['stopped'] and client['stopped'][:3] == ('unmapped', '0x4', 4)
             and mine['status'] == 3)
    if not client['ok'] and not fault:
        differences.append(('client', client['checks'], client['stopped'], client['error']))
    if mine['status'] != 0 and not fault:
        differences.append(('authored-status', mine['status']))
    for name, payload in mine['regions'].items():
        if client['regions'].get(name) != payload:
            a, b = client['regions'].get(name, b''), payload
            first = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), None)
            differences.append(('region', name, first))
    if own_calls(client['calls'], own) != own_calls(mine['calls'], own):
        differences.append(('calls', own_calls(client['calls'], own), own_calls(mine['calls'], own)))
    extra_models = [c for c in client['calls'] if c[0] == 'access' and c[1] != own]
    python = {}
    for variant in ('faithful', 'unchecked-defaults', 'no-scale', 'checked-direct'):
        model = python_open(case, lifted, variant)
        same = model['status'] == mine['status'] and model['regions'] == mine['regions'] and \
            own_calls(model['calls'], own) == own_calls(mine['calls'], own)
        python[variant] = same
    if not python['faithful']:
        differences.append(('python-model',))
    return {'python': python,'label': case['label'], 'type': case['type'], 'match': not differences, 'differences': differences,
            'fault': fault,
            'extra_access': extra_models, 'loaders': len(client['loaders'])}


def monster_cases():
    cases = []
    for type_ in range(MONSTER_TYPES):
        cases.append(monster_case(f'type{type_}-a12', type_, actions=12, salt=type_))
        cases.append(monster_case(f'type{type_}-a3', type_, actions=3, salt=type_+1000))
    for type_ in (0x45, 0x46, 0x47, 0x48, 0x49, 0x4a, 0x4b):
        for world in (0x11, 0x12, 0x17, 0x18, 0x1e, 0x35, 0x61, -1):
            cases.append(monster_case(f'type{type_}-world{world}', type_, world=world, salt=type_*7+world))
    for type_ in (0, 3, 37):
        cases.append(monster_case(f'type{type_}-no-meshes', type_, meshes=0))
        cases.append(monster_case(f'type{type_}-negative-meshes', type_, meshes=-1))
        cases.append(monster_case(f'type{type_}-loaded-actions', type_, preloaded=(0, 2)))
        cases.append(monster_case(f'type{type_}-loaded-meshes', type_, preloaded=(1, 0)))
        cases.append(monster_case(f'type{type_}-a0', type_, actions=0))
        cases.append(monster_case(f'type{type_}-a32', type_, actions=32))
    return cases


# --------------------------------------------------------------------------
# Character animation step 0x013960d2.

CHAR_STEP, TICK = 0x013960d2, 0x012b4dd3
HAS_BUFF, STOP = 0x01295ade, 0x0138fe69
WEAPON_CHAIN = (0x0129deaa, 0x0095c595, 0x0095f16e, 0x00c7974e, 0x0095ebbb)
SCENE_STATE, TERRAIN_ATTRIBUTES = 0x01d1df70, 0x0b795420
CHARACTER, OBJECT, MODEL = 0x22000000, 0x22100000, 0x22200000
ACTIONS, BONE, TRACKS, POSITIONS = 0x22300000, 0x22400000, 0x22500000, 0x22600000
STEP_TYPES = [0xa91, 0x7e5, 0x940, 0xa52, 0x7fc, 0x134, 0x145, 0x7a5, 0x801, 0x9fe] + list(range(0x135, 0x145))
STEP_ACTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 0x92, 0x9c, 0x9f, 0xa7, 0x11d, 0x125, 0xd9, 0x170, 0x184]
STEP_FRAMES = [0.0, 0.5, 1.0, 1.0000001, 2.0, 2.9999998, 3.0, 5.5, 5.5000005, 6.0, 6.0000005, 7.25, 9.75]
STEP_BUFFS = (0x3d, 0x48, 0xb2, 0x118)
STEP_BRANCHES = {
    0x0139614d: 'clamp-negative', 0x01396178: 'flag-attack-x1.5', 0x013961ba: 'action-9c-11d-div2',
    0x013961f3: 'action-92-div10', 0x013962c5: 'weapon-div8', 0x013962d9: 'weapon-div2', 0x013962f9: 'action-9f-div2',
    0x0139636c: 'model-a52-x0.5', 0x013963a3: 'model-7e5-940-die-x4', 0x013963ba: 'model-135-13e-x2',
    0x013963d1: 'model-13f-x1.5', 0x013963e8: 'model-140-x2', 0x013963ff: 'model-141-x2', 0x01396413: 'model-142-x1.5',
    0x01396432: 'model-143-action0-x2', 0x01396446: 'model-143-x2', 0x01396465: 'model-144-action0-x1',
    0x01396479: 'model-144-x1.5', 0x013964a3: 'model-7fc-die-div2', 0x01396517: 'buff-no-tick',
    0x01396581: 'stop-184', 0x013965ae: 'stop-d9-125', 0x01396690: 'stop-170-attribute', 0x013965c9: 'action-170'}
ACTION_RECORDS = 8
_ATTRIBUTES = random.Random(0xb795420)
ATTRIBUTE_MAP = bytes(_ATTRIBUTES.choice([0, 4, 5, 1, 0x40]) for _ in range(0x20000))


def step_case(label, generator, *, type_=None, action=None):
    type_ = generator.choice(STEP_TYPES) if type_ is None else type_
    action = generator.choice(STEP_ACTIONS + [generator.randrange(0x200)]) if action is None else action
    count = generator.choice([0, 1, 3, ACTION_RECORDS, ACTION_RECORDS])
    current = generator.randrange(max(count, 1)+1) if generator.random() < 0.2 else generator.randrange(ACTION_RECORDS)
    speed = generator.choice([0.25, 0.34, -0.3, 0.0, float('nan'), 1.7, generator.uniform(-1, 2)])
    keys = generator.choice([0, 1, 2, 5, 9, 12])
    frame = generator.choice(STEP_FRAMES + [generator.uniform(-2, keys+2)])
    character = am.undefined_region('character', CHARACTER, 0x200)
    character.define(CHARACTER+0xe, bytes([generator.choice([0, 0, 1, 0x80])]))
    character.define(CHARACTER+0x12, bytes([generator.choice([4, 0x14, 0x24, 3, 0, generator.randrange(256)])]))
    character.define(CHARACTER+0x180, struct.pack('<ii', generator.randrange(10, 240), generator.randrange(10, 240)))
    obj = am.undefined_region('object', OBJECT, 0x400)
    obj.define(OBJECT+0x2a, struct.pack('<H', action))
    obj.define(OBJECT+0x5c, struct.pack('<I', type_))
    obj.define(OBJECT+0xd0, struct.pack('<f', am.f32(frame)))
    model = am.undefined_region('model', MODEL, 0xd0)
    model.define(MODEL+0x26, struct.pack('<h', count))
    model.define(MODEL+0x2c, struct.pack('<II', BONE, ACTIONS))
    model.define(MODEL+0xa8, struct.pack('<H', current))
    model.define(MODEL+0xb4, struct.pack('<h', generator.randrange(16)))  # integer frame of an earlier tick
    records = bytearray()
    for index in range(ACTION_RECORDS+2):
        value = speed if index == current else generator.uniform(-0.5, 1.5)
        records += struct.pack('<BBBBfhBBI', generator.choice([0, 0, 1]), 0, 0, 0, am.f32(value),
                               keys if index == current else generator.randrange(0, 12),
                               generator.choice([0, 0, 1]), 0, 0)
    actions = am.defined_region('actions', ACTIONS, records)
    bone = am.undefined_region('bone', BONE, 0x8c)
    bone.define(BONE+0x24, struct.pack('<I', TRACKS))
    tracks = am.defined_region('tracks', TRACKS, b''.join(struct.pack('<III', POSITIONS, 0, 0)
                                                          for _ in range(0x200)))
    positions = am.defined_region('positions', POSITIONS, b''.join(
        struct.pack('<fff', am.f32(generator.uniform(-450, 450)), am.f32(generator.uniform(-450, 450)), 0.0)
        for _ in range(16)))
    attributes = am.Region('attributes', TERRAIN_ATTRIBUTES, ATTRIBUTE_MAP, None, writable=False)
    globals_ = [am.defined_region('world', WORLD, struct.pack('<i', generator.choice([0, 39, 2])), writable=False),
                am.defined_region('scene', SCENE_STATE, struct.pack('<i', generator.choice([2, 5, 4])),
                                  writable=False)]
    buffs = {b for b in STEP_BUFFS if generator.random() < 0.08}
    return {'label': label, 'regions': [character, obj, model, actions, bone, tracks, positions, attributes]+globals_,
            'type': type_, 'model_present': generator.random() > 0.03, 'buffs': buffs,
            'weapon': generator.choice([0, 1, 2]), 'world': struct.unpack('<i', globals_[0].data)[0],
            'scene': struct.unpack('<i', globals_[1].data)[0]}


def run_client_step(machine, case):
    calls, speeds = [], []

    def model_at(m):
        index = m.argument(0)
        return (MODEL if case['model_present'] and index == case['type'] else 0), 4

    def has_buff(m):
        calls.append(('buff', m.argument(0)))
        return int(m.argument(0) in case['buffs']), 4

    def stop(m):
        calls.append(('stop', m.argument(0)))
        return 0

    def weapon(m):
        calls.append(('weapon',))
        return case['weapon']

    def tick_entry(uc, address, size, ignored):
        speeds.append(m_read(uc, uc.reg_read(machine.x86.UC_X86_REG_ESP)+16))

    def m_read(uc, address):
        return struct.unpack('<I', uc.mem_read(address, 4))[0]

    stubs = {MANAGER: lambda m: MANAGER_ADDRESS, MODEL_AT: model_at, HAS_BUFF: has_buff, STOP: stop,
             WEAPON_CHAIN[0]: lambda m: 0x22700000, WEAPON_CHAIN[1]: lambda m: (m.argument(0), 8),
             WEAPON_CHAIN[2]: lambda m: 0x22700100, WEAPON_CHAIN[3]: weapon, WEAPON_CHAIN[4]: lambda m: 0}
    branches = []

    def branch(uc, address, size, ignored):
        branches.append(STEP_BRANCHES[address])

    hooks = [machine.uc.hook_add(machine.UC_HOOK_CODE, tick_entry, begin=TICK, end=TICK)]
    hooks += [machine.uc.hook_add(machine.UC_HOOK_CODE, branch, begin=a, end=a) for a in STEP_BRANCHES]
    try:
        result = machine.execute(CHAR_STEP, [CHARACTER, OBJECT], copy_regions(case['regions']), stubs)
    finally:
        for hook in hooks:
            machine.uc.hook_del(hook)
    result['branches'] = branches
    result['calls'] = calls
    result['speed'] = speeds[0] if speeds else None
    return result


class StepServices(ctypes.Structure):
    MODEL_AT = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32)
    HAS_BUFF = ctypes.CFUNCTYPE(ctypes.c_uint8, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32)
    WEAPON = ctypes.CFUNCTYPE(ctypes.c_uint8, ctypes.c_void_p, ctypes.c_uint32)
    STOP = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint32)
    _fields_ = [('context', ctypes.c_void_p), ('model_at', MODEL_AT), ('has_buff', HAS_BUFF),
                ('weapon_check', WEAPON), ('stop', STOP)]


class TickGlobals(ctypes.Structure):
    _fields_ = [('scene_state', ctypes.c_uint32), ('world', ctypes.c_uint32)]


def run_authored_step(authored, case):
    function = authored.handle.mu_character_animation_step
    function.argtypes = [ctypes.POINTER(authored.Memory), ctypes.c_uint32, ctypes.c_uint32,
                         ctypes.POINTER(StepServices), ctypes.POINTER(TickGlobals),
                         ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_float)]
    function.restype = ctypes.c_int
    buffers, memory, images = authored.memory(case['regions'])
    calls = []

    def has_buff(context, buffs, buff):
        calls.append(('buff', buff))
        return int(buff in case['buffs'])

    def weapon(context, character):
        calls.append(('weapon',))
        return case['weapon'] & 0xff

    def stop(context, character):
        calls.append(('stop', character))

    services = StepServices(None, StepServices.MODEL_AT(
        lambda c, index: MODEL if case['model_present'] and index == case['type'] else 0),
        StepServices.HAS_BUFF(has_buff), StepServices.WEAPON(weapon), StepServices.STOP(stop))
    tick_globals = TickGlobals(SCENE_STATE, WORLD)
    result, speed = ctypes.c_uint8(0xee), ctypes.c_float(0)
    status = function(ctypes.byref(memory), CHARACTER, OBJECT, ctypes.byref(services), ctypes.byref(tick_globals),
                      ctypes.byref(result), ctypes.byref(speed))
    del images
    return {'status': status, 'al': result.value, 'speed': struct.unpack('<I', struct.pack('<f', speed.value))[0],
            'calls': calls, 'regions': {r.name: bytes(b) for r, b in buffers if r.writable}}


def compare_step(machine, authored, case):
    client = run_client_step(machine, case)
    mine = run_authored_step(authored, case)
    differences = []
    if not client['ok']:
        differences.append(('client', client['checks'], client['stopped'], client['error']))
    if mine['status'] != 0:
        differences.append(('authored-status', mine['status']))
    if (client['eax'] & 0xff) != mine['al']:
        differences.append(('al', client['eax'] & 0xff, mine['al']))
    ticked = client['speed'] is not None
    if ticked and client['speed'] != mine['speed']:
        differences.append(('speed', hex(client['speed']), hex(mine['speed'])))
    if client['calls'] != mine['calls']:
        differences.append(('calls', client['calls'], mine['calls']))
    for name, payload in mine['regions'].items():
        if client['regions'].get(name) != payload:
            differences.append(('region', name))
    return {'label': case['label'], 'match': not differences, 'differences': differences, 'ticked': ticked,
            'branches': client['branches'],
            'stopped_calls': sum(1 for c in client['calls'] if c[0] == 'stop'),
            'weapon_checks': sum(1 for c in client['calls'] if c[0] == 'weapon')}


def step_cases(count=4000):
    generator = random.Random(0x13960d2)
    cases = [step_case(f'step-{i}', generator) for i in range(count)]
    for type_ in STEP_TYPES:
        for action in STEP_ACTIONS:
            cases.append(step_case(f'step-grid-{type_:#x}-{action:#x}', generator, type_=type_, action=action))
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--library', default=str(ROOT/f'reconstructed/actors/libactors.{SUFFIX}'))
    parser.add_argument('--output')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second image section')
    machine = am.ActorMachine(text, data)
    authored = Authored(Path(args.library))
    bodies = {name: {'start': hex(s), 'end_exclusive': hex(e),
                     'sha256': hashlib.sha256(text[s-am.TEXT_BASE:e-am.TEXT_BASE]).hexdigest()}
              for name, (s, e) in BODIES.items()}
    import actor_static
    lifted = actor_static.lift_all(actor_static.Image(text, data))
    results = []
    for case in monster_cases()[:args.limit]:
        results.append(compare_open(machine, authored, case, lifted))
    step_results = [compare_step(machine, authored, case) for case in step_cases()[:args.limit]]
    step_mismatches = [r for r in step_results if not r['match']]
    mismatches = [r for r in results if not r['match']]
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'bodies': bodies,
              'library_sha256': hashlib.sha256(Path(args.library).read_bytes()).hexdigest(),
              'monster_open': {'cases': len(results), 'matches': len(results)-len(mismatches),
                               'client_faults_matched': sum(1 for r in results if r['fault'] and r['match']),
                               'mismatches': mismatches[:40],
                               'types_with_extra_models': sorted({r['type'] for r in results if r['extra_access']}),
                               'extra_models': {str(r['type']): r['extra_access'] for r in results
                                                if r['extra_access'] and r['label'].endswith('-a12')},
                               'loader_calls': sum(r['loaders'] for r in results),
                               'negative_controls': {v: sum(1 for r in results if not r['python'][v])
                                                     for v in ('unchecked-defaults', 'no-scale', 'checked-direct')}},
              'character_step': {'cases': len(step_results), 'matches': len(step_results)-len(step_mismatches),
                                 'ticked': sum(r['ticked'] for r in step_results),
                                 'stop_calls': sum(r['stopped_calls'] for r in step_results),
                                 'weapon_checks': sum(r['weapon_checks'] for r in step_results),
                                 'branches': {name: sum(r['branches'].count(name) for r in step_results)
                                              for name in STEP_BRANCHES.values()},
                                 'mismatches': step_mismatches[:40]}}
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: v for k, v in report['monster_open'].items() if k in ('cases', 'matches', 'client_faults_matched', 'negative_controls')}))
    print(json.dumps({k: v for k, v in report['character_step'].items() if k != 'mismatches'}))
    for m in (mismatches+step_mismatches)[:10]:
        print(m)
    return 0 if not mismatches and not step_mismatches else 1


if __name__ == '__main__':
    sys.exit(main())
