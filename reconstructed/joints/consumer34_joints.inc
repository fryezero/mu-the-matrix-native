/* RENDER-EFFECTS-034: joint pairs the world producers already request (Kanturu 37/40's inline hook, Crywolf,
 * Barracks/Refuge, Kalima and tower leaves). CreateJoint 0x0153b02c: 0x7f7c/8 0x0154473a, 0x7f7c/19 0x0154574f,
 * 0x7fd5/4 0x015434ea, 0x7f7d/11 0x01546708. MoveJoint 0x01556c26: 0x7f7c/8 has no case (0x0156d3a9, the head's
 * forward motion only), 0x7f7c/19 shares /18's tail loop 0x0156d9ef with its own turn and jitter (0x0156e071,
 * 0x0156eba0), 0x7fd5/4 0x015698f0, 0x7f7d/11 0x01571d90. RenderJoints draws them with the shared body. */
static int consumer34_joint_kind(int32_t type, int32_t sub)
{
    return (type == MU_JT_BITMAP_THUNDER && (sub == 8 || sub == 19)) || (type == MU_JT_BITMAP_SPARK && sub == 4) ||
           (type == MU_JT_TYPE_THUNDER_BOLT && sub == 11);
}

static void create_consumer34_joint(mu_jt_joint *j, float scale, const float target_position[3], const mu_jt_env *env)
{
    if (j->type == MU_JT_BITMAP_SPARK) {             /* 0x015434ea */
        j->scale = scale * 2.0f + 4.0f;
        j->velocity = (float)(jrand(env) % 5 + 4);
        j->lifetime = jrand(env) % 10 + 8;
        j->max_tails = 4;
        j->light[0] = 1.0f;
        j->light[1] = j->light[2] = F_0_2;
        return;
    }
    if (j->type == MU_JT_TYPE_THUNDER_BOLT) {        /* 0x01545bdf, subtype 0xb 0x01546708 */
        j->scale = scale;
        j->tex_type = MU_JT_BITMAP_THUNDER;
        j->velocity = (float)(jrand(env) % 20) + 80.0f;
        j->light[2] = j->light[2] + F_0_2;
        j->lifetime = 5;
        j->max_tails = 30;
        copy3(j->start, j->position);
        copy3(j->target_position, target_position);
        return;
    }
    j->scale = scale;                                /* 0x01543f1a: the type's head */
    j->max_tails = 50;
    j->velocity = 50.0f;
    if (j->subtype == 8) {                           /* 0x0154473a */
        j->scale = 5.0f;
        j->velocity = (float)(jrand(env) % 10 + 6);
        j->lifetime = jrand(env) % 8 + 8;
        j->max_tails = 2;
        j->light[0] = j->light[1] = j->light[2] = 1.0f;
        return;
    }
    j->max_tails = 30;                               /* 0x0154574f */
    j->lifetime = 2;
    j->velocity = j->scale * 3.0f;
    copy3(j->start, j->position);
}

static void move_consumer34_joint(mu_jt_joint *j, const mu_jt_env *env)
{
    float m[12];
    if (j->type == MU_JT_BITMAP_SPARK) {             /* 0x015698f0 */
        j->velocity = j->velocity + F_0_1;
        j->light[0] = j->light[0] / f32bits(0x3f8ccccdu);   /* 1.1 */
        j->light[1] = j->light[0];
        j->light[2] = j->light[0];
        return;
    }
    if (j->type == MU_JT_TYPE_THUNDER_BOLT) {        /* 0x01571d90 */
        /* The straight run fixes the far end; the drawn bolt repeats it with a jitter of +-(int)(width / 8).
         * A width below 8 divides by zero in the client; imod returns 0 there. */
        float r[3];
        const float v[3] = {0.0f, j->scale / f32bits(0x3fa66666u), 0.0f};   /* 1.3 */
        copy3(j->position, j->start);
        mu_angle_matrix(j->angle, m);
        mu_vector_rotate(v, m, r);
        for (int32_t i = 0; i < j->max_tails - 5; ++i) {
            for (int k = 0; k < 3; ++k) j->position[k] = j->position[k] + r[k];
            mu_jt_tail_shift(j, m);
            copy3(j->target_position, j->position);
        }
        copy3(j->position, j->start);
        for (int32_t i = 0; i < j->max_tails - 5; ++i) {
            for (int k = 0; k < 3; ++k) j->position[k] = j->position[k] + r[k];
            const int32_t a = trunc_i32(j->scale / 8.0f);
            for (int k = 0; k < 3; ++k)
                j->position[k] = (float)(imod(jrand(env), (int32_t)((uint32_t)a << 1)) - a) + j->position[k];
            mu_jt_tail_shift(j, m);
        }
        copy3(j->position, j->target_position);
        mu_jt_tail_shift(j, m);
        return;
    }
    if (j->subtype == 8)
        return;
    /* 0x7f7c/19: /18's arc with a turn of width + 25, an angle jitter of +-512 / width on all three axes and no
     * terrain light */
    copy3(j->position, j->start);
    for (int32_t i = 0; i < j->max_tails; ++i) {
        move_humming(j->position, j->angle, j->target_position, 25.0f + j->scale);
        for (int k = 0; k < 3; ++k)
            j->jitter[k] = (float)(imod(jrand(env), 1024) - 512) / j->scale;
        float a[3];
        for (int k = 0; k < 3; ++k)
            a[k] = j->angle[k] + j->jitter[k];
        mu_angle_matrix(a, m);
        mu_jt_tail_shift(j, m);
        /* 0x0156f2ba: no terrain light for this subtype, whatever the width */
        const float v[3] = {0.0f, -j->velocity, 0.0f};
        add_rotated(j, v, m);
    }
}
