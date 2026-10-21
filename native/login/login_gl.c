/* OpenGL drawing of the native login scene (NATIVE-LOGIN-001). See login_gl.h. */
#include "login_gl.h"

#include <stdlib.h>
#include <string.h>

#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

#include "../core/mu_effect.h"
#include "../core/mu_perf.h"
#include "../core/mu_scene.h"
#include "../viewer/gl_backend.h"
#include "../viewer/gl_batch.h"

struct mu_login_gl {
    mu_login_session *s;
    GLuint tiles[MU_WORLD_BITMAPS], extras[MU_WORLD_EXTRA];
    mu_gl_backend object_gl[MU_OBJECT_TYPES];
    mu_gl_backend particle_gl;   /* NATIVE-JOINT-001: the particle module's bitmaps */
    mu_gl_batch *batch;          /* NATIVE-PERF-001: terrain and objects (NULL: MU_NO_GL_BATCH=1) */
};

static const uint8_t black[4] = {0, 0, 0, 255};

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
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, image->width, image->height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image->rgba);
    return name;
}

mu_login_gl *mu_login_gl_setup(mu_login_session *s)
{
    mu_login_gl *g = calloc(1, sizeof *g);
    if (!g)
        return NULL;
    g->s = s;
    g->batch = mu_perf_batching() ? mu_gl_batch_new() : NULL;
    const mu_world *map = s->map;
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        g->tiles[i] = map->bitmaps[i].width > 0 ? upload(&map->bitmaps[i], map->bitmap_linear[i], 0) : 0;
    for (int32_t i = 0; i < MU_WORLD_EXTRA; ++i)
        g->extras[i] = map->extra[i].width > 0 ? upload(&map->extra[i], map->extra_linear[i], map->extra_clamp[i]) : 0;
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t)
        if (s->has_objects && s->objects.models[t] && s->objects.models[t]->loaded)
            mu_gl_upload(&g->object_gl[t], &s->objects.models[t]->textures, 0);
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t)
        g->object_gl[t].batch = g->batch;
    if (s->has_particles)
        mu_gl_upload(&g->particle_gl, &s->particles.bitmaps, 0);
    return g;
}

void mu_login_gl_teardown(mu_login_gl *g)
{
    if (!g)
        return;
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        if (g->tiles[i])
            glDeleteTextures(1, &g->tiles[i]);
    for (int32_t i = 0; i < MU_WORLD_EXTRA; ++i)
        if (g->extras[i])
            glDeleteTextures(1, &g->extras[i]);
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t)
        if (g->object_gl[t].textures)
            mu_gl_release(&g->object_gl[t]);
    if (g->particle_gl.textures)
        mu_gl_release(&g->particle_gl);
    mu_gl_batch_free(g->batch);
    free(g);
}

/* ---- terrain sink (as mu-charsel / mu-world) ---- */

static void g_state(void *c, int32_t state, int32_t argument)
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
    mu_login_gl *g = c;
    const mu_world *map = g->s->map;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    GLuint name = i >= 0 && i < MU_WORLD_BITMAPS ? g->tiles[i] : 0;
    for (int32_t k = 0; !name && k < MU_WORLD_EXTRA; ++k)
        if (map->extra[k].width > 0 && map->extra_id[k] == texture)
            name = g->extras[k];
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
static void g_c4(void *c, float r, float g, float b, float a) { (void)c; glColor4f(r, g, b, a); }
static void g_v(void *c, const float xyz[3]) { (void)c; glVertex3fv(xyz); }

/* NATIVE-PERF-001: the same terrain stream through the batch. */
static void gb_state(void *c, int32_t state, int32_t argument)
{
    mu_gl_batch *b = ((mu_login_gl *)c)->batch;
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
    mu_login_gl *g = c;
    const mu_world *map = g->s->map;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    GLuint name = i >= 0 && i < MU_WORLD_BITMAPS ? g->tiles[i] : 0;
    for (int32_t k = 0; !name && k < MU_WORLD_EXTRA; ++k)
        if (map->extra[k].width > 0 && map->extra_id[k] == texture)
            name = g->extras[k];
    mu_gl_batch_enable(g->batch, GL_TEXTURE_2D, name != 0);
    if (name)
        mu_gl_batch_bind_texture(g->batch, name);
}

static void gb_begin(void *c, int32_t mode)
{
    mu_gl_batch_begin(((mu_login_gl *)c)->batch, mode == MU_TERRAIN_GL_QUADS ? GL_QUADS : GL_TRIANGLE_FAN);
}
static void gb_end(void *c) { mu_gl_batch_end(((mu_login_gl *)c)->batch); }
static void gb_tex(void *c, float s, float t) { mu_gl_batch_texcoord(((mu_login_gl *)c)->batch, s, t); }
static void gb_c3(void *c, const float rgb[3])
{
    mu_gl_batch_color4(((mu_login_gl *)c)->batch, rgb[0], rgb[1], rgb[2], 1.0f);
}
static void gb_c4(void *c, float r, float g, float b, float a) { mu_gl_batch_color4(((mu_login_gl *)c)->batch, r, g, b, a); }
static void gb_v(void *c, const float xyz[3]) { mu_gl_batch_vertex(((mu_login_gl *)c)->batch, xyz); }

