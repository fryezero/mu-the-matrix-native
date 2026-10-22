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
BODIES = {  # start, exclusive end, SHA-256 of the captured bytes
    'open_monster': (0x0180b0f4, 0x0181f25c, 'c6c97b78666594a237c87a824299fbadf5dd5ea6a0d5e97b1a3885f3a14bb73e'),
    'set_action_speed': (0x012bd437, 0x012bd471, '0a354359ad501962b05a3b4388e23d3c6de7f0ba987339b2b57c4c6602548f33'),
    'set_action_loop': (0x012bd471, 0x012bd4a4, '2420935b433ced77dc5843e78204e7ac94ace6d0323915a929df32bb8f43ef87'),
    'get_action': (0x012bcf9d, 0x012bcfca, 'ce63dbae68bd8836df752e6890b5dd1f5f38bb4b2934625aca9d4d0bebd6a14b'),
    'action_at': (0x00eaaa44, 0x00eaaa73, '3f2c722111c6524140ff913317763fbddb062bfddd0fc0ca5802d4816c0b3b4b'),
    'npc_texture_world': (0x009dacb8, 0x009dacdb, 'd2129e6fa8fc0b28ee3e75a44d60cdfbe7a75793a3189ea35f3e36675bdbbccb'),
    'character_step': (0x013960d2, 0x013966a8, '98736eafe60c031a1630b8dc9115d4d614a5ec76715e5d7b757484303ae4ad27'),
    'set_action': (0x012affa4, 0x012b001a, '1505c3f4e0493da318652a309ee428994c61a86629902a9ceeba87acfecbda85'),
    'unarmed_stop': (0x0139d6da, 0x0139d89f, '2ad0fa438a137b0928b221e03786c513d95d770dfb2cf3a83dfb9b07ad06438a'),
    'create_monster': (0x0137fbac, 0x0138ce1c, '0c9b634eb2dd3750960c82d8989c29303ffc78df054d90a2b217d0bacb8c0df2'),
    'open_npc': (0x01808a40, 0x0180ae1e, 'df11b6ea3f2934291eb0b8952094ff67d83a97dd459f79d1580b6939732a7706'),
    'player_loader': (0x01830aa6, 0x0183220e, '478d847d4e532fef82ea34e6b4b9c727be1772c049b6743ad52d55db222608fe'),
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
        self.own = case.get('index', case['type']+0x7a5)
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


def run_client_open(machine, case, entry=OPEN_MONSTER, argument=None):
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
    result = machine.execute(entry, [case['type'] if argument is None else argument], copy_regions(case['regions']),
                             stubs)
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
    machine.uc.ctl_flush_tb()
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


# --------------------------------------------------------------------------
# SetAction 0x012affa4 and the unarmed stop action 0x0139d6da.

SET_ACTION, UNARMED_STOP = 0x012affa4, 0x0139d6da


def set_action_cases(count=3000):
    generator = random.Random(0x12affa4)
    cases = []
    for index in range(count):
        obj = am.undefined_region('object', OBJECT, 0x400)
        current = generator.choice([0, 1, 2, 3, 6, 0x9c, 0xffff, generator.randrange(0x10000)])
        action = generator.choice([current, current, 0, 1, 5, 0x9c, -1, -0x8000, 0x7fff, 0x10001,
                                   generator.randrange(-5, 300)])
        type_ = generator.choice([0x7a5, 0xa91, 0x9fe])
        obj.define(OBJECT+0x2a, struct.pack('<H', current))
        obj.define(OBJECT+0x5c, struct.pack('<I', type_))
        obj.define(OBJECT+0xd0, struct.pack('<f', am.f32(generator.uniform(-3, 40))))
        if generator.random() < 0.5:
            obj.define(OBJECT+0x2c, struct.pack('<H', generator.randrange(0x10000)))
            obj.define(OBJECT+0xd4, struct.pack('<f', am.f32(generator.uniform(-3, 40))))
        model = am.undefined_region('model', MODEL, 0xd0)
        model.define(MODEL+0x26, struct.pack('<h', generator.choice([0, 1, 7, 0x9c, 0x9d, 300, -1, 0x7fff])))
        cases.append({'label': f'set-action-{index}', 'regions': [obj, model], 'action': action, 'type': type_,
                      'present': generator.random() > 0.05})
    return cases


def compare_set_action(machine, authored, case):
    model_at = lambda index: MODEL if case['present'] and index == case['type'] else 0  # noqa: E731
    client = machine.execute(SET_ACTION, [OBJECT, case['action']], copy_regions(case['regions']),
                             {MANAGER: lambda m: MANAGER_ADDRESS, MODEL_AT: lambda m: (model_at(m.argument(0)), 4)})
    function = authored.handle.mu_set_action
    callback = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32)(lambda c, index: model_at(index))
    function.argtypes = [ctypes.POINTER(authored.Memory), ctypes.c_uint32, ctypes.c_int32, type(callback),
                         ctypes.c_void_p]
    buffers, memory, images = authored.memory(case['regions'])
    status = function(ctypes.byref(memory), OBJECT, case['action'], callback, None)
    mine = {r.name: bytes(b) for r, b in buffers}
    differences = []
    if not client['ok']:
        differences.append(('client', client['checks'], client['stopped']))
    if status != 0:
        differences.append(('authored-status', status))
    for name, payload in mine.items():
        if client['regions'].get(name) != payload:
            differences.append(('region', name))
    changed = client['regions']['object'] != bytes(case['regions'][0].data)
    return {'label': case['label'], 'match': not differences, 'differences': differences, 'changed': changed}


