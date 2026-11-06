# APP-POLISH-001

Codex GPT-6-Astra, xhigh. Based on main `90e11d71`, PR #291. PR-ready only; the merge steward owns the full gate.
No app installation, original-client session, prefix change, service access or character-stat change.

## Player-facing result

- The Hound's authored offline placement moves from 185,131 to 205,131, with the same four-tile wander radius.
  The field arrival used by the refresh journeys is 179,131. Combat rules, damage, hero stats and the other
  actors are unchanged. This reduces nearby monster placement; it is not a safe zone or an immunity rule.
- The old HP-drop attribution is unproven: `mu_gfx_layer.c::demo_step` independently animates displayed HP as
  `max_hp * (0.55 + 0.45 * sin(t * 0.9))`. `world_gfx_open` enables that demo animation. The window captures
  show it continuing in Noria/Devias, after the Lorencia actors are gone. Moving the Hound does **not** fix this
  display behavior. Binding HUD vitality to session/combat state remains open; no hero stats were changed.
- `MU_NATIVE_EXTRA_ARGS` accepts single/double quotes, escaped spaces, empty arguments, adjacent quoted words
  and line continuations. It does not execute a shell or expand variables, globs or commands. Unfinished quoting
  fails before launch, with a diagnostic in CLI mode or the launch-error UI.
- `test_native_data_manifest` works both as a package from the root and from `native/tests`.
- Shadow opacity and Warps scaling stay unchanged. The original instructions support those native choices.
  The complete main HUD movie/Scaleform scaling path is still open; this lane does not claim to have verified it.

## Original evidence

See [client-app-polish.md](../research/client-app-polish.md) for addresses, compared boundaries and exclusions.
The new `validate_app_polish1` compares the native character-shadow policy, GL state, projected mesh vertices,
Warps invokes and the original viewport arguments. Portable tests compile the production shadow function and
exercise the native GFx host. Private comparisons use pinned text/data and the supplied third-section pin.

The shadow policy is compiled verbatim from `mu_particles.c`, with `shadow_with` as a recording boundary.
This avoids duplicating its world rules in a new implementation. Projection reuses the existing particle oracle.
No production C, renderer, item executor, renderchar or effect code changed.

## Journey proofs and screenshots

Runs use this branch's app launch plan and bundled client with the real local Ruffle library, the read-only
APP-REFRESH-004 Native Data, isolated support/log/option directories, `--no-store` and no audio. The installed
Preview and Wine play app are untouched. The session's slot 1 starts at Lorencia 179,131 as in APP-REFRESH-004.

Headless travel at both 1280x800 and 1504x936 reaches Lorencia -> Noria -> Devias. The existing stage-point
row positions remain x 122, Noria y 257, Devias y 324. This display currently has a 2x drawable: direct scripted
window mouse messages require x 244 and y 514/648. Normal SDL mouse events already apply that conversion.
An initial window harness run omitted it and clicked the terrain; it is not counted as a travel proof.

Window PNGs are framebuffer-only captures, not desktop screenshots. They are written under
`~/Documents/MTM/mu-mac-tools/native/renders/app-polish-001/`:
`before-lorencia.png`, `before-devias.png`, `after-lorencia.png`, `after-noria-warps.png`, `after-devias.png`.
Images were downscaled from the 3008x1872 Retina framebuffer to 1504x936. Before uses main's unchanged renderer and placement; after uses the new placement. No shadow/HUD render change
is expected. The cleanup below applies to these temporary review images.

## Checks

All heavy commands used `nice -n 10`, builds at most `-j4`, validator runner `--jobs 2`. Resource readings
stayed below load 14 and above 25% free memory. No full gate was run.

