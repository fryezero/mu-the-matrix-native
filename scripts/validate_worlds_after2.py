#!/usr/bin/env python3
"""RENDER-WORLDS-AFTER2 instruction comparisons (docs/research/client-worlds-after2.md).

Families (compiled C via ctypes against the pinned original under the strict Unicorn machine):
  custom_<world>   the class's custom render slot 0x38 (thiscall(handler, object, model, 0), returns handled):
                   world test, per-type RenderBody/RenderMesh calls with their eight arguments, the model's
                   StreamMesh byte +0x94 and body colour +0x54 at each call, the object and model bytes after the
                   call, PlaySpeed stores into the model's action table (+0x30) and the answer.
  after_<world>    the class's after render slot 0x3c, the same comparison without an answer.
  bitmaps          the class bitmap loaders (slot 0x24) as LoadBitmap 0x0185baac sees them, and every bitmap a
                   compared slot binds to a model mesh resolved through mu_world_slot_bitmap.
The first 301 cases of a slot family sweep the object type 0..300 (the world manager's range); the rest draw the
class's case types. Leaves recorded: RenderBody 0x00966def, RenderMesh 0x00966e4a; the CRT sin/cos and the wave
0x0185bdc4 run as client code; glPushMatrix/glPopMatrix return at once.
"""
import argparse, ctypes as C, hashlib, json, random, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_particles as vp

ROOT = Path(__file__).resolve().parents[1]
# world: (custom slot 0x38, after slot 0x3c, case types)
CLASSES = {
    91: (0xd6c427, 0xd6d3d7, [7, 8, 9, 0xe, 0xf, 0x10, 0x11, 0x16, 0x1a, 0x1b, 0x1c, 0x1e, 0x21, 0x24, 0x2f, 0x30,
                              0x33, 0x34, 0x3b, 0x3c, 0x3d, 0x3e, 0x41, 0x42, 0x44, 0x47, 0x48, 0x4c, 0x4d, 0x4e, 0x4f,
                              0x57, 0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x64, 0x65, 0x66, 0x6b, 0x6d, 0x6e]),
    113: (0xe347a8, 0xe3628c, [0x14, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x32, 0x34,
                               0x35, 0x66, 0x68, 0x69, 0x6a, 0x6b, 0x6c, 0x72, 0x7e, 0x80, 0x84, 0x8a, 0x8b, 0x8d]),
    135: (0xe3ae5e, 0xe3c739, [0x12, 0x15, 0x16, 0x17, 0x1b, 0x29, 0x5c, 0x5d, 0x61, 0x6b, 0x74, 0x78, 0x7b, 0x82,
                               0x83, 0x84, 0x85, 0x87, 0x89, 0x8a]),
    136: (0xd94eef, 0xd97384, [0x12, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1b, 0x29, 0x5c, 0x5e, 0x6b, 0x6c, 0x74, 0x78,
                               0x7a, 0x7b, 0x7c, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x99, 0x9a, 0x9c,
                               0x9f, 0xb3, 0xb5, 0xc1, 0xc2]),
    137: (0xe092f4, 0xe0ab2a, [1, 2, 7, 8, 0xa, 0xc, 0xd, 0xe, 0xf, 0x10, 0x1b, 0x1c, 0x1f, 0x21, 0x23, 0x24, 0x26,
                               0x3a, 0x3b, 0x3e, 0x3f, 0x4c, 0x57, 0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f,
                               0x60, 0x64, 0x65, 0x6b, 0x6d, 0x6e, 0x7c]),
    138: (0xe05f25, 0xe0709e, [0x1d, 0x1e, 0x1f, 0x20, 0x25, 0x2d, 0x4f, 0x5a, 0x5d, 0x5f, 0x90, 0x94, 0x9b, 0xa3,
                               0xaa, 0xab, 0xac, 0xad, 0xae, 0xb1]),
    140: (0xd9a2ed, 0xd9ac50, [0x11, 0x12, 0x1f, 0x44, 0x46, 0x50, 0x5c, 0x60, 0x61, 0x62]),
    142: (0xe677a9, 0xe68c6a, [1, 3, 0xb, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3e, 0x42, 0x6b, 0x71, 0x73, 0x74, 0x75,
                               0x76, 0x77, 0x78, 0x7d, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa2, 0xa3, 0xa5, 0xa7, 0xaa,
                               0xab, 0xb2, 0xb3, 0xc3, 0xc4, 0xc5, 0xc6]),
}
BODY, MESH = 0x966def, 0x966e4a
STREAM, COLOR, SPEED = 0x017ffef3, 0x54, 0x00eaaa44
ACTION_COUNT = 64


