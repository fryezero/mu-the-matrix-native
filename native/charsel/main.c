/* mu-charsel: the character-select scene natively (NATIVE-CHARSEL-001).
 *
 * One window (SDL2 + OpenGL 2.1) or a headless run (CGL/GLX offscreen, or the
 * deterministic software rasterizer) of a scene-5 session (core/mu_charsel):
 * World94's terrain under its camera record, up to five synthetic characters
 * assembled by the character module and placed by the client's slot code, the
 * selected character drawn with the client's selection highlight.
 *
 *   mu-charsel --game-root ROOT [--list FILE] [--slot N] [--marker X,Y[,Z]]
 *              [--width W --height H] [--seconds S]
 *   mu-charsel --game-root ROOT --headless --frames N --out-dir DIR [--backend soft|gl] [--every K]
 *              [--cycle F] [--enter F] [--quiet]
 *
 * --cycle F selects the next list entry every F frames (the GFx list in the
 * client); --enter F presses Enter on frame F (the scene tick then asks for
 * the loading scene, which is reported). In the window: 1..5 select a list
 * entry, Left/Right step through it, Enter is the client's Enter, Esc twice
 * quits, O saves a PNG.
 *
 * Built twice: build/mu-charsel-window (SDL2 + OpenGL) and, with
 * MU_CHARSEL_NO_GL, build/mu-charsel (software only, `make -C native`); the
 * second is also reached as `mu-render charsel`.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifndef MU_CHARSEL_NO_GL
#include <SDL.h>
#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif
#endif

#include "../core/mu_charsel.h"
#include "../core/mu_charsel_ui.h"
#include "../core/mu_objects.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_scene.h"
#include "../core/mu_terrain.h"
#ifndef MU_CHARSEL_NO_GL
#include "../viewer/gl_backend.h"
#include "../viewer/gl_headless.h"
#endif

typedef struct app {
    const char *root, *list_path, *out_dir, *backend, *font, *tip;
    const mu_charsel_list *list_given;   /* NATIVE-CHARCREATE-001: overrides list_path (embed) */
    int32_t width, height, frames, every, headless, quiet, slot, cycle, enter_frame, no_ui;
    mu_charsel_ui *ui;
    float seconds;
    int marker_given;
    float marker[3];
    mu_charsel_list list;
    mu_charsel_session *s;
    /* NATIVE-OBJECTS-001: static objects and markers from a local decoded EncTerrain94.plain */
    const char *objects_dir;
    const char *objects_out;       /* NATIVE-CHARSEL-002: --objects-out FILE, the objects' state after the run */
    mu_objects objects;
    int has_objects;
    long objects_drawn;
#ifndef MU_CHARSEL_NO_GL
    mu_gl_backend object_gl[MU_OBJECT_TYPES];
    GLuint tiles[MU_WORLD_BITMAPS], extras[MU_WORLD_EXTRA];
    mu_gl_backend items[MU_CHARSEL_MAX_ENTRIES][MU_CHARACTER_ITEMS];
    mu_gl_backend particle_gl;                     /* NATIVE-CHARSEL-002: the particle module's bitmaps */
    mu_gl_backend particle_model_gl[MU_WORLD_FX_MODELS];
    int gl_ready;
#endif
} app;

static const int draw_order[MU_CHARACTER_ITEMS] = {5, 4, 3, 2, 1, 0, 6, 7, 8};
static const uint8_t sky[4] = {0, 0, 0, 255};

static char *read_text(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *text = n >= 0 ? malloc((size_t)n + 1) : NULL;
    if (text && fread(text, 1, (size_t)n, f) != (size_t)n) {
        free(text);
        text = NULL;
    }
    if (text)
        text[n] = 0;
    fclose(f);
    return text;
}

