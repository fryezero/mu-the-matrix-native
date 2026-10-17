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
