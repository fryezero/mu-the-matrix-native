#!/usr/bin/env python3
"""Static map of the frame loop, frame cap and hot draw/VBO sites (CLIENT-FRAME-001).

Reads only the pinned restored text and second image section, plus pinned
Debian libwine 8.0~repack-4 i386 DLLs to name import slots. Nothing here
executes client code. Optionally (--game-root) it reads the protected
main.exe and IGC.dll headers to show that the frame-cap bytes are not
present in the file and that the hook targets lie inside IGC.dll.

It reports:

* import slot names for every zero-separated IAT block whose values are
  export RVAs of a pinned Wine DLL at its preferred base, and raw call/load
  counts for the timing, swap and message-loop APIs;
* the frame driver 0x01851d39 checked instruction by instruction: the fixed
  40 ms logic step, GetTickCount bookkeeping, SwapBuffers, the Sleep-based
  frame cap and the accumulator store, plus the scene dispatcher and message
  loop that call it;
* every GL_TRIANGLE_FAN and GL_QUADS glBegin site with its function, return
  address (site + 6), immediate-mode calls up to glEnd, raw callers and an
  investigator label;
* the buffer-object calls reached through data-import function-pointer slots:
  BufferSubData/BufferData/MapBuffer users with their pushed arguments and the
  two stream buffers' creation parameters.

Labels are investigator readings of the decoded code; they are not symbols.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client_render_static as render  # noqa: E402
import model_hierarchy_common as common  # noqa: E402

WINE_SHA256 = {  # Debian libwine_8.0~repack-4_i386.deb, usr/lib/i386-linux-gnu/wine/i386-windows/
    'kernel32.dll': 'a72500f7bb767e336d559bbbb279d2e1887d49d8f74884ab091aa11c0d336e3c',
    'kernelbase.dll': '75533b0a5c05f3c6eb2aaa8df9e951da1d58201036ddc0c89c47740229cb3b6c',
    'ntdll.dll': '7e1ab6c2510bb074b6f42ddcbac815793445f51a072c9d94e7b372d5a854e206',
    'winmm.dll': 'dfc2247e691f9dd76641ef54bb687460fdad3d97351bd30c6b7011ce0fed2175',
    'gdi32.dll': 'a6766c4496ba3f7cd6ae3bcbb7e433fb7ad3eb2db89324ba2875c81ab9b3778b',
    'user32.dll': '45c6dfd228ddc12ec2ec83860e38b7b5e9ac75592480bc1f74b74a8aff6eb94a',
    'opengl32.dll': render.OPENGL32_SHA256,
}
MAIN_SHA256 = common.TARGET_SHA256
IGC_SHA256 = 'dbe122fe94e72286b871e192b6351bafdd28216312c300ba0d97d22a51a9c29b'
IAT_RANGE = (0x01a7c000, 0x01a7cc40)  # zero-separated blocks; ends at a double zero
TIMING_APIS = ('SwapBuffers', 'timeGetTime', 'QueryPerformanceCounter', 'QueryPerformanceFrequency',
               'GetTickCount', 'GetTickCount64', 'Sleep', 'timeBeginPeriod', 'timeSetEvent', 'SetTimer',
               'PeekMessageW', 'wglGetProcAddress', 'wglSwapBuffers')

FRAME_DRIVER = 0x01851d39
DISPATCHER = 0x01859d8a
FRAME_CHECKS = [  # (address, exact Capstone text); the frame driver body, in order
    (0x01851d63, 'mov eax, dword ptr [0xbdc5ec0]'),       # accumulator from the previous frame
    (0x01851d6b, 'cmp dword ptr [ebp - 0x34], 0x28'),     # while acc >= 40: one logic step
    (0x01851f61, 'mov eax, dword ptr [0xb6b53e0]'),
    (0x01851f82, 'mov eax, dword ptr [0xbdc5eb0]'),       # logic-step counter
    (0x01851f88, 'mov dword ptr [0xbdc5eb0], eax'),
    (0x01851f90, 'sub eax, 0x28'),                        # acc -= 40
    (0x01851fb6, 'jmp 0x1851d6b'),
    (0x018524e7, 'mov eax, dword ptr [0xbdc5e64]'),       # previous frame-start tick
    (0x018524ec, 'mov dword ptr [ebp - 0xb8], eax'),
    (0x018524f2, 'call dword ptr [0x1a7c49c]'),           # GetTickCount
    (0x018524f8, 'mov dword ptr [0xbdc5e64], eax'),
    (0x01852501, 'mov eax, dword ptr [0xbdc5ebc]'),       # rendered-frame counter
    (0x01852507, 'mov dword ptr [0xbdc5ebc], eax'),
    (0x01852648, 'movzx eax, byte ptr [ebp - 0x11]'),     # scene render returned "draw"
    (0x01852653, 'call dword ptr [0x1a7c148]'),           # SwapBuffers(hdc)
    (0x0185265a, 'mov eax, dword ptr [0xbdc5e64]'),
    (0x0185265f, 'sub eax, dword ptr [ebp - 0xb8]'),
    (0x01852665, 'mov dword ptr [ebp - 0x28], eax'),      # elapsed = tick - previous tick
    (0x01852668, 'cmp dword ptr [ebp - 0x28], 0x28'),     # if elapsed < 40
    (0x0185266c, 'jge 0x1852694'),
    (0x0185266e, 'push 0x28'),
    (0x01852670, 'pop eax'),
    (0x01852671, 'sub eax, dword ptr [ebp - 0x28]'),
    (0x01852677, 'push dword ptr [ebp - 0x5c]'),
    (0x0185267a, 'call dword ptr [0x1a7c4a0]'),           # Sleep(40 - elapsed)
    (0x01852680, 'mov eax, dword ptr [0xbdc5e64]'),
    (0x01852685, 'add eax, dword ptr [ebp - 0x5c]'),
    (0x01852688, 'mov dword ptr [0xbdc5e64], eax'),       # tick += slept
    (0x0185268d, 'mov dword ptr [ebp - 0x28], 0x28'),     # elapsed = 40
    (0x01852694, 'mov eax, dword ptr [ebp - 0x34]'),
    (0x01852697, 'add eax, dword ptr [ebp - 0x28]'),
    (0x0185269a, 'mov dword ptr [ebp - 0xd0], eax'),
    (0x018544a4, 'mov eax, dword ptr [ebp - 0xd0]'),
    (0x018544aa, 'mov dword ptr [0xbdc5ec0], eax'),       # accumulator for the next frame
    (0x01851d5e, 'call 0x10b7c7b0'),                      # outside main.exe: IGC.dll range
    (0x018526e7, 'jmp 0x10b47590'),                       # outside main.exe: IGC.dll range
]
CAP_FIELDS = [  # (instruction, immediate byte address, encoded instruction bytes)
    (0x01852668, 0x0185266b, '837dd828'),
    (0x0185266e, 0x0185266f, '6a28'),
    (0x0185268d, 0x01852690, 'c745d828000000'),
]
CAP_BRANCH = (0x0185266c, '7d26')         # jge over the Sleep; EB 26 would skip it always
LOGIC_FIELDS = [(0x01851d6b, 0x01851d6e, '837dcc28'), (0x01851f90, 0x01851f92, '83e828')]
CAP_BLOCK = (0x01852668, 0x01852694)      # cmp .. through the elapsed = 40 store
DISPATCH_CHECKS = [
    (0x01859e12, 'cmp dword ptr [ebp - 0x1c], 2'), (0x01859e35, 'call 0x185ad63'),
    (0x01859e40, 'call 0x1851adc'), (0x01859e4b, 'call 0x1851d39'),
    (0x0120ed88, 'call dword ptr [0x1a7c90c]'),           # PeekMessageW(PM_REMOVE)
    (0x0120ef29, 'cmp dword ptr [0x1cf0fc0], 1'),         # active window
    (0x0120ef38, 'call 0x1859d8a'), (0x0120ef54, 'call 0x1859d8a'),
]
IGC_RANGE = (0x10000000, 0x1165c000)      # IGC.dll preferred base and SizeOfImage

# Investigator labels for GL_TRIANGLE_FAN / GL_QUADS functions (CLIENT-FRAME-001 reading).
LABELS = {
    0x016cf46c: ('terrain', 'tile layer face; world/layer special cases (0x7630+layer texture)'),
    0x016cfada: ('terrain', 'tile face for layers 0x64/0x65 (alpha/additive)'),
    0x016cfb31: ('terrain', 'tile face, alpha blend, alternate corner set'),
    0x016cfb70: ('terrain', 'tile face, additive, alternate corner set'),
    0x016cfbac: ('terrain', 'tile face with neighbour test, texture 0x7723'),
    0x016cff65: ('terrain-grass', 'grass quad per tile, texture 0x7694+layer byte'),
    0x016d197d: ('terrain-decal', 'one fan per terrain tile under a projected decal (0x016cdd5f)'),
    0x0184d9bb: ('2d', 'untextured coloured rectangle, glVertex2f loop of 4'),
    0x0184dcb1: ('2d', 'textured rectangle (bitmap), glVertex2f loop of 4'),
    0x0184e01a: ('2d', 'textured rectangle with byte colour'),
    0x0184e34d: ('2d', 'rotated textured rectangle'),
    0x0184e72b: ('2d', 'rotated textured rectangle variant'),
    0x0184eb8a: ('2d', 'textured rectangle variant'),
    0x0184f036: ('2d', 'textured rectangle with colour'),
    0x0184f4ba: ('2d', 'textured rectangle variant'),
    0x010ae63d: ('2d', 'textured / untextured rectangle with glColor4ub'),
    0x0107ba6b: ('2d', 'coloured 2D fan'),
    0x009f8fd4: ('3d-misc', 'textured coloured fan, glVertex3fv'),
    0x01534b4c: ('3d-effect', 'segment strip, one 4-vertex fan per segment, called by scene renders'),
    0x0153518b: ('3d-effect', 'unrolled 24-vertex fan'),
    0x009888bf: ('3d-misc', 'flat-shaded quad (glNormal3f) and outline'),
    0x009fef9f: ('2d', 'textured quad inside the 2D projection helper 0x0184f793'),
    0x00fd8fba: ('3d-object', 'virtual draw 0x00fd8bc2 (vtable 0x01ab27a0) quad helper'),
    0x00fd9663: ('3d-object', 'virtual draw 0x00fd8bc2 quad helper'),
    0x00fd97de: ('3d-object', 'virtual draw 0x00fd8bc2 four-quad helper'),
    0x00fd9c61: ('3d-object', 'virtual draw 0x00fd8bc2 quad helper'),
    0x0107c555: ('3d-misc', 'textured quad (glVertex3f)'),
    0x01537498: ('3d-effect', 'bone-attached textured quads (calls 0x012b6ef1)'),
    0x01589b56: ('3d-scene', 'three textured quads, called by every scene render'),
    0x0158bd14: ('3d-effect', 'textured coloured quad loop'),
    0x0158c495: ('2d', 'textured coloured quad loop, glVertex2f'),
    0x0158e1aa: ('3d-effect', 'unrolled 20-vertex quad strip'),
    0x0158e9be: ('3d-effect', 'textured coloured quad loop'),
    0x0158f238: ('3d-effect', 'textured quad loop with glColor4f'),
    0x0158fb3b: ('3d-effect', 'unrolled textured quad'),
    0x0158fec1: ('3d-effect', 'textured coloured quad loop (glVertex3f)'),
    0x0184b807: ('3d-misc', 'six-face box, unrolled 24 vertices'),
    0x0184c121: ('3d-effect', 'unrolled textured quad (13 callers)'),
    0x0184c39c: ('3d-effect', 'billboard sprite quad; 433 of 445 callers in 0x0159123f'),
    0x0184ca6b: ('3d-effect', 'sprite quad variant (13 callers in 0x0184cd2f)'),
}

# Data-import function-pointer slots (call [eax] after mov eax,[slot]); names inferred from arguments.
POINTER_SLOTS = {
    0x01a7cb58: 'glBindBuffer', 0x01a7cb80: 'glBufferSubData', 0x01a7cb84: 'glBufferData',
    0x01a7cb88: 'glDeleteBuffers', 0x01a7cbcc: 'glGenBuffers', 0x01a7cc04: 'glUnmapBuffer',
    0x01a7cc14: 'glMapBuffer', 0x01a7cb68: 'glVertexAttribPointer', 0x01a7cb6c: 'glActiveTexture',
    0x01a7cc00: 'glUseProgram',
}
POINTER_ARITY = {'glBindBuffer': 2, 'glBufferSubData': 4, 'glBufferData': 4, 'glDeleteBuffers': 2, 'glGenBuffers': 2,
                 'glUnmapBuffer': 1, 'glMapBuffer': 2, 'glVertexAttribPointer': 6, 'glActiveTexture': 1,
                 'glUseProgram': 1}
POINTER_BLOCK = (0x01a7cb54, 0x01a7cc18)
VBO_CREATORS = {0x00a6fe5d: 0x01d1e2c8, 0x00a8a3ea: 0x01d1e6f8}   # creator -> buffer object
VBO_CREATE = 0x00a92497
VBO_DRAWS = {0x00a6ebd1: 'effect sprite draw (vtable 0x01a80844 slot 1)',
             0x00a88720: 'effect particle-emitter draw (vtable 0x01a81d0c slot 1)'}
GL_TARGETS = {0x8892: 'GL_ARRAY_BUFFER', 0x8893: 'GL_ELEMENT_ARRAY_BUFFER'}
GL_USAGE = {0x88e0: 'GL_STREAM_DRAW', 0x88e4: 'GL_STATIC_DRAW', 0x88e8: 'GL_DYNAMIC_DRAW'}
VERTEX_CALLS = re.compile(r'^gl(Vertex|TexCoord|Color|Normal)')


def pe_header(payload):
    """(preferred base, SizeOfImage) of a PE32 image."""
    pe = struct.unpack_from('<I', payload, 0x3c)[0]
    if payload[pe:pe+4] != b'PE\0\0':
        raise ValueError('not a PE image')
    return struct.unpack_from('<I', payload, pe+24+28)[0], struct.unpack_from('<I', payload, pe+24+56)[0]


def load_dlls(folder, pins=WINE_SHA256):
    dlls = {}
    for name, digest in pins.items():
        payload = (Path(folder)/name).read_bytes()
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError(f'{name} does not match the pinned Debian 8.0~repack-4 i386 build')
        dlls[name] = render.pe_exports(payload)
    return dlls


def import_blocks(data, low, high):
    """Zero-separated runs of nonzero slots."""
    blocks, current = [], []
    for slot in range(low, high, 4):
        value = struct.unpack('<I', data.read(slot, 4))[0]
        if value:
            current.append((slot, value))
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def name_imports(data, dlls, low=IAT_RANGE[0], high=IAT_RANGE[1]):
    """Name each slot whose value minus a DLL's preferred base is one of its export RVAs."""
    slots, blocks = {}, []
    for block in import_blocks(data, low, high):
        owners = collections.Counter()
        for slot, value in block:
            for dll, (base, exports) in dlls.items():
                names = exports.get((value-base) & 0xffffffff)
                if names:
                    slots[slot] = (dll, names[0])
                    owners[dll] += 1
                    break
        blocks.append({'first': hex(block[0][0]), 'slots': len(block), 'first_value': hex(block[0][1]),
                       'named': sum(owners.values()), 'dlls': dict(owners)})
    return slots, blocks


