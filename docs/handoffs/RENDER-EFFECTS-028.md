# RENDER-EFFECTS-028

## WIP checkpoint

Branch `codex/render-effects-028`, base `d4af71dd`. Worktree
`~/Documents/MTM/worktrees/render-effects-028`.

Done: static aura consumer audit, isolated `aura_fx` reconstruction, opt-in
hero fixture adapter and original-instruction comparator authored. Baseline
world built before native adapter edits; default sweep running. Nothing is
PR-ready yet. No live client or installed app touched.

Original comparison: 4,390 cases, zero mismatches, 18/18 compiled C mutants
caught without original-machine stops, 49.71 s. Baseline default sweep: 230
artifacts across 46 captures, 121.17 s; binary SHA-256
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
Native root build passed, 11.36 s; rebuilt world passed, 5.64 s. Four
private native tests passed in 9.33 s, including both buffs drawing, expiry,
repeat identity, unchanged HP/requests and existing bitmap/combat consumers.
Portable affected suites passed: 162 work items, 1,742 tests, 1,453 passed,
289 skipped, zero failures/errors, 518.00 s outer wall. All 56 private affected validators passed, zero fail/error/skip, 1,029.71 s
outer wall. Run launched at `4f616859`; compiled sources match `a3762b6a`.
The added bitmap-site checker was corrected before its row executed and passed. Native private selection is 163 items, so 8d reduced applies.

Changed bitmap checker: 424 cases and 23/23 compiled mutants passed, 34.39 s.
Installed-data GL proofs passed, 10.03 s: skill 27 has 95 requests / zero
refused, skill 28 has 209 / zero refused; all ten after/repeat PNGs match,
and the expired frames match baseline. The after identity sweep is running.

Left: after identity result, audit, final status docs and PR publication.
Main is still `d4af71dd` on the last fetch.
Next: inspect `scratch/render-effects-028/sweep-after.log` under the shared
native tools. World was rebuilt immediately before the sweep. Finalize the
handoff from the reports, update status lines, audit, then publish the PR.
