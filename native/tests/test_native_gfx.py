"""GFx interface files and the Ruffle route (NATIVE-GFX-001).

Portable (synthetic data authored here, no client bytes):
  * the ModulusCrypt envelope of .ozg/.ozd files decodes with the BMD v14
    reader (independent oracle vectors of model-recovery);
  * DDS decoding (DXT1, DXT3, DXT5, uncompressed RGBA) against hand-built blocks;
  * a synthetic GFx movie (CFX header, ExporterInfo, DefineExternalImage2 atlas
    and plain image, DefineSubImage, ImportAssets2 of gfxfontlib.swf, AS2 with
    ExternalInterface/EventCall/fscommand/class definitions) goes through
    gfx_inventory.py (tag, image, font, AS2 and cross-reference report) and
    gfxconvert.py (standard SWF: no GFx tags, cropped/resampled
    DefineBitsLossless2, inlined renamed font, fontconfig mapping, Latin
    subset, host bridge DoAction);
  * when native/gfx/mugfx is built (needs Rust and the pinned Ruffle), the
    converted movie is rendered by Ruffle and the bridge round trip
    (game -> movie invoke -> ExternalInterface back) is checked.
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): the installed GFx
directory: 179 movies parse (AS2, one exporter version), every .ozd decodes,
and the inventory and main movies convert.
"""
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
sys.path.insert(0, str(NATIVE/'gfx'))

import gfxswf as g  # noqa: E402
import gfxconvert as conv  # noqa: E402
import gfx_inventory as inv  # noqa: E402

PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
SHOT = NATIVE/'gfx/mugfx/target/release/mugfx-shot'
MODULUS = ROOT/'model-recovery'/('libmodulus.dylib' if sys.platform == 'darwin' else 'libmodulus.so')

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


# --------------------------------------------------------------------------- SWF writing helpers

class Bits:
    def __init__(self):
        self.bits = []

    def ub(self, n, v):
        self.bits += [(v >> (n - 1 - i)) & 1 for i in range(n)]

    def sb(self, n, v):
        self.ub(n, v & ((1 << n) - 1))

    def bytes(self):
        b = self.bits + [0] * (-len(self.bits) % 8)
        return bytes(int(''.join(map(str, b[i:i + 8])), 2) for i in range(0, len(b), 8))


def rect(xmin, xmax, ymin, ymax):
    w = Bits()
    n = max(abs(v).bit_length() for v in (xmin, xmax, ymin, ymax)) + 1
    w.ub(5, n)
    for v in (xmin, xmax, ymin, ymax):
        w.sb(n, v)
    return w.bytes()


def matrix_bits(w, scale=None, tx=0, ty=0):
    if scale is None:
        w.ub(1, 0)
    else:
        w.ub(1, 1)
        w.ub(5, 24)
        w.sb(24, int(scale * 65536))
        w.sb(24, int(scale * 65536))
    w.ub(1, 0)
    n = max(abs(tx).bit_length(), abs(ty).bit_length()) + 1
    w.ub(5, n)
    w.sb(n, tx)
    w.sb(n, ty)


def tag(code, payload):
    return g.encode_tag(code, payload, force_long=len(payload) >= 63)


def cstr(s):
    return s.encode() + b'\0'


def pstr(s):
    return bytes([len(s.encode())]) + s.encode()


