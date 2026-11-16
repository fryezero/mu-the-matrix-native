# RENDER-ITEMS-002AB

Branch `claude/render-items-002ab`, started from RENDER-ITEMS-002AA (PR #404, `baec5c08`). Main `c49fa188`
(batch 121, which merged #404) is merged in at `9ac99348`. Claude Fable 5.2, no subagents. Offline/static only.
Research is [part 43](../research/client-render-items.md#part-43-level-guards-matrix-brackets-scalar-forms-gated-producers-and-low-level-callers-render-items-002ab);
every remaining body has a row in the [144-row ledger](../research/item-body-groups-002ab.tsv).

## WIP (stopped 2026-11-15 18:10 on the owner's order to finish; draft PR, no ready line)

### Done

Bodies **1,530 -> 1,590 of 1,674**: sixty admitted, **84 left**. The denominator is unchanged. Skins stay
17/17.

| Part 41 group | Size | Admitted | Left |
|---|---:|---:|---:|
| Producer/service programs | 50 | 5 | 45 |
| Scalar/colour programs | 24 | 15 | 9 |
| Variable draw counts | 18 | 18 | 0 |
| Helper callers | 17 | 9 | 8 |
| Stopped fixtures | 12 | 0 | 12 |
| Matrix-stack programs | 10 | 7 | 3 |
| Independent failures | 10 | 4 | 6 |
| Entry/helper state | 3 | 2 | 1 |
| Total | 144 | 60 | 84 |

| Admitted form | Bodies | Types |
|---|---:|---|
| Packed helper level word (`>= 9`) | 7 | `0x0b34..0x0b36`, `0x1103`, `0x130e`, `0x1523`, `0x1524` |
| Guarded, decoded level word (`>= 11`, recipe `level_split=3`) | 11 | `0x239a..0x239d`, `0x239f`, `0x23a0`, `0x23a2..0x23a4`, `0x23a6`, `0x23a7` |
| Bare glPushMatrix/glPopMatrix bracket | 9 | `0x0b05`, `0x0ef4`, `0x12fa`, `0x12fb`, `0x14f2`, `0x16f5`, `0x16f6`, `0x1711`, `0x24f1` |
| Scalar forms | 16 | `0x0b21`, `0x0b41`, `0x0b54`, `0x0f19`, `0x10f3`, `0x1101`, `0x132f`, `0x14f1`, `0x155b`, `0x1578`, `0x157a`, `0x1703`, `0x1735`, `0x1737`, `0x1738`, `0x1755` |
| Flag programs (recipe kind 11) | 3 | `0x231b`, `0x231c`, `0x24e3` |
| Level-gated pre-draw producers (effect op 51) | 5 | `0x0b2b..0x0b2e`, `0x0b32` |
| Low-level callers that draw two meshes | 9 | `0x27ef..0x27f2`, `0x286e`, `0x286f`, `0x2874`; with light and helper `0x2406`, `0x2477` |

### Verified

| Check | Result | Wall |
|---|---|---:|
| `validate_item_level_guards.py --mutations`, 18 bodies | 60,234 comparisons, 0 mismatches, 16 mutants caught | 332 s |
| `validate_item_brackets.py --mutations`, 28 bodies | 54,916 comparisons, 0 mismatches, 11 mutants caught | about 270 s |
| `validate_item_gated_programs.py --mutations`, 5 producers | 5,384 comparisons, 0 mismatches, 10 mutants caught; every gate is the single threshold 9 | 39 s |
| `validate_item_mesh_callers.py --mutations`, 9 callers | 22,698 comparisons, 0 mismatches, 15 mutants caught | 151 s |
| Official pinned extraction on the merged tree (`gen_item_bodies.py --output`) | 1,562 rows, 493,428 bytes, byte-identical to the committed header; SHA-256 `92e8632c1aba1db1cfdeccdc3e0b3beca870982d26cbb1c582e908934b019cb7` | 2,246.4 s |
| Header format (no trailing zero values, no unsigned suffix) | same compiled library for the 1,511 rows of #404, SHA-256 `e8f2ea6b2ffce2b1fd64d51f728cb9db6cd2ac6e6c768bd1c76ca100e0537cb7` both ways; 500,314 -> 446,045 bytes | - |
| C-to-C against main `c49fa188` | 216,448 states: 208,768 identical, 7,680 admissions on exactly sixty types, no other difference | 13.2 s |
| Classifier (`classify_item_bodies.py`) | 1,691 types / 798 shapes; exactly sixty memberships change; complete shapes 689 -> 741; raw shapes unchanged | 82.7 s |
| Default identity sweep, rebuilt `mu-world` on both sides | 46 saved views, 276 files per side (92 PNG, 92 dumps, 46 reports, 46 logs) identical; no saved view changes | 122.8 s / 119.9 s |
| Item proof renders, 22 states per side | draw passes rise from 60 to 120..720; 20 raw PNGs change; `0x0b2c` and `0x0b32` create 780 and 600 bone sprites, none refused | 74.9 s |
| Four new unittest modules, portable part | 13 tests pass, 4 integration tests skipped | 0.1 s |
| Root build after the merge | pass | 23.6 s |

`mu-world` SHA-256: main sources `acc4754f7a9b251091997650bf77cf2ec840657c0199445cdd869c6be673d02b`, branch
`c575aea9e2e03e1c1f297eba1bba4b80915488cc780a786dd3727fa9d37b7792` (640 x 400, 25 frames sampled 0/24,
`draw_all=false`, `live_time=false`). The four validator runs above used the lane's own cache and ran before
the merge of main; the merge changed no file under `reconstructed/renderchar` and none the generators import.

### Not verified (stopped)

- The affected private validator run (`run_validators.py --private --no-mutants --cache --affected
  origin/main --jobs 2`) was started at `cba75204` and stopped before any row finished. The selection is
  84 of 263 rows (one symbol fallback, `validate_movement`; nine pruned).
- The affected portable tests, the reduced private `native/tests` modules (8d) and
  `scripts/audit_repository.py` were not run.
- The four new rows in `scripts/validators.toml` carry the counts of the lane runs above; they were not
  run through `run_validators.py`.
- Status lines in `docs/status.md`, `docs/handoff.md`, `docs/roadmap.md` and the plan row are not written.

### Left, by group

| Group | Left | Reason |
|---|---:|---|
| Producer/service programs | 45 | Four have no pre-draw block at any level, four run services before and after the draws, six write the model light in the case, four select bones from random tables, three wings re-transform the model (`0x00966ea5`), the rest stop at one unread instruction or helper each |
| Stopped fixtures | 12 | Five read the model's texture-name table (`+0x34`), two an action record's play speed (`+0x30`), five stop inside producer state |
| Scalar/colour programs | 9 | `0x0b38`/`0x0b39` name gate and random vector; `0x0b3b`, `0x0f08`, `0x12e9`, `0x1d1b` unread programs; `0x1106` reversed frame in a later block; `0x16f9` OBJECT field write; `0x2009` armour overlay light |
| Helper callers | 8 | Own RenderObjDraw cases with level-dependent draws (`0x23f4`, `0x249b`, `0x24f5`, `0x2505`, `0x2701`, `0x2875`), `0x10ef` (57 of 292 states differ with its early draw read), `0x130b` (own clock scroll) |
| Independent failures | 6 | `0x1710`, `0x10fd` stay excluded; four armour overlays keep the light argument in their ancient tail |
| Matrix-stack, entry state | 4 | `0x0afc` later-phase light; `0x24ed`/`0x26ed` base draw chosen by OBJECT `+0x68`; `0x0ef0` OBJECT field writes |

The ledger names the reason and address for each of the 84.

### Next step

1. From the repository root, at this branch's head: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`,
   `nice -n 10 make -j4`, then the affected validator run above with `--report`. The shared cache already
   holds the generator's samples for this tree (key `a83ae449290e71e4bfab3885`), so the drift checks reuse them.
2. Mutants once for the four new rows: `--only
   validate_item_level_guards,validate_item_brackets,validate_item_gated_programs,validate_item_mesh_callers`.
3. `run_test_suites.py --affected origin/main` without `native/tests/test_native_app.py`, the reduced private
   `native/tests` modules, `scripts/audit_repository.py`.
4. Status lines, the Steward validators table with wall times, PR body, ready line.

The lane's scratch tools (header assembler, trial fitter, ledger writer, identity and proof helpers) are
deleted; the ledger and the header are committed, and the checks above can be repeated with the committed
validators. No particle, joint or effect consumer, actor file or hero adapter is changed. No original-client
process, network, protection, character-power feature, installed app or Native Data refresh is involved.
