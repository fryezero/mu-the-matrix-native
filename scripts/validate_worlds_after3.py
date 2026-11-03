#!/usr/bin/env python3
"""RENDER-WORLDS-AFTER3 instruction comparisons (docs/research/client-worlds-after3.md).

Families (compiled C via ctypes against the pinned original under the strict Unicorn machine):
  custom_<world>   the class's custom render slot 0x38 for Temple of Arnil 133, Tormenta Island 141, Kardamahal
                   143, Swamp of Destruction 144 and 145: RenderBody/RenderMesh calls with their eight arguments,
                   the model's StreamMesh byte +0x94 and body colour +0x54 at each call, PlayBuffer and
                   AddTerrainLight requests in order with them, the object and model bytes after the call and the
                   answer (validate_worlds_after2's slot comparison, with these leaves added).
  after_<world>    the class's after render slot 0x3c, the same comparison without an answer.
  loaders          each class's bitmap loader (slot 0x24) run as client code with LoadBitmap 0x0185baac
                   recorded (sprintf 0x0095248d / 0x009619dd formatted by the stub; terrain, water and sound
                   loaders stubbed): every bitmap a slot of the world names must be registered by it with the
                   path, filter and wrap mu_world_slot_bitmap returns.
The first 301 cases of a slot family sweep the object type 0..300 (the world manager's range); the rest draw the
class's case types. rand 0x01989721 is an MSVC rand shared with the C through mu_slot_model.rand_fn; the action
frame count (model +0x30 action table record +8) is passed as mu_slot_model.action_frames.
"""
import argparse, ctypes as C, hashlib, json, random, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_particles as vp
import validate_worlds_after2 as a2

ROOT = Path(__file__).resolve().parents[1]
# world: (custom slot 0x38, after slot 0x3c, bitmap loader slot 0x24, case types)
CLASSES = {
    133: (0xd80cea, 0xd81c49, 0xd807f5, [6, 0xe, 0x1b, 0x4d, 0x4e, 0x4f, 0x50, 0x51, 0x60, 0x62, 0x63, 0x64, 0x65,
                                         0x66, 0x67, 0x7b, 0x80, 0x84, 0x86, 0x8f, 0x91, 0x92, 0x94, 0xaa]),
    141: (0xe4cbd7, 0xe4f952, 0xe4c08c, [0xc, 0x14, 0x15, 0x1e, 0x1f, 0x20, 0x22, 0x2b, 0x2c, 0x41, 0x48, 0x4b, 0x4c,
                                         0x4d, 0x4e, 0x4f, 0x50, 0x76, 0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e,
                                         0x7f, 0x80, 0x81, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d,
                                         0x8e, 0x8f, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9a, 0x9b]),
    143: (0xe0f4bc, 0xe118fd, 0xe0e5d6, [0, 4, 0x1c, 0x21, 0x6f, 0x71, 0x72, 0x73, 0x7b, 0x7e, 0x7f, 0x80, 0x81,
                                         0x82, 0x85, 0x8c, 0x96, 0x97, 0x98, 0x99, 0xaa]),
    144: (0xe46e94, 0xe48f1c, 0xe464be, [3, 4, 6, 0xb, 0xd, 0x20, 0x40, 0x4c, 0x7c, 0x7d, 0x7e, 0x7f, 0x80, 0x86,
                                         0x87, 0x89, 0x8a, 0x99]),
    145: (0xd76059, 0xd77d18, 0xd75679, [0x13, 0x2d, 0x2e, 0x31, 0x54, 0x55, 0x56, 0x57, 0x5a, 0x5b, 0x5d, 0x5f,
                                         0x61, 0x71, 0x77, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8e, 0x98, 0x99, 0xa0,
                                         0xa1, 0xa4]),
}
# types with state-dependent branches, drawn more often: 145's fading glow and sound, 141's frame window, 143's
# terrain light
FOCUS = {145: [0x99] * 8, 141: [0x2c] * 3, 143: [0x71] * 3}
BODY, MESH = a2.BODY, a2.MESH
RAND, PLAY_BUFFER, ADD_LIGHT = 0x1989721, 0xa6ac96, 0x16cacfc
SOUND_CALL, LIGHT_CALL = 0x00a6ac96, 0x016cacfc


