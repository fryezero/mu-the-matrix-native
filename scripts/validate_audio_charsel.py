#!/usr/bin/env python3
"""AUDIO-002E: complete scene-5 tick gates and compiled sound-site adapter.

Runs the pinned tick unchanged with the existing charsel recording services.
Original SND_Play return addresses supply sites independently of the adapter.
No account, packet, GFx movie or FMOD body is executed by this comparison.
"""
import argparse
import ctypes as C
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import pins
import validate_charsel as vc

ROOT = Path(__file__).resolve().parents[1]


class Decision(C.Structure):
    _fields_ = [('routine', C.c_uint32), ('site', C.c_uint32), ('id', C.c_int32),
                ('key', C.c_int32), ('loop', C.c_int32)]


WRAPPER = r'''
#include "mu_charsel_audio.h"
typedef struct decision { unsigned routine, site; int id, key, loop; } decision;
int decide(mu_charsel_tick *t, decision *out) {
    mu_charsel_log log = {0}; mu_charsel_tick_step(t, &log); int n = 0;
    for (int i = 0; i < log.count; ++i) {
        mu_cue cue;
        if (mu_charsel_audio_cue(&log, i, &cue))
            out[n++] = (decision){cue.handler, cue.u.sound.site, cue.u.sound.id,
                                  cue.u.sound.at_key, cue.u.sound.loop};
    }
    return n;
}
'''


def build(folder, name, header, source):
    path = folder / name
    path.mkdir()
    (path / 'wrapper.c').write_text(WRAPPER)
    (path / 'mu_charsel_audio.h').write_text(header.replace('"../../reconstructed/charsel/charsel.h"',
                                                         '"charsel.h"').replace('"../session/mu_cue.h"', '"mu_cue.h"'))
    (path / 'charsel.c').write_text(source)
    out = path / 'adapter.dylib'
    subprocess.run(['cc', '-shared', '-O2', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-I', str(path), '-I', str(ROOT / 'reconstructed/charsel'),
                    '-I', str(ROOT / 'native/session'), str(path / 'wrapper.c'),
                    str(path / 'charsel.c'), '-lm', '-o', str(out)], check=True)
    lib = C.CDLL(str(out))
    lib.decide.argtypes = [C.POINTER(vc.Tick), C.POINTER(Decision)]
    return lib


class Harness(vc.Harness):
    def _record(self, address, count, **kw):
        super()._record(address, count, **kw)
        if address == 0x00a6ac96:
            def sound(m):
                ret = struct.unpack('<I', m.uc.mem_read(m.uc.reg_read(vc.cm.UC_X86_REG_ESP), 4))[0]
                args = m.args(3)
                assert args[1:] == [0, 0], args
                self.sounds.append((0x01856e6c, ret - 5, args[0], -2, args[2]))
                return 0
            self.m.stub(address, sound, 0)

    def run(self, t):
        self.sounds = []
        case = self.begin({})
        m = self.m
        for addr, value in [(0x01d1df70, t.scene), (0x06fca2c4, t.protocol),
                            (0x01cf1864, t.selected), (0x01cf1154, t.shown)]:
            m.write(addr, struct.pack('<i', value))
        for addr, value in [(0x0bdc5ca2, t.initialised), (0x01d22d1e, t.global_1d22d1e),
                            (0x06fca007, t.global_6fca007)]:
            m.write(addr, bytes([value]))
        m.write(0x01d22c7c, struct.pack('<I', vc.ID['MENU']))
        for addr, value in [(vc.ID['GFX'] + 0x90, vc.ID['GFX_MOVIE']),
                            (vc.ID['GFX'] + 0x22c, vc.ID['GFX_22C'])]:
            m.uc.mem_write(addr, struct.pack('<I', value))
        for addr, value in [(vc.ID['MENU'] + 0x1c, t.gfx_menu_flag),
                            (vc.ID['INPUT'] + 0x31, t.input_byte_31),
                            (vc.ID['UIMNG'] + 0x464, t.ui_byte_464),
                            (vc.ID['UIMNG'] + 0x65b9, t.ui_byte_65b9)]:
            m.uc.mem_write(addr, bytes([value]))
        m.uc.mem_write(vc.ID['GFX_22C'] + 0x78, bytes([t.gfx_flag_78, t.gfx_flag_79]))
        case.busy = [t.gfx_busy, t.gfx_busy_enter if t.key_enter and not t.input_byte_31 else t.gfx_busy_escape]
        case.keys = {0x0d: t.key_enter, 0x1b: t.key_escape}
        case.enter_refused = t.enter_refused
        m.call(0x01856e6c, [])
        state = (m.read(0x0bdc5ca2, 1)[0], struct.unpack('<i', m.read(0x01cf1864, 4))[0],
                 bytes(m.uc.mem_read(vc.ID['UIMNG'] + 0x65b9, 1))[0])
        return self.sounds[:], state


