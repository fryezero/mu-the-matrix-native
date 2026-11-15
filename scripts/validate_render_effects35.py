#!/usr/bin/env python3
"""RENDER-EFFECTS-035: receive-slice callers of the skills outside the learned set.

Only the case bodies of the two receive switches and the selected end bodies execute, on authored
CHARACTER/OBJECT records and an authored frame. The packet prologues, network, power, eligibility,
actor construction and every effect consumer are outside this comparison.

One table (ROWS) drives every group: per row the original body, its exit and the frame it needs.
Each case compares, in order, every effect/joint/sound/pose/arrow request with all its argument
words, plus the state the body writes (AttackTime, target-index word, hero bytes).
"""
import argparse
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import time
import actor_machine as am
import pins
import validate_combat as vc
import validate_particles as pt
import validate_skill_fx as fx
import validate_render_effects30 as r30

ROOT = Path(__file__).resolve().parents[1]
CHAR, TCHAR, HCHAR = 0x28000000, 0x28010000, 0x28020000     # source, target and (when distinct) hero
OBJ = 0x3254                                               # CHARACTER -> OBJECT
HERO_PTR, HERO_DATA_PTR = 0x0a39d754, 0x01d1df18
MODEL = 0x23000000
SKILL_ACTION, SET_MAGIC, SET_ATTACK, BOW_POSE, ARROWS = 0x012b001a, 0x013944d9, 0x01392bde, 0x013946ee, 0x0158d5bd
MAGIC_EXIT, POSITION_EXIT, AREA_EXIT, TARGET_EXIT = 0x0125c47c, 0x01260e1d, 0x013aea7a, 0x013b1911
MAGIC_FAIL = 0x0125c47f      # the magic handler's other return (eax = 0), taken when a model is missing
POSITION_FAIL = 0x01261592   # the same early return of the position handler
F3 = C.c_float * 3

# skill: (group, family, body, end of body). family: magic / position receive slice, area / target end.
ROWS = {
    740: ('A', 'magic', 0x012598ab, 0x01259964), 77: ('A', 'magic', 0x012575bc, 0x01257634),
    652: ('A', 'magic', 0x012591f6, 0x01259262), 651: ('A', 'magic', 0x0125983f, 0x0125984b),
    727: ('A', 'magic', 0x01255ba2, 0x01255c5c), 2023: ('A', 'position', 0x0125f710, 0x0125f78b),
    2025: ('A', 'position', 0x0125f82c, 0x0125f8a6), 2047: ('A', 'position', 0x0125f798, 0x0125f82c),
    1500: ('B', 'magic', 0x01254c46, 0x01254e31), 1502: ('B', 'magic', 0x01254e31, 0x0125501c),
    1503: ('B', 'magic', 0x0125501c, 0x012551f9),
    1125: ('C', 'magic', 0x01259964, 0x01259b1b), 1126: ('C', 'magic', 0x01259b1b, 0x01259cd2),
    1127: ('C', 'magic', 0x01259cd2, 0x01259e89),
    425: ('D', 'magic', 0x01258d76, 0x01258fbc), 430: ('D', 'magic', 0x01258fbc, 0x012591f6),
    2024: ('D', 'magic', 0x0125bf1c, 0x0125c134), 234: ('D', 'magic', 0x012552d1, 0x012558ff),
    432: ('E', 'magic', 0x0125594d, 0x0125599c), 2026: ('E', 'magic', 0x0125594d, 0x0125599c),
    2027: ('E', 'magic', 0x0125594d, 0x0125599c),
}
ENDS = {432: ('area', 0x013a9449, 0x013a94a4), 2026: ('target', 0x013b18a2, 0x013b1911),
        2027: ('target', 0x013b16c1, 0x013b18a2)}
# A row with a case in both receive switches: the position case is phase 2.
POSITION_CASES = {234: ('position', 0x0125ddd7, 0x0125e24b)}
# Second group: the learned buffs' end bodies and the general link selector.
BUFF_ENDS = {27: (0x013afb06, 0x013afcea), 28: (0x013afcea, 0x013afd5c)}
LINK_SWITCH, LINK_END, LINK_HELPER, LINK_OTHER, LINK_INDEX = 0x0137eefc, 0x0137f5f6, 0x00df230b, 0x00d9013e, 0x013a5658
LINK_OFFSET, LINK_STRIDE = 0x19b1, 0x3fc


class Actor(C.Structure):
    _fields_ = [('owner', C.c_int32), ('key', C.c_uint16), ('index', C.c_uint16), ('class_word', C.c_int16),
                ('height_word', C.c_uint16), ('position', F3), ('angle', F3), ('light', F3)]


class Input(C.Structure):
    _fields_ = [('skill', C.c_int32), ('base', C.c_int32), ('source', Actor), ('target', Actor),
                ('source_is_hero', C.c_uint8), ('model_present', C.c_uint8), ('mounted', C.c_uint8),
                ('presence_18', C.c_uint8), ('presence_2', C.c_uint8), ('joint_4', C.c_uint8),
                ('joint_9', C.c_uint8), ('flag_7', C.c_uint8), ('attack_time', C.c_uint8),
                ('hero_attack_time', C.c_uint8),
                ('hero_key', C.c_uint16), ('source_key', C.c_uint16), ('target_key', C.c_uint16),
                ('packet_word', C.c_uint16), ('target_word', C.c_uint16), ('bone', F3),
                ('random', C.c_int32 * 2), ('bone_count', C.c_int32), ('bones', F3 * 2)]