static int load(app *a)
{
    char error[512];
    if (a->list_given) {   /* NATIVE-CHARCREATE-001: the caller's list (mu-client's offline session) */
        a->list = *a->list_given;
    } else if (a->list_path) {
        char *text = read_text(a->list_path);
        if (!text) {
            fprintf(stderr, "%s: cannot read\n", a->list_path);
            return 1;
        }
        int status = mu_charsel_list_parse(text, a->root, &a->list, error, sizeof error);
        free(text);
        if (status) {
            fprintf(stderr, "%s: %s\n", a->list_path, error);
            return 1;
        }
    } else {
        mu_charsel_list_default(&a->list);
    }
    a->s = calloc(1, sizeof *a->s);
    if (!a->s)
        return 1;
    float markers[MU_CHARSEL_MARKERS][3];
    for (int k = 0; k < MU_CHARSEL_MARKERS; ++k)
        memcpy(markers[k], a->marker_given ? a->marker : mu_charsel_default_marker1, sizeof markers[k]);
    if (a->objects_dir) {
        mu_objects_init(&a->objects, MU_CHARSEL_WORLD);
        if (mu_objects_load_dir(&a->objects, a->objects_dir, error, sizeof error) != MU_OBJECTS_FILE_OK) {
            fprintf(stderr, "objects: %s\n", error);
            return 1;
        }
        a->has_objects = 1;
        /* marker k is the object of type 13 + k (CreateObject 0x00daa2b2); the last one of a type wins */
        for (int32_t i = 0; i < a->objects.count && !a->marker_given; ++i) {
            int32_t k = a->objects.records[i].type - 13;
            if (k >= 0 && k < MU_CHARSEL_MARKERS)
                memcpy(markers[k], a->objects.records[i].position, sizeof markers[k]);
        }
    }
    if (mu_charsel_init(a->s, a->root, &a->list, (const float(*)[3])markers, (uint32_t)a->width,
                        (uint32_t)a->height, 20.0f)) {
        fprintf(stderr, "%s\n", a->s->error);
        return 1;
    }
    if (a->has_objects) {
        mu_objects_load_models(&a->objects, a->root, 0);
        /* NATIVE-CHARSEL-002: the client's object lifecycle with CGMCharacterScene_Ex */
        if (mu_charsel_attach_objects(a->s, a->root, &a->objects))
            fprintf(stderr, "objects: the lifecycle did not start (static objects are not drawn)\n");
    }
    if (a->slot >= 0) {
        if (mu_charsel_entry_of(a->s, a->slot) < 0) {
            fprintf(stderr, "slot %d is not in the list\n", a->slot);
            return 1;
        }
        mu_charsel_select(a->s, a->slot);
    }
    if (!a->no_ui && a->headless) {
        a->ui = calloc(1, sizeof *a->ui);
        if (!a->ui || mu_charsel_ui_init(a->ui, a->root, a->width, a->height, a->font, a->s, a->tip)) {
            fprintf(stderr, "2D layer initialisation failed\n");
            return 1;
        }
    }
    return 0;
}

static void unload(app *a)
{
    if (a->ui) {
        mu_charsel_ui_free(a->ui);
        free(a->ui);
        a->ui = NULL;
    }
    if (a->s) {
        mu_charsel_free(a->s);
        free(a->s);
        a->s = NULL;
    }
}

static void select_next(app *a, int step)
{
    mu_charsel_session *s = a->s;
    int32_t i = mu_charsel_entry_of(s, s->selected);
    i = (i + step + s->list.count) % s->list.count;
    mu_charsel_select(s, s->list.entries[i].slot);
}

/* ---- software ---- */

#define MU_CHARSEL_AFTER_MESHES 32

/* The drawn character's parts in the client's order, each after its shadow (RenderCharacter 0x01363260: the
 * shadow first, then the parts; the item render's shadow block, NATIVE-CHARSEL-002). */
typedef void (*part_backend_fn)(app *a, int entry, int part, mu_render_backend *out);

static void draw_character(app *a, part_backend_fn part_backend, mu_raster *raster)
{
    mu_charsel_session *s = a->s;
    if (s->draw_entry < 0)
        return;
    mu_draw_options options;
    mu_draw_default_options(&options);
    const mu_character *ch = &s->characters[s->draw_entry];
    for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
        const mu_character_item *item = &ch->items[draw_order[n]];
        if (!item->loaded)
            continue;
        mu_render_backend backend;
        part_backend(a, s->draw_entry, draw_order[n], &backend);
        if (raster) {
            raster->textures = item->textures.slots;
            raster->texture_count = item->textures.count;
            raster->texture_filter = item->textures.filter;
            raster->texture_wrap = item->textures.wrap;
        }
        if (s->has_particles && mu_world_particles_character_shadow(&s->particles, &item->model, &item->bmd, &backend))
            ++s->shadows;
        options.textures = &item->textures;
        mu_draw_stats ds = {0, 0, 0, 0};
        mu_scene_draw_model(&item->model, &options, &backend, &ds);
    }
    if (raster) {
        raster->textures = NULL;
        raster->texture_count = 0;
        raster->texture_filter = NULL;
        raster->texture_wrap = NULL;
    }
}

/* ---- software ---- */

static mu_raster *soft_raster;

static void soft_part_backend(app *a, int entry, int part, mu_render_backend *out)
{
    (void)a;
    (void)entry;
    (void)part;
    mu_raster_backend(soft_raster, out);
}

static void soft_bind(mu_raster *raster, const mu_object_model *m)
{
    raster->textures = m ? m->textures.slots : NULL;
    raster->texture_count = m ? m->textures.count : 0;
    raster->texture_filter = m ? m->textures.filter : NULL;
    raster->texture_wrap = m ? m->textures.wrap : NULL;
}

