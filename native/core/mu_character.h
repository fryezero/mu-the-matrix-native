#ifndef MU_CHARACTER_VIEW_H
#define MU_CHARACTER_VIEW_H

#include <stdint.h>

#include "mu_bmd.h"
#include "mu_model.h"
#include "mu_textures.h"

/* Character assembly for the native viewer (NATIVE-CHAR-001).
 *
 * Follows the character render 0x0139be7a (docs/research/native-character.md):
 *   1. the Player.bmd model takes the object's action and is posed into the
 *      shared bone buffer 0x06fce398 (keep root 0, translate 0);
 *   2. body-part slots 5..0 copy the object's scale, lighting flag, position
 *      and light into their own model and are skinned by the transform
 *      0x012b5bde against the shared bones (translate 1, vertex scale 0,
 *      light 0.4/0.8/0.2); part models are never posed;
 *   3. weapon slots 0 and 1: rotation position 0x012b7019 on the Player model
 *      with the slot's link bone and (0, 0, 0) copies that bone matrix into
 *      the root matrix 0x078965ac; the item model's origin becomes position +
 *      result; it is posed at frame 0 (prior 0, prior action 0, zero angles)
 *      with keep root 1 and translate 1 into the same shared buffer, then
 *      skinned with the same light arguments;
 *   4. the wing slot does the same with vector (0, 0, 15), frame 2, prior 2
 *      and its own scale.
 * All posing and skinning is the reconstructed client code through mu_model.
 * One shared bone/root/quaternion storage stands in for the client globals,
 * so later poses overwrite earlier bones exactly as in the client. */

enum {
    MU_CHARACTER_PART_SLOTS = 6,   /* record slots 0..5; 1..5 are helm, armor, pants, gloves, boots */
    MU_CHARACTER_WEAPON_SLOTS = 2,
    MU_CHARACTER_ITEMS = MU_CHARACTER_PART_SLOTS + MU_CHARACTER_WEAPON_SLOTS + 1
};

/* Item index of the wing in mu_character.items. Weapons follow the parts. */
#define MU_CHARACTER_WEAPON_ITEM(slot) (MU_CHARACTER_PART_SLOTS + (slot))
#define MU_CHARACTER_WING_ITEM (MU_CHARACTER_PART_SLOTS + MU_CHARACTER_WEAPON_SLOTS)

typedef struct mu_character_item {
    int loaded;
    char path[4096];
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    int32_t link_bone;       /* weapons and wing: Player bone index (record byte +5) */
    uint16_t action;         /* weapons and wing: item action (record byte +6) */
    float *bones;            /* weapons and wing: own bone matrices right after their pose */
} mu_character_item;

typedef struct mu_character_params {
    float position[3];       /* object +0x158 */
    float angles[3];         /* object +0x164 */
    float head[2];           /* object +0x170 */
    float scale;             /* object +0xa0 (creation default 0.9, 0x0137d9dd) */
    float wing_scale;        /* character +0x32f4 */
    float light[3];          /* object +0xec light times object +0xdc */
    uint8_t lighting;        /* object +5 */
} mu_character_params;

typedef struct mu_character {
    mu_bmd player_bmd;
    mu_model player;
    int player_loaded;
    mu_character_item items[MU_CHARACTER_ITEMS];
    mu_character_params params;
    uint8_t *shared_bones, *shared_root, *shared_quaternions;
    float *player_bones;     /* Player bone matrices right after its pose (before items overwrite) */
    int32_t player_bone_count;
} mu_character;

void mu_character_default_params(mu_character_params *params);
int mu_character_init(mu_character *character, const char *player_path, const mu_model_params *model_params,
                      char *error, size_t error_size);
void mu_character_free(mu_character *character);
/* Loads (or with path NULL unloads) an item; textures from the file's directory unless no_textures. */
int mu_character_set_item(mu_character *character, int item, const char *path, int no_textures, char *error,
                          size_t error_size);
/* Player animation state (object +0x2a action, +0xd0 frame, +0xd4 prior frame, +0x2c prior action). */
void mu_character_set_state(mu_character *character, uint16_t action, float frame, float prior_frame,
                            uint16_t prior_action);
int mu_character_tick(mu_character *character, float speed, uint8_t *loop);
/* Poses and skins every loaded model in the order above. */
int mu_character_update(mu_character *character);
/* Axis-aligned bounds of every transformed vertex; returns 0 when there are none. */
int mu_character_bounds(const mu_character *character, float lo[3], float hi[3]);

/* Data/Player path of a class body part: root/Data/Player/<file> with the
 * file name of the reconstructed loader table (mu_character_part_file).
 * Returns 0 when the loader does not load that part. */
int mu_character_part_path(const char *game_root, int slot, uint8_t class_byte, char *out, size_t size);

#endif
