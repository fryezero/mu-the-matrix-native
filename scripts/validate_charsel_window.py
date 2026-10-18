#!/usr/bin/env python3
"""Compare the reconstructed character-select window with the client (NATIVE-CHARSEL-001).

CCharSelMainWin (vtable 0x01a7ec20) runs as client code in Unicorn on the
UI-002 machine (scripts/validate_ui_widgets.py: CWin, CButton, CSprite, the
text facade and CUIRenderTextOriginal are client code there too) and the
reconstruction reconstructed/ui/ui_charsel.c runs through ctypes. Every case
compares the platform-call streams (OpenGL, GDI, sounds, client events) word
for word and, after every step, the window's complete state (both sprites,
the four buttons, the window rectangle, the warning flag and the tip index).

Client code run unmodified: the constructor 0x009a4838, Create 0x009a492e,
SetPosition 0x009a4be1, Show 0x009a4d2c, CursorInWin 0x009a4d9f,
UpdateDisplay 0x009a4dd7, ReleaseControls 0x009a5164, UpdateWhileActive
0x009a5197, RenderControls 0x009a533d and the delete check 0x009a553c, with
CWin::Update/Render driving them.

Modelled explicitly (stubs): the character table getter 0x0095f6db (a
synthetic CharactersClient), 0x0095f75d's object (+4 flag), 0x0185bdbd and
0x010a5cf2/0x010a5dca (slot mode and count), the GFx manager queries
0x009a59f6/0x00aae6f9/0x009a5a06, rand() 0x01989721, the connect check
0x009a5029, and the actions the buttons start, recorded as events: the GFx
create interface 0x00b49bf4(1), the menu 0x00c8c8b1, the loading scene
0x0185a75a(0), message boxes 0x00b3967c/0x011e3598 and the delete
confirmation 0x00b49c82.
"""
import argparse
import ctypes
from ctypes import POINTER, Structure, c_char, c_int32, c_uint8, c_uint16, c_uint32, c_void_p, c_int, c_double
import json
from pathlib import Path
import random
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import client_ui_machine as cm  # noqa: E402
import model_hierarchy_common as common  # noqa: E402
import validate_ui as vu  # noqa: E402
import validate_ui_widgets as vw  # noqa: E402

CSW_SIZE = 0x518
RECORD, OBJECT = 0x3670, 0x3254
CSW_ROOTS = (0x009a4838, 0x009a492e, 0x009a4be1, 0x009a4d2c, 0x009a4d9f, 0x009a4dd7, 0x009a5164, 0x009a5197,
             0x009a533d, 0x009a553c, 0x010ad7b2, 0x010ad7d5, 0x00986569, 0x0098659a, 0x0120d0ce, 0x0120d26d,
             0x0098285a, 0x011a0998, 0x011a09f3, 0x0119fe9b, 0x0119fedf)
EVENT_CREATE, EVENT_MENU, EVENT_CONNECT, EVENT_MESSAGE, EVENT_NOTICE, EVENT_CONFIRM = range(0x20, 0x26)
CSW_STOPS = vw.STOPS | {0x0095f6db, 0x0185bdbd, 0x010a5cf2, 0x010a5dca, 0x00ac3bf7, 0x009a59f6, 0x00aae6f9,
                        0x009a5a06, 0x00b49bf4, 0x009a5920, 0x00b4b684, 0x01989721, 0x009a5029, 0x0185a75a,
                        0x009a5792, 0x00c8c8b1, 0x009a589a, 0x01072a96, 0x00b3967c, 0x011e3598, 0x008e7940,
                        0x009619dd, 0x00b39648, 0x00b49c82, 0x009a58e5}
TEXTS = (0x6ae, 0x6cb, 0x6cc, 0x1b4, 0x1b5, 0x676, 0x1a1, 0x166e, 0x6b0)
GFX, GFX_22C, GFX_90, FLAG_OBJ, SLOT_OBJ = 0x7e008000, 0x7e00a000, 0x7e009000, 0x7e00b000, 0x7e00c000


class Slot(Structure):
    _fields_ = [('live', c_uint8), ('flags', c_uint8), ('byte_17', c_uint8), ('level', c_uint16),
                ('byte_3634', c_uint8), ('name', c_char * 32)]


class Input(Structure):
    _fields_ = [('slots', Slot * 16), ('selected', c_int32), ('flag_95f75d', c_uint8), ('slot_mode', c_int32),
                ('slot_count', c_int32), ('gfx_create_open', c_uint8), ('gfx_movie_busy', c_uint8),
                ('gfx_blocked', c_uint8), ('enter_refused', c_uint8), ('server_flag', c_uint8), ('random', c_int32)]


