"""Native mix table/quote adapter on independently encoded synthetic tables."""
import ctypes as C
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from test_native_data import item_record, item_file, xor3

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_mix import recipe,condition,put


class Item(C.Structure):
    _fields_=[(k,C.c_int32) for k in ('code','level','option','excellent','durability','period')]


class Quote(C.Structure):
    _fields_=[(k,C.c_int32) for k in ('recipe','ready','supported')]+[
        ('rate',C.c_uint32),('cost',C.c_uint32),('title',C.c_char*96),('detail',C.c_char*256)]


def build(directory):
    path=directory/'libmixbook.dylib'
    sources=['native/core/mu_mix.c','native/core/mu_data.c','reconstructed/price/item_price.c']
    sources += [str(p.relative_to(ROOT)) for folder in ('data','mix') for p in (ROOT/'reconstructed'/folder).glob('*.c')]
    subprocess.run(['clang','-std=c11','-O2','-shared','-fPIC',*sources,'-lm','-o',str(path)],cwd=ROOT,
                   capture_output=True,check=True)
    lib=C.CDLL(str(path));lib.mu_mix_book_open.argtypes=[C.c_char_p];lib.mu_mix_book_open.restype=C.c_void_p
    lib.mu_mix_book_close.argtypes=[C.c_void_p]
    lib.mu_mix_book_quote.argtypes=[C.c_void_p,C.c_int,C.POINTER(Item),C.c_int,C.POINTER(Quote)]
    return lib


class MixBook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.lib=build(cls.root)
        cls.local=cls.root/'Data/Local';cls.local.mkdir(parents=True)
        rec=bytearray(item_record(1,b'Data/Item/',b'synthetic.bmd',b'Synthetic'))
        rec[0x250]=1;rec[0x291:0x2a1]=bytes(16)
        bless=bytearray(rec);struct.pack_into('<IHH',bless,0,0x1c0d,14,13)
        (cls.local/'Item.bmd').write_bytes(item_file([bytes(rec),bytes(bless)]))

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def quote(self,items,mode=ord('A'),repeat=1,code=1,value_formula=False):
        r=recipe([condition(code)]);r[0x3c]=mode;r[0x14c]=ord('A');r[0x15b]=repeat
        put(r,0x40,100);put(r,0x44,1);struct.pack_into('<If',r,0x48,0,65);put(r,0x148,100)
        if value_formula:
            put(r,0x44,3)
            for j,(token,value) in enumerate(((0x21,0),(4,0),(0,100000))):
                struct.pack_into('<If',r,0x48+j*8,token,value)
        counts=struct.pack('<22i',1,*([0]*21));(self.local/'Mix.bmd').write_bytes(xor3(counts)+xor3(r))
        book=self.lib.mu_mix_book_open(str(self.root).encode());self.assertTrue(book)
        try:
            q=Quote();self.lib.mu_mix_book_quote(book,0,(Item*len(items))(*items),len(items),C.byref(q));return q
        finally:self.lib.mu_mix_book_close(book)

    def test_quote_and_duplicate_quantity(self):
        a=Item(1,0,0,0,20,0)
        q=self.quote([a]);self.assertEqual((q.recipe,q.ready,q.supported,q.rate,q.cost),(0,1,1,65,100))
        q=self.quote([a,a],repeat=2);self.assertEqual((q.ready,q.cost),(1,200))
        self.assertEqual(self.quote([a,a]).ready,0)

    def test_unsupported_cost_and_option_are_not_free_quotes(self):
        a=Item(1,0,0,0,20,0)
        self.assertEqual(self.quote([a],mode=ord('D')).supported,0)
        a.option=1;self.assertEqual(self.quote([a]).supported,0)

    def test_missing_tables_and_empty_inputs(self):
        self.assertFalse(self.lib.mu_mix_book_open(b'/no-such-root'))
        q=self.quote([]);self.assertEqual((q.ready,q.recipe),(0,-1))

    def test_mix_valuation_drives_rate_and_mode_b_cost(self):
        q=self.quote([Item(0x1c0d,0,0,0,1,0)],mode=ord('B'),code=0x1c0d,value_formula=True)
        self.assertEqual((q.ready,q.supported,q.rate,q.cost),(1,1,1,100))


if __name__=='__main__':unittest.main()
