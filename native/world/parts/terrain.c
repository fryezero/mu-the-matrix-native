/* parts/terrain.c (WORLD-RT-001): the terrain frame and RenderTerrain (NATIVE-TERRAIN-002 in the client's frame
 * order, NATIVE-FIDELITY-002's scene passes).  The world map itself is loaded by the runtime (world_rt_load);
 * this part owns its tile textures. */
#include <string.h>

#include "../../core/mu_perf.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

#define TERRAIN_RADIUS 34

#ifndef MU_WORLD_NO_GL
typedef struct terrain_part {
    GLuint tiles[MU_WORLD_BITMAPS];
    mu_gl_batch *batch;            /* the runtime's batch for this draw (the batched sink's context) */
} terrain_part;
#endif

static void terrain_box(const mu_world_rt *a, int32_t box[4])
{
    int32_t cx = (int32_t)(a->walk.hero.position[0] / 100.0f), cy = (int32_t)(a->walk.hero.position[1] / 100.0f);
    int32_t x0 = cx - TERRAIN_RADIUS, y0 = cy - TERRAIN_RADIUS, x1 = cx + TERRAIN_RADIUS, y1 = cy + TERRAIN_RADIUS;
    box[0] = x0 < 0 ? 0 : x0 & ~3;
    box[1] = y0 < 0 ? 0 : y0 & ~3;
    box[2] = x1 > 254 ? 254 : x1;
    box[3] = y1 > 254 ? 254 : y1;
}

/* NATIVE-FIDELITY-002: RenderTerrain(0) of the main render scene 0x0185916b (verified slice
 * 0x018597c2..0x0185985e, reconstructed/terrain mu_terrain_scene_passes; the top-view flag [0x01ec9188] and the
 * Kanturu event state are 0 here). */
static int scene_draws_terrain(const mu_world_rt *a)
{
    if (mu_terrain_is_signed_world(a->map->world)) return 1;

    uint32_t calls = mu_terrain_scene_passes(a->map->world, 0, 0);
    for (; calls; calls >>= 2)
        if ((calls & 3) == MU_SCENE_CALL_TERRAIN)
            return 1;
    return 0;
}

/* RenderTerrain's view: CreateFrustrum 0x016cba24 from the GL modelview the
 * camera left (aspect = window width / 640, far [0x01cf1630] = the far plane
 * MoveMainCamera set, fov [0x01cf1634]) and CreateFrustrum2D 0x016d20d9 around
 * the hero in zoom mode 0, whose scale and distance come from the world
 * camera record (0x0098ac7c: width / 640 * Distance * Z_Distance * scale;
 * 0x0098ac45(2400) = 2400 * Distance * Z_Distance * scale). Then the
 * per-frame update 0x016ca4fa over the box: light copy, waves, and the
 * animated-layer counter; the water UV scroll follows the world time.  The object light sources follow in the
 * objects part (AddTerrainLight). */
static void terrain_particle(void *context, int32_t type, const float p[3], const float light[3])
{
    mu_world_rt *a=context;
    const float angle[3]={0,0,0};
    if (a->has_particles) mu_world_particles_create(&a->particles,type,p,angle,light,0,
        type==0x7f5e ? 1.5f : 1.0f);
}

