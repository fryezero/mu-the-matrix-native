#!/usr/bin/env python3
"""Compare the GFx layer's game side with the client's routines (NATIVE-GFX-003).

The client routines run in Unicorn over the pinned restored text and second
image section (scripts/client_ui_machine.py).  Their GFx value building and
invokes are recorded through stubs of the GFx value API (object/array
creation, member setters, array pushes, Invoke), which turns each routine's
output into a JSON-like structure.  The layer's output for the same inputs
comes from native/gfx/mu_gfx_layer.c driven by the test host against the
stand-in libmugfx (tests/gfx_layer_host.c, tests/gfx_stub_mugfx.c), whose
log records every invoke.

Sections:

* loadlist: the UIFrame onLoad handler 0x00c8f05d (the base movie's
  LoadFrameFiles argument) against the layer's LoadFrameFiles;
* menu: the main frame's InitMenuInfo builder 0x00c71fc2 with its entry
  helpers 0x00c72580 / 0x00c725e6 (GlobalText 0x0095f027 returns "GT<n>")
  against the layer's InitMenuInfo with MU_GFX_GT_IDS=1;
* skill: the SkillInfo builder 0x00c5ebaa over synthetic skill records
  (the table lookup 0x00961620 returns them): member names and the record
  offsets they read;
* window: the GFx window creator 0x00ac9edc for random window sizes and the
  registry alignments of InventoryFrame (11) and CharacterInfoFrame (9):
  its SetScale / SetAlign / SetWindowSize invokes (through the window base
  0x00aaebca, 0x00aae4ae and the invoke 0x00aae7e0) against the layer's.

Modelled explicitly (not client code): the GFx value API, GlobalText, the
skill table lookup and std::string accessors, the window's movie loading
(vtable +4 returns true, +8 does nothing), the movie view calls of
SetWindowSize and the window list insert.  Any other call outside the
allowlisted functions stops the case.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402

DEFAULT_TEXT = ROOT/'evidence/x86-text-capture-09/client-text.bin'
DEFAULT_DATA = ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
SECURITY_COOKIE = 0x01cf65c0

# GFx value API of the client (thiscall unless noted)
VALUE_CTOR, VALUE_DTOR = 0x00aad26b, 0x00aad299
NEW_OBJECT, NEW_ARRAY = 0x00c8f5f4, 0x00c8f9cf          # (out)
ARRAY_PUSH_STR = 0x00c8eba5                            # (array, char *)
SET_VALUE, SET_INT, SET_STR = 0x00ae497d, 0x00ae957f, 0x00ae94c9   # (object, name, value)
ARRAY_PUSH_VALUE = 0x00ae495f                          # this = array (value)
INVOKE = 0x00c8fac2                                    # (method, value)
GLOBAL_TEXT = 0x0095f027                               # this = 0x06fbab48 (index) -> char *
SKILL_LOOKUP, STRING_CSTR = 0x00961620, 0x008e7940
UI_LOADLIST, MENU_INFO, MENU_ITEM, MENU_ENTRY, SKILL_INFO = 0x00c8f05d, 0x00c71fc2, 0x00c72580, 0x00c725e6, 0x00c5ebaa
WINDOW_CREATE, SET_SCALE, SET_WINDOW_SIZE, WINDOW_INVOKE = 0x00ac9edc, 0x00aaebca, 0x00aae4ae, 0x00aae7e0
MANAGER = 0x00ac3bf7
WINDOW_GETTERS = (0x0095f998, 0x0095f5d7, 0x009e819e, 0x00acd83e, 0x009ff656, 0x00acd6ff, 0x009a5937, 0x00acd884,
                  0x00acd896, 0x00acd6df, 0x00ac16af, 0x00ac16d0)
WINDOW_STUBS = (0x0040c8d0, 0x0040ca50, 0x0040cb60, 0x00ab0dc6, 0x00ab0271, 0x00acaf98, 0x00aaea78, 0x00ac0b96,
                0x00ab03cf, 0x00ab041b, 0x00ab0d72)
SCREEN_W, SCREEN_H = 0x01cf1624, 0x01cf1628
VTABLE_LOAD, VTABLE_INIT = 0x008e0480, 0x008e0490   # int3 padding used as stub addresses for the window's vtable


def sha256_file(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Values:
    """The GFx values the client builds: Value address -> Python value."""

    def __init__(self, m, text):
        self.m, self.text = m, text
        self.nodes = {}
        self.invokes = []

    def cstr(self, address):
        out = bytearray()
        while len(out) < 512:
            b = self.m.read(address + len(out), 1)[0]
            if not b:
                break
            out.append(b)
        return out.decode('latin1')

    def ecx(self):
        return self.m.uc.reg_read(cm.UC_X86_REG_ECX)

    def install(self):
        m, text = self.m, self.text

        def cleanup(address):
            return cm.stdcall_cleanup(text, address)

        def ctor(_):
            self.nodes[self.ecx()] = None
        m.stub(VALUE_CTOR, ctor, cleanup(VALUE_CTOR))
        m.stub(VALUE_DTOR, lambda _: 0, cleanup(VALUE_DTOR))

        def new_object(_):
            self.nodes[m.args(1)[0]] = {}
        m.stub(NEW_OBJECT, new_object, cleanup(NEW_OBJECT))

        def new_array(_):
            self.nodes[m.args(1)[0]] = []
        m.stub(NEW_ARRAY, new_array, cleanup(NEW_ARRAY))

        def push_str(_):
            array, s = m.args(2)
            self.nodes[array].append(self.cstr(s))
        m.stub(ARRAY_PUSH_STR, push_str, cleanup(ARRAY_PUSH_STR))

        def set_value(_):
            obj, name, value = m.args(3)
            self.nodes[obj][self.cstr(name)] = self.nodes[value]   # GFx object values are references
        m.stub(SET_VALUE, set_value, cleanup(SET_VALUE))

        def set_int(_):
            obj, name, value = m.args(3)
            self.nodes[obj][self.cstr(name)] = struct.unpack('<i', struct.pack('<I', value))[0]
        m.stub(SET_INT, set_int, cleanup(SET_INT))

        def set_str(_):
            obj, name, value = m.args(3)
            self.nodes[obj][self.cstr(name)] = self.cstr(value)
        m.stub(SET_STR, set_str, cleanup(SET_STR))

        def push_value(_):
            self.nodes[self.ecx()].append(self.nodes[m.args(1)[0]])
        m.stub(ARRAY_PUSH_VALUE, push_value, cleanup(ARRAY_PUSH_VALUE))

        def invoke(_):
            method, value = m.args(2)
            self.invokes.append((self.cstr(method), self.nodes.get(value)))
        m.stub(INVOKE, invoke, cleanup(INVOKE))


def machine(text, data):
    m = cm.Machine(text, data)
    m.put32(SECURITY_COOKIE, 0xbb40e64e)
    return m


def allow_functions(m, text, *starts):
    m.allow(*[(s, cm.function_extent(text, s)) for s in starts])


def handler_object(m):
    h = m.alloc(0x400, define=True)
    m.put32(h, m.alloc(0x100, define=True))   # a vtable word for code that reads it
    return h


# --------------------------------------------------------------------------- the layer through the test host

def layer_log(work, size=(1280, 800), gt_ids=False):
    """Stub log of the layer's start-up (all base-list movies present)."""
    host = work/'gfx-layer-host'
    lib = work/('libmugfx_stub.dylib' if sys.platform == 'darwin' else 'libmugfx_stub.so')
    if not host.exists():
        cc = os.environ.get('CC', 'cc')
        hud = ROOT/'reconstructed/hud'
        subprocess.run([cc, '-std=c11', '-O1', '-shared', '-fPIC', '-o', str(lib),
                        str(ROOT/'native/tests/gfx_stub_mugfx.c')], check=True)
        subprocess.run([cc, '-std=c11', '-O1', '-DMU_GFX_NO_GL', '-I', str(ROOT/'native/gfx'), '-I', str(hud),
                        str(ROOT/'native/tests/gfx_layer_host.c'), str(ROOT/'native/gfx/mu_gfx_layer.c'),
                        str(hud/'inv_grid.c'), str(hud/'item_slots.c'), str(hud/'tooltip_html.c'), '-lm'] +
                       ([] if sys.platform == 'darwin' else ['-ldl']) + ['-o', str(host)], check=True)
        movies = work/'movies'
        movies.mkdir(exist_ok=True)
        for name in ('base', 'ImageData', 'Tooltip', 'Popups', 'main', 'ItemDurability', 'Chat', 'AlarmFrame',
                     'topmenu', 'bufflist', 'hudPlayerName', 'hudMap', 'hudNotice', 'InventoryFrame', 'InfoPopup',
                     'CharacterInfoFrame'):
            (movies/f'{name}.swf').write_bytes(b'')
    log = work/'stub.log'
    if log.exists():
        log.unlink()
    env = {**os.environ, 'MUGFX_STUB_LOG': str(log), 'MU_GFX_SIZE': f'{size[0]}x{size[1]}'}
    if gt_ids:
        env['MU_GFX_GT_IDS'] = '1'
    subprocess.run([str(host), str(work/'movies'), str(lib), 'print'], check=True, capture_output=True, env=env)
    return log.read_text().splitlines()


