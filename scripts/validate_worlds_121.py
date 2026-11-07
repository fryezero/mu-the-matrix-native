#!/usr/bin/env python3
"""RENDER-WORLDS-121 instruction comparisons (docs/research/client-worlds-121.md).

Families (compiled C via ctypes against the pinned original under the strict Unicorn machine):
  custom_121  Test Area 121's custom render 0x00d58bd8 (slot 0x38, thiscall(handler, object, model, index), ret 0xc)
              against mu_class_custom(121, ...): RenderBody/RenderMesh with the StreamMesh byte and colour at each
              call, CreateParticle 0x0168fafd (type, point, angle, light, sub, scale, owner), TransformPosition's
              bone list, the answer, the rand generator, the object and the model fields after the call, and the
              per-vertex light buffer 0x06fd0918: its writes are read at every draw and at the end, and the native
              pseudo call MU_OBJ_CALL_VERTEX_LIGHT stands for "every normal k < mesh +6 of every mesh m < model +0x24
              set to the value" at its place in the sequence. SetAction 0x012affa4 runs as client code (the model
              lookup 0x00966cc4/0x00eaa8cf stubbed to the case's model, whose +0x26 is the action count).
  actions_121 the custom render for types 0x10, 0x11, 0x13, 0x14, 0x15 only: frames at the edges of their windows,
              actions 0..3, and generator seeds whose first rand() lands on the residues the branches compare
              (0x11: % 100 near 90 and 0; 0x13/0x14/0x15: % 40 at 30/25/19 and their neighbours), compared as
              custom_121.
  after_121   the after render 0x00d5a6cc (slot 0x3c) against mu_class_after(121, ...), compared the same way.
  devias_67   RenderObjectVisual 0x017f9758 in Devias 2 with type 0x67's action choice (0x017f9d79), as
              validate_worlds_slots3's rng_2 (its composition and object comparison) under this validator's seed,
              for the mutants of mu_devias_action_pick and the shared SetAction.
Neither slot tests the world: a case runs in world 121 or, one in five, another world (the native passes the class
121 and that world). The first 301 cases of a slot family sweep the type 0..300.
"""
import argparse, ctypes as C, json, math, random, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_particles as vp
import validate_worlds_after2 as a2
import validate_worlds_slots as ws
import validate_worlds_slots2 as w2
import validate_worlds_slots3 as w3

ROOT = Path(__file__).resolve().parents[1]
CUSTOM, AFTER = 0xd58bd8, 0xd5a6cc
SET_ACTION = 0x12affa4
LIGHTS, LIGHT_STRIDE = 0x06fd0918, 0xea60
VERTEX_LIGHT = 0x06fd0918   # MU_OBJ_CALL_VERTEX_LIGHT
SENTINEL = struct.pack('<f', 7.25)
BODY, MESH, PARTICLE, TRANSFORM = ws.BODY, ws.MESH, ws.PARTICLE, ws.TRANSFORM
CUSTOM_TYPES = list(range(6, 13)) + [0x10, 0x11, 0x13, 0x14, 0x15, 0x2e, 0x35, 0x39, 0x44, 0x45, 0x47, 0x4c, 0x52,
                                     0x53, 0x59, 0x5c]
ACTION_TYPES = [0x10, 0x11, 0x13, 0x14, 0x15]
AFTER_TYPES = [0x2e, 0x35, 0x4c, 0x53, 0x59, 0x5c]
# actions_121: (frames at the window edges, actions, rand modulus, residues the branch compares and neighbours)
FOCUS = {
    0x10: ([18.0, 18.99, 19.0, 19.5, 30.0], [0, 1, 2], 2, [0, 1]),
    0x11: ([18.99, 19.0, 20.0, 96.99, 97.0, 97.5, 97.99, 98.0, 99.0], [0, 1, 2, 3], 100, [0, 1, 88, 89, 90, 91]),
    0x13: ([1.99, 2.0, 5.0, 5.01, 10.99, 11.0, 12.0, 12.25, 12.5, 12.51, 13.0, 14.0, 15.0, 17.0, 17.01, 19.49,
            19.5, 20.0], [0, 0, 1, 1, 2], 40, [29, 30, 31]),
    0x14: ([7.99, 8.0, 8.01, 11.99, 12.0, 15.0, 15.01, 18.99, 19.0], [0, 0, 1, 1, 2], 40, [24, 25, 26]),
    0x15: ([3.99, 4.0, 8.0, 8.01, 8.5, 9.0, 9.01, 18.99, 19.0], [0, 0, 1, 1, 2], 40, [18, 19, 20]),
}


