/* The hero's footstep sound and the tile it stands on (NATIVE-WORLD-002).
 *
 * Client routines (restored text, main.exe SHA-256 3cf91f3c...b5527a), names
 * are investigator choices:
 *
 *   0x016ad7a5..0x016ad81f  tail of MoveHero 0x016a9150: HeroTile
 *                           (0x0b437c10) = layer-1 tile under the hero
 *   0x013b1f61              PlayWalkSound: picks the footstep sound id from the
 *                           world, HeroTile and the hero's state, SND_Play(id)
 *   0x013b8090..0x013b8187  footstep trigger inside the per-character routine
 *                           0x013b23f8 (MoveCharacters, after the animation)
 *   0x013a773c..0x013a777e  foot-flag reset after the animation step in
 *                           0x013a763e
 *
 * Order in one logic step (in-world tick 0x0185613e): MoveHero (HeroTile at
 * its end), then MoveCharacters 0x0137a7ce: per character 0x0137a716 runs the
 * mover 0x013b852a (skips the hero), 0x013a85a9 (which animates through
 * 0x013a763e: animation step 0x013960d2, then the foot reset when it returned
 * 0), then 0x013b23f8 (the footstep trigger). The trigger therefore sees the
 * frame after this step's tick.
 */
#ifndef MU_HERO_SOUND_H
#define MU_HERO_SOUND_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Sound ids PlayWalkSound passes to SND_Play (registered by the startup
 * loader 0x018433ed, except 0x4d1 by 0x018392db). */
enum {
    MU_SOUND_WALK_SOIL = 8,
    MU_SOUND_WALK_GRASS = 9,
    MU_SOUND_WALK_SNOW = 10,
    MU_SOUND_SWIM = 11,
    MU_SOUND_WALK_BRIDGE = 0x4d1   /* world 0x7a, attribute 0x8000 */
};

/* HeroTile: index = ((int)y / 100 << 8) + (int)x / 100 with cvttss2si and a
 * truncating idiv, wrapped to 32 bits; a negative index reads 0, one above
 * 0xffff reads 0xffff; the result is layer1[index] (0x0b735420). */
int32_t mu_hero_tile(const uint8_t *layer1, float x, float y);
/* The clamped index the tail computes ([ebp-0x8c]). */
int32_t mu_hero_tile_index(float x, float y);

/* Inputs of PlayWalkSound, read from client globals and the hero. */
typedef struct mu_walk_sound_state {
    int32_t world;            /* 0x01cf15fc */
    int32_t hero_tile;        /* 0x0b437c10 */
    uint16_t hero_action;     /* hero object (+0x3254) +0x2a */
    uint8_t hero_safe_zone;   /* hero +4 (0x0095fb27) */
    int32_t hero_x, hero_y;   /* hero +0x180 / +0x184 */
    uint8_t manager_state;    /* AL of 0x0106b9f7(hero, 2, 1) on the singleton 0x009c104e */
} mu_walk_sound_state;

/* PlayWalkSound 0x013b1f61: the id it passes to SND_Play, or -1 when it plays
 * nothing (actions 0x59..0x5f, or the manager predicate). attributes is the
 * 256x256 terrain attribute grid 0x0b795420 (read only in world 0x7a). */
int32_t mu_walk_sound_id(const mu_walk_sound_state *state, const uint16_t *attributes);

/* 0x016a88d3: worlds where the hero swims outside the safe zone (Atlans
 * 0x016a88ae, 0x18..0x1d, 0x24). */
int mu_world_is_water(int32_t world);

/* Footstep trigger 0x013b8090..0x013b8187 for character c and object o:
 * when o is the Player model (+0x5c == 0xa91), c is the hero and the action
 * is a walk or run (0x32..0x3e or 0x4f..0x6e): at frame >= 1.5 with foot[0]
 * clear, foot[0] = 1 and PlayWalkSound; then at frame >= 4.5 with foot[1]
 * clear, foot[1] = 1 and PlayWalkSound. foot is character +0xc/+0xd.
 * Returns the number of PlayWalkSound calls (0..2). */
int mu_footstep_trigger(int32_t object_type, int is_hero, uint16_t action, float frame, uint8_t foot[2]);

/* Foot reset 0x013a773c..0x013a777e: when the animation step returned 0 (the
 * tick wrapped or clamped), character +0x168 = -1 and both foot flags clear.
 * Returns 1 when it reset. */
int mu_footstep_reset(uint8_t step_result, uint8_t foot[2], int32_t *field_168);

#ifdef __cplusplus
}
#endif
#endif
