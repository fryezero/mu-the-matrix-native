"""Synthetic checks for the MODEL-HIERARCHY-001 tools and slot-flow model.

No game bytes are used.  x86 fixtures are short hand-assembled sequences.
The private pinned-input check runs only with MU_RECOVERY_INTEGRATION=1.
"""
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = load('model_hierarchy_common')
scan = load('model_hierarchy_scan')
verify = load('model_hierarchy_verify')
flow = load('model_hierarchy_flow')


def call(source, target):
    return b'\xe8' + struct.pack('<i', target - source - 5)


class PinnedInputTests(unittest.TestCase):
    def test_wrong_size_and_digest_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'x.bin'
            path.write_bytes(b'abc')
            with self.assertRaises(common.PinError):
                common.load_pinned(path, 4, common.sha256(b'abcd'))
            with self.assertRaises(common.PinError):
                common.load_pinned(path, 3, common.sha256(b'abd'))
            self.assertEqual(common.load_pinned(path, 3, common.sha256(b'abc')), b'abc')

    def test_region_reads_are_bounded(self):
        region = common.Region(0x1000, b'\x90' * 4)
        self.assertEqual(region.read(0x1002, 2), b'\x90\x90')
        for va, size in ((0x0fff, 1), (0x1003, 2), (0x1000, -1)):
            with self.assertRaises(ValueError):
                region.read(va, size)


class DecodeTests(unittest.TestCase):
    def test_decode_reports_exact_end_early_stop_and_overrun(self):
        region = common.Region(0x1000, b'\x55\x8b\xec\xc3')
        instructions, stop = common.decode_range(region, 0x1000, 0x1004)
        self.assertIsNone(stop)
        self.assertEqual([common.text_of(i) for i in instructions], ['push ebp', 'mov ebp, esp', 'ret'])
        with self.assertRaises(ValueError):
            common.decode_range(region, 0x1000, 0x1002)  # lands inside mov ebp, esp
        undecodable = common.Region(0x1000, b'\x90\x0f\x04\x90')
        _, stop = common.decode_range(undecodable, 0x1000, 0x1004)
        self.assertEqual(stop, 0x1001)

    def test_instruction_claims_must_match_exact_text(self):
        region = common.Region(0x1000, b'\x55\x8b\xec\xc3')
        good = verify.check_instructions(region, 0x1000, 0x1004, {0x1003: 'ret'})
        self.assertTrue(good['ok'])
        bad = verify.check_instructions(region, 0x1000, 0x1004, {0x1003: 'ret 4', 0x1002: 'nop'})
        self.assertFalse(bad['ok'])
        self.assertEqual(set(bad['mismatches']), {'0x1003', '0x1002'})
        self.assertIsNone(bad['mismatches']['0x1002']['found'])

    def test_body_claim_checks_count_and_boundary(self):
        region = common.Region(0x1000, b'\x55\x8b\xec\xc3')
        self.assertTrue(verify.check_body(region, 0x1000, 0x1004, 3)['ok'])
        self.assertFalse(verify.check_body(region, 0x1000, 0x1004, 4)['ok'])


class StrideScanTests(unittest.TestCase):
    def test_only_decoded_stride_immediates_are_reported(self):
        code = (b'\x55\x8b\xec'                      # push ebp; mov ebp, esp
                b'\x69\x45\xdc\x8c\x00\x00\x00'      # imul eax, [ebp-0x24], 0x8c
                b'\xb9\x8c\x00\x00\x00'              # mov ecx, 0x8c
                b'\x69\x45\xdc\x8d\x00\x00\x00'      # imul eax, [ebp-0x24], 0x8d (decoy)
                b'\x68\x8c\x00\x00\x00'              # push 0x8c (not a stride use form)
                b'\xc3')
        region = common.Region(0x1000, code)
        sites = scan.stride_sites(region)
        self.assertEqual(sites, {0x1003: 'imul eax, dword ptr [ebp - 0x24], 0x8c',
                                 0x100a: 'mov ecx, 0x8c'})

    def test_function_candidate_requires_boundary_aligned_decode(self):
        code = b'\x55\x8b\xec\x90\x90\x69\x45\xdc\x8c\x00\x00\x00\xc3'
        region = common.Region(0x2000, code)
        self.assertEqual(scan.function_candidate(region, 0x2005), 0x2000)
        # A site in the middle of the imul is not reachable on a boundary.
        self.assertIsNone(scan.function_candidate(region, 0x2007))

    def test_field_accesses_parse_width_base_and_offset(self):
        region = common.Region(0x1000, b'\x0f\xbf\x40\x20\x0f\xbe\x40\x22')
        instructions, _ = common.decode_range(region, 0x1000, 0x1008)
        fields = scan.field_accesses(instructions)
        self.assertEqual([(f['width'], f['base'], f['offset']) for f in fields],
                         [('word', 'eax', '0x20'), ('byte', 'eax', '0x22')])