def targeted_seed(g, modulus, residues):
    """A generator seed whose first MSVC rand() % modulus is one of the residues (a random seed after 4,000 tries)."""
    for _ in range(4000):
        seed = g.randrange(2**32)
        if (((seed * 214013 + 2531011) & 0xffffffff) >> 16 & 0x7fff) % modulus in residues:
            return seed
    return g.randrange(2**32)


class SlotModel(C.Structure):   # mu_slot_model with RENDER-WORLDS-121's bone and action counts
    _fields_ = ws.SlotModel._fields_ + [('bone_count', C.c_int32), ('action_count', C.c_int32)]


class Library(w3.Library):
    def __init__(self, path, particles):
        super().__init__(path, particles)
        d = self.dll
        d.mu_obj_set_action.argtypes = [C.c_void_p, C.c_int32, C.c_int32]
        d.mu_obj_set_action.restype = None


def case_counts(g):
    """Normal counts per mesh (mesh record +6), mostly small, sometimes zero or larger."""
    return [g.choice([0, 1, 3, 17, 64, g.randrange(0, 300), g.randrange(0, 2000)]) for _ in range(16)]


def light_slices(count, normals):
    return [(m * LIGHT_STRIDE, 4 * (normals[m] + 8)) for m in range(max(count, 0))]


def expected_set(count, normals):
    return [(m, k) for m in range(max(count, 0)) for k in range(normals[m])]


