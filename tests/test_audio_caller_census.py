"""The census keeps unknown owners explicit and uses the pinned denominator."""
import os
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch
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
        for base, count in [(census.OPAQUE[0], 0), (census.OPAQUE[1], 1)]:
            call = b'\xe8' + struct.pack('<i', census.PLAY - (base+5))
            with patch.object(census, 'BASE', base):
                self.assertEqual(len(census.call_sites(call)), count)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'Pinned census is opt-in')
    def test_pinned_inventory_keeps_unresolved_and_new_sites_separate(self):
        import pins
        result = census.inventory(pins.TEXT.read(), pins.DATA.read())
        self.assertEqual(result['total'], 1980)
        self.assertEqual(sum(row['sites'] for row in result['summary']), 1980)
        self.assertEqual(result['mapped_audio_sites'], 113)
        self.assertEqual(result['added_audio_sites'], 16)
        unknown = [row for row in result['sites'] if row['owner']=='unresolved']
        with patch('audio_owner_groups.semantic_owners', return_value=({}, [])), patch.dict(
                census.NON_OWNER_REFERENCES, {('reconstructed/objects/world_inner5_visual.c',0xe8d888):'not present at entry',
                                              ('reconstructed/objects/world_inner5_visual.h',0xe8d888):'not present at entry'}):
            entry = census.inventory(pins.TEXT.read(), pins.DATA.read())
        self.assertEqual(sum(r['owner']=='unresolved' for r in entry['sites']),546)
        self.assertEqual(len(unknown),516)
        self.assertEqual(result['audio_006_sites'],182)
        self.assertEqual(result['enumerated_play_boundaries'],593)
        extended=[r for r in result['sites'] if r['audio_006_adapter']]
        self.assertTrue(all(r['owner']=='monsters' and r['native_reference'] and
                            r['sound_id_status']=='compared' and r['sound_ids'] for r in extended))
        self.assertTrue(all(not r['audio_005_adapter'] for r in extended))
        # INNER-004 named a refusal; merged INNER-005 now owns the visual-only body.
        refusal_only = [r for r in result['sites'] if r['anchor'] == '0x00e8d888']
        self.assertEqual({r['site'] for r in refusal_only}, {'0x00e8db8b', '0x00e8e002'})
        self.assertTrue(all(r['owner'] == 'world' and r['native_reference'] and
                            r['native_owner'] == 'bounded reference only' and not r['audio_005_adapter'] and not r['audio_006_adapter']
                            for r in refusal_only))
        self.assertEqual(result['audio_004_sites'], 33)
        self.assertEqual(result['audio_005_selector_sites'], 245)
        self.assertEqual(result['audio_005_sites'], 249)
        self.assertEqual(result['audio_005_stop_sites'], 2)
        admitted = [r for r in result['sites'] if r['audio_004_adapter']]
        self.assertTrue(all(r['native_owner'] == 'complete compared owner' and r['sound_id_status'] == 'compared' for r in admitted))
        self.assertTrue(all(r['routine_status'] == 'prologue grouping only' for r in unknown))
        self.assertFalse(any(row['audio_adapter'] for row in unknown))


    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'Pinned grouping ledger is opt-in')
    def test_reviewed_entry_groups_reproduce_without_a_private_report(self):
        import csv
        import pins
        import audio_owner_groups as groups
        with (ROOT/'docs/research/audio-006-entry-groups.csv').open(newline='') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),891)
        self.assertEqual(len({r['site'] for r in rows}),891)
        before={'sites':[dict(site=r['site'],anchor=r['anchor'],owner=r['entry_owner'],source=r['entry_source'],sound_id_status=r['entry_sound_id_status']) for r in rows]}
        text,data=pins.TEXT.read(),pins.DATA.read()
        result=groups.classify(before,census.inventory(text,data),text,data)
        self.assertEqual(result['groups'],{'owner unknown':546,'scalar world/distance/audio RNG':182,
            'delegated owner/context absent':47,'marker field or service absent':47,
            'prior action and stop ordering':3,'use owner target/buff/request/timing context absent':66})
        self.assertEqual(sum(r['wired'] for r in result['sites']),182)
        self.assertEqual(sum(r['group']=='owner unknown' and r['owner_after']!='unresolved' for r in result['sites']),30)


if __name__ == '__main__':
    unittest.main()
