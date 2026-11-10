# MUUN-VISUAL-001

In progress on `codex/muun-visual-001`, from main `9d6ce467`, with current main merged before shared hooks.
Offline/static only; no original client, protection code, network work, installed-app change or proprietary data commits.

The dedicated reconstructed base slot and native fixture model/effect owner now draw an authored Muun beside
the demo hero. `MU_MUUN_FIXTURE=363` in `mu-world` selects an appearance record only. Its model, two attachments,
90 updates per attachment and eight drawn vertices are visible in the local 960x600 GL proof at Lorencia 128,124.
The body-only control uses an absent table; the existing verified effect consumer is unchanged.
[Addresses and scope](../research/client-muun.md).

Checked so far: 912 original instruction cases, zero mismatches; canonical private Muun host, 3 tests,
2.44 s, all 15 actual model codes and all 16 attachments, with exact matrices and ownership controls;
new world render test, 1 test, 2.63 s, visible model and attachment pixel difference. Latest full build 13.78 s,
GL world target 3.41 s (the subsequent frustum fix also compiled). One-time default baselines: October 22
22.60 s, DATA-ACQ-002 58.55 s, 640x400, no draw-all/live-time.

Remaining before PR-ready: final affected portable/private selection, changed mutants once, final identity
sweep, audit and final documentation. No ready-prs entry has been written.

Limits: base body/pose/follow and fixture lifetime only. Auxiliary attack/command classes, additional model/mesh
passes and production Muun selection remain excluded. The fixture RNG has its own deterministic phase.
No original screenshot or live-motion equivalence is claimed. Missing, dummy and out-of-range bones remain refused.
