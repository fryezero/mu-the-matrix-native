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

Stubbed in those five families (not slot writes there): 0x009dadf1 (the castle worlds' weapon override), 0x0137ad93
(hero only), 0x00a00fb7 (the stat machine), and 0x01394f6f after its head store (0x013950ba: scale floats).
0x009dacb8 runs.

HERO-ITEMS-002 runs 0x009dadf1 and 0x01394f6f unstubbed (only 0x0137ad93 and 0x00a00fb7 stay stubbed; the interface
calls 0x00f2bb92, 0x00f2bf8b, 0x009dc2f0, 0x009dc341, 0x011e042c, 0x009dc316, 0x011f4019 and the buff query
0x01295ade are answered by the host and logged):

* head_rows  the table: each of the 17 helms x every class byte, plus controls (the helms' neighbours, an empty
             helm slot, other helm types) for 16 class bytes. Per row: 0x01394870 complete, then RenderCharacter's
             body-part loop 0x0136a374..0x0136a8ef on the result. The head slot is 0x3700 + skin for a listed helm
             and -1 otherwise, and the loop's RenderPartObject 0x017e63f4 calls (slot record, model type, in
             order) equal the C's: the head is the last call for a listed helm and absent otherwise.
* castle     0x01394870 complete over the worlds -4..299 and random words, x 16 class nibbles: all 11 slots' five
             bytes, c + 0x16, the six part floats and the OBJECT scale (bit patterns), the host calls of the
             override (none outside 0x009dacb8's worlds) and the buff queries; and 0x009dadf1(c) directly on random
             prior slots (as ChangeCharacterExt calls it).
* scale      0x01394f6f(c) directly: every class byte x castle / other world x scenes 3..6 x the four buff answers,
             c + 0xe 0 and set, random prior floats and helm types: the seven floats, the head slot, the branch's
             buff queries (ids and order).
* part_loop  the body-part loop on random characters (slot types -1, item groups 7..11, class parts, others; every
             class nibble; actions 0xd1 / 0xdf / 0xdd and others; glow classes of 0x0139bcdc): the RenderPartObject
             calls against mu_he_part_draws, with the model types of class nibbles 4 (helm slot), 5 and 6; plus
             1,376 directed rows (the helms 0x18e6..0x18f1 in each slot of each class nibble; indices 0..15 of the
             groups 6..12 for class nibbles 5 and 6). Class nibble 6's action 0xdd (a second pass of the same part or
             0x00d2d3f9) is outside the domain.