def compare_unarmed_stop(machine, authored, class_byte, world, rand_value):
    calls = []

    def rand(m):
        calls.append(1)
        return rand_value
    client = machine.execute(UNARMED_STOP, [class_byte],
                             [am.defined_region('world', WORLD, struct.pack('<i', world), writable=False)],
                             {RAND: rand})
    function = authored.handle.mu_player_unarmed_stop_action
    mine_calls = []

    def c_rand(context):
        mine_calls.append(1)
        return rand_value
    callback = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)(c_rand)
    function.argtypes = [ctypes.c_uint8, ctypes.c_int32, type(callback), ctypes.c_void_p]
    function.restype = ctypes.c_int32
    mine = function(class_byte, world, callback, None)
    client_value = struct.unpack('<i', struct.pack('<I', client['eax']))[0]
    ok = client['ok'] and client_value == mine and len(calls) == len(mine_calls)
    return {'match': ok, 'value': client_value, 'class': class_byte, 'world': world, 'rand': rand_value,
            'mine': mine, 'stopped': client['stopped']}


# --------------------------------------------------------------------------
# Player action speeds: the speed section of the player loader 0x01830aa6.

PLAYER_SPEEDS_START, PLAYER_LOADER_FRAME = 0x018311c2, 0xc+0x5c
PLAYER_MODEL_AT, PLAYER_ACTION_AT, ATTACK_SPEED = 0x0142fc46, 0x00d33153, 0x0138d9cf
PLAYER_ACTIONS = 0x186     # the loader requires Player.bmd to have exactly 0x186 actions (0x01830b39)
PLAYER_RECORD, PLAYER_ACTION_ARRAY = 0x25800000, 0x25000000


def extract_player_speeds(machine):
    """Runs the loader from 0x018311c2 (after its part loads and a temporary object array) to
    its end. The Player model getter 0x0142fc46 and the action getter 0x00d33153 (returns
    &Actions[a] of model 0xa91) are stubs over a declared 0x186-action model; the attack-speed
    adjustment 0x0138d9cf, which reads the hero's stats, is recorded and skipped."""
    model = bytearray(0xd0)
    struct.pack_into('<hh', model, 0x24, 0, PLAYER_ACTIONS)
    struct.pack_into('<I', model, 0x30, PLAYER_ACTION_ARRAY)
    actions = b''.join(struct.pack('<BBBBIhBBI', 0xee, 0, 0, 0, CLASS_ACTION_SENTINEL, 10, 0, 0, 0)
                       for _ in range(PLAYER_ACTIONS))
    regions = [am.defined_region('player', PLAYER_RECORD, bytes(model)),
               am.defined_region('actions', PLAYER_ACTION_ARRAY, actions),
               am.defined_region('world', WORLD, struct.pack('<i', 0), writable=False)]
    calls = []
    stubs = {ACCESS_MODEL: lambda m: calls.append(('access', m.argument(0), m.cstring(m.argument(2)),
                                                   m.argument(3))) or 0,
             MANAGER: lambda m: MANAGER_ADDRESS, PLAYER_MODEL_AT: lambda m: PLAYER_RECORD,
             PLAYER_ACTION_AT: lambda m: (PLAYER_ACTION_ARRAY+16*m.argument(0), 4),
             ATTACK_SPEED: lambda m: calls.append(('attack-speed',)) or 0}
    result = machine.execute(PLAYER_SPEEDS_START, [], regions, stubs, frame=(PLAYER_LOADER_FRAME, {}))
    data = result['regions']['actions']
    speeds = [struct.unpack_from('<I', data, 16*a+4)[0] for a in range(PLAYER_ACTIONS)]
    loops = [data[16*a] for a in range(PLAYER_ACTIONS)]
    player = result['regions']['player']
    return {'ok': result['ok'], 'stopped': result['stopped'], 'calls': calls,
            'speeds': [0 if v == CLASS_ACTION_SENTINEL else v for v in speeds],
            'loops': [0 if v == 0xee else v for v in loops],
            'head_bone': struct.unpack_from('<i', player, 0x60)[0]}