class Call(C.Structure):
    _fields_ = [('visual', fx.Call), ('site', C.c_uint32), ('skill', C.c_int32)]


class Plan(C.Structure):
    _fields_ = [('count', C.c_int32), ('attack_time', C.c_int32), ('hero_attack_time', C.c_int32),
                ('target_index', C.c_int32), ('hero_byte', C.c_int32), ('frame_reset', C.c_int32),
                ('calls', Call * 40)]


class Machine(r30.Machine):
    """Leaves a case body at its switch join: the join returns through the sentinel."""
    EXITS = (MAGIC_EXIT, MAGIC_FAIL, POSITION_EXIT, POSITION_FAIL, AREA_EXIT, TARGET_EXIT)

    def stub_entry(self, uc, address, size, ignored):
        if address in self.EXITS and address in self.stubs:
            for reg, value in self.preserved.items():
                uc.reg_write(reg, value)
            uc.mem_write(am.TIB, struct.pack('<I', am.SEH_HEAD))
            uc.reg_write(self.x86.UC_X86_REG_ESP, am.ENTRY_ESP + 4)
            uc.reg_write(self.x86.UC_X86_REG_EIP, am.SENTINEL)
            return
        super().stub_entry(uc, address, size, ignored)


def load(path):
    lib = C.CDLL(str(path))
    lib.mu_skill35_plan_cast.argtypes = [C.POINTER(Input), C.c_int, C.POINTER(Plan)]
    lib.mu_skill35_select.argtypes = [C.c_int32, C.c_int32]
    lib.mu_skill35_learned.argtypes = [C.c_int32, C.POINTER(C.c_uint16), C.c_int32]
    lib.mu_skill35_action.argtypes = [C.c_int32, C.c_int32, C.c_int32, C.c_int32]
    lib.mu_skill35_step.argtypes = [C.c_int32, C.c_int32, C.c_int32, C.c_float, C.POINTER(C.c_uint8)]
    lib.mu_skill35_buff_end.argtypes = [C.POINTER(Input), C.POINTER(Plan)]
    lib.mu_link_bones.argtypes = [C.c_int32, C.POINTER(C.c_uint8)]
    lib.mu_link_index.argtypes = [C.c_int32, C.c_int32]
    return lib


def address_of(owner):
    """Native owner index -> the authored OBJECT address: 0 source, 1 target, -1 none."""
    return {0: CHAR + OBJ, 1: TCHAR + OBJ}.get(owner, 0)


def normalized(call):
    c = call.visual
    if c.routine == SKILL_ACTION:
        return ['action', c.type & 0xffffffff, c.subtype & 0xffffffff]
    if c.routine in (SET_MAGIC, SET_ATTACK):
        return ['pose', c.routine]
    if c.routine == 0x01989721:
        return ['rand']
    if c.routine == 0x012b678d:
        return ['bone', address_of(c.owner), c.range]
    if c.routine == 0x009fd745:
        return ['key-list', address_of(c.owner) + 0x1dc, c.type & 0xffffffff]
    if c.routine == ARROWS:
        return ['arrow', address_of(c.owner), 0, c.range, c.subtype, c.type]
    if c.routine == fx.PLAY_BUFFER:
        return ['sound', c.type, address_of(c.owner), 0, call.site]
    if c.routine == fx.CREATE_EFFECT_WRAPPER:
        return ['effect', c.type, list(c.position), list(c.angle), list(c.light), c.subtype, address_of(c.owner),
                [c.range & 0xffffffff, call.skill & 0xffffffff, 0, 0, fx.bits(c.scale), c.arg7 & 0xffffffff, 0, 0]]
    if c.routine == fx.CREATE_JOINT:
        return ['joint', c.type, list(c.position), list(c.target), list(c.angle), c.subtype, address_of(c.owner),
                c.scale, [c.arg7 & 0xffffffff, c.arg8 & 0xffffffff, 0, call.skill & 0xffffffff, 0, 0xffffffff, 0]]
    raise ValueError(hex(c.routine))


def case_input(rng, skill, n):
    """One authored case. Deterministic edges first, then random records."""
    s = Input()
    s.skill = s.base = skill
    s.source.owner, s.target.owner = 0, 1
    for actor in (s.source, s.target):
        actor.key = rng.randrange(1, 0x10000 if n % 9 == 8 else 0x7fff)
        actor.index = rng.randrange(400)
        actor.class_word, actor.height_word = rng.choice([0, 1, 2, 0x4d, 0x4c]), rng.randrange(600)
        for k in range(3):
            actor.position[k] = fx.f32(rng.uniform(-1000, 25000))
            actor.angle[k] = fx.f32(rng.uniform(-360, 360))
            actor.light[k] = fx.f32(rng.random())
    s.source_is_hero = n % 2
    s.hero_key = s.source.key if s.source_is_hero else rng.randrange(1, 0x7fff)
    # The receive record's key words: normally the two characters' own keys; equal words are the self-cast edge.
    s.source_key, s.target_key = s.source.key, s.target.key
    if n % 5 == 3:
        s.target_key = s.source_key
    if n % 7 == 5:
        s.source_key = s.hero_key
    s.packet_word, s.target_word = rng.randrange(65536), rng.randrange(65536)
    s.model_present = n % 11 != 10
    s.mounted = 0
    s.presence_18, s.presence_2 = n % 3 == 2, n % 4 == 3
    s.joint_4, s.joint_9 = n % 8 == 7, n % 16 == 3
    s.flag_7 = n % 5 != 4
    for k in range(3):
        s.bone[k] = fx.f32(rng.uniform(-1000, 25000))
    s.random[:] = [rng.randrange(32768), rng.randrange(32768)]
    s.bone_count = rng.choice([0, 1, 60, 77, -3]) if n % 4 == 1 else rng.randrange(1, 90)
    for i in range(2):
        for k in range(3):
            s.bones[i][k] = fx.f32(rng.uniform(-1000, 25000))
    s.attack_time = rng.choice([0, 1, 5, 14])
    s.hero_attack_time = s.attack_time if s.source_is_hero else rng.choice([0, 1, 5, 14])
    if n % 13 == 12:      # sign-extension edge of the hero key compare
        s.hero_key = s.source_key = 0x8000 | rng.randrange(0x8000)
    return s


