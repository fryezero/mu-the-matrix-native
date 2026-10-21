#!/usr/bin/env python3
"""Compare the client's item value and repair-cost routines with reconstructed/price (NATIVE-LANG-002).

Client code runs in Unicorn over the pinned restored text (capture 09) and
second image section (run 10), on the machine of scripts/validate_item_fields.py:
the item-script manager is built by its own constructor and the Item.bmd
loader from the installed file, item objects by the constructor 0x00ccbaa2
and bound to their record by 0x00ccc51e.

* ItemValue 0x0169320b (cdecl item, goldType) runs for every installed code
  x item levels 0..15 x goldType 0/1/2 with random object states (options,
  excellent/set bits, sockets, durability, stack, harmony, period), random
  world (0 or 0x5c) and singleton flags, and on synthetic records (random
  bytes, forced kinds and special codes).  Socket items price their seed
  spheres through 0x010a91a7, which constructs a new object and calls
  ItemValue again, all as client code.
* ConvertRepairGold 0x016b8d16 runs on ItemValue(item, 2) of the same cases
  and on random values, durabilities and window states.

Modelled (not client code), each a stub returning the case's input:
  - the singleton getter 0x0095f75d (its byte +4 = the sell flag);
  - the pet / special-durability record 0x00c9362d (first int = status) and
    its price 0x00c93eb2;
  - MonsterSoulConversion's lookup 0x00d371cb (a random code set);
  - 0x0096baca / 0x0097f855 (a manager whose result does not change the
    price: kind A 0x1c is 200000 on every branch);
  - for ConvertRepairGold: the GFx manager 0x00ac3bf7 and IsVisible
    0x00aae6f9 (NpcShop +0xf4, its repair flag +0xb0, inventory +0xa0), the
    equipped helper slots 0x00c062b5 and the info manager 0x0099536d /
    0x009b460f / 0x009b481a that give the discount percent, and the
    number formatter 0x016b8b26 (text only);
  - the three displaced compares (jumps to 0x10b401b0 / 0x10b40050 /
    0x10b40100, outside the restored image) as stubs that execute
    "cmp [ebp-X], 4 (or 5); je case; jmp back": an INFERRED reading, so
    those option values are checked for consistency only.
The CRT conversions take their SSE2 paths (bit 0x20 of [0x01cf6610], as in
validate_terrain.py); the x87 control word is the Windows default 0x27f.

--mutations rebuilds the library with five planted mistakes
(reconstructed/price/Makefile mutantN) and requires each to be detected.
Decoded game data is never written; the report holds counts and digests.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fields = load_module('validate_item_fields', ROOT/'scripts/validate_item_fields.py')
tables, models = fields.tables, fields.models

ITEM_VALUE, REPAIR_GOLD, SOCKET_PRICE = 0x0169320b, 0x016b8d16, 0x010a91a7
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
BODIES = {  # start, exclusive end, SHA-256 of the captured bytes (checked before use)
    'item_value': (0x0169320b, 0x016963bf, '6a6af89ad2e2cb56f95297328af861541763c71d839e9fb0da8c2f9ee5f570b7'),
    'repair_gold': (0x016b8d16, 0x016b9103, '2447d911384a79ea8a1591cd52f2d3aa231553cf36c909f0dda533510ee715fd'),
    'socket_price': (0x010a91a7, 0x010a9310, '8f3fc36674f0a018a450acb19b58479580dace737a317c81666ac04a26d98924'),
    'has_excellent': (0x00cd14a7, 0x00cd14e0, '9d9e894e42af53443192d51c504e268a345ae40156b8917439eb02df2b8eb071'),
    'kind_2d_group': (0x00cd1dfc, 0x00cd1ef8, 'f043d4f8265442d7cd613f59b7cefe0c73c728e60ee29c60f94ebcd61ae6ad38'),
    'set_2d_group': (0x00cd21f6, 0x00cd2225, '1bb33edbd0aff711a0ef3d6f899bbd450a5bd8344ed343d01e2e7480464a0163'),
    'type2_kind2': (0x00cd2175, 0x00cd21aa, '70935e911d41f2cb10ffa91f6e22c4dcb79b94385470d72ec0725a134bbf9b01'),
    'wing_core_bits': (0x00cdaf42, 0x00cdaf89, 'fb5a41934518b325ec96af3ee3b3157ea92fbad5f63571163db2b5b15b72de2b'),
    'code_range': (0x0095c61f, 0x0095c652, '46bc378365742890320c64af2e66325ce9718778fb524245d62091bf73507998'),
    'pet_kind': (0x00c92e9a, 0x00c92ef3, '7c7e05998b069791e2f038d410bc6f659da5ca8e3625cfd980aceb61bad87665'),
}
HOOK_TARGETS = {  # displaced compare: (stub address, ebp displacement, first value, case, resume)
    0x10b401b0: (-0x50, 4, 0x01694b8c, 0x01694b71),
    0x10b40050: (-0x54, 4, 0x01694d7f, 0x01694d64),
    0x10b40100: (-0x58, 5, 0x01694e6c, 0x01694e51),
}
SINGLETON_GETTER, PET_RECORD, PET_VALUE, SOUL = 0x0095f75d, 0x00c9362d, 0x00c93eb2, 0x00d371cb
MGR_96, LOOKUP_97 = 0x0096baca, 0x0097f855
GFX_MANAGER, IS_VISIBLE, SLOT_ITEM = 0x00ac3bf7, 0x00aae6f9, 0x00c062b5
INFO_MANAGER, INFO_GET, INFO_ADJUST, FORMAT = 0x0099536d, 0x009b460f, 0x009b481a, 0x016b8b26
CURRENT_WORLD, CPU_FLAGS, SOCKET_MANAGER = 0x01cf15fc, 0x01cf6610, 0x06fb4518
DELETE, FREE_BASE = 0x0191baab, 0x0191c490   # operator delete / free (CRT heap, modelled as the Runner's free)
SPECIAL_CODES = [0x807, 0x80f, 0x1c0d, 0x1c0e, 0x180f, 0x1c10, 0x1c16, 0x1c8d, 0x1a0e, 0x1a03, 0x1a0f, 0x1a10,
                 0x1a11, 0x1a12, 0x1c1c, 0x1c1d, 0x1c6f, 0x1c6e, 0x1c66, 0x286c, 0x1c6d, 0x1c65, 0x1c68, 0x1a1d,
                 0x1c15, 0x1c11, 0x1c12, 0x1c13, 0x1a31, 0x1c17, 0x1c09, 0x1c14, 0x1c34, 0x1c0a, 0x1c1f, 0x1c07,
                 0x1a07, 0x1a0b, 0x1c23, 0x1c27, 0x1c55, 0x1a91, 0x1a93, 0x1890, 0x1896, 0x1897, 0x1920, 0x1d22,
                 0x1d36, 0x1d3c, 0x1d40, 0x1d3d, 0x1dd4, 0x1c00, 0x1c03, 0x1c05, 0x1a14, 0x1a34, 0x1a1f, 0x1a20,
                 0x1a25, 0x1c2e, 0x1db3, 0x1ce0, 0x1c9a, 0x1c9e, 0x18e8, 0x18db, 0x1a48, 0x1a04, 0x1a05, 0x28f7,
                 0x2900, 0x1a70, 0x1a7b, 0x1886, 0x1b0c, 0x190a, 0x19e0, 0x1aa9, 0x1cdb, 0x1cf6, 0x1d10, 0x1d86,
                 0x18d7, 0x20ef, 0x20f0, 0x1d1b, 0x29, 0x1bfe, 0x1b98, 0x1d59, 0x1da4, 0x1d74, 0x1c45, 0x1dae,
                 0x1dbe, 0x1dd2, 0x1dd9, 0x1ddd, 0x2915, 0x285e, 0x1d9e, 0x286d, 0x28a4, 0x289d, 0x2876, 0x289e,
                 0x28a0, 0x28a1, 0x181d, 0x1a06, 0x2985, 0x1a92, -1, -7, 0x2c00, 0x2c01, 0x7ffffff0]
COVERAGE = {  # client addresses whose execution the report counts (branch coverage of the cases)
    0x10b401b0: 'displaced_compare_wing', 0x10b40050: 'displaced_compare_plain', 0x10b40100: 'displaced_compare_5',
    0x01693263: 'fixed_zen', 0x0169462f: 'value_branch_return', 0x01694719: 'kind_19', 0x016947a9: 'kind_1a',
    0x0169485c: 'type_c_d_f', 0x016949da: 'wing_formula', 0x01694a3c: 'one_handed_80', 0x01694abb: 'skill_x1_5',
    0x01694b8c: 'wing_6_10', 0x01694c19: 'wing_56_10', 0x01694cc3: 'type2_kind2_6_10', 0x01694d7f: 'plain_6_10',
    0x01694e0c: 'plain_56_10', 0x01694e6c: 'opt3_6_10', 0x01694ef9: 'opt3_56_10', 0x01694f27: 'opt5_25',
    0x01694f55: 'opt_double', 0x01694fc0: 'excellent_loop', 0x016950c3: 'excellent_pow', 0x01695178: 'set_pow',
    0x016951c7: 'flag72_16', 0x010a91e5: 'socket_item', 0x010a92d3: 'seed_sphere_recursion',
    0x01695220: 'harmony', 0x01695286: 'clamp_3e9', 0x016955a1: 'pet_minus_one', 0x016955a9: 'pet_value',
    0x01695cd3: 'soul_conversion', 0x01696254: 'sell_wear', 0x01694546: 'value_1c00_range',
    0x016b8d7a: 'repair_roots', 0x016b8e1a: 'repair_broken_pet', 0x016b8e2e: 'repair_broken_plus40',
    0x016b8e9a: 'repair_npc_shop', 0x016b8f3c: 'repair_self_1_1', 0x016b906d: 'repair_discount'}
SKILLS = [0, 0x12, 0x15, 0x18, 0x19, 0x38, 0x104, 0x105, 0x10e, 0x2a]


class Item(ctypes.Structure):
    _fields_ = [('code', ctypes.c_int32), ('level', ctypes.c_int32), ('durability', ctypes.c_uint8),
                ('max_durability', ctypes.c_uint8), ('set_bits', ctypes.c_uint8), ('special_count', ctypes.c_uint8),
                ('special', ctypes.c_uint16*8), ('special_value', ctypes.c_uint16*8), ('skill', ctypes.c_uint16),
                ('flag_72', ctypes.c_uint8), ('slot_73', ctypes.c_uint8*5), ('socket_count', ctypes.c_uint8),
                ('socket', ctypes.c_uint8*5), ('socket_level', ctypes.c_uint8*5), ('period', ctypes.c_uint8),
                ('expired', ctypes.c_uint8), ('excellent', ctypes.c_uint8), ('excellent_options', ctypes.c_uint8*9),
                ('harmony', ctypes.c_int32)]


RECORD_OF = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
SOUL_OF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32)


class State(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('sell_flag', ctypes.c_uint8),
                ('socket_seed', ctypes.POINTER(ctypes.c_int32)), ('record_of', RECORD_OF),
                ('soul_conversion', SOUL_OF), ('user', ctypes.c_void_p), ('pet_status', ctypes.c_int32),
                ('pet_value', ctypes.c_uint32)]


class Repair(ctypes.Structure):
    _fields_ = [('shop_visible', ctypes.c_int), ('shop_repair_flag', ctypes.c_int),
                ('inventory_visible', ctypes.c_int), ('discount_percent', ctypes.c_int32)]


class Native:
    def __init__(self, path, records):
        self.lib = lib = ctypes.CDLL(str(path))
        lib.mu_item_price.argtypes = [ctypes.c_char_p, ctypes.POINTER(Item), ctypes.c_int, ctypes.POINTER(State)]
        lib.mu_item_price.restype = ctypes.c_int32
        lib.mu_item_repair_cost.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int16,
                                            ctypes.POINTER(Repair)]
        lib.mu_item_repair_cost.restype = ctypes.c_int32
        self.buffers = {code: ctypes.create_string_buffer(record, len(record)) for code, record in records.items()}
        self.soul = set()
        self.record_of = RECORD_OF(lambda user, code: ctypes.addressof(self.buffers[code])
                                   if code in self.buffers else None)
        self.soul_of = SOUL_OF(lambda user, code: int(code in self.soul))
        self.seeds = (ctypes.c_int32*256)()

    def price(self, record, item, gt, world, flag, pet):
        state = State(world, flag, self.seeds, self.record_of, self.soul_of, None, pet[0], pet[1] & 0xffffffff)
        return self.lib.mu_item_price(record, ctypes.byref(item), gt, ctypes.byref(state))

    def repair(self, value, durability, maximum, code, window):
        return self.lib.mu_item_repair_cost(value, durability, maximum, ctypes.c_int16(code).value,
                                            ctypes.byref(Repair(*window)))


class Client(fields.Client):
    """The item-fields runner plus the modelled stubs of this validator."""

    def __init__(self, machine, image):
        super().__init__(machine, image)
        from unicorn import UC_HOOK_CODE, UC_PROT_ALL
        uc = self.uc
        self.sell_flag, self.pet, self.soul, self.windows = 0, (-1, 0), set(), (0, 0, 0)
        self.slots, self.infos = [None, None, None], {}
        self.singleton = self.allocate(0x40)
        self.pet_record = self.allocate(0x40)
        self.gfx = self.allocate(0x400)
        self.shop, self.inventory = self.allocate(0x200), self.allocate(0x200)
        uc.mem_write(self.gfx+0xf4, struct.pack('<I', self.shop))
        uc.mem_write(self.gfx+0xa0, struct.pack('<I', self.inventory))
        self.slot_objects = [self.allocate(0x200) for _ in range(3)]
        self.info_objects = {}
        self.text = self.allocate(0x400)
        uc.mem_map(0x10b40000, 0x1000, UC_PROT_ALL)
        for stub, (disp, first, case, resume) in HOOK_TARGETS.items():
            code = bytes([0x83, 0x7d, disp & 0xff, first]) + b'\x0f\x84' + struct.pack('<i', case-(stub+10)) + \
                b'\xe9' + struct.pack('<i', resume-(stub+15))
            uc.mem_write(stub, code)
        uc.mem_write(CPU_FLAGS, bytes([uc.mem_read(CPU_FLAGS, 1)[0] | 0x20]))
        extra = {SINGLETON_GETTER: lambda: self.finish(self.singleton),
                 PET_RECORD: lambda: self.finish(self.pet_record),
                 PET_VALUE: lambda: self.finish(self.pet[1]),
                 SOUL: lambda: self.finish(int(self.argument(0) in self.soul)),
                 MGR_96: lambda: self.finish(tables.DUMMY),
                 LOOKUP_97: lambda: self.finish(0, 8),
                 GFX_MANAGER: lambda: self.finish(self.gfx),
                 IS_VISIBLE: self.is_visible,
                 SLOT_ITEM: self.slot_item,
                 INFO_MANAGER: lambda: self.finish(tables.DUMMY),
                 INFO_GET: self.info_get,
                 INFO_ADJUST: self.info_adjust,
                 FORMAT: lambda: self.finish(0),
                 DELETE: lambda: self.finish(0), FREE_BASE: lambda: self.finish(0)}
        self.handlers.update(extra)
        self.coverage = {name: 0 for name in COVERAGE.values()}

        def count(uc_, address, size, ignored):
            self.coverage[COVERAGE[address]] += 1
        self.hooks += [uc.hook_add(UC_HOOK_CODE, count, begin=a, end=a) for a in COVERAGE]
        self.hooks += [uc.hook_add(UC_HOOK_CODE, self.dispatch, begin=a, end=a) for a in extra]
        uc.ctl_flush_tb()

    def is_visible(self):
        from unicorn.x86_const import UC_X86_REG_ECX
        this = self.uc.reg_read(UC_X86_REG_ECX)
        shop, _, inventory = self.windows
        self.finish(shop if this == self.shop else inventory if this == self.inventory else 0)

    def slot_item(self):
        self.finish(self.slot_objects[self.argument(0)] if self.slots[self.argument(0)] else 0, 4)

    def info_get(self):
        code = self.argument(0)
        self.finish(self.info_objects.get(code, 0), 4)

    def info_adjust(self):   # modelled: the adjusted percent is value + level + 1
        code, level, value = (self.argument(i) for i in range(3))
        self.finish(value + level + 1, 0xc)

    def call(self, address, arguments, ecx=0, limit=3_000_000_000):
        from unicorn import UcError
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_EAX, \
            UC_X86_REG_EIP, UC_X86_REG_FPCW
        uc = self.uc
        uc.context_restore(self.machine.snapshot)
        esp = tables.STACK+tables.STACK_BYTES-0x2000
        uc.mem_write(esp, struct.pack('<I', tables.SENTINEL)+b''.join(struct.pack('<I', a & 0xffffffff)
                                                                        for a in arguments))
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.reg_write(UC_X86_REG_EBP, 0)
        uc.reg_write(UC_X86_REG_ECX, ecx)
        uc.reg_write(UC_X86_REG_FPCW, 0x27f)
        self.stop = None
        try:
            uc.emu_start(address, tables.SENTINEL, count=limit)
        except UcError as error:
            raise RuntimeError(f'{address:#x}: {error}; {self.stop}') from error
        if uc.reg_read(UC_X86_REG_EIP) != tables.SENTINEL:
            raise RuntimeError(f'{address:#x} did not return ({self.stop})')
        return uc.reg_read(UC_X86_REG_EAX)

    def write_item(self, obj, it):
        uc = self.uc
        uc.mem_write(obj+0x10, struct.pack('<i', it.code))
        uc.mem_write(obj+0x14, struct.pack('<i', it.level << 3))
        uc.mem_write(obj+0x38, bytes([it.durability, it.max_durability]))
        uc.mem_write(obj+0x3b, bytes([it.set_bits]))
        uc.mem_write(obj+0x3d, bytes([it.special_count]))
        uc.mem_write(obj+0x3e, struct.pack('<8H', *it.special))
        uc.mem_write(obj+0x4e, struct.pack('<8H', *it.special_value))
        uc.mem_write(obj+0x60, struct.pack('<H', it.skill))
        uc.mem_write(obj+0x72, bytes([it.flag_72, *it.slot_73, it.socket_count, *it.socket, *it.socket_level]))
        uc.mem_write(obj+0x92, bytes([it.period, it.expired]))
        uc.mem_write(obj+0x98, bytes([it.excellent, *it.excellent_options]))
        uc.mem_write(obj+0xe8, struct.pack('<i', it.harmony))

    def set_case(self, world, flag, pet):
        uc = self.uc
        uc.mem_write(CURRENT_WORLD, struct.pack('<i', world))
        uc.mem_write(self.singleton+4, bytes([flag]))
        uc.mem_write(self.pet_record, struct.pack('<i', pet[0]))
        self.sell_flag, self.pet = flag, pet

    def set_seeds(self, seeds):
        for i, seed in enumerate(seeds):
            self.uc.mem_write(SOCKET_MANAGER+0x68+i*0xa8+4, struct.pack('<i', seed))


def random_item(rng, code, sphere_ids):
    it = Item()
    it.code = code
    it.level = rng.randrange(16)
    it.durability = rng.choice([0, 1, rng.randrange(256), 255, rng.randrange(1, 40)])
    it.max_durability = rng.choice([0, it.durability, rng.randrange(256), 255, min(255, it.durability+rng.randrange(1, 50))])
    it.set_bits = rng.choice([0, 0, 0x01, 0x04, 0x10, 0x20, rng.randrange(256)])
    it.special_count = rng.choice([0, 0, 1, 2, 3, rng.randrange(9)])
    for i in range(8):
        it.special[i] = rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, rng.randrange(20)])
        it.special_value[i] = rng.choice([1, 2, 3, 4, 5, 8, 10, 12, 15, 16, 20, rng.randrange(40), rng.randrange(1 << 16)])
    it.skill = rng.choice(SKILLS)
    it.flag_72 = rng.choice([0, 0, 1, 2])
    for i in range(5):
        it.slot_73[i] = rng.choice([0xff, rng.randrange(256)])
    it.socket_count = rng.choice([0, 0, 1, 2, 3, 5])
    for i in range(5):
        it.socket[i] = rng.choice([0xff] + sphere_ids) if sphere_ids else 0xff
        it.socket_level[i] = rng.randrange(1, 11)
    it.period, it.expired = rng.choice([(0, 0), (1, 0), (1, 1), (0, 1)])
    it.excellent = rng.choice([0, 0, 1, 2])
    n = rng.choice([0, 0, 1, 2, 4, 9])
    for i in range(9):
        it.excellent_options[i] = rng.randrange(255) if i < n else 0xff
    rng.shuffle(it.excellent_options)
    it.harmony = rng.choice([0, 0, 0, rng.randrange(16), rng.randrange(-5, 70000)])
    return it


def socket_setup(rng, records):
    """A seed table whose (seed, level) codes exist in Item.bmd; returns seeds and usable socket ids."""
    seeds = [rng.randrange(1, 7) for _ in range(256)]
    usable = []
    for sid in range(256):
        seed = seeds[sid]-1
        ok = all((((lv-1-(5 if lv > 5 else 0))*6 + (0x1937 if lv > 5 else 0x1864) + seed) in records)
                 for lv in range(1, 11))
        if ok:
            usable.append(sid)
    return seeds, usable[:40]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--evidence', type=Path, default=ROOT/'evidence')
    parser.add_argument('--game-root', type=Path, default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--library', type=Path, default=ROOT/f'reconstructed/price/libitemprice.{SUFFIX}')
    parser.add_argument('--cases-per-code', type=int, default=16, help='random states per installed code (x3 goldTypes)')
    parser.add_argument('--synthetic', type=int, default=2000)
    parser.add_argument('--repair', type=int, default=20000, help='extra random ConvertRepairGold cases')
    parser.add_argument('--limit', type=int, default=0, help='only the first N installed codes')
    parser.add_argument('--seed', type=int, default=0x5052)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    started = time.time()
    ev = args.evidence
    text = tables.load_pinned(ev/'x86-text-capture-09/client-text.bin', tables.TEXT_BYTES, tables.TEXT_SHA256,
                              'restored text')
    data = tables.load_pinned(ev/'image-data-run10/data-capture-10/client-image-data.bin', tables.DATA_BYTES,
                              tables.DATA_SHA256, 'second image section')
    feature = tables.load_pinned(ev/'image-data-run10/math-capture-10/cpu-features.bin', 4, tables.FEATURE_SHA256,
                                 'CPU feature word')
    if not args.game_root:
        raise SystemExit('--game-root or MU_GAME_ROOT is required')
    bodies = {}
    for name, (start, end, digest) in BODIES.items():
        actual = hashlib.sha256(text[start-tables.TEXT_BASE:end-tables.TEXT_BASE]).hexdigest()
        if actual != digest:
            raise ValueError(f'captured {name} body does not match its pinned digest')
        bodies[name] = {'start': hex(start), 'end_exclusive': hex(end), 'sha256': actual}
    item_file = next(p for p in (Path(args.game_root)/'Data/Local').iterdir() if p.name.lower() == 'item.bmd')
    image = item_file.read_bytes()
    count = struct.unpack_from('<I', image, 0)[0]
    records = {}
    for index in range(count):
        record = bytes(b ^ tables.KEY3[i % 3] for i, b in enumerate(image[4+708*index:4+708*(index+1)]))
        records.setdefault(struct.unpack_from('<i', record, 0)[0], record)
    codes = sorted(records)
    if args.limit:
        codes = codes[:args.limit]

    machine = tables.Machine(text, data, feature)
    client = Client(machine, image)
    manager = client.allocate(0x1000)
    client.call(models.MANAGER_CTOR, [], ecx=manager)
    path = client.allocate(32)
    machine.uc.mem_write(path, b'Data\\Local\\Item.bmd\0')
    client.call(models.ITEM_LOADER, [path], ecx=manager)
    client.manager = manager
    item = client.new_item()
    scratch = client.allocate(0x400)

    rng = random.Random(args.seed)
    seeds, sphere_ids = socket_setup(rng, records)
    client.set_seeds(seeds)
    soul = set(rng.sample(codes, min(40, len(codes)))) | {0x1c0d, 0x1a03}
    client.soul = soul

    cases = []   # (label, code, record or None (installed), Item, gt, world, flag, pet)

    def case_state():
        world = rng.choice([0, 0, 0x5c])
        flag = 1 if rng.random() < 0.05 else 0
        pet = (rng.choice([-1, 0, 1, 2]), rng.choice([0, 1, rng.randrange(1 << 32)]))
        return world, flag, pet

    for code in codes:
        for k in range(args.cases_per_code):
            it = random_item(rng, code, sphere_ids)
            it.level = k % 16
            for gt in (0, 1, 2):
                cases.append(('installed', code, None, it, gt) + case_state())
    for k in range(args.synthetic):
        record = bytearray(rng.randrange(256) for _ in range(708))
        code = rng.choice(SPECIAL_CODES + [rng.randrange(0, 0x2c00) for _ in range(20)])
        struct.pack_into('<i', record, 0, code)
        mode = k % 8
        if mode == 1:
            record[0x28c:0x290] = bytes(4)
        elif mode == 2:
            record[0x28c:0x290] = bytes(4)
            record[0x288] = 0
            record[0x250] = rng.choice([6, 9, 0xb, 0xc, 0x17, 0x18, 0x19, 0x1a, 0x1c, 0x20, 0x22, 0x2d, 0x2e, 0x2f, 0x38,
                                        0x39, 0x3a, 0xe, 0x21])
        elif mode == 3:
            record[0x28c:0x290] = bytes(4)
            record[0x288] = 0
            record[0x251] = rng.choice([0, 0x16, 0x2b, 0x2c, 0x5c, 0x64])
            record[0x252] = rng.choice([0, 2, 4, 5])
        elif mode == 4:
            record[0x28c:0x290] = bytes(4)
            record[0x288] = rng.choice([0, 0, 1, 255])
            record[0x2af] = rng.choice([0, 0, 3])
            record[0x2b0] = record[0x2b1] = 0
        elif mode == 5:
            record[0x28c:0x290] = struct.pack('<i', rng.choice([1, 999, 1000, 150, -5, rng.randrange(1 << 31)]))
        elif mode == 6:
            record[0x28c:0x290] = bytes(4)
            record[0x288] = 0
            record[0x250], record[0x252] = 2, 2      # 0x00cd2175: the 1/2/3 ladder and gold / 100
            record[0x2af] = record[0x2b0] = record[0x2b1] = 0
        elif mode == 7:
            record[0x28c:0x290] = bytes(4)
            record[0x288] = 0
            record[0x250] = rng.choice([1, 2, 3, 4, 5, 6])
            record[0x251] = rng.randrange(0x20)
            record[0x252] = rng.choice([0, 1, 2, 3, 7])
            record[0x2ae], record[0x2af], record[0x2b0], record[0x2b1] = rng.choice([0, 1]), 0, 0, 0
        it = random_item(rng, code, sphere_ids)
        cases.append(('synthetic', code, bytes(record), it, rng.choice([0, 1, 2])) + case_state())

    def run(native, mutations_only=False):
        native.soul = soul
        for i, s in enumerate(seeds):
            native.seeds[i] = s
        mismatches, counts = [], {'installed': 0, 'synthetic': 0, 'repair_from_value': 0, 'repair_random': 0,
                                  'minus_one': 0, 'nonzero': 0}
        for label, code, record, it, gt, world, flag, pet in cases:
            if label == 'installed':
                client.bind(item, code)
                obj = item
                rec = records[code]
            else:
                machine.uc.mem_write(scratch, record)
                client.bind(item, code, scratch)
                obj, rec = item, record
            client.write_item(obj, it)
            client.set_case(world, flag, pet)
            got = ctypes.c_int32(client.call(ITEM_VALUE, [obj, gt])).value
            want = native.price(rec, it, gt, world, flag, pet)
            counts[label] += 1
            counts['minus_one'] += got == -1
            counts['nonzero'] += got not in (0, -1)
            if got != want:
                mismatches.append((label, 'item_value', hex(code), it.level, gt, world, flag, got, want))
                if mutations_only and len(mismatches) > 3:
                    return mismatches, counts
            if gt == 2 and got != -1 and it.durability < it.max_durability and got >= 0:
                window = (rng.randrange(2), rng.randrange(2), rng.randrange(2))
                client.windows = window
                machine.uc.mem_write(client.shop+0xb0, bytes([window[1]]))
                client.slots = [None, None, None]
                g2 = ctypes.c_int32(client.call(REPAIR_GOLD, [got, it.durability, it.max_durability, code & 0xffff,
                                                              client.text])).value
                w2 = native.repair(got, it.durability, it.max_durability, code, window + (0,))
                counts['repair_from_value'] += 1
                if g2 != w2:
                    mismatches.append((label, 'repair', hex(code), got, it.durability, it.max_durability, window, g2, w2))
        for k in range(args.repair):
            value = rng.choice([0, 1, 99, 100, 999, 1000, rng.randrange(1000), rng.randrange(1 << 20),
                                rng.randrange(1 << 31), 400000000, 400000001])
            maximum = rng.choice([0, 1, rng.randrange(256), 255])
            durability = rng.choice([0, maximum, rng.randrange(maximum+1), rng.randrange(256)])
            code = rng.choice([0x1a04, 0x1a05, 0x28f7, 0x2900, 0x1a06, rng.randrange(0x2c00)])
            window = (rng.randrange(2), rng.randrange(2), rng.randrange(2))
            client.windows = window
            machine.uc.mem_write(client.shop+0xb0, bytes([window[1]]))
            discount = 0
            client.slots = [None, None, None]
            if k % 3 == 0:   # equipped helpers: the modelled info manager gives the percent
                client.info_objects = {}
                for slot in range(3):
                    if rng.random() < 0.6:
                        obj = client.slot_objects[slot]
                        scode = rng.randrange(0x2c00)
                        dur, flag118 = rng.choice([0, 1, 5]), rng.choice([0, 1])
                        lv = rng.choice([0, 2, 5, 6, 7])
                        word6e = rng.choice([0, 1])
                        info = client.allocate(0x200)
                        kind = rng.choice([0xf, 0xf, 3])
                        table = [rng.randrange(0, 30) for _ in range(6)]
                        machine.uc.mem_write(info+0xc, bytes([kind]))
                        machine.uc.mem_write(info+0x110, struct.pack('<6i', *table))
                        if rng.random() < 0.85:
                            client.info_objects[scode] = info
                        machine.uc.mem_write(obj+0x10, struct.pack('<i', scode))
                        machine.uc.mem_write(obj+0x14, struct.pack('<i', lv << 3))
                        machine.uc.mem_write(obj+0x38, bytes([dur]))
                        machine.uc.mem_write(obj+0x6e, struct.pack('<H', word6e))
                        machine.uc.mem_write(obj+0x118, bytes([flag118]))
                        client.slots[slot] = True
                        if dur > 0 and flag118 and scode in client.info_objects and kind == 0xf and lv < 6:
                            v = table[lv]
                            if word6e == 0:
                                v = v + lv + 1
                            discount += v
            g2 = ctypes.c_int32(client.call(REPAIR_GOLD, [value, durability, maximum, code & 0xffff,
                                                          client.text])).value
            w2 = native.repair(value, durability, maximum, code, window + (discount,))
            counts['repair_random'] += 1
            if g2 != w2:
                mismatches.append(('random', 'repair', value, durability, maximum, hex(code), window, discount, g2, w2))
                if mutations_only and len(mismatches) > 3:
                    return mismatches, counts
        return mismatches, counts

    native = Native(args.library, records)
    mismatches, counts = run(native)
    report = {'item_file_sha256': hashlib.sha256(image).hexdigest(), 'records': count, 'codes': len(codes),
              'bodies': bodies, 'cases': counts, 'mismatch_count': len(mismatches), 'mismatches': mismatches[:20],
              'coverage': dict(client.coverage), 'socket_ids': len(sphere_ids), 'seconds': round(time.time()-started, 1)}
    if args.mutations:
        detected = {}
        for n in (1, 2, 3, 4, 5):
            lib = ROOT/f'reconstructed/price/mutant{n}.{SUFFIX}'
            subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/price'), lib.name], check=True)
            found, _ = run(Native(lib, records), mutations_only=True)
            detected[n] = len(found)
            lib.unlink()
        report['mutations'] = detected
        report['mutations_detected'] = sum(1 for v in detected.values() if v)
    report['seconds'] = round(time.time()-started, 1)
    client.close()
    print(json.dumps({k: v for k, v in report.items() if k not in ('mismatches', 'bodies')}))
    if mismatches:
        print(json.dumps(mismatches[:10]))
    if args.output:
        args.output.write_text(json.dumps(report, indent=1)+'\n')
    ok = not mismatches and (not args.mutations or report['mutations_detected'] == 5)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
