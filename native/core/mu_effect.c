#define _POSIX_C_SOURCE 200809L
#include "mu_effect.h"
#include "mu_camera.h"

#include <ctype.h>
#include <dirent.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>

static int is_file(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0 && S_ISREG(st.st_mode);
}

static int is_directory(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0 && S_ISDIR(st.st_mode);
}

/* Appends one path component, matching it case-insensitively in `dir`. */
static int append_component(char *path, unsigned long size, const char *component)
{
    size_t used = strlen(path);
    char candidate[4096];
    snprintf(candidate, sizeof candidate, "%s/%s", path, component);
    struct stat st;
    if (stat(candidate, &st) == 0) {
        snprintf(path + used, size - used, "/%s", component);
        return 1;
    }
    DIR *d = opendir(path);
    if (!d)
        return 0;
    struct dirent *entry;
    int found = 0;
    while ((entry = readdir(d)) != NULL) {
        if (!strcasecmp(entry->d_name, component)) {
            snprintf(path + used, size - used, "/%s", entry->d_name);
            found = 1;
            break;
        }
    }
    closedir(d);
    return found;
}

int mu_effect_resolve_path(const char *root, const char *client_path, char *out, unsigned long out_size)
{
    if (!root || !client_path || !*client_path)
        return 0;
    char path[4096];
    snprintf(path, sizeof path, "%s", root);
    size_t n = strlen(path);
    while (n > 1 && path[n - 1] == '/')
        path[--n] = 0;
    const char *p = client_path;
    while (*p) {
        while (*p == '\\' || *p == '/')
            p++;
        if (!*p)
            break;
        char component[512];
        size_t k = 0;
        while (*p && *p != '\\' && *p != '/' && k + 1 < sizeof component)
            component[k++] = *p++;
        component[k] = 0;
        if (!append_component(path, sizeof path, component))
            return 0;
    }
    if (!is_file(path))
        return 0;
    snprintf(out, out_size, "%s", path);
    return 1;
}

/* ROOT/Data/Effect/x.ein -> ROOT (the "Data" component matched case-insensitively). */
static int derive_root(const char *ein_path, char *out, unsigned long size)
{
    char path[4096];
    snprintf(path, sizeof path, "%s", ein_path);
    for (int up = 0; up < 3; ++up) {
        char *slash = strrchr(path, '/');
        if (!slash)
            return 0;
        *slash = 0;
        const char *last = strrchr(path, '/');
        last = last ? last + 1 : path;
        if (!strcasecmp(last, "Data")) {
            char *cut = strrchr(path, '/');
            if (cut)
                *cut = 0;
            else
                snprintf(path, sizeof path, ".");
            if (!is_directory(path))
                return 0;
            snprintf(out, size, "%s", path);
            return 1;
        }
    }
    return 0;
}

static int allocate_vertices(mu_effect *e)
{
    uint32_t need = e->fx.type == MU_FX_PARTICLE_SYSTEM ? 4u * e->fx.capacity : 4u;
    e->vertex_capacity = need;
    e->vertices = calloc(need ? need : 1u, sizeof *e->vertices);
    return e->vertices != NULL;
}

int mu_effect_load_text(mu_effect *e, const char *text, unsigned long length, uint32_t seed, char *error,
                        unsigned long error_size)
{
    memset(e, 0, sizeof *e);
    if (mu_fx_load_json(&e->fx, text, length, error, error_size) != MU_FX_OK)
        return MU_EFFECT_ERROR;
    mu_fx_rng_seed(&e->rng, seed);
    if (!allocate_vertices(e)) {
        mu_fx_free(&e->fx);
        snprintf(error, error_size, "out of memory");
        return MU_EFFECT_ERROR;
    }
    return MU_EFFECT_OK;
}

int mu_effect_load_file(mu_effect *e, const char *path, const char *game_root, uint32_t seed, char *error,
                        unsigned long error_size)
{
    memset(e, 0, sizeof *e);
    FILE *f = fopen(path, "rb");
    if (!f) {
        snprintf(error, error_size, "cannot open %s", path);
        return MU_EFFECT_ERROR;
    }
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (size <= 0 || size > (16L << 20)) {
        fclose(f);
        snprintf(error, error_size, "bad size");
        return MU_EFFECT_ERROR;
    }
    char *text = malloc((size_t)size);
    if (!text || fread(text, 1, (size_t)size, f) != (size_t)size) {
        free(text);
        fclose(f);
        snprintf(error, error_size, "read error");
        return MU_EFFECT_ERROR;
    }
    fclose(f);
    int status = mu_effect_load_text(e, text, (unsigned long)size, seed, error, error_size);
    free(text);
    if (status != MU_EFFECT_OK)
        return status;
    char root[4096];
    if (game_root)
        snprintf(root, sizeof root, "%s", game_root);
    else if (!derive_root(path, root, sizeof root))
        root[0] = 0;
    if (root[0] && mu_effect_resolve_path(root, e->fx.texture, e->texture_path, sizeof e->texture_path)) {
        char image_error[256];
        if (mu_image_load_file(e->texture_path, &e->texture, image_error, sizeof image_error) == MU_IMAGE_OK)
            e->texture_loaded = 1;
    }
    return MU_EFFECT_OK;
}

