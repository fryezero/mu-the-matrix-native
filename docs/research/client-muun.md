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

Validation and native integration are in progress; this note makes no completed visual proof claim yet.