def library(path=None):
    lib = vw.library(path)
    P = c_void_p
    sigs = {'mu_ui_charsel_win_init': ([P, P], None), 'mu_ui_charsel_win_create': ([P, P], None),
            'mu_ui_charsel_win_set_position': ([P, P, c_int32, c_int32], None),
            'mu_ui_charsel_win_show': ([P, P, c_int], None), 'mu_ui_charsel_win_update_display': ([P, P], None),
            'mu_ui_probe_charsel_win': ([P, P], c_int), 'mu_ui_probe_charsel_held': ([P, P], c_int32),
            'mu_ui_charsel_win_cursor_in_win': ([P, P, c_int32], c_int)}
    for name, (args, res) in sigs.items():
        getattr(lib, name).argtypes = args
        getattr(lib, name).restype = res
    return lib


def normalize_authored(calls):
    out = []
    for name, words in calls:
        if name == 'Event' and words[0] >= 0x20:
            out.append(('Event', tuple(words)))
        else:
            out.extend(vw.normalize_authored([(name, words)]))
    return out


def bitmaps(rng):
    out = vw.ssw_bitmaps(rng)
    for index, (w, h) in {0x7b10: (256, 128), 0x7b11: (64, 128), 0x7b12: (64, 128), 0x7b13: (64, 128),
                          0x7b14: (64, 128)}.items():
        if rng.random() < 0.3:
            w, h = w * 2, h * rng.choice([1, 2])
        out[index] = {'width': float(w), 'height': float(h), 'texture': 4000 + index % 977, 'components': 4}
    return out


class CharselClient(vw.WidgetClient):
    def __init__(self, text, data):
        super().__init__(text, data)
        entries = [struct.unpack('<I', data[0x01a7ec20 - cm.DATA_BASE + 4 * i:0x01a7ec24 - cm.DATA_BASE + 4 * i])[0]
                   for i in range(14)]
        extra = vw.closure(text, CSW_ROOTS, entries, stops=CSW_STOPS)
        for start, end in extra.items():
            self.machine.allow((start, end))
        self.functions.update(extra)
        self.machine.uc.mem_map(0x7e000000, 0x100000, cm.UC_PROT_ALL)   # GFx and helper objects

    def install(self, inp):
        m = self.machine
        calls = m.calls
        table = m.alloc(16 * RECORD, define=True)
        manager = m.alloc(0x10, define=True)
        m.put32(manager + 8, table)
        self.table = table
        self.names = {}
        for i in range(16):
            s = inp.slots[i]
            r = table + i * RECORD
            m.write(r + OBJECT, bytes([s.live]))
            m.write(r + 0x14, bytes([s.flags, 0, 0, s.byte_17]))
            m.write(r + 0x144, struct.pack('<H', s.level))
            m.write(r + 0x3634, bytes([s.byte_3634]))
            name = m.alloc(33, define=True)
            m.write(name, bytes(s.name) + b'\0')
            m.put32(r + 0x3658, name)
        self.stub(0x0095f6db, lambda mm: manager, 0)
        m.put32(0x01cf1864, inp.selected & 0xffffffff)      # SelectedHero
        flag = m.alloc(0x10, define=True)
        m.write(flag + 4, bytes([inp.flag_95f75d]))
        self.stub(0x0095f75d, lambda mm: flag, 0)
        self.stub(0x0185bdbd, lambda mm: inp.slot_mode & 0xffffffff, 0)
        self.stub(0x010a5cf2, lambda mm: SLOT_OBJ, 0)
        self.stub(0x010a5dca, lambda mm: inp.slot_count & 0xffffffff, 0)
        m.uc.mem_write(GFX + 0x90, struct.pack('<I', GFX_90))
        m.uc.mem_write(GFX + 0x22c, struct.pack('<I', GFX_22C))
        self.stub(0x00ac3bf7, lambda mm: GFX, 0)
        self.stub(0x009a59f6, lambda mm: inp.gfx_create_open, 0)
        self.stub(0x00aae6f9, lambda mm: inp.gfx_movie_busy, 0)
        self.stub(0x009a5a06, lambda mm: inp.gfx_blocked, 0)

        def b49bf4(mm):
            if mm.args(1)[0] == 1:
                calls.append(('Event', (EVENT_CREATE, 0)))
            return 0
        self.stub(0x00b49bf4, b49bf4, 4)
        self.stub(0x009a5920, lambda mm: 0, 4)
        self.stub(0x00b4b684, lambda mm: 0, 0)
        self.stub(0x01989721, lambda mm: inp.random & 0x7fff, 0)
        self.stub(0x009a5029, lambda mm: inp.enter_refused, 4)
        self.stub(0x0185a75a, lambda mm: (calls.append(('Event', (EVENT_CONNECT, mm.args(1)[0]))), 0)[1], 0)

        def menu(mm):
            out = mm.args(1)[0]
            mm.put32(out, 0x7e00d000)
            mm.put32(out + 4, 0)
            return out
        self.stub(0x009a5792, menu, 4)
        self.stub(0x009a58e5, lambda mm: mm.u32(mm.uc.reg_read(cm.UC_X86_REG_ECX)), 0)
        self.stub(0x00c8c8b1, lambda mm: (calls.append(('Event', (EVENT_MENU, 0))), 0)[1], 0)
        self.stub(0x009a589a, lambda mm: 0, 0)
        self.stub(0x01072a96, lambda mm: inp.server_flag, 0)
        index_of = {address: index for index, address in self.strings.items()}
        self.stub(0x00b3967c, lambda mm: (calls.append(('Event', (EVENT_MESSAGE, index_of.get(mm.args(3)[2], -1)))),
                                          0)[1], 0x1c)
        self.stub(0x011e3598, lambda mm: (calls.append(('Event', (EVENT_NOTICE, mm.args(1)[0]))), 0)[1], 8)
        self.stub(0x008e7940, lambda mm: mm.u32(mm.uc.reg_read(cm.UC_X86_REG_ECX)), 0)
        self.stub(0x009619dd, lambda mm: 0, 0)
        self.stub(0x00b39648, lambda mm: 0, 0x1c)
        self.stub(0x00b49c82, lambda mm: (calls.append(('Event', (EVENT_CONFIRM, mm.args(1)[0]))), 0)[1], 4)


