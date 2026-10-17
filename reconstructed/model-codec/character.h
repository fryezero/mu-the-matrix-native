#ifndef MU_CHARACTER_H
#define MU_CHARACTER_H

#include <stddef.h>
#include <stdint.h>

#include "pose_builder.h"

/* Authored reconstructions of the small client routines that assemble a
 * player character from the shared Player.bmd skeleton, the class body-part
 * models and linked items. Names are investigator labels, not recovered
 * original symbols. See docs/research/native-character.md.
 *
 *   0x012b7019  mu_rotation_position   thiscall on a model, ret 0xc
 *   0x012b6ef1  mu_transform_position  thiscall on a model, ret 0x10
 *   0x0139d6a2  mu_character_skin_index (calls 0x0095f5cc and 0x0139cb8a)
 *   0x0139cb8a  mu_character_class_tier
 *   0x0139d89f  mu_character_skips_tier2
 *
 * The two position routines read the model's body scale (+0x74) and body
 * origin (+0x78..+0x83) and operate on mu_client_memory views, like the pose
 * builder and the transform. */

enum {
    MU_CHARACTER_OK = 0,
    MU_CHARACTER_OUTSIDE_MEMORY = 2
};

/* 0x012b7019 (arguments matrix, vector, out). When matrix is 0 nothing
 * happens. Otherwise, in this order:
 *   t = R(matrix) * vector                       (vector rotate 0x00d000ad)
 *   out[k] = model[+0x74] * t[k], k = 0, 1, 2    (binary32)
 *   root[i][j] = matrix[i][j] for i < 3, j < 4   (dword copy, row-major)
 * root is the global 0x078965ac that the pose builder composes the root bones
 * under when its keep-root argument is set. The out writes precede the copy;
 * every dword of the copy is read just before it is written. */
int mu_rotation_position(const mu_client_memory *memory, uint32_t model, uint32_t matrix, uint32_t vector,
                         uint32_t out, uint32_t root_matrix);

/* 0x012b6ef1 (arguments matrix, vector, out, world). When matrix is 0
 * nothing happens. When the low byte of world is set:
 *   t = M(matrix) * vector (vector transform 0x00d002b2), t[k] *= model[+0x74],
 *   out[k] = t[k] + model[+0x78 + 4k];
 * otherwise out = M(matrix) * vector directly. */
int mu_transform_position(const mu_client_memory *memory, uint32_t model, uint32_t matrix, uint32_t vector,
                          uint32_t out, uint32_t world);

/* 0x0139cb8a: evolution tier of a class byte. The high nibble holds
 * evolution flags; tier 1 when it is zero, otherwise 2 + the index of its
 * highest set bit (bit 0 -> 2, bit 1 -> 3, bit 2 -> 4, bit 3 -> 5). */
uint8_t mu_character_class_tier(uint8_t class_byte);

/* 0x0139d6a2: skin index = (class & 0xf) + 16 * (tier - 1), truncated to a
 * byte. Body-part model types are base + skin index (see below). */
uint8_t mu_character_skin_index(uint8_t class_byte);

/* 0x0139d89f: 1 for base classes 3, 4, 6 and 7, whose tier-2 part models the
 * loader 0x01830aa6 skips. */
uint8_t mu_character_skips_tier2(uint8_t class_byte);

/* Body-part slots of the character record (stride 0x3fc from +0x1c4), with
 * the model-type bases that 0x01395473 adds the skin index to and that the
 * loader 0x01830aa6 fills. Slot 0 is not a class part. */
enum {
    MU_PART_HELM = 1,
    MU_PART_ARMOR = 2,
    MU_PART_PANTS = 3,
    MU_PART_GLOVES = 4,
    MU_PART_BOOTS = 5
};

#define MU_CHARACTER_PLAYER_TYPE 0x0a91u    /* AccessModel(0xa91, "Data\\Player\\", "Player", -1) */
#define MU_CHARACTER_PART_BASE 0x3700u      /* helm; armor 0x3750, pants 0x37a0, gloves 0x37f0, boots 0x3840 */
#define MU_CHARACTER_PART_STRIDE 0x50u
#define MU_CHARACTER_RIGHT_HAND_BONE 33     /* default weapon slot 0 link bone (0x0137f5d9) */
#define MU_CHARACTER_LEFT_HAND_BONE 42      /* default weapon slot 1 link bone (0x0137f5ec) */
#define MU_CHARACTER_BACK_BONE 47           /* wing and carried-weapon link bone (0x0139e5aa, 0x0139e6e3) */

/* Model type of a body part for a class byte (0x01395473). */
uint32_t mu_character_part_type(int slot, uint8_t class_byte);

/* File name the loader 0x01830aa6 gives a body-part model type, written as
 * "<Name><index>.bmd" with the AccessModel 0x018202b4 rule ("%s0%d.bmd" for
 * an index below 10, "%s%d.bmd" otherwise). Returns 0 when the loader does
 * not load that type (outside the table, or a tier-2 slot of a skipping
 * class), 1 otherwise. */
int mu_character_part_file(uint32_t type, char *out, size_t size);

#endif