def slot_bodies(text):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md, out = Cs(CS_ARCH_X86, CS_MODE_32), {}
    md.skipdata = True
    for w, (custom, after, loader, _) in CLASSES.items():
        for name, start in (('custom', custom), ('after', after), ('loader', loader)):
            end = start
            for ins in md.disasm(text[start - am.TEXT_BASE:start - am.TEXT_BASE + 0x2800], start):
                end = ins.address + ins.size
                if ins.mnemonic == 'ret' and text[end - am.TEXT_BASE] in (0xcc, 0x55):
                    break
            out[f'{name}_{w}'] = (start, end)
    return out


SlotModel = a2.SlotModel


class Library(a2.Library):
    def __init__(self, path):
        super().__init__(path)
        d = self.dll
        d.mu_world_slot_bitmaps.argtypes = [C.c_int32, C.c_int32, C.POINTER(C.c_int32)]


def native_events(events, model):
    """Draws (with the StreamMesh byte and colour at the call), sounds and terrain lights, in order."""
    stream, colour, out = model[0x94], list(struct.unpack_from('<3I', model, 0x54)), []
    for e in events:
        call, args = e[0], list(e[2:])
        if call == a2.STREAM:
            stream = args[0] & 0xff
        elif call == a2.COLOR:
            colour = args[:3]
        elif call in (BODY, MESH):
            out.append((call,) + tuple(args[:8]) + (stream,) + tuple(colour))
        elif call == SOUND_CALL:
            out.append((PLAY_BUFFER,) + tuple(args[:3]))
        elif call == LIGHT_CALL:
            out.append((ADD_LIGHT,) + tuple(args[:6]))
    return out


