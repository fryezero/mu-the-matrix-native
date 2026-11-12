# Muun base visual slot, MUUN-VISUAL-001

Offline static audit of the pinned restored text and second image section in `scripts/pins.py`.
No server handlers, packet data, protection modules or live client are used. The native fixture supplies
appearance and owner identity explicitly. Model and effect data remain local, read only.

## Caller map (static)

- `0x009a9516` is the base slot setup; `0x009a9992` is its final call to effect attach `0x009af699`.
  A fresh slot allocates a `0x3d8` OBJECT, rejects an already-live OBJECT, stores owner/record/key/active,
  takes model `record +0x264`, scale `+0x110`, offset `+0x114`, owner angle and position plus offset.
  The horizontal offset length is the follow radius. OBJECT `+0x34c` points at character `+0x3254`.
  The loader `0x009b90d5` decodes 612-byte MuunRenderInfo records and derives `+0x264 = item +0x0ae6`.
- `0x009a99a9` is the logic update. It requires an OBJECT and owner OBJECT, and a live Muun. In scene 6
  a dead owner or owner kind other than 1 clears its live flag. The base calls state choice `0x009a9e29`,
  animation `0x009aa1b9`, then follow `0x009aa268`. Auxiliary command state is outside this base fixture.
- `0x009a9e29` compares horizontal distance with the offset radius. Idle 0 starts chase 2 beyond it,
  otherwise requests idle variation 1 on `rand() % 500 == 0`. State 1 returns to 0 at animation end or
  chases when far. State 2 returns to 0 at animation end only when the owner is stationary and within
  radius + 10. States 3/4 return to idle at animation end; their command entry is excluded.
- `0x009aa1b9` calls animation tick `0x012b4dd3` with record speeds `+0x238 + 4 * state`, copying action
  into the model first. Posing/bounds `0x009ab41e` allocates the OBJECT bone array and poses it.
- `0x009aa268` stores owner + offset as idle target without moving. In chase it uses owner x/y and
  owner z + record offset z, CreateAngle `0x012aed9e`, TurnAngle2 `0x012aefff` with 10 degrees, then
  `0x009aafd4`. For each component that helper stores force = -1.4 * (from - target), step = 20 * velocity,
  delta = force - velocity, acceleration = (1/25) * delta, step += acceleration, out = from + step.
  It reads slot velocity `+0x54` without overwriting it; the base constructor starts it at zero.
- `0x009a9ae2` is render, not the follow update: live flag, position-based frustum into OBJECT `+0x0b`,
  owner key (`character +0x3244`), model pass, `0x0129f671(dt)` attachment update, virtual extra passes,
  body after-pass and optional active-slot timing. A foreign key is allowed only by an auxiliary object's
  `+0x44` exception; the fixture deliberately has no auxiliary object and refuses a foreign key.
- `0x009a942b` clears owner/record, frees bone storage (`0x0129f0e5`), clears live, deletes OBJECT and
  auxiliary object, then clears lists. Native fixture generations additionally prevent stale-owner reuse.

## Effect owner fields (static, existing verified consumer)

`mu_fx_owner` documents the fields actually read: OBJECT `+5/+6` (tint requires both), `+0x2a` action,
`+0x38` visibility, `+0xd0` frame, and `+0x1e8` tint. Muun setup sets +5 = 1; OBJECT constructor sets +6 = 1.
The factory called by the Muun table passes owner-tint = 0 and an empty action list, so these particular
requests do not enable action/tint gates. Visibility still matters for both effect draw kinds.
The external matrix needs model/type, scale, position, angle and bone storage. The native fixture must
refuse an absent bone rather than follow the original's unchecked shared-buffer fallback.

## Native fixture (implemented; finish checks pending)

`reconstructed/muun/visual` owns the base setup, action choice, spring, follow and base gates. The native
`mu_muun_visual` loads the decoded render record and Item.bmd model, poses local bones with the existing
instruction-compared model pipeline, then calls the unchanged `mu_muun_owner_refresh/update` consumer.
It propagates the Muun action/frame, tint flags and visibility into each effect instance. Native fixture
key/generation changes and owner death retire the owner terminally; frustum hiding can resume without cloning.
Unavailable poses and missing, dummy or out-of-range bones are refused before any shared-pose fallback.

`native/world/world_muun` owns the opt-in demo adapter, model textures and independent effect scene. The
existing helper lifecycle calls it through small hooks. `MU_MUUN_FIXTURE=<render-info id>` places the companion
by the authored demo hero. With no variable the adapter is idle. Effect data comes from Native Data's `lang`
when present, otherwise `MU_LANG_DIR`. There is no authoritative selection, inventory or packet feed.
The render adapter uses the original caller's x/y * 0.01 frustum coordinates and range -20.

