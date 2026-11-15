"""Synthetic provenance controls for the second UI route pass."""
import struct
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from survey_ui_indirect import indirect_routes, indirect_manager_roots

class IndirectRoutes(unittest.TestCase):
    def scan(self,tail,helper=False):
        text=bytearray(0x6ac300 if helper else 2048)
        start=0x401100;getter=0x401600
        def call(a,t):return b'\xe8'+struct.pack('<i',t-a-5)
        # Manager call has already returned when this pass starts.
        seq=call(start,0xac3bf7)+b'\x8b\xc8'+call(start+7,getter)
        if helper:
            seq+=b'\x8b\xc8'+call(start+len(seq)+2,0xaad100)
            text[0x6ac100:0x6ac100+len(tail)]=tail
        else:seq+=tail
        text[0x100:0x100+len(seq)]=seq
        return indirect_routes(bytes(text),b'',[{'slot':0xe0,'movie':'Authored.swf','lifecycle':[0xaae420,0xaae470]}],{0xac3bf7:[start]},{getter:0xe0})

    def test_register_method_and_branch_preserve_receiver(self):
        # Save window, branch, restore this; load method into edx then call it.
        rows=self.scan(bytes.fromhex('89 45 fc 85 c0 74 0c 8b 4d fc 8b 01 8b 50 40 ff d2 c3'))
        self.assertEqual([(r['manager_slot'],r['action'],r['encoding']) for r in rows],[('0xe0','open','register')])

    def test_wrong_vtable_and_clobbered_receiver_refuse(self):
        for tail in ('8b c8 31 c0 ff 50 40 c3','8b c8 8b 00 31 c9 ff 50 40 c3',
                     '8b c8 8b 00 83 c1 04 ff 50 40 c3'):
            self.assertEqual(self.scan(bytes.fromhex(tail)),[])

    def test_intermediate_window_method(self):
        rows=self.scan(bytes.fromhex('55 8b ec 51 89 4d fc 8b 4d fc 8b 01 ff 50 40 c9 c3'),helper=True)
        self.assertEqual([(r['manager_slot'],r['action']) for r in rows],[('0xe0','open')])

    def test_captured_pointer_roots_only(self):
        table=struct.pack('<II',0xac3bf7,0x111111)
        text=bytes.fromhex('ff 15 00 c0 a7 01 ff 15 04 c0 a7 01 b8 f7 3b ac 00 ff d0')
        self.assertEqual(indirect_manager_roots(text,table),[0x401000,0x401011])