| Check | Result | Wall time |
|---|---|---|
| Main baseline native `all world` build | pass | 17.70 s |
| Branch app build with real Ruffle | pass | 16.20 s |
| Final root `make -j4` | pass | 12.87 s |
| App, manifest and new polish unittest modules | 37 tests, 0 failures, 0 skips, private enabled | 66.40 s |
| Placement consumers: world2, combat, items, names, npc, perf, players, quest | 88 tests, 84 pass, 4 optional GFx/quest environment skips | 90.02 s |
| New private `validate_app_polish1` through registry | 752 cases, 0 mismatches; 8/8 mutants caught, none equivalent | 17.69 s |
| Root package registry tests and test-directory manifest invocation | 17/17 registry; 15/15 manifest from test directory | 0.69 / 7.00 s |
| Headless arrival, main placement / new placement | both reach Lorencia, 520 frames each | 20.37 / 15.03 s |
| Headless travel at 1280x800 / 1504x936 | both 0 -> 3 -> 2, unchanged stage row points | 15.65 / 15.78 s |
| Corrected window travel, before / after | both 0 -> 3 -> 2, five inspected PNGs | 28.20 / 28.12 s |
| Initial window harness attempt | invalid travel coordinates at Retina scale; corrected above | 52.97 s |
| 32 DATA-ACQ-002 default-draw tours | 32/32 maps, 128/128 PNG/binary artifacts byte-identical; no frame changes | baseline 53.64 s, final 53.25 s |
| Staged repository audit | 1856 staged files, 0 rejected | 15.34 s; initial home-path rejection 15.66 s |

Private comparison breakdown: shadow caller policy 300; shadow state 32; shadow projection 300; Warps size
60; viewport words 60. Five mutants compile changed C policy slices. Three mutate observations: proportional
movie scaling, fixed 800x600 viewport and shadow height at the origin. The full-count/mutant run was performed
once; development and the private unittest used 20-case samples without mutants.

TEST BUDGET 6b: searched native/tests, reconstructed and tests for `LaunchPlan`, `ExtraArguments` and the changed
placement filename. Ran the app tests and all eight placement consumer modules named above. No shared C symbol,
structure or constant changed. Existing validator build lists that broadly name `native` do not compile the
changed Swift, test Python or placement text; no existing compiled validator source was touched. No existing
validator needed a rerun. The registry schema tests cover the new row.

Steward validators: validate_app_polish1

Steward mutants: none; the new row's eight were already caught once. Run without `--mutants`.
Environment: `MU_RECOVERY_INTEGRATION=1`,
`MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_GAME_ROOT=~/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix`.
Native Data: `~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-004/Native Data`, read-only.

Screenshot SHA-256 prefixes after downscaling: before Lorencia `3c5be791a3adc187`, before Devias
`90ab33d340a7717f`, after Lorencia `979232ccce98171f`, after Noria/Warps `c2c2136c1bf22ce1`, after Devias
`b577ba53549dfffa`. Window frames have different elapsed animation times; they are appearance checks, not
byte-identity comparisons or combat-HP measurements.

## Remaining scope and APP-REFRESH-005

- Verify the quieter field arrival, quoted input-script paths and the normal mouse-driven Warps journey after
  installing the merged app. Existing Native Data remains usable; no export/setup input changed.
- Do not make the Noria/Devias body shadow translucent on the basis of the old visual inference. The ordinary
  body caller uses opaque black. A live window-only original capture could still assess coverage, mesh hiding,
  overlap, culling and whole-frame appearance. None was taken here.
- Replace the animated demonstration vitals with the session/combat vitality view. The Hound placement change
  is not evidence that the reported 1,707 -> 614 display drop was combat damage.
- Recover the main HUD base movie's complete viewport/scale-mode initialization and ActionScript layout at
  1504x936. Warps creator/viewport evidence does not establish every main-HUD element's behavior.
- Special character states, item hidden-mesh rules, helper shadows and all of RenderPartObject are outside the
  new caller-policy comparison. RENDER-ITEMS-HIDDENMESH owns its item executor changes.

## Cleanup

After queueing, remove this lane's renders, scratch, build outputs, worktree and local branch. No new private
input is needed by later lanes. The canonical data, existing captures, Ruffle library and installed apps remain.
