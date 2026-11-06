#!/usr/bin/env python3
"""RENDER-WORLDS-SLOTS instruction comparisons (docs/research/client-worlds-slots.md).

Families (compiled C via ctypes against the pinned original under the strict Unicorn machine):
  custom_<world>   the class's custom render slot 0x38: RenderBody/RenderMesh calls with their eight arguments, the
                   model's StreamMesh byte +0x94 and body colour +0x54 at each call, rand draws, the object and model
                   bytes after the call and the answer (validate_worlds_after3's slot comparison).
  after_<world>    the class's after render slot 0x3c, the same comparison without an answer.
  invisible_<world> the class's invisible-sector move slot 0x1c (MoveObjects asks it for objects of sectors the last
                   render pass did not see): the answer against mu_obj_handler_moves, frustum polygons around the
                   object, its own types and random ones; 143 also with a null object.
  trivial          the base custom (0x00d5cc8e), after (0x00d5cc60) and invisible-move (0x00d5cbbc) methods and the
                   classes whose slots are empty or always answer no (62, 64, 95, 100, 115..120, every class's slot
                   0x1c without an override): answer 0 and no write in the client, no event and answer 0 in the C.
The first 301 cases of a slot family sweep the object type 0..300 (the world manager's range); the rest draw the
class's case types. Worlds are drawn around the class (its own, the class's other worlds, neighbours) so the slot's
world test is compared too.
"""
import argparse, ctypes as C, hashlib, json, random, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_particles as vp
import validate_worlds_after2 as a2
import validate_worlds_after3 as a3

ROOT = Path(__file__).resolve().parents[1]
# class: (custom slot 0x38, after slot 0x3c, worlds the slot is tried in, case types)
CLASSES = {
    79: (0xe6ce2d, 0xe6d062, [79, 79, 114, 78, 80], [8, 0x1e, 0x32, 0x44]),
    114: (0xe1f6ca, 0xe1f8ff, [114, 114, 79, 113, 115], [8, 0x1e, 0x32, 0x44]),
    112: (0xde8a10, 0xde9eab, [112, 112, 111, 113, 0],
          [0x27, 0x2b, 0x33, 0x4b, 0x51, 0x57, 0x5f, 0x72, 0x73, 0x7b, 0x8a, 0x99, 0x9a, 0x9b]),
    123: (0xe1a5df, 0xe1b6f5, [123, 124, 125, 126, 127, 122, 128],
          [0x1d, 0x1e, 0x2f, 0x34, 0x48, 0x4c, 0x5e, 0x6d, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7e,
           0x83, 0x86, 0x8b, 0x8c, 0x92, 0x93, 0x9f, 0xa0]),
}
# the class loaders (slot 0x24) that write the handler's bitmap fields: class -> (loader, worlds)
LOADERS = {123: (0xe18efb, [123, 124, 125, 126, 127]), 112: (0xde5977, [112])}
# member worlds of a class whose slots the native calls with cls = the world
MEMBERS = {123: [123, 124, 125, 126, 127]}
# types whose branches depend on the object action (1/3) and frame: drawn with those more often
ACTION_TYPES = {123: [0x2f, 0x34], 112: [0x27]}
# world: (slot 0x1c, its own types)
INVISIBLE = {
    142: (0xe673b4, [0xa0, 0xa1]),
    143: (0xe0e539, [0x71, 0x80]),
    144: (0xe46a9f, [4, 6, 0xa, 0xd, 0x12, 0x15, 0x17, 0x18, 0x1b, 0x1c, 0x22, 0x24, 0x25, 0x26, 0x2b, 0x3b, 0x40,
                     0x42, 0x43, 0x49, 0x4e, 0x5e, 0x6a, 0x6b, 0x6d, 0x6e, 0x6f, 0x71, 0x74, 0x78, 0x7a, 0x7d, 0x7f,
                     0x82, 0x83, 0x84, 0x8d, 0x8e, 0x90, 0x91, 0x92, 0x94, 0xb5, 0x27, 0x23, 0x5a, 0x99, 0x4a, 0x4d,
                     0x10, 0x21, 0x7e, 0x1a, 0x79, 0x39, 0x70, 0x81, 0x4f, 0x19, 0x37, 0x52, 0x5b, 0xb7, 0xc8, 0x8c,
                     0x1f, 0x93, 0x36]),
    145: (0xd7565d, []),
}
BASE_CUSTOM, BASE_AFTER, BASE_INVISIBLE = 0xd5cc8e, 0xd5cc60, 0xd5cbbc
# class: (custom, after) of the slots that draw nothing and answer no (the base methods, 62's after, 64's two)
TRIVIAL = {62: (None, 0xe428af), 64: (0xdc6a2e, 0xdc6a5b), 95: (None, BASE_AFTER), 100: (None, BASE_AFTER),
           115: (BASE_CUSTOM, BASE_AFTER), 116: (BASE_CUSTOM, BASE_AFTER), 117: (BASE_CUSTOM, BASE_AFTER),
           118: (BASE_CUSTOM, BASE_AFTER), 119: (BASE_CUSTOM, BASE_AFTER), 120: (BASE_CUSTOM, BASE_AFTER)}