static int particle_backend(void *context, const mu_world_particles *p, mu_render_backend *out)
{
    mu_login_gl *g = context;
    (void)p;
    mu_gl_backend_bind(&g->particle_gl, out);
    return 0;
}

/* RenderSprites(0) / RenderParticles(0) through the reconstructed particle module (NATIVE-JOINT-001). */
static void sprites_and_particles(mu_login_gl *g, mu_login_session *s)
{
    if (!s->has_particles)
        return;
    mu_world_particles_target target = {g, particle_backend};
    s->billboards = mu_world_particles_draw(&s->particles, s->frame->view.modelview, &target);
    glBindTexture(GL_TEXTURE_2D, 0);
    glDepthMask(GL_TRUE);
    glDisable(GL_BLEND);
    glDisable(GL_ALPHA_TEST);
}

long mu_login_gl_draw(mu_login_gl *g, mu_login_session *s, int32_t width, int32_t height)
{
    const mu_client_view *v = &s->frame->view;
    mu_gl_frame(width, height, black, v->modelview, v->projection);   /* glClearColor(0, 0, 0, 1) */
    if (!s->draw_3d)
        return 0;
    glViewport(v->gl_viewport[0], v->gl_viewport[1], v->gl_viewport[2], v->gl_viewport[3]);
    glEnable(GL_DEPTH_TEST);
    glFrontFace(GL_CCW);
    mu_terrain_sink sink = {g, g_state, g_bind, g_begin, g_tex, g_c3, g_c4, g_v, g_end};
    if (g->batch) {   /* NATIVE-PERF-001 */
        mu_terrain_sink batched = {g, gb_state, gb_bind, gb_begin, gb_tex, gb_c3, gb_c4, gb_v, gb_end};
        sink = batched;
        mu_gl_batch_session_begin(g->batch);
    }
    mu_terrain_scene scene;
    mu_world_scene(s->map, &scene);
    mu_terrain_tile_stats stats;
    memset(&stats, 0, sizeof stats);
    mu_terrain_render(&scene, &s->frustum, MU_LOGIN_SCENE, 0, mu_terrain_alpha_layers(s->map->world), &sink, &stats);
    if (g->batch)
        mu_gl_batch_session_end(g->batch);
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    s->objects_drawn = s->after_meshes = s->billboards = 0;
    if (!s->has_objects)
        return stats.faces;
    mu_objects *o = &s->objects;
    const uint64_t sprites = s->particles.stats.sprites_created;
    if (g->batch)
        mu_gl_batch_session_begin(g->batch);
    mu_objects_visibility(o, &s->frustum, MU_LOGIN_SCENE);   /* RenderObjects 0x016d5020 */
    for (int32_t k = 0; k < o->rt.draw_count; ++k) {
        mu_draw_options options;
        mu_object_model *m = mu_objects_prepare(o, k, s->map, MU_LOGIN_SCENE, &options);
        if (!m)
            continue;
        mu_render_backend backend;
        mu_gl_backend_bind(&g->object_gl[m->type], &backend);
        mu_draw_stats ds = {0, 0, 0, 0};
        if (!mu_scene_draw_model(&m->model, &options, &backend, &ds))
            ++s->objects_drawn;
    }
    mu_objects_after_visibility(o, &s->frustum, MU_LOGIN_SCENE);   /* RenderObjects_AfterCharacter 0x016d6949 */
    for (int32_t k = 0; k < o->rt.after_count; ++k) {
        mu_object_mesh meshes[MU_LOGIN_MESHES];
        int32_t count = 0;
        mu_object_model *m = mu_objects_prepare_after(o, k, s->map, MU_LOGIN_SCENE, meshes, MU_LOGIN_MESHES, &count);
        if (!m)
            continue;
        mu_render_backend backend;
        mu_gl_backend_bind(&g->object_gl[m->type], &backend);
        for (int32_t j = 0; j < count; ++j) {
            meshes[j].options.fields = &meshes[j].fields;
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&m->model, &meshes[j].options, &backend, &ds))
                ++s->after_meshes;
        }
    }
    if (g->batch)
        mu_gl_batch_session_end(g->batch);
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    s->frame_sprites = (int32_t)(s->particles.stats.sprites_created - sprites);
    sprites_and_particles(g, s);   /* RenderSprites(0) / RenderParticles(0) */
    return stats.faces;
}
