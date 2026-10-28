#!/usr/bin/env python3
"""AUDIO-002F: the music table, its index uses and the Doppelganger manager, against the pinned client.

Families:
  doppelganger  manager 0x00e305ee runs unchanged under Unicorn (its object getters 0x00f2c111 and
                0x00e308e2 too); the singleton 0x00f2bb92, std::string and PlayMp3/StopMp3 are modelled
                as in validate_audio_events. Compared with mu_event_music(0x00e305ee).
  sites         every reference to the music array 0x01cf1680 in the pinned text decodes to a constant
                index (`push 4; pop eax; imul/shl eax; push [eax+0x01cf1680]`); index 43 has one use, in
                0x00e305ee, and index 44 none.
  table         the live read (pins.MUSIC_TABLE_READ) holds, for each of the 76 indices, the address of the
                literal extract_audio_tables.MUSIC_LAYOUT names in the pinned image data.
  group_word    the live 0x06fba808 word (pins.MUSIC_GROUP_WORD) is the start of the std::string the static
                initializer 0x008dc54b builds from the literal "Music": the channel-group names, not music.

The two live-read families need the local snapshot (MU_SNAPSHOT_DIR or their pin variables); without it they
are reported as skipped. --mutations compiles wrong C and also checks wrong table layouts.
No original client is started.
"""
import argparse
import collections
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

import pins
from extract_audio_tables import MUSIC_LAYOUT, Image, music_table
from validate_audio import FAKE, MUSIC_TABLE, MUSIC_COUNT, WORLD, GROUP_NAME_STRINGS, Machine
from validate_audio_events import EVENT, Hooks, Oracle

ROOT = Path(__file__).resolve().parents[1]
MANAGER, END = 0xe305ee, 0xe30660
SINGLETON_GETTER, STRING_CTOR, STATIC_INIT = 0xf2bb92, 0x94997e, 0x8dc54b
MUSIC_LITERAL_GROUP = 0x1ab9ac8
DOPPELGANGER = 16
VALUES = [0, 1, -1, 2, 255, 0x100, 0x10000, 0x1000000, -0x80000000, 0x7fffffff, -2, 0x44]
OBJECTS = [FAKE + 0x3100, FAKE + 0x3ffc0]


class State(C.Structure):
    _fields_ = [(k, C.c_int32) for k in ('world', 'crywolf', 'crywolf_result', 'kanturu', 'temple', 'raklion')] + \
        [('known', C.c_uint32), ('doppelganger', C.c_int32)]


def native(lib, address, s):
    out = []
    cb = EVENT(lambda ctx, k, a, b: out.append((k, a, b)))
    lib.mu_event_music(C.c_uint32(address), C.byref(s), C.byref(Hooks(None, None, None, cb)))
    return out


class DoppelgangerOracle(Oracle):
    def __init__(self, text, data):
        super().__init__(text, data)
        self.m.hook(SINGLETON_GETTER, lambda m: (FAKE + 0x3000, 0))

    def case(self, world, value, obj):
        m = self.m
        self.events.clear()
        m.write32(WORLD, world)
        m.write32(FAKE + 0x3000 + 0x78, obj)
        m.write32(obj + 0x44, value)
        m.call(MANAGER, [], this=FAKE + 0x2000)
        return list(self.events)


def doppelganger_family(text, data, lib):
    oracle = DoppelgangerOracle(text, data)
    cases = 0
    for world in [-1] + list(range(167)) + [0x7fffffff]:
        for value in VALUES:
            for obj in OBJECTS:
                want = oracle.case(world, value, obj)
                got = native(lib, MANAGER, State(world, 0, 0, 0, 0, 0, 0x1f, value))
                if got != want:
                    raise AssertionError((world, value, hex(obj), want, got))
                cases += 1
    return {'cases': cases, 'mismatches': 0,
            'body_sha256': hashlib.sha256(text[MANAGER - 0x401000:END - 0x401000]).hexdigest()}