DUEL_TEST = 0xdc6bfa   # 64's custom calls it and answers no either way
FOCUS = {123: [0x2f, 0x34, 0x71, 0x75, 0x6d, 0xa0, 0x86, 0x4c]}
BODY, MESH = a2.BODY, a2.MESH
RAND = 0x1989721


def body_range(text, start):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.skipdata = True
    end = start
    for ins in md.disasm(text[start - am.TEXT_BASE:start - am.TEXT_BASE + 0x2800], start):
        end = ins.address + ins.size
        if ins.mnemonic == 'ret' and text[end - am.TEXT_BASE] in (0xcc, 0x55):
            break
    return start, end


def slot_bodies(text):
    out = {}
    for w, (custom, after, _, _) in CLASSES.items():
        out[f'custom_{w}'] = body_range(text, custom)
        out[f'after_{w}'] = body_range(text, after)
    for w, (address, _) in INVISIBLE.items():
        out[f'invisible_{w}'] = body_range(text, address)
    for w, (custom, after) in TRIVIAL.items():
        if custom and custom != BASE_CUSTOM:
            out[f'custom_{w}'] = body_range(text, custom)
        if after != BASE_AFTER:
            out[f'after_{w}'] = body_range(text, after)
    for name, address in (('base_custom', BASE_CUSTOM), ('base_after', BASE_AFTER),
                          ('base_invisible', BASE_INVISIBLE), ('duel_test', DUEL_TEST)):
        out[name] = body_range(text, address)
    return out


def run_loader(machine, world, loader):
    """The class loader as client code into a writable handler: LoadBitmap calls and the handler afterwards."""
    loaded = []

    def load(m):
        loaded.append((m.cstring(m.argument(0)), m.argument(1), m.argument(2), m.argument(3)))
        return 1

    def sprintf_s(m):
        text = a3.c_format(m, m.cstring(m.argument(2)), 3).encode('latin1') + b'\0'
        m.uc.mem_write(m.argument(0), text)
        return len(text) - 1

    def sprintf(m):
        text = a3.c_format(m, m.cstring(m.argument(1)), 2).encode('latin1') + b'\0'
        m.uc.mem_write(m.argument(0), text)
        return len(text) - 1
    stubs = {a3.LOAD_BITMAP: load, a3.SPRINTF_S: sprintf_s, a3.SPRINTF: sprintf}
    for leaf in a3.LOADER_LEAVES:
        stubs[leaf] = (lambda m: 0) if leaf != 0x94997e else (lambda m: (m.uc.reg_read(m.x86.UC_X86_REG_ECX), 4))
    regions = v.global_regions(world, 6, [am.defined_region('fake', v.FAKE, v.fake_object())])
    result = v.run(machine, loader, [], regions, stubs, ecx=v.FAKE, cleanup=0)
    return loaded, result['regions'].get('fake'), v.stopped_reason(result)


_HANDLERS = {}


