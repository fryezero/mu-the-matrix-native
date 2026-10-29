# RENDER-ITEMS-002 part 14 (WIP, stopped on owner request)

Branch `claude/render-items-002n`, worktree `~/Documents/MTM/worktrees/render-items-002n` (Claude Opus 5.5).
The branch is based on `origin/claude/render-items-002m` (part 13, PR #275, not merged when this started;
its base is main `7f18bf05`). **No source change yet.** This commit holds only this handoff. Bodies stay
**1,162/1,674**. No PR and no `ready-prs.txt` line. No gate has been run on this branch.

## What was done: survey of the 469 remaining non-stopping types

These are probe and screen results only (verified by Unicorn runs against the pinned text/data). None is a
passing validation. Scratch scripts are in `~/Documents/MTM/mu-mac-tools/native/scratch/render-items-002n/`
(kept as resume inputs, about 1.7 MB):

- `common.py`: shared imports. `remaining()` lists the 469 types from `item-body-types.tsv`.
- `diag.py` → `diag.json`: first probe-stage reason per type (without scalar programs).
- `fits.py` → `fits.pkl`: `gen.fit(scalars=True)`, carry off then on. **66 types fit**, none needed carry.
- `base.py` → `base_types.pkl`: the current 1,143-row table. It reproduces `item_bodies.h` byte for byte.
- `build.py`: builds a scratch library (base table plus candidates) under `scratch/.../build/<name>/`.
- `screen.py <fits.pkl> <name>`: runs all 292 full-comparison states of `validate_item_clusters.body_cases`
  with `validate_item_carry.ColourWorld` and records every failing case with quality, level and diff kind.
  Results: `s1.screen.pkl` (the 66 fits) and `s2.screen.pkl` (19 carry refits).
- `show.py <lib> <type> <k,..>`: client-versus-C stream diff. `callers.py <type> <k>`: draw and rand call
  sites. `disx.py a b`: disassembly with data constants. `exitstate.py <type> <k> <rets>`: model fields at
  helper return sites.

Probe-stage breakdown (no scalar programs): 185 services (mostly `effect` calls, 13 `glPushMatrix/Pop`,
3 `transform`), 182 phase-0 inference failures (52 draw count, 42 blend light, 36 body light, 17 V, 10 U,
9 BODY light, 7 COLOR), 54 group/phase count mismatches, plus the 66 fits.

**0 of the 66 fits pass.** The real causes, which correct part 13's labels:

1. **Wings, 25 types** (`0x230a..0x2712`; "quality 1-2" in part 13). Every failure is a record with kind B
   `0x26`/`0x5b`, which forces glow level 9. The standard probes use record `(0,0,0)` at levels 0/7/13. For
   wings the glow rows map those levels to 0, so helper phase 1 (`0x44/0x48`) is never sampled and its
   recipe is empty, which gives missing draws (verified `0x230f` k=17).
   **Fix:** supplementary probes for part-14 types only, so earlier tables reproduce: records
   `(0,0x26,0)`/`(0,0x5b,0)`/`(0,0,0)` × quality 0/1/2/9 × levels 0/7/13. `gen.sample` needs `quality` and
   `record` parameters. Assign the phase from the render_type 0x40000 bit, not from the index.
2. **1-ulp blend light, about 17 types** (`0xf0c, 0x1105, 0x1546` plus the mixed `0x156x`). The client
   computes `wave(-4,0)*0.7f + 0.3f` in binary32 with no clamp (`0x01712b6e..0x01712b93`). That is a
   part-11 kind-1 program that `parse_scalar` already parses. The shared input 20 (binary64 pulse with
   clamp) agrees at every probe clock, so the program fallback never runs. **Fix:** the same supplementary
   probes, with more clocks, make input 20 fail and the existing fallback select the program.
   Alternatively, prefer program inputs (index ≥35) in `infer` for part-14 types.
3. **Body light at the ancient/helper passes, 19 types** (`0xb10, 0xb12, 0x1569..0x1574, 0x170f, 0x1718,
   0x1728, 0x1732, 0x1752`). Carry refits (`fits_carry.pkl`) still fail. The body leaves the model at
   *exit* fields that are not its last draw's fields. Verified on `0xb10` k=32: the last draw's light is
   (1, 0.8, 0.2), but at the return to `0x017e1f3d` the model light is (1,1,1). The helpers then overwrite
   it, and the ancient pass keeps the helpers' light. **Fix design:** a new recipe entry kind 4 = EXIT
   (fields 8..15 = body light, level, shade, flag) inferred like the other words. The generator snapshots
   model fields at each helper's return site in RenderObjDraw. Find the sites by scanning the
   `0x0176ce74..0x017e7000` text for `e8` calls to `0x016e036c/0x016dc148/0x016dec15` and hooking the
   following addresses. `apply_recipe` writes EXIT to `s->model` without emitting it. The probe entry
   `mu_rc_item_draws_carry` takes the exit snapshots instead of the last draws. Use a new row flag so part-13
   carry rows are unchanged. `0x2003/7/9/f/10` fail carry refit at the probe stage. Check them after EXIT.
4. **Body random, 56 types** (12 among the fits: `0xb22, 0xb3b, 0xb43, 0xb45, 0xf0d, 0x10fd, 0x171d..f,
   0x1742..4`). Idiom: `call 0x01989721; cdq; push N; pop ecx; idiv ecx; cvtsi2ss xmm0,edx;
   divss K; addss K2` (e.g. `0x016ebefc`: %15 /21.5 +0.4 → blend light; `0x01752cb4`: %15 /37.5 +0.5,
   which then scales the body-light vector (0.9,0.4,0.2) through `0x00cfcd74`). **Fix design:** program
   kind 4 = random chain parsed at the rand return site. The executor draws through
   `mu_rc_item_context.random` (as rank 5 does), with per-phase draw counts in client order. The
   validator stubs rand with a sequence and compares the consumed count (pattern:
   `validate_item_next.rank5_cases`). `c_stream` would need a context entry. Body-light products need a
   multiply source, or keep those types out.
5. **UV words** `0x1108, 0x1328` (MESH arg5): not investigated yet.

Not started: the 187 "no recipe" clusters beyond the counts above, effects (169) and matrix services (13).

## Next steps (in order)

1. Add supplementary probes (item 1/2) behind a new list `QUALITY_TYPES`. Refit the 66 and the 182
   inference failures with `scalars=True`, then screen. Expect the wings and most of the precision cluster.
2. Add the EXIT entry (item 3), refit and screen.
3. Add random programs (item 4) if time allows.
4. Write `scripts/validate_item_quality.py` as a copy of `validate_item_carry.py` (bodies plus a family for
   the new probes), compiled mutants (phase-1 recipe drop, program-versus-shared input, exit light, random
   modulus/order), a manifest row and a private test. Then: old-versus-new library equality (pattern in
   parts 12/13), the gallery with `MU_LANG_DIR` set, docs, merge main, the gate, the part 10-13
   validators, and the PR.

Steward validators (when PR-ready): the new one plus validate_item_carry, validate_item_chains,
validate_item_scalars, validate_item_wings_next.
