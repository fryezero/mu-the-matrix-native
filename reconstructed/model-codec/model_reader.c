#include "model_reader.h"

#include <stddef.h>
#include <string.h>

/* Plaintext part of model reader 0x012b3812 (0x012b3b50..0x012b4477) and the
 * bone box pass 0x012b47fd. Client fields are reread where the original rereads
 * them and writes happen in the original order, so overlapping layouts follow
 * the same sequence of effects. */

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

static const mu_client_image *region_of(const mu_client_memory *memory, uint32_t address)
{
    for (uint32_t index = 0; index < memory->count; ++index) {
        const mu_client_image *region = &memory->regions[index];
        if (address >= region->base && address - region->base < region->size)
            return region;
    }
    return NULL;
}

static int read8(const mu_client_memory *m, uint32_t a, uint8_t *v)
{
    uint8_t *p = at(m, a, 1);
    if (!p)
        return 0;
    *v = p[0];
    return 1;
}

static int read16(const mu_client_memory *m, uint32_t a, uint16_t *v)
{
    uint8_t *p = at(m, a, 2);
    if (!p)
        return 0;
    *v = (uint16_t)(p[0] | (p[1] << 8));
    return 1;
}

static int read_s16(const mu_client_memory *m, uint32_t a, int32_t *v)
{
    uint16_t raw;
    if (!read16(m, a, &raw))
        return 0;
    *v = (int16_t)raw;
    return 1;
}

static int read32(const mu_client_memory *m, uint32_t a, uint32_t *v)
{
    uint8_t *p = at(m, a, 4);
    if (!p)
        return 0;
    *v = (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
    return 1;
}

static int write8(const mu_client_memory *m, uint32_t a, uint8_t v)
{
    uint8_t *p = at(m, a, 1);
    if (!p)
        return 0;
    p[0] = v;
    return 1;
}

static int write16(const mu_client_memory *m, uint32_t a, uint16_t v)
{
    uint8_t *p = at(m, a, 2);
    if (!p)
        return 0;
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    return 1;
}

static int write32(const mu_client_memory *m, uint32_t a, uint32_t v)
{
    uint8_t *p = at(m, a, 4);
    if (!p)
        return 0;
    for (unsigned byte = 0; byte < 4; ++byte)
        p[byte] = (uint8_t)(v >> (byte * 8));
    return 1;
}

static int readf(const mu_client_memory *m, uint32_t a, float *v)
{
    uint32_t bits;
    if (!read32(m, a, &bits))
        return 0;
    memcpy(v, &bits, sizeof *v);
    return 1;
}

static int writef(const mu_client_memory *m, uint32_t a, float v)
{
    uint32_t bits;
    memcpy(&bits, &v, sizeof bits);
    return write32(m, a, bits);
}

/* MUL followed by CMOVB -1. */
static uint32_t saturating(uint32_t a, uint32_t b)
{
    uint64_t product = (uint64_t)a * b;
    return (product >> 32) ? UINT32_MAX : (uint32_t)product;
}

/* Client memcpy 0x0194c200: memmove semantics; zero length touches nothing. */
static int copy(const mu_client_memory *m, uint32_t destination, uint32_t source, int32_t length)
{
    if (length == 0)
        return 1;
    if (length < 0)
        return 0;
    uint8_t *out = at(m, destination, (uint32_t)length);
    uint8_t *in = at(m, source, (uint32_t)length);
    if (!out || !in)
        return 0;
    memmove(out, in, (size_t)length);
    return 1;
}

#define CHECK(expression) do { if (!(expression)) { *offset = position; return MU_READER_OUTSIDE_MEMORY; } } while (0)
#define NEW(variable, request) do { variable = hooks->allocate(hooks->context, (request)); \
    if (!variable) { *offset = position; return MU_READER_ALLOCATION_FAILED; } } while (0)

/* [model+field] when at least 1, else 1 (the max(count,1) array sizes). */
static int at_least_one(const mu_client_memory *m, uint32_t address, int32_t *value)
{
    if (!read_s16(m, address, value))
        return 0;
    if (*value < 1)
        *value = 1;
    return 1;
}