* part_type  0x00d2ae8c on every type -0x400..0x3fff (class nibble 6's part models) against mu_he_part_draw_type.

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
# HERO-ITEMS-002: the complete routine; 0x009681bd returns a float in st0 (fldz; ret)
FULL_STUBS = {0x0137ad93: b'\xc3', 0x00a00fb7: b'\xc3', 0x009681bd: b'\xd9\xee\xc3'}
CASTLE_OVERRIDE, SCALE, PART_LOOP, PART_LOOP_END, RF_TYPE = 0x009dadf1, 0x01394f6f, 0x0136a374, 0x0136a8ef, 0x00d2ae8c
SCENE, OBJECT, PART_FLOAT, OBJECT_SCALE, BUFFS, UI_PTR = 0x01d1df70, 0x3254, 0x288, 0x32f4, 0x35ac, 0x06fc9eb0
# host calls: address -> stack bytes the callee removes
HOST = {0x00f2bb92: 0, 0x00f2bf8b: 0, 0x009dc2f0: 0, 0x009dc341: 12, 0x011e042c: 4, 0x009dc316: 0, 0x011f4019: 0,
        0x01295ade: 4, 0x00966cc4: 0, 0x00eaa8cf: 4, 0x017e63f4: 0, 0x016d5eb3: 0, 0x00d2d3f9: 16}
HOST_ARGS = {0x009dc341: 3, 0x011e042c: 1, 0x01295ade: 1, 0x00eaa8cf: 1, 0x017e63f4: 3}
CASTLE_WORLDS = (0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x35, 0x61)
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
# HERO-ITEMS-002: the castle override, the scale branches and the body-part loop (run against families2)
MUTANTS2 = {
    'castle_bound': ('(world >= 0x12 && world <= 0x17)', '(world >= 0x12 && world <= 0x16)'),
    'castle_world_61': ('world == 0x35 || world == 0x61', 'world == 0x35'),
    'castle_class': ('case 1: case 3: case 4: case 6: case 7: case 9: case 10: case 13: case 15:',
                     'case 1: case 3: case 4: case 6: case 7: case 9: case 10: case 15:'),
    'castle_bow': ('type[0] = 0x12f9;', 'type[0] = type[1] = 0x12f9;'),
    'castle_staff': ('type[0] = 0x14eb;', 'type[0] = 0x14ea;'),
    'castle_sword_left': ('type[0] = type[1] = 0x0af6;', 'type[0] = 0x0af6;'),
    'castle_option': ('        s->level = 0;\n        s->option = 0;\n', '        s->level = 0;\n'),
    'castle_byte_16': ('    c->byte_16 = 0;\n', ''),
    'castle_helper': ('    c->slots[MU_RP_SLOT_HELPER].level = 0;\n', ''),
    'castle_wing': ('    c->slots[MU_RP_SLOT_WING].type = -1;\n', ''),
    'castle_order': ('        mu_he_castle_override(c, in->world);   /* 0x01394f3a */\n', ''),
    'world_model_gate': ('if (c->model == MU_RP_PLAYER_MODEL) {   /* 0x01394879: only a Player model */',
                         'if (c->model != 0) {'),
    'scale_castle_elf': ('return nibble == 2 ? 0.88f : 0.9f;', 'return nibble == 3 ? 0.88f : 0.9f;'),
    'scale_castle_parts': ('        for (int k = 0; k < 6; ++k)\n            scale->part[k] = 0.0f;\n', ''),
    'scale_table': ('0.92f, 0.9f, 1.03f, 0.9f,', '0.92f, 0.9f, 1.0f, 0.9f,'),
    'scale_part_class': ('nibble == 11 && k == 1 ? 0.95f', 'nibble == 10 && k == 1 ? 0.95f'),
    'scale_part_slot': ('nibble == 11 && k == 1 ? 0.95f', 'nibble == 11 && k == 0 ? 0.95f'),
    'scale_scene': ('if (in->scene == 5) {', 'if (in->scene == 6) {'),
    'scale_buff_order': ('uint8_t buff = in->buff_1a8;   /* 0x013953aa */', 'uint8_t buff = in->buff_1a9;'),
    'scale_buff_value': ('        scale->object = 1.1f;\n        scale->branch = MU_HE_SCALE_BUFF;',
                         '        scale->object = 1.0f;\n        scale->branch = MU_HE_SCALE_BUFF;'),
    'scale_castle_buff': ('        scale->branch = MU_HE_SCALE_CASTLE;\n        return;\n',
                          '        scale->branch = MU_HE_SCALE_CASTLE;\n'),
    'scale_skip_head': ('    if (c->byte_0e) {   /* 0x01394f78 */', '    if (c->byte_0e == 1) {'),
    'loop_order': ('for (int32_t k = MU_RP_SLOT_BOOTS; k >= MU_RP_SLOT_HEAD; --k) {',
                   'for (int32_t k = MU_RP_SLOT_HEAD; k <= MU_RP_SLOT_BOOTS; ++k) {'),
    'loop_head': ('for (int32_t k = MU_RP_SLOT_BOOTS; k >= MU_RP_SLOT_HEAD; --k) {',
                  'for (int32_t k = MU_RP_SLOT_BOOTS; k >= MU_RP_SLOT_HELM; --k) {'),
    'loop_skip': ('if (c->slots[k].type == -1)   /* 0x0136a3b7 */', 'if (c->slots[k].type < 0)'),
    'loop_summoner': ('nibble == 5 && (index == 10 || index == 11)', 'nibble == 5 && (index == 9 || index == 11)'),
    'loop_summoner_base': ('return 0x36ce + index + 2 * group;', 'return 0x36ce + index + group;'),
    'loop_rf_group': ('4 * (group == 11 ? group - 1 : group)', '4 * group'),
    'loop_rf_list': ('static const int32_t list[4] = {5, 6, 8, 9};', 'static const int32_t list[4] = {5, 6, 7, 9};'),
    'loop_lord_slot': ('if (nibble == 4 && slot == MU_RP_SLOT_HELM) {', 'if (nibble == 4 && slot != MU_RP_SLOT_HEAD) {'),
    'loop_lord_list': ('if (d == 0 || d == 5 || d == 6 || d == 8 || d == 9)', 'if (d == 0 || d == 5 || d == 6 || d == 9)'),
    'loop_lord_base': ('return 0x38f6 + d;', 'return 0x38f5 + d;'),
    'loop_group_bound': ('    if (group < 7 || group > 11)\n        return slot_type;',
                         '    if (group < 7 || group > 10)\n        return slot_type;'),
}


class Item(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int32), ('level', ctypes.c_int32), ('ancient', ctypes.c_uint8),
                ('flag_92', ctypes.c_uint8), ('flag_98', ctypes.c_uint8)]