def loaded_handler(machine, cls, world):
    """The fake handler with the bitmap fields the class loader writes in `world` (cached per world)."""
    if cls not in LOADERS:
        return v.fake_object()
    loader, worlds = LOADERS[cls]
    key = world if world in worlds else worlds[0]
    if key not in _HANDLERS:
        _, handler, stop = run_loader(machine, key, loader)
        assert not stop, stop
        _HANDLERS[key] = handler
    return _HANDLERS[key]


class SlotModel(C.Structure):   # mu_slot_model with RENDER-WORLDS-SLOTS' handler state
    _fields_ = a2.SlotModel._fields_ + [('handler_state', C.c_int32)]


class Library(a3.Library):
    pass


def slot_family(machine, lib, g, cases, world_cls, after):
    custom, after_addr, worlds, types = CLASSES[world_cls]
    t = v.Tally(('after_' if after else 'custom_') + str(world_cls))
    for n in range(cases):
        world = world_cls if g.random() < 0.8 else g.choice(worlds + [0, 128, 140])
        typ = n if n <= 300 else g.choice(types + FOCUS.get(world_cls, [])) if g.random() < 0.9 else \
            g.randrange(0, 301)
        count, subs, array, records = a2.slot_meshes(g)
        o, b = a2.slot_object(g, typ), a2.slot_model(g, count)
        o[0] = g.choice([0, 1, 1, 1])
        if typ in ACTION_TYPES.get(world_cls, []):
            struct.pack_into('<H', o, 0x2a, g.choice([1, 3, 1, 3, 0, 2]))
            v.put_f(o, 0xd0, v.f32(g.choice([2.99, 3.0, 3.01, 10.0, 28.0, 29.0, 30.0, g.uniform(0, 40)])))
        struct.pack_into('<h', b, 0xb4, g.choice([0, 1, 2, 3, g.randrange(-40, 40)]))
        struct.pack_into('<H', b, 0xa8, g.choice([0, 0, 1, 2, 2, g.randrange(0, 0x10000)]))
        actions = bytearray(g.getrandbits(8) for _ in range(16 * a2.ACTION_COUNT))
        act = struct.unpack_from('<H', o, 0x2a)[0]
        struct.pack_into('<h', actions, 16 * act + 8, g.choice([0, 1, 2, 10, 29, 30, 31, g.randrange(-5, 60)]))
        time = v.f32(g.choice([0.0, g.uniform(0, 100000), g.uniform(0, 1e7), g.uniform(1e7, 3e9)]))
        state = g.choice([0, 0, 1, 2, 3, g.randrange(-5, 10)])
        seed = g.randrange(2**32)
        ra, rb = v.MsvcRand(seed), v.MsvcRand(seed)
        calls = []

        def recorder(address):
            def stub(m):
                model = bytes(m.uc.mem_read(v.MODEL, 0x100))
                calls.append((address,) + tuple(m.argument(k) for k in range(8)) + (model[0x94],) +
                             struct.unpack_from('<3I', model, 0x54))
                return (0, 32)
            return stub
        stubs = {BODY: recorder(BODY), MESH: recorder(MESH), RAND: lambda m: ra()}
        fake = bytearray(loaded_handler(machine, world_cls, world))
        if world_cls == 112:
            struct.pack_into('<i', fake, 0x48, state)   # the door state object {state, ...} (0x00dee9ee)
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                                              am.defined_region('model', v.MODEL, bytes(b)),
                                              am.defined_region('actions', v.ACTIONS, bytes(actions),
                                                                writable=False),
                                              am.defined_region('meshes', a2.MESHES, bytes(array), writable=False),
                                              am.defined_region('subs', a2.SUBS, bytes(records), writable=False),
                                              am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                                              am.defined_region('fake', v.FAKE, bytes(fake), writable=False)])
        start = after_addr if after else custom
        result = v.run(machine, start, [v.OBJECTS, v.MODEL, 0], regions, stubs, ecx=v.FAKE, cleanup=12)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': hex(typ)}, stop)
            continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        cb = C.create_string_buffer(bytes(b), 0x100)
        log = v.new_log()
        flags = (C.c_int16 * 16)(*(subs + [0] * (16 - len(subs))))
        frames = struct.unpack_from('<h', actions, 16 * act + 8)[0]
        rand_fn = v.RAND_FN(lambda c: rb())
        model = SlotModel(count, flags, frames, rand_fn, None, state)
        cls = world if world in MEMBERS.get(world_cls, []) else world_cls   # the native passes the world
        if after:
            lib.dll.mu_class_after(cls, co, cb, 0, world, time, C.byref(model), C.byref(log))
            answer, client = 0, 0
        else:
            answer = 1 if lib.dll.mu_class_custom(cls, co, cb, 0, world, time, C.byref(model),
                                                  C.byref(log)) else 0
            client = result['eax'] & 0xff
        mine = a3.native_events(v.log_events(log), b)
        named = (C.c_int32 * 36)()
        listed = set(named[:lib.dll.mu_world_slot_bitmaps(world, typ, named)])
        textures = {c[8] for c in calls if c[0] in (BODY, MESH) and c[8] != 0xffffffff}
        bitmaps_ok = all(x in listed for x in textures if 0x7000 <= x < 0x9000)
        if textures:
            t.count('bitmap meshes')
        ok = (bitmaps_ok and calls == mine and client == answer and ra.seed == rb.seed and
              result['regions']['object'] == co.raw[:v.OBJ_SIZE] and result['regions']['model'] == cb.raw[:0x100])
        t.count(f'answer {client}')
        t.count('drawn' if calls else 'no draw')
        if world == world_cls and typ in types:
            t.count('case types')
        if world != world_cls:
            t.count('other world')
        t.add(ok, {'case': n, 'world': world, 'type': hex(typ), 'client': [tuple(hex(x) for x in c) for c in calls[:6]],
                   'native': [tuple(hex(x) for x in c) for c in mine[:6]], 'answer': (client, answer),
                   'object': result['regions']['object'] == co.raw[:v.OBJ_SIZE],
                   'model': result['regions']['model'] == cb.raw[:0x100], 'rand': ra.seed == rb.seed,
                   'bitmaps': (sorted(textures), sorted(listed))})
    return t