def slot_bodies(text):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md, out = Cs(CS_ARCH_X86, CS_MODE_32), {}
    for w, (custom, after, _) in CLASSES.items():
        for name, start in (('custom', custom), ('after', after)):
            end = start
            for ins in md.disasm(text[start - am.TEXT_BASE:start - am.TEXT_BASE + 0x2000], start):
                end = ins.address + ins.size
                if ins.mnemonic == 'ret' and text[end - am.TEXT_BASE] in (0xcc, 0x55):
                    break
            out[f'{name}_{w}'] = (start, end)
    return out


class Library(v.Library):
    def __init__(self, path):
        super().__init__(path)
        d, P, I, F, L = self.dll, C.c_void_p, C.c_int32, C.c_float, C.POINTER(v.Log)
        d.mu_class_custom.argtypes = [I, P, P, I, I, F, P, L]
        d.mu_class_after.argtypes = [I, P, P, I, I, F, P, L]
        d.mu_class_after.restype = None
        d.mu_class_premove.argtypes = [I, P, I, I, I, v.RAND_FN, P, L]
        d.mu_world_slot_bitmap.argtypes = [I, I, C.POINTER(C.c_char_p), C.POINTER(C.c_uint32), C.POINTER(C.c_uint32)]
        d.mu_world_slot_bitmaps.argtypes = [I, I, C.POINTER(C.c_int32)]


def slot_object(g, typ):
    o = bytearray(v.poison_object(g))
    v.put_i(o, 0x5c, typ)
    o[0xa] = g.choice([0, 0, 0, 0, 1, 2])
    struct.pack_into('<H', o, 0x2a, g.choice([0, 0, 1, 2, g.randrange(0, ACTION_COUNT)]))
    v.put_f(o, 0xd0, v.f32(g.choice([0.0, 1.0, 19.5, 29.0, g.uniform(0, 40)])))
    v.put_f(o, 0xdc, v.f32(g.choice([1.0, 0.5, g.uniform(0, 1)])))
    v.put_i(o, 0x74, g.choice([-1, 0, 1, 2, 3, g.randrange(-2**31, 2**31)]))
    v.put_i(o, 0x68, g.choice([-1, -2, 0, 1, 2, 3, 4]))
    v.put_i(o, 0x60, g.choice([0, 1, 90, g.randrange(-1000, 1000)]))
    v.put_f(o, 0xc8, v.f32(g.choice([0.5, 0.7, 1.0, g.uniform(0, 1.5)])))
    for off in (0xa8, 0xac, 0xb0):
        v.put_f(o, off, v.f32(g.choice([0.0, 1.0, g.uniform(-2, 2)])))
    return o


MESHES, SUBS = 0x41006000, 0x41007000


class SlotModel(C.Structure):
    _fields_ = [('mesh_count', C.c_int32), ('sub_flag', C.POINTER(C.c_int16))]


def slot_meshes(g):
    """Model +0x24 mesh count, +0x28 mesh array (0x20 each, +0x1c texture sub record or 0)."""
    count = g.choice([0, 1, 3, 6, 12])
    subs = [g.choice([-1, -1, 0, 1, 1, 2]) for _ in range(count)]
    array, records = bytearray(0x20 * 16), bytearray(16 * 16)
    for k, sub in enumerate(subs):
        struct.pack_into('<I', array, 0x20 * k + 0x1c, 0 if sub < 0 else SUBS + 16 * k)
        if sub >= 0:
            records[16 * k] = sub
    return count, subs, array, records


