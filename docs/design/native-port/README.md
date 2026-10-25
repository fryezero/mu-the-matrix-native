# Design: completing the native macOS port

The architecture and the remaining work for a native client that logs in to the live Mu The Matrix service
(owner decision, 2026-10-24). Produced with the pstack `architect` workflow: grounding over the current code, three
structurally different candidate designs, an independent cross-judge, and a synthesis on the strongest base.

| File | What it is |
|---|---|
| [rationale.md](rationale.md) | Problem, the caller's usage, the shape, the synthesis decision, tradeoffs, alternatives, open questions |
| [plan.md](plan.md) | Every remaining milestone (IDs, scope, completion evidence, dependencies, EA/BP/OP status), critical paths, parallel lanes with owned paths, gate mapping |
| [sketch/MODULES.md](sketch/MODULES.md) | Module map: who owns which state, who may include which header, generated lists, call chains |
| `sketch/` | Type and signature sketches at their future repository paths. Bodies are `MU_NOT_IMPLEMENTED()` or `TODO` pseudocode. Nothing here is built; each milestone moves its files into place and fills them in |

Status classes in the plan: **EA** evidence-available, **BP** blocked by the protection boundary, **OP** needs the
owner or the server operator. The operator's answers (2026-10-25: account-only login, native client allowed,
recording and automated play allowed, one client at a time) are in
[service-contract.md](../../research/service-contract.md). The protection boundary is unchanged: no part of this
design analyses, forges, records or replays launcher, IGC.dll or RGS.dll material.
