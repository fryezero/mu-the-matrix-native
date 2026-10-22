#!/usr/bin/env python3
"""Compare F6 56/7B path resumes and the actual MyQuestInfo tab registration in Unicorn.

Original F6 56 inline block 0x0128a52d..0x0128a66b and 7B handler
0x012534ae run over random PATH_t flags, signed targets and service results.
PathFinding2-long, GetPath and SendMove are recording stubs with independent
answers. Their call order/arguments and the final flag/move byte must match
quest_move.c. No packet payload fields are consumed by either handler.

MyQuestInfo's real ctor 0x00be3710 runs with the existing snapshot/STL
machine. Base window/derived tab construction and shared-pointer assignment
are modelled; actual map insertion and key selection run as client code.
It registers exactly 0..4, so an EventMap label in InitText does not establish
an event tab in this build.
"""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import client_ui_machine as cm
import validate_lang as vl
import validate_map as vm
import validate_quest as vq


class State(C.Structure):
    _fields_ = [('flag', C.c_int32), ('x', C.c_int32), ('y', C.c_int32),
                ('tx', C.c_int16), ('ty', C.c_int16), ('move', C.c_uint8)]


FIND = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_int32, C.c_int32, C.c_int32, C.c_int32)
RESULT = C.CFUNCTYPE(C.c_int, C.c_void_p)


class Host(C.Structure):
    _fields_ = [('user', C.c_void_p), ('find', FIND), ('next', RESULT), ('send', RESULT)]


def run_answers(text, data, lib, cases, seed):
    L = C.CDLL(str(lib))
    L.mu_quest_resume_path.argtypes = [C.POINTER(State), C.POINTER(Host), C.c_uint8]
    m = cm.Machine(text, data)
    m.allow((0x0128a52d, 0x0128a66b), (0x012534ae, 0x01253577))
    log, answers = [], []
    def find(mm):
        sx, sy, tx, ty, error, path, distance, level = mm.args(8)
        log.append(('find', vm.i32(sx), vm.i32(sy), vm.i32(tx), vm.i32(ty), error, distance, level))
        return answers[0]
    m.stub(0x012b104c, find, 0)
    m.stub(0x0129cc44, lambda mm: log.append(('next',)) or answers[1], 0)
    m.stub(0x016b5cd0, lambda mm: log.append(('send',)) or answers[2], 0)
    def stop(mm):
        mm.uc.reg_write(cm.UC_X86_REG_EIP, cm.RETURN_SENTINEL)
        return cm.REDIRECT
    m.stub(0x0128a66b, stop, 0)
    rng, fam = random.Random(seed), vl.Family('move_answers')
    for k in range(cases):
        sub = 0x56 if k % 2 else 0x7b
        flag = rng.choice([0, 1, 1, 1, 2, 3, -1])
        sx, sy = rng.randrange(256), rng.randrange(256)
        tx, ty = rng.choice([-32768, -1, 0, 255, 32767]), rng.randrange(-32768, 32768)
        move = rng.randrange(256)
        answers[:] = [rng.choice([0, 1, 2, 0x100, 0x101, -1]) for _ in range(3)]
        m.reset()
        log.clear()
        hero = m.alloc(0x3800, define=True)
        m.put32(0x0a39d754, hero)
        m.put32(hero + 0x31c8, flag)
        m.put32(hero + 0x180, sx)
        m.put32(hero + 0x184, sy)
        m.write(hero + 0x31cc, struct.pack('<hh', tx, ty))
        m.write(hero + 0x39, bytes([move]))
        m.call(0x0128a52d if sub == 0x56 else 0x012534ae)
        client = (m.u32(hero + 0x31c8), m.read(hero + 0x39, 1)[0], list(log))
        native_log = []
        h = Host(None,
                 FIND(lambda u, x, y, a, b: native_log.append(('find', x, y, a, b, 0, 0, 4)) or answers[0]),
                 RESULT(lambda u: native_log.append(('next',)) or answers[1]),
                 RESULT(lambda u: native_log.append(('send',)) or answers[2]))
        state = State(flag, sx, sy, tx, ty, move)
        L.mu_quest_resume_path(C.byref(state), C.byref(h), sub)
        fam.check((k, sub, answers[:]), client, (state.flag & 0xffffffff, state.move, native_log))
    return fam


def run_tabs(text, data, snap):
    m = vq.QuestMachine(text, data, snap)
    m.allow((cm.TEXT_BASE, cm.TEXT_BASE + len(text)))
    vq.install_stubs(m)
    m.setup()
    m.stub(0x00aad53a, lambda mm: mm.uc.reg_read(cm.UC_X86_REG_ECX), 0)
    m.stub(0x00ab02b7, lambda mm: mm.alloc(mm.args(1)[0], define=True), 0)
    m.stub(0x00be4b5e, lambda mm: mm.uc.reg_read(cm.UC_X86_REG_ECX), 4)
    m.stub(0x00ab02fd, lambda mm: 0, 4)
    constructors = []
    for address, category in ((0x00d4c27a, 0), (0x00d4e90b, 1), (0x00d4f16e, -1)):
        def ctor(mm, cat=category):
            constructors.append(cat if cat >= 0 else mm.args(1)[0])
            return mm.uc.reg_read(cm.UC_X86_REG_ECX)
        m.stub(address, ctor, 4 if category == -1 else 0)
    window = m.alloc(0x100, define=True)
    m.call(0x00be3710, ecx=window)
    keys = [key for key, _ in vq.tree(m, window + 0x80)]
    assert keys == list(range(5)), keys
    return {'cases': 1, 'keys': keys, 'event_tab_registered': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(vl.DEFAULT_TEXT)))
    p.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(vl.DEFAULT_DATA)))
    p.add_argument('--snapshot', required=True)
    p.add_argument('--cases', type=int, default=2000)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    for path, digest in ((a.text, vl.TEXT_SHA256), (a.data, vl.DATA_SHA256)):
        if vl.sha256_file(path) != digest:
            raise SystemExit(f'{path}: unexpected SHA-256')
    text, data = Path(a.text).read_bytes(), Path(a.data).read_bytes()
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/quest')], check=True)
    lib = ROOT / 'reconstructed/quest/libquest.dylib'
    fam = run_answers(text, data, lib, a.cases, 1)
    report = {'text_sha256': vl.TEXT_SHA256, 'data_sha256': vl.DATA_SHA256,
              'move_answers': fam.summary(), 'tabs': run_tabs(text, data, vm.plain.Snapshot.load(a.snapshot))}
    if a.mutations:
        with tempfile.TemporaryDirectory() as tmp:
            report['mutations'] = {}
            for mutation in (12, 13):
                out = Path(tmp) / f'quest-{mutation}.dylib'
                subprocess.run(['cc', '-std=c11', '-O2', '-shared', '-fPIC', '-ffp-contract=off',
                                f'-DMU_QUEST_MUTATION={mutation}',
                                *map(str, sorted((ROOT / 'reconstructed/quest').glob('quest_*.c'))), '-o', str(out)],
                               check=True)
                report['mutations'][str(mutation)] = run_answers(text, data, out, 200, 1).mismatches > 0
        assert all(report['mutations'].values()), report['mutations']
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return int(fam.mismatches != 0)


if __name__ == '__main__':
    sys.exit(main())
