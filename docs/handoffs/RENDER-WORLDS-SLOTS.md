# RENDER-WORLDS-SLOTS

The world classes' other slots after the primary methods: custom render (+0x38), after render (+0x3c) and
invisible move (+0x1c), the hook chain around the class slot, and Loren Market's outer RenderObjectVisual draw.
[Census, addresses, fidelity and limits](../research/client-worlds-slots.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-slots`, branch `claude/render-worlds-slots`,
  from origin/main `b8645181`. MERGE-PLACEHOLDER Input links `tools/python`, `evidence` and `input` point at the
  main checkout and are never committed.
- **Census (verified/static):** all 48 classes × 3 slots, ordered by player reach. Before this lane 49/144 were
  native and compared (the coverage JSON still listed 9); **now 125/144**. 19 are missing, none in a captured or
  warp-reachable world.
- **Captured worlds' slots (verified):**
  - custom + after of Vulcanus 63, Loren Market 79 (with Event square 114, the same body), Ferea 112, Swamp of
    Darkness 122 and Kubera 123..127;
  - invisible move of 142, 143, 144 and 145.
  - Bitmaps: Kubera's loader table (61 bitmaps, per-world handler words), Ferea's statue, the crocodiles.
- **Trivial slots (verified):** 60 base or empty slots are compared under Unicorn and need no native code.
- **Hook chain (verified):** every hook around the class slot in RenderObjectVisual, the custom render and the
  after chain is a no-op in all 57 class registrations (1,881 runs). The direct class-slot dispatch is complete;
  no chain code was needed.
- **Loren Market RNG (verified, changed):** `0x017f9758` draws `rand() % 30` for every object with a model before
  its world switch. The native 79 branch now draws it too. Other branches without it are listed in the finding
  (§5) and left unchanged.
- **Shared lines:**
  - `world_slots_visual.c`: the slot helpers moved verbatim into `world_visual_slots.h`; three dispatch fallbacks
    and two bitmap fallbacks;
  - `world_visual.h`: three `mu_slot_model` fields (handler state, bone callback) and one declaration;
  - `object_render.{c,h}`: `mu_obj_handler_moves` for 142..145;
  - `mu_objects_runtime.c`: `class_custom_call` (Vulcanus bones, the sprite/particle requests to `consume_visual`),
    the slot model's new fields, the 145 step handler, the 79 outer draw;
  - `native/Makefile`: the `worlds-slots-host` rule;
  - `world-handler-coverage.json`: slot statuses (including AFTER..AFTER3's);
  - one validator row;
  - `docs/handoff.md`: a leftover merge-conflict block at the top resolved by keeping both sides.

## Checks

CHECKS-PLACEHOLDER

## Remaining

- Custom/after of 62, Imperial Guardian 69..72 (70/71 forward to 69's 1,468-instruction custom slot), 82, Arca War
  92, Nars 110, Test Area 121, and the custom slots of 95 and 100. None has a capture.
- The outer RenderObjectVisual draw in the native branches of 57/58, 62, 63, 64, 82, 100/101, 128..130 and 137
  (finding §5).
- Ferea's door state writer (server messages; the state stays at its constructor value 0).

No original client or launcher was started; the DATA-ACQ-002 and October 22 inputs were only read. No shared
particle/effect/joint hook was added: Vulcanus' sprites and particles use the existing visual consumer.
