/* RENDER-EFFECTS-007: Rudolph's effect 0x3fa (subtype 0, the pet's visuals 0x00eaf993 in state 3), included by
 * skill_fx.c. CreateEffect's shared 0x3f4..0x3fa body 0x013de0ff and MoveEffect's case 0x01437d53. Cosmetic only. */

static int pet_effect_kind(int32_t type, int32_t sub)
{
    return type == 0x3fa && sub == 0;
}

/* 0x013de157..0x013de439 for 0x3fa (the 0x3f4..0x3f8 branches are not taken) */
static int pet_effect_create(mu_sfx_effect *e, const mu_sfx_env *env)
{
    e->lifetime = smod(env_rand(env), 10) + 50;
    e->scale = (float)(smod(env_rand(env), 10) - 5) * 0.02f + 1.6f;
    for (int k = 0; k < 3; ++k)
        e->angle[k] = (float)smod(env_rand(env), 360);
    float m[12];
    mu_angle_matrix(e->angle, m);
    e->gravity = (float)(smod(env_rand(env), 10) + 10);
    float v[3];
    v[0] = (float)(smod(env_rand(env), 10) - 5) * F_0_1;
    v[1] = (float)(smod(env_rand(env), 60) - 40) * F_0_1;
    v[2] = 0.0f;
    for (int k = 0; k < 3; ++k)
        v[k] = 1.3f * v[k];
    mu_vector_rotate(v, m, e->direction);
    e->field_64 = smod(env_rand(env), 3);   /* the axis it spins about */
    return 1;
}

/* 0x01437d53 (model Data\\Monster\\sulgold.bmd, loader 0x00a938d2): a gold piece spins, drifts, falls and bounces once on the terrain (two steps of life each bounce), then drift again */
static void pet_effect_move(mu_sfx_effect *e, const mu_sfx_env *env)
{
    if (e->field_64 >= 0 && e->field_64 < 3)
        e->angle[e->field_64] = e->angle[e->field_64] + 10.0f;
    e->position[0] = e->direction[0] * 1.2f + e->position[0];
    e->position[1] = e->direction[1] * 1.2f + e->position[1];
    e->position[2] = e->gravity * 1.5f + e->position[2];
    e->gravity = e->gravity - 1.5f;
    const float ground = env_height(env, e->position[0], e->position[1]);
    if (ground > e->position[2]) {
        e->position[2] = ground;
        e->gravity = -e->gravity * F_0_3;
        e->lifetime = e->lifetime - 2;
    }
    for (int k = 0; k < 3; ++k)
        e->position[k] = e->position[k] + e->direction[k];
}
