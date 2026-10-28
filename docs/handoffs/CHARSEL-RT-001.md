# CHARSEL-RT-001: character-select runtime

Implemented on `codex/charsel-rt-001` from `a9128ef`, following WORLD-RT-001. All work and builds used
`~/Documents/MTM/worktrees/charsel-rt-001`. No original client, launcher, live session or installed game root
was used.

## Runtime and ownership

- `native/charsel/mu_charsel_rt.h`: opaque `mu_charsel_rt`, the one `mu_charsel_rt_options` struct and defaults,
  open/close, session access, selection, resize and software/GL rendering. The front end owns the GL context
  and tears down GL resources before closing it.
- `charsel_rt.c`: asset lifetime, error unwind and dispatch through `parts.def`.
- `charsel_part.h` and `charsel_rt_internal.h`: part hooks, draw context and runtime state. GL caches are
  grouped by their owning pass; terrain's batch is shared with the first objects pass.
- `parts.def`: nine rows, in the old draw order: scene assets, terrain, objects, character, effects,
  after-character objects, decals, billboards, optional standalone UI. Open follows row order, close reverses
  it so UI releases before its session. GL setup/teardown and both renderers dispatch the same list.
- `parts/*.c`: the existing loader, marker extraction, terrain, character-part/shadow ordering, object passes,
  effects, decals and billboards moved from the former `main.c`. The software raster filter state is saved
  after terrain, exactly as before. The former global software-backend pointer is now per runtime.
- `charsel_tool.c`: CLI, scripted selection/Enter, virtual clock, reports, PNGs, object-state export and SDL
  window. `main.c` is a six-line entry point. `mu-render charsel` links the tool directly.
- Deleted `charsel_embed.c/.h`; no textual C include, main-renaming or `MU_CHARSEL_TOOL_ONLY` remains.

The existing `core/mu_charsel` session still owns the tick, records, character and particle state. The shell
continues to own its own UI/GFx windows. There is no session-account migration or behavior redesign here.
The runtime closes its loaded object assets for standalone tools too, rather than leaving them to process exit.

Minimal shared edits:
- `native/client/{shell.c,shell.h,main.c}`: replace embed types/calls with the runtime. `open_charsel` uses its
  defaults and sets `no_ui` because the shell already owns that layer. The four `main.c` call renames are
  character-select callbacks only; world callbacks and input were left alone.
- `native/Makefile`: charsel runtime sources/headers and software objects, separate tool entry, front-end
  links. Client/shell object names now include their source path to prevent charsel/world `terrain.c`,
  `objects.c`, etc. from overwriting each other. Old flat objects are removed on each relink.
- `reconstructed/charsel/test_charcreate.py`: 60 to 300 cases. The test and `test_charsel_gfx.py` no longer
  reference validators' removed `EVIDENCE` attributes. Validators resolve and verify pins themselves and fail
  explicitly when requested private inputs are absent.
- Only `validate_charcreate` in `scripts/validators.toml` changed: 300 cases per family, 4,368 total, six mutants.
  No reconstructed routine or input pin changed.

## Verification

Baseline and new binaries were built on this Mac. Baseline gate passed before edits. Baseline binaries and
source are retained under the scratch directory below.

- Private `reconstructed/charsel` suite: 28 tests pass, including all four Unicorn comparisons.
- Character-create: 4,368 cases, zero mismatches, 6/6 planted mistakes detected. The 300-case run gives the
  name mutant 60 trials including CP949 lead bytes. Measured at 50.4 seconds with concurrent checks.
- Character select: 360 cases across six families, zero mismatches, 12/12 mutants.
- Legacy charsel window: 20 cases, zero mismatches, 7/7 mutants.
- GFx charsel: 420 cases across seven families, zero mismatches, 5/5 mutants.
- Charsel-world object handler: 1,200 cases across six families, all equal, no stopped cases.
- Total original-instruction comparisons: 6,368, zero mismatches; 30/30 planted mistakes in the four
  families that have mutation runs. World-handler run uses its existing comparison without mutants.
- Differential existing tests (`test_native_charsel`, `test_native_shell`, `test_native_objects`,
  `test_native_lang`): 61 tests pass, eight private-input skips; 62 baseline/new tool invocations and 164
  generated files byte-identical. Comparison includes exit codes, stdout, stderr, PNGs, object-state exports,
  character stores and GFx logs. Append logs and stores are restored between baseline/new invocations.
- The same 61-test differential suite replayed with mu-shell journeys through mu-client GL also passes:
  62 byte-identical invocations and 164 files.
- `verify-mu-native` scene-flow recipes: all five headless drives through mu-client GL, mu-client software and
  mu-shell, plus cycling/Enter through mu-charsel, mu-charsel-window in GL/software, and mu-render charsel.
  19 drives, 320 PNGs; exit codes, stdout, stderr and PNG bytes unchanged. Selected character-select PNG
  inspected in the real output. The synthetic textures and incomplete body assets look the same as baseline.
- Local macOS gate: `bash scripts/local-macos-ci.sh tools/python/bin/python` passed, 38 suites / 1,283 tests,
  154 explicit skips, native suite 535 tests / 76 skips; viewer and read-only reader builds, repository audit
  passed. Reader binaries were built, never run against the client.

## Local artifacts

Never committed:
- `~/Documents/MTM/mu-mac-tools/native/scratch/charsel-rt-001/`: `baseline/bin/`, baseline gate/source,
  final gate logs, validator reports, `charcreate.json`, `charsel-world.json`, recipe manifests, differential
  logs/manifests and the reproduction scripts.
- `~/Documents/MTM/mu-mac-tools/native/renders/charsel-rt-001/`: retained verify-mu-native proof and `run.json`.

## Limits and next step

Parts describe the existing host order, not a new reconstruction of the scene manager's call graph.
The UI/GFx adapters and demo session behavior remain in their existing files. CLI script state stays in the
tool; session-account lists, create/delete intents and live sessions remain SESSION-ACCOUNT-001 and its
prerequisites. No new installed-data render or real Ruffle-movie visual comparison was attempted; synthetic
GFx tests use the repository's stub. No live proof is claimed. Other lanes and unrelated private failures
recorded in the main handoff remain outside this milestone.
