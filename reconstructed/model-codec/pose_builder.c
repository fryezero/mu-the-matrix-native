#include "pose_builder.h"

#include <stddef.h>
#include <string.h>

#include "../record-math/record_math.h"

/* Pose builder 0x012b5064..0x012b58cb. Client memory is reread where the
 * original rereads it; writes happen in the original order. */

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

static uint32_t load32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void store32(uint8_t *p, uint32_t value)
{
    for (unsigned byte = 0; byte < 4; ++byte)
        p[byte] = (uint8_t)(value >> (byte * 8));
}

static float bits_float(uint32_t bits)
{
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

static uint32_t float_bits(float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return bits;
}

#define CHECK(expression) do { if (!(expression)) return MU_POSE_OUTSIDE_MEMORY; } while (0)

static int read8(const mu_client_memory *memory, uint32_t address, uint8_t *value)
{
    uint8_t *p = at(memory, address, 1);
    if (!p)
        return 0;
    *value = p[0];
    return 1;
}

static int read16(const mu_client_memory *memory, uint32_t address, uint16_t *value)
{
    uint8_t *p = at(memory, address, 2);
    if (!p)
        return 0;
    *value = (uint16_t)(p[0] | (p[1] << 8));
    return 1;
}

/* MOVSX of a 16-bit field. */
static int read_s16(const mu_client_memory *memory, uint32_t address, int32_t *value)
{
    uint16_t raw;
    if (!read16(memory, address, &raw))
        return 0;
    *value = (int16_t)raw;
    return 1;
}

static int write16(const mu_client_memory *memory, uint32_t address, uint16_t value)
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
    *value = load32(p);
    return 1;
}

static int write32(const mu_client_memory *memory, uint32_t address, uint32_t value)
{
    uint8_t *p = at(memory, address, 4);
    if (!p)
        return 0;
    store32(p, value);
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
    return write32(memory, address, float_bits(value));
}