static long draw_soft(app *a, mu_raster *raster)
{
    mu_charsel_session *s = a->s;
    const mu_client_view *v = &s->frame.view;
    memcpy(raster->view, v->modelview, sizeof raster->view);
    memcpy(raster->projection, v->projection, sizeof raster->projection);
    mu_raster_clear(raster, sky);
    mu_terrain_frustum frustum;
    mu_charsel_frustum(s, &frustum);
    mu_world_draw_stats stats;
    memset(&stats, 0, sizeof stats);
    mu_world_draw_raster_view(s->map, raster, &frustum, MU_CHARSEL_SCENE, 0, &stats);   /* RenderTerrain(0) */
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    const int linear = raster->linear;
    s->objects_drawn = s->after_meshes = s->billboards = s->shadows = 0;
    const uint64_t sprites = s->particles.stats.sprites_created;
    a->objects_drawn = 0;
    if (s->has_objects) {   /* RenderObjects 0x016d5020 with CGMCharacterScene_Ex (NATIVE-CHARSEL-002) */
        mu_objects *o = s->objects;
        raster->linear = 1;
        mu_objects_visibility(o, &frustum, MU_CHARSEL_SCENE);
        for (int32_t k = 0; k < o->rt.draw_count; ++k) {
            mu_draw_options options;
            mu_object_model *m = mu_objects_prepare(o, k, s->map, MU_CHARSEL_SCENE, &options);
            if (!m)
                continue;
            soft_bind(raster, m);
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&m->model, &options, &backend, &ds))
                ++s->objects_drawn;
        }
        soft_bind(raster, NULL);
        a->objects_drawn = s->objects_drawn;
    } else if (a->has_objects) {
        a->objects_drawn = mu_objects_draw_raster(&a->objects, s->map, raster, 0, 0, 255, 255);
    }
    raster->linear = 1;
    raster->front_ccw = 1;
    soft_raster = raster;
    draw_character(a, soft_part_backend, raster);   /* RenderCharacter(shown) */
    if (s->has_particles)   /* RenderEffects 0x015181fa: the effect models */
        mu_world_particles_draw_models_raster(&s->particles, raster);
    if (s->has_objects) {   /* RenderObjects_AfterCharacter 0x016d6949 */
        mu_objects *o = s->objects;
        mu_objects_after_visibility(o, &frustum, MU_CHARSEL_SCENE);
        for (int32_t k = 0; k < o->rt.after_count; ++k) {
            mu_object_mesh meshes[MU_CHARSEL_AFTER_MESHES];
            int32_t count = 0;
            mu_object_model *m = mu_objects_prepare_after(o, k, s->map, MU_CHARSEL_SCENE, meshes,
                                                          MU_CHARSEL_AFTER_MESHES, &count);
            if (!m)
                continue;
            soft_bind(raster, m);
            for (int32_t j = 0; j < count; ++j) {
                meshes[j].options.fields = &meshes[j].fields;
                mu_draw_stats ds = {0, 0, 0, 0};
                if (!mu_scene_draw_model(&m->model, &meshes[j].options, &backend, &ds))
                    ++s->after_meshes;
            }
        }
        soft_bind(raster, NULL);
    }
    raster->linear = linear;
    for (int32_t i = 0; i < s->decal_count; ++i) {
        const mu_charsel_decal *d = &s->decals[i];
        /* EnableAlphaBlend 0x0184aa2b, then RenderTerrainAlphaBitmap(0x8036, x, y, size, size, light,
         * rotation, 1, 5, 1, 0) */
        mu_world_decal_raster(s->map, raster, 0x8036, d->x, d->y, d->size, d->size, d->light, d->rotation, 1.0f, 5.0f,
                              1, 0, MU_TERRAIN_STATE_ADDITIVE);
    }
    if (s->has_particles) {   /* RenderJoints(0), RenderSprites(0), RenderParticles(0) */
        s->frame_sprites = (int32_t)(s->particles.stats.sprites_created - sprites);
        s->billboards = mu_world_particles_draw_raster(&s->particles, raster, v->modelview);
    }
    return stats.tiles.faces;
}

#ifndef MU_CHARSEL_NO_GL
/* ---- OpenGL ---- */

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
    app *a = c;
    const mu_world *map = a->s->map;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    GLuint name = i >= 0 && i < MU_WORLD_BITMAPS ? a->tiles[i] : 0;
    for (int32_t k = 0; !name && k < MU_WORLD_EXTRA; ++k)
        if (map->extra[k].width > 0 && map->extra_id[k] == texture)
            name = a->extras[k];
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

static void gl_setup(app *a)
{
    const mu_world *map = a->s->map;
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        a->tiles[i] = map->bitmaps[i].width > 0 ? upload(&map->bitmaps[i], map->bitmap_linear[i], 0) : 0;
    for (int32_t i = 0; i < MU_WORLD_EXTRA; ++i)
        a->extras[i] = map->extra[i].width > 0 ? upload(&map->extra[i], map->extra_linear[i], map->extra_clamp[i]) : 0;
    for (int e = 0; e < MU_CHARSEL_MAX_ENTRIES; ++e)
        for (int i = 0; i < MU_CHARACTER_ITEMS; ++i) {
            memset(&a->items[e][i], 0, sizeof a->items[e][i]);
            if (a->s->character_loaded[e] && a->s->characters[e].items[i].loaded)
                mu_gl_upload(&a->items[e][i], &a->s->characters[e].items[i].textures, 0);
        }
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t) {
        memset(&a->object_gl[t], 0, sizeof a->object_gl[t]);
        if (a->has_objects && a->objects.models[t] && a->objects.models[t]->loaded)
            mu_gl_upload(&a->object_gl[t], &a->objects.models[t]->textures, 0);
    }
    memset(&a->particle_gl, 0, sizeof a->particle_gl);
    memset(a->particle_model_gl, 0, sizeof a->particle_model_gl);
    if (a->s->has_particles)   /* NATIVE-CHARSEL-002 */
        mu_gl_upload(&a->particle_gl, &a->s->particles.bitmaps, 0);
    a->gl_ready = 1;
}

