/* The client's ambient world life and weather in the native session
 * (NATIVE-ENV-001). */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mu_env.h"
#include "mu_objects.h"
#include "mu_particles.h"
#include "../../reconstructed/movement/client_movement.h"

static const int32_t bitmap_ids[MU_WORLD_ENV_BITMAPS] = {MU_ENV_BITMAP_LEAF1, MU_ENV_BITMAP_LEAF2, MU_ENV_BITMAP_RAIN,
                                                         MU_ENV_BITMAP_RAIN_SPLASH, MU_ENV_BITMAP_RAIN_RING};

static mu_world_env_model *model_of(mu_world_env *e, int32_t type)
{
    for (int32_t i = 0; i < e->model_count; ++i)
        if (e->models[i].type == type)
            return &e->models[i];
    return NULL;
}

/* ---- host of the reconstructed routines ---- */

static float h_terrain(void *c, float x, float y)
{
    mu_world_env *e = c;
    /* RequestTerrainHeight 0x016cc9e2 in scene state 6 */
    return mu_request_terrain_height(e->map->height, e->map->attributes, e->map->water_height, 6, x, y);
}

static void h_sound(void *c, int32_t id, const mu_env_object *o, int32_t loop)
{
    mu_world_env *e = c;
    (void)o;
    (void)loop;
    e->stats.sounds++;
    if (id == 0xc || id == 0xd)
        e->stats.sound_bird++;
    else if (id == 0xe)
        e->stats.sound_bat++;
    else if (id == 0xf)
        e->stats.sound_rat++;
    else
        e->stats.sound_other++;
    if (e->sound)
        e->sound(e->sound_context, id);
}

static void h_set_action(void *c, mu_env_object *o, int32_t action)
{
    mu_world_env *e = c;
    mu_world_env_model *m = model_of(e, o->type);
    int32_t count = m && m->loaded ? m->bmd.action_count : 0;
    mu_move_set_action(&o->action, &o->prior_action, &o->frame, &o->prior_frame, count, action);
}

static void h_animate(void *c, mu_env_object *o, float speed)
{
    mu_world_env *e = c;
    mu_world_env_model *m = model_of(e, o->type);
    if (!m || !m->loaded || m->bmd.action_count <= 0)
        return;
    uint8_t loop = 0;
    mu_model_set_state(&m->model, o->action, o->frame, o->prior_frame, o->prior_action);
    mu_model_tick(&m->model, speed, &loop);
    o->frame = mu_model_frame(&m->model);
    o->prior_frame = mu_model_prior_frame(&m->model);
    o->prior_action = mu_model_prior_action(&m->model);
}

static void h_particle(void *c, int32_t bitmap, const float p[3], const float a[3], const float l[3], int32_t s,
                       float scale)
{
    mu_world_env *e = c;
    e->stats.particles++;
    if (e->particles)   /* CreateParticle 0x0168fafd (NATIVE-PARTICLE-001) */
        mu_world_particles_create(e->particles, bitmap, p, a, l, s, scale);
}

static void h_kill(void *c, mu_env_object *o)
{
    (void)o;
    ((mu_world_env *)c)->stats.kills++;
}

static void h_init(void *c, mu_env_object *o)
{
    (void)o;
    ((mu_world_env *)c)->stats.inits++;
}

static void h_effect(void *c, int32_t bitmap, const mu_env_object *o, float scale, int32_t argument)
{
    (void)bitmap, (void)o, (void)scale, (void)argument;
    ((mu_world_env *)c)->stats.effects++;
}

/* ---- assets ---- */