def shape_with_bitmap(shape_id, bitmap_id, size_px):
    """DefineShape: a size_px square filled with a clipped bitmap (20 twips/px)."""
    tw = size_px * 20
    w = Bits()
    w.ub(8, 1)                      # fill style count (byte-aligned array, written bitwise)
    w.ub(8, 0x41)
    w.ub(16, 0)                     # bitmap id placeholder, patched below (little endian)
    matrix_bits(w, scale=20.0)
    head = w.bytes()
    head = head[:2] + struct.pack('<H', bitmap_id) + head[4:]
    r = Bits()
    r.ub(8, 0)                      # line style count
    r.ub(4, 1)                      # fill bits
    r.ub(4, 0)                      # line bits
    r.ub(1, 0); r.ub(1, 0); r.ub(1, 0); r.ub(1, 1); r.ub(1, 0); r.ub(1, 1)   # style change: fill1 + moveto
    r.ub(5, 2); r.sb(2, 0); r.sb(2, 0)
    r.ub(1, 1)                      # fill style 1 = 1
    for dx, dy in ((tw, 0), (0, tw), (-tw, 0), (0, -tw)):
        n = max(abs(dx).bit_length(), abs(dy).bit_length()) + 1
        r.ub(1, 1); r.ub(1, 1); r.ub(4, n - 2)
        if dx and not dy:
            r.ub(1, 0); r.ub(1, 0); r.sb(n, dx)
        else:
            r.ub(1, 0); r.ub(1, 1); r.sb(n, dy)
    r.ub(6, 0)                      # end
    return struct.pack('<H', shape_id) + rect(0, tw, 0, tw) + head + r.bytes()


def place(char_id, depth, tx=0, ty=0, name=None):
    w = Bits()
    matrix_bits(w, tx=tx, ty=ty)
    flags = 0x06 | (0x20 if name else 0)
    return tag(26, bytes([flags]) + struct.pack('<HH', depth, char_id) + w.bytes() + (cstr(name) if name else b''))


def font3(font_id, name, codes, bold=False):
    """DefineFont3 with one tiny square glyph per code, layout tables and kerning."""
    n = len(codes)
    glyph = Bits()
    glyph.ub(4, 1); glyph.ub(4, 0)
    glyph.ub(1, 0); glyph.ub(1, 0); glyph.ub(1, 0); glyph.ub(1, 1); glyph.ub(1, 0); glyph.ub(1, 1)
    glyph.ub(5, 2); glyph.sb(2, 0); glyph.sb(2, 0); glyph.ub(1, 1)
    for dx, dy in ((400, 0), (0, -400), (-400, 0), (0, 400)):
        glyph.ub(1, 1); glyph.ub(1, 1); glyph.ub(4, 11 - 2)
        if dx:
            glyph.ub(1, 0); glyph.ub(1, 0); glyph.sb(11, dx)
        else:
            glyph.ub(1, 0); glyph.ub(1, 1); glyph.sb(11, dy)
    glyph.ub(6, 0)
    shape = glyph.bytes()
    flags = 0x80 | 0x08 | 0x04 | (1 if bold else 0)
    out = struct.pack('<HBB', font_id, flags, 1) + pstr(name) + struct.pack('<H', n)
    table = 4 * n + 4
    out += b''.join(struct.pack('<I', table + i * len(shape)) for i in range(n))
    out += struct.pack('<I', table + n * len(shape)) + shape * n
    out += b''.join(struct.pack('<H', c) for c in codes)
    out += struct.pack('<hhh', 900, 200, 0)
    out += b''.join(struct.pack('<h', 512 + i) for i in range(n))
    out += rect(0, 400, -400, 0) * n
    kern = [(codes[0], codes[-1], -20), (codes[-1], codes[0], 15)]
    out += struct.pack('<H', len(kern)) + b''.join(struct.pack('<HHh', *k) for k in kern)
    return out


def swf(tags, sig=b'FWS', version=9, size=(200, 100), rate=30):
    body = rect(0, size[0] * 20, 0, size[1] * 20) + struct.pack('<HH', rate << 8, 1) + b''.join(tags) + b'\0\0'
    if sig in (b'CWS', b'CFX'):
        return sig + bytes([version]) + struct.pack('<I', 8 + len(body)) + zlib.compress(body)
    return sig + bytes([version]) + struct.pack('<I', 8 + len(body)) + body


