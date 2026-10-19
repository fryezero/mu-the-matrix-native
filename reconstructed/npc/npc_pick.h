/* Character picking under the mouse (NATIVE-NPC-001).
 *
 * The client selects NPCs, monsters and players with one routine,
 * 0x016b47bf(kind mask), called by the selection pass 0x016b5157 in the
 * order NPC (4), then characters 0x22, then 1 (static).  It tests the mouse
 * segment against each candidate's oriented box (object +0x31c, written by
 * the model transform 0x012b5bde from the object's box +0x128/+0x134 and
 * position) with the separating-axis test 0x018500bf and keeps the
 * candidate nearest to the camera.  These functions restate it; every one
 * is compared with the client's instructions in Unicorn by
 * scripts/validate_npc.py (verified).  The box table comes from executing
 * the box section of the character create routine 0x0137d8a1. */
#ifndef MU_NPC_PICK_H
#define MU_NPC_PICK_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MU_PICK_CHARACTERS 400   /* the routine walks indices 0..399 */

/* OBB as the client stores it: StartPos, XAxis, YAxis, ZAxis (12 binary32). */
typedef struct mu_obb {
    float start[3], x[3], y[3], z[3];
} mu_obb;

/* 0x00cfeff3(a, b, out): out = a x b, binary32 in the client's order. */
void mu_pick_cross(const float a[3], const float b[3], float out[3]);

/* 0x01850d88(axis, p1, p2, obb): projects the segment and the box on the
 * axis; 1 when the intervals [min(d1,d2), max(d1,d2)] and [lo, hi] overlap
 * (lo/hi: start projection plus the negative/positive axis projections). */
int mu_pick_axis_overlap(const float axis[3], const float p1[3], const float p2[3], const mu_obb *obb);

/* 0x018500bf(p1, p2, obb): the segment p1..p2 against the box on six axes:
 * (p2-p1) x X, x Y, x Z, then X, Y, Z.  1 = no separating axis. */
int mu_pick_segment_obb(const float p1[3], const float p2[3], const mu_obb *obb);

/* One candidate as 0x016b47bf reads it (character c, object o = c + 0x3254). */
typedef struct mu_pick_character {
    uint8_t live;               /* o + 0x00 */
    uint8_t visible;            /* o + 0x0b */
    float alpha;                /* o + 0xdc, must be > 0 */
    uint8_t kind;               /* o + 0x3b, a subset of the mask's bits */
    int32_t type;               /* o + 0x5c, model index */
    uint16_t highlight;         /* c + 0x144: highlight colour index of the first pass */
    uint8_t c1f;                /* c + 0x1f: >= 6 forces highlight 1 */
    uint8_t dead;               /* c + 0x23, must be 0 */
    uint8_t c10;                /* c + 0x10, must be non-zero */
    uint8_t buff_1b;            /* o has buff 0x1b (0x01295ade on o + 0x358): not selectable */
    uint8_t is_hero;            /* c == [0x0a39d754] (skipped unless scene 5) */
    float position[3];          /* o + 0x158 */
    mu_obb obb;                 /* o + 0x31c, adjusted in place for some types (see below) */
    /* written by the routine */
    uint8_t marked;             /* o + 0x05 = 1 by the first pass */
    float light[3];             /* o + 0xec, the first pass's highlight colour */
    uint8_t light_set;
} mu_pick_character;

typedef struct mu_pick_scene {
    int32_t scene;              /* [0x01d1df70]: 5 (character select) lets the hero be picked */
    int32_t world;              /* [0x01cf15fc] */
    float ray_start[3];         /* 0x0bdc5984 */
    float ray_end[3];           /* 0x0bdc5990 */
    float camera[3];            /* 0x0bdc5ab4 */
    const uint8_t *map;         /* 0x0b735420: a byte per tile (256 x 256), read in worlds 0 and 2 */
    int32_t map_value;          /* [0x0b437c10] */
} mu_pick_scene;

/* 0x016b47bf(kind): returns the picked index or -1.  First pass: every
 * candidate of the mask that is live, visible and not transparent gets
 * o+5 = 1 and the highlight light by c+0x144 (0: 0.2 grey, 1: -0.4 grey,
 * 2: (0.2, -0.6, -0.6), 3: 1.5 grey, 4: (0.3, 0.2, -0.5); c+0x1f >= 6:
 * -0.4 grey).  Second pass: the selectable candidates (also not dead, no
 * buff 0x1b, not the hero outside scene 5, c+0x10 set) have their box
 * adjusted in place (type 0xa40: start.z += 300; 0x81b/0x81c: start.z +=
 * 200; 0xa3e: start.x -= 100, start.z += 100, X.x += 100, Z.z += 100;
 * world 0x5d: Z.z += 100; type 0xa64: X.x += 100, Z.z += 100), are tested
 * against the segment, and the one with the smallest squared distance from
 * the camera position wins (start 999999995904, strict less).  In world 2
 * a candidate on a map byte 3 that differs from map_value is refused unless
 * map_value is 0xb. */
int32_t mu_npc_pick(mu_pick_character *characters, int32_t count, uint8_t kind, const mu_pick_scene *scene);

/* The object box the character create routine 0x0137d8a1 gives a model
 * type (o + 0x128 min, o + 0x134 max): default (-60, -60, 0)..(50, 50, 150);
 * other types from the executed table (character_box_table.h). */
void mu_character_box(int32_t type, float min[3], float max[3]);

/* The OBB the model transform builds from that box (bounds mode != 2,
 * 0x012b5bde verified by CLIENT-SKIN-001): start = min + body origin
 * (the object position), axes = diag(max - min). */
void mu_character_obb(const float min[3], const float max[3], const float origin[3], mu_obb *obb);

#ifdef __cplusplus
}
#endif

#endif
