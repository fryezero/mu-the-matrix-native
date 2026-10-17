#ifndef MU_DATA_TABLES_H
#define MU_DATA_TABLES_H

#include <stddef.h>
#include <stdint.h>

/* Client data-table decode schedules (NATIVE-DATA-001).
 *
 * Each client loader reads a table file, optionally verifies a trailing
 * checksum (client 0x00976895), and then decodes the payload in units: each
 * unit is one call of a decoder that restarts the three-byte key phase. The
 * unit boundaries are part of the format. A spec below reproduces, for one
 * loader, the sequence of (offset, length, codec) units and the checksum
 * decision it applies to an in-memory file image. Field meanings of the
 * decoded records are outside this module.
 *
 * Authored API; no original structure or symbol names are implied. Loader
 * addresses are documented in docs/research/client-data-tables.md.
 */

typedef enum {
    MU_DATA_COUNTED = 1,     /* u32 count, count*R records, [u32 checksum over records] */
    MU_DATA_FIXED,           /* N*R records, [u32 checksum] */
    MU_DATA_UNTIL_EOF,       /* R-byte records while a whole record remains */
    MU_DATA_FIXED_PLAIN,     /* N*R records, no checksum, no count */
    MU_DATA_COUNT_BYTES,     /* u32 n, n bytes decoded as one unit, u32 checksum */
    MU_DATA_FORMULA,         /* u32 records, u32 groups, payload, checksum; groups of (u32,u32 count, count*R) */
    MU_DATA_MAP_LISTS,       /* repeated {u32 key, u32 n, n*u32}, every field its own 4-byte unit */
    MU_DATA_WORDS,           /* repeated {6-byte header (u32 id, u16 length), length-byte text} */
    MU_DATA_SERVER_LIST,     /* repeated {39-byte header with u16 count at 37, count*76}, local-key codec */
    MU_DATA_PET,             /* u32, u32 n, u32 count, count*(8n+16), checksum */
    MU_DATA_MIX,             /* 22 u32 counts decoded as one 88-byte unit, then counts[i]*928 per group */
    MU_DATA_TWO_COUNTS,      /* u32 a, u32 b, (a+b)*R records, checksum */
    MU_DATA_PACKAGE          /* whole file but last 4 bytes: checksum, then one xor3+key unit */
} mu_data_kind;

typedef enum {
    MU_DATA_CODEC_XOR3 = 0,       /* client 0x00976855 */
    MU_DATA_CODEC_XOR3_LOCAL = 1, /* client 0x01072ebc */
    MU_DATA_CODEC_XOR3_KEY = 2    /* client 0x00f1600f with the spec's codec_key */
} mu_data_codec;

/* Flags. */
#define MU_DATA_HAS_CHECKSUM   0x01u
#define MU_DATA_STOP_BYTE4     0x02u /* stop decoding at the first record whose byte 4 is zero */
#define MU_DATA_COUNT_NONZERO  0x04u /* the loader rejects a zero count before reading records */

typedef struct {
    const char *file;          /* file name under Data/Local or Data, as installed */
    const char *path;          /* client path string or "" when only the file was matched */
    uint32_t loader;           /* client loader entry address, 0 when not located */
    mu_data_kind kind;
    uint32_t record_size;      /* R */
    uint32_t record_count;     /* N for FIXED/FIXED_PLAIN, maximum for MU_DATA_MIX groups (0 = none) */
    uint32_t checksum_key;     /* low 16 bits used */
    uint32_t codec;            /* mu_data_codec */
    uint32_t codec_key;        /* for MU_DATA_CODEC_XOR3_KEY */
    uint32_t flags;
} mu_data_spec;

typedef enum {
    MU_DATA_OK = 0,
    MU_DATA_TRUNCATED = 1,     /* file shorter than the schedule needs */
    MU_DATA_BAD_CHECKSUM = 2,  /* client reports "file corrupted" and decodes nothing */
    MU_DATA_ZERO_COUNT = 3,    /* client reports "Data Count 0" */
    MU_DATA_BAD_HEADER = 4,    /* value the client rejects (e.g. Mix group count > 3000) */
    MU_DATA_BAD_ARGUMENT = 5
} mu_data_status;

/* Called once per decode unit after it was decoded in place. */
typedef void (*mu_data_unit_fn)(void *user, size_t offset, uint32_t length, uint32_t codec);

typedef struct {
    mu_data_status status;
    uint32_t checksum_stored;
    uint32_t checksum_computed;
    uint32_t checksum_offset;   /* first byte the checksum covers */
    uint32_t checksum_length;
    uint32_t units;             /* decode units applied */
    uint32_t records;           /* records decoded (kind-specific meaning) */
    size_t records_offset;      /* offset of the first record */
    size_t consumed;            /* bytes the schedule covers */
} mu_data_result;

/* Decode a whole file image in place following spec. callback may be NULL.
 * Returns result->status. The image is not resized; on a checksum mismatch
 * no byte is changed. TRUNCATED stops at the first unit that does not fit
 * (earlier units remain decoded), an authored choice: the client's fread
 * short-read paths differ per loader and are not reproduced.
 */
mu_data_status mu_data_decode(const mu_data_spec *spec, uint8_t *image, size_t size,
                              mu_data_unit_fn callback, void *user, mu_data_result *result);

/* Built-in catalog of the loaders recovered from the pinned client. */
const mu_data_spec *mu_data_specs(size_t *count);
/* Case-insensitive lookup by file name ("item.bmd"); NULL if absent. */
const mu_data_spec *mu_data_find(const char *file);

const char *mu_data_status_name(mu_data_status status);
const char *mu_data_kind_name(mu_data_kind kind);

#endif
