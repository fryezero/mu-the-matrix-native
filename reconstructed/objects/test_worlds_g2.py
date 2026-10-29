"""OpenTexture's lookup order, the preload tables and the event-world predicate (RENDER-WORLDS-G2)."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_worlds_g2 as g2  # noqa: E402


class WorldsG2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/camera')], check=True)
        cls.lib = g2.bind(C.CDLL(str(ROOT / f'reconstructed/objects/libobjects.{g2.SUFFIX}')))
        cls.camera = g2.bind_camera(C.CDLL(str(ROOT / f'reconstructed/camera/libclient_camera.{g2.SUFFIX}')))

    def open(self, sub, name, files, cache):
        case = {'names': [name], 'sub': sub, 'files': files, 'cache': cache, 'count': 1, 'present': True,
                'wrap': 0x2901, 'filter': 0x2600}
        return g2.run_c(self.lib, case)

    def test_lookup_order(self):
        events, index = self.open('Object64\\', 'bons.jpg', {'Data\\Item\\bons.jpg': 7}, {'bons.jpg': (5, 'S')})
        self.assertEqual(events, [('load', 'Data\\Object64\\bons.jpg', 0x2600, 0x2901), ('find', 'bons.jpg'),
                                  ('reuse', 5, 'S', 0x2600, 0x2900)])
        self.assertEqual(index, [5])
        events, index = self.open('Object64\\', 'a.tga', {'Data\\Item\\Texture\\a.tga': 9}, {})
        self.assertEqual([e[1] if len(e) > 1 else e[0] for e in events],
                         ['Data\\Object64\\a.tga', 'a.tga', 'Data\\Item\\a.tga', 'Data\\Item\\Texture\\a.tga'])
        self.assertEqual(events[0][2], 0x2600)   # TGA always GL_NEAREST
        self.assertEqual(index, [9])
        events, index = self.open('Object64\\', 'x.jpg', {}, {})
        self.assertEqual(events[-1], ('error',))
        self.assertEqual(index, [0x7530])
        for name, special in (('skin1.jpg', 0x7725), ('level_2.jpg', 0x7725), ('hide.jpg', 0x791a),
                              ('hair.tga', 0x7776), ('face_1.jpg', 0x791c), ('hqskin3.jpg', 0x7869),
                              ('HQskin2.jpg', 0x7818), ('HQskinA.jpg', 0x77c7), ('HQlevel_1.jpg', 0x77c7),
                              ('HQhair_r.jpg', 0x78ba)):
            events, index = self.open('Object64\\', name, {}, {})
            self.assertEqual((events, index), ([], [special]), name)

    def test_preload_tables(self):
        startup = [g2.c_entry(self.lib.mu_tl_startup(i)) for i in range(self.lib.mu_tl_startup_count())]
        self.assertIn(('Data\\Skill\\', 'Skeleton', 1, 'Skill\\'), startup)
        self.assertEqual(len(set(startup)), len(startup))

        def world(w):
            first = C.POINTER(g2.Preload)()
            n = self.lib.mu_tl_world_preloads(w, C.byref(first))
            return [g2.c_entry(C.pointer(first[i])) for i in range(n)]
        for w in range(116, 121):
            self.assertEqual(world(w)[0], ('Data\\Object2\\', 'DungeonStone', 1, 'Object2\\'))
        self.assertTrue(all(e[0] == 'Data\\Monster\\' for e in world(63)))
        self.assertEqual(world(500), [])

    def test_event_world(self):
        got = [w for w in range(-5, 300) if self.camera.mu_world_camera_event_world(w)]
        self.assertEqual(got, [63] + list(range(0x52, 0x5b)))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-g2-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_g2.py'), '--cases', '1500',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(len(result['families']), 5)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 17)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
