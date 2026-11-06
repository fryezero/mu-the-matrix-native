# RENDER-EFFECTS-015

The ground skills' rain 0x70a with its rings and ring models, RenderEffects' terrain decals of 0x70a, 0x70c and 0x45e,
and the effect-sound sites. [Instruction evidence and remaining inputs](../research/client-render-effects-015.md).

Branch `claude/render-effects-015`, worktree `~/Documents/MTM/worktrees/render-effects-015`. The work was traced on
`origin/claude/render-effects-014` while #306 was in steward batch 45; after it merged, main `eb2a8e76` was merged
in `9e734234` (`validators.toml`: both rows kept) and the "before" numbers were taken there once, from a detached
base worktree. No live client session, network work, memory write or installed-app change. The `tools/python`,
`evidence` and `input` links are ignored and never committed.

## Scope

- `reconstructed/combat/bow_fx.inc`: CreateEffect and MoveEffect 0x70a (subtypes 0, 1), 0x700/0x701/0x702
  (0, 1) and 0x707/0; the aim `0x012af5cb`; `mu_sfx_effect_render_ops` (RenderEffects' wrappers and
  RenderTerrainAlphaBitmap calls of 0x70a, 0x70c and 0x45e/3..7); `mu_sfx_sound_site` (six PlayBuffer sites).
  `skill_fx.h`: `MU_SFX_CALL_CASTER`, `MU_SFX_CALL_CREATE_ARROW`, the render-op type, the sound site in `arg8`.
  `skill_fx.c`: `call_sound` passes the site.
- `native/core/mu_combat.{c,h}`: the caster answer (the hero's key, not dead), the rain's CreateArrow for the hero's
  bow owned by the rain's effect OBJECT, the landing flag on the rain record's own +0x64, the ring models
  `min_elf_skill_ring01..08` (`MU_COMBAT_MODEL_ELF_RING1..8`), eleven decal bitmaps loaded GL_CLAMP
  (`MU_COMBAT_BITMAPS` 25 → 36, `mu_combat_bitmap.wrap`), `mu_combat_decal_quads` (one quad per terrain tile,
  drawn in the software path), the sound route's site fallback, summary fields `decals`, `decal_quads`,
  `decal_quads_dropped`, one log line each for missing decal bitmaps and ring models.
- `native/world/parts/combat.c` (GL only): decal quads before the frame's quads; decal textures clamp to edge.
- `scripts/validate_render_effects15.py`, registry row, `native/tests/test_render_effects15.py` with host
  `effects15_host.c`. `effects14_host.c`: 0x70a is now created, not refused. `test_native_combat.py`: installed
  bitmaps 36, models 29.
- No change to reconstructed/joints, reconstructed/particles, the world particle table, item, HUD, app or world
  object code. RENDER-ITEMS-002P: if an item body effect lays a terrain decal, `mu_sfx_effect_render_ops` and
  `mu_combat_decal_quads` are the route.

## Scene results

Installed client, Lorencia tile 182,128, a spider placed at 186,128 (scratch placement), 640x400 software, no
audio/items/players. Bows: class 2, `2:skill:24:spider;3:stop`, 30 frames, every fifth drawn, all 40 bow items of
CreateArrow's arrow table (014's 33-bow list was not kept; these include them). Staff: class 0, skills 1, 2, 3, 4,
5, 7, 8, 9, 10, 14. Ground skills: `2:skill:2044:spider` / `2045`, 40 frames, Bow01 (0x12e6) and 0x12f7.

| Scenes | Before (`eb2a8e76`) | After |
|---|---|---|
| 40 bows, unsupported / arrows | 0 / 140 | 0 / 140; all frames byte-identical |
| 10 staff, unsupported | 0 | 0; all frames byte-identical |
| bows 0x12f7, 0x1303: sound cues | 0 | 12 each (Flare/b's 0x42 at `0x01579fa1`; frames identical) |

| Ground scene | Unsupported | Arrows | Effects | Particles | Sounds | Decal calls (tiles) | Unsupported kinds after |
|---|---|---|---|---|---|---|---|
| 2044, Bow01 | 1 → 53 | 3 → 14 | 3 → 121 | 42 → 140 | 0 → 2 | 0 → 252 (8,788) | Fire06 0x7f40/1, /2, /3: 12, 20, 21 |
| 2044, 0x12f7 | 20 → 46 | 3 → 14 | 30 → 148 | 0 → 0 | 0 → 48 | 0 → 270 (8,926) | Fire06: 18, 18, 10 |
| 2045, Bow01 | 1 → 27 | 0 → 11 | 0 → 73 | 0 → 88 | 0 → 2 | 0 → 150 (5,446) | Fire06: 11, 12, 4 |
| 2045, 0x12f7 | 1 → 13 | 0 → 11 | 0 → 73 | 0 → 0 | 0 → 47 | 0 → 98 (3,546) | Fire06: 2, 4, 7 |

Before, the only unsupported request of the Bow01 scenes was 0x70a itself (0x12f7's own skill-0x7fc arrows already
landed 0x70c before, hence its Fire06 requests). After, 0x70a rains 11 arrows; their landings make 0x70c with its
rings 0x703..0x706 and stones, 0x70a's own rings 0x700..0x702/0x707 rise and sink, and the decals lie on the
terrain. The unsupported count rises because the scenes now contain 0x70c's stones: every remaining request is the
stones' Fire06 particle (not reconstructed). Kept native renders (640x400, not original-client captures) in
`~/Documents/MTM/mu-mac-tools/native/renders/render-effects-015/keep/`: `before-2044-bow01-frame15.png`,
`after-2044-bow01-frame15.png` (the rain, landing craters, the rings), `after-2045-bow01-frame25.png` (landing
flashes and rings), `after-2044-0x12f7-frame20.png`.

## Checks

No lane full gate; the steward runs it. Heavy work used `nice -n 10`, make at most `-j4`, two validator workers.

CHECKS_TABLE

## Steward

STEWARD_SECTION

## Remaining work and cleanup

See the finding's [still-open list](../research/client-render-effects-015.md#still-open): Fire06 0x7f40/1..3
(0x70c's stone particle), the crater decal's alpha test, the other combat bitmaps' clamp, Uruk's weather capture and
the Muun owner fixture.

After the final push: one ready-prs.txt line, then no further push. Scratch, the base worktree and build products of
this lane are removed; the four PNGs above stay. No private input needs to survive cleanup.