def loaders_family(machine, lib, g, cases):
    """Each class loader as client code: the handler bitmap words it writes per world against
    mu_slots_more_handler, and every bitmap the slots name per (world, type) against its LoadBitmap call."""
    t = v.Tally('loaders')
    for cls, (loader, worlds) in LOADERS.items():
        for world in worlds + [0, worlds[0] - 1]:
            loaded, handler, stop = run_loader(machine, world, loader)
            if stop:
                t.add(False, {'world': world}, stop)
                continue
            words = (C.c_int32 * 12)()
            have = lib.dll.mu_slots_more_handler(world, words)
            client = list(struct.unpack_from('<12i', handler, 0x1c))
            if world in worlds and cls == 112:   # Ferea's loader writes no handler field
                t.count('no handler words')
                t.add(not have and client == [0] * 12, {'world': world, 'have': have, 'client': client})
            elif world in worlds:
                t.count('handler words')
                t.add(bool(have) and list(words) == client, {'world': world, 'c': [hex(x) for x in words],
                                                             'client': [hex(x) for x in client]})
            else:
                t.count('other world')
                t.add(not have, {'world': world, 'have': have})
                continue
            by_index = {}
            for path, index, filt, wrap in loaded:
                by_index.setdefault(index, (path, filt, wrap))
            named = set()
            for typ in range(301):
                out = (C.c_int32 * 36)()
                named.update(out[:lib.dll.mu_world_slot_bitmaps(world, typ, out)])
            for index in sorted(named):
                path, filt, wrap = C.c_char_p(), C.c_uint32(), C.c_uint32()
                have = lib.dll.mu_world_slot_bitmap(world, index, C.byref(path), C.byref(filt), C.byref(wrap))
                expect = by_index.get(index)
                mine = (path.value.decode(), filt.value, wrap.value) if have else None
                t.count('registered by the loader' if expect else 'not registered')
                t.add(expect is not None and mine == (expect[0].removeprefix('Data\\'), expect[1], expect[2]),
                      {'world': world, 'index': hex(index), 'c': mine, 'client': expect})
    return t


