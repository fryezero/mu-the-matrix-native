/* Checked BMD loader for the native viewer. See mu_bmd.h.
 * The parse order and every check mirror model-recovery/bmd10.py. */
#include "mu_bmd.h"

#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/model-codec/client_lea.h"
#include "../../reconstructed/model-codec/model_codec.h"

/* model-recovery/modulus.cpp (Crypto++), linked as C. */
int mu_modulus_decrypt(const unsigned char *input, size_t length, unsigned char *output, size_t capacity,
                       size_t *written, char *error, size_t error_capacity);

/* Published asset-format constant (model-recovery/bmd_encrypted.py FORMAT_KEY),
 * not an account or authentication key. */
static const uint8_t lea_format_key[32] = {
    0xcc, 0x50, 0x45, 0x13, 0xc2, 0xa6, 0x57, 0x4e, 0xd6, 0x9a, 0x45, 0x89, 0xbf, 0x2f, 0xbc, 0xd9,
    0x39, 0xb3, 0xb3, 0xbd, 0x50, 0xbd, 0xcc, 0xb6, 0x85, 0x46, 0xd1, 0xd6, 0x16, 0x54, 0xe0, 0x87};

int16_t mu_bmd_s16(const uint8_t *p) { return (int16_t)(uint16_t)(p[0] | (p[1] << 8)); }

static uint32_t u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