def invoke_args(log, movie, method):
    for line in log:
        head, _, args = line.partition(' ')
        path, _, rest = args.partition(' ')
        if head == movie and path.endswith('.' + method):
            return json.loads(rest)
    raise AssertionError(f'{movie} {method} not in the layer log')


# --------------------------------------------------------------------------- sections

def validate_loadlist(text, data, work, report):
    m = machine(text, data)
    v = Values(m, text)
    v.install()
    allow_functions(m, text, UI_LOADLIST)
    m.call(UI_LOADLIST, ecx=handler_object(m))
    assert len(v.invokes) == 1 and v.invokes[0][0] == 'LoadFrameFiles', v.invokes
    client = v.invokes[0][1]
    layer = invoke_args(layer_log(work), 'base', 'LoadFrameFiles')[0]
    assert client == layer, (client, layer)
    report['loadlist'] = client
    return {'movies': sum(len(x) for x in client.values()), 'slots': len(client)}


def validate_menu(text, data, work, report):
    m = machine(text, data)
    v = Values(m, text)
    v.install()
    strings = {}

    def global_text(_):
        n = m.args(1)[0]
        if n not in strings:
            s = f'GT{n}'.encode() + b'\0'
            strings[n] = m.alloc(len(s), define=True)
            m.write(strings[n], s)
        return strings[n]
    m.stub(GLOBAL_TEXT, global_text, cm.stdcall_cleanup(text, GLOBAL_TEXT))
    allow_functions(m, text, MENU_INFO, MENU_ITEM, MENU_ENTRY)
    m.call(MENU_INFO, ecx=handler_object(m))
    v.invokes = copy.deepcopy(v.invokes)
    assert len(v.invokes) == 1 and v.invokes[0][0] == 'InitMenuInfo', v.invokes
    client = v.invokes[0][1]
    layer = invoke_args(layer_log(work, gt_ids=True), 'base', 'InitMenuInfo')[0]

    def normal(node):   # the layer labels its placeholders "GlobalText <n>"
        if isinstance(node, dict):
            return {k: normal(x) for k, x in node.items()}
        if isinstance(node, list):
            return [normal(x) for x in node]
        if isinstance(node, str) and node.startswith('GlobalText '):
            return 'GT' + node.split()[1]
        return node
    assert client == normal(layer), (client, normal(layer))
    report['menu'] = client
    entries = sum(1 + len(g.get('subMenu', [])) for g in client.values())
    return {'groups': len(client), 'entries': entries, 'global_texts': len(strings)}


