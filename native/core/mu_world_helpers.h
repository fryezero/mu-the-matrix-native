#ifndef MU_WORLD_HELPERS_H
#define MU_WORLD_HELPERS_H

/* Helpers (pets and mounts) in the walk-around world (NATIVE-HELPERS-001, docs/research/client-helpers.md).
 *
 * The client's own routines, reconstructed in reconstructed/helpers (compared with the client in Unicorn):
 *   - the Guardian Angel is a bug (CreateBug 0x00c9d8df, MoveBug 0x00c9d95a, RenderBug 0x00c9e28a, DeleteBug
 *     0x00c9ea70): it circles its owner within 150 units, sparkles (Spark02) and carries a flare sprite;
 *   - the Imp is a link item on the owner's bone 0x22 (BackCarry's helper block, static reading) with a flare;
 *   - Uniria, Dinorant, Dark Horse, Fenrir and the later ride items are mounts of the mount manager (the C++
 *     classes behind 0x0106cde5): the mount follows its rider (base move 0x0103d45a), maps the rider's action to
 *     its own (0x0103d931), raises dust or flying steps, lifts the rider by its bone offset (0x0103da5c) and puts
 *     the rider into the ride actions (0x0106c382: 0x26.. stand, 0x47.. walk, 0x67.. run).
 * This module owns the native side: the models (Data/Item/helper01..02.bmd, Data/Skill/<mount>.bmd), the host
 * services of the reconstructed routines (terrain height, the model's animation tick, SetAction, CreateParticle /
 * CreateSprite / CreateEffect / CreateJoint through NATIVE-PARTICLE-001, the bone lookup by name), the owners
 * (the hero and the players of NATIVE-PLAYERS-001) and the draw.
 *
 * Owners: index 0 is the hero; 1 + i is mu_world_players.list[i]. The hero's helper comes from the demo option
 * (--helper ITEM, labelled DEMO: the client sets it from the inventory, not reconstructed); a player's from its
 * viewport record through ChangeCharacterExt's recorded calls (the angel effect 0x24e6, DeleteBug, the mount
 * manager's reset / set with the ride word c + 0x322e). */

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "../../reconstructed/helpers/helpers.h"
#include "../../reconstructed/helpers/mount_class.h"
#include "mu_bmd.h"
#include "mu_model.h"
#include "mu_raster.h"
#include "mu_scene.h"
#include "mu_terrain.h"
#include "mu_textures.h"

struct mu_world_helpers;
struct mu_jt_object;
struct mu_walk;
struct mu_world_players;
struct mu_world_particles;
struct mu_character;
struct mu_world_raven;
struct mu_world_pets;

enum { MU_WH_EFFECT_BASE = 0x10000000 };
int32_t mu_world_helpers_effect_id(const struct mu_world_helpers *w, const mu_hp_object *object);

enum { MU_WH_OWNERS = 9, MU_WH_MODELS = 16 };

typedef struct mu_wh_model {
    int32_t index;             /* AccessModel index (object +0x5c) */
    int loaded, tried;
    char path[1024];
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    uint8_t *share[3];         /* the Imp: shared bone / root / quaternion storage with its owner (NULL: own) */
} mu_wh_model;

typedef struct mu_wh_owner {
    int active;                /* the hero, or a player in view */
    int32_t key;               /* the manager key (character key c + 0x3e) */
    int32_t helper_item;       /* the hero: the demo helper item code; players: -1 */
    int16_t helper_slot;       /* slot 10 type (0x24e6 angel, 0x24e7 imp, -1) */
    uint16_t ride;             /* c + 0x322e */
    uint8_t ride_state;        /* c + 0x322c */
    uint32_t equip_events, creates;
    int applied;               /* the hero's helper was applied */
    float imp_frame;           /* the Imp's part animation frame (slot +0x14 speed 0.5 per step) */
} mu_wh_owner;

typedef struct mu_wh_stats {
    uint32_t steps, bugs_created, bugs_deleted, mounts_set, mounts_reset;
    uint32_t particles, sprites, effects, joints, set_actions, rider_actions;
    uint32_t live_bugs, live_mounts;                 /* now */
    uint32_t drawn_bugs, drawn_mounts, drawn_imps, shadows;   /* last draw */
    uint32_t passes, decals;                         /* NATIVE-HELPERS-002: model passes, terrain decals (last draw) */
} mu_wh_stats;

typedef struct mu_world_helpers {
    mu_helpers h;
    mu_hp_mounts mounts;
    mu_hp_owner owners[MU_WH_OWNERS];
    mu_wh_owner who[MU_WH_OWNERS];
    mu_hp_inputs inputs;
    char root[1024];
    int no_assets;
    const mu_world *map;
    struct mu_walk *walk;
    struct mu_world_players *players;
    struct mu_world_particles *particles;   /* optional: particles, sprites, effects, joints */
    struct mu_character *hero_character;    /* optional: the hero's model (rider action speeds, the hero's Imp) */
    struct mu_world_pets *pets;             /* NATIVE-HELPERS-002: the pet process (mu_world_pets), NULL when unused */
    mu_wh_model models[MU_WH_MODELS];
    int32_t model_count;
    float shadow_rgba[4];
    mu_wh_stats stats;
    struct mu_world_raven *raven;           /* NATIVE-HELPERS-002: the Dark Raven (mu_world_raven) */
    char log[32][96];
    int32_t log_count;
    float world_time;                       /* NATIVE-HELPERS-002: WorldTime 0x06fce370 (40 ms per step) */
    /* NATIVE-HELPERS-002: the later classes' visual state per mount key */
    int32_t class_keys[MU_HP_MOUNTS];
    mu_hp_class_state class_states[MU_HP_MOUNTS];
    float class_eyes[MU_HP_MOUNTS][2][3]; /* SetEye's +0x188 / +0x194, updated by the class visual */
    int32_t class_state_count;
} mu_world_helpers;