def invisible_family(machine, lib, g, cases, world_cls):
    address, types = INVISIBLE[world_cls]
    t = v.Tally(f'invisible_{world_cls}')
    for n in range(cases):
        x2d, y2d = v.frustum_polygon(g)
        cx, cy = sum(x2d) / 4, sum(y2d) / 4
        scene = g.choice([6, 6, 2])
        o = bytearray(v.poison_object(g))
        v.put_i(o, 0x5c, g.choice(types + [g.randrange(0, 0xd0)]) if types and g.random() < 0.7 else
                g.randrange(-2, 0x200))
        v.put_f(o, 0x158, v.f32((cx + g.uniform(-60, 60)) * 100), v.f32((cy + g.uniform(-60, 60)) * 100), 0.0)
        v.put_f(o, 0xc0, v.f32(g.choice([-1000.0, -30.0, g.uniform(-1500, 100)])))
        o[0xb] = g.choice([0, 1, 2, 0xff])
        null = world_cls == 143 and g.random() < 0.1
        regions = v.global_regions(world_cls, scene, [
            am.defined_region('object', v.OBJECTS, bytes(o), writable=False),
            am.defined_region('x2d', v.X2D, v.pack_f(*x2d), writable=False),
            am.defined_region('y2d', v.Y2D, v.pack_f(*y2d), writable=False)])
        result = v.run(machine, address, [0 if null else v.OBJECTS], regions, {}, ecx=v.FAKE, cleanup=4)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n}, stop)
            continue
        xs, ys = (C.c_float * 4)(*x2d), (C.c_float * 4)(*y2d)
        c = lib.dll.mu_obj_handler_moves(None if null else C.create_string_buffer(bytes(o), v.OBJ_SIZE),
                                         world_cls, xs, ys, scene)
        got = result['eax'] & 0xff
        t.count('moves' if got else 'stays')
        if null:
            t.count('null object')
        t.add(got == c, {'case': n, 'got': got, 'c': c, 'type': hex(struct.unpack_from('<i', o, 0x5c)[0])})
    return t


def trivial_family(machine, lib, g, cases):
    """Empty and always-no slots: client answer 0 and nothing written; C answer 0 and nothing logged."""
    t = v.Tally('trivial')
    rows = []
    for cls, (custom, after) in TRIVIAL.items():
        if custom:
            rows.append(('custom', cls, custom))
        rows.append(('after', cls, after))
    no_class = [w for w in range(-1, 200) if w not in INVISIBLE and w != 141]
    for n in range(cases):
        kind, cls, address = rows[n % len(rows)] if n % 4 else ('invisible', g.choice(no_class), BASE_INVISIBLE)
        world = cls if g.random() < 0.8 else g.randrange(-1, 200)
        typ = g.randrange(0, 301)
        count, subs, array, records = a2.slot_meshes(g)
        o, b = a2.slot_object(g, typ), a2.slot_model(g, count)
        o[0xb] = g.choice([0, 1])
        calls = []

        def recorder(address_):
            def stub(m):
                calls.append(address_)
                return (0, 32)
            return stub
        stubs = {BODY: recorder(BODY), MESH: recorder(MESH)}
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                                              am.defined_region('model', v.MODEL, bytes(b)),
                                              am.defined_region('meshes', a2.MESHES, bytes(array), writable=False),
                                              am.defined_region('subs', a2.SUBS, bytes(records), writable=False),
                                              am.defined_region('fake', v.FAKE, v.fake_object(), writable=False)])
        args, cleanup = ([v.OBJECTS], 4) if kind == 'invisible' else \
            ([v.OBJECTS if g.random() < 0.9 else 0, v.MODEL if g.random() < 0.9 else 0, 0], 12)
        result = v.run(machine, address, args, regions, stubs, ecx=v.FAKE, cleanup=cleanup)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'kind': kind, 'class': cls}, stop)
            continue
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        cb = C.create_string_buffer(bytes(b), 0x100)
        log = v.new_log()
        flags = (C.c_int16 * 16)(*(subs + [0] * (16 - len(subs))))
        model = SlotModel(count, flags, 0, v.RAND_FN(lambda c: 0), None, 0)
        if kind == 'invisible':
            xs = (C.c_float * 4)(0.0, 1.0, 1.0, 0.0)
            answer = lib.dll.mu_obj_handler_moves(co, cls, xs, xs, 6)
            client = result['eax'] & 0xff
        elif kind == 'custom':
            answer = lib.dll.mu_class_custom(cls, co, cb, 0, world, 0.0, C.byref(model), C.byref(log))
            client = result['eax'] & 0xff
        else:
            lib.dll.mu_class_after(cls, co, cb, 0, world, 0.0, C.byref(model), C.byref(log))
            answer = client = 0
        unchanged = result['regions']['object'] == bytes(o) and result['regions']['model'] == bytes(b)
        same_c = co.raw[:v.OBJ_SIZE] == bytes(o) and cb.raw[:0x100] == bytes(b)
        t.count(kind)
        t.add(client == 0 and answer == 0 and not calls and not v.log_events(log) and unchanged and same_c,
              {'case': n, 'kind': kind, 'class': cls, 'world': world, 'client': client, 'c': answer,
               'calls': calls, 'unchanged': unchanged, 'same_c': same_c})
    return t


