/* The GFx interface over mu-world's 3D view (NATIVE-GFX-002/003).
 *
 * `mu-world --gfx DIR` opens native/gfx/mu_gfx_layer over the world: the
 * client's bottom bar, inventory, item tooltips, character window and chat,
 * played through mugfx (loaded at run time) and composited after the 3D
 * pass, the way the client's main-game render draws the GFx manager after
 * the world (client-hud.md, "UI pass order").  Clicks and keys the
 * interface takes do not reach the walk session.  With a game root, the
 * demo inventory uses the client's Item.bmd sizes and names, and tooltips
 * come from itemtooltip/itemtooltiptext through core/mu_hud_tip.
 * NATIVE-GFX-003: with a converted base movie the HUD runs as the client's
 * base movie; item models are drawn over the inventory and into the item
 * hotkey image (world_gfx_game.c); the skill icons use the installed
 * skill.bmd's icon numbers.  NATIVE-LANG-001: with MU_LANG_DIR (the tables
 * read from the running client) the labels, the skill table (names, icons)
 * and the top menu's map name come from the client's GlobalText and
 * Skill(Kor) tables. */
#ifndef MU_WORLD_GFX_H
#define MU_WORLD_GFX_H

#include <stddef.h>
#include <stdio.h>
#include <stdint.h>

#include <SDL.h>

typedef struct world_gfx world_gfx;

/* width/height in drawable pixels, scale = pixels per window point (Retina
 * 2: the movies lay out in points and draw at full resolution).  `open`
 * lists windows to show at start ("inventory,character"). */
world_gfx *world_gfx_open(const char *movie_dir, const char *game_root, int width, int height, double scale,
                          int shared, const char *open, char *error, size_t error_size);
void world_gfx_close(world_gfx *g);
/* NATIVE-PERF-001: the window changed size (drawable pixels): every movie's stage and the client's window
 * placement (SetWindowSize, SetScale(83) below 700 points of height) follow. */
void world_gfx_resize(world_gfx *g, int width, int height);
/* 1 when the interface took the event. */
int world_gfx_event(world_gfx *g, const SDL_Event *e, double scale);
/* Advance by dt and, with draw, composite over the current GL framebuffer. */
void world_gfx_frame(world_gfx *g, double dt_ms, int draw);
/* Hero location for the top menu (world index, world position). */
void world_gfx_set_location(world_gfx *g, int world, float x, float y);
/* One summary line (JSON object body) for the run report. */
void world_gfx_report(world_gfx *g, char *out, size_t cap);

/* NATIVE-NAMES-001: the GFx layer (world_names_gfx.c drives hudPlayerName through it). */
struct mu_gfx_layer;
struct mu_gfx_layer *world_gfx_layer(world_gfx *g);
/* NATIVE-PROGRESS-001: bind the hero's progression (core/mu_progress): HUD values, the experience bar, the
 * character window's rows and "+" buttons; NULL unbinds. */
struct mu_progress;
void world_gfx_progress(world_gfx *g, struct mu_progress *p);
/* NATIVE-NPC-001: the window a talk answer opens (core/mu_npc), the talk
 * result's close-all, whether an NPC window is still open (the player may
 * close it), and the scripted window verbs (buy, sell, take, put, option,
 * next, close).  The texts come from the client's tables with MU_LANG_DIR
 * (Npcname for titles, Dialog(kor) for the demo dialogue text); the items,
 * prices and dialogue choices are the demo table's. */
struct mu_npc_open;
void world_gfx_npc_open(world_gfx *g, const struct mu_npc_open *open, const char *label);
void world_gfx_npc_close_all(world_gfx *g);
int world_gfx_npc_window(world_gfx *g);
int world_gfx_npc_action(world_gfx *g, const char *verb, const char *arg);
const char *world_gfx_npc_last(world_gfx *g);
struct mu_npc_item;
void world_gfx_npc_storage(world_gfx *g, const struct mu_npc_item *items, int n);
/* NATIVE-QUEST-001: quests (core/mu_quest over reconstructed/quest) when MU_LANG_DIR holds the quest tables:
 * setup with the demo file's quest lines (NULL: none), the logic step, a monster kill (demo progress), the
 * report line, and the quest verbs of world_gfx_npc_action (qnext qno qok qclose qwin qtab qsel qgo qgiveup
 * qkill qset).  T opens the quest window; 1..9 / Esc act on NpcQuestProgress. */
int world_gfx_quest_setup(world_gfx *g, const char *demo_text);
struct mu_walk;
struct mu_map_session;
/* The world owns both sessions and consumes the map session's pending teleport. */
void world_gfx_quest_bind(world_gfx *g, struct mu_walk *walk, struct mu_map_session *maps);
void world_gfx_quest_travel_complete(world_gfx *g, int success);
void world_gfx_quest_step(world_gfx *g);
void world_gfx_quest_kill(world_gfx *g, int monster_class);
void world_gfx_quest_report(world_gfx *g, FILE *out);
/* NATIVE-SKILL-001: the selected skill's cast through the client's checks (MU_SKILL_CAST_*, core/mu_skill.h;
 * *skill = the skill), the skill book, and the scripted Skill Imprint window verbs of
 * mu_gfx_layer_skill_action ("open", "drag" from to, "over" slot, "save", "tip" bar slot, ...). */
int world_gfx_skill_cast(world_gfx *g, int32_t *skill);
struct mu_skill_book *world_gfx_skills(world_gfx *g);
int world_gfx_skill_action(world_gfx *g, const char *verb, int a, int b);

#endif
