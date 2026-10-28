"""Checks for the reconstructed in-game interface routines (NATIVE-HUD-001).

Portable checks compare the C reconstruction with independent Python
statements of the client rules on synthetic inputs: the item grid, window
anchoring and the slot pass, RenderItem3D's general path, the tooltip HTML
and the formatter cases.  The private check (MU_RECOVERY_INTEGRATION=1)
runs scripts/validate_hud.py, which compares the reconstruction with the
client's own instructions in Unicorn on the pinned restored captures.
"""
import ctypes
from ctypes import c_int, c_int32
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
import validate_hud as vh  # noqa: E402


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def lib():
    return vh.html_lib(vh.slot_lib(vh.grid_lib(vh.library())))


class GridModel:
    """The grid rules restated: linear-index fit test, row-major searches."""

    def __init__(self, cols, rows):
        self.cols, self.rows, self.cells = cols, rows, [0]*(cols*rows)

    def fits_index(self, index, w, h):
        for r in range(h):
            for c in range(w):
                cell = r*self.cols + index + c
                if cell >= self.cols*self.rows or cell < 0 or self.cells[cell]:
                    return False
        return True

    def find_free(self, w, h):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.fits_index(r*self.cols + c, w, h):
                    return c, r
        return None

    def find_free_index(self, w, h):
        for i in range(self.cols*self.rows):
            if self.fits_index(i, w, h) and i % self.cols < self.cols - (w - 1):
                return i
        return -1

    def place(self, col, row, w, h, ident):
        for r in range(h):
            for c in range(w):
                cell = col + (row + r)*self.cols + c
                if 0 <= cell < len(self.cells):
                    self.cells[cell] = ident


class TestGrid(unittest.TestCase):
    def setUp(self):
        self.lib = lib()

    def new_grid(self, cols, rows):
        g = vh.Grid()
        self.lib.mu_grid_construct(ctypes.byref(g))
        self.assertTrue(self.lib.mu_grid_init(ctypes.byref(g), 1, 0, 100, 50, cols, rows, 0))
        return g

    def test_init_extents_and_reinit(self):
        g = self.new_grid(8, 8)
        self.assertEqual((g.pixel_w, g.pixel_h, g.field_3c, g.type, g.flag_49), (8*26, 8*26, -1, 1, 1))
        self.assertFalse(self.lib.mu_grid_init(ctypes.byref(g), 1, 0, 0, 0, 8, 8, 0))

    def test_random_placements_against_model(self):
        rng = random.Random(4)
        for case in range(60):
            cols, rows = rng.choice([(8, 8), (8, 4), (5, 3)])
            g, model, items = self.new_grid(cols, rows), GridModel(cols, rows), []
            for k in range(30):
                w, h = rng.randrange(1, 5), rng.randrange(1, 5)
                col, row = c_int32(), c_int32()
                found = self.lib.mu_grid_find_free(ctypes.byref(g), w, h, ctypes.byref(col), ctypes.byref(row))
                self.assertEqual(bool(found), model.find_free(w, h) is not None)
                self.assertEqual(self.lib.mu_grid_find_free_index(ctypes.byref(g), w, h), model.find_free_index(w, h))
                if not found:
                    continue
                self.assertEqual((col.value, row.value), model.find_free(w, h))
                if (row.value + h - 1)*cols + col.value + w - 1 >= cols*rows:
                    continue
                item = vh.GridItem(k + 1, k, 0, 0, w, h)
                items.append(item)
                self.assertTrue(self.lib.mu_grid_place(ctypes.byref(g), col.value, row.value, ctypes.byref(item)))
                model.place(col.value, row.value, w, h, k + 1)
                self.assertEqual(list(g.cells[:cols*rows]), model.cells, case)
            self.assertEqual(self.lib.mu_grid_count_empty(ctypes.byref(g)), model.cells.count(0))
            for item in items[::2]:
                self.lib.mu_grid_remove(ctypes.byref(g), ctypes.byref(item))
                model.place(item.col, item.row, item.width, item.height, 0)
            self.assertEqual(list(g.cells[:cols*rows]), model.cells)

    def test_wide_item_wraps_into_next_row(self):
        g = self.new_grid(8, 8)
        # a 2-wide item at the last column fits: the client tests only the linear index
        self.assertTrue(self.lib.mu_grid_fits(ctypes.byref(g), 7, 0, 2, 1))
        self.assertEqual(self.lib.mu_grid_find_free_index(ctypes.byref(g), 2, 1), 0)

    def test_pixel_cell_uses_twenty_pixel_divisor(self):
        g = self.new_grid(8, 8)
        col, row = c_int32(), c_int32()
        self.assertTrue(self.lib.mu_grid_pixel_cell(ctypes.byref(g), 100 + 205, 50 + 41, ctypes.byref(col),
                                                    ctypes.byref(row)))
        self.assertEqual((col.value, row.value), (10, 2))        # 205 // 20: a column past the grid
        self.assertFalse(self.lib.mu_grid_pt_in(ctypes.byref(g), 100 + 8*26, 60))

    def test_count_fits_greedy(self):
        g = self.new_grid(4, 2)
        self.assertEqual(self.lib.mu_grid_count_fits(ctypes.byref(g), 2, 2, 100, None), 2)
        self.assertEqual(self.lib.mu_grid_count_fits(ctypes.byref(g), 1, 1, 3, None), 3)


