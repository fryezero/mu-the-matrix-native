#ifndef MU_PT_WORLD_FLAMES_H
#define MU_PT_WORLD_FLAMES_H
#include "particles.h"
int mu_pt_world_flame_kind(int32_t type, int32_t sub);
void mu_pt_world_flame_create(mu_pt_particle *, const mu_pt_host *, float);
void mu_pt_world_flame_move(mu_pt_particle *, const mu_pt_host *);
#endif
