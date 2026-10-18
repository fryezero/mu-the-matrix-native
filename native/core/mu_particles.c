/* The client's legacy particles, sprites and blob shadows in the native
 * session (NATIVE-PARTICLE-001). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mu_particles.h"
#include "mu_objects.h"
#include "mu_env.h"
#include "mu_meshdraw.h"
#include "../../reconstructed/environment/env.h"
#include "../../reconstructed/movement/client_movement.h"

/* Effect bitmaps first (MU_WORLD_PT_EFFECTS of them), then the world's rain02/rain03. */
#define MU_WORLD_PT_EFFECTS 7
static const int32_t bitmap_ids[MU_WORLD_PT_BITMAPS] = {
    MU_PT_BITMAP_FIRE,   MU_PT_BITMAP_SMOKE,  MU_PT_BITMAP_FLARE,       MU_PT_BITMAP_SPARK3,   MU_PT_BITMAP_THUNDER,
    MU_PT_BITMAP_SPARK2, MU_PT_BITMAP_SHINY2, MU_PT_BITMAP_RAIN_SPLASH, MU_PT_BITMAP_RAIN_RING};
static const char *const effect_files[MU_WORLD_PT_EFFECTS] = {
    "Data/Effect/Fire01.OZJ",  "Data/Effect/smoke01.OZJ", "Data/Effect/flare01.OZJ", "Data/Effect/Spark03.OZJ",
    "Data/Effect/Thunder01.OZJ", "Data/Effect/Spark02.OZJ", "Data/Effect/Shiny02.OZJ"};

static int32_t slot_of(int32_t bitmap)
{
    for (int32_t i = 0; i < MU_WORLD_PT_BITMAPS; ++i)
        if (bitmap_ids[i] == bitmap)
            return i;
    return -1;
}

int32_t mu_world_particles_rand(mu_world_particles *p)
{
    p->rand_state = p->rand_state * 214013u + 2531011u;   /* rand() 0x01989721 */
    p->rand_calls++;
    return (int32_t)((p->rand_state >> 16) & 0x7fff);
}

/* ---- host of the reconstructed routines ---- */

static int32_t h_rand(void *c) { return mu_world_particles_rand(c); }

static float h_terrain(void *c, float x, float y)
{
    const mu_world_particles *p = c;
    if (!p->map)
        return 0.0f;
    return mu_request_terrain_height(p->map->height, p->map->attributes, p->map->water_height, 6, x, y);
}

static void host(mu_world_particles *p, mu_pt_host *h)
{
    memset(h, 0, sizeof *h);
    h->context = p;
    h->rand = h_rand;
    h->terrain_height = h_terrain;
    h->world = p->world;
    h->world_time = p->world_time;
    h->frame_time = 0.1f;   /* [0x01cf103c] */
    h->drop_divisor = 1;
}

/* ---- assets ---- */

static void load_bitmaps(mu_world_particles *p, const char *root, int no_assets)
{
    mu_textures *t = &p->bitmaps;
    t->count = t->model_count = MU_WORLD_PT_BITMAPS;
    t->images = calloc(MU_WORLD_PT_BITMAPS, sizeof *t->images);
    t->slots = calloc(MU_WORLD_PT_BITMAPS, sizeof *t->slots);
    t->components = calloc(MU_WORLD_PT_BITMAPS, sizeof *t->components);
    t->filter = calloc(MU_WORLD_PT_BITMAPS, sizeof *t->filter);
    t->wrap = calloc(MU_WORLD_PT_BITMAPS, sizeof *t->wrap);
    if (!t->images || !t->slots || !t->components || !t->filter || !t->wrap)
        return;
    for (int32_t i = 0; i < MU_WORLD_PT_BITMAPS; ++i) {
        char relative[512], path[2048], error[256];
        if (i < MU_WORLD_PT_EFFECTS) {
            /* LoadBitmap("Effect\\...", index, GL_LINEAR, GL_CLAMP) in the effect loader (0x01820f19 ...) */
            t->filter[i] = 0x2601;
            t->wrap[i] = 0x2900;
            snprintf(relative, sizeof relative, "%s", effect_files[i]);
        } else {
            /* the world's rain02/rain03: GL_NEAREST, GL_CLAMP (0x01829e21) */
            t->filter[i] = 0x2600;
            t->wrap[i] = 0x2900;
            if (!mu_env_bitmap_file(p->world, bitmap_ids[i], relative, sizeof relative))
                continue;
        }
        if (no_assets || !mu_objects_resolve(root, relative, path, sizeof path))
            continue;
        size_t n = strlen(path);
        char kind = (n > 0 && (path[n - 1] == 'J' || path[n - 1] == 'j')) ? 'j' : 't';
        if (mu_texture_upload_file(path, kind, &t->images[i], &t->components[i], error, sizeof error) == 0 &&
            t->images[i].width > 0) {
            t->slots[i] = &t->images[i];
            p->bitmap_present[i] = 1;
        }
    }
}

