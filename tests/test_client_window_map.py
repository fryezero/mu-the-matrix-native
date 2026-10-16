import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('map_client_window', Path(__file__).resolve().parents[1] / 'scripts/map_client_window.py')
mapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapper)


def call(source, target):
    return b'\xe8' + struct.pack('<i', target - source - 5)


class ClientWindowMapTests(unittest.TestCase):
    def test_calls_distinguish_local_external_and_investigator_seeds(self):
        code = call(0x1000, 0x1010) + call(0x1005, 0x5000) + b'\xc3' + bytes(5) + b'\xc3'
        result = mapper.map_window(code, 0x1000, [0x1000], discover_padding=False)
        entries = {item['entry']: item for item in result['candidates']}
        self.assertEqual(entries['0x1000']['origins'], ['explicit_seed'])
        self.assertEqual(entries['0x1010']['origins'], ['decoded_call_target'])
        self.assertEqual([item['kind'] for item in entries['0x1000']['calls']], ['direct_local', 'direct_outside_window'])

    def test_conditional_loop_terminates_without_claiming_a_new_function(self):
        result = mapper.map_window(b'\x75\xfe\xc3', 0x1000, [0x1000], discover_padding=False)
        function = result['candidates'][0]
        self.assertEqual(function['decoded_instructions'], 2)
        self.assertEqual(function['issues'], [])
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(function['branches'][0]['target'], '0x1000')

    def test_prefixed_unconditional_jump_has_no_fallthrough(self):
        result = mapper.map_window(b'\xf2\xeb\x01\xcc\xc3', 0x1000, [0x1000], discover_padding=False)
        function = result['candidates'][0]
        self.assertEqual(function['decoded_instructions'], 2)
        self.assertEqual(function['issues'], [])
        self.assertEqual(function['branches'][0]['target'], '0x1004')

    def test_indirect_calls_and_window_exits_remain_unresolved(self):
        result = mapper.map_window(b'\xff\xd0\xeb\x7f', 0x1000, [0x1000], discover_padding=False)
        function = result['candidates'][0]
        self.assertEqual(function['calls'][0]['kind'], 'indirect')
        self.assertEqual(function['branches'][0]['kind'], 'direct_outside_window')

    def test_absolute_memory_segment_offsets_and_address_expressions_stay_distinct(self):
        code = b'\xa1' + struct.pack('<I', 0x5000) + b'\x64\xa1' + struct.pack('<I', 0x40)
        code += b'\x8d\x0d' + struct.pack('<I', 0x6000) + b'\xc3'
        result = mapper.map_window(code, 0x1000, [0x1000], discover_padding=False)
        refs = result['candidates'][0]['memory_operands']
        self.assertEqual([item['kind'] for item in refs],
                         ['absolute_memory_operand', 'segmented_offset', 'absolute_address_expression'])
        self.assertEqual(refs[1]['segment'], 'fs')
        self.assertEqual(refs[1]['target'], '0x40')

    def test_loop_edges_and_far_calls_are_not_silently_dropped(self):
        result = mapper.map_window(b'\xe2\xfe\xc3', 0x1000, [0x1000], discover_padding=False)
        self.assertEqual(result['candidates'][0]['branches'][0]['target'], '0x1000')
        far = mapper.map_window(b'\x9a' + bytes(6) + b'\xc3', 0x1000, [0x1000], discover_padding=False)
        self.assertEqual(far['candidates'][0]['calls'][0]['kind'], 'unresolved_operand_form')

    def test_padding_boundaries_are_labeled_as_candidates(self):
        code = b'\xc3' + b'\xcc' * 15 + b'\xc3'
        result = mapper.map_window(code, 0x1000, [0x1000])
        self.assertEqual(result['candidates'][1]['entry'], '0x1010')
        self.assertEqual(result['candidates'][1]['origins'], ['aligned_padding_candidate'])

    def test_instruction_overlap_and_truncation_are_explicit(self):
        result = mapper.map_window(b'\x75\x01\xb8\x00\x00\x00\x00\xc3', 0x1000, [0x1000], discover_padding=False)
        self.assertIn('overlapping_decode_path', [item['kind'] for item in result['candidates'][0]['issues']])
        truncated = mapper.map_window(b'\xe8\x00', 0x1000, [0x1000], discover_padding=False)
        self.assertEqual(truncated['candidates'][0]['issues'][0]['kind'], 'invalid_or_truncated_instruction')

    def test_conflicting_decodes_across_candidate_entries_are_reported(self):
        result = mapper.map_window(b'\xb8\x90\x90\x90\x90\xc3', 0x1000, [0x1000, 0x1001], discover_padding=False)
        conflicts = result['cross_candidate_decode_conflicts']
        self.assertEqual(len(conflicts), 4)
        self.assertEqual(conflicts[0]['first_instruction'], '0x1000')
        self.assertEqual(conflicts[0]['other_instruction'], '0x1001')

    def test_instruction_and_function_budgets_are_explicit(self):
        result = mapper.map_window(b'\x90\x90\xc3', 0x1000, [0x1000], max_instructions=1, discover_padding=False)
        self.assertEqual(result['candidates'][0]['issues'][0]['kind'], 'instruction_budget')
        limited = mapper.map_window(call(0x1000, 0x1006) + b'\xc3\xc3', 0x1000, [0x1000], max_functions=1, discover_padding=False)
        self.assertEqual(limited['unprocessed_entries'], ['0x1006'])

    def test_range_and_seed_validation(self):
        for data, base, seeds in ((b'', 0, [0]), (b'\xc3', -1, [-1]),
                                  (b'\xc3\xc3', 0xffffffff, [0xffffffff]),
                                  (b'\xc3', 0x1000, [0x1001]),
                                  (bytes(mapper.MAX_WINDOW + 1), 0, [0])):
            with self.subTest(base=base), self.assertRaises(ValueError):
                mapper.map_window(data, base, seeds)

    def test_cli_rejects_unpinned_input_without_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'synthetic', Path(directory) / 'map.json'
            source.write_bytes(b'authored non-client input')
            result = subprocess.run([sys.executable, str(Path(mapper.__file__)), '--capture', str(source),
                                     '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('pinned restored client text', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
