/* Client-memory model for the native viewer. See mu_model.h. */
#include "mu_model.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/model-codec/bone_tracks.h"
#include "../../reconstructed/model-codec/pose_builder.h"

/* Region indices. */
enum { R_WINDOW, R_BONES, R_LIGHTS, R_QUATERNIONS, R_SECONDARY, R_ROOT, R_VERTICES, R_NORMALS,
       R_GLOBALS, R_WORLD, R_SCENE, R_BOUNDS };

#define OBJECT_FRAME 0x00
#define OBJECT_PRIOR_FRAME 0x04
#define OBJECT_PRIOR_ACTION 0x08
#define OBJECT_ANGLES 0x10
#define OBJECT_HEAD 0x20
#define OBJECT_BOUNDS_MIN 0x30
#define OBJECT_BOUNDS_MAX 0x40
#define OBJECT_BOX 0x50

static uint32_t align_up(uint32_t value, uint32_t boundary) { return (value + boundary - 1) & ~(boundary - 1); }

static uint32_t float_bits(float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return bits;
}

uint8_t *mu_model_host(const mu_model *model, uint32_t address, uint32_t length)
{
    for (unsigned index = 0; index < MU_MODEL_REGION_COUNT; ++index) {
        const mu_client_image *region = &model->regions[index];
        if (address < region->base)
            continue;
        uint32_t start = address - region->base;
        if (start <= region->size && length <= region->size - start)
            return region->bytes + start;
    }
    return NULL;
}

