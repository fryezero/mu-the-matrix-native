"""Golden data for the native character assembly (NATIVE-CHAR-001).

Builds the expected `mu-render chardump` output independently of
native/core/mu_character.c and mu_model.c, from the validators' case builders
(scripts/validate_bone_tracks.py build_case, validate_pose_builder.py
make_setup, validate_skinning.py transform_setup/installed_meshes) and the
authored libraries (libcharacter: bone-track loop, pose builder, tick,
transform, rotation position), with every pose and transform also checked
against the validators' pure-Python models.

It restates the order that native/core/mu_character.h documents for the
character copy render 0x0139be7a: the Player pose (keep root 0, translate 0)
into one shared bone buffer, body parts 5..0 skinned against it (translate 1,
light 0.4/0.8/0.2), then weapons 0 and 1 and the wing: rotation position on
the link bone of the shared buffer as it is at that moment, a keep-root pose
(translate 1) into the same buffer, and a transform. Layouts, window bases
and allocators differ from the viewer's, so equality shows the viewer feeds
the reconstructed functions the same inputs in the same order.
"""
import ctypes
import struct
from pathlib import Path

import reference

ROOT = Path(__file__).resolve().parents[2]
SUFFIX = reference.SUFFIX
LIGHT = (0.4, 0.8, 0.2)          # ambient, scale, minimum (binary32 0x01a7df0c, 0x01a7df18, 0x01a7df08)
SHARED_BYTES = 200*0x30          # client bone buffer 0x06fce398 (200 bones)
WEAPON_VECTOR, WING_VECTOR = (0.0, 0.0, 0.0), (0.0, 0.0, 15.0)
LINK_BONES = {6: 33, 7: 42, 8: 47}  # item index -> Player bone (0x0137f5d9, 0x0137f5ec, 0x0139e5aa)
ITEM_FRAMES = {6: 0.0, 7: 0.0, 8: 2.0}


def read_chardump(path):
    data = Path(path).read_bytes()
    assert data[:4] == b'MUCD'
    version, bones = struct.unpack_from('<II', data, 4)
    offset = 12
    result = {'player_bones': data[offset:offset+bones*0x30], 'items': []}
    offset += bones*0x30
    for _ in range(9):
        loaded, = struct.unpack_from('<I', data, offset)
        offset += 4
        if not loaded:
            result['items'].append(None)
            continue
        count, = struct.unpack_from('<I', data, offset)
        offset += 4
        item = {'bones': data[offset:offset+count*0x30], 'meshes': []}
        offset += count*0x30
        meshes, = struct.unpack_from('<I', data, offset)
        offset += 4
        for _ in range(meshes):
            nv, nn = struct.unpack_from('<II', data, offset)
            offset += 8
            mesh = {}
            for name, size in (('vertices', nv*12), ('normals', nn*12), ('lights', nn*4), ('secondary', nn*4)):
                mesh[name] = data[offset:offset+size]
                offset += size
            item['meshes'].append(mesh)
        item['box'] = data[offset:offset+48]
        offset += 48
        result['items'].append(item)
    assert offset == len(data)
    return result


