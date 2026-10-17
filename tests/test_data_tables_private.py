"""Private actual-instruction comparison of the data-table decoders and item attributes.

Runs scripts/validate_data_tables.py only with MU_RECOVERY_INTEGRATION=1 and
MU_GAME_ROOT pointing at the matching installation (read-only). Portable
synthetic checks live in reconstructed/data/test_data_tables.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DataTablesPrivateTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT'),
                         'private pinned client captures and installation')
    def test_loaders_and_codecs_match_client(self):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/data')], check=True, capture_output=True)
        text = os.environ.get('MU_CLIENT_TEXT', str(ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = os.environ.get('MU_IMAGE_DATA', str(ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        feature = os.environ.get('MU_CPU_FEATURES', str(ROOT/'evidence/image-data-run10/math-capture-10/cpu-features.bin'))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_data_tables.py'), '--text', text, '--data', data,
                            '--feature', feature, '--game-root', os.environ['MU_GAME_ROOT'], '--output', str(output)],
                           check=True, capture_output=True)
            report = json.loads(output.read_text())
        summary = report['summary']
        self.assertEqual(summary['matches'], summary['loader_cases'])
        self.assertGreaterEqual(summary['installed_files'], 44)
        self.assertEqual(summary['mutations_rejected_by_client'], summary['mutation_cases'])
        self.assertEqual(report['codec']['failure_count'], 0)
        self.assertGreater(sum(report['codec']['counts'].values()), 10000)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT'),
                         'private pinned client captures and installation')
    def test_item_model_mapping_matches_client(self):
        subprocess.run(['make', '-C', str(ROOT/'native'), 'build/mu-data'], check=True, capture_output=True)
        text = os.environ.get('MU_CLIENT_TEXT', str(ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = os.environ.get('MU_IMAGE_DATA', str(ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        feature = os.environ.get('MU_CPU_FEATURES', str(ROOT/'evidence/image-data-run10/math-capture-10/cpu-features.bin'))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'models.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_item_models.py'), '--text', text, '--data', data,
                            '--feature', feature, '--game-root', os.environ['MU_GAME_ROOT'], '--output', str(output)],
                           check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertEqual(report['mismatch_count'], 0)
        self.assertEqual(report['found'], report['records'])
        self.assertEqual(report['model_loader_calls'], report['records'])
        self.assertEqual(report['getter_queries'], 0x3af6+5)
        self.assertTrue(report['duplicate_code_case']['match'])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT'),
                         'private pinned client captures and installation')
    def test_item_attributes_match_client(self):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/data')], check=True, capture_output=True)
        text = os.environ.get('MU_CLIENT_TEXT', str(ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = os.environ.get('MU_IMAGE_DATA', str(ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        feature = os.environ.get('MU_CPU_FEATURES', str(ROOT/'evidence/image-data-run10/math-capture-10/cpu-features.bin'))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'fields.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_item_fields.py'), '--text', text, '--data', data,
                            '--feature', feature, '--game-root', os.environ['MU_GAME_ROOT'], '--output', str(output)],
                           check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertEqual(report['mismatch_count'], 0)
        self.assertGreater(report['codes'], 4000)
        checks = report['installed_checks']
        self.assertEqual(checks['convert_fields'], 11*report['codes'])
        self.assertEqual(checks['max_durability'], 64*report['codes'])
        self.assertEqual(checks['bans'], 32*report['codes'])
        self.assertGreater(report['all_checks']['max_durability'], checks['max_durability'])


if __name__ == '__main__':
    unittest.main()
