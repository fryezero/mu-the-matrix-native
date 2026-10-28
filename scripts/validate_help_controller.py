#!/usr/bin/env python3
"""HelpWindow provider/loader/invoke logic vs original pinned instructions.

STL vector operations, std::string, ASCII identity conversion, GlobalText,
base-load success and GFx Invoke are explicit services. Window control flow,
row selection, ordering and argument offsets run as original instructions.
This does not validate allocation failures, the original code page or a movie.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tests'))
import test_help as th
import client_ui_machine as cm
import pins

OFFSETS = (0x11078, 0x11084, 0x11090)


class Provider(C.Structure):
    _fields_ = [('lists', (C.c_uint8 * th.PAYLOAD) * 3), ('counts', C.c_uint32 * 3)]


INVOKE = C.CFUNCTYPE(None, C.c_void_p, C.c_char_p, C.c_size_t, C.POINTER(C.c_char_p))


def bind(lib):
    ptr = C.POINTER(Provider)
    lib.mu_help_provider_init.argtypes = [ptr]
    lib.mu_help_build.argtypes = [ptr, C.c_void_p]
    lib.mu_help_hotkeys.argtypes = [ptr, C.c_int, INVOKE, C.c_void_p]
    lib.mu_help_chatkeys.argtypes = [ptr, INVOKE, C.c_void_p]
    lib.mu_help_reload.argtypes = [ptr, C.c_int, INVOKE, C.c_void_p]
    lib.mu_help_load.argtypes = [ptr, C.c_void_p, C.c_int, C.c_int,
                               C.POINTER(C.c_char_p), INVOKE, C.c_void_p]
    return lib


class Original:
    def __init__(self, text, data):
        self.m = m = cm.Machine(text, data)
        for start, end in [(0xb89866, 0xb89c47), (0xb89cc0, 0xb89fbc), (0xb8a091, 0xb8a0c1),
                           (0xb6ced8, 0xb6cf07), (0xb89588, 0xb89646), (0xb89fbc, 0xb89fe5)]:
            m.allow((start, end))
        self.lists, self.strings, self.events = {}, {}, []
        m.stub(0xb6ce60, self.clear)           # vector clear, ret 0
        m.stub(0xb6cf74, self.push, 4)         # vector push_back(row copy)
        m.stub(0xb6ce11, self.begin, 4)
        m.stub(0xb6cf07, self.end, 4)
        m.stub(0xb6ca2f, lambda _: m.u32(self.ecx()))  # iterator dereference
        m.stub(0xb6ca7c, self.increment, 8)
        m.stub(0xb6c9f2, lambda _: int(m.u32(self.ecx()) != m.u32(m.args(1)[0])), 4)
        m.stub(0x8e6d00, self.string_init)
        m.stub(0x94997e, self.string_from_cstr, 4)
        m.stub(0x8e83a0, lambda _: 0)
        m.stub(0xa99d93, self.convert)
        m.stub(0x8e7940, lambda _: self.cstring(self.strings[self.ecx()]))
        m.stub(0xaae7e0, self.invoke)
        m.stub(0x95f027, lambda _: self.cstring(f'GT{m.args(1)[0]}'.encode()), 4)
        m.stub(0xaadbc3, lambda _: self.loaded)
        m.stub(0xb8968b, self.read_table)
        m.stub(0x1072152, lambda _: 0x01234000)
        m.stub(0x1072aa9, lambda _: self.mode)
        m.stub(0xaad53a, self.base_construct)
        m.stub(0xb6c951, self.vector_construct)
        m.stub(0xab02b7, self.allocate_callback)
        m.stub(0xaaf5ab, lambda _: self.ecx(), 4)
        m.stub(0xab02fd, self.register_callback, 4)

    def base_construct(self, _):
        self.constructor_events.append(('base', self.ecx() - self.obj))
        return self.ecx()

    def vector_construct(self, _):
        self.constructor_events.append(('vector', self.ecx() - self.obj))
        self.clear(None)
        return self.ecx()

    def allocate_callback(self, _):
        size = self.m.args(1)[0]
        self.constructor_events.append(('allocate', size))
        return self.m.alloc(size, define=True)

    def register_callback(self, _):
        pointer = self.m.args(1)[0]
        self.constructor_events.append(('register', self.ecx() - self.obj,
                                        self.m.u32(pointer), self.m.u32(pointer + 16) - self.obj))

    def ecx(self):
        return self.m.uc.reg_read(cm.UC_X86_REG_ECX)

    def cstring(self, value):
        address = self.m.alloc(len(value) + 1)
        self.m.write(address, value + b'\0')
        return address

    def read_cstring(self, address):
        value = bytearray()
        for i in range(512):
            b = self.m.read(address + i, 1)
            if b == b'\0':
                return bytes(value)
            value += b
        raise RuntimeError('unterminated synthetic string')

    def sync(self, vector):
        base, rows = self.lists[vector]
        self.m.put32(vector, base)
        self.m.put32(vector + 4, base + len(rows) * 136)
        self.m.put32(vector + 8, base + 512 * 136)

    def clear(self, _):
        vector = self.ecx()
        self.lists[vector][1].clear()
        self.sync(vector)

    def push(self, _):
        vector = self.ecx()
        base, rows = self.lists[vector]
        row = self.m.read(self.m.args(1)[0], 136)
        if len(rows) >= 512:
            raise RuntimeError('comparison exceeded bounded vector capacity')
        self.m.write(base + len(rows) * 136, row)
        rows.append(row)
        self.sync(vector)

    def begin(self, _):
        out = self.m.args(1)[0]
        self.m.put32(out, self.m.u32(self.ecx()))
        return out

    def end(self, _):
        out = self.m.args(1)[0]
        self.m.put32(out, self.m.u32(self.ecx() + 4))
        return out

    def increment(self, _):
        out = self.m.args(2)[0]
        self.m.put32(out, self.m.u32(self.ecx()))
        self.m.put32(self.ecx(), self.m.u32(self.ecx()) + 136)
        return out

    def string_init(self, _):
        self.strings[self.ecx()] = b''
        return self.ecx()

    def string_from_cstr(self, _):
        self.strings[self.ecx()] = self.read_cstring(self.m.args(1)[0])
        return self.ecx()

    def convert(self, _):
        out, source = self.m.args(2)
        self.strings[out] = self.strings[source]  # explicit ASCII-only service

    def invoke(self, _):
        handler, method, fmt = self.m.args(3)
        if handler != self.obj:
            raise RuntimeError('wrong Invoke handler')
        count = self.read_cstring(fmt).count(b'%s')
        args = self.m.args(3 + count)[3:]
        self.events.append((self.read_cstring(method).decode(),
                            [self.read_cstring(a).decode('ascii') for a in args]))

    def read_table(self, _):
        self.m.write(self.ecx() + 0x78, self.table)

    def seed(self, table, initial=None, mode=0, loaded=True):
        self.m.reset()
        self.obj = self.m.alloc(0x1109c, define=True)
        self.table, self.mode, self.loaded = table, mode, loaded
        self.m.write(self.obj + 0x78, table)
        self.events, self.strings, self.lists, self.constructor_events = [], {}, {}, []
        initial = initial or [[], [], []]
        for offset, rows in zip(OFFSETS, initial):
            base = self.m.alloc(th.PAYLOAD)
            self.lists[self.obj + offset] = [base, list(rows)]
            for i, row in enumerate(rows):
                self.m.write(base + i * 136, row)
            self.sync(self.obj + offset)

    def run(self, entry):
        result = self.m.call(entry, ecx=self.obj)
        return result, [self.lists[self.obj + o][1] for o in OFFSETS], list(self.events)


def rows(seed):
    rng = random.Random(seed)
    out = []
    # Includes empty table, full table and every zero-sentinel position across
    # a 512-case corpus. Text lengths reach both field boundaries.
    count = seed % 513
    for i in range(512):
        row = bytearray(136)
        ident = rng.choice([-5, -1, 1, 2, 3, 4, 0x7fffffff]) if i != count else 0
        category = rng.choice([0, 1, 2, 12, 13, 14, 255])
        auxiliary = rng.choice([0, 1, 2, 3, 255])
        struct.pack_into('<iBB', row, 0, ident, category, auxiliary)
        key = (f'Key-{seed}-{i}-' + 'k' * (i % 64))[:63].encode()
        text = (f'Description-{seed}-{i}-' + 'd' * (i % 66))[:65].encode()
        row[6:6 + len(key)] = key
        row[70:70 + len(text)] = text
        out.append(bytes(row))
    return b''.join(out)


def provider_lists(p):
    return [[bytes(p.lists[k][i * 136:(i + 1) * 136]) for i in range(p.counts[k])] for k in range(3)]


def authored(lib, table, mode, operation, initial=None, loaded=True):
    p = Provider()
    lib.mu_help_provider_init(C.byref(p))
    if initial:
        for k, items in enumerate(initial):
            p.counts[k] = len(items)
            for i, row in enumerate(items):
                C.memmove(C.addressof(p.lists[k]) + i * 136, row, 136)
    events = []
    callback = INVOKE(lambda user, method, count, args:
                      events.append((method.decode(), [args[i].decode('ascii') for i in range(count)])))
    if operation == 'construct':
        lib.mu_help_provider_init(C.byref(p))
        result = 1
    elif operation == 'build':
        result = lib.mu_help_build(C.byref(p), table)
    elif operation == 'load':
        labels = (C.c_char_p * 5)(*[f'GT{0xd57 + i}'.encode() for i in range(5)])
        result = lib.mu_help_load(C.byref(p), table, loaded, mode, labels, callback, None)
    else:
        fn = getattr(lib, 'mu_help_' + operation)
        arguments = [C.byref(p)] + ([] if operation == 'chatkeys' else [mode]) + [callback, None]
        result = fn(*arguments)
    return result, provider_lists(p), events


MUTANTS = {
    'provider-init': ('memset(provider, 0, sizeof *provider)', 'memset(provider, 0, sizeof *provider - 4)'),
    'sentinel': ('if (row_id(row) == 0) break;', 'if (row_id(row) == -1) break;'),
    'category-13': ('row[4] == 13', 'row[4] == 12'),
    'category-byte': ('row[4] == 1 ? 1', 'row[5] == 1 ? 1'),
    'auxiliary-byte': ('row[5] == 1 || row[5] == 2', 'row[5] == 1 || row[5] == 3'),
    'mode-filter': ('id == 2 && !mode', 'id == 2 && mode == 1'),
    'description-offset': ('(const char *)row + 70', '(const char *)row + 71'),
    'clear-provider': ('invoke(user, "ClearDataProvider", 0, NULL);', '/* omitted clear */'),
    'auxiliary-retention': ('provider->count[0] = provider->count[1] = 0;',
                            'provider->count[0] = provider->count[1] = provider->count[2] = 0;'),
    'base-load-guard': ('if (!base_loaded || !labels', 'if ((base_loaded < 0) || !labels'),
    'center-order': ('invoke(user, "SetPosCenter", 0, NULL);', '/* omitted center */'),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', type=int, default=64)
    ap.add_argument('--mutants', action='store_true')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    if args.cases < 1:
        ap.error('--cases must be positive')
    original = Original(pins.TEXT.read(), pins.DATA.read())
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
              'families': {}, 'mutants': {}}
    references = []
    for i in range(args.cases):
        boundary_seeds = [0, 1, 511, 512]
        seed = i if args.cases >= 513 else boundary_seeds[i] if i < 4 else (i * 97) % 513
        table = rows(seed)
        initial = [[table[:136]]] * 3
        original.seed(table, initial=initial)
        returned, lists, events = original.run(0xb89588)
        expected_ctor = [('base', 0), *[('vector', offset) for offset in OFFSETS],
                         ('allocate', 20), ('register', 0x30, 0x01a8f1d0, 0)]
        if returned != original.obj or original.m.u32(original.obj) != 0x01a8f180 or original.constructor_events != expected_ctor:
            raise AssertionError('original constructor boundary trace changed')
        references.append(('construct', table, 0, initial, True, (lists, events)))
        report['families'].setdefault('construct-provider-projection', {'cases': 0, 'mismatches': 0})['cases'] += 1
        for operation, entry in [('build', 0xb89866), ('hotkeys', 0xb89cc0),
                                 ('chatkeys', 0xb89e69), ('reload', 0xb89c17), ('load', 0xb89977)]:
            modes = (0, 1, 2) if operation in ('hotkeys', 'reload', 'load') else (0,)
            for mode in modes:
                original.seed(table, mode=mode)
                original.run(0xb89866)
                initial = [list(original.lists[original.obj + o][1]) for o in OFFSETS]
                if operation in ('build', 'load'):
                    # Exercise reset of old first/second lists and retained third
                    # list without exceeding the explicit bounded capacity.
                    initial = [items[:1] for items in initial]
                original.seed(table, initial=initial, mode=mode)
                returned, lists, events = original.run(entry)
                if operation in ('load', 'reload') and returned & 0xff != 1:
                    raise AssertionError('original success return changed')
                expected = (lists, events)
                references.append((operation, table, mode, initial, True, expected))
                report['families'].setdefault(operation, {'cases': 0, 'mismatches': 0})['cases'] += 1
        original.seed(table, mode=0, loaded=False)
        returned, lists, events = original.run(0xb89977)
        if returned & 0xff:
            raise AssertionError('base-load failure returned success')
        references.append(('load', table, 0, None, False, (lists, events)))
        report['families'].setdefault('load-refusal', {'cases': 0, 'mismatches': 0})['cases'] += 1
    with tempfile.TemporaryDirectory(prefix='mu-help-controller-') as directory:
        work = Path(directory)
        lib = bind(th.library(th.build_library(work)))
        for operation, table, mode, initial, loaded, expected in references:
            result, lists, events = authored(lib, table, mode, operation, initial, loaded)
            if (lists, events) != expected or (operation == 'load' and bool(result) != loaded):
                raise AssertionError(f'{operation}, mode {mode}, base {loaded}: compiled C mismatch')
        if args.mutants:
            paths = [ROOT/'reconstructed/help/help.c', ROOT/'reconstructed/help/help_controller.c',
                     ROOT/'reconstructed/data/data_tables.c', ROOT/'reconstructed/data/data_codec.c']
            for name, (before, after) in MUTANTS.items():
                folder = work/name
                folder.mkdir()
                sources = []
                for path in paths:
                    source = path.read_text()
                    if path.name == 'help_controller.c':
                        if before not in source:
                            raise AssertionError(f'Mutant anchor absent: {name}')
                        source = source.replace(before, after)
                    dest = folder/path.name
                    dest.write_text(source)
                    sources.append(dest)
                mutant = bind(th.library(th.build_library(folder, sources)))
                caught = None
                for operation, table, mode, initial, loaded, expected in references:
                    _, lists, events = authored(mutant, table, mode, operation, initial, loaded)
                    if (lists, events) != expected:
                        caught = operation
                        break
                if not caught:
                    raise AssertionError(f'Compiled mutant survived: {name}')
                report['mutants'][name] = {'caught': True, 'family': caught}
    report['cases'] = len(references)
    report['mismatches'] = 0
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
