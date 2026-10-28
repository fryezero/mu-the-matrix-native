#ifndef WORLD_GFX_HELP_H
#define WORLD_GFX_HELP_H
struct mu_gfx_layer;
struct mu_lang;
/* One-time installed HelpWindow load. Returns 1 when Ctrl+H may open it. */
int world_gfx_help_load(struct mu_gfx_layer *, const char *game_root, const struct mu_lang *);
#endif
