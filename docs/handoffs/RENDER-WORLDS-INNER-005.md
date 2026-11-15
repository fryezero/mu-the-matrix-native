# RENDER-WORLDS-INNER-005

Branch `codex/render-worlds-inner-005`, from main `6900914e`. Implementation by Codex,
GPT-6.1 Sol, without subagents. Merge belongs to the steward.

## WIP

Done: classified all ten Kalima and fourteen tower active types before implementation. Added Kalima
15/29/32 helpers and complete tower type 0/nested sequence producers, with explicit authored contexts.
Four original families pass 4,000 cases with no mismatches/stops. All 37 compiled mutants are caught, minimum 18 detections, zero stops. Private focused checks pass 13/13 in 6.45 s and the post-change root build passes in 11.18 s.
The expanded 46/98 registry trace identifies all direct registrations in the static factory; neither
world has an identified handler object/vtable, so both remain refused.

Post-build selection retains 75 validator rows, including conservative fallbacks. At this checkpoint,
74 pass and validate_render_effects31 is still running, without mutants. The audit passed 2,303 files,
zero rejected, in 38.74 s. The code under validation is 607adef6.

Left: finish the last validator and affected portable checks,
before/after world proofs, one default identity sweep, latest-main integration, final docs/PR/queue/cleanup.

Next step: finish the running effect row, run the prepared portable selection excluding
`native/tests/test_native_app.py`, then render. One ambiguous loop-count
anchor matched both 10 and 100; it was narrowed and only uncompleted mutants resumed. No successful
baseline or mutant repeated. The combined comparison/mutant wall is 225.29 s.

## Scope and limits

[Per-type classification, addresses and context](../research/client-worlds-inner.md).
Production uses fixed authored idle/null-water Kalima context and inactive tower context. Active hero,
water sampler, sequence and timer inputs are instruction-compared authored fixtures. No event controller,
water simulation or live fidelity is inferred. Missing bones and particle/effect consumers remain counted.
No consumers are added, and no installed app, packaging, README, item/actor/combat/UI work occurs.
