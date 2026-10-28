#ifndef MU_WORLD_WARP_H
#define MU_WORLD_WARP_H
#include "../combat/skill_fx.h"
#include "objects.h"
/* RENDER-WORLDS-D: CreateEffect 0x013c38ef/0x013c391b and MoveEffect
 * 0x01435834, following the common effect initialization/prologue. */
int mu_world_warp_type(int32_t type);
void mu_world_warp_create(mu_sfx_effect *e, float source_light[3], const mu_sfx_env *env);
void mu_world_warp_move(mu_sfx_effect *e, float world_time);
int mu_world_warp_render(mu_sfx_effect *e, const float normal[5][3], const float d[5],
                         int alpha_pass, int model_meshes);
/* AccessModels' Noria placement, 0x01839870..0x01839952. */
int32_t mu_noria_records(mu_object_record *records);
#endif
