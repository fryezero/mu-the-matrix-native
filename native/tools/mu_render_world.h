#ifndef MU_RENDER_WORLD_H
#define MU_RENDER_WORLD_H

#include "../core/mu_options.h"

/* Strips the world-mode options (--world-render, --item-level SLOT=L, --excellent SLOT=1,
 * --ancient SLOT=BITS, --item-type SLOT=TYPE, --kind-a/--kind-b/--item-kind SLOT=V,
 * --glow-color R,G,B, --quality Q, --world-time MS, --safe-zone, --attachments,
 * --actor-weapon N=PATH, --actor-weapon-level N=L) from argv. */
int mu_render_world_args(int *argc, char **argv);
int mu_render_world_active(void);
int mu_render_world_character(const mu_options *options);
int mu_render_world_actor(const mu_options *options);

#endif