def dds(width, height, fourcc=None, data=b''):
    """DDS header: FourCC (DXT*) or uncompressed 32-bit BGRA masks."""
    pf = struct.pack('<II', 32, 4 if fourcc else 0x41) + (fourcc or b'\0\0\0\0')
    pf += struct.pack('<5I', 0, 0, 0, 0, 0) if fourcc else struct.pack('<5I', 32, 0xff0000, 0xff00, 0xff, 0xff000000)
    head = struct.pack('<7I', 124, 0x1007, height, width, 0, 0, 1) + b'\0' * 44 + pf + struct.pack('<4I', 0x1000, 0, 0, 0)
    head += b'\0' * 4
    assert len(head) == 124
    return b'DDS ' + head + data


def bgra(pixels):
    return b''.join(bytes((b, gg, r, a)) for r, gg, b, a in pixels)


# --------------------------------------------------------------------------- AS2 snippets

def as2_movie_code():
    """ExternalInterface.call("requestSlotInfo", 1); ExternalInterface.call("onClick" + x);
    this.EventCall("onHotKey"); fscommand("TextInput", "a"); _global.gfx.controls.Button = function(){};
    _root.setHPMP = function(info) {}"""
    P = conv._push
    GV, GM, CM, CF, POP, SM, SV = b'\x1c', b'\x4e', b'\x52', b'\x3d', b'\x17', b'\x4f', b'\x1d'
    ei = P('flash') + GV + P('external') + GM + P('ExternalInterface') + GM
    code = P(1, 'requestSlotInfo', 2) + ei + P('call') + CM + POP
    code += P('onClick') + P('x') + GV + b'\x47' + P(1) + ei + P('call') + CM + POP
    code += P('onHotKey', 1, 'this') + GV + P('EventCall') + CM + POP
    code += P('a', 'TextInput', 2, 'fscommand') + CF + POP
    code += P('_global') + GV + P('gfx') + GM + P('controls') + GM + P('Button') + conv._function([], b'') + SM
    code += P('_root') + GV + P('setHPMP') + conv._function(['info'], b'') + SM
    code += P('Common') + GV + P('Global') + GM + P('MUDefines') + GM + P('EXTERNAL_WINDOWPOS', 'requestWindowPos') + SM
    code += P(0, 0) + P(1) + P('Common') + GV + P('Global') + GM + P('MUDefines') + GM + P('EXTERNAL_WINDOWPOS') + GM
    code += P(3) + ei + P('call') + CM + POP
    code += P('_global') + GV + P('gfxExtensions', True) + SM
    return code + b'\0'


def ping_code():
    """_root.ping = function(a) { ExternalInterface.call("pong", a + 1); }"""
    P = conv._push
    ei = P('flash') + b'\x1c' + P('external') + b'\x4e' + P('ExternalInterface') + b'\x4e'
    body = P('a') + b'\x1c' + P(1) + b'\x47' + P('pong', 2) + ei + P('call') + b'\x52' + b'\x17'
    return P('_root') + b'\x1c' + P('ping') + conv._function(['a'], body) + b'\x4f' + b'\0'