class ScaleIn(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('scene', ctypes.c_int32), ('buff_1a8', ctypes.c_uint8),
                ('buff_1a9', ctypes.c_uint8)]


class Scale(ctypes.Structure):
    _fields_ = [('part', ctypes.c_float * 6), ('object', ctypes.c_float), ('branch', ctypes.c_uint8),
                ('buff_queries', ctypes.c_uint8)]


class PartDraw(ctypes.Structure):
    _fields_ = [('slot', ctypes.c_int32), ('type', ctypes.c_int32)]


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
    lib.mu_he_castle_override.argtypes = [ctypes.POINTER(Character), ctypes.c_int32]
    lib.mu_he_castle_override.restype = ctypes.c_int
    lib.mu_he_character_scale.argtypes = [ctypes.POINTER(Character), ctypes.POINTER(ScaleIn), ctypes.POINTER(Scale)]
    lib.mu_he_set_character_class_world.argtypes = [ctypes.POINTER(Character), ctypes.POINTER(Item),
                                                    ctypes.POINTER(ScaleIn), ctypes.POINTER(Scale)]
    lib.mu_he_part_draw_type.argtypes = [ctypes.c_uint8, ctypes.c_int32, ctypes.c_int16]
    lib.mu_he_part_draw_type.restype = ctypes.c_int32
    lib.mu_he_part_draws.argtypes = [ctypes.POINTER(Character), ctypes.POINTER(PartDraw)]
    lib.mu_he_part_draws.restype = ctypes.c_int32
    return lib, None


