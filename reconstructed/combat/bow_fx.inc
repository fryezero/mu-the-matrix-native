/* RENDER-EFFECTS-011: the bows' effects, included by skill_fx.c after pet_fx.inc. CreateEffect's cases and
 * MoveEffect's cases (both end in the common code of skill_fx.c):
 *   0x477/3, 0x477/4  the arrows of 0x45b/0x47f/0x60d: a widening ring (create 0x013d9444, subtypes 2..4
 *                     0x013d97f4; move 0x014719f8 / 0x01471ac0)
 *   0x60b/0           0x60a's burst (create 0x014001e3, move 0x01468a1f)
 *   0x611/0           0x610's ring (create 0x0140fea0, move 0x014c4c8e)
 *   0x45f/0, 0x45f/1  0x45c's dark feathers (darkwing_hetachi; create 0x013e45bc, move 0x01488ec6 / 0x0148922a)
 *   0x70c/0           the ground skills' landing mark (RENDER-EFFECTS-010's ground test; create 0x0141a4c4 with
 *                     effects 0x703..0x706 and 0x419/0x41a, move 0x014d2131)
 * RENDER-EFFECTS-014, 0x70c's rings (min_elf_skill_ring04..07, loader 0x01827299..0x01827354; RenderEffects'
 * default RenderObject): 0x703/0 and 0x704/0 (create 0x01419f69 / 0x01419fa0, move 0x014d09e8 / 0x014d0a48),
 * 0x705/0, 1, 3 (create 0x0141a016, move 0x014d2253), 0x706/0 (create 0x0141a168, move 0x014d0aa8). */

static int bow_effect_kind(int32_t type, int32_t sub)
{
    return (type == 0x477 && (sub == 3 || sub == 4)) || (type == 0x60b && sub == 0) || (type == 0x611 && sub == 0) ||
           (type == 0x45f && (sub == 0 || sub == 1)) || (type == 0x70c && sub == 0) ||
           ((type == 0x703 || type == 0x704 || type == 0x706) && sub == 0) ||
           (type == 0x705 && (sub == 0 || sub == 1 || sub == 3));
}

/* 0x706 and 0x705/3: alpha = pow(1 - |life0 - 2 life| / life0, 2), the pulse 0x0184f8ff / 0x00cee37c */
static float ring_pulse(const mu_sfx_effect *e)
{
    float t = (float)e->field_70 - (float)e->lifetime * 2.0f;
    t = 0.0f > t ? -t : t;
    return (float)pow((double)(1.0f - t / (float)e->field_70), 2.0);
}

