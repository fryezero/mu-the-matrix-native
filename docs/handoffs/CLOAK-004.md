# CLOAK-004

Branch/worktree `codex/cloak-004`, from `origin/main` `825c37b7`. Offline/static only. No live client,
launcher, installed app, network work or hosted workflow. No full gate in the lane, per TEST BUDGET.

Scope: NPC/monster cloth constructor `0x01362755`, its model selections and native actor callers.
The existing wing/armour cloth code supplies the physics, texture upload and software/GL renderer.

## Result

- `mu_cloth_npc_create` ports all six class-index cases, including the two Eunice halves, UV setters and
  opposite-side collision spheres. `mu_cloth_npc_cloths` rejects every other class.
- RenderCloth's sole direct call is `0x01363102`, after the player armour constructor declines. An existing
  NPC list makes the constructor return false. These actors get one MoveCloth per frame, with the creation
  frame's extra step, rather than the player armour's repeated second step.
- `world_cloak_actor_draw` uses each actor's own posed bones, body scale/origin, angle, action pair and alpha.
  Player-model actors draw cloth between body parts and linked items. Other actors draw it after their body.
  Actor slots survive between saved frames and are freed before an actor-cache replacement and at travel/unload.
  The original cloth gate and second-list white-light draw are reused.
- Death King class 55 can now use the existing player-model actor loader. Nightmare class 361 takes its
  world-39 processor's model/scale; Eunice Monster class 937 takes its dedicated create method's model/scale.
  Generic table values for those last two had been the world-0 fallback model `0x7a5`.
- Four cloth bitmap registrations use the original startup file names, filters and wraps. Item/particle sources
  and the shipped placement files are unchanged. Ordinary Lorencia, Devias and Noria NPC class IDs select no cloth.

## Which NPCs and monsters

Class index is CHARACTER `+0x146`, not the OBJECT model index. Names are the local exported `npcnames.tsv` lookup.
The names shown in rendered fixtures are authored demo labels.

| Class | Name | Model / type | Cloth |
|---|---|---|---|
| `55` / `0x37` | Death King | Player `0xa91`, scale 1.4 from the existing generic table | one bone-19 10x10 robe, origin 0,10,0; 55x140; bitmap `0x790d`; type `0x1001` |
| `361` / `0x169` | Nightmare | world 39: `0x81e`, monster type 121, `Monster122.bmd`, scale 1.6; other worlds keep the generic fallback | one bone-2 6x6 cloth, origin 0,0,0; 180x100; bitmap `0x7ff2`; type `0x1008`; no spheres |
| `937` / `0x3a9` | Eunice (Monster) | dedicated virtual create method: `0x95a`, monster type 437, `Monster438.bmd`, scale 0.9 | two bone-4 10x10 halves, origins +/-10,8,2; 200x120; bitmaps `0x84e6/0x84e7`; type `0x1005` |
| `939..941` / `0x3ab..0x3ad` | Eunice (Town / Entrance / Quest) | NPC `0xa8b`, `N_eunice.bmd`, scale 0.9 from the existing generic table | same two halves |

Death King spheres: (-10,-10,-10,r35,b17), (10,-10,-10,r35,b17), (0,-10,-40,r50,b19).
Eunice U scale is 0.5, V scale 1, U offset 0/1. The first half's spheres have x=-10, the second x=10,
with y=-5, z=-10/-30, radius 30/35, bone 3. Their origins use the opposite sign.

Bitmap startup calls: `0x0182c044`, `0x0183d611`, `0x01827fc5`, `0x01827fe5`:
`Player/Robe03.tga`, `Monster/nightmare_cloth.tga`, `NPC/eunice_cape_L.tga`, `NPC/eunice_cape_R.tga`.
All use clamp `0x2900`; the first two use nearest `0x2600`, Eunice uses linear `0x2601`.

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`, from the repository root. Heavy commands use
`nice -n 10`, `make -j4`, validators `--jobs 2`. Resource checks precede heavy steps.

Final results are recorded here after the affected checks finish.

## Scenes, byte identity, renders

The baseline binaries were built once from main `825c37b7` before source edits. Temporary outputs live under
`~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/cloak-004/` and are removed at cleanup.

## Limits

- Static and Unicorn evidence only. No live original-client motion or pixel comparison.
- The original gate's guild/duel/buff inputs remain at rest, as in CLOAK-002/003. Fixture actors use sub-type 0.
- Native uses its own wind/rand history and reconstructed posed bones. Instruction comparisons use identical
  authored bones and rand state on both sides. This does not establish original-client pixel equivalence.
- Class 937's dedicated create method is compared through model selection and scale. The original virtual manager's
  world/event selection and trailing effects are outside this lane. A native fixture explicitly placing class 937
  selects that known model. Nightmare's world-39 predicate is preserved; outside it the generic table still applies.
- Death King's pre-existing generic equipment table has only a weapon. This lane enables that actor loader and
  its robe; it does not reconstruct missing body-part or special monster render recipes.
- The lane adds no actors to the shipped placements. Eligible IDs supplied by existing fixture/session records get
  cloth automatically. The ordinary town smith, merchant, storage, guild and quest NPCs do not acquire capes.
- GL_QUADS become two triangles, as in the earlier cloak lanes. No protection code, server state, stats or packets
  are inspected or changed.

## Release

Steward validators and their tested commit will be recorded after the affected selection and runs.
Cleanup removes the lane's scratch, renders, build outputs, worktree and local branch after its ready-prs line.
No new input needs to be kept. The remote branch remains for the steward.
