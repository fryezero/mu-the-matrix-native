# Current status

Updated 2026-10-16. The target is the exact installed Mu The Matrix client.
The later destination is native macOS gameplay. A playable source build does
not exist yet.

## Working components

- The startup decompressor is reconstructed in C. Four original compressed
  blocks match independent decoding, but the result is still protector code.
- The isolated QEMU x86 Linux/Wine guest restores a repeatable 23,572,480-byte
  code section. The selected second image section is also captured twice with
  matching digests. No Windows PC is required for this analysis route.
- Authored 64-byte copy/clear source matches captured instructions in 393/768
  synthetic cases. Controlled cofactor/inverse source matches 1,680/1,050 cases.
- The BMD filename call path reaches a version-dispatching model-read routine.
  Its v12 decoder now has authored C matching 4,048 synthetic cases and all 180
  installed v12 payloads, covering 3,176,971 encrypted bytes. Exact overlap and
  signed-length behavior are preserved. [Evidence](research/client-model-loader.md).
- The observed v15 key-setup target has authored C matching 1,320 synthetic
  instruction cases across 16/24/32-byte keys, alignments and no-op gates.
  [Key evidence](research/client-lea-key.md). The ECB decoder now matches 12,960
  actual-code guest cases and 1,152 scalar instruction cases. All 11,583 installed
  payloads match the independent reader, separately from original-code testing.
  [Decoder evidence](research/client-lea-decode.md).
- Images: 19,703 of 19,707 wrapper candidates decode. One remaining candidate is
  editable mesh text; three are inconsistent terrain images.
- Models: 12,663 of 12,754 unique BMD-extension files parse. Versions 10/12/14 pass
  all 701/180/216 files; v15 passes 11,566 of 11,583. Seventeen v15 inputs remain
  rejected and 74 other/table envelopes unsupported. Rejections have precise
  field diagnostics; original handling remains unknown.
- Selected bone/pose instructions show that dummy records leave output slots
  unwritten, while children compose from prior caller-buffer contents. Those
  contents are unknown. Raw call-search totals remain candidates.
- The hierarchy pose-composition source matches 5,176 controlled binary32
  instruction cases; 24 out-of-domain attempts are recorded separately.
  [Evidence](research/pose-concat.md). Actual prior pose state remains unknown.
- The rotation helper `0x00d00724` (ZYX Euler angles to x,y,z,w quaternion)
  has authored C matching 8,012 controlled cases bitwise. Its actual body and client
  SSE2 sine/cosine run with captured flag 1 and no stubs. The C substitutes host
  libm trig; binary32 trig results agree in all 48,072 calls, including
  host-midpoint candidates. [Evidence](research/client-rotation.md).
- All 370 effect JSON files parse and their 92 distinct texture references exist.

## Verification

The suite discovers 147 tests. Portable checks pass 134 and explicitly skip thirteen
private-input checks. In the rotation worktree, opt-in integration passes 142;
five installed-model checks need `MU_GAME_ROOT` model data and were not run there.
The previous full local integration passed all 141 earlier tests. A fresh
129-file source-only checkout passes 134 with thirteen explicit skips.

The v14 reader matches its pinned independent oracle on 216 installed files and
91 synthetic vectors. A complete model rescan preserves every one of 12,754
statuses and all 12,663 previously pinned parsed-input hashes. The exact-client
v12 comparison runs actual captured leaf instructions without helper stubs.
Its deliberately wrong feedback order fails 312 overlap cases.

Detailed identities, counts and CI references are in `evidence-index.json`.
Original-file scan manifests and binary evidence remain ignored local inputs;
CI runs authored fixtures and reports the private skips explicitly.

## Runtime boundary

The original client works on Windows. Earlier isolated CrossOver `win10_64`
starts fail with a Rosetta selector error. A new `win10`/win32 compatibility path
uses .NET 4.8, builtin WIC/GDI+, WPF software rendering and the default IGCN skin
in a cloned installation. The authored setup and local validation are recorded
in [the CrossOver finding](research/mac-crossover-32bit.md), issue #39.
The fresh test bottle passed all eight synthetic image-pipeline steps, kept
the launcher alive for 65.8 seconds, and was deleted after validation.
GAME START awaits the owner's interactive test; no login or gameplay has been
demonstrated. No Windows PC is currently available. The separate Mac-only Linux
guest still has outbound networking blocked and reaches an unresolved localhost
connection. Native Windows capture/equivalence
remains unverified, although the optional Windows helper builds and its own
memory/hash smoke checks pass under Wine.

## Repository and next work

The private [repository](https://github.com/fryezero/mu-the-matrix-recovery)
contains reviewed authored source, synthetic fixtures and evidence summaries.
PRs #4, #6, #8, #10, #13, #14, #16, #18, #20, #23, #25, #26, #28, #30, #32, #34 and #36 are merged after macOS/Linux checks.
No game executable, asset pack or memory capture was uploaded.

The client-linked v12 milestone is merged through PR #23. Two selected v15
dispatch slots now resolve into restored client code. See
[the capture finding](research/model-dispatch.md). Next trace the original v14 helper or bounded model record-loading/matrix code.
Original types, hierarchy semantics, initialization dependencies, simulation,
networking, renderer/input/audio equivalence and a complete client build remain
unfinished. Read `handoff.md` for exact local artifact paths and entry addresses.

The fixed v15 dispatch scope is merged through PR #26 after macOS/Linux CI.
Hierarchy findings are merged through PR #25. Post-merge review corrections
are merged through PR #28 after both platform checks. Strict model acceptance is unchanged.

The v15 key context is merged through PR #30. The ECB source and guest comparator
are merged through PR #32 after macOS/Linux CI. The guest is shut down. Decoder equivalence does not
resolve the model loader's allocation, hierarchy or actual rendering behavior.

Pose arithmetic is merged through PR #34 after macOS/Linux CI. Next validate original rotation/model
record loading, keeping actual FP state and unknown prior output contents open.

Issue #35 adds a fixed four-byte rotation dispatch capture. Two reads match
value 1; early packed code is refused without a payload and every prior scope
repeats. [Finding](research/client-trig-state.md). Actual FP state and full
rotation/trigonometric equivalence remain open. Guest is shut down.

Issue #37 adds rotation source and an actual-instruction comparison with
8,012 matches, 2,816 alias/alignment and 256 FP-state variants. A wrong axis
order fails 7,547. [Finding](research/client-rotation.md). Client SSE2 trig
algorithms are not reconstructed. Out-of-domain angles, non-finite values and live
caller FP state remain open. No guest run was needed.
