# Death Stab's step trails

RENDER-EFFECTS-027 recovers base skill 43's trail requests and their two joint
kinds. The native route is an authored base-DK demo with link bone 33. It does
not select later-class aliases, supply buffs or alter a target's state.
[Handoff](../handoffs/RENDER-EFFECTS-027.md),
[coverage inventory](client-skill-visual-coverage.md).

## Evidence and domain

Target executable SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The pinned capture09 text SHA-256 is
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`,
and run10 image-data SHA-256 is
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
Inputs remain private. No live client was started or inspected.

**Verified** means compiled authored C compared with these original instructions
under the strict Unicorn machine. The validator checks defined record fields,
ordered call values, RNG consumption, the saved weapon point and AttackTime.
Joint rendering compares the complete recorded GL stream, not GPU pixels.
Each comparison family uses a fresh machine. The continuous lifecycle family
carries the original record bytes between ticks independently of the C record,
including owner death, the closing tails and retirement.

The full focused run has 6,064 comparisons, zero mismatches, and 20/20 compiled
production-C mutants caught without an original-machine stop, 50.74 s. The
randomized families have 1,000 cases each; 64 further comparisons cover complete
create-to-retirement joint lifecycles. The mutants cover caller gates/counts,
scatter/reach, the saved point, cutoff, emitter lifetime/child kind, ribbon
lifetime/tail count/width/blend, direction frequency, curl phase/fade/recursion
and ribbon render colour. This is component evidence, not whole-client or live
image equivalence.

Model lookup, selected-bone lookup, TransformPosition, the current-world
predicate and target lookup are declared services with authored results. The
original caller's scatter helper, rand call sites and scalar arithmetic
execute. Sine/cosine use the existing host-libm services. The joint families execute their original
creation, movement, direction helper, tail shift and GL render instructions;
engine requests and host libm remain the existing recorded services.

## Caller audit

MoveCharacter `0x013a763e` calls the per-step attack helper `0x013966ea` at
`0x013a9047`, before incrementing CHARACTER `+0x21`. Its normalized base-skill
43 branch is `0x0139959c..0x01399c9d`. The native route's action remains `0x9e`.
The earlier combat description's "skill-step trails unaudited" gap was this
helper, not a missing end-of-attack CreateEffect.

The helper first obtains the current object model. It refuses a missing model,
a dummy selected bone, or a link index beyond the model's bone count. The
selector uses `0x013a5658` and CHARACTER `+0x19b1 + index * 0x3fc`. This lane
supplies that result explicitly and does not reconstruct the general selector.

| Input AttackTime | Original requests and writes |
|---|---|
| 1 | Transform the selected link bone's zero offset; save OBJECT `+0x104` with the forward offset below |
| 2..5 | Three `CreateJoint(0x472, p, p, angle, 2, caster, 40, -1, 0, 0, -1, NULL, -1, 0)`, then refresh `+0x104` |
| 6..8 | The same three joints and saved point, then two identical `CreateEffect(0x10e6, p, angle, white, 1, caster, -1, 0, 0, 0, 0.0, -1, 0, 0)` requests |
| 8 | Also `PlayBuffer(0x71, 0, 0)` at `0x01399628`, unless the world predicate returns 3 |
| 9..11 | Two `0x10e6/1` requests; keep the saved `+0x104` point |
| 12 | Two `0x10e6/1` requests, then set AttackTime to 15 |
| >=13, direct helper input | No trail requests; set AttackTime to 15. A normal cast has already ended |

The helper's model/bone failures can return before the listed later writes.
Missing-model and missing-transform answers are compared. The pre-body
dummy/index gate is static evidence. Native admission is
narrower: it requires the authored DK/bone context before requesting any trail.

For the three early requests, begin at caster position with z +120. Helper
`0x00d750fa..0x00d751da` scatters each coordinate by `rand()%601 - 300`.
Then x += `-1400*sin(yaw*pi_f/180)` and y += `1400*cos(yaw*pi_f/180)`.
This consumes nine rand values per emitting caller step. Both joint position
arguments receive this same scattered point. The light argument is NULL.

For AttackTime <=8, `0x0139984d..0x013999da` stores the transformed zero-offset
bone point into OBJECT `+0x104`, with x += `300*sin(yaw*pi_f/180)` and
y += `-300*cos(yaw*pi_f/180)`. This field remains fixed after step 8.

For the two marker requests, transform the selected bone again. Their forward
reach is `(AttackTime - 8)*10 + 100`, 80..140 units for steps 6..12. Add
`reach*sin(yaw*pi_f/180)` to x and `-reach*cos(yaw*pi_f/180)` to y. Light is
`1,1,1`; the requests are at `0x01399bdb` and `0x01399c21`. `pi_f` is the
client's binary32 `0x40490fdb`, with binary32 products and stores.

At steps >=10, `0x01399c29..0x01399c81` can write byte `0x23` to a looked-up
target object's `+0x40` when that target is live. The visual adapter omits this
CHARACTER/target-state path. Its comparison fixture answers the target lookup
with no target, while independently comparing every visual request.

## Joint and emitter lifetimes

| Kind | Creation | Movement and retirement |
|---|---|---|
| `0x472/2`, early red ribbons | Body `0x01548aeb..0x01548bab`: lifetime 20, max tails 5, colour `1,0.3,0.3`, supplied width 40, bitmap `0x7fde` |
| | The common create writes its first cross from the recycled record's previous width. The supplied target position replaces the owner's position for subtype 2 |
| | `0x01569e07..0x0156a15b`: width = lifetime*3. Clamp `(lifetime-10)/10` to 0..1; blend from the saved random point plus a 300-unit direction toward the owner's `+0x104`. `0x0158bac2` uses pool ordinal*`0x4539`, ambient clock and frequency 1.4. A missing/dead owner clears the owner pointer and keeps the current head; it still shifts tails, decrements and retires below 0. Thus 21 normal pool ticks from a fresh record |
| `0x10e6/1`, stationary trail marker | `0x013c465a`: lifetime 10, common effect fields preserved |
| | `0x014374f6..0x01437551`: one `CreateJoint(0x7f78, position, position, angle, 12, this marker, 100, -1, 0, 0, -1, NULL, -1, 0)` per effect move. The common effect lifecycle produces eleven requests before retiring. RenderEffects defaults at `0x015324cf..0x015324fc` only draw types below `0x7a4`, so this marker has no model draw; native draws its emitted joints |
| `0x7f78/12`, blue curls | `0x0154a9a2..0x0154ab15`: lifetime 70, max tails 50, supplied width, colour `0.1,0.1,1`, random phase `rand()%360`; drift x/y = `-4*sin(-yaw*pi_f/180)` / `-4*cos(-yaw*pi_f/180)`. Copy the supplied target point at `0x0154bfad` |
| | `0x01579558..0x0157993c`: phase = `(lifetime + random phase)*0.1`; lateral offset `-26*cos(phase)`, vertical offset `26*sin(phase) - (90-lifetime)*0.3`. Increment the stored target x/y by the drift; rotate the lateral offset by `90-yaw`. Below lifetime 10 divide each light component by binary32 1.3 |
| | Common tail `0x015896fb..0x015897e4`: shift, add time step, decrement. If alive and the new lifetime is not divisible by 12, recursively move the same record. A fresh curl therefore lasts seven outer pool ticks, including its terminal tick. It does not read the marker owner while moving |

Rendering retains the existing cross-tail geometry and blending. `0x472` uses
the lifetime factor `min(lifetime,20)*0.05`; Flare/12 uses its record light and
render type 1. The native loader adds `Effect/NSkill.jpg`, bitmap `0x7fde`, with
LINEAR/CLAMP from original startup call `0x018228a5`. The existing Flare texture
is reused. No particle pool or item/world consumer was changed.

## Native route and remaining limits

`mu_combat_step` calls the reconstructed helper before AttackTime increments.
The authored context requires class byte exactly 1, a non-none demo weapon,
Player model, non-dummy bone 33 and its posed matrix. Promoted class byte `0x11`,
other classes and missing weapon contexts are refused and counted. It uses the
current Player bone matrix, caster position/scale and angle. This does not
recover CHARACTER's selector or prove real gear/class eligibility.

One portable DK cast makes 21 early ribbons, 14 markers and 154 marker-child
curls, 189 visual requests total, zero refused. All effects and joints retire;
removing NSkill/Flare changes the rendered pixels; two repeated runs are
byte-identical. The only cast request remains unsent, target HP stays fixed,
and no hit, kill or authoritative target state is invented. The original
step-8 sound uses its recorded provenance.

The strict coverage inventory keeps Death Stab L because the general link
selector and unrestricted caller context remain absent. Other aliases,
master/later-class selectors, equipment-specific link choices, target-state
writes, persistent buffs, GPU/original-image equivalence and live play remain
outside this result. The next limited rows are Greater Defense/Damage; their
persistent aura context remains separate from a spell's cast animation.

Installed-data render evidence, default capture identity, exact affected rows
and final wall times are recorded in the handoff before PR-ready.

## Next limited skill, research only

Static follow-up on Greater Defense 27 and Greater Damage 28: normalized base
values `0x1b` and `0x1c` take the step helper's default branch
`0x013967be -> 0x0139b454`, rather than a Death-Stab-like emission branch.
The default tests animation/model state and can end AttackTime; it does not
provide their persistent aura. Their existing cast sound is the shared
`0x6f` call at `0x01255962`, with the class-`0x4d` exclusion, already recorded
by AUDIO-002C. These are static observations, not new instruction-comparison
families or evidence of a complete buff visual.

A separate aura lane must identify the actual buff-presence consumer and its
buff identifiers, exact attachment and removal requests, owner fields and
lifetimes. It then needs an explicitly authored presence/expiry fixture,
absent-buff refusal controls, original caller/consumer comparisons and a
visible render. This lane adds none of that state and no buff implementation.