def corpus():
    # Every combination of the relevant byte gates; include non-bool busy=2,
    # selection limits, shown substitution and refused Enter after the sound.
    for family, fields in [
        ('enter', ['input_byte_31', 'gfx_busy_enter', 'gfx_flag_79', 'global_1d22d1e',
                   'global_6fca007', 'gfx_flag_78', 'ui_byte_464']),
        ('escape', ['input_byte_31', 'gfx_busy_escape', 'global_6fca007',
                    'gfx_flag_78', 'global_1d22d1e', 'gfx_menu_flag'])]:
        for bits in itertools.product([0, 1], repeat=len(fields)):
            variants = itertools.product([-2, -1, 0, 9, 10], [-1, 9, 11], [0, 1, 2]) if family == 'enter' else [(0, 0, 0)]
            for selected, shown, refused in variants:
                t = vc.Tick(scene=5, initialised=1, protocol=0x33, selected=selected, shown=shown,
                            key_enter=family == 'enter', key_escape=1, enter_refused=refused, ui_byte_65b9=1)
                for field, bit in zip(fields, bits):
                    setattr(t, field, bit)
                yield family, t
    for protocol, busy, initialised, enter, escape, panel in itertools.product(
            [0x32, 0x33, 0x35], [0, 1, 2], [0, 1], [0, 1], [0, 1], [0, 1]):
        yield 'common', vc.Tick(scene=5, protocol=protocol, gfx_busy=busy, initialised=initialised,
                                selected=0, shown=0, key_enter=enter, key_escape=escape, gfx_flag_78=panel)


def check(lib, rows):
    for image, want, state in rows:
        t = vc.Tick.from_buffer_copy(image)
        out = (Decision * 8)()
        n = lib.decide(C.byref(t), out)
        got = [tuple(getattr(out[i], k) for k, _ in Decision._fields_) for i in range(n)]
        if got != want or (t.initialised, t.selected, t.ui_byte_65b9) != state:
            return {'input': list(image), 'want': want, 'got': got}
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--report')
    a = p.parse_args()
    text, data = pins.TEXT.read(), pins.DATA.read()
    start, end, _ = vc.ROUTINES['tick']
    digest = hashlib.sha256(text[start - vc.cm.TEXT_BASE:end - vc.cm.TEXT_BASE]).hexdigest()
    assert digest == vc.PINNED['tick']
    h = Harness(text, data)
    rows, families, sites = [], {}, {}
    for family, t in corpus():
        want, state = h.run(t)
        rows.append((bytes(t), want, state))
        families[family] = families.get(family, 0) + 1
        for row in want:
            sites[hex(row[1])] = sites.get(hex(row[1]), 0) + 1
    assert set(sites) == {'0x1857064', '0x1857163', '0x18571e6'}, sites
    header = (ROOT / 'native/core/mu_charsel_audio.h').read_text()
    source = (ROOT / 'reconstructed/charsel/charsel.c').read_text()
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'tick_sha256': digest,
              'families': families, 'cases': len(rows), 'mismatches': 0, 'sites': sites, 'mutants': {}}
    with tempfile.TemporaryDirectory(prefix='audio-charsel-') as folder:
        tmp = Path(folder)
        assert check(build(tmp, 'base', header, source), rows) is None
        if a.mutations:
            plants = [
                ('enter-site', 'header', '0x01857064u', '0x01857163u'),
                ('menu-site', 'header', '0x01857163u', '0x018571e6u'),
                ('panel-site', 'header', '0x018571e6u', '0x01857064u'),
                ('id', 'header', 'cue->u.sound.id = 25', 'cue->u.sound.id = 26'),
                ('object', 'header', 'at_key = -2', 'at_key = -1'),
                ('loop', 'header', 'cue->kind = MU_CUE_SOUND;', 'cue->kind = MU_CUE_SOUND; cue->u.sound.loop = 1;'),
                ('enter-selection', 'source', 't->selected >= MU_CHARSEL_LIST', 't->selected > MU_CHARSEL_LIST'),
                ('enter-panel', 'source', 't->gfx_flag_78 || t->ui_byte_464', 't->ui_byte_464'),
                ('menu-gate', 'source', '!t->gfx_flag_78 && !t->global_1d22d1e && !t->gfx_menu_flag', '!t->gfx_flag_78'),
                ('panel-gate', 'source', 'if (t->gfx_flag_78) {', 'if (!t->gfx_flag_78) {'),
                ('early-refusal', 'source', 'event(log, 0x00a6ac96, 3, 0x19u, 0u, 0u);',
                 'if (t->enter_refused == 1) return 1; event(log, 0x00a6ac96, 3, 0x19u, 0u, 0u);')]
            for name, target, old, new in plants:
                original = header if target == 'header' else source
                assert old in original, name
                bad = original.replace(old, new, 1)
                lib = build(tmp, name, bad if target == 'header' else header, bad if target == 'source' else source)
                assert check(lib, rows) is not None, name
                report['mutants'][name] = 'caught'
    if a.report:
        Path(a.report).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