static void gl_teardown(app *a)
{
    if (!a->gl_ready)
        return;
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        if (a->tiles[i])
            glDeleteTextures(1, &a->tiles[i]);
    for (int32_t i = 0; i < MU_WORLD_EXTRA; ++i)
        if (a->extras[i])
            glDeleteTextures(1, &a->extras[i]);
    for (int e = 0; e < MU_CHARSEL_MAX_ENTRIES; ++e)
        for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
            mu_gl_release(&a->items[e][i]);
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t)
        if (a->object_gl[t].textures)
            mu_gl_release(&a->object_gl[t]);
    if (a->particle_gl.textures)
        mu_gl_release(&a->particle_gl);
    for (int i = 0; i < MU_WORLD_FX_MODELS; ++i)
        if (a->particle_model_gl[i].textures)
            mu_gl_release(&a->particle_model_gl[i]);
    a->gl_ready = 0;
}

static void gl_part_backend(app *a, int entry, int part, mu_render_backend *out)
{
    mu_gl_backend_bind(&a->items[entry][part], out);
}

static int particle_gl_backend(void *context, const mu_world_particles *p, mu_render_backend *out)
{
    app *a = context;
    (void)p;
    mu_gl_backend_bind(&a->particle_gl, out);
    return 0;
}

/* RenderEffects' effect models through the scene draw (NATIVE-JOINT-001's helper). */
static void particle_model_gl(void *context, const mu_model *model, const mu_textures *textures, int32_t slot,
                              const mu_draw_options *draw_options)
{
    app *a = context;
    mu_gl_backend *gl = &a->particle_model_gl[slot];
    if (!gl->textures)
        mu_gl_upload(gl, textures, 0);
    mu_render_backend backend;
    mu_gl_backend_bind(gl, &backend);
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_scene_draw_model(model, draw_options, &backend, &ds);
}

static long draw_gl(app *a, int32_t width, int32_t height)
{
    mu_charsel_session *s = a->s;
    const mu_client_view *v = &s->frame.view;
    mu_gl_frame(width, height, sky, v->modelview, v->projection);
    glViewport(v->gl_viewport[0], v->gl_viewport[1], v->gl_viewport[2], v->gl_viewport[3]);
    glEnable(GL_DEPTH_TEST);
    glFrontFace(GL_CCW);
    mu_terrain_sink sink = {a, g_state, g_bind, g_begin, g_tex, g_c3, g_c4, g_v, g_end};
    mu_terrain_scene scene;
    mu_world_scene(s->map, &scene);
    mu_terrain_tile_stats stats;
    memset(&stats, 0, sizeof stats);
    mu_terrain_frustum frustum;
    mu_charsel_frustum(s, &frustum);
    mu_terrain_render(&scene, &frustum, MU_CHARSEL_SCENE, 0, mu_terrain_alpha_layers(s->map->world), &sink, &stats);
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    a->objects_drawn = 0;
    s->objects_drawn = s->after_meshes = s->billboards = s->shadows = 0;
    const uint64_t sprites = s->particles.stats.sprites_created;
    if (s->has_objects) {   /* RenderObjects 0x016d5020 with CGMCharacterScene_Ex (NATIVE-CHARSEL-002) */
        mu_objects *o = s->objects;
        mu_objects_visibility(o, &frustum, MU_CHARSEL_SCENE);
        for (int32_t k = 0; k < o->rt.draw_count; ++k) {
            mu_draw_options options;
            mu_object_model *m = mu_objects_prepare(o, k, s->map, MU_CHARSEL_SCENE, &options);
            if (!m)
                continue;
            mu_render_backend backend;
            mu_gl_backend_bind(&a->object_gl[m->type], &backend);
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&m->model, &options, &backend, &ds))
                ++s->objects_drawn;
        }
        a->objects_drawn = s->objects_drawn;
    } else if (a->has_objects) {   /* static placement (the lifecycle did not start) */
        mu_draw_options options;
        mu_draw_default_options(&options);
        for (int32_t i = 0; i < a->objects.count; ++i) {
            mu_object_model *m = mu_objects_place(&a->objects, i, s->map);
            if (!m)
                continue;
            mu_render_backend backend;
            mu_gl_backend_bind(&a->object_gl[m->type], &backend);
            options.textures = &m->textures;
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&m->model, &options, &backend, &ds))
                ++a->objects_drawn;
        }
    }
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    draw_character(a, gl_part_backend, NULL);   /* RenderCharacter(shown), each part after its shadow */
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    if (s->has_particles)   /* RenderEffects 0x015181fa: the effect models */
        mu_world_particles_draw_models(&s->particles, particle_model_gl, a);
    if (s->has_objects) {   /* RenderObjects_AfterCharacter 0x016d6949 */
        mu_objects *o = s->objects;
        mu_objects_after_visibility(o, &frustum, MU_CHARSEL_SCENE);
        for (int32_t k = 0; k < o->rt.after_count; ++k) {
            mu_object_mesh meshes[MU_CHARSEL_AFTER_MESHES];
            int32_t count = 0;
            mu_object_model *m = mu_objects_prepare_after(o, k, s->map, MU_CHARSEL_SCENE, meshes,
                                                          MU_CHARSEL_AFTER_MESHES, &count);
            if (!m)
                continue;
            mu_render_backend backend;
            mu_gl_backend_bind(&a->object_gl[m->type], &backend);
            for (int32_t j = 0; j < count; ++j) {
                meshes[j].options.fields = &meshes[j].fields;
                mu_draw_stats ds = {0, 0, 0, 0};
                if (!mu_scene_draw_model(&m->model, &meshes[j].options, &backend, &ds))
                    ++s->after_meshes;
            }
        }
    }
    for (int32_t i = 0; i < s->decal_count; ++i) {
        const mu_charsel_decal *d = &s->decals[i];
        g_state(a, MU_TERRAIN_STATE_ADDITIVE, 1);
        mu_terrain_decal(&scene, 0x8036, d->x, d->y, d->size, d->size, d->light, d->rotation, 1.0f, 5.0f, 1, 0, &sink);
    }
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    if (s->has_particles) {   /* RenderJoints(0), RenderSprites(0), RenderParticles(0) */
        s->frame_sprites = (int32_t)(s->particles.stats.sprites_created - sprites);
        mu_world_particles_target target = {a, particle_gl_backend};
        s->billboards = mu_world_particles_draw(&s->particles, v->modelview, &target);
        glBindTexture(GL_TEXTURE_2D, 0);
        glDepthMask(GL_TRUE);
        glDisable(GL_BLEND);
        glDisable(GL_ALPHA_TEST);
    }
    return stats.faces;
}
#endif