class Client:
    STACK, CHAR, CM, ITEM, SENTINEL = 0x20000000, 0x20100000, 0x20200000, 0x20300000, 0x20400ff0

    MODEL = 0x20500000

    def __init__(self, text, data, full=False):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_ALL, UC_HOOK_CODE
        from unicorn import x86_const as x86
        self.x86 = x86
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, len(text), UC_PROT_ALL)
        uc.mem_write(TEXT_BASE, text)
        for address, code in (FULL_STUBS if full else STUBS).items():
            uc.mem_write(address, code)
        self.host, self.answers = [], {}
        if full:   # HERO-ITEMS-002: the host's calls are logged and answered
            for base, size in ((0x06fc9000, 0x1000), (0x06fce000, 0x1000), (self.MODEL, 0x1000)):
                uc.mem_map(base, size, UC_PROT_ALL)
            uc.mem_write(UI_PTR, struct.pack('<I', 0x20600000))
            for address in HOST:
                uc.hook_add(UC_HOOK_CODE, self._host, None, address, address)
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

    def _host(self, uc, address, size, user):
        x86 = self.x86
        esp = uc.reg_read(x86.UC_X86_REG_ESP)
        ret, = struct.unpack('<I', uc.mem_read(esp, 4))
        count = HOST_ARGS.get(address, 0)
        args = struct.unpack(f'<{count}I', uc.mem_read(esp + 4, 4 * count)) if count else ()
        self.host.append((address, uc.reg_read(x86.UC_X86_REG_ECX), args))
        answer = self.answers.get(address, 0x20700000 + (address & 0xfff0))
        if address == 0x00eaa8cf:   # GetModel: a model record per call
            answer = self.MODEL + 0x100 * (sum(1 for h in self.host if h[0] == address) % 16)
        if callable(answer):
            answer = answer(args)
        uc.reg_write(x86.UC_X86_REG_EAX, answer & 0xffffffff)
        uc.reg_write(x86.UC_X86_REG_ESP, esp + 4 + HOST[address])
        uc.reg_write(x86.UC_X86_REG_EIP, ret)

    def write_character(self, state, rng):
        uc = self.uc
        uc.mem_write(self.CHAR, rng.randbytes(0x3800))
        for k, slot in enumerate(state['slots']):
            uc.mem_write(self.CHAR + SLOT_BASE + k * SLOT_STRIDE, struct.pack('<hBBB', *slot))
        uc.mem_write(self.CHAR + 0x0e, bytes([state['byte_0e']]))
        uc.mem_write(self.CHAR + 0x12, bytes([state['class_byte']]))
        uc.mem_write(self.CHAR + 0x16, bytes([state.get('byte_16', 0)]))
        uc.mem_write(self.CHAR + 0x32b0, struct.pack('<i', state['model']))
        if 'floats' in state:
            for k in range(6):
                uc.mem_write(self.CHAR + PART_FLOAT + k * SLOT_STRIDE, struct.pack('<I', state['floats'][k]))
            uc.mem_write(self.CHAR + OBJECT_SCALE, struct.pack('<I', state['floats'][6]))
        uc.mem_write(WORLD, struct.pack('<i', state['world']))
        uc.mem_write(SCENE, struct.pack('<i', state.get('scene', 6)))
        self.host = []
        self.answers = {0x009dc2f0: state.get('window', 0), 0x011e042c: state.get('ui_flag', 0),
                        0x01295ade: lambda args: state.get('buff_1a8', 0) if args[0] == 0x1a8 else
                        state.get('buff_1a9', 0) if args[0] == 0x1a9 else 0x55}

    def read_character(self):
        uc = self.uc
        floats = [struct.unpack('<I', uc.mem_read(self.CHAR + PART_FLOAT + k * SLOT_STRIDE, 4))[0] for k in range(6)]
        floats.append(struct.unpack('<I', uc.mem_read(self.CHAR + OBJECT_SCALE, 4))[0])
        return {'slots': [struct.unpack('<hBBB', uc.mem_read(self.CHAR + SLOT_BASE + k * SLOT_STRIDE, 5))
                          for k in range(SLOTS)],
                'byte_16': uc.mem_read(self.CHAR + 0x16, 1)[0], 'floats': floats,
                'buffs': [(ecx - self.CHAR, args[0]) for a, ecx, args in self.host if a == 0x01295ade],
                'host': [(a, args) for a, ecx, args in self.host if a != 0x01295ade]}

    def full(self, state, rng, entry=SET_CLASS):
        """0x01394870 complete (or 0x009dadf1 / 0x01394f6f alone) on the state."""
        self.write_character(state, rng)
        if entry == SET_CLASS:
            for s, item in enumerate(state['equipment']):
                self.write_item(self.CM + EQUIP_BASE + s * ITEM_STRIDE, item, rng.randbytes(ITEM_STRIDE))
            self.uc.mem_write(HERO_PTR, struct.pack('<I', self.CHAR if state['is_hero'] else 0x20101000))
        _, error = self.call(entry, [self.CHAR])
        return (None, error) if error else (self.read_character(), None)

    def part_loop(self, state, rng, write=True):
        """RenderCharacter's body-part loop on the character: the RenderPartObject calls (slot, model type)."""
        x86, uc = self.x86, self.uc
        if write:
            self.write_character(state, rng)
        self.host = []
        uc.mem_write(self.CHAR + 0x146, struct.pack('<h', state.get('class_word', -1)))
        uc.mem_write(self.CHAR + 0x2c, bytes([state.get('byte_2c', 0)]))
        uc.mem_write(self.CHAR + OBJECT + 0x2a, struct.pack('<H', state.get('action', 0)))
        uc.mem_write(self.CHAR + OBJECT + 0x364, struct.pack('<h', state.get('word_364', -1)))
        ebp = self.STACK + 0x30000
        uc.mem_write(ebp + 8, struct.pack('<III', self.CHAR, self.CHAR + OBJECT, 0x20800000))
        uc.reg_write(x86.UC_X86_REG_EBP, ebp)
        uc.reg_write(x86.UC_X86_REG_ESP, ebp - 0x2000)
        uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        try:
            uc.emu_start(PART_LOOP, PART_LOOP_END, timeout=0, count=200000)
        except Exception as failure:  # UcError
            return None, f'uc {failure} at {uc.reg_read(x86.UC_X86_REG_EIP):#x}'
        pc = uc.reg_read(x86.UC_X86_REG_EIP)
        if pc != PART_LOOP_END:
            return None, f'stopped at {pc:#x}'
        if uc.reg_read(x86.UC_X86_REG_EBP) != ebp:
            return None, 'frame pointer changed'
        draws = []
        for address, ecx, args in self.host:
            if address != 0x017e63f4:
                continue
            if args[0] != self.CHAR + OBJECT:
                return None, f'RenderPartObject object {args[0]:#x}'
            offset = args[2] - self.CHAR - SLOT_BASE
            if offset % SLOT_STRIDE:
                return None, f'RenderPartObject slot record {args[2]:#x}'
            draws.append((offset // SLOT_STRIDE, args[1] - (1 << 32) if args[1] & 0x80000000 else args[1]))
        return draws, None

    def rf_type(self, value):
        eax, error = self.call(RF_TYPE, [value & 0xffffffff], ecx=0x01ec8db0)
        return (None if error else eax - (1 << 32) if eax & 0x80000000 else eax), error

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


# ---- HERO-ITEMS-002 ----

def c_character(state):
    c = Character()
    c.model = state['model']
    c.class_byte = state['class_byte']
    c.byte_0e = state['byte_0e']
    c.byte_16 = state.get('byte_16', 0)
    for k, (t, lv, op, ex) in enumerate(state['slots']):
        c.slots[k].type, c.slots[k].level, c.slots[k].option, c.slots[k].ext = t, lv, op, ex
    return c


def fbits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def c_full(lib, state, entry=SET_CLASS):
    """The C on the same state: slots, c + 0x16, the seven floats, the buff queries and whether the override ran."""
    c = c_character(state)
    inputs = ScaleIn(state['world'], state.get('scene', 6), state.get('buff_1a8', 0), state.get('buff_1a9', 0))
    scale = Scale()
    for k in range(6):
        scale.part[k] = struct.unpack('<f', struct.pack('<I', state['floats'][k]))[0]
    scale.object = struct.unpack('<f', struct.pack('<I', state['floats'][6]))[0]
    scale.branch, ran, queries = 0xff, 0, 0
    if entry == SET_CLASS:
        items = (Item * EQUIP)(*[Item(i['type'], i['level'], i['ancient'], i['flag_92'], i['flag_98'])
                                 for i in state['equipment']])
        lib.mu_he_set_character_class_world(ctypes.byref(c), items, ctypes.byref(inputs), ctypes.byref(scale))
        ran = int(state['model'] == 0xa91 and state['world'] in CASTLE_WORLDS)
        queries = scale.buff_queries if state['model'] == 0xa91 else 0
    elif entry == CASTLE_OVERRIDE:
        ran = lib.mu_he_castle_override(ctypes.byref(c), state['world'])
    else:
        lib.mu_he_character_scale(ctypes.byref(c), ctypes.byref(inputs), ctypes.byref(scale))
        queries = scale.buff_queries
    return {'slots': [(c.slots[k].type, c.slots[k].level, c.slots[k].option, c.slots[k].ext) for k in range(SLOTS)],
            'byte_16': c.byte_16, 'floats': [fbits(scale.part[k]) for k in range(6)] + [fbits(scale.object)],
            'buffs': [(BUFFS, 0x1a8), (BUFFS, 0x1a9)][:queries],
            'host': expected_host(ran, state.get('window', 0), state.get('ui_flag', 0)), 'branch': scale.branch}, c


def expected_host(ran, window, flag):
    """0x009dadf1's interface calls in a castle world (the host's; no slot write): the window getter, the close
    of a found window, the flag query and, when it answers, the second getter and its call."""
    if not ran:
        return []
    pair = [(0x00f2bb92, ()), (0x00f2bf8b, ())]
    out = pair + [(0x009dc2f0, ())]
    if window:
        out += pair + [(0x009dc341, (4, window, 0))]
    out.append((0x011e042c, (1,)))
    if flag & 0xff:
        out += pair + [(0x009dc316, ()), (0x011f4019, ())]
    return out


def random_floats(rng):
    return [fbits(rng.uniform(-4.0, 4.0)) for _ in range(7)]


def full_state(rng, **fixed):
    state = random_state(rng)
    state.update(byte_16=rng.randrange(256), floats=random_floats(rng), scene=rng.choice([3, 4, 5, 6, 6, 6]),
                 buff_1a8=rng.choice([0, 0, 1, 0x100]), buff_1a9=rng.choice([0, 0, 1, 0x100]),
                 window=rng.choice([0, 0x20900000]), ui_flag=rng.choice([0, 1, 0x100]))
    state.update(fixed)
    return state


def note(family, bad, example):
    family['cases'] += 1
    if bad:
        family['mismatches'] += 1
        if len(family['examples']) < 3:
            family['examples'].append(example)


def compare_full(family, client, lib, state, rng, entry=SET_CLASS):
    got, error = client.full(state, rng, entry)
    want, c = c_full(lib, state, entry)
    keys = ('slots', 'byte_16', 'floats', 'buffs', 'host')
    bad = bool(error) or any(got[k] != want[k] for k in keys)
    note(family, bad, {'error': error, 'client': got, 'c': want, 'class': state['class_byte'],
                       'world': state['world'], 'entry': hex(entry)})
    return got, want, c, bad


def c_part_draws(lib, c):
    out = (PartDraw * 6)()
    n = lib.mu_he_part_draws(ctypes.byref(c), out)
    return [(out[i].slot, out[i].type) for i in range(n)]


def head_row(family, table, client, lib, rng, helm, class_byte, listed):
    """One row: the helm in the helm equipment slot of a class; the head slot and the loop's part draws."""
    state = full_state(rng, model=0xa91, byte_0e=0, class_byte=class_byte, world=rng.choice([0, 2, 3, 7, 51]), scene=6)
    state['equipment'][2] = empty_item() if helm is None else dict(random_item(rng), type=helm - 0xae6)
    got, want, c, bad = compare_full(family, client, lib, state, rng)
    if not bad:
        head = got['slots'][0][0]
        skin = (class_byte & 0xf) + 16 * (0 if not class_byte >> 4 else (class_byte >> 4).bit_length())
        expect = 0x3700 + skin if listed else -1
        draws, error = client.part_loop(state, rng, write=False)
        c_draws = c_part_draws(lib, c)
        last = draws[-1] if draws else None
        bad = bool(error) or head != expect or draws != c_draws or (last == (0, expect)) != bool(listed) or \
            any(slot == 0 for slot, _ in draws) != bool(listed)
        if bad:
            family['mismatches'] += 1
            if len(family['examples']) < 3:
                family['examples'].append({'error': error, 'helm': helm, 'class': class_byte, 'head': head,
                                           'expect': expect, 'client': draws, 'c': c_draws})
    row = table.setdefault('none' if helm is None else f'{helm:#06x}', {'listed': bool(listed), 'rows': 0,
                                                                        'mismatches': 0, 'head_draws': 0})
    row['rows'] += 1
    row['mismatches'] += int(bad)
    row['head_draws'] += int(not bad and listed)


def part_state(rng):
    def slot_type():
        r = rng.random()
        if r < 0.2:
            return -1
        if r < 0.65:
            return 0xae6 + rng.randrange(7, 12) * 512 + rng.choice([rng.randrange(16), rng.randrange(512)])
        if r < 0.7:   # the helms class nibble 4 replaces, in any slot
            return 0x18e6 + rng.choice([0, 5, 6, 8, 9, 7, 10])
        if r < 0.85:
            return 0x3700 + rng.randrange(5) * 0x50 + rng.randrange(0x50)
        return rng.choice([-2, 0, 0xae6, 0x18e5, 0x22e6, 0x36ce, 0x7fff, rng.randrange(-32768, 32768)])
    state = full_state(rng, model=0xa91)
    state['slots'] = [(slot_type() if k < 6 else state['slots'][k][0],) + tuple(state['slots'][k][1:])
                      for k in range(SLOTS)]
    state.update(class_word=rng.choice([-1, -1, 0x211, 0x216, 0x349, rng.randrange(-32768, 32768)]),
                 action=rng.choice([0, 0xd1, 0xdf, 0xdd, rng.randrange(0x200)]), byte_2c=rng.randrange(256),
                 word_364=rng.choice([-1, 0, 5]))
    if state['class_byte'] & 0xf == 6 and state['action'] == 0xdd:   # outside the domain (second pass)
        state['action'] = 0
    return state


def families2(client, lib, cases, seed, quick=False):
    """quick (the mutant runs): the same families on a sample that keeps every boundary value."""
    rng = random.Random(seed ^ 0x2002)
    out = {name: {'cases': 0, 'mismatches': 0, 'examples': []}
           for name in ('head_rows', 'castle', 'scale', 'part_loop', 'part_type')}
    table = {}
    fam = out['head_rows']
    for helm in HEAD_HELMS:
        for class_byte in (range(0, 256, 9) if quick else range(256)):
            head_row(fam, table, client, lib, rng, helm, class_byte, True)
    controls = sorted({h + d for h in HEAD_HELMS for d in (-1, 1)} - set(HEAD_HELMS)) + [None, 0x1900, 0x1ae6, 0x18d0]
    for helm in controls:
        for nibble in range(16):
            head_row(fam, table, client, lib, rng, helm, nibble | rng.choice([0, 0x10, 0x20, 0x40, 0x80, 0xf0]), False)
    fam['table'] = table
    fam = out['castle']
    worlds = (list(range(0x10, 0x1a)) + [0x34, 0x35, 0x36, 0x60, 0x61, 0x62] if quick else list(range(-4, 300))) + \
        [rng.randrange(-2**31, 2**31) for _ in range(16)]
    for world in worlds:
        for nibble in range(16):
            compare_full(fam, client, lib, full_state(rng, world=world, class_byte=nibble | rng.randrange(16) << 4),
                         rng)
    for _ in range(cases):
        state = full_state(rng, world=rng.choice(list(CASTLE_WORLDS) + [0, 0x11, 0x18, 0x34, 0x36, 0x60, 0x62]))
        compare_full(fam, client, lib, state, rng, CASTLE_OVERRIDE)
    fam = out['scale']
    for class_byte in (range(0, 256, 3) if quick else range(256)):
        for world in (rng.choice(CASTLE_WORLDS), rng.choice([0, 2, 3, 0x11, 0x18, 0x36, 0x60])):
            for scene in (3, 4, 5, 6):
                for buffs in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    state = full_state(rng, class_byte=class_byte, world=world, scene=scene, buff_1a8=buffs[0],
                                       buff_1a9=buffs[1], byte_0e=0 if rng.random() < 0.9 else rng.randrange(1, 256))
                    if rng.random() < 0.3:
                        state['slots'][1] = (rng.choice(HEAD_HELMS),) + tuple(state['slots'][1][1:])
                    compare_full(fam, client, lib, state, rng, SCALE)
    fam = out['part_loop']
    for _ in range(cases):
        state = part_state(rng)
        draws, error = client.part_loop(state, rng)
        want = c_part_draws(lib, c_character(state))
        note(fam, bool(error) or draws != want, {'error': error, 'client': draws, 'c': want,
                                                  'class': state['class_byte']})
    # directed rows: the helms 0x18e6 + d in every slot of every class nibble (class nibble 4 replaces five of them
    # in the helm slot), and the indices 0..15 of the groups 6..12 for class nibbles 5 and 6
    directed = [(nibble, slot, 0x18e6 + d) for nibble in range(16) for slot in range(6) for d in range(12)]
    directed += [(nibble, rng.randrange(1, 6), 0xae6 + group * 512 + index)
                 for nibble in (5, 6) for group in range(6, 13) for index in range(16)]
    for nibble, slot, slot_type in directed:
        state = part_state(rng)
        state.update(class_byte=nibble | rng.randrange(16) << 4, action=0)
        state['slots'][slot] = (slot_type,) + tuple(state['slots'][slot][1:])
        draws, error = client.part_loop(state, rng)
        want = c_part_draws(lib, c_character(state))
        note(fam, bool(error) or draws != want, {'error': error, 'client': draws, 'c': want,
                                                  'class': state['class_byte']})
    fam = out['part_type']
    for value in (range(0x1800, 0x2400) if quick else range(-0x400, 0x4000)):
        got, error = client.rf_type(value)
        want = lib.mu_he_part_draw_type(6, 0, value)
        note(fam, bool(error) or got != want, {'error': error, 'client': got, 'c': want, 'type': value})
    return out


def mutations(client, cases, seed, work):
    source = (DIR / 'hero_equipment.c').read_text()
    results = {}
    for name, (old, new) in {**MUTANTS, **MUTANTS2}.items():
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
        fam = families2(client[1], lib, cases, seed, quick=True) if name in MUTANTS2 else \
            families(client[0], lib, cases, seed)
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
    full = Client(text, data, full=True)   # HERO-ITEMS-002: 0x009dadf1 and 0x01394f6f unstubbed
    work = Path(tempfile.mkdtemp(prefix='hero-items-'))
    try:
        lib, error = build(DIR, work, 'hero_items')
        if lib is None:
            raise SystemExit(error)
        report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
                  'families': families(client, lib, args.cases, args.seed)}
        report['families'].update(families2(full, lib, args.cases, args.seed))
        if args.mutations:
            report['mutants'] = mutations((client, full), max(300, args.cases // 4), args.seed, work)
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
