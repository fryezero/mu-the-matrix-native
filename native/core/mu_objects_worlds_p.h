/* RENDER-WORLDS-P host side of worlds 135/136/140 (see reconstructed/objects/worlds_p.h). */
#ifndef MU_OBJECTS_WORLDS_P_H
#define MU_OBJECTS_WORLDS_P_H
#include "mu_objects.h"
/* Deferred class create of worlds 135/136 (MU_WP_CREATE): the type's model action speeds and the RNG. */
void mu_objects_worlds_p_create(mu_objects *, int32_t index);
/* Deferred class move (MU_WP_MOVE), after this object's animation tick. */
void mu_objects_worlds_p_move(mu_objects *, int32_t index, const float hero[3]);
/* PlaySpeed of (type, action) written by a 135/136 create; 0 with *set = 0 otherwise. */
float mu_objects_worlds_p_speed(const mu_objects *, int32_t type, int32_t action, int *set);
#endif