def snap(client, w):
    m = client.machine
    out = client.snap_win(w)
    for i in range(2):
        out += client.snap_sprite(w + 0x40 + 0xa8 * i)
    for i in range(4):
        out += client.snap_button(w + 0x190 + 0xe0 * i)
    return out + [m.read(w + 0x510, 1)[0], struct.unpack('<i', struct.pack('<I', struct.unpack('<h', m.read(
        w + 0x512, 2))[0] & 0xffffffff))[0] & 0xffffffff]


def random_input(rng):
    inp = Input()
    for i in range(16):
        s = inp.slots[i]
        s.live = 1 if rng.random() < rng.choice([0.0, 0.5, 0.9, 1.0]) else 0
        s.flags = rng.choice([0, 0, 0x10, 0x02, 0x12, 0x04])
        s.byte_17 = rng.choice([0xff, 0xff, 0xff, 0, 3])
        s.level = rng.choice([1, 400, 699, 699, 700, 700, 1000])
        s.byte_3634 = rng.choice([0, 0, 0, 1, 2])
        s.name = rng.choice([b'Nighty', b'Frye', b'Wizard', b'X'])
    inp.selected = rng.choice([-1, 0, 1, 3, 9, 12, 15, -2])
    inp.flag_95f75d = 1 if rng.random() < 0.2 else 0
    inp.slot_mode = rng.choice([0, 0, 1, 2])
    inp.slot_count = rng.choice([0, 3, 5, 8, 10, 12, 16])
    inp.gfx_create_open = 1 if rng.random() < 0.3 else 0
    inp.gfx_movie_busy = 1 if rng.random() < 0.1 else 0
    inp.gfx_blocked = 1 if rng.random() < 0.1 else 0
    inp.enter_refused = rng.choice([0, 0, 1, 2])
    inp.server_flag = 1 if rng.random() < 0.3 else 0
    inp.random = rng.randint(0, 0x7fff)
    return inp


