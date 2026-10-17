#ifndef MU_DATA_H
#define MU_DATA_H

/* Native client data tables (NATIVE-DATA-001).
 *
 * Loads a table file into memory and decodes it with the reconstructed client
 * schedules in reconstructed/data (decode units, checksum decisions). Adds the
 * Item.bmd record view and the item-to-model mapping traced from the client's
 * model getter 0x00eaa8cf, and a directory listing of the Lang.mpr package.
 * No game data is embedded; callers pass installed files.
 */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/data/data_tables.h"

typedef struct {
    char *name;                 /* file name as given (basename) */
    const mu_data_spec *spec;   /* NULL when the file is not in the catalog */
    uint8_t *bytes;             /* decoded in place */
    size_t size;
    mu_data_result result;
} mu_data_table;

/* Read and decode path. Returns 0 on success (the decode status is in
 * table->result.status), -1 when the file cannot be read or is unknown.
 * spec may be NULL to look it up by basename. */
int mu_data_load(const char *path, const mu_data_spec *spec, mu_data_table *table);
/* Decode an in-memory copy (takes ownership of bytes allocated with malloc). */
int mu_data_load_memory(const char *name, uint8_t *bytes, size_t size, const mu_data_spec *spec,
                        mu_data_table *table);
void mu_data_free(mu_data_table *table);

/* ---- Item.bmd ---- */
#define MU_ITEM_RECORD_SIZE 708
#define MU_ITEM_MODEL_BASE 0xae6      /* model index = item code + 0xae6 (getter 0x00eaa8cf) */
#define MU_ITEM_MODEL_LIMIT 0x3af6    /* getter accepts 0 <= model index <= 0x3af6 */

typedef struct {
    uint32_t code;              /* +0x000 item code, the lookup key (section * 512 + index) */
    uint16_t section;           /* +0x004 */
    uint16_t index;             /* +0x006 */
    char folder[261];           /* +0x008 char[260], model folder ("Data\\Item\\") */
    char file[261];             /* +0x10c char[260], model file name */
    char name[65];              /* +0x210 char[64], display name (client code page bytes) */
    const uint8_t *record;      /* the whole decoded 708-byte record */
} mu_item;

/* Scalar attribute fields initialised by the record constructor 0x01184277,
 * in order: offset and width in bytes. Field meanings are not recovered. */
typedef struct { uint16_t offset; uint8_t width; } mu_item_field;
extern const mu_item_field mu_item_fields[];
extern const size_t mu_item_field_count;

size_t mu_item_count(const mu_data_table *table);
/* Fills item for record i (0-based). Returns 0 or -1 when out of range. */
int mu_item_get(const mu_data_table *table, size_t i, mu_item *item);
/* Client lookup semantics (std::map keyed by code): last record with code. */
int mu_item_find(const mu_data_table *table, uint32_t code, mu_item *item);
/* Read a field value (little endian, width 1/2/4). */
uint32_t mu_item_field_value(const mu_item *item, const mu_item_field *field);

/* Model index -> item. Returns 1 and fills item when the getter would call
 * the model loader with (index, folder, file); 0 when the index is in range
 * but has no item (the client returns an empty model object); -1 when out of
 * range (the client returns NULL). */
int mu_item_model(const mu_data_table *table, int32_t model_index, mu_item *item);

/* ---- Lang.mpr ---- */
typedef struct {
    char name[260];
    uint32_t crc32;
    uint32_t compressed_size;
    uint32_t size;
    uint16_t method;
    uint16_t flags;             /* bit 0: entry is encrypted (password not recovered) */
} mu_package_entry;

/* Parse the zip central directory of a decoded package image.
 * Returns the number of entries written (up to max), or -1 if not a zip. */
int mu_package_list(const mu_data_table *table, mu_package_entry *entries, int max, int *total);

#endif