static void add_model(mu_world_env *e, const char *root, int32_t type, int no_assets)
{
    if (e->model_count >= MU_WORLD_ENV_MODELS || model_of(e, type))
        return;
    mu_world_env_model *m = &e->models[e->model_count++];
    memset(m, 0, sizeof *m);
    m->type = type;
    char relative[512], message[512];
    if (no_assets || !mu_env_model_file(e->world, type, relative, sizeof relative) ||
        !mu_objects_resolve(root, relative, m->path, sizeof m->path) ||
        mu_bmd_load_file(m->path, &m->bmd, message, sizeof message) != MU_BMD_OK)
        return;
    mu_model_params p;
    mu_model_default_params(&p);
    p.world = e->world;
    if (mu_model_init(&m->model, &m->bmd, &p, message, sizeof message) != MU_MODEL_OK) {
        mu_bmd_free(&m->bmd);
        return;
    }
    char directory[2048];
    mu_path_directory(m->path, directory, sizeof directory);
    mu_textures_load(&m->textures, &m->bmd, directory);
    m->loaded = 1;
}

/* Models the world's boid and fish creators can give an object. */
static void add_world_models(mu_world_env *e, const char *root, int no_assets)
{
    const int32_t w = e->world;
    if (w == 0) {
        add_model(e, root, MU_ENV_MODEL_BIRD, no_assets);
        add_model(e, root, MU_ENV_MODEL_FISH, no_assets);
    } else if (w == 1 || w == 4 || (w >= 0x74 && w <= 0x78)) {
        add_model(e, root, MU_ENV_MODEL_BAT, no_assets);
        add_model(e, root, MU_ENV_MODEL_RAT, no_assets);
    } else if (w == 3) {
        add_model(e, root, MU_ENV_MODEL_BUTTERFLY, no_assets);
    } else if (w == 6) {
        add_model(e, root, MU_ENV_MODEL_BUG, no_assets);
    } else if (w == 7 || (w >= 0x80 && w <= 0x82)) {
        for (int32_t t = 0x199; t <= 0x1a0; ++t)
            add_model(e, root, t, no_assets);
    } else if ((w >= 11 && w <= 17) || w == 52) {
        add_model(e, root, MU_ENV_MODEL_CROW, no_assets);
    }
}

static void load_bitmaps(mu_world_env *e, const char *root, int no_assets)
{
    mu_textures *t = &e->bitmaps;
    t->count = t->model_count = MU_WORLD_ENV_BITMAPS;
    t->images = calloc(MU_WORLD_ENV_BITMAPS, sizeof *t->images);
    t->slots = calloc(MU_WORLD_ENV_BITMAPS, sizeof *t->slots);
    t->components = calloc(MU_WORLD_ENV_BITMAPS, sizeof *t->components);
    t->filter = calloc(MU_WORLD_ENV_BITMAPS, sizeof *t->filter);
    t->wrap = calloc(MU_WORLD_ENV_BITMAPS, sizeof *t->wrap);
    if (!t->images || !t->slots || !t->components || !t->filter || !t->wrap)
        return;
    for (int i = 0; i < MU_WORLD_ENV_BITMAPS; ++i) {
        t->filter[i] = 0x2600;   /* LoadBitmap(..., GL_NEAREST, GL_CLAMP) in 0x01829e21 */
        t->wrap[i] = 0x2900;
        if (no_assets)
            continue;
        char relative[512], path[2048], error[256];
        if (!mu_env_bitmap_file(e->world, bitmap_ids[i], relative, sizeof relative))
            continue;
        int found = mu_objects_resolve(root, relative, path, sizeof path);
        if (!found && e->tga_leaves && i <= 1) {   /* viewer option: the .tga the client unloads */
            size_t n = strlen(relative);
            if (n > 3)
                memcpy(relative + n - 3, "OZT", 3);
            found = mu_objects_resolve(root, relative, path, sizeof path);
        }
        if (!found)
            continue;
        size_t n = strlen(path);
        char kind = (n > 0 && (path[n - 1] == 'J' || path[n - 1] == 'j')) ? 'j' : 't';
        if (mu_texture_upload_file(path, kind, &t->images[i], &t->components[i], error, sizeof error) == 0 &&
            t->images[i].width > 0) {
            t->slots[i] = &t->images[i];
            e->bitmap_present[i] = 1;
        }
    }
}

