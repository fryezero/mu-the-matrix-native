# Test finish costs

TEST-SPEED-001 isolates repeated original-instruction execution and repeated mutant compilation from live C
comparisons. The recorded continuation profile spent 89% in body-table regeneration. Warm original-side caching
reduces the recorded continuation/ranked/expansion rows from 867.7/687.5/822.4 s to 23.1/27.2/30.0 s.

Affected-suite selection remains broad because most native hosts link the shared native archive. Removing false
default-goal dependencies helps individual targets; preserving unknown-input fallback and docs consumers leaves
the twelve-PR median near 97%. No large suite-selection gain is claimed.

[Measured results, cache identity, commands and limitations](../testing/TEST-BUDGET.md).
[Delivery checks and remaining work](../handoffs/TEST-SPEED-001.md).