int mu_world_particles_open(mu_world_particles *p, const char *root, const mu_world *map, int32_t world,
                            uint32_t seed, int no_assets, char *error, size_t error_size)
{
    memset(p, 0, sizeof *p);
    p->world = world;
    p->map = map;
    p->rand_state = seed;
    p->sprites = calloc(1, sizeof *p->sprites);
    if (!p->sprites || mu_pt_system_init(&p->list, MU_WORLD_PT_CAPACITY)) {
        snprintf(error, error_size, "out of memory");
        free(p->sprites);
        p->sprites = NULL;
        return 1;
    }
    load_bitmaps(p, root, no_assets);
    return 0;
}

void mu_world_particles_close(mu_world_particles *p)
{
    mu_textures *t = &p->bitmaps;
    if (t->images)
        for (int i = 0; i < t->count; ++i)
            mu_image_free(&t->images[i]);
    free(t->images);
    free(t->slots);
    free(t->components);
    free(t->filter);
    free(t->wrap);
    mu_pt_system_free(&p->list);
    free(p->sprites);
    memset(p, 0, sizeof *p);
}

/* ---- creation and the step ---- */

int mu_world_particles_create(mu_world_particles *p, int32_t type, const float position[3], const float angle[3],
                              const float light[3], int32_t subtype, float scale)
{
    mu_pt_host h;
    host(p, &h);
    const int kept = mu_pt_create(&p->list, &h, type, position, angle, light, subtype, scale, MU_PT_NO_OWNER, 0);
    p->stats.created = p->list.created;
    p->stats.dropped = p->list.dropped;
    p->stats.unsupported = p->list.unsupported;
    p->stats.overflow = p->list.overflow;
    return kept;
}

int32_t mu_world_particles_sprite(mu_world_particles *p, int32_t bitmap, const float position[3], float scale,
                                  const float light[3], int32_t owner, float rotation, int32_t blend, int32_t axes)
{
    static const mu_pt_sheet sheet = {1, 1, 1.0f};   /* 0x00a0c1d0 */
    const int32_t i = mu_pt_sprite_create(p->sprites, bitmap, position, scale, light, owner, rotation, blend, axes,
                                          &sheet);
    p->stats.sprites_created = p->sprites->created;
    p->stats.sprites_full = p->sprites->full;
    return i;
}

void mu_world_particles_step(mu_world_particles *p, float world_time)
{
    p->world_time = world_time;
    mu_pt_host h;
    host(p, &h);
    mu_pt_move_all(&p->list, &h);
    p->stats.steps++;
    p->stats.live = (uint32_t)p->list.count;
    if (p->stats.live > p->stats.max_live)
        p->stats.max_live = p->stats.live;
}

/* ---- the GL stream through a render backend ---- */

typedef struct draw_context {
    mu_world_particles *p;
    const mu_world_particles_target *target;
    mu_meshdraw_state state;
    int32_t slot;
    int32_t mode;
    float color[4];
    float uv[4][2];
    float v[4][3];
    int32_t corners;
    int32_t pending_uv;
    long quads;
    /* shadows */
    const mu_render_backend *backend;
    float shadow_rgba[4];
    int32_t shadow_vertices;
    int shadow_open;
} draw_context;