class TestSlots(unittest.TestCase):
    def setUp(self):
        self.lib = lib()

    def test_frame_anchor(self):
        for align, expect in ((0, 100 - (1024 - 1722)/2), (5, 100), (6, 100 - (1024 - 1722)), (9, 0)):
            self.assertEqual(self.lib.mu_frame_x(align, 100.0, 1722), f32(expect))
        for align, expect in ((0, 40 - (768 - 1048)/2), (1, 40), (8, 40 - (768 - 1048))):
            self.assertEqual(self.lib.mu_frame_y(align, 40.0, 1048), f32(expect))

    def test_slot_pass_geometry(self):
        g = vh.Grid()
        self.lib.mu_grid_construct(ctypes.byref(g))
        self.lib.mu_grid_init(ctypes.byref(g), 8, 0, 0, 0, 8, 8, 0)
        item = vh.GridItem(5, 12, 0, 0, 2, 3)
        self.lib.mu_grid_place(ctypes.byref(g), 3, 2, ctypes.byref(item))
        page = vh.SlotPage(ctypes.cast(ctypes.pointer(g), ctypes.c_void_p), 4.0, 6.0, 26.0, 26.0, 1.0, 0.0)
        frame = vh.SlotFrame(1, 6, 718.0, 540.0, 0.75, 1.0, ctypes.pointer(page), 1, 0x1234)
        out = []
        cf = vh.COLORFN(lambda u, r, g_, b, a: out.append(('color', r, g_, b, a)))
        ef = vh.EMITFN(lambda u, c: out.append(('slot', c.contents.x, c.contents.y, c.contents.w, c.contents.h,
                                                 c.contents.type8_seen)))
        rx, ry = f32(640/1722), f32(480/1048)
        self.assertEqual(self.lib.mu_slot_pass(ctypes.byref(frame), 1722, 1048, rx, ry, cf, ef, None), 1)
        fx = f32(718.0 - f32(1024.0 - 1722.0))
        x = f32(f32(fx + f32(f32(3*f32(26.0 + 1.0)) + 4.0)*1.0)*rx)
        y = f32(f32(540.0 + f32(f32(2*26.0) + 6.0))*ry)
        self.assertEqual(out[0], ('color', 1.0, 1.0, 1.0, 0.75))
        self.assertEqual(out[1][1:3], (x, y))
        self.assertEqual(out[1][3:], (f32(f32(2*26.0)*rx), f32(f32(3*26.0)*ry), 1))

    def test_item3d_general_path(self):
        inp = vh.Item3dIn()
        inp.x, inp.y, inp.w, inp.h, inp.code = 100.0, 200.0, 20.0, 40.0, 12
        inp.trs = vh.ItemTRS(0.5, 0.75, (ctypes.c_float*3)(270, -10, 0), 0.003)
        inp.frame_scale, inp.rate_x, inp.rate_y = 1.0, f32(640/1722), f32(480/1048)
        out = vh.Item3dOut()
        self.assertEqual(self.lib.mu_item3d(ctypes.byref(inp), ctypes.byref(out)), 1)
        self.assertEqual(out.model, 12 + 0xae6)
        self.assertEqual(out.position[0], f32(f32(20.0*0.5 + 100.0)/inp.rate_x))
        self.assertEqual(out.position[1], f32(f32(480.0 - f32(40.0*0.75 + 200.0))/inp.rate_y))
        self.assertEqual((out.position[2], list(out.angle)), (-100.0, [270.0, -10.0, 0.0]))
        inp.code, inp.level_word = 0x1c0b, 8 << 3
        self.assertEqual(self.lib.mu_item3d(ctypes.byref(inp), ctypes.byref(out)), 2)    # external jump
        inp.code, inp.kind_b_6a = 12, 1
        self.lib.mu_item3d(ctypes.byref(inp), ctypes.byref(out))
        self.assertEqual(out.position[2], -140.0)


