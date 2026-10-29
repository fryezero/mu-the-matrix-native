# RENDER-JOINTS-001

The joint kinds the world lanes refused and the StreamMesh consumer.
[Addresses, kinds, checks and limits](../research/client-joints.md#11-kanturu-undergrounds-and-uruk-mountains-lightning-and-the-streammesh-consumer-render-joints-001).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-joints-001`, branch `claude/render-joints-001`,
  from origin/main `8eb54978`. Input links `tools/python` and `evidence` from the main checkout, never committed.
- **Joint kinds (verified):** `0x7f7d` subtypes 0xc, 0xe, 0xf (Kanturu Underground 66/122, 54/120, 65/121) and
  0xd (Uruk Mountain 109, with CreateJoint's colour argument 12), `0x7f7c` subtype 0x12 (Kanturu 8/92..96): create,
  move and render, in `reconstructed/joints/kanturu_joints.inc` with small hooks in `joints.c`; argument 12 is
  opt-in through `mu_jt_env.has_creation_light`. They draw with the installed JointThunder01 bitmap.
- **StreamMesh (verified consumer):** the model byte `+0x94` is read by the mesh draw `0x012b8d1d` (already
  compared: `mu_meshdraw_model.light_mesh`): unlit with the body colour, u/v scroll. Native wiring: Ignis 79/148's
  create write and MoveObject's write set the model byte, class-slot meshes pass the byte at each call
  (`mu_draw_model_fields.light_mesh`), the primary draw uses the written byte. The counts are gone.
- Shared lines (minimal): `mu_objects.h` one hook (`joint_light`); `mu_objects_runtime.c` the create/move stream
  writes, the pose byte, the slot-mesh byte, the Uruk colour-joint consumer; `mu_particles.c` a static
  `world_joint` behind `mu_world_particles_joint` and `o_joint_light`; `mu_scene.{h,c}` two draw-field members;
  `native/world/parts/objects.c` two summary fields (`objects_draw_unsupported`, `objects_move_unsupported`);
  Makefile dependency lines. No per-world dispatch, particle or effect kind changed.

## Checks

- `validate_joints --cases 3000 --mutations`: 9,000 cases equal (555 per family on the five new kinds), zero
  mismatches/stops, **22/22 compiled mutants** + 9 negative controls. Registry entry updated (`--mutations`, 31).
- Hosts: `worlds_p2_host` (Kanturu 36 joints, 0 refusals; Ignis 0 create refusals, stream 0 for 79/148),
  `worlds_i_host` (Uruk 109: 200 coloured joints, 0 refusals); `test_joints.py` worked examples.
- Refused counters, base → lane: 137 draw-all 1 → 0; 138 draws 32 → 0 (draw-all 400 → 0), creates 11 → 0; 144 0 → 0;
  all 32 DATA-ACQ-002 views 72 → 8 (the 8 left: other causes in 112, 132, 134).
- Fidelity (DATA-ACQ-002, masked mean |Δ|): 137 6.362 → 6.362 (live clock 5.043 → 5.043), 138 3.825 → 3.825, 144
  12.395 → 12.395 (draw-all 12.399 → 12.399): nothing new is in view at the arrival tiles. October 22 tour 28/28 PNG,
  14/14 OBJECT, 14/14 light identical; DATA-ACQ-002 61/64 PNG, 32/32 OBJECT, 32/32 light identical, the three changed
  frames being intended StreamMesh scrolls (142 crystal beam in the masked box, 131 first frame), scores unchanged.
- Real frames inspected: Kanturu 26,216 (0xe/0xf beams), 135,136 (0x7f7c arcs), Ignis 74,113 and 93,116 (scrolling
  lava stream meshes).

No original client or launcher was started; no live read was needed. No service, wire, protection-module, item or
session change. Only authored C/Python, synthetic fixtures and reviewed summaries are committed.

Remaining: Uruk Mountain has no capture (its 0xd is checked by instructions and the host only); BMD-specific StreamMesh
initial values (taken as −1); Uruk's keyed effect `0x806e` stays refused; the other joint kinds of section 10.

During the lane, reports and renders were under `~/Documents/MTM/mu-mac-tools/native/scratch/render-joints-001` and
`renders/render-joints-001`, plus a base build worktree `worktrees/rj001-base`; all are deleted at handoff. The
DATA-ACQ-002 inputs were only read. No new local input needs retention.
