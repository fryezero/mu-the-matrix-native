#include "mu_data.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Scalar fields zero-initialised by the item record constructor 0x01184277
 * (offset, width). Folder/file/name are the three memset spans before them. */
const mu_item_field mu_item_fields[] = {
    {0x250, 1}, {0x251, 1}, {0x253, 1}, {0x254, 2}, {0x256, 1}, {0x258, 2}, {0x25a, 1}, {0x25b, 1},
    {0x25c, 2}, {0x25e, 2}, {0x260, 1}, {0x262, 2}, {0x264, 2}, {0x266, 1}, {0x267, 1}, {0x268, 1},
    {0x26a, 2}, {0x26c, 1}, {0x270, 4}, {0x274, 4}, {0x278, 4}, {0x27c, 2}, {0x27e, 2}, {0x280, 2},
    {0x282, 2}, {0x284, 2}, {0x286, 2}, {0x288, 1}, {0x28c, 4}, {0x290, 1}, {0x2a9, 1}, {0x2ab, 1},
    {0x2ac, 1}, {0x2ad, 1}, {0x2ae, 1}, {0x2af, 1}, {0x2b2, 2}, {0x2b4, 2}, {0x2b6, 2}, {0x2b8, 1},
    {0x2b9, 1}, {0x2ba, 1}, {0x2bc, 2}, {0x2be, 2}, {0x2c0, 2},
};
const size_t mu_item_field_count = sizeof mu_item_fields / sizeof mu_item_fields[0];

static const char *base_name(const char *path) {
    const char *slash = strrchr(path, '/');
    const char *back = strrchr(path, '\\');
    if (back && (!slash || back > slash)) slash = back;
    return slash ? slash + 1 : path;
}

int mu_data_load_memory(const char *name, uint8_t *bytes, size_t size, const mu_data_spec *spec,
                        mu_data_table *table) {
    memset(table, 0, sizeof *table);
    if (!spec) spec = mu_data_find(base_name(name));
    if (!spec) {
        free(bytes);
        return -1;
    }
    size_t length = strlen(base_name(name));
    table->name = malloc(length + 1);
    if (!table->name) {
        free(bytes);
        return -1;
    }
    memcpy(table->name, base_name(name), length + 1);
    table->spec = spec;
    table->bytes = bytes;
    table->size = size;
    mu_data_decode(spec, bytes, size, NULL, NULL, &table->result);
    return 0;
}

int mu_data_load(const char *path, const mu_data_spec *spec, mu_data_table *table) {
    memset(table, 0, sizeof *table);
    FILE *file = fopen(path, "rb");
    if (!file) return -1;
    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return -1;
    }
    long length = ftell(file);
    if (length < 0 || length > 0x7fffffffL || fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return -1;
    }
    uint8_t *bytes = malloc((size_t)length + 1);
    if (!bytes) {
        fclose(file);
        return -1;
    }
    size_t got = fread(bytes, 1, (size_t)length, file);
    fclose(file);
    if (got != (size_t)length) {
        free(bytes);
        return -1;
    }
    return mu_data_load_memory(path, bytes, (size_t)length, spec, table);
}

void mu_data_free(mu_data_table *table) {
    if (!table) return;
    free(table->bytes);
    free(table->name);
    memset(table, 0, sizeof *table);
}

static uint32_t le(const uint8_t *p, unsigned width) {
    uint32_t value = 0;
    for (unsigned i = 0; i < width; ++i) value |= (uint32_t)p[i] << (8 * i);
    return value;
}

static int is_item_table(const mu_data_table *table) {
    return table && table->spec && table->spec->kind == MU_DATA_COUNTED &&
           table->spec->record_size == MU_ITEM_RECORD_SIZE && table->result.status == MU_DATA_OK;
}

size_t mu_item_count(const mu_data_table *table) {
    return is_item_table(table) ? table->result.records : 0;
}

int mu_item_get(const mu_data_table *table, size_t i, mu_item *item) {
    if (!is_item_table(table) || i >= table->result.records) return -1;
    const uint8_t *r = table->bytes + table->result.records_offset + i * MU_ITEM_RECORD_SIZE;
    memset(item, 0, sizeof *item);
    item->code = le(r, 4);
    item->section = (uint16_t)le(r + 4, 2);
    item->index = (uint16_t)le(r + 6, 2);
    /* fixed char arrays, copied with a terminator (the client bounds them by their arrays) */
    memcpy(item->folder, r + 0x008, 260);
    memcpy(item->file, r + 0x10c, 260);
    memcpy(item->name, r + 0x210, 64);
    item->record = r;
    return 0;
}

int mu_item_find(const mu_data_table *table, uint32_t code, mu_item *item) {
    size_t n = mu_item_count(table);
    for (size_t i = 0; i < n; ++i) {
        const uint8_t *r = table->bytes + table->result.records_offset + i * MU_ITEM_RECORD_SIZE;
        if (le(r, 4) == code) return mu_item_get(table, i, item); /* std::map::insert keeps the first */
    }
    return -1;
}

uint32_t mu_item_field_value(const mu_item *item, const mu_item_field *field) {
    return le(item->record + field->offset, field->width);
}

int mu_item_model(const mu_data_table *table, int32_t model_index, mu_item *item) {
    if (model_index < 0 || model_index > MU_ITEM_MODEL_LIMIT) return -1;
    uint32_t code = (uint32_t)(model_index - MU_ITEM_MODEL_BASE);
    return mu_item_find(table, code, item) == 0 ? 1 : 0;
}

int mu_package_list(const mu_data_table *table, mu_package_entry *entries, int max, int *total) {
    if (total) *total = 0;
    if (!table || table->result.status != MU_DATA_OK || table->size < 26) return -1;
    size_t size = table->size - 4; /* decoded package excludes the checksum trailer */
    const uint8_t *p = table->bytes;
    /* end of central directory: signature PK\5\6, searched backwards */
    size_t at = size >= 22 ? size - 22 : 0;
    for (;;) {
        if (le(p + at, 4) == 0x06054b50u) break;
        if (at == 0 || size - at > 22 + 0xffff) return -1;
        --at;
    }
    uint32_t count = le(p + at + 10, 2);
    uint32_t offset = le(p + at + 16, 4);
    int written = 0;
    for (uint32_t i = 0; i < count; ++i) {
        if ((size_t)offset + 46 > size || le(p + offset, 4) != 0x02014b50u) return -1;
        uint32_t name_length = le(p + offset + 28, 2), extra = le(p + offset + 30, 2),
                 comment = le(p + offset + 32, 2);
        if ((size_t)offset + 46 + name_length > size) return -1;
        if (written < max && entries) {
            mu_package_entry *e = &entries[written++];
            memset(e, 0, sizeof *e);
            e->flags = (uint16_t)le(p + offset + 8, 2);
            e->method = (uint16_t)le(p + offset + 10, 2);
            e->crc32 = le(p + offset + 16, 4);
            e->compressed_size = le(p + offset + 20, 4);
            e->size = le(p + offset + 24, 4);
            size_t n = name_length < sizeof e->name - 1 ? name_length : sizeof e->name - 1;
            memcpy(e->name, p + offset + 46, n);
        }
        if (total) ++*total;
        offset += 46 + name_length + extra + comment;
    }
    return written;
}
