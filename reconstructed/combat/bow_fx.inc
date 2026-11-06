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
           (type == 0x705 && (sub == 0 || sub == 1 || sub == 3)) ||
           ((type == 0x70a || type == 0x700 || type == 0x701 || type == 0x702) && (sub == 0 || sub == 1)) ||
           (type == 0x707 && sub == 0);
}

/* 0x706 and 0x705/3: alpha = pow(1 - |life0 - 2 life| / life0, 2), the pulse 0x0184f8ff / 0x00cee37c */
static float ring_pulse(const mu_sfx_effect *e)
{
    float t = (float)e->field_70 - (float)e->lifetime * 2.0f;
    t = 0.0f > t ? -t : t;
    return (float)pow((double)(1.0f - t / (float)e->field_70), 2.0);
}

/* RENDER-EFFECTS-015: the ground skills' rain 0x70a (create 0x01418f78..0x0141955d, move 0x014d1a18..0x014d2131,
 * render 0x0152dc88) and its rings min_elf_skill_ring01..03, 08 (0x700..0x702, 0x707; AccessModel 0x018271fa..
 * 0x0182736d, textures Effect\; create 0x0141a21a, 0x0141a29c, 0x0141a319, 0x01419f40; move 0x014d0586, 0x014d06fc,
 * 0x014d0872, 0x014d0b58; RenderEffects' default RenderObject). */

/* The PlayBuffer 0x00a6ac96 call site (and its routine) of each effect sound the reconstructed routines play: the
 * session's sound provenance (MU_CUE_SOUND site). One site per sound among them; 0 for any other sound. */
uint32_t mu_sfx_sound_site(int32_t sound, uint32_t *routine)
{
    static const struct { int32_t sound; uint32_t routine, site; } sites[] = {
        {0x582, 0x013c0f19u, 0x013c42eeu},   /* CreateEffect 0x40e: the tornado */
        {0x55d, 0x013c0f19u, 0x0141953eu},   /* CreateEffect 0x70a: the ground skills' rain */
        {0x97, 0x0142fd09u, 0x01451cceu},    /* MoveEffect 0x461: Rageful Blow's quake */
        {0x96, 0x0142fd09u, 0x014520f4u},    /* MoveEffect 0x461: the weapon's hop */
        {0x55e, 0x0142fd09u, 0x014eca9au},   /* MoveEffect's ground test: an owner's first landing */
        {0x42, 0x01556c26u, 0x01579fa1u},    /* MoveJoint 0x7f78/b at lifetime 30 */
    };
    for (size_t k = 0; k < sizeof sites / sizeof sites[0]; ++k)
        if (sites[k].sound == sound) {
            if (routine)
                *routine = sites[k].routine;
            return sites[k].site;
        }
    if (routine)
        *routine = 0;
    return 0;
}

/* position + (0, 0, z) as the vector sum 0x00cfca74 (so -0 + 0 = +0 in x and y) */
static void lifted(float out[3], const float position[3], float z)
{
    out[0] = position[0] + 0.0f;
    out[1] = position[1] + 0.0f;
    out[2] = position[2] + z;
}

/* 0x012af5cb(position, angle, target): the heading (0x012aed9e) to the target and the pitch over the ground
 * distance (sqrtf 0x00961a07); the length 0x00cfd020 it then takes is discarded */
static void bow_aim(const float p[3], float angle[3], const float t[3])
{
    angle[2] = mu_create_angle(p[0], p[1], t[0], t[1]);
    const float d[3] = {p[0] - t[0], p[1] - t[1], p[2] - t[2]};
    const float h = sqrtf(d[0] * d[0] + d[1] * d[1]);
    angle[0] = 360.0f - mu_create_angle(p[2], h, t[2], 0.0f);
}

/* CreateArrow 0x0158cf57(caster, this effect, 0, 0x7e7, 0x7e7, 0x7e7, 0) at the effect's current position */
static void rain_arrow(const mu_sfx_env *env, mu_sfx_effect *e)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_CREATE_ARROW;
    c.type = 0x7e7;
    c.subtype = 0x7e7;
    c.range = 0x7e7;
    c.owner = -2;
    copy3(c.position, e->position);
    copy3(c.angle, e->angle);
    copy3(c.light, e->light);
    env_call(env, &c, e);
}

/* one aimed shot: from 500 above a random point within 200 of the effect, at the point twice as far out on the
 * effect's own height (0x014d1b35..0x014d1ccb) */