void mu_effect_free(mu_effect *e)
{
    mu_fx_free(&e->fx);
    if (e->texture_loaded)
        mu_image_free(&e->texture);
    free(e->vertices);
    memset(e, 0, sizeof *e);
}

/* Flat ground z = 0 for the terrain collider (the client queries its terrain
 * 0x016cc9e2 / 0x016ccbb6; no world is loaded here). */
static float ground_height(void *context, float x, float y)
{
    (void)context;
    (void)x;
    (void)y;
    return 0.0f;
}

static void ground_normal(void *context, float x, float y, float out[3])
{
    (void)context;
    (void)x;
    (void)y;
    out[0] = 0.0f;
    out[1] = 0.0f;
    out[2] = 1.0f;
}

void mu_effect_update(mu_effect *e, float dt)
{
    static const mu_fx_terrain ground = {NULL, ground_height, ground_normal};
    mu_fx_update(&e->fx, dt, &e->rng, &ground);
    e->frame++;
}

static void normalize3(float v[3])
{
    double l = sqrt((double)v[0] * v[0] + (double)v[1] * v[1] + (double)v[2] * v[2]);
    if (l > 0.0) {
        v[0] = (float)(v[0] / l);
        v[1] = (float)(v[1] / l);
        v[2] = (float)(v[2] / l);
    }
}

void mu_effect_camera(mu_fx_camera *c, const float eye[3], const float target[3])
{
    float forward[3] = {target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]};
    normalize3(forward);
    float world_up[3] = {0.0f, 0.0f, 1.0f};
    float right[3] = {forward[1] * world_up[2] - forward[2] * world_up[1],
                      forward[2] * world_up[0] - forward[0] * world_up[2],
                      forward[0] * world_up[1] - forward[1] * world_up[0]};
    normalize3(right);
    float up[3] = {right[1] * forward[2] - right[2] * forward[1], right[2] * forward[0] - right[0] * forward[2],
                   right[0] * forward[1] - right[1] * forward[0]};
    normalize3(up);
    mu_fx_camera_set(c, eye, forward, up);
}

static uint8_t blend_factor(uint32_t gl)
{
    switch (gl) {
    case 0: return MU_BLEND_ZERO;
    case 1: return MU_BLEND_ONE;
    case 0x300: return MU_BLEND_SRC_COLOR;
    case 0x301: return MU_BLEND_ONE_MINUS_SRC_COLOR;
    case 0x302: return MU_BLEND_SRC_ALPHA;
    case 0x303: return MU_BLEND_ONE_MINUS_SRC_ALPHA;
    case 0x306: return MU_BLEND_DST_COLOR;
    default: return MU_BLEND_ONE;
    }
}

uint32_t mu_effect_draw(mu_effect *e, const mu_fx_camera *camera, mu_raster *raster)
{
    mu_fx_draw_state s;
    uint32_t n = mu_fx_draw(&e->fx, camera, e->texture_loaded, e->vertices, &s);
    if (!s.visible || n == 0)
        return 0;
    mu_meshdraw_state state;
    memset(&state, 0, sizeof state);
    state.blend = s.blend;
    state.src = blend_factor(s.src);
    state.dst = blend_factor(s.dst);
    state.depth_test = 1;
    state.depth_mask = 0;
    state.cull = 0;
    state.alpha_test = 0;
    state.texture = s.texture;
    const mu_image *slot = e->texture_loaded ? &e->texture : NULL;
    const mu_image *const *saved_textures = raster->textures;
    int32_t saved_count = raster->texture_count;
    int saved_linear = raster->linear;
    raster->textures = &slot;
    raster->texture_count = 1;
    raster->linear = 1;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    backend.prepare(backend.context, &state, 0);
    float saved_view[16];
    memcpy(saved_view, raster->view, sizeof saved_view);
    if (s.multiply_matrix)
        mu_mat4_multiply(saved_view, e->fx.matrix, raster->view);
    backend.begin(backend.context);
    static const int corner[6] = {0, 1, 2, 0, 2, 3};
    for (uint32_t q = 0; q + 3 < n; q += 4) {
        for (int k = 0; k < 6; ++k) {
            const mu_fx_vertex *v = &e->vertices[q + (uint32_t)corner[k]];
            backend.sink.texcoord(backend.sink.context, v->texcoord[0], v->texcoord[1]);
            backend.sink.color4(backend.sink.context, v->color[0], v->color[1], v->color[2], v->color[3]);
            backend.sink.vertex(backend.sink.context, v->position);
        }
    }
    backend.end(backend.context);
    memcpy(raster->view, saved_view, sizeof saved_view);
    raster->textures = saved_textures;
    raster->texture_count = saved_count;
    raster->linear = saved_linear;
    return n;
}