def build_root(folder: Path, with_bridge_movie=True) -> Path:
    """A synthetic game root with Data/Interface/GFx."""
    gfx = folder/'Data/Interface/GFx'
    (gfx/'fonts').mkdir(parents=True)
    # Atlas 8x8: four quadrants (red, green, blue, half-transparent white).
    quad = []
    for y in range(8):
        for x in range(8):
            quad.append([(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 255, 0)][(y >= 4) * 2 + (x >= 4)])
    (gfx/'Test_IE.ozd').write_bytes(dds(8, 8, None, bgra(quad)))
    # A plain image stored at 8x8 for a 4x4 target (the exporter stretches to powers of two).
    (gfx/'Test_I1.ozd').write_bytes(dds(8, 8, None, bgra([(10, 200, 30, 255)] * 64)))
    exporter = struct.pack('<HIH', 0x036f, 0, 14) + pstr('') + pstr('Test') + struct.pack('<H', 1) + struct.pack('<I', 99)
    atlas = struct.pack('<IHHH', 0x90000, 14, 8, 8) + pstr('') + pstr('Test_IE.dds') + b'\0'
    plain = struct.pack('<IHHH', 1, 14, 4, 4) + pstr('guege_hp-nopack') + pstr('Test_I1.dds') + b'\0'
    sub = struct.pack('<HHHHHH', 5, 0, 4, 0, 8, 4)          # top-right quadrant (green)
    imp = cstr('gfxfontlib.swf') + struct.pack('<HH', 1, 1) + struct.pack('<H', 9) + cstr('$NormalFont')
    tags = [tag(1000, exporter), tag(69, b'\0\0\0\0'), tag(9, b'\x10\x20\x30'), tag(1009, atlas), tag(1009, plain),
            tag(1008, sub), tag(71, imp), tag(2, shape_with_bitmap(20, 5, 4)), tag(2, shape_with_bitmap(21, 1, 4)),
            place(20, 1, 0, 0), place(21, 2, 200, 0, name='mc'), tag(12, as2_movie_code())]
    if with_bridge_movie:
        tags.append(tag(12, ping_code()))
    tags.append(tag(1, b''))
    (gfx/'Test.ozg').write_bytes(swf(tags, sig=b'CFX', size=(64, 32)))
    # Font library (as the client's gfxfontlib.swf) and the full library behind fontconfig.txt.
    lib = [tag(69, b'\0\0\0\0'), tag(75, font3(1, 'Arial Unicode MS', [0x41, 0x42, 0x43])),
           tag(73, struct.pack('<HB', 1, 0) + b'\0' * 3), tag(56, struct.pack('<HH', 1, 1) + cstr('$NormalFont')),
           tag(1, b'')]
    (gfx/'gfxfontlib.swf').write_bytes(swf(lib, sig=b'CWS'))
    full = [tag(75, font3(1, 'Arial Unicode MS', [0x41, 0x42, 0xe9, 0x4e00, 0xac00])), tag(1, b'')]
    (gfx/'fonts/fonts_all.swf').write_bytes(swf(full, sig=b'CWS'))
    (gfx/'fontconfig.txt').write_text('﻿[FontConfig "English"]\nfontlib "fonts/fonts_all.swf"\n'
                                      'map "$NormalFont" = "Arial Unicode MS" Normal\n', encoding='utf-8')
    return gfx


# --------------------------------------------------------------------------- tests

@unittest.skipUnless(MODULUS.exists(), 'model-recovery/libmodulus not built (make -C model-recovery)')
class Envelope(unittest.TestCase):
    def test_oracle_vectors_decode_through_the_gfx_reader(self):
        vectors = json.loads((ROOT/'model-recovery/fixtures/modulus-v14-vectors.json').read_text())
        checked = 0
        for v in vectors['vectors']:
            if v['kind'] == 'model':
                continue
            cipher = bytes.fromhex(v['envelope_hex'])
            expected = bytes((i * 37 + 11) % 256 for i in range(v['body_bytes']))
            self.assertEqual(g.open_envelope(cipher), expected, v['name'])
            checked += 1
        self.assertGreater(checked, 10)

    def test_short_envelope_rejected(self):
        with self.assertRaises(g.FormatError):
            g.open_envelope(b'\0' * 20)