class TestTooltip(unittest.TestCase):
    def setUp(self):
        self.lib = lib()

    def line(self, text, color, bold):
        buf = ctypes.create_string_buffer(4096)
        self.lib.mu_tooltip_html_line(buf, 4096, text, color, bold)
        return buf.value

    def test_html_line(self):
        self.assertEqual(self.line(b'a<b', 2, 0), b"<font color='#FF3319'>a&lt;b</font><br>")
        self.assertEqual(self.line(b'x', 1, 1), b"<font color='#7FB2FF'><b>x</b></font><br>")
        self.assertEqual(self.line(b'x', 99, 0x101), b"<font color='#FFFFFF'><b>x</b></font><br>")
        self.assertEqual(self.line(b'\n', 0, 0), b'')

    def test_tooltip_html_and_stars(self):
        lines = [vh.TooltipLine(b'Name', 3, 1, 0), vh.TooltipLine(b'\n', 0, 0, 0), vh.TooltipLine(b'', 0, 0, 0),
                 vh.TooltipLine(b'<i>raw</i>', 0, 0, 1), vh.TooltipLine(b'q starGrade*2', 0, 0, 0)]
        arr = (vh.TooltipLine*5)(*lines)
        buf = ctypes.create_string_buffer(8192)
        bad = c_int()
        self.lib.mu_tooltip_html(buf, 8192, arr, 5, ctypes.byref(bad))
        on = b"<img src = 'icon_star01' align = 'center' width = '13' height = '13'>"
        off = b"<img src = 'icon_star00' align = 'center' width = '13' height = '13'>"
        self.assertEqual(buf.value, b"<font color='#FFCC19'>Name</font><br><BR><i>raw</i> " + on*2 + off*3 + b' <br>')
        self.assertEqual(bad.value, 0)
        utf = ctypes.create_string_buffer(64)
        self.lib.mu_latin1_to_utf8(utf, 64, b'\xe9')
        self.assertEqual(utf.value, '\xe9'.encode('utf-8'))

    def test_formatter_lacking_marks_previous_line(self):
        self.lib.mu_tooltip_format.restype = c_int
        self.lib.mu_tooltip_format.argtypes = [ctypes.c_char_p, ctypes.c_char_p, c_int32, ctypes.POINTER(vh.TtfItem),
                                               c_int32, ctypes.POINTER(vh.TtfInputs), c_int32,
                                               ctypes.POINTER(c_int32), ctypes.POINTER(c_int32)]
        item = vh.TtfItem(30, 30, 0, 100, 0, 7)
        inp = vh.TtfInputs()
        inp.req_strength, inp.hero_strength = 500, 420
        out = ctypes.create_string_buffer(0x100)
        color = c_int32(0)
        tc = (c_int32*4)(9, 9, 9, 9)
        self.assertEqual(self.lib.mu_tooltip_format(out, b'(need %d str)', 202, ctypes.byref(item), 0,
                                                    ctypes.byref(inp), 2, ctypes.byref(color), tc), 0)
        self.assertEqual((out.value, color.value, list(tc)), (b'(need 80 str)', 2, [9, 2, 9, 9]))
        self.lib.mu_tooltip_format(out, b'Dur [%d/%d]', 4, ctypes.byref(item), 0, ctypes.byref(inp), 1,
                                   ctypes.byref(color), tc)
        self.assertEqual(out.value, b'Dur [30/30]')
        self.assertEqual(self.lib.mu_tooltip_format(out, b'x', 0, ctypes.byref(item), 0, ctypes.byref(inp), 1,
                                                    ctypes.byref(color), tc), -1)

    def test_c_sprintf_model(self):
        self.assertEqual(vh.c_sprintf(b'%d%% [%02d/%s]', [5, 3, b'x'])[0], b'5% [03/x]')


class TestPrivate(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private restored captures')
    def test_private_client_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'hud.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_hud.py'), '--text', str(text), '--data', str(data),
                            '--sections', 'grid,slots,pass,item3d,html,format', '--cases', '8', '--output', str(report)],
                           check=True, capture_output=True, timeout=1800)
            result = json.loads(report.read_text())
        for section in ('grid', 'slots', 'pass', 'item3d', 'html', 'format'):
            self.assertEqual(result[section]['cases'], 8, section)


if __name__ == '__main__':
    unittest.main()