int mu_world_env_open(mu_world_env *e, const char *root, const mu_world *map, int32_t world, uint32_t seed,
                      int no_assets, int tga_leaves, char *error, size_t error_size)
{
    memset(e, 0, sizeof *e);
    if (!map) {
        snprintf(error, error_size, "no terrain");
        return 1;
    }
    e->world = world;
    e->map = map;
    e->tga_leaves = tga_leaves;
    mu_env_world_info_get(world, &e->info);
    mu_env_host h;
    memset(&h, 0, sizeof h);
    h.context = e;
    h.terrain_height = h_terrain;
    h.play_sound = h_sound;
    h.set_action = h_set_action;
    h.animate = h_animate;
    h.create_particle = h_particle;
    h.kill = h_kill;
    h.init = h_init;
    h.create_effect = h_effect;   /* has_model NULL: the world's models count as loaded, as in the client */
    mu_env_init(&e->env, seed, &h);
    add_world_models(e, root, no_assets);
    load_bitmaps(e, root, no_assets);
    return 0;
}

void mu_world_env_close(mu_world_env *e)
{
    for (int32_t i = 0; i < e->model_count; ++i) {
        mu_world_env_model *m = &e->models[i];
        if (!m->loaded)
            continue;
        mu_textures_free(&m->textures);
        mu_model_free(&m->model);
        mu_bmd_free(&m->bmd);
    }
    mu_textures *t = &e->bitmaps;
    if (t->images)
        for (int i = 0; i < t->count; ++i)
            mu_image_free(&t->images[i]);
    free(t->images);
    free(t->slots);
    free(t->components);
    free(t->filter);
    free(t->wrap);
    memset(e, 0, sizeof *e);
}

/* ---- tick ---- */

void mu_world_env_step(mu_world_env *e, const mu_world_env_hero *hero, const float camera[3], float world_time)
{
    mu_env_inputs *in = &e->inputs;
    memset(in, 0, sizeof *in);
    in->world = e->world;
    for (int k = 0; k < 3; ++k) {
        in->hero_position[k] = hero->position[k];
        in->camera_position[k] = camera[k];
    }
    in->hero_tile[0] = hero->tile[0];
    in->hero_tile[1] = hero->tile[1];
    in->hero_action = hero->action;
    in->hero_safe_zone = hero->safe_zone;
    in->world_time = world_time;
    in->frame_time = 0.1f;   /* [0x01cf103c] */
    in->attributes = e->map->attributes;
    in->layer1 = e->map->layer1;
    int weather = e->world == 0x8d ? e->env.tormenta.weather : 0;
    if (mu_env_leaves_active(e->world, hero->hero_tile, weather)) {
        mu_env_move_leaves(&e->env, in);
        e->stats.leaf_steps++;
    }
    mu_env_move_boids(&e->env, in);
    mu_env_move_fishs(&e->env, in);
    e->stats.steps++;
    uint32_t boids = 0, fishs = 0, leaves = 0;
    for (int i = 0; i < MU_ENV_BOIDS; ++i)
        boids += e->env.boids[i].live;
    for (int i = 0; i < MU_ENV_FISHS; ++i)
        fishs += e->env.fishs[i].live;
    for (int i = 0; i < MU_ENV_LEAVES; ++i)
        leaves += e->env.leaves[i].live;
    e->stats.live_boids = boids;
    e->stats.live_fishs = fishs;
    e->stats.live_leaves = leaves;
    if (boids > e->stats.max_boids)
        e->stats.max_boids = boids;
    if (fishs > e->stats.max_fishs)
        e->stats.max_fishs = fishs;
    if (leaves > e->stats.max_leaves)
        e->stats.max_leaves = leaves;
}

/* ---- draw ---- */