class LightWatch:
    """The client's per-vertex light writes, read at each draw and at the end as ('VLIGHT', value bits) markers."""

    def __init__(self, count, normals):
        self.count, self.normals = count, normals
        self.size = max(count, 1) * LIGHT_STRIDE
        self.initial = SENTINEL * (self.size // 4)
        self.last = {}

    def snapshot(self, m):
        out = {}
        for mesh, (at, n) in enumerate(light_slices(self.count, self.normals)):
            data = bytes(m.uc.mem_read(LIGHTS + at, min(n, self.size - at)))
            for k in range(len(data) // 4):
                word = data[4 * k:4 * k + 4]
                if word != SENTINEL:
                    out[(mesh, k)] = word
        return out

    def marker(self, m):
        now = self.snapshot(m)
        changed = {key: word for key, word in now.items() if self.last.get(key) != word}
        self.last = now
        if not changed:
            return None
        values = set(changed.values())
        if sorted(changed) == expected_set(self.count, self.normals) and len(values) == 1:
            return ('VLIGHT', struct.unpack('<I', values.pop())[0])
        return ('VLIGHT?', len(changed), len(values))


def native_events(events, model, count, normals):
    """Draws (with StreamMesh byte and colour), particles and per-vertex light markers, in order."""
    stream, colour, out = model[0x94], list(struct.unpack_from('<3I', model, 0x54)), []
    for e in events:
        call, args = e[0], list(e[2:])
        if call == a2.STREAM:
            stream = args[0] & 0xff
        elif call == a2.COLOR:
            colour = args[:3]
        elif call in (BODY, MESH):
            out.append((call,) + tuple(args[:8]) + (stream,) + tuple(colour))
        elif call == PARTICLE:
            out.append((PARTICLE,) + tuple(args[:13]))
        elif call == VERTEX_LIGHT:
            if expected_set(count, normals):   # a write to no entry is no write
                out.append(('VLIGHT', args[0]))
        else:
            out.append(('unexpected', call))
    return out


def native_lights(initial, events, count, normals):
    out = bytearray(initial)
    for e in events:
        if e[0] == VERTEX_LIGHT:
            for m, k in expected_set(count, normals):
                struct.pack_into('<I', out, m * LIGHT_STRIDE + 4 * k, e[2])
    return bytes(out)


class Spec:
    """One class that runs this slot code: its class id, slot entries, own worlds and other worlds, and whether the
    handler byte +0x22 matters (RENDER-WORLDS-RAKLION's validate_worlds_raklion passes Raklion's)."""

    def __init__(self, name, cls, custom, after, worlds, others, focus, gate=False):
        self.name, self.cls, self.custom, self.after = name, cls, custom, after
        self.worlds, self.others, self.focus, self.gate = worlds, others, focus, gate


TEST_AREA = Spec('121', 121, CUSTOM, AFTER, [121], [0, 2, 57, 120, 122, 140], FOCUS)


def slot_family(machine, lib, g, cases, after, focus=False, spec=TEST_AREA):
    t = v.Tally(('after_' if after else 'actions_' if focus else 'custom_') + spec.name)
    types = AFTER_TYPES if after else CUSTOM_TYPES
    for n in range(cases):
        world = g.choice(spec.worlds) if g.random() < 0.8 else g.choice(spec.others)
        typ = g.choice(list(spec.focus)) if focus else n if n <= 300 else \
            g.choice(types + ACTION_TYPES * (0 if after else 4)) if g.random() < 0.9 else g.randrange(0, 301)
        count, subs, array, records = a2.slot_meshes(g)
        normals = case_counts(g)
        for k in range(16):
            struct.pack_into('<h', array, 0x20 * k + 6, normals[k])
        o, b = a2.slot_object(g, typ), a2.slot_model(g, count)
        o[0] = g.choice([0, 1, 1, 1])
        bones = g.choice([0, 1, 6, 12, 20, 25, 30, g.randrange(0, 40)])
        actions_count = g.choice([4, 4, 2, 1, 0, 64, g.randrange(-2, 70)])
        struct.pack_into('<h', b, 0x22, bones)
        struct.pack_into('<h', b, 0x26, actions_count)
        if typ in ACTION_TYPES:   # actions 0..3 and the frame windows of 0x10..0x15
            struct.pack_into('<H', o, 0x2a, g.choice([0, 0, 1, 1, 2, 3, g.randrange(0, 70)]))
            v.put_f(o, 0xd0, v.f32(g.choice([0.0, 1.99, 2.0, 3.5, 5.0, 5.01, 8.0, 8.01, 10.99, 11.0, 12.0, 12.5, 13.0,
                                             14.0, 15.0, 16.0, 17.0, 17.01, 18.99, 19.0, 19.49, 19.5, 20.0, 96.99,
                                             97.0, 97.99, 98.0, 99.0, math.nan, g.uniform(-5, 110)])))
        time = v.f32(g.choice([0.0, g.uniform(0, 100000), g.uniform(0, 1e7), g.uniform(1e7, 3e9),
                               g.uniform(-3e9, 0)]))
        actions = bytearray(g.getrandbits(8) for _ in range(16 * a2.ACTION_COUNT))
        seed = g.randrange(2**32)
        handler = bytearray(v.fake_object())
        if spec.gate:   # the handler byte +0x22 (Raklion: its event state <= 6)
            handler[0x22] = g.choice([0, 1, 1, 2, 0xff])
        if focus:
            frames, acts, modulus, residues = spec.focus[typ]
            struct.pack_into('<H', o, 0x2a, g.choice(acts))
            v.put_f(o, 0xd0, v.f32(g.choice(frames)))
            actions_count = g.choice([4, 4, 4, 3, 2, 1])
            struct.pack_into('<h', b, 0x26, actions_count)
            seed = targeted_seed(g, modulus, residues) if g.random() < 0.8 else seed
        ra, rb = v.MsvcRand(seed), v.MsvcRand(seed)
        watch = LightWatch(count, normals)
        calls, cbones_client = [], []

        def mark(m):
            marker = watch.marker(m)
            if marker:
                calls.append(marker)

        def recorder(address):
            def stub(m):
                mark(m)
                model = bytes(m.uc.mem_read(v.MODEL, 0x100))
                calls.append((address,) + tuple(m.argument(k) for k in range(8)) + (model[0x94],) +
                             struct.unpack_from('<3I', model, 0x54))
                return (0, 32)
            return stub

        def transform(m):
            a = [m.argument(k) for k in range(4)]
            k = (a[0] - 0x6fce398) // 0x30
            assert a[0] == 0x6fce398 + 0x30 * k and a[3] == 0 and m.uc.reg_read(m.x86.UC_X86_REG_ECX) == v.MODEL
            local = struct.unpack('<3f', bytes(m.uc.mem_read(a[1], 12)))
            cbones_client.append(k)
            m.uc.mem_write(a[2], v.pack_f(*(v.f32(x + d) for x, d in zip(local, ws.bone_offset(k)))))
            return (0, 16)

        def particle(m):
            a = [m.argument(k) for k in range(8)]
            assert a[6] == 0 and a[7] == 0 and a[2] == v.OBJECTS + 0x164, a
            mark(m)
            calls.append((PARTICLE, a[0]) + v.read_vec(m, a[1]) + v.read_vec(m, a[2]) + v.read_vec(m, a[3]) +
                         (a[4], a[5], 0))
            return 0
        stubs = {BODY: recorder(BODY), MESH: recorder(MESH), w2.RAND: lambda m: ra(), TRANSFORM: transform,
                 PARTICLE: particle, vp.MODEL_CONTAINER: lambda m: v.FAKE, vp.MODEL_GET: lambda m: (v.MODEL, 4)}
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                                              am.defined_region('model', v.MODEL, bytes(b)),
                                              am.defined_region('actions', v.ACTIONS, bytes(actions),
                                                                writable=False),
                                              am.defined_region('meshes', a2.MESHES, bytes(array), writable=False),
                                              am.defined_region('subs', a2.SUBS, bytes(records), writable=False),
                                              am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                                              am.defined_region('fake', v.FAKE, bytes(handler), writable=False),
                                              am.defined_region('lights', LIGHTS, watch.initial)])
        result = v.run(machine, spec.after if after else spec.custom, [v.OBJECTS, v.MODEL, 0], regions, stubs, ecx=v.FAKE,
                       cleanup=12)
        stop = v.stopped_reason(result)
        if stop:
            t.add(False, {'case': n, 'world': world, 'type': hex(typ)}, stop)
            continue
        client_lights = result['regions']['lights']
        co = C.create_string_buffer(bytes(o), v.OBJ_SIZE)
        cb = C.create_string_buffer(bytes(b), 0x100)
        log = v.new_log()
        flags = (C.c_int16 * 16)(*(subs + [0] * (16 - len(subs))))
        rand_fn = v.RAND_FN(lambda c: rb())
        cbones = []

        def c_bone(ctx, k, local, out):
            cbones.append(k)
            for q, d in enumerate(ws.bone_offset(k)):
                out[q] = v.f32(local[q] + d)
        bone_fn = ws.BONE(c_bone)
        model = SlotModel(count, flags, 0, rand_fn, None, handler[0x22] if spec.gate else 0, bone_fn, None, bones,
                          actions_count)
        if after:
            lib.dll.mu_class_after(spec.cls, co, cb, 0, world, time, C.byref(model), C.byref(log))
            answer, client = 0, 0
        else:
            answer = 1 if lib.dll.mu_class_custom(spec.cls, co, cb, 0, world, time, C.byref(model),
                                                  C.byref(log)) else 0
            client = result['eax'] & 0xff
        events = v.log_events(log)
        mine = native_events(events, b, count, normals)
        # a light write after the last draw shows only in the region after the call
        if client_lights != watch.initial and not any(c[0] in ('VLIGHT', 'VLIGHT?') for c in calls):
            calls.append(('VLIGHT-after-draws',))
        named = (C.c_int32 * 36)()
        listed = set(named[:lib.dll.mu_world_slot_bitmaps(spec.worlds[0], typ, named)])
        textures = {c[8] for c in calls if c[0] in (BODY, MESH) and c[8] != 0xffffffff}
        bitmaps_ok = all(x in listed for x in textures if 0x7000 <= x < 0x9000)
        lights_ok = client_lights == native_lights(watch.initial, events, count, normals)
        ok = (bitmaps_ok and lights_ok and calls == mine and cbones_client == cbones and client == answer and
              ra.seed == rb.seed and result['regions']['object'] == co.raw[:v.OBJ_SIZE] and
              result['regions']['model'] == cb.raw[:0x100])
        t.count(f'answer {client}')
        t.count('drawn' if any(c[0] in (BODY, MESH) for c in calls) else 'no draw')
        if any(c[0] == PARTICLE for c in calls):
            t.count('particles')
        if any(c[0] == 'VLIGHT' for c in calls):
            t.count('per-vertex light written')
        if textures:
            t.count('bitmap meshes')
        if ra.seed != seed:
            t.count('rand drawn')
        if struct.unpack_from('<H', result['regions']['object'], 0x2c) != struct.unpack_from('<H', o, 0x2c):
            t.count('SetAction changed the action')
        if world not in spec.worlds:
            t.count('other world')
        if spec.gate and typ == 0x52 and result['regions']['object'][0xd0:0xd8] != bytes(o[0xd0:0xd8]):
            t.count('0x52 frame restarted')
        t.add(ok, {'case': n, 'world': world, 'type': hex(typ), 'client': [tuple(hex(x) if isinstance(x, int) else x
                                                                                  for x in c) for c in calls[:6]],
                   'native': [tuple(hex(x) if isinstance(x, int) else x for x in c) for c in mine[:6]],
                   'answer': (client, answer), 'lights': lights_ok, 'bitmaps': bitmaps_ok,
                   'object': result['regions']['object'] == co.raw[:v.OBJ_SIZE],
                   'model': result['regions']['model'] == cb.raw[:0x100], 'rand': ra.seed == rb.seed,
                   'bones': (cbones_client[:12], cbones[:12])})
    return t


