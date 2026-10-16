import hashlib
import importlib.util
import os
import struct
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('capture_text', Path(__file__).resolve().parents[1] / 'runtime-linux/capture_text.py')
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class WineCaptureBoundaries(unittest.TestCase):
    def test_fixed_scopes_limit_data_acquisition_and_preserve_text_default(self):
        self.assertEqual(capture.scope_regions('text'), [('client-text.bin', capture.TEXT_START, capture.TEXT_BYTES)])
        regions = capture.scope_regions('math-data')
        self.assertEqual([(address, size) for _, address, size in regions],
                         [(0x1a7dd40, 8), (0x1cf3b00, 64), (0x1cf6618, 4)])
        self.assertEqual(sum(size for _, _, size in regions), 76)
        with self.assertRaises(ValueError):
            capture.scope_regions('arbitrary-process-memory')

    def test_readonly_data_mapping_is_accepted_only_for_data_scope(self):
        maps = '00001000-00002000 r--p 0 00:00 0\n'
        self.assertEqual(capture.image_ranges(maps, 0x1800, 16, require_executable=False),
                         [(0x1800, 0x1810, 'r--p')])
        with self.assertRaises(ValueError):
            capture.image_ranges(maps, 0x1800, 16)
        with self.assertRaises(ValueError):
            capture.image_ranges('00001000-00002000 ---p 0 00:00 0\n', 0x1800, 16, require_executable=False)

    def test_image_data_scope_is_exact_declared_second_section_without_page_padding(self):
        self.assertEqual(capture.scope_regions('image-data'),
                         [('client-image-data.bin', 0x01a7c000, 2557764)])
        start, size = capture.scope_regions('image-data')[0][1:]
        self.assertEqual(start+size, 0x01cec744)
        self.assertLess(start+size, 0x01ced000)

    def test_model_dispatch_scope_selects_only_the_two_observed_jump_slots(self):
        regions = capture.scope_regions('model-dispatch')
        self.assertEqual(regions, [('model-key-target.bin', 0x01d04e14, 4),
                                   ('model-decode-target.bin', 0x01d04df4, 4)])
        self.assertEqual(sum(size for _, _, size in regions), 8)

    def test_trig_state_scope_reads_only_the_selected_dispatch_flag(self):
        self.assertEqual(capture.scope_regions('trig-state'),
                         [('math-dispatch-flag.bin', 0x0bdd1cc8, 4)])

    def test_hash_reads_selected_ranges_without_gaps_and_rejects_short_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic-memory'
            path.write_bytes(bytes(range(32)))
            with path.open('rb') as memory:
                digest = capture.hash_ranges(memory.fileno(), [(0, 8, 'r--p'), (16, 24, 'r--p')])
                self.assertEqual(digest, hashlib.sha256(bytes(range(8)) + bytes(range(16, 24))).hexdigest())
                with self.assertRaisesRegex(OSError, 'Short'):
                    capture.hash_ranges(memory.fileno(), [(24, 40, 'r--p')])
                with self.assertRaisesRegex(ValueError, 'restored section'):
                    capture.require_restored_text(memory.fileno(), [(0, 32, 'r--p')])

    def test_header_mapping_requires_the_exact_file_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'selected').mkdir()
            (root / 'other').mkdir()
            target = root / 'selected/main.exe'
            other = root / 'other/main.exe'
            target.write_bytes(b'synthetic selected image')
            other.write_bytes(b'synthetic different image')
            selected_stat = target.stat()
            for image, accepted in ((target, True), (other, False)):
                stat = image.stat()
                maps = (f'00400000-00401000 r--p 00000000 '
                        f'{os.major(stat.st_dev):x}:{os.minor(stat.st_dev):x} {stat.st_ino} {image}\n')
                if accepted:
                    self.assertEqual(capture.mapped_image_identity(maps, selected_stat),
                                     (os.major(stat.st_dev), os.minor(stat.st_dev), stat.st_ino))
                else:
                    with self.assertRaisesRegex(ValueError, 'pinned target file'):
                        capture.mapped_image_identity(maps, selected_stat)

    def test_header_mapping_rejects_wrong_offset_or_missing_header(self):
        with tempfile.NamedTemporaryFile() as image:
            stat = os.fstat(image.fileno())
            identity = f'{os.major(stat.st_dev):x}:{os.minor(stat.st_dev):x} {stat.st_ino}'
            for maps in (f'00400000-00401000 r--p 00001000 {identity}\n',
                         f'00400000-00400800 r--p 00000000 {identity}\n',
                         f'00401000-00402000 r-xp 00000000 {identity}\n'):
                with self.subTest(maps=maps), self.assertRaises(ValueError):
                    capture.mapped_image_identity(maps, stat)

    def test_header_requires_the_pinned_pe32_image_layout(self):
        header = bytearray(4096)
        header[:2] = b'MZ'
        struct.pack_into('<I', header, 60, 128)
        header[128:132] = b'PE\0\0'
        struct.pack_into('<H', header, 132, 0x14c)
        struct.pack_into('<H', header, 152, 0x10b)
        struct.pack_into('<I', header, 180, capture.IMAGE_BASE)
        struct.pack_into('<I', header, 208, capture.IMAGE_BYTES)
        capture.check_image_header(header)
        for offset in (0, 60, 128, 132, 152, 180, 208):
            invalid = bytearray(header)
            invalid[offset] ^= 0xff
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                capture.check_image_header(invalid)
        with self.assertRaises(ValueError):
            capture.check_image_header(b'MZ')

    def test_process_name_delimiters_do_not_shift_start_time(self):
        stat = '123 (a name) with) brackets) S ' + ' '.join(str(i) for i in range(4, 40))
        self.assertEqual(capture.process_identity(stat), (123, 22, 'S'))

    def test_range_plan_clamps_to_selected_image_only(self):
        maps = ('00000000-00001000 r-xp 0 00:00 0\n'
                '00001000-00002000 r-xp 0 00:00 0\n'
                '00002000-00003000 rw-p 0 00:00 0 [stack]\n')
        self.assertEqual(capture.image_ranges(maps, 0x800, 0x1000),
                         [(0x800, 0x1000, 'r-xp'), (0x1000, 0x1800, 'r-xp')])

    def test_gaps_overlaps_nonexecutable_and_malformed_maps_rejected(self):
        invalid = ['00000000-00000008 r-xp 0 00:00 0\n',
                   '00000000-00000010 rw-p 0 00:00 0\n',
                   '00000000-00000010 --xp 0 00:00 0\n',
                   '00000000-00000010 r-xp 0 00:00 0\n00000008-00000010 r-xp 0 00:00 0\n',
                   'invalid\n']
        for maps in invalid:
            with self.subTest(maps=maps), self.assertRaises(ValueError):
                capture.image_ranges(maps, 0, 16)

    def test_copy_preserves_exact_selected_bytes_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'memory').write_bytes(bytes(range(256)))
            with (root / 'memory').open('rb') as memory:
                result = capture.copy_ranges(memory.fileno(), root / 'out', [(16, 32, 'r-xp'), (32, 48, 'r-xp')])
                self.assertEqual((root / 'out').read_bytes(), bytes(range(16, 48)))
                self.assertEqual(result, (32, hashlib.sha256(bytes(range(16, 48))).hexdigest()))
                with self.assertRaises(FileExistsError):
                    capture.copy_ranges(memory.fileno(), root / 'out', [(16, 32, 'r-xp')])

    def test_short_memory_read_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'memory').write_bytes(b'short')
            with (root / 'memory').open('rb') as memory:
                with self.assertRaisesRegex(OSError, 'Short'):
                    capture.copy_ranges(memory.fileno(), root / 'out', [(0, 16, 'r-xp')])