def slot_family(machine, lib, g, cases, world_cls, after):
    custom, after_addr, _, types = CLASSES[world_cls]
    t = v.Tally(('after_' if after else 'custom_') + str(world_cls))
    for n in range(cases):
        world = world_cls if g.random() < 0.9 else g.choice([world_cls - 1, world_cls + 1, 0, 128, 137, 140])
        typ = n if n <= 300 else g.choice(types + FOCUS.get(world_cls, [])) if g.random() < 0.9 else \
            g.randrange(0, 301)
        count, subs, array, records = a2.slot_meshes(g)
        o, b = a2.slot_object(g, typ), a2.slot_model(g, count)
        o[0] = g.choice([0, 1, 1, 1])                                          # live (144's after tests it)
        v.put_f(o, 0x188, v.f32(g.choice([0.0, 0.5, 0.99, 1.0, 1.02, -0.5, g.uniform(-1, 2)])))   # 145 0x99 fade
        struct.pack_into('<h', b, 0xb4, g.choice([0, 1, 2, 3, g.randrange(-40, 40)]))            # Animation frame
        struct.pack_into('<H', b, 0xa8, g.choice([0, 0, 1, 2, 2, g.randrange(0, 0x10000)]))      # model action
        if g.random() < 0.3:
            v.put_f(o, 0xdc, v.f32(g.choice([0.89, 0.9, 0.91, 0.0])))           # 145's alpha test
        actions = bytearray(g.getrandbits(8) for _ in range(16 * a2.ACTION_COUNT))
        act = struct.unpack_from('<H', o, 0x2a)[0]
        struct.pack_into('<h', actions, 16 * act + 8, g.choice([0, 1, 2, 10, 29, 30, 31, g.randrange(-5, 60)]))
        time = v.f32(g.choice([0.0, g.uniform(0, 100000), g.uniform(0, 1e7), g.uniform(1e7, 3e9)]))
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

        def play(m):
            calls.append((PLAY_BUFFER, m.argument(0), m.argument(1), m.argument(2)))
            return 0

        def light(m):
            rgb = struct.unpack('<3I', bytes(m.uc.mem_read(m.argument(2), 12)))
            calls.append((ADD_LIGHT, m.argument(0), m.argument(1)) + rgb + (m.argument(3),))
            if m.argument(4) != v.FRAME_LIGHT:
                m.stop(('light buffer', hex(m.argument(4))))
            return 0
        stubs = {BODY: recorder(BODY), MESH: recorder(MESH), RAND: lambda m: ra(), PLAY_BUFFER: play,
                 ADD_LIGHT: light}
        regions = v.global_regions(world, 6, [am.defined_region('object', v.OBJECTS, bytes(o)),
                                              am.defined_region('model', v.MODEL, bytes(b)),
                                              am.defined_region('actions', v.ACTIONS, bytes(actions),
                                                                writable=False),
                                              am.defined_region('meshes', a2.MESHES, bytes(array), writable=False),
                                              am.defined_region('subs', a2.SUBS, bytes(records), writable=False),
                                              am.defined_region('time', v.TIME, v.pack_f(time), writable=False),
                                              am.defined_region('fake', v.FAKE, v.fake_object(), writable=False)])
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
        model = SlotModel(count, flags, frames, rand_fn, None)
        if after:
            lib.dll.mu_class_after(world_cls, co, cb, 0, world, time, C.byref(model), C.byref(log))
            answer, client = 0, 0
        else:
            answer = 1 if lib.dll.mu_class_custom(world_cls, co, cb, 0, world, time, C.byref(model),
                                                  C.byref(log)) else 0
            client = result['eax'] & 0xff
        mine = native_events(v.log_events(log), b)
        named = (C.c_int32 * 36)()
        listed = set(named[:lib.dll.mu_world_slot_bitmaps(world_cls, typ, named)])
        textures = {c[8] for c in calls if c[0] in (BODY, MESH) and c[8] != 0xffffffff}
        bitmaps_ok = all(x in listed for x in textures if 0x7000 <= x < 0x9000)
        if textures:
            t.count('bitmap meshes')
        ok = (bitmaps_ok and calls == mine and client == answer and ra.seed == rb.seed and
              result['regions']['object'] == co.raw[:v.OBJ_SIZE] and result['regions']['model'] == cb.raw[:0x100])
        t.count(f'answer {client}')
        t.count('drawn' if any(c[0] in (BODY, MESH) for c in calls) else 'no draw')
        for kind, label in ((PLAY_BUFFER, 'sound'), (ADD_LIGHT, 'terrain light')):
            if any(c[0] == kind for c in calls):
                t.count(label)
        if world == world_cls and typ in types:
            t.count('case types')
        t.add(ok, {'case': n, 'world': world, 'type': hex(typ), 'client': [tuple(hex(x) for x in c) for c in calls[:6]],
                   'native': [tuple(hex(x) for x in c) for c in mine[:6]], 'answer': (client, answer),
                   'object': result['regions']['object'] == co.raw[:v.OBJ_SIZE],
                   'model': result['regions']['model'] == cb.raw[:0x100], 'rand': ra.seed == rb.seed,
                   'bitmaps': (sorted(textures), sorted(listed))})
    return t


LOAD_BITMAP, SPRINTF_S, SPRINTF = 0x185baac, 0x95248d, 0x9619dd
LOADER_LEAVES = [0x18202b4, 0x181fbe9, 0xa6ab76, 0x94997e, 0x8e83a0]   # water/terrain loads, sound load, string


def c_format(m, fmt, first):
    """printf %d/%02d/%s with the stub's stack arguments from index `first`."""
    out, k = [], first

    def repl(match):
        nonlocal k
        spec = match.group(0)
        value = m.argument(k)
        k += 1
        if spec.endswith('s'):
            return m.cstring(value)
        value = value - (1 << 32) if value & 0x80000000 else value
        return ('%' + spec[1:]) % value
    return re.sub(r'%[0-9]*[ds]', repl, fmt)


def run_loader(machine, world):
    _, _, loader, _ = CLASSES[world]
    loaded, buffers = [], {}

    def load(m):
        loaded.append((m.cstring(m.argument(0)), m.argument(1), m.argument(2), m.argument(3)))
        return 1

    def sprintf_s(m):
        text = c_format(m, m.cstring(m.argument(2)), 3).encode('latin1') + b'\0'
        m.uc.mem_write(m.argument(0), text)   # a stack buffer
        return len(text) - 1

    def sprintf(m):
        text = c_format(m, m.cstring(m.argument(1)), 2).encode('latin1') + b'\0'
        m.uc.mem_write(m.argument(0), text)   # a stack buffer
        return len(text) - 1
    stubs = {LOAD_BITMAP: load, SPRINTF_S: sprintf_s, SPRINTF: sprintf}
    for leaf in LOADER_LEAVES:
        stubs[leaf] = (lambda m: 0) if leaf not in (0x94997e,) else (lambda m: (m.uc.reg_read(m.x86.UC_X86_REG_ECX), 4))
    regions = v.global_regions(world, 6, [am.defined_region('fake', v.FAKE, v.fake_object(), writable=False)])
    result = v.run(machine, loader, [], regions, stubs, ecx=v.FAKE, cleanup=0)
    return loaded, v.stopped_reason(result)


