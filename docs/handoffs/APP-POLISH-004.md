# APP-POLISH-004

Claude Opus 5.5. Branch `claude/app-polish-004` from main `7d7d694b`, merged up to `eb2a8e76` (#304, #305, #306).
PR-ready for the merge steward. No full gate, installation, original-client run or live read. The installed
Native Preview and the Wine apps were not touched.

## Player-facing result

- **Window title.** The preview window reads "Mu The Matrix Native Preview — OFFLINE PREVIEW (no server
  connection)", with no "scene 6 world 25.0 fps" suffix. `mu-client` without `--title` shows the original's
  window name `MU`. The scene/frame-rate suffix is a diagnostic behind `--title-stats` or `MU_TITLE_STATS=1`.
- **Inventory icons use the original's render info.** RenderItem3D reads ItemTRSData `0x06fbb624`, a Lang.mpr
  table. Native read `Data/Local/itemtrsdata.bmd` × 200 instead. That file lacks 2,667 of the map's 4,919 codes,
  wing 0x19ab among them, which therefore got the default record. Wing 0x19ab (model 0x2491) now draws at
  scale 0.44 (was 0.55), offset y 0.44 (was 0.5) and rotation (270, 0, 2): 20% smaller and higher in its cells.
  Weapons absent from the file (e.g. 55, 2612) were drawn edge-on at the default -90°; they now get their
  rotations. 4,333 codes draw larger, 2,083 of them by exactly 1.1 ×; 449 draw smaller.
- **The wing still overlaps the left edge of the grid in column 0.** The original does the same: there is no
  scissor or bounds fit in its item path (below). This is not changed further.