/* Opens the module for a world (no_assets: logic only). hero_item: the hero's helper item code (DEMO, -1 none:
 * 0x1a00 Guardian Angel, 0x1a01 Imp, 0x1a02 Uniria, 0x1a03 Dinorant, 0x1a04 Dark Horse, 0x1a25 Fenrir, the later
 * ride items); hero_state: the ride state (Fenrir: 0 red, 1 black, 2 blue, 4 gold). players may be NULL.
 * Returns 0, or 1 with a message. */
int mu_world_helpers_open(mu_world_helpers *w, const char *game_root, const mu_world *map, struct mu_walk *walk,
                          struct mu_world_players *players, int32_t hero_item, int32_t hero_state, uint32_t seed,
                          int no_assets, char *error, size_t error_size);
void mu_world_helpers_close(mu_world_helpers *w);
void mu_world_helpers_attach_particles(mu_world_helpers *w, struct mu_world_particles *particles);
void mu_world_helpers_attach_hero(mu_world_helpers *w, struct mu_character *hero);

/* One 40 ms logic step after MoveCharacters: the owners' state, the equipment changes, MoveBugs, the mount
 * manager's move loop, the riders' flags and the lift offsets the next placement uses. */
void mu_world_helpers_step(mu_world_helpers *w);
/* The rider action 0x0106c382 of an owner when it rides (0x0106bdb7); returns 1 when it set the action.
 * how: 0 stand, 1 walk, 2 run. */
int mu_world_helpers_ride(mu_world_helpers *w, int32_t owner, int32_t how);

/* Draw target: the backend for a model slot. Returns 0 when it filled `out`. */
typedef struct mu_world_helpers_target {
    void *context;
    int (*backend)(void *context, const mu_world_helpers *w, int32_t slot, mu_render_backend *out);
    /* RenderBodyShadow of a mount (optional): the posed model, the glColor4f colour */
    void (*shadow)(void *context, const mu_world_helpers *w, int32_t slot, const float rgba[4]);
    /* NATIVE-HELPERS-002 (optional): RenderBodyShadow over the meshes first..end (a functor's second shadow) */
    void (*shadow_range)(void *context, const mu_world_helpers *w, int32_t slot, const float rgba[4], int32_t first,
                         int32_t end);
} mu_world_helpers_target;

/* RenderBugs, the mount render loop and the Imps on their owners. hero: the hero's character model (the Imp's
 * host; NULL skips the hero's Imp); frustum: TestFrustrum2D's polygon (NULL: all visible). */
long mu_world_helpers_draw(mu_world_helpers *w, const mu_terrain_frustum *frustum, struct mu_character *hero,
                           const mu_world_helpers_target *target);
long mu_world_helpers_draw_raster(mu_world_helpers *w, mu_raster *raster, const mu_terrain_frustum *frustum,
                                  struct mu_character *hero);

/* The model slot of a model index (loaded on first use; the pets' models share the table) and RenderObject's pose
 * and body for an object of the table (a1: Transform's translate). Return NULL / 0 when there is nothing. */
mu_wh_model *mu_world_helpers_model(mu_world_helpers *w, int32_t index);
int mu_world_helpers_draw_object(mu_world_helpers *w, const struct mu_world_helpers_target *target,
                                 const mu_hp_object *o, int32_t a1);

/* Parses a helper name or item code for --helper: angel, imp, uniria, dinorant, darkhorse, fenrir,
 * fenrir-black/-blue/-gold (sets *state), the later ride item names, the pets (demon, spirit, rudolph, panda,
 * unicorn, skeleton: NATIVE-HELPERS-002), or a number (item code, or G:I). Returns
 * the item code, -1 for "none", -2 when unknown. */
int32_t mu_world_helpers_parse(const char *text, int32_t *state);

/* NATIVE-HELPERS-002: a helper model by index (loaded on first use; NULL when the table is full) and its slot. */
mu_wh_model *mu_world_helpers_model(mu_world_helpers *w, int32_t index);
int32_t mu_world_helpers_model_slot(const mu_world_helpers *w, const mu_wh_model *m);

/* Native owner adapter for the effect and joint pools. IDs hold the mount's stable character key. */
int mu_world_helpers_effect_object(mu_world_helpers *w, int32_t id, struct mu_jt_object *out);
int mu_world_helpers_effect_bone(mu_world_helpers *w, int32_t id, int32_t bone, const float in[3], float out[3]);

void mu_world_helpers_report_frame(const mu_world_helpers *w, FILE *out, int32_t frame);
void mu_world_helpers_report_summary(const mu_world_helpers *w, FILE *out, int quiet);

#endif