class Dds(unittest.TestCase):
    def test_dxt1_dxt3_dxt5_and_rgba_blocks(self):
        red = struct.pack('<HHI', 0xf800, 0xf800, 0)
        w, h, px = g.dds_decode_rgba(dds(4, 4, b'DXT1', red))
        self.assertEqual((w, h), (4, 4))
        self.assertEqual(px[:4], bytes((255, 0, 0, 255)))
        # DXT1 3-colour mode: c0 <= c1, index 3 is transparent black.
        tr = struct.pack('<HHI', 0x001f, 0xf800, 0xffffffff)
        self.assertEqual(g.dds_decode_rgba(dds(4, 4, b'DXT1', tr))[2][:4], bytes(4))
        # DXT3: explicit 4-bit alpha (pixel 0 = 0x8 -> 136), blue.
        dxt3 = struct.pack('<Q', 0x8) + struct.pack('<HHI', 0x001f, 0, 0)
        self.assertEqual(g.dds_decode_rgba(dds(4, 4, b'DXT3', dxt3))[2][:8], bytes((0, 0, 255, 136, 0, 0, 255, 0)))
        # DXT5: interpolated alpha, index 2 of (255, 0) = (6*255 + 0)/7 = 218; 8x4 = two blocks.
        a = bytes((255, 0)) + (0b010).to_bytes(6, 'little')
        blk = a + struct.pack('<HHI', 0x07e0, 0, 0)
        w, h, px = g.dds_decode_rgba(dds(8, 4, b'DXT5', blk + blk))
        self.assertEqual((w, h), (8, 4))
        self.assertEqual(px[:4], bytes((0, 255, 0, 218)))
        self.assertEqual(px[4:8], bytes((0, 255, 0, 255)))
        self.assertEqual(px[16:20], bytes((0, 255, 0, 218)))     # first pixel of the second block
        w, h, px = g.dds_decode_rgba(dds(2, 1, None, bgra([(1, 2, 3, 4), (5, 6, 7, 8)])))
        self.assertEqual(px, bytes((1, 2, 3, 4, 5, 6, 7, 8)))
        with self.assertRaises(g.FormatError):
            g.dds_decode_rgba(dds(8, 8, b'DXT5', b'\0' * 16))      # truncated
        with self.assertRaises(g.FormatError):
            g.dds_info(b'NOPE' + b'\0' * 200)


