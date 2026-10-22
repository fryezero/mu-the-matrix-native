"""Compose the native service adapter with synthetic Item.bmd and price rules."""
import ctypes as C
from pathlib import Path
import struct
import tempfile
import unittest
from test_native_mix_book import build,Item
from test_native_data import item_record,item_file,xor3

class ServiceBook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.lib=build(cls.root)
        local=cls.root/'Data/Local';local.mkdir(parents=True)
        r=bytearray(item_record(1,b'Data/Item/',b'synthetic.bmd',b'Synthetic'))
        r[0x250]=1;struct.pack_into('<H',r,0x254,1);r[0x268]=20;r[0x2aa]=r[0x2ae]=1
        struct.pack_into('<I',r,0x28c,100000)
        (local/'Item.bmd').write_bytes(item_file([bytes(r)]));(local/'Mix.bmd').write_bytes(xor3(bytes(88)))
        cls.lib.mu_mix_book_store.argtypes=[C.c_void_p,C.POINTER(Item)]
        cls.lib.mu_mix_book_repair.argtypes=[C.c_void_p,C.POINTER(Item),C.c_int,C.POINTER(C.c_int32),C.POINTER(C.c_int32)]
        cls.book=cls.lib.mu_mix_book_open(str(cls.root).encode());assert cls.book
    @classmethod
    def tearDownClass(cls):cls.lib.mu_mix_book_close(cls.book);cls.tmp.cleanup()
    def repair(self,item,npc=1):
        cost=C.c_int32();maximum=C.c_int32()
        ok=self.lib.mu_mix_book_repair(self.book,C.byref(item),npc,C.byref(cost),C.byref(maximum))
        return ok,cost.value,maximum.value
    def test_store_flags_and_periods_are_from_table_and_snapshot(self):
        self.assertEqual(self.lib.mu_mix_book_store(self.book,C.byref(Item(1,0,0,0,1,0))),1)
        self.assertEqual(self.lib.mu_mix_book_store(self.book,C.byref(Item(1,0,0,0,1,1))),0)
        self.assertEqual(self.lib.mu_mix_book_store(self.book,C.byref(Item(999,0,0,0,1,0))),0)
    def test_repair_cost_and_full_durability(self):
        npc=self.repair(Item(1,0,0,0,5,0));own=self.repair(Item(1,0,0,0,5,0),0)
        self.assertEqual(npc[0],1);self.assertEqual(npc[2],20)
        self.assertGreater(npc[1],0);self.assertGreater(own[1],npc[1])
        self.assertEqual(self.repair(Item(1,0,0,0,20,0))[0],0)
    def test_unsupported_option_and_bad_snapshot_decline(self):
        for it in (Item(1,0,1,0,5,0),Item(999,0,0,0,5,0),Item(1,0,0,0,256,0),Item(1,0,0,0,5,1)):
            self.assertEqual(self.repair(it)[0],0)
if __name__=='__main__':unittest.main()
