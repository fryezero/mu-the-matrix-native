/* Flat handle API over the reconstructed effect module for the equivalence
 * harness (scripts/validate_effects.py) and the portable tests (ctypes). */
#include "effects.h"

#include <stdlib.h>
#include <string.h>

typedef struct mu_fx_handle {
    mu_fx_effect effect;
    mu_fx_rng rng;
    mu_fx_terrain terrain;
    float plane[4];           /* terrain z = plane[0] + plane[1]*x + plane[2]*y; normal from the slopes */
    int use_terrain;
    mu_fx_vertex *vertices;
    uint32_t vertex_capacity;
} mu_fx_handle;

static float plane_height(void *context, float x, float y)
{
    const float *p = context;
    float h = p[1] * x;
    h = h + p[2] * y;
    return p[0] + h;
}

static void plane_normal(void *context, float x, float y, float out[3])
{
    const float *p = context;
    (void)x;
    (void)y;
    out[0] = -p[1];
    out[1] = -p[2];
    out[2] = 1.0f;
}

mu_fx_handle *mu_fx_open(const char *text, size_t length, uint32_t seed, char *error, size_t error_size)
{
    mu_fx_handle *h = calloc(1, sizeof *h);
    if (!h)
        return NULL;
    if (mu_fx_load_json(&h->effect, text, length, error, error_size) != MU_FX_OK) {
        free(h);
        return NULL;
    }
    mu_fx_rng_seed(&h->rng, seed);
    h->vertex_capacity = h->effect.type == MU_FX_PARTICLE_SYSTEM ? 4u * h->effect.capacity : 4u;
    h->vertices = calloc(h->vertex_capacity ? h->vertex_capacity : 1u, sizeof *h->vertices);
    if (!h->vertices) {
        mu_fx_free(&h->effect);
        free(h);
        return NULL;
    }
    h->terrain.context = h->plane;
    h->terrain.height = plane_height;
    h->terrain.normal = plane_normal;
    return h;
}

void mu_fx_close(mu_fx_handle *h)
{
    if (!h)
        return;
    mu_fx_free(&h->effect);
    free(h->vertices);
    free(h);
}

/* Terrain stand-in for the collider: z = a + b*x + c*y, normal (-b, -c, 1)
 * (not normalised, like whatever the caller's normal routine returns). */
void mu_fx_set_plane(mu_fx_handle *h, float a, float b, float c)
{
    h->plane[0] = a;
    h->plane[1] = b;
    h->plane[2] = c;
    h->use_terrain = 1;
}

/* Overrides used by the mutation cases. */
void mu_fx_set_transform(mu_fx_handle *h, const float position[3], const float rotation[3], float scale)
{
    memcpy(h->effect.position, position, 3 * sizeof(float));
    memcpy(h->effect.rotation, rotation, 3 * sizeof(float));
    h->effect.scale = scale;
}

void mu_fx_frame_update(mu_fx_handle *h, float dt)
{
    mu_fx_update(&h->effect, dt, &h->rng, h->use_terrain ? &h->terrain : NULL);
}

/* camera: position, forward, up (9 floats). Returns the vertex count and
 * writes the vertices (36 bytes each) and the draw state words:
 * visible, blend, src, dst, texture, multiply_matrix, disable_cull. */
uint32_t mu_fx_frame_draw(mu_fx_handle *h, const float camera[9], int texture_loaded, void *vertices,
                          uint32_t state[7])
{
    mu_fx_camera c;
    mu_fx_camera_set(&c, camera, camera + 3, camera + 6);
    mu_fx_draw_state s;
    uint32_t n = mu_fx_draw(&h->effect, &c, texture_loaded, h->vertices, &s);
    if (vertices && n)
        memcpy(vertices, h->vertices, (size_t)n * sizeof(mu_fx_vertex));
    if (state) {
        state[0] = s.visible;
        state[1] = s.blend;
        state[2] = s.src;
        state[3] = s.dst;
        state[4] = s.texture;
        state[5] = s.multiply_matrix;
        state[6] = s.disable_cull;
    }
    return n;
}

const void *mu_fx_particle_records(mu_fx_handle *h, uint32_t *count)
{
    *count = h->effect.count;
    return h->effect.particles;
}

