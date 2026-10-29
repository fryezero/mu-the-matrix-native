#define _POSIX_C_SOURCE 200809L
#include "mu_effect_scene.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

static float flat_height(void *context, float x, float y)
{
    (void)context;
    (void)x;
    (void)y;
    return 0.0f;
}

static void flat_normal(void *context, float x, float y, float out[3])
{
    (void)context;
    (void)x;
    (void)y;
    out[0] = 0.0f;
    out[1] = 0.0f;
    out[2] = 1.0f;
}

static float world_height(void *context, float x, float y)
{
    return mu_world_height_at((const mu_world *)context, x, y);
}

static void world_normal(void *context, float x, float y, float out[3])
{
    const mu_world *w = context;
    int32_t xi = (int32_t)(x / 100.0f), yi = (int32_t)(y / 100.0f);
    xi = xi < 0 ? 0 : xi > 255 ? 255 : xi;
    yi = yi < 0 ? 0 : yi > 255 ? 255 : yi;
    const float *n = &w->normal[3 * (yi * 256 + xi)];
    out[0] = n[0];
    out[1] = n[1];
    out[2] = n[2];
}

int mu_effect_scene_init(mu_effect_scene *s, const char *game_root, uint32_t seed)
{
    memset(s, 0, sizeof *s);
    snprintf(s->root, sizeof s->root, "%s", game_root ? game_root : ".");
    mu_fx_rng_seed(&s->rng, seed);
    s->tree = mu_fx_octree_create(MU_FX_OCTREE_ROOT, 0);   /* EffectManager init 0x00a79534 */
    mu_effect_scene_set_world(s, NULL);
    return s->tree ? MU_EFFECT_OK : MU_EFFECT_ERROR;
}

void mu_effect_scene_set_world(mu_effect_scene *s, const mu_world *world)
{
    s->world = world;
    s->terrain.context = (void *)world;
    s->terrain.height = world ? world_height : flat_height;
    s->terrain.normal = world ? world_normal : flat_normal;
}

void mu_effect_scene_free(mu_effect_scene *s)
{
    mu_fx_octree_free(s->tree);
    for (uint32_t i = 0; i < s->instance_count; ++i)
        mu_fx_free(&s->instances[i].fx);
    for (uint32_t i = 0; i < s->template_count; ++i)
        mu_effect_free(&s->templates[i]);
    free(s->instances);
    free(s->templates);
    free(s->template_keys);
    free(s->vertices);
    memset(s, 0, sizeof *s);
}

static void set_managed(mu_fx_effect *e)
{
    e->managed = 1;   /* the factory constructs templates with the manager (+0x28) */
    for (uint32_t i = 0; i < e->child_count; ++i)
        set_managed(e->children[i]);
}

static int find_template(mu_effect_scene *s, const char *client_path, char *error, unsigned long error_size)
{
    for (uint32_t i = 0; i < s->template_count; ++i)
        if (!strcasecmp(s->template_keys[i], client_path))
            return (int)i;
    if (s->template_count == s->template_capacity) {
        uint32_t capacity = s->template_capacity ? 2u * s->template_capacity : 16u;
        mu_effect *t = realloc(s->templates, capacity * sizeof *t);
        if (!t)
            return -1;
        s->templates = t;
        char (*k)[256] = realloc(s->template_keys, capacity * sizeof *k);
        if (!k)
            return -1;
        s->template_keys = k;
        s->template_capacity = capacity;
    }
    char path[4096];
    if (!mu_effect_resolve_path(s->root, client_path, path, sizeof path)) {
        snprintf(error, error_size, "%s not found under %s", client_path, s->root);
        return -1;
    }
    mu_effect *t = &s->templates[s->template_count];
    if (mu_effect_load_file(t, path, s->root, 0, error, error_size) != MU_EFFECT_OK)
        return -1;
    /* Templates are never updated; their children's parent links point at the
     * template root, which only the clone reads through child lists. */
    set_managed(&t->fx);
    snprintf(s->template_keys[s->template_count], sizeof s->template_keys[0], "%s", client_path);
    if (t->vertex_capacity > s->vertex_capacity) {
        mu_fx_vertex *v = realloc(s->vertices, t->vertex_capacity * sizeof *v);
        if (!v)
            return -1;
        s->vertices = v;
        s->vertex_capacity = t->vertex_capacity;
    }
    return (int)s->template_count++;
}

int mu_effect_scene_create(mu_effect_scene *s, const char *client_path, const float position[3],
                           const float rotation[3], float scale, int use_template_transform, int owner_tint,
                           const int32_t *actions, uint32_t action_count, float start_frame, char *error,
                           unsigned long error_size)
{
    int t = find_template(s, client_path, error, error_size);
    if (t < 0)
        return -1;
    if (s->instance_count == s->instance_capacity) {
        /* Instances are linked into the octree and their children point at
         * their root, so the array is sized once and never moved. */
        if (s->instance_capacity) {
            snprintf(error, error_size, "scene is full (%u instances)", s->instance_capacity);
            return -1;
        }
        s->instance_capacity = s->instance_limit ? s->instance_limit : 256;
        s->instances = calloc(s->instance_capacity, sizeof *s->instances);
        if (!s->instances)
            return -1;
    }
    mu_effect_instance *inst = &s->instances[s->instance_count];
    memset(inst, 0, sizeof *inst);
    const mu_fx_effect *source = &s->templates[t].fx;
    if (use_template_transform) {
        position = source->position;
        rotation = source->rotation;
        scale = source->scale;
    }
    if (!mu_fx_clone(&inst->fx, source, position, rotation, scale, owner_tint, actions, action_count, start_frame)) {
        snprintf(error, error_size, "out of memory");
        return -1;
    }
    inst->template_index = (uint32_t)t;
    inst->owner.visible = 1;
    mu_fx_set_owner(&inst->fx, &inst->owner);
    return (int)s->instance_count++;
}

