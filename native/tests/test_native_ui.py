"""Native 2D interface layer (NATIVE-UI-001) checks.

Portable (synthetic data only):
  * the software GL subset: fill rule (shared edges are drawn once), texture
    filtering, blending and alpha test;
  * `mu-render ui title|login|text` on a synthetic game root (OZT textures,
    Pillow-encoded OZJ textures, the placeholder font): texture counts, frame
    geometry, and SHA-256 regression hashes where no JPEG is involved.
  * `mu-render ui servers` (NATIVE-UI-002) on a synthetic root: the
    server-select window's layout, the selected group's check frame, hover and
    pressed frames, and the click events.
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): the title, login and
server-select renders of the installed interface files load every texture
and draw; the PNGs stay in a temporary directory.
"""
import ctypes
from ctypes import POINTER, c_float, c_int, c_int32, c_size_t, c_uint8, c_uint32, c_void_p
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
TOOL = NATIVE/'build/mu-render'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'

# Raw-framebuffer SHA-256 regression hashes (synthetic inputs, placeholder font).
HASHES = {
    'text-640': '9e4c7c4cf0790303fd5fde8813ca472f8157603e9df2b85cd92ffe5699501860',
    'login-800': 'e323423696e098217d8447e8c075b166d377ae110433afe25ae3968e1a554663',
}

SINK = ctypes.CFUNCTYPE(None, c_void_p, c_int, POINTER(c_uint32), c_int, c_void_p, c_size_t)


def fbits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def ozt(width, height, rgba_rows):
    """OZT wrapper: 4 bytes + an 18-byte TGA header + BGRA rows, bottom row first."""
    header = bytearray(4) + bytearray(18)
    header[4 + 2] = 2
    struct.pack_into('<hh', header, 16, width, height)
    header[20], header[21] = 32, 8
    body = bytearray()
    for row in reversed(rgba_rows):
        for r, g, b, a in row:
            body += bytes([b, g, r, a])
    return bytes(header) + bytes(body)


def solid_ozt(width, height, colour):
    return ozt(width, height, [[colour]*width for _ in range(height)])


def ozj(width, height, colour):
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (width, height), colour).save(buffer, 'JPEG', quality=95)
    return b'\0'*24 + buffer.getvalue()


