/* CHARSEL-RT-001: shared scene-5 asset and render lifetime. */
#include "charsel_rt_internal.h"

static const mu_charsel_part_ops *const parts[] = {
#define MU_CHARSEL_PART(id) &mu_charsel_##id##_part,
#include "parts.def"
#undef MU_CHARSEL_PART
};
#define PART_COUNT (sizeof parts / sizeof parts[0])
static const uint8_t sky[4] = {0, 0, 0, 255};

void mu_charsel_rt_default_options(mu_charsel_rt_options *o)
{
    memset(o, 0, sizeof *o);
    o->width = 1280;
    o->height = 800;
    o->slot = -1;
    o->font = "Tahoma";
}

mu_charsel_rt *mu_charsel_rt_open(const mu_charsel_rt_options *o, char *error, size_t error_size)
{
    mu_charsel_rt *a = calloc(1, sizeof *a);
    if (!a) {
        snprintf(error, error_size, "out of memory");
        return NULL;
    }
    a->options = *o;
    for (size_t i = 0; i < PART_COUNT; ++i) {
        if (parts[i]->open && parts[i]->open(a)) {
            snprintf(error, error_size, "character select did not load%s%s", a->s && a->s->error[0] ? ": " : "",
                     a->s ? a->s->error : "");
            /* Close the failed part too: its allocation may have partially succeeded. */
            for (size_t j = i + 1; j > 0; --j)
                if (parts[j - 1]->close)
                    parts[j - 1]->close(a);
            free(a);
            return NULL;
        }
    }
    return a;
}

void mu_charsel_rt_close(mu_charsel_rt *a)
{
    if (!a)
        return;
    for (size_t i = PART_COUNT; i > 0; --i)
        if (parts[i - 1]->close)
            parts[i - 1]->close(a);
    free(a);
}

mu_charsel_session *mu_charsel_rt_session(mu_charsel_rt *a)
{
    return a->s;
}

void mu_charsel_rt_select_next(mu_charsel_rt *a, int step)
{
    mu_charsel_session *s = a->s;
    int32_t i = mu_charsel_entry_of(s, s->selected);
    i = (i + step + s->list.count) % s->list.count;
    mu_charsel_select(s, s->list.entries[i].slot);
}

void mu_charsel_rt_resize(mu_charsel_rt *a, int32_t width, int32_t height)
{
    a->options.width = width;
    a->options.height = height;
    mu_frame_world *f = &a->s->frame;
    f->view.window_width = (uint32_t)width;
    f->view.window_height = (uint32_t)height;
    f->mouse.scale_x = (float)width / 640.0f;
    f->mouse.scale_y = (float)height / 480.0f;
}

static void begin_draw(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_charsel_frustum(a->s, &d->frustum);
    a->s->objects_drawn = a->s->after_meshes = a->s->billboards = a->s->shadows = 0;
    a->objects_drawn = 0;
    d->sprites = a->s->particles.stats.sprites_created;
}

long mu_charsel_rt_draw_soft(mu_charsel_rt *a, mu_raster *raster)
{
    const mu_client_view *v = &a->s->frame.view;
    memcpy(raster->view, v->modelview, sizeof raster->view);
    memcpy(raster->projection, v->projection, sizeof raster->projection);
    mu_raster_clear(raster, sky);
    mu_charsel_draw d = {0};
    d.raster = raster;
    mu_raster_backend(raster, &d.backend);
    begin_draw(a, &d);
    for (size_t i = 0; i < PART_COUNT; ++i)
        if (parts[i]->draw_soft)
            parts[i]->draw_soft(a, &d);
    return d.faces;
}

#ifndef MU_CHARSEL_NO_GL
int mu_charsel_rt_gl_setup(mu_charsel_rt *a)
{
    for (size_t i = 0; i < PART_COUNT; ++i)
        if (parts[i]->gl_setup)
            parts[i]->gl_setup(a);
    a->gl_ready = 1;
    return 0;
}

void mu_charsel_rt_gl_teardown(mu_charsel_rt *a)
{
    if (!a->gl_ready)
        return;
    for (size_t i = 0; i < PART_COUNT; ++i)
        if (parts[i]->gl_teardown)
            parts[i]->gl_teardown(a);
    mu_gl_batch_free(a->terrain.batch);
    a->terrain.batch = NULL;
    a->gl_ready = 0;
}

long mu_charsel_rt_draw_gl(mu_charsel_rt *a, int32_t width, int32_t height)
{
    const mu_client_view *v = &a->s->frame.view;
    mu_gl_frame(width, height, sky, v->modelview, v->projection);
    glViewport(v->gl_viewport[0], v->gl_viewport[1], v->gl_viewport[2], v->gl_viewport[3]);
    glEnable(GL_DEPTH_TEST);
    glFrontFace(GL_CCW);
    mu_charsel_draw d = {0};
    begin_draw(a, &d);
    for (size_t i = 0; i < PART_COUNT; ++i)
        if (parts[i]->draw_gl)
            parts[i]->draw_gl(a, &d);
    return d.faces;
}
#endif