def devias_family(machine, lib, g, cases):
    tally = w3.rng_family(machine, lib, g, cases, [2], 'devias_67')
    return tally


FAMILIES = {
    'custom_121': lambda m, l, g, n: slot_family(m, l, g, n, False),
    'actions_121': lambda m, l, g, n: slot_family(m, l, g, n, False, True),
    'after_121': lambda m, l, g, n: slot_family(m, l, g, n, True),
    'devias_67': devias_family,
}
T, K = 'world_test_area_visual.c', 'kanturu_underground.c'
MUTATIONS = [
    # the custom slot 0x00d58bd8
    ('Types 6..12 end at 11', T, 'if(t>=6&&t<=12)', 'if (t >= 6 && t <= 11)', 'custom_121'),
    ('Per-vertex light 0.25', T, 'wv_bits(0.5f)', 'wv_bits(0.25f)', 'custom_121'),
    ('Per-vertex light not written', T, 'wv_emit(s->l,MU_OBJ_CALL_VERTEX_LIGHT,s->i,half,1);', '(void)half;',
     'custom_121'),
    ('Object light blue 0.9', T, 'ta_object_light(s,1.0f,1.0f,1.0f);', 'ta_object_light(s, 1.0f, 1.0f, 0.9f);',
     'custom_121'),
    ('0x10 from frame 18', T, 'case0x10:if(mu_obj_f32(s->o,MU_OBJF_FRAME)>=19.0f)',
     'case 0x10: if (mu_obj_f32(s->o, MU_OBJF_FRAME) >= 18.0f)', 'actions_121'),
    ('0x11 split at 89', T, 'if(r<90)', 'if (r < 89)', 'actions_121'),
    ('0x11 action 3 from frame 97', T, 'a==3&&f>=98.0f', 'a == 3 && f >= 97.0f', 'actions_121'),
    ('0x13 window [11, 12.5]', T, 'f>=11.0f&&12.0f>=f', 'f >= 11.0f && 12.5f >= f', 'actions_121'),
    ('0x13 bones 12..18', T, 'k<20;', 'k < 19;', 'actions_121'),
    ('0x13 per-bone scale 1.4', T, 'ta_bone_particle(s,k,0x801c,8,1.5f);', 'ta_bone_particle(s, k, 0x801c, 8, 1.4f);',
     'custom_121'),
    ('0x13 return roll 29', T, '%40==30', '% 40 == 29', 'actions_121'),
    ('0x13 action 1 through SetAction', T, 'mu_obj_set_u16(s->o,MU_OBJF_ACTION,1);/*adirectwrite,notSetAction*/',
     'ta_set_action(s, 1);', 'actions_121'),
    ('0x14 glow without Chrome08', T, 'mesh_std(s,1,0x280,0x800a);', 'mesh_std(s, 1, 0x280, -1);', 'custom_121'),
    ('0x14 bones 8 and 10', T, '{8,11}', '{8, 10}', 'actions_121'),
    ('0x14 return roll 24', T, '%40==25', '% 40 == 24', 'actions_121'),
    ('0x15 window [4, 9]', T, 'f>=4.0f&&8.0f>=f', 'f >= 4.0f && 9.0f >= f', 'actions_121'),
    ('0x15 spark 17 scale 0.6', T, '{17,0.7f}', '{17, 0.6f}', 'actions_121'),
    ('0x15 return roll 18', T, '%40==19', '% 40 == 18', 'actions_121'),
    ('0x39 bone 2', T, 'ta_bone(s,1,p);', 'ta_bone(s, 2, p);', 'custom_121'),
    ('0x44 pulse +0.4', T, '*0.5f+0.3f,U(s)', '* 0.5f + 0.4f, U(s)', 'custom_121'),
    ('0x53 without mesh 3', T, 'mesh_self(s,3,0x42,BL(s),U(s),V(s));set_after(s);', 'set_after(s);', 'custom_121'),
    ('0x59 not flagged', T, 'case0x2e:case0x35:case0x4c:case0x59:', 'case 0x2e: case 0x35: case 0x4c:', 'custom_121'),
    ('0x52 hidden -1', T, '}body_std(s,H(s));}', '} body_std(s, -1); }', 'custom_121'),
    ('Chrome08 listed for 0x15', T, 'if(!ta_world(world)||type!=0x14||room<=0)',
     'if (!ta_world(world) || type != 0x15 || room <= 0)', 'custom_121'),
    ('Shared SetAction bound off by one', K, 'mu_move_set_action(&a,&prior,&frame,&prior_frame,count,action);',
     'mu_move_set_action(&a, &prior, &frame, &prior_frame, count + 1, action);', 'actions_121'),
    # the after slot 0x00d5a6cc
    ('After 0x4c green period 0.0016', T, 'csin(s->time*0.0015f)*0.2f+0.5f', 'csin(s->time * 0.0016f) * 0.2f + 0.5f',
     'after_121'),
    ('After 0x53 mesh 3', T, 'mesh_self(s,4,0x42', 'mesh_self(s, 3, 0x42', 'after_121'),
    ('After 0x35 not drawn', T, 'case0x2e:case0x35:body_std(s,H(s));break;', 'case 0x2e: body_std(s, H(s)); break;',
     'after_121'),
    # Devias 0x67 (0x017f9d79)
    ('Devias roll % 31', T, 'rnd(context)%32==0?1:0', 'rnd(context) % 31 == 0 ? 1 : 0', 'devias_67'),
    ('Devias at the last key + 1', T, '(int32_t)frame_whole!=(int32_t)keys-1', '(int32_t)frame_whole != (int32_t)keys',
     'devias_67'),
    ('Devias SetAction bound off by one', K, 'mu_move_set_action(&a,&prior,&frame,&prior_frame,count,action);',
     'mu_move_set_action(&a, &prior, &frame, &prior_frame, count + 1, action);', 'devias_67'),
]