def emit_player_table(player):
    lines = ['/* Generated by scripts/validate_actors.py --emit-player-table from the speed section of',
             ' * the client\'s player loader 0x01830aa6 (from 0x018311c2) executed under Unicorn over a',
             ' * 0x186-action Player model. Base play speeds (binary32 bits, 0 = not written) and loop',
             ' * flags per Player action; the hero attack-speed adjustment 0x0138d9cf is not applied.',
             ' * Do not edit. */', '#ifndef MU_PLAYER_ACTION_TABLE_H', '#define MU_PLAYER_ACTION_TABLE_H', '',
             f'#define MU_PLAYER_ACTION_COUNT {PLAYER_ACTIONS}', '',
             'static const uint32_t mu_player_action_speeds[MU_PLAYER_ACTION_COUNT] = {']
    for i in range(0, PLAYER_ACTIONS, 6):
        lines.append('    ' + ', '.join(f'{v:#010x}u' for v in player['speeds'][i:i+6]) + ',')
    lines += ['};', '', 'static const uint8_t mu_player_action_loops[MU_PLAYER_ACTION_COUNT] = {']
    for i in range(0, PLAYER_ACTIONS, 24):
        lines.append('    ' + ', '.join(str(v) for v in player['loops'][i:i+24]) + ',')
    lines += ['};', '', '#endif', '']
    return '\n'.join(lines)


# --------------------------------------------------------------------------
# OpenNpc 0x01808a40: NPC model index -> file, action speeds (extraction under emulation).

NPC_FIRST, NPC_LAST = 0x9fe, 0xa90
NPC_ACTIONS = 16


def extract_npc(machine, index, world=0):
    case = monster_case(f'npc{index:#x}', 0, actions=NPC_ACTIONS, world=world)
    case['index'] = index
    result = run_client_open(machine, case, OPEN_NPC, index)
    if not result['ok']:
        return {'index': index, 'error': str(result['stopped'])}
    actions = result['regions']['actions0']
    files = [c[1:] for c in result['calls'] if c[0] == 'access']
    own = [f for f in files if f[0] == index]
    return {'index': index, 'file': own[0][1:] if own else None, 'extra': [f for f in files if f[0] != index],
            'textures': [c[1:] for c in result['calls'] if c[0] == 'texture' and c[1] == index],
            'speeds': [struct.unpack_from('<I', actions, 16*a+4)[0] for a in range(NPC_ACTIONS)],
            'loops': [actions[16*a] for a in range(NPC_ACTIONS)],
            'initial_speeds': [struct.unpack_from('<I', case['regions'][1].data, 16*a+4)[0] for a in range(NPC_ACTIONS)]}


