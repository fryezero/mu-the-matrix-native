# ITEMS-UI-001

Branch `codex/items-ui-001`, GPT-6.1 Sol. Based on `d4af71dd`; merged UI-WINDOWS-001
main `710ac816` as `43d97c28`, then main `6b75fbda` (#373..#376) as `35c9c51d`.
Final implementation checks are at `537572ef`'s tree. Later edits are documentation
only. [Original addresses and limits](../research/client-items-ui.md).

## Result and scope

Equipment hover now uses the original wrapper's independently truncated 640x480
slot rectangle and integer mouse coordinates. The same hit opens an equipment
item tooltip through the existing fixture code/level callback. It also drives the
existing icon selection/spin path. Native previously tested a floating window
rectangle and supplied no equipment tooltip.

The full authored level word already reaches the icon adapter. In the compared
bodies, option/luck/skill bits `0x87` add no glow: the original extracts level with
`>> 3 & 15`. Excellent and ancient/set flags are separate arguments and were already
connected by INVENTORY-FX. No new glow interpretation or shared renderer change
was needed. Ordered original/native body, mesh and colour streams match with all
16 combinations of `0x87`, levels 0..15, and separate excellent/set controls.

The existing movie -> item -> overlay ordering is retained. The captured main-game
UI path reaches opaque `0x10b3e920`; original same-frame GFx/sprite/tooltip ordering
remains unverified. This lane does not follow that hook or claim parity through it.

Offline/static only. No subagents, live client, memory writes to a process,
network/service work, original launcher, installed-app replacement, item-table
or generator changes, README work, or character-stat formulas. Appearance records
and names are authored demo values. Other lanes' installed-app work is separate.

## Original evidence

- `0x016c246e..0x016c248b`: four independent CVTTSS2SI slot conversions and call
  to `0x00ec4bf2`; the latter compares signed integer half-open bounds with x86
  wrapping additions. Native `native/gfx/items_ui.h` reproduces it.
- `0x0121012c..0x0121016b`, `0x012101ab..0x012101f7`: window mouse division,
  truncation and clamp to 640x480. Retina input is converted to window points first.
- `0x016c24d7`: tooltip request after the hit; ordinary popup rectangle path
  `0x00cda1cf` -> `0x00cda471` -> `0x00cda352` -> `0x00b8c7f9`.
- `0x017e7960` / `0x017e7997`: full word, excellent and set arguments reach
  RenderObjDraw separately. Level extraction `0x0176cf4a..0x0176cf53` and helper
  `0x016a78c9..0x016a78d6` discard `0x87`.
- `0x01859ab6` / `0x01859bb1`: main-game RenderSprites call sites precede the
  legacy UI pass and opaque hook. Captured per-window pass `0x00abfcca` and its
  captured caller chain are recorded in the finding; its main-game invocation is
  not recovered.

The finding records capture hashes and the exact bounded comparison domain.
No original bytes or decoded client data are committed.

## Checks

All commands ran from the repository root with canonical
`. ~/Documents/MTM/mu-mac-tools/native/private-env.sh` for private work. Builds used
nice 10 and at most `-j4`; validator/test pools used two jobs. No lane full gate.

| Check | Actual result | Wall |
|---|---|---:|
| Root build after latest-main merge, `make -j4` | pass, no warnings | 18.15 s |
| Final GL world check, `make -C native -j2 world` | up to date after the affected/private scene builds | 0.20 s |
| New `validate_items_ui --mutations`, at `57ad1819` | 3,144 cursor + 3,064 mouse + 2,304 draw-stream comparisons + 5 static checks; zero mismatches; **8/8 compiled mutants caught** | 20.12 s |
| Initial affected validator selection | 10 rows | 29.22 s |
| Initial affected portable suites at `bb492408` | 123 work items; 1,281 tests, 1,041 passed, 240 skipped, zero failures/errors | 451.30 s including selection |
| Initial affected private validators, no mutants/cache, at `bb492408` | 10/10 passed, zero skips | 101.50 s |
| Initial reduced private UI/scene pass | 29 passed, no skips/failures | 73.40 s |
| Stricter popup-coordinate controls | normal and Retina popup arguments `[958,40,30,40]`, both passed; also included in the final private pass | 1.37 s |
| Post-merge validator selection against `bb492408` | 5 of the lane's 10 rows have changed inputs | 53.34 s |
| Those five rows, no mutants/cache, at `537572ef` | 5/5 passed, zero skips | 40.39 s |
| Post-merge affected portable suites, `--affected-since bb492408` | 165 work items; 1,777 tests, 1,482 passed, 295 skipped, zero failures/errors | 520.30 s including selection; 407.9 s execution |
| Final private native UI/scene pass, **8d reduced**, at `537572ef` | 29/29 passed, no skips/failures; original short run, integer/Retina/rollout/close, actual equipment hover, six accessories, shared GFx hosts, new-window controls, four-start repeatability in both HUD scenes | 63.69 s |
| Final after-only overlay captures | two fixed-clock scenes, zero missing models; before images reused | 9.50 s |
| Default identity sweep | all 276 files identical across 46 views; original before hashes reused after main merge | before 112.75 s; final after 108.47 s |
| Final repository audit | 2,207 staged files, zero rejected | 41.38 s |
| Final documentation/manifest modules | 53 distinct tests: 52 passed, one private-input skip | 2.03 + 12.75 s |

8d was reduced because the native selection exceeded 40 items: 121 initially,
153 after the core-code main merge. The private command selected `test_items_ui`,
Inventory-FX reconstruction/scenes, FOLLOWUPS accessory and frame-zero classes,
GFx2/GFx3 stand-in hosts and UI-WINDOWS presentation controls. It did not rerun
unchanged validators' mutants. The stand-in C host emits three existing
missing-field-initializer warnings; production builds do not.

One initial mutant attempt stopped under `-Werror` because the endpoint-rounding
mutant left a variable unused. The authored mutant was corrected; the complete
final run compiled all eight and detected each. No production arithmetic changed.
The documentation follow-up initially used `tests.` instead of `native.tests.`
for two modules. Its other 30 tests passed; only those two modules were rerun
under their correct names, yielding the remaining 23 tests with one skip.

The machine repeatedly exceeded the load guard, including load 72 while this lane
had no heavy job running. After more than 20 minutes of post-merge resource waits,
the common brief's `-j2`/two-worker fallback was used, still at nice 10 and with
memory/disk checks. Before that, one early baseline world build started from a
combined resource-print/build command before its high-load output was inspected.
Subsequent heavy launches used an inspected or programmatic guard.

## Steward validators

Run with canonical private-env.sh, `--private --no-mutants --cache --jobs 2`.
No further mutants are required. The new header's mutants passed at `57ad1819`;
its inputs did not change through either main merge.

| Row | Cases or checks | Wall at `bb492408` | Post-merge wall at `537572ef` |
|---|---|---:|---:|
| validate_gfx3 | caller/feed/adapter checks pass | 6.7 s | inputs unchanged |
| validate_map_polish | 876 | 0.8 s | inputs unchanged |
| validate_audio_callers | 5,528 | 7.5 s | 6.7 s |
| validate_audio_domains | 2,544 | 36.3 s | 40.3 s |
| validate_audio_items | 3,000 | 5.6 s | 4.4 s |
| validate_app_polish1 | 752 | 27.4 s | inputs unchanged |
| validate_app_polish2 | 1,028 | 4.3 s | inputs unchanged |
| validate_app_polish7 | 5,120 | 2.3 s | inputs unchanged |
| validate_render_effects16 | 424 | 4.4 s | 4.1 s |
| validate_items_ui | 8,517 | 16.5 s | 24.7 s |

Steward validators: validate_gfx3,validate_map_polish,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_app_polish1,validate_app_polish2,validate_app_polish7,validate_render_effects16,validate_items_ui

The post-merge selector pruned the other five rows. The registry append conflict
kept all three new registrations; this branch adds only its own 14 lines relative
to main. The portable run includes the manifest/policy checks.

## Captures and default identity

Native window framebuffer only, Preview demo, fixed-clock frame 30, 1280x800 GL.
Inputs: APP-REFRESH-006 Native Data, canonical fixed-clock GFx library,
`--gfx-open inventory,equipment-demo`, sword `0:68:9:1`, shield `6:0:7`, wing `12:1`.
Frame 20 sends the fixture hover at `(1005,240)` or `(1057,313)`. The real clock
probe and four-start tests passed with no legacy-clock skips.

Local review inputs, left before / right after:

- `~/Documents/MTM/mu-mac-tools/native/renders/items-ui-001/sword-comparison.png`:
  the new tooltip covers the equipment ring icon where they overlap.
- `~/Documents/MTM/mu-mac-tools/native/renders/items-ui-001/ring-comparison.png`:
  the Ring of Ice tooltip now appears.
- `comparison.html` in the same folder presents both PNGs.

Sword: 19,429 changed pixels. Ring: 12,760. Both have **zero changed pixels outside**
the inventory/popup region `(900,100)..(1280,650)`. Nine equipment records draw
with zero missing models. These are native comparisons, not original-client images.

Both binaries were rebuilt with `make -C native world` before the sweep:

| Binary | SHA-256 |
|---|---|
| Before, main `d4af71dd`, saved before edits | `4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c` |
| Final after, lane with main `6b75fbda` | `7184d004b0f5d9eef3f93e6dc0155d2e40f4209dab28a6d257b03d27c5ccb6e0` |

Default draw only, no draw_all/live_time: October 22's 14 views and DATA-ACQ-002's
32 views. All 92 PNGs, 92 OBJECT/light dumps, 46 reports and 46 logs match byte for
byte. The same lane-local output paths were used on both sides, so no path
normalization was needed. Before renders were taken once. The first after pass
also matched all 276 files; only the after side was refreshed for the core-code
main merge. No installed app was used as a baseline.

## Limits, next and cleanup

- No original inventory pixel capture. Exact original main-game GFx/sprite/tooltip
  frame order remains behind the excluded opaque hook; no parity claim or guessed
  reorder. The captured per-window movie/item/overlay order is preserved.
- The host gates tooltip requests using its existing held/busy/picked-movie state;
  complete original GFx active-frame identity is not reconstructed here.
- Equipment supplies appearance fields, not complete ITEM option records. Tooltip
  HTML uses the existing fixture code/level callback. No additional stat formulas,
  real equipment replication, equipping or transactions were introduced.
- The `0x87` no-effect comparison is bounded to the recorded types/kinds/quality,
  clocks and ordinary nonnegative level words. It excludes the `-1` sentinel.

Next: steward combined gate and merge, then an APP-REFRESH lane can install the
change. This lane never replaces the installed Native Preview or Wine apps.

Checkpoint commits `57ad1819`, `bb492408`, `5943dbeb`, `537572ef` saved the WIP and
measured results. At PR-ready, delete this lane's scratch/reports/builds and remove
its worktree/local branch. Keep only the two comparison PNGs and small HTML file
as named review inputs for the steward; no later implementation input is required.
