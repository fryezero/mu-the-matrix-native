# MODEL-HIERARCHY-001 continuation (Claude, issue #22)

Read [the finding](../research/model-hierarchy.md). The client reader `0x012b3812` stores the dummy byte at bone `+0x22` and copies the parent word to `+0x20` unchecked. It writes nothing else for dummy records. Pose builders `0x012b5064` and `0x012bcffb` skip dummy records and compose a child from `out[parent]` with no range, order or dummy check. For the 66 rejected edges, that slot is never written by the same call. The parent input is the caller buffer's unknown prior content. The child output composes it with the local matrix. Raw searches suggest shared-buffer use at `0x06fce398`, but caller/argument provenance remains unverified. No validation change was made.

Checks run: `scripts/model_hierarchy_verify.py` passes all scripted checks against the pinned captures. `tests/test_model_hierarchy.py` has 14 portable tests plus one private check; all 15 pass with `MU_RECOVERY_INTEGRATION=1`. Results of the full portable suite and the publication audit are in the PR.

Private artifacts are in the Claude worktree's ignored `evidence/claude-model-hierarchy/`: decompiler text, function listings, stride scan and verification reports. An earlier report with the incorrect store window is kept as `verify-report.failed-store-window.json`. The shared evidence and installation were read only.

Next concrete step: capture the `0x06fce398` slots, guarded by the restored-text hash, while one affected model (for example `Data/Item/medusa.bmd`, edge 87→86) renders. Also decode the 13 files' full parent arrays to count affected descendants. Then choose between keeping rejection and the per-bone "unwritten parent slot" marker described in the finding.

Post-merge review corrections under issue #27 qualify the raw call/PUSH counts and unknown prior state. The scanner stops at control transfers, and two new synthetic counterexamples guard those limits. Selected-loop instruction observations and strict model rejection remain unchanged.
