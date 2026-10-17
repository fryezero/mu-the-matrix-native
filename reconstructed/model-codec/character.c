#include "character.h"

#include <stdio.h>
#include <string.h>

#include "../record-math/record_math.h"

/* Rotation position 0x012b7019, transform position 0x012b6ef1 and the class
 * helpers 0x0139d6a2, 0x0139cb8a, 0x0139d89f, 0x0095f5cc. Client memory is
 * read where the original reads it and written in the original order. */

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
    memcpy(value, &bits, sizeof bits);
    return 1;
}

static int write_float(const mu_client_memory *memory, uint32_t address, float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return write32(memory, address, bits);
}

#define CHECK(expression) do { if (!(expression)) return MU_CHARACTER_OUTSIDE_MEMORY; } while (0)

/* The vector helpers read their operands before writing the local result,
 * which stands in for the original's stack temporary. */
static int helper(const mu_client_memory *memory, void (*function)(const void *, const void *, void *),
                  uint32_t in, uint32_t matrix, float result[3])
{
    uint8_t *a = at(memory, in, 12), *m = at(memory, matrix, 48);
    if (!a || !m)
        return 0;
    uint8_t local[12];
    function(a, m, local);
    memcpy(result, local, sizeof local);
    return 1;
}

int mu_rotation_position(const mu_client_memory *memory, uint32_t model, uint32_t matrix, uint32_t vector,
                         uint32_t out, uint32_t root_matrix)
{
    if (matrix == 0)
        return MU_CHARACTER_OK;
    float t[3];
    CHECK(helper(memory, mu_vector_rotate, vector, matrix, t));
    for (uint32_t k = 0; k < 3; ++k) {
        float scale;
        CHECK(read_float(memory, model + 0x74, &scale));
        volatile float product = scale * t[k];
        CHECK(write_float(memory, out + 4 * k, product));
    }
    for (uint32_t row = 0; row < 3; ++row)
        for (uint32_t column = 0; column < 4; ++column) {
            uint32_t value;
            CHECK(read32(memory, matrix + row * 16 + column * 4, &value));
            CHECK(write32(memory, root_matrix + row * 16 + column * 4, value));
        }
    return MU_CHARACTER_OK;
}

int mu_transform_position(const mu_client_memory *memory, uint32_t model, uint32_t matrix, uint32_t vector,
                          uint32_t out, uint32_t world)
{
    if (matrix == 0)
        return MU_CHARACTER_OK;
    if ((uint8_t)world == 0) {
        uint8_t *a = at(memory, vector, 12), *m = at(memory, matrix, 48), *o = at(memory, out, 12);
        CHECK(a && m && o);
        mu_vector_transform(a, m, o);
        return MU_CHARACTER_OK;
    }
    float t[3];
    CHECK(helper(memory, mu_vector_transform, vector, matrix, t));
    for (uint32_t k = 0; k < 3; ++k) {
        float scale;
        CHECK(read_float(memory, model + 0x74, &scale));
        volatile float product = scale * t[k];
        t[k] = product;
    }
    for (uint32_t k = 0; k < 3; ++k) {
        float origin;
        CHECK(read_float(memory, model + 0x78 + 4 * k, &origin));
        volatile float sum = t[k] + origin;
        CHECK(write_float(memory, out + 4 * k, sum));
    }
    return MU_CHARACTER_OK;
}

uint8_t mu_character_class_tier(uint8_t class_byte)
{
    uint8_t flags = (uint8_t)((class_byte >> 4) & 0xf);
    if (flags == 0)
        return 1;
    for (int bit = 3; bit >= 0; --bit)
        if ((flags >> bit) & 1)
            return (uint8_t)(bit + 2);
    return 1;  /* unreachable: a nonzero nibble has a set bit */
}

uint8_t mu_character_skin_index(uint8_t class_byte)
{
    uint8_t base = (uint8_t)(class_byte & 0xf);
    uint8_t tier = (uint8_t)(mu_character_class_tier(class_byte) - 1);
    return (uint8_t)(base + (uint8_t)(tier << 4));
}

uint8_t mu_character_skips_tier2(uint8_t class_byte)
{
    uint8_t base = (uint8_t)(class_byte & 0xf);
    return (uint8_t)(base == 3 || base == 4 || base == 6 || base == 7);
}

uint32_t mu_character_part_type(int slot, uint8_t class_byte)
{
    return MU_CHARACTER_PART_BASE + (uint32_t)(slot - 1) * MU_CHARACTER_PART_STRIDE + mu_character_skin_index(class_byte);
}

int mu_character_part_file(uint32_t type, char *out, size_t size)
{
    static const char *const names[5] = {"Helm", "Armor", "Pant", "Glove", "Boot"};
    static const char *const tiers[5] = {"Class", "Class2", "Class3", "Class4", "Class4"};
    if (type < MU_CHARACTER_PART_BASE || type >= MU_CHARACTER_PART_BASE + 5 * MU_CHARACTER_PART_STRIDE)
        return 0;
    uint32_t offset = type - MU_CHARACTER_PART_BASE;
    uint32_t slot = offset / MU_CHARACTER_PART_STRIDE, within = offset % MU_CHARACTER_PART_STRIDE;
    uint32_t tier = within / 16, base = within % 16;
    if (tier == 1 && mu_character_skips_tier2((uint8_t)base))
        return 0;
    int index = (int)base + 1;
    int written = snprintf(out, size, index < 10 ? "%s%s0%d.bmd" : "%s%s%d.bmd", names[slot], tiers[tier], index);
    return written > 0 && (size_t)written < size;
}