def original(m, skill, s, family, entry):
    """Run one original body on authored records; return the machine result and the request stream."""
    hero = CHAR if s.source_is_hero else HCHAR
    regions = []
    for base, actor, name in ((CHAR, s.source, 'character'), (TCHAR, s.target, 'target')):
        region = am.undefined_region(name, base, 0x3670)
        obj = base + OBJ
        for off, data in [(0x21, bytes([s.attack_time])), (0x3e, struct.pack('<H', actor.key)),
                          (0x146, struct.pack('<h', actor.class_word)), (0x158, struct.pack('<H', actor.height_word)),
                          (0x40, struct.pack('<H', s.target_word)), (0x7, bytes([s.flag_7])),
                          (0x26, struct.pack('<H', skill))]:
            region.define(base + off, data)
        for off, data in [(0x5c, struct.pack('<i', 0xa91)), (0x158, struct.pack('<3f', *actor.position)),
                          (0x164, struct.pack('<3f', *actor.angle)), (0xec, struct.pack('<3f', *actor.light)),
                          (0xd0, struct.pack('<f', 3.0)), (0x364, b'\xff\xff'), (0x1dc, struct.pack('<I', 0))]:
            region.define(obj + off, data)
        regions.append(region)
    if not s.source_is_hero:
        region = am.undefined_region('hero', HCHAR, 0x3670)
        region.define(HCHAR + 0x3e, struct.pack('<H', s.hero_key))
        region.define(HCHAR + 0x21, bytes([s.hero_attack_time]))
        regions.append(region)
    model = am.undefined_region('model', MODEL, 0x40)
    model.define(MODEL + 0x22, struct.pack('<h', s.bone_count))
    regions += [model, am.defined_region('hero-pointer', HERO_PTR, struct.pack('<I', hero)),
                am.defined_region('hero-data-pointer', HERO_DATA_PTR, struct.pack('<I', fx.HERO_DATA)),
                am.defined_region('hero-data', fx.HERO_DATA + 0x2de8, bytes(8))]
    client = []

    def effect(mm):
        client.append(['effect', mm.argument(0), mm.floats(mm.argument(1), 3), mm.floats(mm.argument(2), 3),
                       mm.floats(mm.argument(3), 3), mm.argument(4), mm.argument(5),
                       [mm.argument(i) for i in range(6, 14)]])
        return 0

    def joint(mm):
        client.append(['joint', mm.argument(0), mm.floats(mm.argument(1), 3), mm.floats(mm.argument(2), 3),
                       mm.floats(mm.argument(3), 3), mm.argument(4), mm.argument(5), mm.float_argument(6),
                       [mm.argument(i) for i in range(7, 14)]])
        return 0

    def sound(mm):
        ret = struct.unpack('<I', mm.uc.mem_read(mm.uc.reg_read(mm.x86.UC_X86_REG_ESP), 4))[0]
        client.append(['sound', mm.argument(0), mm.argument(1), mm.argument(2), ret - 5])
        return 0

    def action(mm):
        assert mm.argument(0) == CHAR and mm.argument(1) == skill
        client.append(['action', mm.argument(2), mm.argument(3)])
        return 0

    def pose(routine, count):
        def stub(mm):
            assert mm.argument(0) == CHAR and (count == 1 or mm.argument(1) == skill)
            client.append(['pose', routine])
            return 0
        return stub

    def bone(mm):
        # TransformByObjectBone(out, object, bone, 0), thiscall on the model: fill the caller's vector.
        client.append(['bone', mm.argument(1), mm.argument(2)])
        answered = sum(entry[0] == 'bone' for entry in client) - 1
        answer = s.bones[answered % 2] if skill == 234 else s.bone   # 234 asks two random bones
        mm.uc.mem_write(mm.argument(0), struct.pack('<3f', *answer))
        return (0, 16)

    def rand(mm):
        used = sum(entry[0] == 'rand' for entry in client)
        client.append(['rand'])
        return s.random[used % 2]

    def key_list(mm):
        # push_back on the source OBJECT's +0x1dc list: (end pointer, pointer to the pushed word)
        this = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)
        value = struct.unpack('<i', mm.uc.mem_read(mm.argument(1), 4))[0]
        client.append(['key-list', this, value & 0xffffffff])
        return (0, 8)

    def sine(mm):
        x = mm.float_argument(0)
        return mm.x87_return(fx.f32(math.sin(x)) if math.isfinite(x) else float('nan'))

    def cosine(mm):
        x = mm.float_argument(0)
        return mm.x87_return(fx.f32(math.cos(x)) if math.isfinite(x) else float('nan'))

    def arrows(mm):
        assert mm.argument(0) == CHAR
        client.append(['arrow'] + [mm.argument(i) for i in range(1, 6)])
        return 0

    def presence(mm):
        this = mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)
        answers = {(CHAR + OBJ + 0x358, 0x12): s.presence_18, (TCHAR + OBJ + 0x358, 2): s.presence_2}
        return (int(answers[(this, mm.argument(0))]), 4)

    def joint_search(mm):
        assert mm.argument(0) == 0x472 and mm.argument(1) == TCHAR + OBJ
        return int({4: s.joint_4, 9: s.joint_9}[mm.argument(2)])

    stubs = {fx.CREATE_EFFECT_WRAPPER: effect, fx.CREATE_JOINT: joint, fx.PLAY_BUFFER: sound,
             SKILL_ACTION: action, SET_MAGIC: pose(SET_MAGIC, 2), SET_ATTACK: pose(SET_ATTACK, 1),
             0x00966cc4: lambda mm: fx.CONTAINER, 0x00eaa8cf: lambda mm: (MODEL if s.model_present else 0, 4),
             0x012b678d: bone, 0x009c104e: lambda mm: (fx.CONTAINER, 4), 0x0106bdb7: lambda mm: int(s.mounted),
             0x01295ade: presence, 0x01553b41: joint_search, 0x009fd745: key_list,
             fx.SINE: sine, fx.COSINE: cosine, ARROWS: arrows, 0x01989721: rand}
    for address in Machine.EXITS:
        stubs[address] = lambda mm: 0
    if family in ('magic', 'position'):
        slots = {-0x18: CHAR, -0x10: CHAR + OBJ, -0x24: TCHAR, -0x14: TCHAR + OBJ, -0x1c: skill,
                 -0x28: skill, -0x80: s.source_key, -0x40: s.target_key, -0x64: s.source.index,
                 -0x44: s.target.index, -4: 0xffffffff}
        if family == 'position':
            slots = {-0x14: CHAR, -0x10: CHAR + OBJ, -0x18: skill, -0x24: skill, -0x28: s.packet_word,
                     -4: 0xffffffff}
        result = m.execute(entry, [], regions, stubs, frame=(0x1000, slots))
    else:
        result = m.execute(entry, [CHAR, CHAR + OBJ], regions, stubs,
                           frame=(0x1000, {-0x10: TCHAR + OBJ, -0x14: skill, -0x20: skill, -0x40: skill}))
    return result, client


