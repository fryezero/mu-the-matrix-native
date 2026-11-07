#!/usr/bin/env python3
"""HERO-ITEMS-001: the hero's part slots from its equipment against the pinned client.

The client fills the hero's CHARACTER part slots (c + 0x1c4 + k * 0x3fc: +0 type word, +2 level, +3 option, +4 ext)
from CharacterMachine [0x01d1df18]'s equipped ITEM records (+0x1b58 + s * 0x12c) in SetCharacterClass 0x01394870.
reconstructed/hero-equipment reproduces it; the native world runtime feeds the hero's render from it. Families:

* set_class  0x01394870(c) on random equipment (codes -1 / in range / out of range / negative, random level words
             including negative ones, random +0x3b / +0x92 / +0x98 bytes, other ITEM bytes random), random class
             bytes, random prior slot bytes (so untouched fields are checked: wing/helper option and ext, slot 9),
             c + 0xe random and the model c + 0x32b0 mostly 0xa91 (other models: nothing written). All 11 slots'
             five bytes against the C.
* defaults   every class byte with an empty equipment: the class parts 0x3700 + 0x50 (k - 1) + skin and the head.
* head       every helm type 0x18d0..0x1a6f (and c + 0xe 0/1): 0x01394f6f's head slot.
* item_flag  0x00cd0995(item, mode) directly: modes -1..3, codes around the 0..0x2c00 bounds.
* record     APP-POLISH-008: the offline session's equipment records (code group*512+index, level 0..15, option
             0/1, ext 0..255; some slots empty) written as ITEMs by mu_he_item_of_record, then 0x01394870 on them:
             the client's slots equal the C's, and they hold the session's fields (hands and parts: code + 0xae6,
             level, option, ext; wing and helper: code + 0xae6 and level). The round trip is client-checked; the
             helper itself is not client code.

Stubbed (not slot writes, not reproduced): 0x009dadf1 (the castle worlds' weapon override), 0x0137ad93 (hero only),
0x00a00fb7 (the stat machine), and 0x01394f6f after its head store (0x013950ba: scale floats). 0x009dacb8 runs.

--mutations plants mistakes in reconstructed/hero-equipment/hero_equipment.c (compiled separately) and requires
each to be caught.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import random
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402
from validate_players import Character  # noqa: E402  (the shared CHARACTER slot view)

TEXT_BASE, DATA_BASE = 0x00401000, 0x01a7c000
SET_CLASS, ITEM_FLAG = 0x01394870, 0x00cd0995
STUBS = {0x009dadf1: b'\xc3', 0x0137ad93: b'\xc3', 0x00a00fb7: b'\xc3', 0x013950ba: b'\xc9\xc3'}
CM_PTR, HERO_PTR, WORLD = 0x01d1df18, 0x0a39d754, 0x01cf15fc
SLOT_BASE, SLOT_STRIDE, SLOTS = 0x1c4, 0x3fc, 11
EQUIP_BASE, ITEM_STRIDE, EQUIP = 0x1b58, 0x12c, 9
HEAD_HELMS = (0x18e6, 0x18e8, 0x18f0, 0x18f1, 0x18f2, 0x18f3, 0x1925, 0x1927, 0x192a, 0x192c, 0x193d, 0x193e,
              0x193f, 0x19a0, 0x19a1, 0x1a35, 0x1a5f)
DIR = ROOT / 'reconstructed/hero-equipment'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
MUTANTS = {
    'level_shift': ('(item->level >> 3) & 0xf', '(item->level >> 4) & 0xf'),
    'level_mask': ('>> 3) & 0xf)', '>> 3) & 0x7)'),
    'model_base': ('item->type + MU_HE_MODEL_BASE', 'item->type + MU_HE_MODEL_BASE + 1'),
    'empty_test': ('item->type == -1 ? -1', 'item->type < 0 ? -1'),
    'flag_bound': ('item->type > 0x2c00', 'item->type >= 0x2c00'),
    'flag_mode': ('s->option = mu_he_item_flag(&e[h], 1)', 's->option = mu_he_item_flag(&e[h], 0)'),
    'flag98': ('item->flag_98 == 1', 'item->flag_98 != 0'),
    'wing_ext': ('c->slots[MU_RP_SLOT_WING].level = item_level(&e[MU_HE_WING]);',
                 'c->slots[MU_RP_SLOT_WING].level = item_level(&e[MU_HE_WING]); '
                 'c->slots[MU_RP_SLOT_WING].ext = e[MU_HE_WING].ancient;'),
    'part_stride': ('MU_HE_PART_STRIDE * (k - MU_RP_SLOT_HELM)', 'MU_HE_PART_STRIDE * (k - MU_RP_SLOT_HEAD)'),
    'head_list': ('case 0x1a5f:\n', ''),
    'head_flag': ('if (!c->byte_0e)', 'if (c->byte_0e != 1)'),
    'model_gate': ('if (c->model != MU_RP_PLAYER_MODEL)', 'if (c->model == 0)'),
    'helper_slot': ('c->slots[MU_RP_SLOT_HELPER].type = item_type(&e[MU_HE_HELPER]);',
                    'c->slots[MU_RP_SLOT_MUUN].type = item_type(&e[MU_HE_HELPER]);'),
    'swap_hands': ('c->slots[MU_RP_SLOT_WEAPON0].type = item_type(&e[MU_HE_RIGHT]);',
                   'c->slots[MU_RP_SLOT_WEAPON0].type = item_type(&e[MU_HE_LEFT]);'),
    # APP-POLISH-008: the session record -> ITEM fields
    'record_level': ('((level & 0xfu) << 3)', '((level & 0xfu) << 4)'),
    'record_option': ('.flag_98 = (uint8_t)(option != 0)', '.flag_98 = (uint8_t)(option + 1)'),
    'record_ext': ('.ancient = ext,', '.ancient = (uint8_t)(ext & 0x33),'),
    'record_code': ('.type = code,', '.type = code + 1,'),
}


class Item(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int32), ('level', ctypes.c_int32), ('ancient', ctypes.c_uint8),
                ('flag_92', ctypes.c_uint8), ('flag_98', ctypes.c_uint8)]


def build(source_dir: Path, work: Path, name: str):
    out = work / f'lib{name}.{SUFFIX}'
    result = subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-fPIC',
                             '-ffp-contract=off', '-fno-fast-math', '-shared', str(source_dir / 'hero_equipment.c'),
                             str(ROOT / 'reconstructed/players/remote_players.c'), '-I', str(ROOT / 'reconstructed'),
                             '-lm', '-o', str(out)], capture_output=True, text=True)
    if result.returncode:
        return None, result.stderr[-2000:]
    lib = ctypes.CDLL(str(out))
    lib.mu_he_set_character_class.argtypes = [ctypes.POINTER(Character), ctypes.POINTER(Item)]
    lib.mu_he_item_flag.argtypes = [ctypes.POINTER(Item), ctypes.c_int32]
    lib.mu_he_item_flag.restype = ctypes.c_uint8
    lib.mu_he_item_of_record.argtypes = [ctypes.c_int32, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8]
    lib.mu_he_item_of_record.restype = Item
    return lib, None


class Client:
    STACK, CHAR, CM, ITEM, SENTINEL = 0x20000000, 0x20100000, 0x20200000, 0x20300000, 0x20400ff0

    def __init__(self, text, data):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_ALL
        from unicorn import x86_const as x86
        self.x86 = x86
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, len(text), UC_PROT_ALL)
        uc.mem_write(TEXT_BASE, text)
        for address, code in STUBS.items():
            uc.mem_write(address, code)
        uc.mem_map(DATA_BASE, (len(data) + 0xfff) & ~0xfff, UC_PROT_ALL)
        uc.mem_write(DATA_BASE, data)
        for base, size in ((0x01cf1000, 0x1000), (0x01d1d000, 0x1000), (0x0a39d000, 0x1000), (self.STACK, 0x40000),
                           (self.CHAR, 0x4000), (self.CM, 0x4000), (self.ITEM, 0x1000), (0x20400000, 0x1000)):
            uc.mem_map(base, size, UC_PROT_ALL)
        uc.mem_write(CM_PTR, struct.pack('<I', self.CM))

    def call(self, start, args, ecx=0):
        x86, uc = self.x86, self.uc
        top = self.STACK + 0x3f000
        uc.mem_write(top, struct.pack('<I', self.SENTINEL) + b''.join(struct.pack('<I', a) for a in args))
        uc.reg_write(x86.UC_X86_REG_ESP, top)
        uc.reg_write(x86.UC_X86_REG_EBP, 0x13579bdf)
        uc.reg_write(x86.UC_X86_REG_ECX, ecx)
        uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        try:
            uc.emu_start(start, self.SENTINEL, timeout=0, count=100000)
        except Exception as failure:  # UcError
            return None, f'uc {failure} at {uc.reg_read(x86.UC_X86_REG_EIP):#x}'
        pc = uc.reg_read(x86.UC_X86_REG_EIP)
        return uc.reg_read(x86.UC_X86_REG_EAX), (None if pc == self.SENTINEL else f'stopped at {pc:#x}')

    def write_item(self, address, item, junk):
        self.uc.mem_write(address, junk)
        self.uc.mem_write(address + 0x10, struct.pack('<ii', item['type'], item['level']))
        self.uc.mem_write(address + 0x3b, bytes([item['ancient']]))
        self.uc.mem_write(address + 0x92, bytes([item['flag_92']]))
        self.uc.mem_write(address + 0x98, bytes([item['flag_98']]))

    def set_class(self, state, rng):
        uc = self.uc
        uc.mem_write(self.CHAR, bytes(rng.randrange(256) for _ in range(0x3400)))
        for k, slot in enumerate(state['slots']):
            uc.mem_write(self.CHAR + SLOT_BASE + k * SLOT_STRIDE, struct.pack('<hBBB', *slot))
        uc.mem_write(self.CHAR + 0x0e, bytes([state['byte_0e']]))
        uc.mem_write(self.CHAR + 0x12, bytes([state['class_byte']]))
        uc.mem_write(self.CHAR + 0x32b0, struct.pack('<i', state['model']))
        for s, item in enumerate(state['equipment']):
            self.write_item(self.CM + EQUIP_BASE + s * ITEM_STRIDE, item,
                            bytes(rng.randrange(256) for _ in range(ITEM_STRIDE)))
        uc.mem_write(WORLD, struct.pack('<i', state['world']))
        uc.mem_write(HERO_PTR, struct.pack('<I', self.CHAR if state['is_hero'] else 0x20101000))
        _, error = self.call(SET_CLASS, [self.CHAR])
        if error:
            return None, error
        return [struct.unpack('<hBBB', uc.mem_read(self.CHAR + SLOT_BASE + k * SLOT_STRIDE, 5)) for k in range(SLOTS)], None

    def item_flag(self, item, mode, rng):
        self.write_item(self.ITEM, item, bytes(rng.randrange(256) for _ in range(ITEM_STRIDE)))
        eax, error = self.call(ITEM_FLAG, [mode & 0xffffffff], ecx=self.ITEM)
        return (None if error else eax & 0xff), error


def c_set_class(lib, state):
    c = Character()
    c.model = state['model']
    c.class_byte = state['class_byte']
    c.byte_0e = state['byte_0e']
    for k, (t, lv, op, ex) in enumerate(state['slots']):
        c.slots[k].type, c.slots[k].level, c.slots[k].option, c.slots[k].ext = t, lv, op, ex
    items = (Item * EQUIP)(*[Item(i['type'], i['level'], i['ancient'], i['flag_92'], i['flag_98'])
                             for i in state['equipment']])
    lib.mu_he_set_character_class(ctypes.byref(c), items)
    return [(c.slots[k].type, c.slots[k].level, c.slots[k].option, c.slots[k].ext) for k in range(SLOTS)]


def random_code(rng):
    r = rng.random()
    if r < 0.3:
        return -1
    if r < 0.75:
        return rng.randrange(0, 0x2c01)
    return rng.choice([0, 0x2c00, 0x2c01, -2, -0xae6, 0x7fff - 0xae6, 0x8000, rng.randrange(-2**31, 2**31)])


def random_item(rng):
    return {'type': random_code(rng),
            'level': rng.choice([rng.randrange(16) << 3, rng.randrange(-2**31, 2**31), rng.randrange(256)]),
            'ancient': rng.randrange(256), 'flag_92': rng.choice([0, 1, 2, rng.randrange(256)]),
            'flag_98': rng.choice([0, 1, 2, rng.randrange(256)])}


def empty_item():
    return {'type': -1, 'level': 0, 'ancient': 0, 'flag_92': 0, 'flag_98': 0}


def random_state(rng):
    return {'equipment': [random_item(rng) for _ in range(EQUIP)],
            'slots': [(rng.randrange(-32768, 32768), rng.randrange(256), rng.randrange(256), rng.randrange(256))
                      for _ in range(SLOTS)],
            'class_byte': rng.randrange(256), 'byte_0e': 0 if rng.random() < 0.8 else rng.randrange(1, 256),
            'model': 0xa91 if rng.random() < 0.9 else rng.choice([0, 0xa92, 0x7d9, rng.randrange(2**31)]),
            'world': rng.choice([0, 2, 3, 0x12, 0x17, 0x35, 0x61, rng.randrange(256)]), 'is_hero': rng.random() < 0.5}


def compare(family, client, lib, state, rng):
    got, error = client.set_class(state, rng)
    want = c_set_class(lib, state)
    family['cases'] += 1
    if error or got != want:
        family['mismatches'] += 1
        if len(family['examples']) < 3:
            family['examples'].append({'error': error, 'client': got, 'c': want, 'class': state['class_byte']})


def record_expected(state, records):
    """The slots the session's fields must reach: hands and parts all four, wing and helper type and level."""
    want = {}
    for k, s in ((6, 0), (7, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (8, 7), (10, 8)):
        r = records[s]
        if r is None:
            continue
        code, level, option, ext = r
        prior = state['slots'][k]
        want[k] = (code + 0xae6, level, option, ext) if k not in (8, 10) else (code + 0xae6, level, prior[2], prior[3])
    return want


def record_case(family, client, lib, rng):
    state = random_state(rng)
    state.update(model=0xa91, byte_0e=0)
    records = []
    for s in range(EQUIP):
        if rng.random() < 0.2:
            records.append(None)
            state['equipment'][s] = empty_item()
            continue
        r = (rng.randrange(16) * 512 + rng.randrange(512), rng.randrange(16), rng.randrange(2), rng.randrange(256))
        records.append(r)
        item = lib.mu_he_item_of_record(*r)
        state['equipment'][s] = {'type': item.type, 'level': item.level, 'ancient': item.ancient,
                                 'flag_92': item.flag_92, 'flag_98': item.flag_98}
    got, error = client.set_class(state, rng)
    want = c_set_class(lib, state)
    expected = record_expected(state, records)
    family['cases'] += 1
    bad = error or got != want or any(got[k] != v for k, v in expected.items())
    if bad:
        family['mismatches'] += 1
        if len(family['examples']) < 3:
            family['examples'].append({'error': error, 'client': got, 'c': want, 'records': records})


def families(client, lib, cases, seed):
    rng = random.Random(seed)
    out = {name: {'cases': 0, 'mismatches': 0, 'examples': []}
           for name in ('set_class', 'defaults', 'head', 'item_flag', 'record')}
    for _ in range(cases):
        compare(out['set_class'], client, lib, random_state(rng), rng)
    for class_byte in range(256):
        state = random_state(rng)
        state.update(equipment=[empty_item() for _ in range(EQUIP)], class_byte=class_byte, byte_0e=0, model=0xa91)
        compare(out['defaults'], client, lib, state, rng)
    for helm in range(0x18d0, 0x1a70):
        for flag in (0, 1):
            state = random_state(rng)
            state['equipment'][2]['type'] = helm - 0xae6
            state.update(byte_0e=flag, model=0xa91)
            compare(out['head'], client, lib, state, rng)
    fam = out['item_flag']
    for _ in range(cases):
        item = random_item(rng)
        if rng.random() < 0.3:
            item['type'] = rng.choice([-1, 0, 1, 0x2bff, 0x2c00, 0x2c01])
        mode = rng.choice([-1, 0, 1, 2, 3, rng.randrange(-2**31, 2**31)])
        got, error = client.item_flag(item, mode, rng)
        c_item = Item(item['type'], item['level'], item['ancient'], item['flag_92'], item['flag_98'])
        want = lib.mu_he_item_flag(ctypes.byref(c_item), mode)
        fam['cases'] += 1
        if error or got != want:
            fam['mismatches'] += 1
            if len(fam['examples']) < 3:
                fam['examples'].append({'error': error, 'client': got, 'c': want, 'mode': mode, 'item': item})
    for _ in range(cases):
        record_case(out['record'], client, lib, rng)
    return out


def mutations(client, cases, seed, work):
    source = (DIR / 'hero_equipment.c').read_text()
    results = {}
    for name, (old, new) in MUTANTS.items():
        count = source.count(old)
        if count != 1:
            raise SystemExit(f'mutant {name}: anchor matches {count} times, expected exactly once')
        mdir = work / f'm_{name}'
        mdir.mkdir()
        (mdir / 'hero_equipment.c').write_text(source.replace(old, new))
        shutil.copy(DIR / 'hero_equipment.h', mdir / 'hero_equipment.h')
        # the header includes ../players/remote_players.h: give the copy the same neighbour
        (work / 'players').mkdir(exist_ok=True)
        shutil.copy(ROOT / 'reconstructed/players/remote_players.h', work / 'players/remote_players.h')
        lib, error = build(mdir, work, f'm_{name}')
        if lib is None:
            raise SystemExit(f'mutant {name} does not compile: {error}')
        fam = families(client, lib, cases, seed)
        results[name] = sum(f['mismatches'] for f in fam.values())
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=3000, help='set_class, item_flag and record cases')
    parser.add_argument('--seed', type=int, default=0x4e20)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--text')
    parser.add_argument('--data')
    args = parser.parse_args(argv)
    text = pins.TEXT.read(args.text, exit=True)
    data = pins.DATA.read(args.data, exit=True)
    client = Client(text, data)
    work = Path(tempfile.mkdtemp(prefix='hero-items-'))
    try:
        lib, error = build(DIR, work, 'hero_items')
        if lib is None:
            raise SystemExit(error)
        report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
                  'families': families(client, lib, args.cases, args.seed)}
        if args.mutations:
            report['mutants'] = mutations(client, max(300, args.cases // 4), args.seed, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + '\n')
    bad = sum(f['mismatches'] for f in report['families'].values())
    missed = [k for k, v in report.get('mutants', {}).items() if not v]
    summary = {k: {'cases': v['cases'], 'mismatches': v['mismatches']} for k, v in report['families'].items()}
    print(json.dumps({'families': summary, 'mutants': report.get('mutants')}))
    return 1 if bad or missed else 0


if __name__ == '__main__':
    sys.exit(main())
