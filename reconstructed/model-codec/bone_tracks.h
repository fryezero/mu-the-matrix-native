#ifndef MU_BONE_TRACKS_H
#define MU_BONE_TRACKS_H

#include <stdint.h>

/* Authored reconstruction of the BMD bone-track loop observed at
 * 0x012b4225..0x012b4441 inside model reader 0x012b3812. Names are
 * investigator labels, not recovered original symbols.
 *
 * The loop stores 32-bit client pointers inside client records, so this API
 * operates on a flat little-endian view of one 32-bit client address window.
 * Every client address used by the loop (model object, bone array, action
 * array, decoded stream and every allocated block) must lie inside the image.
 *
 * Layouts (byte offsets):
 *   model  +0x22 int16 bone count, +0x26 int16 action count,
 *          +0x2c u32 bone array, +0x30 u32 action array (stride 16, int16 key
 *          count at +8). Bone count/action count/arrays are reread as the
 *          original does.
 *   bone   stride 0x8c: +0x00 32-byte name, +0x20 int16 parent,
 *          +0x22 int8 dummy, +0x24 u32 track array. A dummy record receives
 *          only +0x22; nothing else in any bone record is written.
 *   track  stride 12 per action: +0 u32 positions (12 bytes/key),
 *          +4 u32 Euler rotations (12 bytes/key), +8 u32 quaternions
 *          (16 bytes/key, x,y,z,w from mu_rotation_quaternion).
 *
 * Stream records per bone: dummy byte; if zero, 32-byte name, int16 parent,
 * then for each action keys*12 position bytes followed by keys*12 rotation
 * bytes. No stream length or count validation is performed, as in the client.
 */
typedef struct mu_client_image {
    uint8_t *bytes;
    uint32_t base;
    uint32_t size;
} mu_client_image;

/* Called with the operator-new request size, in the original order:
 * per non-dummy bone actions*12, then per action positions, rotations and
 * quaternions. Sizes use the client's saturating unsigned multiplies, so a
 * negative count requests 0xffffffff. Return a client address of an
 * accessible block of at least max(request, 1) bytes, or 0 for failure.
 * The client never observes failure here: its operator new retries through a
 * new handler or throws. That path is not reconstructed (see the finding). */
typedef uint32_t (*mu_client_allocate)(void *context, uint32_t request);

enum {
    MU_BONE_TRACKS_OK = 0,
    MU_BONE_TRACKS_ALLOCATION_FAILED = 1,
    MU_BONE_TRACKS_OUTSIDE_IMAGE = 2
};

/* Runs the loop for the model object at client address model. stream is the
 * decoded payload base and *offset the signed 32-bit stream offset of the first
 * bone record; on return *offset holds the advanced offset (also on failure,
 * reflecting the last completed step). Effects up to a failure remain applied.
 * An access outside the image stops with MU_BONE_TRACKS_OUTSIDE_IMAGE, where
 * the client would read or write arbitrary memory or fault (unverified). */
int mu_bone_tracks_read(const mu_client_image *image, uint32_t model, uint32_t stream,
                        int32_t *offset, mu_client_allocate allocate, void *context);

#endif
