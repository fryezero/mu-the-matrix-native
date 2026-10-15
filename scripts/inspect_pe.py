#!/usr/bin/env python3
"""Read-only PE32 inventory. Does not execute, unpack, or decompile a target."""
import argparse
import collections
import hashlib
import json
import math
import pathlib
import struct


def inspect(path):
    data = path.read_bytes()

    def unpack(fmt, offset):
        return struct.unpack_from(fmt, data, offset)

    if data[:2] != b'MZ':
        raise ValueError('Not an MZ executable')
    pe = unpack('<I', 60)[0]
    if data[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Not a PE executable')
    machine, count, timestamp, symptr, symcount, optsize, flags = unpack('<HHIIIHH', pe + 4)
    opt = pe + 24
    if unpack('<H', opt)[0] != 0x10b:
        raise ValueError('This inspector supports PE32 only')
    entry = unpack('<I', opt + 16)[0]
    base = unpack('<I', opt + 28)[0]
    sections = []
    for i in range(count):
        offset = opt + optsize + 40 * i
        name = data[offset:offset + 8].rstrip(b'\0').decode('ascii', errors='replace')
        virtual_size, rva, size, raw = unpack('<IIII', offset + 8)
        if size and raw + size > len(data):
            raise ValueError(f'Section {i} extends beyond file')
        block = data[raw:raw + size]
        entropy = -sum(n / size * math.log2(n / size) for n in collections.Counter(block).values()) if size else None
        sections.append(dict(index=i, name=name, rva=rva, virtual_address=base + rva,
                             virtual_size=virtual_size, file_offset=raw, file_size=size,
                             entropy_bits_per_byte=entropy,
                             contains_entry=rva <= entry < rva + max(size, virtual_size)))

    def file_offset(rva):
        if 0 <= rva < unpack('<I', opt + 60)[0]:
            return rva
        for section in sections:
            delta = rva - section['rva']
            if 0 <= delta < section['file_size']:
                return section['file_offset'] + delta
        raise ValueError(f'RVA {rva:#x} is not file-backed')

    def cstring(offset):
        end = data.find(b'\0', offset, min(offset + 4096, len(data)))
        if end < 0:
            raise ValueError('Unterminated string')
        return data[offset:end].decode('ascii', errors='replace')

    directories = [dict(index=i, rva=unpack('<II', opt + 96 + i * 8)[0],
                        size=unpack('<II', opt + 96 + i * 8)[1])
                   for i in range(min(unpack('<I', opt + 92)[0], 16))]
    imports, issues = [], []
    imp = directories[1]
    if imp['rva']:
        for i in range(min(imp['size'] // 20, 4096)):
            try:
                fields = unpack('<IIIII', file_offset(imp['rva'] + 20 * i))
                if not any(fields):
                    break
                original, _, _, name_rva, thunk = fields
                module = dict(name=cstring(file_offset(name_rva)), functions=[])
                imports.append(module)
                for j in range(65536):
                    value = unpack('<I', file_offset((original or thunk) + 4 * j))[0]
                    if value == 0:
                        break
                    module['functions'].append({'ordinal': value & 0xffff} if value & 0x80000000
                                               else {'name': cstring(file_offset(value) + 2)})
                else:
                    issues.append('Import thunk limit reached')
            except (ValueError, struct.error) as error:
                issues.append(f'Import descriptor {i}: {error}')
                break
    debug = []
    if directories[6]['rva']:
        for i in range(directories[6]['size'] // 28):
            fields = unpack('<IIHHIIII', file_offset(directories[6]['rva'] + i * 28))
            _, _, _, _, kind, size, rva, raw = fields
            record = dict(type=kind, bytes=size, rva=rva, file_offset=raw)
            if kind == 2 and data[raw:raw + 4] == b'RSDS':
                record['pdb_path_reference'] = cstring(raw + 24)
                record['note'] = 'Embedded path reference only; does not contain the PDB or source.'
            debug.append(record)
    if symcount and symptr + symcount * 18 > len(data):
        issues.append('Declared COFF symbol table extends beyond end of file')
    certificate = directories[4]
    if certificate['rva'] and certificate['rva'] + certificate['size'] > len(data):
        issues.append('Declared certificate table extends beyond end of file')
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(data).hexdigest(),
                bytes=len(data), format='PE32', machine=machine, image_base=base,
                entry_rva=entry, entry_virtual_address=base + entry,
                image_size=unpack('<I', opt + 56)[0], timestamp_raw=timestamp,
                coff_symbol_table=dict(offset=symptr, count=symcount),
                sections=sections, imports=imports, debug=debug, directories=directories,
                issues=issues,
                limitations=['Static file inventory only. No runtime behavior verified.',
                             'Import table is not a complete inventory of runtime dependencies.',
                             'Entropy measures byte distribution, not proof of a particular protector.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=pathlib.Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.path), indent=2))
