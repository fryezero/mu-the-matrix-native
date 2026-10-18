/* mu-charsel's session as a module (NATIVE-SHELL-001). See charsel_embed.h.
 *
 * charsel/main.c is compiled here unchanged (its tool entry stays unused). */
#define MU_CHARSEL_TOOL_ONLY 1
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "main.c"
#pragma GCC diagnostic pop

#include "charsel_embed.h"

struct mu_charsel_embed {
    app a;
};

mu_charsel_embed *mu_charsel_embed_open(const mu_charsel_embed_config *c, char *error, size_t error_size)
{
    mu_charsel_embed *e = calloc(1, sizeof *e);
    if (!e) {
        snprintf(error, error_size, "out of memory");
        return NULL;
    }
    app *a = &e->a;
    a->root = c->root;
    a->list_path = c->list_path;
    a->objects_dir = c->objects_dir;
    a->width = c->width;
    a->height = c->height;
    a->slot = c->slot;
    a->no_ui = 1;          /* the 2D layer belongs to the front end (core/mu_charsel_ui) */
    a->font = "Tahoma";
    a->backend = "soft";
    if (load(a)) {
        snprintf(error, error_size, "character select did not load%s%s", a->s && a->s->error[0] ? ": " : "",
                 a->s ? a->s->error : "");
        unload(a);
        free(e);
        return NULL;
    }
    return e;
}

void mu_charsel_embed_close(mu_charsel_embed *e)
{
    if (!e)
        return;
    if (e->a.has_objects)
        mu_objects_free(&e->a.objects);
    unload(&e->a);
    free(e);
}

mu_charsel_session *mu_charsel_embed_session(mu_charsel_embed *e)
{
    return e->a.s;
}

void mu_charsel_embed_select_next(mu_charsel_embed *e, int step)
{
    select_next(&e->a, step);
}

long mu_charsel_embed_draw_soft(mu_charsel_embed *e, mu_raster *raster)
{
    return draw_soft(&e->a, raster);
}

#ifndef MU_CHARSEL_NO_GL
int mu_charsel_embed_gl_setup(mu_charsel_embed *e)
{
    gl_setup(&e->a);
    return 0;
}

void mu_charsel_embed_gl_teardown(mu_charsel_embed *e)
{
    gl_teardown(&e->a);
}

long mu_charsel_embed_draw_gl(mu_charsel_embed *e, int32_t width, int32_t height)
{
    return draw_gl(&e->a, width, height);
}
#endif