def validate_skill(text, data, rng, report, cases):
    names = None
    for _ in range(cases):
        m = machine(text, data)
        v = Values(m, text)
        v.install()
        record = m.alloc(0x100, define=True)
        name = m.alloc(64, define=True)
        fields = {'Index': rng.randrange(1, 1000), 'Magic_Icon': rng.randrange(0, 450),
                  'Delay': rng.randrange(0, 5000), 'SkillUseType': rng.randrange(0, 15),
                  'MasteryType': rng.randrange(0, 8)}
        text_name = f'skill{rng.randrange(10000)}'
        m.put32(record + 4, fields['Index'])
        m.put32(record + 0x8c, fields['Magic_Icon'])
        m.put32(record + 0x38, fields['Delay'])
        m.put32(record + 0x58, fields['SkillUseType'])
        m.put32(record + 0x50, fields['MasteryType'])
        m.write(name, text_name.encode() + b'\0')
        seen = {}

        def lookup(_):
            seen['index'] = m.args(1)[0]
            seen['table'] = v.ecx()
            return record
        m.stub(SKILL_LOOKUP, lookup, cm.stdcall_cleanup(text, SKILL_LOOKUP))

        def cstr(_):
            assert v.ecx() == record + 8
            return name
        m.stub(STRING_CSTR, cstr, cm.stdcall_cleanup(text, STRING_CSTR))
        allow_functions(m, text, SKILL_INFO)
        obj = m.alloc(16, define=True)
        v.nodes[obj] = {}
        m.call(SKILL_INFO, args=(obj, fields['Index']), ecx=handler_object(m))
        expect = dict(fields, Name=text_name)
        assert v.nodes[obj] == expect, (v.nodes[obj], expect)
        assert seen == {'index': fields['Index'], 'table': 0x06fbb138}, seen
        names = list(v.nodes[obj])
    # the members the layer sends, in the client's order
    assert names == ['Index', 'Magic_Icon', 'Name', 'Delay', 'SkillUseType', 'MasteryType'], names
    report['skill_members'] = names
    return {'cases': cases}


