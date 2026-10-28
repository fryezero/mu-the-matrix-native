#!/usr/bin/env python3
"""Extract the client's sound table and music table from the restored image.

Sound table: every call to SND_Load 0x00a6ab76 is decoded statically. The
pattern at each site is `push <path literal>; lea ecx, tmp; call
std::string(const char*) 0x0094997e; push legacy_3d; push legacy_channels;
lea eax, tmp; push eax; push <id>; call 0x00a6ab76`. The loader function of
each site is reported (startup sets, per-monster OpenMonsterModel 0x0180b0f4,
per-NPC 0x01808a40, ...); the same id can be registered by several loaders
because SND_Load keeps the first registration until SND_Remove.

Music table: the client indexes a 76-entry `char *` array at 0x01cf1680 in the
packed .data section, which no capture contains. Its literals sit in the
second image section at 0x01af63ec.. in declaration order. Four array entries
have no literal of their own there (the compiler pooled identical strings):
indices 40..42 repeat entry 39 and one of 43/44 is unresolved. The placement
is inferred from the code that uses each index (world numbers, the ambient
sound played next to it and the event managers) and is labelled as such.

The output stays local: it contains client file names. Nothing here is
committed.
"""
import native_data_manifest as manifest
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

TEXT_BASE, TEXT_BYTES = 0x401000, 23572480
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_BASE, DATA_BYTES = 0x1a7c000, 2557764
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
SND_LOAD, STRING_CTOR = 0xa6ab76, 0x94997e
MUSIC_LITERALS, MUSIC_COUNT = 0x1af63ec, 76
LOADERS = {0x18392db: 'startup set A', 0x18433ed: 'startup set B', 0x180b0f4: 'OpenMonsterModel',
           0x1808a40: 'OpenNpc'}
# Array index -> literal ordinal in the contiguous run (None: unresolved).
MUSIC_LAYOUT = list(range(0, 40)) + [39, 39, 39, 40, None] + list(range(41, 72))
MUSIC_NOTES = {40: 'duplicate of 39 (inferred: world 70 manager 0x00dd8891)',
               41: 'duplicate of 39 (inferred: world 71 manager 0x00dde543)',
               42: 'duplicate of 39 (inferred: worlds 72..74 manager 0x00de5467)',
               43: 'inferred: either 43 or 44 holds this literal; 43 is used by manager 0x00e305ee',
               44: 'unresolved: no client code uses this index'}


class Image:
    def __init__(self, text, data):
        self.text, self.data = text, data

    def read(self, address, size):
        if TEXT_BASE <= address < TEXT_BASE + len(self.text):
            return self.text[address - TEXT_BASE:address - TEXT_BASE + size]
        if DATA_BASE <= address < DATA_BASE + len(self.data):
            return self.data[address - DATA_BASE:address - DATA_BASE + size]
        return None

    def cstring(self, address, limit=300):
        raw = self.read(address, limit)
        if raw is None or b'\0' not in raw:
            return None
        return raw.split(b'\0')[0].decode('latin1')

    def calls_to(self, target):
        sites, text = [], self.text
        position = text.find(b'\xe8')
        while 0 <= position < len(text) - 5:
            relative = struct.unpack_from('<i', text, position + 1)[0]
            if TEXT_BASE + position + 5 + relative == target:
                sites.append(TEXT_BASE + position)
            position = text.find(b'\xe8', position + 1)
        return sites

    def function_start(self, address, limit=0x40000):
        for p in range(address, address - limit, -1):
            window = self.read(p - 1, 4)
            if window and window[1:4] == b'\x55\x8b\xec' and window[0] in (0xcc, 0xc3, 0x90, 0xc2, 0x00):
                return p
        return None


def window(image, decoder, site, back=0x80):
    for start in range(site - back, site - back + 16):
        instructions = list(decoder.disasm(image.read(start, back + 8), start))
        if any(i.address == site for i in instructions):
            return [i for i in instructions if i.address <= site]
    return None


def immediate(instruction):
    try:
        return int(instruction.op_str, 0)
    except ValueError:
        return None


