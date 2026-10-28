"""DATA-ACQ-002 provenance: the capture list, the coverage annotations and the generated coverage view agree."""
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAPTURES = json.loads((ROOT / 'docs/research/client-world-captures-2.json').read_text())
COVERAGE = json.loads((ROOT / 'docs/research/world-handler-coverage.json').read_text())
spec = importlib.util.spec_from_file_location('world_handler_coverage', ROOT / 'scripts/world_handler_coverage.py')
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


class WorldCaptures2Tests(unittest.TestCase):
    def test_every_capture_has_hashes_and_one_record_version(self):
        self.assertEqual(len(CAPTURES['captures']), 32)
        for capture in CAPTURES['captures']:
            files = capture['files_sha256']
            for suffix in ('-obj.bin', '-glob.bin', '-light.bin', '-time.txt', '.png'):
                self.assertTrue(any(name.endswith(suffix) for name in files), (capture['capture'], suffix))
            for digest in files.values():
                self.assertRegex(digest, r'^[0-9a-f]{64}$')
            self.assertEqual(len(capture['objects']['record_versions_fitting_installed_length']), 1, capture['capture'])

    def test_captured_classes_match_captures(self):
        captured_worlds = {capture['world'] for capture in CAPTURES['captures']}
        for row in COVERAGE['classes']:
            status = row['capture']['status']
            self.assertIn(status, ('captured', 'earlier', 'not_reachable'))
            self.assertEqual(status == 'captured', row['worlds'][0] in captured_worlds, row['class_id'])

    def test_music_read_settles_index_44(self):
        result = CAPTURES['music_read']['result']
        self.assertEqual(result['index_43']['pointer'], result['index_44']['pointer'])
        self.assertEqual((result['index_43']['word_at'], result['index_44']['word_at']), ('0x01cf172c', '0x01cf1730'))
        for digest in CAPTURES['music_read']['reads'].values():
            self.assertRegex(digest, r'^[0-9a-f]{64}$')

    def test_generated_coverage_view_is_current(self):
        rendered = coverage.markdown(COVERAGE)
        self.assertEqual((ROOT / 'docs/research/world-handler-coverage.md').read_text(), rendered)
        self.assertIsNotNone(re.search(r'Original populated captures: 27 classes from DATA-ACQ-002', rendered))


if __name__ == '__main__':
    unittest.main()
