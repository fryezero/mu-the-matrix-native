#!/usr/bin/env python3
"""Compare the native objects' per-normal light with the client's pose builder and transform (NATIVE-LIGHT-001).

For every object the native runtime draws (`mu-terrain render ... --object-steps N --light-report 1`), the
actual client routines run in Unicorn on the installed model file, chained as in scripts/validate_skinning.py:
the bone-track loop seeds the bone arrays, the pose builder 0x012b5064 runs with RenderObject's arguments
(the object's action, frame, prior frame, prior action and angle, keep-root 0, translate = the native report's
pose_translate) and the transform 0x012b5bde reads its bone matrices with the report's transform translate,
vertex scale 0 and light arguments. The client state the transform reads comes from a read of our own running
client (`mac-play/diagnostics/lightread`, a 'MULITLV1' snapshot): the light-override byte 0x01cf1048, the world
0x01cf15fc and the model's shadow angle +0x98 for the object's type (the lighting byte +0x50 is the object's +5,
which RenderObject writes before the transform). The per-normal light the client writes must equal the native
report's values bit for bit.

A negative control repeats every case with the pre-NATIVE-LIGHT-001 inputs (light override 0, the body scale
applied by the transform instead of the bones); it must differ from the native values for every object that
has a lit normal (above the light minimum), and the count of differing lit normals is reported.

Modelled, not client code: the case memory of scripts/validate_skinning.py (output arrays, the mesh record
array, bounds), and the bone-track seed. Inputs stay local (installed models, live snapshot).
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/f'scripts/{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


skin = _load('validate_skinning')
pose, tracks = skin.pose, skin.tracks


def parse_lightread(path):
    data = Path(path).read_bytes()
    if data[:8] != b'MULITLV1':
        raise ValueError(f'{path}: not a lightread snapshot')
    offset, out = 8, {'globals': {}, 'models': {}}
    while offset < len(data):
        tag, size = data[offset:offset+4].decode(), struct.unpack_from('<I', data, offset+4)[0]
        body = data[offset+8:offset+8+size]
        offset += 8+size
        if tag == 'GLOB':
            p = 0
            while p < len(body):
                address, length = struct.unpack_from('<II', body, p)
                out['globals'][address] = body[p+8:p+8+length]
                p += 8+length
        elif tag == 'MODL':
            for p in range(0, len(body), 8+0xd0):
                key = struct.unpack_from('<i', body, p)[0]
                out['models'][key] = body[p+8:p+8+0xd0]
    return out


def client_lights(machines, authored, case, row, live, override, pose_translate, transform_translate, feature):
    """Run the client's loop, pose builder and transform for one object; per-mesh light lists."""
    machine_tracks, machine_pose, machine = machines
    seeded = pose.seed_case(machine_tracks, authored.pose, case, feature)
    if not seeded['ok'] or not seeded['authored_tracks_match']:
        raise RuntimeError(f"{row['type']}: bone-track seed failed: {seeded['stopped']}")
    locks = {a: int(bool(action['lock_positions'])) for a, action in enumerate(case['parsed']['actions'])}
    params = {'current': row['action'], 'prior_action': row['prior_action'], 'frame': skin.f32(row['frame']),
              'prior_frame': skin.f32(row['prior_frame']), 'angles': tuple(skin.f32(v) for v in row['angles']),
              'scale': skin.f32(row['scale']), 'translation': tuple(skin.f32(v) for v in row['origin']),
              'keep_root': 0, 'translate': pose_translate, 'locks': locks}
    # make_setup declares its synthetic prior matrices over the angles and head slots: declare them again
    region = pose.align(len(seeded['window']), 0x1000)
    params['declare'] = [(skin.WINDOW+region, struct.pack('<3f', *params['angles'])),
                         (skin.WINDOW+region+0x20, struct.pack('<2f', 0.0, 0.0))]
    setup = pose.make_setup(f"type {row['type']}", case, seeded, params)
    built = machine_pose.run(setup)
    if not (all(built['checks'].values()) and built['stopped'] is None):
        raise RuntimeError(f"{row['type']}: pose builder stopped: {built['stopped']}")
    window = skin.Region('window', skin.WINDOW, built['window'], skin.built_defined(setup, built))
    meshes = skin.installed_meshes(window, case)
    model = live['models'].get(row['type'])
    # RenderObject's setup writes model +0x50 = object +5 right before Animation/Transform (compared in the render
    # family); the snapshot's byte is only the last object's (0 for models not drawn since load). The shadow angle
    # +0x98 and the override byte are not written by the draw path: the live values are used.
    lighting = row['lighting']
    shadow = struct.unpack_from('<3f', model, 0x98) if model else (0.0, 0.0, 0.0)
    world = struct.unpack('<i', live['globals'][0x01cf15fc])[0]
    transform_params = {'lighting': lighting, 'override': override, 'world': world, 'light_angles': shadow,
                        'translate': transform_translate, 'vertex_scale': 0.0, 'ambient': skin.f32(row['ambient']),
                        'light_scale': skin.f32(row['light_scale']), 'light_minimum': skin.f32(row['light_minimum']),
                        'body_scale': params['scale'], 'origin': params['translation']}
    transform = skin.transform_setup(setup['label'], window, case['model'], setup['output_span'][0], meshes,
                                     transform_params)
    x86 = machine.execute(skin.TRANSFORM_START, transform['arguments'], transform['regions'], ecx=transform['model'],
                          return_instruction=skin.TRANSFORM_RETURN, cleanup=0x30)
    if not all(x86['checks'].values()) or x86['stopped'] is not None:
        raise RuntimeError(f"{row['type']}: transform stopped: {x86['stopped']} {x86['checks']}")
    lights = []
    for index, mesh in enumerate(meshes):
        raw = x86['regions'].get(f'lights:{index}', b'')
        lights.append(list(struct.unpack(f"<{mesh['nn']}f", raw)) if mesh['nn'] > 0 else [])
    return lights, {'lighting': lighting, 'live_model_lighting': model[0x50] if model else None,
                    'shadow_angle': shadow, 'world': world}