static void apply_state(mu_meshdraw_state *s, int32_t wrapper, int32_t argument)
{
    switch (wrapper) {
    case MU_PT_STATE_ADD:          /* 0x0184aa2b */
        s->blend = 1;
        s->src = MU_GL_ONE;
        s->dst = MU_GL_ONE;
        s->depth_mask = 0;
        s->alpha_test = 0;
        s->cull = 0;
        s->texture = 1;
        break;
    case MU_PT_STATE_SUBTRACT:     /* 0x0184aab7 */
        s->blend = 1;
        s->src = MU_GL_ZERO;
        s->dst = MU_GL_ONE_MINUS_SRC_COLOR;
        s->depth_mask = 0;
        s->alpha_test = 0;
        s->cull = 0;
        s->texture = 1;
        break;
    case MU_PT_STATE_ADD_INVERSE:  /* 0x0184ab46 */
        s->blend = 1;
        s->src = MU_GL_ONE_MINUS_SRC_COLOR;
        s->dst = MU_GL_ONE;
        s->depth_mask = 0;
        s->alpha_test = 0;
        s->cull = 0;
        s->texture = 1;
        break;
    case MU_PT_STATE_ALPHA:        /* 0x0184a990(arg): the depth mask is turned on only for arg != 0 */
        s->blend = 1;
        s->src = MU_GL_SRC_ALPHA;
        s->dst = MU_GL_ONE_MINUS_SRC_ALPHA;
        if (argument)
            s->depth_mask = 1;
        s->alpha_test = 1;
        s->cull = 0;
        s->texture = 1;
        break;
    case MU_PT_STATE_UNTEXTURED:   /* 0x0184a783(0) */
        s->depth_mask = 1;
        s->alpha_test = 0;
        s->texture = 0;
        break;
    case MU_PT_STATE_DEPTH_OFF:
        s->depth_mask = 0;
        break;
    case MU_PT_STATE_DEPTH_ON:
        s->depth_mask = 1;
        break;
    default:
        break;
    }
}

static void g_state(void *c, int32_t wrapper, int32_t argument)
{
    apply_state(&((draw_context *)c)->state, wrapper, argument);
}

static void g_bind(void *c, int32_t bitmap)
{
    draw_context *d = c;
    const int32_t s = slot_of(bitmap);
    d->slot = s >= 0 && d->p->bitmap_present[s] ? s : -1;
}

static void g_begin(void *c, int32_t mode)
{
    draw_context *d = c;
    d->mode = mode;
    d->corners = 0;
    d->color[0] = d->color[1] = d->color[2] = d->color[3] = 1.0f;
}

static void g_color3(void *c, const float rgb[3])
{
    draw_context *d = c;
    d->color[0] = rgb[0];
    d->color[1] = rgb[1];
    d->color[2] = rgb[2];
    d->color[3] = 1.0f;
}

static void g_color4(void *c, float r, float g, float b, float a)
{
    draw_context *d = c;
    d->color[0] = r;
    d->color[1] = g;
    d->color[2] = b;
    d->color[3] = a;
}

static void g_tex(void *c, float u, float v)
{
    draw_context *d = c;
    if (d->corners < 4) {
        d->uv[d->corners][0] = u;
        d->uv[d->corners][1] = v;
    }
}

static void g_vertex(void *c, const float v[3])
{
    draw_context *d = c;
    if (d->corners < 4) {
        d->v[d->corners][0] = v[0];
        d->v[d->corners][1] = v[1];
        d->v[d->corners][2] = v[2];
        d->corners++;
    }
}

/* view space back to world space: x = R^T (v - t) (the camera rows are orthonormal) */
static void to_world(const float camera[12], const float v[3], float out[3])
{
    for (int k = 0; k < 3; ++k) {
        float s = 0.0f;
        for (int r = 0; r < 3; ++r)
            s += camera[4 * r + k] * (v[r] - camera[4 * r + 3]);
        out[k] = s;
    }
}

