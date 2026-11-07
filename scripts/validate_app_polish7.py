#!/usr/bin/env python3
"""APP-POLISH-007: the join answer's vitals block versus the offline seed's copy of it.

The original client has no class/level/stat formula for the HUD maxima. The join answer 0x0124cc64 copies eight
server words into CharacterAttribute (block 0x0124d1bf..0x0124d365), and only server answers write those fields
afterwards. The native world seed stands in for that answer (fixture/hero_join.h gives the values, current =
maximum) and applies them with hero_join_vitals (native/session/domains/hero.c).

Families:
  join  the original block entered at 0x0124d1bf with [ebp-0x18] = a random answer and [0x01d1df1c] = a random
        CharacterAttribute, stopped at 0x0124d365, against hero_join_vitals on the same bytes: all 0x200 attribute
        bytes compared. Words mix 0, 1, 0xffff and random values.
  seed  random class/level/stats join data (and the five offline demo characters) through mu_fixture_hero_join
        and mu_dom_hero_seed, against the original block fed the answer those vitals make (current = maximum
        words) on a zeroed attribute: the eight vitals fields compared, and current = maximum checked.
"""
import argparse
import ctypes
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
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402

BLOCK = (0x0124d1bf, 0x0124d365)
ATTR_GLOBAL = 0x01d1df1c
ATTR_SIZE = 0x200
ANSWER_SIZE = 0x34
VITALS = (0x68, 0x70, 0x6c, 0x74, 0x78, 0x7c, 0x80, 0x84)   # HP, HP max, MP, MP max, SD, SD max, AG, AG max
# The five offline demo characters (native/client/demo-characters.txt, demo-session.txt): class byte, and the join
# data the fixture server gets (has_stats, level, stats); without a "hero" line, the class start stats at level 1.
DEMO = [('Nightfall', 0x00, 0, 0, (0, 0, 0, 0, 0)), ('Ironclad', 0x01, 0, 0, (0, 0, 0, 0, 0)),
        ('Windleaf', 0x02, 1, 320, (22, 1302, 20, 15, 0)), ('Spellblade', 0x03, 0, 0, (0, 0, 0, 0, 0)),
        ('Crownlord', 0x04, 0, 0, (0, 0, 0, 0, 0))]


def function(path, signature):
    text = (ROOT / path).read_text()
    start = text.index(signature)
    return text[start:text.index('\n}', start) + 2]


def native(work, mutation=None):
    """Compile hero_join_vitals, mu_dom_hero_seed and mu_fixture_hero_join from the production sources."""
    for tool in ('gen_layout.py', 'gen_domains.py'):
        subprocess.run([sys.executable, str(ROOT / 'scripts' / tool), '--out', str(work / 'gen')], check=True,
                       capture_output=True)
    join_header = (ROOT / 'native/fixture/hero_join.h').read_text()
    demo_header = (ROOT / 'native/fixture/progress_demo.h').read_text()
    fixture = work / 'native/fixture'
    fixture.mkdir(parents=True)
    source = '''#include <stdio.h>
#include <string.h>
#include "native/session/domains/hero.h"
#include "native/session/domains/hero_state.h"
#define MU_SESSION_SEED 1
#include "native/fixture/hero_join.h"
#define mu_session_touch(s,d) ((void)(s))
struct mu_session { mu_dom_hero hero; };
'''
    source += function('native/session/domains/hero.c', 'static void hero_join_vitals(') + '\n'
    source += function('native/session/domains/hero.c', 'void mu_dom_hero_seed(') + '\n'
    source += '''
static mu_session s;
void join_block(uint8_t *attr, const uint8_t *answer) { hero_join_vitals(attr, answer); }
/* the seed: vitals[4] out, then the attribute's eight vitals fields */
void seed(int cls, int has_stats, int level, const int32_t *stats, int32_t *vitals, int32_t *fields) {
 mu_session_seed sd = {0}; sd.class_byte = (uint8_t)cls;
 mu_skills_demo_join join = {NULL, has_stats, level, {stats[0], stats[1], stats[2], stats[3], stats[4]}, 0};
 mu_fixture_hero_join(&sd, &join);
 memcpy(vitals, sd.vitals, sizeof sd.vitals);
 memset(&s, 0, sizeof s); mu_dom_hero_seed(&s, &sd);
 const int offsets[8] = {0x68, 0x70, 0x6c, 0x74, 0x78, 0x7c, 0x80, 0x84};
 for (int i = 0; i < 8; i++) memcpy(fields + i, s.hero.attr + offsets[i], 4);
}
'''
    if mutation:
        old, new = mutation
        hit = False
        if old in source:
            source, hit = source.replace(old, new, 1), True
        if old in join_header:
            join_header, hit = join_header.replace(old, new, 1), True
        if old in demo_header:
            demo_header, hit = demo_header.replace(old, new, 1), True
        assert hit, mutation
    (fixture / 'hero_join.h').write_text(join_header.replace('#include "../session/mu_session_seed.h"',
                                                             '#include "native/session/mu_session_seed.h"')
                                         .replace('#include "skills_demo.h"', '#include "native/fixture/skills_demo.h"'))
    (fixture / 'progress_demo.h').write_text(demo_header)
    c = work / 'probe.c'
    c.write_text(source)
    lib = work / 'probe.so'
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-O1', '-shared', '-fPIC', '-I', str(work), '-I', str(ROOT),
                    '-I', str(ROOT / 'native/session'), '-I', str(work / 'gen'), str(c), '-o', str(lib)],
                   check=True, capture_output=True)
    dll = ctypes.CDLL(str(lib))
    dll.join_block.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    dll.seed.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int32),
                         ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32)]

    def join(attr, answer):
        buf = ctypes.create_string_buffer(bytes(attr), ATTR_SIZE)
        dll.join_block(buf, bytes(answer))
        return buf.raw[:ATTR_SIZE]

    def seed(cls, has_stats, level, stats):
        vitals, fields = (ctypes.c_int32 * 4)(), (ctypes.c_int32 * 8)()
        dll.seed(cls, has_stats, level, (ctypes.c_int32 * 5)(*stats), vitals, fields)
        return list(vitals), list(fields)
    return join, seed


