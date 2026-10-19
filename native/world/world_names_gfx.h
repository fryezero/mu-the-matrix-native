/* hudPlayerName through the GFx layer (NATIVE-NAMES-001).
 *
 * With --gfx and the base movie, the overhead names, HP bars and chat
 * bubbles are drawn by the client's own movie: core/mu_names' operations
 * become the calls the client's handler makes (addInfo/removeInfo on the
 * movie, setHp/setHpShow/setGuildName/... on the clip's _info,
 * setTopMovie/setMessage on the clip, display-info changes as _x/_y/_visible).
 * The clip paths follow the movie's naming (playerContainer.ply_<key>,
 * container.mon_<key>) instead of the addMC event's clip value.  Positions
 * are window pixels divided by the Retina scale (the movies lay out in
 * points).  The movie loads asynchronously: when its channel appears, the
 * plates created so far are replayed (layer choice). */
#ifndef WORLD_NAMES_GFX_H
#define WORLD_NAMES_GFX_H

#include "../core/mu_names.h"
#include "world_gfx.h"

typedef struct world_names_gfx {
    struct mu_gfx_layer *layer;
    mu_names *names;
    double scale;
    char path[192];
    int bound;
    long calls;
    int probe;
} world_names_gfx;

void world_names_gfx_attach(world_names_gfx *b, world_gfx *g, mu_names *names, double scale);
/* Per frame (before the names update): binds when the movie's channel exists. */
void world_names_gfx_frame(world_names_gfx *b);
/* 1 while the movie draws the names (the stand-in stays off). */
int world_names_gfx_active(const world_names_gfx *b);

#endif