int mu_effect_scene_template(mu_effect_scene *s, const char *client_path, char *error, unsigned long error_size)
{
    return find_template(s, client_path, error, error_size);
}

void mu_effect_scene_update_one(mu_effect_scene *s, uint32_t instance, float dt)
{
    if (instance >= s->instance_count)
        return;
    mu_effect_instance *inst = &s->instances[instance];
    mu_fx_node_update(&inst->fx, dt, inst->has_external ? inst->external : NULL, &inst->owner, &s->rng, &s->terrain,
                      s->tree);
}

void mu_effect_scene_attach(mu_effect_scene *s, uint32_t instance, const float matrix[16])
{
    if (instance >= s->instance_count)
        return;
    memcpy(s->instances[instance].external, matrix, sizeof s->instances[instance].external);
    s->instances[instance].has_external = 1;
}

void mu_effect_object_matrix(float out[16], const float position[3], float scale)
{
    memset(out, 0, 16 * sizeof(float));
    out[0] = out[5] = out[10] = scale;
    out[12] = position[0];
    out[13] = position[1];
    out[14] = position[2];
    out[15] = 1.0f;
}

void mu_effect_scene_update(mu_effect_scene *s, float dt)
{
    for (uint32_t i = 0; i < s->instance_count; ++i) {
        mu_effect_instance *inst = &s->instances[i];
        mu_fx_node_update(&inst->fx, dt, inst->has_external ? inst->external : NULL, &inst->owner, &s->rng,
                          &s->terrain, s->tree);
    }
}

static const mu_image *node_texture(mu_effect_scene *s, const mu_fx_effect *node)
{
    for (uint32_t i = 0; i < s->instance_count; ++i) {
        mu_effect_instance *inst = &s->instances[i];
        uint32_t n = mu_fx_tree_count(&inst->fx);
        for (uint32_t k = 0; k < n; ++k)
            if (mu_fx_tree_node(&inst->fx, k) == node)
                return mu_effect_node_texture(&s->templates[inst->template_index], k);
    }
    return NULL;
}

static void normalize(float v[3])
{
    double l = sqrt((double)v[0] * v[0] + (double)v[1] * v[1] + (double)v[2] * v[2]);
    if (l > 0.0)
        for (int k = 0; k < 3; ++k)
            v[k] = (float)(v[k] / l);
}

static void raster_draw(void *context, const mu_fx_vertex *vertices, uint32_t count, const mu_fx_draw_state *state,
                        const mu_image *texture, const float *matrix)
{
    mu_effect_raster_quads((mu_raster *)context, vertices, count, state, texture, matrix);
}

uint32_t mu_effect_scene_render(mu_effect_scene *s, const float eye[3], const float target[3], float fov_degrees,
                                float aspect, float near_plane, float far_plane, mu_raster *raster)
{
    return mu_effect_scene_render_to(s, eye, target, fov_degrees, aspect, near_plane, far_plane,
                                     raster ? raster_draw : NULL, raster);
}

uint32_t mu_effect_scene_render_to(mu_effect_scene *s, const float eye[3], const float target[3], float fov_degrees,
                                   float aspect, float near_plane, float far_plane, mu_effect_draw_fn draw,
                                   void *context)
{
    float forward[3] = {target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]};
    normalize(forward);
    float up[3] = {0.0f, 0.0f, 1.0f};
    float d = forward[2];
    for (int k = 0; k < 3; ++k)
        up[k] -= d * forward[k];
    normalize(up);
    mu_fx_frustum_set(&s->frustum, eye, forward, up, fov_degrees * (float)(3.14159265358979 / 180.0), aspect,
                      near_plane, far_plane);
    uint32_t total = 0;
    for (uint32_t i = 0; i < s->instance_count; ++i)
        total += mu_fx_tree_count(&s->instances[i].fx);
    mu_fx_effect **visible = calloc(total ? total : 1u, sizeof *visible);
    if (!visible)
        return 0;
    uint32_t n = mu_fx_octree_query(s->tree, &s->frustum, visible, total);
    if (n > total)
        n = total;
    s->visible = n;
    s->vertices_drawn = 0;
    for (uint32_t i = 0; i < n; ++i) {   /* 0x00a7a30e: draws in octree order */
        const mu_image *texture = node_texture(s, visible[i]);
        mu_fx_draw_state state;
        uint32_t count = mu_fx_draw(visible[i], &s->frustum.camera, texture != NULL, s->vertices, &state);
        if (draw)
            draw(context, s->vertices, count, &state, texture, state.multiply_matrix ? visible[i]->matrix : NULL);
        s->vertices_drawn += count;
    }
    free(visible);
    return n;
}
