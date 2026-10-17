"""Checks for the reconstructed 2D interface layer (NATIVE-UI-001).

Portable checks compare the C reconstruction with independent Python
statements of the client rules (binary32 arithmetic in source order) on
synthetic inputs.  The private check (MU_RECOVERY_INTEGRATION=1) runs
scripts/validate_ui.py, which compares the reconstruction with the client's
own instructions in Unicorn on the pinned restored captures and, with
MU_GAME_ROOT, on installed interface textures.
"""
import ctypes
from ctypes import POINTER, c_float, c_int, c_int32, c_size_t, c_uint8, c_uint32, c_void_p
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


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def fval(word):
    return struct.unpack('<f', struct.pack('<I', word))[0]


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        # The ctypes view lives in the validator so both use one definition.
        import importlib.util
        spec = importlib.util.spec_from_file_location('validate_ui', ROOT/'scripts/validate_ui.py')
        cls.v = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(cls.v)
        except ImportError as error:          # unicorn/capstone are optional for portable checks
            raise unittest.SkipTest(f'validator imports unavailable: {error}')
        cls.lib = cls.v.library()

    def authored(self, width=1024, height=768, bitmaps=None, rates=None):
        return self.v.Authored(self.lib, width, height, bitmaps if bitmaps is not None else self.v.base_bitmaps(),
                               rates=rates)

    # ---- RenderBitmap / RenderColor -------------------------------------

    def model_render_bitmap(self, W, H, tex_name, x, y, w, h, u, v, uw, vh, scale, start, alpha):
        if start:
            x, y = f32(f32(f32(float(W))*x)/640.0), f32(f32(f32(float(H))*y)/480.0)
        if scale:
            w, h = f32(f32(f32(float(W))*w)/640.0), f32(f32(f32(float(H))*h)/480.0)
        y = f32(f32(float(H)) - y)
        p = [(x, y), (x, f32(y - h)), (f32(x + w), f32(y - h)), (f32(x + w), y)]
        c = [(u, v), (u, f32(v + vh)), (f32(u + uw), f32(v + vh)), (f32(u + uw), v)]
        out = [('glBindTexture', (0xde1, tex_name)), ('glBegin', (6,))]
        for i in range(4):
            if alpha > 0:
                out.append(('glColor4f', (bits(1.0),)*3 + (bits(alpha),)))
            out.append(('glTexCoord2f', (bits(c[i][0]), bits(c[i][1]))))
            out.append(('glVertex2f', (bits(p[i][0]), bits(p[i][1]))))
            if alpha > 0:
                out.append(('glColor4f', (bits(1.0),)*4))
        out.append(('glEnd', ()))
        return out

    def test_render_bitmap_matches_the_model(self):
        rng = random.Random(3)
        for W, H in ((640, 480), (1024, 768), (1366, 768)):
            for _ in range(40):
                args = [f32(rng.uniform(-100, 900)) for _ in range(4)] + [f32(rng.random()) for _ in range(4)]
                scale, start = rng.randint(0, 1), rng.randint(0, 1)
                alpha = f32(rng.choice([0.0, -1.0, 0.5, rng.random()]))
                a = self.authored(W, H)
                self.lib.mu_ui_render_bitmap(a.sp, 5, *args, scale, start, alpha)
                tex = a.bitmaps[5].texture
                self.assertEqual(a.calls, self.model_render_bitmap(W, H, tex, *args, scale, start, alpha))

    def test_render_bitmap_binds_through_the_cache_and_negative_names(self):
        a = self.authored()
        for index in (5, 5, -9, -9, 5):
            self.lib.mu_ui_bind_texture(a.sp, index)
        self.assertEqual([c for c in a.calls if c[0] == 'glBindTexture'],
                         [('glBindTexture', (0xde1, a.bitmaps[5].texture)), ('glBindTexture', (0xde1, 9)),
                          ('glBindTexture', (0xde1, a.bitmaps[5].texture))])

    def test_render_color_disables_texture_and_colours_by_mode(self):
        a = self.authored(800, 600)
        self.lib.mu_ui_render_color(a.sp, f32(10), f32(20), f32(30), f32(40), f32(0.5), 1)
        names = [c[0] for c in a.calls]
        self.assertEqual(names[:1], ['glDisable'])        # texture (depth mask already on)
        self.assertIn(('glColor4f', (0, 0, 0, bits(0.5))), a.calls)
        self.assertNotIn('glTexCoord2f', names)

    def test_state_wrappers_deduplicate(self):
        a = self.authored()
        self.lib.mu_ui_enable_alpha_test(a.sp, 1)
        first = list(a.calls)
        self.lib.mu_ui_enable_alpha_test(a.sp, 1)
        self.assertEqual(a.calls, first)
        self.assertEqual(first[:2], [('glEnable', (0xbe2,)), ('glBlendFunc', (0x302, 0x303))])
        self.lib.mu_ui_enable_alpha_blend(a.sp)
        self.assertIn(('glBlendFunc', (1, 1)), a.calls)
        self.assertEqual(a.state.blend_mode, 3)

    def test_begin_bitmap_sets_a_pixel_orthographic_projection(self):
        a = self.authored(1280, 1024)
        self.lib.mu_ui_begin_bitmap(a.sp)
        ortho = [c for c in a.calls if c[0] == 'gluOrtho2D'][0][1]
        values = struct.unpack('<4d', struct.pack('<8I', *ortho))
        self.assertEqual(values, (0.0, 1280.0, 0.0, 1024.0))
        self.assertIn(('glViewport', (0, 0, 1280, 1024)), a.calls)
        self.assertEqual(a.calls[-1], ('glDisable', (0xb71,)))

    # ---- sprites, gauge and title scene ----------------------------------

    def test_sprite_corners_follow_create_position_and_size(self):
        a = self.authored(1024, 768)
        sprite = ctypes.create_string_buffer(512)
        self.lib.mu_ui_sprite_init(sprite)
        self.lib.mu_ui_sprite_create(a.sp, sprite, 53, 46, 0x7b85, 0, 0, 0, 0, f32(1.0), f32(1.0))
        self.lib.mu_ui_sprite_set_position(sprite, 16, 8, 3)
        view = self.v.SpriteView.from_buffer(sprite)
        self.assertEqual(list(view.position), [16.0, 760.0, 16.0, 714.0, 69.0, 714.0, 69.0, 760.0])
        self.assertEqual(list(view.texcoord), [f32(0.5/64), f32(0.5/64), f32(0.5/64), f32(45.5/64),
                                               f32(52.5/64), f32(45.5/64), f32(52.5/64), f32(0.5/64)])
        # right/bottom anchoring with a datum
        self.lib.mu_ui_sprite_create(a.sp, sprite, 100, 50, 0x7b85, 4, 6, 1, 3, f32(1.0), f32(1.0))
        self.lib.mu_ui_sprite_set_position(sprite, 200, 100, 3)
        view = self.v.SpriteView.from_buffer(sprite)
        # right anchor: x + width - datum_x; bottom anchor: (768 - y) - height + datum_y
        self.assertEqual(list(view.position), [196.0, 674.0, 196.0, 624.0, 296.0, 624.0, 296.0, 674.0])
        self.lib.mu_ui_sprite_set_size(sprite, 40, 10, 3)
        view = self.v.SpriteView.from_buffer(sprite)
        self.assertEqual(list(view.position), [256.0, 634.0, 256.0, 624.0, 296.0, 624.0, 296.0, 634.0])
        # tiled: the anchored side's texture coordinate moves by width / texture width
        self.assertEqual(view.texcoord[0], f32(f32(99.5/64) - f32(40/64)))
        self.assertEqual(view.texcoord[1], f32(f32(49.5/64) - f32(10/64)))

    def test_title_scene_draws_eleven_sprites_and_the_gauge(self):
        a = self.authored(1024, 768)
        title = ctypes.create_string_buffer(8192)
        self.lib.mu_ui_title_create(a.sp, title, 1024, 768)
        self.lib.mu_ui_title_render(a.sp, title, 25, 100)
        begins = [c for c in a.calls if c[0] == 'glBegin']
        self.assertEqual(len(begins), 12)               # 13 sprites minus #2 (skipped) and #3 (hidden), + gauge
        binds = [c[1][1] for c in a.calls if c[0] == 'glBindTexture']
        textures = {a.bitmaps[i].texture: i for i in a.bitmaps}
        self.assertEqual([textures[b] for b in binds],
                         [0x7b81, 0x7b82, 0x7b85, 0x7b87, 0x7b88, 0x7b89, 0x7b8a, 0x7b8b, 0x7b8c, 0x7b8d, 0x7b8e,
                          0x7b86])
        verts = [tuple(fval(w) for w in c[1]) for c in a.calls if c[0] == 'glVertex2f']
        # webzen logo: 53x46 at (16, 8), scale 1
        self.assertEqual(verts[8:12], [(16.0, 760.0), (16.0, 714.0), (69.0, 714.0), (69.0, 760.0)])
        # top letterbox: 400x69 at (0, 0), scale (1024/800, 768/600)
        sx, sy = f32(1024/800), f32(768/600)
        self.assertEqual(verts[0], (0.0, f32(f32(f32(768.0)/sy)*sy)))
        self.assertEqual(verts[2], (f32(400.0*sx), f32(f32(f32(f32(768.0)/sy) - 69.0)*sy)))
        # gauge: 25% of 0x290 starting at x = 0x48 (800x600 units)
        gauge = verts[-4:]
        self.assertEqual(gauge[0][0], f32(72.0*sx))
        self.assertEqual(gauge[2][0], f32(f32(72.0 + 0x290*25//100)*sx))

    # ---- text ---------------------------------------------------------------

    def run_text(self, string, sort=1, box=(0, 0), pos=(10, 10), window=(800, 600), back=0):
        gdi = self.v.SyntheticGdi()
        rates = (f32(window[0]/640.0), f32(window[1]/480.0))
        bitmaps = self.v.base_bitmaps()
        a = self.authored(*window, bitmaps=bitmaps, rates=rates)
        text = self.v.Text()
        text.gdi.extent = gdi._extent
        text.gdi.text_out = gdi._text_out
        self.lib.mu_ui_text_init(ctypes.byref(text), a.sp)
        dib = (c_uint8*(self.lib.mu_ui_text_dib_stride(text.dib_width)*text.dib_height))()
        text.dib = ctypes.cast(dib, POINTER(c_uint8))
        text.text_color = 0x80c0e0ff
        text.back_color = back
        out = (c_int32*2)()
        self.lib.mu_ui_render_text(a.sp, ctypes.byref(text), pos[0], pos[1], string, box[0], box[1], sort, out)
        return a, text, bytes(bitmaps[0x7532]['_c_buffer']), tuple(out)

    def test_text_is_converted_from_the_dib_by_the_blue_channel(self):
        a, text, font, size = self.run_text(b'AB')
        width, height = self.v.text_extent(b'AB')
        self.assertEqual(size, (int(f32(width/f32(800/640))), int(f32(height/f32(600/480)))))
        for row in range(height):
            for col in range(width):
                pixel = font[(row*256 + col)*4:(row*256 + col)*4 + 4]
                self.assertIn(pixel, (b'\0\0\0\0', struct.pack('<I', 0x80c0e0ff)))
        uploads = [c for c in a.calls if c[0] == 'glTexImage2D']
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0][1][:8], (0xde1, 0, 4, 256, 32, 0, 0x1908, 0x1401))

    def test_wide_text_is_drawn_in_256_pixel_chunks(self):
        string = b'W'*60
        a, text, font, size = self.run_text(string, window=(1024, 768))
        width = self.v.text_extent(string)[0]
        self.assertGreater(width, 256)
        quads = [c for c in a.calls if c[0] == 'glBegin']
        self.assertEqual(len(quads), width//256 + 1)

    def test_centred_text_offsets_and_background(self):
        a, text, font, size = self.run_text(b'Hi', sort=3, box=(100, 0), back=0x40102030)
        self.assertIn(('glColor4ub', (0x30, 0x20, 0x10, 0x40)), a.calls)
        self.assertEqual([c[0] for c in a.calls].count('glBegin'), 2)    # background + text

    def test_font_heights_follow_the_window_width(self):
        table = {640: 12, 799: 12, 800: 13, 1023: 13, 1024: 14, 1279: 14, 1280: 15, 1679: 15, 1680: 16, 2560: 16}
        for width, height in table.items():
            self.assertEqual(self.lib.mu_ui_font_height(width), height)

    # ---- textures ------------------------------------------------------------

    def ozt(self, w, h, pixels, bits_per_pixel=32, image_type=2, origin=0x08):
        header = bytearray(22)
        header[4 + 2] = image_type
        struct.pack_into('<hh', header, 16, w, h)
        header[20] = bits_per_pixel
        header[21] = origin
        return bytes(header) + pixels

    def open_tga(self, data, index=0x7b15):
        a = self.authored(800, 600, bitmaps={})
        bitmap = self.v.Bitmap()
        buf = ctypes.create_string_buffer(data, len(data))
        result = self.lib.mu_ui_open_tga(a.sp, buf, len(data), index, 0x2601, 0x2900, 7, ctypes.byref(bitmap))
        return result, bitmap, a

    def test_tga_rows_are_flipped_and_swizzled_into_a_power_of_two_buffer(self):
        pixels = bytes(range(3*2*4))
        result, bitmap, a = self.open_tga(self.ozt(3, 2, pixels))
        self.assertEqual(result, 1)
        self.assertEqual((bitmap.width, bitmap.height, bitmap.image_width, bitmap.components), (4.0, 2.0, 3, 4))
        buffer = ctypes.string_at(bitmap.buffer, 4*2*4)
        # buffer row 0 is the file's last row, BGRA -> RGBA
        self.assertEqual(buffer[0:4], bytes([14, 13, 12, 15]))
        self.assertEqual(buffer[16:20], bytes([2, 1, 0, 3]))
        self.assertEqual(buffer[12:16], b'\0\0\0\0')
        self.assertEqual([c[0] for c in a.calls], ['glGenTextures', 'glBindTexture', 'glTexImage2D', 'glTexEnvf',
                                                   'glTexParameteri', 'glTexParameteri', 'glTexParameteri',
                                                   'glTexParameteri'])

    def test_tga_header_fields_the_client_ignores_or_refuses(self):
        pixels = bytes(2*2*4)
        base = self.open_tga(self.ozt(2, 2, pixels))[1]
        for variant in (self.ozt(2, 2, pixels, image_type=10), self.ozt(2, 2, pixels, origin=0x28)):
            result, bitmap, _ = self.open_tga(variant)
            self.assertEqual(result, 1)
            self.assertEqual(ctypes.string_at(bitmap.buffer, 16), ctypes.string_at(base.buffer, 16))
        self.assertEqual(self.open_tga(self.ozt(2, 2, bytes(2*2*3), bits_per_pixel=24))[0], 0)
        self.assertEqual(self.open_tga(self.ozt(1025, 1, bytes(1025*4)))[0], 0)
        self.assertEqual(self.open_tga(self.ozt(4, 4, bytes(10)))[0], 0)      # short file: refused here

    def test_texture_sizes(self):
        lib = ctypes.CDLL(str(HERE/('libmu_ui.dylib' if sys.platform == 'darwin' else 'libmu_ui.so')))
        lib.mu_ui_texture_size.argtypes = [c_int32]
        lib.mu_ui_texture_size.restype = c_int32
        self.assertEqual([lib.mu_ui_texture_size(n) for n in (-3, 0, 1, 2, 3, 640, 1024, 1025)],
                         [1, 1, 1, 2, 4, 1024, 1024, 1024])

    def test_jpeg_rows_are_copied_with_the_texture_stride(self):
        lib = ctypes.CDLL(str(HERE/('libmu_ui.dylib' if sys.platform == 'darwin' else 'libmu_ui.so')))
        lib.mu_ui_open_jpeg.argtypes = [c_void_p, c_void_p, c_size_t] + [c_uint32]*4 + [c_void_p]*4
        lib.mu_ui_open_jpeg.restype = c_int

        class Image(ctypes.Structure):
            _fields_ = [('width', c_int32), ('height', c_int32), ('components', c_int32), ('pixels', c_void_p)]
        rows = (c_uint8*(5*3*3))(*range(45))
        seen = {}
        DECODE = ctypes.CFUNCTYPE(c_int, c_void_p, c_void_p, c_size_t, POINTER(Image))

        def decode(user, data, size, image):
            seen['payload'] = ctypes.string_at(data, size)
            image[0].width, image[0].height, image[0].components = 5, 3, 3
            image[0].pixels = ctypes.addressof(rows)
            return 1
        callback = DECODE(decode)
        a = self.authored(800, 600, bitmaps={})
        bitmap = self.v.Bitmap()
        data = b'x'*24 + b'JPEG'
        result = lib.mu_ui_open_jpeg(a.sp, data, len(data), 0x7b89, 0x2601, 0x2900, 9, callback, None, None,
                                     ctypes.byref(bitmap))
        self.assertEqual(result, 1)
        self.assertEqual(seen['payload'], b'JPEG')                      # 24-byte OZJ header skipped
        self.assertEqual((bitmap.width, bitmap.height, bitmap.components), (8.0, 4.0, 3))
        buffer = ctypes.string_at(bitmap.buffer, 8*4*3)
        self.assertEqual(buffer[0:15], bytes(range(15)))
        self.assertEqual(buffer[24:39], bytes(range(15, 30)))
        self.assertEqual(buffer[3*24:], bytes(24))
        self.assertNotIn('glTexEnvf', [c[0] for c in a.calls])

    # ---- login overlay ----------------------------------------------------------

    def test_login_overlay_layout(self):
        gdi = self.v.SyntheticGdi()
        bitmaps = self.v.base_bitmaps()
        bitmaps[0x7b1e] = {'width': 512.0, 'height': 256.0, 'texture': 77, 'image_width': 400, 'image_height': 160}
        bitmaps[0x7b1f] = {'width': 512.0, 'height': 256.0, 'texture': 78}
        a = self.authored(1024, 768, bitmaps=bitmaps, rates=(f32(1024/640), f32(768/480)))
        text = self.v.Text()
        text.gdi.extent = gdi._extent
        text.gdi.text_out = gdi._text_out
        self.lib.mu_ui_text_init(ctypes.byref(text), a.sp)
        dib = (c_uint8*(self.lib.mu_ui_text_dib_stride(text.dib_width)*text.dib_height))()
        text.dib = ctypes.cast(dib, POINTER(c_uint8))
        strings = self.v.LoginText(text454=b'left', text455=b'right', format456=b'V%s')
        strings.version_bytes[:] = [ord(c) + i + 1 for i, c in enumerate('12345')]
        fade = c_float(9.99)
        self.lib.mu_ui_login_overlay(a.sp, ctypes.byref(text), ctypes.byref(fade), 640, ctypes.byref(strings))
        self.assertEqual(fade.value, 10.0)
        extents = [c[1] for c in a.calls if c[0] == 'GetTextExtent']
        self.assertEqual([e[1] for e in extents][-1], 'V12345')
        colours = [c for c in a.calls if c[0] == 'glColor4ub']
        self.assertEqual(colours[0][1], (0xff, 0xff, 0xff, 0x4c))
        # logo centred: x = 1024*0.5*(640/1024) - 400*(640/1024)*0.5 in 640 units -> 312 px
        verts = [tuple(fval(w) for w in c[1]) for c in a.calls if c[0] == 'glVertex2f']
        self.assertEqual(verts[0][0], 312.0)
        self.assertEqual(verts[2][0], 712.0)

    # ---- private: the client's own instructions -----------------------------

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned client captures')
    def test_private_client_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        command = [sys.executable, str(ROOT/'scripts/validate_ui.py'), '--text', str(text), '--data', str(data),
                   '--tga-limit', '40', '--jpeg-large', '1', '--jpeg-small', '25']
        game = os.environ.get('MU_GAME_ROOT')
        if game:
            command += ['--game-root', game]
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'ui.json'
            subprocess.run(command + ['--output', str(report)], check=True, capture_output=True, timeout=1800)
            import json
            result = json.loads(report.read_text())
        self.assertEqual(result['render_bitmap_color_cases'], 48)
        self.assertEqual(result['state_projection_cases'], 192)
        self.assertEqual(result['sprite_cases'], 160)
        self.assertEqual(result['title_scene_cases'], 40)
        self.assertEqual(result['text_cases'], 140)
        self.assertEqual(result['login_overlay_cases'], 48)
        self.assertGreaterEqual(result['tga_cases'], 48)
        if game:
            self.assertEqual(result['tga_installed_files'], 40)
            if 'jpeg_cases' in result:
                self.assertGreaterEqual(result['jpeg_cases'], 26)


if __name__ == '__main__':
    unittest.main()