uint32_t mu_fx_capacity(mu_fx_handle *h) { return h->effect.capacity; }
int mu_fx_type(mu_fx_handle *h) { return h->effect.type; }
int mu_fx_faulted(mu_fx_handle *h) { return h->effect.faulted; }
uint64_t mu_fx_rand_calls(mu_fx_handle *h) { return h->rng.calls; }
uint32_t mu_fx_rand_state(mu_fx_handle *h) { return h->rng.state; }
float mu_fx_time_left(mu_fx_handle *h) { return h->effect.time_left; }
const float *mu_fx_matrix(mu_fx_handle *h) { return h->effect.matrix; }
const char *mu_fx_texture(mu_fx_handle *h) { return h->effect.texture; }

/* ---- effect trees, owners, clones and the EffectManager octree (NATIVE-FX-002,
 * scripts/validate_effect_tree.py). A handle holds a scene of up to 16 root
 * effects sharing one random sequence, one owner and (when managed) one
 * octree; node indices run over the roots in order, each in pre-order. ---- */

enum { MU_FXT_ROOTS = 16 };

typedef struct mu_fxt_handle {
    mu_fx_effect roots[MU_FXT_ROOTS];
    mu_fx_effect templates[MU_FXT_ROOTS];
    uint8_t has_template[MU_FXT_ROOTS];
    uint32_t root_count;
    int managed;
    mu_fx_rng rng;
    mu_fx_owner owner;
    int use_owner;
    mu_fx_octree_node *tree;
    mu_fx_frustum frustum;
    mu_fx_vertex *vertices;
    uint32_t vertex_capacity;
    mu_fx_terrain terrain;
    float plane[4];
} mu_fxt_handle;

static uint32_t max_vertices(const mu_fx_effect *e)
{
    uint32_t n = e->type == MU_FX_PARTICLE_SYSTEM ? 4u * e->capacity : 4u;
    for (uint32_t i = 0; i < e->child_count; ++i) {
        uint32_t c = max_vertices(e->children[i]);
        if (c > n)
            n = c;
    }
    return n;
}

static void set_managed(mu_fx_effect *e, uint8_t managed)
{
    e->managed = managed;
    for (uint32_t i = 0; i < e->child_count; ++i)
        set_managed(e->children[i], managed);
}

static mu_fx_effect *node_at(mu_fxt_handle *h, uint32_t index)
{
    for (uint32_t r = 0; r < h->root_count; ++r) {
        uint32_t n = mu_fx_tree_count(&h->roots[r]);
        if (index < n)
            return mu_fx_tree_node(&h->roots[r], index);
        index -= n;
    }
    return NULL;
}

static int grow_vertices(mu_fxt_handle *h, const mu_fx_effect *e)
{
    uint32_t n = max_vertices(e);
    if (n <= h->vertex_capacity && h->vertices)
        return 1;
    mu_fx_vertex *v = realloc(h->vertices, (n ? n : 1u) * sizeof *v);
    if (!v)
        return 0;
    h->vertices = v;
    h->vertex_capacity = n;
    return 1;
}

mu_fxt_handle *mu_fxt_new(uint32_t seed, int managed)
{
    mu_fxt_handle *h = calloc(1, sizeof *h);
    if (!h)
        return NULL;
    mu_fx_rng_seed(&h->rng, seed);
    h->managed = managed != 0;
    h->terrain.context = h->plane;   /* flat ground z = 0 unless mu_fxt_set_plane changes it */
    h->terrain.height = plane_height;
    h->terrain.normal = plane_normal;
    if (managed && !(h->tree = mu_fx_octree_create(MU_FX_OCTREE_ROOT, 0))) {
        free(h);
        return NULL;
    }
    return h;
}

/* Loads one more root; returns its root index or -1. */
int mu_fxt_add(mu_fxt_handle *h, const char *text, size_t length, char *error, size_t error_size)
{
    if (h->root_count == MU_FXT_ROOTS)
        return -1;
    mu_fx_effect *e = &h->roots[h->root_count];
    if (mu_fx_load_json(e, text, length, error, error_size) != MU_FX_OK)
        return -1;
    set_managed(e, (uint8_t)h->managed);
    if (h->use_owner)
        mu_fx_set_owner(e, &h->owner);
    if (!grow_vertices(h, e)) {
        mu_fx_free(e);
        return -1;
    }
    return (int)h->root_count++;
}

void mu_fxt_close(mu_fxt_handle *h)
{
    if (!h)
        return;
    mu_fx_octree_free(h->tree);
    for (uint32_t r = 0; r < h->root_count; ++r) {
        mu_fx_free(&h->roots[r]);
        if (h->has_template[r])
            mu_fx_free(&h->templates[r]);
    }
    free(h->vertices);
    free(h);
}