def slot_references(text, slot):
    """Raw FF 15 calls, FF 25 thunks and A1 / 8B r32 loads of an import slot."""
    packed = struct.pack('<I', slot)
    calls = text.raw_bytes(b'\xff\x15'+packed)
    jumps = text.raw_bytes(b'\xff\x25'+packed)
    loads = text.raw_bytes(b'\xa1'+packed) + [site for modrm in (0x05, 0x0d, 0x15, 0x1d, 0x35, 0x3d)
                                              for site in text.raw_bytes(b'\x8b'+bytes([modrm])+packed)]
    return {'calls': calls, 'jumps': jumps, 'loads': sorted(loads)}


def check_instructions(text, checks):
    """Decode each address and compare the exact Capstone text."""
    results = []
    for address, expected in checks:
        found = next(text.engine.disasm(text.region.read(address, 16), address), None)
        actual = common.text_of(found) if found else None
        results.append({'address': hex(address), 'expected': expected, 'actual': actual, 'match': actual == expected})
    return results


def cap_fields(text, fields):
    out = []
    for instruction, immediate, encoded in fields:
        raw = bytes.fromhex(encoded)
        found = text.region.read(instruction, len(raw))
        out.append({'instruction': hex(instruction), 'immediate_address': hex(immediate),
                    'immediate': text.region.read(immediate, 1)[0], 'bytes': found.hex(), 'match': found == raw})
    return out


