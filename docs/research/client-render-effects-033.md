# Learned-skill presentation, RENDER-EFFECTS-033

Offline authored fixtures only. Baseline combines EFFECTS-032 b8ef0051 with
main 6900914e, including EFFECTS-031. No actor, app, UI or power work.
Target/text/data identities use scripts/pins.py and the EFFECTS-032 captures.

## Initial classification

The inherited 29-row table is 11 P / 7 L / 11 M. All eighteen L/M rows
are listed below before implementation. P means bounded primary presentation,
L means visible subset, M means missing primary presentation. These labels
never grant eligibility or claim authoritative input.

| Skill | Before | Exact missing part |
|---|---|---|
| 344 Blood Storm | M | Effect 0x583/0 emitter and 0x584/0 body; emitter also requests 0x585/0 and 0x586/0; body requests particle 0x8145/1. Full lifecycle, owner +0x3b and draw dispatch unproved |
| 52 Penetration | L | Effect 0x46c/0 follows the arrow owner action/live/position; charge is now supported by 031 |
| 51 Ice Arrow | L | Optional target-side ice presentation input/caller; primary arrow already supported |
| 18 Defense | L | Original held-input lifetime and shield body context; current finite pose is supported |
| 48 Swell Life | M inherited | Requests recovered by 030, consumers now supplied by 031; reassess combined fixture; persistent presence remains separate |
| 44 Crescent Moon Slash | L | Final effect 0x49e/0 create/move/draw consumer |
| 49 Fire Breath | M | Effect 0x8001/0 consumer; mount body/lifetime unavailable in current fixture |
| 30 Summon Goblin | M | Shared ground effect 0x7f84/3; summon actor selector/body and lifetime |
| 31 Summon Stone Golem | M | Same shared ground request; actor selector/body and lifetime |
| 32 Summon Assassin | M | Same shared ground request; actor selector/body and lifetime |
| 33 Summon Elite Yeti | M | Same shared ground request; actor selector/body and lifetime |
| 34 Summon Dark Knight | M | Same shared ground request; actor selector/body and lifetime |
| 35 Summon Bali | M | Same shared ground request; actor selector/body and lifetime |
| 36 Summon Soldier | M | Same shared ground request; actor selector/body and lifetime |
| 43 Death Stab | L | General equipment/link selector, outside current base-DK bone-33 proof |
| 27 Greater Defense | L | General equipment links and authored presence lifecycle beyond bounded aura fixture |
| 28 Greater Damage | L | Same shared link/presence boundary |
| 47 stale entry | M | Absent record, always refused; capacity entries past learned count excluded |

Uniform groups: seven summon rows share one ground consumer and actor contract;
two aura rows share link/presence services; the other nine rows each have the
specific gap above. All ordinary request forms are already recovered by 030/032.
There is no request-only M group left on this combined base. No alias is admitted
by sharing a consumer.

Frozen Native Data lacks exact names DarkLordSkill.bmd, Flame01.OZJ and water.OZJ.
No refresh is permitted. Rows requiring these assets stay refused with frozen
input even if separate full read-only game data can demonstrate a component.
Effect 0x47a is reserved for MUUN-VISUAL-005 and is not changed here.

## Recovered consumer contracts

The original target is `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The pinned text hash is
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`;
data hash is
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
These are offline original-instruction comparisons over authored records and
named services. Animation/bone service outputs are fixture inputs; draw-stream
checks compare ordered GL calls. Native asset appearance is separate proof.

| Consumer | Original boundary | Recovered behavior |
|---|---|---|
| Effect 0x7f84/3 | create 0x013c80a3; move 0x0143fbda | Twenty-step ground emitter, three JointEnergy01/3 children per step; exact default key -1 |
| Joint 0x7fd8/3 | Existing Energy01 dispatch | Same homing/lifetime as subtype 1, orange (L, .6L, .4L) palette |
| Effect 0x46c/0 | 0x013ca40b..0x013ca7ec; 0x01463c5e..0x0146409b | Owner live/position/angle, saved prior position, heading spin; four Flare02 trails, key 30, skill 0; sound 0x7a |
| Joint 0x7f79/0..3 | Flare02 dispatch | Caller width/radius, three substeps, owner heading/impact; 50-tail capacity, closing tail, fade and owner death |
| Effect 0x412/1,2 | 0x013d01f8..0x013d04e1; 0x0146bbb8..0x0146bfef | Target presence ID 0x39; action-dependent hidden-all flag; frame hold, fade, subtype-1 orbit/Fire03; source-light mutation |
| Particle 0x7f3e/10 | Fire03 uses Fire01 cases | Life 24, ordered velocity/rotation RNG, shrink .95, vertical gravity, four-frame strip and full GL stream |
| Effect 0x583/0 | 0x013f2b83; 0x014a18fc | Life 70, caster-owned 0x584, sound 0x2b0; ten jittered 0x585 requests and central 0x586 |
| Effect 0x584/0 | 0x013f2c53; 0x014a1b1c..0x014a2131 | Owner +0x3b must equal 1; life 36, .35 animation; bone-zero 0x4b7/1, 55 blur calls over eleven exact bones, brightness ramp |

