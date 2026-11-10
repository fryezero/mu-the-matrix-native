# RENDER-EFFECTS-027

Death Stab's offline base-DK fixture trails. Branch `codex/render-effects-027`,
started at `ff8e0543`, with main through `807d757c` merged. The merge steward
owns integration and the full gate. Final affected checks are in progress.

## What draws

The selected skill-43 branch of attack-step helper `0x013966ea`, called by
MoveCharacter `0x013a9047` before AttackTime increments, now supplies the demo's
trail requests. Steps 2..8 make three `0x472/2` red ribbons. Steps 6..12 make
two `0x10e6/1` markers, each of which emits `Flare/12` blue curls. The saved
OBJECT `+0x104` point, step cutoff, scatter, widths, drift, recursive movement,
tail streams and retirement follow the compared instructions.

[Research and address tables](../research/client-render-effects-027.md),
[coverage inventory](../research/client-skill-visual-coverage.md).

The native adapter requires class byte exactly 1, a non-none demo weapon,
loaded Player model and posed, non-dummy bone 33. This bone is authored fixture
context. It does not recover the general CHARACTER link selector or infer real
equipment eligibility. Other classes, promoted `0x11` and missing weapon
context are refused and counted. No target CHARACTER state is written.

## Original evidence and lifetimes

The pinned capture09 text and run10 data identities are in the research note.
`validate_render_effects27.py` runs original caller instructions
`0x0139959c..0x01399c9d`, both joint constructors/movers/render streams, the
marker constructor/mover, and independent create-to-retirement joint sequences.
Model/bone/target lookups, TransformPosition and world predicate are declared
fixture services; sine/cosine use host libm. No original/live client was run.

- `0x472/2`: constructor `0x01548aeb`, mover `0x01569e07`, texture `0x7fde`
  from startup site `0x018228a5`; lifetime 20, five tails, 21 outer ticks.
- `0x10e6/1`: constructor `0x013c465a`, mover `0x014374f6`; lifetime 10,
  eleven child requests, no model draw in the original RenderEffects default.
- `Flare/12`: constructor `0x0154a9a2`, mover `0x01579558`, recursive common
  tail `0x015896fb`; lifetime 70, fifty tails, seven outer ticks.
- Caller comparisons check every one of the fourteen arguments, including both
  key words and fixed defaults. Wrapper `0x013c0ed8` maps effect argument 11
  into info word8; native preserves its `0xffff` value. The first stricter
  comparison caught the request records' omitted keys, which were corrected.
  Three added key mutants prove those fields are observed.

The original target-byte write at `0x01399c81` is excluded. Continuous joint
comparisons carry original record bytes between ticks independently of C,
including owner death, closing tails and retirement. Recorded ordered GL calls
are component evidence, not original GPU-image equivalence.

## Checks

