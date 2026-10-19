/* mu-world's session as a module (NATIVE-SHELL-001). See world_embed.h.
 *
 * world/main.c is compiled here unchanged: its main becomes
 * mu_world_cli_main (unused) and its static routines are wrapped below. */
#define main mu_world_cli_main
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "main.c"
#pragma GCC diagnostic pop
#undef main

#include "world_embed.h"

int mu_world_cli_main(int argc, char **argv);

struct mu_world_embed {
    app a;
};

mu_world_embed *mu_world_embed_open(const mu_world_embed_config *c, char *error, size_t error_size)
{
    mu_world_embed *e = calloc(1, sizeof *e);
    if (!e) {
        snprintf(error, error_size, "out of memory");
        return NULL;
    }
    app *a = &e->a;
    a->root = c->root;
    a->world = c->world;
    a->class_byte = c->class_byte;
    a->tile[0] = c->tile[0];
    a->tile[1] = c->tile[1];
    a->angle = c->angle;
    a->width = c->width;
    a->height = c->height;
    a->near_plane = c->near_plane > 0.0f ? c->near_plane : 20.0f;
    a->sound_table = c->sound_table;
    a->audio = c->audio;
    a->audio_rate = c->audio_rate > 0 ? c->audio_rate : 44100;
    a->placement = c->placement;
    a->objects_dir = c->objects_dir;
    a->quiet = c->quiet;
    a->hero_name = c->hero_name;
    a->backend = "soft";
    a->pause = 8;
    if (load(a)) {
        snprintf(error, error_size, "world %d did not load (see the messages above)", c->world);
        unload(a);
        free(e);
        return NULL;
    }
    /* the chosen character's equipment (mu-world itself shows the class parts only) */
    for (int i = 1; i < MU_CHARACTER_ITEMS; ++i) {
        if (!c->items[i] || !c->items[i][0])
            continue;
        if (mu_character_set_item(&a->ch, i, c->items[i], 0, error, error_size)) {
            unload(a);
            free(e);
            return NULL;
        }
    }
    mu_walk_place(&a->walk, &a->ch);
    return e;
}

void mu_world_embed_close(mu_world_embed *e)
{
    if (!e)
        return;
    unload(&e->a);
    free(e);
}

void mu_world_embed_message(mu_world_embed *e, uint32_t message, uint32_t wparam, uint32_t lparam)
{
    mu_walk_message(&e->a.walk, message, wparam, lparam);
}

void mu_world_embed_key(mu_world_embed *e, int vk, int down)
{
    mu_walk_key(&e->a.walk, vk, down);
}

void mu_world_embed_resize(mu_world_embed *e, int32_t width, int32_t height)
{
    app *a = &e->a;
    a->width = width;
    a->height = height;
    a->walk.frame.view.window_width = (uint32_t)width;
    a->walk.frame.view.window_height = (uint32_t)height;
    a->walk.frame.mouse.scale_x = (float)width / 640.0f;
    a->walk.frame.mouse.scale_y = (float)height / 480.0f;
}

void mu_world_embed_set_clock(mu_world_embed *e, uint32_t now)
{
    e->a.walk.frame.clock.frame_tick = now;
    e->a.audio_start = now;
}

int32_t mu_world_embed_advance(mu_world_embed *e, uint32_t now)
{
    return advance(&e->a, now);
}

int32_t mu_world_embed_end_frame(mu_world_embed *e)
{
    int32_t sleep = mu_walk_end_render(&e->a.walk);
    sound_frame(&e->a);   /* after the cap, as 0x0185280c in the frame driver */
    return sleep;
}

long mu_world_embed_draw_soft(mu_world_embed *e, mu_raster *raster)
{
    return draw_soft(&e->a, raster);
}

#ifndef MU_WORLD_NO_GL
int mu_world_embed_gl_setup(mu_world_embed *e)
{
    gl_setup(&e->a);
    return 0;
}

void mu_world_embed_gl_teardown(mu_world_embed *e)
{
    gl_teardown(&e->a);
}

long mu_world_embed_draw_gl(mu_world_embed *e, int32_t width, int32_t height)
{
    return draw_gl(&e->a, width, height);
}
#endif

int mu_world_embed_has_sound(const mu_world_embed *e)
{
    return e->a.has_sound;
}

uint32_t mu_world_embed_sound_rate(const mu_world_embed *e)
{
    return e->a.has_sound ? mu_world_sound_rate(&e->a.sound) : 44100u;
}

void mu_world_embed_mix(mu_world_embed *e, float *out, uint32_t frames)
{
    if (e->a.has_sound)
        mu_world_sound_mix(&e->a.sound, out, frames);
    else
        memset(out, 0, (size_t)frames * 2 * sizeof *out);
}

const mu_walk *mu_world_embed_walk(const mu_world_embed *e)
{
    return &e->a.walk;
}

int32_t mu_world_embed_folder(const mu_world_embed *e)
{
    return e->a.map ? e->a.map->report.folder : -1;
}

#ifndef MU_WORLD_NO_GL
void mu_world_embed_set_gfx(mu_world_embed *e, struct world_gfx *gfx, double scale)
{
    e->a.gfx = gfx;
    if (gfx)
        names_gfx_attach(&e->a, scale);
    else if (e->a.names)
        mu_names_set_sink(&e->a.names->names, NULL);
}
#endif