The Blood Storm loop poses once at frame minus action speed, then reuses that
pose in all five outer samples. The loop computes speed / 35 and increments a
local frame, but does not pose again. No interpolated intermediate poses are
invented. The constructor-reachable action is 0; other actions and out-of-range
parent scale indices are refused. Downstream 0x585/0, 0x586/0, 0x4b7/1,
particle 0x8145/1 and blur 0x814b remain counted refusals, so the body is a
visible subset. Piercing.bmd and blood_storm_sword.bmd use the exact static
AccessModel paths (0x0183461a and 0x01836133); action-0 speed is set at
0x0183616a. Fire03.jpg uses the original LINEAR/CLAMP loader entry.

`MU_SKILL33_TARGET_ICE` is an authored positive tick count (maximum 10,000),
default zero. The original target visual slice 0x01256b8a..0x01256cc7 deletes
subtype 1 and creates both ice effects only when its input byte is nonzero.
The first constructor mutates the supplied light; the second request sees
(.4, .3, .2), not a fabricated white reset. The following target freeze/movement
writes are excluded. The fixture owns a separate visual-presence expiry; it
never writes actor state or derives a freeze from hitting with an arrow.

`MU_SKILL33_BLOOD_OWNER=1` supplies the body owner's +0x3b view explicitly.
Zero, absent and invalid values leave the body disabled. This is separate from
the skill request and does not write an actor or infer live hit state.

Defense remains finite. The action fragment 0x01222f89..0x01222fb0 only invokes
SkillAction and sound. SkillAction 0x012b001a..0x012b0088 selects the action;
the recovered default MoveCharacter cutoff ends at frame 5. None establishes
a held-button renewal/release rule. No arbitrary hold duration is admitted as
original behavior. Shield geometry and the held-input rule remain the exact
missing dependencies.

## Actor and adjacent-lane audit

The summon end request contains a ground effect and no actor selector or actor
lifetime. An actor body's existence therefore cannot turn that ground request
into actor creation. The baseline had ACTORS-005; pushed ACTORS-006/007 plans were inspected
read-only. ACTORS-006 is now integrated from batch 115 main. Candidate ordinary fixture selectors 20, 21, 32 and
150 have checked plain bodies on 006; 26 has a checked body/weapon group on
007. Selectors 10 and 151 still need effect caller services on 007. The
skill-to-actor mapping and separate spawn/lifetime input remain unproved for
all seven summon rows; they stay M. These selector numbers are actor-lane
follow-up candidates, not a new skill admission table. No actor file changed.

Late inspection of ITEMS-002AA and INNER-005 pushed WIP handoffs found no
complete small refused-consumer ID contract suitable for admission here.
Their new producers retain named missing dependencies; no extra pair is
admitted from an incomplete WIP statement.

## Verification method and corrections

The single grouped verifier checks every pair against original instructions,
including full particle/joint draw streams, ordered RNG, optional target caller,
Blood Storm pose frame/angles and all blur arguments. Existing 030/032 callers
supply per-skill original checks for aliases and seven summon rows; native
fixtures exercise each affected skill independently. There is no blanket alias
admission. Forty-five compiled controls cover records, calls, draw streams,
owner mapping and native callback defaults. Final counts/timings follow in the
handoff after those controls run.

Exploratory failures found a mutable ctypes callback reference, the wrong
Energy01 dispatch branch, a missing fourth trail, lost native self ownership,
a fragment exit hook registration, and a zero-vector bone argument represented
as an address. Each was corrected from the pinned instructions or a native
boundary assertion; failed runs are not proof. The old 031 null-owner census
still refuses 0x46c and 0x583. Only 0x584's obsolete missing-kind expectation is
updated; the new positive owner contexts are checked here.

