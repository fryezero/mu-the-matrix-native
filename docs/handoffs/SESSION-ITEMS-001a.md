# SESSION-ITEMS-001a

Bounded ground-domain migration on `codex/session-items-001a`, based on origin/main `3162017`.
[Evidence and exact limits](../research/client-ground-items.md#10-session-items-001a-2026-10-28).

The session owns 1,000 ground slots, viewport entries and render records. Recorded C2 20/21 routes
apply creation/removal; the view supplies existing CreateItem services and uses the leased pool for
MoveItems, selection, render plans and labels. The combat drop-event bridge and local pickup/despawn
queue are removed. Scripted drops, the fixed combat sword reward, removal latency and despawn belong
to the fixture `items` behavior. View detachment/rebinding retains records without replaying drop sounds.

Ordinary/zen pickup builder slices and the successful answer sound/label slice are compared against
pinned instructions. Begin(C1,0) is retained exactly as captured. Send(1,0) stays journaled unsent.
Because the findings do not name a pickup-answer route, the fixture's explicit pickup command removes
through the recorded 21 handler. It does not insert inventory, credit zen or claim a pickup answer.

## Checks

- New original instruction comparison: 4,000 cases, zero mismatches; 4/4 compiled mutants caught.
  Families: delete, zen builder, ordinary builder, successful pickup sound/label tail, 1,000 each.
- Existing unchanged item families: rerun in progress, target 22,200.
- Focused session checks: malformed atomicity, invalid-key clamp, pending/refusal, slot 999,
  detach/rebind/delete and motion lease; native synthetic item drive covers fall/pose/labels,
  click/space removal, combat drop and determinism.
- Full locked Mac gate and final fixture counts pending.

## Remaining SESSION-ITEMS-001 evidence

- Inbound opcode/subopcode, head layout and decode boundary for `0x012424bd`, `0x012420a5`,
  `0x01242ea8`, `0x00b0fd9e`. No dispatcher jump table was read. The first routine has a decode
  prelude using `0x06fca280`, which this lane leaves alone.
- Inventory insert `0x01227c51` is named in client-quests.md but has no recorded route; list,
  move, delete, durability and equipment route evidence is also missing. No inventory handlers
  were guessed. GFx inventory/session ownership, `item items[48]` removal, equipment propagation,
  full pickup eligibility and inventory persistence across character select remain.
- NET-DECODE is required for actual pickup sends; SESSION-ACCOUNT owns world/session lifetime.

`docs/handoffs/SYS-MISC-001a.md` was absent from latest origin/main and local worktrees when checked.
The requested lesson was followed directly: finish recorded routes, list missing route evidence,
and leave dispatch/decode untouched. Only `dispatch.seed.def` gains the already recorded 21 row.

No live game or launcher was used. No client inputs, decoded data, screenshots or local symlinks
are committed. Local scratch/build outputs will be removed after merge; no new retained input is needed.