/* VectorNormalize 0x00cff0d3: divides by the length (sqrtf 0x00961a07); zero below 1e-6 */
static void bow_vector_normalize(float v[3])
{
    const float length = sqrtf(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
    if (f32bits(0x358637bdu) > length) {
        v[0] = v[1] = v[2] = 0.0f;
        return;
    }
    for (int k = 0; k < 3; ++k)
        v[k] = v[k] / length;
}

static int bow_effect_create(mu_sfx_effect *e, const float angle_arg[3], float scale, const mu_sfx_info *info,
                             const mu_sfx_env *env)
{
    switch (e->type) {
    case 0x703: case 0x704: case 0x705: case 0x706:   /* rings: twenty steps */
        e->field_70 = 20;
        e->lifetime = 20; /* ring life */
        if (e->type == 0x705 && e->subtype == 3) {
            e->scale = scale;
            e->alpha = 0.0f;
        } else if (e->type == 0x706) {
            e->scale = scale;
            e->alpha = 0.0f; /* 0x706 alpha */
        } else {
            e->scale_arg = scale; /* ring growth */
            e->scale = 0.0f;
        }
        if (e->type == 0x704)
            e->angle[1] = arrow_rand_range(env, 0.0f, 360.0f);   /* 0x01419feb: 0x011ff622(0, 360, 1) */
        return 1;
    case 0x70c: {
        e->lifetime = 50;
        e->field_70 = 20;
        e->scale = 0.0f;
        e->field_d8 = 0.0f;
        set3(e->angle, 0.0f, 0.0f, 0.0f);
        set3(e->light, 1.0f, 1.0f, 1.0f);
        float light[3] = {0.75f, 0.75f, 1.0f};
        call_effect_ks(env, e, 0x704, e->position, e->angle, light, 0, MU_SFX_NO_OWNER, 0xffff, 0.5f);
        set3(light, F_0_8, F_0_4, 1.0f);
        call_effect_ks(env, e, 0x703, e->position, e->angle, light, 0, MU_SFX_NO_OWNER, 0xffff, 0.25f);
        set3(light, f32bits(0x3f333333u), f32bits(0x3f333333u), 1.0f);   /* 0.7 */
        call_effect_ks(env, e, 0x705, e->position, e->angle, light, 0, MU_SFX_NO_OWNER, 0xffff, 0.25f);
        set3(light, F_0_2, F_0_9, F_0_9);
        call_effect_ks(env, e, 0x705, e->position, e->angle, light, 1, MU_SFX_NO_OWNER, 0xffff, 0.125f);
        set3(light, 1.0f, 1.0f, 1.0f);
        call_effect_ks(env, e, 0x705, e->position, e->angle, light, 3, MU_SFX_NO_OWNER, 0xffff, 0.25f);
        call_effect_ks(env, e, 0x706, e->position, e->angle, light, 0, MU_SFX_NO_OWNER, 0xffff,
                       f32bits(0x3e051eb8u));   /* 0.13 */
        set3(light, 1.0f, 0.0f, 0.0f);
        for (int k = 0; k < 2; ++k) {              /* two stones 0x419 / 0x41a turned at random */
            float turn[3] = {0.0f, 0.0f, 0.0f};
            turn[2] = arrow_rand_range(env, 0.0f, 360.0f);
            const int32_t stone = 0x419 + smod(env_rand(env), 2);
            call_effect_ks(env, e, stone, e->position, turn, light, 0x13, MU_SFX_NO_OWNER, 0xffff, 0.0f);
        }
        e->angle[2] = arrow_rand_range(env, 0.0f, 360.0f);
        return 1;
    }
    case 0x45f: {                                  /* subtypes 0 and 1 */
        float from[3];
        copy3(from, e->position);
        for (int k = 0; k < 3; ++k)
            e->position[k] = (float)(smod(env_rand(env), 20) - 10) * 4.0f + e->position[k];
        for (int k = 0; k < 3; ++k)
            e->direction[k] = from[k] - e->position[k];
        bow_vector_normalize(e->direction);
        const int32_t jitter = (int32_t)((float)(smod(env_rand(env), 10) - 5) * f32bits(0x3da3d70au));   /* 0.08 */
        for (int k = 0; k < 3; ++k)
            e->direction[k] = (float)jitter + e->direction[k];
        e->scale = (float)(smod(env_rand(env), 20) - 10) * (e->scale * f32bits(0x3cf5c28fu)) + e->scale;   /* 0.03 */
        e->lifetime = smod(env_rand(env), 20) + 20;
        e->alpha = (float)smod(env_rand(env), 10) * f32bits(0x3ca3d70au) + f32bits(0x3f19999au);   /* 0.02, 0.6 */
        e->gravity = F_0_1;
        for (int k = 0; k < 3; ++k)
            e->angle[k] = (float)smod(env_rand(env), 360);
        for (int k = 0; k < 3; ++k)
            e->spin[k] = (float)(smod(env_rand(env), 10) - 5);
        return 1;
    }
    case 0x477:
        e->lifetime = 20;
        e->gravity = F_0_1;
        e->blend_mesh = -2;
        e->blend_light = 1.0f;
        e->angle[0] = e->angle[1] = e->angle[2] = 0.0f;
        copy3(e->impact, e->position);
        e->position[2] = e->position[2] + 50.0f;
        /* subtypes 2..4, 0x013d97f4 */
        e->lifetime = 15;
        e->key = 0xffff;
        e->scale = (float)(int16_t)info->key * f32bits(0x3d4ccccdu);   /* the info key x 0.05 (0x01a7e6d4) */
        e->gravity = F_0_01;
        e->position[2] = e->position[2] - 50.0f;
        e->angle[0] = 90.0f;
        e->angle[2] = angle_arg[2];
        return 1;
    case 0x60b:
        e->lifetime = 10;
        e->scale = 2.0f;
        e->blend_mesh = 0;
        return 1;
    default:                                       /* 0x611 */
        e->lifetime = 10;
        e->field_70 = 10;
        e->scale = scale;                          /* the argument itself (CreateEffect's 0.9 for <= 0 undone) */
        e->angle[0] = -90.0f;
        return 1;
    }
}

static void bow_effect_move(mu_sfx_effect *e, const mu_sfx_env *env)
{
    switch (e->type) {
    case 0x703: case 0x704: case 0x705:            /* grow by the argument over life0 and fade */
        if (e->type == 0x705 && e->subtype == 3) {
            e->alpha = ring_pulse(e); /* 0x705/3 pulse */
            return;
        }
        e->scale = e->scale_arg / (float)e->field_70 + e->scale;
        e->alpha = e->alpha - 1.0f / (float)e->field_70; /* ring fade */
        return;
    case 0x706:                                    /* 0x014d0aa8: four-frame scroll and the pulse */
        e->blend_v = (float)(e->lifetime % 4) * 0.25f; /* 0x706 scroll */
        e->alpha = ring_pulse(e);
        return;
    case 0x70c: {                                  /* grows, fades and pulses once at life 30 */
        e->scale = 1.0f / (float)e->field_70 + e->scale;
        e->alpha = e->alpha - 1.0f / (float)e->field_70;
        float t = (float)e->field_70 - (float)(e->lifetime - 30) * 2.0f;
        t = 0.0f > t ? -t : t;                     /* 0x0184f8ff */
        e->field_d8 = (float)pow((double)(1.0f - t / (float)e->field_70), 2.0);   /* 0x00cee37c(x, 2) */
        if (e->lifetime < 25)
            for (int k = 0; k < 3; ++k)
                e->light[k] = e->light[k] - f32bits(0x3d23d70au);   /* 0.04 */
        return;
    }
    case 0x45f: {                                  /* fades; subtype 1 also shrinks; spins */
        const float fade = f32bits(0x3f7851ecu);   /* 0.97 */
        for (int k = 0; k < 3; ++k)
            e->light[k] = e->light[k] * fade;
        e->alpha = e->alpha * fade;
        if (e->subtype == 1)
            e->scale = e->scale * f32bits(0x3f7d70a4u);   /* 0.99 */
        for (int k = 0; k < 3; ++k)
            e->angle[k] = e->spin[k] + e->angle[k];
        return;
    }
    case 0x477: {
        const int three = e->subtype == 3;
        e->scale = e->scale + e->gravity;
        e->gravity = e->gravity + (three ? f32bits(0x3ba3d70au) : f32bits(0x3b03126fu));   /* 0.005 / 0.002 */
        const float most = three ? 1.5f : 2.5f;
        if (e->scale > most)
            e->scale = most;
        e->blend_light = e->blend_light / (three ? f32bits(0x3fa66666u) : f32bits(0x3f99999au));   /* 1.3 / 1.2 */
        e->angle[1] = e->angle[1] + 45.0f;
        return;
    }
    case 0x60b: {
        int16_t keys = 1;
        if (env && env->model && !env->model(env->context, e->type, e->action, &keys))
            return;                                /* no model: 0x01468a40 */
        e->scale = e->scale + f32bits(0x3f19999au);   /* 0.6 */
        e->angle[1] = e->angle[1] + 30.0f;
        e->blend_light = e->blend_light / f32bits(0x3fa66666u);
        if (F_0_2 > e->blend_light) {
            e->blend_light = 0.0f;
            kill_effect(env, e);                   /* SetLive(o, 0) 0x0129f4a5 */
        }
        return;
    }
    default:                                       /* 0x611 */
        e->scale = e->scale + 0.25f;
        e->alpha = (float)e->lifetime / (float)e->field_70;
        return;
    }
}