All commands ran from the repository root, heavy jobs at nice 10, make at most
four jobs and validator runners at two jobs. Resource-limit pauses were
observed. No full gate ran in the lane. Private commands sourced
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`; all private inputs and
symlinks remain outside version control.

| Check | Result | Wall seconds |
|---|---|---:|
| Final focused original comparisons, code at `26eef91d` | 6,064 comparisons, zero mismatches; 23/23 compiled production-C mutants caught; no original-machine stops | 53.34 |
| Earlier caller iteration | 1,200 comparisons, zero mismatches | 3.67 |
| Complete-argument correction iteration | 1,264 comparisons, zero mismatches | 2.83 |
| First portable affected run, 157 work items | 1,718 tests, 1,433 passed, 284 skipped; one stale EFFECTS-016 bitmap-count failure, repaired below | 502.59 |
| Repaired EFFECTS-016 private module | 2 tests; 424 comparisons and 23 mutants, pass | 41.14 |
| First private changed modules | 18 tests, all passed | 24.41 |
| First affected private validators at `3447e585` | 49/49 rows passed, 711,353 reported cases, zero failures/errors/skips | 693.80 |
| After ITEMS-002X merge, reduced private native modules | 43/43 passed, zero skips | 40.05 |
| After ITEMS-002X merge, portable affected run at `6687e6a6` | 147 work items, 1,383 tests, 1,151 passed, 232 skipped, zero failures/errors | 500.44 |
| Final root build through AUDIO-002G, `ba699cfc` | pass | 10.59 |

The second portable runner reports 398.9 s after selection; the table records
the outer wall time. The initial focused mutant run was repeated because the
complete-argument comparator and production request words changed. The final
run above supersedes its 20-mutant result. EFFECTS-016 mutants were not repeated
after its checks stopped changing.

The native private selection exceeds 40 items, so **8d reduced** applies. The
changed combat, bitmap and renderer consumers are checked explicitly; the
portable skip count does not imply those private checks ran.

Final affected validator results, final portable/private checks and final audit
will be recorded before PR-ready.

## Render and identity evidence

Before measurements were taken once from main `ff8e0543`. The authored installed-
data GL scene uses `DemoKnight`, class 1, sword, tile 182,127, and only one
placement, `actor 3 184 127 0 label DemoTarget`. It runs skill 43 at tick 2,
stop at tick 3, for 28 frames, saving 0/9/18/27 at 960 by 600. Audio, other
items and other players are disabled. These are native fixture renders, not
screenshots of an original client.

| Counter | Before | After |
|---|---:|---:|
| Effect records created | 0 | 14 |
| Joint records created | 0 | 175 |
| Routed visual requests, sum of those two counters | 0 | 189 |
| Global unsupported requests | 0 | 0 |
| Cast requests sent / unsent | 0 / 1 | 0 / 1 |
| Hits / kills | 0 / 0 | 0 / 0 |
| Sound decisions | 0 | 1 |

The new Death Stab counters report 12 steps, 189 requests, zero refusals and
zero context refusals. The baseline predates these dedicated counters. One
cast contains 21 early ribbons, 14 markers and 154 marker-child curls. Portable
fixture tests verify constant target HP, texture-removal pixel differences,
class/weapon refusal controls, full retirement and repeated image identity.

The initial GL proof and repeat took 4.27 s. All four after/repeat images were
byte-identical; frame zero also matched baseline. Visual inspection showed the
long ribbons converging on the DK and the short curls near the skill point.
Final render and default-sweep results follow after late-main checks.

The default capture baseline has 46 entries, 92 PNGs and 92 OBJECT/light dumps.
Its first after sweep at `3447e585` was byte-identical for all 184 artifacts,
105.09 s. The final comparison reuses that same baseline; it does not rerun
before measurements. JSON reports are not part of the byte-identity claim.

## Limits and next

Death Stab stays L in the strict coverage inventory. General equipment link
selection, master/later-class aliases, unrestricted caller contexts, target
state, authoritative buffs, original GPU images and live play are outside
this result. The original caller's dummy/index pre-gate is statically audited;
missing-model and missing-transform answers are compared. Native admission
requires its whole authored context before any trail request.

Research-only follow-up covers Greater Defense 27 and Greater Damage 28. Both
take the step helper's default branch, not this emission branch. A future aura
lane needs the buff-presence consumer/IDs, attachment/removal calls, owner and
lifetime rules, authored expiry controls and original comparisons. No buff
state or aura implementation was added.

No protection analysis, network/login/packet work, memory writes, character-
stat features or original-client screenshots occurred. The owner's Wine apps
and installed Native Preview were untouched. Other lanes' item/world source
files were not edited; their main merges were retained.

## Steward validators

The exact selected names, row counts/timings and tested commits will be added
when the final affected run finishes. No steward mutant reruns are needed
unless the relevant checked inputs change.

## Cleanup

The lane's local reports, baseline binaries and rendered images are temporary
under `~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-027` and
`~/Documents/MTM/mu-mac-tools/native/renders/render-effects-027`. They, the lane
build directories and worktree will be removed after the final push and ready
line. No inputs need to be retained for another lane. Shared validator cache,
main checkout, private inputs and other lanes are preserved.
