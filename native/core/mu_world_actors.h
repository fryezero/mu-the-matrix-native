/* VIEWPORT-MONSTER-001: actor presentation from session records; fixture owns placement/wander. */
#ifndef MU_WORLD_ACTORS_H
#define MU_WORLD_ACTORS_H

#include <stddef.h>
#include "../session/domains/characters.h"
#include <stdint.h>

#include "../../reconstructed/movement/client_movement.h"
#include "mu_actor.h"
#include "mu_character.h"
#include "mu_renderchar.h"
#include "mu_effect_scene.h"
#include "mu_terrain.h"

#define MU_WORLD_ACTOR_EFFECTS 4
#define MU_WORLD_ACTORS_MAX 32

typedef struct mu_world_actor {
    int32_t session_slot;
    int16_t session_key;
    mu_actor actor;
    struct mu_world_actor_weapons *weapons;
    /* Assembled NPCs use their own skeleton or Player, with extracted parts. */
    mu_character *player;
    mu_renderchar_glow player_glow[MU_CHARACTER_ITEMS];
    int32_t server_class;
    char label[48];
    float position[3];        /* object +0x158 */
    float angle[3];           /* object +0x164 (degrees) */
    int32_t tile[2];          /* character +0x180 / +0x184 */
    mu_path path;             /* character +0x3194 */
    uint8_t moving, run;
    float timer;              /* object +0xb4 */
    int32_t home[2], wander, idle_steps;
    uint8_t step_result;      /* AL of the last animation step */
    int32_t effects[MU_WORLD_ACTOR_EFFECTS], effect_bone[MU_WORLD_ACTOR_EFFECTS], effect_count;
    uint32_t moves, arrivals;
} mu_world_actor;

typedef struct mu_world_actors {
    uint64_t record_stamp;
    struct mu_session *session;
    struct mu_fixture *fixture;
    struct mu_transport *transport;
    mu_world_actor *list;
    int32_t count;
    const mu_world *map;
    mu_effect_scene effects;
    int has_effects;
    uint32_t rng;             /* demo wander only */
    uint32_t steps, moves, arrivals, effect_instances;
    char log[16][96];
    int32_t log_count;
} mu_world_actors;

int mu_world_actors_init_records(mu_world_actors *actors, const char *root, const mu_world *map,
    const mu_characters_view *view, char *error, size_t cap);
void mu_world_actors_free(mu_world_actors *actors);

void mu_world_actors_step_one(mu_world_actors *actors, int32_t index, mu_rp_character *record);
/* Per rendered frame: pose and skin every actor, move its effects with it
 * (external matrices) and run the effect node updates (dt per frame, the
 * client's 0.1). */
void mu_world_actors_frame(mu_world_actors *actors, float effect_dt);

/* Ordinary RenderObjDraw pass for a recovered composite NPC part. */
int mu_world_actor_npc_part_draw(const mu_world_actor *actor, int slot, float alpha,
    const mu_render_backend *backend, mu_draw_stats *stats);

/* Recovered monster weapons, independently owned by this actor instance. */
const mu_renderchar_attachment *mu_world_actor_weapon(const mu_world_actor *actor, int slot);
int mu_world_actor_weapon_draw(const mu_world_actor *actor, int slot, float alpha,
    const mu_renderchar_env *env, const mu_render_backend *backend, mu_draw_stats *stats);

/* Apply the generated single-body draw plan when this exact fixture matches.
 * Returns 1 for a checked plan, 0 for other actors. Other draw options remain
 * owned by the caller. World/buff/temporal equivalence is outside this API. */
int mu_world_actor_plain_options(const mu_world_actor *actor, float alpha, mu_draw_options *options);

/* RENDER-ACTORS-008: RenderLinkItem's own sprite requests of a checked monster
 * weapon (the plan's link_effect_mask), through the item link consumer the
 * hero's weapons use, on the hand's posed bones. Returns the requests kept. */
struct mu_world_particles;
long mu_world_actor_weapon_effects(const mu_world_actor *actor, int slot, struct mu_world_particles *particles);

/* RENDER-ACTORS-008: the checked plan's RenderCharacter sprite requests for
 * one rendered frame, in original order. Positions are TransformPosition
 * 0x012b6ef1 of the actor's posed body bone. clock: world time in ms;
 * random_value: the caller's one rand() (used only by flicker rows, see
 * mu_actor_caller_fx_random). Returns the number of requests sent, 0 for an
 * actor without a checked request plan or whose model, scale, weapons or
 * bones differ from it; then nothing is sent. */
typedef struct mu_world_actor_fx {
    int32_t bitmap;
    float position[3], scale, light[3];
    int32_t owner;                 /* 1: the actor's OBJECT, 0: none */
    float rotation;
    int32_t blend, axes;
} mu_world_actor_fx;
typedef void (*mu_world_actor_fx_fn)(void *context, const mu_world_actor_fx *request);
int32_t mu_world_actor_caller_fx(const mu_world_actor *actor, float clock, int32_t random_value,
                                 mu_world_actor_fx_fn emit, void *context);

#endif