def original(text, data):
    import client_ui_machine as cm
    import validate_gfx3 as gfx
    m = gfx.machine(text, data)
    m.allow(BLOCK)

    def stop(mm):
        mm.uc.reg_write(cm.UC_X86_REG_EIP, cm.RETURN_SENTINEL)
        return cm.REDIRECT
    m.stub(BLOCK[1], stop)

    def run(attr_bytes, answer):
        m.reset()
        attr = m.alloc(ATTR_SIZE, define=True)
        packet = m.alloc(0x100, define=True)
        m.write(attr, attr_bytes)
        m.write(packet, bytes(answer) + bytes(0x100 - len(answer)))
        m.put32(ATTR_GLOBAL, attr)

        def enter(mm):
            ebp = cm.STACK_BASE + 0x10000
            mm.write(ebp - 0x400, bytes(0x400))
            mm.put32(ebp - 0x18, packet)
            mm.uc.reg_write(cm.UC_X86_REG_EBP, ebp)
            mm.uc.reg_write(cm.UC_X86_REG_ESP, ebp - 0x500)
            mm.uc.reg_write(cm.UC_X86_REG_EIP, BLOCK[0])
            return cm.REDIRECT
        m.stub(0x8e0480, enter)
        m.call(0x8e0480)
        return m.read(attr, ATTR_SIZE)
    return run


def answer_words(words):
    """An answer whose +0x24..+0x32 holds the eight words (HP, HP max, MP, MP max, SD, SD max, AG, AG max)."""
    answer = bytearray(ANSWER_SIZE)
    for i, w in enumerate(words):
        struct.pack_into('<H', answer, 0x24 + 2 * i, w)
    return answer


def fields(attr):
    return [struct.unpack_from('<i', attr, off)[0] for off in VITALS]


def word(rng):
    r = rng.randrange(8)
    return 0 if r == 0 else 1 if r == 1 else 0xffff if r == 2 else rng.randrange(0x10000)


def join_cases(rng, n):
    cases = [(bytes(ATTR_SIZE), answer_words([0] * 8)), (bytes([0xff]) * ATTR_SIZE, answer_words([0xffff] * 8)),
             (bytes([0x80]) * ATTR_SIZE, answer_words([1, 0, 1, 0, 0, 1, 0, 1]))]
    while len(cases) < n:
        attr = bytes(rng.randrange(256) for _ in range(ATTR_SIZE))
        answer = bytearray(rng.randrange(256) for _ in range(ANSWER_SIZE))
        answer[0x24:0x34] = answer_words([word(rng) for _ in range(8)])[0x24:0x34]
        cases.append((attr, bytes(answer)))
    return cases[:n]