static void g_end(void *c)
{
    draw_context *d = c;
    if (d->mode != MU_PT_GL_QUADS || d->corners != 4 || d->slot < 0)
        return;
    mu_render_backend b;
    if (d->target->backend(d->target->context, d->p, &b))
        return;
    mu_meshdraw_state s = d->state;
    s.texture = 1;
    s.depth_test = 1;
    b.prepare(b.context, &s, d->slot);
    b.begin(b.context);
    static const int order[6] = {0, 1, 2, 0, 2, 3};
    for (int i = 0; i < 6; ++i) {
        float w[3];
        to_world(d->p->camera, d->v[order[i]], w);
        b.sink.texcoord(b.sink.context, d->uv[order[i]][0], d->uv[order[i]][1]);
        b.sink.color4(b.sink.context, d->color[0], d->color[1], d->color[2], d->color[3]);
        b.sink.vertex(b.sink.context, w);
    }
    b.end(b.context);
    d->quads++;
}

static int bitmap_info(void *c, int32_t bitmap, mu_pt_bitmap *out)
{
    const mu_world_particles *p = c;
    const int32_t s = slot_of(bitmap);
    if (s < 0 || !p->bitmap_present[s])
        return 0;
    out->width = (float)p->bitmaps.images[s].width;     /* +0x204: the uploaded size */
    out->height = (float)p->bitmaps.images[s].height;   /* +0x208 */
    out->components = p->bitmaps.components[s];          /* +0x214 */
    return 1;
}

long mu_world_particles_draw(mu_world_particles *p, const float modelview[16], const mu_world_particles_target *t)
{
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 4; ++j)
            p->camera[4 * i + j] = modelview[4 * j + i];   /* 0x0184a569: CameraMatrix[i][j] = gl[4j + i] */
    draw_context d;
    memset(&d, 0, sizeof d);
    d.p = p;
    d.target = t;
    d.slot = -1;
    mu_meshdraw_state_defaults(&d.state);
    d.state.depth_mask = 0;
    mu_pt_gl gl = {&d, g_state, g_bind, g_begin, g_end, g_color3, g_color4, g_tex, g_vertex, NULL, NULL};
    mu_pt_sprites_mark_visible(p->sprites);   /* 0x01692887 */
    const int32_t sprites = mu_pt_sprites_render(p->sprites, 0, p->world_time, p->camera, bitmap_info, p, &gl,
                                                 NULL, NULL);
    const int32_t particles = mu_pt_render_all(&p->list, 0, p->camera, bitmap_info, p, &gl);
    p->stats.drawn_sprites = (uint32_t)sprites;
    p->stats.drawn_particles = (uint32_t)particles;
    p->stats.shadows = p->stats.pending_shadows;   /* the frame's RenderBoids/RenderFishs ran before the sprite pass */
    p->stats.shadow_vertices = p->stats.pending_shadow_vertices;
    p->stats.pending_shadows = p->stats.pending_shadow_vertices = 0;
    return d.quads;
}

typedef struct raster_target {
    mu_raster *raster;
    mu_render_backend backend;
} raster_target;

static int raster_backend(void *c, const mu_world_particles *p, mu_render_backend *out)
{
    raster_target *t = c;
    t->raster->textures = p->bitmaps.slots;
    t->raster->texture_count = p->bitmaps.count;
    t->raster->texture_filter = p->bitmaps.filter;
    t->raster->texture_wrap = p->bitmaps.wrap;
    *out = t->backend;
    return 0;
}

long mu_world_particles_draw_raster(mu_world_particles *p, mu_raster *raster, const float modelview[16])
{
    raster_target t = {raster, {0}};
    mu_raster_backend(raster, &t.backend);
    const int linear = raster->linear;
    raster->linear = 1;
    mu_world_particles_target target = {&t, raster_backend};
    long n = mu_world_particles_draw(p, modelview, &target);
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
    raster->linear = linear;
    return n;
}

/* ---- shadows ---- */

static void s_state(void *c, int32_t wrapper, int32_t argument)
{
    apply_state(&((draw_context *)c)->state, wrapper, argument);
}

static void s_begin(void *c, int32_t mode)
{
    draw_context *d = c;
    const mu_render_backend *b = d->backend;
    if (mode != MU_PT_GL_TRIANGLES || !b)
        return;
    mu_meshdraw_state s = d->state;
    s.texture = 0;
    s.depth_test = 1;
    s.cull = 0;
    b->prepare(b->context, &s, -1);
    b->begin(b->context);
    d->shadow_open = 1;
}