/* Mesh record constructor 0x010a82d9, in its store order; byte +1 is untouched. */
static int construct_mesh(const mu_client_memory *m, uint32_t mesh)
{
    return write32(m, mesh + 0xc, 0) && write32(m, mesh + 0x10, 0) && write32(m, mesh + 0x18, 0) &&
           write32(m, mesh + 0x1c, 0) && write32(m, mesh + 0x14, 0) && write16(m, mesh + 2, 0) &&
           write8(m, mesh, 0) && write16(m, mesh + 0xa, 0) && write16(m, mesh + 8, 0) && write16(m, mesh + 6, 0) &&
           write16(m, mesh + 4, 0);
}

int mu_model_read_layout(const mu_client_memory *memory, uint32_t model, uint32_t stream, int32_t *offset,
                         const mu_reader_hooks *hooks, const mu_reader_globals *globals)
{
    const mu_client_memory *m = memory;
    int32_t position = *offset;
    uint16_t word;
    /* 0x012b3b50: name, then mesh, bone and action counts into +0x24, +0x22, +0x26. */
    CHECK(copy(m, model, stream + (uint32_t)position, 0x20));
    position += 0x20;
    static const uint32_t count_fields[3] = {0x24, 0x22, 0x26};
    for (unsigned k = 0; k < 3; ++k) {
        CHECK(read16(m, stream + (uint32_t)position, &word));
        CHECK(write16(m, model + count_fields[k], word));
        position += 2;
    }
    /* 0x012b3bb5: arrays sized max(count, 1). */
    int32_t n;
    uint32_t block;
    CHECK(at_least_one(m, model + 0x24, &n));
    int32_t mesh_slots = n;
    NEW(block, saturating((uint32_t)n, 0x20));
    for (int32_t i = 0; i < mesh_slots; ++i)   /* vector constructor iterator 0x0098642b */
        CHECK(construct_mesh(m, block + (uint32_t)i * 0x20u));
    CHECK(write32(m, model + 0x28, block));
    CHECK(at_least_one(m, model + 0x22, &n));
    NEW(block, saturating((uint32_t)n, 0x8c));
    CHECK(write32(m, model + 0x2c, block));
    CHECK(at_least_one(m, model + 0x26, &n));
    NEW(block, saturating((uint32_t)n, 0x10));
    CHECK(write32(m, model + 0x30, block));
    static const struct { uint32_t field, size; } tables[3] = {{0x34, 0x20}, {0x38, 4}, {0x3c, 4}};
    for (unsigned k = 0; k < 3; ++k) {
        CHECK(at_least_one(m, model + 0x24, &n));
        NEW(block, saturating((uint32_t)n, tables[k].size));
        CHECK(write32(m, model + tables[k].field, block));
    }
    CHECK(write32(m, model + 0x40, 0));
    CHECK(at_least_one(m, model + 0x24, &n));
    uint32_t zero_table;
    CHECK(read32(m, model + 0x3c, &zero_table));
    for (int32_t i = 0; i < n; ++i)            /* 0x010a8263(table, &zero, &count) */
        CHECK(write32(m, zero_table + (uint32_t)i * 4u, 0));

    /* 0x012b3e36: meshes. */
    for (int32_t i = 0;; ++i) {
        int32_t meshes;
        CHECK(read_s16(m, model + 0x24, &meshes));
        if (i >= meshes)
            break;
        uint32_t array;
        CHECK(read32(m, model + 0x28, &array));
        uint32_t mesh = ((uint32_t)i << 5) + array;
        static const uint32_t fields[5] = {4, 6, 8, 0xa, 2};
        for (unsigned k = 0; k < 5; ++k) {
            CHECK(read16(m, stream + (uint32_t)position, &word));
            CHECK(write16(m, mesh + fields[k], word));
            position += 2;
        }
        CHECK(write8(m, mesh, 0));
        static const struct { uint32_t count, pointer, stride; } arrays[4] = {
            {4, 0xc, 0x10}, {6, 0x10, 0x14}, {8, 0x14, 8}, {0xa, 0x18, 0x24}};
        for (unsigned k = 0; k < 4; ++k) {
            int32_t count;
            CHECK(read_s16(m, mesh + arrays[k].count, &count));
            NEW(block, saturating((uint32_t)count, arrays[k].stride));
            CHECK(write32(m, mesh + arrays[k].pointer, block));
        }
        for (unsigned k = 0; k < 3; ++k) {   /* vertices, normals, texcoords: one copy each */
            int32_t count;
            CHECK(read_s16(m, mesh + arrays[k].count, &count));
            int32_t length = (int32_t)((uint32_t)count * (k == 0 ? 16u : k == 1 ? 20u : 8u));
            uint32_t target;
            CHECK(read32(m, mesh + arrays[k].pointer, &target));
            CHECK(copy(m, target, stream + (uint32_t)position, length));
            position += length;
        }
        for (int32_t j = 0;; ++j) {          /* triangles: 0x24 of every 0x40 stream bytes */
            int32_t count;
            CHECK(read_s16(m, mesh + 0xa, &count));
            if (j >= count)
                break;
            uint32_t triangles;
            CHECK(read32(m, mesh + 0x18, &triangles));
            CHECK(copy(m, (uint32_t)j * 0x24u + triangles, stream + (uint32_t)position, 0x24));
            position += 0x40;
        }
        uint32_t names;
        CHECK(read32(m, model + 0x34, &names));
        CHECK(copy(m, names + ((uint32_t)i << 5), stream + (uint32_t)position, 0x20));
        position += 0x20;
        /* 0x012b4094..0x012b4134: texture-name record. */
        CHECK(read32(m, model + 0x34, &names));
        uint8_t flags[5] = {0, 0, 0, 0, 0};
        int parsed = hooks->name_flags(hooks->context, names + ((uint32_t)i << 5), flags);
        if (parsed & 0xff) {
            NEW(block, 5);
            for (unsigned k = 0; k < 5; ++k)  /* 0x010a8290 zeroes, 0x011850cc copies */
                CHECK(write8(m, block + k, 0));
            CHECK(write32(m, mesh + 0x1c, block));
            uint32_t sub;
            CHECK(read32(m, mesh + 0x1c, &sub));
            for (unsigned k = 0; k < 5; ++k)
                CHECK(write8(m, sub + k, flags[k]));
        } else {
            CHECK(write32(m, mesh + 0x1c, 0));
        }
    }

    /* 0x012b4149: actions. */
    for (int32_t i = 0;; ++i) {
        int32_t actions;
        CHECK(read_s16(m, model + 0x26, &actions));
        if (i >= actions)
            break;
        uint32_t array;
        CHECK(read32(m, model + 0x30, &array));
        uint32_t action = ((uint32_t)i << 4) + array;
        CHECK(write8(m, action, 0));
        CHECK(read16(m, stream + (uint32_t)position, &word));
        CHECK(write16(m, action + 8, word));
        position += 2;
        uint8_t lock;
        CHECK(read8(m, stream + (uint32_t)position, &lock));
        CHECK(write8(m, action + 0xa, lock));
        position += 1;
        CHECK(read8(m, action + 0xa, &lock));
        if (lock) {
            int32_t keys;
            CHECK(read_s16(m, action + 8, &keys));
            NEW(block, saturating(saturating((uint32_t)keys, 3), 4));
            CHECK(write32(m, action + 0xc, block));
            CHECK(read_s16(m, action + 8, &keys));
            int32_t length = (int32_t)((uint32_t)keys * 12u);
            uint32_t target;
            CHECK(read32(m, action + 0xc, &target));
            CHECK(copy(m, target, stream + (uint32_t)position, length));
            position += length;
        } else {
            CHECK(write32(m, action + 0xc, 0));
        }
    }

    /* 0x012b4225: bones (bone-track loop) inside the model's region. */
    const mu_client_image *window = region_of(m, model);
    CHECK(window);
    int status = mu_bone_tracks_read(window, model, stream, &position, hooks->allocate, hooks->context);
    if (status == MU_BONE_TRACKS_ALLOCATION_FAILED) {
        *offset = position;
        return MU_READER_ALLOCATION_FAILED;
    }
    CHECK(status == MU_BONE_TRACKS_OK);

    /* 0x012b4441: release the stream, 0x012b2df3(0), memset(+0xb6, 0xff, 0x14). */
    hooks->release(hooks->context, stream);
    CHECK(write32(m, model + 0x60, UINT32_MAX));
    CHECK(write8(m, model + 0x94, 0xff));
    int boxes = mu_model_bone_boxes(m, model, globals);
    if (boxes != MU_READER_OK) {
        *offset = position;
        return boxes;
    }
    for (uint32_t k = 0; k < 0x14; ++k)
        CHECK(write8(m, model + 0xb6 + k, 0xff));
    *offset = position;
    return MU_READER_OK;
}