def pushes_before(text, site):
    """Pushed operands of the straight-line run ending at site, first argument first."""
    start = text.function_start(site)
    if start is None:
        return None
    run = text.decode(start, site)
    if not run or run[-1].address != site:
        return None
    pushed = []
    for instruction in reversed(run[:-1]):
        if instruction.mnemonic == 'call' or render.JUMPS.match(instruction.mnemonic):
            break
        if instruction.mnemonic == 'push':
            pushed.append(instruction.op_str)
    return pushed


def pointer_calls(text, slot):
    """mov r32,[slot] followed within six instructions by call dword ptr [r32]."""
    sites = []
    for load in slot_references(text, slot)['loads']:
        instructions = list(text.engine.disasm(text.region.read(load, 0x30), load))
        if not instructions:
            continue
        register = instructions[0].op_str.split(',')[0]
        for instruction in instructions[1:7]:
            if instruction.mnemonic == 'call' and instruction.op_str == f'dword ptr [{register}]':
                sites.append((load, instruction.address))
                break
    return sites


def block_calls(text, site, slots, limit=0x1800):
    """GL import names called from a glBegin site through its glEnd."""
    names = []
    code = text.region.read(site, min(limit, text.region.end-site))
    for address, size, mnemonic, op_str in text.lite.disasm_lite(code, site):
        if mnemonic == 'call' and op_str.startswith('dword ptr [0x'):
            name = slots.get(int(op_str[11:-1], 16))
            if name:
                names.append(name)
                if name == 'glEnd':
                    break
        if mnemonic in ('ret', 'retf'):
            break
    return names