class Synthetic(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.gfx = build_root(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_movie_and_tag_walk(self):
        layer, data = g.read_container(self.gfx/'Test.ozg')
        self.assertEqual(layer, 'plain')
        movie = g.parse_movie(data)
        self.assertEqual((movie.signature, movie.version, movie.width, movie.height), ('CFX', 9, 64.0, 32.0))
        names = [t.name for t in g.movie_tags(movie)]
        for n in ('GFx:ExporterInfo', 'GFx:DefineExternalImage2', 'GFx:DefineSubImage', 'ImportAssets2', 'DoAction'):
            self.assertIn(n, names)
        info = g.parse_exporter_info(next(t for t in g.movie_tags(movie) if t.code == 1000).data)
        self.assertEqual((info['version'], info['bitmap_format'], info['swf_name'], info['code_offsets']),
                         ('0x036f', 'DDS', 'Test', 1))
        with self.assertRaises(g.FormatError):
            g.parse_movie(b'XYZ' + data[3:])
        with self.assertRaises(g.FormatError):
            list(g.iter_tags(struct.pack('<H', (2 << 6) | 10) + b'abc', 0))

    def test_avm1_scanner(self):
        found = g.scan_avm1(as2_movie_code(), g.AvmFindings())
        calls = found.resolved_external_calls()
        self.assertEqual(calls.get('requestSlotInfo'), 1)
        self.assertEqual(calls.get('onClick{?}'), 1)
        self.assertEqual(calls.get('requestWindowPos'), 1)        # through MUDefines.EXTERNAL_WINDOWPOS
        self.assertEqual(found.event_calls, {'onHotKey': 1})
        self.assertEqual(found.fscommands, {'TextInput': 1})
        self.assertIn('gfx.controls.Button', found.classes)
        self.assertIn('setHPMP', found.members)
        self.assertIn('gfxExtensions', found.strings)

    def test_inventory_report(self):
        report = inv.build(self.root)
        agg = inv.aggregate(report)
        self.assertEqual(agg['ozg_movies'], 1)
        self.assertEqual(agg['actionscript'], {'AS2': 1})
        self.assertEqual(agg['exporter'], {'0x036f': 1})
        self.assertEqual((agg['external_images'], agg['atlases'], agg['sub_images']), (2, 1, 1))
        self.assertEqual(agg['imports'], {'gfxfontlib.swf:$NormalFont': 1})
        self.assertEqual(agg['clik_classes'], {'gfx.controls.Button': 1})
        self.assertEqual(agg['hud_xref']['setHPMP'], ['Test'])
        self.assertEqual(agg['hud_xref']['requestSlotInfo'], ['Test'])
        self.assertEqual(agg['gfx_extensions'], {'gfxExtensions': 1})
        movie = next(m for m in report['movies'] if m['file'] == 'Test.ozg')
        atlas = next(i for i in movie['external_images'] if i['atlas'])
        self.assertEqual(atlas['dds'], ['RGBA', 8, 8, 1])
        self.assertEqual(report['ozd']['formats'], {'RGBA/32': 2})
        lib = next(m for m in report['movies'] if m['file'] == 'gfxfontlib.swf')
        self.assertEqual(lib['fonts'][0]['glyphs'], 3)

    @unittest.skipUnless(Image, 'Pillow missing')
    def test_convert_to_standard_swf(self):
        out, rep = conv.convert_movie(self.gfx/'Test.ozg', bridge=True, init_vars={'_root.isClient': True})
        self.assertEqual(out[:3], b'CWS')
        self.assertEqual((rep.images, rep.sub_images, rep.atlases), (1, 1, 1))
        self.assertEqual(rep.fonts_inlined, ['$NormalFont<-gfxfontlib.swf:$NormalFont'])
        movie = g.parse_movie(out)
        tags = list(g.movie_tags(movie))
        codes = {t.code for t in tags}
        self.assertFalse(codes & {1000, 1001, 1008, 1009, 57, 71})
        bitmaps = {struct.unpack_from('<H', t.data)[0]: t.data for t in tags if t.code == 36}
        self.assertEqual(set(bitmaps), {1, 5})
        for cid, (w, h, argb) in ((5, (4, 4, (255, 0, 255, 0))), (1, (4, 4, (255, 10, 200, 30)))):
            fmt, bw, bh = struct.unpack_from('<BHH', bitmaps[cid], 2)
            pixels = zlib.decompress(bitmaps[cid][7:])
            self.assertEqual((fmt, bw, bh), (5, w, h))
            self.assertEqual(tuple(pixels[:4]), argb)
        font = next(t for t in tags if t.code == 75)
        self.assertEqual(g.parse_font(font), {'id': 9, 'name': '$NormalFont', 'glyphs': 3, 'bold': False,
                                              'italic': False, 'layout': True, 'kind': 'DefineFont3'})
        self.assertIn(73, codes)
        # The bridge DoAction sits before the first ShowFrame and registers the three callbacks.
        order = [t.code for t in tags if t.depth == 0]
        bridge = [t for t in tags if t.code == 12][-1]
        self.assertLess(order.index(12), order.index(1))
        found = g.scan_avm1(bridge.data, g.AvmFindings())
        self.assertEqual(set(found.add_callbacks), set(conv.BRIDGE_CALLBACKS))
        self.assertIn('_root.isClient', found.strings)
        # Transparent conversion drops the background colour.
        out2, rep2 = conv.convert_movie(self.gfx/'Test.ozg', drop_background=True)
        self.assertNotIn(9, {t.code for t in g.movie_tags(g.parse_movie(out2))})
        self.assertEqual(rep2.dropped, {'GFx:ExporterInfo': 1, 'SetBackgroundColor': 1})

    @unittest.skipUnless(Image, 'Pillow missing')
    def test_fontconfig_mapping_and_subset(self):
        fonts = conv.FontResolver(self.gfx, 'English', conv.LATIN_SUBSET)
        out, rep = conv.convert_movie(self.gfx/'Test.ozg', fonts)
        self.assertEqual(rep.fonts_inlined, ['$NormalFont<-fonts/fonts_all.swf:Arial Unicode MS'])
        tags = list(g.movie_tags(g.parse_movie(out)))
        font = next(t for t in tags if t.code == 75)
        info = g.parse_font(font)
        self.assertEqual((info['id'], info['name'], info['glyphs']), (9, '$NormalFont', 3))   # A, B, e-acute
        self.assertNotIn(73, {t.code for t in tags})
        # The subset keeps codes, advances and kerning of the kept glyphs.
        full = font3(1, 'X', [0x41, 0x42, 0xe9, 0x4e00, 0xac00])
        sub = conv.subset_font3(full, lambda c: c < 0x100)
        n = struct.unpack_from('<H', sub, 5 + sub[4])[0]
        self.assertEqual(n, 3)
        whole = conv.subset_font3(full, lambda c: True)
        self.assertEqual(g.parse_font(g.Tag(75, whole))['glyphs'], 5)
        self.assertEqual(whole[-14:], full[-14:])                  # kerning table unchanged
        with self.assertRaises(g.FormatError):
            conv.FontResolver(self.gfx, 'Klingon')

    @unittest.skipUnless(Image, 'Pillow missing')
    def test_missing_external_image_is_reported(self):
        (self.gfx/'Test_I1.ozd').unlink()
        _, rep = conv.convert_movie(self.gfx/'Test.ozg')
        self.assertEqual(rep.missing_files, ['Test_I1.dds'])
        self.assertEqual(rep.images, 0)

    @unittest.skipUnless(SHOT.exists() and Image, 'native/gfx/mugfx not built (fetch-ruffle.sh, build-mugfx.sh)')
    def test_ruffle_renders_converted_movie_and_bridge_round_trip(self):
        out, _ = conv.convert_movie(self.gfx/'Test.ozg', drop_background=True, bridge=True)
        swf_path = self.root/'Test.swf'
        swf_path.write_bytes(out)
        png = self.root/'Test.png'
        r = subprocess.run([str(SHOT), str(swf_path), str(png), '--size', '64x32', '--frames', '2',
                            '--invoke', '_level0', 'ping', '[41]'], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('call pong [42.0]', r.stdout)
        self.assertIn('call requestSlotInfo [1.0]', r.stdout)
        im = Image.open(png).convert('RGBA')
        self.assertEqual(im.getpixel((1, 1)), (0, 255, 0, 255))   # sub-image of the atlas (green quadrant)
        self.assertEqual(im.getpixel((11, 1)), (10, 200, 30, 255))  # plain image, resampled to its 4x4 target
        self.assertEqual(im.getpixel((40, 20))[3], 0)               # transparent stage


@unittest.skipUnless(PRIVATE, 'set MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class Installed(unittest.TestCase):
    def test_installed_gfx_directory(self):
        root = Path(os.environ['MU_GAME_ROOT'])
        report = inv.build(root)
        agg = inv.aggregate(report)
        self.assertEqual(agg['ozg_movies'], 179)
        self.assertEqual(agg['errors'], [])
        self.assertEqual(agg['actionscript'], {'AS2': 179})
        self.assertEqual(agg['exporter'], {'0x036f': 179})
        self.assertEqual(report['ozd']['errors'], [])
        self.assertIn('requestSlotInfo', agg['external_calls'])
        self.assertEqual(agg['hud_xref']['setHPMP'], ['main'])

    @unittest.skipUnless(Image, 'Pillow missing')
    def test_inventory_and_main_convert(self):
        gfx = Path(os.environ['MU_GAME_ROOT'])/'Data/Interface/GFx'
        for name in ('main', 'InventoryFrame'):
            out, rep = conv.convert_movie(gfx/f'{name}.ozg', bridge=True)
            self.assertEqual(rep.missing_files, [])
            self.assertGreater(rep.sub_images, 0)
            self.assertFalse({t.code for t in g.movie_tags(g.parse_movie(out))} & {1000, 1008, 1009})


if __name__ == '__main__':
    unittest.main()
