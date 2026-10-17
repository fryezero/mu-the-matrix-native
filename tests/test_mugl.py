"""Synthetic export and primitive conversion checks; no game, Wine or GL needed."""
import ctypes
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'mac-play/mugl'
spec = importlib.util.spec_from_file_location('mugl_gen', SOURCE / 'gen.py')
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


class ExportTests(unittest.TestCase):
    def test_every_export_has_exactly_one_implementation(self):
        names = (SOURCE / 'exports.txt').read_text().splitlines()
        self.assertEqual(len(names), 361)  # CrossOver 26.3 i386 export manifest.
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            self.assertEqual(gen.generate(SOURCE / 'exports.txt', out), len(names))
            definitions = (out / 'opengl32.def').read_text().splitlines()[2:]
            self.assertEqual(len(definitions), len(names))
            stubs = (out / 'stubs.S').read_text()
            header = (out / 'names.h').read_text()
            for name, definition in zip(names, definitions):
                target = f'mugl_{name}@{gen.CUSTOM[name]}' if name in gen.CUSTOM else f'stub_{name}'
                self.assertEqual(definition.strip(), f'{name} = {target}')
                self.assertEqual(stubs.count(f'_stub_{name}:\n'), int(name not in gen.CUSTOM))
                self.assertEqual(stubs.count(f'_real_{name}: .long 0\n'), 1)
                self.assertEqual(header.count(f'  "{name}",\n'), 1)
            self.assertEqual(set(re.findall(r'_stub_(\w+):', stubs)), set(names) - gen.CUSTOM.keys())
            first = {p.name: p.read_bytes() for p in out.iterdir()}
            gen.generate(SOURCE / 'exports.txt', out)
            self.assertEqual(first, {p.name: p.read_bytes() for p in out.iterdir()})

    def test_invalid_manifest_is_rejected(self):
        for text in ('glBegin\nglBegin\n', 'bad@name\n', 'glBegin\n'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as td:
                path = Path(td) / 'exports.txt'
                path.write_text(text)
                with self.assertRaises(ValueError):
                    gen.generate(path, Path(td) / 'out')


class TriangleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        lib = Path(cls.temp.name) / 'triangles.so'
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                        str(SOURCE / 'triangles.c'), '-o', str(lib)], check=True)
        cls.lib = ctypes.CDLL(str(lib))
        cls.lib.mugl_triangle_count.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        cls.lib.mugl_triangle_count.restype = ctypes.c_size_t
        cls.lib.mugl_triangle.argtypes = [ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t,
                                         ctypes.POINTER(ctypes.c_size_t)]
        cls.lib.mugl_triangle.restype = ctypes.c_int

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def triangles(self, mode, n):
        count = self.lib.mugl_triangle_count(mode, n)
        result = []
        for t in range(count):
            out = (ctypes.c_size_t * 3)()
            self.assertEqual(self.lib.mugl_triangle(mode, n, t, out), 1)
            result.append(tuple(out))
        sentinel = (ctypes.c_size_t * 3)(99, 99, 99)
        self.assertEqual(self.lib.mugl_triangle(mode, n, count, sentinel), 0)
        self.assertEqual(tuple(sentinel), (99, 99, 99))
        return result

    def test_hand_computed_vertex_and_provoking_order(self):
        expected = {
            5: [(0, 1, 2), (2, 1, 3), (2, 3, 4), (4, 3, 5)],
            6: [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5)],
            7: [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)],
            8: [(0, 1, 3), (0, 3, 2), (2, 3, 5), (2, 5, 4)],
            9: [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5)],
        }
        for mode, triangles in expected.items():
            with self.subTest(mode=mode):
                self.assertEqual(self.triangles(mode, 8 if mode == 7 else 6), triangles)
        # Fans/strips keep each original last provoking vertex. Quad/polygon
        # conversion is allowed only under SMOOTH, so no flat equivalence claim.
        for mode in (5, 6):
            self.assertEqual([t[2] for t in self.triangles(mode, 6)], [2, 3, 4, 5])

    def test_winding_on_synthetic_convex_geometry(self):
        fixtures = {
            5: [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)],
            6: [(0, 0), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)],
            7: [(0, 0), (1, 0), (1, 1), (0, 1)],
            8: [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)],
            9: [(0, 0), (1, 0), (1, 1), (0, 1), (-1, 1)],
        }
        for mode, points in fixtures.items():
            for t in self.triangles(mode, len(points)):
                a, b, c = [points[i] for i in t]
                area = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
                self.assertGreater(area * (-1 if mode in (5, 8) else 1), 0)

    def test_degenerate_and_incomplete_counts(self):
        for mode in (5, 6, 7, 8, 9):
            for n in range(3 if mode in (5, 6, 9) else 4):
                self.assertEqual(self.triangles(mode, n), [])
        self.assertEqual(self.triangles(7, 7), [(0, 1, 2), (0, 2, 3)])
        self.assertEqual(self.triangles(8, 5), [(0, 1, 3), (0, 3, 2)])
        self.assertEqual(self.triangles(100, 100), [])
        # Repeated geometric vertices are retained, including degenerate triangles.
        self.assertEqual(self.triangles(5, 3), [(0, 1, 2)])


if __name__ == '__main__':
    unittest.main()