def window_case(text, data, width, height, align):
    m = machine(text, data)
    invokes = []

    def cleanup(address):
        return cm.stdcall_cleanup(text, address)
    for address in WINDOW_STUBS:
        result = {0x00ab03cf: 1, 0x00ab041b: 0x30000100}.get(address, 0)
        m.stub(address, lambda _, r=result: r, cleanup(address))
    manager = m.alloc(0x400, define=True)
    for k in range(0, 0x400, 4):
        m.put32(manager + k, 0x5000 + k)      # other windows: never the created one
    m.stub(MANAGER, lambda _: manager, cleanup(MANAGER))

    def window_invoke(_):   # cdecl (window, method, format, ...)
        window, method, fmt = m.args(3)
        fmt_s, method_s = Values(m, text).cstr(fmt), Values(m, text).cstr(method)
        words = m.args(3 + 2 * fmt_s.count('%'))[3:]
        values, k = [], 0
        for spec in fmt_s.split():
            if spec == '%f':
                values.append(struct.unpack('<d', struct.pack('<II', words[k], words[k + 1]))[0])
                k += 2
            else:
                values.append(struct.unpack('<i', struct.pack('<I', words[k]))[0])
                k += 1
        invokes.append([method_s] + values)
    m.stub(WINDOW_INVOKE, window_invoke, 0)
    m.stub(VTABLE_LOAD, lambda _: 1, 8)
    m.stub(VTABLE_INIT, lambda _: 0, 0)
    window = m.alloc(0x200, define=True)
    vtable = m.alloc(0x40, define=True)
    m.put32(window, vtable)
    m.put32(vtable + 4, VTABLE_LOAD)
    m.put32(vtable + 8, VTABLE_INIT)
    m.put32(SCREEN_W, width)
    m.put32(SCREEN_H, height)
    m.put32(0x01cf09c4, m.alloc(8, define=True))
    allow_functions(m, text, WINDOW_CREATE, SET_SCALE, SET_WINDOW_SIZE, *WINDOW_GETTERS)
    registry = m.alloc(0x100, define=True)
    window_list = m.alloc(0x40, define=True)
    name = m.alloc(0x20, define=True)
    m.call(WINDOW_CREATE, args=(window_list, window, 0, name, 0, align), ecx=registry)
    return invokes


def validate_window(text, data, work, rng, report, cases):
    sizes = [(1280, 800), (1024, 768), (800, 600), (1024, 699), (1024, 700), (1920, 1080)]
    sizes += [(rng.randrange(640, 2600), rng.randrange(480, 1500)) for _ in range(max(0, cases - len(sizes)))]
    checked = 0
    for width, height in sizes[:max(cases, 6)]:
        log = layer_log(work, (width, height))
        for movie, align in (('InventoryFrame', 11), ('CharacterInfoFrame', 9)):
            client = window_case(text, data, width, height, align)
            layer = []
            for line in log:
                head, _, args = line.partition(' ')
                path, _, rest = args.partition(' ')
                method = path.rsplit('.', 1)[-1]
                if head == movie and method in ('SetScale', 'SetAlign', 'SetWindowSize'):
                    layer.append([method] + [float(x) if method == 'SetScale' else x for x in json.loads(rest)])
            assert client == layer, (width, height, movie, client, layer)
            checked += 1
    report['window_example'] = {'1024x600': window_case(text, data, 1024, 600, 11)}
    return {'cases': checked}