float mu_bmd_f32(const uint8_t *p)
{
    uint32_t bits = u32(p);
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

typedef struct reader {
    const uint8_t *data;   /* "BMD\x0a" + payload, as in bmd10.py */
    size_t size, offset;
    char *error;
    size_t error_size;
    int failed;
} reader;

static int fail(reader *r, const char *format, ...)
{
    if (!r->failed && r->error && r->error_size) {
        va_list list;
        va_start(list, format);
        vsnprintf(r->error, r->error_size, format, list);
        va_end(list);
    }
    r->failed = 1;
    return 0;
}

static const uint8_t *take(reader *r, size_t size)
{
    if (r->failed)
        return NULL;
    if (size > r->size - r->offset) {
        fail(r, "Truncated read at offset %zu: need %zu bytes", r->offset, size);
        return NULL;
    }
    const uint8_t *p = r->data + r->offset;
    r->offset += size;
    return p;
}

static int finite_floats(reader *r, const uint8_t *p, size_t start, unsigned first, unsigned count)
{
    for (unsigned index = 0; index < count; ++index)
        if (!isfinite(mu_bmd_f32(p + first + 4 * index)))
            return fail(r, "Non-finite numeric data at layout offset %zu", start + first + 4 * index);
    return 1;
}

static int read_s16(reader *r, int32_t *value)
{
    const uint8_t *p = take(r, 2);
    if (!p)
        return 0;
    *value = mu_bmd_s16(p);
    return 1;
}

static int read_flag(reader *r, uint8_t *value)
{
    const uint8_t *p = take(r, 1);
    if (!p)
        return 0;
    if (p[0] > 1)
        return fail(r, "Non-boolean flag %u near offset %zu", p[0], r->offset);
    *value = p[0];
    return 1;
}

static int read_string(reader *r, char out[33])
{
    const uint8_t *p = take(r, 32);
    if (!p)
        return 0;
    memcpy(out, p, 32);
    out[32] = 0;
    return 1;
}

static int check_count(reader *r, int32_t value, const char *label, int32_t maximum)
{
    if (value < 0 || value > maximum)
        return fail(r, "Invalid %s count %d", label, (int)value);
    return 1;
}

static int parse_layout(reader *r, mu_bmd *m, int lea_padding)
{
    if (r->size > MU_BMD_MAX_FILE || r->size < 42)
        return fail(r, "File outside supported size limits");
    const uint8_t *header = take(r, 4);
    if (!header || memcmp(header, "BMD\x0a", 4) != 0)
        return fail(r, "Only plaintext BMD version 10 is supported");
    if (!read_string(r, m->name))
        return 0;
    const uint8_t *counts = take(r, 6);
    if (!counts)
        return 0;
    int32_t nm = counts[0] | (counts[1] << 8), nb = counts[2] | (counts[3] << 8), na = counts[4] | (counts[5] << 8);
    if (!check_count(r, nm, "mesh", MU_BMD_MAX_COUNT) || !check_count(r, nb, "bone", MU_BMD_MAX_COUNT) ||
        !check_count(r, na, "action", MU_BMD_MAX_COUNT))
        return 0;
    m->mesh_count = nm;
    m->bone_count = nb;
    m->action_count = na;
    m->meshes = calloc((size_t)(nm ? nm : 1), sizeof *m->meshes);
    m->actions = calloc((size_t)(na ? na : 1), sizeof *m->actions);
    m->bones = calloc((size_t)(nb ? nb : 1), sizeof *m->bones);
    if (!m->meshes || !m->actions || !m->bones)
        return fail(r, "Out of memory");

    for (int32_t mi = 0; mi < nm; ++mi) {
        mu_bmd_mesh *mesh = &m->meshes[mi];
        int32_t nv, nn, nt, nf, texture;
        if (!read_s16(r, &nv) || !read_s16(r, &nn) || !read_s16(r, &nt) || !read_s16(r, &nf) || !read_s16(r, &texture))
            return 0;
        if (!check_count(r, nv, "vertex", 32767) || !check_count(r, nn, "normal", 32767) ||
            !check_count(r, nt, "texcoord", 32767) || !check_count(r, nf, "polygon", 32767))
            return 0;
        size_t minimum = (size_t)nv * 16 + (size_t)nn * 20 + (size_t)nt * 8 + (size_t)nf * 64 + 32;
        if (minimum > r->size - r->offset)
            return fail(r, "Mesh %d arrays exceed file bounds", (int)mi);
        mesh->texture_index = (int16_t)texture;
        mesh->vertex_count = nv;
        mesh->normal_count = nn;
        mesh->uv_count = nt;
        mesh->polygon_count = nf;
        mesh->vertex_offset = (uint32_t)(r->offset - 4);
        for (int32_t k = 0; k < nv; ++k) {
            size_t start = r->offset;
            const uint8_t *p = take(r, 16);
            if (!p || !finite_floats(r, p, start, 4, 3))
                return 0;
        }
        mesh->normal_offset = (uint32_t)(r->offset - 4);
        for (int32_t k = 0; k < nn; ++k) {
            size_t start = r->offset;
            const uint8_t *p = take(r, 20);
            if (!p || !finite_floats(r, p, start, 4, 3))
                return 0;
        }
        mesh->uv_offset = (uint32_t)(r->offset - 4);
        for (int32_t k = 0; k < nt; ++k) {
            size_t start = r->offset;
            const uint8_t *p = take(r, 8);
            if (!p || !finite_floats(r, p, start, 0, 2))
                return 0;
        }
        mesh->polygon_offset = (uint32_t)(r->offset - 4);
        for (int32_t fi = 0; fi < nf; ++fi) {
            size_t face = r->offset;
            const uint8_t *block = take(r, 64);
            if (!block)
                return 0;
            unsigned corners = block[0];
            if (corners != 3 && corners != 4)
                return fail(r, "Mesh %d polygon %d: unsupported corner count %u", (int)mi, (int)fi, corners);
            static const unsigned fields[3] = {2, 10, 18};
            static const char *kinds[3] = {"vertex", "normal", "UV"};
            const int32_t upper[3] = {nv, nn, nt};
            for (unsigned a = 0; a < 3; ++a)
                for (unsigned c = 0; c < corners; ++c) {
                    int32_t index = mu_bmd_s16(block + fields[a] + 2 * c);
                    if (index < 0 || index >= upper[a])
                        return fail(r, "Mesh %d polygon %d: invalid active %s index %d at corner %u at layout offset %zu",
                                    (int)mi, (int)fi, kinds[a], (int)index, c, face + fields[a] + 2 * c);
                }
        }
        if (!read_string(r, mesh->texture))
            return 0;
    }
    for (int32_t ai = 0; ai < na; ++ai) {
        int32_t keys;
        uint8_t locked;
        if (!read_s16(r, &keys) || !check_count(r, keys, "animation key", 32767) || !read_flag(r, &locked))
            return 0;
        m->actions[ai].keys = keys;
        m->actions[ai].lock_positions = locked;
        if (locked)
            for (int32_t k = 0; k < keys; ++k) {
                size_t start = r->offset;
                const uint8_t *p = take(r, 12);
                if (!p || !finite_floats(r, p, start, 0, 3))
                    return 0;
            }
    }
    m->bone_stream = (uint32_t)(r->offset - 4);
    for (int32_t bi = 0; bi < nb; ++bi) {
        mu_bmd_bone *bone = &m->bones[bi];
        bone->offset = (uint32_t)(r->offset - 4);
        bone->parent = -1;
        if (!read_flag(r, &bone->dummy))
            return 0;
        if (bone->dummy)
            continue;
        int32_t parent;
        if (!read_string(r, bone->name) || !read_s16(r, &parent))
            return 0;
        if (parent < -1 || parent >= nb)
            return fail(r, "Bone %d: invalid parent %d", (int)bi, (int)parent);
        bone->parent = (int16_t)parent;
        for (int32_t ai = 0; ai < na; ++ai) {
            int32_t keys = m->actions[ai].keys;
            if ((size_t)keys * 24 > r->size - r->offset)
                return fail(r, "Bone %d: animation arrays exceed file bounds", (int)bi);
            for (int32_t k = 0; k < 2 * keys; ++k) {
                size_t start = r->offset;
                const uint8_t *p = take(r, 12);
                if (!p || !finite_floats(r, p, start, 0, 3))
                    return 0;
            }
        }
    }
    size_t trailer = r->size - r->offset;
    if (trailer && (!lea_padding || trailer > 16 || (r->size - 4) % 16))
        return fail(r, "%zu unparsed trailing bytes at offset %zu", trailer, r->offset);
    for (int32_t mi = 0; mi < nm; ++mi) {
        const mu_bmd_mesh *mesh = &m->meshes[mi];
        const uint8_t *payload = r->data + 4;
        for (int32_t k = 0; k < mesh->vertex_count; ++k) {
            int32_t node = mu_bmd_s16(payload + mesh->vertex_offset + 16 * (uint32_t)k);
            if (node < 0 || node >= nb || m->bones[node].dummy)
                return fail(r, "Mesh %d vertex %d: unsupported vertex bone %d", (int)mi, (int)k, (int)node);
        }
        for (int32_t k = 0; k < mesh->normal_count; ++k) {
            const uint8_t *p = payload + mesh->normal_offset + 20 * (uint32_t)k;
            int32_t node = mu_bmd_s16(p), bind = mu_bmd_s16(p + 16);
            if (node < 0 || node >= nb || m->bones[node].dummy)
                return fail(r, "Mesh %d normal %d: unsupported normal bone %d", (int)mi, (int)k, (int)node);
            if (bind < -1 || bind >= mesh->vertex_count)
                return fail(r, "Mesh %d: invalid normal bind vertex %d", (int)mi, (int)bind);
        }
    }
    /* Parent chains: no cycle, and no non-dummy bone below a dummy ancestor. */
    uint8_t *seen = calloc((size_t)(nb ? nb : 1), 1);
    if (!seen)
        return fail(r, "Out of memory");
    for (int32_t bi = 0; bi < nb; ++bi) {
        memset(seen, 0, (size_t)nb);
        int32_t current = bi, owner = bi;
        while (current != -1) {
            if (seen[current]) {
                free(seen);
                return fail(r, "Bone parent cycle");
            }
            seen[current] = 1;
            const mu_bmd_bone *ancestor = &m->bones[current];
            if (ancestor->dummy) {
                if (current != bi) {
                    free(seen);
                    return fail(r, "Bone %d: parent %d references dummy bone", (int)owner, (int)current);
                }
                break;
            }
            owner = current;
            current = ancestor->parent;
        }
    }
    free(seen);
    m->parsed_size = (uint32_t)(r->offset - 4);
    return 1;
}

void mu_bmd_free(mu_bmd *model)
{
    if (!model)
        return;
    free(model->payload);
    free(model->meshes);
    free(model->actions);
    free(model->bones);
    memset(model, 0, sizeof *model);
}

static int set_error(char *error, size_t size, const char *message)
{
    if (error && size)
        snprintf(error, size, "%s", message);
    return MU_BMD_ERROR;
}

int mu_bmd_load(const uint8_t *raw, size_t size, mu_bmd *model, char *error, size_t error_size)
{
    memset(model, 0, sizeof *model);
    if (error && error_size)
        error[0] = 0;
    if (!raw || size > MU_BMD_MAX_FILE || size < 4 || memcmp(raw, "BMD", 3) != 0)
        return set_error(error, error_size, "Invalid BMD envelope or unsupported file size");
    int version = raw[3];
    uint8_t *layout = NULL;
    size_t layout_size = 0;
    if (version == 10) {
        layout = malloc(size);
        if (!layout)
            return set_error(error, error_size, "Out of memory");
        memcpy(layout, raw, size);
        layout_size = size;
    } else if (version == 12 || version == 14 || version == 15) {
        if (size < 8)
            return set_error(error, error_size, "Truncated encrypted envelope");
        uint32_t length = u32(raw + 4);
        if ((size_t)length != size - 8)
            return set_error(error, error_size, "Declared encrypted length must match the complete payload");
        const uint8_t *body = raw + 8;
        size_t plain_size = length;
        if (version == 14) {
            if (length < 34)
                return set_error(error, error_size, "BMD v14 requires a complete 34-byte cipher prefix");
            plain_size = length - 34;
        }
        if (version == 15 && length % 16)
            return set_error(error, error_size, "LEA ECB requires complete blocks and a 32-byte key");
        layout = malloc(plain_size + 4);
        if (!layout)
            return set_error(error, error_size, "Out of memory");
        memcpy(layout, "BMD\x0a", 4);
        layout_size = plain_size + 4;
        if (version == 12) {
            mu_bmd12_decode(layout + 4, body, (int32_t)length);
        } else if (version == 14) {
            size_t written = 0;
            char message[256];
            if (mu_modulus_decrypt(body, length, layout + 4, plain_size, &written, message, sizeof message) ||
                written != plain_size) {
                free(layout);
                return set_error(error, error_size, message[0] ? message : "BMD v14 decoder failed");
            }
        } else {
            uint8_t context[MU_CLIENT_LEA_CONTEXT_BYTES];
            memset(context, 0, sizeof context);
            mu_client_lea_setup(context, lea_format_key, 32);
            mu_client_lea_decode(layout + 4, body, length, context);
        }
    } else {
        char message[64];
        snprintf(message, sizeof message, "Unsupported model version %d", version);
        return set_error(error, error_size, message);
    }
    reader r = {layout, layout_size, 0, error, error_size, 0};
    if (!parse_layout(&r, model, version == 15)) {
        free(layout);
        mu_bmd_free(model);
        return MU_BMD_ERROR;
    }
    model->version = version;
    model->payload = malloc(layout_size - 4 ? layout_size - 4 : 1);
    if (!model->payload) {
        free(layout);
        mu_bmd_free(model);
        return set_error(error, error_size, "Out of memory");
    }
    memcpy(model->payload, layout + 4, layout_size - 4);
    model->payload_size = (uint32_t)(layout_size - 4);
    free(layout);
    return MU_BMD_OK;
}

int mu_bmd_load_file(const char *path, mu_bmd *model, char *error, size_t error_size)
{
    memset(model, 0, sizeof *model);
    FILE *file = fopen(path, "rb");
    if (!file)
        return set_error(error, error_size, "Cannot open model file");
    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return set_error(error, error_size, "Cannot size model file");
    }
    long length = ftell(file);
    if (length < 0 || (unsigned long)length > MU_BMD_MAX_FILE) {
        fclose(file);
        return set_error(error, error_size, "File exceeds supported size limit");
    }
    rewind(file);
    uint8_t *raw = malloc((size_t)length ? (size_t)length : 1);
    if (!raw || fread(raw, 1, (size_t)length, file) != (size_t)length) {
        free(raw);
        fclose(file);
        return set_error(error, error_size, "Cannot read model file");
    }
    fclose(file);
    int status = mu_bmd_load(raw, (size_t)length, model, error, error_size);
    free(raw);
    return status;
}
