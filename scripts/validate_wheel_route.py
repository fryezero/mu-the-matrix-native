#!/usr/bin/env python3
"""RENDER-TIME-003: compare the reconstructed wheel route and GetScreenWidth (reconstructed/camera/client_wheel.c)
with the client's instructions in Unicorn.

Families:
  screen_width  GetScreenWidth 0x016bc355 over random NewUI open sets: the result and the ordered window queries.
  wheel_route   WM_MOUSEWHEEL through the whole window procedure 0x0120fee3: the UI layer handler 0x00aefb79, the
                case 0x0121069d, the wheel handler 0x018588d9 and 0x0185a9bf, and the common exit 0x01211083.
                Compared: the procedure's result stage, MouseWheel, the mouse button globals, the UI flag
                0x0b436573, the camera/zoom state, the ordered GFx dispatch calls (with their packed points),
                the base.swf events and hit tests, and the window-0x3e queries.

The guest machinery (strict read tracking, import and client stubs) is validate_camera.py's. Client callees that
are not part of the route are replaced by synthetic values; each is listed in EXTRA_STUBS with its reason. The
GFx dispatch 0x00ac9800 and base.swf's HitTest are Scaleform behaviour: they are inputs here, not reconstructed.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_camera as vc  # noqa: E402

ROUTINES = {
    'screen_width': (0x016bc355, 0x434, None),
    'ui_layer_handler': (0x00aefb79, 0x6a0, None),
    'world_list': (0x00da9d49, 0x14, None),
    'wndproc': vc.ROUTINES['wndproc'],
    'wheel_zoom': vc.ROUTINES['wheel_zoom'],
    'apply_zoom': vc.ROUTINES['apply_zoom'],
}
DIGESTS = {
    'screen_width': 'cfcaaec6c7a7651f60443688446c13d68daa889c15b8708166b54cf935b26e8e',
    'ui_layer_handler': '9ff4ae84d9906578cdb9f4890b2188850b994d5bec6ea9f7f042cf616871bb76',
    'world_list': 'a6dbe75e2e1edf2e8ddd1868c690e1903256f39e65efdde7968523ab84342f35',
}

WNDPROC, CHKSTK, DEFPROC_CALL, WNDPROC_EXIT = 0x0120fee3, 0x0191c5a0, 0x012110b7, 0x012110c9
HWND, GFX_SINGLETON, UI_LAYER, CHAT_HOLDER = 0x06fc9c94, 0x01d22c0c, 0x01d22c60, 0x01d22c6c
A = vc.ARENA
MANAGER, INPUT, CHAT, MOVIE, VTABLE, FOCUS, UIOBJ = (A + 0x30000, A + 0x31000, A + 0x32000, A + 0x33000,
                                                   A + 0x33400, A + 0x34000, A + 0x36000)
HANDLE_EVENT, HIT_TEST = vc.STUBS + 0x4000, vc.STUBS + 0x4010

EXTRA_STUBS = {
    # address: (cleanup bytes, reason)
    0x009fe825: (0, 'message-hook object getter at the top of the procedure (not part of the route)'),
    0x009fe97b: (0xc, 'message hook (logging/IME); its result is unused'),
    0x00af0245: (0x10, 'UI layer pre-processing (text input focus); its result is unused'),
    0x00aae6f9: (0, 'GFx window visibility (Scaleform GetVisible) of the manager window +0x254: input'),
    0x00ac9800: (0xc, 'GFx mouse dispatch (Scaleform window hit tests and handlers): input "handled"'),
    0x00cd4ea8: (0, 'zoom-change log text getter after 0x0185a9bf'),
    0x00cd5d29: (4, 'zoom-change log text getter after 0x0185a9bf'),
    0x01983b90: (0, 'zoom-change log formatter (cdecl)'),
    HANDLE_EVENT: (4, 'base.swf HandleEvent (vtable +0xb4): recorded event'),
    HIT_TEST: (0x10, 'base.swf HitTest (vtable +0xc0): input'),
}


class Env(ctypes.Structure):
    DISPATCH = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint32, ctypes.c_uint32,
                                ctypes.c_uint32)
    HIT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)
    EVENT = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.c_float, ctypes.c_float, ctypes.c_float)
    OPEN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32)
    _fields_ = [('context', ctypes.c_void_p), ('dispatch', DISPATCH), ('hit_test', HIT), ('event', EVENT),
                ('window_open', OPEN), ('origin_x', ctypes.c_int32), ('origin_y', ctypes.c_int32),
                ('hero_busy', ctypes.c_uint8), ('base_movie', ctypes.c_uint8), ('focus_window_shown', ctypes.c_uint8),
                ('chat_in_view', ctypes.c_uint8), ('gfx_input', ctypes.c_uint8), ('gfx_window6', ctypes.c_uint8)]


def load_library(directory=None):
    lib = vc.load_library(directory)
    P = ctypes.POINTER
    lib.mu_client_screen_width.argtypes = [Env.OPEN, ctypes.c_void_p]
    lib.mu_client_screen_width.restype = ctypes.c_int32
    lib.mu_client_mouse_wheel.argtypes = [P(vc.WorldCamera), P(vc.View), P(vc.Mouse), P(Env), ctypes.c_uint32,
                                          ctypes.c_uint32, ctypes.c_int32, P(ctypes.c_uint8)]
    lib.mu_client_mouse_wheel.restype = ctypes.c_int
    return lib


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def from_word(w):
    return struct.unpack('<f', struct.pack('<I', w & 0xffffffff))[0]


class Tally(vc.Tally):
    pass


def new_guest(text, data, flag):
    imports = dict(vc.IMPORTS)
    imports[0x01a7c7e0] = ('ClientToScreen', 2)
    stubs = {k: v for k, v in vc.CLIENT_STUBS.items() if k != 0x00da9d49}   # the world list runs here
    saved = vc.IMPORTS, vc.CLIENT_STUBS
    vc.IMPORTS, vc.CLIENT_STUBS = imports, stubs
    try:
        guest = vc.Guest(text, data, flag)
    finally:
        vc.IMPORTS, vc.CLIENT_STUBS = saved
    guest.answers = {}
    for address, (cleanup, reason) in EXTRA_STUBS.items():
        guest.stub_client(address, cleanup, lambda args, ecx, a=address: guest.answers[a](args, ecx), reason=reason)

    def chkstk(uc, address, size, ignored):   # __chkstk: lower esp by eax, no page probes
        x = guest.x
        esp, eax = uc.reg_read(x.UC_X86_REG_ESP), uc.reg_read(x.UC_X86_REG_EAX)
        ret = struct.unpack('<I', guest.get(esp, 4))[0]
        uc.reg_write(x.UC_X86_REG_ESP, esp + 4 - eax)
        uc.reg_write(x.UC_X86_REG_EIP, ret)
    guest.uc.hook_add(guest.u.UC_HOOK_CODE, chkstk, begin=CHKSTK, end=CHKSTK)

    def defproc(uc, address, size, ignored):  # DefWindowProc tail of the common exit: not executed
        guest.calls.append(('DefWindowProc', ()))
        uc.reg_write(guest.x.UC_X86_REG_EIP, WNDPROC_EXIT)
    guest.uc.hook_add(guest.u.UC_HOOK_CODE, defproc, begin=DEFPROC_CALL, end=DEFPROC_CALL)
    guest.uc.mem_write(HANDLE_EVENT, b'\xc3')
    guest.uc.mem_write(HIT_TEST, b'\xc3')
    return guest


# ---------------- GetScreenWidth ----------------

SCREEN_IDS = [0x3, 0x4, 0x5, 0x6, 0x7, 0x8, 0x9, 0xa, 0xb, 0xc, 0xd, 0xe, 0xf, 0x10, 0x12, 0x13, 0x14, 0x15, 0x16,
              0x17, 0x18, 0x19, 0x1a, 0x1b, 0x38, 0x39, 0x3b, 0x3f, 0x41, 0x42, 0x43, 0x46, 0x47, 0x48, 0x49, 0x4a,
              0x4b]


def case_screen_width(guest, lib, tally, generator, count):
    for number in range(count):
        k = generator.choice([0, 0, 1, 1, 2, 3, 5])
        opened = set(generator.sample(SCREEN_IDS, k)) if number else set()
        if generator.random() < 0.05:
            opened.add(generator.randint(0x50, 0x60))   # an id the routine never asks about
        guest.reset_memory()
        guest.answers.clear()
        guest.client_values[0x00f2bb92] = UIOBJ
        guest.client_stubs[0x00f2aba9] = guest.client_stubs[0x00f2aba9][:2] + (
            lambda args, ecx: int(args[0] in opened),) + guest.client_stubs[0x00f2aba9][3:]
        got = guest.call(ROUTINES['screen_width'][0], [])
        got_q = [w[0] for name, w in guest.calls if name == hex(0x00f2aba9)]
        asked = []
        cb = Env.OPEN(lambda ctx, i: (asked.append(i), int(i in opened))[1])
        want = lib.mu_client_screen_width(cb, None)
        ok = got == want and got_q == asked
        tally.add('GetScreenWidth 0x016bc355', ok, {'open': sorted(opened), 'got': got, 'want': want,
                                                    'queries': [got_q, asked]})
        if not number:
            tally.add('GetScreenWidth with no window open is 640', got == 640, {'got': got})


# ---------------- wheel route ----------------

def route_scenario(generator):
    c, view = vc.world_scenario(generator)
    c.world = generator.choice([0, 0, 0, 2, 3, 0x8b, 0x45, 6])
    c.scene = generator.choice([6, 6, 6, 6, 5])
    c.zoom_timer.done = generator.choice([1, 1, 1, 0])
    s = {
        'delta': generator.choice([120, -120, 240, -240, 1, -1, 119, -119, 60, 0, 0x7fff, -0x8000]),
        'screen': (generator.randint(-200, 3000), generator.randint(-200, 2000)),
        'origin': (generator.choice([420, 0, generator.randint(-100, 2000)]),
                   generator.choice([297, 0, generator.randint(-100, 1500)])),
        'hero': generator.choice([0, 0, 0, 1, 0x80, 0xff]),
        'base_movie': generator.random() < 0.85,
        'focus': generator.choice([None, None, None, 0, 1]),
        'dispatch': [generator.random() < 0.2, generator.random() < 0.2],
        'hits': [generator.random() < 0.3, generator.random() < 0.15],
        'chat': generator.random() < 0.15,
        'input': generator.random() < 0.9,
        'window6': generator.random() < 0.15,
        'window3e': generator.random() < 0.15,
        'skill': generator.choice([0x185d, 0x1000, 0]), 'cls': generator.choice([0, 2, 3]),
        'mouse': {'x': generator.randint(0, 640), 'y': generator.randint(0, 480),
                  'left': generator.randint(0, 1), 'left_push': generator.randint(0, 1),
                  'left_pop': generator.randint(0, 1), 'left_double': generator.randint(0, 1),
                  'wheel': generator.randint(-3, 3)},
    }
    m = s['mouse']
    m['last_click_x'] = generator.choice([m['x'], generator.randint(0, 640)])
    m['last_click_y'] = generator.choice([m['y'], generator.randint(0, 480)])
    if generator.random() < 0.3:   # the live Lorencia state: every memory-held guard clear
        s.update(hero=0, focus=None, chat=False, window6=False, window3e=False, base_movie=True)
        c.world, c.scene, c.zoom_timer.done = 0, 6, 1
    return c, view, s


def install_route(guest, c, view, s, now):
    vc.install_world(guest, c, view, now, {0x0106b9ca: s['skill'], 0x0106b99d: s['cls']})
    guest.answers.clear()
    g = guest
    g.put_u(HWND, 0x00010abc)
    g.put_u(GFX_SINGLETON, MANAGER)
    g.put_u(MANAGER + 0x70, INPUT if s['input'] else 0)
    g.put(INPUT + 0xc, bytes([int(s['window6'])]))
    g.put_u(MANAGER + 0x254, FOCUS if s['focus'] is not None else 0)
    g.put_u(UI_LAYER + 0x88, MOVIE if s['base_movie'] else 0)
    g.put_u(MOVIE, VTABLE)
    g.put_u(VTABLE + 0xb4, HANDLE_EVENT)
    g.put_u(VTABLE + 0xc0, HIT_TEST)
    g.put_u(CHAT_HOLDER, CHAT)
    g.put(CHAT + 0x68, bytes([int(s['chat'])]))
    g.put(vc.HERO + 0x190, bytes([s['hero']]))   # install_world's hero ([0x0a39d754])
    m = s['mouse']
    g.put_i(0x0bdc5ad8, m['x'], m['y'])
    g.put_i(0x06fc9e58, m['last_click_x'], m['last_click_y'])
    g.put(0x0bdc5981, bytes([m['left']]))
    g.put(0x0bdc599c, bytes([m['left_push']]))
    g.put(0x0bdc5983, bytes([m['left_pop']]))
    g.put(0x0bdc59a0, bytes([m['left_double']]))
    g.put_i(0x0bdc59a4, m['wheel'])
    g.put(0x0b436573, b'\x00')
    ox, oy = s['origin']

    def client_to_screen(args):
        point = args[1]
        x, y = struct.unpack('<ii', g.get(point, 8))
        g.put(point, struct.pack('<ii', x + ox, y + oy))
        return 1
    g.handler['ClientToScreen'] = client_to_screen
    dispatch_calls = iter(range(2))
    g.answers[0x009fe825] = lambda a, e: UIOBJ
    g.answers[0x009fe97b] = lambda a, e: 0
    g.answers[0x00af0245] = lambda a, e: 0
    g.answers[0x00aae6f9] = lambda a, e: int(bool(s['focus'])) if e == FOCUS else -1
    g.answers[0x00ac9800] = lambda a, e: int(s['dispatch'][next(dispatch_calls)]) if e == MANAGER else -1
    g.answers[0x00cd4ea8] = lambda a, e: UIOBJ
    g.answers[0x00cd5d29] = lambda a, e: UIOBJ + 0x100
    g.answers[0x01983b90] = lambda a, e: 0
    g.answers[HANDLE_EVENT] = lambda a, e: 0
    hit_calls = iter(range(2))
    g.answers[HIT_TEST] = lambda a, e: int(s['hits'][next(hit_calls)]) if e == MOVIE else -1
    g.client_values[0x00f2bb92] = UIOBJ
    g.client_stubs[0x00f2aba9] = g.client_stubs[0x00f2aba9][:2] + (
        lambda args, ecx: int(s['window3e']) if args[0] == 0x3e else -1,) + g.client_stubs[0x00f2aba9][3:]


def guest_trace(guest):
    out = []
    for name, w in guest.calls:
        if name == hex(0x00ac9800):
            out.append(('dispatch', w[0], w[1], w[2]))
        elif name == hex(HIT_TEST):
            out.append(('hit', from_word(w[0]), from_word(w[1]), w[2]))
        elif name == hex(0x00f2aba9):
            out.append(('window', w[0]))
    return out


def event_trace(guest):
    out = []
    for name, w in guest.calls:
        if name == hex(HANDLE_EVENT):
            e = w[0]
            t = struct.unpack('<I', guest.get(e, 4))[0]
            if t == 4:
                x, y, lines = struct.unpack('<3f', guest.get(e + 4, 12))
                out.append((t, x, y, lines, struct.unpack('<I', guest.get(e + 0x10, 4))[0],
                            struct.unpack('<I', guest.get(e + 0x14, 4))[0]))
            else:
                out.append((t,))
    return out


def case_wheel_route(guest, lib, tally, generator, count):
    stages = {}
    for number in range(count):
        c, view, s = route_scenario(generator)
        now = generator.getrandbits(32)
        install_route(guest, c, view, s, now)
        wparam = ((s['delta'] & 0xffff) << 16) | generator.choice([0, 4, 8])
        lparam = ((s['screen'][1] & 0xffff) << 16) | (s['screen'][0] & 0xffff)
        min_index = 1 if s['cls'] == 2 or s['skill'] == 0x185d else 0
        try:
            ret = guest.call(WNDPROC, [0x00010abc, 0x20a, wparam, lparam], until=WNDPROC_EXIT, count=600000)
        except vc.Stop as stop:
            tally.add('wheel route 0x0120fee3 (WM_MOUSEWHEEL)', False, {'stop': str(stop)})
            continue
        got = vc.world_state(guest)
        got_mouse = {'left': guest.get(0x0bdc5981, 1)[0], 'left_push': guest.get(0x0bdc599c, 1)[0],
                     'left_pop': guest.get(0x0bdc5983, 1)[0], 'left_double': guest.get(0x0bdc59a0, 1)[0],
                     'wheel': guest.get_i(0x0bdc59a4)}
        got_flag = guest.get(0x0b436573, 1)[0]
        got_trace, got_events = guest_trace(guest), event_trace(guest)
        defproc = any(name == 'DefWindowProc' for name, w in guest.calls)
        # C
        mouse = vc.Mouse()
        for key, value in s['mouse'].items():
            setattr(mouse, key, value)
        trace, events = [], []
        e = Env()
        e.dispatch = Env.DISPATCH(lambda ctx, call, msg, wp, pt: (trace.append(('dispatch', msg, wp, pt)),
                                                                  int(s['dispatch'][call]))[1])
        e.hit_test = Env.HIT(lambda ctx, x, y: (trace.append(('hit', f32(x), f32(y), 3)),
                                                int(s['hits'][sum(1 for t in trace if t[0] == 'hit') - 1]))[1])

        def on_event(ctx, t, x, y, lines):
            events.append((t, f32(x), f32(y), f32(lines), 0, 0) if t == 4 else (t,))
        e.event = Env.EVENT(on_event)
        e.window_open = Env.OPEN(lambda ctx, i: (trace.append(('window', i)), int(s['window3e']))[1])
        e.origin_x, e.origin_y = s['origin']
        e.hero_busy = int(bool(s['hero']))
        e.base_movie = int(s['base_movie'])
        e.focus_window_shown = int(bool(s['focus']))
        e.chat_in_view, e.gfx_input, e.gfx_window6 = int(s['chat']), int(s['input']), int(s['window6'])
        flag = ctypes.c_uint8(0)
        stage = lib.mu_client_mouse_wheel(ctypes.byref(c), ctypes.byref(view), ctypes.byref(mouse), ctypes.byref(e),
                                          wparam, lparam, min_index, ctypes.byref(flag))
        want = vc.c_state(c, view)
        want_mouse = {k: getattr(mouse, k) for k in got_mouse}
        diff = {k: (got[k], want[k]) for k in got if not vc.states_equal({k: got[k]}, {k: want[k]})}
        ok = (not diff and got_mouse == want_mouse and got_flag == flag.value and got_trace == trace
              and got_events == events and defproc == (stage != 1) and (stage != 1 or ret == 0))
        stages[stage] = stages.get(stage, 0) + 1
        tally.add('wheel route 0x0120fee3 (WM_MOUSEWHEEL)', ok,
                  {'s': {k: v for k, v in s.items() if k != 'mouse'}, 'world': c.world, 'scene': c.scene, 'done': c.zoom_timer.done, 'stage': stage, 'diff': diff, 'mouse': [got_mouse, want_mouse], 'flag': [got_flag, flag.value],
                   'trace': [got_trace, trace], 'events': [got_events, events], 'defproc': defproc})
    return stages


FAMILIES = [('screen_width', case_screen_width, 1.0), ('wheel_route', case_wheel_route, 2.0)]

MUTATIONS = [
    ('screen width: one side window is 260', 'client_wheel.c', 'width = 450;', 'width = 260;', 'screen_width'),
    ('screen width: window 0x4b checked before 0x4a', 'client_wheel.c',
     'if (open(context, 0x4a))\n        width = 260;\n    else if (open(context, 0x4b))\n        width = 70;',
     'if (open(context, 0x4b))\n        width = 70;\n    else if (open(context, 0x4a))\n        width = 260;',
     'screen_width'),
    ('UI layer ignores the hero byte', 'client_wheel.c', 'if (e->hero_busy || !e->base_movie',
     'if (!e->base_movie', 'wheel_route'),
    ('UI layer skips the raw-lParam hit test', 'client_wheel.c',
     'if (e->hit_test(e->context, (float)(int32_t)(lparam & 0xffffu)', 'if (0 && e->hit_test(e->context, (float)(int32_t)(lparam & 0xffffu)',
     'wheel_route'),
    ('client point without the window origin', 'client_wheel.c', '- e->origin_x;', ';', 'wheel_route'),
    ('wheel lines without the << 7 / 120 step', 'client_wheel.c', 'delta * 128 / 120 / 120 * 3', 'delta / 120 * 3',
     'wheel_route'),
    ('chat InMouseViewBox guard dropped', 'client_wheel.c', '&& !e->chat_in_view &&', '&&', 'wheel_route'),
    ('world 0x8b guard dropped', 'client_wheel.c', '&& c->world != 0x8b &&', '&&', 'wheel_route'),
    ('UI layer does not store MouseWheel', 'client_wheel.c', '    m->wheel = delta / 120;\n    if (e->hit_test',
     '    (void)m;\n    if (e->hit_test', 'wheel_route'),
    ('LPop check of the common exit dropped', 'client_wheel.c',
     'if (m->left_pop == 1 && (m->last_click_x != m->x || m->last_click_y != m->y))\n        m->left_pop = 0;',
     '', 'wheel_route'),
]


def run_mutations(guest, seed, count):
    results = []
    table = {name: function for name, function, scale in FAMILIES}
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        shutil.copytree(ROOT / 'reconstructed' / 'record-math', scratch / 'record-math',
                        ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d'))
        if (ROOT / 'reconstructed' / 'deps.mk').exists():   # the reconstructed Makefiles include ../deps.mk
            shutil.copy(ROOT / 'reconstructed' / 'deps.mk', scratch / 'deps.mk')
        for label, filename, old, new, family in MUTATIONS:
            target = scratch / 'camera'
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(ROOT / 'reconstructed' / 'camera', target,
                            ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.d'))
            source = (target / filename).read_text()
            if source.count(old) != 1:
                raise ValueError(f'mutation anchor not unique: {label}')
            (target / filename).write_text(source.replace(old, new))
            lib = load_library(target)
            tally = Tally()
            table[family](guest, lib, tally, random.Random(f'{seed}:{family}'), count)
            results.append({'mutation': label, 'family': family,
                            'mismatches': sum(r['mismatches'] for r in tally.results.values()),
                            'cases': sum(r['cases'] for r in tally.results.values())})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--text', default=vc.pins.TEXT.default_str())
    parser.add_argument('--data', default=vc.pins.DATA.default_str())
    parser.add_argument('--cases', type=int, default=600)
    parser.add_argument('--seed', type=int, default=0x525433)
    parser.add_argument('--output', default=None)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--print-digests', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    text = vc.load_pinned(args.text, vc.TEXT_BYTES, vc.TEXT_SHA256, 'restored text')
    data = vc.load_pinned(args.data, vc.DATA_BYTES, vc.DATA_SHA256, 'second image section')
    for name, (start, length, digest) in ROUTINES.items():
        actual = hashlib.sha256(text[start - vc.TEXT_BASE:start - vc.TEXT_BASE + length]).hexdigest()
        if args.print_digests:
            print(name, actual)
        if (digest or DIGESTS[name]) != actual and not args.print_digests:
            raise ValueError(f'pinned routine {name} changed')
    if args.print_digests:
        return 0
    guest = new_guest(text, data, struct.pack('<I', 1))
    lib = load_library()
    tally = Tally()
    extra = {}
    for name, function, scale in FAMILIES:
        result = function(guest, lib, tally, random.Random(f'{args.seed}:{name}'), int(args.cases * scale))
        if result is not None:
            extra[name + '_stages'] = {str(k): v for k, v in sorted(result.items())}
    mutations = run_mutations(guest, args.seed, max(100, args.cases // 3)) if args.mutations else None
    for entry in mutations or []:
        print(f"mutation {entry['mutation']:52s} {entry['mismatches']:5d}/{entry['cases']} detected")
    total = sum(r['cases'] for r in tally.results.values())
    bad = sum(r['mismatches'] for r in tally.results.values())
    for name, r in tally.results.items():
        print(f"{name:52s} {r['cases']:7d} cases  {r['mismatches']:5d} mismatches")
        if r['first'] is not None:
            print('    first:', json.dumps(r['first'], default=str)[:900])
    print(f'total {total} comparisons, {bad} mismatches', extra)
    report = {'routines': {k: {'start': hex(v[0]), 'bytes': v[1]} for k, v in ROUTINES.items()},
              'stubs': {hex(k): v[1] for k, v in EXTRA_STUBS.items()}, 'results': tally.results, 'extra': extra,
              'mutations': mutations, 'seed': args.seed, 'cases': args.cases}
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    undetected = [m for m in (mutations or []) if m['mismatches'] == 0]
    if undetected:
        print('undetected mutations:', [m['mutation'] for m in undetected])
    return 1 if bad or undetected else 0


if __name__ == '__main__':
    sys.exit(main())