/* Replaces root r by an instance of itself (the loaded tree becomes the template). */
int mu_fxt_clone(mu_fxt_handle *h, uint32_t r, const float position[3], const float rotation[3], float scale,
                 int owner_tint, const int32_t *actions, uint32_t action_count, float start_frame)
{
    if (r >= h->root_count || h->has_template[r])
        return 0;
    h->templates[r] = h->roots[r];
    h->has_template[r] = 1;
    memset(&h->roots[r], 0, sizeof h->roots[r]);
    if (!mu_fx_clone(&h->roots[r], &h->templates[r], position, rotation, scale, owner_tint, actions, action_count,
                     start_frame))
        return 0;
    if (h->use_owner)
        mu_fx_set_owner(&h->roots[r], &h->owner);
    return 1;
}

uint32_t mu_fxt_node_count(mu_fxt_handle *h)
{
    uint32_t n = 0;
    for (uint32_t r = 0; r < h->root_count; ++r)
        n += mu_fx_tree_count(&h->roots[r]);
    return n;
}

int mu_fxt_node_type(mu_fxt_handle *h, uint32_t index)
{
    mu_fx_effect *e = node_at(h, index);
    return e ? e->type : -1;
}

void mu_fxt_set_transform(mu_fxt_handle *h, uint32_t index, const float position[3], const float rotation[3],
                          float scale)
{
    mu_fx_effect *e = node_at(h, index);
    if (!e)
        return;
    memcpy(e->position, position, 3 * sizeof(float));
    memcpy(e->rotation, rotation, 3 * sizeof(float));
    e->scale = scale;
}

/* Owner fields: flag5, flag6, action, visible, frame, tint[3]. */
void mu_fxt_set_owner(mu_fxt_handle *h, int flag5, int flag6, int action, int visible, float frame,
                      const float tint[3])
{
    h->owner.flag5 = (uint8_t)flag5;
    h->owner.flag6 = (uint8_t)flag6;
    h->owner.action = (uint16_t)action;
    h->owner.visible = (uint8_t)visible;
    h->owner.frame = frame;
    memcpy(h->owner.tint, tint, 3 * sizeof(float));
    if (!h->use_owner) {
        h->use_owner = 1;
        for (uint32_t r = 0; r < h->root_count; ++r)
            mu_fx_set_owner(&h->roots[r], &h->owner);
    }
}

/* Gate and tint settings on one node. */
int mu_fxt_set_gate(mu_fxt_handle *h, uint32_t index, int owner_tint, const int32_t *actions, uint32_t count,
                    float start_frame)
{
    mu_fx_effect *e = node_at(h, index);
    if (!e)
        return 0;
    free(e->actions);
    e->actions = NULL;
    e->action_count = 0;
    if (count) {
        e->actions = malloc(count * sizeof *e->actions);
        if (!e->actions)
            return 0;
        memcpy(e->actions, actions, count * sizeof *e->actions);
        e->action_count = count;
    }
    e->start_frame = start_frame;
    e->owner_tint = (uint8_t)(owner_tint != 0);
    return 1;
}

/* Node update of root r with an optional external matrix; 0 on a fault. */
int mu_fxt_update(mu_fxt_handle *h, uint32_t r, float dt, const float *external)
{
    if (r >= h->root_count)
        return 0;
    return mu_fx_node_update(&h->roots[r], dt, external, h->use_owner ? &h->owner : NULL, &h->rng, &h->terrain,
                             h->tree);
}

static uint32_t draw_node(mu_fxt_handle *h, mu_fx_effect *e, const mu_fx_camera *c, int texture_loaded,
                          void *vertices, uint32_t state[7])
{
    mu_fx_draw_state s;
    uint32_t n = mu_fx_draw(e, c, texture_loaded, h->vertices, &s);
    if (vertices && n)
        memcpy(vertices, h->vertices, (size_t)n * sizeof(mu_fx_vertex));
    if (state) {
        state[0] = s.visible; state[1] = s.blend; state[2] = s.src; state[3] = s.dst;
        state[4] = s.texture; state[5] = s.multiply_matrix; state[6] = s.disable_cull;
    }
    return n;
}

uint32_t mu_fxt_draw(mu_fxt_handle *h, uint32_t index, const float camera[9], int texture_loaded, void *vertices,
                     uint32_t state[7])
{
    mu_fx_effect *e = node_at(h, index);
    if (!e)
        return 0;
    mu_fx_camera c;
    mu_fx_camera_set(&c, camera, camera + 3, camera + 6);
    return draw_node(h, e, &c, texture_loaded, vertices, state);
}

