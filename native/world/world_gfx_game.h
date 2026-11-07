/* Game-side pieces of the GFx interface over the native world (NATIVE-GFX-003).
 *
 * The client draws its 3D item models over the GFx windows and into the bar's
 * item hotkey image; GFx cannot.  This module does both for the layer
 * (native/gfx/mu_gfx_layer.h):
 *
 *   - wg_items_draw: the per-window item pass 0x00abfcca for the slot calls
 *     the layer's reconstructed slot pass made: the slot wrapper 0x016c23d5
 *     and RenderItem3D's general path 0x016c154e (reconstructed/hud) give
 *     model, position, rotation and scale; the model is drawn with the
 *     reconstructed world item render (NATIVE-RENDERCHAR-001: glow levels,
 *     excellent passes) through the GL mesh-draw port under
 *     glOrtho(0, W, 0, H, 20, 2000), depth cleared per window, as the client
 *     does;
 *   - wg_items_icons: the item hotkey icons rendered the same way into an
 *     offscreen 512 x 512 target and read back for the game image image0;
 *   - wg_skills_load: a skill table for the data movie's skill icons.
 *
 * Inputs from outside the restored code, labelled in docs/research/native-gfx3.md:
 * item render info from Lang's ItemTRSData (itemtrs.tsv, APP-POLISH-004), or
 * without it from itemtrsdata.bmd with the authored scale factor of
 * NATIVE-HUD-001; the picked-up item's 1.4x enlargement and the hovered
 * item's spin are RenderObjectScreen static readings; the skill table is the
 * installed Data/Local/skill.bmd, which the restored code never loads (the
 * build reads its skills from the encrypted Lang.mpr): its icon numbers and
 * sheet types are an inference, its names are not shown. */
#ifndef MU_WORLD_GFX_GAME_H
#define MU_WORLD_GFX_GAME_H

#include <stddef.h>
#include <stdint.h>

#include "../gfx/mu_gfx_layer.h"

typedef struct wg_items wg_items;

/* game_root may be NULL (nothing is drawn; the layer keeps its stand-ins). */
wg_items *wg_items_open(const char *game_root);
void wg_items_close(wg_items *w);
/* RENDER-ITEMS-TEX-002 (authored): part models loaded afterwards take this class byte's skin index (+0xa4), as if
 * the hero had worn them; -1 (default) keeps 0. */
void wg_items_set_wearer(wg_items *w, int32_t class_byte);
/* mu_gfx_items_fn / mu_gfx_icons_fn for the layer config (user = wg_items). */
void wg_items_draw(void *user, const mu_gfx_item_draw *items, int n, int32_t stage_w, int32_t stage_h);
int wg_items_icons(void *user, const mu_gfx_item_draw *items, int n, uint8_t *rgba, int32_t w, int32_t h);
/* Clock for the hovered item's spin (ms). */
void wg_items_set_time(wg_items *w, double time_ms);
/* Models drawn / failed so far (reports, tests). */
void wg_items_counts(const wg_items *w, long *drawn, long *missing, long *icons);

/* INVENTORY-FX: the world the icons' effects go to. RenderObjectScreen draws an icon through RenderPartObject and
 * RenderObjDraw like a ground item: the type's pre-draw program (and RenderObjDraw's 0x389c/0x389d skin
 * sprite) runs on the icon's own pose and calls CreateSprite/CreateParticle, whose lists only the world scene's
 * RenderSprites/RenderParticles draw (with the world camera, the next frame); the item pass draws none. Its
 * TestFrustrum2D flag is taken at the icon's OBJECT +0x158 (its screen position) with the world frame's polygon.
 * particles: the world's lists (NULL: no world, nothing is created); item_pre: sets env->item_bones, the flag and
 * the counters as world_rt_item_pre does for the other callers. NULL world: no effects (the default). */
struct mu_renderchar_env;
struct mu_world_particles;
struct mu_model;
typedef struct wg_items_world {
    void *user;
    struct mu_world_particles *(*particles)(void *user);
    /* object: the icon's owner key within the pass (OBJECT-owned particles, RENDER-EFFECTS-020) */
    void (*item_pre)(void *user, struct mu_renderchar_env *env, int32_t type, const struct mu_model *model,
                     const float *bones, uint32_t object);
} wg_items_world;
void wg_items_set_world(wg_items *w, const wg_items_world *world);

/* Skills from Data/Local/skill.bmd: 120-byte records, each XORed with the
 * repeating key FC CF AB; record i is skill index i; Magic_Icon at +74 (u16),
 * MasteryType at +54, SkillUseType at +55.  Names are left as "Skill N"
 * placeholders (Korean in the file; the build's names are in Lang.mpr).
 * Returns the count (0 when absent or malformed). */
int wg_skills_load(const char *game_root, mu_gfx_skill *out, int max);
/* The same decode over a buffer (tests). */
int wg_skills_decode(const uint8_t *data, size_t size, mu_gfx_skill *out, int max);

#endif
