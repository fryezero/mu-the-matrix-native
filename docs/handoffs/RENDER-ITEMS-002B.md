# RENDER-ITEMS-002 part 2

Bounded subset implemented in `reconstructed/renderchar`, `native/core/mu_renderchar` and the existing
native item draw paths. [Finding](../research/client-render-items.md#part-2-bounded-body-and-link-effects-render-items-002b)
contains the exact types, original addresses, evidence boundaries and remainder.

- Generated scalar remaps for 103 model types. Compared across all 8,192 types and 16 levels.
- Complete body streams for 11 of the original 1,674 types: two bows and nine wing models.
- RenderLinkItem target `0x012c70e7` for six bow models, two/six/ten linked sprites through the existing
  particle pool and saved item bones. Hero/remote-player/NPC hooks; shared ground and inventory body draws.
- Unicorn: 131,072 scalar cases, 3,212 body cases, 792 link cases, 100 bone-helper cases.
  Total 135,176, zero mismatches. Six compiled mutants caught: 229/584/107/396/792/264 detections.
- Portable rules and bounded-output tests; native saved-pose, bone-bounds, pool-capacity, character and inventory
  integration regressions. Validator manifest row and private owning test.
- Offline before/after character and inventory renders inspected under local `renders/render-items-002b/`;
  reports and before executable under local `scratch/render-items-002b/`. Part-1 artifacts preserved.

Remaining: 1,663 special body types and 17 class skins, other link switch targets starting with `0x012c741a`,
weapon buffs 6/0x8f and other unsupported record/outline/shadow paths, authoritative hero item instances,
Muun integration and nested map-object tables. Part-1 special-window, costume mappings and external Box of Luck
jump limits remain. The other 92 remap-table types still refuse their unrecovered body branches.
Native random state is the existing particle pool's own stream; one-frame sprites have no durable owner index.
No original game or launcher was started, stopped or read. No terrain or per-world-object files changed.

Local macOS gate on the tree integrated with main `fecdddd`: 1357 tests across 38 discovery runs, 158 explicit private/unavailable-input skips. Offline fixture scenarios, native viewer/readers and publication audit pass, zero rejected files. No hosted workflow dispatched.

The existing generic item validator also passes 1,586 comparisons, zero mismatches, with 414 explicit
unsupported inputs excluded. The registered new validator passes with no skips. Self-review against the
brief, repository standards and evidence policy found no blocking issue for this bounded subset.
The first gate caught two historical hero-call structural assertions; their expected call now follows
the shared item helper and the combined gate passes. Local log: `scratch/render-items-002b/integrated-gate.log`.