def compare(native, client):
    compared = equal = 0
    for mesh, values in enumerate(native):
        for n, value in enumerate(values):
            compared += 1
            equal += struct.pack('<f', value) == struct.pack('<f', client[mesh][n])
    return compared, equal


def validate(args):
    text = tracks.load_pinned(args.text, tracks.TEXT_BYTES, tracks.TEXT_SHA256, 'restored text')
    data = tracks.load_pinned(args.data, tracks.DATA_BYTES, tracks.DATA_SHA256, 'second image section')
    flag = tracks.load_pinned(args.flag, 4, tracks.FLAG_SHA256, 'dispatch flag')
    feature = Path(args.feature).read_bytes()
    for name, (start, end, digest) in skin.BODIES.items():
        if hashlib.sha256(text[start-skin.TEXT_BASE:end-skin.TEXT_BASE]).hexdigest() != digest:
            raise ValueError(f'{name}: pinned body differs')
    live = parse_lightread(args.live)
    override_live = live['globals'][0x01cf1048][0]
    command = [str(args.terrain), 'render', str(args.game_root), '--world', str(args.world), '--objects',
               str(args.objects), '--object-steps', str(args.steps), '--light-report', '1', '--width', '64',
               '--height', '48']
    out = subprocess.run(command, capture_output=True, text=True, check=True).stdout
    rows = [json.loads(line) for line in out.splitlines() if line.startswith('{"object_light"')]
    machines = (tracks.Machine(text, data, flag, feature, args.library, None), pose.PoseMachine(text, data, flag),
                skin.SkinMachine(text, data, flag))
    authored = skin.Authored(args.library)
    cases, report = {}, []
    totals = {'objects': 0, 'normals': 0, 'equal': 0, 'negative_normals': 0, 'negative_differ': 0}
    for row in rows[:args.limit] if args.limit else rows:
        object_type = row['type']
        if object_type not in cases:
            path = Path(row['model'])
            raw = path.read_bytes()
            cases[object_type] = tracks.installed_case(path, path.name, raw)
        case = cases[object_type]
        feature_value = tracks.FEATURE_VALUES[0]
        lights, state = client_lights(machines, authored, case, row, live, override_live, row['pose_translate'],
                                      row['transform_translate'], feature_value)
        compared, equal = compare(row['lights'], lights)
        old, _ = client_lights(machines, authored, case, row, live, 0, 0, 1, feature_value)
        lit = [(m, n) for m, values in enumerate(row['lights']) for n, v in enumerate(values)
               if skin.f32(v) > skin.f32(row['light_minimum'])]
        differ = sum(struct.pack('<f', row['lights'][m][n]) != struct.pack('<f', old[m][n]) for m, n in lit)
        totals['objects'] += 1
        totals['normals'] += compared
        totals['equal'] += equal
        totals['negative_normals'] += len(lit)
        totals['negative_differ'] += differ
        report.append({'object': row['object_light'], 'type': object_type, 'scale': row['scale'],
                       'normals': compared, 'equal': equal, 'lit_normals': len(lit), 'old_inputs_differ': differ,
                       'live_state': state})
    return {'live_override': override_live, 'world': args.world, 'steps': args.steps, 'totals': totals,
            'objects': report}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--flag', type=Path, required=True)
    parser.add_argument('--feature', type=Path, required=True)
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/model-codec' /
                        ('libskinning.dylib' if sys.platform == 'darwin' else 'libskinning.so'))
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--world', type=int, required=True, help='client world index (login 94, Lorencia 0)')
    parser.add_argument('--objects', type=Path, required=True, help='local decoded EncTerrain<n>.plain')
    parser.add_argument('--live', type=Path, required=True, help='lightread snapshot of the same world')
    parser.add_argument('--terrain', type=Path, default=ROOT/'native/build/mu-terrain')
    parser.add_argument('--steps', type=int, default=25)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')
    encoded = json.dumps(result, indent=2)+'\n'
    if args.output:
        args.output.write_text(encoded)
    print(json.dumps(result['totals']))
    t = result['totals']
    controls = all(o['old_inputs_differ'] > 0 for o in result['objects'] if o['lit_normals'])
    return int(t['equal'] != t['normals'] or not controls or not t['objects'])


if __name__ == '__main__':
    sys.exit(main())