def state_of(result, s):
    """What the body wrote: source AttackTime, hero AttackTime, target-index word, hero byte, frame."""
    regions = result['regions']
    source, target = regions['character'], regions['target']
    hero = source if s.source_is_hero else regions['hero']
    word = struct.unpack_from('<H', target, OBJ + 0x364)[0]
    frame = struct.unpack_from('<f', source, OBJ + 0xd0)[0]
    return dict(attack_time=source[0x21], hero_attack_time=hero[0x21],
                target_index=-1 if word == 0xffff else word, hero_byte=regions['hero-data'][5],
                frame_reset=int(frame == 0.0))


def compare(m, lib, cases, only=None, dump=False):
    report = pt.Report()
    rng = random.Random(20261115)
    for skill, (group, family, entry, _end) in ROWS.items():
        if only and skill not in only:
            continue
        bodies = [(0, family, entry)]
        if skill in ENDS:
            bodies.append((1,) + ENDS[skill][:2])
        if skill in POSITION_CASES:
            bodies.append((2,) + POSITION_CASES[skill][:2])
        for phase, fam, start in bodies:
            for n in range(cases):
                s = case_input(rng, skill, n)
                result, client = original(m, skill, s, fam, start)
                plan = Plan()
                supported = lib.mu_skill35_plan_cast(C.byref(s), phase, C.byref(plan)) if lib else 0
                mine = [normalized(plan.calls[i]) for i in range(plan.count)]
                error = None
                if dump and n < dump and not vc.ok(result):
                    print(json.dumps(dict(skill=skill, phase=phase, stopped=result['stopped'],
                                          error=result['error'], client=client), default=str))
                if vc.ok(result):
                    state = state_of(result, s)
                    mine_state = dict(attack_time=plan.attack_time, hero_attack_time=plan.hero_attack_time,
                                      target_index=plan.target_index, hero_byte=plan.hero_byte,
                                      frame_reset=plan.frame_reset)
                    if dump and n < dump:
                        print(json.dumps(dict(skill=skill, phase=phase, hero=s.source_is_hero, client=client,
                                              state=state), default=str))
                    if not vc._same_call(client, mine):
                        error = ('calls', client[:4], mine[:4], len(client), len(mine))
                    elif state != mine_state:
                        error = ('state', state, mine_state)
                report.add(f'{group}-{("receive", "end", "position")[phase]}',
                           bool(supported) and vc.ok(result) and error is None,
                           dict(case=n, skill=skill, error=error, stopped=result['stopped'],
                                machine_error=result['error']))
    return report


STEP_EDGES = [(0xa91, 0x8f, 0.999), (0xa91, 0x8f, 1.0), (0xa91, 0x8f, 5.0), (0xa91, 0x6e, 5.0), (0xa91, 0x6f, 5.0),
              (0xa91, 0x6f, 4.999), (0xa91, 0x132, 5.0), (0xa91, 0x133, 5.0), (0x7a5, 3, 5.0), (0x7a4, 3, 5.0),
              (0x9fc, 4, 5.0), (0x9fd, 4, 5.0), (0x7b7, 2, 5.0), (0x7b7, 5, 5.0), (0x7b7, 4, 4.999),
              (0xa91, 0x9a, float('nan')), (0xa91, 0x8f, float('nan')), (0xa91, 0x107, 6.0)]