static void s_vertex(void *c, const float v[3])
{
    draw_context *d = c;
    const mu_render_backend *b = d->backend;
    if (!d->shadow_open)
        return;
    b->sink.color4(b->sink.context, d->shadow_rgba[0], d->shadow_rgba[1], d->shadow_rgba[2], d->shadow_rgba[3]);
    b->sink.vertex(b->sink.context, v);
    d->shadow_vertices++;
}

static void s_end(void *c)
{
    draw_context *d = c;
    if (d->shadow_open && d->backend)
        d->backend->end(d->backend->context);
    d->shadow_open = 0;
}

int32_t mu_world_particles_shadow(mu_world_particles *p, const mu_model *model, const mu_bmd *bmd, const float rgba[4],
                                  const mu_render_backend *backend)
{
    if (!model || !bmd || !backend)
        return 0;
    mu_pt_shadow_mesh meshes[MU_WORLD_PT_SHADOW_MESHES];
    int32_t count = bmd->mesh_count < MU_WORLD_PT_SHADOW_MESHES ? bmd->mesh_count : MU_WORLD_PT_SHADOW_MESHES;
    for (int32_t i = 0; i < count; ++i) {
        const mu_bmd_mesh *m = &bmd->meshes[i];
        meshes[i].triangle_count = (int16_t)m->polygon_count;
        meshes[i].texture = m->texture_index;
        meshes[i].triangles = mu_model_triangles(model, i);
        meshes[i].vertices = mu_model_vertices(model, i);
        meshes[i].vertex_count = m->vertex_count;
    }
    draw_context d;
    memset(&d, 0, sizeof d);
    d.p = p;
    d.backend = backend;
    mu_meshdraw_state_defaults(&d.state);
    /* EnableAlphaTest(1) before the call (RenderBoids/RenderFishs, RenderObject's shadow block) */
    apply_state(&d.state, MU_PT_STATE_ALPHA, 1);
    for (int k = 0; k < 4; ++k)
        d.shadow_rgba[k] = rgba[k];
    mu_pt_gl gl = {&d, s_state, NULL, s_begin, s_end, NULL, NULL, NULL, s_vertex, NULL, NULL};
    mu_pt_host h;
    host(p, &h);
    const float *origin = mu_model_origin(model);
    const int32_t n = mu_pt_render_body_shadow(meshes, count, origin, -1, -1, -1, -1, 0, &h, &gl);
    p->stats.pending_shadows++;
    p->stats.pending_shadow_vertices += (uint32_t)n;
    p->stats.shadows_total++;
    return n;
}

/* ---- bones ---- */

int mu_world_particles_bone_position(const mu_model *model, int32_t bone, const float in[3], float out[3])
{
    const float *bones = model ? mu_model_bone_matrices(model) : NULL;
    if (!bones || bone < 0 || bone >= MU_MODEL_MAX_BONES)
        return 0;
    mu_pt_transform_position(bones + 12 * bone, in, out, 1, model->params.body_scale, model->params.origin);
    return 1;
}

int mu_world_particles_named_bone_position(const mu_model *model, const mu_bmd *bmd, const char *name,
                                           const float in[3], float out[3])
{
    if (!model || !bmd || bmd->bone_count <= 0)
        return 0;
    const char *names[MU_MODEL_MAX_BONES];
    int32_t n = bmd->bone_count < MU_MODEL_MAX_BONES ? bmd->bone_count : MU_MODEL_MAX_BONES;
    for (int32_t i = 0; i < n; ++i)
        names[i] = bmd->bones[i].name;
    const int32_t bone = mu_pt_find_bone(names, n, name);
    if (bone < 0)
        return 0;   /* 0x0129f18a returns NULL; TransformPosition then leaves `out` alone */
    return mu_world_particles_bone_position(model, bone, in, out);
}

/* ---- object visuals ---- */

typedef struct visual_context {
    mu_world_particles *p;
    int has_model;
    const mu_model *model;
    const mu_bmd *bmd;
} visual_context;

static int32_t v_rand(void *c) { return mu_world_particles_rand(((visual_context *)c)->p); }

static int v_has_model(void *c, const mu_pt_visual_object *o)
{
    (void)o;
    return ((visual_context *)c)->has_model;
}

