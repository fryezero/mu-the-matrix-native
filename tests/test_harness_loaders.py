"""Portable error-contract checks for the VERIFY-HARNESS-002 adapters."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import map_client_window as mapper
import model_hierarchy_common as common


class HierarchyLoaderTests(unittest.TestCase):
    def test_region_loaders_keep_using_their_caller_constants(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.bin'
            path.write_bytes(b'abc')
            digest = common.sha256(b'abc')
            for name in ('TEXT', 'DATA'):
                with self.subTest(region=name), mock.patch.multiple(
                        common, **{f'{name}_BYTES': 3, f'{name}_SHA256': digest}):
                    region = getattr(common, f'load_{name.lower()}')(str(path))
                    self.assertEqual(region.base, getattr(common, f'{name}_BASE'))
                    self.assertEqual(region.data, b'abc')

    def test_size_error_precedes_digest_error_and_keeps_its_message(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.bin'
            path.write_bytes(b'abc')
            with self.assertRaises(common.PinError) as caught:
                common.load_pinned(path, 4, 'invalid digest')
            self.assertEqual(str(caught.exception), f'{path}: expected 4 bytes, found 3')

    def test_digest_error_keeps_both_digests(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.bin'
            path.write_bytes(b'abc')
            expected, found = common.sha256(b'abd'), common.sha256(b'abc')
            with self.assertRaises(common.PinError) as caught:
                common.load_pinned(path, 3, expected)
            self.assertEqual(str(caught.exception),
                             f'{path}: SHA-256 {found} does not match pinned {expected}')

    def test_missing_file_keeps_the_native_exception_and_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'absent.bin'
            with self.assertRaises(FileNotFoundError) as native:
                path.read_bytes()
            with self.assertRaises(FileNotFoundError) as caught:
                common.load_pinned(path, 3, common.sha256(b'abc'))
            self.assertIs(type(caught.exception), type(native.exception))
            self.assertEqual(caught.exception.args, native.exception.args)
            self.assertEqual(caught.exception.filename, native.exception.filename)
            self.assertEqual(str(caught.exception), str(native.exception))


class WindowLoaderTests(unittest.TestCase):
    def run_main(self, source, output):
        with mock.patch.object(sys, 'argv', ['map_client_window.py', '--capture', str(source),
                                           '--output', str(output)]):
            mapper.main()

    def test_mismatch_keeps_argparse_exit_and_message(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'synthetic.bin', Path(folder) / 'map.json'
            source.write_bytes(b'authored input')
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
                self.run_main(source, output)
            self.assertEqual(caught.exception.code, 2)
            self.assertTrue(stderr.getvalue().endswith(
                'map_client_window.py: error: Capture does not match the pinned restored client text\n'))
            self.assertFalse(output.exists())

    def test_missing_file_keeps_the_native_exception_and_no_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'absent.bin', Path(folder) / 'map.json'
            with self.assertRaises(FileNotFoundError) as native:
                source.read_bytes()
            with self.assertRaises(FileNotFoundError) as caught:
                self.run_main(source, output)
            self.assertIs(type(caught.exception), type(native.exception))
            self.assertEqual(str(caught.exception), str(native.exception))
            self.assertEqual(caught.exception.filename, native.exception.filename)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