def family_loaders(machine, lib, g, cases):
    t = v.Tally('loaders')
    for world in CLASSES:
        loaded, stop = run_loader(machine, world)
        if stop:
            t.add(False, {'world': world}, stop)
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


FAMILIES = {}
for _w in CLASSES:
    FAMILIES[f'custom_{_w}'] = (lambda w: lambda m, l, g, n: slot_family(m, l, g, n, w, False))(_w)
    FAMILIES[f'after_{_w}'] = (lambda w: lambda m, l, g, n: slot_family(m, l, g, n, w, True))(_w)
FAMILIES['loaders'] = family_loaders
W = 'world_slots_visual.c'
MUTATIONS = [
    # Temple of Arnil 133
    ('Arnil 0x1b glow scale', W, 'wave(s,-1.5f)*0.4f+0.2f;mesh_std(s,0,2,-1);grey(s,w);',
     'wave(s, -1.5f) * 0.5f + 0.2f; mesh_std(s, 0, 2, -1); grey(s, w);', 'custom_133'),
    ('Arnil 0x67 shares the 0.8 glow', W, '==0x67?0.4f:0.8f', '== 0x67 ? 0.8f : 0.8f', 'custom_133'),
    ('Arnil 0x91 restores the stream', W, 'if(last==5)stream(s,0xff);', 'stream(s, 0xff);', 'custom_133'),
    ('Arnil stream u scroll sign', W, '-t*(m==2?4.0f:2.0f)', 't * (m == 2 ? 4.0f : 2.0f)', 'custom_133'),
    ('Arnil 0x92 answers no', W, 'mesh(s,0,2,A(s),BM(s),BL(s),U(s),t,-1);return1;}default:return0;}}staticvoidarnil_after',
     'mesh(s, 0, 2, A(s), BM(s), BL(s), U(s), t, -1); return 0; } default: return 0; } } static void arnil_after', 'custom_133'),
    ('Arnil after water period', W, 'water_body(s,1000000,1e-05f)', 'water_body(s, 100000, 1e-05f)', 'after_133'),
    ('Arnil after 0x84 blend', W, 'mesh(s,1,0x42,A(s),1,BL(s),U(s),V(s),-1);break;case0x8f',
     'mesh(s, 1, 0x42, A(s), BM(s), BL(s), U(s), V(s), -1); break; case 0x8f', 'after_133'),
    ('Water frame rate', W, 'cvtt(s->time*0.015f)%32', 'cvtt(s->time * 0.016f) % 32', 'after_133'),
    ('Water object light', W, 'set_light(s,0.2f);', 'set_light(s, 0.25f);', 'after_133'),
    # Swamp of Destruction 144
    ('Swamp 0xb bitmap', W, 't==6?0x8346:0x8347', 't == 6 ? 0x8346 : 0x8346', 'custom_144'),
    ('Swamp 0xd light', W, 'mesh(s,0,2,A(s),-1,-1.0f,U(s),V(s),-1);', 'mesh(s, 0, 2, A(s), -1, 1.0f, U(s), V(s), -1);', 'custom_144'),
    ('Swamp 0x7c scroll period', W, 'tmod(s,50000,0.0002f,0)', 'tmod(s, 5000, 0.0002f, 0)', 'custom_144'),
    ('Swamp 0x89 no restore', W, "grey(s,t==0x89?w*0.5f+0.5f:w*0.4f+0.6f);mesh(s,0,2,A(s),0,BL(s),U(s),V(s),t==0x89?0x8341:0x8342);restore_color(s,k);",
     "grey(s, t == 0x89 ? w * 0.5f + 0.5f : w * 0.4f + 0.6f); mesh(s, 0, 2, A(s), 0, BL(s), U(s), V(s), t == 0x89 ? 0x8341 : 0x8342); (void)k;", 'custom_144'),
    ('Swamp 0x86 glow', W, 'changenothing*/mesh_std(s,0,2,-1);mesh(s,1,2,A(s),1,wave(s,-1.5f)*0.6f+0.3f',
     'change nothing */ mesh_std(s, 0, 2, -1); mesh(s, 1, 2, A(s), 1, wave(s, -1.5f) * 0.6f + 0.4f', 'custom_144'),
    ('Swamp after ignores live', W, 'if(!s->o[MU_OBJF_LIVE])return;', '', 'after_144'),
    ('Swamp after 0x20 scroll sign', W, 'tmod(s,100000,0.0004f,1),-1);break;case0x40', 'tmod(s, 100000, 0.0004f, 0), -1); break; case 0x40', 'after_144'),
    # 145
    ('145 alpha threshold', W, 'if(0.9f>A(s))return1;', 'if (0.8f > A(s)) return 1;', 'custom_145'),
    ('145 0x99 fade step', W, 'f+0.03f:f-0.01f', 'f + 0.03f : f - 0.02f', 'custom_145'),
    ('145 0x99 no upper clamp', W, 'f=f>1.0f?1.0f:f;', '', 'custom_145'),
    ('145 0x99 sound action', W, 'action(s)==2&&', 'action(s) == 1 &&', 'custom_145'),
    ('145 0x98 skips mesh 0xb', W, 'if(m!=0xb)mesh_std', 'if (m != 0xc) mesh_std', 'custom_145'),
    ('145 0x77 alpha factor', W, 'mesh_own(s,m,2,A(s)*wave(s,-1.5f)*0.6f+0.4f,-1)', 'mesh_own(s, m, 2, wave(s, -1.5f) * 0.6f + 0.4f, -1)', 'custom_145'),
    ('145 custom world test', W, 'returncls==145||world_test(cls,world);', 'return world_test(cls, world);', 'custom_145'),
    ('145 after 0x88 glow alpha', W, 'mesh(s,2,0x44,0.3f,2,BL(s),U(s),V(s),-1);break;case0x8e', 'mesh(s, 2, 0x44, 0.35f, 2, BL(s), U(s), V(s), -1); break; case 0x8e', 'after_145'),
    ('145 after 0x98 mesh', W, 'mesh_own(s,0xb,2,', 'mesh_own(s, 0xa, 2,', 'after_145'),
    # Kardamahal 143
    ('Kardamahal 0x71 second bitmap', W, 'mesh_own(s,1,2,BL(s),0x85ab);', 'mesh_own(s, 1, 2, BL(s), 0x85aa);', 'custom_143'),
    ('Kardamahal 0x6f glow', W, '(t==0x71?0.6f:0.3f)+(t==0x71?0.4f:0.7f)', '(t == 0x71 ? 0.6f : 0.3f) + (t == 0x71 ? 0.4f : 0.6f)', 'custom_143'),
    ('Kardamahal 0x73 restore', W, "mesh_own(s,6,2,BL(s),0x85ac);restore_color(s,k);", "mesh_own(s, 6, 2, BL(s), 0x85ac);", 'custom_143'),
    ('Kardamahal 0x7e hidden', W, 'body(s,2,BM(s),BL(s),U(s),V(s),1);', 'body(s, 2, BM(s), BL(s), U(s), V(s), -1);', 'custom_143'),
    ('Kardamahal 0x81 colour', W, 'x*0.1f,x*0.41f,x*0.8f', 'x * 0.1f, x * 0.4f, x * 0.8f', 'custom_143'),
    ('Kardamahal 0x96 stream', W, 'tmod(s,100000,8e-05f,0),V(s),-1);stream(s,0xff);', 'tmod(s, 100000, 8e-05f, 0), V(s), -1);', 'custom_143'),
    ('Kardamahal type 0 answers no', W, 'case0:case0x1c:case0x21:return1;', 'case 0x1c: case 0x21: return 1;', 'custom_143'),
    ('Kardamahal after light flags', W, 's->o[MU_OBJF_LIGHT_ENABLE]=0;', '', 'after_143'),
    ('Kardamahal after terrain light', W, '%4+3)*0.1f*0.4f', '% 4 + 2) * 0.1f * 0.4f', 'after_143'),
    ('Kardamahal after 0x85 period', W, '%3000)/3000.0f', '% 3000) / 3001.0f', 'after_143'),
    ('Kardamahal after default draws', W, '3000.0f,V(s),-1);break;default:break;}}', '3000.0f, V(s), -1); break; default: body_std(s, H(s)); break; } }', 'after_143'),
    # Tormenta Island 141
    ('Tormenta 0x97 bitmap order', W, '{0x84ca,0x84c9}', '{0x84c9, 0x84ca}', 'custom_141'),
    ('Tormenta 0x2c frame bound', W, 'frame(s)>=1.0f&&n>frame(s)', 'frame(s) >= 1.0f && n >= frame(s)', 'custom_141'),
    ('Tormenta 0x2b scroll sign', W, 'tmod(s,100000,0.0004f,1),-1);return1;case0x4b', 'tmod(s, 100000, 0.0004f, 0), -1); return 1; case 0x4b', 'custom_141'),
    ('Tormenta 0x7b glow meshes', W, 'first=t==0x7b?2:0', 'first = t == 0x7b ? 1 : 0', 'custom_141'),
    ('Tormenta 0x89 wave', W, 'wave(s,-0.8f)*0.4f+0.6f', 'wave(s, -0.8f) * 0.4f + 0.5f', 'custom_141'),
    ('Tormenta 0x8a scroll', W, 'tmod(s,100000,0.0001f,0)', 'tmod(s, 100000, 0.0001f, 1)', 'custom_141'),
    ('Tormenta 0x7c glow mesh', W, 'glow_pair(s,2,-1,5,-1);', 'glow_pair(s, 2, -1, 4, -1);', 'custom_141'),
    ('Tormenta after 0x76 blend', W, 'mesh(s,1,0x42,A(s),2,w,U(s),V(s),-1);', 'mesh(s, 1, 0x42, A(s), 1, w, U(s), V(s), -1);', 'after_141'),
    ('Tormenta after 0x4e bitmaps', W, '0x84b1+2*(t-0x4c)', '0x84b1 + 2 * (t - 0x4d)', 'after_141'),
    ('Tormenta after 0x48 mesh', W, 'mesh(s,1,0x42,A(s),1,BL(s),U(s),V(s),-1);break;case0x41', 'mesh(s, 0, 0x42, A(s), 1, BL(s), U(s), V(s), -1); break; case 0x41', 'after_141'),
    # bitmaps
    ('Water folder', W, '(int)world+1,', '(int)world,', 'loaders'),
    ('Kardamahal bitmap wrap', W, '{143,0x85ab,"Object144\\\\hsFieldLighting02_R.jpg",0x2601,0x2900}',
     '{143, 0x85ab, "Object144\\\\hsFieldLighting02_R.jpg", 0x2601, 0x2901}', 'loaders'),
    ('Swamp bitmap world', W, '{144,0x8341,', '{136, 0x8341,', 'loaders'),
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
    p.add_argument('--dump-loaders', action='store_true', help='print the LoadBitmap calls of each class loader')
    p.add_argument('--output')
    a = p.parse_args()
    text = am.load_pinned(a.text, am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(a.data, am.DATA_BYTES, am.DATA_SHA256, 'data')
    machine = vp.PtMachine(text, data)
    if a.dump_loaders:
        for world in CLASSES:
            loaded, stop = run_loader(machine, world)
            print(world, stop)
            for row in loaded:
                print('  ', hex(row[1]), row[0], hex(row[2]), hex(row[3]))
        return 0
    names = a.only.split(',') if a.only else list(FAMILIES)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': [],
              'bodies': {k: {'start': hex(b), 'end': hex(e),
                             'sha256': hashlib.sha256(text[b - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for k, (b, e) in slot_bodies(text).items()}}
    lib = build(ROOT / 'reconstructed')
    seed = lambda name: random.Random(0xaf73 + list(FAMILIES).index(name))
    for name in names:
        tally = FAMILIES[name](machine, lib, seed(name), a.cases)
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:2500], flush=True)
    if a.mutations:
        for label, file, old, new, family in MUTATIONS:
            if family not in names:
                continue
            with tempfile.TemporaryDirectory(prefix='worlds-after3-mut-') as mtmp:
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
