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
    /* Player-model NPCs use CreateMonster's extracted equipment, without becoming remote players. */
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

#endif
