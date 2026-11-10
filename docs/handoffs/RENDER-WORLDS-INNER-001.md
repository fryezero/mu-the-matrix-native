# RENDER-WORLDS-INNER-001

Implementation checkpoint, checks in progress. Branch `codex/render-worlds-inner-001`, from origin/main
`ff8e0543`. Owned files: `reconstructed/objects/world_inner_visual.*`, the object-runtime seam, new validator
and synthetic tests. Shared Makefile and validator registry changes are added lines only. Input links point
at the main checkout and are not committed. Installed apps and live clients are untouched.

[Research, addresses, call table and explicit consumer limits](../research/client-worlds-inner.md).

Done: complete authored call producers for Kanturu 0x00e75089 in 37/40 and the Blood Castle inline switch
0x017fc023 in 11..17/52; bounded original comparison; native emitters and extra mesh adapter; portable production
host. Small comparisons exposed and corrected pulse/light constants. The production host passes.

Left: full original counts and changed mutants once, affected suites/validators, reduced private native tests,
render comparison and one default byte-identity sweep, final self-review/docs/PR/ready line, cleanup.
