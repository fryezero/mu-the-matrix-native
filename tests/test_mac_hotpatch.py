"""Synthetic publication/regeneration checks, with no game bytes or Wine execution."""
import hashlib
import io
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'mac-play/hotpatch'
sys.path.insert(0, str(SOURCE))
import generate as hp
import inliner
import peep
sys.path.pop(0)


class GeneratorTests(unittest.TestCase):
    def test_bounds_overlap_and_replacement_size(self):
        hp.validate_records([(16,b'abc',b'xyz'),(19,b'a',b'b')])
        for records in [[(16,b'',b'')],[(16,b'ab',b'x')],[(16,b'ab',b'cd'),(17,b'x',b'y')]]:
            with self.subTest(records=records), self.assertRaises(ValueError):
                hp.validate_records(records)
        with self.assertRaises(ValueError):
            hp.checked(b'changed',{'length':7,'sha256':hashlib.sha256(b'correct').hexdigest()},'fixture')

    def test_private_headers_are_only_locally_generated(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            hp.tables(output,[],[],[],bytes(16),False)
            self.assertEqual((output/'private-build.h').read_text(),'#define MUGL_PRIVATE_TABLES 0\n')
            self.assertNotIn('0x12b5bde',(output/'hotpatches.h').read_text())
            hp.tables(output,[('fixture',16,b'abc',b'xyz')],[(32,b'abcde',b'vwxyz')],[],bytes(16),True)
            self.assertEqual((output/'private-build.h').read_text(),'#define MUGL_PRIVATE_TABLES 1\n')
        for name in ('hotpatches.h','inlinesites.h','peepsites.h','orig.h','xform-prologue.h'):
            self.assertFalse((SOURCE/name).exists(),name)

    def test_offline_listing_derivation_keeps_direct_calls_only(self):
        config = {'image_base':0x400000,'text_start':0x400002,'text_end':0x400006}
        fake = mock.Mock()
        fake.stdout = io.StringIO('header\n  400002:\tcall   0x400040\n  400007:\tcall   *%eax\n')
        fake.wait.return_value = 0
        with tempfile.TemporaryDirectory() as td, mock.patch.object(hp.subprocess,'Popen',return_value=fake) as popen:
            output = Path(td)
            calls, dis = hp.derive_listings(b'abcdefgh',config,output,'fixture-objdump')
            self.assertEqual((output/'text.bin').read_bytes(),b'cdef')
            self.assertEqual(calls.read_text(),'400002 0x400040\n')
            self.assertEqual(len(dis.read_text().splitlines()),2)
            self.assertIn('--adjust-vma=0x400002',popen.call_args.args[0])

    def test_inline_scanner_uses_hashes_and_checks_call_displacement(self):
        # Authored fixture: an identity helper and one relative call.
        base = 0x4000
        helper = b'\x89\xc8\xc3'
        mem = bytearray(64); mem[32:35] = helper
        mem[0:5] = b'\xe8' + struct.pack('<i',27)
        cfg = {'image_base':base,'helpers':[], 'ret4_address':base+48,
               'inline_templates':{'self':{'length':3,'sha256':hp.digest(helper),'replacement':'89c8909090'}},
               'wrapper_prefix':{'length':11,'sha256':'0'*64},'wrapper_suffix':{'length':2,'sha256':'0'*64}}
        records = inliner.scan(bytes(mem),[(base,base+32)],cfg)
        self.assertEqual(records,[(base,bytes(mem[:5]),b'\x89\xc8\x90\x90\x90')])
        mem[1] ^= 1
        with self.assertRaisesRegex(ValueError,'disagrees'):
            inliner.scan(bytes(mem),[(base,base+32)],cfg)

    def test_peephole_nonzero_base_slice_and_live_flags_rejection(self):
        base = 0x400000
        mem = b'\x6a\x04\x58\x6b\xc0\x00\xc3'
        ins = [(base,'push','$0x4'),(base+2,'pop','%eax'),(base+3,'imul','$0x0,%eax,%eax'),(base+6,'ret','')]
        a, old, new = peep.find_at(ins,0,mem,base)
        self.assertEqual((a,old,new),(base,mem[:6],b'\xb8\0\0\0\0\x90'))
        ins[-1] = (base+6,'je','0x500000')
        self.assertIsNone(peep.find_at(ins,0,mem,base))

    def test_no_credentials_or_process_restart_in_autologin(self):
        text = (ROOT/'mac-play/automation/mu-autologin.sh').read_text()
        self.assertIn('security find-generic-password',text)
        self.assertIn('"$MU_ACCOUNT"',text)
        self.assertNotIn('pkill',text)
        self.assertNotIn('mu-to-server.sh',text)
        self.assertNotIn('set -x',text)


if __name__ == '__main__':
    unittest.main()
