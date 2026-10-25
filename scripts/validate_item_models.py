#!/usr/bin/env python3
"""Trace the client's item index -> model file mapping (NATIVE-DATA-001).

Actual client code runs in Unicorn over the pinned restored text, with no
skipped callees except the modelled CRT file/heap calls:

1. the item-script manager constructor 0x00cd4dbc (its std::map, iterator,
   empty record and two option maps) on a zero-filled object;
2. the Item.bmd loader 0x00cd4f2a on the installed file, inserting every
   decoded 0x2c4-byte record through the record constructor 0x01184277 and
   the container code;
3. the lookup 0x00cd5d29 for every item code present and for absent codes;
4. the model-cache constructor 0x00eaa6d9 and the model getter 0x00eaa8cf for
   every model index 0..0x3af6 and out-of-range indexes. The item-script
   singleton accessor 0x00cd4ea8 (thread-local static guard) returns the
   manager from step 1, and the model loader 0x00cd558e is replaced by a
   recorder of its three arguments (model index, folder, file) returning 0,
   so no model is loaded or cached.

Each observed (model index -> item code -> folder, file) result is compared
with the authored native parser (native/build/mu-data item-models --json).
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402
spec = importlib.util.spec_from_file_location('validate_data_tables', ROOT/'scripts/validate_data_tables.py')
tables = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tables)

MANAGER_CTOR, ITEM_LOADER, FIND = 0x00cd4dbc, 0x00cd4f2a, 0x00cd5d29
CACHE_CTOR, GET_MODEL, MANAGER_SINGLETON, LOAD_MODEL = 0x00eaa6d9, 0x00eaa8cf, 0x00cd4ea8, 0x00cd558e
MODEL_BASE, MODEL_LIMIT = 0xae6, 0x3af6
BODIES = {  # start, exclusive end, SHA-256 of the captured bytes (checked before use)
    'model_getter': (0x00eaa8cf, 0x00eaaa44, 'bdbe352624e0bf0cb69ae79a389cbdffa39c6fa1b0b362a4b1a0c59e68d2bc0d'),
    'find': (0x00cd5d29, 0x00cd5d7f, 'b9cab55605f3fafbc78edd41430cc91d5f5524ad302e16169208861aa4b940cf'),
    'item_loader': (0x00cd4f2a, 0x00cd51c0, 'ae82e91259b6f5a0604b3e68cfe83fe89529934a612999a00737b6ed68910c64'),
    'manager_ctor': (0x00cd4dbc, 0x00cd4e32, '8ded5893240825440b4cd65593a3dca7e8e85cc1dc046cc9f5a1b3d71702a1a0'),
    'cache_ctor': (0x00eaa6d9, 0x00eaa729, '056c79f4e13b8cd5ad65ee06c41879b4c08dff662380bd545f0d1a1f869aae05'),
}


class Runner:
    """Executes client functions with only the CRT and two named calls modelled."""

    def __init__(self, machine, image):
        from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_FETCH_UNMAPPED
        self.machine, self.uc, self.image = machine, machine.uc, image
        self.heap, self.position, self.eof = tables.HEAP, 0, False
        self.manager = None
        self.model_calls = []
        self.stop = None
        handlers = {tables.FOPEN: self.fopen, tables.FREAD: self.fread, tables.FCLOSE: self.ret0,
                    tables.FEOF: self.feof, tables.NEW: self.new, tables.MALLOC: self.new, tables.FREE: self.ret0,
                    MANAGER_SINGLETON: self.singleton, LOAD_MODEL: self.load_model}
        self.handlers = handlers
        self.hooks = [self.uc.hook_add(UC_HOOK_CODE, self.dispatch, begin=a, end=a) for a in handlers]
        self.hooks.append(self.uc.hook_add(UC_HOOK_MEM_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED, self.unmapped))
        self.uc.ctl_flush_tb()

    def close(self):
        for hook in self.hooks:
            self.uc.hook_del(hook)
        self.uc.ctl_flush_tb()

    def unmapped(self, uc, access, address, size, value, ignored):
        from unicorn.x86_const import UC_X86_REG_EIP
        self.stop = f'unmapped {address:#x} at {uc.reg_read(UC_X86_REG_EIP):#x}'
        return False

    def allocate(self, size):
        address = self.heap
        self.heap += (size+15) & ~15
        self.uc.mem_write(address, bytes(size))
        return address

    def argument(self, index):
        from unicorn.x86_const import UC_X86_REG_ESP
        esp = self.uc.reg_read(UC_X86_REG_ESP)
        return struct.unpack('<I', self.uc.mem_read(esp+4+4*index, 4))[0]

    def finish(self, eax, cleanup=0):
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP
        esp = self.uc.reg_read(UC_X86_REG_ESP)
        target = struct.unpack('<I', self.uc.mem_read(esp, 4))[0]
        self.uc.reg_write(UC_X86_REG_EAX, eax & 0xffffffff)
        self.uc.reg_write(UC_X86_REG_ESP, esp+4+cleanup)
        self.uc.reg_write(UC_X86_REG_EIP, target)

    def dispatch(self, uc, address, size, ignored):
        self.handlers[address]()

    def fopen(self):
        self.position, self.eof = 0, False
        self.finish(tables.FILE_HANDLE)

    def fread(self):
        pointer, item, count, handle = (self.argument(i) for i in range(4))
        got = self.image[self.position:self.position+item*count]
        whole = len(got)//item if item else 0
        got = got[:whole*item]
        self.eof = len(got) < item*count
        if got:
            self.uc.mem_write(pointer, got)
        self.position += len(got)
        self.finish(whole)

    def feof(self):
        self.finish(1 if self.eof else 0)

    def ret0(self):
        self.finish(0)

    def new(self):
        self.finish(self.allocate(self.argument(0)))

    def singleton(self):
        self.finish(self.manager)

    def load_model(self):
        index, folder, name = (self.argument(i) for i in range(3))
        def text(address):
            return bytes(self.uc.mem_read(address, 260)).split(b'\0')[0].decode('latin1')
        self.model_calls.append((index, text(folder), text(name)))
        self.finish(0, 12)

    def call(self, address, arguments, ecx=0, limit=3_000_000_000):
        from unicorn import UcError
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_ECX, UC_X86_REG_EAX, \
            UC_X86_REG_EIP
        uc = self.uc
        uc.context_restore(self.machine.snapshot)
        esp = tables.STACK+tables.STACK_BYTES-0x2000
        uc.mem_write(esp, struct.pack('<I', tables.SENTINEL)+b''.join(struct.pack('<I', a) for a in arguments))
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.reg_write(UC_X86_REG_EBP, 0)
        uc.reg_write(UC_X86_REG_ECX, ecx)
        try:
            uc.emu_start(address, tables.SENTINEL, count=limit)
        except UcError as error:
            raise RuntimeError(f'{address:#x}: {error}; {self.stop}') from error
        if uc.reg_read(UC_X86_REG_EIP) != tables.SENTINEL:
            raise RuntimeError(f'{address:#x} did not return ({self.stop})')
        return uc.reg_read(UC_X86_REG_EAX)


def duplicate_case(machine, image):
    """Mutation: the last record repeats record 0's code with another file name.

    The client's std::map insert keeps the first record; mu_item_find does the
    same. Returns the file name the client's lookup yields for that code.
    """
    count = struct.unpack_from('<I', image, 0)[0]
    first = bytearray(b ^ tables.KEY3[i % 3] for i, b in enumerate(image[4:4+708]))
    clone = bytearray(first)
    clone[268:268+260] = b'duplicate.bmd'.ljust(260, b'\0')
    encoded = bytes(b ^ tables.KEY3[i % 3] for i, b in enumerate(clone))
    payload = bytearray(image[4:4+708*count])
    payload[708*(count-1):] = encoded
    mutated = struct.pack('<I', count)+bytes(payload)+struct.pack('<I', checksum(bytes(payload), 0xe2f1))
    runner = Runner(machine, mutated)
    manager = runner.allocate(0x1000)
    runner.call(MANAGER_CTOR, [], ecx=manager)
    path = runner.allocate(32)
    machine.uc.mem_write(path, b'Data\\Local\\Item.bmd\0')
    runner.call(ITEM_LOADER, [path], ecx=manager)
    code = struct.unpack_from('<I', first, 0)[0]
    pointer = runner.call(FIND, [code], ecx=manager)
    runner.close()
    found = bytes(machine.uc.mem_read(pointer+268, 260)).split(b'\0')[0].decode('latin1') if pointer else None
    expected = first[268:528].split(b'\0')[0].decode('latin1')
    return {'code': code, 'client_file': found, 'first_record_file': expected, 'match': found == expected}


def checksum(data, key):
    result = (key << 9) & 0xffffffff
    for offset in range(0, len(data)-3, 4):
        word = struct.unpack_from('<I', data, offset)[0]
        result = result ^ word if ((offset >> 2)+key) % 2 == 0 else (result+word) & 0xffffffff
        if offset % 16 == 0:
            result = (((key+result) & 0xffffffff) >> (((offset >> 2) % 8)+1)) ^ result
    return result


def authored_models(binary, item_file):
    out = subprocess.run([str(binary), 'item-models', str(item_file), '--json'], check=True, capture_output=True)
    return json.loads(out.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, default=pins.TEXT.default())
    parser.add_argument('--data', type=Path, default=pins.DATA.default())
    parser.add_argument('--feature', type=Path, default=pins.FEATURE.default())
    parser.add_argument('--game-root', type=Path, default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--mu-data', type=Path, default=ROOT/'native/build/mu-data')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = tables.load_pinned(args.text, tables.TEXT_BYTES, tables.TEXT_SHA256, 'restored text')
    data = tables.load_pinned(args.data, tables.DATA_BYTES, tables.DATA_SHA256, 'second image section')
    feature = tables.load_pinned(args.feature, 4, tables.FEATURE_SHA256, 'CPU feature word')
    if not args.game_root:
        raise SystemExit('--game-root or MU_GAME_ROOT is required')
    item_file = next(p for p in (Path(args.game_root)/'Data/Local').iterdir() if p.name.lower() == 'item.bmd')
    image = item_file.read_bytes()
    bodies = {}
    for name, (start, end, digest) in BODIES.items():
        actual = hashlib.sha256(text[start-tables.TEXT_BASE:end-tables.TEXT_BASE]).hexdigest()
        if actual != digest:
            raise ValueError(f'captured {name} body does not match its pinned digest')
        bodies[name] = {'start': hex(start), 'end_exclusive': hex(end), 'sha256': actual}
    machine = tables.Machine(text, data, feature)
    duplicate = duplicate_case(machine, image)
    runner = Runner(machine, image)

    manager = runner.allocate(0x1000)
    runner.call(MANAGER_CTOR, [], ecx=manager)
    path = runner.allocate(32)
    machine.uc.mem_write(path, b'Data\\Local\\Item.bmd\0')
    runner.call(ITEM_LOADER, [path], ecx=manager)
    runner.manager = manager

    count = struct.unpack_from('<I', image, 0)[0]
    codes = []
    for index in range(count):
        record = bytes(b ^ tables.KEY3[i % 3] for i, b in enumerate(image[4+708*index:4+708*index+12]))
        codes.append(struct.unpack_from('<I', record, 0)[0])
    found = {}
    for code in sorted(set(codes)) + [0x7fffffff, 0xffffffff]:
        pointer = runner.call(FIND, [code], ecx=manager)
        if pointer:
            raw = bytes(machine.uc.mem_read(pointer, 0x2c4))
            found[code] = {'index_field': struct.unpack_from('<I', raw, 0)[0],
                           'folder': raw[8:268].split(b'\0')[0].decode('latin1'),
                           'file': raw[268:528].split(b'\0')[0].decode('latin1'),
                           'name_sha256': hashlib.sha256(raw[528:592].split(b'\0')[0]).hexdigest()}
        else:
            found[code] = None

    cache_object = runner.allocate(0x40)
    runner.call(CACHE_CTOR, [], ecx=cache_object)
    getter = {}
    for model in list(range(-2, MODEL_LIMIT+3)):
        runner.model_calls.clear()
        result = runner.call(GET_MODEL, [model & 0xffffffff], ecx=cache_object)
        calls = list(runner.model_calls)
        getter[model] = {'returned': 'null' if result == 0 else 'object', 'loader_calls': calls}
    runner.close()

    authored = authored_models(args.mu_data, item_file)
    by_code = {e['code']: e for e in authored['items']}
    mismatches = []
    for code, entry in found.items():
        mine = by_code.get(code)
        if entry is None:
            if mine is not None:
                mismatches.append(('find-missing', code))
            continue
        if mine is None or (mine['folder'], mine['file']) != (entry['folder'], entry['file']) \
                or entry['index_field'] != code:
            mismatches.append(('find', code, entry, mine))
    loader_calls = 0
    for model, outcome in getter.items():
        code = model-MODEL_BASE
        mine = by_code.get(code) if 0 <= model <= MODEL_LIMIT else None
        expected = [(model, mine['folder'], mine['file'])] if mine else []
        observed = [tuple(c) for c in outcome['loader_calls']]
        loader_calls += len(observed)
        if observed != expected:
            mismatches.append(('getter', model, observed, expected))
        # a valid index with no script yields an empty model object; out of range yields null
        if not mine:
            want = 'object' if 0 <= model <= MODEL_LIMIT else 'null'
            if outcome['returned'] != want:
                mismatches.append(('getter-return', model, outcome['returned'], want))
    report = {'item_file_sha256': hashlib.sha256(image).hexdigest(), 'records': count, 'bodies': bodies,
              'find_queries': len(found), 'found': sum(1 for v in found.values() if v),
              'getter_queries': len(getter), 'model_loader_calls': loader_calls,
              'empty_model_indexes': sum(1 for m, o in getter.items() if o['returned'] == 'object' and not o['loader_calls']),
              'duplicate_code_case': duplicate,
              'mismatches': mismatches[:20], 'mismatch_count': len(mismatches)}
    print(json.dumps({k: v for k, v in report.items() if k != 'mismatches'}))
    if mismatches:
        print(json.dumps(mismatches[:5]))
    if not duplicate['match']:
        mismatches.append(('duplicate', duplicate))
        report['mismatch_count'] = len(mismatches)
    if args.output:
        args.output.write_text(json.dumps(report, indent=1)+'\n')
    return 0 if not mismatches else 1


if __name__ == '__main__':
    sys.exit(main())
