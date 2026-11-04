/* RENDER-EFFECTS-011: the bows' effects, included by skill_fx.c after pet_fx.inc. CreateEffect's cases and
 * MoveEffect's cases (both end in the common code of skill_fx.c):
 *   0x477/3, 0x477/4  the arrows of 0x45b/0x47f/0x60d: a widening ring (create 0x013d9444, subtypes 2..4
 *                     0x013d97f4; move 0x014719f8 / 0x01471ac0)
 *   0x60b/0           0x60a's burst (create 0x014001e3, move 0x01468a1f)
 *   0x611/0           0x610's ring (create 0x0140fea0, move 0x014c4c8e) */

static int bow_effect_kind(int32_t type, int32_t sub)
{
    return (type == 0x477 && (sub == 3 || sub == 4)) || (type == 0x60b && sub == 0) || (type == 0x611 && sub == 0);
}

static int bow_effect_create(mu_sfx_effect *e, const float angle_arg[3], float scale, const mu_sfx_info *info)
{
    switch (e->type) {
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