static void put8(mu_model *m, uint32_t address, uint8_t value) { *mu_model_host(m, address, 1) = value; }
static void put16(mu_model *m, uint32_t address, uint32_t value)
{
    uint8_t *p = mu_model_host(m, address, 2);
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
}
static void put32(mu_model *m, uint32_t address, uint32_t value)
{
    uint8_t *p = mu_model_host(m, address, 4);
    for (unsigned k = 0; k < 4; ++k)
        p[k] = (uint8_t)(value >> (8 * k));
}
static void putf(mu_model *m, uint32_t address, float value) { put32(m, address, float_bits(value)); }
static uint32_t get32(const mu_model *m, uint32_t address)
{
    const uint8_t *p = mu_model_host(m, address, 4);
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static float getf(const mu_model *m, uint32_t address)
{
    uint32_t bits = get32(m, address);
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

void mu_model_default_params(mu_model_params *p)
{
    memset(p, 0, sizeof *p);
    p->body_scale = 1.0f;
    p->color[0] = p->color[1] = p->color[2] = 1.0f;
    p->special_bone = -1;
    p->light_skip_mesh = -1;
    p->lighting = 1;
    p->pose_translate = 0;
    p->transform_translate = 1;
    /* Wrapper 0x012b5a0a passes vertex scale 0 and 0.4, 0.4, 0.4 for the light terms. */
    p->light_ambient = 0.4f;
    p->light_scale = 0.4f;
    p->light_minimum = 0.4f;
    p->bone_scale = 1.0f;
}

/* Deterministic bump allocator; same policy as scripts/validate_bone_tracks.py Heap. */
static uint32_t allocate(void *context, uint32_t request)
{
    mu_model *m = context;
    if (request > 0xffffffe0u)  /* client malloc refuses before HeapAlloc */
        return 0;
    uint32_t size = request ? request : 1;
    uint32_t address = align_up(m->heap_cursor + 16, 16);
    if (address > m->heap_end || size > m->heap_end - address)
        return 0;
    m->heap_cursor = address + size;
    memset(mu_model_host(m, address, size), 0, size);
    return address;
}

static uint32_t heap_need(const mu_bmd *b)
{
    uint64_t total = 0;
    for (int32_t i = 0; i < b->bone_count; ++i) {
        if (b->bones[i].dummy)
            continue;
        total += align_up((uint32_t)(b->action_count * 12 > 0 ? b->action_count * 12 : 1) + 16, 16);
        for (int32_t a = 0; a < b->action_count; ++a) {
            uint32_t k = (uint32_t)b->actions[a].keys;
            total += 2u * align_up((k * 12 ? k * 12 : 1) + 16, 16) + align_up((k * 16 ? k * 16 : 1) + 16, 16);
        }
    }
    total += 4096;
    return total > 0x40000000u ? 0x40000000u : (uint32_t)total;
}

static int region(mu_model *m, unsigned index, uint32_t base, uint32_t size)
{
    uint8_t *storage = calloc(size ? size : 1, 1);
    if (!storage)
        return 0;
    m->region_storage[index] = storage;
    m->regions[index].bytes = storage;
    m->regions[index].base = base;
    m->regions[index].size = size;
    return 1;
}

static int failure(mu_model *m, char *error, size_t size, const char *message)
{
    if (error && size)
        snprintf(error, size, "%s", message);
    mu_model_free(m);
    return MU_MODEL_ERROR;
}

void mu_model_free(mu_model *m)
{
    if (!m)
        return;
    for (unsigned index = 0; index < MU_MODEL_REGION_COUNT; ++index)
        free(m->region_storage[index]);
    free(m->triangles);
    free(m->texcoords);
    memset(m, 0, sizeof *m);
}

void mu_model_relocate(mu_model *m, const mu_bmd *bmd)
{
    m->bmd = bmd;
    m->memory.regions = m->regions;
}

void mu_model_apply_params(mu_model *m, const mu_model_params *p)
{
    m->params = *p;
    put8(m, m->model + 0x50, p->lighting);
    for (unsigned k = 0; k < 3; ++k) {
        putf(m, m->model + 0x54 + 4 * k, p->color[k]);
        putf(m, m->model + 0x78 + 4 * k, p->origin[k]);
        putf(m, m->model + 0x98 + 4 * k, p->light_angles[k]);
        putf(m, m->object + OBJECT_ANGLES + 4 * k, p->angles[k]);
    }
    put32(m, m->model + 0x60, (uint32_t)p->special_bone);
    putf(m, m->model + 0x74, p->body_scale);
    putf(m, m->model + 0x90, p->height);
    put32(m, m->model + 0x94, (uint32_t)p->light_skip_mesh);
    put8(m, m->model + 0xcb, p->secondary_light);
    putf(m, m->object + OBJECT_HEAD, p->head_angles[0]);
    putf(m, m->object + OBJECT_HEAD + 4, p->head_angles[1]);
    put8(m, 0x01cf1048u, p->light_override);
    putf(m, 0x01cf104cu, p->bone_scale);
    put32(m, 0x01cf15fcu, (uint32_t)p->world);
    put32(m, 0x01d1df70u, (uint32_t)p->scene_state);
    put32(m, 0x0b437bfcu, (uint32_t)p->bounds_mode);
}

int mu_model_init(mu_model *m, const mu_bmd *b, const mu_model_params *params, char *error, size_t error_size)
{
    memset(m, 0, sizeof *m);
    m->bmd = b;
    if (b->bone_count > MU_MODEL_MAX_BONES)
        return failure(m, error, error_size, "Model exceeds the client's 200-bone output buffer");
    if (b->mesh_count > MU_MODEL_MAX_MESHES)
        return failure(m, error, error_size, "Model exceeds the client's 50-mesh output buffers");
    for (int32_t i = 0; i < b->mesh_count; ++i)
        if (b->meshes[i].vertex_count > MU_MODEL_MAX_ENTRIES || b->meshes[i].normal_count > MU_MODEL_MAX_ENTRIES)
            return failure(m, error, error_size, "Mesh exceeds the client's 15,000-entry output stride");

    /* Window layout. */
    uint32_t cursor = 0x200;
    m->model = MU_MODEL_WINDOW;
    m->object = MU_MODEL_WINDOW + 0x100;
    m->actions = MU_MODEL_WINDOW + cursor;
    cursor = align_up(cursor + 16u * (uint32_t)(b->action_count ? b->action_count : 1), 16);
    m->bones = MU_MODEL_WINDOW + cursor;
    cursor = align_up(cursor + 0x8cu * (uint32_t)(b->bone_count ? b->bone_count : 1), 16);
    m->meshes = MU_MODEL_WINDOW + cursor;
    cursor = align_up(cursor + 0x20u * (uint32_t)(b->mesh_count ? b->mesh_count : 1), 16);
    uint32_t mesh_start = cursor;
    for (int32_t i = 0; i < b->mesh_count; ++i) {
        const mu_bmd_mesh *mesh = &b->meshes[i];
        cursor = align_up(cursor + 16u * (uint32_t)mesh->vertex_count, 16);
        cursor = align_up(cursor + 20u * (uint32_t)mesh->normal_count, 16);
        cursor = align_up(cursor + 8u * (uint32_t)mesh->uv_count, 16);
        cursor = align_up(cursor + 0x24u * (uint32_t)mesh->polygon_count, 16);
    }
    uint32_t stream = align_up(cursor, 16) + 0x40;
    cursor = stream + b->payload_size + 0x40;
    uint32_t heap = align_up(cursor + 0x100, 0x1000);
    uint32_t window_size = align_up(heap + heap_need(b), 0x1000);
    m->heap_cursor = MU_MODEL_WINDOW + heap;
    m->heap_end = MU_MODEL_WINDOW + window_size;
    m->window_size = window_size;

    uint32_t nm = (uint32_t)b->mesh_count, nb = (uint32_t)b->bone_count;
    if (!region(m, R_WINDOW, MU_MODEL_WINDOW, window_size) ||
        !region(m, R_BONES, MU_MODEL_BONES, (nb ? nb : 1) * 0x30u) ||
        !region(m, R_LIGHTS, MU_MODEL_LIGHTS, nm * MU_MODEL_LIGHT_STRIDE) ||
        !region(m, R_QUATERNIONS, MU_POSE_BONE_QUATERNIONS, MU_SKIN_SECONDARY_LIGHT - MU_POSE_BONE_QUATERNIONS) ||
        !region(m, R_SECONDARY, MU_SKIN_SECONDARY_LIGHT, nm * MU_MODEL_LIGHT_STRIDE) ||
        !region(m, R_ROOT, MU_POSE_ROOT_MATRIX, 0x30) ||
        !region(m, R_VERTICES, MU_MODEL_VERTICES, nm * MU_MODEL_VERTEX_STRIDE) ||
        !region(m, R_NORMALS, MU_MODEL_NORMALS, nm * MU_MODEL_VERTEX_STRIDE) ||
        !region(m, R_GLOBALS, MU_SKIN_LIGHT_OVERRIDE, 8) ||
        !region(m, R_WORLD, MU_SKIN_WORLD, 4) ||
        !region(m, R_SCENE, MU_TICK_SCENE_STATE, 4) ||
        !region(m, R_BOUNDS, MU_SKIN_BOUNDS_MODE, 4))
        return failure(m, error, error_size, "Out of memory");
    m->window = m->region_storage[R_WINDOW];
    m->memory.regions = m->regions;
    m->memory.count = MU_MODEL_REGION_COUNT;
    m->triangles = calloc(nm ? nm : 1, sizeof *m->triangles);
    m->texcoords = calloc(nm ? nm : 1, sizeof *m->texcoords);
    if (!m->triangles || !m->texcoords)
        return failure(m, error, error_size, "Out of memory");

    /* Model object counts and arrays (offsets from bone_tracks.h, pose_builder.h, skinning.h). */
    put16(m, m->model + 0x22, nb);
    put16(m, m->model + 0x24, nm);
    put16(m, m->model + 0x26, (uint32_t)b->action_count);
    put32(m, m->model + 0x28, m->meshes);
    put32(m, m->model + 0x2c, m->bones);
    put32(m, m->model + 0x30, m->actions);
    for (int32_t a = 0; a < b->action_count; ++a) {
        uint32_t entry = m->actions + 16u * (uint32_t)a;
        put8(m, entry, 0);                                   /* stop flag */
        put16(m, entry + 8, (uint32_t)b->actions[a].keys);   /* keys */
        put8(m, entry + 0xa, b->actions[a].lock_positions);  /* lock flag (from the file) */
    }

    /* Mesh records (stride 0x20) and their arrays. */
    cursor = mesh_start;
    for (int32_t i = 0; i < b->mesh_count; ++i) {
        const mu_bmd_mesh *mesh = &b->meshes[i];
        uint32_t record = m->meshes + 0x20u * (uint32_t)i;
        uint32_t vertices = MU_MODEL_WINDOW + cursor;
        cursor = align_up(cursor + 16u * (uint32_t)mesh->vertex_count, 16);
        uint32_t normals = MU_MODEL_WINDOW + cursor;
        cursor = align_up(cursor + 20u * (uint32_t)mesh->normal_count, 16);
        uint32_t texcoords = MU_MODEL_WINDOW + cursor;
        cursor = align_up(cursor + 8u * (uint32_t)mesh->uv_count, 16);
        uint32_t triangles = MU_MODEL_WINDOW + cursor;
        cursor = align_up(cursor + 0x24u * (uint32_t)mesh->polygon_count, 16);
        memcpy(mu_model_host(m, vertices, 0), b->payload + mesh->vertex_offset, 16u * (uint32_t)mesh->vertex_count);
        memcpy(mu_model_host(m, normals, 0), b->payload + mesh->normal_offset, 20u * (uint32_t)mesh->normal_count);
        memcpy(mu_model_host(m, texcoords, 0), b->payload + mesh->uv_offset, 8u * (uint32_t)mesh->uv_count);
        for (int32_t f = 0; f < mesh->polygon_count; ++f)
            memcpy(mu_model_host(m, triangles + 0x24u * (uint32_t)f, 0x24),
                   b->payload + mesh->polygon_offset + 64u * (uint32_t)f, 0x24);
        put16(m, record + 2, (uint32_t)(uint16_t)mesh->texture_index);
        put16(m, record + 4, (uint32_t)mesh->vertex_count);
        put16(m, record + 6, (uint32_t)mesh->normal_count);
        put16(m, record + 8, (uint32_t)mesh->uv_count);
        put16(m, record + 0xa, (uint32_t)mesh->polygon_count);
        put32(m, record + 0xc, vertices);
        put32(m, record + 0x10, normals);
        put32(m, record + 0x14, texcoords);
        put32(m, record + 0x18, triangles);
        m->triangles[i] = triangles;
        m->texcoords[i] = texcoords;
    }

    /* Decoded stream and the reconstructed bone-track loop. */
    memcpy(mu_model_host(m, MU_MODEL_WINDOW + stream, 0), b->payload, b->payload_size);
    int32_t offset = (int32_t)b->bone_stream;
    int status = mu_bone_tracks_read(&m->regions[R_WINDOW], m->model, MU_MODEL_WINDOW + stream, &offset, allocate, m);
    if (status != MU_BONE_TRACKS_OK)
        return failure(m, error, error_size, "Bone-track loop failed");
    if ((uint32_t)offset != b->parsed_size)
        return failure(m, error, error_size, "Bone-track loop ended away from the parsed bone records");

    mu_model_params defaults;
    if (!params) {
        mu_model_default_params(&defaults);
        params = &defaults;
    }
    mu_model_apply_params(m, params);
    mu_model_set_state(m, 0, 0.0f, 0.0f, 0);
    return MU_MODEL_OK;
}

void mu_model_set_state(mu_model *m, uint16_t action, float frame, float prior_frame, uint16_t prior_action)
{
    put16(m, m->model + 0xa8, action);
    putf(m, m->object + OBJECT_FRAME, frame);
    putf(m, m->object + OBJECT_PRIOR_FRAME, prior_frame);
    put16(m, m->object + OBJECT_PRIOR_ACTION, prior_action);
}

uint16_t mu_model_action(const mu_model *m) { return (uint16_t)(get32(m, m->model + 0xa8) & 0xffff); }
float mu_model_frame(const mu_model *m) { return getf(m, m->object + OBJECT_FRAME); }
float mu_model_prior_frame(const mu_model *m) { return getf(m, m->object + OBJECT_PRIOR_FRAME); }
uint16_t mu_model_prior_action(const mu_model *m) { return (uint16_t)(get32(m, m->object + OBJECT_PRIOR_ACTION) & 0xffff); }

int32_t mu_model_action_stop(const mu_model *m, uint16_t action)
{
    if (action >= m->bmd->action_count)
        return 0;
    return *mu_model_host(m, m->actions + 16u * action, 1);
}

void mu_model_set_action_stop(mu_model *m, uint16_t action, uint8_t stop)
{
    if (action < m->bmd->action_count)
        put8(m, m->actions + 16u * action, stop);
}

int mu_model_tick(mu_model *m, float speed, uint8_t *loop)
{
    mu_tick_arguments arguments = {m->object + OBJECT_FRAME, m->object + OBJECT_PRIOR_FRAME,
                                   m->object + OBJECT_PRIOR_ACTION, float_bits(speed), 0, 0};
    mu_tick_globals globals = {MU_TICK_SCENE_STATE, MU_SKIN_WORLD};
    uint8_t result = 1;
    int status = mu_animation_tick(&m->memory, m->model, &arguments, &globals, &result);
    if (loop)
        *loop = result;
    return status == MU_SKIN_OK ? MU_MODEL_OK : MU_MODEL_ERROR;
}

static void identity_bones(mu_model *m)
{
    static const float identity[12] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0};
    for (int32_t i = 0; i < m->bmd->bone_count; ++i)
        memcpy(mu_model_host(m, MU_MODEL_BONES + 0x30u * (uint32_t)i, 0x30), identity, sizeof identity);
}

int mu_model_pose(mu_model *m)
{
    const mu_bmd *b = m->bmd;
    uint16_t action = mu_model_action(m), prior = mu_model_prior_action(m);
    uint16_t current_checked = action < b->action_count ? action : 0;
    uint16_t prior_checked = prior < b->action_count ? prior : 0;
    if (b->action_count == 0 || b->actions[current_checked].keys <= 0 || b->actions[prior_checked].keys <= 0) {
        identity_bones(m);
        m->posed = 0;
        return MU_MODEL_OK;
    }
    mu_pose_arguments arguments = {MU_MODEL_BONES, get32(m, m->object + OBJECT_FRAME),
                                   get32(m, m->object + OBJECT_PRIOR_FRAME), prior, m->object + OBJECT_ANGLES,
                                   m->object + OBJECT_HEAD, 0, m->params.pose_translate};
    mu_pose_globals globals = {MU_POSE_BONE_QUATERNIONS, MU_POSE_ROOT_MATRIX};
    int status = mu_pose_build(&m->memory, m->model, &arguments, &globals);
    m->posed = status == MU_POSE_OK;
    return status == MU_POSE_OK ? MU_MODEL_OK : MU_MODEL_ERROR;
}

int mu_model_transform_all(mu_model *m)
{
    const mu_model_params *p = &m->params;
    mu_transform_arguments arguments = {
        MU_MODEL_BONES, MU_MODEL_VERTICES, MU_MODEL_NORMALS, MU_MODEL_LIGHTS,
        m->object + OBJECT_BOUNDS_MIN, m->object + OBJECT_BOUNDS_MAX, m->object + OBJECT_BOX,
        p->transform_translate, float_bits(p->vertex_scale), float_bits(p->light_ambient),
        float_bits(p->light_scale), float_bits(p->light_minimum)};
    mu_transform_globals globals = {MU_SKIN_BONE_SCALE, MU_SKIN_LIGHT_OVERRIDE, MU_SKIN_WORLD, MU_SKIN_BOUNDS_MODE,
                                    MU_SKIN_SECONDARY_LIGHT};
    return mu_model_transform(&m->memory, m->model, &arguments, &globals) == MU_SKIN_OK ? MU_MODEL_OK : MU_MODEL_ERROR;
}

int mu_model_update(mu_model *m)
{
    if (mu_model_pose(m) != MU_MODEL_OK)
        return MU_MODEL_ERROR;
    return mu_model_transform_all(m);
}

const float *mu_model_vertices(const mu_model *m, int32_t mesh)
{
    return (const float *)(void *)(m->region_storage[R_VERTICES] + MU_MODEL_VERTEX_STRIDE * (uint32_t)mesh);
}
const float *mu_model_normals(const mu_model *m, int32_t mesh)
{
    return (const float *)(void *)(m->region_storage[R_NORMALS] + MU_MODEL_VERTEX_STRIDE * (uint32_t)mesh);
}
const float *mu_model_lights(const mu_model *m, int32_t mesh)
{
    return (const float *)(void *)(m->region_storage[R_LIGHTS] + MU_MODEL_LIGHT_STRIDE * (uint32_t)mesh);
}
const float *mu_model_secondary_lights(const mu_model *m, int32_t mesh)
{
    return (const float *)(void *)(m->region_storage[R_SECONDARY] + MU_MODEL_LIGHT_STRIDE * (uint32_t)mesh);
}
const float *mu_model_bone_matrices(const mu_model *m) { return (const float *)(void *)m->region_storage[R_BONES]; }
const uint8_t *mu_model_triangles(const mu_model *m, int32_t mesh) { return mu_model_host(m, m->triangles[mesh], 0); }
const float *mu_model_texcoords(const mu_model *m, int32_t mesh)
{
    return (const float *)(void *)mu_model_host(m, m->texcoords[mesh], 0);
}
const float *mu_model_color(const mu_model *m) { return (const float *)(void *)mu_model_host(m, m->model + 0x54, 12); }
const float *mu_model_origin(const mu_model *m) { return (const float *)(void *)mu_model_host(m, m->model + 0x78, 12); }
const float *mu_model_box(const mu_model *m) { return (const float *)(void *)mu_model_host(m, m->object + OBJECT_BOX, 48); }
