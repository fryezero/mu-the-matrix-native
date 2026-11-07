#!/usr/bin/env python3
"""RENDER-WORLDS-KARUTAN instruction comparisons (docs/research/client-worlds-karutan.md).

Karutan's class (world-80, worlds 80/81, vtable 0x01aa9a4c) has its own slot code, not Test Area 121's: its custom
render 0x00e14596 tests the world (0x00e18ae9: 80, 81; 0x009dad2c: 102; the singleton 0x00c7dfcc's 0x009d3e63:
103..106), flags ten types for the after pass, chooses 0x42's action (frame >= 19: SetAction(o, rand() % 10 == 0))
and draws 0x81 (the body, then mesh 1 grey-pulsed by the wave 0x0185bdc4(-2.5, 0) with the bitmap 0x85bb, the body
colour restored, mesh 1 again with flags 0x44). Its after render 0x00e1543e tests 80/81 only and draws ten types. The
native runs both through world_karutan_visual.c (mu_class_custom / mu_class_after(80, ...)). The families reuse
validate_worlds_121's slot comparison with Karutan's spec (draws with the StreamMesh byte and colour, the answer,
rand, the object and model fields after the call, and the bitmaps the class names):
  custom_karutan   the custom render (the first 301 cases sweep the type 0..300); one case in five runs in another
                   world (79, 82, 0, 142, 143, 107 answer 0; 102..106 pass the world test).
  actions_karutan  type 0x42 only, frames at the frame-19 edge and seeds whose first rand() % 10 is 0, 1 or 9.
  after_karutan    the after render against mu_class_after(80, ...).
The singleton accessor 0x00c7dfcc (no argument) is a leaf answering a dummy pointer; its predicate 0x009d3e63 runs
as client code.
"""
import argparse, json, random, re, shutil, sys, tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_worlds_121 as w121
import validate_worlds_slots2 as w2

ROOT = Path(__file__).resolve().parents[1]
CUSTOM, AFTER = 0xe14596, 0xe1543e
SINGLETON = 0xc7dfcc
CUSTOM_TYPES = [1, 3, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3e, 0x3f, 0x42, 0x77] + [0x81] * 4   # 0x81 weighted: it draws
AFTER_TYPES = [1, 3, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3e, 0x3f, 0x42, 0x77]
FOCUS = {0x42: ([18.0, 18.99, 19.0, 19.01, 30.0, 97.0], [0, 1, 2], 10, [0, 1, 9])}
KARUTAN = w121.Spec('karutan', 80, CUSTOM, AFTER, [80, 81], [79, 82, 0, 142, 143, 107, 102, 103, 104, 105, 106],
                    FOCUS, types=CUSTOM_TYPES, after_types=AFTER_TYPES, action_types=[0x42],
                    stubs={SINGLETON: lambda m: v.FAKE})