A native lifecycle test also exposed the per-step object-view reset: the arrow
view was cleared before its owned effect moved. The native now refreshes an
arrow view immediately after moving that arrow, so its later 0x46c child reads
the moved live record. A compiled native control removes that refresh and must
fail the live-child assertion. This changes no actor record.

The parent Arrow01/2 constructor is also compared with all fourteen nested
CreateEffect arguments, including the default info word8 of -1. Native combat
and world adapters preserve that word along with self ownership and key.

Final grouped proof: 6,410 checks equal, 45 compiled controls detected, no
original stops. Fourteen controls completed before a harness-only target-ice
argument dispatch error; only the remaining 31 resumed. The native controls
include self owner, key, heading and same-step owner refresh. No passing
control was repeated. Final affected replay, assets and identity results are
recorded in the handoff.


## Updated learned-skill table

The verified fixture boundary moves **11 P / 7 L / 11 M to 14 P / 6 L / 9 M**.
P is bounded primary presentation, L a visible subset, M missing primary
presentation. It is not a whole-client fidelity score or an eligibility claim.
Swell Life is a reassessment of the combined 031 consumers and 030 caller,
not a newly authored consumer in this lane.

| Skill | Before -> after | Current boundary |
|---|---|---|
| 0 ordinary attack | P -> P | Unchanged |
| 19 Falling Slash | P -> P | Unchanged |
| 20 Lunge | P -> P | Unchanged |
| 21 Uppercut | P -> P | Unchanged |
| 22 Cyclone | P -> P | Unchanged |
| 23 Slash | P -> P | Unchanged |
| 41 Twisting Slash | P -> P | Unchanged |
| 42 Anger Strike | P -> P | Unchanged |
| 43 Death Stab | L -> L | General equipment/link selection remains open |
| 44 Crescent Moon Slash | L -> L | End consumer 0x49e/0 remains refused |
| 18 Defense | L -> L | Finite pose; held-input renewal/release and shield body context unproved |
| 47 stale entry | M -> M | Always refused; no invented record |
| 48 Swell Life | M -> P | Combined bounded cast: 36 initial ribbons, 36 children and two ground effects; zero unsupported requests |
| 49 Fire Breath | M -> M | Primary 0x8001/0 and mount body/lifetime remain missing |
| 344 Blood Storm | M -> L | Parent and sword body work; downstream burst, particle and blur consumers remain counted refusals |
| 24 Triple Shot | P -> P | Unchanged bounded caller/context |
| 26 Heal | P -> P | Unchanged |
| 27 Greater Defense | L -> L | General equipment links and authoritative presence remain open |
| 28 Greater Damage | L -> L | Same bounded aura boundary |
| 30 Summon Goblin | M -> M | Ground supported; matching-name candidate 26 has a body/weapon plan on ACTORS-007; spawn/lifetime input unproved |
| 31 Summon Stone Golem | M -> M | Ground supported; matching-name candidate 32 has checked body; spawn/lifetime input unproved |
| 32 Summon Assassin | M -> M | Ground supported; candidate 21 has checked body; spawn/lifetime input unproved |
| 33 Summon Elite Yeti | M -> M | Ground supported; candidate 20 has checked body; spawn/lifetime input unproved |
| 34 Summon Dark Knight | M -> M | Ground supported; candidate 10 also lacks actor effect/sword-sprite services |
| 35 Summon Bali | M -> M | Ground supported; candidate 150 has checked body; spawn/lifetime input unproved |
| 36 Summon Soldier | M -> M | Ground supported; candidate 151 also lacks actor effect services |
| 51 Ice Arrow | L -> P | Existing arrow plus separately authored target ice; no freeze or damage input inferred |
| 52 Penetration | L -> P | Existing charge/arrow plus the owned child and four trails |
| 2044 Raining Arrow of Saturation | P -> P | Unchanged |

Explicit synthetic aliases 416/52 and 424/51 move L -> P outside those 29 rows.
All other aliases keep their prior refusal/inventory state. Candidate actor
names match the existing read-only language snapshot; that is not proof of a
skill spawn selector. Main's ACTORS-006 body plans are used only as read-only
census evidence, and no ground request is converted into actor creation.
