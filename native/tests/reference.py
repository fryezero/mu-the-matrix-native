"""Golden-data reference for the native viewer's CPU path.

The reference state is built independently of native/core/mu_model.c, through
the existing validators' case builders (scripts/validate_bone_tracks.py
build_case, validate_pose_builder.py make_setup, validate_skinning.py
tick_setup/installed_meshes/transform_setup), and run twice:

  * through the authored reconstructed libraries (libskinning: bone-track
    loop, pose builder, animation tick, transform), loaded with ctypes;
  * through the validators' independent pure-Python models (python_tick,
    python_model, python_transform).

Both must agree with each other and, byte for byte, with `mu-render dump`.
The layouts differ (other window bases, other allocators, other buffer
addresses), so equality shows the viewer feeds the reconstructed functions
the same inputs and reads their outputs correctly.
"""
import importlib.util
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
sys.path.insert(0, str(ROOT/'model-recovery'))
import bmd_encrypted  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/f'scripts/{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode(raw, client_layout=False):
    """(parsed model, decoded payload) through the Python readers."""
    model = bmd_encrypted.parse_model(raw, client_layout=client_layout)
    version = raw[3]
    if version == 10:
        plain = raw[4:]
    else:
        plain = {12: bmd_encrypted.decrypt_map, 14: bmd_encrypted.decrypt_modulus,
                 15: bmd_encrypted.decrypt_lea}[version](raw[8:])
    return model, plain


DEFAULTS = dict(action=0, frame=0.0, prior_action=0, prior_frame=0.0, ticks=0, speed=0.25, stop=0,
                scale=1.0, origin=(0.0, 0.0, 0.0), angles=(0.0, 0.0, 0.0), head=(0.0, 0.0), height=0.0,
                special=-1, lighting=1, light_angles=(0.0, 0.0, 0.0), ambient=0.4, light_scale=0.4,
                light_minimum=0.4, vertex_scale=0.0, bone_scale=1.0, world=0, scene=0, bounds_mode=0,
                override=0, pose_translate=0, translate=1)


def cli_arguments(state):
    """mu-render options for a reference state."""
    s = dict(DEFAULTS, **state)
    args = ['--action', s['action'], '--frame', s['frame'], '--prior-action', s['prior_action'],
            '--prior-frame', s['prior_frame'], '--ticks', s['ticks'], '--speed', s['speed'],
            '--scale', s['scale'], '--origin', *s['origin'], '--angles', *s['angles'], '--head', *s['head'],
            '--root-height', s['height'], '--special-bone', s['special'], '--lighting', s['lighting'],
            '--light-angles', *s['light_angles'], '--ambient', s['ambient'], '--light-scale', s['light_scale'],
            '--light-min', s['light_minimum'], '--vertex-scale', s['vertex_scale'], '--bone-scale', s['bone_scale'],
            '--world', s['world'], '--scene', s['scene'], '--bounds-mode', s['bounds_mode'],
            '--light-override', s['override'], '--pose-translate', s['pose_translate'], '--translate', s['translate']]
    if s['stop']:
        args.append('--stop')
    return [repr(a) if isinstance(a, float) else str(a) for a in args]


def read_dump(path):
    data = Path(path).read_bytes()
    assert data[:4] == b'MUVD'
    version, bones, meshes = struct.unpack_from('<III', data, 4)
    offset = 16
    result = {'bones': data[offset:offset+bones*0x30], 'meshes': []}
    offset += bones*0x30
    for _ in range(meshes):
        nv, nn = struct.unpack_from('<II', data, offset)
        offset += 8
        mesh = {}
        for name, size in (('vertices', nv*12), ('normals', nn*12), ('lights', nn*4), ('secondary', nn*4)):
            mesh[name] = data[offset:offset+size]
            offset += size
        result['meshes'].append(mesh)
    result['box'] = data[offset:offset+48]
    return result


