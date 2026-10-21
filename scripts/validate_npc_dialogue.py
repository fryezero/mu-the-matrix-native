#!/usr/bin/env python3
"""Validate the NPC dialogue manager and the npcdialogue window's choice against the client (NATIVE-LANG-002).

Actual client code runs in Unicorn over the pinned restored text (the
machine of scripts/validate_data_tables.py with the CRT file and heap calls
modelled, as in scripts/validate_item_models.py):

1. the manager constructor 0x00fdc8bd, then the loaders 0x00fdcbb4
   (NPCDialogue.bmd), 0x00fdccc1 (QuestProgress.bmd) and 0x00fdcdc8
   (QuestWords.bmd) read the installed files through the modelled fopen/fread
   and decode them with the client's 0x00976855; their std::map inserts run;
2. on that manager (its +0x1c, the dialogue NPC, written directly: 0x00fdc96c
   also copies the NPC's name from the Lang table) run the lookups
   0x00fdc9c1 text(id), 0x00fdca1b state text, 0x00fdca92 option text and
   0x00fdcb1f option next for every NPC of the file, NPC 0 and absent NPCs,
   states 0..30, 999 and absent states, options 0..9;
3. the window's choice handler 0x00be906d (quest-list mode off) runs on a
   window object with the state and the choice: its call of the state display
   0x00be86de (argument recorded, then returned) or the jump-table case of a
   server request (recorded, execution resumed at the handler's exit
   0x00be9907) is the observed result.

Each result is compared with reconstructed/npc/npc_dialogue.c (libnpc, ctypes)
parsing the same files decoded by native/build/mu-data.  Mutations: planted
mistakes in the decoded copy the C reads (a text, an option pair, the order
of a repeated key) must be detected; a planted repeated key and an option
next beyond 920 given to both sides are positive controls.  Decoded game text
is never written out; the report holds counts and the first mismatches.
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
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tables = load_module('validate_data_tables', ROOT/'scripts/validate_data_tables.py')
models = load_module('validate_item_models', ROOT/'scripts/validate_item_models.py')

MANAGER_CTOR, LOAD_DIALOGUE, LOAD_PROGRESS, LOAD_WORDS = 0x00fdc8bd, 0x00fdcbb4, 0x00fdccc1, 0x00fdcdc8
TEXT, STATE_TEXT, OPTION_TEXT, OPTION_NEXT = 0x00fdc9c1, 0x00fdca1b, 0x00fdca92, 0x00fdcb1f
SELECT, SHOW_STATE, SELECT_EXIT, CASE_TABLE = 0x00be906d, 0x00be86de, 0x00be9907, 0x00be9915
FREE_BASE, MANAGER = 0x019a4d50, 0x01ec9858
FILES = {'NPCDialogue.bmd': 'npcdialogue.bmd', 'QuestProgress.bmd': 'questprogress.bmd',
         'QuestWords.bmd': 'questwords.bmd'}
BODIES = {  # start, exclusive end, SHA-256 of the captured bytes (checked before use)
    'manager_ctor': (0x00fdc8bd, 0x00fdc938),
    'lookups': (0x00fdc9c1, 0x00fdcbb4),
    'loaders': (0x00fdcbb4, 0x00fdcf40),
    'select': (0x00be906d, 0x00be9915),
}


class Runner(models.Runner):
    """models.Runner with several files (fopen picks the image by the path's file name) and code hooks."""

    def __init__(self, machine, images):
        super().__init__(machine, b'')
        self.images, self.current = images, b''
        self.extra_hooks = []
        # _free_base 0x019a4d50 (reached through operator delete) calls HeapFree: modelled as a no-op
        self.hook(FREE_BASE, lambda uc, address, size, user: self.finish(0))

    def fopen(self):
        path = bytes(self.uc.mem_read(self.argument(0), 260)).split(b'\0')[0].decode('latin1')
        name = path.replace('\\', '/').split('/')[-1]
        self.image = self.images.get(name, b'')
        self.position, self.eof = 0, False
        self.finish(tables.FILE_HANDLE if name in self.images else 0)

    def hook(self, address, handler):
        from unicorn import UC_HOOK_CODE
        self.extra_hooks.append(self.uc.hook_add(UC_HOOK_CODE, handler, begin=address, end=address))

    def close(self):
        for h in self.extra_hooks:
            self.uc.hook_del(h)
        super().close()


def cstr(runner, address, limit=4096):
    if not address:
        return None
    return bytes(runner.uc.mem_read(address, limit)).split(b'\0')[0]


def i32(value):
    return struct.unpack('<i', struct.pack('<I', value & 0xffffffff))[0]


class Native:
    def __init__(self, lib):
        self.lib = L = ctypes.CDLL(str(lib))
        self.size = 64
        L.mu_dlg_parse_records.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        L.mu_dlg_parse_records.restype = ctypes.c_long
        L.mu_dlg_parse_words.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        L.mu_dlg_parse_words.restype = ctypes.c_long
        L.mu_dlg_free.argtypes = [ctypes.c_void_p]
        L.mu_dlg_set_npc.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_dlg_text.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_dlg_text.restype = ctypes.c_char_p
        L.mu_dlg_state_text.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_dlg_state_text.restype = ctypes.c_char_p
        L.mu_dlg_option_text.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
        L.mu_dlg_option_text.restype = ctypes.c_char_p
        L.mu_dlg_option_next.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
        L.mu_dlg_option_next.restype = ctypes.c_int32
        L.mu_dlg_select.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
        L.mu_dlg_select.restype = ctypes.c_uint64

    def tables(self, records, words):
        t = ctypes.create_string_buffer(self.size)
        self.lib.mu_dlg_parse_records(t, records, len(records))
        self.lib.mu_dlg_parse_words(t, words, len(words))
        return t

    def select(self, t, state, choice):
        v = self.lib.mu_dlg_select(t, state, choice)
        kind, value = v & 0xffffffff, i32(v >> 32)
        return ('action' if kind == 1 else 'show', value)


class Family:
    def __init__(self, name):
        self.name, self.cases, self.mismatches, self.examples = name, 0, 0, []
        self.kinds = {}

    def check(self, label, client, native):
        self.cases += 1
        if client != native:
            self.mismatches += 1
            if len(self.examples) < 5:
                self.examples.append({'case': repr(label), 'client': repr(client)[:120], 'native': repr(native)[:120]})

    def summary(self):
        out = {'cases': self.cases, 'mismatches': self.mismatches, 'examples': self.examples}
        if self.kinds:
            out['client_results'] = dict(sorted(self.kinds.items()))
        return out


def build_manager(machine, images):
    runner = Runner(machine, images)
    manager = MANAGER        # the singleton's own address: the window code addresses it directly
    runner.uc.mem_write(manager, bytes(0x40))
    runner.call(MANAGER_CTOR, [], ecx=manager)
    for loader, name in ((LOAD_DIALOGUE, 'NPCDialogue.bmd'), (LOAD_PROGRESS, 'QuestProgress.bmd'),
                         (LOAD_WORDS, 'QuestWords.bmd')):
        path = runner.allocate(64)
        runner.uc.mem_write(path, b'Data\\Local\\' + name.encode() + b'\0')
        runner.call(loader, [path], ecx=manager)
    return runner, manager


def install_select_hooks(runner, seen):
    """0x00be86de: record its argument and return (thiscall, ret 4); the 20 server-request cases: record and jump
    to the handler's exit."""
    from unicorn.x86_const import UC_X86_REG_EIP

    def show(uc, address, size, user):
        seen.append(('show', i32(runner.argument(0))))
        runner.finish(0, 4)
    runner.hook(SHOW_STATE, show)
    targets = struct.unpack('<20I', runner.uc.mem_read(CASE_TABLE, 80))
    for k, target in enumerate(targets):
        def case(uc, address, size, user, action=901 + k):
            seen.append(('action', action))
            uc.reg_write(UC_X86_REG_EIP, SELECT_EXIT)
        runner.hook(target, case)
    return targets


def run_cases(runner, manager, native, t, keys, word_ids, rng, families, select_window):
    npcs = sorted({k >> 16 for k in keys})
    absent_npcs = [n for n in rng.sample(range(1, 0x400), 40) if n not in npcs][:6]
    states_of = {}
    for k in keys:
        states_of.setdefault(k >> 16, set()).add(k & 0xffff)
    uc = runner.uc
    text_f, state_f, opt_f, next_f, sel_f = families
    ids = sorted(set(word_ids) | set(rng.sample(range(-5, 25000), 300)))
    for wid in ids:
        text_f.check(wid, cstr(runner, runner.call(TEXT, [wid & 0xffffffff], ecx=manager)),
                     native.lib.mu_dlg_text(t, wid))
    for npc in [0] + npcs + absent_npcs:
        uc.mem_write(manager + 0x1c, struct.pack('<i', npc))
        native.lib.mu_dlg_set_npc(t, npc)
        states = sorted(set(range(0, 31)) | {999, 1000, 0xffff, -1} | states_of.get(npc, set()))
        for state in states:
            state_f.check((npc, state), cstr(runner, runner.call(STATE_TEXT, [state & 0xffffffff], ecx=manager)),
                          native.lib.mu_dlg_state_text(t, state))
            for i in range(10):
                opt_f.check((npc, state, i),
                            cstr(runner, runner.call(OPTION_TEXT, [state & 0xffffffff, i], ecx=manager)),
                            native.lib.mu_dlg_option_text(t, state, i))
                next_f.check((npc, state, i), i32(runner.call(OPTION_NEXT, [state & 0xffffffff, i], ecx=manager)),
                             native.lib.mu_dlg_option_next(t, state, i))
                if select_window and (state in states_of.get(npc, ()) or i == 0):
                    window, seen = select_window
                    seen.clear()
                    uc.mem_write(window, bytes(0x1d80))
                    uc.mem_write(window + 0x1cd8, struct.pack('<i', i + 1))
                    uc.mem_write(window + 0x1d08, struct.pack('<i', state))
                    runner.call(SELECT, [], ecx=window)
                    client = seen[0] if len(seen) == 1 else tuple(seen)
                    sel_f.check((npc, state, i), client, native.select(t, state, i))
                    kind = 'action' if client[0] == 'action' else ('show_999' if client == ('show', 999) else 'show')
                    sel_f.kinds[kind] = sel_f.kinds.get(kind, 0) + 1


def decode(mu_data, path, work):
    out = Path(work)/(path.name + '.dec')
    subprocess.run([str(mu_data), 'decode', str(path), '--out', str(out)], check=True, capture_output=True)
    return out.read_bytes()


def find_file(root, name):
    folder = Path(root)/'Data/Local'
    for p in folder.iterdir():
        if p.name.lower() == name.lower():
            return p
    raise SystemExit(f'{name} not found under {folder}')


def encode_records(decoded):
    """The client's file form of decoded 88-byte records (per-record XOR 0x00976855 with FC CF AB)."""
    out = bytearray()
    for k in range(0, len(decoded), 88):
        out += bytes(b ^ tables.KEY3[i % 3] for i, b in enumerate(decoded[k:k + 88]))
    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--text', type=Path, default=Path(os.environ.get(
        'MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin')))
    parser.add_argument('--data', type=Path, default=Path(os.environ.get(
        'MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin')))
    parser.add_argument('--feature', type=Path, default=ROOT/'evidence/image-data-run10/math-capture-10/cpu-features.bin')
    parser.add_argument('--game-root', type=Path, default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--mu-data', type=Path, default=ROOT/'native/build/mu-data')
    parser.add_argument('--libnpc', type=Path, default=ROOT/'reconstructed/npc/libnpc.dylib')
    parser.add_argument('--seed', type=int, default=0x4e50)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.game_root:
        raise SystemExit('--game-root or MU_GAME_ROOT is required')
    started = time.time()
    text = tables.load_pinned(args.text, tables.TEXT_BYTES, tables.TEXT_SHA256, 'restored text')
    data = tables.load_pinned(args.data, tables.DATA_BYTES, tables.DATA_SHA256, 'second image section')
    feature_path = args.feature if args.feature.exists() else \
        Path.home()/'Documents/main-exe-study/evidence/image-data-run10/math-capture-10/cpu-features.bin'
    feature = tables.load_pinned(feature_path, 4, tables.FEATURE_SHA256, 'CPU feature word')
    bodies = {name: {'start': hex(a), 'end_exclusive': hex(b),
                     'sha256': hashlib.sha256(text[a - tables.TEXT_BASE:b - tables.TEXT_BASE]).hexdigest()}
              for name, (a, b) in BODIES.items()}
    files = {name: find_file(args.game_root, lower) for name, lower in FILES.items()}
    images = {name: p.read_bytes() for name, p in files.items()}
    rng = random.Random(args.seed)
    report = {'bodies': bodies, 'families': {}}
    with tempfile.TemporaryDirectory() as work:
        dec_records = decode(args.mu_data, files['NPCDialogue.bmd'], work)
        dec_words = decode(args.mu_data, files['QuestWords.bmd'], work)
        native = Native(args.libnpc)
        t = native.tables(dec_records, dec_words)
        keys = [struct.unpack_from('<i', dec_records, k)[0] for k in range(0, len(dec_records) - 87, 88)]
        word_ids, off = [], 0
        while off + 6 <= len(dec_words):
            wid, length = struct.unpack_from('<Ih', dec_words, off)
            word_ids.append(i32(wid))
            off += 6 + max(length, 0)
        machine = tables.Machine(text, data, feature)
        runner, manager = build_manager(machine, images)
        seen = []
        install_select_hooks(runner, seen)
        window = runner.allocate(0x1d80)
        fams = [Family(n) for n in ('text', 'state_text', 'option_text', 'option_next', 'select')]
        run_cases(runner, manager, native, t, keys, word_ids, rng, fams, (window, seen))
        for f in fams:
            report['families'][f.name] = f.summary()
            print(f.name, json.dumps({k: v for k, v in f.summary().items() if k != 'examples'}))
        report['records'], report['texts'] = len(set(keys)), len(set(word_ids))
        runner.close()
        if args.mutations:
            report['mutations'] = mutations(machine, images, native, dec_records, dec_words, keys, rng)
            print('mutations', json.dumps(report['mutations']))
    report['seconds'] = round(time.time() - started, 1)
    total = sum(f['mismatches'] for f in report['families'].values())
    report['mismatches'] = total
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    if total:
        for name, fam in report['families'].items():
            if fam['mismatches']:
                print(name, json.dumps(fam['examples'], indent=1))
        raise SystemExit(f'{total} mismatches')
    if args.mutations and not all(v == 'caught' or v == 'equal' for v in report['mutations'].values()):
        raise SystemExit('a mutation was not handled as expected')
    print(f'all cases match ({report["seconds"]} s)')


def mutations(machine, images, native, dec_records, dec_words, keys, rng):
    """Negative cases: the C reads a changed copy (the client the installed file): a mismatch must appear.
    Positive controls: the same change on both sides: no mismatch."""
    out = {}

    def compare(native_records, native_words, client_images, label, expect):
        t = native.tables(native_records, native_words)
        runner, manager = build_manager(machine, client_images)
        seen = []
        install_select_hooks(runner, seen)
        window = runner.allocate(0x1d80)
        fams = [Family(n) for n in ('text', 'state_text', 'option_text', 'option_next', 'select')]
        k2 = [struct.unpack_from('<i', native_records, k)[0] for k in range(0, len(native_records) - 87, 88)]
        ids, off = [], 0
        while off + 6 <= len(native_words):
            wid, length = struct.unpack_from('<Ih', native_words, off)
            ids.append(i32(wid))
            off += 6 + max(length, 0)
        run_cases(runner, manager, native, t, k2[:12], ids[:200], random.Random(1), fams, (window, seen))
        runner.close()
        native.lib.mu_dlg_free(t)
        bad = sum(f.mismatches for f in fams)
        out[label] = ('caught' if bad else 'missed') if expect == 'caught' else ('equal' if not bad else 'differs')

    # 1. a text of the first record's state changed in the C's copy
    first_text = struct.unpack_from('<i', dec_records, 4)[0]
    words = bytearray(dec_words)
    off = 0
    while off + 6 <= len(words):
        wid, length = struct.unpack_from('<Ih', words, off)
        if i32(wid) == first_text and length > 2:
            words[off + 6] ^= 0x20
            break
        off += 6 + max(length, 0)
    compare(dec_records, bytes(words), images, 'text_changed', 'caught')
    # 2. the first two option pairs of a record with two options swapped
    recs = bytearray(dec_records)
    for k in range(0, len(recs) - 87, 88):
        if struct.unpack_from('<i', recs, k + 16)[0]:
            a, b = recs[k + 8:k + 16], recs[k + 16:k + 24]
            recs[k + 8:k + 16], recs[k + 16:k + 24] = b, a
            break
    compare(bytes(recs), dec_words, images, 'option_pairs_swapped', 'caught')
    # 3. a repeated first key with another text id: both sides keep the first record (positive control) ...
    clone = bytearray(dec_records[:88])
    struct.pack_into('<i', clone, 4, struct.unpack_from('<i', clone, 4)[0] + 1)
    both = dec_records + bytes(clone)
    client = dict(images, **{'NPCDialogue.bmd': encode_records(both)})
    compare(both, dec_words, client, 'repeated_key_first_wins', 'equal')
    # ... and the C given the repeat first (as if the last record won) differs
    compare(bytes(clone) + dec_records, dec_words, client, 'repeated_key_last_wins', 'caught')
    # 4. an option next beyond 920 on both sides: the choice shows state 999 (positive control)
    recs = bytearray(dec_records)
    struct.pack_into('<i', recs, 12, 950)
    compare(bytes(recs), dec_words, dict(images, **{'NPCDialogue.bmd': encode_records(bytes(recs))}),
            'next_950_fallback', 'equal')
    return out


if __name__ == '__main__':
    main()