FAMILIES = {}
for _w in CLASSES:
    FAMILIES[f'custom_{_w}'] = (lambda w: lambda m, l, g, n: slot_family(m, l, g, n, w, False))(_w)
    FAMILIES[f'after_{_w}'] = (lambda w: lambda m, l, g, n: slot_family(m, l, g, n, w, True))(_w)
for _w in INVISIBLE:
    FAMILIES[f'invisible_{_w}'] = (lambda w: lambda m, l, g, n: invisible_family(m, l, g, n, w))(_w)
FAMILIES['trivial'] = trivial_family
FAMILIES['loaders'] = loaders_family
W, R = 'world_slots_more_visual.c', 'object_render.c'
MUTATIONS = [
    # Loren Market / Event square
    ('Market 0x1e not flagged', W, 'case8:case0x1e:set_after(s);', 'case 8: set_after(s);', 'custom_79'),
    ('Market 0x32 pulse clamp', W, 'if(x>1.0f)x=1.0f;', 'if (x > 0.9f) x = 0.9f;', 'custom_79'),
    ('Market 0x32 pulse period', W, 'wave(s,-1.2f)+0.4f', 'wave(s, -1.0f) + 0.4f', 'custom_79'),
    ('Market 0x32 mesh 3', W, 'mesh_std(s,3,2,-1);', 'mesh_std(s, 2, 2, -1);', 'custom_79'),
    ('Market custom world', W, "world==(cls==114?0x72:0x4f)", "world == (cls == 114 ? 0x72 : 0x50)", 'custom_79'),
    ('Square custom world', W, "world==(cls==114?0x72:0x4f)", "world == (cls == 114 ? 0x71 : 0x4f)", 'custom_114'),
    ('Market after scroll sign', W, 'tmod(s,10000,0.001f,1)', 'tmod(s, 10000, 0.001f, 0)', 'after_79'),
    ('Market after wave u', W, 'csin(s->time*0.0007f)*0.05f', 'csin(s->time * 0.0007f) * 0.06f', 'after_79'),
    ('Market after 0x44 blend', W, 'mesh(s,0,0x42,A(s),0,BL(s),U(s),V(s),-1);', 'mesh(s, 0, 0x42, A(s), -1, BL(s), U(s), V(s), -1);', 'after_114'),
    ('Market after 0x1e hidden', W, 'body_std(s,H(s));', 'body_std(s, -1);', 'after_79'),
    # Ferea
    ('Ferea door scroll sign', W, 'V(s)+0.1f);', 'V(s) + 0.2f);', 'custom_112'),
    ('Ferea door closing', W, 'elseif(act==2)', 'else if (act == 3)', 'custom_112'),
    ('Ferea door stream', W, 'stream(s,3);mesh_a', 'stream(s, 2); mesh_a', 'custom_112'),
    ('Ferea 0x4b glow blend', W, 'mesh(s,0,0x44,A(s),0,BL(s),U(s),V(s),-1);', 'mesh(s, 0, 0x44, A(s), -1, BL(s), U(s), V(s), -1);', 'custom_112'),
    ('Ferea 0x57 scroll period', W, '%5000)*1e-4f*2.0f*2.0f', '% 5000) * 1e-4f * 2.0f * 1.0f', 'custom_112'),
    ('Ferea 0x73 pulse', W, '*0.5f*0.5f+0.5f', '* 0.5f * 0.5f + 0.4f', 'custom_112'),
    ('Ferea statue state 2', W, 'state==3||state==2', 'state == 3', 'custom_112'),
    ('Ferea 0x8a glow mesh', W, 'mesh(s,3,2,A(s),3,w,U(s),V(s),-1);', 'mesh(s, 3, 2, A(s), 2, w, U(s), V(s), -1);', 'custom_112'),
    ('Ferea 0x9a double', W, '*0.3+0.20000000298023224', '* 0.3 + 0.2', 'custom_112'),
    ('Ferea 0x72 drawn first', W, 'case0x2b:case0x33:case0x72:return1;', 'case 0x2b: case 0x33: return 1;', 'custom_112'),
    ('Ferea after 0x51 light', W, 't==0x51?0.7f:1.0f', 't == 0x51 ? 0.8f : 1.0f', 'after_112'),
    ('Ferea after 0x4b pulse', W, '(csin(s->time*0.007f)+2.0f)*0.5f', '(csin(s->time * 0.007f) + 1.0f) * 0.5f', 'after_112'),
    ('Ferea after 0x57 period', W, 'ferea_scroll(s,0x1a0b,1.5f)', 'ferea_scroll(s, 0x1a0c, 1.5f)', 'after_112'),
    ('Ferea after 0x99 v', W, 'BL(s),U(s),U(s),-1);', 'BL(s), U(s), V(s), -1);', 'after_112'),
    ('Ferea after 0x33 light', W, 'body(s,2,-1,1.0f,0.0f,0.0f,-1);', 'body(s, 2, -1, BL(s), 0.0f, 0.0f, -1);', 'after_112'),
    ('Ferea after 0x9b sign', W, 'mesh(s,2,2,A(s),2,BL(s),x,-x,-1);', 'mesh(s, 2, 2, A(s), 2, BL(s), x, x, -1);', 'after_112'),
    # Kubera
    ('Kubera 0x83 drawn in the first pass', W, 'case0x79:case0x83:', 'case 0x79:', 'custom_123'),
    ('Kubera gem backwards scroll', W, '-r*0.002f', 'r * 0.002f', 'custom_123'),
    ('Kubera gem frame start', W, 'act==1&&f>=3.0f', 'act == 1 && f >= 2.0f', 'custom_123'),
    ('Kubera gem last key', W, 'last=(float)(s->model->action_frames-1)', 'last = (float)(s->model->action_frames)', 'custom_123'),
    ('Kubera gem stream', W, 'stream(s,(uint8_t)k);', '', 'custom_123'),
    ('Kubera 0x4c glow', W, 'wave(s,-3.0f)*0.2f+0.7f', 'wave(s, -3.0f) * 0.2f + 0.8f', 'custom_123'),
    ('Kubera 0x72 order', W, '{0x72,4,{0x2c,0x28,0x30,0x34}}', '{0x72, 4, {0x28, 0x2c, 0x30, 0x34}}', 'custom_123'),
    ('Kubera chrome flags', W, 'mesh(s,rows[r].n-1,0x20000,', 'mesh(s, rows[r].n - 1, 0x42,', 'custom_123'),
    ('Kubera 0x8b field', W, 'kh(world,0x24));return1;', 'kh(world, 0x20)); return 1;', 'custom_123'),
    ('Kubera 0x8c second glow', W, 'mesh(s,3,0x42,A(s),-2,w,U(s),V(s),-1);mesh(s,3,0x42,A(s),-2,w,U(s),V(s),-1);return1;',
     'mesh(s, 3, 0x42, A(s), -2, w, U(s), V(s), -1); return 1;', 'custom_123'),
    ('Kubera world 125 field', W, '{0x82b5,0x82b6,0x82c0,', '{0x82b5, 0x82b6, 0x82c1,', 'custom_123'),
    ('Kubera after body hidden', W, 'case0x9f:body_std(s,H(s));', 'case 0x9f: body_std(s, -1);', 'after_123'),
    ('Kubera after gate colours', W, '{0x82a0,0x82aa},{0x82a2,0x82ac}', '{0x82a2, 0x82ac}, {0x82a0, 0x82aa}', 'after_123'),
    ('Kubera after 0xa0 mesh 9', W, 'mesh(s,9,2,A(s),BM(s),BL(s),U(s),V(s),kh(world,0x44));', 'mesh(s, 9, 2, A(s), BM(s), BL(s), U(s), V(s), kh(world, 0x48));', 'after_123'),
    ('Kubera after 0x86 skips', W, 'if(m!=2&&m!=3)mesh_std', 'if (m != 2) mesh_std', 'after_123'),
    ('Kubera after glow base', W, 'wave(s,-3.0f)*0.2f+0.8f;constint32_tt', 'wave(s, -3.0f) * 0.2f + 0.7f; const int32_t t', 'after_123'),
    ('Kubera bitmap wrap', W, '{0x829d,"Object124\\\\sd_Amethyst04A.jpg",0x2900}', '{0x829d, "Object124\\\\sd_Amethyst04A.jpg", 0x2901}', 'loaders'),
    ('Kubera chrome listed', W, 'if(type>=0x71&&type<=0x75&&n<room)', 'if (type >= 0x71 && type <= 0x74 && n < room)', 'custom_123'),
    # invisible move
    ('Karutan 0x1c type', R, 'returnt==0xa0||t==0xa1;', 'return t == 0xa0;', 'invisible_142'),
    ('Kardamahal 0x1c type', R, 'returnt==0x71||t==0x80;', 'return t == 0x71 || t == 0x81;', 'invisible_143'),
    ('Kardamahal null object', R, 'if(world==143&&!o)return0;', 'if (world == 143 && !o) return 1;', 'invisible_143'),
    ('Swamp 0x1c list', R, '0x93,0x36};', '0x93};', 'invisible_144'),
    ('145 visible byte', R, 'returno[MU_OBJF_VISIBLE]?1:0;', 'return o[MU_OBJF_VISIBLE] == 1;', 'invisible_145'),
]


def build(root):
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
    lib = Library(root / 'objects' / ('libobjects.' + v.SUFFIX))
    d = lib.dll
    d.mu_obj_handler_moves.argtypes = [C.c_void_p, C.c_int32, C.POINTER(C.c_float), C.POINTER(C.c_float), C.c_int32]
    d.mu_obj_handler_moves.restype = C.c_uint8
    d.mu_slots_more_handler.argtypes = [C.c_int32, C.POINTER(C.c_int32)]
    return lib


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
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': [],
              'bodies': {k: {'start': hex(b), 'end': hex(e),
                             'sha256': hashlib.sha256(text[b - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for k, (b, e) in slot_bodies(text).items()}}
    lib = build(ROOT / 'reconstructed')
    seed = lambda name: random.Random(0x5107 + list(FAMILIES).index(name))
    for name in names:
        tally = FAMILIES[name](machine, lib, seed(name), a.cases)
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:2500], flush=True)
    if a.mutations:
        for label, file, old, new, family in MUTATIONS:
            if family not in names:
                continue
            with tempfile.TemporaryDirectory(prefix='worlds-slots-mut-') as mtmp:
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