static void terrain_frame(struct mu_world_rt *a, void *self, uint32_t now)
{
    (void)self;
    const mu_client_view *v = &a->walk.frame.view;
    mu_world_terrain_view(a->map,a->walk.hero.position,v->position);
    a->map->terrain_effect=terrain_particle;
    a->map->terrain_effect_context=a;

    mu_terrain_frustum *f = &a->frustum;
    memset(f, 0, sizeof *f);
    if (a->legacy_box) {
        int32_t box[4];
        terrain_box(a, box);
        f->x_min = box[0];
        f->y_min = box[1];
        f->x_max = box[2];
        f->y_max = box[3];
        mu_world_frame(a->map, (float)now);
        return;
    }
    float rows[12];
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 4; ++j)
            rows[4 * i + j] = v->modelview[4 * j + i];   /* 0x0184a569: m[i][j] = gl[4j + i] */
    int32_t width = (int32_t)v->window_width;
    mu_terrain_frustum_create((float)width / 640.0f, v->view_far, v->fov, rows, v->position, f);
    const mu_camera_info *c = &a->info;
    float factor = c->distance * c->z_distance * 1.0f;   /* camera scale +0x10 = 1 */
    mu_terrain_frustum_2d_params params;
    const float hero[3] = {a->walk.hero.position[0], a->walk.hero.position[1], a->walk.hero.position[2]};
    if (mu_terrain_frustum_2d_params_for(a->map->world, 0, width, (float)width / 640.0f * factor, 2400.0f * factor,
                                         &params)) {
        const float angle[3] = {v->angle[0], v->angle[1], v->angle[2]};
        int special=a->map->world==6 && a->hero_name && strstr(a->hero_name,"webzen");
        if (special) {
            const float scale=(float)width/640.0f;
            params.distance=8500.0f; params.near_offset=8500.0f*0.05f; params.back_offset=8500.0f*0.47f;
            params.width_far=3000.0f*scale; params.width_near=540.0f*scale;
        }
        mu_terrain_frustum_2d_camera(a->map->world,hero,angle,&params,0,special,0.0f,f->x2d,f->y2d);
    }
    mu_world_frame_box(a->map, (float)now, f->x_min, f->y_min, f->x_max, f->y_max);
}

static void terrain_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    mu_raster *raster = d->raster;
    mu_world_draw_stats stats;
    memset(&stats, 0, sizeof stats);
    if (!scene_draws_terrain(a))
        ;   /* NATIVE-FIDELITY-002: no terrain in Icarus (render scene 0x0185916b) */
    else if (a->legacy_box)
        mu_world_draw_raster(a->map, raster, a->frustum.x_min, a->frustum.y_min, a->frustum.x_max, a->frustum.y_max,
                             &stats);
    else
        mu_world_draw_raster_view(a->map, raster, &a->frustum, 6, 0, &stats);
    if ((a->map->world>=0x12 && a->map->world<=0x17) || a->map->world==0x35 || a->map->world==0x61)
        a->walk.frame.camera.earthquake=a->map->camera_shake;
    a->tile_stats = stats.tiles;
    d->faces = stats.tiles.faces;
}

#ifndef MU_WORLD_NO_GL
static void g_state(void *c, int32_t state, int32_t argument)
{
    (void)c;
    mu_meshdraw_state s;
    mu_world_state(state, argument, &s);
    if (s.blend) {
        glEnable(GL_BLEND);
        glBlendFunc((GLenum)s.src, (GLenum)s.dst);   /* GL blend factors */
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
    terrain_part *t = c;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    GLuint name = i >= 0 && i < MU_WORLD_BITMAPS ? t->tiles[i] : 0;
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
    glBegin((GLenum)mode);
}
static void g_end(void *c) { (void)c; glEnd(); }
static void g_tex(void *c, float s, float t) { (void)c; glTexCoord2f(s, t); }
static void g_c3(void *c, const float rgb[3]) { (void)c; glColor3fv(rgb); }
static void g_c4(void *c, float r, float g, float b, float al) { (void)c; glColor4f(r, g, b, al); }
static void g_v(void *c, const float xyz[3]) { (void)c; glVertex3fv(xyz); }

/* NATIVE-PERF-001: the terrain stream through the batch (same calls, merged draws). */
static void gb_state(void *c, int32_t state, int32_t argument)
{
    terrain_part *t = c;
    mu_meshdraw_state s;
    mu_world_state(state, argument, &s);
    mu_gl_batch_enable(t->batch, GL_BLEND, s.blend);
    if (s.blend)
        mu_gl_batch_blend_func(t->batch, (uint32_t)s.src, (uint32_t)s.dst);
    mu_gl_batch_enable(t->batch, GL_CULL_FACE, s.cull);
    mu_gl_batch_depth_mask(t->batch, s.depth_mask);
    mu_gl_batch_enable(t->batch, GL_ALPHA_TEST, s.alpha_test);
}

static void gb_bind(void *c, int32_t texture)
{
    terrain_part *t = c;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    GLuint name = i >= 0 && i < MU_WORLD_BITMAPS ? t->tiles[i] : 0;
    if (name) {
        mu_gl_batch_enable(t->batch, GL_TEXTURE_2D, 1);
        mu_gl_batch_bind_texture(t->batch, name);
    } else {
        mu_gl_batch_enable(t->batch, GL_TEXTURE_2D, 0);
    }
}

static void gb_begin(void *c, int32_t mode)
{
    terrain_part *t = c;
    mu_gl_batch_begin(t->batch, (uint32_t)mode);
}
static void gb_end(void *c) { mu_gl_batch_end(((terrain_part *)c)->batch); }
static void gb_tex(void *c, float s, float t) { mu_gl_batch_texcoord(((terrain_part *)c)->batch, s, t); }
static void gb_c3(void *c, const float rgb[3]) { mu_gl_batch_color4(((terrain_part *)c)->batch, rgb[0], rgb[1], rgb[2], 1.0f); }
static void gb_c4(void *c, float r, float g, float b, float al) { mu_gl_batch_color4(((terrain_part *)c)->batch, r, g, b, al); }
static void gb_v(void *c, const float xyz[3]) { mu_gl_batch_vertex(((terrain_part *)c)->batch, xyz); }

static void terrain_gl_setup(struct mu_world_rt *a, void *self)
{
    terrain_part *t = self;
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i) {
        const mu_image *image = &a->map->bitmaps[i];
        t->tiles[i] = 0;
        if (image->width <= 0)
            continue;
        GLuint name = 0;
        glGenTextures(1, &name);
        glBindTexture(GL_TEXTURE_2D, name);
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        GLint filter = a->map->bitmap_linear[i] ? GL_LINEAR : GL_NEAREST;  /* loader argument 0x2601 / 0x2600 */
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filter);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filter);
        GLint wrap=mu_terrain_is_signed_world(a->map->world) && i==1 ? GL_CLAMP : GL_REPEAT;
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, image->width, image->height, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                     image->rgba);
        t->tiles[i] = name;
    }
}

