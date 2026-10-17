#ifndef MU_ACTOR_H
#define MU_ACTOR_H

#include <stddef.h>
#include <stdint.h>

#include "mu_bmd.h"
#include "mu_model.h"
#include "mu_textures.h"
#include "../../reconstructed/actors/actors.h"

/* Animated monsters and NPCs for the native viewer (NATIVE-ACTOR-001).
 *
 * An actor is named the way the client names it:
 *   - a server monster class (CreateMonster 0x0137fbac): the extracted class
 *     table gives the model index, the opened monster type or NPC index, the
 *     object scale and the equipment slots;
 *   - a monster type (OpenMonsterModel 0x0180b0f4): Data/Monster/Monster<nn>.bmd,
 *     model index type + 0x7a5;
 *   - an NPC model index (OpenNpc 0x01808a40): the extracted NPC file table.
 * Loading lays the model out as client memory (mu_model) and then runs the
 * reconstructed opener over that memory, so the action records get the
 * client's play speeds and loop flags: mu_monster_open for monsters, the
 * extracted OpenNpc speeds for NPCs, then the speeds CreateMonster writes for
 * the class. Actions the client leaves unset (the reader allocates the action
 * array without initialising play speeds) get MU_ACTOR_UNSET_SPEED, a viewer
 * choice.
 *
 * Each step runs the reconstructed SetAction 0x012affa4 and character
 * animation step 0x013960d2 (which runs the reconstructed tick 0x012b4dd3) on
 * a client-layout object and character record placed next to the model
 * window. As in the client's callers, the model's current action (+0xa8) is
 * set from the object's action before the step. The resulting frame, prior
 * frame and prior action feed the pose builder and skinning through mu_model.
 */

#define MU_ACTOR_OBJECT 0x0e000000u      /* client-layout object (0x400 bytes) */
#define MU_ACTOR_CHARACTER 0x0e001000u   /* client-layout character record (0x200 bytes) */
#define MU_ACTOR_SCRATCH_MODEL 0x0e002000u /* stands in for other models an opener touches */
#define MU_ACTOR_UNSET_SPEED 0.25f

enum { MU_ACTOR_BY_CLASS = 1, MU_ACTOR_BY_MONSTER = 2, MU_ACTOR_BY_NPC = 3 };

typedef struct mu_actor_spec {
    int by;                   /* MU_ACTOR_BY_* */
    int32_t id;               /* server class, monster type or NPC index */
    int32_t monster_type;     /* -1 when not a monster */
    int32_t npc_index;        /* -1 when not an NPC */
    int32_t model_index;      /* client model index (object +0x5c) */
    int32_t server_class;     /* -1 when not given by class */
    float scale;              /* object scale (+0xa0) */
    char path[4096];          /* resolved model file */
} mu_actor_spec;

/* Resolves the model file under game_root/Data (case-insensitive file match).
 * Returns 0 on success, 1 with a message otherwise (player-model classes and
 * classes without a model are refused). */
int mu_actor_resolve(const char *game_root, int by, int32_t id, mu_actor_spec *spec, char *error, size_t error_size);

enum { MU_ACTOR_REGIONS = MU_MODEL_REGION_COUNT + 3 };

typedef struct mu_actor {
    mu_actor_spec spec;
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    int loaded;
    uint8_t object[0x400], character[0x200], scratch[0x100 + 32 * 16];
    mu_client_image regions[MU_ACTOR_REGIONS];
    mu_client_memory memory;
    int32_t open_status;      /* status of the reconstructed opener */
    uint32_t unset_actions;   /* actions given MU_ACTOR_UNSET_SPEED */
    float last_speed;         /* speed the last step passed to the tick */
} mu_actor;

/* Loads the resolved model and textures (unless no_textures) and applies the
 * client's action setup. params->body_scale is replaced by spec->scale. */
int mu_actor_load(mu_actor *actor, const mu_actor_spec *spec, const mu_model_params *params, int no_textures,
                  char *error, size_t error_size);
void mu_actor_free(mu_actor *actor);

/* Play speed and loop flag of an action record after the setup. */
float mu_actor_action_speed(const mu_actor *actor, int32_t action);
int mu_actor_action_loop(const mu_actor *actor, int32_t action);
int32_t mu_actor_action_count(const mu_actor *actor);
uint16_t mu_actor_action(const mu_actor *actor);
float mu_actor_frame(const mu_actor *actor);

/* Reconstructed SetAction 0x012affa4 on the actor's object. */
int mu_actor_set_action(mu_actor *actor, int32_t action);
/* One animation step (client logic step): reconstructed 0x013960d2 with the
 * tick. *loop receives its AL. */
int mu_actor_step(mu_actor *actor, uint8_t *loop);
/* Pose and skin the model from the object's animation state. */
int mu_actor_update(mu_actor *actor);

#endif