All 15 codes with effect rows load their actual skeletons: 16 attachments, no missing templates or bones.
The GL fixture for code 363 shows the model and both attachments (eight vertices), with a body-only image
control and a private render regression test. The original-instruction comparison covers 912 base-slot
cases with zero mismatches. Finish counts, timings, limits and cleanup are in the
[handoff](../handoffs/MUUN-VISUAL-001.md).

## Mesh and command fixtures, MUUN-VISUAL-002

Target identity is unchanged from [the effect consumer](client-render-effects-018.md): the pinned restored
text and second image section in `scripts/pins.py`, from client SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
No original client, server handler, network, protection module or memory write is used.

### Extra mesh passes

**Static:** `0x017f76ec..0x017f919e`, called from RenderObject's after pass, identifies a Muun through the item
record's bytes `+0x250 == 12` and `+0x251 != 0`. For an ordinary OBJECT, `+0x60 == 0`, the render-info lookup
`0x01807c32` supplies the base-body byte `+0x258` and vector `+0x270`. The base body draws first when that byte
is set. Then each mesh record draws in vector order. Each row starts with the OBJECT's blend mesh/light,
alpha, UV offsets and model colour. The model colour is restored after every row.

The mesh loader `0x009b9510..0x009b98fc` decodes 300-byte records into 304-byte runtime rows. It associates
rows by **item/model code**, rather than the render-info/effect id. Texture `default` means no override,
otherwise the loader appends the name to `Data/Item/Texture/`, with linear filtering and repeat wrapping.
The last runtime int32 `+0x12c` is the allocated bitmap id; it is absent from the file.

| Mesh-record field | Meaning in this branch |
|---|---|
| `+4`, `+0x124` | mesh index, render flags |
| `+0x108` | RGB override when byte `+0x12a` is nonzero |
| `+0x114` | alpha override when byte `+0x12b` is nonzero |
| `+0x118`, `+0x11c`, `+0x120` | pulse parameter, minimum, maximum |
| byte `+0x129` | replace blend mesh with this row's mesh |
| byte `+0x128` | pulse blend light rather than use the minimum |

The pulsed light is `wave(-parameter, 0) * (maximum - minimum) + minimum`, with the original's binary32
operation order. `0x0185bdc4` truncates its clock and signed period, evaluates its cosine and folds it into
0..1. The native implementation refuses invalid pulse periods before rendering.

**Verified:** `validate_muun_passes` executes the complete caller, including `0x0185bdc4`, with named item,
render-info and vector services. Only the CRT cosine is a host math service. It compares the complete ordered
body/mesh argument stream and colour at every call, and checks the restored colour. Synthetic flags cover
every gate combination, multiple flags and positive/negative clocks. The private extension uses the actual
rows of all fifteen attachment codes at three clocks. Decoded data stays local and is never serialized in
the report.

**Private data audit:** codes 174, 176, 178, 184 and 363 have respectively 1, 2, 1, 1 and 3 extra mesh rows.
The other ten codes have no extra rows. All fifteen request their base body. Six added texture overrides
load successfully. The three rows of 363 include RGB/alpha and alpha-only passes plus a pulsing texture pass.
This is an eight-pass subset, not a census of every Muun in the client.

Special models `0x2b7a`, `0x2b7b`, `0x2b8d`, `0x2b8e` and `0x2b90` take further branches, including atlas
motion and bone-driven effects. None is one of the fifteen audited attachment models. Native refuses their
extra rows rather than drawing them with this ordinary branch.

### Base-slot shadow

**Static and verified:** vtable `0x01a7ed58`, slot `+0x18`, calls `0x009aa54b`. It reads render-info alpha
`+0x254`, or OBJECT alpha when the owner kind is 2. It skips worlds 10/132, 24..29/36 and the original option
flag. It uses alpha 0.2 in worlds 7/128..130 and calls `RenderBodyShadow(-1,-1,-1,-1,0)` for these fifteen models.
Native uses the existing verified projection over the whole body. Its ordinary-owner fixture supplies option 0 and owner kind 1. `--no-particles` also suppresses the
shared shadow renderer, as it does for other companions. This does not establish live option/buff parity.

### Slot-class census

**Static:** the manager factory `0x009b9dda` selects slot classes from render-record byte `+8`. This is
separate from MuunInfo's command category byte `+0x0c`.

| Slot kind | Construction and visual methods | Result of this lane |
|---|---|---|
| 0 | `0x009a90c6`, vtable `0x01a7ed58`, 188-byte base slot | All fifteen audited attachment appearances use this kind |
| 1 | `0x009beac5`, vtable `0x01a7f268`, 244-byte slot; setup `0x009bec34`, update `0x009bf225`, render `0x009bf31e` | Secondary-body lifecycle audited below; not implemented or counted as a complete appearance |
| 2 | `0x009b0c9d`, vtable `0x01a7ee18`, 188 bytes | Setup/update/render wrappers forward to the base routines |
| 3 | `0x009c2bd0`, vtable `0x01a7f2a0`, 188 bytes | Setup/update/render wrappers forward to the base routines |

