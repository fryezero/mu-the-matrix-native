#include "../charsel_rt_internal.h"

static void draw_soft(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_charsel_session *s = a->s;
    mu_raster *raster = d->raster;
    mu_world_draw_stats stats;
    memset(&stats, 0, sizeof stats);
    mu_world_draw_raster_view(s->map, raster, &d->frustum, MU_CHARSEL_SCENE, 0, &stats);   /* RenderTerrain(0) */
    d->faces = stats.tiles.faces;
    d->linear = raster->linear; /* restore the state left by terrain, as main.c did */
}

#ifndef MU_CHARSEL_NO_GL
void charsel_gl_state(void *c, int32_t state, int32_t argument)
{
    (void)c;
    mu_meshdraw_state s;
    mu_world_state(state, argument, &s);
    if (s.blend) {
        glEnable(GL_BLEND);
        glBlendFunc((GLenum)s.src, (GLenum)s.dst);
    } else {
        glDisable(GL_BLEND);
    }
    if (s.cull)
        glEnable(GL_CULL_FACE);
    else
        glDisable(GL_CULL_FACE);
    glDepthMask(s.depth_mask ? GL_TRUE : GL_FALSE);
    if (s.alpha_test)
        glEnable(GL_ALPHA_TEST);
    else
        glDisable(GL_ALPHA_TEST);
}

static void g_bind(void *c, int32_t texture)
{
    mu_charsel_rt *a = c;
    const mu_world *map = a->s->map;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    GLuint name = i >= 0 && i < MU_WORLD_BITMAPS ? a->terrain.tiles[i] : 0;
    for (int32_t k = 0; !name && k < MU_WORLD_EXTRA; ++k)
        if (map->extra[k].width > 0 && map->extra_id[k] == texture)
            name = a->terrain.extras[k];
    if (name) {
        glEnable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, name);
    } else {
        glDisable(GL_TEXTURE_2D);
    }
}

static void g_begin(void *c, int32_t mode)
{
    (void)c;
    glBegin(mode == MU_TERRAIN_GL_QUADS ? GL_QUADS : GL_TRIANGLE_FAN);
}
static void g_end(void *c) { (void)c; glEnd(); }
static void g_tex(void *c, float s, float t) { (void)c; glTexCoord2f(s, t); }
static void g_c3(void *c, const float rgb[3]) { (void)c; glColor3fv(rgb); }
static void g_c4(void *c, float r, float g, float b, float al) { (void)c; glColor4f(r, g, b, al); }
static void g_v(void *c, const float xyz[3]) { (void)c; glVertex3fv(xyz); }

/* NATIVE-PERF-001: the same terrain stream through the batch. */
static void gb_state(void *c, int32_t state, int32_t argument)
{
    mu_gl_batch *b = ((mu_charsel_rt *)c)->terrain.batch;
    mu_meshdraw_state s;
    mu_world_state(state, argument, &s);
    mu_gl_batch_enable(b, GL_BLEND, s.blend);
    if (s.blend)
        mu_gl_batch_blend_func(b, (uint32_t)s.src, (uint32_t)s.dst);
    mu_gl_batch_enable(b, GL_CULL_FACE, s.cull);
    mu_gl_batch_depth_mask(b, s.depth_mask);
    mu_gl_batch_enable(b, GL_ALPHA_TEST, s.alpha_test);
}

static void gb_bind(void *c, int32_t texture)
{
    mu_charsel_rt *a = c;
    const mu_world *map = a->s->map;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    GLuint name = i >= 0 && i < MU_WORLD_BITMAPS ? a->terrain.tiles[i] : 0;
    for (int32_t k = 0; !name && k < MU_WORLD_EXTRA; ++k)
        if (map->extra[k].width > 0 && map->extra_id[k] == texture)
            name = a->terrain.extras[k];
    mu_gl_batch_enable(a->terrain.batch, GL_TEXTURE_2D, name != 0);
    if (name)
        mu_gl_batch_bind_texture(a->terrain.batch, name);
}

