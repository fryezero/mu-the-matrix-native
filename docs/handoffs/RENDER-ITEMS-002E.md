# RENDER-ITEMS-002 part 5

This slice adds 75 item bodies, the remaining six class skins and two RenderLinkItem targets. Bounded
coverage is **501/1,674 item bodies**, **17/17 class skins**, and **seven link targets/twelve types** with
native consumers. [Finding](../research/client-render-items.md#part-5-remaining-skins-and-ranked-body-clusters-render-items-002e)
records original addresses, arithmetic and the command-stream/native-render evidence boundary.

The 75 bodies comprise 38 armour types, one wing and 36 model-group `pet/item` types. Four ranked shapes
are complete: rank 6 `ef7283f9b1892031`, rank 7 `6cc0c623a575db41`, rank 8 `b0c194a89f726bf0` and rank 10
`64fc725e1c85631d`. The other additions fill smaller shapes. The 1,691 type rows and their original shapes,
stopped-state counts and ranks are unchanged; only implementation membership changed. Frequency/visibility
remain model-index inference. Seven probe-fitting candidates remain refused:
`0x230f/0x2317/0x248e/0x2490/0x2492/0x2504/0x270f`.

The shared recipe executor distinguishes pulsed body light from the caller's binary64 blend-light pulse.
Class-skin early returns preserve raw/effective-level selection, fixed draw words and initial model shade.
The two sprite skins use saved player bone zero, transform without scale, then add object origin. Their
colour, scale and offsets are compared separately from native particle allocation. The scrolling skin uses
the signed remainder of truncated negative time. The sword links preserve random order, jitter, offsets,
bone selection and time-dependent colour/rotation.

Hero, remote-player and NPC body calls retain the new recipes and sprites after merging the newer session
call sites. Ground and GFx inventory draws share body/UV commands; their skin sprites remain unconsumed.
Link effects remain character attachments. Native tests cover saved poses, origin/scale, missing bones,
full pools, random consumption and standalone character integration. Portable controls cover skin output
capacity with a sentinel, both mesh-override refusals for all six skins, and all seven rejected candidates.
The resumed review found that standalone character renders left the particle pool's clock at zero. The
renderer now forwards each frame's body-command time before skin/link emission. A native pixel regression
using an authored Spark03 JPEG fails before the fix and passes afterward, with visible colour/scale changes
at times 0 and 500. Native JPEG/Pillow unavailability produces an explicit portable skip.

## Verification

The pinned executable/text/data identities are unchanged. `validate_item_continuation.py --mutations`
compares production C against original instructions in **25,772 cases**, zero mismatches:

- 21,900 complete body streams, 75 types times 292 varied states.
- 3,072 complete skin body/effect streams, six types times 512 varied states.
- 800 full link callers for `0x0afd/0x0afe`, targets `0x012c807d` and `0x012c8d7b`.

All **9/9 compiled mutants** are caught: mesh index, blend pulse, raw skin level, skin scroll, sprite colour,
sprite offset, sword bone, sword rotation and sword flare offset. Both body and skin generators reproduce
their checked-in rendering rules from pinned instructions. Twenty further original-instruction cases cover
signed clocks, wrap/remainder boundaries and conversion limits. New evidence totals **25,792 cases**.
These comparisons cover bounded draw/service streams, not every persistent model/OBJECT byte or GL output.

Earlier body/link/skin/particle regression results and the full Mac release gate are recorded below after
the resumed runs complete. Reports/logs stay local under
`~/Documents/MTM/mu-mac-tools/native/scratch/render-items-002e/resume/`.

Offline before/after renders are preserved under `mu-mac-tools/native/renders/render-items-002e/`, with
reproduced pairs and the textured pulse proof in `resume/`.
The authored armour scene changes from three refused bodies/three passes to zero refusals/24 passes;
the early-return skins change from three refusals/three passes to zero refusals/seven passes. The other skin
scene has four passes and two allocated sprites. These are untextured synthetic software renders, not
original-client pixel comparisons. The sword scene allocates five sprites but has unchanged image pixels
without effect textures. Previous milestones' renders/hashes remain preserved.

## Review and remaining work

The interrupted checkpoint was reviewed against the brief, repository standards and original comparison
boundaries. The generated skin fallback retains initial shade, and all world body hooks supply saved player
bones rather than a later overwritten shared item pose. The coverage TSVs were checked independently against
the original survey and enabled C recipe membership. After correcting the standalone clock forwarding,
self-review found no blocking issue in this subset.

Remaining: **1,173 item bodies**, further links, rank-5 pose-aware animation and rank-9 armour branches.
Rank 5 reads the absent model action pointer at `+0x30`, stopping at `0x012b51a7` from `0x01747a0a`;
a stubbed pose call would not prove native geometry. Next shared link target `0x012c8571` covers
`0x132f/0x14f2` and adds particle behavior. Ground/inventory skin sprites, authoritative hero equipment,
owner-follow/random-stream synchronization, missing model mappings, selection/shadow/buff/record-kind and
mesh-override limits, and earlier NewUI/Box of Luck limits remain open. Muun/nested map-object work is deferred.

Only the assigned existing worktree was edited/built. No main-checkout or other-worktree files were changed.
No live game or launcher was started, stopped, driven or read. No hosted workflow was dispatched.