def steps(m, lib, cases, report):
    """The attack-step dispatcher 0x013966ea for every admitted row: all select the default body."""
    rng = random.Random(350)
    for skill in ROWS:
        for n in range(cases):
            if n < len(STEP_EDGES):
                model, action, frame = STEP_EDGES[n]
            else:
                model = rng.choice([0xa91, 0x7b7, 0x7a5, 0x9fc])
                action = rng.choice([3, 4, 5, 0x6e, 0x6f, 0x8f, 0x9a, 0x9c, 0xd9, 0x106, 0x107, 0x132, 0x133])
                frame = rng.choice([0.0, 0.999, 1.0, 4.999, 5.0, 5.001, 6.0])
            time_in = n % 18
            char = am.undefined_region('character', CHAR, 0x3670)
            char.define(CHAR + 0x21, bytes([time_in]))
            char.define(CHAR + 0x26, struct.pack('<H', skill))
            char.define(CHAR + 0x146, bytes(2))
            obj = am.undefined_region('object', fx.OBJECTS, 0x400)
            for off, payload in [(0x5c, struct.pack('<i', model)), (0x2a, struct.pack('<H', action)),
                                 (0xd0, struct.pack('<f', frame))]:
                obj.define(fx.OBJECTS + off, payload)
            regions = [char, obj, am.defined_region('cutoff', 0x1cf1050, struct.pack('<i', 0)),
                       am.defined_region('hero', HERO_PTR, struct.pack('<I', CHAR)),
                       am.defined_region('hero-ptr', HERO_DATA_PTR, struct.pack('<I', fx.HERO_DATA)),
                       am.defined_region('hero-equipment', fx.HERO_DATA + 0x1c94, bytes(4))]
            seen = []
            record = lambda mm: seen.append(mm.argument(0)) or 0
            stubs = {fx.CREATE_EFFECT_WRAPPER: record, fx.CREATE_JOINT: record, fx.CREATE_PARTICLE: record,
                     fx.PLAY_BUFFER: record, 0x01989721: record, 0x013a5658: lambda mm: 0,
                     0x00ac3bf7: lambda mm: (fx.CONTAINER, 4), 0x0095f998: lambda mm: fx.CONTAINER,
                     0x00bb1c32: lambda mm: skill}
            result = m.execute(0x013966ea, [CHAR, fx.OBJECTS], regions, stubs)
            mine = C.c_uint8(time_in)
            limit = lib.mu_skill35_step(skill, model, action, frame, C.byref(mine))
            equal = vc.ok(result) and not seen and result['regions']['character'][0x21] == mine.value and \
                struct.unpack('<i', result['regions']['cutoff'])[0] == limit
            report.add('step', equal, dict(skill=skill, case=n, model=model, action=action, frame=str(frame),
                                           seen=seen, stopped=result['stopped'], machine_error=result['error']))


def buff_ends(m, lib, cases, report):
    """End bodies of the learned buffs 27 / 28 on the same authored records as group E's ends."""
    rng = random.Random(2728)
    for skill, (entry, _end) in BUFF_ENDS.items():
        for n in range(cases):
            s = case_input(rng, skill, n)
            result, client = original(m, skill, s, 'target', entry)
            plan = Plan()
            supported = lib.mu_skill35_buff_end(C.byref(s), C.byref(plan))
            mine = [normalized(plan.calls[i]) for i in range(plan.count)]
            equal = bool(supported) and vc.ok(result) and vc._same_call(client, mine)
            report.add('buff-end', equal, dict(skill=skill, case=n, client=client[:2], mine=mine[:2],
                                               stopped=result['stopped'], machine_error=result['error']))


def links(m, lib, report):
    """The link selector's type switch 0x0137eefc..0x0137f5f4 for every model type of the model range,
    and the slot index 0x013a5658. The fragment's routine has no SEH frame, so the frame harness's
    restored-handler check does not apply to it; every other machine check does.

    The first default helper 0x00df230b runs as client code. The second, 0x00d9013e, is a stub that
    answers from its own two compares (static reading): it is a different setter, not recovered here."""
    for model_type in list(range(0x700, 0xb40)) + [0, 1, 0x1a1, 0x412, 0xfff, 0x10e6, 0x7fffffff, -1]:
        region = am.undefined_region('character', CHAR, 0x3670)
        region.define(CHAR + LINK_OFFSET, b'\xee')
        region.define(CHAR + LINK_OFFSET + LINK_STRIDE, b'\xee')
        asked = []

        def other(mm):
            asked.append(mm.argument(1))
            return int(mm.argument(1) in (0x7ee, 0xa2f))
        result = m.execute(LINK_SWITCH, [CHAR, model_type & 0xffffffff], [region], {LINK_OTHER: other},
                           frame=(0x40, {-4: CHAR + OBJ}))
        ran = all(value for name, value in result['checks'].items() if name != 'seh_restored')
        mine = (C.c_uint8 * 2)(0xee, 0xee)
        mask = lib.mu_link_bones(model_type, mine)
        data = result['regions']['character']
        theirs = (data[LINK_OFFSET], data[LINK_OFFSET + LINK_STRIDE])
        expected = 4 if asked and asked[0] in (0x7ee, 0xa2f) else (theirs[0] != 0xee) | ((theirs[1] != 0xee) << 1)
        report.add('links', ran and tuple(mine) == theirs and mask == expected,
                   dict(type=model_type, theirs=theirs, mine=tuple(mine), mask=mask, expected=expected,
                        stopped=result['stopped'], machine_error=result['error']))
    for model in (0xa91, 0xa90, 0x7b7, 0):
        for action in (0, 0x72, 0x73, 0x74, 0x75, 0x9e, 0x173, 0xffff):
            region = am.undefined_region('object', fx.OBJECTS, 0x400)
            region.define(fx.OBJECTS + 0x5c, struct.pack('<i', model))
            region.define(fx.OBJECTS + 0x2a, struct.pack('<H', action))
            result = m.execute(LINK_INDEX, [fx.OBJECTS], [region], {})
            report.add('link-index', vc.ok(result) and result['eax'] == lib.mu_link_index(model, action),
                       dict(model=model, action=action, eax=result['eax'], stopped=result['stopped']))


