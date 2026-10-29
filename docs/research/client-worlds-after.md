# RENDER-WORLDS-AFTER: the second object pass, the world-group chains and the frame time

Target: the executable SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`, text and second-image-data
captures pinned in `scripts/pins.py` (capture09/run10). Method: static disassembly of the pinned text, then compiled
authored C compared with the original instructions under the strict Unicorn machine (`scripts/validate_worlds_after.py`).
Labels: **verified** = instruction-compared, **static** = read from the disassembly only, **inference** = reasoning.

## 1. Where the after-character objects leave the first pass (static, then verified per slot)

RenderObjects `0x016d5020` never reads OBJECT `+0xa`. Every visible object is drawn by RenderObject `0x016d4fe4`,
whose draw `0x017edf43` asks the custom render `0x017f76ec`. That routine runs a fixed chain (model/item cases,
worlds 2/8 types, then hooks `0x00deff29`, `0x00d8ea2c`, `0x00dfc3cf`, `0x00d63d6c`, `0x00dac3c1`, `0x00e760aa`,
`0x00e7ed6f`, `0x00e855f1`, `0x00d54e48`, singleton `0x00db747f` slot 0x38, `0x00e31985`, `0x00e6021d`,
`0x00a9c6c9`), ending at the world manager `0x00ea2f07`, which calls the **current world class's slot 0x38**.
A true answer skips RenderBody. So the "skip in the first pass" is per class: slot 0x38 answers true for the
flagged types and draws nothing (static for the chain before the class; verified for Abyss below).

RenderObjects_AfterCharacter `0x016d6949` then draws every selected object through `0x016d6791`: RenderObject's
setup `0x017ec896`, then the after chain `0x016d67c7` (Noria type 0x13 / world 8 types 0x59/0x5d bodies, then hooks
`0x00e765eb`, `0x00e7f718`, `0x00e86aac`, `0x00d550ea`, singleton slot 0x3c, Elbeland `0x00e321bb`, `0x00e60ab0`,
the world manager `0x00ea306c` → **class slot 0x3c**, `0x00d63f5f`). Each hook starts with its own world test
for worlds 0x25..0x2a, 0x2d..0x32, 0x21/0x36, 0x33 or 0x38 (static), so for the class worlds the second pass is
the class's slot 0x3c.

### The pass `0x016d6949` (verified, every world -1..150)

- **World test**: worlds 0x25..0x2a, 0x2d..0x32/0x62/0x63 (`0x0095fba9`), 0x33, 0x38, 0x39/0x3a, 0x3f, 0x52..0x5a,
  0x4f, 0x50/0x51, 0x5b..0x5e, 3, 0x21/0x36, 0x45..0x4a, 0x6e..0x71, 0x7a..0x85, 8, or the current world handler's
  byte +5 (manager `0x00ea594b` → `0x00ea273a` → slot 8 `0x00d5cb7c`). The base constructor `0x00d5c99f` clears +5;
  only the constructors of the classes of worlds **134..145** set it (static scan of all 48 constructors).
- Counter `0x06fc9c90` as in the first pass; bias −10 in world 10; sector range −180, or −300 in world 0x86.
- World 0x27 outside tower states 3..5 (`0x009a6ef3()+0x78`, field +4, `0x009a645f`) draws only type 0x4be.
- Per object: the selector `0x017fe909` first (draw regardless of sector, live and +0xa; visible byte = frustum at
  range + bias); otherwise sector visible (or top view), live, `+0xa == 1`, visible (or top view); world 2 type 0x64
  also needs hero level ≥ 0x35 for the master class (`0x0139d89f == 1`), else ≥ 0x50.
- **Selector `0x017fe909`**: a world switch (3: 0x13 at −600; 0x21/0x36: 0x19/0x29 at −600; 0x25 → falls through to
  0x33's case, its own test `type == 0x5f && type == 0x74` never holds; 0x33: 0x59 at −400; 0x39/0x3a: 0x4c at −600;
  0x3f/0x52: 0x10/0x43/0x44 at −600; 0x5b/0x5c: 0x1b, 0x3c..0x3e; 0x6e/0x6f: 6, 0x11, 0x96; 0x70: eight types;
  0x71: 0x6a; 0x7a: 0x58; 0x7b..0x7f: 0x86; **0x80..0x82: 0x17, 0x28, 0x29, 0x2c**; 0x83: 0xb2/0x6a; 0x85: type 6
  always, else `+0xa` at the object range). A failed case falls through to the class's slot 0x14 (`0x00ea27b4`):
  the base `0x00d5cbd6` answers no; 134 type 0, 136 0x18, 138 0x2d, 141 0x1f/0x20, 142 twelve types (first writes the
  range −800, type 0xc5 −1500), 143 type 0 always plus five types, 144 0x40/0x20, 145 live plus ten types, all at the
  object range; 135, 137, 139, 140 answer no.

C: `mu_world_after_gate`, `mu_world_class_after`, `mu_world_after_select`, `mu_world_after_pass_ex`
(`reconstructed/objects/world_after.c`). `mu_world_after_pass` keeps its signature (class flag from the world).

### Abyss of Atlans 1-3 slots (verified)

| World | Custom slot 0x38 | After slot 0x3c |
|---|---|---|
| 128 | `0x00d5d2f6` | `0x00d5d5ad` |
| 129 | `0x00d5ef96` (no world test) | `0x00d5f23a` |
| 130 | `0x00d606da` | `0x00d60991` |

Custom: types 0x17/0x26/0x28/0x2c/0x32 (the create's +0xa types, except 0x29) answer true with no draw; type 7 runs
an action gate (128: `rand()%10 >= 8` then frame ≥ 19; 129/130: frame ≥ 19.97 first, then `rand()%10 >= 7`; action 1
returns to 0 at the same frame limit; other actions draw nothing) and RenderBody(2, …); type 0x34 draws mesh 0
(flags 2, light = alpha) and mesh 0 again with blend −2, light `|sin(WorldTime·0.001)|·0.4+0.3`, bitmap 0x82df.
After: type 0x29 RenderMesh(0, 0x42, …, bitmap 0x82de); 0x17/0x26/0x28/0x2c/0x32 RenderBody(2, …); any other
selected type RenderBody(0x42, …); blend mesh through a float round trip (`cvtsi2ss`/`cvttss2si`).
C: `reconstructed/objects/world_abyss_visual.c`. Type 0x29 is drawn in **both** passes.

## 2. The "default hook chain" (verified predicates; static order)

CreateObject `0x016d8538` ends (static, `0x016d99c4..0x016d9ab5`): Chaos Castle `0x009dafa8` and `0x00def3ac`
(return on true), the custom-map class (world 92's, `0x0095c652(0x5c)` slot 0x2c; return on true), then
**unconditionally** `0x00d8e18f`, `0x00dfbc3f`, `0x00d6200e`, `0x00dabeb4`, `0x00e74a58`, `0x00e7dcf4`,
`0x00e84530`, `0x00d53d53`, `0x00d53d7d`, singleton `0x00db747f` slot 0x2c, `0x00e30a02`, `0x00e5f617`, and
**last** the world manager `0x00ea2ad6`: class slot 0x2c, then `0x00ce4a17(o, 0)` (SetAction(0) of the action
registry `0x01ec7d5c`) whatever the slot answered. MoveObject `0x017ff238`'s default branch (`0x01801554..`)
calls its hooks in the same order with an early return on true and **last** `0x00ea2c2b`: class slot 0x74
(pre-move), the registry tick `0x00ce4b5b`, then class slot 0x30.

So nothing runs *after* a false class create or move: the hooks run first and each is gated by its own world test.
The validator runs every hook's test for worlds −1..200 (`chain_predicates`, 3,232 cases) and, wherever the C says
none passes, the whole hook on a poisoned object (`chain_noop`, 5,192 cases: no write, no answer), including all
48 class worlds. The native per-world dispatch therefore needed **no change**. Open (static): slot 0x74 is a no-op
for every class except 69, 70, 71, 72, 79, 80/81, 92 and 122; `0x00ce4a17`/`0x00ce4b5b` act only when the action
registry (filled at run time) has an entry for (type, action); native create already leaves action 0, so the field
part of SetAction(0) is a no-op; the registry is not modelled.

## 3. The frame time `0x01cf103c` (verified)

Writer: the per-frame timing `0x012aeb2b` (FPS counter and WorldTime). Frame time = `(int)(now − prior) / 1000.0f`
from timeGetTime, or the constant `0x01ac8d6c` (bits `0x38d1b718`, one ulp above `0.0001f`) when the clock did not
advance; WorldTime `0x06fce370 = (float)(double)timeGetTime()`; FPS over a window reset after 2 s and 10 frames.
The image initialises the frame time to 0.1 (client-effects.md). C: `native/core/mu_frame_time.{h,c}`
(1,000 cases of the whole routine up to `0x012aec9f`, all four clock reads).

Native wiring: the five 0.1 stand-ins (objects render pass, environment, particles, worlds-P moves, actor effect
nodes) read `mu_frame_time_value()`. It is ticked **only** by the two window loops (`mu-world` SDL loop and the
client window loop), with SDL ticks. The fidelity tour, headless tools and tests never tick and keep 0.1, so no
hash changes; this is recorded on purpose: the tour renders 2 of 25 logic steps, so a real frame time there would
be ~0.5 s and change every particle world without bringing it closer to a live frame.

## 4. Checks

`scripts/validate_worlds_after.py --cases 1000 --mutations`: **13,424 cases equal, 0 mismatches, 0 stops**
(after_pass 1,000, select 1,000, abyss_custom 1,000, abyss_after 1,000, chain_predicates 3,232, chain_noop 5,192,
frame_time 1,000); **21/21 compiled mutants detected** (several by 1–5 cases: tower state 5, world-2 level 0x35,
class 145 live, world 0x25 fall-through, Abyss 1 chance 8). One planted change was equivalent (the bias on the
selector path: no world with a bias has a selector case) and was replaced by the flagged-path bias.
WORLDS-A's validator (9,000 cases, 13 mutants; its "special visibility" mutant now targets the selector call) and
world order (2,400) pass on the generalised pass.

## 5. Fidelity

Base = origin/main `f7a1e33` built in a temporary worktree, lane = this branch, both at the DATA-ACQ-002 arrival
tiles (32 captures, 25 steps, 1722×1048) and the October 22 fourteen views (live PNGs deleted October 23, so only
hashes there).

- **29 of 32 DATA-ACQ-002 captures and all 14 October 22 views: PNG, OBJECT and light dumps identical.**
- Abyss 1 (128): 13 objects leave the first pass (241 → 228 drawn), 26 after meshes; the frames stay byte-identical
  (the moved bodies are opaque and nothing in front of them changes). Image mean |Δ| 5.386 → 5.386.
- Abyss 2 (129): 338 → 300 first-pass draws, 82 after meshes; frames identical; OBJECT dump changes (type-7 action
  gate draws rand(); actions/frames differ). 4.412 → 4.412.
- Abyss 3 (130): 266 → 239, 56 after meshes; 8 / 10,841 of 1,804,656 pixels differ (top band: animated plants and
  fish in another phase, because the action gate draws rand() each frame). 2.230 → 2.230; share > 24 unchanged.
- Near-hero field differences unchanged (blend light 60/58/72, blend mesh 4/12/18; after-character already 0).

## 6. Limits and next

- Custom/after slots of the other verified classes (Kanturu Underground `0x00e092f4`/`0x00e0ab2a`, Ignis
  `0x00e05f25`/`0x00e0709e`, Nixies `0x00e347a8`/`0x00e3628c`, 135/136/140, the A worlds' remaining types): the
  second pass now lists their objects correctly (verified), but native draws them only in 128..130 and the A worlds
  (`mu_world_after_native`); elsewhere the first pass still draws them.
- Bitmap meshes (0x82de, 0x82df) are refused and counted in `draw_unsupported`: native has no bitmap → model texture path.
- The custom-render chain before the class slot is static; the action registry `0x01ec7d5c`, slot 0x74 of eight
  classes and the invisible-move slot 0x1c are not modelled.
- The shadow block of RenderObject is untouched.