def build(root):
    subprocess.run(['make', '-s', '-C', str(root / 'objects')], check=True)
    subprocess.run(['make', '-s', '-C', str(root / 'particles')], check=True)
    return Library(root / 'objects' / ('libobjects.' + v.SUFFIX),
                   root / 'particles' / ('libclient_particles.' + v.SUFFIX))


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
    machine = w2.Machine(text, data)
    names = a.only.split(',') if a.only else list(FAMILIES)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': []}
    lib = build(ROOT / 'reconstructed')
    seed = lambda name: random.Random(0x5121 + list(FAMILIES).index(name))
    for name in names:
        tally = FAMILIES[name](machine, lib, seed(name), a.cases)
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:2500], flush=True)
    if a.mutations:
        for label, file, old, new, family in MUTATIONS:
            if family not in names:
                continue
            with tempfile.TemporaryDirectory(prefix='worlds-121-mut-') as mtmp:
                root = Path(mtmp)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'particles', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                if (ROOT / 'reconstructed/deps.mk').exists():
                    shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                path = root / 'objects' / file
                s = path.read_text()
                pattern = ''.join(re.escape(ch) + r'\s*' for ch in old.replace(' ', ''))
                assert len(re.findall(pattern, s)) == 1, (label, 'the anchor must match exactly once')
                s, count = re.subn(pattern, lambda m: new, s, count=1)
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
