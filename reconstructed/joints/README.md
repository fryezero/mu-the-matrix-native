# The joint pool (NATIVE-JOINT-001)

Authored C for the client's joints (ribbons, trails and lightning bolts): CreateJoint, MoveJoint and the
per-record part of RenderJoints, compared with the client's instructions in Unicorn by
`scripts/validate_joints.py`. One implementation: NATIVE-COMBAT-002's `reconstructed/combat/skill_fx` wraps it
(`mu_sfx_joint` is `mu_jt_joint`). Findings, kind table and limits:
[docs/research/client-joints.md](../../docs/research/client-joints.md).

| File | Client routines |
|---|---|
| `joints.h` | API: the 0xa64-byte record, the object view, the call record, the environment, the GL stream |
| `joints.c` | CreateJoint `0x0153b02c` (record part `0x0153b0a6..`), MoveJoint `0x01556c26` with the tail shift `0x01553ba6`, MoveHumming `0x012af2f1`, the vector helpers `0x00cfd0cc`/`0x00cfcd74`, RenderJoints `0x01589b56` (per record) |

RENDER-WORLDS-C adds Icarus `0x7f7c` subtype 6 and `0x7f7d` subtype 0, compared in
`scripts/validate_icarus.py`. Their creation colours are verified for world 10; world 0x84 remains outside this port.

Kinds (`mu_jt_kind_supported`): Tormenta Island's lightning `0x7f7d` subtypes `0x10..0x1a` (bolts, arcs,
rings), the spark streaks `0x7fd5` 0 (Noria, Twisting Slash), Heal `0x7fd8` 1 and Evil Spirit `0x7fd3` 0.

`native/core/mu_joints.*` runs the pool in the native session (slot search, MoveJoints, RenderJoints as quads)
for the world objects (`mu_particles`) and the skills (`mu_combat`).

```sh
make -C reconstructed/joints
python3 -m unittest discover -s reconstructed/joints -p 'test_*.py'
scripts/validate_joints.py --cases 3000 --output /tmp/joints.json
```

Build with `-ffp-contract=off`: the float arithmetic follows the client's binary32 order.
