"""Portable HelpWindow provider lifetime, filtering and refusal behavior."""
import ctypes as C
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import test_help as th
import validate_help_controller as vh


def table(rows):
    result = bytearray(th.PAYLOAD)
    for i, (ident, category, auxiliary, key, text) in enumerate(rows):
        struct.pack_into('<iBB', result, i * 136, ident, category, auxiliary)
        result[i * 136 + 6:i * 136 + 6 + len(key)] = key.encode()
        result[i * 136 + 70:i * 136 + 70 + len(text)] = text.encode()
    return bytes(result)


class HelpControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory(prefix='mu-help-controller-test-')
        cls.lib = vh.bind(th.library(th.build_library(cls.work.name)))

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_zero_stop_and_independent_category_bytes(self):
        rows = table([(1, 0, 0, 'A', 'Always'), (2, 13, 2, 'B', 'Classic'),
                      (3, 1, 1, '/test', 'Chat'), (-1, 255, 1, 'X', 'Auxiliary'),
                      (0, 0, 0, '', ''), (1, 0, 0, 'Hidden', 'After sentinel')])
        p = vh.Provider()
        self.assertEqual(self.lib.mu_help_build(C.byref(p), rows), 1)
        self.assertEqual(list(p.counts), [2, 1, 3])
        self.assertEqual(vh.provider_lists(p)[0], [rows[:136], rows[136:272]])

    def test_provider_copies_and_preserves_auxiliary_on_rebuild(self):
        first = table([(1, 0, 1, 'First', 'One')])
        second = table([(2, 1, 2, 'Second', 'Two')])
        p = vh.Provider()
        self.lib.mu_help_provider_init(C.byref(p))
        self.assertEqual(self.lib.mu_help_build(C.byref(p), first), 1)
        self.assertEqual(self.lib.mu_help_build(C.byref(p), second), 1)
        self.assertEqual(list(p.counts), [0, 1, 2])
        self.assertEqual(vh.provider_lists(p)[2], [first[:136], second[:136]])

    def test_mode_filter_and_reload_order(self):
        rows = table([(1, 0, 0, 'Always', 'a'), (2, 13, 0, 'Classic', 'b'),
                      (3, 0, 0, 'Alternate', 'c'), (4, 0, 0, 'Other', 'd'),
                      (99, 1, 0, '/chat', 'e')])
        _, lists, _ = vh.authored(self.lib, rows, 0, 'build')
        for mode, keys in [(0, ['Always', 'Classic']), (1, ['Always', 'Alternate']),
                           (2, ['Always'])]:
            _, _, events = vh.authored(self.lib, rows, mode, 'reload', lists)
            self.assertEqual(events[0], ('ClearDataProvider', []))
            self.assertEqual([args[0] for method, args in events if method == 'SetHotKeyData'], keys)
            self.assertEqual(events[-1], ('SetChatHotKeyData', ['/chat', 'e']))

    def test_base_load_refusal_has_no_side_effects(self):
        rows = table([(1, 0, 0, 'A', 'One')])
        _, initial, _ = vh.authored(self.lib, rows, 0, 'build')
        result, lists, events = vh.authored(self.lib, bytes(th.PAYLOAD), 0, 'load', initial, False)
        self.assertEqual((result, lists, events), (0, initial, []))

    def test_capacity_refusal_is_atomic(self):
        rows = table([(1, 0, 1, 'A', 'One')])
        p = vh.Provider()
        p.counts[2] = 512
        before = bytes(p)
        self.assertEqual(self.lib.mu_help_build(C.byref(p), rows), 0)
        self.assertEqual(bytes(p), before)

    def test_unterminated_fields_refuse_before_invoke(self):
        row = table([(1, 0, 0, 'A', 'One')])
        _, initial, _ = vh.authored(self.lib, row, 0, 'build')
        bad = bytearray(initial[0][0])
        bad[6:70] = b'A' * 64
        initial[0][0] = bytes(bad)
        result, _, events = vh.authored(self.lib, row, 0, 'reload', initial)
        self.assertEqual((result, events), (0, []))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction inputs opt-in')
    def test_original_instructions(self):
        subprocess.run([sys.executable, str(ROOT/'scripts/validate_help_controller.py'),
                        '--cases', '3', '--mutants'], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
