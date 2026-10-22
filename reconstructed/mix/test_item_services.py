"""Synthetic boundary fixtures for personal-store registration and repair payloads."""
import ctypes as C
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

class Services(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();root=Path(__file__).parent
        path=Path(cls.tmp.name)/'services.dylib'
        subprocess.run(['clang','-std=c11','-shared','-fPIC',str(root/'item_services.c'),'-o',str(path)],check=True)
        cls.lib=C.CDLL(str(path))
        for name in ('mu_personal_store_ban','mu_personal_store_register'):
            getattr(cls.lib,name).argtypes=[C.c_void_p,C.c_void_p]
        cls.lib.mu_repair_request.argtypes=[C.c_void_p,C.c_uint8,C.c_uint8]
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def check(self,code=1,level=0,kind_a=1,kind_b=0,bound=0,durability=1,period=0,flag=1):
        r=bytearray(708);it=bytearray(300)
        r[0x250]=kind_a;r[0x251]=kind_b;r[0x2aa]=flag
        struct.pack_into('<ii',it,0x10,code,level<<3);struct.pack_into('<H',it,0x70,bound)
        it[0x38]=durability;it[0x92]=period
        return self.lib.mu_personal_store_register(bytes(r),bytes(it))
    def test_period_value_and_special_levels(self):
        self.assertEqual(self.check(period=1),0);self.assertEqual(self.check(period=2),1)
        self.assertEqual(self.check(flag=0),0)
        self.assertEqual(self.check(code=0x1c15,level=3,flag=0),1)
        self.assertEqual(self.check(code=0x1a14,level=1),0)
        self.assertEqual(self.check(code=0x1c0b,level=13),0)
        self.assertEqual(self.check(code=0x1c1a,level=1),0)
    def test_bound_and_depleted_categories(self):
        for a,b in ((5,0),(1,0x4f),(1,0x2e)):
            self.assertEqual(self.check(kind_a=a,kind_b=b,bound=1),0)
            self.assertEqual(self.check(kind_a=a,kind_b=b,bound=257),1)
        self.assertEqual(self.check(kind_b=0x2f,durability=254),0)
        self.assertEqual(self.check(kind_b=0x2b,durability=0),0)
        self.assertEqual(self.lib.mu_personal_store_register(None,None),0)
    def test_repair_modes_and_payload(self):
        for state,want in ((1,2),(2,1),(0,1),(-1,1)):
            self.assertEqual(self.lib.mu_repair_toggle(state),want)
        p=C.create_string_buffer(5)
        self.lib.mu_repair_request(p,255,0);self.assertEqual(p.raw,bytes([193,5,177,255,0]))
        self.lib.mu_repair_request(p,12,1);self.assertEqual(p.raw,bytes([193,5,177,12,1]))
if __name__=='__main__':unittest.main()
