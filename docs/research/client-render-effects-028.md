# Greater Defense and Greater Damage fixture auras

RENDER-EFFECTS-028 adds an opt-in presentation fixture for skills 27 and 28.
It supplies authored buff presence and an authored expiry clock. It carries no
buff values, character stats, authoritative cast result or service state.

## Evidence and method

The executable identity is SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Capture09 text is
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Run10 image data is
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
All original bytes remain private. No live client was started or inspected.

Static inspection found the persistent consumer in RenderCharacter, separate
from the default attack-step path described by EFFECTS-027. The new comparator
executes the bounded inline slice `0x01370ccc..0x01371132` with its declared
caller frame, followed separately by original CreateJoint, MoveJoint and
RenderJoints. Buff queries, joint-existence queries, link-bone lookup and
TransformPosition are explicit services. The latter returns independently
authored points. The comparison includes ordered complete sprite/joint calls,
bone queries, RNG consumption, modeled record fields and the recorded GL stream.
The slice stops at its own boundary; surrounding character rendering is outside
this proof. The common frame exit restores caller registers and SEH state.

Original-side lifecycle bytes are carried independently from creation through
37 moves, including owner movement and the final expiry or owner-live removal.
Each of the five pool ordinals is checked. Original output is never reseeded
from the native record between moves. Host sine/cosine remain declared libm
services, as in the existing joint validators. GPU equivalence is unclaimed.

## Presence and requests

Presence accessor `0x01295ade` reads the OBJECT buff collection at `+0x358`.
The private language table independently names IDs 1 as attack, 2 as defense
and 3 as the combined Shadow Phantom effect. Only the reviewed identifiers and
roles appear here, not the private table or buff values.

| Site | Behavior |
|---|---|
| `0x01370ccc..0x01370d18` | Attack-side presence is ID 1, 3 or `0x15a`. It takes precedence over the defense-only branch |
| `0x01370d18..0x01370d33` | ID `0x12` suppresses attack sprites and new joint attachment |
| `0x01370d33..0x01370f65` | Two link groups. Each samples one rand: pulse = `(rand()%30 + 70)*0.01`. Light is pulse times `1,0.3,0.2` |
| `0x01370dbf..0x01370f60` | CHARACTER `+0x19b1 + group*0x3fc` supplies the link bone. Draw at that bone, bone minus 6, bone minus 7. A missing bone ends the sprite loop. TransformPosition uses zero offset and its final argument 1 |
| `0x01370e41`, `0x01370ece`, `0x01370f58` | Each point requests Shiny02 `0x7f67`, scale 1.5, owner OBJECT, rotation 0, blend 0, axes 4, default axis descriptor `1,1,1.0` |
| `0x01370f65..0x01371021` | If neither `0x472/4` nor `0x472/9` exists for the owner, request five `0x472/4` joints. Width 20, both points = owner position, owner angle, key -1, skill 0, byte10 0, argument11 = signed CHARACTER target key, NULL light, word13 -1, argument14 0 |
| `0x01371026..0x01371132` | With no attack-side presence, ID 2 or `0x15b` and no ID `0x12` requests the same five joints, without weapon sprites |

The attack-only path really does request the same subtype 4. Its mover below
keeps it only for defense/combined presence. Therefore attack-only fixture
draws keep the weapon sprites and recreate the short-lived joint requests.
No invented attack-specific orbit subtype replaces this behavior.

## Joint lifetime and draw

CreateJoint's subtype table at `0x0155397c` maps both 4 and 9 to
`0x01548998..0x01548a09`: light `0.4,0.8,0.2`, lifetime 10000, 30 tails,
texture `0x7fdd`. The common part uses the previous record width for the first
cross, copies the owner position and installs the supplied width 20.
The reconstruction reuses that common part through supported subtype 1 and
then applies the exact subtype-4 overrides. It preserves record reuse.

MoveJoint first performs equipment lookup `0x01569cda..0x01569e07` using the
retained target key. A selected equipment context can switch subtype 4 to 9.
The fixture supplies no such equipment lookup result, so it admits only the
ordinary subtype-4 branch. Subtype 9 remains unsupported here.

`0x0156a997..0x0156ac58` clears live and lifetime when the owner is no longer
live, or when IDs 2, `0x15b` and 3 are all absent. Otherwise it refreshes lifetime
to 100. The common tail decrements this to 99. ID 1 alone does not refresh it.
The fixture maps authored expiry to absence and owner death to a dead owner.
This proves the visual consumer's removal, not the original death-to-buff-list
update or a server's duration calculation.

Existing tails first subtract the previous target point, then add the new
owner position with z +10. This keeps the whole ribbon attached while the
owner moves. The orbit uses pool index times `0xd1e3`, plus ambient clock for
odd indices and minus clock for even indices. Frequencies are binary32
`0.048,0.0613,0.1113`; the rotated spherical direction uses radius 80 in x/y,
and z = target z +110 + direction z*120. The common closing tail, time step
and lifetime retirement execute as in the original. No particle is emitted.

RenderJoints `0x0158a5a4..0x0158a955` adds behavior absent from the older generic
joint renderer. Each segment uses light minus positive
`(tail[0].z - (owner.z +50))*0.01`; nonpositive values retain the record light.
At segment `num_tails/2`, the average of its four corners requests one
`0x7fdd` sprite, scale 0.7, no owner, rotation/blend 0, axes 4 and the same
height-adjusted light. The new aura renderer wraps the common joint renderer
for this color and sprite behavior, retaining its GL state, geometry and UVs.
The null-owner original path uses an uninitialized local for the midpoint
sprite color. Native refuses that context, and comparisons use a present owner.

Startup LoadBitmap calls `0x01822885` and `0x01822045` load
`Effect/flareBlue.jpg` and `Effect/Shiny02.jpg`, both LINEAR/CLAMP. The native
combat bitmap table adds these two slots. The particle/item tables are unchanged.

## Fixture admission and limits

Set `MU_AURA_FIXTURE_TICKS` to an integer 1..10000 before starting the native
combat fixture. A scripted or accepted demo cast of skill 27/28 sets the hero's
corresponding expiry to current logic step plus that duration. Disabled,
invalid and absent settings add no aura. Recasts refresh only their own expiry;
the two flags can overlap. This is an explicit hero appearance fixture even
when a combat script names a synthetic target. No target buff state changes.

The adapter uses five dedicated joint slots with ordinals 0..4 and authored
Player link bones 33/42. Missing or dummy bones refuse and count the missing
sprite context; valid earlier bone sprites and the joint path retain the
original loop ordering. These links do not recover general equipment selection.
The optional flags 3, `0x12`, `0x15a` and `0x15b` are comparator inputs only;
the native fixture casts only the two base buffs. No further buff is admitted.

The original requests stay unsent and fixture target HP remains fixed. Existing
cast animations and sound selection are unchanged. Buff packet handling, real
buff durations, master selectors, alternate equipment/subtype-9 visuals,
original GPU images and live play remain outside this result. The strict
coverage rows remain limited because their authoritative feed and unrestricted
owner/equipment contexts are absent.

Final counts, wall times, fixture counters and identity evidence are in the
[handoff](../handoffs/RENDER-EFFECTS-028.md).
