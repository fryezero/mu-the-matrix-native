"""Synthetic publication/regeneration checks, with no game bytes or Wine execution."""
import hashlib
import io
import importlib.util
import json
from pathlib import Path
import re
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
        for name in ('hotpatches.h','inlinesites.h','peepsites.h','orig.h','xform-prologue.h','meshdraw-orig.h'):
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


class MeshDrawPublicationTests(unittest.TestCase):
    def setUp(self):
        self.mugl = (SOURCE/'mugl.c').read_text()
        self.meshdraw = (SOURCE/'meshdraw.c').read_text()
        self.targets = json.loads((SOURCE/'targets.json').read_text())

    def test_patch_site_originals_are_hash_pinned_and_header_is_not_source(self):
        sites = {site['name']: site for site in self.targets['meshdraw_sites']}
        self.assertEqual(set(sites),{'md_orig','md_lorig','md_prologue'})
        addresses = {name: int(re.search(rf'#define {macro} (0x[0-9a-fA-F]+)',self.meshdraw).group(1),16)
                     for name,macro in [('md_orig','MD_PATCH'),('md_lorig','MD_LPATCH'),('md_prologue','MD_ENTRY')]}
        for name,site in sites.items():
            with self.subTest(name=name):
                self.assertEqual(site['address'],addresses[name])
                self.assertRegex(site['sha256'],r'^[0-9a-f]{64}$')
                # The C source compares/copies exactly this many bytes of the generated array.
                self.assertRegex(self.meshdraw,rf'{name}, (?:j, )?{site["length"]}\b')
        self.assertIn('#include "meshdraw-orig.h"',self.meshdraw)
        for name in sites:
            self.assertIsNone(re.search(rf'{name}\[[0-9]*\]\s*=',self.meshdraw),'original bytes must stay in the generated header')
        self.assertIsNone(re.search(r'unsigned char[^;=]*\[[^\]]*\]\s*=\s*\{\s*0x',self.meshdraw))

    def test_synthetic_meshdraw_header_has_zero_tables_and_private_one_is_exact_size(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            hp.tables(output,[],[],[],bytes(16),False)
            text = (output/'meshdraw-orig.h').read_text()
            for name,length in [('md_orig',7),('md_lorig',6),('md_prologue',10)]:
                self.assertIn(f'static const unsigned char {name}[{length}] = {{'+','.join(['0']*length)+'};',text)
            hp.tables(output,[],[],[],bytes(16),True,[('md_orig',b'\x01\x02')])
            self.assertIn('md_orig[2] = {1,2};',(output/'meshdraw-orig.h').read_text())
        for site in self.targets['meshdraw_sites']:
            with self.assertRaises(ValueError):
                hp.checked(bytes(site['length']),site,site['name'])

    def test_mask_bits_are_documented_and_default_is_their_sum(self):
        default = int(re.search(r'int want = (\d+);',self.mugl).group(1))
        mask = int(re.search(r'want = v & (\d+);',self.mugl).group(1))
        readme = (SOURCE/'README.md').read_text()
        rows = {int(m.group(1)) for m in re.finditer(r'^\| (\d+) \|',readme,re.M)}
        self.assertEqual(rows,{1<<k for k in range(14)})
        self.assertEqual(mask,(1<<14)-1)
        self.assertEqual(default,7599)
        self.assertEqual(default,sum(1<<k for k in (0,1,2,3,5,7,8,10,11,12)))
        self.assertEqual(default & (8192|64|16|512),0,'diagnostic and unverified bits stay off by default')
        self.assertIn('md_untested = (mask & 8192) != 0',self.mugl)

    def test_synthetic_build_cannot_apply_game_patches(self):
        self.assertRegex(self.mugl,r'total_frames > 100 && MUGL_PRIVATE_TABLES')
        self.assertIn('0x8000',self.meshdraw)
        self.assertRegex(self.meshdraw,r'if \(mode == 0x8000\) \{ md_fallback\+\+')
        self.assertRegex(self.meshdraw,r'\(flags & 0x420\) == 0x400')

    def test_provenance_records_v71_sources_and_new_diagnostic(self):
        provenance = json.loads((SOURCE/'source-provenance.json').read_text())
        for source,published in [('mugl/mugl_v71.c','mac-play/hotpatch/mugl.c'),('mugl/meshdraw_v71.c','mac-play/hotpatch/meshdraw.c'),
                                 ('glstride/glstride.c','mac-play/diagnostics/glstride.c')]:
            with self.subTest(source=source):
                self.assertRegex(provenance[source]['sha256'],r'^[0-9a-f]{64}$')
                self.assertEqual(provenance[source]['published_as'],published)
                self.assertTrue((ROOT/published).is_file())
        self.assertEqual(provenance['mugl/xform_v70.c']['published_as'],'mac-play/hotpatch/xform.c')  # xform.c is unchanged between v7.0 and v7.1


if __name__ == '__main__':
    unittest.main()
