#include "bone_tracks.h"

#include <stddef.h>
#include <string.h>

#include "../record-math/record_math.h"

/* Bone-track loop 0x012b4225..0x012b4441. Every field is reread from client
 * memory where the original rereads it, so overlapping layouts follow the same
 * sequence of effects. */

static uint8_t *at(const mu_client_image *image, uint32_t address, uint32_t length)
{
    if (address < image->base)
        return NULL;
    uint32_t start = address - image->base;
    if (start > image->size || length > image->size - start)
        return NULL;
    return image->bytes + start;
}

static int read8(const mu_client_image *image, uint32_t address, uint8_t *value)
{
    uint8_t *p = at(image, address, 1);
    if (!p)
        return 0;
    *value = p[0];
    return 1;
}

static int read16(const mu_client_image *image, uint32_t address, uint16_t *value)
{
    uint8_t *p = at(image, address, 2);
    if (!p)
        return 0;
    *value = (uint16_t)(p[0] | (p[1] << 8));
    return 1;
}

static int read32(const mu_client_image *image, uint32_t address, uint32_t *value)
{
    uint8_t *p = at(image, address, 4);
    if (!p)
        return 0;
    *value = (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
    return 1;
}

static int write32(const mu_client_image *image, uint32_t address, uint32_t value)
{
    uint8_t *p = at(image, address, 4);
    if (!p)
        return 0;
    for (unsigned byte = 0; byte < 4; ++byte)
        p[byte] = (uint8_t)(value >> (byte * 8));
    return 1;
}

/* Signed 16-bit count read with MOVSX. */
static int read_count(const mu_client_image *image, uint32_t address, int32_t *value)
{
    uint16_t raw;
    if (!read16(image, address, &raw))
        return 0;
    *value = (int16_t)raw;
    return 1;
}

/* MUL followed by CMOVB -1: unsigned 32x32 product saturated on carry. */
static uint32_t saturating(uint32_t a, uint32_t b)
{
    uint64_t product = (uint64_t)a * b;
    return (product >> 32) ? UINT32_MAX : (uint32_t)product;
}

/* Client memcpy 0x0194c200 copies backward when destination lies inside the
 * source span, otherwise forward; the visible result is memmove. Zero-length
 * copies access nothing. A negative length is never reached here because the
 * matching allocation request saturates first. */
static int copy(const mu_client_image *image, uint32_t destination, uint32_t source, int32_t length)
{
    if (length == 0)
        return 1;
    if (length < 0)
        return 0;
    uint8_t *out = at(image, destination, (uint32_t)length);
    uint8_t *in = at(image, source, (uint32_t)length);
    if (!out || !in)
        return 0;
    memmove(out, in, (size_t)length);
    return 1;
}

#define CHECK(expression) do { if (!(expression)) { *offset = position; return MU_BONE_TRACKS_OUTSIDE_IMAGE; } } while (0)

int mu_bone_tracks_read(const mu_client_image *image, uint32_t model, uint32_t stream,
                        int32_t *offset, mu_client_allocate allocate, void *context)
{
    int32_t position = *offset;
    for (int32_t index = 0;; ++index) {
        int32_t bones;
        CHECK(read_count(image, model + 0x22, &bones));
        if (index >= bones)
            break;
        uint32_t array;
        CHECK(read32(image, model + 0x2c, &array));
        uint32_t bone = array + (uint32_t)index * 0x8cu;
        uint8_t flag;
        CHECK(read8(image, stream + (uint32_t)position, &flag));
        uint8_t *slot = at(image, bone + 0x22, 1);
        CHECK(slot);
        *slot = flag;
        position += 1;
        CHECK(read8(image, bone + 0x22, &flag));
        if ((int8_t)flag != 0)
            continue;
        CHECK(copy(image, bone, stream + (uint32_t)position, 0x20));
        position += 0x20;
        uint16_t parent;
        CHECK(read16(image, stream + (uint32_t)position, &parent));
        uint8_t *field = at(image, bone + 0x20, 2);
        CHECK(field);
        field[0] = (uint8_t)parent;
        field[1] = (uint8_t)(parent >> 8);
        position += 2;

        int32_t actions;
        CHECK(read_count(image, model + 0x26, &actions));
        uint32_t tracks = allocate(context, saturating((uint32_t)actions, 12));
        if (!tracks) {
            *offset = position;
            return MU_BONE_TRACKS_ALLOCATION_FAILED;
        }
        CHECK(write32(image, bone + 0x24, tracks));
        for (int32_t action = 0;; ++action) {
            CHECK(read_count(image, model + 0x26, &actions));
            if (action >= actions)
                break;
            uint32_t entry, action_array;
            CHECK(read32(image, bone + 0x24, &entry));
            entry += (uint32_t)action * 12u;
            int32_t keys, copied;
            CHECK(read32(image, model + 0x30, &action_array));
            CHECK(read_count(image, action_array + ((uint32_t)action << 4) + 8, &copied));
            copied = (int32_t)((uint32_t)copied * 12u);
            CHECK(read32(image, model + 0x30, &action_array));
            CHECK(read_count(image, action_array + ((uint32_t)action << 4) + 8, &keys));
            uint32_t vector_bytes = saturating(saturating((uint32_t)keys, 3), 4);
            uint32_t quaternion_bytes = saturating(saturating((uint32_t)keys, 4), 4);
            static const uint32_t fields[3] = {0, 4, 8};
            for (unsigned item = 0; item < 3; ++item) {
                uint32_t block = allocate(context, item == 2 ? quaternion_bytes : vector_bytes);
                if (!block) {
                    *offset = position;
                    return MU_BONE_TRACKS_ALLOCATION_FAILED;
                }
                CHECK(write32(image, entry + fields[item], block));
            }
            uint32_t target;
            CHECK(read32(image, entry, &target));
            CHECK(copy(image, target, stream + (uint32_t)position, copied));
            position += copied;
            CHECK(read32(image, entry + 4, &target));
            CHECK(copy(image, target, stream + (uint32_t)position, copied));
            position += copied;
            for (int32_t key = 0; key < keys; ++key) {
                uint32_t rotations, quaternions;
                CHECK(read32(image, entry + 8, &quaternions));
                CHECK(read32(image, entry + 4, &rotations));
                uint8_t *output = at(image, quaternions + ((uint32_t)key << 4), 16);
                uint8_t *input = at(image, rotations + (uint32_t)key * 12u, 12);
                CHECK(output && input);
                mu_rotation_quaternion(input, output);
            }
        }
    }
    *offset = position;
    return MU_BONE_TRACKS_OK;
}
