"""DATA-ACQ-003: the compiled CLI vs the retained Python oracle, synthetic only.
The optional installed-corpus tool lives beside the converter, not in this suite.
"""
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
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(NATIVE / 'gfx'))
import gfxconvert as oracle
from test_native_gfx import build_root, swf, tag, dds, bgra, pstr, cstr, font3

BINARY = Path(os.environ.get('MU_GFXCONVERT_TEST_BINARY', NATIVE / 'build/gfxconvert/gfxconvert'))
OPTIONS = ['--bridge', '--transparent', '--var', '_root.isClient=true', '--fontconfig', 'English',
           '--font-subset', 'latin']


class ConverterC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if 'MU_GFXCONVERT_TEST_BINARY' not in os.environ:
            subprocess.run(['make', '-C', str(NATIVE / 'gfx'), 'converter'], check=True, capture_output=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'root'
        self.gfx = build_root(self.root)
        self.out = Path(self.tmp.name) / 'converted'

    def run_c(self, *args, ok=True):
        r = subprocess.run([str(BINARY), '--root', str(self.root), '--out', str(self.out), *args],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return r

    def equal(self, stem='Test', options=(), config=None, subset=None, bridge=False, transparent=False, vars=None):
        self.run_c('--movie', stem, *options)
        expected, _ = oracle.convert_movie(self.gfx / f'{stem}.ozg',
            oracle.FontResolver(self.gfx, config, subset), transparent, bridge=bridge, init_vars=vars)
        actual = (self.out / f'{stem}.swf').read_bytes()
        self.assertEqual(actual, expected, f'{stem}: C output differs from oracle')

    def test_default_and_app_options(self):
        self.equal()
        self.equal(options=OPTIONS, config='English', subset=oracle.LATIN_SUBSET, bridge=True,
                   transparent=True, vars={'_root.isClient': True})

    def test_bridge_and_initial_value_types(self):
        values = {'a': False, 'b': -2147483648, 'c': 2147483647, 'd': 'text', 'e': ''}
        opts = ['--bridge']
        for k, v in values.items():
            opts += ['--var', f'{k}={str(v).lower() if isinstance(v, bool) else v}']
        self.equal(options=opts, bridge=True, vars=values)
        self.equal(options=['--var', 'foo=37'], vars={'foo': 37})

    def test_plain_compressed_containers_and_absent_showframe(self):
        for sig in (b'GFX', b'CFX', b'FWS', b'CWS'):
            (self.gfx / 'Bare.ozg').write_bytes(swf([tag(9, b'\x12\x34\x56')], sig=sig))
            self.equal('Bare', ['--bridge', '--transparent'], bridge=True, transparent=True)

    def test_dxt1_dxt3_dxt5_and_bilinear_alpha(self):
        rng = random.Random(3003)
        cases = [(None, 7, 5), (b'DXT1', 8, 8), (b'DXT3', 8, 8), (b'DXT5', 8, 8)]
        for fmt, w, h in cases:
            for iteration in range(4):
                pixels = bytes(rng.randrange(256) for _ in range(w * h * 4)) if not fmt else bytes(
                    rng.randrange(256) for _ in range(((w + 3) // 4) * ((h + 3) // 4) * (8 if fmt == b'DXT1' else 16)))
                (self.gfx / 'Pic.ozd').write_bytes(dds(w, h, fmt, pixels))
                tw, th = [(w, h), (3, 2), (13, 11), (w, 2)][iteration]
                ext = struct.pack('<IHHH', 1, 14, tw, th) + pstr('') + pstr('folder\\Pic.dds')
                (self.gfx / 'Pic.ozg').write_bytes(swf([tag(1009, ext), tag(1, b'')]))
                self.equal('Pic')

    def test_scaled_atlas_rounding_padding_and_resize(self):
        pixels = [(x * 23, y * 31, 200, (x * 47 + y * 13) % 256) for y in range(7) for x in range(9)]
        (self.gfx / 'Atlas.ozd').write_bytes(dds(9, 7, data=bgra(pixels)))
        for tw, th, rect in [(6, 4, (1, 1, 5, 3)), (9, 7, (7, 5, 12, 9)), (18, 14, (1, 1, 5, 5))]:
            ext = struct.pack('<IHHH', 0x90002, 14, tw, th) + pstr('') + pstr('Atlas.dds')
            sub = struct.pack('<6H', 5, 2, *rect)
            (self.gfx / 'Atlas.ozg').write_bytes(swf([tag(1009, ext), tag(1008, sub), tag(1, b'')]))
            self.equal('Atlas')

    def test_compacted_font_chooses_richest_and_preserves_full_font(self):
        for name, codes in [('Alpha', [65, 66]), ('Rich', [65, 66, 67, 0x4e00])]:
            (self.gfx / f'{name}.ozg').write_bytes(swf([tag(75, font3(3, 'Slate Mobile', codes))]))
        (self.gfx / 'Packed.ozg').write_bytes(swf([tag(1005, struct.pack('<H', 7) + b'Slate Mobile\0'), tag(1, b'')]))
        self.equal('Packed', ['--font-subset', 'latin'], subset=oracle.LATIN_SUBSET)

    def test_unresolved_import_and_missing_images_follow_oracle(self):
        imp = cstr('absent.swf') + struct.pack('<HH', 1, 1) + cstr('$Missing')
        ext = struct.pack('<HHHH', 1, 14, 2, 2) + pstr('') + pstr('absent.dds')
        (self.gfx / 'Missing.ozg').write_bytes(swf([tag(57, imp), tag(1001, ext), tag(1008, b'\0' * 12)]))
        self.equal('Missing')

    def test_navimaps_and_report(self):
        nav = self.gfx / 'NaviMap'
        nav.mkdir()
        png = b'\x89PNG\r\n\x1a\nsynthetic'
        (nav / 'Navimap01.OZP').write_bytes(png[:4] + png)
        (nav / 'Navimap02.ozp').write_bytes(png)
        rep = Path(self.tmp.name) / 'report.json'
        self.run_c('--report', str(rep))
        self.assertEqual(json.loads(rep.read_text())['NaviMap']['images'], 2)
        self.assertEqual((self.out / 'NaviMap/navimap01.ozp').read_bytes(), png)
        self.assertEqual((self.out / 'NaviMap/navimap02.ozp').read_bytes(), png)

    def test_malformed_inputs_fail_without_output(self):
        for bad in [b'FWS', b'FWS\x09' + struct.pack('<I', 12) + b'\x08',
                    b'CWS\x09' + struct.pack('<I', 12) + b'bad zlib',
                    swf([b'\xff\xff' + struct.pack('<I', 0xffffffff)])]:
            (self.gfx / 'Bad.ozg').write_bytes(bad)
            self.run_c('--movie', 'Bad', ok=False)
            self.assertFalse((self.out / 'Bad.swf').exists())
        self.run_c('--movie', '../outside', ok=False)
        self.run_c('--movie', 'Test', '--fontconfig', 'absent', ok=False)

    def test_truncated_dds_and_bad_font_offsets_fail(self):
        (self.gfx / 'Test_IE.ozd').write_bytes(dds(8, 8, b'DXT5', b'\0' * 8))
        self.run_c('--movie', 'Test', ok=False)
        font = bytearray(font3(1, 'Arial Unicode MS', [65, 66]))
        struct.pack_into('<I', font, 5 + len('Arial Unicode MS') + 2, 0xffffffff)
        (self.gfx / 'fonts/fonts_all.swf').write_bytes(swf([tag(75, font)]))
        (self.gfx / 'Import.ozg').write_bytes(swf([tag(71, cstr('gfxfontlib.swf') + b'\x01\x00' + struct.pack('<HH', 1, 3) + cstr('$NormalFont'))]))
        self.run_c('--movie', 'Import', *OPTIONS, ok=False)


if __name__ == '__main__':
    unittest.main()
