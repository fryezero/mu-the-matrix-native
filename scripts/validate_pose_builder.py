#!/usr/bin/env python3
"""Compare the authored pose builder with the captured client instructions.

The actual builder 0x012b5064..0x012b58cb runs in Unicorn over the pinned
restored text, the verified second image section and the captured trig
dispatch flag, together with every client function it reaches: the vector
accessors, quaternion compare 0x00cfec33 with the CRT fabs chain, slerp
0x00d00ca4 with the actual acos/sin helpers, quaternion-to-matrix 0x00d008bf,
angle-to-matrix 0x00cff32a, rotation 0x00d00724 and composition 0x00cff83e.
No client instruction is stubbed and the builder reaches no import.

Every case is seeded by first running the actual bone-track loop
0x012b4225..0x012b4441 through scripts/validate_bone_tracks.py, so the per-action
position, Euler and quaternion arrays are the loop's real outputs. Modelled
explicitly (not client code):

* the two uncaptured globals the builder uses, the bone quaternion table at
  0x075a90d8 (16 bytes per bone index) and the root matrix at 0x078965ac. Both
  start as undefined poison; a case that asks to keep the root matrix supplies
  a declared synthetic matrix;
* caller memory: the output matrix buffer (with declared synthetic prior
  contents), the body/head angle vectors, the builder's model fields that the
  loader does not write (+0x60, +0x74..+0x83, +0x90, +0xa8) and the action lock
  bytes.

Any read of uncaptured bytes, of undefined window/global bytes or of caller
stack outside the eight arguments stops a case.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import math
import multiprocessing
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]


def _load_tracks():
    spec = importlib.util.spec_from_file_location('validate_bone_tracks', ROOT/'scripts/validate_bone_tracks.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tracks = _load_tracks()
WINDOW = tracks.WINDOW
TEXT_BASE, DATA_BASE = tracks.TEXT_BASE, tracks.DATA_BASE
BUILDER_START, BUILDER_END = 0x012b5064, 0x012b58ce
BODIES = {  # start, exclusive end, SHA-256 of captured bytes
    'builder': (0x012b5064, 0x012b58ce, '11a830ee49191265f3d7175caf1f9c11c45327ebd277562d30fd0e0671527d94'),
    'compare': (0x00cfec33, 0x00cfec8d, '6722b79afebb674465292e284a785c14c56f21307d69585b0d86998bd9b4dd9e'),
    'fabs_wrapper': (0x0098a647, 0x0098a65d, 'b1d366bbcdc493fe5bda59987029177526991ebc171cd4b141c0b08293176d51'),
    'fabs_inner': (0x0098a6d2, 0x0098a6f1, 'a2ca2e2c55f0166c71b660a4c7e92b19a8de867c14add0e7d26f3aeee910b7d9'),
    'crt_fabs': (0x01983660, 0x01983680, '74d303bcc4e15aa29ae0ef6bc37ed306861bc0ce37a3c0d5dba8159aa386b728'),
    'slerp': (0x00d00ca4, 0x00d0104f, '24c2020d5c829119c23ef5640567db8da50f33962fa09e959f4ab9f965127d0f'),
    'acos_wrapper': (0x0099d513, 0x0099d529, '72a6f8d0734af6b13a62545d8edac38c006bd49e336eb93c9505e82da2368884'),
    'acos_inner': (0x0099d6d5, 0x0099d6f4, 'fe7c72db87ae5a8740b6d94958fc6a778515eb7d73a2975979ae012fc2182e5c'),
    'acos_dispatch': (0x0198ae30, 0x0198ae73, 'e1f36ab76b86ce5b48f48e1dc7cb1ad2f9da4f7d7bfff9acd841265030274457'),
    'quaternion_matrix': (0x00d008bf, 0x00d00ca4, '5de131c3e991bde117771227db8f1c61e4b81bed3e9f37fb0d3831360e5bb713'),
    'angle_matrix': (0x00cff32a, 0x00cff5b4, '70ff218049521f6f14b62347ffb6bf937a8964023320f359aa1f1042dc075451'),
    'element': (0x00cfc922, 0x00cfc936, '0518ccd07aae2d4de135e2ab9c0b1c22e7898200e3c42fd1db23a397871043b5'),
    'vector': (0x00cfc94a, 0x00cfc956, '25992882b0f4cb017f9114855550dd8181349a42644f0517cc755246d09e132a'),
    'concat': (0x00cff83e, 0x00cfff3c, 'c358cd6e89029b912c7297f31c049c8383a5aa85bf6400ee77c6e033c01bcb7c'),
    'rotation': (0x00d00724, 0x00d008bf, '1d585a53f706aed8dd37de105b739b739905065deb41350a02fe83d9153e53a2'),
    'sin_wrapper': (0x009681bd, 0x009681dc, '5299f69a1ed1c228522dc86d7ce56a32ec3dcc4324d4639ca64f1712963c9ac1'),
    'cos_wrapper': (0x009fa223, 0x009fa242, '9fe1da882ace99ead520b8b5cbc8ddc3a068fa279d72553144e41eef98d4763b'),
}
ELEMENT, VECTOR, ROTATION, COMPARE, SLERP = 0x00cfc922, 0x00cfc94a, 0x00d00724, 0x00cfec33, 0x00d00ca4
QMATRIX, AMATRIX, CONCAT = 0x00d008bf, 0x00cff32a, 0x00cff83e
CALLS = {0x12b50c8: ELEMENT, 0x12b50e6: ELEMENT, 0x12b5103: ELEMENT, 0x12b53c9: ROTATION, 0x12b53d8: ROTATION,
         0x12b54fc: COMPARE, 0x12b5526: SLERP, 0x12b55b5: QMATRIX, 0x12b57ad: VECTOR, 0x12b57b3: AMATRIX,
         0x12b5824: ELEMENT, 0x12b5846: ELEMENT, 0x12b5868: ELEMENT, 0x12b5895: CONCAT, 0x12b58bc: CONCAT}
BRANCHES = {
    0x12b507c: 'no-actions-return', 0x12b5090: 'prior-action-reset', 0x12b50ab: 'current-action-reset',
    0x12b517c: 'prior-frame-negative', 0x12b518e: 'current-frame-negative', 0x12b51b1: 'prior-frame-reset',
    0x12b51db: 'current-frame-reset', 0x12b521f: 'dummy-skip', 0x12b5256: 'special-bone-euler',
    0x12b53e4: 'stored-quaternions', 0x12b5507: 'interpolate', 0x12b5530: 'copy-equal',
    0x12b561d: 'locked-root-position', 0x12b56c0: 'interpolated-position', 0x12b579f: 'root-rebuild',
    0x12b57c6: 'root-scale-translate', 0x12b5881: 'root-compose', 0x12b589f: 'child-compose',
    0xd00d52: 'slerp-negate-q', 0xd00e3d: 'slerp-spherical', 0xd00ecb: 'slerp-linear', 0xd00f38: 'slerp-opposite',
    0xcfec81: 'compare-differs', 0x19ab9e8: 'acos-sse2', 0x199a49f: 'acos-x87-fallback',
    0x19a72f8: 'sin-sse2', 0x19acd58: 'cos-sse2', 0x19997cf: 'sin-x87-fallback', 0x19996df: 'cos-x87-fallback',
}
# Return addresses inside the float wrappers, right after the client binary64
# helper returns in ST0 with its argument still at [esp].
TRIG_RETURNS = {0x9681d2: ('sin', math.sin), 0x9fa238: ('cos', math.cos), 0x99d6ea: ('acos', math.acos)}
QUATERNIONS, ROOT_MATRIX = 0x075a90d8, 0x078965ac
GLOBAL_REGIONS = {'quaternions': (0x075a9000, 0x10000), 'root': (0x07896000, 0x1000)}
STACK, STACK_BYTES = 0x31000000, 0x10000
ENTRY_ESP = STACK + 0xc000
SENTINEL = 0x7ffe0000
FPCW, MXCSR = 0x027f, 0x1f80
ARGUMENT_BYTES = 0x20
PRIOR_ACTION_SLOT = ENTRY_ESP + 0x10
HEAD_DIVISOR = 57.2957763671875  # binary32 at 0x01a85c38
DEGREES = struct.unpack('<f', struct.pack('<f', 0.017453292))[0]  # binary32 at 0x01a7fd6c
PI32 = struct.unpack('<f', struct.pack('<f', math.pi))[0]


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def from_bits(value):
    return struct.unpack('<f', struct.pack('<I', value & 0xffffffff))[0]


def align(value, boundary=16):
    return (value+boundary-1) & -boundary


def truncate32(value):
    """CVTTSS2SI."""
    if not (-2147483648.0 <= value < 2147483648.0):
        return -0x80000000
    return int(value)


def poison(size, salt):
    return bytes(((index*37+salt) & 0x7f) | 0x80 for index in range(size))


# --------------------------------------------------------------------------
# Case construction.


def seed_case(machine_tracks, authored, tcase, feature):
    """Run the actual bone-track loop; return its window and defined mask."""
    result = machine_tracks.run(tcase, feature)
    seeded = {'window': result['window'], 'defined': bytes(machine_tracks.defined),
              'ok': all(result['checks'].values()) and result['stopped'] is None and result['error'] is None,
              'stopped': result['stopped'], 'rotations': result['rotations']}
    native = authored.tracks.run(tcase)
    seeded['authored_tracks_match'] = native['status'] == 0 and native['window'] == result['window'] and \
        native['offset'] == result['offset']
    return seeded


def seed_authored(authored, tcase):
    """Portable seeding through the authored bone-track C (no emulator)."""
    native = authored.tracks.run(tcase)
    if native['status'] != 0:
        raise ValueError(f"{tcase['label']}: authored bone-track status {native['status']}")
    return {'window': native['window'], 'defined': b'\1'*len(native['window'])}


def random_matrix(generator, scale=2.0):
    return [f32(generator.uniform(-scale, scale)) for _ in range(12)]


def make_setup(label, tcase, seeded, params):
    """Window image/mask, globals and arguments for one builder call."""
    image = bytearray(seeded['window'])
    defined = bytearray(seeded['defined'])
    generator = random.Random(params.get('seed', 0))
    region = align(len(image), 0x1000)
    bones = max(tcase['bones'], 1)
    out_offset = region+0x400
    out_bytes = bones*0x30
    size = align(out_offset+out_bytes+0x400, 0x1000)
    image.extend(bytes(((index*13+0x31) & 0x7f) | 0x40 for index in range(len(image), size)))
    defined.extend(bytes(size-len(defined)))
    model = tcase['model']

    def define(address, payload):
        offset = address-WINDOW
        image[offset:offset+len(payload)] = payload
        defined[offset:offset+len(payload)] = b'\1'*len(payload)

    angles = WINDOW+region
    head = WINDOW+region+0x20
    output = WINDOW+out_offset
    define(angles, struct.pack('<3f', *params.get('angles', (0.0, 0.0, 0.0))))
    define(head, struct.pack('<2f', *params.get('head', (0.0, 0.0))))
    # Declared synthetic prior matrices across the output buffer and margins.
    prior = b''.join(struct.pack('<12f', *random_matrix(generator)) for _ in range((out_bytes+0x800)//0x30+1))
    span = (out_offset-0x400, out_offset+out_bytes+0x400)
    define(WINDOW+span[0], prior[:span[1]-span[0]])
    define(model+0x60, struct.pack('<i', params.get('special', -1)))
    define(model+0x74, struct.pack('<4f', params.get('scale', 1.0), *params.get('translation', (0.0, 0.0, 0.0))))
    define(model+0x90, struct.pack('<f', params.get('height', 0.0)))
    define(model+0xa8, struct.pack('<H', params.get('current', 0) & 0xffff))
    actions = struct.unpack_from('<I', image, model+0x30-WINDOW)[0]
    for action, flag in params.get('locks', {}).items():
        define(actions+action*16+0xa, bytes([flag]))
    if params.get('angles_alias'):
        define(model+0x84, struct.pack('<3f', *params['angles']))
        angles = model+0x84
    for address, payload in params.get('declare', []):
        define(address, payload)
    for hook in params.get('inject', []):
        hook(image, defined, tcase, define)
    quaternions = bytearray(poison(GLOBAL_REGIONS['quaternions'][1], 0x11))
    root = bytearray(poison(GLOBAL_REGIONS['root'][1], 0x23))
    quaternion_defined = bytearray(len(quaternions))
    root_defined = bytearray(len(root))
    if params.get('root_matrix') is not None:
        offset = ROOT_MATRIX-GLOBAL_REGIONS['root'][0]
        root[offset:offset+48] = struct.pack('<12f', *params['root_matrix'])
        root_defined[offset:offset+48] = b'\1'*48
    frame = params.get('frame', 0.0)
    prior_frame = params.get('prior_frame', 0.0)
    arguments = [output, frame if isinstance(frame, int) else bits(frame),
                 prior_frame if isinstance(prior_frame, int) else bits(prior_frame),
                 params.get('prior_action', 0) & 0xffffffff, angles, head,
                 params.get('keep_root', 0) & 0xffffffff, params.get('translate', 0) & 0xffffffff]
    return {'label': label, 'image': bytes(image), 'defined': bytes(defined), 'model': model,
            'quaternions': bytes(quaternions), 'quaternion_defined': bytes(quaternion_defined),
            'root': bytes(root), 'root_defined': bytes(root_defined), 'arguments': arguments,
            'output_span': (WINDOW+out_offset, WINDOW+out_offset+out_bytes), 'bones': tcase['bones']}


def track_entry(image, tcase, bone, action):
    model = tcase['model']-WINDOW
    array = struct.unpack_from('<I', image, model+0x2c)[0]
    tracks_pointer = struct.unpack_from('<I', image, array+bone*0x8c+0x24-WINDOW)[0]
    return struct.unpack_from('<3I', image, tracks_pointer+action*12-WINDOW)


def inject_quaternions(bone, action, values):
    """Overwrite seeded quaternion keys (state the loader cannot produce)."""
    def hook(image, defined, tcase, define):
        quaternions = track_entry(image, tcase, bone, action)[2]
        for key, q in enumerate(values):
            define(quaternions+key*16, struct.pack('<4f', *q))
    return hook


def declare_empty_blocks(bone, action):
    """Declare 16 bytes at each 1-byte block of a zero-key action."""
    def hook(image, defined, tcase, define):
        for index, pointer in enumerate(track_entry(image, tcase, bone, action)):
            define(pointer, struct.pack('<4f', 0.25*(index+1), -0.5, 0.125, 0.75))
    return hook


def euler_bone(generator, actions, parent=-1, dummy=0, angles=None, positions=None, spread=math.pi):
    if dummy:
        return {'dummy': dummy}
    return {'dummy': 0, 'name': b'b', 'parent': parent,
            'tracks': [((positions or (lambda k: [(f32(generator.uniform(-50, 50)), f32(generator.uniform(-50, 50)),
                                                     f32(generator.uniform(-50, 50))) for _ in range(k)]))(keys),
                        (angles or (lambda k: [(f32(generator.uniform(-spread, spread)),
                                                f32(generator.uniform(-spread, spread)),
                                                f32(generator.uniform(-spread, spread))) for _ in range(k)]))(keys))
                       for keys in actions]}


def random_params(generator, actions, bones, nonzero=None):
    nonzero = nonzero if nonzero is not None else [a for a, k in enumerate(actions) if k > 0]
    current = generator.choice(nonzero)
    prior = generator.choice(nonzero)
    keep = generator.random() < 0.3
    return {'seed': generator.randrange(1 << 30), 'current': current, 'prior_action': prior,
            'frame': f32(generator.randrange(actions[current])+generator.random()),
            'prior_frame': f32(generator.randrange(actions[prior])+generator.random()),
            'angles': tuple(f32(generator.uniform(-180, 180)) for _ in range(3)),
            'head': tuple(f32(generator.uniform(-60, 60)) for _ in range(2)),
            'special': generator.choice([-1, generator.randrange(max(bones, 1))]),
            'scale': f32(generator.uniform(0.5, 2.0)),
            'translation': tuple(f32(generator.uniform(-100, 100)) for _ in range(3)),
            'height': f32(generator.uniform(-50, 50)), 'keep_root': int(keep) | (generator.randrange(256) << 8),
            'translate': generator.randrange(2) | (generator.randrange(256) << 16),
            'root_matrix': random_matrix(generator) if keep else None}


def synthetic_groups():
    """[(label, bone-track case, [builder params ...]), ...]."""
    generator = random.Random(0x12b5064)
    groups = []

    def add(label, actions, bones, param_list, **build):
        groups.append((label, tracks.build_case(label, actions, bones, **build), param_list))

    base = {'angles': (10.0, -20.0, 30.0), 'head': (12.0, -7.0), 'scale': 1.5, 'translation': (1.0, 2.0, 3.0),
            'height': 4.0}
    # No actions: the builder returns before touching anything.
    add('no-actions', [], [euler_bone(generator, []) for _ in range(3)], [dict(base, frame=1.5)])
    # Frame boundaries on one root bone with four keys.
    frames = [0.0, 0.25, 0.5, 1.0, 1.75, 2.999, 3.0, 3.5, 3.9999998, 4.0, 4.25, 7.5, 100.75, -0.0, -0.25, -1.0,
              -1.5, -3.75, 32767.5, 1e-30]
    keys = [4]
    param_list = []
    for frame in frames:
        for prior_frame in (0.0, 2.9, 3.0, 4.0, -2.5, 9.0):
            param_list.append(dict(base, frame=f32(frame), prior_frame=f32(prior_frame), seed=len(param_list)))
    add('frame-boundaries', keys, [euler_bone(generator, keys, spread=1.2)], param_list)
    # Same-action consecutive keys: the conventional per-frame step.
    param_list = [dict(base, frame=f32(k+frac), prior_frame=f32(k), seed=k) for k in range(5) for frac in (0.0, 0.3, 0.9)]
    add('same-action-steps', [6], [euler_bone(generator, [6]), euler_bone(generator, [6], parent=0)], param_list)
    # Action indices outside the action count; upper argument bits are junk.
    param_list = [dict(base, prior_action=0xabcd0000 | prior, current=current, frame=1.5, prior_frame=0.5, seed=prior)
                  for prior in (0, 1, 2, 3, 0x7fff, 0xffff) for current in (0, 1, 2, 0x8000, 0xffff)]
    add('action-clamps', [3, 2], [euler_bone(generator, [3, 2]) for _ in range(2)], param_list)
    # Flags: only the low byte of keep_root/translate is tested.
    param_list = []
    for keep in (0, 1, 0x100, 0x1ff):
        for translate in (0, 1, 0x10000, 0xff):
            param_list.append(dict(base, frame=0.4, prior_frame=1.0, keep_root=keep, translate=translate,
                                   root_matrix=random_matrix(generator) if keep & 0xff else None, seed=keep+translate))
    roots = [euler_bone(generator, [2]), euler_bone(generator, [2], parent=0), euler_bone(generator, [2]),
             euler_bone(generator, [2], parent=2)]
    add('root-flags', [2], roots, param_list)
    # Locked root positions on prior/current action, and on a dummy bone 0.
    param_list = []
    for locks in ({}, {0: 1}, {1: 1}, {0: 1, 1: 0x80}, {1: 0xff}):
        for prior, current in ((0, 1), (1, 0), (1, 1)):
            param_list.append(dict(base, locks=locks, prior_action=prior, current=current, frame=1.25,
                                   prior_frame=2.0, seed=len(param_list)))
    add('lock-positions', [3, 3], [euler_bone(generator, [3, 3]), euler_bone(generator, [3, 3], parent=0)], param_list)
    add('lock-dummy-bone0', [3], [{'dummy': 1}, euler_bone(generator, [3])],
        [dict(base, locks={0: 1}, frame=1.5, prior_frame=0.0)])
    # Special ("head") bone: Euler path with head angles, including bone 0 + lock.
    param_list = []
    for special in (0, 1, 2, 3, -1, 99):
        for head in ((0.0, 0.0), (30.0, -45.0), (-90.0, 180.0)):
            param_list.append(dict(base, special=special, head=head, frame=1.6, prior_frame=0.0,
                                   locks={0: 1} if special == 0 else {}, seed=len(param_list)))
    add('special-bone', [3], [euler_bone(generator, [3])]+[euler_bone(generator, [3], parent=i) for i in range(3)],
        param_list)
    # Dummy bones, dummy parents, forward/self/out-of-range parents (prior slots).
    hierarchy = [euler_bone(generator, [2]), {'dummy': 1}, euler_bone(generator, [2], parent=1),
                 euler_bone(generator, [2], parent=5), euler_bone(generator, [2], parent=4),
                 euler_bone(generator, [2], parent=0), euler_bone(generator, [2], parent=-2),
                 euler_bone(generator, [2], parent=9), {'dummy': 0x80}, euler_bone(generator, [2], parent=8)]
    add('dummy-and-parents', [2], hierarchy, [dict(base, frame=f, prior_frame=0.0, seed=i)
                                              for i, f in enumerate((0.0, 0.5, 1.5))])
    # Deep chain and a branching tree.
    chain = [euler_bone(generator, [3], parent=i-1, spread=0.6) for i in range(48)]
    add('deep-chain', [3], chain, [dict(base, frame=f, prior_frame=p, seed=i)
                                   for i, (f, p) in enumerate(((0.5, 1.0), (2.75, 2.0), (1.0, 1.0)))])
    tree = [euler_bone(generator, [2, 4], parent=(i-1)//2 if i else -1) for i in range(31)]
    add('binary-tree', [2, 4], tree, [dict(base, current=1, prior_action=0, frame=f32(2.5), prior_frame=1.0),
                                      dict(base, current=0, prior_action=1, frame=f32(0.75), prior_frame=3.0,
                                           keep_root=1, root_matrix=random_matrix(generator))])
    # Hemisphere: equal rotations whose Euler angles differ by 2*pi negate q.
    flips = [(0.3, -0.4, 1.0), (f32(0.3+2*math.pi), -0.4, 1.0), (0.3, -0.4, f32(1.0-2*math.pi)),
             (0.31, -0.4, 1.0)]
    add('hemisphere', [4], [euler_bone(generator, [4], angles=lambda k: flips)],
        [dict(base, frame=f32(c+0.4), prior_frame=float(p), seed=c*4+p) for c in range(4) for p in range(4)])
    # Nearly equal quaternions around the 0.001 compare threshold.
    near = [(0.0, 0.0, 0.0), (0.0019, 0.0, 0.0), (0.0021, 0.0, 0.0), (0.0, 0.0, -0.00201), (0.0, 0.002, 0.0)]
    add('compare-threshold', [5], [euler_bone(generator, [5], angles=lambda k: near)],
        [dict(base, frame=f32(c+0.5), prior_frame=float(p), seed=c*5+p) for c in range(5) for p in range(5)])
    # Injected (non-loader) quaternions: linear and opposite slerp branches.
    # Keys 6/7: |p|^2 = 2^28 hides a-b = 4, so q is not negated and cosom = -1.
    injected = [(0.0, 0.0, 0.0, 1.0), (0.002, 0.0, 0.0, 1.0), (4096.0, 0.0, 0.0, 0.0),
                (-1/4096, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 0.0), (0.5, 0.5, 0.5, -0.5),
                (16384.0, 0.0, 0.0, 0.0), (-2.0**-14, 0.0, 0.0, 1.0)]
    add('injected-quaternions', [8], [euler_bone(generator, [8]), euler_bone(generator, [8], parent=0)],
        [dict(base, frame=f32(c+t), prior_frame=float(p),
              inject=[inject_quaternions(0, 0, injected), inject_quaternions(1, 0, injected[::-1])], seed=c*8+p)
         for c, p in ((1, 0), (0, 1), (3, 2), (2, 3), (4, 0), (0, 4), (5, 5), (5, 1), (4, 4), (7, 6), (6, 7))
         for t in (0.0, 0.3, 0.8)])
    # Zero keys: the builder reads 12/16 bytes from 1-byte blocks (declared here).
    add('zero-keys-declared', [0, 2], [euler_bone(generator, [0, 2]), euler_bone(generator, [0, 2], parent=0)],
        [dict(base, current=0, prior_action=1, frame=0.5, prior_frame=1.0,
              inject=[declare_empty_blocks(b, 0) for b in (0, 1)]),
         dict(base, current=0, prior_action=0, frame=2.5, prior_frame=-1.0, locks={0: 1},
              inject=[declare_empty_blocks(b, 0) for b in (0, 1)])])
    # Aliasing: angle argument is the model's own angle field.
    add('angles-alias', [2], [euler_bone(generator, [2])],
        [dict(base, angles_alias=True, frame=0.5, prior_frame=1.0)])
    # Wrapped int16 frame index: t becomes 65536.5 with identical quaternions.
    same = [(0.2, 0.1, -0.3)]*2
    add('frame-int16-wrap', [2], [euler_bone(generator, [2], angles=lambda k: same)],
        [dict(base, frame=f32(32768.5), prior_frame=0.0), dict(base, frame=f32(65537.25), prior_frame=1.0)])
    # Random layouts.
    for index in range(60):
        actions = [generator.randrange(1, 9) for _ in range(generator.randrange(1, 5))]
        bones = []
        for b in range(generator.randrange(1, 14)):
            if generator.random() < 0.15:
                bones.append({'dummy': generator.randrange(1, 256)})
            else:
                bones.append(euler_bone(generator, actions, parent=generator.randrange(-1, b) if b else -1,
                                        spread=generator.choice([0.3, 1.0, math.pi, 4*math.pi])))
        param_list = [random_params(generator, actions, len(bones)) for _ in range(3)]
        for params in param_list:
            if generator.random() < 0.3:
                params['locks'] = {a: generator.choice([0, 1, 0x40]) for a in range(len(actions))}
        add('random', actions, bones, param_list, stream_align=generator.randrange(16))
    return groups


def characterization_groups():
    """Inputs that leave the compared domain; recorded, never counted."""
    generator = random.Random(5)
    base = {'angles': (1.0, 2.0, 3.0), 'head': (0.0, 0.0)}
    bones = [euler_bone(generator, [0, 2]), euler_bone(generator, [0, 2], parent=0)]
    return [('zero-keys-undeclared', tracks.build_case('zero-keys', [0, 2], bones),
             [dict(base, current=0, prior_action=1, frame=0.5, prior_frame=1.0)]),
            ('huge-interpolation-factor', tracks.build_case('huge-t', [2], [euler_bone(generator, [2])]),
             [dict(base, frame=f32(40000.25), prior_frame=1.0)]),
            ('parent-outside-buffer', tracks.build_case('far-parent', [1], [euler_bone(generator, [1], parent=0x7fff)]),
             [dict(base, frame=0.0)])]


# --------------------------------------------------------------------------
# Independent Python model (third implementation and negative controls).


class PyMemory:
    def __init__(self, regions):
        self.regions = regions  # [(base, bytearray)]

    def find(self, address, size):
        for base, buffer in self.regions:
            if base <= address and address+size <= base+len(buffer):
                return buffer, address-base
        raise IndexError(hex(address))

    def u8(self, a):
        buffer, offset = self.find(a, 1)
        return buffer[offset]

    def u16(self, a):
        buffer, offset = self.find(a, 2)
        return struct.unpack_from('<H', buffer, offset)[0]

    def s16(self, a):
        buffer, offset = self.find(a, 2)
        return struct.unpack_from('<h', buffer, offset)[0]

    def u32(self, a):
        buffer, offset = self.find(a & 0xffffffff, 4)
        return struct.unpack_from('<I', buffer, offset)[0]

    def f(self, a):
        return from_bits(self.u32(a))

    def put16(self, a, v):
        buffer, offset = self.find(a, 2)
        struct.pack_into('<H', buffer, offset, v & 0xffff)

    def put32(self, a, v):
        buffer, offset = self.find(a & 0xffffffff, 4)
        struct.pack_into('<I', buffer, offset, v & 0xffffffff)

    def putf(self, a, v):
        self.put32(a, bits(v))


def py_rotation(angles):
    half = [f32(f32(a)*0.5) for a in angles]
    s = [f32(math.sin(h)) for h in half]
    c = [f32(math.cos(h)) for h in half]

    def product(a, b, d):
        return f32(f32(a*b)*d)
    return [f32(product(s[0], c[1], c[2]) - product(c[0], s[1], s[2])),
            f32(product(c[0], s[1], c[2]) + product(s[0], c[1], s[2])),
            f32(product(c[0], c[1], s[2]) - product(s[0], s[1], c[2])),
            f32(product(c[0], c[1], c[2]) + product(s[0], s[1], s[2]))]


def py_compare(a, b):
    for x, y in zip(a, b):
        if abs(f32(x-y)) > 0.001:
            return 0
    return 1


def py_slerp(p, q, t):
    """Returns (result bits, q bits after the in-place sign flips)."""
    q = list(q)
    a = b = 0.0
    for i in range(4):
        d = f32(from_bits(p[i]) - from_bits(q[i]))
        a = f32(f32(d*d) + a)
        s = f32(from_bits(p[i]) + from_bits(q[i]))
        b = f32(f32(s*s) + b)
    if a > b:
        q = [v ^ 0x80000000 for v in q]
    P = [from_bits(v) for v in p]
    Q = [from_bits(v) for v in q]
    cosom = f32(P[0]*Q[0])
    for i in range(1, 4):
        cosom = f32(cosom + f32(P[i]*Q[i]))
    if cosom + 1.0 > 1e-8:
        if 1.0 - cosom > 1e-8:
            omega = f32(math.acos(cosom))
            sinom = f32(math.sin(omega))
            sp = f32(f32(math.sin(f32((1.0-t)*omega))) / sinom)
            sq = f32(f32(math.sin(f32(t*omega))) / sinom)
        else:
            sp, sq = f32(1.0-t), t
        return [bits(f32(f32(sp*P[i]) + f32(sq*Q[i]))) for i in range(4)], q
    out = [p[1] ^ 0x80000000, p[0], p[3] ^ 0x80000000, p[2]]
    sp = f32(math.sin(f32((1.0-t)*0.5*PI32)))
    sq = f32(math.sin(f32(t*0.5*PI32)))
    for i in range(3):
        out[i] = bits(f32(f32(sp*P[i]) + f32(sq*from_bits(out[i]))))
    return out, q


def py_quaternion_matrix(q):
    x, y, z, w = (from_bits(v) for v in q)
    m = [0.0]*12
    m[0] = f32(1.0 - 2.0*y*y - 2.0*z*z)
    m[4] = f32(2.0*x*y + 2.0*w*z)
    m[8] = f32(2.0*x*z - 2.0*w*y)
    m[1] = f32(2.0*x*y - 2.0*w*z)
    m[5] = f32(1.0 - 2.0*x*x - 2.0*z*z)
    m[9] = f32(2.0*y*z + 2.0*w*x)
    m[2] = f32(2.0*x*z + 2.0*w*y)
    m[6] = f32(2.0*y*z - 2.0*w*x)
    m[10] = f32(1.0 - 2.0*x*x - 2.0*y*y)
    return m


def py_angle_matrix(angles):
    a0, a1, a2 = (f32(v*DEGREES) for v in angles)
    sy, cy = f32(math.sin(a2)), f32(math.cos(a2))
    sp, cp = f32(math.sin(a1)), f32(math.cos(a1))
    sr, cr = f32(math.sin(a0)), f32(math.cos(a0))
    return [f32(cp*cy), f32(f32(f32(sr*sp)*cy) + f32(-sy*cr)), f32(f32(f32(cr*sp)*cy) + f32(-sr*-sy)), 0.0,
            f32(cp*sy), f32(f32(f32(sr*sp)*sy) + f32(cr*cy)), f32(f32(f32(cr*sp)*sy) + f32(-sr*cy)), 0.0,
            -sp, f32(sr*cp), f32(cr*cp), 0.0]


def py_concat(memory, parent, local, destination):
    for row in range(3):
        for column in range(4):
            value = f32(memory.f(parent+row*16)*local[column])
            value = f32(value + f32(memory.f(parent+row*16+4)*local[4+column]))
            value = f32(value + f32(memory.f(parent+row*16+8)*local[8+column]))
            if column == 3:
                value = f32(value + memory.f(parent+row*16+12))
            memory.putf(destination+row*16+column*4, value)


def python_model(setup, variant='faithful'):
    """Independent restatement. Variants 'lerp' and 'modulo-wrap' are negative controls."""
    window = bytearray(setup['image'])
    quaternions = bytearray(setup['quaternions'])
    root = bytearray(setup['root'])
    m = PyMemory([(WINDOW, window), (GLOBAL_REGIONS['quaternions'][0], quaternions),
                  (GLOBAL_REGIONS['root'][0], root)])
    output, frame_bits, prior_bits, prior_arg, angles, head, keep, translate = setup['arguments']
    model = setup['model']
    prior_slot = prior_arg
    if m.s16(model+0x26) <= 0:
        return window, quaternions, root, prior_slot
    prior = prior_slot & 0xffff
    if prior >= m.s16(model+0x26):
        prior = 0
        prior_slot &= 0xffff0000
    if m.u16(model+0xa8) >= m.s16(model+0x26):
        m.put16(model+0xa8, 0)
    for k in range(3):
        m.put32(model+0x84+4*k, m.u32(angles+4*k))
    m.put32(model+0xac, frame_bits)
    m.put16(model+0xb4, truncate32(from_bits(frame_bits)))
    t = f32(m.f(model+0xac) - float(m.s16(model+0xb4)))
    complement = f32(1.0 - t)
    prior_frame = truncate32(from_bits(prior_bits))
    actions = m.u32(model+0x30)
    if variant == 'modulo-wrap':
        prior_keys = m.s16(actions+prior*16+8)
        prior_frame = prior_frame % prior_keys if prior_keys > 0 else 0
        current_keys = m.s16(actions+m.u16(model+0xa8)*16+8)
        index = m.s16(model+0xb4)
        m.put16(model+0xb4, index % current_keys if current_keys > 0 else 0)
    else:
        prior_frame = max(prior_frame, 0)
        if m.s16(model+0xb4) < 0:
            m.put16(model+0xb4, 0)
        if prior_frame >= m.s16(actions+prior*16+8):
            prior_frame = 0
        if m.s16(model+0xb4) >= m.s16(actions+m.u16(model+0xa8)*16+8):
            m.put16(model+0xb4, 0)
    index = 0
    while index < m.s16(model+0x22):
        bone = (m.u32(model+0x2c)+index*0x8c) & 0xffffffff
        if m.u8(bone+0x22):
            index += 1
            continue
        e1 = (prior*12 + m.u32(bone+0x24)) & 0xffffffff
        e2 = (m.u16(model+0xa8)*12 + m.u32(bone+0x24)) & 0xffffffff
        current = m.s16(model+0xb4)
        if index == struct.unpack('<i', struct.pack('<I', m.u32(model+0x60)))[0]:
            a1 = [m.f(m.u32(e1+4)+prior_frame*12+4*k) for k in range(3)]
            a2 = [m.f(m.u32(e2+4)+current*12+4*k) for k in range(3)]
            hx, hy = f32(m.f(head)/HEAD_DIVISOR), f32(m.f(head+4)/HEAD_DIVISOR)
            a1[0], a2[0], a1[2], a2[2] = f32(a1[0]-hx), f32(a2[0]-hx), f32(a1[2]-hy), f32(a2[2]-hy)
            q1 = [bits(v) for v in py_rotation(a1)]
            q2 = [bits(v) for v in py_rotation(a2)]
        else:
            q1 = [m.u32(m.u32(e1+8)+prior_frame*16+4*k) for k in range(4)]
            q2 = [m.u32(m.u32(e2+8)+current*16+4*k) for k in range(4)]
        slot = (QUATERNIONS + (index << 4)) & 0xffffffff
        if variant == 'lerp':
            result = [bits(f32(f32(from_bits(a)*complement) + f32(from_bits(b)*t))) for a, b in zip(q1, q2)]
        elif not py_compare([from_bits(v) for v in q1], [from_bits(v) for v in q2]):
            result = py_slerp(q1, q2, t)[0]
        else:
            result = q1
        for k in range(4):
            m.put32(slot+4*k, result[k])
        local = py_quaternion_matrix([m.u32(slot+4*k) for k in range(4)])
        p1 = (m.u32(e1)+prior_frame*12) & 0xffffffff
        p2 = (m.u32(e2)+current*12) & 0xffffffff
        locked = index == 0 and (m.u8(actions+prior*16+0xa) or m.u8(actions+m.u16(model+0xa8)*16+0xa))
        if locked:
            # Raw copies of the current action's key-0 x and y.
            local[3] = from_bits(m.u32(m.u32(e2)))
            local[7] = from_bits(m.u32(m.u32(e2)+4))
            local[11] = f32(f32(f32(m.f(p1+8)*complement) + f32(m.f(p2+8)*t)) + m.f(model+0x90))
        else:
            for row in range(3):
                local[row*4+3] = f32(f32(m.f(p1+4*row)*complement) + f32(m.f(p2+4*row)*t))
        parent = m.s16(bone+0x20)
        destination = (output+index*0x30) & 0xffffffff
        if parent == -1:
            if not keep & 0xff:
                matrix = py_angle_matrix([m.f(model+0x84+4*k) for k in range(3)])
                for k, value in enumerate(matrix):
                    m.putf(ROOT_MATRIX+4*k, value)
                if translate & 0xff:
                    for row in range(3):
                        for column in range(3):
                            field = ROOT_MATRIX+row*16+column*4
                            m.putf(field, f32(m.f(field)*m.f(model+0x74)))
                    for row in range(3):
                        m.put32(ROOT_MATRIX+row*16+12, m.u32(model+0x78+row*4))
            parent_address = ROOT_MATRIX
        else:
            parent_address = (output+parent*0x30) & 0xffffffff
        py_concat(m, parent_address, local, destination)
        index += 1
    return window, quaternions, root, prior_slot


# --------------------------------------------------------------------------
# Emulator.


class PoseMachine:
    def __init__(self, text, data, flag):
        from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
                             UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_FETCH_UNMAPPED, UC_PROT_READ, UC_PROT_WRITE,
                             UC_PROT_EXEC, UC_MEM_WRITE)
        from unicorn import x86_const as x86
        self.x86, self.UC_MEM_WRITE = x86, UC_MEM_WRITE
        self.RW = UC_PROT_READ | UC_PROT_WRITE
        self.ACCESS = UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, tracks.TEXT_BYTES, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, align(tracks.DATA_BYTES, 4096), UC_PROT_READ)
        uc.mem_write(DATA_BASE, data)
        page = tracks.FLAG_ADDRESS & ~0xfff
        uc.mem_map(page, 4096, UC_PROT_READ)
        uc.mem_write(tracks.FLAG_ADDRESS, flag)
        uc.hook_add(UC_HOOK_MEM_READ, self.flag_read, begin=page, end=page+4095)
        for name, (base, size) in GLOBAL_REGIONS.items():
            uc.mem_map(base, size, self.RW)
            uc.hook_add(self.ACCESS, self.tracked, name, begin=base, end=base+size-1)
        uc.mem_map(STACK, STACK_BYTES, self.RW)
        uc.hook_add(self.ACCESS, self.caller_stack, begin=ENTRY_ESP, end=STACK+STACK_BYTES-1)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED, self.unmapped)
        for address in BRANCHES:
            uc.hook_add(UC_HOOK_CODE, self.branch, begin=address, end=address)
        for address in (ROTATION, COMPARE, SLERP, QMATRIX, AMATRIX, CONCAT):
            uc.hook_add(UC_HOOK_CODE, self.call, begin=address, end=address)
        for address in TRIG_RETURNS:
            uc.hook_add(UC_HOOK_CODE, self.trig_result, begin=address, end=address)
        self.window_hook, self.mapped_window = None, 0
        self.preserved = {x86.UC_X86_REG_EBX: 0x12345678, x86.UC_X86_REG_ESI: 0x3456789a,
                          x86.UC_X86_REG_EDI: 0x456789ab, x86.UC_X86_REG_EBP: 0x56789abc}

    def stop(self, reason):
        if self.state['stopped'] is None:
            self.state['stopped'] = reason
        self.uc.emu_stop()

    def pc(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_EIP)

    def flag_read(self, uc, access, address, size, value, ignored):
        if not (tracks.FLAG_ADDRESS <= address and address+size <= tracks.FLAG_ADDRESS+4):
            self.stop(('uncaptured-read', hex(address), size, hex(self.pc())))

    def tracked(self, uc, access, address, size, value, name):
        base, defined, written = self.regions[name]
        offset = address-base
        if access == self.UC_MEM_WRITE:
            defined[offset:offset+size] = b'\1'*size
            if written is not None:
                written[offset:offset+size] = b'\1'*size
            return
        if b'\0' in defined[offset:offset+size]:
            self.stop(('undefined-read', name, hex(address), size, hex(self.pc())))
            return
        if written is not None:
            low, high = self.output_span
            if address < high and address+size > low and b'\0' in written[offset:offset+size]:
                self.state['prior_output_reads'] += 1

    def caller_stack(self, uc, access, address, size, value, ignored):
        pc = self.pc()
        if address == ENTRY_ESP and size == 4 and access != self.UC_MEM_WRITE and pc == self.return_instruction:
            return
        if address >= ENTRY_ESP+4 and address+size <= ENTRY_ESP+4+self.argument_bytes:
            if access != self.UC_MEM_WRITE:
                self.state['argument_reads'] += 1
                return
            if (address, size) in self.allowed_writes:
                self.state['argument_writes'].append((hex(address), size, hex(pc)))
                return
        self.stop(('caller-stack', hex(address), size, access == self.UC_MEM_WRITE, hex(pc)))

    def unmapped(self, uc, access, address, size, value, ignored):
        self.stop(('unmapped', hex(address), size, hex(self.pc())))
        return False

    def branch(self, uc, address, size, ignored):
        name = BRANCHES[address]
        self.state['branches'][name] = self.state['branches'].get(name, 0)+1

    def call(self, uc, address, size, ignored):
        name = hex(address)
        self.state['calls'][name] = self.state['calls'].get(name, 0)+1

    def trig_result(self, uc, address, size, ignored):
        """Characterize the host-libm substitution against the client result."""
        name, host = TRIG_RETURNS[address]
        x86 = self.x86
        argument = struct.unpack('<d', uc.mem_read(uc.reg_read(x86.UC_X86_REG_ESP), 8))[0]
        top = (uc.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7
        mantissa, exponent = uc.reg_read(getattr(x86, f'UC_X86_REG_FP{top}'))
        value = math.ldexp(mantissa, (exponent & 0x7fff)-16383-63) if mantissa else 0.0
        value = -value if exponent & 0x8000 else value
        expected = host(argument)
        entry = self.state['trig'].setdefault(name, [0, 0, 0, 0])
        entry[0] += 1
        if struct.pack('<d', value) != struct.pack('<d', expected):
            entry[1] += 1
            ulps = abs(struct.unpack('<q', struct.pack('<d', value))[0]-struct.unpack('<q', struct.pack('<d', expected))[0])
            entry[3] = max(entry[3], ulps)
        if struct.pack('<f', value) != struct.pack('<f', expected):
            entry[2] += 1
            self.state['trig_binary32_differences'].append((name, argument.hex(), value.hex(), expected.hex()))

    def map_window(self, size):
        uc = self.uc
        if self.mapped_window != size:
            if self.window_hook is not None:
                uc.hook_del(self.window_hook)
            if self.mapped_window:
                uc.mem_unmap(WINDOW, self.mapped_window)
            uc.mem_map(WINDOW, size, self.RW)
            self.window_hook = uc.hook_add(self.ACCESS, self.tracked, 'window', begin=WINDOW, end=WINDOW+size-1)
            self.mapped_window = size

    def execute(self, start, arguments, image, defined, globals_state, *, ecx=0xdeadbeef, return_instruction,
                allowed_writes=(), output_span=(0, 0), cleanup=0):
        uc, x86 = self.uc, self.x86
        self.map_window(len(image))
        uc.mem_write(WINDOW, image)
        self.regions = {'window': (WINDOW, bytearray(defined), bytearray(len(image)))}
        for name, (base, size) in GLOBAL_REGIONS.items():
            payload, mask = globals_state[name]
            uc.mem_write(base, payload)
            self.regions[name] = (base, bytearray(mask), None)
        self.output_span = output_span
        self.return_instruction = return_instruction
        self.argument_bytes = 4*len(arguments)
        self.allowed_writes = set(allowed_writes)
        self.state = {'stopped': None, 'branches': {}, 'calls': {}, 'prior_output_reads': 0,
                      'argument_reads': 0, 'argument_writes': [], 'trig': {}, 'trig_binary32_differences': []}
        uc.mem_write(STACK, b'\xa5'*STACK_BYTES)
        uc.mem_write(ENTRY_ESP, struct.pack('<I', SENTINEL)+b''.join(struct.pack('<I', a) for a in arguments))
        for register, value in self.preserved.items():
            uc.reg_write(register, value)
        uc.reg_write(x86.UC_X86_REG_EAX, 0xdeadbeef)
        uc.reg_write(x86.UC_X86_REG_EDX, 0xdeadbeef)
        uc.reg_write(x86.UC_X86_REG_ECX, ecx)
        for index in range(8):
            lane = 0x7ff4dead5eed0000+index*0x0101010101
            uc.reg_write(getattr(x86, f'UC_X86_REG_XMM{index}'), lane | (lane << 64))
        uc.reg_write(x86.UC_X86_REG_ESP, ENTRY_ESP)
        uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        uc.reg_write(x86.UC_X86_REG_FPCW, FPCW)
        uc.reg_write(x86.UC_X86_REG_FPSW, 0)
        uc.reg_write(x86.UC_X86_REG_FPTAG, 0xffff)
        uc.reg_write(x86.UC_X86_REG_MXCSR, MXCSR)
        error = None
        try:
            uc.emu_start(start, SENTINEL, timeout=600000000, count=0)
        except Exception as failure:  # UcError
            error = str(failure)
        state = self.state
        returned = self.pc() == SENTINEL and state['stopped'] is None and error is None
        checks = {'returned': returned,
                  'esp': uc.reg_read(x86.UC_X86_REG_ESP) == ENTRY_ESP+4+cleanup,
                  'callee_saved': all(uc.reg_read(r) == v for r, v in self.preserved.items()),
                  'direction_flag': (uc.reg_read(x86.UC_X86_REG_EFLAGS) >> 10) & 1 == 0,
                  'fpcw': uc.reg_read(x86.UC_X86_REG_FPCW) == FPCW,
                  'mxcsr_control': uc.reg_read(x86.UC_X86_REG_MXCSR) & ~0x3f == MXCSR,
                  'x87_top': (uc.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7 == 0}
        result = {'checks': checks, 'error': error, 'stopped': state['stopped'],
                  'window': bytes(uc.mem_read(WINDOW, len(image))),
                  'eax': uc.reg_read(x86.UC_X86_REG_EAX), 'x87_tag': uc.reg_read(x86.UC_X86_REG_FPTAG),
                  'arguments': list(struct.unpack('<%dI' % len(arguments),
                                                  uc.mem_read(ENTRY_ESP+4, 4*len(arguments)))),
                  'branches': state['branches'], 'calls': state['calls'],
                  'prior_output_reads': state['prior_output_reads'], 'argument_writes': state['argument_writes'],
                  'trig': state['trig'], 'trig_binary32_differences': state['trig_binary32_differences']}
        for name, (base, size) in GLOBAL_REGIONS.items():
            result[name] = bytes(uc.mem_read(base, size))
        return result

    def run(self, setup):
        return self.execute(BUILDER_START, setup['arguments'], setup['image'], setup['defined'],
                            {'quaternions': (setup['quaternions'], setup['quaternion_defined']),
                             'root': (setup['root'], setup['root_defined'])},
                            ecx=setup['model'], return_instruction=0x12b58cb,
                            allowed_writes=[(PRIOR_ACTION_SLOT, 2)], output_span=setup['output_span'],
                            cleanup=ARGUMENT_BYTES)


class Authored:
    class Image(ctypes.Structure):
        _fields_ = [('bytes', ctypes.c_void_p), ('base', ctypes.c_uint32), ('size', ctypes.c_uint32)]

    class Memory(ctypes.Structure):
        pass

    class Arguments(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint32) for name in ('output', 'frame', 'prior_frame', 'prior_action', 'angles',
                                                          'head_angles', 'keep_root', 'translate')]

    class Globals(ctypes.Structure):
        _fields_ = [('bone_quaternions', ctypes.c_uint32), ('root_matrix', ctypes.c_uint32)]

    Memory._fields_ = [('regions', ctypes.POINTER(Image)), ('count', ctypes.c_uint32)]

    def __init__(self, library):
        handle = ctypes.CDLL(str(library))
        self.build = handle.mu_pose_build
        self.build.argtypes = [ctypes.POINTER(self.Memory), ctypes.c_uint32, ctypes.POINTER(self.Arguments),
                               ctypes.POINTER(self.Globals)]
        self.build.restype = ctypes.c_int
        self.tracks = tracks.Authored(library)
        self.compare = handle.mu_quaternion_compare
        self.compare.argtypes, self.compare.restype = [ctypes.c_void_p]*2, ctypes.c_int
        self.slerp = handle.mu_quaternion_slerp
        self.slerp.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_void_p]
        self.slerp.restype = None
        self.quaternion_matrix = handle.mu_quaternion_matrix
        self.quaternion_matrix.argtypes, self.quaternion_matrix.restype = [ctypes.c_void_p]*2, None
        self.angle_matrix = handle.mu_angle_matrix
        self.angle_matrix.argtypes, self.angle_matrix.restype = [ctypes.c_void_p]*2, None

    def run(self, setup):
        buffers = [(WINDOW, (ctypes.c_ubyte*len(setup['image'])).from_buffer_copy(setup['image']))]
        for name in ('quaternions', 'root'):
            payload = setup[name]
            buffers.append((GLOBAL_REGIONS[name][0], (ctypes.c_ubyte*len(payload)).from_buffer_copy(payload)))
        images = (self.Image*3)(*[self.Image(ctypes.addressof(b), base, len(b)) for base, b in buffers])
        memory = self.Memory(images, 3)
        arguments = self.Arguments(*setup['arguments'])
        status = self.build(ctypes.byref(memory), setup['model'], ctypes.byref(arguments),
                            ctypes.byref(self.Globals(QUATERNIONS, ROOT_MATRIX)))
        return {'status': status, 'window': bytes(buffers[0][1]), 'quaternions': bytes(buffers[1][1]),
                'root': bytes(buffers[2][1]), 'prior_action': arguments.prior_action}


# --------------------------------------------------------------------------
# Comparison driver.


def finite_outputs(setup, window):
    """Whether every output matrix value written by the call is finite."""
    low, high = setup['output_span']
    values = struct.unpack_from('<%df' % ((high-low)//4), window, low-WINDOW)
    return all(math.isfinite(v) for v in values)


def compare_setup(setup, machine, authored, negative=True):
    x86 = machine.run(setup)
    native = authored.run(setup)
    python = python_model(setup)
    expected_slot = native['prior_action']
    checks = dict(x86['checks'], native_status=native['status'] == 0,
                  window=native['window'] == x86['window'],
                  quaternion_table=native['quaternions'] == x86['quaternions'],
                  root_matrix=native['root'] == x86['root'],
                  prior_action_slot=x86['arguments'][3] == expected_slot,
                  other_arguments=x86['arguments'][:3]+x86['arguments'][4:] ==
                  setup['arguments'][:3]+setup['arguments'][4:],
                  python_model=(bytes(python[0]), bytes(python[1]), bytes(python[2]), python[3]) ==
                  (x86['window'], x86['quaternions'], x86['root'], x86['arguments'][3]))
    result = {'label': setup['label'], 'checks': checks, 'match': all(checks.values()),
              'stopped': x86['stopped'], 'error': x86['error'], 'branches': x86['branches'], 'calls': x86['calls'],
              'prior_output_reads': x86['prior_output_reads'], 'bones': setup['bones'], 'trig': x86['trig'],
              'trig_binary32_differences': x86['trig_binary32_differences'],
              'finite_outputs': finite_outputs(setup, x86['window'])}
    if negative:
        result['negatives'] = {}
        for variant in ('lerp', 'modulo-wrap'):
            wrong = python_model(setup, variant)
            result['negatives'][variant] = (bytes(wrong[0]), bytes(wrong[1]), bytes(wrong[2]), wrong[3]) != \
                (x86['window'], x86['quaternions'], x86['root'], x86['arguments'][3])
    if not result['match']:
        diffs = [i for i, (a, b) in enumerate(zip(native['window'], x86['window'])) if a != b]
        result['first_window_difference'] = hex(WINDOW+diffs[0]) if diffs else None
        result['window_difference_count'] = len(diffs)
        qd = [i for i, (a, b) in enumerate(zip(native['quaternions'], x86['quaternions'])) if a != b]
        result['first_quaternion_difference'] = hex(GLOBAL_REGIONS['quaternions'][0]+qd[0]) if qd else None
    return result


def run_group(label, tcase, param_list, machine_tracks, machine, authored, feature, negative=True):
    seeded = seed_case(machine_tracks, authored, tcase, feature)
    results = []
    if not seeded['ok']:
        return [{'label': label, 'seed_failed': seeded['stopped'], 'match': False, 'checks': {}, 'branches': {},
                 'calls': {}, 'prior_output_reads': 0, 'bones': tcase['bones']}]
    for index, params in enumerate(param_list):
        setup = make_setup(label, tcase, seeded, params)
        result = compare_setup(setup, machine, authored, negative)
        result['seed_authored_tracks_match'] = seeded['authored_tracks_match']
        result['match'] = result['match'] and seeded['authored_tracks_match']
        results.append(result)
    return results


# Direct helper comparisons ---------------------------------------------------

def helper_cases():
    generator = random.Random(0xd00ca4)

    def unit(scale=1.0):
        v = [generator.gauss(0, 1) for _ in range(4)]
        n = math.sqrt(sum(x*x for x in v)) or 1.0
        return [f32(scale*x/n) for x in v]
    slerps = []
    for _ in range(600):
        p, q = unit(), unit()
        slerps.append((p, q, f32(generator.uniform(-0.5, 1.5))))
    for _ in range(200):  # close pairs
        p = unit()
        q = [f32(x+generator.uniform(-0.01, 0.01)) for x in p]
        slerps.append((p, q, f32(generator.random())))
    for _ in range(100):  # opposite hemisphere
        p = unit()
        slerps.append((p, [f32(-x+generator.uniform(-1e-3, 1e-3)) for x in p], f32(generator.random())))
    slerps += [([0, 0, 0, 1], [0.002, 0, 0, 1], 0.3), ([4096, 0, 0, 0], [-1/4096, 0, 0, 1], 0.25),
               ([4096, 1, 2, 0], [-1/4096, 0, 0, 1], 0.75), ([0, 0, 0, 0], [0, 0, 0, 0], 0.5),
               ([1, 0, 0, 0], [1, 0, 0, 0], 0.5), ([0, 0, 0, 1], [0, 0, 0, -1], 0.5), ([0.5]*4, [0.5]*4, 2.0),
               ([0, 0, 0, 1], [0, 0, 1, 0], 0.0), ([0, 0, 0, 1], [0, 0, 1, 0], 1.0), ([0, 0, 0, 1], [0, 0, 1, 0], -0.0)]
    compares = []
    for _ in range(300):
        p = unit()
        compares.append((p, [f32(x+generator.choice([0, 1e-4, -9.99e-4, 1.001e-3, 0.002, -0.5])*(i == generator.randrange(4)))
                             for i, x in enumerate(p)]))
    compares += [([0, 0, 0, 0], [0.001, 0, 0, 0]), ([0, 0, 0, 0], [f32(0.001), 0, 0, 0]),
                 ([0, 0, 0, 0], [0, 0, 0, 0.0010000001]), ([1, 2, 3, 4], [1, 2, 3, 4])]
    matrices = [unit(generator.choice([1.0, 0.5, 3.0])) for _ in range(300)] + [[0, 0, 0, 0], [0, 0, 0, 1]]
    angles = [[f32(generator.uniform(-720, 720)) for _ in range(3)] for _ in range(300)]
    angles += [[0, 0, 0], [90, 0, 0], [0, 90, 0], [0, 0, 90], [-0.0, 180, -180], [1e4, -3e4, 4.9e6]]
    return slerps, compares, matrices, angles


def run_helpers(machine, authored):
    slerps, compares, matrices, angles = helper_cases()
    base = WINDOW+0x100
    results = {'slerp': [0, 0], 'compare': [0, 0], 'quaternion_matrix': [0, 0], 'angle_matrix': [0, 0]}
    failures = []
    branches = {}
    trig = {}
    empty = {name: (bytes(size), bytes(size)) for name, (b, size) in GLOBAL_REGIONS.items()}

    returns = {SLERP: 0xd0104e, COMPARE: 0xcfec8c, QMATRIX: 0xd00ca3, AMATRIX: 0xcff5b3}

    def go(name, start, arguments, image, defined_spans, check):
        defined = bytearray(len(image))
        for low, high in defined_spans:
            defined[low-WINDOW:high-WINDOW] = b'\1'*(high-low)
        x86 = machine.execute(start, arguments, image, defined, empty, return_instruction=returns[start])
        ok = all(x86['checks'].values()) and check(x86)
        results[name][0] += 1
        results[name][1] += int(ok)
        for key, value in x86['branches'].items():
            branches[key] = branches.get(key, 0)+value
        for key, value in x86['trig'].items():
            entry = trig.setdefault(key, [0, 0, 0, 0])
            for k in range(3):
                entry[k] += value[k]
            entry[3] = max(entry[3], value[3])
        if not ok and len(failures) < 12:
            failures.append({'helper': name, 'arguments': [hex(a) for a in arguments], 'stopped': x86['stopped'],
                             'checks': x86['checks'], 'error': x86['error']})

    for p, q, t in slerps:
        image = bytearray(0x1000)
        struct.pack_into('<4f4f', image, 0x100, *p, *q)
        out = bytearray(16)
        pb, qb = ctypes.create_string_buffer(bytes(image[0x100:0x110]), 16), \
            ctypes.create_string_buffer(bytes(image[0x110:0x120]), 16)
        ob = ctypes.create_string_buffer(16)
        authored.slerp(pb, qb, t, ob)
        py_out, py_q = py_slerp(list(struct.unpack('<4I', pb.raw)), list(struct.unpack_from('<4I', image, 0x110)), t)
        del out

        def check(x86, pb=pb, qb=qb, ob=ob, py_out=py_out, py_q=py_q):
            w = x86['window']
            return (w[0x110:0x120] == qb.raw and w[0x120:0x130] == ob.raw and w[0x100:0x110] == pb.raw and
                    struct.pack('<4I', *py_out) == ob.raw and struct.pack('<4I', *py_q) == qb.raw)
        go('slerp', SLERP, [base, base+0x10, bits(t), base+0x20], bytes(image), [(base, base+0x20)], check)
    for a, b in compares:
        image = bytearray(0x1000)
        struct.pack_into('<4f4f', image, 0x100, *a, *b)
        expected = authored.compare(ctypes.create_string_buffer(bytes(image[0x100:0x110])),
                                    ctypes.create_string_buffer(bytes(image[0x110:0x120])))
        python = py_compare(struct.unpack_from('<4f', image, 0x100), struct.unpack_from('<4f', image, 0x110))
        go('compare', COMPARE, [base, base+0x10], bytes(image), [(base, base+0x20)],
           lambda x86, e=expected, p=python: x86['eax'] == e == p)
    for q in matrices:
        image = bytearray(0x1000)
        struct.pack_into('<4f', image, 0x100, *q)
        sentinel = bytes(range(0x40, 0x70))
        image[0x120:0x150] = sentinel
        mb = ctypes.create_string_buffer(sentinel, 48)
        authored.quaternion_matrix(ctypes.create_string_buffer(bytes(image[0x100:0x110])), mb)
        python = py_quaternion_matrix(list(struct.unpack_from('<4I', image, 0x100)))
        expect_py = bytearray(sentinel)
        for k in (0, 1, 2, 4, 5, 6, 8, 9, 10):
            struct.pack_into('<f', expect_py, 4*k, python[k])
        go('quaternion_matrix', QMATRIX, [base, base+0x20], bytes(image), [(base, base+0x10)],
           lambda x86, mb=mb, e=bytes(expect_py): x86['window'][0x120:0x150] == mb.raw == e)
    for a in angles:
        image = bytearray(0x1000)
        struct.pack_into('<3f', image, 0x100, *a)
        mb = ctypes.create_string_buffer(48)
        authored.angle_matrix(ctypes.create_string_buffer(bytes(image[0x100:0x10c])), mb)
        python = struct.pack('<12f', *py_angle_matrix(list(struct.unpack_from('<3f', image, 0x100))))
        go('angle_matrix', AMATRIX, [base, base+0x20], bytes(image), [(base, base+0x0c)],
           lambda x86, mb=mb, e=python: x86['window'][0x120:0x150] == mb.raw == e)
    return {'cases': results, 'failures': failures, 'branches': branches, 'trig': trig}


# Installed models -----------------------------------------------------------

_WORKER = {}


def installed_params(case, digest, index):
    generator = random.Random(int(digest[:16], 16))
    actions = [a['keys'] for a in case['parsed']['actions']]
    bones = len(case['parsed']['bones'])
    locks = {a: int(bool(action['lock_positions'])) for a, action in enumerate(case['parsed']['actions'])}
    nonzero = [a for a, k in enumerate(actions) if k > 0]
    if not actions:
        return [('no-actions', {'frame': 1.0})]
    if not nonzero:
        return []
    samples = []
    for kind in ('same-action', 'blend', 'wrap', 'integer'):
        params = random_params(generator, actions, bones, nonzero)
        params['locks'] = locks
        if kind == 'same-action':
            params['prior_action'] = params['current']
        elif kind == 'wrap':
            keys = actions[params['current']]
            params['frame'] = f32(keys+generator.choice([0.0, 0.5, 0.999]) if generator.random() < 0.5
                                  else keys-1+generator.random())
            params['prior_frame'] = f32(actions[params['prior_action'] & 0xffff]+generator.random())
        elif kind == 'integer':
            params['prior_action'] = params['current']
            params['frame'] = f32(generator.randrange(actions[params['current']]))
            params['prior_frame'] = params['frame']
        samples.append((kind, params))
    return samples


def worker_init(paths):
    text = Path(paths['text']).read_bytes()
    data = Path(paths['data']).read_bytes()
    flag = Path(paths['flag']).read_bytes()
    feature = Path(paths['feature']).read_bytes()
    _WORKER['tracks'] = tracks.Machine(text, data, flag, feature, paths['library'], None)
    _WORKER['machine'] = PoseMachine(text, data, flag)
    _WORKER['authored'] = Authored(paths['library'])
    _WORKER['samples'] = paths['samples']


def worker_model(job):
    index, path, relative = job
    raw = Path(path).read_bytes()
    try:
        case = tracks.installed_case(path, relative, raw)
    except Exception as error:  # reader rejection or decode error
        return {'label': relative, 'version': raw[3], 'reader_error': str(error)}
    digest = hashlib.sha256(raw).hexdigest()
    samples = installed_params(case, digest, index)
    version = case['version']
    limit = _WORKER['samples'].get(str(version), 4)
    if len(samples) > limit:
        offset = index % len(samples)
        samples = [samples[(offset+k*len(samples)//limit) % len(samples)] for k in range(limit)]
    summary = {'label': relative, 'version': version, 'sha256': digest, 'bones': len(case['parsed']['bones']),
               'samples': len(samples), 'zero_key_actions': sum(a['keys'] == 0 for a in case['parsed']['actions'])}
    if not samples:
        summary['skipped'] = 'only zero-key actions'
        summary['results'] = []
        return summary
    results = run_group(relative, case, [p for _, p in samples], _WORKER['tracks'], _WORKER['machine'],
                        _WORKER['authored'], tracks.FEATURE_VALUES[index % len(tracks.FEATURE_VALUES)],
                        negative=False)
    for (kind, _), result in zip(samples, results):
        result['kind'] = kind
    summary['results'] = [{k: r[k] for k in ('match', 'branches', 'calls', 'prior_output_reads', 'stopped',
                                             'finite_outputs', 'kind', 'trig', 'trig_binary32_differences')
                           if k in r} |
                          ({} if r['match'] else {'checks': r['checks'], 'detail': {k: r.get(k) for k in (
                              'first_window_difference', 'window_difference_count', 'first_quaternion_difference',
                              'seed_failed', 'error')}})
                          for r in results]
    return summary


def installed_jobs(root, versions):
    return tracks.installed_jobs(root, versions)


def summarize(results):
    summary = {'cases': len(results), 'matches': sum(bool(r['match']) for r in results), 'by_label': {},
               'branches': {}, 'calls': {}, 'prior_output_reads': 0, 'cases_reading_prior_output': 0, 'bones': 0,
               'nonfinite_outputs': sum(not r.get('finite_outputs', True) for r in results),
               'trig': {}, 'trig_binary32_differences': []}
    for r in results:
        entry = summary['by_label'].setdefault(r['label'] if '/' not in r['label'] else 'installed', [0, 0])
        entry[0] += 1
        entry[1] += int(bool(r['match']))
        for field in ('branches', 'calls'):
            for name, count in r.get(field, {}).items():
                summary[field][name] = summary[field].get(name, 0)+count
        for name, value in r.get('trig', {}).items():
            entry = summary['trig'].setdefault(name, [0, 0, 0, 0])
            for k in range(3):
                entry[k] += value[k]
            entry[3] = max(entry[3], value[3])
        summary['trig_binary32_differences'] += r.get('trig_binary32_differences', [])[:4]
        summary['prior_output_reads'] += r.get('prior_output_reads', 0)
        summary['cases_reading_prior_output'] += int(bool(r.get('prior_output_reads', 0)))
        summary['bones'] += r.get('bones', 0)
    summary['failures'] = [r for r in results if not r['match']][:12]
    return summary


def validate(text, data, flag, feature, library, game_root=None, versions=(12, 14), workers=1, samples=None):
    payload = tracks.load_pinned(text, tracks.TEXT_BYTES, tracks.TEXT_SHA256, 'restored text')
    data_payload = tracks.load_pinned(data, tracks.DATA_BYTES, tracks.DATA_SHA256, 'second image section')
    flag_payload = tracks.load_pinned(flag, 4, tracks.FLAG_SHA256, 'dispatch flag')
    feature_payload = tracks.load_pinned(feature, 4, tracks.FEATURE_SHA256, 'memcpy feature word')
    for name, (start, end, digest) in BODIES.items():
        if hashlib.sha256(payload[start-TEXT_BASE:end-TEXT_BASE]).hexdigest() != digest:
            raise ValueError(f'Pinned {name} body mismatch')
    for name, (start, end, digest) in tracks.BODIES.items():
        if hashlib.sha256(payload[start-TEXT_BASE:end-TEXT_BASE]).hexdigest() != digest:
            raise ValueError(f'Pinned bone-track {name} body mismatch')
    for address, expected in ((0x1a7dd48, struct.pack('<f', 1.0)), (0x1a85c38, struct.pack('<f', HEAD_DIVISOR)),
                              (0x1a7fd6c, struct.pack('<f', DEGREES)), (0x1aa1f78, struct.pack('<d', 0.001)),
                              (0x1aa1f70, struct.pack('<d', 1e-8)), (0x1aa1f88, struct.pack('<d', PI32)),
                              (0x1a89120, struct.pack('<d', 2.0)), (0x1a7dd50, struct.pack('<d', 1.0)),
                              (0x1a7de98, struct.pack('<d', 0.5))):
        if data_payload[address-DATA_BASE:address-DATA_BASE+len(expected)] != expected:
            raise ValueError(f'Constant at {address:#x} changed')
    import unicorn
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86 import X86_OP_IMM
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    decoded = list(decoder.disasm(payload[BUILDER_START-TEXT_BASE:BUILDER_END-TEXT_BASE], BUILDER_START))
    if sum(item.size for item in decoded) != BUILDER_END-BUILDER_START or decoded[-1].mnemonic != 'ret' or \
            decoded[-1].op_str != '0x20':
        raise ValueError('Builder decode does not land on its ret 0x20')
    calls = {item.address: item.operands[0].imm for item in decoded
             if item.mnemonic == 'call' and item.operands[0].type == X86_OP_IMM}
    if calls != CALLS or any(item.mnemonic == 'call' and item.address not in CALLS for item in decoded):
        raise ValueError('Builder call targets changed')
    library = Path(library).resolve(strict=True)
    machine_tracks = tracks.Machine(payload, data_payload, flag_payload, feature_payload, library, None)
    machine = PoseMachine(payload, data_payload, flag_payload)
    authored = Authored(library)

    helpers = run_helpers(machine, authored)
    synthetic = []
    for number, (label, tcase, param_list) in enumerate(synthetic_groups()):
        synthetic += run_group(label, tcase, param_list, machine_tracks, machine, authored,
                               tracks.FEATURE_VALUES[number % 3])
    characterization = []
    for label, tcase, param_list in characterization_groups():
        seeded = seed_case(machine_tracks, authored, tcase, 0)
        for params in param_list:
            setup = make_setup(label, tcase, seeded, params)
            x86 = machine.run(setup)
            native = authored.run(setup)
            characterization.append({'label': label, 'seeded': seeded['ok'],
                                     'emulator_returned': x86['checks']['returned'],
                                     'emulator_stopped': x86['stopped'], 'authored_status': native['status'],
                                     'windows_equal': native['window'] == x86['window']})
    negatives = {variant: sum(r.get('negatives', {}).get(variant, False) for r in synthetic)
                 for variant in ('lerp', 'modulo-wrap')}
    report = {'text_sha256': tracks.TEXT_SHA256, 'data_sha256': tracks.DATA_SHA256,
              'flag_sha256': tracks.FLAG_SHA256,
              'bodies': {name: {'start': hex(s), 'end_exclusive': hex(e), 'sha256': d}
                         for name, (s, e, d) in BODIES.items()},
              'builder_calls': {hex(a): hex(t) for a, t in CALLS.items()},
              'unicorn': unicorn.__version__,
              'authored_library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
              'fpcw': hex(FPCW), 'mxcsr': hex(MXCSR), 'helpers': helpers,
              'synthetic': summarize(synthetic), 'negative_controls': negatives,
              'characterization': characterization}
    if game_root:
        jobs = installed_jobs(game_root, versions)
        paths = {'text': str(text), 'data': str(data), 'flag': str(flag), 'feature': str(feature),
                 'library': str(library), 'samples': samples or {}}
        if workers > 1:
            with multiprocessing.get_context('spawn').Pool(workers, worker_init, (paths,)) as pool:
                models = pool.map(worker_model, jobs, chunksize=4)
        else:
            worker_init(paths)
            models = [worker_model(job) for job in jobs]
        compared = [r for m in models if 'reader_error' not in m for r in m['results']]
        for m in models:
            for r in m.get('results', []):
                r['label'] = m['label']
                r['bones'] = m['bones']
        per_version = {}
        for m in models:
            entry = per_version.setdefault(str(m['version']), {'files': 0, 'reader_rejected': 0, 'models_compared': 0,
                                                              'models_matching': 0, 'calls': 0, 'matches': 0,
                                                              'zero_key_only': 0, 'bones': 0})
            entry['files'] += 1
            if 'reader_error' in m:
                entry['reader_rejected'] += 1
                continue
            if m.get('skipped'):
                entry['zero_key_only'] += 1
                continue
            entry['models_compared'] += 1
            entry['models_matching'] += int(all(r['match'] for r in m['results']))
            entry['calls'] += len(m['results'])
            entry['matches'] += sum(bool(r['match']) for r in m['results'])
            entry['bones'] += m['bones']*len(m['results'])
        report['installed'] = dict(summarize(compared), per_version=per_version,
                                   reader_rejected=[m['label'] for m in models if 'reader_error' in m],
                                   max_bones=max((m.get('bones', 0) for m in models), default=0),
                                   models_over_200_bones=sum(m.get('bones', 0) > 200 for m in models),
                                   models_with_zero_key_actions=sum(bool(m.get('zero_key_actions')) for m in models),
                                   corpus_sha256=hashlib.sha256('\n'.join(
                                       f"{m['label']}\t{m.get('sha256', '')}" for m in models).encode()).hexdigest())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--flag', type=Path, required=True)
    parser.add_argument('--feature', type=Path, required=True, help='math-capture cpu-features.bin')
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/model-codec' /
                        ('libposebuilder.dylib' if sys.platform == 'darwin' else 'libposebuilder.so'))
    parser.add_argument('--game-root', type=Path)
    parser.add_argument('--versions', default='12,14')
    parser.add_argument('--samples', default='12:4,14:4,15:4',
                        help='builder calls per installed model, per version')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    samples = dict(item.split(':') for item in args.samples.split(',') if item)
    samples = {key: int(value) for key, value in samples.items()}
    try:
        result = validate(args.text, args.data, args.flag, args.feature, args.library, args.game_root,
                          tuple(int(v) for v in args.versions.split(',')), args.workers, samples)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(result, indent=2)+'\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')
    synthetic = result['synthetic']
    helpers = result['helpers']['cases']
    failed = synthetic['matches'] != synthetic['cases'] or not all(result['negative_controls'].values())
    failed = failed or any(total != matched for total, matched in helpers.values())
    if 'installed' in result:
        failed = failed or result['installed']['matches'] != result['installed']['cases']
    return int(bool(failed))


if __name__ == '__main__':
    sys.exit(main())