static void gb_begin(void *c, int32_t mode)
{
    mu_gl_batch_begin(((mu_charsel_rt *)c)->terrain.batch, mode == MU_TERRAIN_GL_QUADS ? GL_QUADS : GL_TRIANGLE_FAN);
}
static void gb_end(void *c) { mu_gl_batch_end(((mu_charsel_rt *)c)->terrain.batch); }
static void gb_tex(void *c, float s, float t) { mu_gl_batch_texcoord(((mu_charsel_rt *)c)->terrain.batch, s, t); }
static void gb_c3(void *c, const float rgb[3]) { mu_gl_batch_color4(((mu_charsel_rt *)c)->terrain.batch, rgb[0], rgb[1], rgb[2], 1.0f); }
static void gb_c4(void *c, float r, float g, float b, float al) { mu_gl_batch_color4(((mu_charsel_rt *)c)->terrain.batch, r, g, b, al); }
static void gb_v(void *c, const float xyz[3]) { mu_gl_batch_vertex(((mu_charsel_rt *)c)->terrain.batch, xyz); }

static GLuint upload(const mu_image *image, int linear, int clamp)
{
    GLuint name = 0;
    glGenTextures(1, &name);
    glBindTexture(GL_TEXTURE_2D, name);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    GLint filter = linear ? GL_LINEAR : GL_NEAREST;
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, clamp ? GL_CLAMP : GL_REPEAT);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, clamp ? GL_CLAMP : GL_REPEAT);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, image->width, image->height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image->rgba);
    return name;
}


void charsel_terrain_sink(mu_charsel_rt *a, mu_terrain_sink *sink)
{
    *sink = (mu_terrain_sink){a, charsel_gl_state, g_bind, g_begin, g_tex, g_c3, g_c4, g_v, g_end};
}
static void draw_gl(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_charsel_session *s = a->s;
    mu_terrain_sink sink = {a, charsel_gl_state, g_bind, g_begin, g_tex, g_c3, g_c4, g_v, g_end};
    mu_terrain_scene scene;
    mu_world_scene(s->map, &scene);
    mu_terrain_tile_stats stats;
    memset(&stats, 0, sizeof stats);
    if (a->terrain.batch) {   /* NATIVE-PERF-001: the terrain through the batch (the decals below stay immediate) */
        mu_terrain_sink batched = {a, gb_state, gb_bind, gb_begin, gb_tex, gb_c3, gb_c4, gb_v, gb_end};
        mu_gl_batch_session_begin(a->terrain.batch);
        mu_terrain_render(&scene, &d->frustum, MU_CHARSEL_SCENE, 0, mu_terrain_alpha_layers(s->map->world), &batched,
                          &stats);
        mu_gl_batch_session_end(a->terrain.batch);
    } else {
        mu_terrain_render(&scene, &d->frustum, MU_CHARSEL_SCENE, 0, mu_terrain_alpha_layers(s->map->world), &sink,
                          &stats);
    }
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    d->faces = stats.faces;
}

static void gl_setup(mu_charsel_rt *a)
{
    const mu_world *map = a->s->map;
    a->terrain.batch = mu_perf_batching() ? mu_gl_batch_new() : NULL;
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        a->terrain.tiles[i] = map->bitmaps[i].width > 0 ? upload(&map->bitmaps[i], map->bitmap_linear[i], 0) : 0;
    for (int32_t i = 0; i < MU_WORLD_EXTRA; ++i)
        a->terrain.extras[i] = map->extra[i].width > 0 ? upload(&map->extra[i], map->extra_linear[i], map->extra_clamp[i]) : 0;
}

static void gl_teardown(mu_charsel_rt *a)
{
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        if (a->terrain.tiles[i])
            glDeleteTextures(1, &a->terrain.tiles[i]);
    for (int32_t i = 0; i < MU_WORLD_EXTRA; ++i)
        if (a->terrain.extras[i])
            glDeleteTextures(1, &a->terrain.extras[i]);
}
#endif

const mu_charsel_part_ops mu_charsel_terrain_part = {
    .draw_soft = draw_soft,
#ifndef MU_CHARSEL_NO_GL
    .draw_gl = draw_gl,
    .gl_setup = gl_setup,
    .gl_teardown = gl_teardown,
#endif
};
