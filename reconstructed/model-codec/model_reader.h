#ifndef MU_MODEL_READER_H
#define MU_MODEL_READER_H

#include <stdint.h>

#include "pose_builder.h"

/* Authored reconstruction of the plaintext part of BMD model reader 0x012b3812:
 * the instructions from the model-name copy 0x012b3b50 to the success return
 * 0x012b4477 (AL = 1), including the bone-track loop (mu_bone_tracks_read),
 * the stream release, the bone box pass 0x012b2df3(0) -> 0x012b47fd and the
 * trailing memset of model +0xb6. Names are investigator labels, not recovered
 * original symbols. See docs/research/model-edge.md.
 *
 * Nothing in this range validates a count, an index, a bone reference, a parent
 * or a floating-point value. Every array is copied raw from the stream:
 *   model  +0x00 32-byte name; +0x22/+0x24/+0x26 int16 bone/mesh/action counts
 *          (stream order mesh, bone, action); +0x28 mesh array (stride 0x20);
 *          +0x2c bone array (stride 0x8c, uninitialized); +0x30 action array
 *          (stride 16); +0x34 texture names (32 bytes each); +0x38 per-mesh
 *          dword table (allocated, never written here); +0x3c per-mesh dword
 *          table zero-filled; +0x40 = 0; +0x60 = -1; +0x94 = 0xff;
 *          +0xb6..+0xc9 = 0xff.
 *   mesh   +0x00 byte 0, +0x01 untouched, +0x02 int16 texture, +0x04/+0x06/
 *          +0x08/+0x0a int16 vertex/normal/texcoord/triangle counts,
 *          +0x0c vertices (16-byte records), +0x10 normals (20-byte records),
 *          +0x14 texcoords (8 bytes), +0x18 triangles: the first 0x24 bytes of
 *          each 64-byte stream polygon, +0x1c 5-byte texture-name record or 0.
 *   action +0x00 byte 0, +0x08 int16 keys, +0x0a lock byte (any nonzero locks),
 *          +0x0c locked positions (keys*12 bytes) or 0.
 *   bone   bone-track loop layout (bone_tracks.h) plus +0x28 "has vertices"
 *          byte and +0x2c..+0x8b eight box corners written for every record.
 * Bone boxes: per bone index i < bone count the pass initializes min[i] to
 * 9999 and max[i] to -9999 (binary32 globals 0x01a7edf8/0x01a7ee10), zeroes
 * count[i], then for every vertex v of every mesh uses node = int16 v.bone,
 * unchecked: min[node][k] = p[k] when min > p (ordered compare), max[node][k]
 * = p[k] when p > max, count[node] += 1 (16-bit). A node outside 0..bones-1
 * therefore reads and writes the tables at node*12 / node*2 from their bases.
 * Corner c of bone i takes component k from min when bit (2-k) of c is set.
 */

typedef struct mu_reader_hooks {
    /* operator new (0x0191bab9 and the retry loop 0x0191ba7b); see bone_tracks.h. */
    mu_client_allocate allocate;
    /* operator delete 0x0191bac2 of the decoded stream block. */
    void (*release)(void *context, uint32_t block);
    /* Texture-name parser 0x01185111 on the 32-byte name at client address
     * name. Returns its AL result and the first five bytes of its 6-byte local
     * record (zeroed by 0x010a82be before the call), which the reader copies
     * into a fresh 5-byte block when AL is nonzero. The parser itself is not
     * reconstructed here (CLIENT-MESHDRAW-EXEC-001 ports it). */
    int (*name_flags)(void *context, uint32_t name, uint8_t flags[5]);
    void *context;
} mu_reader_hooks;

/* Client addresses of the bone box tables (third image section). */
#define MU_READER_BOX_COUNTS 0x075a9d58u  /* int16 per bone index */
#define MU_READER_BOX_MIN 0x078965e0u     /* three binary32 per bone index */
#define MU_READER_BOX_MAX 0x07896f40u     /* three binary32 per bone index */

typedef struct mu_reader_globals {
    uint32_t box_counts, box_min, box_max;
} mu_reader_globals;

enum {
    MU_READER_OK = 0,
    MU_READER_ALLOCATION_FAILED = 1,  /* the client would loop in its new handler or throw */
    MU_READER_OUTSIDE_MEMORY = 2      /* the client would touch memory outside every region */
};

/* Runs 0x012b3b50..0x012b4477 for the model object at client address model.
 * stream is the decoded payload (the bytes after "BMD" and the version byte's
 * envelope), *offset the signed stream offset (0 at entry, as the reader sets
 * it after decoding). The model object, stream and every allocation must lie in
 * one region; the box tables may lie in others. Effects up to a failure remain
 * applied and *offset reflects the last completed step. */
int mu_model_read_layout(const mu_client_memory *memory, uint32_t model, uint32_t stream, int32_t *offset,
                         const mu_reader_hooks *hooks, const mu_reader_globals *globals);

/* The bone box pass alone (0x012b47fd, thiscall on the model). */
int mu_model_bone_boxes(const mu_client_memory *memory, uint32_t model, const mu_reader_globals *globals);

#endif