def slot_model(g, count=0):
    b = bytearray(g.getrandbits(8) for _ in range(0x100))
    struct.pack_into('<h', b, 0x24, count)
    struct.pack_into('<I', b, 0x28, MESHES)
    struct.pack_into('<I', b, 0x30, v.ACTIONS)
    struct.pack_into('<H', b, 0xa8, g.choice([0, 0, 1, g.randrange(0, 0x10000)]))
    v.put_f(b, 0xac, v.f32(g.choice([0.0, 1.0, 1.5, 28.5, 28.9, 29.0, 30.0, g.uniform(-5, 35)])))
    b[0x94] = g.choice([0xff, 0, 1, g.randrange(256)])
    v.put_f(b, 0x54, *(v.f32(g.uniform(0, 1.5)) for _ in range(3)))
    return b


def native_calls(events, model):
    """Body/Mesh tuples as the client recorder sees them: arguments, then the StreamMesh byte and colour."""
    stream, colour, calls, speeds = model[0x94], list(struct.unpack_from('<3I', model, 0x54)), [], []
    for e in events:
        call, args = e[0], list(e[2:])
        if call == STREAM:
            stream = args[0] & 0xff
        elif call == COLOR:
            colour = args[:3]
        elif call == SPEED:
            speeds.append(args)
        elif call in (BODY, MESH):
            calls.append((call,) + tuple(args[:8]) + (stream,) + tuple(colour))
    return calls, speeds


def slot_family(machine, lib, g, cases, world_cls, after):
    custom, after_addr, types = CLASSES[world_cls]
    t = v.Tally(('after_' if after else 'custom_') + str(world_cls))
    for n in range(cases):
        world = world_cls if g.random() < 0.9 else g.choice([world_cls - 1, world_cls + 1, 0, 128, 137, 140])
        # the world manager calls the slots for types 0..300 only (0x00ea2f07 / 0x00ea306c)
        typ = n if n <= 300 else g.choice(types) if g.random() < 0.9 else g.randrange(0, 301)
        count, subs, array, records = slot_meshes(g)
        o, b = slot_object(g, typ), slot_model(g, count)
        actions = bytearray(g.getrandbits(8) for _ in range(16 * ACTION_COUNT))
        time = v.f32(g.choice([0.0, g.uniform(0, 100000), g.uniform(0, 1e7), g.uniform(1e7, 3e9)]))
        calls = []

        def recorder(address):
            def stub(m):
                model = bytes(m.uc.mem_read(v.MODEL, 0x100))
                calls.append((address,) + tuple(m.argument(k) for k in range(8)) + (model[0x94],) +
                             struct.unpack_from('<3I', model, 0x54))
                return (0, 32)
            return stub
        stubs = {BODY: recorder(BODY), MESH: recorder(MESH)}
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                                              am.defined_region('model', v.MODEL, bytes(b)),
                                              am.defined_region('actions', v.ACTIONS, bytes(actions)),
                                              am.defined_region('meshes', MESHES, bytes(array), writable=False),
                                              am.defined_region('subs', SUBS, bytes(records), writable=False),
                                              am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                                              am.defined_region('fake', v.FAKE, v.fake_object(), writable=False)])
        start = after_addr if after else custom
        result = v.run(machine, start, [v.OBJECTS, v.MODEL, 0], regions, stubs, ecx=v.FAKE, cleanup=12)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': typ}, stop)
            continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        cb = C.create_string_buffer(bytes(b), 0x100)
        log = v.new_log()
        flags = (C.c_int16 * 16)(*(subs + [0] * (16 - len(subs))))
        model = SlotModel(count, flags)
        if after:
            lib.dll.mu_class_after(world_cls, co, cb, 0, world, time, C.byref(model), C.byref(log))
            answer, client = 0, 0
        else:
            answer = 1 if lib.dll.mu_class_custom(world_cls, co, cb, 0, world, time, C.byref(model),
                                                  C.byref(log)) else 0
            client = result['eax'] & 0xff
        mine, speeds = native_calls(v.log_events(log), b)
        expect_actions = bytearray(actions)
        for typ_, act, value in speeds:
            struct.pack_into('<I', expect_actions, 16 * act + 4, value)
        model_c = bytearray(cb.raw[:0x100])
        named = (C.c_int32 * 4)()
        listed = set(named[:lib.dll.mu_world_slot_bitmaps(world_cls, typ, named)])
        textures = {c[8] for c in calls if c[8] != 0xffffffff}
        bitmaps_ok = all(x in listed for x in textures if 0x7000 <= x < 0x9000)
        if textures:
            t.count('bitmap meshes')
        ok = (bitmaps_ok and calls == mine and client == answer and result['regions']['object'] == co.raw[:v.OBJ_SIZE] and
              result['regions']['model'] == bytes(model_c) and result['regions']['actions'] == bytes(expect_actions))
        t.count(f'answer {client}')
        t.count('drawn' if calls else 'no draw')
        if world == world_cls and typ in types:
            t.count('case types')
        t.add(ok, {'case': n, 'world': world, 'type': hex(typ), 'client': [tuple(hex(x) for x in c) for c in calls[:6]],
                   'native': [tuple(hex(x) for x in c) for c in mine[:6]], 'answer': (client, answer),
                   'object': result['regions']['object'] == co.raw[:v.OBJ_SIZE],
                   'model': result['regions']['model'] == bytes(model_c),
                   'actions': result['regions']['actions'] == bytes(expect_actions),
                   'bitmaps': (sorted(textures), sorted(listed))})
    return t