def mutations(text, data, work, report):
    """Planted mistakes the comparisons must catch."""
    caught = {}
    # 1. a LoadFrameFiles list without hudNotice
    m = machine(text, data)
    v = Values(m, text)
    v.install()
    allow_functions(m, text, UI_LOADLIST)
    m.call(UI_LOADLIST, ecx=handler_object(m))
    client = copy.deepcopy(v.invokes[0][1])
    layer = invoke_args(layer_log(work), 'base', 'LoadFrameFiles')[0]
    layer['mcBottomHud'] = [x for x in layer['mcBottomHud'] if x != 'hudNotice']
    caught['loadlist_without_hudNotice'] = client != layer
    # 2. the Community and Quest submenus swapped (the first static reading)
    menu = copy.deepcopy(report['menu'])
    menu['Quest']['subMenu'], menu['Community']['subMenu'] = menu['Community']['subMenu'], menu['Quest']['subMenu']
    caught['menu_submenus_swapped'] = menu != report['menu']
    # 3. Magic_Icon read from +0x90 instead of +0x8c
    m = machine(text, data)
    v = Values(m, text)
    v.install()
    record, name = m.alloc(0x100, define=True), m.alloc(16, define=True)
    m.put32(record + 0x8c, 7)
    m.put32(record + 0x90, 9)
    m.write(name, b'x\0')
    m.stub(SKILL_LOOKUP, lambda _: record, cm.stdcall_cleanup(text, SKILL_LOOKUP))
    m.stub(STRING_CSTR, lambda _: name, cm.stdcall_cleanup(text, STRING_CSTR))
    allow_functions(m, text, SKILL_INFO)
    obj = m.alloc(16, define=True)
    v.nodes[obj] = {}
    m.call(SKILL_INFO, args=(obj, 1), ecx=handler_object(m))
    caught['skill_icon_offset_0x90'] = v.nodes[obj]['Magic_Icon'] != 9
    # 4. the inventory aligned RightCenter (4, the NATIVE-GFX-002 choice) and 5. the scale threshold at 768
    client = window_case(text, data, 1280, 800, 4)
    caught['inventory_align_4'] = client != [['SetAlign', 11], ['SetWindowSize', 1280, 800]]
    client = window_case(text, data, 1280, 720, 11)
    caught['scale_threshold_768'] = client != [['SetScale', 83.0], ['SetAlign', 11], ['SetWindowSize', 1280, 720]]
    report['mutations'] = caught
    return caught


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(DEFAULT_TEXT)))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(DEFAULT_DATA)))
    parser.add_argument('--sections', default='loadlist,menu,skill,window')
    parser.add_argument('--cases', type=int, default=20)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--mutations', action='store_true', help='check that planted mistakes are caught')
    parser.add_argument('--output')
    args = parser.parse_args()
    for path, digest in ((args.text, TEXT_SHA256), (args.data, DATA_SHA256)):
        if sha256_file(path) != digest:
            raise SystemExit(f'{path}: unexpected SHA-256')
    text, data = Path(args.text).read_bytes(), Path(args.data).read_bytes()
    rng = random.Random(args.seed)
    report = {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'seed': args.seed}
    sections = args.sections.split(',')
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        if 'loadlist' in sections:
            print('loadlist', json.dumps(validate_loadlist(text, data, work, report)))
        if 'menu' in sections:
            print('menu', json.dumps(validate_menu(text, data, work, report)))
        if 'skill' in sections:
            print('skill', json.dumps(validate_skill(text, data, rng, report, args.cases)))
        if 'window' in sections:
            print('window', json.dumps(validate_window(text, data, work, rng, report, args.cases)))
        if args.mutations:
            if 'menu' not in report:
                validate_menu(text, data, work, report)
            caught = mutations(text, data, work, report)
            print('mutations', json.dumps(caught))
            if not all(caught.values()):
                raise SystemExit('a planted mistake was not caught')
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    print('all cases match')


if __name__ == '__main__':
    main()
