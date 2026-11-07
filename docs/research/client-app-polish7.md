# Demo vitals, inventory wings and Retina input (APP-POLISH-007)

APP-POLISH-007 follows up three APP-REFRESH-007 findings. Labels: **verified** = the original instructions ran under
Unicorn and agreed with compiled native code; **static** = an instruction reading that was not executed;
**inference** = a conclusion from values. Inputs: the pinned restored text at `0x00401000` (capture09) and second
image section at `0x01a7c000` (run10) (`scripts/pins.py`).

## 1. HUD maxima: the client has no formula

**Where the maxima come from (static, all writers listed).** setHPMP `0x00c71772` (APP-POLISH-002, verified) shows
CharacterAttribute `+0x68..+0x84` (HP, MP, HP max, MP max, SD, SD max, AG, AG max), or `+0x40..+0x4c` for a
third-class hero. Every store into `+0x70`, `+0x74`, `+0x7c` and `+0x84` through `[0x01d1df1c]` sits in a server
answer:

| Routine | Answer | Maxima written |
|---|---|---|
| `0x0124cc64` | join (`0xA0` sub `0x07`) | all four, block `0x0124d1bf..0x0124d365` |
| `0x01250b05` | level up (`0xA0` sub `0x06`) | all four (client-progression section 3) |
| `0x01223f04` | stat point answer (`0xA0` sub `0x11`) | HP or MP, SD, AG |
| code at `0x0125133e`, `0x0126202e` | two more handlers in the packet-handler range, each followed by setHPMP (`0x012513d7`, `0x012621ba`) | HP/SD, MP/AG |

The third-class setters `0x00a001fb`, `0x00a0021e`, `0x00a00241` and `0x00a00264` (`+0x40..+0x4c`) have no direct
call site. The data-driven formula table `0x00993099` (CalculateAll) adds to damage, attack rate, PvP rates, defense
and magic (`+0x194..+0x1dc`), never to a vital. **So the original client never computes an HP/MP/SD/AG maximum from
class, level or stats.** The server sends them, and the join copies them.

**The join block (verified).** `0x0124d1bf..0x0124d365` reads eight u16 words of the answer at `[ebp-0x18]`:
`+0x24` HP → `+0x68`, `+0x26` HP max → `+0x70`, `+0x28` MP → `+0x6c`, `+0x2a` MP max → `+0x74`, `+0x30` AG → `+0x80`,
`+0x32` AG max → `+0x84`, `+0x2c` SD → `+0x78`, `+0x2e` SD max → `+0x7c`. A maximum below 1 becomes 1. The current
values' `< 0` tests cannot fire on a zero-extended word. `scripts/validate_app_polish7.py` runs the block (entered at
`0x0124d1bf`, stopped at `0x0124d365`) against `hero_join_vitals` in `native/session/domains/hero.c`:

| Family | What is compared | Cases | Mismatches |
|---|---|---:|---:|
| `join` | random answers (words 0, 1, 0xffff or random) on random attributes, all 0x200 attribute bytes | 4,096 | 0 |
| `seed` | random class/level/stats join data plus the five demo characters through `mu_fixture_hero_join` and `mu_dom_hero_seed`, against the block fed current = maximum words; the eight fields, and current = maximum | 1,024 | 0 |

Ten planted mistakes are caught (two maximum floors, a current floor, SD/AG and MP word swaps, a dropped high byte,
the seed's SD/AG order, the seed's missing maximum word, a skipped field).

**Native.** The offline world seed stands in for the join answer (NET-ACCOUNT-001 keeps the real one out of scope).
It now applies the join block's rule (`hero_join_vitals`) to values from `fixture/hero_join.h`:

1. the recorded level-1 Dark Knight (FryeZEN2, 2026-10-22, client-progression section 7): class byte 1, level 1,
   stats 28/20/25/10/0 → 1100/200/52/25;
2. otherwise the progress fixture's **DEMO** join maxima (`fixture/progress_demo.h`, the tables of
   `core/mu_progress.c` since NATIVE-PROGRESS-001) for the same class, level and stats the fixture server is given.
   The server's own resource answers (A0/30 at join and respawn, A0/06, A0/11) already used this rule, which is why
   Windleaf's MP/SD/AG were 778/1775/284 with maxima 0 before.

The demo rule gives the recorded Dark Knight exactly 1100/200/52/25 (inference that the tables were tuned to it).
These are fixture values for the five offline demo characters, not client data and not a server formula.

| Demo character (row) | Class, fixture level and stats | HP / MP / SD / AG (current = maximum) | Source | Before (HUD, `max`) |
|---|---|---|---|---|
| Nightfall (0) | 0, level 1, start 18/18/15/30 | 600 / 600 / 51 / 39 | demo rule | 1100/0, 600/0, 51/0, 39/0 |
| Ironclad (1) | 1, level 1, start 28/20/25/10 | 1100 / 200 / 52 / 25 | recorded join | unchanged |
| Windleaf (2) | 2, level 320, 22/1302/20/15 (`hero 2` line) | 1119 / 778 / 1775 / 284 | demo rule | 1100/0, 778/0, 1775/0, 284/0 |
| Spellblade (3) | 3, level 1, start 26/26/26/26 | 1100 / 600 / 65 / 41 | demo rule | 1100/0, 600/0, 65/0, 41/0 |
| Crownlord (4) | 4, level 1, start 26/20/20/15/25 | 900 / 400 / 66 / 28 | demo rule | 1100/0, 400/0, 66/0, 28/0 |

