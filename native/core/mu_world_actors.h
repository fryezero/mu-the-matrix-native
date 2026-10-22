/* Monsters and NPCs placed in the walk-around world (NATIVE-WORLD-002).
 *
 * In the real game the server places every monster and NPC (create packets
 * with the server class, tile and direction) and sends their movement paths.
 * The native session has no server, so a DEMO PLACEMENT FILE stands in for
 * those packets; it is not client data and not a reading of the server. Each
 * line names a server class, a tile, a direction and an optional wander
 * radius:
 *
 *     # comment
 *     actor <server-class> <tile-x> <tile-y> <direction 0..7> [wander <radius>] [label <text>]
 *
 * What follows the placement is client behaviour, reconstructed elsewhere:
 *
 *   - class -> model, opened monster type or NPC index and object scale: the
 *     CreateMonster table (reconstructed/actors/monster_class_table.h), or for
 *     the classes whose creation calls the EffectManager the extraction in
 *     reconstructed/actors/effect_class_table.h;
 *   - action play speeds and loop flags: OpenMonsterModel / OpenNpc and the
 *     class speeds (mu_actor);
 *   - every 40 ms step: SetAction 0x012affa4 and the character animation step
 *     0x013960d2 with the tick (mu_actor);
 *   - movement along a path: MovePath 0x012b0846 and MoveCharacterPosition
 *     0x0137b351 at CharacterMoveSpeed 0x013957b5 with the MoveSpeed word
 *     10 that character create stores (0x0137dbb2, static reading);
 *   - effects the creation attaches (factory 0x00a797a0, attach 0x0129f9c6):
 *     instances of the EffectManager scene (mu_effect_scene) following the
 *     object.
 *
 * Demo choices (labelled, not client readings): the wander targets and the
 * straight cell paths toward them stand in for the server's move packets;
 * monsters use action 2 while moving and 0 while standing (the action
 * indices of docs/research/client-actors.md section 2, an inference); NPCs
 * stand in action 0; the bone-following effect matrix uses the bone's
 * point (its matrix translation times the body scale, plus the origin, as
 * the transform places a vertex on the bone) and the object scale, not the
 * bone rotation of 0x0129fd4f, which was not traced.
 */
#ifndef MU_WORLD_ACTORS_H
#define MU_WORLD_ACTORS_H

#include <stddef.h>
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

/* Parses a placement file and loads every actor (textures unless
 * no_textures). Lines that fail to resolve are reported in error and make the
 * call fail. Returns 0 on success. */
int mu_world_actors_load(mu_world_actors *actors, const char *game_root, const mu_world *map, const char *placement,
                         int no_textures, char *error, size_t error_size);
/* Same from text (tests). */
int mu_world_actors_load_text(mu_world_actors *actors, const char *game_root, const mu_world *map, const char *text,
                              int no_textures, char *error, size_t error_size);
void mu_world_actors_free(mu_world_actors *actors);

/* One 40 ms logic step: demo wander decisions, movement, SetAction and the
 * animation step of every actor. */
void mu_world_actors_step(mu_world_actors *actors);
/* Per rendered frame: pose and skin every actor, move its effects with it
 * (external matrices) and run the effect node updates (dt per frame, the
 * client's 0.1). */
void mu_world_actors_frame(mu_world_actors *actors, float effect_dt);

#endif
