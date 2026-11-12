# RENDER-WORLDS-INNER-003

Branch `codex/render-worlds-inner-003`, from merged main `fb747e42`, PR #378. Implementation by Codex,
GPT-6.1 Sol, without subagents. Merge belongs to the steward.

## Scope and what draws now

Authored inline producers for Aida 33 and its shared world-54 guard, Kanturu Remain 38, Land of Trials 31
and Devil Square 9. Owned source is `reconstructed/objects/world_inner3_visual.*`, with the existing
`native/core/mu_objects_runtime.c` adapter. Existing audio lines are preserved. No new consumers or event model.

## WIP

- Done: All four producers pass 8,000 full original comparisons with no mismatches/stops. All 54 compiled
  mutants are caught, minimum six detections, zero stopped mutants, 287.03 s at `5f8fbb98`. The extended production
  host and producer module pass five private tests, 3.51 s. Main `626abce1` is integrated as `3893d981`, retaining
  both appended validator rows. Integrated root/world builds pass in 13.18 / 6.11 s. Producer inputs are unchanged. Original baseline binary explicitly built from `fb747e42`,
  SHA-256 `e41e2ec2e3e91e6d89e12c81865bdf1bcbde256fa4c3ef88c40380c7c0a249f8`.
  Both default captured tours rendered once with `--hero-name Preview` and `MU_GFX_PUBLIC_DEMO=1`.
- Left: Affected checks, 8d reduced selection, fidelity/identity evidence, review, final docs/PR/cleanup.
- Next: wait for load at most 14 and free memory at least 25%, then run the queued affected selectors/checks and fidelity pass.
  Resume inputs and logs are under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-inner-003/`.
  The integrated mu-world is `7bf4a7e24a283e07e472ea09dff63989955876237a18ecfda2028004bad6114a`.
  The checkpoint has no PR-ready claim. Other worlds and the alpha-reference seam remain untouched.

## Limits and next

Remaining named task worlds are 24, 30, 39, 41, 42, 46 and 98. Entry points remain in
[the research table](../research/client-worlds-inner.md#remaining-inline-work).
Worlds 46/98 reach the common guarded chain `0x017fcb5c..0x017fccbc` and the manager at `0x00ea2dc1`.
A static reread confirms the manager looks up a registered world handler and invokes slot 0x34. It does not
identify a new dedicated 46/98 leaf. No complete absence claim is made. No new live capture or installed app change.

Remaining entry points, not newly verified implementations:

| World | Address / limitation |
|---|---|
| 24 | Kalima `0x00def747`, guard `0x009b0418`, also 25..29/36 |
| 30 | `0x00d8e640`, event byte getter `0x00d8b3e3`; authored input only |
| 39 | `0x00e84941`, guard `0x00e84513`; tower fixture input |
| 41/42 | `0x00d5404b`, getter `0x00d53c8f`, tests `0x00d53d11` / `0x00d53d32` |
| 46/98 | `0x017fcb5c..0x017fccbc` and manager `0x00ea2dc1`; no dedicated leaf identified |

World 54's terrain assets are absent locally. Its shared Aida guard has instruction and production-host
coverage; it has no rendered proof. The alpha-reference seam remains deferred.

## Completed checks at this checkpoint

All commands ran from the repository root, with `nice -n 10`, make at most -j4 and validator jobs 2.
Canonical private-env supplied private inputs. No full lane gate. Resource waits are excluded from check walls.

| Check | Result | Wall |
|---|---|---:|
| Full original comparisons at `5f8fbb98` | Eight families, 8,000 cases, zero mismatches/stops | Included in mutant run |
| Compiled mutants | 54/54 detected, minimum six detections, zero stopped mutants | 287.03 s |
| Extended private production host and producer module | 5/5 pass, no skips | 3.51 s |
| Main-integrated root build | Pass at `3893d981` | 13.18 s |
| Main-integrated explicit world build | Pass, binary differs from before | 6.11 s |
| Initial repository audit | 2,212 files, zero rejected | 19.32 s |
| Validator selection | All 68 selected rows retained, including fallbacks | 64.90 s |
| Private native selection | 166 work items, above the 40-item cap | 59.20 s |

**8d reduced:** the changed production host and new producer module ran privately. No shared struct fields,
table sizes or existing constant values changed. The new exported names occur in the new module/tests and
production adapter. All selected fallback validators remain in the queued run. Affected regression and render
results are pending, so these are checkpoint results, not a PR-ready declaration.