def seed_cases(rng, n):
    cases = [(c, h, lv, st) for _, c, h, lv, st in DEMO]
    while len(cases) < n:
        cls = rng.randrange(16) | (rng.randrange(8) << 4 if rng.randrange(4) == 0 else 0)
        has = rng.randrange(3) != 0
        level = rng.choice([0, 1, 2, rng.randrange(1, 401), rng.randrange(1, 1601)])
        stats = tuple(rng.choice([0, 1, rng.randrange(40), rng.randrange(0x10000)]) for _ in range(5))
        cases.append((cls, int(has), level, stats))
    return cases[:n]


def compare(client, join, seed, jcases, scases):
    mismatches = []
    for attr, answer in jcases:
        if client(attr, answer) != join(attr, answer):
            mismatches.append(('join', answer.hex()))
    demo = {}
    for cls, has, level, stats in scases:
        vitals, got = seed(cls, has, level, stats)
        words = [w for v in vitals for w in (v & 0xffff, v & 0xffff)]
        want = fields(client(bytes(ATTR_SIZE), answer_words([words[0], words[1], words[2], words[3],
                                                             words[4], words[5], words[6], words[7]])))
        if got != want or got[0::2] != got[1::2]:
            mismatches.append(('seed', cls, has, level, stats, got, want))
        for name, c, h, lv, st in DEMO:
            if (c, h, lv, st) == (cls, has, level, stats):
                demo[name] = {'hp': got[0:2], 'mp': got[2:4], 'sd': got[4:6], 'ag': got[6:8]}
    return mismatches, demo


MUTANTS = [
    ('{MU_PRG_A_LIFE_MAX, 1, 0x26}', '{MU_PRG_A_LIFE_MAX, 0, 0x26}'),
    ('{MU_PRG_A_SHIELD_MAX, 1, 0x2e}', '{MU_PRG_A_SHIELD_MAX, 0, 0x2e}'),
    ('{MU_PRG_A_LIFE, 0, 0x24}', '{MU_PRG_A_LIFE, 1, 0x24}'),
    ('{MU_PRG_A_AG, 0, 0x30}', '{MU_PRG_A_AG, 0, 0x2c}'),
    ('{MU_PRG_A_SHIELD, 0, 0x2c}', '{MU_PRG_A_SHIELD, 0, 0x30}'),
    ('{MU_PRG_A_MANA_MAX, 1, 0x2a}', '{MU_PRG_A_MANA_MAX, 1, 0x28}'),
    ('answer[COPY[i].word] | answer[COPY[i].word + 1] << 8', 'answer[COPY[i].word]'),
    ('static const uint8_t WORD[4] = {0x24, 0x28, 0x2c, 0x30};', 'static const uint8_t WORD[4] = {0x24, 0x28, 0x30, 0x2c};'),
    ('for (int k = 0; k < 4; k += 2) {', 'for (int k = 0; k < 2; k += 2) {'),
    ('for (int i = 0; i < 8; ++i) {', 'for (int i = 0; i < 7; ++i) {'),
]


def run(args):
    start = time.monotonic()
    text = pins.TEXT.read(args.text)
    data = pins.DATA.read(args.data)
    client = original(text, data)
    rng = random.Random(20261107)
    jcases = join_cases(rng, args.cases)
    scases = seed_cases(rng, max(len(DEMO), args.cases // 4))
    with tempfile.TemporaryDirectory() as tmp:
        join, seed = native(Path(tmp))
        mismatches, demo = compare(client, join, seed, jcases, scases)
    caught = []
    if args.mutants:
        for i, mutation in enumerate(MUTANTS):
            with tempfile.TemporaryDirectory() as tmp:
                join, seed = native(Path(tmp), mutation)
                bad, _ = compare(client, join, seed, jcases[:64], scases[:64])
                assert bad, mutation
                caught.append(i + 1)
    return {'families': {'join': {'cases': len(jcases), 'mismatches': sum(1 for m in mismatches if m[0] == 'join')},
                         'seed': {'cases': len(scases), 'mismatches': sum(1 for m in mismatches if m[0] == 'seed')}},
            'cases': len(jcases) + len(scases), 'mismatches': len(mismatches), 'first_mismatches': mismatches[:3],
            'demo': demo, 'mutants_caught': caught, 'equivalent': 0,
            'wall_seconds': round(time.monotonic() - start, 3)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('text', 'data'):
        ap.add_argument('--' + name)
    ap.add_argument('--cases', type=int, default=4096)
    ap.add_argument('--mutants', action='store_true')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    report = run(a)
    print(json.dumps(report))
    if a.out:
        a.out.write_text(json.dumps(report, indent=2) + '\n')
    sys.exit(1 if report['mismatches'] else 0)