typedef struct draw_context {
    mu_world_env *e;
    const mu_world_env_target *target;
    const mu_terrain_frustum *frustum;
    long drawn;
    float color[4];   /* glColor3f of RenderLeaves */
} draw_context;

static int r_frustum(void *c, float x, float y, float range)
{
    draw_context *d = c;
    if (!d->frustum)
        return 1;
    return mu_terrain_test_frustum_2d(d->frustum->x2d, d->frustum->y2d, 6, x, y, range);
}

static void r_object(void *c, const mu_env_object *o, int32_t a1)
{
    draw_context *d = c;
    (void)a1;
    mu_world_env *e = d->e;
    int32_t slot = -1;
    for (int32_t i = 0; i < e->model_count; ++i)
        if (e->models[i].type == o->type && e->models[i].loaded)
            slot = i;
    if (slot < 0)
        return;
    mu_world_env_model *m = &e->models[slot];
    mu_render_backend backend;
    if (d->target->backend(d->target->context, e, slot, &backend))
        return;
    mu_model_params p = m->model.params;
    for (int k = 0; k < 3; ++k) {
        p.origin[k] = o->position[k];
        p.angles[k] = o->angle[k];
        p.color[k] = o->light[k];   /* viewer choice: RenderObject's light is not reconstructed */
    }
    p.body_scale = o->scale;
    mu_model_apply_params(&m->model, &p);
    mu_model_set_state(&m->model, o->action, o->frame, o->prior_frame, o->prior_action);
    if (mu_model_pose(&m->model) != MU_MODEL_OK || mu_model_transform_all(&m->model) != MU_MODEL_OK)
        return;
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = &m->textures;
    options.alpha = o->alpha;
    mu_draw_stats ds = {0, 0, 0, 0};
    if (!mu_scene_draw_model(&m->model, &options, &backend, &ds)) {
        d->drawn++;
        e->stats.drawn_objects++;
    }
}

static void r_sprite(void *c, int32_t bitmap, const float p[3], float scale, const float l[3], const mu_env_object *o)
{
    mu_world_env *e = ((draw_context *)c)->e;
    e->stats.sprites++;
    /* CreateSprite 0x01692eb7(bitmap, position, scale, light, owner, 0, 0 (additive), 4) (NATIVE-PARTICLE-001) */
    if (e->particles)
        mu_world_particles_sprite(e->particles, bitmap, p, scale, l, (int32_t)(o - e->env.boids), 0.0f, 0, 4);
}

static void r_bone(void *c, const mu_env_object *o, int32_t bone, const float v[3], float out[3])
{
    mu_world_env *e = ((draw_context *)c)->e;
    mu_world_env_model *m = model_of(e, o->type);
    /* TransformPosition 0x012b6ef1(BoneTransform[bone], v, out, 1) on the model r_object just posed */
    if (e->particles && m && m->loaded && mu_world_particles_bone_position(&m->model, bone, v, out))
        return;
    out[0] = v[0];
    out[1] = v[1];
    out[2] = v[2];
}

static void r_alpha_test(void *c, int32_t arg)
{
    (void)arg;
    ((draw_context *)c)->e->blend = 0;
}

static void r_alpha_blend(void *c) { ((draw_context *)c)->e->blend = 1; }

static void r_shadow(void *c, const mu_env_object *o, const float origin[3])
{
    draw_context *d = c;
    mu_world_env *e = d->e;
    e->stats.shadows++;
    if (!e->particles)
        return;
    /* RenderBodyShadow 0x012bc07a with BodyOrigin = origin (the terrain under the object), on the model r_object
     * just posed and transformed (NATIVE-PARTICLE-001) */
    int32_t slot = -1;
    for (int32_t i = 0; i < e->model_count; ++i)
        if (e->models[i].type == o->type && e->models[i].loaded)
            slot = i;
    if (slot < 0)
        return;
    mu_world_env_model *m = &e->models[slot];
    mu_render_backend backend;
    if (d->target->backend(d->target->context, e, slot, &backend))
        return;
    mu_model_params p = m->model.params;
    for (int k = 0; k < 3; ++k)
        p.origin[k] = origin[k];
    mu_model_apply_params(&m->model, &p);   /* BodyOrigin (model +0x78) only: the vertices stay as transformed */
    mu_world_particles_shadow(e->particles, &m->model, &m->bmd, e->shadow_rgba, &backend);
}