class CallSiteTests(unittest.TestCase):
    def test_direct_calls_and_pushed_buffer_before_call(self):
        target = 0x1100
        code = b''
        code += b'\x68' + struct.pack('<I', 0x6fce398)    # push buffer
        code += b'\x6a\x00'                               # push 0
        code += call(0x1000 + len(code), target)          # call target
        code += b'\x68' + struct.pack('<I', 0x6fce398)    # push buffer
        code += call(0x1000 + len(code), 0x1200)          # call elsewhere
        code += call(0x1000 + len(code), target)          # bare call target
        code += b'\xc3'
        region = common.Region(0x1000, code.ljust(0x300, b'\xcc'))
        self.assertEqual(verify.direct_call_candidates(region, target), [0x1007, 0x1016])
        self.assertEqual(verify.push_buffer_call_candidates(region, 0x6fce398, target), [0x1000])

    def test_embedded_call_opcode_remains_only_an_unanchored_candidate(self):
        # E8 is inside a MOV immediate, not at a decoded instruction boundary.
        region = common.Region(0x1000, bytes.fromhex('b8e800000000c3'))
        candidates = verify.direct_call_candidates(region, 0x1006)
        instructions, _ = common.decode_range(region, 0x1000, 0x1007)
        self.assertEqual(candidates, [0x1001])
        self.assertNotIn(candidates[0], {i.address for i in instructions})

    def test_push_lookahead_stops_at_control_transfers(self):
        for transfer in (b'\xc3', b'\xeb\x00', b'\x75\x00', b'\xe2\x00',
                         b'\xe3\x00', b'\xcc', b'\xf4', b'\x0f\x0b'):
            with self.subTest(transfer=transfer.hex()):
                prefix = b'\x68'+struct.pack('<I', 0x6fce398)+transfer
                code = prefix+call(0x1000+len(prefix), 0x1100)+b'\xc3'
                region = common.Region(0x1000, code)
                self.assertEqual(verify.push_buffer_call_candidates(region, 0x6fce398, 0x1100), [])

    def test_argument_uses_counts_frame_slots(self):
        code = b'\x03\x45\x08\x03\x45\x08\x8b\x4d\x0c\xc3'   # add eax,[ebp+8] x2; mov ecx,[ebp+0xc]
        region = common.Region(0x1000, code)
        self.assertEqual(verify.argument_uses(region, 0x1000, 0x100a), {'8': 2, '0xc': 1})


class PoseFlowTests(unittest.TestCase):
    def test_well_formed_chain_reads_only_written_slots(self):
        result = flow.summarize([(False, -1), (False, 0), (False, 1)])
        self.assertEqual(result['direct_unwritten_reads'], 0)
        self.assertEqual(result['bones_depending_on_unwritten_slots'], 0)

    def test_dummy_parent_reads_a_slot_the_call_never_writes(self):
        bones = [(False, -1), (True, 12345), (False, 1), (False, 2), (False, 0)]
        records = flow.pose_flow(bones)
        self.assertTrue(records[1]['skipped'])
        self.assertNotIn('parent', records[1])            # dummy parent field is not read
        self.assertEqual(records[2]['parent_slot'], flow.UNWRITTEN)
        self.assertTrue(records[2]['depends_on_slot_not_written_here'])
        self.assertEqual(records[3]['parent_slot'], flow.WRITTEN)
        self.assertTrue(records[3]['depends_on_slot_not_written_here'])  # inherited via bone 2
        self.assertFalse(records[4]['depends_on_slot_not_written_here'])
        summary = flow.summarize(bones)
        self.assertEqual(summary['direct_dummy_parent_reads'], 1)
        self.assertEqual(summary['bones_depending_on_unwritten_slots'], 2)

    def test_forward_and_out_of_range_parents_are_distinguished(self):
        records = flow.pose_flow([(False, 1), (False, -1), (False, 7), (False, -2)])
        self.assertEqual(records[0]['parent_slot'], flow.UNWRITTEN)   # written later in loop
        self.assertEqual(records[2]['parent_slot'], flow.OUTSIDE)
        self.assertEqual(records[3]['parent_slot'], flow.OUTSIDE)

    def test_parent_must_be_int16_only_where_the_client_reads_it(self):
        with self.assertRaises(ValueError):
            flow.pose_flow([(False, 0x8000)])
        self.assertTrue(flow.pose_flow([(True, None)])[0]['skipped'])


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned client captures')
class PrivateInstructionClaims(unittest.TestCase):
    def test_all_documented_instruction_claims(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT / 'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_CLIENT_IMAGE_DATA',
                                   ROOT / 'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        for path in (text, data):
            if not path.exists():
                self.fail(f'requested integration input is missing: {path}')
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'report.json'
            code = verify.main(['--text', str(text), '--data', str(data), '--output', str(report)])
            result = json.loads(report.read_text())
        self.assertEqual(code, 0)
        self.assertEqual(result['report_format'], 'mu-model-hierarchy-checks-v2')
        self.assertIn('unverified', result['call_search_confidence'])
        self.assertIn('direct_call_candidates', result)
        self.assertNotIn('direct_callers', result)


if __name__ == '__main__':
    unittest.main()