static void terrain_gl_teardown(struct mu_world_rt *a, void *self)
{
    (void)a;
    terrain_part *t = self;
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        if (t->tiles[i]) {
            glDeleteTextures(1, &t->tiles[i]);
            t->tiles[i] = 0;
        }
}

static void terrain_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    terrain_part *t = self;
    d->perf = mu_perf_begin(a->perf);   /* NATIVE-PERF-001: phase times (off unless --perf) */
    t->batch = a->batch;
    mu_terrain_sink sink = {t, g_state, g_bind, g_begin, g_tex, g_c3, g_c4, g_v, g_end};
    if (a->batch) {   /* NATIVE-PERF-001: the same stream, merged draws */
        mu_terrain_sink batched = {t, gb_state, gb_bind, gb_begin, gb_tex, gb_c3, gb_c4, gb_v, gb_end};
        sink = batched;
        mu_gl_batch_session_begin(a->batch);
    }
    mu_terrain_scene scene;
    mu_world_scene(a->map, &scene);
    mu_terrain_tile_stats stats;
    memset(&stats, 0, sizeof stats);
    if (!scene_draws_terrain(a))
        ;   /* NATIVE-FIDELITY-002: the render scene draws no terrain in Icarus (and worlds 0x84, -1) */
    else if (a->legacy_box)
        mu_terrain_draw(&scene, a->frustum.x_min, a->frustum.y_min, a->frustum.x_max, a->frustum.y_max,
                        mu_terrain_alpha_layers(a->map->world), &sink, &stats);
    else   /* RenderTerrain with the client's block and tile tests, in-game scene state 6 */
        mu_terrain_render(&scene, &a->frustum, 6, 0, mu_terrain_alpha_layers(a->map->world), &sink, &stats);
    if ((a->map->world>=0x12 && a->map->world<=0x17) || a->map->world==0x35 || a->map->world==0x61)
        a->walk.frame.camera.earthquake=a->map->camera_shake;
    a->tile_stats = stats;
    if (a->batch)
        mu_gl_batch_session_end(a->batch);
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    mu_perf_end(a->perf, MU_PERF_TERRAIN, d->perf);
    d->faces = stats.faces;
}
#endif

const mu_world_part_ops mu_part_terrain = {
    .name = "terrain",
#ifndef MU_WORLD_NO_GL
    .state_size = sizeof(terrain_part),
    .draw_gl = terrain_draw_gl,
    .gl_setup = terrain_gl_setup,
    .gl_teardown = terrain_gl_teardown,
#endif
    .frame = terrain_frame,
    .draw_soft = terrain_draw_soft,
};
