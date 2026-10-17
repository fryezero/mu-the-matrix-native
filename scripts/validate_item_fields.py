#!/usr/bin/env python3
"""Validate the Item.bmd attribute accessors against the client (NATIVE-DATA-002).

Actual client code runs in Unicorn over the pinned restored text. Only the
CRT file/heap calls and the item-script singleton accessor are modelled (as in
scripts/validate_item_models.py):

1. the item-script manager constructor and the Item.bmd loader insert every
   installed record through the real container code;
2. per item code, the getters 0x00cd5de8 (kind A) and 0x00cd5dba (kind B) and
   the code predicate 0x00cd6017 (kind B equals k) run, including absent codes;
3. item objects are built by the client constructor 0x00ccbaa2 and bound to
   their record by the client's 0x00ccc51e (installed codes) or by writing the
   record pointer at +0 (synthetic records). On them run the object
   predicates 0x0095fc2e (kind A), 0x00987982 (kind B), 0x0095fbeb (type),
   the ItemConvert prefix 0x00cce06c..0x00cce1a3 (the copy of eleven
   record fields into the object), the maximum durability routine 0x00ccc5b0
   for item levels 0..15 with plain/excellent/ancient/both options, and the
   warehouse and repair predicates 0x016bec14 / 0x016be1d9 over levels and
   period/expired states.

Each observed value is compared with the authored C in
reconstructed/data/item_attributes.c (mu_item_attributes_read,
mu_item_max_durability, mu_item_store_ban, mu_item_repair_ban), called via
ctypes. Synthetic records with random bytes and forced kinds, types and
special codes are mutation cases. Decoded game data is never written; the
report holds counts, digests and the first mismatches.
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
import sys

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tables = load_module('validate_data_tables', ROOT/'scripts/validate_data_tables.py')
models = load_module('validate_item_models', ROOT/'scripts/validate_item_models.py')

GET_KIND_A, GET_KIND_B, HAS_KIND_B = 0x00cd5de8, 0x00cd5dba, 0x00cd6017
IS_KIND_A, IS_KIND_B, IS_TYPE = 0x0095fc2e, 0x00987982, 0x0095fbeb
ITEM_CTOR, SET_SCRIPT = 0x00ccbaa2, 0x00ccc51e
CONVERT, CONVERT_STOP = 0x00cce06c, 0x00cce1a3
MAX_DURABILITY, STORE_BAN, REPAIR_BAN = 0x00ccc5b0, 0x016bec14, 0x016be1d9
BODIES = {  # start, exclusive end, SHA-256 of the captured bytes (checked before use)
    'get_kind_a': (0x00cd5de8, 0x00cd5e16, '30c25f2982676212a8ed265ad1529e2cf3b77f0cd835cf7a7d8f0b332a9eda17'),
    'get_kind_b': (0x00cd5dba, 0x00cd5de8, 'bda30f46a306c451255e7460c191503df53f79a138a6f9ad761afae4eb5bc073'),
    'has_kind_b': (0x00cd6017, 0x00cd605f, 'b294148585c1193b312296cffd742d3950679814b3b3d27ed11aa918c3b083e4'),
    'is_kind_a': (0x0095fc2e, 0x0095fc71, '32cd25d654a8ee876f25ca3bd946d092bf037a61d6803345a0e5068b34c26687'),
    'is_kind_b': (0x00987982, 0x009879c5, '851aabd9d6a270265bf58df7a930ff613f695aec4649772432e9d5f379c3353b'),
    'is_type': (0x0095fbeb, 0x0095fc2e, '53def2c614734425d24cef92dd315fe1d9dce48780c2fcfdb3e9cc114fd1a0fd'),
    'item_option': (0x00cd0995, 0x00cd0a10, '1eea26759c2d993e26da97fa24a45eac9e42c6c9e01810773cd40604f5070eca'),
    'get_script': (0x00ccc591, 0x00ccc5b0, 'a5f1c28d51949e6f8f2d53ff2794012eb52f665c70ca5ea2f77c485e2884e61b'),
    'set_script': (0x00ccc51e, 0x00ccc591, '9b9dff6e3519977a3c4c2f648588b740f69faa93bd55f8947c0f7634a0ddbe08'),
    'special_durability': (0x00cd2326, 0x00cd2386, '1dfc0c908c86359520568a58d14e1267a4079475a2a8c7e4391b16ed94e9f972'),
    'max_durability': (0x00ccc5b0, 0x00ccc884, '8ee34b2565d0b713b6d1a1e3ec95d5882350f173d23e74b7825db4d5d9a63ff5'),
    'store_ban': (0x016bec14, 0x016bec9f, 'b5b1db6e7d6ab3e7f0a8ec612adb2bc1d3fd549d75cf576be8b5ca1beecf9ddc'),
    'repair_ban': (0x016be1d9, 0x016be26c, '893b47e94d3fa24dd41c9aaaf31ec55b8394ad386dfdbe378e10b732a3c94f10'),
    'sub_has_option': (0x00cbc2e6, 0x00cbc310, 'e41330dc6de15c41b0228afad2de01825dd8f6e9a65d6c09258892340aafc967'),
    'item_convert_prefix': (0x00cce06c, 0x00cce1a3, 'ba42a4fd9f3ad0fee85380ca19ac50be40d5264bce2515251c131ba474f0a976'),
}
# ItemConvert prefix: object offset, width, attribute name
CONVERT_COPIES = [(0x1a, 1, 'two_handed'), (0x34, 1, 'attack_speed'), (0x1c, 2, 'damage_min'),
                  (0x1e, 2, 'damage_max'), (0x20, 2, 'defense_rate'), (0x22, 2, 'defense'),
                  (0x24, 2, 'magic_defense'), (0x36, 2, 'walk_speed'), (0x28, 4, 'magic_power'),
                  (0x2c, 4, 'combat_power'), (0x30, 4, 'attack_success_rate')]
OPTION_STATES = [(0, 0), (1, 0), (0, 1), (1, 1)]   # (excellent, ancient)
BAN_STATES = [(0, 0), (1, 0), (1, 1), (0, 1)]      # (period, expired)
BAN_LEVELS = [0, 3, 13, 15]
STAFF_KINDS = [0x0c, 0x0d, 0x0e, 0x4e, 0x54, 0x59, 0x5a, 0x72, 0x73]
SPECIAL_CODES = [0x1a04, 0x1a05, 0x28f7, 0x28f8, 0x28f9, 0x28fa, 0x2900, 0x1a14, 0x1c0b, 0x1c15, 0x2c00, 0x2c01]


class Attributes(ctypes.Structure):
    _fields_ = [('code', ctypes.c_uint32), ('section', ctypes.c_uint16), ('index', ctypes.c_uint16)] + [
        (n, t) for n, t in [
            ('kind_a', ctypes.c_uint8), ('kind_b', ctypes.c_uint8), ('type', ctypes.c_uint8),
            ('two_handed', ctypes.c_uint8), ('level', ctypes.c_uint16), ('slot', ctypes.c_uint8),
            ('skill', ctypes.c_uint16), ('width', ctypes.c_uint8), ('height', ctypes.c_uint8),
            ('damage_min', ctypes.c_uint16), ('damage_max', ctypes.c_uint16), ('defense_rate', ctypes.c_uint8),
            ('defense', ctypes.c_uint16), ('magic_defense', ctypes.c_uint16), ('attack_speed', ctypes.c_uint8),
            ('walk_speed', ctypes.c_uint8), ('durability', ctypes.c_uint8), ('set_defense_tier', ctypes.c_uint16),
            ('magic_durability', ctypes.c_uint8), ('magic_power', ctypes.c_uint32),
            ('combat_power', ctypes.c_uint32), ('attack_success_rate', ctypes.c_uint32),
            ('require_strength', ctypes.c_uint16), ('require_dexterity', ctypes.c_uint16),
            ('require_energy', ctypes.c_uint16), ('require_vitality', ctypes.c_uint16),
            ('require_command', ctypes.c_uint16), ('require_level', ctypes.c_uint16), ('value', ctypes.c_uint8),
            ('zen', ctypes.c_uint32), ('set_attribute', ctypes.c_uint8), ('require_class', ctypes.c_uint8*16),
            ('resistance', ctypes.c_uint8*7), ('can_drop', ctypes.c_uint8), ('can_trade', ctypes.c_uint8),
            ('can_personal_store', ctypes.c_uint8), ('can_warehouse', ctypes.c_uint8), ('can_sell', ctypes.c_uint8),
            ('high_value', ctypes.c_uint8), ('can_repair', ctypes.c_uint8), ('max_stack', ctypes.c_uint8),
            ('pc_room', ctypes.c_uint8), ('evolved_pet', ctypes.c_uint8), ('stat_option_melee', ctypes.c_uint16),
            ('stat_option_ranged', ctypes.c_uint16), ('stat_option_magic', ctypes.c_uint16),
            ('pentagram_grade', ctypes.c_uint8), ('field_2b9', ctypes.c_uint8), ('field_2ba', ctypes.c_uint8),
            ('elemental_attack', ctypes.c_uint16), ('elemental_defense_bonus', ctypes.c_uint16),
            ('elemental_defense', ctypes.c_uint16)]]


class State(ctypes.Structure):
    _fields_ = [('code', ctypes.c_int32), ('level', ctypes.c_int32), ('ancient', ctypes.c_uint8),
                ('period', ctypes.c_uint8), ('expired', ctypes.c_uint8), ('excellent', ctypes.c_uint8)]


class Native:
    def __init__(self, library):
        lib = self.lib = ctypes.CDLL(str(library))
        lib.mu_item_attributes_read.argtypes = [ctypes.c_char_p, ctypes.POINTER(Attributes)]
        for name in ('mu_item_max_durability', 'mu_item_store_ban', 'mu_item_repair_ban'):
            getattr(lib, name).argtypes = [ctypes.POINTER(Attributes), ctypes.POINTER(State)]
            getattr(lib, name).restype = ctypes.c_int

    def attributes(self, record):
        out = Attributes()
        self.lib.mu_item_attributes_read(bytes(record), ctypes.byref(out))
        return out

    def derived(self, name, attributes, code, level=0, excellent=0, ancient=0, period=0, expired=0):
        state = State(code, level, 0x01 if ancient else 0, period, expired, excellent)
        return getattr(self.lib, name)(ctypes.byref(attributes), ctypes.byref(state)) & 0xff


class Client(models.Runner):
    """Runner with item objects and a stop-address call."""

    def call_until(self, address, stop, ecx):
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_EIP
        hit = []

        def halt(uc, at, size, ignored):
            hit.append(at)
            uc.emu_stop()
        hook = self.uc.hook_add(UC_HOOK_CODE, halt, begin=stop, end=stop)
        try:
            from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_ECX
            uc = self.uc
            uc.context_restore(self.machine.snapshot)
            esp = tables.STACK+tables.STACK_BYTES-0x2000
            uc.mem_write(esp, struct.pack('<I', tables.SENTINEL))
            uc.reg_write(UC_X86_REG_ESP, esp)
            uc.reg_write(UC_X86_REG_EBP, 0)
            uc.reg_write(UC_X86_REG_ECX, ecx)
            uc.emu_start(address, tables.SENTINEL, count=1_000_000)
            if not hit or uc.reg_read(UC_X86_REG_EIP) != stop:
                raise RuntimeError(f'{address:#x} did not reach {stop:#x} ({self.stop})')
        finally:
            self.uc.hook_del(hook)

    def new_item(self):
        item = self.allocate(0x400)
        self.call(ITEM_CTOR, [], ecx=item)
        return item

    def bind(self, item, code, record=None, level=0, excellent=0, ancient=0, period=0, expired=0):
        uc = self.uc
        uc.mem_write(item+0x10, struct.pack('<i', code))
        uc.mem_write(item+0x14, struct.pack('<i', level << 3))
        uc.mem_write(item+0x3b, bytes([0x01 if ancient else 0]))
        uc.mem_write(item+0x92, bytes([period, expired]))
        uc.mem_write(item+0x98, bytes([excellent]))
        if record is None:
            uc.mem_write(item, bytes(4))
            self.call(SET_SCRIPT, [], ecx=item)
        else:
            uc.mem_write(item, struct.pack('<I', record))

    def read(self, address, width):
        return int.from_bytes(bytes(self.uc.mem_read(address, width)), 'little')


def compare_object(client, native, item, attributes, code, label, mismatches, counts):
    """Predicates, ItemConvert copies, max durability and bans for one bound object."""
    a = attributes
    in_range = 0 <= code <= 0x2c00
    for routine, value, name in ((IS_KIND_A, a.kind_a, 'is_kind_a'), (IS_KIND_B, a.kind_b, 'is_kind_b'),
                                 (IS_TYPE, a.type, 'is_type')):
        for probe in (value, value ^ 1):
            got = client.call(routine, [probe], ecx=item) & 0xff
            want = int(in_range and probe == value)
            counts['predicates'] += 1
            if got != want:
                mismatches.append((label, name, code, probe, got, want))
    client.bind(item, code, client.read(item, 4))
    client.call_until(CONVERT, CONVERT_STOP, item)
    for offset, width, name in CONVERT_COPIES:
        counts['convert_fields'] += 1
        got, want = client.read(item+offset, width), getattr(a, name)
        if got != want:
            mismatches.append((label, 'convert', code, name, got, want))
    record = client.read(item, 4)
    for level in range(16):
        for excellent, ancient in OPTION_STATES:
            client.bind(item, code, record, level, excellent, ancient)
            client.call(MAX_DURABILITY, [], ecx=item)
            got = client.read(item+0x39, 1)
            want = native.derived('mu_item_max_durability', a, code, level, excellent, ancient)
            counts['max_durability'] += 1
            if got != want:
                mismatches.append((label, 'max_durability', code, level, excellent, ancient, got, want))
    for level in BAN_LEVELS:
        for period, expired in BAN_STATES:
            client.bind(item, code, record, level, period=period, expired=expired)
            for routine, name in ((STORE_BAN, 'mu_item_store_ban'), (REPAIR_BAN, 'mu_item_repair_ban')):
                got = client.call(routine, [item]) & 0xff
                want = native.derived(name, a, code, level, period=period, expired=expired)
                counts['bans'] += 1
                if got != want:
                    mismatches.append((label, name, code, level, period, expired, got, want))


def synthetic_records(count, seed=0x4e44):
    rng = random.Random(seed)
    out = []
    for i in range(count):
        record = bytearray(rng.randrange(256) for _ in range(708))
        code = rng.choice(SPECIAL_CODES + [rng.randrange(0, 0x2c00) for _ in range(6)] + [-5, 0x7fffffff])
        struct.pack_into('<i', record, 0, code)
        mode = i % 6
        if mode == 1:
            record[0x251] = rng.choice(STAFF_KINDS)
        elif mode == 2:
            record[0x251] = rng.choice([0x2b, 0x79])
        elif mode == 3:
            record[0x252] = 4
        elif mode == 4:
            record[0x268] = rng.choice([0, 1, 0xf0, 0xff])
            record[0x26c] = rng.choice([0, 0xfe, 0xff])
        out.append((code, bytes(record)))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, default=ROOT/'evidence/x86-text-capture-09/client-text.bin')
    parser.add_argument('--data', type=Path, default=ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin')
    parser.add_argument('--feature', type=Path, default=ROOT/'evidence/image-data-run10/math-capture-10/cpu-features.bin')
    parser.add_argument('--game-root', type=Path, default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--library', type=Path, default=ROOT/'reconstructed/data'/(
        'libdatatables.dylib' if sys.platform == 'darwin' else 'libdatatables.so'))
    parser.add_argument('--synthetic', type=int, default=300)
    parser.add_argument('--limit', type=int, default=0, help='check only the first N installed codes (0 = all)')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = tables.load_pinned(args.text, tables.TEXT_BYTES, tables.TEXT_SHA256, 'restored text')
    data = tables.load_pinned(args.data, tables.DATA_BYTES, tables.DATA_SHA256, 'second image section')
    feature = tables.load_pinned(args.feature, 4, tables.FEATURE_SHA256, 'CPU feature word')
    if not args.game_root:
        raise SystemExit('--game-root or MU_GAME_ROOT is required')
    bodies = {}
    for name, (start, end, digest) in BODIES.items():
        actual = hashlib.sha256(text[start-tables.TEXT_BASE:end-tables.TEXT_BASE]).hexdigest()
        if actual != digest:
            raise ValueError(f'captured {name} body does not match its pinned digest')
        bodies[name] = {'start': hex(start), 'end_exclusive': hex(end), 'sha256': actual}
    native = Native(args.library)
    item_file = next(p for p in (Path(args.game_root)/'Data/Local').iterdir() if p.name.lower() == 'item.bmd')
    image = item_file.read_bytes()
    machine = tables.Machine(text, data, feature)
    client = Client(machine, image)
    manager = client.allocate(0x1000)
    client.call(models.MANAGER_CTOR, [], ecx=manager)
    path = client.allocate(32)
    machine.uc.mem_write(path, b'Data\\Local\\Item.bmd\0')
    client.call(models.ITEM_LOADER, [path], ecx=manager)
    client.manager = manager

    count = struct.unpack_from('<I', image, 0)[0]
    records = {}
    for index in range(count):
        record = bytes(b ^ tables.KEY3[i % 3] for i, b in enumerate(image[4+708*index:4+708*(index+1)]))
        records.setdefault(struct.unpack_from('<I', record, 0)[0], record)  # std::map keeps the first
    codes = sorted(records)
    if args.limit:
        codes = codes[:args.limit]
    mismatches = []
    counts = {'getters': 0, 'predicates': 0, 'convert_fields': 0, 'max_durability': 0, 'bans': 0}
    for code in codes + [0x7ffffff0, 0xffffffff]:
        a = native.attributes(records[code]) if code in records else None
        for routine, name in ((GET_KIND_A, 'kind_a'), (GET_KIND_B, 'kind_b')):
            got = client.call(routine, [code], ecx=manager) & 0xff
            want = getattr(a, name) if a else 0
            counts['getters'] += 1
            if got != want:
                mismatches.append(('installed', name, code, got, want))
        if a:
            for probe in (a.kind_b, a.kind_b ^ 1):
                got = client.call(HAS_KIND_B, [code, probe], ecx=manager) & 0xff
                want = int(code <= 0x2c00 and probe == a.kind_b)
                counts['getters'] += 1
                if got != want:
                    mismatches.append(('installed', 'has_kind_b', code, probe, got, want))
    item = client.new_item()
    for code in codes:
        client.bind(item, code)
        if client.read(item, 4) == 0:
            mismatches.append(('installed', 'set_script', code))
            continue
        compare_object(client, native, item, native.attributes(records[code]), code, 'installed', mismatches, counts)
    installed_counts = dict(counts)
    scratch = client.allocate(0x400)
    for code, record in synthetic_records(args.synthetic):
        machine.uc.mem_write(scratch, record)
        client.bind(item, code, scratch)
        compare_object(client, native, item, native.attributes(record), code, 'synthetic', mismatches, counts)
    client.close()
    report = {'item_file_sha256': hashlib.sha256(image).hexdigest(), 'records': count, 'codes': len(codes),
              'bodies': bodies, 'installed_checks': installed_counts,
              'synthetic_records': args.synthetic,
              'all_checks': counts, 'mismatch_count': len(mismatches), 'mismatches': mismatches[:20]}
    print(json.dumps({k: v for k, v in report.items() if k not in ('mismatches', 'bodies')}))
    if mismatches:
        print(json.dumps(mismatches[:8]))
    if args.output:
        args.output.write_text(json.dumps(report, indent=1)+'\n')
    return 0 if not mismatches else 1


if __name__ == '__main__':
    sys.exit(main())