static void r_bind(void *c, int32_t bitmap)
{
    mu_world_env *e = ((draw_context *)c)->e;
    e->slot = -1;
    for (int i = 0; i < MU_WORLD_ENV_BITMAPS; ++i)
        if (bitmap_ids[i] == bitmap)
            e->slot = i;
}

static int r_has_bitmap(void *c, int32_t bitmap)
{
    mu_world_env *e = ((draw_context *)c)->e;
    for (int i = 0; i < MU_WORLD_ENV_BITMAPS; ++i)
        if (bitmap_ids[i] == bitmap)
            return e->bitmap_present[i];
    return 0;
}

/* One textured quad through the backend, as two triangles. */
static void quad(draw_context *d, const float v[4][3], const float rgba[4])
{
    mu_world_env *e = d->e;
    if (e->slot < 0)
        return;
    mu_render_backend b;
    if (d->target->backend(d->target->context, e, -1, &b))
        return;
    mu_meshdraw_state s;
    mu_meshdraw_state_defaults(&s);
    s.texture = 1;
    s.cull = 0;
    s.blend = 1;
    if (e->blend) {   /* EnableAlphaBlend 0x0184aa2b */
        s.src = MU_GL_ONE;
        s.dst = MU_GL_ONE;
        s.depth_mask = 0;
        s.alpha_test = 0;
    } else {          /* EnableAlphaTest 0x0184a990(1) */
        s.src = MU_GL_SRC_ALPHA;
        s.dst = MU_GL_ONE_MINUS_SRC_ALPHA;
        s.depth_mask = 1;
        s.alpha_test = 1;
    }
    b.prepare(b.context, &s, e->slot);
    b.begin(b.context);
    static const float uv[4][2] = {{0.0f, 1.0f}, {1.0f, 1.0f}, {1.0f, 0.0f}, {0.0f, 0.0f}};
    static const int order[6] = {0, 1, 2, 0, 2, 3};
    for (int i = 0; i < 6; ++i) {
        b.sink.texcoord(b.sink.context, uv[order[i]][0], uv[order[i]][1]);
        b.sink.color4(b.sink.context, rgba[0], rgba[1], rgba[2], rgba[3]);
        b.sink.vertex(b.sink.context, v[order[i]]);
    }
    b.end(b.context);
    d->drawn++;
    e->stats.drawn_leaves++;
}

static void r_color3(void *c, float r, float g, float b)
{
    draw_context *d = c;
    d->color[0] = r;
    d->color[1] = g;
    d->color[2] = b;
    d->color[3] = 1.0f;
}

static void r_color4(void *c, float r, float g, float b, float a)
{
    mu_world_env *e = ((draw_context *)c)->e;   /* the shadow colour */
    e->shadow_rgba[0] = r;
    e->shadow_rgba[1] = g;
    e->shadow_rgba[2] = b;
    e->shadow_rgba[3] = a;
}

static void r_plane(void *c, const float p[3], const float corners[4][3], int32_t count)
{
    draw_context *d = c;
    if (!count || !corners)
        return;
    float v[4][3];
    for (int i = 0; i < 4; ++i)
        for (int k = 0; k < 3; ++k)
            v[i][k] = corners[i][k] + p[k];   /* glTranslatef(position) */
    quad(d, (const float(*)[3])v, d->color);
}