def controls(m, lib, report):
    """SkillAction's own selection and the authored admission controls."""
    for character in (CHAR, 0):
        for mounted in (0, 1):
            for flag in (0, 1):
                for action, alternative in ((0x9c, 0x11d), (0x9a, 0x12c), (0xd9, 0x125), (0x107, 0xffffffff),
                                            (0x106, 0xffffffff)):
                    region = am.undefined_region('character', CHAR, 0x3670)
                    region.define(CHAR + 0x31e8, bytes([flag]))
                    seen = []

                    def start(mm):
                        seen.append(['start', mm.argument(0), mm.argument(1), mm.argument(2)])
                        return 0

                    def set_action(mm):
                        seen.append(['set', mm.argument(0), mm.argument(1)])
                        return 0
                    stubs = {0x01392afd: start, 0x009c104e: lambda mm: (fx.CONTAINER, 4),
                             0x0106bdb7: lambda mm: mounted, 0x012affa4: set_action}
                    result = m.execute(SKILL_ACTION, [character, 740, action, alternative], [region], stubs)
                    signed = alternative - (1 << 32) if alternative >> 31 else alternative
                    mine = lib.mu_skill35_action(action, signed, mounted, flag)
                    expected = [] if not character else [['start', CHAR, 740, 0], ['set', CHAR + OBJ, mine & 0xffffffff]]
                    report.add('action', vc.ok(result) and seen == expected,
                               dict(character=character, mounted=mounted, flag=flag, action=action, seen=seen,
                                    stopped=result['stopped'], machine_error=result['error']))
    groups = {skill: ' ABCDE'.index(row[0]) for skill, row in ROWS.items()}
    dk = {740, 1125, 1126, 1127, 1500, 1502, 1503}
    elf = set(ROWS) - {1500, 1502, 1503}
    for skill in sorted(ROWS) + [0, 24, 46, 76, 232, 235, 416, 426, 427, 441, 723, 801, 810, 813, 1129, 1222, 1501,
                                 2040, 2043, 2044, 9999]:
        for cls in (0, 1, 2, 3, 0x11, 0x12, 0x21, 0x42):
            nibble = cls & 15
            expected = groups[skill] if (nibble == 1 and skill in dk) or (nibble == 2 and skill in elf) else 0
            report.add('select', lib.mu_skill35_select(skill, cls) == expected, dict(skill=skill, cls=cls))
        report.add('select', bool(lib.mu_skill35_position(skill)) == (skill in ROWS and ROWS[skill][1] == 'position'),
                   dict(skill=skill, position=True))
        for index in (0, 13, 149, 150, 159):
            entries = (C.c_uint16 * 160)()
            entries[index] = skill
            for count in (-1, 0, index, index + 1, 160):
                actual = bool(lib.mu_skill35_learned(skill, entries, count))
                report.add('learned', actual == (skill in ROWS and index < min(count, 150)),
                           dict(skill=skill, index=index, count=count))
    report.add('learned', not lib.mu_skill35_learned(740, None, 150), dict(null_list=True))
    rng = random.Random(35)
    for skill in sorted(ROWS):
        s = case_input(rng, skill, 0)
        plan = Plan()
        for phase in (-1, 2, 3):
            refused = not lib.mu_skill35_plan_cast(C.byref(s), phase, C.byref(plan))
            report.add('refusal', refused == (phase != 2 or skill not in POSITION_CASES) and (not refused or plan.count == 0),
                       dict(skill=skill, phase=phase))
        report.add('refusal', bool(lib.mu_skill35_plan_cast(C.byref(s), 1, C.byref(plan))) == (ROWS[skill][0] == 'E'),
                   dict(skill=skill, end=True))
        s.base = 0 if skill != 0 else 1       # an alias pair is never admitted through its base
        report.add('refusal', not lib.mu_skill35_plan_cast(C.byref(s), 0, C.byref(plan)) and plan.count == 0,
                   dict(skill=skill, alias=True))
        s.base, s.mounted = skill, 1          # the mount position service is outside admission
        refused = not lib.mu_skill35_plan_cast(C.byref(s), 0, C.byref(plan))
        report.add('refusal', refused == (ROWS[skill][0] == 'B') and (not refused or plan.count == 0),
                   dict(skill=skill, mounted=True))
    for skill in (0, 46, 76, 232, 235, 426, 427, 723, 813, 1501, 2040, 2043, 2044, 9999):
        s = case_input(rng, skill, 0)
        plan = Plan()
        report.add('refusal', not lib.mu_skill35_plan_cast(C.byref(s), 0, C.byref(plan)) and plan.count == 0,
                   dict(skill=skill, outside=True))