/* Draw with the frustum record's camera fields (what the manager render passes). */
uint32_t mu_fxt_draw_frustum(mu_fxt_handle *h, uint32_t index, int texture_loaded, void *vertices, uint32_t state[7])
{
    mu_fx_effect *e = node_at(h, index);
    return e ? draw_node(h, e, &h->frustum.camera, texture_loaded, vertices, state) : 0;
}

const void *mu_fxt_particles(mu_fxt_handle *h, uint32_t index, uint32_t *count)
{
    mu_fx_effect *e = node_at(h, index);
    *count = e && e->type == MU_FX_PARTICLE_SYSTEM ? e->count : 0;
    return e ? e->particles : NULL;
}

/* Node record: matrix[16], world position[3], world scale, duration, time
 * left, bbox[6] (28 floats), then bytes playing, drawn, looping, faulted. */
void mu_fxt_node_state(mu_fxt_handle *h, uint32_t index, float out[28], uint8_t flags[4])
{
    mu_fx_effect *e = node_at(h, index);
    if (!e)
        return;
    memcpy(out, e->matrix, 16 * sizeof(float));
    memcpy(out + 16, e->world_position, 3 * sizeof(float));
    out[19] = e->world_scale;
    out[20] = e->duration;
    out[21] = e->time_left;
    memcpy(out + 22, e->bbox, 6 * sizeof(float));
    flags[0] = e->playing;
    flags[1] = e->drawn;
    flags[2] = e->looping;
    flags[3] = e->faulted;
}

uint64_t mu_fxt_rand_calls(mu_fxt_handle *h) { return h->rng.calls; }

/* Terrain stand-in for the collider: z = a + b*x + c*y (as mu_fx_set_plane). */
void mu_fxt_set_plane(mu_fxt_handle *h, float a, float b, float c)
{
    h->plane[0] = a;
    h->plane[1] = b;
    h->plane[2] = c;
}

void mu_fxt_set_frustum(mu_fxt_handle *h, const float eye[3], const float forward[3], const float up[3], float fov,
                        float aspect, float near_plane, float far_plane, float record[36])
{
    mu_fx_frustum_set(&h->frustum, eye, forward, up, fov, aspect, near_plane, far_plane);
    if (record)
        memcpy(record, &h->frustum, sizeof h->frustum);
}

/* Visible nodes in render order as node indices; returns the count. */
uint32_t mu_fxt_query(mu_fxt_handle *h, uint32_t *indices, uint32_t capacity)
{
    enum { LIMIT = 4096 };
    static mu_fx_effect *found[LIMIT];
    uint32_t n = mu_fx_octree_query(h->tree, &h->frustum, found, LIMIT);
    uint32_t total = mu_fxt_node_count(h);
    for (uint32_t i = 0; i < n && i < capacity && i < LIMIT; ++i) {
        indices[i] = 0xffffffffu;
        for (uint32_t k = 0; k < total; ++k)
            if (node_at(h, k) == found[i])
                indices[i] = k;
    }
    return n;
}

/* Octree node holding a tree node: its depth and box, or -1 when not in the tree. */
int mu_fxt_cell(mu_fxt_handle *h, uint32_t index, float box[6])
{
    mu_fx_effect *e = node_at(h, index);
    if (!e || !e->cell)
        return -1;
    memcpy(box, e->cell->bbox, sizeof e->cell->bbox);
    return (int)e->cell->depth;
}

/* before: alpha test, texture 2D, blend, depth mask, blend src, blend dst. */
uint32_t mu_fxt_render_calls(const uint32_t before[6], uint32_t visible, uint32_t out[72])
{
    mu_fx_gl_state s = {(uint8_t)before[0], (uint8_t)before[1], (uint8_t)before[2], (uint8_t)before[3],
                        before[4], before[5]};
    mu_fx_gl_call calls[24];
    uint32_t n = mu_fx_manager_render_calls(&s, visible, calls);
    for (uint32_t i = 0; i < n; ++i) {
        out[3 * i] = calls[i].op;
        out[3 * i + 1] = calls[i].a;
        out[3 * i + 2] = calls[i].b;
    }
    return n;
}

uint32_t mu_fxt_texture_calls(int has_pixels, int32_t width, int32_t height, uint32_t format, uint32_t filter,
                              uint32_t wrap, int mipmap, uint32_t out[36])
{
    mu_fx_gl_call calls[12];
    uint32_t n = mu_fx_texture_upload_calls(has_pixels, width, height, format, filter, wrap, mipmap, calls);
    for (uint32_t i = 0; i < n; ++i) {
        out[3 * i] = calls[i].op;
        out[3 * i + 1] = calls[i].a;
        out[3 * i + 2] = calls[i].b;
    }
    return n;
}