static void v_bone(void *c, const mu_pt_visual_object *o, const char *bone, const float in[3], float out[3])
{
    visual_context *v = c;
    (void)o;
    mu_world_particles_named_bone_position(v->model, v->bmd, bone, in, out);
}

static void v_particle(void *c, int32_t type, const float position[3], const float angle[3], const float light[3],
                       int32_t subtype, float scale, int32_t owner)
{
    (void)owner;
    mu_world_particles_create(((visual_context *)c)->p, type, position, angle, light, subtype, scale);
}

static void v_sprite(void *c, int32_t bitmap, const float position[3], float scale, const float light[3],
                     int32_t owner, float rotation, int32_t blend, int32_t axes)
{
    mu_world_particles_sprite(((visual_context *)c)->p, bitmap, position, scale, light, owner, rotation, blend, axes);
}

static void v_joint(void *c, int32_t bitmap, const float position[3], const float angle[3], int32_t subtype,
                    int32_t owner, float scale)
{
    (void)bitmap, (void)position, (void)angle, (void)subtype, (void)owner, (void)scale;
    ((visual_context *)c)->p->stats.joints++;   /* CreateJoint: the joint pool is not part of this module */
}

static void v_effect(void *c, int32_t type, const float position[3], const float angle[3], const float light[3],
                     int32_t subtype, int32_t owner)
{
    (void)type, (void)position, (void)angle, (void)light, (void)subtype, (void)owner;
    ((visual_context *)c)->p->stats.effects++;
}

int mu_world_particles_object_visual(mu_world_particles *p, mu_pt_visual_object *object, int has_model,
                                     const mu_model *model, const mu_bmd *bmd)
{
    visual_context v = {p, has_model, model, bmd};
    mu_pt_visual_host h;
    memset(&h, 0, sizeof h);
    h.context = &v;
    h.rand = v_rand;
    h.has_model = v_has_model;
    h.bone_position = v_bone;
    h.particle = v_particle;
    h.sprite = v_sprite;
    h.joint = v_joint;
    h.effect = v_effect;
    h.world = p->world;
    h.world_time = p->world_time;
    const int handled = mu_pt_object_visual(object, &h);
    if (handled)
        p->stats.visuals++;
    return handled;
}

/* ---- hooks ---- */

static void o_particle(void *c, int32_t bitmap, const float position[3], const float angle[3], const float light[3],
                       int32_t subtype, float scale)
{
    mu_world_particles_create(c, bitmap, position, angle, light, subtype, scale);
}

static void o_visual(void *c, struct mu_objects *o, int32_t index, int has_model, mu_object_model *m)
{
    mu_world_particles *p = c;
    uint8_t *img = mu_objects_object_image(o, index);
    if (!img)
        return;
    mu_pt_visual_object v;
    memset(&v, 0, sizeof v);
    v.index = index;
    v.type = mu_obj_i32(img, MU_OBJF_TYPE);
    memcpy(v.position, img + MU_OBJF_POSITION, 12);
    memcpy(v.angle, img + MU_OBJF_ANGLE, 12);
    memcpy(v.light, img + MU_OBJF_LIGHT, 12);
    v.scale = mu_obj_f32(img, MU_OBJF_SCALE);
    v.blend_light = mu_obj_f32(img, MU_OBJF_BLEND_LIGHT);
    v.blend_v = mu_obj_f32(img, MU_OBJF_BLEND_V);
    if (p->map)
        p->world_time = p->map->time;   /* 0x06fce370 */
    if (!mu_world_particles_object_visual(p, &v, has_model, m ? &m->model : NULL, m ? &m->bmd : NULL)) {
        mu_obj_visual(img, o->world, p->world_time);   /* other worlds: the reconstructed scroll part */
        return;
    }
    memcpy(img + MU_OBJF_LIGHT, v.light, 12);
    mu_obj_set_f32(img, MU_OBJF_BLEND_LIGHT, v.blend_light);
    mu_obj_set_f32(img, MU_OBJF_BLEND_V, v.blend_v);
}

void mu_world_particles_attach(mu_world_particles *p, struct mu_objects *objects, struct mu_world_env *env)
{
    if (objects) {
        objects->rt.particle = o_particle;
        objects->rt.visual = o_visual;
        objects->rt.hook_context = p;
    }
    if (env)
        env->particles = p;
}