The character list's levels (350, 400, 320, 280, 250) are display data. Only Windleaf has join stats
(`demo-session.txt`), so the fixture server runs the others at level 1 with the class start stats, as before.

**Combat HP.** The world's default combat HP input was the Dark Knight's 1100 for every class. It is now
`MU_WORLD_HERO_HP_JOIN`, resolved in `mu_world_rt_open` to the hero's join HP maximum (`world_rt_hero_join_hp`).
`--hero-hp N` still overrides it. The Dark Knight keeps 1100. A level-1 Elf in `mu-world --class 2` gets 800 (before:
1100 with maximum 0).

## 2. Inventory wings 0x2382..0x2385: faithful

APP-REFRESH-007 saw the four wings draw only their upper part since #325. The cause is the body, not the item pass.

- **Path (static).** RenderObjectScreen `0x016c2d82` calls RenderPartObject `0x017e63f4` (`0x016c33d1`), which calls
  RenderObjDraw `0x0176ce74` (`0x017e7960`, `0x017e7997`), the same type cases the world uses.
- **Meshes (verified).** RenderObjDraw under Unicorn (`validate_renderchar.client_stream`), 320 states: levels 0, 7,
  9, 13, 15; OBJECT hidden mesh -1, 0, 1, 2; render types 0, 2, 0x102, 0x40042. `0x2382`/`0x2383` draw mesh 1,
  mesh 2, mesh 1. `0x2384`/`0x2385` draw mesh 0 and mesh 2 three times. No state draws the remaining mesh (0 for
  `0x2382`/`0x2383`, 1 for `0x2384`/`0x2385`). The native recipes give the same mesh list. For hidden mesh -1 and 0
  (the inventory's values) all 160 streams are equal.
- **No clip.** The item pass `0x00abfcca` sets `glOrtho(0, W, 0, H, 20, 2000)` (`0x00abfe8d`; near and far are the
  doubles at `0x01a83c80` and `0x01a7f580`). Native `mu_hud_item_projection` uses the same values. A native render
  with near/far widened to ±20000 is byte-identical (SHA-256 `50190474…`), so no part of these wings is
  depth-clipped. APP-POLISH-004 found no scissor, stencil or clip plane in the item pass.

So the original's inventory shows the same upper part: the model's other mesh is not drawn by its RenderObjDraw case.
Nothing changes. Found in passing, for the renderchar lane (RENDER-ITEMS-002S): with OBJECT hidden mesh 1 or 2 the
native recipes refuse the state and draw nothing, while the client draws its four records (160 of the 320 states).
The inventory and ground items never use those values.

## 3. Retina input

- **Real mouse events (static + windowed).** SDL reports window points. mu-client multiplies them by drawable pixels
  per point (`f->scale`) for the shell (`main.c`) and the world (`input_sdl.h`: `(int)(x * scale)`). The GFx layer
  divides back to stage points (`mu_gfx_layer_mouse`, `x /= L->scale`). So a real click lands where the game draws.
  Windowed check (worktree build, 1600×1000 points, 3200×2000 drawable): SDL mouse events queued at window points
  122,257 and 122,324 (the new `event:` action, handled by the same event loop as the system's events) select
  Noria and Devias in the Warps window: `travel: world 0 -> 3`, `world 3 -> 2`.
- **The input script was the inconsistent part.** Its positions were drawable pixels (INPUT-001's contract), so a
  Retina window needed doubled numbers. They are now window points: windowed front ends (mu-client, mu-world)
  scale them like a real event (`mu_world_rt_action_scaled`). Headless runs and 1x displays use scale 1, so their
  scripts are unchanged. Main's build with window-point clicks 122,257 / 122,324: the Warps window opens, no travel.
  This branch: travel 0 → 3 → 2. [client-input](client-input.md) documents the space.
- **UI scale.** The GFx layer lays its movies out in window points: stage = drawable / scale
  (`mu_gfx_layer.c` `L->w = px_w / scale`), drawn at 2× on Retina. The windowed 3200×2000 Warps frame, downscaled by 2,
  matches a headless 1600×1000 frame of the same scene: mean absolute difference 2.63/2.30/1.87 per channel over the
  Warps region (a 1.1× mis-scale gives 15.98/14.10/11.17), and the window's gold frame ends at 409,582 vs 408,582. The
  headless 1600×1000 layout is the client's own viewport rule at that size (`validate_app_polish2` viewport cases). So
  the HUD and Warps window have the original's size relative to a 1600×1000 window. The offline label (native-only)
  is drawn in drawable pixels and looks half-size on Retina.

## Limits

- Vitals for characters other than the level-1 Dark Knight are demo-server values: the original has no client rule
  and no recording of them. The join block is verified; the numbers fed to it are fixture data.
- The real NSEvent → SDL point conversion is SDL's own. The windowed check starts at the SDL event, because the lane
  may not move the owner's pointer.
- The wing verdict follows the client to RenderObjDraw's mesh calls. No original-client inventory capture.