The installed render table has 378 kind-0 and eight kind-1 records, with no kind-2/3 records. The eight
kind-1 ids are 16, 17 and 100..105. None belongs to the fifteen attachment appearances proved here.

Kind 1 allocates a second `0x3d8` OBJECT at slot `+0xbc`, with model from runtime render-info `+0x268`, its own
bone storage, owner pointer, scale, alpha and clock. Destruction `0x009bebd3` frees its bones and OBJECT.
Update calls the base, checks the second OBJECT and owner, then `0x009bf58b` maps the owner's action through a
separate action table and calls SetAction on changes. `0x009bf626` advances the second model using its action
speed; `0x009bf6f8` copies the owner's position and angles. `0x009bf820` resolves the named attachment on this
second skeleton, transforms the zero point and scales its offset. The owner's active-mount item comparison,
owner flag `+0x31e8`, buff `0x1a` and a further mount predicate gate secondary rendering. If admitted, it uses
its own frustum and `RenderObject`, plus `0x009bfe13` for model-specific effects on models `0x5cb..0x5d2`.
Those effects include named-bone particles and additional positions; they are not the fifteen `.ein` attachments.

This is an explicit remaining visual gap. The current fixture supplies a base-slot lease and optional same-owner
command target, not that secondary skeleton or an authored active-mount lease. No kind-1 secondary-body, owner
rider-action or effect equivalence is claimed. Its next bounded implementation needs both models, the separate
action mapping, exact attachment names and a synthetic mount-selection input, with no authoritative feed.

### Auxiliary command audit and authored pose cycle

**Static:** slot setup `0x009a9c88` reads MuunInfo category `+0x0c`. Only categories 50..99 allocate the 84-byte
helper at `0x009c2243`. Its defaults `0x009c22e3` clear its timers, pending/remote flags and offset; setup
supplies an offset, timer parameter and render-record timing values. `0x009c2371` advances those timers.
The timer helper `0x009c2b6c` zeros period, elapsed and flag;
`0x009c2bb0` adds the supplied delta and `0x009c2b91` tests elapsed >= period. Initial periods are 10 seconds
and 0.5 seconds; slot setup supplies the record periods in milliseconds / 1000 and a 3-second transition
period. A remote helper's transition expiry creates effect `0x47a` at object position plus offset.

`0x009c2539` refuses a command while flag `+0x2c` is set. A different owner key invokes a separate target
lookup/rotation path, rotates the owner-relative displacement by owner key * 30 degrees, sets `+0x44`,
and emits `0x47a`. With the owner's own key it skips that path, marks a
command pending, resolves its supplied target, faces that target with CreateAngle, and maps categories
50/53 to action 3; 51/52/54/55 to action 4. Other categories request no action. These action calls are compared
with the original over the signed category domain, including absent and extreme values. Base-state selection
`0x009a9e29` already returns states 3/4 to idle at animation end; follow `0x009aa268` does not chase in them.

**Implemented fixture:** `MU_MUUN_COMMAND_FIXTURE=50..55`, together with `MU_MUUN_FIXTURE=<id>`, supplies an
explicit synthetic command category and a fixed demo target every 100 logic steps. It uses the recovered
action map, SetAction, posed skeleton and existing animation-end transition. It never infers a command from
combat, inventory or owner stats. Unsupported categories, absent actions, invalid targets and retired owners
are refused. Fourteen of the fifteen actual models have actions 3/4; code 363 has only actions 0..2 and refuses
both. Posed attachment/lifetime controls continue to cover all fifteen models.

**Limit:** the installed MuunInfo table has no categories 50..99. The fifteen attachment records are category
1. Thus this is an authored pose demonstration of the same-owner branch, not evidence that those appearances
receive attack commands in production. Remote target motion, original helper timers and `0x47a` transitions
remain audited but unimplemented. The fixture clock is explicitly authored and is not the original process clock.

### Demo selection boundary

The statically established ownership rule remains slot owner/key plus an explicitly supplied render-info
record. No source of authoritative MainMuun/SubMuun/HeroMuun selection has been established within this
offline visual audit; its packet/inventory inputs remain excluded. Therefore no demo character record is
assigned a Muun implicitly. The environment appearance switch remains, as permitted by this lane's conditional
scope. A future authored record field needs a caller that supplies the chosen slot and record explicitly.

All counts, final checks, render controls and remaining limits are recorded in
[MUUN-VISUAL-002](../handoffs/MUUN-VISUAL-002.md). No full original-scene or live-motion equivalence is claimed.