/* CVTTSS2SI: truncation, with 0x80000000 for NaN and out-of-range values. */
static int32_t truncate32(float value)
{
    if (!(value >= -2147483648.0f && value < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)value;
}

/* Signed 32-bit address arithmetic as in IMUL/SHL/ADD. */
static uint32_t scaled(uint32_t base, int32_t index, uint32_t stride)
{
    return base + (uint32_t)index * stride;
}

int mu_pose_build(const mu_client_memory *memory, uint32_t model, mu_pose_arguments *arguments,
                  const mu_pose_globals *globals)
{
    int32_t actions, keys, frame_index;
    uint32_t action_array;
    uint16_t current;

    CHECK(read_s16(memory, model + 0x26, &actions));
    if (actions <= 0)
        return MU_POSE_OK;
    uint16_t prior = (uint16_t)arguments->prior_action;
    CHECK(read_s16(memory, model + 0x26, &actions));
    if ((int32_t)prior >= actions) {
        prior = 0;
        arguments->prior_action &= 0xffff0000u;
    }
    CHECK(read16(memory, model + 0xa8, &current));
    CHECK(read_s16(memory, model + 0x26, &actions));
    if ((int32_t)current >= actions)
        CHECK(write16(memory, model + 0xa8, 0));
    for (uint32_t component = 0; component < 3; ++component) {
        uint32_t value;
        CHECK(read32(memory, arguments->angles + component * 4, &value));
        CHECK(write32(memory, model + 0x84 + component * 4, value));
    }
    CHECK(write32(memory, model + 0xac, arguments->frame));
    CHECK(write16(memory, model + 0xb4, (uint16_t)truncate32(bits_float(arguments->frame))));
    float frame;
    CHECK(read_s16(memory, model + 0xb4, &frame_index));
    CHECK(read_float(memory, model + 0xac, &frame));
    volatile float t = frame - (float)frame_index;
    volatile float complement = 1.0f - t;
    int32_t prior_frame = truncate32(bits_float(arguments->prior_frame));

    CHECK(read_s16(memory, model + 0x26, &actions));
    if (actions > 0) {
        if (prior_frame < 0)
            prior_frame = 0;
        CHECK(read_s16(memory, model + 0xb4, &frame_index));
        if (frame_index < 0)
            CHECK(write16(memory, model + 0xb4, 0));
        CHECK(read32(memory, model + 0x30, &action_array));
        CHECK(read_s16(memory, action_array + ((uint32_t)prior << 4) + 8, &keys));
        if (prior_frame >= keys)
            prior_frame = 0;
        CHECK(read_s16(memory, model + 0xb4, &frame_index));
        CHECK(read16(memory, model + 0xa8, &current));
        CHECK(read32(memory, model + 0x30, &action_array));
        CHECK(read_s16(memory, action_array + ((uint32_t)current << 4) + 8, &keys));
        if (frame_index >= keys)
            CHECK(write16(memory, model + 0xb4, 0));
    }

    for (int32_t index = 0;; ++index) {
        int32_t bones;
        CHECK(read_s16(memory, model + 0x22, &bones));
        if (index >= bones)
            break;
        uint32_t array, tracks;
        CHECK(read32(memory, model + 0x2c, &array));
        uint32_t bone = scaled(array, index, 0x8c);
        uint8_t dummy;
        CHECK(read8(memory, bone + 0x22, &dummy));
        if ((int8_t)dummy != 0)
            continue;
        CHECK(read32(memory, bone + 0x24, &tracks));
        uint32_t prior_entry = (uint32_t)prior * 12u + tracks;
        CHECK(read16(memory, model + 0xa8, &current));
        CHECK(read32(memory, bone + 0x24, &tracks));
        uint32_t current_entry = (uint32_t)current * 12u + tracks;

        uint8_t q1[16], q2[16];
        uint32_t special;
        CHECK(read32(memory, model + 0x60, &special));
        if (index == (int32_t)special) {
            uint8_t a1[12], a2[12];
            uint32_t base, value;
            for (uint32_t component = 0; component < 3; ++component) {
                CHECK(read32(memory, prior_entry + 4, &base));
                CHECK(read32(memory, scaled(base, prior_frame, 12) + component * 4, &value));
                store32(a1 + component * 4, value);
            }
            for (uint32_t component = 0; component < 3; ++component) {
                CHECK(read_s16(memory, model + 0xb4, &frame_index));
                CHECK(read32(memory, current_entry + 4, &base));
                CHECK(read32(memory, scaled(base, frame_index, 12) + component * 4, &value));
                store32(a2 + component * 4, value);
            }
            /* Head angles in degrees, divided by binary32 57.29578 (0x01a85c38). */
            float head_x, head_y;
            CHECK(read_float(memory, arguments->head_angles, &head_x));
            volatile float x = head_x / 57.2957763671875f;
            CHECK(read_float(memory, arguments->head_angles + 4, &head_y));
            volatile float y = head_y / 57.2957763671875f;
            volatile float adjusted;
            adjusted = bits_float(load32(a1)) - x;
            store32(a1, float_bits(adjusted));
            adjusted = bits_float(load32(a2)) - x;
            store32(a2, float_bits(adjusted));
            adjusted = bits_float(load32(a1 + 8)) - y;
            store32(a1 + 8, float_bits(adjusted));
            adjusted = bits_float(load32(a2 + 8)) - y;
            store32(a2 + 8, float_bits(adjusted));
            mu_rotation_quaternion(a1, q1);
            mu_rotation_quaternion(a2, q2);
        } else {
            uint32_t base, value;
            for (uint32_t component = 0; component < 4; ++component) {
                CHECK(read32(memory, prior_entry + 8, &base));
                CHECK(read32(memory, scaled(base, prior_frame, 16) + component * 4, &value));
                store32(q1 + component * 4, value);
            }
            for (uint32_t component = 0; component < 4; ++component) {
                CHECK(read_s16(memory, model + 0xb4, &frame_index));
                CHECK(read32(memory, current_entry + 8, &base));
                CHECK(read32(memory, scaled(base, frame_index, 16) + component * 4, &value));
                store32(q2 + component * 4, value);
            }
        }

        uint32_t slot = globals->bone_quaternions + ((uint32_t)index << 4);
        uint8_t *quaternion = at(memory, slot, 16);
        CHECK(quaternion);
        if (mu_quaternion_compare(q1, q2) == 0)
            mu_quaternion_slerp(q1, q2, t, quaternion);
        else
            memcpy(quaternion, q1, 16);
        uint8_t local[48];
        memset(local, 0, sizeof local);
        mu_quaternion_matrix(quaternion, local);

        uint32_t position1, position2;
        CHECK(read32(memory, prior_entry, &position1));
        position1 = scaled(position1, prior_frame, 12);
        CHECK(read_s16(memory, model + 0xb4, &frame_index));
        CHECK(read32(memory, current_entry, &position2));
        position2 = scaled(position2, frame_index, 12);
        int locked = 0;
        if (index == 0) {
            uint8_t flag;
            CHECK(read32(memory, model + 0x30, &action_array));
            CHECK(read8(memory, action_array + ((uint32_t)prior << 4) + 0xa, &flag));
            if (flag) {
                locked = 1;
            } else {
                CHECK(read16(memory, model + 0xa8, &current));
                CHECK(read32(memory, model + 0x30, &action_array));
                CHECK(read8(memory, action_array + ((uint32_t)current << 4) + 0xa, &flag));
                locked = flag != 0;
            }
        }
        float p1, p2;
        volatile float left, right;
        if (locked) {
            uint32_t base, value;
            for (uint32_t row = 0; row < 2; ++row) {
                CHECK(read32(memory, current_entry, &base));
                CHECK(read32(memory, base + row * 4, &value));
                store32(local + row * 16 + 12, value);
            }
            float height;
            CHECK(read_float(memory, position1 + 8, &p1));
            left = p1 * complement;
            CHECK(read_float(memory, position2 + 8, &p2));
            right = p2 * t;
            left = left + right;
            CHECK(read_float(memory, model + 0x90, &height));
            left = left + height;
            store32(local + 32 + 12, float_bits(left));
        } else {
            for (uint32_t row = 0; row < 3; ++row) {
                CHECK(read_float(memory, position1 + row * 4, &p1));
                left = p1 * complement;
                CHECK(read_float(memory, position2 + row * 4, &p2));
                right = p2 * t;
                store32(local + row * 16 + 12, float_bits(left + right));
            }
        }

        int32_t parent;
        CHECK(read_s16(memory, bone + 0x20, &parent));
        uint8_t *destination = at(memory, scaled(arguments->output, index, 0x30), 48);
        if (parent == -1) {
            uint8_t *root = at(memory, globals->root_matrix, 48);
            CHECK(root);
            if ((uint8_t)arguments->keep_root == 0) {
                uint8_t *angles = at(memory, model + 0x84, 12);
                CHECK(angles);
                mu_angle_matrix(angles, root);
                if ((uint8_t)arguments->translate != 0) {
                    for (uint32_t row = 0; row < 3; ++row)
                        for (uint32_t column = 0; column < 3; ++column) {
                            float value, scale;
                            uint32_t field = globals->root_matrix + row * 16 + column * 4;
                            CHECK(read_float(memory, field, &value));
                            CHECK(read_float(memory, model + 0x74, &scale));
                            volatile float product = value * scale;
                            CHECK(write_float(memory, field, product));
                        }
                    for (uint32_t row = 0; row < 3; ++row) {
                        uint32_t value;
                        CHECK(read32(memory, model + 0x78 + row * 4, &value));
                        CHECK(write32(memory, globals->root_matrix + row * 16 + 12, value));
                    }
                }
            }
            CHECK(destination);
            mu_pose_concat(root, local, destination);
        } else {
            CHECK(read_s16(memory, bone + 0x20, &parent));
            uint8_t *source = at(memory, scaled(arguments->output, parent, 0x30), 48);
            CHECK(source && destination);
            mu_pose_concat(source, local, destination);
        }
    }
    return MU_POSE_OK;
}