static void r_billboard(void *c, int32_t bitmap, const float p[3], float w, float h, const float l[3])
{
    draw_context *d = c;
    mu_world_env *e = d->e;
    float eye[4][3], v[4][3], rgba[4];
    mu_env_billboard_quad((const float(*)[4])e->camera, p, w, h, eye);
    int slot = -1;
    for (int i = 0; i < MU_WORLD_ENV_BITMAPS; ++i)
        if (bitmap_ids[i] == bitmap)
            slot = i;
    int components = slot >= 0 ? e->bitmaps.components[slot] : 4;
    mu_env_billboard_color(bitmap, components, l, rgba);
    if (components == 3)
        rgba[3] = 1.0f;
    /* view space back to world space: x = R^T (v - t) (the camera rows are orthonormal) */
    for (int i = 0; i < 4; ++i)
        for (int k = 0; k < 3; ++k) {
            float s = 0.0f;
            for (int r = 0; r < 3; ++r)
                s += e->camera[r][k] * (eye[i][r] - e->camera[r][3]);
            v[i][k] = s;
        }
    quad(d, (const float(*)[3])v, rgba);
}

long mu_world_env_draw(mu_world_env *e, const float modelview[16], const mu_terrain_frustum *frustum,
                       const mu_world_env_target *target)
{
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 4; ++j)
            e->camera[i][j] = modelview[4 * j + i];   /* 0x0184a569: CameraMatrix[i][j] = gl[4j + i] */
    draw_context d = {e, target, frustum, 0, {1.0f, 1.0f, 1.0f, 1.0f}};
    mu_env_render_host r;
    memset(&r, 0, sizeof r);
    r.context = &d;
    r.frustum = r_frustum;
    r.draw_object = r_object;
    r.sprite = r_sprite;
    r.bone_position = r_bone;
    r.alpha_test = r_alpha_test;
    r.alpha_blend = r_alpha_blend;
    r.color4 = r_color4;
    r.color3 = r_color3;
    r.shadow = r_shadow;
    r.bind = r_bind;
    r.plane = r_plane;
    r.billboard = r_billboard;
    r.has_bitmap = r_has_bitmap;
    e->stats.drawn_objects = e->stats.drawn_leaves = 0;
    e->stats.shadows = e->stats.sprites = 0;
    e->slot = -1;
    e->blend = 0;
    mu_env_render_boids(&e->env, &e->inputs, 0, &r);
    mu_env_render_fishs(&e->env, &e->inputs, &r);
    mu_env_render_leaves(&e->env, &e->inputs, &r);
    mu_env_render_boids(&e->env, &e->inputs, 1, &r);
    return d.drawn;
}

typedef struct raster_target {
    mu_raster *raster;
    mu_render_backend backend;
} raster_target;

static int raster_backend(void *c, const mu_world_env *e, int32_t slot, mu_render_backend *out)
{
    raster_target *t = c;
    const mu_textures *tex = slot < 0 ? &e->bitmaps : &e->models[slot].textures;
    t->raster->textures = tex->slots;
    t->raster->texture_count = tex->count;
    t->raster->texture_filter = tex->filter;
    t->raster->texture_wrap = tex->wrap;
    *out = t->backend;
    return 0;
}

long mu_world_env_draw_raster(mu_world_env *e, mu_raster *raster, const float modelview[16],
                              const mu_terrain_frustum *frustum)
{
    raster_target t = {raster, {0}};
    mu_raster_backend(raster, &t.backend);
    const int linear = raster->linear;
    raster->linear = 0;
    mu_world_env_target target = {&t, raster_backend};
    long n = mu_world_env_draw(e, modelview, frustum, &target);
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
    raster->linear = linear;
    return n;
}

void mu_world_env_clear(const mu_world_env *e, uint8_t rgba[4])
{
    for (int k = 0; k < 3; ++k) {
        float v = e->info.clear[k] * 255.0f + 0.5f;
        rgba[k] = (uint8_t)(v < 0.0f ? 0.0f : v > 255.0f ? 255.0f : v);
    }
    rgba[3] = 255;
}
