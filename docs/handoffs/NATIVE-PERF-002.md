# NATIVE-PERF-002

PR [#182](https://github.com/fryezero/mu-the-matrix-native/pull/182) adds ordered player batching,
direct float-corner delivery, bounded scratch storage and an offline stress/measurement command.
**The 25 fps goal remains open in all four measured scenarios.** The full before/after table, CPU/GL
measurement boundaries, unfavorable results and exact reproduction command are in
[the finding](../research/native-performance-stress.md).

## Scope and result

Owned worktree and branch only. No live client, launcher, wire/protection work or captured stat changes.
All 40/80 players have equipment and nameplates. Each authored scenario starts with 32 wandering
monsters, repeated area skills, particles/joints, real Ruffle windows and a map. Missing workload,
models/textures, particle drops or overflow reject a timing run. No quality reduction was introduced.
`--perf-fov 65` is an offline wide-camera override, not complete interactive camera unlocking.

Final timing source `4d556f3` includes main `128679f`, the item expansion, Icarus C2 and monster/session
migration. Before/after fps are 10.40/12.05, 7.08/6.38, 4.61/6.76 and 5.02/6.99. Runs share this Mac
with validation work. They do not prove a causal speedup. The Lorencia 80-player pair regresses overall.
GFx mean time exceeds the whole 40 ms budget in three scenes. Ruffle/Metal GPU execution is unmeasured;
the asynchronous world-GL interval overlaps CPU submission. Do not add those columns as a GPU split.

`--check` fails the strict 25 Hz target in all four scenes. `--check-regression` passes three measured
after runs and fails Tormenta's earlier warning envelope. The failure is recorded; limits were not widened.
Completed sampling profiles predate the final main integration. Two integrated repeat sampling attempts
produced no usable report, so an updated profile remains open.

`mu-world`, `mu-client` and the Preview bundle share the optimized core/runtime. The extreme matrix
measures `mu-world`; separate extreme autoplay/Preview performance is not established. The final bundle
was rebuilt with real ABI-3 Ruffle, passed `--check-bundle` and deep signature verification, and was not
installed over the owner's app.

Minimal integration repairs include the absent-player batch boundary, the full crowd name capacity,
long text-valued script options in the Native Data guard, and an incremental character-select header
dependency. Existing owner Native Data was not changed. Tests use a fresh scratch clone with its own
build-pinned manifest. The renderchar metadata now accounts for all 500 item requests, 106 existing
record-type exclusions and 394 equal comparisons, plus other sections, 625 total. No mismatch was waived.

## Checks

- Final `bash scripts/local-macos-ci.sh`: 1,417 tests in 38 discovery runs, 171 explicit skips, six fixture
  scenarios, viewer and reader builds; publication audit 1,282 files, zero rejected.
- Registry sweep plus incremental merged-source reruns: 86 passing root validator rows, 1,665,962 counted
  cases, zero failures/errors. All nine affected final-source reruns pass. The four newly merged families
  catch 26/26 mutants. Existing mesh-draw validation has 14,619 cases and four caught negative controls.
- Five root families have unavailable original inputs: client LEA decode, model codec, effect tree,
  effects and objects. The missing pins are the verified-v14 manifest, edge diagnostics and capture-04
  section. These are explicit skips, not passing comparisons. Sixteen social helper rows are covered
  through their owning validator. All 107 registry rows are accounted for.
- The authored direct-corner host matches all 247 pinned stream/table cases and catches both mutants.
  Seven stress tests are included in the Mac gate. Nine private PERF-001 checks also pass after integration.
- Twelve private before/after PNG pairs match by full file SHA-256 at frames 0/60/120 across all four
  scenarios on the integrated source. GFx is disabled in both pixel runs because identical Ruffle runs
  already have timing-dependent differences. Actual timing uses full Ruffle; its UI was visually checked
  on the earlier optimized snapshot. No optimization difference is intended in any frame.

## Local artifacts

Private files stay outside git under `~/Documents/MTM/mu-mac-tools/native/`:

- `scratch/native-perf-002/integrated-{before,after}-*/`: final commands, binary hashes, workload logs,
  CPU/phase/GPU TSV and reports; `integrated-results.json`, `integrated-table.md`, `stress-comparison.html`.
- `scratch/native-perf-002/validators*/`, `validator-combined-integrated.json`, `gate-final-integrated.log`,
  `private-perf-integrated.log`; completed earlier profiles `profile-final.txt` and baseline sample reports.
- `renders/native-perf-002/integrated-render-hashes/`: twelve final byte-identical frame pairs.
- `scratch/native-perf-002/release/`: rebuilt `mu-world`, `mu-client`, and ad-hoc signed
  `Mu The Matrix Native Preview.app`. Owner signing/install state was left alone.

## Next

Keep issue #176 open for the 25 fps shortfall. Repeat the matrix on an idle Mac, obtain a current sampling
profile and complete the Ruffle/Metal GPU split. Investigate validated pose/skin caching, AVM1/movie work,
remaining scene allocations and corner submission. Broaden worlds, movement/skill mixes and real free-camera
coverage. Safe cache keys must preserve shared-buffer side effects, attachments, light, alpha and roots.
The demo is not a live crowded-server trace. Separate extreme `mu-client`/Preview timing and the five
missing-input validator families remain unverified. Cleanup follows the common brief after the authorized
PR merge; the private reports and release bundle remain outside the removed worktree.