#undef CHECK
#define CHECK(expression) do { if (!(expression)) return MU_READER_OUTSIDE_MEMORY; } while (0)

int mu_model_bone_boxes(const mu_client_memory *memory, uint32_t model, const mu_reader_globals *g)
{
    const mu_client_memory *m = memory;
    const float initial_min = 9999.0f, initial_max = -9999.0f;  /* 0x01a7edf8, 0x01a7ee10 */
    for (int32_t i = 0;; ++i) {
        int32_t bones;
        CHECK(read_s16(m, model + 0x22, &bones));
        if (i >= bones)
            break;
        for (uint32_t k = 0; k < 3; ++k) {
            CHECK(writef(m, g->box_min + (uint32_t)i * 12u + 4u * k, initial_min));
            CHECK(writef(m, g->box_max + (uint32_t)i * 12u + 4u * k, initial_max));
        }
        CHECK(write16(m, g->box_counts + (uint32_t)i * 2u, 0));
    }
    for (int32_t i = 0;; ++i) {
        int32_t meshes;
        CHECK(read_s16(m, model + 0x24, &meshes));
        if (i >= meshes)
            break;
        uint32_t array;
        CHECK(read32(m, model + 0x28, &array));
        uint32_t mesh = ((uint32_t)i << 5) + array;
        for (int32_t j = 0;; ++j) {
            int32_t vertices;
            CHECK(read_s16(m, mesh + 4, &vertices));
            if (j >= vertices)
                break;
            uint32_t base;
            CHECK(read32(m, mesh + 0xc, &base));
            uint32_t vertex = ((uint32_t)j << 4) + base;
            for (uint32_t k = 0; k < 3; ++k) {
                int32_t node;
                float slot, p;
                CHECK(read_s16(m, vertex, &node));
                uint32_t low = (uint32_t)node * 12u + g->box_min + 4u * k;
                CHECK(readf(m, low, &slot));
                CHECK(readf(m, vertex + 4 + 4 * k, &p));
                if (slot > p) {                        /* COMISS; JBE skips unordered and <= */
                    CHECK(read_s16(m, vertex, &node));
                    CHECK(writef(m, (uint32_t)node * 12u + g->box_min + 4u * k, p));
                }
                CHECK(read_s16(m, vertex, &node));
                uint32_t high = (uint32_t)node * 12u + g->box_max + 4u * k;
                CHECK(readf(m, vertex + 4 + 4 * k, &p));
                CHECK(readf(m, high, &slot));
                if (p > slot) {
                    CHECK(read_s16(m, vertex, &node));
                    CHECK(writef(m, (uint32_t)node * 12u + g->box_max + 4u * k, p));
                }
            }
            int32_t node;
            uint16_t count;
            CHECK(read_s16(m, vertex, &node));
            CHECK(read16(m, (uint32_t)node * 2u + g->box_counts, &count));
            CHECK(read_s16(m, vertex, &node));
            CHECK(write16(m, (uint32_t)node * 2u + g->box_counts, (uint16_t)(count + 1u)));
        }
    }
    for (int32_t i = 0;; ++i) {
        int32_t bones;
        CHECK(read_s16(m, model + 0x22, &bones));
        if (i >= bones)
            break;
        uint32_t array;
        CHECK(read32(m, model + 0x2c, &array));
        uint32_t bone = (uint32_t)i * 0x8cu + array;
        uint16_t count;
        CHECK(read16(m, (uint32_t)i * 2u + g->box_counts, &count));
        CHECK(write8(m, bone + 0x28, count != 0));
        for (uint32_t corner = 0; corner < 8; ++corner)
            for (uint32_t k = 0; k < 3; ++k) {
                uint32_t table = (corner >> (2 - k)) & 1 ? g->box_min : g->box_max;
                uint32_t value;
                CHECK(read32(m, (uint32_t)i * 12u + table + 4u * k, &value));
                CHECK(write32(m, bone + 0x2c + corner * 12u + 4u * k, value));
            }
    }
    return MU_READER_OK;
}
