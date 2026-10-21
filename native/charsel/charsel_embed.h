#ifndef MU_CHARSEL_EMBED_H
#define MU_CHARSEL_EMBED_H

/* mu-charsel's scene-5 session as a module for other front ends
 * (NATIVE-SHELL-001: mu-client's character select). charsel_embed.c
 * compiles charsel/main.c unchanged into its own translation unit and exposes
 * its loader and draw routines; the session itself is core/mu_charsel.
 * Built with MU_CHARSEL_NO_GL for the software-only tools. */

#include <stddef.h>
#include <stdint.h>

#include "../core/mu_charsel.h"
#include "../core/mu_raster.h"

typedef struct mu_charsel_embed mu_charsel_embed;

typedef struct mu_charsel_embed_config {
    const char *root;
    const char *list_path;     /* character list file (mu_charsel_list_parse format), NULL: built-in list */
    const char *objects_dir;   /* local decoded EncTerrain94.plain (objects and markers), may be NULL */
    int32_t width, height;
    int32_t slot;              /* initial selection, -1: the scene's default */
    const mu_charsel_list *list;   /* NATIVE-CHARCREATE-001: the characters (overrides list_path), may be NULL */
} mu_charsel_embed_config;

mu_charsel_embed *mu_charsel_embed_open(const mu_charsel_embed_config *config, char *error, size_t error_size);
void mu_charsel_embed_close(mu_charsel_embed *e);
mu_charsel_session *mu_charsel_embed_session(mu_charsel_embed *e);
void mu_charsel_embed_select_next(mu_charsel_embed *e, int step);
long mu_charsel_embed_draw_soft(mu_charsel_embed *e, mu_raster *raster);
#ifndef MU_CHARSEL_NO_GL
int mu_charsel_embed_gl_setup(mu_charsel_embed *e);
void mu_charsel_embed_gl_teardown(mu_charsel_embed *e);
long mu_charsel_embed_draw_gl(mu_charsel_embed *e, int32_t width, int32_t height);
#endif

#endif