def validate(client, lib, rng, cases):
    counts = {'cases': 0, 'render_calls': 0, 'update_frames': 0, 'state_words': 0, 'events': {}, 'clicks': 0}
    started = time.time()
    for number in range(cases):
        window = vw.WINDOWS[number % len(vw.WINDOWS)] if number < len(vw.WINDOWS) else rng.choice(vw.WINDOWS)
        rates = (cm.f32(window[0] / 640.0), cm.f32(window[1] / 480.0))
        bm = bitmaps(rng)
        strings = {index: vw.phrase(rng, rng.randint(1, 6)) for index in TEXTS if index not in (0x6ae, 0x6cb, 0x6cc) or rng.random() < 0.9}
        width_px, height_px = int(cm.f32(640.0 * rates[0])), int(cm.f32(480.0 * rates[1]))
        dib_init = bytes((((width_px * 24 + 31) & ~31) >> 3) * height_px)
        side = vw.Side(lib, window, bm, rates, strings, {'groups': [], 'notice': b''}, dib_init)
        client.setup(side.authored.state, bm, window, strings, {'groups': [], 'notice': b''})
        inp = random_input(rng)
        client.install(inp)
        m = client.machine
        m.write(client.dib, dib_init)
        client.set_input(0, 0, 0, 0, window)
        win = m.alloc(CSW_SIZE, define=True)       # a CUIMng member: zero-initialised static storage
        mine = ctypes.create_string_buffer(lib.mu_ui_probe_sizeof(8))
        lib.mu_ui_charsel_win_init(mine, ctypes.byref(inp))
        ctx = ctypes.byref(side.ctx)
        out = (c_uint32 * 8192)()
        label = f'charsel window case {number} {window}'

        def step(name, client_fn, authored_fn, compare_dib=False):
            m.calls.clear()
            del side.calls[:]
            client_fn()
            authored_fn()
            problem = vu.diff(vw.normalize(m.calls), normalize_authored(side.calls))
            if problem:
                raise AssertionError(f'{label} {name}: {problem}; client {vw.normalize(m.calls)[:6]} authored {normalize_authored(side.calls)[:6]}')
            got, want = snap(client, win), list(out[:lib.mu_ui_probe_charsel_win(mine, out)])
            if got != want:
                index = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
                raise AssertionError(f'{label} {name}: state differs at word {index}: {got[index:index + 4]} '
                                     f'{want[index:index + 4]} ({len(got)} {len(want)})')
            held_client = m.u32(vw.HELD_BUTTON)
            buttons = [win + 0x190 + 0xe0 * i for i in range(4)]
            held_client = -1 if not held_client else (buttons.index(held_client) if held_client in buttons else -2)
            if held_client != lib.mu_ui_probe_charsel_held(ctx, mine):
                raise AssertionError(f'{label} {name}: held button differs')
            if compare_dib and m.read(client.dib, len(side.dib)) != bytes(side.dib):
                raise AssertionError(f'{label} {name}: DIB contents differ')
            counts['state_words'] += len(got)
            for n, words in side.calls:
                if n == 'Event':
                    counts['events'][hex(words[0])] = counts['events'].get(hex(words[0]), 0) + 1
                elif n == 'Sound':
                    counts['clicks'] += 1
            return len(m.calls)

        step('ctor+Create', lambda: (m.call(0x009a4838, ecx=win), m.call(0x009a492e, ecx=win)),
             lambda: lib.mu_ui_charsel_win_create(ctx, mine))
        y = window[1] - m.u32(win + 0x24) - 0xe
        step('SetPosition', lambda: m.call(0x009a4be1, [0x16, y & 0xffffffff], ecx=win),
             lambda: lib.mu_ui_charsel_win_set_position(ctx, mine, 0x16, y))
        show = 1 if rng.random() < 0.9 else 0
        active = 1 if rng.random() < 0.9 else 0
        step('Show', lambda: (m.call(0x009a4d2c, [show], ecx=win), m.call(0x0098285a, [active], ecx=win)),
             lambda: (lib.mu_ui_charsel_win_show(ctx, mine, show), lib.mu_ui_win_set_active(mine, active)))
        step('UpdateDisplay', lambda: m.call(0x009a4dd7, ecx=win), lambda: lib.mu_ui_charsel_win_update_display(ctx, mine))
        counts['render_calls'] += step('Render', lambda: m.call(0x0120d26d, ecx=win),
                                       lambda: lib.mu_ui_win_render(ctx, mine), compare_dib=True)
        for frame in range(rng.choice([0, 4, 10, 20])):
            b = win + 0x190 + 0xe0 * (3 if rng.random() < 0.4 else rng.randrange(4))
            x0 = struct.unpack('<f', m.read(b + 0x1c, 4))[0]
            y0 = struct.unpack('<f', m.read(b + 8, 4))[0] - struct.unpack('<f', m.read(b + 0x20, 4))[0]
            if not (abs(x0) < 1e6 and abs(y0) < 1e6):
                x0, y0 = 0, 0
            x, yy = int(x0) + rng.choice([1, 20, 53, 54, -1]), int(y0) + rng.choice([1, 15, 29, 30, -1])
            if rng.random() < 0.15:
                x, yy = rng.randint(0, window[0]), rng.randint(0, window[1])
            delta = rng.choice([40.0, 40.0, 40.0, 0.0, -1.0])
            if rng.random() < 0.6:     # a click: hover, press, release on the same spot
                sequence = [(0, 0), (1, 0), (0, 1)]
            else:
                sequence = [rng.choice([(1, 0), (0, 1), (0, 0), (1, 1)])]
            for down, up in sequence:
                client.set_input(x, yy, down, up, window)
                side.set_input(x, yy, down, up)
                lo, hi = struct.unpack('<II', struct.pack('<d', delta))
                step(f'Update({x},{yy},{down},{up},{delta})', lambda: m.call(0x0120d0ce, [lo, hi], ecx=win),
                     lambda: lib.mu_ui_win_update(ctx, mine, delta))
                counts['update_frames'] += 1
        counts['render_calls'] += step('Render again', lambda: m.call(0x0120d26d, ecx=win),
                                       lambda: lib.mu_ui_win_render(ctx, mine), compare_dib=True)
        counts['cases'] += 1
    counts['seconds'] = round(time.time() - started, 1)
    return counts


