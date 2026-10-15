import unittest
from recover_smd import unwrap_smd, validate_payload

SAMPLE = b'''version 1
nodes
0 "root" -1
end
skeleton
time 0
0 0 0 0 0 0 0
end
triangles
sample.png
0 0 0 0 0 0 1 0 0
0 1 0 0 0 0 1 1 0
0 0 1 0 0 0 1 0 1
end
'''


class SmdTests(unittest.TestCase):
    def test_preserves_payload(self):
        payload, facts = unwrap_smd(SAMPLE[:24]+SAMPLE)
        self.assertEqual(payload, SAMPLE)
        self.assertEqual(facts['triangles'], 1)

    def test_rejects_missing_triangle_vertex(self):
        with self.assertRaises(ValueError):
            validate_payload(SAMPLE.replace(b'0 0 1 0 0 0 1 0 1\n', b''))

    def test_rejects_nonfinite_coordinate(self):
        with self.assertRaises(ValueError):
            validate_payload(SAMPLE.replace(b'0 1 0 0 0 0 1 1 0', b'0 nan 0 0 0 0 1 1 0'))

    def test_rejects_unknown_bone(self):
        with self.assertRaises(ValueError):
            validate_payload(SAMPLE.replace(b'0 1 0 0 0 0 1 1 0', b'9 1 0 0 0 0 1 1 0'))

    def test_rejects_parent_cycle(self):
        with self.assertRaises(ValueError):
            validate_payload(SAMPLE.replace(b'"root" -1', b'"root" 0'))

    def test_rejects_missing_skeleton(self):
        with self.assertRaises(ValueError):
            validate_payload(SAMPLE.replace(b'skeleton\ntime 0\n0 0 0 0 0 0 0\nend\n', b''))

if __name__ == '__main__':
    unittest.main()
