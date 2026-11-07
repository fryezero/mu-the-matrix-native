#!/usr/bin/env python3
"""RENDER-WORLDS-RAKLION instruction comparisons (docs/research/client-worlds-raklion.md).

Raklion's class (world-57, worlds 57/58, vtable 0x01aad9d0) has Test Area 121's slot code: its custom render
0x00e949f8 is 121's 0x00d58bd8 plus the world test 0x00ea233c and type 0x52's frame restart behind the handler byte
+0x22, and its after render 0x00e96536 is 121's 0x00d5a6cc instruction for instruction. The native runs both
through world_test_area_visual.c with Raklion's row (mu_class_custom / mu_class_after(57, ...)). The families reuse
validate_worlds_121's slot comparison (draws with the StreamMesh byte and colour, CreateParticle, TransformPosition's
bone list, the per-vertex light buffer 0x06fd0918, the answer, rand, the object and model fields after the call):
  custom_raklion   the custom render 0x00e949f8 (the first 301 cases sweep the type 0..300); one case in five runs in
                   another world (56, 59, 0, 2, 121, 140: the world test answers 0 and draws nothing). The handler
                   (ecx) byte +0x22 is 0, 1, 2 or 0xff, given to the native as mu_slot_model.handler_state.
  actions_raklion  the custom render for 0x10, 0x11, 0x13..0x15 and 0x52 only, frames at their window edges and seeds
                   whose first rand() lands on the residues the branches compare (validate_worlds_121's actions_121).
  after_raklion    the after render 0x00e96536 against mu_class_after(57, ...).
"""
import argparse, json, random, re, shutil, sys, tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_worlds_121 as w121
import validate_worlds_slots2 as w2

ROOT = Path(__file__).resolve().parents[1]
CUSTOM, AFTER = 0xe949f8, 0xe96536
FOCUS = dict(w121.FOCUS)
FOCUS[0x52] = ([0.0, 5.5, 19.0, 97.25], [0, 1, 3], 2, [0, 1])   # no rand: the gate byte decides
RAKLION = w121.Spec('raklion', 57, CUSTOM, AFTER, [57, 58], [56, 59, 0, 2, 121, 140], FOCUS, gate=True)
FAMILIES = {
    'custom_raklion': lambda m, l, g, n: w121.slot_family(m, l, g, n, False, spec=RAKLION),
    'actions_raklion': lambda m, l, g, n: w121.slot_family(m, l, g, n, False, True, spec=RAKLION),
    'after_raklion': lambda m, l, g, n: w121.slot_family(m, l, g, n, True, spec=RAKLION),
}
T, S2 = 'world_test_area_visual.c', 'world_slots2_visual.c'
MUTATIONS = [
    # Raklion's row and its gate
    ('World test from 56', T, 'RAKLION={57,58,1}', 'RAKLION = {56, 58, 1}', 'custom_raklion'),
    ('World test to 59', T, 'RAKLION={57,58,1}', 'RAKLION = {57, 59, 1}', 'custom_raklion'),
    ('No world test', T, 'RAKLION={57,58,1}', 'RAKLION = {0, -1, 1}', 'custom_raklion'),
    ('No frame gate', T, 'RAKLION={57,58,1}', 'RAKLION = {57, 58, 0}', 'actions_raklion'),
    ('Gate on byte 1 only', T, 's->model->handler_state==0', 's->model->handler_state != 1', 'actions_raklion'),
    ('Gate keeps the prior frame', T, 'mu_obj_set_f32(s->o,MU_OBJF_PRIOR_FRAME,0.0f);', '', 'actions_raklion'),
    ('Gate restarts the frame at 1', T, 'mu_obj_set_f32(s->o,MU_OBJF_FRAME,0.0f);',
     'mu_obj_set_f32(s->o, MU_OBJF_FRAME, 1.0f);', 'actions_raklion'),
    ('Chrome08 not listed in 57', T, 'world==121||world==57||world==58', 'world == 121 || world == 58',
     'custom_raklion'),
    # the class chain
    ('Custom slot is 121\'s', S2, 'returnmu_slots_raklion_custom(s,world);', 'return mu_slots121_custom(s);',
     'custom_raklion'),
    ('After slot not chained', S2, 'case57:/*noworldtest,as121\'s*/mu_slots_raklion_after(s);break;', 'case 57: break;',
     'after_raklion'),
    # the shared body, seen from Raklion
    ('Per-vertex light 0.25', T, 'wv_bits(0.5f)', 'wv_bits(0.25f)', 'custom_raklion'),
    ('0x13 bones 12..18', T, 'k<20;', 'k < 19;', 'actions_raklion'),
    ('0x15 spark 17 scale 0.6', T, '{17,0.7f}', '{17, 0.6f}', 'actions_raklion'),
    ('After 0x53 mesh 3', T, 'mesh_self(s,4,0x42', 'mesh_self(s, 3, 0x42', 'after_raklion'),
    ('After 0x5c mesh 0', T, 'mesh_self(s,1,0x42', 'mesh_self(s, 0, 0x42', 'after_raklion'),
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
    seed = lambda name: random.Random(0x5757 + list(FAMILIES).index(name))
    for name in names:
        tally = FAMILIES[name](machine, lib, seed(name), a.cases)
        report['families'][name] = tally.report()
        print(name, json.dumps(tally.report())[:2500], flush=True)
    if a.mutations:
        for label, file, old, new, family in MUTATIONS:
            if family not in names:
                continue
            with tempfile.TemporaryDirectory(prefix='worlds-raklion-mut-') as mtmp:
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
