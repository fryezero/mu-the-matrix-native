# RENDER-EFFECTS-030

Branch `codex/render-effects-030`, base EFFECTS-028 `32e36706` because #376 was
open at start. Main at start `d4af71dd`. Offline/static only; no subagents.

## WIP

Done: read the binding briefs and dependency handoffs. Created the owned
worktree and private input symlinks. Completed the first selectable-skill audit
in `docs/research/client-render-effects-030.md`: 28 learned entries plus ordinary
attack, the stale skill 47, original step/end branches and bounded before status.
Found Triple Shot's missed caller fallthrough and argument ordering.
Built root before edits, 31.92 s, and explicitly built mu-world. Baseline binary
SHA-256 `6f1f9d6a6367e54078a8848b3398dddff92d75ffb6cbf47bf5fd49956a6d43e7`.
The one baseline sweep is in progress. No implementation or verification claim yet.

Left: reconstruct prioritized missing callers and consumers, synthetic selector
proof, original comparisons and mutants, deterministic fixture renders, affected
checks, final identity sweep, main integration and PR-ready docs.

Next: inspect Blood Storm's `0x583/0` dependencies, then implement the bounded
arrow-caller slice. Scratch and baseline binary are under the shared native tools'
`scratch/render-effects-030`; renders use `renders/render-effects-030`.

## WIP checkpoint, 21:52 local

Done: baseline sweep completed once, 46 captures, 92 PNGs and 92 dumps.
The October manifest initially stopped before its first render because its old
paths needed rebasing; completed October run 16.18 s, DATA-ACQ run 44.12 s.
Root build after caller integration passes, 11.43 s. The new caller comparator
matches 120/120 step cases and 180/210 end cases; the remaining Swell Life
sound-owner mismatch was corrected, rerun pending. Selector controls pass 78/78.
Native probes show Ice Arrow with zero refusals and full retirement by frame 90;
Penetration reveals charge `0x7fd0/0` and child `0x46c/0` refusals; Swell Life
refuses 36 joints plus two ground effects, Blood Storm one emitter. Initial
native tests failed on an insufficient retirement horizon and the previously
unknown Penetration child refusal. These are not final passing checks.

Left: finish and review caller comparison, add real synthetic arrow assets and
pixel-removal controls, decide bounded skill-consumer work, verify lifecycles,
run mutants once at finish, affected checks and identity, integrate main, PR.
Next: fix portable test horizon and record both Penetration refusals, then run
the complete caller comparison before consumer implementation.