MUTANTS = [
    ('0x9a, 0x12c', '0x9a, 0x12d'), ('0x608, 0,', '0x608, 1,'),
    ('0x4b3, 0, KEY_DEFAULT, 0, 0x2e1, 0x01257627', '0x4b3, 0, KEY_DEFAULT, 0, 0x2e1, 0x01257628'),
    ('0x4b3, 2,', '0x4b3, 1,'), ('KEY_DEFAULT, 0, 0, 0, F_TIME}', 'KEY_DEFAULT, 0, 0, 0, 0}'),
    ('{727, GROUP_A, ELF, 0, GUARD_NOT_HERO', '{727, GROUP_A, ELF, 0, GUARD_NONE'),
    ('0x70e, 0, KEY_TARGET', '0x70e, 0, KEY_SOURCE'),
    ('0x107, -1, 0x70a, 0, KEY_SOURCE', '0x107, -1, 0x70a, 1, KEY_SOURCE'),
    ('KEY_SOURCE, 0, 0, 0, F_SCALE_ONE', 'KEY_SOURCE, 0, 0, 0, 0'),
    ('0x708, 0, KEY_PACKET, 0, 0x55f, 0x0125f899, 0', '0x708, 0, KEY_DEFAULT, 0, 0x55f, 0x0125f899, 0'),
    ('0x7ff, 0x55f, 0x0125f806, F_SKILL_WORD', '0x7ff, 0x55f, 0x0125f806, 0'),
    ('KEY_PACKET, 0x7ff,', 'KEY_PACKET, 0x7fc,'),
    ('0x69d, 1, KEY_DEFAULT, 0, 0, 0, F_INDEX}', '0x69d, 1, KEY_DEFAULT, 0, 0, 0, 0}'),
    ('F_INDEX | F_BONE_TARGET', 'F_INDEX'),
    ('0x69e, 0, KEY_DEFAULT, 0, 0, 0, F_ACTION_FIRST', '0x69e, 0, KEY_DEFAULT, 0, 0, 0, 0'),
    ('0x635, 0, KEY_DEFAULT, 0x8263', '0x635, 0, KEY_DEFAULT, 0x8264'),
    ('0x8021, 1, KEY_DEFAULT, 0x593', '0x8021, 1, KEY_DEFAULT, 0x594'),
    ('{430, GROUP_D, ELF, 0, GUARD_NOT_HERO', '{430, GROUP_D, ELF, 0, GUARD_NONE'),
    ('0x106, -1, 0x8021, 3', '0x106, -1, 0x8021, 1'),
    ('(int32_t)(int16_t)s->hero_key == (int32_t)s->source_key', '(int32_t)s->hero_key == (int32_t)s->source_key'),
    (' || s->source_key == s->target_key', ''), ('p->hero_byte = 10', 'p->hero_byte = 11'),
    ('c->light[0] = c->light[1] = 0.7f', 'c->light[0] = c->light[1] = 0.8f'),
    ('if (!s->model_present) return 1;', ''), ('c->range = 0x11;', 'c->range = 0x12;'),
    ('memcpy(c->position, s->bone, sizeof c->position);', ''),
    ('+ 30.0f) + s->target.position[2]', '+ 31.0f) + s->target.position[2]'), ('n < 2; ++n', 'n < 1; ++n'),
    ('c->light[0] = c->light[1] = c->light[2] = 1.0f;\n        c->owner = MU_SKILL35_NO_OWNER;',
     'c->owner = MU_SKILL35_NO_OWNER;'),
    ('{0.0f, -220.0f, 130.0f}', '{0.0f, -220.0f, 131.0f}'),
    ('offset[k] + s->source.position[k]', 'offset[k] + s->target.position[k]'),
    ('r->subtype == 1 ? 1.0f : 0.92f', 'r->subtype == 1 ? 1.0f : 0.9f'),
    ('p->attack_time = 1; p->hero_attack_time = 1;', 'p->attack_time = 1;'),
    ('r->flags & F_ACTION_FIRST ? &s->source : &s->target', '&s->target'),
    ('s->source.class_word != 0x4d', 's->source.class_word != 0x4c'),
    ('{ pose(p, r); p->frame_reset = 1; }', '{ pose(p, r); }'), ('if (s->presence_18) return;', ''),
    ('if (r->skill == 2027 && !s->flag_7) return;', ''),
    ('(s->presence_2 && (s->joint_4 || s->joint_9))', '(s->presence_2 && s->joint_4)'),
    ('n < 5; ++n', 'n < 4; ++n'), ('c->scale = 20.0f', 'c->scale = 10.0f'),
    ('(int16_t)s->target_word', '(uint16_t)s->target_word'),
    ('mounted && !flag_31e8 && alternative != -1', 'mounted && alternative != -1'),
    ('i < count && i < 150', 'i < count && i < 151'), ('!(r->classes & cls)', '!(r->classes | cls)'),
    ('if (s->mounted) return 0;', ''),
    ('request(p, MU_SKILL35_KEY_LIST, (int16_t)s->target.key, 0)', 'request(p, MU_SKILL35_KEY_LIST, s->target.key, 0)'),
    ('if (s->source_is_hero) p->hero_attack_time = p->attack_time;', ''),
    ('action == 0x8f && frame >= 1.0f', 'action == 0x8f && frame > 1.0f'),
    ('action >= 0x6f && action < 0x133', 'action >= 0x6f && action < 0x132'),
    ('model >= 0x7a5 && model < 0x9fd', 'model >= 0x7a5 && model < 0x9fc'),
    ('action >= 3 && action <= 4', 'action >= 3 && action <= 5'),
    ('else if (frame >= 5.0f &&', 'else if (frame > 5.0f &&'),
    ('return 15;   /* the cutoff', 'return 14;   /* the cutoff'),
    ('s->skill == 27 ? 2027 : 2026', 's->skill == 27 ? 2026 : 2027'),
    ('(s->skill != 27 && s->skill != 28)', '(s->skill != 27 && s->skill != 26)'),
]
LINK_MUTANTS = [
    ('{0x7a5, {42, 33}, 3}', '{0x7a5, {33, 42}, 3}'), ('{0x7ce, {23, 0}, 1}', '{0x7ce, {23, 0}, 3}'),
    ('{0x950, {43, 0}, 1}', '{0x951, {43, 0}, 1}'), ('{0x7e9, {60, 60}, 3}', '{0x7e9, {60, 61}, 3}'),
    ('{0x94f, {32, 68}, 3}', '{0x94f, {32, 67}, 3}'), ('type == 0x7ee || type == 0xa2f', 'type == 0x7ee'),
    ('bones[0] = 33; bones[1] = 42;', 'bones[0] = 42; bones[1] = 33;'),
    ('if (LINKS[i].mask & MU_LINK_SLOT1) bones[1]', 'if (LINKS[i].mask & MU_LINK_SLOT0) bones[1]'),
    ('action == 0x73 || action == 0x74', 'action == 0x73 || action == 0x75'),
    ('model == 0xa91 && (action', 'model != 0xa91 && (action'),
]
SOURCES = ['reconstructed/combat/catalogue_skill_fx.c', 'reconstructed/combat/link_selector.c',
           'reconstructed/record-math/record_math.c']