/* ---- reports ---- */

static void report_frame(const app *a, int32_t frame, uint32_t now, const char *hash, const char *png)
{
    const mu_charsel_session *s = a->s;
    const mu_client_view *v = &s->frame.view;
    float pos[3] = {0, 0, 0}, scale = 0;
    int32_t action = -1;
    float anim = 0;
    if (s->draw_entry >= 0) {
        const mu_character *ch = &s->characters[s->draw_entry];
        memcpy(pos, ch->params.position, sizeof pos);
        scale = ch->params.scale;
        action = mu_model_action(&ch->player);
        anim = mu_model_frame(&ch->player);
    }
    printf("{\"frame\": %d, \"tick\": %u, \"steps\": %u, \"selected\": %d, \"shown\": %d, \"drawn_entry\": %d,"
           " \"position\": [%.2f, %.2f, %.2f], \"scale\": %.3f, \"action\": %d, \"frame_anim\": %.3f,"
           " \"decals\": %d, \"particles\": %d, \"enter_requests\": %d, \"fov\": %.3f, \"angle\": [%.2f, %.2f, %.2f],"
           " \"eye\": [%.2f, %.2f, %.2f], \"far\": %.2f, \"objects_drawn\": %ld, \"after_meshes\": %ld,"
           " \"sprites\": %d, \"live_particles\": %u, \"billboards\": %ld, \"shadows\": %ld,"
           " \"effect_models\": %u, \"pick\": %d, \"sha256\": \"%s\", \"png\": \"%s\"}\n",
           frame, now, s->steps, s->selected, s->shown, s->draw_entry, (double)pos[0], (double)pos[1], (double)pos[2],
           (double)scale, action, (double)anim, s->decal_count, s->particles_created, s->enter_requests, (double)v->fov,
           (double)v->angle[0], (double)v->angle[1], (double)v->angle[2], (double)v->position[0],
           (double)v->position[1], (double)v->position[2], (double)v->view_far, s->objects_drawn, s->after_meshes,
           s->frame_sprites, s->particles.stats.live, s->billboards, s->shadows, s->particles.stats.drawn_effect_models,
           s->pick, hash ? hash : "", png ? png : "");
}