MUTATIONS = [
    ('tip table order', '{0x6ae, 0x6cb, 0x6cc}', '{0x6cb, 0x6ae, 0x6cc}'),
    ('tip line 6 below the bar', 'mu_ui_sprite_y(bar) + 7', 'mu_ui_sprite_y(bar) + 6'),
    ('connect refused by any nonzero 0x009a5029', 'enter_refused != 1)', 'enter_refused != 0)'),
    ('delete level limit 699', 'c->level >= 0x2bc', 'c->level >= 0x2bb'),
    ('deco 0x3a above the buttons', 'y - 0x3b, 3);', 'y - 0x3a, 3);'),
    ('bar alpha 0x80', 'win->sprites[1].alpha = 0x8f;', 'win->sprites[1].alpha = 0x80;'),
    ('menu button with a disable frame', 'BITMAP_MENU, 3, 2, 1, -1,', 'BITMAP_MENU, 3, 2, 1, 2,'),
]


def run_mutations(client, seed, cases):
    import shutil
    import subprocess
    import tempfile
    results = []
    with tempfile.TemporaryDirectory() as scratch:
        for label, old, new in MUTATIONS:
            target = Path(scratch) / 'ui'
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(ROOT / 'reconstructed' / 'ui', target, ignore=shutil.ignore_patterns('*.dylib', '*.so'))
            source = (target / 'ui_charsel.c').read_text()
            if source.count(old) != 1:
                raise ValueError(f'mutation anchor not unique: {label}')
            (target / 'ui_charsel.c').write_text(source.replace(old, new))
            subprocess.run(['make', '-s', '-C', str(target)], check=True)
            suffix = 'dylib' if sys.platform == 'darwin' else 'so'
            lib = library(target / f'libmu_ui.{suffix}')
            try:
                validate(client, lib, random.Random(seed), cases)
                detected = False
            except AssertionError:
                detected = True
            results.append({'mutation': label, 'detected': detected})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--text', default=ROOT / 'evidence/x86-text-capture-09/client-text.bin')
    parser.add_argument('--data', default=ROOT / 'evidence/image-data-run10/data-capture-10/client-image-data.bin')
    parser.add_argument('--seed', type=int, default=5)
    parser.add_argument('--cases', type=int, default=60)
    parser.add_argument('--output')
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args(argv)
    text = common.load_pinned(args.text, common.TEXT_BYTES, common.TEXT_SHA256)
    data = common.load_pinned(args.data, common.DATA_BYTES, common.DATA_SHA256)
    lib = library()
    client = CharselClient(text, data)
    report = {'text_sha256': common.TEXT_SHA256, 'data_sha256': common.DATA_SHA256, 'seed': args.seed,
              'allowlisted_functions': len(client.functions)}
    report['charsel_window'] = validate(client, lib, random.Random(args.seed), args.cases)
    if args.mutations:
        report['mutations'] = run_mutations(client, args.seed, max(30, args.cases // 2))
    print(json.dumps(report, indent=1))
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1) + '\n')
    return 1 if any(not m['detected'] for m in report.get('mutations', [])) else 0


if __name__ == '__main__':
    sys.exit(main())
