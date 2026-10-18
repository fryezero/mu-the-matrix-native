#ifndef MU_OBJECTS_RECON_H
#define MU_OBJECTS_RECON_H

#include <stddef.h>
#include <stdint.h>

/* Authored C for the client's static map-object loader and object model table
 * (docs/research/client-objects.md). Names are ours; each function names the
 * client routine it follows.
 *
 * EncTerrain<n>.obj: the loader 0x016d9ac5 reads the whole file, decodes it in
 * one call of the v12 rolling decoder 0x0098c5f2 (mu_bmd12_decode in
 * reconstructed/model-codec) and walks the plaintext:
 *
 *   u8 version, u8 map number, i16 count, then count records of
 *   i16 type, f32 position[3], f32 angle[3], f32 scale,
 *   version >= 1: u8 +0x2c, u8 +0x2d;   version >= 2: u8 +0x2e;
 *   version >= 3: f32 vector[3] (+0x1c); version >= 4: u8 +0x2f;
 *   version >= 5: f32 +0x30, f32 +0x34.
 *
 * The version byte is compared with jl, so 6..255 read like 5. Each record is
 * built in a 0x38-byte local initialised by the constructor 0x0180778f and
 * passed to CreateObject 0x016d8538. The loader returns the map number byte;
 * OpenWorld 0x0182876e compares it with the folder number. The count is also
 * stored (sign-extended) in the global 0x0bdb5888.
 *
 * The client bounds nothing: a count larger than the file reads past the
 * buffer. mu_objects_parse refuses that instead (MU_OBJECTS_TRUNCATED), an
 * authored convention; within bounds it yields the client's records. */

enum {
    MU_OBJECTS_OK = 0,
    MU_OBJECTS_TRUNCATED = 1,    /* header or records past the end of the plaintext */
    MU_OBJECTS_BAD_ARGUMENT = 2
};

/* The constructor 0x0180778f's 0x38-byte record, field offsets as in the
 * client. Bytes 2..3 are never written by the client (stack contents). */
typedef struct mu_object_record {
    int16_t type;              /* +0x00 object type == model index */
    uint8_t pad[2];            /* +0x02 untouched by the client */
    float position[3];         /* +0x04 world units (100 per terrain tile) */
    float angle[3];            /* +0x10 degrees */
    float vector[3];           /* +0x1c version >= 3, zero otherwise */
    float scale;               /* +0x28 default 1.0 */
    uint8_t flag_2c;           /* +0x2c version >= 1, default 1 -> object +5 */
    uint8_t flag_2d;           /* +0x2d version >= 1, default 1 -> object +6 */
    uint8_t flag_2e;           /* +0x2e version >= 2, default 1 -> object +7 */
    uint8_t hidden;            /* +0x2f version >= 4, default 0; nonzero -> object +0x68 = -2 */
    float value_30;            /* +0x30 version >= 5, default 0.8 -> object +0xe4 */
    float value_34;            /* +0x34 version >= 5, default 0.2 -> object +0xe8 */
} mu_object_record;

typedef struct mu_object_header {
    uint8_t version;           /* plaintext byte 0 */
    uint8_t map;               /* plaintext byte 1, the loader's return value */
    int16_t count;             /* plaintext bytes 2..3 */
    int32_t record_size;       /* bytes per record for this version */
} mu_object_header;

/* Bytes per record the loader consumes for a version byte (30, 32, 33, 45, 46, 54). */
int32_t mu_objects_record_size(uint8_t version);

/* 0x0180778f: type 0, position/angle/vector zero, scale 1.0, flags 1,1,1,0,
 * value_30 0.8, value_34 0.2. pad is set to zero (the client leaves it). */
void mu_objects_record_init(mu_object_record *record);

/* 0x016d9ac5 after the decode: the header and up to capacity records.
 * *parsed receives the number of records written (max(count, 0) when OK).
 * records may be NULL with capacity 0 to read the header only. */
int mu_objects_parse(const uint8_t *plain, size_t size, mu_object_header *header, mu_object_record *records,
                     int32_t capacity, int32_t *parsed);

/* Object model table built by 0x018392db (OpenWorld's model pass) for types
 * 0..299, the range a .obj type can name through the generic loop.
 *
 * World 0 (Lorencia) loads named models from Data\Object1\ (Tree01..13 as
 * types 0..12, Grass01..08 as 20..27, ... House01..05 as 115..119); every
 * other world loads type t from Data\Object<folder>\Object<t+1>.bmd, numbers
 * below 10 written with one leading zero (AccessModel 0x018202b4: "%s0%d.bmd",
 * "%s%d.bmd", "%s.bmd" for -1); folder is mu_objects_folder(world), except
 * that world 0x80 loads types 0x42..0x46 from Object129.
 *
 * Writes "Data/Object<f>/<name>.bmd" into out and returns 1, or returns 0 when
 * the client loads no model for that type in that world. */
int mu_objects_model_file(int32_t world, int32_t type, char *out, size_t out_size);

/* The object folder number 0x018392db selects before its generic loop:
 * world + 1, or the shared folder of an event-map group (Blood Castle 12,
 * Chaos Castle 19, Kalima 25, Illusion Temple 47, 82..90 -> 83, 123..127 -> 124,
 * 128..130 -> 131, 131 -> 132, 132 -> 133). The client asks a runtime
 * custom-map table (0x0095c652(0x5c)) between the 83 and 124 checks; that
 * table's contents are runtime data outside the captures and it is not
 * reconstructed. */
int32_t mu_objects_folder(int32_t world);

/* Number of named groups of the world 0 table (for tests and tools). */
int32_t mu_objects_lorencia_groups(void);
/* Group i of the world 0 table: first type, name, first file number, count. */
int mu_objects_lorencia_group(int32_t index, int32_t *first_type, const char **name, int32_t *first_number,
                              int32_t *count);

#endif