static void rain_shot(const mu_sfx_env *env, mu_sfx_effect *e)
{
    float target[3];
    copy3(target, e->position);
    const float dx = arrow_rand_range(env, -200.0f, 200.0f);   /* 0x011ff622(-200, 200, 1); 0x01a9a3b4, 0x01a7dec8 */
    const float dy = arrow_rand_range(env, -200.0f, 200.0f);
    e->position[0] = e->position[0] + dx;
    e->position[1] = e->position[1] + dy;
    e->position[2] = env_height(env, e->position[0], e->position[1]) + 500.0f; /* rain height */
    target[0] = dx * 2.0f + target[0];
    target[1] = dy * 2.0f + target[1];
    bow_aim(e->position, e->angle, target);
    rain_arrow(env, e);
}

static void rain_move(mu_sfx_effect *e, const mu_sfx_env *env)
{
    e->alpha = ring_pulse(e);
    if (e->lifetime <= 10)
        e->field_d8 = (float)(10 - e->lifetime); /* rain fade */
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_CASTER;
    c.range = (int16_t)e->key;
    c.owner = -2;
    if (!env_call(env, &c, e))
        return;                                    /* no caster, or its +0x23 is set: 0x014eca00 */
    float position[3], angle[3];
    copy3(position, e->position);
    copy3(angle, e->angle);
    if (e->subtype == 1) {
        if (e->lifetime > 9)                       /* subtype 1: eleven aimed shots */
            rain_shot(env, e);
    } else if (e->lifetime > 15) {                 /* 0x014d1e5b: straight up from 200 above the effect */
        e->position[2] = env_height(env, e->position[0], e->position[1]) + 200.0f;
        e->angle[0] = 270.0f;
        e->angle[2] = 180.0f;
        e->angle[1] = arrow_rand_range(env, -10.0f, 10.0f);
        rain_arrow(env, e);
    } else if (e->lifetime > 9) {
        rain_shot(env, e);
    }
    copy3(e->position, position);                  /* 0x014d1cde: both restored */
    copy3(e->angle, angle);
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
    case 0x700: case 0x701: case 0x702:            /* rings 01..03: 25 steps */
        e->field_70 = 25;
        e->lifetime = 25;
        if (e->subtype == 0) {
            e->scale = scale;
        } else {
            e->scale_arg = scale;
            e->scale = e->type == 0x701 ? 0.0f : 1.0f; /* ring 1 start */
        }
        return 1;
    case 0x707:
        e->field_70 = 20;
        e->lifetime = 20;
        e->scale = scale;
        return 1;
    case 0x70a: {
        /* +0x38 = 1 (0x01418f7b) is not modelled: no reconstructed routine reads it */
        e->field_70 = 20;
        e->lifetime = 20; /* rain life */
        e->field_d8 = 0.0f;
        e->scale = scale;
        set3(e->light, 1.0f, 1.0f, 1.0f);
        float light[3] = {0.5f, f32bits(0x3f266666u), 1.0f};   /* 0.65 */
        float p[3];
        lifted(p, e->position, 300.0f);
        call_effect_ks(env, e, 0x700, p, e->angle, light, 0, MU_SFX_NO_OWNER, 0xffff, 2.5f);
        set3(light, f32bits(0x3f266666u), F_0_3, f32bits(0x3f333333u));   /* (0.65, 0.3, 0.7) */
        lifted(p, e->position, 250.0f);
        call_effect_ks(env, e, 0x702, p, e->angle, light, 0, MU_SFX_NO_OWNER, 0xffff, 1.5f);
        lifted(p, e->position, 250.0f);
        call_effect_ks(env, e, 0x702, p, e->angle, light, 0, MU_SFX_NO_OWNER, 0xffff, 2.0f);
        call_effect_ks(env, e, 0x707, e->position, e->angle, e->light, 0, MU_SFX_NO_OWNER, 0xffff, F_0_8);
        const float z = e->position[2];
        set3(e->angle, 0.0f, 0.0f, 0.0f);
        set3(light, F_0_8, F_0_8, 1.0f);
        e->position[2] = e->position[2] + 350.0f;
        for (int k = 0; k < 3; ++k) {              /* three rings 02 stacked 100 apart */
            if (k)
                e->position[2] = e->position[2] + 100.0f;
            call_effect_ks(env, e, 0x701, e->position, e->angle, light, 1, MU_SFX_NO_OWNER, 0xffff,
                           f32bits(0x3fe66666u));  /* 1.8 */
        }
        e->position[2] = z;
        call_sound(env, e, 0x55d);   /* rain sound */
        e->field_64 = 0;                           /* 0x01419549: the arrows' landing-sound flag */
        return 1;
    }
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
    case 0x70a:
        rain_move(e, env);
        return;
    case 0x700: case 0x701: case 0x702:
        if (e->subtype == 0) {                     /* grow, fade and sink; dead once the alpha is spent */
            if (!(0.0f < e->alpha) && !isnan(e->alpha))
                kill_effect(env, e);               /* SetLive(o, 0) 0x0129f4a5 */
            e->scale = e->scale + (e->type == 0x702 ? F_0_1 : f32bits(0x3cf5c28fu));   /* 0.1 / 0.03 */
            e->alpha = e->alpha - f32bits(0x3d4ccccdu);   /* 0.05 */
        } else {                                   /* grow by the argument over life0 and pulse */
            e->scale = e->scale_arg / (float)e->field_70 + e->scale;
            float t = (float)e->field_70 - (float)(int32_t)((uint32_t)e->lifetime << 1);
            t = 0.0f > t ? -t : t;
            e->alpha = (float)pow((double)(1.0f - t / (float)e->field_70), 2.0);
        }
        e->position[2] = e->position[2] - 3.0f; /* ring sink */
        return;
    case 0x707:                                    /* turns 5 a step and pulses */
        e->angle[2] = e->angle[2] + 5.0f;
        e->alpha = ring_pulse(e);
        return;
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

/* ---------------------------------------------------------------- RENDER-EFFECTS-015: RenderEffects' decals */

static mu_sfx_render_op *render_op(mu_sfx_render_op *out, int *n, int32_t routine, int32_t argument)
{
    mu_sfx_render_op *op = &out[(*n)++];
    memset(op, 0, sizeof *op);
    op->routine = routine;
    op->argument = argument;
    return op;
}

/* RenderTerrainAlphaBitmap(texture, x, y, size, size, light, rotation, alpha, 5, 1, 0) */
static void render_decal(mu_sfx_render_op *out, int *n, const mu_sfx_effect *e, int32_t texture, float size,
                         const float light[3], float rotation, float alpha)
{
    mu_sfx_render_op *op = render_op(out, n, MU_SFX_RENDER_DECAL, 0);
    op->texture = texture;
    op->x = e->position[0];
    op->y = e->position[1];
    op->size_x = op->size_y = size;
    copy3(op->light, light);
    op->rotation = rotation;
    op->alpha = alpha;
    op->height = 5.0f;
    op->follow = 1;
}

static void scaled3(float out[3], float r, float g, float b, float s)
{
    out[0] = r * s;
    out[1] = g * s;
    out[2] = b * s;
}

int mu_sfx_effect_render_ops(const mu_sfx_effect *e, float world_time, mu_sfx_render_op out[MU_SFX_RENDER_OPS])
{
    int n = 0;
    float light[3];
    const float r7 = f32bits(0x3f333333u);                 /* 0.7 */
    if (e->type == 0x45e && e->subtype >= 3 && e->subtype <= 7) {   /* 0x0151919b: PoundingBall under the arrow */
        render_op(out, &n, MU_SFX_RENDER_BLEND_ADD, 0);
        set3(light, F_0_3, F_0_3, F_0_3);
        render_decal(out, &n, e, 0x8002, 2.0f, light, world_time, 1.0f);
    } else if (e->type == 0x70a) {                          /* 0x0152dc88: empact01, enemy_ring02, ... */
        render_op(out, &n, MU_SFX_RENDER_BLEND_ADD, 0);
        scaled3(light, r7, 0.5f, F_0_4, e->alpha);
        render_decal(out, &n, e, 0x8070, 2.0f, light, 0.0f, 1.0f);
        scaled3(light, r7, 0.5f, F_0_4, e->alpha);
        render_decal(out, &n, e, 0x7f87, 3.0f, light, 0.0f, 1.0f); /* rain ring */
        if (e->lifetime <= 10) {                            /* the last ten steps widen by +0xd8 */
            const float d = e->field_d8;
            scaled3(light, r7, 0.5f, F_0_4, 1.0f - d * F_0_1);
            render_decal(out, &n, e, 0x8147, d * 0.5f + 0.5f, light, 0.0f, 1.0f);
            scaled3(light, r7, 0.5f, F_0_4, 1.0f - d * f32bits(0x3e19999au));   /* 0.15 */
            render_decal(out, &n, e, 0x824c, d * F_0_2 + 2.0f, light, 0.0f, 1.0f);
            scaled3(light, r7, 0.5f, F_0_4, 1.0f - d * F_0_2);
            render_decal(out, &n, e, 0x8070, d * f32bits(0x3e19999au) + 2.0f, light, 0.0f, 1.0f);
        }
        scaled3(light, 0.75f, 0.75f, F_0_8, e->alpha);
        render_decal(out, &n, e, 0x8078, 4.0f, light, 0.0f, 1.0f);   /* lightmarks */
        render_op(out, &n, MU_SFX_RENDER_BLEND_OFF, 0);
    } else if (e->type == 0x70c && e->subtype == 0) {       /* 0x0152e296: the crater, then the flash while young */
        render_op(out, &n, MU_SFX_RENDER_BLEND_ALPHA, 1);
        render_decal(out, &n, e, 0x7fe9, 2.25f, e->light, e->angle[2], e->light[0]);
        render_op(out, &n, MU_SFX_RENDER_BLEND_OFF, 0);
        render_op(out, &n, MU_SFX_RENDER_BLEND_ADD, 0);
        if (e->lifetime > 30) {                             /* landing flash */
            scaled3(light, r7, 0.75f, 1.0f, e->field_d8);
            render_decal(out, &n, e, 0x810a, 1.0f, light, 0.0f, 1.0f);
            scaled3(light, 1.0f, 1.0f, 1.0f, e->field_d8);
            render_decal(out, &n, e, 0x8155, 1.0f, light, 0.0f, 1.0f);
            scaled3(light, r7, 0.75f, f32bits(0x3f59999au), e->alpha);   /* 0.85 */
            render_decal(out, &n, e, 0x8179, e->scale * 2.0f, light, 0.0f, 1.0f);
            scaled3(light, r7, f32bits(0x3f19999au), F_0_8, e->alpha);   /* 0.6 */
            render_decal(out, &n, e, 0x8013, e->scale * 3.5f, light, e->angle[2], 1.0f);
        }
        render_op(out, &n, MU_SFX_RENDER_BLEND_OFF, 0);
    }
    return n;
}

/* ---------------------------------------------------------------- RENDER-EFFECTS-016: the wrappers' GL state */

static void gl_cap(uint8_t *cache, uint8_t *gl, uint8_t on)
{   /* the wrappers' cached glEnable/glDisable: movzx, test; a call only when the byte is zero (enable) or
     * non-zero (disable) */
    if (on ? *cache == 0 : *cache != 0) {
        *cache = on;
        *gl = on;
    }
}

static void gl_blend_func(mu_sfx_gl_state *s, int32_t id, uint32_t src, uint32_t dst)
{
    if (s->blend != id) {                                   /* 0x0184a993 / 0x0184aa2e */
        s->blend = id;
        s->gl_blend = 1;
        s->gl_src = src;
        s->gl_dst = dst;
    }
}

int mu_sfx_render_state(mu_sfx_gl_state *s, int32_t routine, int32_t argument)
{
    switch (routine) {
    case MU_SFX_RENDER_BLEND_ADD:                           /* 0x0184aa2b */
        gl_blend_func(s, 3, 1u, 1u);
        gl_cap(&s->cull, &s->gl_cull, 0);                   /* 0x0184a720 */
        gl_cap(&s->depth_mask, &s->gl_depth_mask, 0);       /* 0x0184a763 */
        gl_cap(&s->alpha_test, &s->gl_alpha_test, 0);
        gl_cap(&s->texture, &s->gl_texture, 1);
        if (s->fog_flag)
            s->gl_fog = 0;
        return 1;
    case MU_SFX_RENDER_BLEND_ALPHA:                         /* 0x0184a990 */
        gl_blend_func(s, 2, 0x0302u, 0x0303u);
        gl_cap(&s->cull, &s->gl_cull, 0);
        if ((uint8_t)argument)                              /* movzx byte [ebp+8] */
            gl_cap(&s->depth_mask, &s->gl_depth_mask, 1);   /* 0x0184a743 */
        gl_cap(&s->alpha_test, &s->gl_alpha_test, 1);
        gl_cap(&s->texture, &s->gl_texture, 1);
        if (s->fog_flag)
            s->gl_fog = 1;
        return 1;
    case MU_SFX_RENDER_BLEND_OFF:                           /* 0x0184a7f3 */
        if (s->blend != 0) {
            s->blend = 0;
            s->gl_blend = 0;
        }
        gl_cap(&s->cull, &s->gl_cull, 1);                   /* 0x0184a6fd */
        gl_cap(&s->depth_mask, &s->gl_depth_mask, 1);
        gl_cap(&s->alpha_test, &s->gl_alpha_test, 0);
        gl_cap(&s->texture, &s->gl_texture, 1);
        if (s->fog_flag)
            s->gl_fog = 1;
        return 1;
    default:
        return 0;
    }
}
