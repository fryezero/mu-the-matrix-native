#ifndef MU_BMD_H
#define MU_BMD_H

#include <stddef.h>
#include <stdint.h>

/* BMD loader for the native viewer.
 *
 * Envelopes are decoded with the repository's existing sources:
 *   v10  plaintext;
 *   v12  mu_bmd12_decode (client-linked rolling decoder, reconstructed/model-codec);
 *   v14  mu_modulus_decrypt (model-recovery/modulus.cpp, Crypto++);
 *   v15  mu_client_lea_setup + mu_client_lea_decode (client-linked LEA, reconstructed/model-codec).
 * The decoded payload is walked like the client's model reader 0x012b3812
 * (docs/research/model-edge.md; authored C in reconstructed/model-codec/
 * model_reader.c): it checks no index, bone reference, parent, flag or
 * floating-point value. Every value outside the strict reader's supported
 * semantics (model-recovery/bmd10.py) is kept raw and listed as an anomaly;
 * "strict" anomalies are exactly the ones bmd10.py rejects, so a file is
 * strict-clean iff the Python strict reader accepts it, and loads iff
 * bmd10.py's client_layout mode accepts it. Structural limits still reject:
 * truncation (the client would read past its decoded buffer), negative or
 * oversized counts and the file size limits.
 *
 * All offsets below are payload offsets: byte 0 is the first byte after the
 * four-byte "BMD"+version header (the decoded v10 layout without its header).
 */

#define MU_BMD_MAX_FILE (128u * 1024u * 1024u)
#define MU_BMD_MAX_COUNT 4096

typedef struct mu_bmd_mesh {
    int16_t texture_index;
    int32_t vertex_count, normal_count, uv_count, polygon_count;
    uint32_t vertex_offset;   /* 16 bytes per vertex: int16 bone, int16 pad, 3 x binary32 */
    uint32_t normal_offset;   /* 20 bytes per normal: int16 bone, int16 pad, 3 x binary32, int16 bind vertex, int16 pad */
    uint32_t uv_offset;       /* 8 bytes per texcoord */
    uint32_t polygon_offset;  /* 64 bytes per polygon: u8 corners, pad, int16 v[4], n[4], t[4], ... */
    char texture[33];         /* NUL-terminated copy of the 32-byte field */
} mu_bmd_mesh;

typedef struct mu_bmd_action {
    int32_t keys;
    uint8_t lock_positions;
} mu_bmd_action;

typedef struct mu_bmd_bone {
    uint8_t dummy;            /* raw dummy byte; any nonzero value is a dummy record (client test) */
    int16_t parent;           /* raw parent (-1 for a root); meaningless for dummy bones */
    uint32_t offset;          /* payload offset of the record's dummy byte */
    uint8_t unresolved;       /* non-dummy bone whose parent chain reaches a dummy record or an
                                 out-of-range parent: the client's pose builder composes a slot it
                                 does not write in that call (prior contents) */
    char name[33];
} mu_bmd_bone;

/* Values outside the strict reader's supported semantics, as the client reads them. */
enum {
    MU_BMD_ANOMALY_NONFINITE = 1,     /* value: binary32 bits; a: record kind (see below) */
    MU_BMD_ANOMALY_FLAG,              /* non-boolean lock/dummy byte; value: the byte */
    MU_BMD_ANOMALY_CORNER_COUNT,      /* a: mesh, b: polygon, value: corner byte */
    MU_BMD_ANOMALY_VERTEX_INDEX,      /* a: mesh, b: polygon, c: corner, value: index */
    MU_BMD_ANOMALY_NORMAL_INDEX,
    MU_BMD_ANOMALY_UV_INDEX,
    MU_BMD_ANOMALY_VERTEX_BONE,       /* a: mesh, b: vertex, value: bone */
    MU_BMD_ANOMALY_NORMAL_BONE,       /* a: mesh, b: normal, value: bone */
    MU_BMD_ANOMALY_BIND_VERTEX,       /* a: mesh, b: normal, value: bind vertex */
    MU_BMD_ANOMALY_PARENT,            /* a: bone, value: parent outside -1..bones-1 */
    MU_BMD_ANOMALY_PARENT_CYCLE,      /* a: bone */
    MU_BMD_ANOMALY_DUMMY_PARENT,      /* a: bone, value: its dummy parent */
    MU_BMD_ANOMALY_PARENT_FORWARD,    /* a: bone, value: parent > bone (not strict) */
    MU_BMD_ANOMALY_TRAILER            /* value: unparsed bytes after the last bone record */
};

typedef struct mu_bmd_anomaly {
    uint8_t kind;
    uint8_t strict;           /* 1 when model-recovery/bmd10.py (strict) rejects the file for it */
    int32_t a, b, c, value;
    uint32_t offset;          /* payload offset of the field */
} mu_bmd_anomaly;

typedef struct mu_bmd {
    int version;              /* envelope version 10, 12, 14 or 15 */
    char name[33];
    uint8_t *payload;         /* decoded payload, owned */
    uint32_t payload_size;
    uint32_t parsed_size;     /* payload bytes consumed by the parser */
    uint32_t bone_stream;     /* payload offset of the first bone record (bone-track loop input) */
    int32_t mesh_count, bone_count, action_count;
    mu_bmd_mesh *meshes;
    mu_bmd_action *actions;
    mu_bmd_bone *bones;
    mu_bmd_anomaly *anomalies;
    int32_t anomaly_count;
    int32_t strict_anomalies; /* anomalies with strict = 1 */
} mu_bmd;

enum { MU_BMD_OK = 0, MU_BMD_ERROR = 1 };

/* Decode and parse a complete file image. On failure, *model is zeroed and
 * error receives a message (when error_size > 0). Anomalies do not fail. */
int mu_bmd_load(const uint8_t *raw, size_t size, mu_bmd *model, char *error, size_t error_size);
int mu_bmd_load_file(const char *path, mu_bmd *model, char *error, size_t error_size);
void mu_bmd_free(mu_bmd *model);

/* Short name of an anomaly kind ("nonfinite", "normal-index", ...). */
const char *mu_bmd_anomaly_name(int kind);

/* Little-endian field readers for the payload (no alignment requirement). */
int16_t mu_bmd_s16(const uint8_t *p);
float mu_bmd_f32(const uint8_t *p);

#endif