- This reaches the player only after a refresh adds `itemtrs.tsv` to Native Data `lang/` (see "Next app
  refresh"). Until then the app keeps the old stand-in, and nothing changes in the installed preview.

## Causes and evidence

Full addresses in [client-app-polish4](../research/client-app-polish4.md).

- Title: the original creates its window with `L"MU"` (`0x01ac7a88`, built at `0x012114e0`; `_BATTLE_CORE`
  `0x01ac7a90` appended at `0x0121150c` for that mode) as class and window name (`CreateWindowExW`
  `0x01211646`/`0x01211686`). Its only `SetWindowTextW`, `0x010aef4b`, adds `" onStreaming"`. The fps suffix came
  from `native/client/main.c` (NATIVE-PERF-001).
- Render info: RenderItem3D `0x016c154e` → find `0x011204db` on `0x06fbb624+0x38` → node `+0x14`, or the
  default record `0x06fbaa40` (initializer `0x008dcce0`: 0.5, 0.5, (-90, 0, 0), 0.55). Fields read at
  `0x016c162d..0x016c1671`.
- Fit: scale = record × InventoryFrame `+0x58`. RenderObjectScreen passes it to the body scale unchanged; no
  bounds measurement. The item pass `0x00abfcca` uses `glViewport(0, 0, W, H)` (`0x00abfe0f`). The only
  `glScissor` (`0x006124a7`) is in the GFx renderer's viewport method `0x00612340`. The direct-call closure of
  the item pass, wrapper, RenderItem3D and RenderObjectScreen (5,761 functions) holds no scissor, stencil or
  clip-plane site.

## Changes

- `scripts/live_lang_to_plain.py`: `itemtrs.tsv` (code + six signed binary32 words) from ItemTRSData.
- `native/core/mu_lang.c/.h`: `mu_lang_item_trs`. The internal row loader takes up to six values per key.
- `native/core/mu_hud.c/.h`: `mu_hud_item_trs` (map record / default record / old bmd stand-in without the table).
  `mu_hud_inventory_pass_at` takes the lang handle. `native/world/world_gfx_game.c` (the GFx item pass) and
  `native/tools/mu_render_hud.c` (`mu-render ui inventory`; `render_info` now reports `itemtrs`) call the resolver.
  No renderchar body, executor, generator or effect code changed.
- `native/client/main.c`: `MU_WINDOW_TITLE "MU"`, `window_title()`, `--title-stats` / `MU_TITLE_STATS=1`.
- `scripts/guarded_run.py`: runs a program under the network guard at lower priority without `/usr/bin/nice`
  (which drops `DYLD_*` under SIP). The documented command is in the finding, section 5.
- Tests: `native/tests/test_app_polish4.py` (new). `test_native_app` adds a guard-under-nice test.
  `test_native_item_textures`, `test_native_hud` and `test_inventory_skin` now import from the repository root
  too (`python -m unittest native.tests.<module>`).
- `scripts/validate_app_polish4.py` + validator row `validate_app_polish4`.
- `scripts/audit_repository.py` (orchestrator request): `violations()` rejects lines starting `<<<<<<< `,
  `=======` alone, or `>>>>>>> ` in any audited file (`CONFLICT_MARKER_EXEMPT` is the explicit, empty exception
  list). The audit and the gate therefore fail on #303-style markers. `tests/test_repository_policy.py` plants
  each kind (caught, line 4) and lookalikes (not caught), and scans every tracked text file. On main `6ef9059e`'s
  `docs/handoff.md` it reports `merge conflict marker (line 5)`; current main is clean.

## Checks

All heavy commands ran with `nice -n 10`, `make -j4`, validator runner `--jobs 2`. Env:
`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT=…/MuTheMatrix/prefix/drive_c/MuTheMatrix`,
`MU_SECTION3=…/x86-linux-capture-04/main-01ced000.bin`, `MU_SNAPSHOT_DIR=~/Documents/MTM/mu-mac-tools/native/scratch`
(lang3), `MU_EVIDENCE_DIR=<main checkout>/evidence`.

| Check | Result | Wall time |
|---|---|---|
| `make -j4` (after the mu_hud change) | pass | 13.5 s |
| `validate_app_polish4` full, no mutants | trs_lookup 5,276, render_item3d 5,207, window_name 2; 0 mismatches | 30.3 s |
| `validate_app_polish4 --mutants` (once, at the end) | 10,485 cases, 0 mismatches; 8/8 mutants caught, 0 equivalent | 34.5 s |
| `test_app_polish4` (private) | 4 tests OK | 32 s |
| `test_native_app` | 19 tests OK | 64 s |
| `test_native_item_textures` (root and `native/tests`) | 7 tests OK | 51 s |
| `test_native_hud`, `test_inventory_skin` (root and `native/tests`) | 6 + 4 tests OK | 1 s + 5 s |
| `test_native_lang`, `test_native_fidelity`, `test_native_gfx3` (6b: mu_lang/mu_hud users) | 15 (2 skipped), 12 (1 skipped), 12 (5 skipped) OK | 5 s, 11 s, 6 s |
| Existing validators compiling mu_lang.c/mu_hud.c or importing the converter, `--no-mutants --cache` | 28 pass, 0 fail (5 social2 helper rows skip by design: run inside `validate_social2`); started at `610b97fd`, #306's mu_combat.c merged mid-run (no check input) | 18 min 13 s |
| Byte identity, 32 DATA-ACQ-002 tours, default draw, `MU_LANG_DIR` with `itemtrs.tsv`, main `6ef9059e` vs branch | 128/128 PNG, 64/64 OBJECT/light dumps, 32/32 logs and 33 JSON identical; 32/32 `native.jsonl` identical after normalising the output folder name | 57 s + 67 s |
| `audit_repository.py` (with the new marker rule) | 1,935 files, 0 rejected | 30 s |
| `tests.test_repository_policy` | 9 tests OK | 0.6 s |

`--list-affected origin/main` selects all 184 rows, because a scripts/ helper used only by tests
(`guarded_run.py`) counts as an unmapped input. Without that file it selects 92 rows. 58 of those match only on
the path words "native"/"client"/"world". The rows run above are the 33 that compile `mu_lang.c`/`mu_hud.c`
(directly, through `validate_lang`'s module, or through `libmunative.a`) or import `live_lang_to_plain.py`.
`run_test_suites --list-affected` selects 135 of 165 items through `libmunative.a`. Per the brief, no full gate
was run; the modules above were.

## Before/after (window-only, own builds)

Local review images (deleted at cleanup, not committed) under `~/Documents/MTM/mu-mac-tools/native/renders/app-polish-004/`:

- `title-before-after.png` (SHA-256 `85a031924c8eb7e1…`): main `6ef9059e` with the app title ("… scene 6 world
  24.8 fps"), this branch with the app title, this branch without `--title` (`MU`). Captured from the
  `mu-client` windows by process id, at Lorencia after `--hold 6`.
- `wing-before-after.png` (`2e5ad14ad1d697dd…`): `mu-render ui inventory`, items 6571, 55, 2612, time 123456,
  1722 × 1048, the same `MU_LANG_DIR` (canonical lang + `itemtrs.tsv`). Main uses the bmd/default record (left);
  this branch uses ItemTRSData (right).

## Next app refresh

- Regenerate Native Data `lang/` with this converter so it gains `itemtrs.tsv`:
  `scripts/live_lang_to_plain.py --out <dir> scratch/lang/live/lang3.bin` (or lang4; same 4,919 records). The
  canonical export set (`scratch/native-data/export`, NATIVE-DATA-MANIFEST-001) needs the file too, plus a new
  manifest. Without it the app keeps the old stand-in and the icons do not change.
- Expect most inventory icons ~10% larger and absent-from-bmd weapons rotated. The window title loses the fps
  suffix.
- Headless helpers that lower priority should use `scripts/guarded_run.py` instead of `/usr/bin/nice` in front of
  `DYLD_INSERT_LIBRARIES`.

## Limits

- No live original-client inventory capture: the fit is matched up to RenderObjectScreen's arguments, not pixels.
- Battle-core and streaming title variants are not ported. Special-cased RenderItem3D codes keep their existing
  paths. The static no-clip reading does not follow indirect calls.
- The steward's `--affected` selection over-selects for `guarded_run.py` (above); the steward rows are listed below.

## Cleanup

Deleted: the tour renders (1.6 GB), the main-build worktree and run folders under
`scratch/app-polish-004`, this worktree's `native/build`. Kept until the steward merges: this worktree and the
remote branch.