PREMOVE = {69: 0xdd2fae, 70: 0xdd886b, 71: 0xdde51d, 72: 0xde5441, 79: 0xe6dd0a, 80: 0xe189af, 81: 0xe189af,
           122: 0xe5e1a4}
PLAY_BUFFER, HANDLER69, VTABLE69 = 0xa6ac96, 0x41008000, 0x1aa7dd4


def premove_family(machine, lib, g, cases, cls):
    """Synthetic objects and handler state only: worlds 69..72 and 80/81 have no original capture."""
    t = v.Tally(f'premove_{cls}')
    for n in range(cases):
        world = g.choice([cls, cls, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4a, 0x44, 0x4b, 122, 0]) if cls <= 72 else \
            cls if g.random() < 0.8 else g.choice([0, 79, 80, 122, 140])
        null = cls not in (80, 81) and g.random() < 0.05
        o = bytearray(v.poison_object(g))
        types = {80: [0x3a, 0x42, 0x3b, 0], 81: [0x3a, 0x42, 0x41], 122: [0x1a, 0x83, 0x84, 0x85, 0xa1, 0xa8, 0xa9, 7]}
        v.put_i(o, 0x5c, g.choice(types.get(cls, [0, 1])) if g.random() < 0.85 else g.randrange(0, 301))
        struct.pack_into('<H', o, 0x2a, g.choice([0, 1, 2]))
        tx, ty = g.choice([0xa2, 0xa3, 0xb0, 0xca, 0xcb, g.randrange(0, 256)]), g.choice([-1, 0, 0x27, 0x28, g.randrange(0, 256)])
        v.put_f(o, 0x158, v.f32(tx * 100 + g.uniform(0, 99.9)), v.f32(ty * 100 + g.uniform(0, 99.9)))
        state = g.choice([0, 1, 2, 3, 4, -1])
        handler = bytearray(0x40)
        struct.pack_into('<I', handler, 0, VTABLE69)
        struct.pack_into('<i', handler, 0x14, state)
        seed = g.randrange(2**32)
        a, b = v.MsvcRand(seed), v.MsvcRand(seed)
        calls = []

        def play(m):
            arg1 = m.argument(1)
            calls.append((m.argument(0), 1 if arg1 == v.OBJECTS and arg1 else arg1, m.argument(2)))
            return 0
        stubs = {PLAY_BUFFER: play, 0x1989721: lambda m: a(), 0xdd8a3c: lambda m: HANDLER69}
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o), writable=False),
                                              am.defined_region('handler69', HANDLER69, bytes(handler), writable=False),
                                              am.defined_region('fake', v.FAKE, v.fake_object(), writable=False)])
        ecx = HANDLER69 if cls == 69 else v.FAKE
        result = v.run(machine, PREMOVE[cls], [0 if null else v.OBJECTS], regions, stubs, ecx=ecx, cleanup=4)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world}, stop)
            continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        log = v.new_log()
        lib.dll.mu_class_premove(cls, None if null else co, 0, world, state, v.RAND_FN(lambda c: b()), None,
                                 C.byref(log))
        mine = [tuple(e[2:5]) for e in v.log_events(log)]
        t.count('sound' if calls else 'quiet')
        t.add(calls == mine and a.seed == b.seed, {'case': n, 'world': world, 'state': state, 'null': null,
                                                    'type': struct.unpack_from('<i', o, 0x5c)[0], 'client': calls,
                                                    'c': mine})
    return t


