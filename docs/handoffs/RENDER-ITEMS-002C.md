# RENDER-ITEMS-002 part 3

Body coverage is **262/1,674**, up from 11. The 251 additions are 120 armour, 122 wings and nine weapons.
The two largest exact call-shape clusters, 61 and 59 wing types, are complete. A 76-type armour parameter
family omits ordinary high colour passes and adds its original three-pass ancient tail. Other additions
include helm/armour/pants set indices 39..44. [Finding](../research/client-render-items.md#part-3-body-clusters-and-offset-links-render-items-002c).

- All 1,674 special item types and 17 class skins surveyed over eleven states, 18,601 runs and 798 observed
  helper/leaf-call shapes. [Types](../research/item-body-types.tsv), [ranked shapes](../research/item-body-shapes.tsv).
  Both size and inferred visibility ranks are recorded. Sixty-two types have at least one explicitly stopped
  state from unavailable synthetic model/mesh data. This is a finite branch survey, not whole-program proof.
- Generated, reviewed parameter recipes drive compiled C and the existing shared hero/remote/NPC/ground/GFx
  inventory draw paths. New types require the normal no-mesh-override inputs. No world files changed.
- Link target `0x012c741a`, staff `0x14f0`, fully integrated with saved-pose offsets and original random order.
  Target `0x012c761d`, bow `0x12fb`, has verified caller requests and five native sprites. Its two conditional
  Spark03 subtype-11 particle requests are counted as unsupported by the existing particle consumer.
  Three targets/eight types now have verified caller streams; two targets are fully integrated.
- New Unicorn checks: 73,292 body streams, 800 link cases, 200 nonzero-offset transforms, **74,292 total**,
  zero mismatches; **8/8 compiled mutants** caught. Each new body type has 292 comparisons. Part 2 rerun:
  135,176 cases, zero mismatches, 6/6 mutants. Generator reproduction is part of the private check.
- Portable and native regressions cover flag/alpha order, hidden meshes, levels, capacity, random consumption,
  saved poses, offsets, absent bones, full pools and explicit subtype-11 refusal. New private owning test and
  manifest row. Fresh-machine controls check the resettable Unicorn world before its body sweep.
- Inspected before/after renders and reports are local under `mu-mac-tools/native/{renders,scratch}/render-items-002c/`.
  Set-40 parts: three refused bodies to zero, 13 to 25 passes. Staff: 11 linked sprites after; its body still
  refuses its unrelated branch. No client bytes, table records, textures or renders are committed.

Remaining: **1,412 special body types and all 17 class skins**, with exact branch membership and priorities
in the TSVs. Next untouched armour cluster has 47 types. Next link target is `0x012c7a45` for `0x0ef4`, then
`0x012c7e68` for `0x0afc`. Spark03 subtype 11 needs its creation/update/render consumer. New-type mesh overrides,
older record-kind/buff/selection/shadow limits, authoritative hero items and unresolved model mappings remain.
Muun and nested map-object tables stay deferred. No original client/launcher process was started, stopped or read.
