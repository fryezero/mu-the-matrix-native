#ifndef WORLD_GFX_SOCIAL_H
#define WORLD_GFX_SOCIAL_H
#include "../core/mu_social.h"
struct mu_gfx_layer;
typedef struct world_gfx_social world_gfx_social;
world_gfx_social *world_gfx_social_open(struct mu_gfx_layer *, mu_social_session *);
void world_gfx_social_close(world_gfx_social *);
void world_gfx_social_frame(world_gfx_social *);
int world_gfx_social_action(world_gfx_social *, const char *, const char *);
#endif
