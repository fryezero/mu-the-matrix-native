# RENDER-WORLDS-INNER-003

Branch `codex/render-worlds-inner-003`, from merged main `fb747e42`, PR #378. Implementation by Codex,
GPT-6.1 Sol, without subagents. Merge belongs to the steward.

## Scope and what draws now

Authored inline producers for Aida 33 and its shared world-54 guard, Kanturu Remain 38, Land of Trials 31
and Devil Square 9. Owned source is `reconstructed/objects/world_inner3_visual.*`, with the existing
`native/core/mu_objects_runtime.c` adapter. Existing audio lines are preserved. No new consumers or event model.

## WIP

- Done: All four producers pass 1,600 original comparisons with no mismatches/stops. The Aida/Remain production host
  and producer module passed five private tests. Original baseline binary explicitly built from `fb747e42`,
  SHA-256 `e41e2ec2e3e91e6d89e12c81865bdf1bcbde256fa4c3ef88c40380c7c0a249f8`.
  Both default captured tours rendered once with `--hero-name Preview` and `MU_GFX_PUBLIC_DEMO=1`.
- Left: Final full original cases and 54 compiled mutants, affected checks,
  private host extensions, 8d reduced selection, fidelity/identity evidence, review, final docs/PR/cleanup.
- Next: wait for load at most 14 and free memory at least 25%, then run the extended private host and final comparison/mutants.
  Resume inputs and logs are under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-inner-003/`.
  The checkpoint has no PR-ready claim. Other worlds and the alpha-reference seam remain untouched.

## Limits and next

Remaining named task worlds are 24, 30, 39, 41, 42, 46 and 98. Entry points remain in
[the research table](../research/client-worlds-inner.md#remaining-inline-work).
Worlds 46/98 reach the common guarded chain `0x017fcb5c..0x017fccbc` and the manager at `0x00ea2dc1`.
A static reread confirms the manager looks up a registered world handler and invokes slot 0x34. It does not
identify a new dedicated 46/98 leaf. No complete absence claim is made. No new live capture or installed app change.
