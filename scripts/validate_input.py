#!/usr/bin/env python3
"""INPUT-001: compiled production C against pinned x86 scan and menu-key blocks.

The scan is the whole 0x00ec5475 routine. GetAsyncKeyState, foreground/active
HWND queries are synthetic OS inputs. Binding cases execute the key-test block
through its dispatch call, stopping before the context-dependent window code.
No model of a panel, service, original IME or network is claimed.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile

import pins
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_EIP

ROOT = Path(__file__).resolve().parents[1]
KEYS = ROOT / 'native/world/input_keys.c'
# key, menu id, key-test entry, fallthrough. These are source addresses, not copied bytes.
BINDINGS = [
    ('Y',13,0xefc559,0xefc593), ('I',14,0xefc593,0xefc5cd), ('C',1,0xefc5cd,0xefc616),
    ('Q',16,0xefc86c,0xefc8a6), ('W',17,0xefc8a6,0xefc8e0), ('E',18,0xefc8e0,0xefc91a),
    ('R',19,0xefc91a,0xefc954), ('X',0,0xefc9e6,0xefca20), ('T',2,0xefca20,0xefca5a),
    ('M',4,0xefca5a,0xefca94), ('O',5,0xefca94,0xefcace), ('J',6,0xefcace,0xefcb08),
    ('P',7,0xefcb08,0xefcb42), ('F',9,0xefcb42,0xefcb7c), ('G',10,0xefcb7c,0xefcbb6),
    ('B',11,0xefcbb6,0xefcbf0), ('N',12,0xefcbf0,0xefcc2a), ('K',15,0xefcc2a,0xefcc64),
]


def native(tmp, source, name):
    c = tmp / (name + '.c'); c.write_text(source)
    lib = tmp / (name + '.dylib')
    subprocess.run(['cc', '-shared', '-fPIC', '-O2', '-I', str(KEYS.parent), str(c), '-o', str(lib)], check=True)
    dll = C.CDLL(str(lib)); arr = C.POINTER(C.c_uint8)
    dll.mu_input_scan.argtypes = [arr, arr, C.c_int, C.c_int, C.c_int, C.c_int]
    dll.mu_input_menu.argtypes = [C.c_int, C.c_int]; dll.mu_input_menu.restype = C.c_int
    return dll


class Original:
    def __init__(self, text):
        self.uc = u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(0x401000, (len(text)+4095)&~4095); u.mem_write(0x401000, text)
        for addr, size in [(0x1a7c000,4096),(0x6fc9000,4096),(0xbdc5000,4096),(0x10000000,0x10000)]:
            u.mem_map(addr,size)
        for slot, stub in [(0x1a7c7bc,0x10000100),(0x1a7c7b8,0x10000110),(0x1a7c840,0x10000120)]:
            u.mem_write(slot, struct.pack('<I',stub))
        u.hook_add(UC_HOOK_CODE,self.hook)

    def ret(self, value, cleanup=0):
        u=self.uc; sp=u.reg_read(UC_X86_REG_ESP); addr=self.word(sp)
        u.reg_write(UC_X86_REG_EAX,value); u.reg_write(UC_X86_REG_ESP,sp+4+cleanup)
        u.reg_write(UC_X86_REG_EIP,addr)

    def word(self, addr): return struct.unpack('<I',self.uc.mem_read(addr,4))[0]

    def hook(self,u,a,size,data):
        if a==0x10000100: self.ret(0x8000 if self.down[self.word(u.reg_read(UC_X86_REG_ESP)+4)] else 0,4)
        elif a==0x10000110: self.ret(7 if self.foreground else 8)
        elif a==0x10000120: self.ret((7 if self.foreground else 8) if self.active else 9)
        elif self.binding and a in (0xec53a7,0xec53bb):
            key=self.word(u.reg_read(UC_X86_REG_ESP)+4)
            self.ret(int((key==self.key and self.pressed) if a==0xec53a7 else (key==0x10 and self.shift)))
        elif self.binding and a==0x95f144: self.ret(0x10008000)
        elif self.binding and a==0xc714bd:
            self.result=self.word(u.reg_read(UC_X86_REG_ESP)+4); u.emu_stop()
        elif self.binding and a==self.fall: u.emu_stop()
        elif a==0x10000200: u.emu_stop()

    def scan(self,state,down,enabled,foreground,allow,active):
        self.binding=False; self.down=down; self.foreground=foreground; self.active=active
        u=self.uc
        u.mem_write(0x10008000,state); u.mem_write(0x6fc9cb5,bytes([enabled])); u.mem_write(0x6fc9c94,struct.pack('<I',7))
        u.mem_write(0xbdc5982,bytes([allow])); u.mem_write(0x1000f000,struct.pack('<I',0x10000200))
        u.reg_write(UC_X86_REG_ESP,0x1000f000); u.reg_write(UC_X86_REG_ECX,0x10008000)
        u.emu_start(0xec5475,0,count=30000)
        assert u.reg_read(UC_X86_REG_EIP)==0x10000200
        return bytes(u.mem_read(0x10008000,256))

    def menu(self,key,entry,fall,pressed,shift=0):
        self.binding=True; self.key=key; self.pressed=pressed; self.shift=shift; self.fall=fall; self.result=-1
        u=self.uc; u.reg_write(UC_X86_REG_ESP,0x1000e000); u.reg_write(UC_X86_REG_EBP,0x1000f000)
        u.emu_start(entry,0,count=200)
        assert u.reg_read(UC_X86_REG_EIP) in (fall,0xc714bd)
        return self.result


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--cases',type=int,default=400)
    ap.add_argument('--text'); ap.add_argument('--mutations',action='store_true'); ap.add_argument('--output')
    args=ap.parse_args(); text=pins.TEXT.read(args.text); original=Original(text); rng=random.Random(1001)
    cases=[]
    # Exhaustive byte states, including invalid states, then random whole arrays and all OS gates.
    for i in range(max(256,args.cases)):
        state=bytes([i%256]*256) if i<256 else bytes(rng.randrange(256) for _ in range(256))
        down=bytes(rng.randrange(2) for _ in range(256))
        gates=(1,i%2,(i//2)%2,(i//4)%2) if i<256 else tuple(rng.randrange(2) for _ in range(4))
        cases.append((state,down,gates,original.scan(state,down,*gates)))
    for state_value in range(4):
        for held_value in range(2):
            for bits in range(16):
                state=bytes([state_value]*256); down=bytes([held_value]*256)
                gates=tuple((bits>>k)&1 for k in range(4))
                cases.append((state,down,gates,original.scan(state,down,*gates)))
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td); source=KEYS.read_text(); dll=native(tmp,source,'input')
        def mismatches(lib):
            bad=0
            for state,down,gates,want in cases:
                out=(C.c_uint8*256).from_buffer_copy(state); held=(C.c_uint8*256).from_buffer_copy(down)
                lib.mu_input_scan(out,held,*gates); bad+=bytes(out)!=want
            return bad
        scan_bad=mismatches(dll); binding_bad=0; binding_count=0
        for key,id,entry,fall in BINDINGS:
            for pressed in (0,1):
                for shift in ((0,1) if key=='C' else (0,)):
                    got=original.menu(ord(key),entry,fall,pressed,shift)
                    want=dll.mu_input_menu(ord(key),shift) if pressed else -1
                    binding_bad+=got!=want; binding_count+=1
        # Ctrl branches are entered after their outer held-Ctrl predicate; native API carries that predicate.
        for key,id,entry,fall in [('Z',20,0xefc964,0xefc99e),('X',21,0xefc9ad,0xefc9e6)]:
            for pressed in (0,1):
                got=original.menu(ord(key),entry,fall,pressed)
                binding_bad+=got!=(dll.mu_input_menu(ord(key),2) if pressed else -1); binding_count+=1
        mutants={}
        if args.mutations:
            for name,old,new in [
                ('press_becomes_held','state[k] = 2;','state[k] = 3;'),
                ('release_lost','state[k] = 1;','state[k] = 0;'),
                ('ignore_foreground','down[k] && foreground','down[k]'),
                ('escape_tab_gate','&& !escape_tab_allowed && active_is_foreground','&& escape_tab_allowed && active_is_foreground'),
                ('disabled_scan','if (!enabled) return;','if (enabled == 2) return;')]:
                assert old in source
                mutants[name]=mismatches(native(tmp,source.replace(old,new),name))>0
            for name,old,new,key,mods in [('pet_inventory','return 13;','return 14;',ord('Y'),0),
                                           ('item_slot','return 16;','return 17;',ord('Q'),0)]:
                lib=native(tmp,source.replace(old,new),name)
                mutants[name]=lib.mu_input_menu(key,mods)!=dll.mu_input_menu(key,mods)
        report={'families':{'scan':{'cases':len(cases),'key_decisions':len(cases)*256,'mismatches':scan_bad},
                            'bindings':{'cases':binding_count,'mismatches':binding_bad}},'mutants':mutants,
                'pins':{'text':pins.TEXT.sha256},'limits':'OS queries modeled; window handlers and IME candidate UI not emulated'}
        out=json.dumps(report,indent=2); print(out)
        if args.output: Path(args.output).write_text(out+'\n')
        return int(bool(scan_bad or binding_bad or (mutants and not all(mutants.values()))))


if __name__=='__main__': raise SystemExit(main())