def glbegin_sites(text, slots, labels=LABELS):
    begin = next(slot for slot, name in slots.items() if name == 'glBegin')
    records, callers = [], {}
    for site in text.raw_bytes(b'\xff\x15'+struct.pack('<I', begin)):
        start = text.function_start(site)
        pushed = pushes_before(text, site)
        mode = render.GL_MODES.get(int(pushed[0], 16)) if pushed and re.match(r'^(0x)?[0-9a-f]+$', pushed[0]) else None
        record = {'site': hex(site), 'return_address': hex(site+6), 'function': hex(start) if start else None,
                  'mode': mode}
        if mode in ('GL_TRIANGLE_FAN', 'GL_QUADS'):
            if start not in callers:
                raw = text.raw_calls(start) if start else []
                callers[start] = (len(raw), len({text.function_start(c) for c in raw}))
            calls = block_calls(text, site, slots)
            category, label = labels.get(start, (None, None))
            record.update({'vertex_calls': dict(collections.Counter(c for c in calls if VERTEX_CALLS.match(c))),
                           'two_d': any(c.startswith('glVertex2') for c in calls),
                           'raw_callers': callers[start][0], 'caller_functions': callers[start][1],
                           'category': category, 'label': label})
        records.append(record)
    return records


def creation_parameters(text, creator):
    """Read the four immediate stores and the object passed to the buffer-create helper."""
    stores, target, obj = {}, None, None
    for instruction in text.engine.disasm(text.region.read(creator, 0x60), creator):
        op = instruction.op_str
        match = re.match(r'dword ptr \[ebp - (0x[0-9a-f]+|\d+)\], (0x[0-9a-f]+|\d+)$', op)
        if instruction.mnemonic == 'mov' and match:
            stores[int(match.group(1), 0)] = int(match.group(2), 0)
        if instruction.mnemonic == 'mov' and op.startswith('ecx, 0x'):
            obj = int(op[5:], 16)
        if instruction.mnemonic == 'call':
            target = instruction.operands[0].imm if instruction.operands[0].type == 2 else None
            break
    return {'creator': hex(creator), 'helper': hex(target) if target else None, 'object': hex(obj) if obj else None,
            'flags': stores.get(0x14), 'usage': GL_USAGE.get(stores.get(0x10), stores.get(0x10)),
            'size': stores.get(0xc), 'stride': stores.get(0x8)}