def read_png(path):
    data = Path(path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos, idat, width, height = 8, b'', 0, 0
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if kind == b'IHDR':
            width, height = struct.unpack('>II', body[:8])
        elif kind == b'IDAT':
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width*4 + 1
    rows = [raw[i*stride + 1:(i + 1)*stride] for i in range(height)]
    return width, height, rows


def pixel(rows, x, y):
    return tuple(rows[y][x*4:x*4 + 4])


def run_tool_lines(*args):
    result = subprocess.run([str(TOOL), 'ui', *[str(a) for a in args]], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'mu-render ui {args} failed: {result.stderr}')
    return [json.loads(line) for line in result.stdout.strip().splitlines()]


def frame_strip(width, height, colours):
    """A vertical strip of button frames, `height` rows each."""
    return ozt(width, height*len(colours), [[colours[y // height]]*width for y in range(height*len(colours))])


def run_tool(*args, env=None):
    result = subprocess.run([str(TOOL), 'ui', *[str(a) for a in args]], capture_output=True, text=True,
                            env=env)
    if result.returncode:
        raise AssertionError(f'mu-render ui {args} failed: {result.stderr}')
    return json.loads(result.stdout.strip().splitlines()[-1])


class Raster:
    """ctypes view of mu_ui_raster through libmuui."""

    def __init__(self, lib, width, height):
        self.lib = lib
        self.buffer = ctypes.create_string_buffer(lib.mu_ui_raster_sizeof())
        assert lib.mu_ui_raster_init(self.buffer, width, height) == 0
        self.width, self.height = width, height

    def call(self, op, words, data=None):
        array = (c_uint32*max(len(words), 1))(*words)
        size = len(data) if data else 0
        payload = ctypes.create_string_buffer(data, size) if data else None
        self.lib.mu_ui_raster_call(self.buffer, op, array, len(words), payload, size)

    def pixels(self):
        out = ctypes.create_string_buffer(self.width*self.height*4)
        self.lib.mu_ui_raster_read_top_down(self.buffer, out)
        return out.raw

    def free(self):
        self.lib.mu_ui_raster_free(self.buffer)


# op numbers from reconstructed/ui/ui2d.h
OP = {name: i + 1 for i, name in enumerate(
    ['MatrixMode', 'PushMatrix', 'PopMatrix', 'LoadIdentity', 'Viewport', 'Begin', 'End', 'Vertex2f', 'TexCoord2f',
     'Color4f', 'Color3f', 'Color4ub', 'BindTexture', 'Enable', 'Disable', 'BlendFunc', 'DepthMask', 'TexImage2D',
     'TexParameteri', 'TexEnvf', 'GenTextures', 'Clear', 'ClearColor', 'Perspective', 'Ortho2D'])}


class NativeUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.lib = ctypes.CDLL(str(NATIVE/f'build/libmuui.{SUFFIX}'))
        cls.lib.mu_ui_raster_sizeof.restype = c_size_t
        cls.lib.mu_ui_raster_init.argtypes = [c_void_p, c_int32, c_int32]
        cls.lib.mu_ui_raster_call.argtypes = [c_void_p, c_int, POINTER(c_uint32), c_int, c_void_p, c_size_t]
        cls.lib.mu_ui_raster_read_top_down.argtypes = [c_void_p, c_void_p]
        cls.lib.mu_ui_raster_free.argtypes = [c_void_p]

    def ortho(self, r):
        r.call(OP['MatrixMode'], [0x1701])
        r.call(OP['LoadIdentity'], [])
        r.call(OP['Ortho2D'], list(struct.unpack('<8I', struct.pack('<4d', 0, r.width, 0, r.height))))
        r.call(OP['MatrixMode'], [0x1700])
        r.call(OP['Disable'], [0x0de1])

    def quad(self, r, x0, y0, x1, y1):
        r.call(OP['Begin'], [6])
        for x, y in ((x0, y1), (x0, y0), (x1, y0), (x1, y1)):
            r.call(OP['Vertex2f'], [fbits(x), fbits(y)])
        r.call(OP['End'], [])

    def test_shared_edges_are_drawn_once(self):
        r = Raster(self.lib, 32, 16)
        self.ortho(r)
        r.call(OP['Enable'], [0x0be2])
        r.call(OP['BlendFunc'], [1, 1])
        r.call(OP['ClearColor'], [0, 0, 0, fbits(1.0)])
        r.call(OP['Clear'], [0x4000])
        r.call(OP['Color4f'], [fbits(0.25), 0, 0, fbits(1.0)])
        for x0, x1 in ((2.0, 10.5), (10.5, 20.0), (20.0, 30.0)):
            self.quad(r, x0, 3.0, x1, 13.0)
        pixels = r.pixels()
        reds = {pixels[(y*32 + x)*4] for y in range(16) for x in range(32)}
        self.assertEqual(reds, {0, 64})                      # no doubled (128) and covered area exact
        covered = sum(1 for y in range(16) for x in range(32) if pixels[(y*32 + x)*4])
        self.assertEqual(covered, 28*10)
        r.free()

    def test_back_faces_are_culled_like_the_client_state(self):
        r = Raster(self.lib, 8, 8)
        self.ortho(r)
        r.call(OP['Color4f'], [fbits(1.0)]*4)
        r.call(OP['Begin'], [6])                                 # clockwise in GL window space
        for x, y in ((1, 1), (1, 7), (7, 7), (7, 1)):
            r.call(OP['Vertex2f'], [fbits(x), fbits(y)])
        r.call(OP['End'], [])
        self.assertEqual(set(r.pixels()[0::4]), {0})
        r.call(OP['Disable'], [0x0b44])
        r.call(OP['Begin'], [6])
        for x, y in ((1, 1), (1, 7), (7, 7), (7, 1)):
            r.call(OP['Vertex2f'], [fbits(x), fbits(y)])
        r.call(OP['End'], [])
        self.assertIn(255, r.pixels()[0::4])
        r.free()

    def test_texture_modulate_nearest_linear_and_alpha_test(self):
        r = Raster(self.lib, 4, 4)
        self.ortho(r)
        texels = bytes([255, 0, 0, 255, 0, 255, 0, 60])           # 2x1: red opaque, green alpha 0.235
        r.call(OP['BindTexture'], [0x0de1, 5])
        r.call(OP['TexImage2D'], [0x0de1, 0, 4, 2, 1, 0, 0x1908, 0x1401, 0], texels)
        r.call(OP['TexParameteri'], [0x0de1, 0x2801, 0x2600])
        r.call(OP['TexParameteri'], [0x0de1, 0x2800, 0x2600])
        r.call(OP['Enable'], [0x0de1])
        r.call(OP['Enable'], [0x0bc0])                            # alpha test GREATER 0.25
        r.call(OP['Color4f'], [fbits(1.0), fbits(0.5), fbits(1.0), fbits(1.0)])
        r.call(OP['Begin'], [6])
        for (x, y), (u, v) in (((0, 4), (0, 0)), ((0, 0), (0, 1)), ((4, 0), (1, 1)), ((4, 4), (1, 0))):
            r.call(OP['TexCoord2f'], [fbits(u), fbits(v)])
            r.call(OP['Vertex2f'], [fbits(x), fbits(y)])
        r.call(OP['End'], [])
        pixels = r.pixels()
        self.assertEqual(tuple(pixels[0:4]), (255, 0, 0, 255))    # left half: red texel
        self.assertEqual(tuple(pixels[12:16]), (0, 0, 0, 255))    # right half: alpha 0.235 fails GREATER 0.25
        r.free()

    def synthetic_root(self, tmp, jpeg=True):
        root = Path(tmp)
        (root/'Data/Interface').mkdir(parents=True)
        (root/'Data/Logo').mkdir(parents=True)
        colours = {'New_lo_back_01': (200, 30, 30), 'New_lo_back_02': (30, 200, 30), 'lo_lo': (250, 250, 250),
                   'lo_back_s5_03': (30, 30, 200), 'lo_back_s5_04': (200, 200, 30)}
        sizes = {'New_lo_back_01': (400, 69), 'New_lo_back_02': (400, 69), 'lo_lo': (4, 15),
                 'lo_back_s5_03': (400, 100), 'lo_back_s5_04': (400, 100)}
        for i in range(1, 7):
            colours[f'lo_back_s5_im0{i}'] = (40*i, 100, 255 - 40*i)
            sizes[f'lo_back_s5_im0{i}'] = (512 if i % 3 else 256, 300)
        if jpeg:
            for name, colour in colours.items():
                (root/f'Data/Interface/{name}.OZJ').write_bytes(ozj(*sizes[name], colour))
        (root/'Data/Interface/MU_TITLE.OZT').write_bytes(solid_ozt(8, 8, (255, 255, 255, 255)))
        (root/'Data/Interface/lo_121518.OZT').write_bytes(solid_ozt(8, 8, (255, 0, 255, 255)))
        (root/'Data/Interface/New_lo_webzen_logo.OZT').write_bytes(solid_ozt(53, 46, (250, 20, 20, 255)))
        (root/'Data/Interface/FontInput.OZT').write_bytes(solid_ozt(256, 32, (0, 0, 0, 0)))
        logo = [[(255, 255, 255, 255) if (x//8 + y//8) % 2 else (0, 0, 255, 255) for x in range(120)]
                for y in range(40)]
        (root/'Data/Logo/MU-logo.OZT').write_bytes(ozt(120, 40, logo))
        (root/'Data/Logo/mu-logo_g.ozt').write_bytes(solid_ozt(120, 40, (255, 255, 0, 255)))   # case-insensitive
        return root

    def test_title_render_on_a_synthetic_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.synthetic_root(tmp)
            out = Path(tmp)/'title.png'
            summary = run_tool('title', '--root', root, '--size', '1024x768', '--progress', '50/100', '--out', out)
            jpeg = summary['textures'] == 14
            self.assertIn(summary['textures'], (14, 3))          # 3 without libjpeg
            self.assertEqual(summary['unsupported'], 0)
            width, height, rows = read_png(out)
            self.assertEqual((width, height), (1024, 768))
            # webzen logo: 53x46 at (16, 8), unscaled
            self.assertEqual(pixel(rows, 40, 30), (250, 20, 20, 255))
            if jpeg:
                top = pixel(rows, 200, 40)                       # New_lo_back_01 letterbox (top)
                self.assertGreater(top[0], 150)
                self.assertLess(top[1], 80)
                # progress bar: 50% of 0x290 from x = 0x48 (800x600 units), y = 0x21c
                bar_y = int((0x21c + 7)*768/600)
                self.assertGreater(pixel(rows, int((0x48 + 0x148 - 10)*1024/800), bar_y)[0], 200)
                self.assertLess(pixel(rows, int((0x48 + 0x148 + 30)*1024/800), bar_y)[0], 230)

    def test_login_overlay_render_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.synthetic_root(tmp, jpeg=False)
            out = Path(tmp)/'login.png'
            summary = run_tool('login', '--root', root, '--size', '800x600', '--font', '@box', '--version', '10405',
                               '--text454', 'left text', '--text455', 'right', '--format456', 'V %s', '--out', out)
            self.assertEqual(summary['textures'], 3)
            width, height, rows = read_png(out)
            # logo 120x40 image in a 128x64 texture: centred, top at y = 600*0.05 (640x480 units) * 600/480
            top = int(600*0.05*600/480) + 2
            self.assertEqual(pixel(rows, 400 - 60 + 4, top), (0, 0, 255, 255))
            # bottom line carries text (white placeholder boxes)
            bottom = [pixel(rows, x, y) for y in range(570, 600) for x in range(800)]
            self.assertIn((255, 255, 255, 255), bottom)
            if HASHES['login-800']:
                self.assertEqual(summary['framebuffer_sha256'], HASHES['login-800'])

    def test_text_render_is_deterministic_with_the_placeholder_font(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = run_tool('text', '--font', '@box', '--size', '640x480', '--out', Path(tmp)/'a.png')
            second = run_tool('text', '--font', '@box', '--size', '640x480')
            self.assertEqual(first['framebuffer_sha256'], second['framebuffer_sha256'])
            self.assertEqual(first['primitives'], 3)
            if HASHES['text-640']:
                self.assertEqual(first['framebuffer_sha256'], HASHES['text-640'])

    # ---- server select (NATIVE-UI-002) -----------------------------------

    GROUP_FRAMES = [(200, 0, 0, 255), (0, 200, 0, 255), (0, 0, 200, 255), (200, 200, 0, 255)]
    SERVER_FRAMES = [(10, 120, 120, 255), (120, 10, 120, 255), (120, 120, 10, 255)]

    def server_root(self, tmp):
        root = self.synthetic_root(tmp, jpeg=False)
        interface = root/'Data/Interface'
        (interface/'cha_bt.OZT').write_bytes(frame_strip(108, 26, self.GROUP_FRAMES))
        (interface/'server_b2_all.OZT').write_bytes(frame_strip(193, 26, self.SERVER_FRAMES))
        (interface/'server_deco_all.OZT').write_bytes(solid_ozt(160, 96, (90, 90, 90, 255)))
        (interface/'server_ex03.OZT').write_bytes(solid_ozt(4, 4, (255, 255, 255, 255)))
        (interface/'server_ex01.OZT').write_bytes(solid_ozt(512, 12, (220, 220, 220, 255)))
        (interface/'server_ex02.OZJ').write_bytes(ozj(6, 4, (128, 128, 128)))
        (interface/'server_b2_loding.OZJ').write_bytes(ozj(160, 4, (0, 255, 0)))
        return root

    @staticmethod
    def server_layout(textures, width=1024, height=768):
        """CServerSelWin geometry: notice box 6 + 6 + 10 lines of the side texture (4 px, absent without
        libjpeg); window 465 x (box + 556) centred; group column from the bottom (SetPosition 0x0107592f)."""
        box = 12 + (40 if textures == 10 else 0)
        win_h = box + 0x22c
        x, y = (width - 0x1d1)//2, (height - win_h)//2
        side_y = win_h + y - (26*11 + box + 10)
        return x, side_y

    def test_server_select_layout_and_selected_group(self):
        """1024x768: window 465x608 centred at (279, 80); group button 5 at (279, 340), servers at x 415."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.server_root(tmp)
            out = Path(tmp)/'servers.png'
            image, summary = run_tool_lines('servers', '--root', root, '--size', '1024x768', '--font', '@box',
                                            '--out', out)
            self.assertIn(image['textures'], (10, 8))          # 8 without libjpeg
            self.assertEqual(image['unsupported'], 0)
            x, side_y = self.server_layout(image['textures'])
            self.assertEqual((summary['groups'], summary['selected'], summary['servers']), (2, 5, 7))
            self.assertEqual(summary['events'], [[1, 5]])       # the click on group button 5
            self.assertEqual(summary['sounds'], 1)
            width, height, rows = read_png(out)
            # the clicked group button shows its check frame (frame 3) without a hover
            self.assertEqual(pixel(rows, x + 5, side_y + 3), self.GROUP_FRAMES[3])
            # the right column's group button (15) is unchecked: frame 0
            right_x = x + 108 + 193 + 0x38
            self.assertEqual(pixel(rows, right_x + 4, side_y + 3), self.GROUP_FRAMES[0])
            # server buttons 0..6 next to the column, 26 px apart, frame 0; none below
            server_x = x + 108 + 0x1c
            for i in range(7):
                self.assertEqual(pixel(rows, server_x + 5, side_y + 2 + 26*i), self.SERVER_FRAMES[0])
            self.assertEqual(pixel(rows, server_x + 5, side_y + 2 + 26*7), (0, 0, 0, 255))
            # unused top buttons are hidden
            self.assertEqual(pixel(rows, x + (465 - 108)//2 + 4, side_y - 60), (0, 0, 0, 255))

    def test_server_select_hover_press_and_click(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.server_root(tmp)
            hover, press = Path(tmp)/'hover.png', Path(tmp)/'press.png'
            image, _ = run_tool_lines('servers', '--root', root, '--size', '1024x768', '--font', '@box')
            x, side_y = self.server_layout(image['textures'])
            sx, s0, s1 = x + 108 + 0x1c + 5, side_y + 5, side_y + 26 + 5
            _, summary = run_tool_lines('servers', '--root', root, '--size', '1024x768', '--font', '@box',
                                        '--frames', f'{sx + 80},{s0},0,0', '--out', hover)
            self.assertEqual(summary['events'], [[1, 5]])
            rows = read_png(hover)[2]
            self.assertEqual(pixel(rows, sx, s0), self.SERVER_FRAMES[1])           # over
            self.assertEqual(pixel(rows, sx, s1), self.SERVER_FRAMES[0])
            run_tool_lines('servers', '--root', root, '--size', '1024x768', '--font', '@box',
                           '--frames', f'{sx + 80},{s1},1,0', '--out', press)
            rows = read_png(press)[2]
            self.assertEqual(pixel(rows, sx, s1), self.SERVER_FRAMES[2])           # down
            _, summary = run_tool_lines('servers', '--root', root, '--size', '1024x768', '--font', '@box',
                                        '--frames', f'{sx + 80},{s1},1,0;{sx + 80},{s1},0,1')
            self.assertEqual(summary['events'], [[1, 5], [3, 0], [2, 1]])          # hide window, connect slot 1
            self.assertEqual(summary['sounds'], 2)
            _, summary = run_tool_lines('servers', '--root', root, '--size', '1024x768', '--font', '@box',
                                        '--frames', f'{sx + 80},{s1},1,0;{sx + 400},{s1},0,1')
            self.assertEqual(summary['events'], [[1, 5]])                          # released elsewhere

    def test_credits_fade_blocks_and_end(self):
        """CCreditWin over a synthetic root: illustrations, black text bars, blocks, the end record."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.synthetic_root(tmp, jpeg=False)
            interface = root/'Data/Interface'
            (interface/'deco.OZT').write_bytes(solid_ozt(189, 103, (255, 0, 0, 255)))
            (interface/'cr_mu_lo.OZT').write_bytes(solid_ozt(290, 41, (0, 255, 255, 255)))
            for n in range(1, 9):
                for k in (1, 2):
                    (interface/f'im{n}_{k}.OZJ').write_bytes(ozj(400, 400, (40*n, 200, 30*k)))
            credits = Path(tmp)/'credits.txt'
            credits.write_text('title First\nname One\nname Two\ntitle Second\nname Three\nend\n')
            out = Path(tmp)/'c.png'
            image, summary = run_tool_lines('credits', '--root', root, '--size', '800x600', '--font', '@box',
                                            '--credits', credits, '--time', '1200', '--out', out)
            self.assertEqual(image['unsupported'], 0)
            self.assertEqual((summary['image'], summary['image_state'], summary['next_record']), (0, 1, 3))
            self.assertEqual(summary['text_states'], [2, 2, 2])     # all bars faded out: the block is shown
            width, height, rows = read_png(out)
            self.assertEqual(pixel(rows, 5, 5), (0, 0, 0, 255))     # the window background is opaque black
            # the logo (800x600 units, scale 1): 290x41 at (0xf1, 0x21c)
            self.assertEqual(pixel(rows, 0xf1 + 10, 0x21c + 10), (0, 255, 255, 255))
            # the title row carries text (placeholder boxes) at y 0x14 (640x480 units) * 600/480, in the
            # title colour 0xffe2e2e2
            title = [pixel(rows, x, y) for y in range(25, 40) for x in range(800)]
            self.assertIn((226, 226, 226, 255), title)
            _, summary = run_tool_lines('credits', '--root', root, '--size', '800x600', '--font', '@box',
                                        '--credits', credits, '--time', '12000')
            self.assertEqual(summary['events'], [[3, 0], [4, 0], [5, 1], [6, 21]])   # hide, request, music

    @unittest.skipUnless(PRIVATE and os.environ.get('MU_GAME_ROOT'), 'private installed interface files')
    def test_private_installed_server_select(self):
        root = os.environ['MU_GAME_ROOT']
        with tempfile.TemporaryDirectory() as tmp:
            image, summary = run_tool_lines('servers', '--root', root, '--size', '1024x768', '--font', '@box',
                                            '--out', Path(tmp)/'s.png')
            self.assertEqual(image['textures'], 10)
            self.assertEqual(image['unsupported'], 0)
            self.assertEqual((summary['groups'], summary['selected'], summary['servers']), (2, 5, 7))
            image, summary = run_tool_lines('credits', '--root', root, '--size', '1024x768', '--font', '@box',
                                            '--time', '3000', '--out', Path(tmp)/'c.png')
            self.assertEqual(image['textures'], 7)                  # 5 interface files + 2 illustrations
            self.assertEqual(image['unsupported'], 0)

    @unittest.skipUnless(PRIVATE and os.environ.get('MU_GAME_ROOT'), 'private installed interface files')
    def test_private_installed_title_and_login(self):
        root = os.environ['MU_GAME_ROOT']
        with tempfile.TemporaryDirectory() as tmp:
            title = run_tool('title', '--root', root, '--size', '1024x768', '--out', Path(tmp)/'t.png')
            self.assertEqual(title['textures'], 14)
            self.assertEqual(title['primitives'], 12)
            self.assertEqual(title['unsupported'], 0)
            login = run_tool('login', '--root', root, '--size', '1024x768', '--font', '@box',
                             '--out', Path(tmp)/'l.png')
            self.assertEqual(login['textures'], 3)
            self.assertEqual(login['primitives'], 5)


if __name__ == '__main__':
    unittest.main()
