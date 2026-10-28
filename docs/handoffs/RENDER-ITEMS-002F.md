# RENDER-ITEMS-002 part 6

Checkpoint. The assigned new worktree is `worktrees/render-items-002f`, branch
`codex/render-items-002f`, based on part 5 merge `c769a5d`. No original client or launcher was used.

Implemented bounded additions: 58 item bodies, 27 armour and 31 other item-group models.
Coverage is 559/1,674 item bodies and 17/17 skins. Rank 9 is complete, twelve types. Generated
recipes preserve omitted ancient phases. Nine more ranked shapes are complete in total, including rank 9.
Two generated sprite-chain link targets, `0x012cb556` for `0x0af9` and `0x012cb7ab` for `0x12f9`,
bring complete native caller consumers to nine targets/fourteen types in the existing no-owner domain.

Ground, software inventory and actual GFx item/FBO draws consume the two existing skin sprites through
a skin-only adapter. Character body and attachment hooks retain their existing saved-pose rules.
Native checks cover absent bones, bounded pools, random order, texture-visible sprites, the frame clock
and repeated icon frames on authored static geometry. Animated synthetic models exhibit an existing
first-versus-cached pose difference; the static fixture isolates the sprite clock and does not claim
that broader pose lifecycle is verified.

`validate_item_ranked.py --mutations`: 16,936 complete body streams and 800 link caller streams,
17,736 cases, zero mismatches. Six compiled mutants caught: ancient phase 1,233; object alpha 11,680;
chain bone 800; chain scale 400; random choice 360; final white flare 400. Both generated tables reproduce.
The baseline Mac gate passed before edits. Full integrated release checks are pending this checkpoint.

Reports and source probes stay local under `mu-mac-tools/native/scratch/render-items-002f/`;
before/after renders under `mu-mac-tools/native/renders/render-items-002f/`. These are native synthetic
renders, not original-client pixel comparisons. Client bytes, assets and generated renders are untracked.

Remaining: 1,115 bodies. Rank 5 remains refused: `0x017479b1..0x01747a0a` calls the real pose builder
`0x012b5064` with OBJECT action/frame/angles and writes the shared bone buffer. Its synthetic model lacks
`model+0x30` action data and `model+0x2c` bone tracks. A pose recorder would not verify its resulting geometry.
The shared link target `0x012c8571` for `0x132f/0x14f2` remains unimplemented: it also requests Laser
`0x7fd6` subtype 17 with an item owner, which the current joint consumer refuses. The next sword target
`0x012c91fe` also mutates shared clock/bone state at `0x0a3a0e1c/20`; it is not a stateless sprite recipe.
Earlier mesh-override, selection/shadow/buff/record-kind, hero-instance, owner/random, model mapping,
NewUI and Box of Luck limits remain. Muun and nested map-object tables stay deferred.
