# Bow joints, multishot02 and the gunbow model colour

Target: Mu The Matrix `main.exe`, SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
RENDER-EFFECTS-012 continues [011](client-render-effects-011.md). No live client was used.
The source is the pinned restored instruction image, not another MU client.

## Instruction evidence

`validate_render_effects12.py` reuses the joint create/move/full-GL-stream families and the arrow effect
create/move families. It executes CreateJoint `0x0153b02c`, MoveJoint `0x01556c26`, RenderJoints
`0x01589b56`, CreateEffect `0x013c0f19` and MoveEffect `0x0142fd09`. Randomness, owner lookup, terrain and
external calls are controlled recording services; the original vector helpers execute. Text SHA-256:
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; data SHA-256:
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
`MU_SECTION3` is provided for affected validators that need initialized section-3 data. These new families
use text/data plus declared synthetic globals. No captured bytes are committed.
Final counts and wall times are recorded in the [handoff](../handoffs/RENDER-EFFECTS-012.md).

| Kind (subtypes hexadecimal) | Create body | Move body | Reconstructed behaviour |
|---|---|---|---|
| 0x80e3/4 | 0x015508d2 | 0x01583f63 | Width from caller, velocity 40, eight tails, life 20, blue-green light, reversed U; dead owner sets life zero before the closing decrement |
| 0x80e4/1 | 0x01550adc | 0x01584164 | One pair of faces, pale blue, velocity 70; dead owner returns before the closing tail shift and decrement |
| 0x814c/a | 0x01550ec2 | 0x01584f62 | One pair of faces, eight tails, velocity 60, life 30, caller colour |
| 0x8182/a, 0x8185/a | 0x015510b7, 0x01551101 | 0x015853fb | As above, ten tails |
| 0x85cc/0 | 0x0154c01c | 0x0157c4e8 | Eight tails, velocity 70, caller colour/target position, UV mode 5; death follows owner |
| 0x828c/2 | 0x015516c3 | 0x01585972 | Six tails starting at -1, reversed U; head follows owner plus rotated normalized (0,-1,0) times 15 |
| 0x7f79/c, /12, /16 | 0x0154c119; 0x0154cd27, 0x0154d03b, 0x0154d26f | 0x0157d2f5 | Signed key becomes lifetime, stored key clears; 16/7/9 tails, purple/caller/orange palettes; fade below life 15; c and 16 add terrain light |
| 0x38b5/1 | 0x013cb6b6 | 0x014348b7 | Shared arrow create body, life 13, blend mesh -2, caller scale; scale +0.1, blend/alpha life/18; no arrow hit check |

RenderJoints `0x0158b39f` adds Flare02/c's per-tail colour multiplier
`(num_tails - 1 - tail_index) / max_tails * 2`. This comes after the thunder-bolt colour case.
The first instruction sample exposed this missing call and multishot's incorrectly inherited arrow check;
both were corrected. The first full sample then found three one-ULP 0x828c/2 position mismatches:
AngleToVector calls 0x00cff0d3, which divides each component by the float length; the reused
0x00cfd15f helper multiplied by its reciprocal. The bow path now follows the former. No comparison
tolerance was relaxed, and the failing base run compiled no mutants. The comparison includes state, colour, binding, UVs, corner order,
quad count, owner death, closing tails and random-call counts. Flare02 create samples include skill 0 and 1;
skill 3's non-null-owner colour read is statically transcribed, outside that sampled domain.
The 0x814c/0x8182/0x8185 move domain requires an owner because the original dereferences it unconditionally;
both live and dead owners are sampled. Other move kinds include null owners.

## Native integration

Combat's bitmap capacity grows 16 to 24, with a compile-time table/capacity assertion. The eight appended
registrations match the existing startup bitmap survey: Flare02 (0x018228e5), force_Pillar (0x01835b52),
!SwordEff (0x01835b72), sharke_arrows (0x01821dd9), devil_arrow (0x01833b47), arrows_angelic (0x01833ba0),
Swordeff_mono2 (0x01837b6c), Swordeff_mono3 (0x0182f066). They use the existing joint renderer, including its current linear/repeat bitmap upload policy; this lane
does not claim exact texture-edge sampling against the original clamp registrations.

The native arrow emission callback had discarded CreateJoint's key, skill and colour, substituting the hero key.
It now forwards those arguments for arrows. This is necessary for Flare02's lifetime and the coloured trails.
The current call record represents a null colour by an all-zero vector; the supported arrow callers always
supply a nonzero vector when a colour pointer is present. This is a caller-specific boundary, not a general
pointer-presence representation.

0x38b5 loads `Data/Effect/multishot02.bmd` only for bow 0x130e (arrow 0x60f), preserves its emitted scale 0.2
and key, and bypasses the generic model cutoff at 0x7a4. It is an effect, so it does not increment the arrow count.
RenderEffects' 0x45e case at `0x01518f49` writes model colour (+0x54) to (1,1,1); the native draw now applies that
colour to both model passes. Portable tests use authored synthetic models and inspect the draw callback.
These tests and native before/after scenes do not establish pixel equivalence to a live original-client scene.

## Remaining work

- 0x7f78/b: ambient-clock orbit, owner +0x110 input, owner position writes and collision service. Reconstruct the
  full owner contract before admitting it.
- 0x80e3/5: reads the owning effect's lifetime (+0x6c), absent from the joint owner adapter. Add and compare that
  field before admitting this subtype.
- 0x7f79/e and /f: downstream particles are still unported. Reconstruct and compare the emitted kinds and their
  native route before admitting the joints.
- 0x70c's 0x703..0x706 children, stone subtype 0x13, native ground-skill route, and the owner +0x64 clearing site
  remain as in 011. No new claim is made about the one-play landing sound lifecycle.
- 0x45e's 0x8002 decal for subtypes 3..7 remains counted but undrawn; bow arrows do not use those subtypes.
- Uruk 0x806e/12 needs a captured weather input and a weather feed; Muun table work needs native Muun owners.
  Neither input/owner domain was added here.
