"""Receiver identity matters: a matching field offset alone is not a UI route."""
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import survey_ui_routes as survey


class ReceiverIdentity(unittest.TestCase):
    def test_manager_receiver_and_unrelated_same_offset(self):
        text=bytearray(1024)
        getter=0x401100
        text[0x100:0x112]=bytes.fromhex('55 8b ec 51 89 4d fc 8b 45 fc 8b 80 04 02 00 00 c9 c3')
        def call(a,target):return b'\xe8'+struct.pack('<i',target-a-5)
        a=0x401200
        route=call(a,0xac3bf7)+bytes.fromhex('8b c8')+call(a+7,getter)+bytes.fromhex('8b c8 8b 00 ff 50 40')
        text[0x200:0x200+len(route)]=route
        a=0x401280
        unrelated=call(a,getter)+bytes.fromhex('8b c8 8b 00 ff 50 40')
        text[0x280:0x280+len(unrelated)]=unrelated
        _,sites,_,_=survey.census(bytes(text),b'')
        self.assertEqual(len(sites),2)
        self.assertEqual(sites[0]['manager_slot'],'0x204')
        self.assertEqual(sites[1]['receiver'],'unresolved')

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private pinned registry')
    def test_private_registry_and_menu_correction(self):
        import pins
        text=pins.TEXT.read();registry,sites,direct,_=survey.census(text,pins.DATA.read())
        by_name={r['movie']:r for r in registry}
        self.assertEqual(by_name['PlayGuide.swf']['slot'],0x1f0)
        self.assertEqual(by_name['EventMapEntranceUI.swf']['slot'],0x2ac)
        self.assertEqual(len(direct[0xaae767]),103)
        menu=survey.menu_routes(text)
        self.assertEqual(len(menu),23)
        self.assertEqual(menu[22]['entry'],'0x00c71576')
        self.assertIn('0xb3b39e',menu[22]['calls'])
        self.assertTrue(any(s['manager_slot']=='0x184' and s['action']=='toggle' for s in sites))
