#include "skinning.h"

#include <stddef.h>
#include <string.h>

#include "../record-math/record_math.h"

/* Model transform 0x012b5bde..0x012b678d and animation tick
 * 0x012b4dd3..0x012b5064. Client memory is reread where the original rereads
 * it and writes happen in the original order. */

static uint8_t *at(const mu_client_memory *memory, uint32_t address, uint32_t length)
{
    for (uint32_t index = 0; index < memory->count; ++index) {
        const mu_client_image *region = &memory->regions[index];
        if (address < region->base)
            continue;
        uint32_t start = address - region->base;
        if (start <= region->size && length <= region->size - start)
            return region->bytes + start;
    }
    return NULL;
}

static float bits_float(uint32_t bits)
{
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

#define CHECK(expression) do { if (!(expression)) return MU_SKIN_OUTSIDE_MEMORY; } while (0)

static int read8(const mu_client_memory *memory, uint32_t address, uint8_t *value)
{
    uint8_t *p = at(memory, address, 1);
    if (!p)
        return 0;
    *value = p[0];
    return 1;
}

static int read_s16(const mu_client_memory *memory, uint32_t address, int32_t *value)
{
    uint8_t *p = at(memory, address, 2);
    if (!p)
        return 0;
    *value = (int16_t)(uint16_t)(p[0] | (p[1] << 8));
    return 1;
}

static int read_u16(const mu_client_memory *memory, uint32_t address, uint32_t *value)
{
    uint8_t *p = at(memory, address, 2);
    if (!p)
        return 0;
    *value = (uint32_t)(p[0] | (p[1] << 8));
    return 1;
}

static int write16(const mu_client_memory *memory, uint32_t address, uint32_t value)
{
    uint8_t *p = at(memory, address, 2);
    if (!p)
        return 0;
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    return 1;
}

static int read32(const mu_client_memory *memory, uint32_t address, uint32_t *value)
{
    uint8_t *p = at(memory, address, 4);
    if (!p)
        return 0;
    *value = (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
    return 1;
}

static int write32(const mu_client_memory *memory, uint32_t address, uint32_t value)
{
    uint8_t *p = at(memory, address, 4);
    if (!p)
        return 0;
    for (unsigned byte = 0; byte < 4; ++byte)
        p[byte] = (uint8_t)(value >> (byte * 8));
    return 1;
}

static int read_float(const mu_client_memory *memory, uint32_t address, float *value)
{
    uint32_t bits;
    if (!read32(memory, address, &bits))
        return 0;
    *value = bits_float(bits);
    return 1;
}

static int write_float(const mu_client_memory *memory, uint32_t address, float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return write32(memory, address, bits);
}

static int copy32(const mu_client_memory *memory, uint32_t destination, uint32_t source)
{
    uint32_t bits;
    return read32(memory, source, &bits) && write32(memory, destination, bits);
}

static int32_t truncate32(float value)
{
    if (!(value >= -2147483648.0f && value < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)value;
}

static uint32_t scaled(uint32_t base, int32_t index, uint32_t stride)
{
    return base + (uint32_t)index * stride;
}

/* The vector helpers operate on host pointers; each operand span must lie in
 * one region, which holds for every compared layout. */
typedef void (*vector_helper)(const void *, const void *, void *);

static int vector(const mu_client_memory *memory, vector_helper helper, uint32_t in, uint32_t matrix,
                  uint32_t out)
{
    uint8_t *a = at(memory, in, 12), *m = at(memory, matrix, 48), *o = at(memory, out, 12);
    if (!a || !m || !o)
        return 0;
    helper(a, m, o);
    return 1;
}

/* Light-vector setup: local vectors and the light-angle matrix live in a
 * scratch region standing in for the original stack frame. */
static void set3(uint8_t *vector, float x, float y, float z)
{
    memcpy(vector, &x, 4);
    memcpy(vector + 4, &y, 4);
    memcpy(vector + 8, &z, 4);
}

static float get(const uint8_t *vector, unsigned index)
{
    float value;
    memcpy(&value, vector + 4 * index, 4);
    return value;
}

static float dot_term(const uint8_t *normal, const uint8_t *light)
{
    volatile float value = get(normal, 0) * get(light, 0);
    volatile float product = get(normal, 1) * get(light, 1);
    value = value + product;
    product = get(normal, 2) * get(light, 2);
    value = value + product;
    return value;
}

int mu_model_transform(const mu_client_memory *memory, uint32_t model, const mu_transform_arguments *arguments,
                       const mu_transform_globals *globals)
{
    uint8_t lighting, flag, translate = (uint8_t)arguments->translate;
    uint8_t light_vector[12], light_matrix[48], light1[12], light2[12];
    uint8_t minimum[12], maximum[12], local[12];
    int32_t meshes, count, mode, node, world;
    uint32_t mesh, records, record, output;
    float value, bone_scale;
    const float vertex_scale = bits_float(arguments->vertex_scale);
    const float ambient = bits_float(arguments->light_ambient);
    const float light_scale = bits_float(arguments->light_scale);
    const float light_minimum = bits_float(arguments->light_minimum);

    if (arguments->bones == 0)
        return MU_SKIN_OK;
    CHECK(read8(memory, model + 0x50, &lighting));
    if (lighting) {
        CHECK(read8(memory, globals->light_override, &flag));
        if (flag) {
            set3(light_vector, 1.3f, 0.0f, 2.0f);
        } else {
            CHECK(read32(memory, globals->world, (uint32_t *)&world));
            if (world == 0x1e) { /* 0x0095fb7c(world) */
                set3(light_vector, 0.5f, -1.0f, 1.0f);
                CHECK(write_float(memory, model + 0x98, 0.0f));
                CHECK(write_float(memory, model + 0x9c, 0.0f));
                CHECK(write_float(memory, model + 0xa0, -45.0f));
            } else {
                set3(light_vector, 0.0f, -1.5f, 0.0f);
            }
        }
        uint8_t *angles = at(memory, model + 0x98, 12);
        CHECK(angles);
        mu_angle_matrix(angles, light_matrix);
        mu_vector_irotate(light_vector, light_matrix, light1);
        set3(light_vector, 1.3f, -0.5f, 1.8f);
        mu_vector_irotate(light_vector, light_matrix, light2);
    }
    CHECK(read32(memory, globals->bounds_mode, (uint32_t *)&mode));
    if (mode == 2) {
        set3(minimum, 999999.0f, 999999.0f, 999999.0f);
        set3(maximum, -999999.0f, -999999.0f, -999999.0f);
    }
    for (int32_t i = 0;; ++i) {
        CHECK(read_s16(memory, model + 0x24, &meshes));
        if (i >= meshes)
            break;
        CHECK(read32(memory, model + 0x28, &mesh));
        mesh = scaled(mesh, i, 0x20);
        for (int32_t j = 0;; ++j) {
            CHECK(read_s16(memory, mesh + 4, &count));
            if (j >= count)
                break;
            CHECK(read32(memory, mesh + 0xc, &records));
            record = scaled(records, j, 16);
            output = scaled(arguments->vertices, i, 0x2bf20) + (uint32_t)j * 12u;
            CHECK(read_float(memory, globals->bone_scale, &bone_scale));
            if (bone_scale == 1.0f) {
                if (vertex_scale != 0.0f) {
                    uint8_t *source = at(memory, record + 4, 12);
                    CHECK(source);
                    memcpy(local, source, 12);
                    for (unsigned k = 0; k < 3; ++k) {
                        volatile float product = vertex_scale * get(local, k);
                        float stored = product;
                        memcpy(local + 4 * k, &stored, 4);
                    }
                    CHECK(read_s16(memory, record, &node));
                    uint8_t *m = at(memory, scaled(arguments->bones, node, 0x30), 48);
                    uint8_t *o = at(memory, output, 12);
                    CHECK(m && o);
                    mu_vector_transform(local, m, o);
                } else {
                    CHECK(read_s16(memory, record, &node));
                    CHECK(vector(memory, mu_vector_transform, record + 4, scaled(arguments->bones, node, 0x30),
                                 output));
                }
            } else {
                CHECK(read_s16(memory, record, &node));
                CHECK(vector(memory, mu_vector_rotate, record + 4, scaled(arguments->bones, node, 0x30), output));
                for (unsigned k = 0; k < 3; ++k) {
                    float component, factor, offset;
                    CHECK(read_float(memory, output + 4 * k, &component));
                    CHECK(read_float(memory, globals->bone_scale, &factor));
                    CHECK(read_s16(memory, record, &node));
                    CHECK(read_float(memory, scaled(arguments->bones, node, 0x30) + 0x10 * k + 0xc, &offset));
                    volatile float result = component * factor;
                    result = result + offset;
                    CHECK(write_float(memory, output + 4 * k, result));
                }
            }
            if (translate) {
                for (unsigned k = 0; k < 3; ++k) {
                    float body, component;
                    CHECK(read_float(memory, model + 0x74, &body));
                    CHECK(read_float(memory, output + 4 * k, &component));
                    volatile float result = body * component;
                    CHECK(write_float(memory, output + 4 * k, result));
                }
            }
            CHECK(read32(memory, globals->bounds_mode, (uint32_t *)&mode));
            if (mode == 2) {
                for (unsigned k = 0; k < 3; ++k) {
                    float component;
                    CHECK(read_float(memory, output + 4 * k, &component));
                    if (get(minimum, k) > component)
                        memcpy(minimum + 4 * k, &component, 4);
                    CHECK(read_float(memory, output + 4 * k, &component));
                    if (component > get(maximum, k))
                        memcpy(maximum + 4 * k, &component, 4);
                }
            }
            if (translate) {
                for (unsigned k = 0; k < 3; ++k) {
                    float component, origin;
                    CHECK(read_float(memory, output + 4 * k, &component));
                    CHECK(read_float(memory, model + 0x78 + 4 * k, &origin));
                    volatile float result = component + origin;
                    CHECK(write_float(memory, output + 4 * k, result));
                }
            }
        }
        for (int32_t j = 0;; ++j) {
            CHECK(read_s16(memory, mesh + 6, &count));
            if (j >= count)
                break;
            CHECK(read32(memory, mesh + 0x10, &records));
            record = scaled(records, j, 20);
            output = scaled(arguments->normals, i, 0x2bf20) + (uint32_t)j * 12u;
            CHECK(read_s16(memory, record, &node));
            CHECK(vector(memory, mu_vector_rotate, record + 4, scaled(arguments->bones, node, 0x30), output));
            CHECK(read8(memory, model + 0x50, &lighting));
            if (!lighting)
                continue;
            uint8_t *normal = at(memory, output, 12);
            CHECK(normal);
            volatile float light = dot_term(normal, light1) * light_scale;
            light = light + ambient;
            value = light;
            if (light_minimum > value)
                value = light_minimum;
            CHECK(write_float(memory, scaled(arguments->lights, i, 0xea60) + (uint32_t)j * 4u, value));
            normal = at(memory, output, 12);
            CHECK(normal);
            light = dot_term(normal, light2) * 0.8f;
            light = light + ambient;
            if (0.2f > light) {
                value = 0.2f;
            } else {
                normal = at(memory, output, 12);
                CHECK(normal);
                light = dot_term(normal, light2) * 0.8f;
                light = light + ambient;
                value = light;
            }
            CHECK(write_float(memory, scaled(globals->secondary_light, i, 0xea60) + (uint32_t)j * 4u, value));
        }
    }
    CHECK(read32(memory, globals->bounds_mode, (uint32_t *)&mode));
    const uint32_t box = arguments->box;
    if (mode == 2) {
        for (unsigned k = 0; k < 3; ++k)
            CHECK(write_float(memory, box + 4 * k, get(minimum, k)));
        for (unsigned k = 0; k < 3; ++k) {
            volatile float extent = get(maximum, k) - get(minimum, k);
            CHECK(write_float(memory, box + 0xc * (k + 1) + 4 * k, extent));
        }
    } else {
        for (unsigned k = 0; k < 3; ++k)
            CHECK(copy32(memory, box + 4 * k, arguments->bounds_min + 4 * k));
        for (unsigned k = 0; k < 3; ++k) {
            float high, low;
            CHECK(read_float(memory, arguments->bounds_max + 4 * k, &high));
            CHECK(read_float(memory, arguments->bounds_min + 4 * k, &low));
            volatile float extent = high - low;
            CHECK(write_float(memory, box + 0xc * (k + 1) + 4 * k, extent));
        }
    }
    for (unsigned k = 0; k < 3; ++k) {
        float component, origin;
        CHECK(read_float(memory, box + 4 * k, &component));
        CHECK(read_float(memory, model + 0x78 + 4 * k, &origin));
        volatile float result = component + origin;
        CHECK(write_float(memory, box + 4 * k, result));
    }
    static const uint8_t zeroed[6][2] = {{1, 1}, {1, 2}, {2, 0}, {2, 2}, {3, 0}, {3, 1}};
    for (unsigned k = 0; k < 6; ++k)
        CHECK(write_float(memory, box + 0xc * zeroed[k][0] + 4 * zeroed[k][1], 0.0f));
    return MU_SKIN_OK;
}

int mu_animation_tick(const mu_client_memory *memory, uint32_t model, const mu_tick_arguments *arguments,
                      const mu_tick_globals *globals, uint8_t *loop)
{
    int32_t actions, keys, limit, old, whole, state, world;
    uint32_t action, array, entry;
    uint8_t stop, lock;
    float frame, speed = bits_float(arguments->speed);

    *loop = 1;
    if (arguments->frame == 0 || arguments->prior_frame == 0 || arguments->prior_action == 0)
        return MU_SKIN_OK;
    CHECK(read_s16(memory, model + 0x26, &actions));
    if (actions > 0) {
        CHECK(read_u16(memory, model + 0xa8, &action));
        CHECK(read_s16(memory, model + 0x26, &actions));
        if (!((int32_t)action < actions))
            return MU_SKIN_OK;
    }
    CHECK(read_s16(memory, model + 0x26, &actions));
    if (actions == 0)
        return MU_SKIN_OK;
    CHECK(read_u16(memory, model + 0xa8, &action));
    CHECK(read32(memory, model + 0x30, &array));
    CHECK(read_s16(memory, array + action * 16 + 8, &keys));
    if (keys <= 1)
        return MU_SKIN_OK;
    CHECK(read_float(memory, arguments->frame, &frame));
    old = truncate32(frame);
    {
        volatile float sum = frame + speed;
        CHECK(write_float(memory, arguments->frame, sum));
    }
    CHECK(read_float(memory, arguments->frame, &frame));
    if (old != truncate32(frame)) {
        uint32_t current;
        CHECK(read_u16(memory, model + 0xa8, &current));
        CHECK(write16(memory, arguments->prior_action, current));
        CHECK(write_float(memory, arguments->prior_frame, (float)old));
    }
    CHECK(read_float(memory, arguments->frame, &frame));
    if (!(0.0f < frame)) {
        if (frame == frame) { /* COMISS/JB: unordered skips */
            CHECK(read_u16(memory, model + 0xa8, &action));
            CHECK(read32(memory, model + 0x30, &array));
            CHECK(read_s16(memory, array + action * 16 + 8, &keys));
            volatile float base = (float)keys - 1.0f;
            CHECK(read_float(memory, arguments->frame, &frame));
            base = base + frame;
            CHECK(write_float(memory, arguments->frame, base));
        }
    }
    CHECK(read_u16(memory, model + 0xa8, &action));
    CHECK(read32(memory, model + 0x30, &array));
    entry = array + action * 16;
    CHECK(read8(memory, entry, &stop));
    if (stop) {
        CHECK(read_u16(memory, model + 0xa8, &action));
        CHECK(read32(memory, model + 0x30, &array));
        CHECK(read_s16(memory, array + action * 16 + 8, &keys));
        CHECK(read_float(memory, arguments->frame, &frame));
        if (frame >= (float)keys) {
            CHECK(read_u16(memory, model + 0xa8, &action));
            CHECK(read32(memory, model + 0x30, &array));
            CHECK(read_s16(memory, array + action * 16 + 8, &keys));
            volatile float clamped = (float)keys - 0.01f;
            CHECK(write_float(memory, arguments->frame, clamped));
            *loop = 0;
        }
    } else {
        CHECK(read_u16(memory, model + 0xa8, &action));
        CHECK(read32(memory, model + 0x30, &array));
        CHECK(read8(memory, array + action * 16 + 0xa, &lock));
        CHECK(read_u16(memory, model + 0xa8, &action));
        CHECK(read32(memory, model + 0x30, &array));
        CHECK(read_s16(memory, array + action * 16 + 8, &keys));
        limit = lock ? keys - 1 : keys;
        float test;
        CHECK(read32(memory, globals->scene_state, (uint32_t *)&state));
        if (state == 5) {
            CHECK(read_float(memory, arguments->frame, &frame));
            volatile float shifted = frame + 2.0f;
            test = shifted;
        } else {
            CHECK(read32(memory, globals->world, (uint32_t *)&world));
            int seven = 0;
            if (world == 0x27) {
                CHECK(read_u16(memory, model + 0xa8, &action));
                seven = action == 7;
            }
            CHECK(read_float(memory, arguments->frame, &frame));
            if (seven) {
                volatile float shifted = frame + 1.0f;
                test = shifted;
            } else {
                test = frame;
            }
        }
        if (test >= (float)limit) {
            CHECK(read_float(memory, arguments->frame, &frame));
            whole = truncate32(frame);
            /* IDIV: limit >= 1 here because keys > 1. */
            int32_t remainder = (int32_t)((int64_t)whole % (int64_t)limit);
            CHECK(read_float(memory, arguments->frame, &frame));
            volatile float fraction = frame - (float)whole;
            volatile float result = (float)remainder + fraction;
            CHECK(write_float(memory, arguments->frame, result));
            *loop = 0;
        }
    }
    CHECK(copy32(memory, model + 0xac, arguments->frame));
    CHECK(read_float(memory, model + 0xac, &frame));
    CHECK(write16(memory, model + 0xb4, (uint32_t)(uint16_t)truncate32(frame)));
    return MU_SKIN_OK;
}
