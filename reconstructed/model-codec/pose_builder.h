#ifndef MU_POSE_BUILDER_H
#define MU_POSE_BUILDER_H

#include <stdint.h>

#include "bone_tracks.h"

/* Authored reconstruction of the pose builder observed at 0x012b5064..0x012b58cb
 * (thiscall on the model object, ret 0x20). Names are investigator labels, not
 * recovered original symbols. See docs/research/client-pose-builder.md.
 *
 * The builder reads client records holding 32-bit pointers and two fixed
 * globals, so it operates on a set of flat little-endian views of 32-bit
 * client address ranges. Every access must lie wholly inside one region.
 *
 * Model fields read or written (byte offsets):
 *   +0x22 int16 bone count, +0x26 int16 action count, +0x2c u32 bone array,
 *   +0x30 u32 action array (stride 16: int16 keys at +8, u8 lock flag at +0xa),
 *   +0x60 int32 special ("head") bone index, +0x74 binary32 root scale,
 *   +0x78..+0x83 three binary32 root translation values,
 *   +0x84..+0x8f three binary32 body angles (degrees, written from the argument),
 *   +0x90 binary32 height added to the locked root z translation,
 *   +0xa8 u16 current action (reset to 0 when >= action count),
 *   +0xac binary32 current frame (written), +0xb4 int16 integer frame (written).
 * Bone records and track arrays use the bone-track loop layout
 * (bone_tracks.h): +0x20 int16 parent, +0x22 int8 dummy, +0x24 track array.
 */
typedef struct mu_client_memory {
    const mu_client_image *regions;
    uint32_t count;
} mu_client_memory;

/* The eight 32-bit stack arguments, in push order reversed (first = [esp+4]). */
typedef struct mu_pose_arguments {
    uint32_t output;        /* client address of 0x30-byte row-major 3x4 matrices */
    uint32_t frame;         /* binary32 bits: current frame (integer part and fraction) */
    uint32_t prior_frame;   /* binary32 bits: prior frame, truncated to an integer */
    uint32_t prior_action;  /* low 16 bits; on return the low 16 bits hold the
                               clamped value the original stores into its own
                               argument slot (upper bits unchanged) */
    uint32_t angles;        /* client address of three binary32 body angles */
    uint32_t head_angles;   /* client address of two binary32 head angles */
    uint32_t keep_root;     /* low byte nonzero: reuse the existing root matrix */
    uint32_t translate;     /* low byte nonzero: scale/translate a rebuilt root */
} mu_pose_arguments;

/* Client addresses of the two uncaptured globals the builder uses. */
#define MU_POSE_BONE_QUATERNIONS 0x075a90d8u /* 16 bytes per bone index */
#define MU_POSE_ROOT_MATRIX 0x078965acu      /* one 3x4 matrix */

typedef struct mu_pose_globals {
    uint32_t bone_quaternions;
    uint32_t root_matrix;
} mu_pose_globals;

enum {
    MU_POSE_OK = 0,
    MU_POSE_OUTSIDE_MEMORY = 2
};

/* Runs the builder for the model object at client address model. Each
 * non-dummy bone i receives quaternion slot bone_quaternions + 16*i and
 * matrix output + 0x30*i; dummy bones are skipped and their slots untouched.
 * Interpolation: q1/p1 from (prior action, prior frame), q2/p2 from (current
 * action, integer current frame), t = current frame minus its integer part
 * computed before the frame clamps. Quaternions use mu_quaternion_slerp unless
 * mu_quaternion_compare finds them equal (then q1 is copied); positions use
 * binary32 p1*(1-t) + p2*t. Frames outside 0..keys-1 reset to 0. Trig uses
 * host libm as a substitute for the client helpers. An access outside every
 * region stops with MU_POSE_OUTSIDE_MEMORY after applying earlier effects;
 * the client would read or write arbitrary memory instead (unverified). */
int mu_pose_build(const mu_client_memory *memory, uint32_t model, mu_pose_arguments *arguments,
                  const mu_pose_globals *globals);

#endif