static void report_summary(const app *a, const char *renderer)
{
    const mu_charsel_session *s = a->s;
    printf("{\"summary\": true, \"renderer\": \"%s\", \"world\": %d, \"folder\": %d, \"camera_key\": %d,"
           " \"camera_angle\": [%.3f, %.3f, %.3f], \"camera_position\": [%.3f, %.3f, %.3f], \"fov\": %.3f,"
           " \"characters\": %d, \"marker1\": [%.2f, %.2f, %.2f], \"steps\": %u, \"frames\": %u,"
           " \"enter_requests\": %d, \"objects\": %d, \"objects_drawn\": %ld, \"lifecycle\": %d,"
           " \"objects_created\": %d, \"object_steps\": %u, \"particles_created\": %llu, \"sprites_created\": %llu,"
           " \"effects_created\": %llu, \"effects_unsupported\": %llu, \"terrain_lights\": %ld, \"object_models\": %d,"
           " \"object_models_missing\": %d, \"draw_list\": %d, \"after_character\": %d}\n",
           renderer, MU_CHARSEL_WORLD, s->map->report.folder, s->info.key, (double)s->info.angle[0],
           (double)s->info.angle[1], (double)s->info.angle[2], (double)s->info.position[0],
           (double)s->info.position[1], (double)s->info.position[2], (double)s->info.fov, s->list.count,
           (double)s->scene.position[1][0], (double)s->scene.position[1][1], (double)s->scene.position[1][2], s->steps,
           s->frames, s->enter_requests, a->has_objects ? a->objects.count : 0, a->objects_drawn, s->has_objects,
           s->has_objects ? s->objects->rt.created : 0, s->has_objects ? s->objects->rt.steps : 0u,
           (unsigned long long)s->particles.stats.created, (unsigned long long)s->particles.stats.sprites_created,
           (unsigned long long)s->particles.stats.effects_created,
           (unsigned long long)s->particles.stats.effects_unsupported,
           s->has_objects ? s->objects->rt.light_events : 0L, a->has_objects ? a->objects.models_loaded : 0,
           a->has_objects ? a->objects.models_missing : 0, s->has_objects ? s->objects->rt.draw_count : 0,
           s->has_objects ? s->objects->rt.after_count : 0);
    for (int32_t i = 0; i < s->list.count; ++i) {
        const mu_charsel_entry *e = &s->list.entries[i];
        const uint8_t *r = s->records + (size_t)e->slot * MU_CHARSEL_RECORD;
        float scale;
        memcpy(&scale, r + MU_CHARSEL_OBJECT + MU_OBJ_SCALE, sizeof scale);
        uint16_t parts[6];
        for (int k = 0; k < 6; ++k)
            memcpy(&parts[k], r + MU_CHAR_PARTS + MU_CHAR_PART_SIZE * k, 2);
        printf("{\"entry\": %d, \"slot\": %d, \"class\": %u, \"level\": %u, \"name\": \"%s\", \"scale\": %.3f,"
               " \"parts\": [%d, %d, %d, %d, %d, %d], \"stand_action\": %d}\n",
               i, e->slot, e->class_byte, e->level, e->name, (double)scale, (int16_t)parts[0], (int16_t)parts[1],
               (int16_t)parts[2], (int16_t)parts[3], (int16_t)parts[4], (int16_t)parts[5],
               s->character_loaded[i] ? mu_model_action(&s->characters[i].player) : -1);
    }
}

/* ---- headless ---- */

static void press_enter(app *a, int down)
{
    mu_charsel_key(a->s, 0x0d, down);
}

static int headless(app *a)
{
#ifndef MU_CHARSEL_NO_GL
    char error[256];
    int gl = a->backend && !strcmp(a->backend, "gl");
#else
    const int gl = 0;
    if (a->backend && strcmp(a->backend, "soft")) {
        fprintf(stderr, "this build renders with the software rasterizer only (--backend soft)\n");
        return 2;
    }
#endif
    if (a->out_dir && mkdir(a->out_dir, 0755) && errno != EEXIST) {
        fprintf(stderr, "cannot create %s\n", a->out_dir);
        return 1;
    }
#ifndef MU_CHARSEL_NO_GL
    if (gl && mu_gl_headless_begin(a->width, a->height, error, sizeof error)) {
        fprintf(stderr, "headless GL: %s\n", error);
        return 1;
    }
    if (gl)
        gl_setup(a);
#endif
    mu_raster raster;
    memset(&raster, 0, sizeof raster);
    if (!gl && mu_raster_init(&raster, a->width, a->height)) {
        fprintf(stderr, "raster allocation failed\n");
        return 1;
    }
    size_t bytes = (size_t)a->width * (size_t)a->height * 4;
    uint8_t *pixels = malloc(bytes);
    if (!pixels)
        return 1;
    uint32_t now = 100000;
    a->s->frame.clock.frame_tick = now;
    for (int32_t frame = 0; frame < a->frames; ++frame) {
        if (a->cycle > 0 && frame > 0 && frame % a->cycle == 0)
            select_next(a, 1);
        if (frame == a->enter_frame)
            press_enter(a, 1);
        else if (frame == a->enter_frame + 3)
            press_enter(a, 0);
        mu_charsel_update(a->s, now);
        if (a->ui)
            mu_charsel_ui_update(a->ui, a->s, -1000, -1000, 0, 0);
        mu_charsel_begin_render(a->s, now);
        int save = a->out_dir && a->every > 0 && (frame % a->every == 0 || frame == a->frames - 1);
        char hash[65] = "", path[4096] = "";
        if (!save)
            mu_charsel_frame_objects(a->s);   /* the frame's RenderObjects pass without output (NATIVE-CHARSEL-002) */
        if (save) {
            if (gl) {
#ifndef MU_CHARSEL_NO_GL
                draw_gl(a, a->width, a->height);
                glFinish();
                mu_gl_read(a->width, a->height, pixels);
#endif
            } else {
                draw_soft(a, &raster);
                memcpy(pixels, raster.color, bytes);
            }
            if (a->ui)
                mu_charsel_ui_render(a->ui, pixels);   /* the 2D layer over the 3D frame */
            mu_sha256_hex(pixels, bytes, hash);
            snprintf(path, sizeof path, "%s/frame-%04d.png", a->out_dir, frame);
            if (mu_png_write(path, pixels, a->width, a->height)) {
                fprintf(stderr, "cannot write %s\n", path);
                return 1;
            }
        }
        if (!a->quiet && (save || frame == a->frames - 1))
            report_frame(a, frame, now, save ? hash : NULL, save ? path : NULL);
        now += 12;
        int32_t sleep = mu_charsel_end_render(a->s);
        if (sleep > 0)
            now += (uint32_t)sleep;
    }
    if (a->objects_out && a->s->has_objects) {   /* the objects' state for the live comparison (NATIVE-CHARSEL-002) */
        FILE *f = fopen(a->objects_out, "w");
        for (int32_t i = 0; f && i < a->s->objects->count; ++i) {
            const uint8_t *o = mu_objects_object_image(a->s->objects, i);
            if (!o)
                continue;
            fprintf(f, "%d %d %.3f %.3f %.3f %u %u %.6f\n", i, mu_obj_i32(o, MU_OBJF_TYPE),
                    (double)mu_obj_f32(o, MU_OBJF_POSITION), (double)mu_obj_f32(o, MU_OBJF_POSITION + 4),
                    (double)mu_obj_f32(o, MU_OBJF_POSITION + 8), o[MU_OBJF_VISIBLE], o[MU_OBJF_AFTER_CHARACTER],
                    (double)mu_obj_f32(o, MU_OBJF_BLEND_V));
        }
        if (f)
            fclose(f);
    }
#ifndef MU_CHARSEL_NO_GL
    report_summary(a, gl ? mu_gl_renderer() : "software");
    if (gl) {
        gl_teardown(a);
        mu_gl_headless_end();
    }
#else
    report_summary(a, "software");
#endif
    free(pixels);
    if (!gl)
        mu_raster_free(&raster);
    return 0;
}

