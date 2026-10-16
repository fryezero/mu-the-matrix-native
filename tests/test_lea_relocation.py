"""Hand-assembled fixtures for bounded decoder relocation checks."""
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('lea_decode', ROOT/'scripts/validate_client_lea_decode.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LeaRelocationTests(unittest.TestCase):
    def inspect(self, code):
        # Replace only the expected private-body identity with an authored
        # miniature function. Production input pins remain unchanged.
        bodies = {MODULE.TEXT_BASE: (len(code), hashlib.sha256(code).hexdigest())}
        with mock.patch.dict(MODULE.BODIES, bodies, clear=True):
            return MODULE.check_relocation(code)

    def test_relative_jump_to_instruction_boundary_is_relocatable(self):
        report = self.inspect(bytes.fromhex('eb00c3'))
        self.assertEqual(report[0]['instructions'], 2)
        self.assertEqual(report[0]['absolute_or_segmented_memory_operands'], 0)

    def test_absolute_and_segmented_memory_references_are_refused(self):
        for code in ('a100000000c3', '64a100000000c3', '648b03c3'):
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, 'memory operand'):
                self.inspect(bytes.fromhex(code))

    def test_unbounded_transfers_and_incomplete_decode_are_refused(self):
        for code in ('ebffc3', 'ffe0c3', 'e800000000c3', 'b800', '90'):
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.inspect(bytes.fromhex(code))


if __name__ == '__main__':
    unittest.main()