def vbo_report(text, data):
    slots = {}
    for slot in range(*POINTER_BLOCK, 4):
        uses = pointer_calls(text, slot)
        entry = {'value': hex(struct.unpack('<I', data.read(slot, 4))[0]), 'uses': len(uses),
                 'name': POINTER_SLOTS.get(slot)}
        if slot in POINTER_SLOTS:
            sites = []
            for load, call in uses:
                start = text.function_start(load)
                pushed = pushes_before(text, call)
                sites.append({'call': hex(call), 'function': hex(start) if start else None,
                              'arguments': pushed[:POINTER_ARITY[POINTER_SLOTS[slot]]] if pushed else pushed})
            entry['sites'] = sites
        slots[hex(slot)] = entry
    creators = [creation_parameters(text, creator) for creator in VBO_CREATORS]
    draws = {}
    for function, label in VBO_DRAWS.items():
        uses = [s for s in slots[hex(0x01a7cb80)]['sites'] if s['function'] == hex(function)]
        draws[hex(function)] = {'label': label, 'buffer_sub_data': [u['arguments'] for u in uses]}
    return {'pointer_slots': slots, 'stream_buffers': creators, 'draws': draws}


def file_checks(game_root, text):
    root = Path(game_root)
    main = (root/'main.exe').read_bytes()
    if hashlib.sha256(main).hexdigest() != MAIN_SHA256:
        raise ValueError('main.exe does not match the pinned target')
    block = text.region.read(CAP_BLOCK[0], CAP_BLOCK[1]-CAP_BLOCK[0])
    igc = (root/'IGC.dll').read_bytes()
    base, size = pe_header(igc)
    return {'main_exe_sha256': MAIN_SHA256, 'cap_block_in_file': main.count(block),
            'cap_head_in_file': main.count(block[:12]),
            'igc_dll_sha256': hashlib.sha256(igc).hexdigest(), 'igc_dll_pinned': hashlib.sha256(igc).hexdigest() == IGC_SHA256,
            'igc_dll_range': [hex(base), hex(base+size)],
            'hook_targets_in_igc': all(base <= target < base+size for target in (0x10b7c7b0, 0x10b47590))}


