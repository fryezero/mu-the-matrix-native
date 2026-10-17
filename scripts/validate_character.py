#!/usr/bin/env python3
"""Compare the authored character-assembly helpers with the client.

Executed with Unicorn over the pinned restored text and verified second image
section (scripts/validate_skinning.py SkinMachine boundaries):

* rotation position 0x012b7019 (thiscall, ret 0xc) with its vector rotate
  0x00d000ad: the root setter that copies a parent bone matrix into the root
  global 0x078965ac;
* transform position 0x012b6ef1 (thiscall, ret 0x10) with vector transform
  0x00d002b2 and the element accessor 0x00cfc922;
* the class helpers 0x0139d6a2 (skin index; calls 0x0095f5cc and 0x0139cb8a),
  0x0139cb8a (tier) and 0x0139d89f (tier-2 skip) for all 256 class bytes;
* the body-part loop of the player model loader 0x01830b79..0x01830ec9, with
  AccessModel 0x018202b4 replaced by a recorder of its four arguments (the
  only modelled callee; 0x0139d89f runs as client code).

Chains (with --game-root): the actual bone-track loop and the actual pose
builder pose Player.bmd into a bone buffer; the actual transform 0x012b5bde
then skins every class body-part model against those shared matrices, as the
character render 0x0139be7a does. Linked items run the actual rotation
position on a Player hand bone, the actual pose builder with keep-root set
and translate set, then the actual transform. Every stage is compared with the
authored C (libcharacter) and, for the transform, the Python model.

Modelled explicitly (not client code): the AccessModel recorder, the
uncaptured globals declared by the skinning/pose validators, caller memory
(matrices, vectors, outputs, model fields +0x74..+0x83) and the root global,
which starts undefined.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/f'scripts/{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


skin = _load('validate_skinning')
pose = skin.pose
tracks = pose.tracks
WINDOW = tracks.WINDOW
TEXT_BASE, DATA_BASE = tracks.TEXT_BASE, tracks.DATA_BASE
Region = skin.Region
f32, bits, from_bits, poison, align = skin.f32, skin.bits, skin.from_bits, skin.poison, skin.align
ROOT_MATRIX, ROOT_REGION = pose.ROOT_MATRIX, pose.GLOBAL_REGIONS['root']

BODIES = {  # start, exclusive end, SHA-256 of captured bytes
    'rotation_position': (0x012b7019, 0x012b70f2, '29fece51006b9eac4517ef431f3578dd2f2fc5c1a37a5d389888b52791903e4e'),
    'transform_position': (0x012b6ef1, 0x012b7019, '542654674242dba17bd70e51be567cd836b25011fcecab55bbaecc25ec88f9f0'),
    'skin_index': (0x0139d6a2, 0x0139d6da, '4f90c1b6dac9d02601995bc4755a494200c0021cce59b07c6b603969550f32d1'),
    'class_tier': (0x0139cb8a, 0x0139cbe1, '7d0629010928caeab71f43b9755f5406355c514c6dd86abfd4816fdd51a91eee'),
    'skips_tier2': (0x0139d89f, 0x0139d8ea, '295cb25d2e634bd3bc323e9d30d5f6c4b5d0c9407ae15bc06209040185bd1653'),
    'class_nibble': (0x0095f5cc, 0x0095f5d7, '0ccb64b405499edf6e0778c5493520acecf7b9d1c8421c7ae277ca472664df46'),
    'part_loader_prefix': (0x01830aa6, 0x01830ee2, 'b95847b19165e9a02efb6f69e232692d1f4905b8a49dded80213a3a837c7b4b8'),
    # Static readings (not executed), pinned so the documented reading stays tied to the bytes.
    'character_copy_render': (0x0139be7a, 0x0139ca62, 'bfde4515b3566e6245da38374203342b948c995df76e5178b0be2b3b40d255c8'),
    'part_types': (0x01395473, 0x01395741, 'e142deae979a760d3788ce0843ae3b9c4b94d0cfc2f423c1dddd8096741a18f9'),
    'access_model': (0x018202b4, 0x018203e0, '2ccfd840d72e312b2fd4129b22c90bbc3213eb4b0cf88c59a2a61129444b7e1b'),
    'character_create': (0x0137d8a1, 0x0137f5f6, '722b7eb1ac9911d52c4672698ef295aab4d76c66cba9219072288b46f845987d'),
    'owner_bone': (0x0129f12c, 0x0129f18a, 'b2f844e57633a623c5095e1d2185c27bc686dfa9ccbdf603fcad19dd051e0c3e'),
}
ROTATION_POSITION, TRANSFORM_POSITION = 0x012b7019, 0x012b6ef1
SKIN_INDEX, CLASS_TIER, SKIPS_TIER2 = 0x0139d6a2, 0x0139cb8a, 0x0139d89f
LOADER_LOOP, LOADER_DONE, ACCESS_MODEL = 0x01830b79, 0x01830ec9, 0x018202b4
STRINGS = {0x1aef904: '%s.bmd', 0x1aef968: '%s0%d.bmd', 0x1aef994: '%s%d.bmd'}  # AccessModel formats
LIGHT_ARGUMENTS = (0.4, 0.8, 0.2)  # ambient, scale, minimum: binary32 0x01a7df0c, 0x01a7df18, 0x01a7df08
WEAPON_BONES = {'right': 33, 'left': 42}
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


# --------------------------------------------------------------------------
# Authored C (libcharacter carries the character helpers and the skinning stack).


class Authored(skin.Authored):
    def __init__(self, library):
        super().__init__(library)
        handle = ctypes.CDLL(str(library))
        self.rotation_position = handle.mu_rotation_position
        self.rotation_position.argtypes = [ctypes.POINTER(self.Memory)] + [ctypes.c_uint32]*5
        self.rotation_position.restype = ctypes.c_int
        self.transform_position = handle.mu_transform_position
        self.transform_position.argtypes = [ctypes.POINTER(self.Memory)] + [ctypes.c_uint32]*5
        self.transform_position.restype = ctypes.c_int
        for name in ('class_tier', 'skin_index', 'skips_tier2'):
            function = getattr(handle, f'mu_character_{name}')
            function.argtypes, function.restype = [ctypes.c_uint8], ctypes.c_uint8
            setattr(self, name, function)
        self.part_file = handle.mu_character_part_file
        self.part_file.argtypes = [ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t]
        self.part_file.restype = ctypes.c_int

    def run_position(self, setup):
        buffers, memory = self.memory(setup['regions'])
        if setup['routine'] == 'rotation':
            matrix, vector, out = setup['arguments']
            status = self.rotation_position(ctypes.byref(memory), setup['model'], matrix, vector, out, ROOT_MATRIX)
        else:
            matrix, vector, out, world = setup['arguments']
            status = self.transform_position(ctypes.byref(memory), setup['model'], matrix, vector, out, world)
        return {'status': status, 'regions': {r.name: bytes(b) for r, b in buffers}}

    def file_for(self, type_):
        buffer = ctypes.create_string_buffer(64)
        return buffer.value.decode() if self.part_file(type_, buffer, 64) else None


# --------------------------------------------------------------------------
# Independent Python models.


def py_rotate(m, v, translate=False):
    out = []
    for r in range(3):
        value = f32(f32(f32(v[0]*m[r*4]) + f32(v[1]*m[r*4+1])) + f32(v[2]*m[r*4+2]))
        out.append(f32(value + m[r*4+3]) if translate else value)
    return out


def python_position(setup, variant='faithful'):
    regions = {r.name: bytearray(r.data) for r in setup['regions']}
    bases = {r.name: r.base for r in setup['regions']}

    def locate(address, size):
        for name, data in regions.items():
            if bases[name] <= address and address+size <= bases[name]+len(data):
                return data, address-bases[name]
        raise IndexError(hex(address))

    def get(address):
        data, offset = locate(address, 4)
        return struct.unpack_from('<I', data, offset)[0]

    def put(address, value):
        data, offset = locate(address, 4)
        struct.pack_into('<I', data, offset, value & 0xffffffff)

    model = setup['model']
    matrix, vector, out = setup['arguments'][:3]
    if matrix:
        m = [from_bits(get(matrix+4*k)) for k in range(12)]
        v = [from_bits(get(vector+4*k)) for k in range(3)]
        if setup['routine'] == 'rotation':
            t = py_rotate(m, v)
            for k in range(3):
                scale = 1.0 if variant == 'unscaled' else from_bits(get(model+0x74))
                put(out+4*k, bits(f32(scale*t[k])))
            for k in range(12):
                put(ROOT_MATRIX+4*k, get(matrix+4*k))
        elif setup['arguments'][3] & 0xff:
            t = [f32(from_bits(get(model+0x74))*x) for x in py_rotate(m, v, True)]
            for k in range(3):
                put(out+4*k, bits(f32(t[k]+from_bits(get(model+0x78+4*k)))))
        else:
            # Written straight to out: each component rereads its inputs (sequential aliasing).
            for r in range(3):
                m = [from_bits(get(matrix+4*k)) for k in range(12)]
                v = [from_bits(get(vector+4*k)) for k in range(3)]
                put(out+4*r, bits(py_rotate(m, v, True)[r]))
    return {name: bytes(data) for name, data in regions.items()}


def py_tier(value):
    flags = (value >> 4) & 0xf
    if not flags:
        return 1
    return max(bit for bit in range(4) if flags >> bit & 1)+2


def py_skin(value):
    return ((value & 0xf) + ((py_tier(value)-1) << 4)) & 0xff


def py_skips(value):
    return int(value & 0xf in (3, 4, 6, 7))


# --------------------------------------------------------------------------
# Direct cases for the two position routines.


def position_setup(label, routine, generator, *, matrix=None, vector=None, scale=None, origin=None, world=1,
                   alias=None, null=False):
    data = bytearray(poison(0x400, 0x5a))
    defined = bytearray(0x400)
    window = Region('window', WINDOW, data, defined)
    model = WINDOW
    window.define(model+0x74, struct.pack('<4f', f32(scale if scale is not None else generator.uniform(-3, 3)),
                                          *[f32(x) for x in (origin or [generator.uniform(-500, 500)
                                                                        for _ in range(3)])]))
    matrix_at, vector_at, out_at = WINDOW+0x100, WINDOW+0x200, WINDOW+0x300
    m = matrix or [f32(generator.uniform(-2, 2)) if k % 4 != 3 else f32(generator.uniform(-200, 200))
                   for k in range(12)]
    window.define(matrix_at, struct.pack('<12f', *m))
    window.define(vector_at, struct.pack('<3f', *[f32(x) for x in (vector or [generator.uniform(-50, 50)
                                                                              for _ in range(3)])]))
    if alias == 'out-vector':
        out_at = vector_at
    elif alias == 'out-matrix':
        out_at = matrix_at+0x10
    root = Region('root', ROOT_REGION[0], poison(ROOT_REGION[1], 0x23), bytes(ROOT_REGION[1]))
    regions = [window, root]
    if alias == 'root-matrix':
        matrix_at = ROOT_MATRIX
        root.define(ROOT_MATRIX, struct.pack('<12f', *m))
    arguments = [0 if null else matrix_at, vector_at, out_at]
    if routine == 'transform':
        arguments.append(world & 0xffffffff)
    return {'label': label, 'routine': routine, 'model': model, 'arguments': arguments, 'regions': regions}


def position_cases():
    generator = random.Random(0x12b7019)
    cases = []
    for index in range(160):
        cases.append(position_setup(f'rotation-{index}', 'rotation', generator))
    for alias in ('out-vector', 'out-matrix', 'root-matrix'):
        for index in range(12):
            cases.append(position_setup(f'rotation-{alias}-{index}', 'rotation', generator, alias=alias))
    cases.append(position_setup('rotation-null', 'rotation', generator, null=True))
    cases.append(position_setup('rotation-zero-vector', 'rotation', generator, vector=[0.0, 0.0, 0.0], scale=0.9))
    cases.append(position_setup('rotation-wing-offset', 'rotation', generator, vector=[0.0, 0.0, 15.0], scale=1.1))
    for index in range(160):
        world = generator.choice([0, 1, 0x100, 0x1ff, 0xffffff01])
        cases.append(position_setup(f'transform-{index}', 'transform', generator, world=world))
    for alias in ('out-vector', 'out-matrix'):
        for world in (0, 1):
            for index in range(6):
                cases.append(position_setup(f'transform-{alias}-{world}-{index}', 'transform', generator,
                                            world=world, alias=alias))
    cases.append(position_setup('transform-null', 'transform', generator, null=True))
    return cases


def compare_position(setup, machine, authored):
    if setup['routine'] == 'rotation':
        start, ret, cleanup = ROTATION_POSITION, 0x012b70ef, 0xc
    else:
        start, ret, cleanup = TRANSFORM_POSITION, 0x012b7016, 0x10
    x86 = machine.execute(start, setup['arguments'], setup['regions'], ecx=setup['model'], return_instruction=ret,
                          cleanup=cleanup)
    native = authored.run_position(setup)
    python = python_position(setup)
    checks = dict(x86['checks'], native_status=native['status'] == 0, regions=native['regions'] == x86['regions'],
                  python_model=python == x86['regions'])
    return {'label': setup['label'], 'match': all(checks.values()), 'checks': checks, 'stopped': x86['stopped'],
            'error': x86['error']}


# --------------------------------------------------------------------------
# Class helpers and the part loader loop.


def compare_class_helpers(machine, authored):
    generator = random.Random(0x139d6a2)
    counts = {'skin_index': [0, 0], 'class_tier': [0, 0], 'skips_tier2': [0, 0]}
    failures = []
    for value in range(256):
        argument = value | (generator.randrange(1 << 24) << 8 if value & 1 else 0)
        for name, start, ret, c_function, python in (
                ('skin_index', SKIN_INDEX, 0x0139d6d9, authored.skin_index, py_skin),
                ('class_tier', CLASS_TIER, 0x0139cbe0, authored.class_tier, py_tier),
                ('skips_tier2', SKIPS_TIER2, 0x0139d8e9, authored.skips_tier2, py_skips)):
            x86 = machine.execute(start, [argument], [], ecx=0x0badc0de, return_instruction=ret, cleanup=0)
            al = x86['eax'] & 0xff
            ok = all(x86['checks'].values()) and al == c_function(value) == python(value)
            counts[name][0] += 1
            counts[name][1] += int(ok)
            if not ok:
                failures.append((name, value, al, x86['stopped']))
    return {name: {'cases': c, 'matches': m} for name, (c, m) in counts.items()}, failures[:8]


def run_loader_loop(text, data):
    """Executes the loader's body-part loop with AccessModel recorded."""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_FETCH_UNMAPPED
    from unicorn import UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC
    from unicorn import x86_const as x86
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(TEXT_BASE, tracks.TEXT_BYTES, UC_PROT_READ | UC_PROT_EXEC)
    uc.mem_write(TEXT_BASE, text)
    uc.mem_map(DATA_BASE, align(tracks.DATA_BYTES, 0x1000), UC_PROT_READ)
    uc.mem_write(DATA_BASE, data)
    stack = 0x31000000
    uc.mem_map(stack, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
    calls, problems = [], []

    def access_model(uc, address, size, user):
        esp = uc.reg_read(x86.UC_X86_REG_ESP)
        ret, type_, directory, name, index = struct.unpack('<5I', uc.mem_read(esp, 20))

        def text_at(pointer):
            raw = bytes(uc.mem_read(pointer, 64))
            return raw.split(b'\0')[0].decode('latin-1')
        calls.append((type_, text_at(directory), text_at(name), struct.unpack('<i', struct.pack('<I', index))[0]))
        uc.reg_write(x86.UC_X86_REG_ESP, esp+4)
        uc.reg_write(x86.UC_X86_REG_EIP, ret)

    def unmapped(uc, access, address, size, value, user):
        problems.append(hex(address))
        return False
    uc.hook_add(UC_HOOK_CODE, access_model, begin=ACCESS_MODEL, end=ACCESS_MODEL)
    uc.hook_add(UC_HOOK_MEM_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED, unmapped)
    uc.reg_write(x86.UC_X86_REG_ESP, stack+0x8000)
    uc.reg_write(x86.UC_X86_REG_EBP, stack+0x8100)
    error = None
    try:
        uc.emu_start(LOADER_LOOP, LOADER_DONE, timeout=60000000)
    except Exception as failure:
        error = str(failure)
    finished = uc.reg_read(x86.UC_X86_REG_EIP) == LOADER_DONE and not problems and error is None
    return calls, finished


def compare_loader(text, data, authored):
    calls, finished = run_loader_loop(text, data)
    table = {}
    for type_, directory, name, index in calls:
        file_name = (f'{name}.bmd' if index == -1 else f'{name}0{index}.bmd' if index < 10 else f'{name}{index}.bmd')
        table.setdefault(type_, []).append((directory, file_name))
    authored_table = {t: authored.file_for(t) for t in range(0x3700, 0x3890)}
    mismatches = [hex(t) for t in range(0x3700, 0x3890)
                  if (authored_table[t] is None) != (t not in table) or
                  (t in table and any(entry != ('Data\\Player\\', authored_table[t]) for entry in table[t]))]
    return {'calls': len(calls), 'types': len(table), 'finished': finished, 'mismatches': mismatches,
            'match': finished and not mismatches and len(calls) == len(table),
            'loaded_per_tier': [sum(1 for t in table if (t-0x3700) % 0x50 // 16 == tier) for tier in range(5)]}


# --------------------------------------------------------------------------
# Installed chains: Player skeleton -> body parts and linked items.


def decoded_case(path, label):
    raw = Path(path).read_bytes()
    sys.path.insert(0, str(ROOT/'model-recovery'))
    import bmd_encrypted
    version = raw[3]
    model = bmd_encrypted.parse_model(raw)
    plain = raw[4:] if version == 10 else {12: bmd_encrypted.decrypt_map, 14: bmd_encrypted.decrypt_modulus,
                                          15: bmd_encrypted.decrypt_lea}[version](raw[8:])
    actions = [a['keys'] for a in model['actions']]
    bones = [{'dummy': int(b['dummy'])} for b in model['bones']]
    start = (model['bones'][0]['source_offset'] if model['bones'] else model['parsed_bytes'])-4
    case = tracks.build_case(label, actions, bones, stream=plain, start=start, suffix=b'',
                             heap_bytes=tracks.heap_need(actions, bones))
    case.update(parsed=model, version=version, plain=plain, sha256=hashlib.sha256(raw).hexdigest())
    return case


def pose_actual(case, params, machines, authored, feature):
    machine_tracks, machine_pose, _ = machines
    seeded = pose.seed_case(machine_tracks, authored.pose, case, feature)
    if not seeded['ok'] or not seeded['authored_tracks_match']:
        return None, f"seed {seeded['stopped']}"
    setup = pose.make_setup(case['label'], case, seeded, params)
    built = machine_pose.run(setup)
    native = authored.pose.run(setup)
    ok = all(built['checks'].values()) and built['stopped'] is None and native['status'] == 0 and \
        native['window'] == built['window'] and native['quaternions'] == built['quaternions']
    if not ok:
        return None, f"builder {built['stopped']}"
    return (setup, built), None


def skin_against(window, model, bones, part, params, machine, authored, label):
    """Transform part meshes (decoded stream appended to window) with the given bones."""
    window = window.copy()
    stream = align(window.end, 0x1000)
    pad = stream-window.end
    window.data.extend(poison(pad, 0x7c))
    window.defined.extend(bytes(pad))
    window.data.extend(part['plain'])
    window.defined.extend(b'\1'*len(part['plain']))
    meshes = skin.installed_meshes(window, {'parsed': part['parsed'], 'stream': stream})
    setup = skin.transform_setup(label, window, model, bones, meshes, params)
    result = skin.compare_transform(setup, machine, authored, negative=False)
    return result


def root_setter_actual(window, model, bone_address, vector, machine, authored, label):
    window = window.copy()
    scratch = align(window.end, 0x1000)
    pad = scratch+0x40-window.end
    window.data.extend(poison(pad, 0x3d))
    window.defined.extend(bytes(pad))
    window.define(scratch, struct.pack('<3f', *vector))
    root = Region('root', ROOT_REGION[0], poison(ROOT_REGION[1], 0x23), bytes(ROOT_REGION[1]))
    setup = {'label': label, 'routine': 'rotation', 'model': model, 'arguments': [bone_address, scratch, scratch+0x20],
             'regions': [window, root]}
    result = compare_position(setup, machine, authored)
    x86 = machine.execute(ROTATION_POSITION, setup['arguments'], setup['regions'], ecx=model,
                          return_instruction=0x012b70ef, cleanup=0xc)
    regions = x86['regions']
    offset = ROOT_MATRIX-ROOT_REGION[0]
    matrix = list(struct.unpack_from('<12f', regions['root'], offset))
    out = list(struct.unpack_from('<3f', regions['window'], scratch+0x20-WINDOW))
    return result, matrix, out


def installed_chains(game_root, machines, authored, limit=None):
    data = Path(game_root)/'Data'
    player = decoded_case(data/'Player'/'Player.bmd', 'Data/Player/Player.bmd')
    digest = player['sha256']
    samples = pose.installed_params(player, digest, 0)
    machine = machines[2]
    states = []
    for number, (kind, params) in enumerate(samples):
        params = dict(params, keep_root=0, translate=0)
        posed, error = pose_actual(player, params, machines, authored, tracks.FEATURE_VALUES[number % 3])
        states.append({'kind': kind, 'params': params, 'posed': posed, 'error': error})
    parts = sorted(p for p in (data/'Player').glob('*.bmd')
                   if any(p.name.startswith(n) for n in ('HelmClass', 'ArmorClass', 'PantClass', 'GloveClass',
                                                         'BootClass')))
    items = sorted(p for p in (data/'Item').glob('*.bmd')
                   if p.name.lower().startswith(('sword', 'axe', 'mace', 'spear', 'staff', 'wand', 'bow',
                                                 'crossbow', 'shield', 'blade', 'hammer', 'book')))
    if limit:
        parts, items = parts[:limit], items[:limit]
    results = {'player_states': [{'kind': s['kind'], 'ok': s['posed'] is not None, 'error': s['error']}
                                 for s in states], 'parts': [], 'items': [], 'roots': []}
    generator = random.Random(int(digest[:16], 16))
    good = [s for s in states if s['posed']]
    for number, path in enumerate(parts):
        state = good[number % len(good)]
        setup, built = state['posed']
        window = Region('window', WINDOW, built['window'], skin.built_defined(setup, built))
        part = decoded_case(path, f'Data/Player/{path.name}')
        params = {'lighting': 1, 'body_scale': f32(generator.uniform(0.8, 1.3)),
                  'origin': [f32(generator.uniform(-2000, 2000)) for _ in range(3)],
                  'light_angles': (0.0, 0.0, 0.0), 'translate': 1, 'vertex_scale': 0.0,
                  'ambient': LIGHT_ARGUMENTS[0], 'light_scale': LIGHT_ARGUMENTS[1],
                  'light_minimum': LIGHT_ARGUMENTS[2]}
        result = skin_against(window, setup['model'], setup['output_span'][0], part, params, machine, authored,
                              part['label'])
        results['parts'].append({k: result[k] for k in ('label', 'match', 'vertices', 'normals', 'stopped')})
    for number, path in enumerate(items):
        state = good[number % len(good)]
        setup, built = state['posed']
        window = Region('window', WINDOW, built['window'], skin.built_defined(setup, built))
        hand = 'left' if path.name.lower().startswith('shield') else 'right'
        bone = setup['output_span'][0]+WEAPON_BONES[hand]*0x30
        root, matrix, out = root_setter_actual(window, setup['model'], bone, (0.0, 0.0, 0.0), machine, authored,
                                               f'root:{path.name}')
        results['roots'].append({k: root[k] for k in ('label', 'match', 'stopped')})
        item = decoded_case(path, f'Data/Item/{path.name}')
        actions = item['parsed']['actions']
        if not actions or actions[0]['keys'] <= 0:
            continue
        position = [f32(generator.uniform(-2000, 2000)) for _ in range(3)]
        scale = f32(generator.uniform(0.8, 1.3))
        origin = [f32(position[k]+out[k]) for k in range(3)]
        params = {'frame': 0.0, 'prior_frame': 0.0, 'prior_action': 0, 'current': 0, 'angles': (0.0, 0.0, 0.0),
                  'head': (0.0, 0.0), 'keep_root': 1, 'translate': 1, 'root_matrix': matrix, 'scale': scale,
                  'translation': origin, 'locks': {a: int(bool(x['lock_positions'])) for a, x in enumerate(actions)}}
        posed, error = pose_actual(item, params, machines, authored, tracks.FEATURE_VALUES[number % 3])
        if posed is None:
            results['items'].append({'label': item['label'], 'match': False, 'stopped': error})
            continue
        isetup, ibuilt = posed
        iwindow = Region('window', WINDOW, ibuilt['window'], skin.built_defined(isetup, ibuilt))
        meshes = skin.installed_meshes(iwindow, item)
        tparams = {'lighting': 1, 'body_scale': scale, 'origin': origin, 'translate': 1, 'vertex_scale': 0.0,
                   'ambient': LIGHT_ARGUMENTS[0], 'light_scale': LIGHT_ARGUMENTS[1],
                   'light_minimum': LIGHT_ARGUMENTS[2]}
        tsetup = skin.transform_setup(item['label'], iwindow, isetup['model'], isetup['output_span'][0], meshes,
                                      tparams)
        result = skin.compare_transform(tsetup, machine, authored, negative=False)
        results['items'].append({k: result[k] for k in ('label', 'match', 'vertices', 'normals', 'stopped')})
    for key in ('parts', 'items', 'roots'):
        entries = results[key]
        results[f'{key}_summary'] = {'cases': len(entries), 'matches': sum(bool(e['match']) for e in entries),
                                     'vertices': sum(e.get('vertices', 0) for e in entries),
                                     'normals': sum(e.get('normals', 0) for e in entries)}
    results['player_sha256'] = digest
    return results


# --------------------------------------------------------------------------


def validate(text, data, flag, feature, library, game_root=None, limit=None):
    payload = tracks.load_pinned(text, tracks.TEXT_BYTES, tracks.TEXT_SHA256, 'restored text')
    data_payload = tracks.load_pinned(data, tracks.DATA_BYTES, tracks.DATA_SHA256, 'second image section')
    flag_payload = tracks.load_pinned(flag, 4, tracks.FLAG_SHA256, 'dispatch flag')
    feature_payload = tracks.load_pinned(feature, 4, tracks.FEATURE_SHA256, 'memcpy feature word')
    for table in (BODIES, skin.BODIES, pose.BODIES, tracks.BODIES):
        for name, (start, end, digest) in table.items():
            if hashlib.sha256(payload[start-TEXT_BASE:end-TEXT_BASE]).hexdigest() != digest:
                raise ValueError(f'Pinned {name} body mismatch')
    for address, text_value in STRINGS.items():
        if data_payload[address-DATA_BASE:address-DATA_BASE+len(text_value)+1] != text_value.encode()+b'\0':
            raise ValueError(f'AccessModel format at {address:#x} changed')
    for value, address in zip(LIGHT_ARGUMENTS, (0x1a7df0c, 0x1a7df18, 0x1a7df08)):
        if data_payload[address-DATA_BASE:address-DATA_BASE+4] != struct.pack('<f', value):
            raise ValueError(f'Light argument at {address:#x} changed')
    import unicorn
    library = Path(library).resolve(strict=True)
    machine = skin.SkinMachine(payload, data_payload, flag_payload)
    authored = Authored(library)
    positions = [compare_position(setup, machine, authored) for setup in position_cases()]
    helpers, helper_failures = compare_class_helpers(machine, authored)
    report = {'text_sha256': tracks.TEXT_SHA256, 'data_sha256': tracks.DATA_SHA256, 'unicorn': unicorn.__version__,
              'authored_library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
              'bodies': {name: {'start': hex(s), 'end_exclusive': hex(e), 'sha256': d}
                         for name, (s, e, d) in BODIES.items()},
              'positions': {'cases': len(positions), 'matches': sum(r['match'] for r in positions),
                            'failures': [r for r in positions if not r['match']][:8]},
              'class_helpers': helpers, 'class_helper_failures': helper_failures,
              'loader': compare_loader(payload, data_payload, authored)}
    # Negative control: a rotation position that skips the body scale must differ from the client.
    report['negative_controls'] = {'unscaled_rotation_position': sum(
        python_position(s, 'unscaled') != machine.execute(
            ROTATION_POSITION, s['arguments'], s['regions'], ecx=s['model'], return_instruction=0x012b70ef,
            cleanup=0xc)['regions']
        for s in position_cases()[:40] if s['routine'] == 'rotation')}
    if game_root:
        machines = (tracks.Machine(payload, data_payload, flag_payload, feature_payload, library, None),
                    pose.PoseMachine(payload, data_payload, flag_payload), machine)
        report['installed'] = installed_chains(game_root, machines, authored, limit)
    return report


def failed(report):
    bad = report['positions']['matches'] != report['positions']['cases']
    bad = bad or any(v['matches'] != v['cases'] for v in report['class_helpers'].values())
    bad = bad or not report['loader']['match'] or not report['negative_controls']['unscaled_rotation_position']
    if 'installed' in report:
        installed = report['installed']
        bad = bad or not all(s['ok'] for s in installed['player_states'])
        bad = bad or any(installed[f'{k}_summary']['matches'] != installed[f'{k}_summary']['cases']
                         for k in ('parts', 'items', 'roots'))
    return bad


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--flag', type=Path, required=True)
    parser.add_argument('--feature', type=Path, required=True, help='math-capture cpu-features.bin')
    parser.add_argument('--library', type=Path, default=ROOT/f'reconstructed/model-codec/libcharacter.{SUFFIX}')
    parser.add_argument('--game-root', type=Path)
    parser.add_argument('--limit', type=int, help='first N part and item models only')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.text, args.data, args.flag, args.feature, args.library, args.game_root, args.limit)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(report, indent=2)+'\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')
    return int(bool(failed(report)))


if __name__ == '__main__':
    sys.exit(main())
