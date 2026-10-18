"""Checks for the reconstructed window/widget layer (NATIVE-UI-002).

Portable checks compare the C reconstruction (CButton, CWin, CWinEx,
CServerSelWin, CutText) with independent Python statements of the client
rules on synthetic inputs.  The private check (MU_RECOVERY_INTEGRATION=1)
runs scripts/validate_ui_widgets.py, which compares the reconstruction with
the client's own instructions in Unicorn on the pinned restored captures.
"""
import ctypes
from ctypes import c_uint32
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))


def fval(word):
    return struct.unpack('<f', struct.pack('<I', word))[0]


def cut_text_model(src, lines, width):
    """CutText 0x01859f23 restated: rows of `width` bytes, break after a recent space."""
    rows = [bytearray(width) for _ in range(lines)]
    out = []
    row, line_start, space, i = 0, 0, None, 0
    current = bytearray()
    while i < len(src):
        if (i - line_start) + 1 >= width:
            if space is not None and i - space < min(width // 2, 10):
                del current[len(current) - (i - space - 1):]
                i = space + 1
            out.append(bytes(current))
            current = bytearray()
            line_start = i
            if row >= lines - 1:
                return out, row + 1
            row += 1
            space = None
        current.append(src[i])
        if src[i] == 0x20:
            space = i
        i += 1
    out.append(bytes(current))
    del rows
    return out, row + 1


class Probe:
    """Parser of reconstructed/ui/ui_probe.c's server-window stream."""

    def __init__(self, words):
        self.words, self.pos = words, 0

    def take(self, count=1):
        out = self.words[self.pos:self.pos + count]
        self.pos += count
        return out

    def sprite(self):
        head = self.take(33)
        sprite = {'texture': head[0], 'position': [fval(w) for w in head[4:12]],
                  'texcoord': [fval(w) for w in head[12:20]], 'max_frame': head[23], 'now_frame': head[24],
                  'show': head[31], 'has_frames': head[32]}
        if head[32]:
            sprite['frames'] = [fval(w) for w in self.take(2*min(head[23], 16))]
        sprite['x'] = int(sprite['position'][0])
        return sprite

    def button(self):
        b = self.sprite()
        state = self.take()[0]
        b.update(enable=state & 0xff, active=(state >> 8) & 0xff, click=(state >> 16) & 0xff, check=state >> 24)
        b['map'] = [w if w < 0x80000000 else w - (1 << 32) for w in self.take(8)]
        if self.take()[0]:
            length = self.take()[0]
            b['text'] = bytes(self.take(length))
            count = self.take()[0]
            b['colors'] = self.take(count)
            b['text_color'] = self.take()[0]
        b['text_add_y'] = fval(self.take()[0])
        return b

    def win(self):
        w = self.take(11)
        return {'show': w[0] & 0xff, 'active': (w[0] >> 8) & 0xff, 'state': w[1], 'x': w[2], 'y': w[3],
                'width': w[4], 'height': w[5], 'buttons': w[10]}

    def server_win(self):
        out = {'win': self.win(), 'groups': [self.button() for _ in range(25)], 'servers': [], 'gauges': []}
        for _ in range(20):
            out['servers'].append(self.button())
            gauge = self.sprite()
            gauge['rect'] = self.take(4)
            gauge['xy'] = self.take(2)
            out['gauges'].append(gauge)
        out['decos'] = [self.sprite() for _ in range(2)]
        out['arrows'] = [self.sprite() for _ in range(2)]
        out['notice'] = self.win()
        out['notice_sprites'] = [self.sprite() for _ in range(5)]
        out['lines'] = self.take(3)
        counts = self.take(7)
        out.update(group_count=counts[0], left=counts[1], right=counts[2], server_count=counts[3], top=counts[4],
                   selected=counts[5] if counts[5] < 0x80000000 else counts[5] - (1 << 32),
                   group=counts[6] if counts[6] < 0x80000000 else -1)
        text = bytes(self.take(2*0x53))
        out['text'] = [text[:0x53].split(b'\0')[0], text[0x53:].split(b'\0')[0]]
        assert self.pos == len(self.words)
        return out


class WidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        import importlib.util
        spec = importlib.util.spec_from_file_location('validate_ui_widgets', ROOT/'scripts/validate_ui_widgets.py')
        cls.v = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(cls.v)
        except ImportError as error:          # unicorn/capstone are optional for portable checks
            raise unittest.SkipTest(f'validator imports unavailable: {error}')
        cls.lib = cls.v.library()

    def side(self, window=(1024, 768), servers=None, bitmaps=None, strings=None):
        rates = (window[0]/640.0, window[1]/480.0)
        bitmaps = bitmaps or self.bitmaps()
        width_px, height_px = int(640.0*rates[0]), int(480.0*rates[1])
        dib = bytes((((width_px*24 + 31) & ~31) >> 3)*height_px)
        return self.v.Side(self.lib, window, bitmaps, rates, strings or {}, servers or {'groups': [], 'notice': b''},
                           dib)

    def bitmaps(self, side_height=4):
        out = self.v.vu.base_bitmaps()
        for index, (w, h) in {0x7b0e: (128, 128), 0x7b0f: (256, 128), 0x7b10: (256, 8), 0x7b11: (256, 128),
                              0x7b19: (4, 4), 0x7b1a: (512, 16), 0x7b1b: (8, side_height)}.items():
            out[index] = {'width': float(w), 'height': float(h), 'texture': 100 + index % 97, 'components': 4}
        return out

    def build(self, side, show=True, select=None):
        ctx = ctypes.byref(side.ctx)
        self.lib.mu_ui_server_win_create(ctx, side.win)
        x = (side.ctx.input.screen_width - 0x1d1)//2
        probe = self.state(side)
        y = (side.ctx.input.screen_height - probe['win']['height'])//2
        self.lib.mu_ui_server_win_set_position(ctx, side.win, x, y)
        if show:
            self.lib.mu_ui_win_show(ctx, side.win, 1)
            self.lib.mu_ui_win_set_active(side.win, 1)
        if select is not None:
            self.lib.mu_ui_probe_select(side.win, select)
        self.lib.mu_ui_server_win_update_display(ctx, side.win)
        return x, y

    def state(self, side):
        return Probe(side.snapshot()).server_win()

    # ---- CutText ----------------------------------------------------------

    def test_cut_text_matches_the_model(self):
        rng = random.Random(7)
        words = [b'MTM', b'Season', b'21', b'/', b'Powered', b'by', b'Network-Online', b'Servers', b'x'*30]
        for _ in range(300):
            text = b' '.join(rng.choice(words) for _ in range(rng.randint(0, 25)))
            lines, width = rng.choice([1, 2, 3]), rng.choice([5, 12, 21, 0x53])
            buf = ctypes.create_string_buffer(lines*width)
            count = self.lib.mu_ui_cut_text(text, buf, lines, width)
            rows, model_count = cut_text_model(text, lines, width)
            self.assertEqual(count, model_count, (text, lines, width))
            for r, row in enumerate(rows):
                self.assertEqual(buf.raw[r*width:r*width + len(row)], row, (text, lines, width, r))
                self.assertEqual(buf.raw[r*width + len(row)], 0)

    # ---- CButton and the window layout --------------------------------------

    def test_buttons_frames_and_image_maps(self):
        side = self.side()
        self.build(side)
        state = self.state(side)
        group, server = state['groups'][0], state['servers'][0]
        # CButton::Create(108, 26, cha_bt, 4, down 2, over 1, -1, check 3, -1, -1, -1)
        self.assertEqual(group['map'], [0, 2, 1, -1, 3, 3, 3, -1])
        self.assertEqual(server['map'], [0, 2, 1, -1, -1, -1, -1, -1])
        # frames stacked vertically: v = (26*i + 0.5) / texture height
        for i in range(4):
            self.assertAlmostEqual(group['frames'][2*i + 1], (26*i + 0.5)/128.0, places=6)
            self.assertAlmostEqual(group['frames'][2*i], 0.5/128.0, places=6)
        self.assertEqual((group['enable'], group['active'], group['check']), (1, 1, 0))

    def test_window_layout_follows_set_position(self):
        for window, side_height in (((1024, 768), 4), ((1920, 1080), 4), ((800, 600), 8)):
            side = self.side(window, bitmaps=self.bitmaps(side_height))
            x, y = self.build(side, show=False)
            state = self.state(side)
            box = 6 + 6 + 10*side_height
            self.assertEqual(state['notice']['height'], box)
            self.assertEqual((state['win']['width'], state['win']['height']), (0x1d1, box + 0x22c))
            h = box + 0x22c
            top_y = h + y - 26 - 5 - box
            side_y = h + y - (26*11 + box + 10)
            right_x = x + 108 + 193 + 0x38
            for i in range(5):
                top_y -= 26
                self.assertEqual(state['groups'][i]['position'][0], (0x1d1 - 108)//2 + x)
                self.assertEqual(round(state['groups'][i]['position'][1]), window[1] - top_y)
            for i in range(10):
                self.assertEqual(state['groups'][5 + i]['position'][0], x)
                self.assertEqual(state['groups'][15 + i]['position'][0], right_x)
                self.assertEqual(round(window[1] - state['groups'][5 + i]['position'][1]), side_y + 26*i)
            self.assertEqual(state['notice']['x'], x - (512 - 0x1d1)//2)
            self.assertEqual(state['notice']['y'], h + y - box)
            # column decorations: datum (8, 0x13) and (0x3c, 0x13) against buttons 5 and 15 (+0x6c)
            self.assertEqual(state['decos'][0]['position'][0], x - 8)
            self.assertEqual(state['decos'][1]['position'][0], right_x + 0x6c - 0x3c)

    def test_update_display_places_groups_and_fills_servers(self):
        groups = []
        for i in range(7):
            groups.append({'id': i, 'type': 0, 'position': 2, 'button': -1, 'name': b'T%d' % i, 'description': b'',
                           'servers': []})
        for i in range(12):
            groups.append({'id': 10 + i, 'type': 2 if i == 1 else 0, 'position': 0, 'button': -1, 'name': b'L%d' % i,
                           'description': b'left group description text', 'servers': [
                               {'slot': s, 'percent': 10*s, 'type': s % 4, 'name': b'S%d' % s} for s in range(5)]})
        groups.append({'id': 99, 'type': 0, 'position': 1, 'button': -1, 'name': b'R0', 'description': b'',
                       'servers': []})
        servers = {'groups': groups, 'notice': b'notice text'}
        side = self.side(servers=servers)
        self.build(side, select=6)
        state = self.state(side)
        self.assertEqual((state['top'], state['left'], state['right'], state['group_count']), (5, 10, 1, 20))
        buttons = [side.list.groups[i].button for i in range(20)]
        self.assertEqual(buttons, [0, 1, 2, 3, 4, -1, -1] + list(range(5, 15)) + [-1, -1, 15])
        self.assertEqual(state['group'], 8)                    # button 6 = the second left group
        self.assertEqual(state['server_count'], 5)
        self.assertEqual(state['groups'][6]['text'], b'L1')
        self.assertEqual(state['groups'][6]['colors'][:3], [0xff79ffff, 0xff79ffff, 0xffc1eeff])   # type 2
        self.assertEqual(state['groups'][7]['colors'][:3], [0xffe2e2e2, 0xffe2e2e2, 0xffffffff])
        server_colours = [[0xffe2e2e2, 0xffe2e2e2, 0xffffffff, 0], [0xff79ffff, 0xff79ffff, 0xffc1eeff, 0],
                          [0xff00b4ff, 0xff00b4ff, 0xff27d9ff, 0], [0xff00b4ff, 0xff00b4ff, 0xff27d9ff, 0]]
        for s in range(5):
            self.assertEqual(state['servers'][s]['colors'], server_colours[s % 4])
            self.assertEqual(state['servers'][s]['show'], 1)
        self.assertEqual(state['servers'][5]['show'], 0)
        # gauge width (rect 160) * percent / 100
        for s in range(5):
            corners = state['gauges'][s]['position']
            self.assertAlmostEqual(corners[6] - corners[0], 160*10*s//100)
        self.assertEqual(state['text'][0], b'left group description text')
        self.assertEqual(state['arrows'][0]['show'], 1)           # selection 0..10 uses the left arrow
        self.assertEqual(state['arrows'][1]['show'], 0)

    def test_notice_without_a_selected_group(self):
        servers = {'groups': [{'id': 1, 'type': 0, 'position': 0, 'button': -1, 'name': b'G', 'description': b'd',
                               'servers': []}], 'notice': b'first words of the notice ' * 5}
        side = self.side(servers=servers)
        self.build(side)
        state = self.state(side)
        self.assertEqual(state['selected'], -1)
        self.assertEqual(state['group'], -1)
        rows, _ = cut_text_model(servers['notice'], 2, 0x53)
        self.assertEqual(state['text'], rows)
        self.assertEqual(state['notice']['show'], 1)

    # ---- input: hover, press, click, events -----------------------------------

    def run_frames(self, side, frames):
        events = []
        for x, y, down, up in frames:
            del side.calls[:]
            side.set_input(x, y, down, up)
            self.lib.mu_ui_win_update(ctypes.byref(side.ctx), side.win, 40.0)
            events += [words for name, words in side.calls if name == 'Event']
        return events

    def test_click_selects_a_group_and_connects_to_open_servers(self):
        servers = {'groups': [{'id': 1, 'type': 0, 'position': 0, 'button': -1, 'name': b'G', 'description': b'',
                               'servers': [{'slot': 0, 'percent': 50, 'type': 0, 'name': b'open'},
                                           {'slot': 1, 'percent': 128, 'type': 0, 'name': b'full'}]}],
                   'notice': b''}
        side = self.side(servers=servers)
        x, y = self.build(side)
        state = self.state(side)
        b5 = state['groups'][5]['position']
        cx, cy = int(b5[0]) + 50, 768 - int(b5[1]) + 10
        self.assertEqual(self.run_frames(side, [(cx, cy, 0, 0)]), [])
        self.assertEqual(self.state(side)['groups'][5]['now_frame'], 1)          # over
        self.assertEqual(self.run_frames(side, [(cx, cy, 1, 0)]), [])
        state = self.state(side)
        self.assertEqual(state['groups'][5]['now_frame'], 2)                     # down
        self.assertEqual(state['groups'][5]['text_add_y'], 1.5)
        self.assertEqual(side.held(), 5)
        self.assertEqual(self.run_frames(side, [(cx, cy, 0, 1)]), [(1, 5)])
        state = self.state(side)
        self.assertEqual((state['selected'], state['groups'][5]['check'], state['groups'][5]['now_frame']), (5, 1, 3))
        self.assertEqual(side.held(), -1)
        self.lib.mu_ui_server_win_update_display(ctypes.byref(side.ctx), side.win)     # the list reply
        state = self.state(side)
        s0, s1 = state['servers'][0]['position'], state['servers'][1]['position']
        full = [(int(s1[0]) + 20, 768 - int(s1[1]) + 5, 1, 0), (int(s1[0]) + 20, 768 - int(s1[1]) + 5, 0, 1)]
        self.assertEqual(self.run_frames(side, full), [])                         # load >= 0x80: ignored
        click = [(int(s0[0]) + 20, 768 - int(s0[1]) + 5, 1, 0), (int(s0[0]) + 20, 768 - int(s0[1]) + 5, 0, 1)]
        self.assertEqual(self.run_frames(side, click), [(3, 0), (2, 0)])
        # press on one button and release on another: no click
        moved = [(int(s0[0]) + 20, 768 - int(s0[1]) + 5, 1, 0), (cx, cy, 0, 1)]
        self.assertEqual(self.run_frames(side, moved), [])

    def test_inactive_window_still_updates_buttons_but_ignores_clicks(self):
        servers = {'groups': [{'id': 1, 'type': 0, 'position': 0, 'button': -1, 'name': b'G', 'description': b'',
                               'servers': []}], 'notice': b''}
        side = self.side(servers=servers)
        self.build(side)
        self.lib.mu_ui_win_set_active(side.win, 0)
        b5 = self.state(side)['groups'][5]['position']
        cx, cy = int(b5[0]) + 50, 768 - int(b5[1]) + 10
        self.assertEqual(self.run_frames(side, [(cx, cy, 1, 0), (cx, cy, 0, 1)]), [])
        state = self.state(side)
        self.assertEqual(state['groups'][5]['click'], 1)                         # CButton saw the click
        self.assertEqual(state['selected'], -1)                                  # UpdateWhileActive did not run

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private restored captures')
    def test_private_client_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        command = [sys.executable, str(ROOT/'scripts/validate_ui_widgets.py'), '--text', str(text), '--data', str(data),
                   '--cases', '10']
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'widgets.json'
            subprocess.run(command + ['--output', str(report)], check=True, capture_output=True, timeout=1800)
            result = json.loads(report.read_text())
        self.assertEqual(result['cut_text_cases'], 400)
        self.assertEqual(result['sprites']['cases'], 120)
        self.assertEqual(result['winex']['cases'], 60)
        self.assertEqual(result['server_window']['cases'], 10)
        self.assertGreater(result['server_window']['state_words'], 100000)


if __name__ == '__main__':
    unittest.main()