FLAGS = ['clang', '-std=c11', '-O2', '-shared', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-I',
         str(ROOT / 'reconstructed/combat')]


def run(cases, mutants, only=None, dump=0):
    start = time.monotonic()
    text, data = pins.TEXT.read(), pins.DATA.read()
    path = ROOT / f'reconstructed/combat/libcombat.{fx.SUFFIX}'
    lib = load(path) if not dump else None
    m = Machine(text, data)
    report = compare(m, lib, cases, only, dump)
    if lib and not only:
        steps(m, lib, max(len(STEP_EDGES), cases // 4), report)
        buff_ends(m, lib, cases, report)
        links(m, lib, report)
        controls(m, lib, report)
    out = dict(families=report.families, mutants=[], text_sha256=pins.TEXT.sha256, data_sha256=pins.DATA.sha256,
               bodies={str(skill): dict(group=row[0], family=row[1], start=hex(row[2]), end=hex(row[3]),
                                        sha256=hashlib.sha256(text[row[2] - 0x401000:row[3] - 0x401000]).hexdigest())
                       for skill, row in ROWS.items()})
    out['all_equal'] = all(f['cases'] == f['equal'] for f in report.families.values())
    if mutants and out['all_equal']:
        sources = [(ROOT / name).read_text().replace('"../record-math/record_math.h"',
                                                     f'"{ROOT}/reconstructed/record-math/record_math.h"')
                   for name in SOURCES[:2]]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'combat').mkdir()
            dest = [tmp / 'combat' / Path(name).name for name in SOURCES[:2]]
            planted = [(0, old, new) for old, new in MUTANTS] + [(1, old, new) for old, new in LINK_MUTANTS]
            for index, (which, old, new) in enumerate(planted):
                assert sources[which].count(old) == 1, old
                for k in (0, 1):
                    dest[k].write_text(sources[k].replace(old, new) if k == which else sources[k])
                path = tmp / f'm{index}.{fx.SUFFIX}'
                subprocess.run(FLAGS + [str(dest[0]), str(dest[1]), str(ROOT / SOURCES[2]), '-lm', '-o', str(path)],
                               check=True, capture_output=True)
                mutant = load(path)
                r = compare(m, mutant, min(cases, 40))
                steps(m, mutant, len(STEP_EDGES), r)
                buff_ends(m, mutant, min(cases, 40), r)
                links(m, mutant, r)
                controls(m, mutant, r)
                failures = [f for f in r.families.values() if f['equal'] != f['cases']]
                stops = sum(bool(e.get('stopped')) for f in failures for e in f['first_failures'])
                out['mutants'].append(dict(index=index, detected=sum(f['cases'] - f['equal'] for f in failures),
                                           stopped=stops))
                path.unlink()
    out['all_mutants_caught'] = (not mutants or len(out['mutants']) == len(MUTANTS) + len(LINK_MUTANTS)) and all(
        m['detected'] and not m['stopped'] for m in out['mutants'])
    out['cases'] = sum(f['cases'] for f in report.families.values())
    out['seconds'] = time.monotonic() - start
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=200)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--only', type=lambda v: [int(x) for x in v.split(',')])
    p.add_argument('--dump', type=int, default=0)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    if a.cases < 1:
        p.error('positive --cases required')
    out = run(a.cases, a.mutations, a.only, a.dump)
    if a.output:
        a.output.write_text(json.dumps(out, indent=2) + '\n')
    if not a.dump:
        print(json.dumps(out, indent=2))
    raise SystemExit(not (out['all_equal'] and out['all_mutants_caught']))
