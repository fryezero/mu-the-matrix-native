"""The census keeps unknown owners explicit and uses the pinned denominator."""
import os
from pathlib import Path
import struct
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import audio_caller_census as census


class AudioCensus(unittest.TestCase):
    def test_direct_call_scan_bounds_and_opaque_exclusion(self):
        payload = bytearray(32)
        payload[0] = 0xe8
        struct.pack_into('<i', payload, 1, census.PLAY - (census.BASE+5))
        payload[10] = 0xe8
        struct.pack_into('<i', payload, 11, census.PLAY+1 - (census.BASE+15))
        payload[-1] = 0xe8
        self.assertEqual(census.call_sites(payload), [census.BASE])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'Pinned census is opt-in')
    def test_pinned_inventory_keeps_unresolved_and_new_sites_separate(self):
        import pins
        result = census.inventory(pins.TEXT.read(), pins.DATA.read())
        self.assertEqual(result['total'], 1980)
        self.assertEqual(sum(row['sites'] for row in result['summary']), 1980)
        self.assertEqual(result['mapped_audio_sites'], 113)
        self.assertEqual(result['added_audio_sites'], 16)
        unknown = [row for row in result['sites'] if row['owner']=='unresolved']
        self.assertEqual(len(unknown), 755)
        self.assertFalse(any(row['audio_adapter'] for row in unknown))


if __name__ == '__main__':
    unittest.main()