#ifndef MU_CHARSEL_NO_GL
/* ---- window ---- */

static uint32_t pack(int x, int y)
{
    return ((uint32_t)(uint16_t)y << 16) | (uint16_t)x;
}

static int windowed(app *a)
{
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_Window *window = SDL_CreateWindow("mu-charsel", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, a->width,
                                          a->height, SDL_WINDOW_OPENGL | SDL_WINDOW_ALLOW_HIGHDPI);
    SDL_GLContext context = window ? SDL_GL_CreateContext(window) : NULL;
    if (!context) {
        fprintf(stderr, "SDL: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetSwapInterval(0);
    int dw, dh;
    SDL_GL_GetDrawableSize(window, &dw, &dh);
    double scale = (double)dw / (double)a->width;
    mu_charsel_session *s = a->s;
    s->frame.view.window_width = (uint32_t)dw;
    s->frame.view.window_height = (uint32_t)dh;
    s->frame.mouse.scale_x = (float)dw / 640.0f;
    s->frame.mouse.scale_y = (float)dh / 480.0f;
    gl_setup(a);
    s->frame.clock.frame_tick = SDL_GetTicks();
    uint32_t start = SDL_GetTicks(), frames = 0;
    int running = 1, escapes = 0;
    while (running) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_QUIT) {
                running = 0;
            } else if (e.type == SDL_MOUSEMOTION) {
                mu_charsel_message(s, MU_WM_MOUSEMOVE, 0, pack((int)(e.motion.x * scale), (int)(e.motion.y * scale)));
            } else if (e.type == SDL_KEYDOWN || e.type == SDL_KEYUP) {
                int vk = mu_vk_from_hid((int)e.key.keysym.scancode);
                int down = e.type == SDL_KEYDOWN;
                mu_charsel_key(s, vk, down);
                mu_charsel_message(s, down ? 0x100u : 0x101u, (uint32_t)vk, 0);
                if (down && !e.key.repeat && vk == 0x1b && ++escapes >= 2)
                    running = 0;
                else if (down && vk != 0x1b)
                    escapes = 0;
                if (down && !e.key.repeat && vk >= 0x31 && vk < 0x31 + s->list.count)
                    mu_charsel_select(s, s->list.entries[vk - 0x31].slot);
                if (down && !e.key.repeat && (vk == 0x25 || vk == 0x27))
                    select_next(a, vk == 0x27 ? 1 : -1);
                if (down && !e.key.repeat && vk == 0x4f) {
                    uint8_t *pixels = malloc((size_t)dw * (size_t)dh * 4);
                    if (pixels) {
                        mu_gl_read(dw, dh, pixels);
                        mu_png_write("mu-charsel-screenshot.png", pixels, dw, dh);
                        free(pixels);
                    }
                }
            }
        }
        uint32_t now = SDL_GetTicks();
        mu_charsel_update(s, now);
        mu_charsel_begin_render(s, now);
        draw_gl(a, dw, dh);
        SDL_GL_SwapWindow(window);
        ++frames;
        int32_t sleep = mu_charsel_end_render(s);
        if (sleep > 0)
            SDL_Delay((uint32_t)sleep);
        if (frames % 25 == 0) {
            int32_t i = mu_charsel_entry_of(s, s->selected);
            char title[200];
            snprintf(title, sizeof title, "mu-charsel  World94  %s (class 0x%02x, level %u)  Enter requests %d  %.1f fps",
                     i >= 0 ? s->list.entries[i].name : "-", i >= 0 ? s->list.entries[i].class_byte : 0,
                     i >= 0 ? s->list.entries[i].level : 0, s->enter_requests,
                     (double)frames * 1000.0 / (double)(SDL_GetTicks() - start + 1));
            SDL_SetWindowTitle(window, title);
        }
        if (a->seconds > 0 && (SDL_GetTicks() - start) / 1000.0 >= a->seconds)
            running = 0;
    }
    double elapsed = (SDL_GetTicks() - start) / 1000.0;
    printf("{\"frames\": %u, \"seconds\": %.2f, \"fps\": %.2f, \"logic_steps\": %u, \"enter_requests\": %d}\n", frames,
           elapsed, elapsed > 0 ? frames / elapsed : 0.0, s->steps, s->enter_requests);
    gl_teardown(a);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