def c_string(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def emit_npc_table(records):
    rows = []
    for r in records:
        if 'error' in r or not r.get('file'):
            continue
        directory, name, number = r['file']
        speeds = [s if s != i else 0 for s, i in zip(r['speeds'], r['initial_speeds'])]
        rows.append(f'    {{{r["index"]:#06x}, {c_string(directory)}, {c_string(name)}, {number}, '
                    f'{{{", ".join(f"{v:#010x}u" for v in speeds)}}}}},')
    lines = ['/* Generated by scripts/validate_actors.py --emit-npc-table from the client\'s OpenNpc',
             ' * 0x01808a40 executed under Unicorn (world 0) for model indices 0x9fe..0xa90 with a',
             ' * 16-action model. Fields: model index, AccessModel directory, name and number (-1:',
             ' * "<name>.bmd"), play-speed bits written for actions 0..15 (0 = not written). Indices',
             ' * that only load part models from a parent case are absent. Do not edit. */',
             '#ifndef MU_NPC_TABLE_H', '#define MU_NPC_TABLE_H', '', f'#define MU_NPC_ROWS {len(rows)}', '',
             'static const mu_npc_model mu_npc_models[MU_NPC_ROWS] = {'] + rows + ['};', '', '#endif', '']
    return '\n'.join(lines)


# --------------------------------------------------------------------------
# CreateMonster 0x0137fbac: server class -> model, scale and equipment slots.

CREATE_MONSTER, CREATE_GENERIC = 0x0137fbac, 0x0137ff8c
CREATE_CHARACTER, SET_NAME, POST_CREATE, RAND = 0x0137f6c2, 0x0129de8d, 0x013b8ade, 0x01989721
OPEN_NPC = 0x01808a40
CLASS_CHARACTER = 0x23000000
CLASS_SLOTS = 9          # character + 0x1c4 + slot*0x3fc: u16 model/item, +2 u8 level (6, 7 weapons; 8 wing)
DEFAULT_SCALE = 0.9      # character create 0x0137d8a1 stores 0.9 into object +0xa0 (static reading)
# Map processors tried before the generic switch, in CreateMonster order. Entries marked
# 'assumed-declines' are world-specific processors whose state lives in uncaptured singletons;
# the extraction treats them as declining (a world where none of them applies). The chain also
# passes a 5-byte patch at 0x0137fe24 that jumps outside the captured text (a protection
# boundary, not analysed); the chain is assumed to continue past it.
CLASS_CHAIN = [
    ('virtual', 0x00db747f, 'assumed-declines'), ('cdecl', 0x00df1b30), ('cdecl', 0x00d8f3a3), ('cdecl', 0x00dfc787),
    ('cdecl', 0x00daced9), ('cdecl', 0x00d640ce), ('cdecl', 0x00e76c0a), ('cdecl', 0x00e7ff85), ('cdecl', 0x00e879ad),
    ('this', 0x00d558c3, 'assumed-declines'), ('this', 0x00a9c56b, 'assumed-declines'),
    ('this', 0x00a93a2e, 0x23920000), ('cdecl', 0x00e326cd), ('cdecl', 0x00e60ac8), ('this', 0x00a96ab8, 0x23930000),
    ('this', 0x00ea37d5, 'assumed-declines')]
CLASS_SCENE = 0x01d1df70
FAKE_MODEL = 0x23a00000


def class_case(world, rand):
    regions = [am.defined_region('character', CLASS_CHARACTER, bytes(0x4000)),
               am.defined_region('world', WORLD, struct.pack('<i', world), writable=False),
               am.defined_region('scene', CLASS_SCENE, struct.pack('<i', 0), writable=False),
               *class_models(),
               am.undefined_region('singleton-a', 0x23920000, 0x400),
               am.undefined_region('singleton-b', 0x23930000, 0x400)]
    record = {'calls': []}

    def create(m):
        record['calls'].append(('create',)+tuple(m.argument(i) for i in range(5)))
        return CLASS_CHARACTER

    def string_ctor(m):
        this = m.uc.reg_read(m.x86.UC_X86_REG_ECX)
        m.uc.mem_write(this, struct.pack('<I', m.argument(0)))
        return this, 4

    stubs = {CREATE_CHARACTER: create,
             OPEN_MONSTER: lambda m: record['calls'].append(('monster', m.argument(0))) or 0,
             OPEN_NPC: lambda m: record['calls'].append(('npc', m.argument(0))) or 0,
             STRING_CTOR: string_ctor, STRING_DTOR: lambda m: (0, 0), SET_NAME: lambda m: (0, 4),
             POST_CREATE: lambda m: 0, RAND: lambda m: rand, MANAGER: lambda m: MANAGER_ADDRESS,
             MODEL_AT: lambda m: model_at(m)}
    # Class 257's five creation joints. Effects are recorded, not executed by this class/model extractor.
    stubs[0x0153b02c] = lambda m: record['calls'].append(('joint',) + tuple(m.argument(i) for i in range(5))) or 0
    pool = {}

    def model_at(m):
        index = m.argument(0)
        if index not in pool:
            if len(pool) == CLASS_MODEL_SLOTS:
                m.stop(('model-pool-empty', hex(index)))
                return 0, 4
            pool[index] = FAKE_MODEL+len(pool)*0x1000
        return pool[index], 4
    record['pool'] = pool
    return regions, stubs, record


CLASS_MODEL_SLOTS = 4
CLASS_ACTION_SENTINEL = 0x7fc0dead


def class_models():
    """Model records handed out by the stubbed lookup: 16 actions whose speed slots hold a sentinel,
    so the speeds CreateMonster writes for a class can be read back."""
    regions = []
    for slot in range(CLASS_MODEL_SLOTS):
        base = FAKE_MODEL+slot*0x1000
        model = bytearray(0xd0)
        struct.pack_into('<hhhh', model, 0x22, 0, 0, 16, 0)
        struct.pack_into('<I', model, 0x30, base+0x100)
        regions.append(am.defined_region(f'model{slot}', base, bytes(model)))
        actions = b''.join(struct.pack('<BBBBIhBBI', 0, 0, 0, 0, CLASS_ACTION_SENTINEL, 10, 0, 0, 0) for _ in range(16))
        regions.append(am.defined_region(f'model{slot}-actions', base+0x100, actions))
    return regions


def extract_class(machine, server_class, world=0, rand=0):
    arguments = [server_class, 10, 20, 1000+server_class, 0]
    for entry in CLASS_CHAIN:
        if entry[-1] == 'assumed-declines':
            continue
        regions, stubs, record = class_case(world, rand)
        if entry[0] == 'cdecl':
            result = machine.execute(entry[1], arguments[:4], regions, stubs)
        else:
            result = machine.execute(entry[1], arguments[:4], regions, stubs, ecx=entry[2], cleanup=0x10)
        if not result['ok']:
            return {'class': server_class, 'error': [hex(entry[1]), str(result['stopped']), result['error']]}
        if result['eax']:
            return class_record(server_class, hex(entry[1]), record, result)
    regions, stubs, record = class_case(world, rand)
    result = machine.execute(CREATE_GENERIC, arguments, regions, stubs, frame=(0x1dd4+0xc, {-0x10: 0}))
    if not result['ok']:
        return {'class': server_class, 'error': ['generic', str(result['stopped']), result['error']]}
    return class_record(server_class, 'generic', record, result)


def class_record(server_class, via, record, result):
    character = result['regions']['character']
    creates = [c for c in record['calls'] if c[0] == 'create']
    opens = [c for c in record['calls'] if c[0] in ('monster', 'npc')]
    scale_bits = struct.unpack_from('<I', character, 0x32f4)[0]
    slots = [(struct.unpack_from('<H', character, 0x1c4+k*0x3fc)[0], character[0x1c6+k*0x3fc])
             for k in range(CLASS_SLOTS)]
    speeds = []
    for index, base in record['pool'].items():
        slot = (base-FAKE_MODEL)//0x1000
        actions = result['regions'][f'model{slot}-actions']
        for action in range(16):
            loop, = struct.unpack_from('<B', actions, 16*action)
            bits_, = struct.unpack_from('<I', actions, 16*action+4)
            if bits_ != CLASS_ACTION_SENTINEL or loop:
                speeds.append((index, action, bits_, loop))
    return {'class': server_class, 'via': via, 'model': creates[0][2] if creates else None, 'speeds': speeds,
            'creates': len(creates), 'opens': opens, 'scale_bits': scale_bits, 'slots': slots,
            'class_byte': character[0x12], 'joints': [c for c in record['calls'] if c[0] == 'joint']}


def static_generic_target(text, server_class):
    """Jump-table target of the generic switch (static reading, no execution)."""
    def u8(a): return text[a-am.TEXT_BASE]
    def u32(a): return struct.unpack_from('<I', text, a-am.TEXT_BASE)[0]
    if server_class == 0x19e:
        return 0x0138549e
    if server_class <= 0x198:
        return u32(0x0138ce1c+4*u8(0x0138d070+server_class))
    index = (server_class-0x1aa) & 0xffffffff
    if server_class > 0x19e and index <= 0x22c:
        return u32(0x0138d20c+4*u8(0x0138d430+index))
    return 0x01382f2d


def generic_switch_default(server_class):
    """True when the generic switch reaches its default (not a table entry) for this class."""
    if server_class == 0x19e or server_class <= 0x198:
        return False
    return not (server_class > 0x19e and ((server_class-0x1aa) & 0xffffffff) <= 0x22c)


def static_generic_model(text, server_class):
    """First CreateCharacter model immediate in the generic case block, or None."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    address = static_generic_target(text, server_class)
    pushes = []
    for ins in md.disasm(text[address-am.TEXT_BASE:address-am.TEXT_BASE+0x800], address):
        if ins.mnemonic == 'push':
            pushes.append(ins.op_str)
        if ins.mnemonic == 'call' and ins.op_str == hex(CREATE_CHARACTER):
            candidate = pushes[-2] if len(pushes) >= 2 else ''
            return int(candidate, 16) if candidate.startswith('0x') else None
        if ins.mnemonic in ('jmp', 'ret') and ins.op_str != hex(CREATE_CHARACTER):
            if ins.mnemonic == 'ret' or not ins.op_str.startswith('0x'):
                return None
    return None


def extract_classes(machine, text, count=0x400):
    records = [extract_class(machine, c) for c in range(count)]
    agree = disagree = computed = 0
    for record in records:
        if record.get('via') != 'generic':
            continue
        expected = static_generic_model(text, record['class'])
        if expected is None:
            computed += 1
        elif expected == record['model']:
            agree += 1
        else:
            disagree += 1
            record['static_model'] = expected
    return records, {'static_agree': agree, 'static_disagree': disagree, 'static_not_immediate': computed}


def emit_class_table(records, text):
    rows, speed_rows = [], []
    for r in records:
        if 'error' in r or r['model'] is None:
            continue
        opened = r['opens'][0] if r['opens'] else ('none', 0)
        kind = {'monster': 'MU_CLASS_MONSTER', 'npc': 'MU_CLASS_NPC'}.get(opened[0], 'MU_CLASS_OTHER')
        if r['model'] == 0xa91:
            kind = 'MU_CLASS_PLAYER_MODEL'
        if r['via'] == 'generic' and generic_switch_default(r['class']):
            kind = 'MU_CLASS_DEFAULT'   # switch default: unknown classes become monster type 0
            if r['class'] > 0x3ff:
                continue
        for index, action, value, loop in r['speeds']:
            speed_rows.append(f'    {{{r["class"]:#05x}, {index:#06x}, {action}, {value:#010x}u, {loop}}},')
        slots = ', '.join(f'{{{w:#06x}, {lv}}}' for w, lv in r['slots'][:CLASS_SLOTS])
        rows.append(f'    {{{r["class"]:#05x}, {kind}, {r["model"]:#06x}, {opened[1]:#06x}, {r["scale_bits"]:#010x}u, '
                    f'{{{slots}}}, {r["class_byte"]:#04x}}},')
    lines = ['/* Generated by scripts/validate_actors.py --emit-class-table from the client\'s',
             ' * CreateMonster 0x0137fbac (map processors and generic switch) executed under',
             ' * Unicorn with world 0 and rand() = 0 (see docs/research/client-actors.md for the',
             ' * processors assumed to decline). Fields: server class, kind, model index passed to',
             ' * CreateCharacter, OpenMonsterModel type or OpenNpc index, object scale bits (0 = not',
             ' * written; character create leaves 0.9), nine character slots {u16 model/item, u8',
             ' * level} at +0x1c4 + k*0x3fc (6/7 weapons, 8 wing), class byte +0x12. Do not edit. */',
             '#ifndef MU_MONSTER_CLASS_TABLE_H', '#define MU_MONSTER_CLASS_TABLE_H', '',
             f'#define MU_MONSTER_CLASS_ROWS {len(rows)}', '',
             'static const mu_monster_class mu_monster_classes[MU_MONSTER_CLASS_ROWS] = {'] + rows + \
            ['};', '', '/* Action records CreateMonster itself writes for a class: model index, action,',
             ' * speed bits (0x7fc0dead = not written), loop byte. */',
             f'#define MU_MONSTER_CLASS_SPEED_ROWS {len(speed_rows)}', '',
             'static const mu_monster_class_speed mu_monster_class_speeds[MU_MONSTER_CLASS_SPEED_ROWS] = {'] + \
            speed_rows + ['};', '', '#endif', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--library', default=str(ROOT/f'reconstructed/actors/libactors.{SUFFIX}'))
    parser.add_argument('--output')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--emit-class-table')
    parser.add_argument('--emit-npc-table')
    parser.add_argument('--emit-player-table')
    parser.add_argument('--classes', type=lambda v: int(v, 0), default=0x400)
    args = parser.parse_args()
    text = am.load_pinned(args.text, am.TEXT_BYTES, am.TEXT_SHA256, 'restored text')
    data = am.load_pinned(args.data, am.DATA_BYTES, am.DATA_SHA256, 'second image section')
    machine = am.ActorMachine(text, data)
    authored = Authored(Path(args.library))
    bodies = {}
    for name, (s, e, digest) in BODIES.items():
        observed = hashlib.sha256(text[s-am.TEXT_BASE:e-am.TEXT_BASE]).hexdigest()
        if observed != digest:
            raise SystemExit(f'{name}: captured body differs from the pinned digest')
        bodies[name] = {'start': hex(s), 'end_exclusive': hex(e), 'sha256': digest}
    import actor_static
    lifted = actor_static.lift_all(actor_static.Image(text, data))
    results = []
    for case in monster_cases()[:args.limit]:
        results.append(compare_open(machine, authored, case, lifted))
    player = extract_player_speeds(machine)
    if args.emit_player_table and player['ok']:
        Path(args.emit_player_table).write_text(emit_player_table(player))
    npc_records = [extract_npc(machine, index) for index in range(NPC_FIRST, NPC_LAST+1)]
    if args.emit_npc_table:
        Path(args.emit_npc_table).write_text(emit_npc_table(npc_records))
    class_records, class_static = extract_classes(machine, text, args.classes)
    if args.emit_class_table:
        Path(args.emit_class_table).write_text(emit_class_table(class_records, text))
    set_results = [compare_set_action(machine, authored, case) for case in set_action_cases()[:args.limit]]
    stop_results = [compare_unarmed_stop(machine, authored, c, w, r) for c in range(256)
                    for w in (0, 0x11, 0x12, 0x17, 0x18, 0x1e, 0x35, 0x61, -1) for r in (0, 20, 7, 0x7fff, -20, -3)]
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
              'set_action': {'cases': len(set_results), 'matches': sum(r['match'] for r in set_results),
                             'changed': sum(r['changed'] for r in set_results),
                             'mismatches': [r for r in set_results if not r['match']][:20]},
              'unarmed_stop': {'cases': len(stop_results), 'matches': sum(r['match'] for r in stop_results),
                               'values': sorted({r['value'] for r in stop_results}),
                               'mismatches': [r for r in stop_results if not r['match']][:20]},
              'player_speeds': {'ok': player['ok'], 'stopped': player['stopped'],
                                'written': sum(1 for v in player['speeds'] if v), 'loops': sum(player['loops']),
                                'head_bone': player['head_bone'], 'calls': len(player['calls'])},
              'npcs': {'count': len(npc_records), 'extracted': sum('error' not in r for r in npc_records),
                       'with_file': sum(1 for r in npc_records if r.get('file')), 'records': npc_records},
              'classes': {'count': len(class_records), 'extracted': sum('error' not in r for r in class_records),
                          'by_route': {route: sum(1 for r in class_records if r.get('via') == route)
                                       for route in sorted({r.get('via') for r in class_records if 'via' in r})},
                          **class_static,
                          'errors': [r for r in class_records if 'error' in r][:200],
                          'records': [r for r in class_records if 'error' not in r]},
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
    for key in ('set_action', 'unarmed_stop', 'player_speeds'):
        print(json.dumps({k: v for k, v in report[key].items() if k != 'mismatches'}))
    print(json.dumps({k: v for k, v in report['npcs'].items() if k != 'records'}))
    print(json.dumps({k: v for k, v in report['classes'].items() if k not in ('errors', 'records')}))
    print(json.dumps({k: v for k, v in report['character_step'].items() if k != 'mismatches'}))
    for m in (mismatches+step_mismatches)[:10]:
        print(m)
    failed = mismatches or step_mismatches or class_static['static_disagree'] or \
        report['set_action']['mismatches'] or report['unarmed_stop']['mismatches']
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