class Reference:
    def __init__(self):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/model-codec')], check=True, capture_output=True)
        subprocess.run(['make', '-C', str(ROOT/'model-recovery')], check=True, capture_output=True)
        self.skin = _load('validate_skinning')
        self.pose = self.skin.pose
        self.tracks = self.pose.tracks
        self.authored = self.skin.Authored(ROOT/f'reconstructed/model-codec/libskinning.{SUFFIX}')

    def tick(self, model, s):
        """Chains the tick through the authored C and the Python model."""
        v = self.skin
        actions = [(1 if (s['stop'] and index == s['action']) else 0, a['keys'], int(bool(a['lock_positions'])))
                   for index, a in enumerate(model['actions'])]
        setup = v.tick_setup('tick', actions, {'current': s['action'], 'frame': v.f32(s['frame']),
                                                'speed': v.f32(s['speed']), 'scene': s['scene'],
                                                'world': s['world']})
        window = setup['regions'][0]
        window.define(v.WINDOW+0x110, struct.pack('<f', s['prior_frame']))
        window.define(v.WINDOW+0x120, struct.pack('<H', s['prior_action'] & 0xffff))
        loop = 1
        for _ in range(s['ticks']):
            native = self.authored.run_tick(setup)
            assert native['status'] == 0
            python, python_loop = v.python_tick(setup)
            assert python == native['regions'] and python_loop == native['loop'], 'tick: C and Python differ'
            window.data[:] = native['regions']['window']
            loop = native['loop']
        data = bytes(window.data)
        return {'frame': struct.unpack_from('<f', data, 0x100)[0],
                'prior_frame': struct.unpack_from('<f', data, 0x110)[0],
                'prior_action': struct.unpack_from('<H', data, 0x120)[0], 'loop': loop}

    def outputs(self, raw, state, label='model'):
        """Bone matrices and transform outputs for one state, or None when the
        viewer substitutes identity bones (no actions or a zero-key action)."""
        s = dict(DEFAULTS, **state)
        v, pose, tracks = self.skin, self.pose, self.tracks
        model, plain = decode(raw)
        actions = model['actions']
        ticked = self.tick(model, s) if actions else {'frame': v.f32(s['frame']), 'prior_frame': v.f32(s['prior_frame']),
                                                      'prior_action': s['prior_action'], 'loop': 1}
        current = s['action'] if s['action'] < len(actions) else 0
        prior = ticked['prior_action'] if ticked['prior_action'] < len(actions) else 0
        if not actions or actions[current]['keys'] <= 0 or actions[prior]['keys'] <= 0:
            return None
        keys = [a['keys'] for a in actions]
        bones = [{'dummy': int(b['dummy'])} for b in model['bones']]
        start = (model['bones'][0]['source_offset'] if model['bones'] else model['parsed_bytes'])-4
        tcase = tracks.build_case(label, keys, bones, stream=plain, start=start, suffix=b'',
                                  heap_bytes=tracks.heap_need(keys, bones))
        tcase['parsed'] = model
        seeded = pose.seed_authored(self.authored.pose, tcase)
        params = {'angles': s['angles'], 'head': s['head'], 'special': s['special'], 'scale': s['scale'],
                  'translation': s['origin'], 'height': s['height'], 'current': s['action'],
                  'locks': {a: int(bool(x['lock_positions'])) for a, x in enumerate(actions)},
                  'frame': ticked['frame'], 'prior_frame': ticked['prior_frame'],
                  'prior_action': ticked['prior_action'], 'keep_root': 0, 'translate': s['pose_translate']}
        setup = pose.make_setup(label, tcase, seeded, params)
        # The viewer's bone buffer starts zeroed; zero the declared prior matrices to match.
        image = bytearray(setup['image'])
        low, high = setup['output_span']
        image[low-0x400-v.WINDOW:high+0x400-v.WINDOW] = bytes(high-low+0x800)
        # make_setup places the angle/head arguments inside that declared span; restore them.
        angles_at, head_at = setup['arguments'][4], setup['arguments'][5]
        struct.pack_into('<3f', image, angles_at-v.WINDOW, *s['angles'])
        struct.pack_into('<2f', image, head_at-v.WINDOW, *s['head'])
        setup['image'] = bytes(image)
        built = self.authored.pose.run(setup)
        assert built['status'] == 0, 'authored pose builder failed'
        python_window, python_quaternions, _, _ = pose.python_model(setup)
        assert bytes(python_window) == built['window'], 'pose: C and Python differ'
        assert bytes(python_quaternions) == built['quaternions'], 'pose quaternions: C and Python differ'
        window = v.Region('window', v.WINDOW, built['window'], v.built_defined(setup, built))
        meshes = v.installed_meshes(window, {'parsed': model, 'stream': tcase['stream']})
        tparams = {'lighting': s['lighting'], 'body_scale': s['scale'], 'origin': s['origin'],
                   'light_angles': s['light_angles'], 'bounds_mode': s['bounds_mode'], 'world': s['world'],
                   'override': s['override'], 'bone_scale': s['bone_scale'], 'translate': s['translate'],
                   'vertex_scale': s['vertex_scale'], 'ambient': s['ambient'], 'light_scale': s['light_scale'],
                   'light_minimum': s['light_minimum']}
        tsetup = v.transform_setup(label, window, tcase['model'], low, meshes, tparams)
        native = self.authored.run_transform(tsetup)
        assert native['status'] == 0, 'authored transform failed'
        assert v.python_transform(tsetup) == native['regions'], 'transform: C and Python differ'
        regions = native['regions']
        result = {'state': ticked, 'bones': built['window'][low-v.WINDOW:high-v.WINDOW], 'meshes': []}
        for index, mesh in enumerate(model['meshes']):
            nv, nn = len(mesh['vertices']), len(mesh['normals'])
            result['meshes'].append({
                'vertices': regions.get(f'vertices:{index}', b'')[:nv*12],
                'normals': regions.get(f'normals:{index}', b'')[:nn*12],
                'lights': regions.get(f'lights:{index}', b'')[:nn*4] if s['lighting'] else None,
                'secondary': regions.get(f'secondary:{index}', b'')[:nn*4] if s['lighting'] else None})
        return result