def sound_table(image):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    rows, unresolved = [], []
    for site in image.calls_to(SND_LOAD):
        instructions = window(image, decoder, site)
        pushes = []
        for instruction in reversed(instructions[:-1] if instructions else []):
            if instruction.mnemonic == 'call':
                break
            if instruction.mnemonic == 'push':
                pushes.append(instruction)
                if len(pushes) == 4:
                    break
        if len(pushes) < 4:
            unresolved.append({'site': hex(site), 'reason': 'argument pushes'})
            continue
        id_push, string_push, channels_push, flag_push = pushes
        sound_id = immediate(id_push)
        target = None
        for instruction in reversed(instructions[:-1]):
            if instruction.address < string_push.address and instruction.mnemonic == 'lea' \
                    and instruction.op_str.startswith('eax,'):
                target = instruction.op_str.split(', ', 1)[1]
                break
        path = None
        for k in range(len(instructions) - 1, 1, -1):
            item = instructions[k]
            if item.mnemonic == 'call' and item.op_str == hex(STRING_CTOR):
                if instructions[k - 1].op_str == 'ecx, ' + (target or '') and instructions[k - 2].mnemonic == 'push':
                    value = immediate(instructions[k - 2])
                    path = image.cstring(value) if value is not None else None
                break
        if sound_id is None or path is None:
            unresolved.append({'site': hex(site), 'reason': 'computed id or path',
                               'ops': [f'{i.mnemonic} {i.op_str}' for i in instructions[-8:]]})
            continue
        loader = image.function_start(site)
        rows.append({'id': sound_id, 'path': path, 'legacy_channels': immediate(channels_push),
                     'legacy_3d': immediate(flag_push), 'site': hex(site), 'loader': hex(loader or 0),
                     'loader_name': LOADERS.get(loader, '')})
    rows.sort(key=lambda r: (r['id'], r['site']))
    return rows, unresolved


def music_table(image):
    literals, address = [], MUSIC_LITERALS
    while len(literals) < 72:
        text = image.cstring(address)
        if not text or not re.search(r'(?i)\.(mp3|ogg)$', text):
            break
        literals.append((address, text))
        address += len(text) + 1
        while image.read(address, 1) == b'\0':
            address += 1
    if len(literals) != 72:
        raise ValueError(f'expected 72 music literals, found {len(literals)}')
    table = []
    for index, ordinal in enumerate(MUSIC_LAYOUT):
        entry = {'index': index}
        if ordinal is None:
            entry.update(path=None, evidence='unresolved')
        else:
            entry.update(path=literals[ordinal][1], literal=hex(literals[ordinal][0]),
                         evidence='static literal order' if index < 40 or index > 44 else 'inferred')
        if index in MUSIC_NOTES:
            entry['note'] = MUSIC_NOTES[index]
        table.append(entry)
    assert len(table) == MUSIC_COUNT
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', required=True)
    parser.add_argument('--data', required=True)
    parser.add_argument('--out', required=True, help='JSON output (keep it outside the repository)')
    parser.add_argument('--tsv', help='tab-separated table for native/build/mu-audio')
    manifest.arguments(parser)
    args = parser.parse_args()
    if args.tsv:
        manifest.prepare(args)
        manifest.prepare_output(args, Path(args.tsv).parent)
    text, data = Path(args.text).read_bytes(), Path(args.data).read_bytes()
    if len(text) != TEXT_BYTES or hashlib.sha256(text).hexdigest() != TEXT_SHA256:
        raise SystemExit('restored text does not match the pinned capture')
    if len(data) != DATA_BYTES or hashlib.sha256(data).hexdigest() != DATA_SHA256:
        raise SystemExit('image data does not match the pinned capture')
    image = Image(text, data)
    sounds, unresolved = sound_table(image)
    music = music_table(image)
    result = {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'sounds': sounds,
              'unresolved_sites': unresolved, 'music': music,
              'summary': {'load_sites': len(sounds) + len(unresolved), 'resolved': len(sounds),
                          'distinct_ids': len({r['id'] for r in sounds}),
                          'distinct_paths': len({r['path'].lower() for r in sounds})}}
    Path(args.out).write_text(json.dumps(result, indent=1) + '\n')
    if args.tsv:
        lines = ['# kind\tid\tpath\tlegacy_channels\tlegacy_3d\tloader\tsite']
        for r in sounds:
            lines.append(f"sound\t{r['id']}\t{r['path']}\t{r['legacy_channels']}\t{r['legacy_3d']}\t{r['loader']}\t{r['site']}")
        for entry in music:
            if entry['path']:
                lines.append(f"music\t{entry['index']}\t{entry['path']}\t-\t-\t{entry['evidence']}")
        Path(args.tsv).write_text('\n'.join(lines) + '\n')
    if args.tsv:
        manifest.publish(args, Path(args.tsv).parent, 'audio-export-v1', [args.text, args.data])
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
