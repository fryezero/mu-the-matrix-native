/* The GFx interface over mu-world's 3D view (NATIVE-GFX-002).
 *
 * `mu-world --gfx DIR` opens native/gfx/mu_gfx_layer over the world: the
 * client's bottom bar, inventory, item tooltips, character window and chat,
 * played through mugfx (loaded at run time) and composited after the 3D
 * pass, the way the client's main-game render draws the GFx manager after
 * the world (client-hud.md, "UI pass order").  Clicks and keys the
 * interface takes do not reach the walk session.  With a game root, the
 * demo inventory uses the client's Item.bmd sizes and names, and tooltips
 * come from itemtooltip/itemtooltiptext through core/mu_hud_tip. */
#ifndef MU_WORLD_GFX_H
#define MU_WORLD_GFX_H

#include <stddef.h>

#include <SDL.h>

typedef struct world_gfx world_gfx;

/* width/height in drawable pixels, scale = pixels per window point (Retina
 * 2: the movies lay out in points and draw at full resolution).  `open`
 * lists windows to show at start ("inventory,character"). */
world_gfx *world_gfx_open(const char *movie_dir, const char *game_root, int width, int height, double scale,
                          int shared, const char *open, char *error, size_t error_size);
void world_gfx_close(world_gfx *g);
/* 1 when the interface took the event. */
int world_gfx_event(world_gfx *g, const SDL_Event *e, double scale);
/* Advance by dt and, with draw, composite over the current GL framebuffer. */
void world_gfx_frame(world_gfx *g, double dt_ms, int draw);
/* One summary line (JSON object body) for the run report. */
void world_gfx_report(world_gfx *g, char *out, size_t cap);

#endif