LOAD_BITMAP = 0x185baac
LOADERS = {128: 0xd5cede, 129: 0xd5eb7e, 130: 0xd602c2, 135: 0xe3a3bc, 136: 0xd93713, 142: 0xe67447}
TABLE_IDS = [0x802c, 0x802d, 0x802e, 0x8245, 0x8246, 0x8247, 0x8249, 0x824a, 0x814f, 0x8150, 0x8151, 0x8152,
             0x82de, 0x82df, 0x8341, 0x8342, 0x8343, 0x8538]


def load_sites(text, data, index):
    """LoadBitmap sites of `index`: push 0/1 (bytes), wrap, filter, index, path; call 0x0185baac."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md, out, p = Cs(CS_ARCH_X86, CS_MODE_32), [], 0
    pat = b'\x68' + struct.pack('<I', index)
    while (p := text.find(pat, p)) >= 0:
        a = am.TEXT_BASE + p
        ins = list(md.disasm(text[p:p + 20], a))
        before = [i for i in md.disasm(text[p - 16:p], a - 16) if i.mnemonic == 'push']
        if len(ins) >= 3 and ins[1].mnemonic == 'push' and ins[2].mnemonic == 'call' and \
                int(ins[2].op_str, 16) == LOAD_BITMAP and len(before) >= 2:
            path = int(ins[1].op_str, 16)
            name = data[path - am.DATA_BASE:path - am.DATA_BASE + 96].split(b'\0')[0].decode('latin1')
            out.append((a, name, int(before[-1].op_str, 16), int(before[-2].op_str, 16)))
        p += 1
    return out


def routine_of(text, address, loaders):
    for w, start in loaders.items():
        if start <= address < start + 0x400:
            return w
    return None


def family_bitmaps(machine, lib, g, cases, text=None, data=None):
    t = v.Tally('bitmaps')
    for world in [91, 113, 128, 129, 130, 135, 136, 137, 138, 140, 142, 0]:
        for index in TABLE_IDS:
            path, filt, wrap = C.c_char_p(), C.c_uint32(), C.c_uint32()
            have = lib.dll.mu_world_slot_bitmap(world, index, C.byref(path), C.byref(filt), C.byref(wrap))
            sites = load_sites(text, data, index)
            own = [s_ for s_ in sites if routine_of(text, s_[0], LOADERS) == world]
            shared = [s_ for s_ in sites if routine_of(text, s_[0], LOADERS) is None]
            expect = own[0] if own else shared[0] if len(shared) == 1 and not any(
                routine_of(text, s_[0], LOADERS) for s_ in sites) else None
            if expect is None:
                t.count('not registered for this world')
                t.add(not have, {'world': world, 'index': hex(index), 'have': have})
                continue
            t.count('own loader' if own else 'shared site')
            t.add(bool(have) and path.value.decode() == expect[1] and filt.value == expect[2] and
                  wrap.value == expect[3], {'world': world, 'index': hex(index), 'c': (path.value, filt.value,
                                                                                       wrap.value), 'client': expect})
    return t


FAMILIES = {}
for _w in CLASSES:
    FAMILIES[f'custom_{_w}'] = (lambda w: lambda m, l, g, n: slot_family(m, l, g, n, w, False))(_w)
    FAMILIES[f'after_{_w}'] = (lambda w: lambda m, l, g, n: slot_family(m, l, g, n, w, True))(_w)
for _w in PREMOVE:
    FAMILIES[f'premove_{_w}'] = (lambda w: lambda m, l, g, n: premove_family(m, l, g, n, w))(_w)
FAMILIES['bitmaps'] = None   # set in main (needs the text and data)
FIXED = {'bitmaps'}
MUTATIONS = [
    ('Tarkan 0x1f stream mesh', 'world_slots_visual.c', 'stream(s,3);', 'stream(s, 2);', 'custom_140'),
    ('Tarkan 0x60 scroll', 'world_slots_visual.c', 'tmod(s,50000,5e-05f,1)', 'tmod(s, 50000, 5e-05f, 0)', 'custom_140'),
    ('Tarkan after glow', 'world_slots_visual.c', 'wave(s,-1.0f)*0.3f+0.7f', 'wave(s, -1.0f) * 0.3f + 0.6f', 'after_140'),
    ('Ignis after-character skip', 'world_slots_visual.c', 'if(s->o[MU_OBJF_AFTER_CHARACTER])return1;', '', 'custom_138'),
    ('Ignis 0xac frame window', 'world_slots_visual.c', '29.0f>frame(s)', '28.0f > frame(s)', 'custom_138'),
    ('Ignis 0x5f swapped uv', 'world_slots_visual.c', 'tmod(s,100000,0.0002f,0),U(s));', 'U(s), tmod(s, 100000, 0.0002f, 0));', 'custom_138'),
    ('Ignis after type', 'world_slots_visual.c', '==0x2d)body(', '== 0x2e) body(', 'after_138'),
    ('Kanturu flag type 8', 'world_slots_visual.c', 'case8:case0x5c:case0x5d:case0x5e:case0x5f:case0x60:case0x4c:',
     'case 0x5c: case 0x5d: case 0x5e: case 0x5f: case 0x60: case 0x4c:', 'custom_137'),
    ('Kanturu hidden 0x3e', 'world_slots_visual.c', 'case0x3e:case0x3f:set_hidden(s,2);', 'case 0x3e: case 0x3f: set_hidden(s, 1);', 'custom_137'),
    ('Kanturu 0x1b keeps stream', 'world_slots_visual.c', 'stream(s,4);body(s,2,BM(s),BL(s),U(s),tmod(s,2000,0.0005f,1),H(s));set_after(s);',
     'stream(s, 4); body(s, 2, BM(s), BL(s), U(s), tmod(s, 2000, 0.0005f, 1), H(s)); stream(s, 0xff); set_after(s);', 'custom_137'),
    ('Kanturu clamp', 'world_slots_visual.c', '1.0f>x?x:1.0f', 'x', 'custom_137'),
    ('Kanturu after texture = hidden', 'world_slots_visual.c', 'mesh_std(s,0,2,H(s));', 'mesh_std(s, 0, 2, -1);', 'after_137'),
    ('Kanturu after grey', 'world_slots_visual.c', 'grey(s,0.4f);', 'grey(s, 0.5f);', 'after_137'),
    ('Karutan 0x6b PlaySpeed', 'world_slots_visual.c', 'play_speed(s,5.0f);', 'play_speed(s, 4.0f);', 'custom_142'),
    ('Karutan 0x77 colour restore', 'world_slots_visual.c', 'color(s,r,g,bl);', 'color(s, g, r, bl);', 'custom_142'),
    ('Karutan 0x75 answers no', 'world_slots_visual.c', 'case0x74:case0x76:', 'case 0x74: case 0x75: case 0x76:', 'custom_142'),
    ('Karutan after 0xa3 twice', 'world_slots_visual.c',
     'grey(s,wave(s,-2.5f)*0.3f+0.7f);mesh_self(s,0,2,BL(s),U(s),V(s));mesh_self(s,0,2,BL(s),U(s),V(s));',
     'grey(s, wave(s, -2.5f) * 0.3f + 0.7f); mesh_self(s, 0, 2, BL(s), U(s), V(s));', 'after_142'),
    ('Bitmap wrap', 'world_slots_visual.c', '{-1,0x8151,"Object92\\\\jung03_R.jpg",0x2601,0x2901}',
     '{-1, 0x8151, "Object92\\\\jung03_R.jpg", 0x2601, 0x2900}', 'bitmaps'),
    ('Bitmap world folder', 'world_slots_visual.c', '{136,0x8341,"Object137', '{136, 0x8341, "Object136', 'bitmaps'),
    ('Bitmap use list', 'world_slots_visual.c', '{113,0x2e,{0x8249,0x824a}}', '{113, 0x2e, {0x8249}}', 'custom_113'),
    ('Guardian state sounds', 'world_slots_visual.c', '0x38b+state', '0x38c + state', 'premove_70'),
    ('Guardian event worlds', 'world_slots_visual.c', 'world>=0x48)play', 'world >= 0x49) play', 'premove_69'),
    ('Karutan sound owner', 'world_slots_visual.c', 'play(l,i,0x3db,1)', 'play(l, i, 0x3db, 0)', 'premove_80'),
    ('Swamp chance', 'world_slots_visual.c', 'rnd(c)%50==0', 'rnd(c) % 60 == 0', 'premove_122'),
    ('Swamp quiet box', 'world_slots_visual.c', 'y<=0x27', 'y <= 0x28', 'premove_122'),
    ('Karutan after 0xc5 blend', 'world_slots_visual.c', 'mesh(s,0,2,A(s),-1,', 'mesh(s, 0, 2, A(s), 0,', 'after_142'),
]


def build(root):
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
    return Library(root / 'objects' / ('libobjects.' + v.SUFFIX))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=1000)
    p.add_argument('--only')
    p.add_argument('--text', default=v.pins.TEXT.default_str())
    p.add_argument('--data', default=v.pins.DATA.default_str())
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    text = am.load_pinned(a.text, am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(a.data, am.DATA_BYTES, am.DATA_SHA256, 'data')
    machine = vp.PtMachine(text, data)
    names = a.only.split(',') if a.only else list(FAMILIES)
    FAMILIES['bitmaps'] = lambda m, l, g, n: family_bitmaps(m, l, g, n, text, data)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': [],
              'bodies': {k: {'start': hex(b), 'end': hex(e),
                             'sha256': hashlib.sha256(text[b - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for k, (b, e) in slot_bodies(text).items()}}
    lib = build(ROOT / 'reconstructed')
    seed = lambda name: random.Random(0xaf72 + list(FAMILIES).index(name))
    for name in names:
        tally = FAMILIES[name](machine, lib, seed(name), a.cases)
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:2500], flush=True)
    if a.mutations:
        for label, file, old, new, family in MUTATIONS:
            if family not in names:
                continue
            with tempfile.TemporaryDirectory(prefix='worlds-after2-mut-') as mtmp:
                root = Path(mtmp)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'particles', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                if (ROOT / 'reconstructed/deps.mk').exists():
                    shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                path = root / 'objects' / file
                s = path.read_text()
                pattern = ''.join(re.escape(ch) + r'\s*' for ch in old.replace(' ', ''))
                s, count = re.subn(pattern, lambda m: new, s, count=1)
                assert count == 1, (label, old)
                path.write_text(s)
                tally = FAMILIES[family](machine, build(root), seed(family), a.cases)
                item = {'name': label, 'cases': tally.cases,
                        'detected': tally.cases - tally.equal - tally.stopped, 'stopped': tally.stopped}
                report['mutants'].append(item)
                print(item, flush=True)
    report['ok'] = all(x['mismatch_count'] == 0 and x['stopped'] == 0 for x in report['families'].values()) and \
        all(x['detected'] > 0 for x in report['mutants'])
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=1))
    print('ok' if report['ok'] else 'FAILED', flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
