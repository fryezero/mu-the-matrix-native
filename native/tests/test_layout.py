"""LAYOUT-001: negative builds, every-field C projection/accessor checks, JSON consumers."""
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
import unittest

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / 'scripts/gen_layout.py'
sys.path.insert(0, str(ROOT / 'scripts'))
import gen_layout
import layout_manifest

CC = shutil.which('clang') or shutil.which('cc')
CTYPES = {'u8': ctypes.c_uint8, 'i8': ctypes.c_int8, 'u16': ctypes.c_uint16, 'i16': ctypes.c_int16,
          'u32': ctypes.c_uint32, 'i32': ctypes.c_int32, 'u64': ctypes.c_uint64, 'i64': ctypes.c_int64,
          'f32': ctypes.c_float, 'bytes': ctypes.c_uint8}


def run_gen(layout, out):
    return subprocess.run([sys.executable, str(GEN), '--layout', str(layout), '--out', str(out)],
                          capture_output=True, text=True)


class Layout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.layout = self.t / 'native/session/layout'
        shutil.copytree(ROOT / 'native/session/layout', self.layout)
        self.out = self.t / 'gen'

    def tearDown(self):
        self.tmp.cleanup()

    def generate(self):
        r = run_gen(self.layout, self.out)
        self.assertEqual(r.returncode, 0, r.stderr)
        return layout_manifest.load(self.out / 'layout.json')

    def test_deterministic_domain_merge_and_probe_labels(self):
        data = self.generate()
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        self.assertEqual(run_gen(self.layout, self.out).returncode, 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})
        records = {r['name']: r for r in data['records']}
        self.assertTrue({'CHARACTER', 'CharacterAttribute', 'CharacterMachine', 'OBJECT', 'ITEM'} <= records.keys())
        self.assertEqual(records['CharacterAttribute']['evidence'], 'STATIC')
        self.assertEqual(records['CharacterAttribute']['size'], 0x1b50)
        verified = {(r['name'], f['name']) for r in data['records'] for f in r['fields'] if f['evidence'] == 'VERIFIED'}
        self.assertEqual(verified, {('OBJECT', 'live'), ('OBJECT', 'fade_flag_08'),
                         ('CHARACTER', 'scene_level'), ('CHARACTER', 'label_level_14e'),
                         ('CharacterAttribute', 'skill_count'), ('CharacterAttribute', 'skill_ids'),
                         ('CharacterAttribute', 'skill_timers')})
        # A second lane may add a disjoint field to the same record.
        (self.layout / 'second_lane.def').write_text('MU_RECORD(CHARACTER, 0x3670, STATIC)\n'
            'MU_FIELD(CHARACTER, 0x30, 1, u8, REPLICATED, extra, STATIC)\n')
        self.generate()

    @unittest.skipUnless(shutil.which('make'), 'make unavailable')
    def test_overlaps_fail_the_real_build_before_output(self):
        # Same bytes are forbidden even if types, names or zones agree.
        for declaration in ['MU_FIELD(OBJECT, 0, 1, u8, REPLICATED, live, VERIFIED)',
                            'MU_FIELD(OBJECT, 0, 4, u32, MOTION, wrong_type, STATIC)',
                            'MU_FIELD(CharacterAttribute, 0x1e7, 1, u8, VIEW, inside_array, STATIC)']:
            with self.subTest(declaration=declaration):
                (self.layout / 'conflict.def').write_text(declaration + '\n')
                (self.t / 'scripts').mkdir(exist_ok=True)
                shutil.copy(GEN, self.t / 'scripts/gen_layout.py')
                shutil.copy(ROOT / 'native/Makefile', self.t / 'native/Makefile')
                r = subprocess.run(['make', '-C', str(self.t / 'native'), 'layout',
                                    f'PYTHON={sys.executable}'], capture_output=True, text=True)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn('overlap', r.stderr)
                self.assertIn('conflict.def', r.stderr)
                self.assertFalse((self.t / 'native/build/gen/layout.json').exists())
        # A bad new declaration must not corrupt earlier generated outputs.
        (self.layout / 'conflict.def').unlink()
        self.generate()
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        (self.layout / 'conflict.def').write_text('MU_FIELD(OBJECT, 0, 1, u8, MOTION, oops, STATIC)\n')
        self.assertNotEqual(run_gen(self.layout, self.out).returncode, 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})

    def test_invalid_ranges_names_and_evidence_fail(self):
        for decl in ['MU_FIELD(OBJECT, 0x3d8, 1, u8, VIEW, outside, STATIC)',
                     'MU_FIELD(OBJECT, 0x300, 3, u16, VIEW, bad_size, STATIC)',
                     'MU_FIELD(OBJECT, 0x300, 1, u8, VIEW, live, STATIC)',
                     'MU_FIELD(OBJECT, 0x300, 1, u8, BAD, extra, STATIC)',
                     'MU_RECORD(OBJECT, 0x400, STATIC)', 'MU_RECORD(object, 4, STATIC)\n'
                     'MU_FIELD(object, 0, 1, u8, VIEW, test, STATIC)']:
            with self.subTest(decl=decl):
                (self.layout / 'bad.def').write_text(decl + '\n')
                self.assertNotEqual(run_gen(self.layout, self.out).returncode, 0)
                self.assertFalse(self.out.exists())

    @unittest.skipUnless(CC, 'C compiler unavailable')
    def test_projection_round_trip_and_accessors_over_every_bound_field(self):
        data = self.generate()
        code = ['#include "layout_all.h"',
                'int project(size_t i, const uint8_t *p, size_t n, uint8_t *q, size_t cap) '
                '{ return mu_layout_project(MU_LAYOUT_RECORDS[i], p, n, q, cap); }',
                'int restore(size_t i, uint8_t *p, size_t n, const uint8_t *q, size_t cap) '
                '{ return mu_layout_restore(MU_LAYOUT_RECORDS[i], p, n, q, cap); }']
        for ri, r in enumerate(data['records']):
            for fi, f in enumerate(r['fields']):
                ctype = gen_layout.TYPES[f['type']][1]
                code.append(f'{ctype} get_{ri}_{fi}(const uint8_t *p, size_t n, size_t i) '
                            f'{{ return mu_layout_{r["name"]}_{f["name"]}(p,n,i); }}')
        source = self.t / 'roundtrip.c'; source.write_text('\n'.join(code))
        library = self.t / ('roundtrip.dylib' if sys.platform == 'darwin' else 'roundtrip.so')
        subprocess.run([CC, '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-shared',
                        '-fPIC', '-I', str(self.out), str(source), '-o', str(library)], check=True)
        lib = ctypes.CDLL(str(library))
        for name in ['project', 'restore']:
            getattr(lib, name).argtypes = [ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t,
                                           ctypes.c_void_p, ctypes.c_size_t]
        rng = random.Random(6001)
        tested = 0
        for ri, r in enumerate(data['records']):
            # Finite float patterns, but arbitrary integer/sign bits and nonzero unknown gaps.
            raw = bytearray(rng.randbytes(r['size']))
            for f in r['fields']:
                if f['type'] == 'f32':
                    for off in range(f['offset'], f['offset'] + f['size'], 4):
                        struct.pack_into('<f', raw, off, rng.uniform(-100, 100))
            original = ctypes.create_string_buffer(bytes(raw))
            packed = ctypes.create_string_buffer(r['projection_size'])
            restored = ctypes.create_string_buffer(b'\xa5' * r['size'])
            self.assertEqual(lib.project(ri, original, r['size'], packed, r['projection_size']), 1)
            self.assertEqual(lib.project(ri, original, r['size'] - 1, packed, r['projection_size']), 0)
            self.assertEqual(lib.restore(ri, restored, r['size'], packed, r['projection_size'] - 1), 0)
            self.assertEqual(lib.restore(ri, restored, r['size'], packed, r['projection_size']), 1)
            expected = bytearray(b'\xa5' * r['size'])
            for fi, f in enumerate(r['fields']):
                tested += 1
                a, b = f['offset'], f['offset'] + f['size']
                expected[a:b] = raw[a:b]
                self.assertEqual(packed.raw[f['projection_offset']:f['projection_offset']+f['size']], raw[a:b])
                getter = getattr(lib, f'get_{ri}_{fi}')
                getter.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
                getter.restype = CTYPES[f['type']]
                width = layout_manifest.WIDTHS[f['type']]
                fmt = '<' + layout_manifest.FORMATS[f['type']]
                for index in range(f['size'] // width):
                    self.assertEqual(getter(original, r['size'], index), struct.unpack_from(fmt, raw, a + index*width)[0])
                self.assertEqual(getter(original, r['size'], f['size'] // width), 0)
                self.assertEqual(getter(original, a, 0), 0)
            self.assertEqual(restored.raw[:r['size']], expected)
        self.assertGreater(tested, 90)

    @unittest.skipUnless(CC, 'C compiler unavailable')
    def test_lease_adapter_preserves_zones_gaps_and_prefix_bounds(self):
        self.generate()
        subprocess.run([sys.executable, str(ROOT / 'scripts/gen_domains.py'),
                        '--out', str(self.out)], check=True, capture_output=True)
        source = self.t / 'zones.c'
        source.write_text(r'''#include "session_internal.h"
#include <assert.h>
void mu_dom_hero_zones(const mu_session *s, mu_audit_zones *z) { (void)s; (void)z; }
void mu_dom_hero_step(mu_session *s, const mu_sim *sim) { (void)s; (void)sim; }
void mu_dom_characters_zones(const mu_session *s, mu_audit_zones *z) { (void)s; (void)z; }
void mu_dom_characters_step(mu_session *s, const mu_sim *sim) { (void)s; (void)sim; }
int main(void) {
    uint8_t bytes[8] = {0};
    mu_audit_zones zs = {0};
    const mu_layout_field fields[] = {
        {"replicated", "u8", "STATIC", 1, 1, 0, MU_LAYOUT_REPLICATED},
        {"motion", "u8", "STATIC", 3, 1, 1, MU_LAYOUT_MOTION},
        {"view", "u8", "STATIC", 5, 1, 2, MU_LAYOUT_VIEW}
    };
    const mu_layout_record rec = {"test", "STATIC", 8, 3, 0, fields, 3};
    mu_audit_layout(&zs, "test", bytes, 8, &rec);
    assert(zs.count == 7);
    assert(zs.z[1].zone == MU_ZONE_REPLICATED);
    assert(zs.z[3].zone == MU_ZONE_MOTION);
    assert(zs.z[5].zone == MU_ZONE_VIEW);
    unsigned at = 0;
    for (int i = 0; i < zs.count; ++i) {
        assert(zs.z[i].offset == at);
        at += zs.z[i].size;
        if (!(i & 1)) assert(zs.z[i].zone == MU_ZONE_REPLICATED);
    }
    assert(at == 8);
    zs.count = 0;
    mu_audit_layout(&zs, "prefix", bytes, 4, &rec);
    assert(zs.count == 4 && zs.z[3].offset + zs.z[3].size == 4);
    return 0;
}
''')
        exe = self.t / 'zones'
        subprocess.run([CC, '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wconversion',
                        '-I', str(self.out), '-I', str(ROOT / 'native/session'),
                        str(source), str(ROOT / 'native/session/lease.c'), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)

    def test_json_drives_reader_header_and_existing_validator(self):
        data = self.generate()
        import validate_items
        self.assertEqual(validate_items.OBJ_FIELDS, layout_manifest.fields('OBJECT',
                         omit=('fade_flag_08', 'next'), data=data))
        self.assertEqual(validate_items.ITEM_FIELDS, layout_manifest.fields('ITEM', data=data))
        header = layout_manifest.reader_header(data)
        self.assertIn('MU_READER_OBJECT_SIZE 984u', header)
        # Alter JSON, not .def; the reader compiler must use its value.
        layout_manifest.record('SceneWorld', data)['address'] = 123456
        header = layout_manifest.reader_header(data)
        self.assertIn('MU_READER_SceneWorld 123456u', header)
        data['sha256'] = '0' * 64
        corrupt = self.t / 'corrupt.json'; corrupt.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'digest'):
            layout_manifest.load(corrupt)