#endif

static int usage(void)
{
    fprintf(stderr, "usage: mu-charsel --game-root ROOT [--list FILE] [--slot N] [--marker X,Y[,Z]]\n"
                    "                  [--width W --height H] [--seconds S]\n"
                    "                  [--headless --frames N --out-dir DIR --backend soft|gl --every K]\n"
                    "                  [--cycle F] [--enter F] [--no-ui] [--font FACE] [--tip TEXT] [--quiet]\n"
                    "                  [--objects-dir DIR]   local decoded EncTerrain94.plain: objects + markers\n"
                    "                  [--objects-out FILE]  per object: index type x y z visible(+0xb) after(+0xa) blend_v\n");
    return 2;
}

int mu_charsel_tool_main(int argc, char **argv);

int mu_charsel_tool_main(int argc, char **argv)
{
    static app a;
    memset(&a, 0, sizeof a);
    a.width = 1280;
    a.height = 800;
    a.frames = 50;
    a.every = 10;
    a.slot = -1;
    a.enter_frame = -10;
    a.font = "Tahoma";
#ifdef MU_CHARSEL_NO_GL
    a.headless = 1;
    a.backend = "soft";
#else
    a.backend = "gl";
#endif
    for (int i = 1; i < argc; ++i) {
        const char *k = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(k, "--headless")) { a.headless = 1; continue; }
        if (!strcmp(k, "--quiet")) { a.quiet = 1; continue; }
        if (!strcmp(k, "--no-ui")) { a.no_ui = 1; continue; }
        if (!v)
            return usage();
        ++i;
        if (!strcmp(k, "--game-root")) a.root = v;
        else if (!strcmp(k, "--list")) a.list_path = v;
        else if (!strcmp(k, "--objects-dir")) a.objects_dir = v;
        else if (!strcmp(k, "--objects-out")) a.objects_out = v;
        else if (!strcmp(k, "--slot")) a.slot = atoi(v);
        else if (!strcmp(k, "--marker")) {
            a.marker[2] = 169.5f;
            if (sscanf(v, "%f,%f,%f", &a.marker[0], &a.marker[1], &a.marker[2]) < 2)
                return usage();
            a.marker_given = 1;
        }
        else if (!strcmp(k, "--width")) a.width = atoi(v);
        else if (!strcmp(k, "--height")) a.height = atoi(v);
        else if (!strcmp(k, "--seconds")) a.seconds = strtof(v, NULL);
        else if (!strcmp(k, "--frames")) a.frames = atoi(v);
        else if (!strcmp(k, "--every")) a.every = atoi(v);
        else if (!strcmp(k, "--cycle")) a.cycle = atoi(v);
        else if (!strcmp(k, "--enter")) a.enter_frame = atoi(v);
        else if (!strcmp(k, "--out-dir")) a.out_dir = v;
        else if (!strcmp(k, "--backend")) a.backend = v;
        else if (!strcmp(k, "--font")) a.font = v;
        else if (!strcmp(k, "--tip")) a.tip = v;
        else return usage();
    }
    if (!a.root || a.width < 64 || a.height < 64 || a.width > 8192 || a.height > 8192 || a.frames < 1)
        return usage();
    if (load(&a)) {
        unload(&a);
        return 1;
    }
#ifndef MU_CHARSEL_NO_GL
    int status = a.headless ? headless(&a) : windowed(&a);
#else
    int status = headless(&a);
#endif
    unload(&a);
    return status;
}

#ifndef MU_CHARSEL_TOOL_ONLY
int main(int argc, char **argv)
{
    return mu_charsel_tool_main(argc, argv);
}
#endif