def analyze(text_path, data_path, wine_folder, game_root=None):
    text = render.Text(common.load_text(text_path))
    data = common.load_data(data_path)
    dlls = load_dlls(wine_folder)
    named, blocks = name_imports(data, dlls)
    by_name = {}
    for slot, (dll, name) in named.items():
        by_name.setdefault(name, slot)
    report = {'text_sha256': common.TEXT_SHA256, 'data_sha256': common.DATA_SHA256, 'wine_sha256': WINE_SHA256,
              'import_blocks': blocks}
    timing = {}
    for name in TIMING_APIS:
        if name not in by_name:
            continue
        refs = slot_references(text, by_name[name])
        entry = {'slot': hex(by_name[name]), 'calls': len(refs['calls']), 'thunks': len(refs['jumps']),
                 'loads': len(refs['loads'])}
        if name in ('SwapBuffers', 'Sleep', 'timeBeginPeriod', 'PeekMessageW'):
            entry['call_sites'] = [{'site': hex(s), 'function': hex(text.function_start(s) or 0)}
                                   for s in refs['calls']]
        timing[name] = entry
    report['timing_imports'] = timing
    block = text.region.read(CAP_BLOCK[0], CAP_BLOCK[1]-CAP_BLOCK[0])
    report['frame_driver'] = {
        'function': hex(FRAME_DRIVER), 'checks': check_instructions(text, FRAME_CHECKS),
        'cap_fields': cap_fields(text, CAP_FIELDS), 'logic_step_fields': cap_fields(text, LOGIC_FIELDS),
        'cap_branch': {'address': hex(CAP_BRANCH[0]), 'bytes': text.region.read(CAP_BRANCH[0], 2).hex(),
                       'match': text.region.read(CAP_BRANCH[0], 2).hex() == CAP_BRANCH[1]},
        'cap_block': {'range': [hex(CAP_BLOCK[0]), hex(CAP_BLOCK[1])], 'bytes': block.hex(),
                      'sha256': hashlib.sha256(block).hexdigest()},
        'frame_driver_callers': [hex(c) for c in text.raw_calls(FRAME_DRIVER)],
        'dispatcher_callers': [hex(c) for c in text.raw_calls(DISPATCHER)],
        'dispatch_checks': check_instructions(text, DISPATCH_CHECKS)}
    gl_slots = {int(s['slot'], 16): s['name']
                for s in render.name_slots(data, *render.OPENGL32_SLOTS, (Path(wine_folder)/'opengl32.dll').read_bytes())
                if s['name']}
    sites = glbegin_sites(text, gl_slots)
    hot = [s for s in sites if s['mode'] in ('GL_TRIANGLE_FAN', 'GL_QUADS')]
    report['glbegin'] = {
        'modes': dict(collections.Counter(s['mode'] for s in sites)),
        'hot_sites': hot,
        'unlabelled': [s['site'] for s in hot if not s['category']],
        'categories': {mode: dict(collections.Counter(s['category'] for s in hot if s['mode'] == mode))
                       for mode in ('GL_TRIANGLE_FAN', 'GL_QUADS')}}
    report['vbo'] = vbo_report(text, data)
    if game_root:
        report['files'] = file_checks(game_root, text)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--wine-dlls', type=Path, required=True,
                        help='folder with the pinned Debian libwine 8.0~repack-4 i386-windows DLLs')
    parser.add_argument('--game-root', type=Path, help='optional: installed client with main.exe and IGC.dll')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = analyze(args.text, args.data, args.wine_dlls, args.game_root)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    encoded = json.dumps(report, indent=1)+'\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
