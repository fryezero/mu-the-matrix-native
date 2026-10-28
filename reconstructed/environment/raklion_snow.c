/* World-handler leaf slot 0x64, 0x00e9ec6a..0x00e9ee78. */
#include "../record-math/record_math.h"
#include "env_internal.h"
void mu_env_raklion_snow(mu_env *env, const mu_env_inputs *in, mu_env_leaf *l)
{
    l->texture = MU_ENV_BITMAP_LEAF1;
    l->scale = (float)(mu_env_rand(env) % 10 + 3);
    if (mu_env_rand(env) % 10 == 0)
        l->scale = (float)(mu_env_rand(env) % 3 + 10);
    l->position[0] = (float)(mu_env_rand(env) % 1600 - 800) + in->hero_position[0];
    l->position[1] = (float)(mu_env_rand(env) % 1400 - 500) + in->hero_position[1];
    l->position[2] = (float)(mu_env_rand(env) % 200 + 200) + in->hero_position[2];
    l->angle[0] = -(float)(mu_env_rand(env) % 30 + 50);
    l->angle[1] = 0;
    l->angle[2] = 0;
    float v[3] = {0, 0, -(float)(mu_env_rand(env) % 20 + 30)}, m[3][4];
    mu_angle_matrix(l->angle, m);
    mu_vector_rotate(v, m, l->velocity);
}