def music_sites(text):
    """(site, index) of every [eax+0x01cf1680] operand, from the instructions that load eax."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    needle, sites, position = struct.pack('<I', MUSIC_TABLE), [], text.find(struct.pack('<I', MUSIC_TABLE))
    while position >= 0:
        operand = 0x401000 + position
        # push dword ptr [eax + disp32] = ff b0 <disp32>
        start = operand - 2
        assert text[start - 0x401000:operand - 0x401000] == b'\xff\xb0', hex(operand)
        prologue = text[start - 0x401000 - 6:start - 0x401000]
        if prologue[:3] == b'\x6a\x04\x58' and prologue[3:5] == b'\x6b\xc0':      # imul eax, eax, imm8
            index = prologue[5]
        elif prologue[:3] == b'\x6a\x04\x58' and prologue[3:5] == b'\xc1\xe0':    # shl eax, imm8
            index = 1 << prologue[5]
        elif prologue[1:4] == b'\x6a\x04\x58' and prologue[4:6] == b'\xd1\xe0':   # shl eax, 1
            index = 2
        else:
            raise AssertionError(f'unrecognised music-array use at {operand:#x}: '
                                 f'{[i.mnemonic for i in md.disasm(prologue, start - 6)]}')
        sites.append((start, index))
        position = text.find(needle, position + 1)
    return sites


def sites_family(text):
    sites = music_sites(text)
    by_index = collections.defaultdict(list)
    for site, index in sites:
        by_index[index].append(site)
    assert all(0 <= index < MUSIC_COUNT for index in by_index)
    assert by_index[43] == [0xe3062b], by_index[43]
    assert 44 not in by_index
    unused = [i for i in range(MUSIC_COUNT) if i not in by_index]
    digest = hashlib.sha256(json.dumps(sites).encode()).hexdigest()
    return {'cases': len(sites), 'mismatches': 0, 'indices_used': len(by_index), 'unused': unused,
            'index_43_sites': [hex(s) for s in by_index[43]], 'sites_sha256': digest}


def literal_addresses(text, data):
    table = music_table(Image(text, data))
    return [int(entry['literal'], 16) if entry.get('literal') else None for entry in table]


def table_mismatches(read, text, data, layout):
    from extract_audio_tables import MUSIC_LAYOUT as current
    import extract_audio_tables
    saved, extract_audio_tables.MUSIC_LAYOUT = current, layout
    try:
        expected = literal_addresses(text, data)
    finally:
        extract_audio_tables.MUSIC_LAYOUT = saved
    pointers = struct.unpack('<76I', read)
    return [i for i, (p, e) in enumerate(zip(pointers, expected)) if p != e]


def table_family(text, data, given=None):
    read = pins.MUSIC_TABLE_READ.read(given)
    bad = table_mismatches(read, text, data, MUSIC_LAYOUT)
    if bad:
        raise AssertionError(f'music pointers differ from the layout at {bad}')
    pointers = struct.unpack('<76I', read)
    return {'cases': MUSIC_COUNT, 'mismatches': 0, 'distinct_pointers': len(set(pointers)),
            'read_sha256': pins.MUSIC_TABLE_READ.sha256, 'first_literal': hex(min(pointers)),
            'duplicates': {str(i): MUSIC_LAYOUT.index(MUSIC_LAYOUT[i]) for i in range(MUSIC_COUNT)
                           if MUSIC_LAYOUT.index(MUSIC_LAYOUT[i]) != i}}


def group_word_family(text, data, given=None):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    body = list(md.disasm(text[STATIC_INIT - 0x401000:STATIC_INIT - 0x401000 + 0x50], STATIC_INIT))
    pairs = [(body[i].op_str, body[i + 1].op_str, body[i + 2].op_str) for i in range(len(body) - 2)
             if body[i].mnemonic == 'push' and body[i + 1].mnemonic == 'mov' and body[i + 2].mnemonic == 'call']
    image = Image(text, data)
    names = []
    for k, (literal, target, call) in enumerate(pairs):
        assert (target, call) == (f'ecx, {GROUP_NAME_STRINGS + 0x18*k:#x}', hex(STRING_CTOR)), pairs[k]
        names.append(image.cstring(int(literal, 16)))
    assert names == ['Music', 'Environment', 'Effect'], names
    assert pairs[0][0] == hex(MUSIC_LITERAL_GROUP), pairs[0]
    literal = names[0]
    word = pins.MUSIC_GROUP_WORD.read(given)
    # MSVC std::string: a short string sits inline at offset 0 of the 0x18-byte object.
    assert word == literal.encode('latin1')[:4], word
    return {'cases': 1, 'mismatches': 0, 'strings': names, 'object': hex(GROUP_NAME_STRINGS),
            'literal': hex(MUSIC_LITERAL_GROUP)}


MUTATIONS = {
    'index': ('if (s->doppelganger != 0) mp3(&e, 43);', 'if (s->doppelganger != 0) mp3(&e, 44);'),
    'equality': ('if (s->doppelganger != 0) mp3(&e, 43);', 'if (s->doppelganger == 1) mp3(&e, 43);'),
    'sign': ('if (s->doppelganger != 0) mp3(&e, 43);', 'if (s->doppelganger > 0) mp3(&e, 43);'),
    'byte': ('if (s->doppelganger != 0) mp3(&e, 43);', 'if ((s->doppelganger & 0xff) != 0) mp3(&e, 43);'),
    'stop': ('if (s->doppelganger != 0) mp3(&e, 43);',
             'if (s->doppelganger != 0) mp3(&e, 43); else mp3stop(&e, 43);'),
    'world': ('if (s->doppelganger != 0) mp3(&e, 43);',
              'if (w >= 65 && w <= 68 && s->doppelganger != 0) mp3(&e, 43);'),
}
LAYOUTS = {
    'index-44-unresolved': MUSIC_LAYOUT[:44] + [None] + MUSIC_LAYOUT[45:],
    'index-44-next-literal': MUSIC_LAYOUT[:44] + [41] + MUSIC_LAYOUT[45:],
    'index-43-repeats-39': MUSIC_LAYOUT[:43] + [39] + MUSIC_LAYOUT[44:],
    'index-42-own-literal': MUSIC_LAYOUT[:42] + [40] + MUSIC_LAYOUT[43:],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--report')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--table-read', help='live read of 0x01cf1680 (default: pins.MUSIC_TABLE_READ)')
    parser.add_argument('--group-word', help='live read of 0x06fba808 (default: pins.MUSIC_GROUP_WORD)')
    parser.add_argument('--require-live', action='store_true', help='fail when the live read is not available')
    args = parser.parse_args()
    text, data = pins.TEXT.read(exit=True), pins.DATA.read(exit=True)
    lib = C.CDLL(str(ROOT/'reconstructed/audio'/('libclient_audio.dylib' if sys.platform == 'darwin'
                                                  else 'libclient_audio.so')))
    report = {'families': {}, 'skipped': {}, 'mismatches': 0, 'mutants': {}}
    report['families']['doppelganger'] = doppelganger_family(text, data, lib)
    report['families']['sites'] = sites_family(text)
    live = pins.MUSIC_TABLE_READ.available(args.table_read) and pins.MUSIC_GROUP_WORD.available(args.group_word)
    if live:
        report['families']['table'] = table_family(text, data, args.table_read)
        report['families']['group_word'] = group_word_family(text, data, args.group_word)
    elif args.require_live:
        raise SystemExit(pins.MUSIC_TABLE_READ.hint())
    else:
        report['skipped'] = {'table': 'live read not available', 'group_word': 'live read not available'}
    for name, family in report['families'].items():
        print(f'{name}: {family["cases"]} cases, 0 mismatches', flush=True)
    if args.mutations:
        source = (ROOT/'reconstructed/audio/audio_world.c').read_text()
        small = [State(w, 0, 0, 0, 0, 0, 0x1f, v) for w in (0, 65, 66, 67, 68, 100) for v in VALUES]
        with tempfile.TemporaryDirectory(prefix='audio-music-mutants-') as tmp:
            for name, (old, new) in MUTATIONS.items():
                assert source.count(old) == 1, name
                src, dll = Path(tmp)/'mutant.c', Path(tmp)/f'{name}.dylib'
                src.write_text(source.replace(old, new, 1))
                subprocess.run(['clang', '-shared', '-fPIC', '-I', str(ROOT/'reconstructed/audio'), str(src),
                                '-o', str(dll)], check=True)
                bad = C.CDLL(str(dll))
                assert any(native(bad, MANAGER, s) != native(lib, MANAGER, s) for s in small), name
                report['mutants'][name] = 'caught'
        if live:
            read = pins.MUSIC_TABLE_READ.read(args.table_read)
            for name, layout in LAYOUTS.items():
                assert table_mismatches(read, text, data, layout), name
                report['mutants']['layout-' + name] = 'caught'
    report['cases'] = sum(f['cases'] for f in report['families'].values())
    print(json.dumps(report, indent=2))
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