class CharacterReference(reference.Reference):
    def __init__(self):
        super().__init__()
        library = ROOT/f'reconstructed/model-codec/libcharacter.{SUFFIX}'
        self.authored = self.skin.Authored(library)
        handle = ctypes.CDLL(str(library))
        self.rotation_position = handle.mu_rotation_position
        self.rotation_position.argtypes = [ctypes.POINTER(self.skin.Authored.Memory)] + [ctypes.c_uint32]*5
        self.rotation_position.restype = ctypes.c_int

    # -- stages ------------------------------------------------------------
    def case(self, raw, label):
        model, plain = reference.decode(raw)
        keys = [a['keys'] for a in model['actions']]
        bones = [{'dummy': int(b['dummy'])} for b in model['bones']]
        start = (model['bones'][0]['source_offset'] if model['bones'] else model['parsed_bytes'])-4
        tcase = self.tracks.build_case(label, keys, bones, stream=plain, start=start, suffix=b'',
                                       heap_bytes=self.tracks.heap_need(keys, bones))
        tcase['parsed'] = model
        return tcase

    def pose_into(self, tcase, params, shared, root):
        """Authored pose into the shared buffer; returns (setup, built)."""
        v, pose = self.skin, self.pose
        seeded = pose.seed_authored(self.authored.pose, tcase)
        setup = pose.make_setup(tcase['label'], tcase, seeded, params)
        image = bytearray(setup['image'])
        low, high = setup['output_span']
        image[low-0x400-v.WINDOW:high+0x400-v.WINDOW] = bytes(high-low+0x800)
        image[low-v.WINDOW:high-v.WINDOW] = shared[:high-low]
        struct.pack_into('<3f', image, setup['arguments'][4]-v.WINDOW, *params['angles'])
        struct.pack_into('<2f', image, setup['arguments'][5]-v.WINDOW, *params['head'])
        setup['image'] = bytes(image)
        root_region = bytearray(setup['root'])
        offset = pose.ROOT_MATRIX-pose.GLOBAL_REGIONS['root'][0]
        root_region[offset:offset+48] = root
        setup['root'] = bytes(root_region)
        built = self.authored.pose.run(setup)
        assert built['status'] == 0, 'authored pose builder failed'
        window, quaternions, _, _ = pose.python_model(setup)
        assert bytes(window) == built['window'], 'pose: C and Python differ'
        shared[:high-low] = built['window'][low-v.WINDOW:high-v.WINDOW]
        root[:] = built['root'][offset:offset+48]
        return setup, built

    def transform(self, window, model, bones, tcase, params):
        v = self.skin
        meshes = v.installed_meshes(window, tcase)
        setup = v.transform_setup(tcase['label'], window, model, bones, meshes, params)
        native = self.authored.run_transform(setup)
        assert native['status'] == 0, 'authored transform failed'
        assert v.python_transform(setup) == native['regions'], 'transform: C and Python differ'
        result = []
        for index, mesh in enumerate(tcase['parsed']['meshes']):
            nv, nn = len(mesh['vertices']), len(mesh['normals'])
            r = native['regions']
            result.append({'vertices': r.get(f'vertices:{index}', b'')[:nv*12],
                           'normals': r.get(f'normals:{index}', b'')[:nn*12],
                           'lights': r.get(f'lights:{index}', b'')[:nn*4] if params['lighting'] else None,
                           'secondary': r.get(f'secondary:{index}', b'')[:nn*4] if params['lighting'] else None})
        return result

    def with_stream(self, window, tcase):
        """Appends a part's decoded stream to a window (its mesh records point there)."""
        v = self.skin
        window = window.copy()
        stream = v.align(window.end, 0x1000)
        window.data.extend(v.poison(stream-window.end, 0x7c))
        window.defined.extend(bytes(stream-window.end))
        window.data.extend(tcase['stream_bytes'])
        window.defined.extend(b'\1'*len(tcase['stream_bytes']))
        return window, dict(tcase, stream=stream)

    def root_setter(self, scale, matrix, vector, root):
        """Authored rotation position on a model with body scale `scale`."""
        v = self.skin
        window = v.Region('window', v.WINDOW, bytes(0x200))
        window.define(v.WINDOW+0x74, struct.pack('<f', scale))
        window.define(v.WINDOW+0x100, bytes(matrix))
        window.define(v.WINDOW+0x140, struct.pack('<3f', *vector))
        root_region = v.Region('root', self.pose.ROOT_MATRIX, bytes(root))
        buffers, memory = self.authored.memory([window, root_region])
        status = self.rotation_position(ctypes.byref(memory), v.WINDOW, v.WINDOW+0x100, v.WINDOW+0x140,
                                        v.WINDOW+0x180, self.pose.ROOT_MATRIX)
        assert status == 0
        out = struct.unpack_from('<3f', bytes(buffers[0][1]), 0x180)
        root[:] = bytes(buffers[1][1])
        # Independent statement: out = scale * R(matrix) * vector, root = matrix.
        m = struct.unpack('<12f', bytes(matrix))
        f = v.f32
        expected = []
        for r in range(3):
            value = f(f(f(vector[0]*m[r*4]) + f(vector[1]*m[r*4+1])) + f(vector[2]*m[r*4+2]))
            expected.append(f(scale*value))
        assert struct.pack('<3f', *expected) == struct.pack('<3f', *out), 'rotation position: C and Python differ'
        assert bytes(root) == bytes(matrix)
        return out

    # -- character ---------------------------------------------------------
    def character(self, player_raw, items, state, variant='faithful'):
        """items: {index: (raw, action)}; state: reference DEFAULTS keys plus position/scale/lighting.
        variant 'no-keep-root' rebuilds item roots from their own angles (negative control)."""
        # Character object scale: creation default 0.9 (0x0137d9dd), as mu-render without --scale.
        s = dict(reference.DEFAULTS, **dict({'scale': 0.9}, **state))
        f = self.skin.f32
        position, scale, lighting = [f(x) for x in s['origin']], f(s['scale']), s['lighting']
        shared, root = bytearray(SHARED_BYTES), bytearray(48)
        player = self.case(player_raw, 'player')
        actions = player['parsed']['actions']
        ticked = self.tick(player['parsed'], s)
        params = {'angles': tuple(s['angles']), 'head': tuple(s['head']), 'special': -1, 'scale': scale,
                  'translation': position, 'height': 0.0, 'current': s['action'],
                  'locks': {a: int(bool(x['lock_positions'])) for a, x in enumerate(actions)},
                  'frame': ticked['frame'], 'prior_frame': ticked['prior_frame'],
                  'prior_action': ticked['prior_action'], 'keep_root': 0, 'translate': 0}
        setup, built = self.pose_into(player, params, shared, root)
        player_bones = bytes(shared[:len(player['parsed']['bones'])*0x30])
        result = {'state': ticked, 'player_bones': player_bones, 'items': [None]*9}
        tparams = {'lighting': lighting, 'body_scale': scale, 'origin': position, 'translate': 1,
                   'vertex_scale': 0.0, 'ambient': LIGHT[0], 'light_scale': LIGHT[1], 'light_minimum': LIGHT[2]}
        v = self.skin
        for slot in range(5, -1, -1):
            if slot not in items:
                continue
            part = self.case(items[slot][0], f'part{slot}')
            part['stream_bytes'] = reference.decode(items[slot][0])[1]
            window = v.Region('window', v.WINDOW, bytes(0x3000))
            bones_at = v.WINDOW+0x400
            window.define(bones_at, bytes(shared))
            window.define(v.WINDOW, bytes(0x100))
            window, part = self.with_stream(window, part)
            result['items'][slot] = {'bones': b'', 'meshes': self.transform(window, v.WINDOW, bones_at, part, tparams)}
        for index in (6, 7, 8):
            if index not in items:
                continue
            raw, action = items[index]
            item_scale = f(s.get('wing_scale', scale)) if index == 8 else scale
            link = LINK_BONES[index]
            out = self.root_setter(scale, shared[link*0x30:link*0x30+48],
                                   WING_VECTOR if index == 8 else WEAPON_VECTOR, root)
            origin = [f(position[k]+out[k]) for k in range(3)]
            tcase = self.case(raw, f'item{index}')
            iactions = tcase['parsed']['actions']
            frame = ITEM_FRAMES[index]
            iparams = {'angles': (0.0, 0.0, 0.0), 'head': (0.0, 0.0), 'special': -1, 'scale': item_scale,
                       'translation': origin, 'height': 0.0, 'current': action,
                       'locks': {a: int(bool(x['lock_positions'])) for a, x in enumerate(iactions)},
                       'frame': frame, 'prior_frame': frame, 'prior_action': 0,
                       'keep_root': int(variant != 'no-keep-root'), 'translate': 1}
            isetup, ibuilt = self.pose_into(tcase, iparams, shared, root)
            low, high = isetup['output_span']
            window = v.Region('window', v.WINDOW, ibuilt['window'], v.built_defined(isetup, ibuilt))
            item_params = dict(tparams, body_scale=item_scale, origin=origin)
            result['items'][index] = {'bones': ibuilt['window'][low-v.WINDOW:high-v.WINDOW],
                                      'meshes': self.transform(window, tcase['model'], low, tcase, item_params)}
        return result