FAMILIES = {
    'custom_karutan': lambda m, l, g, n: w121.slot_family(m, l, g, n, False, spec=KARUTAN),
    'actions_karutan': lambda m, l, g, n: w121.slot_family(m, l, g, n, False, True, spec=KARUTAN),
    'after_karutan': lambda m, l, g, n: w121.slot_family(m, l, g, n, True, spec=KARUTAN),
}
K, S2 = 'world_karutan_visual.c', 'world_slots2_visual.c'
MUTATIONS = [
    # the custom slot 0x00e14596
    ('No world test', K, 'if(!karutan_world(world)&&world!=102&&(world<103||world>106))return0;', '(void)world;', 'custom_karutan'),
    ('World 102 not tested', K, 'world!=102&&', '', 'custom_karutan'),
    ('Worlds 103..107', K, 'world>106', 'world > 107', 'custom_karutan'),
    ('0x77 not flagged', K, 'case0x3f:case0x77:set_after(s);', 'case 0x3f: set_after(s);', 'custom_karutan'),
    ('0x42 from frame 18', K, '>=19.0f)', '>= 18.0f)', 'actions_karutan'),
    ('0x42 roll % 9', K, '%10==0?1:0', '% 9 == 0 ? 1 : 0', 'actions_karutan'),
    ('0x42 not flagged', K, 'rand_context)%10==0?1:0);set_after(s);', 'rand_context) % 10 == 0 ? 1 : 0);\n        ',
     'custom_karutan'),
    ('0x81 pulse bias 0.6', K, '*0.3f+0.7f);', '* 0.3f + 0.6f);', 'custom_karutan'),
    ('0x81 wave period -2', K, 'wave(s,-2.5f)', 'wave(s, -2.0f)', 'custom_karutan'),
    ('0x81 colour not restored', K, 'color(s,r,g,bl);', '(void)r; (void)g; (void)bl;', 'custom_karutan'),
    ('0x81 without 0x85bb', K, 'BL(s),U(s),V(s),0x85bb);', 'BL(s), U(s), V(s), -1);', 'custom_karutan'),
    ('0x81 second pass flags 0x42', K, 'mesh(s,1,0x44,', 'mesh(s, 1, 0x42,', 'custom_karutan'),
    ('0x81 body hidden mesh', K, 'body(s,2,BM(s),BL(s),U(s),V(s),-1);', 'body(s, 2, BM(s), BL(s), U(s), V(s), H(s));',
     'custom_karutan'),
    ('Custom slot not chained', S2, 'returnmu_slots_karutan_custom(s,world);', 'return 0;', 'custom_karutan'),
    ('0x85bb not listed for 0x81', K, 'type!=0x81||room<=0', 'type != 0x80 || room <= 0', 'custom_karutan'),
    # the after slot 0x00e1543e
    ('After in world 102', K, 'staticintkarutan_world(int32_tw){returnw==80||w==81;}',
     'static int karutan_world(int32_t w) { return w == 80 || w == 81 || w == 102; }', 'after_karutan'),
    ('After 0x36 pulse +0.4', K, '+0.5f)*0.5f+1.0f', '+ 0.4f) * 0.5f + 1.0f', 'after_karutan'),
    ('After 0x37 without StreamMesh', K, 'stream(s,0);mesh(s,0,0x42,A(s),BM(s),BL(s),U(s),tmod',
     'mesh(s, 0, 0x42, A(s), BM(s), BL(s), U(s), tmod', 'after_karutan'),
    ('After 0x37 period 1000', K, 'tmod(s,10000,', 'tmod(s, 1000,', 'after_karutan'),
    ('After 0x3f glow mesh 1', K, 'mesh(s,2,0x42,A(s),2,p,', 'mesh(s, 1, 0x42, A(s), 2, p,', 'after_karutan'),
    ('After 0x3a mesh order', K, 'mesh(s,3,2,A(s),BM(s),BL(s),0.0f,0.0f,-1);mesh(s,2,0x42,A(s),BM(s)',
     'mesh(s, 2, 0x42, A(s), BM(s), BL(s), 0.0f, 0.0f, -1); mesh(s, 3, 2, A(s), BM(s)', 'after_karutan'),
    ('After 0x3e not drawn', K, 'case3:case0x38:case0x3e:', 'case 3: case 0x38:', 'after_karutan'),
    ('After 0x42 glow blend 1', K, 'mesh(s,1,0x42,A(s),BM(s),BL(s),0.0f,0.0f,-1);break;',
     'mesh(s, 1, 0x42, A(s), 1, BL(s), 0.0f, 0.0f, -1); break;', 'after_karutan'),
    ('After type 1 scrolls u', K, 'mesh(s,m,2,A(s),BM(s),BL(s),0.0f,', 'mesh(s, m, 2, A(s), BM(s), BL(s), U(s),',
     'after_karutan'),
    ('After slot not chained', S2, 'mu_slots_karutan_after(s,world);/*itsownworldtest(80,81)*/break;', 'break;',
     'after_karutan'),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=1000)
    p.add_argument('--only')
    p.add_argument('--text', default=v.pins.TEXT.default_str())
    p.add_argument('--data', default=v.pins.DATA.default_str())
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    text = am.load_pinned(a.text, am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(a.data, am.DATA_BYTES, am.DATA_SHA256, 'data')
    machine = w2.Machine(text, data)
    names = a.only.split(',') if a.only else list(FAMILIES)
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'mutants': []}
    lib = w121.build(ROOT / 'reconstructed')
    seed = lambda name: random.Random(0x8080 + list(FAMILIES).index(name))
    for name in names:
        tally = FAMILIES[name](machine, lib, seed(name), a.cases)
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:2500], flush=True)
    if a.mutations:
        for label, file, old, new, family in MUTATIONS:
            if family not in names:
                continue
            with tempfile.TemporaryDirectory(prefix='worlds-karutan-mut-') as mtmp:
                root = Path(mtmp)
                for d in ['objects', 'terrain', 'record-math', 'model-codec', 'particles', 'movement']:
                    shutil.copytree(ROOT / 'reconstructed' / d, root / d,
                                    ignore=shutil.ignore_patterns('*.dylib', '*.so', '*.o', '*.d', '__pycache__'))
                if (ROOT / 'reconstructed/deps.mk').exists():
                    shutil.copy(ROOT / 'reconstructed/deps.mk', root / 'deps.mk')
                path = root / 'objects' / file
                s = path.read_text()
                pattern = ''.join(re.escape(ch) + r'\s*' for ch in old.replace(' ', ''))
                assert len(re.findall(pattern, s)) == 1, (label, 'the anchor must match exactly once')
                s = re.sub(pattern, lambda m: new, s, count=1)
                path.write_text(s)
                tally = FAMILIES[family](machine, w121.build(root), seed(family), a.cases)
                item = {'name': label, 'cases': tally.cases,
                        'detected': tally.cases - tally.equal - tally.stopped, 'stopped': tally.stopped}
                report['mutants'].append(item)
                print(item, flush=True)
    report['ok'] = all(x['mismatch_count'] == 0 and x['stopped'] == 0 for x in report['families'].values()) and \
        all(x['detected'] > 0 for x in report['mutants'])
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=1))
    print('ok' if report['ok'] else 'FAILED', flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
