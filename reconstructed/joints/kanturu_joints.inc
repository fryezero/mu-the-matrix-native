/* RENDER-JOINTS-001: Kanturu Underground's and Uruk Mountain's lightning (docs/research/client-joints.md
 * section 1). CreateJoint 0x7f7d subtypes 0xc (0x01546828), 0xd (0x01546c21), 0xe (0x01546e03), 0xf (0x015470a7)
 * and 0x7f7c subtype 0x12 (0x01545672); MoveJoint 0x7f7d 0xc/0xd/0xe/0xf (0x01572296, 0x01572665, 0x01572911,
 * 0x01573171) and 0x7f7c 0x12 (0x0156d601, the tail loop 0x0156d9ef..0x0156f5ce). Included after the common
 * helpers. */

/* CreateJoint 0x7f7d 0xc/0xe/0xf after the case head (width = scale, bitmap 0x7f7c). target_position is the
 * argument. Returns 0 when 0xe/0xf return before the tail clamp (width <= 0; NaN goes on). */
static int create_kanturu_bolt(mu_jt_joint *j, const float target_position[3], const mu_jt_env *env)
{
    float m[12], r[3];
    if (j->subtype == 0xc) {
        j->velocity = (float)imod(jrand(env), 20) + 80.0f;
        j->light[2] = (float)j->max_tails;   /* the record's previous tail count */
        j->max_tails = 30;
        j->lifetime = 4;
        j->tail_update = 0;
        copy3(j->start, j->position);
        const float v[3] = {0.0f, j->scale / 1.0f, 0.0f};
        mu_angle_matrix(j->angle, m);
        mu_vector_rotate(v, m, r);
        for (int k = 0; k < 3; ++k)
            r[k] = r[k] * j->scale / 2.0f;
        for (int k = 0; k < 3; ++k)
            j->position[k] = j->position[k] + r[k];
        copy3(j->start, j->position);
        const int32_t a = trunc_i32(j->scale / 4.0f);
        for (int k = 0; k < 3; ++k)
            j->target_position[k] = (float)imod(jrand(env), (int32_t)((uint32_t)a << 1)) + target_position[k] -
                                    (float)a;
        return 1;
    }
    if (j->subtype == 0xd) {   /* the target at R(angle) (0, width, 0); then a width of rand % 10 + 20 */
        j->max_tails = 50;
        j->lifetime = 20;
        j->tail_update = 0;
        const float v[3] = {0.0f, j->scale, 0.0f};
        mu_angle_matrix(j->angle, m);
        mu_vector_rotate(v, m, r);
        copy3(j->start, j->position);
        for (int k = 0; k < 3; ++k)
            j->target_position[k] = j->position[k] + r[k];
        j->scale = (float)imod(jrand(env), 10) + 20.0f;
        return 1;
    }
    if (!(0.0f < j->scale) && !isnan(j->scale))
        return 0;   /* 0x01553637 */
    j->max_tails = 50;
    j->lifetime = 20;
    j->tail_update = 0;
    float v[3] = {0.0f, -1100.0f, 0.0f};
    if (j->subtype == 0xe) {
        const float y = (float)(imod(jrand(env), 10) - 5);
        const float x = (float)(imod(jrand(env), 10) - 5);
        v[0] = x;
        v[1] = y;
        v[2] = 1100.0f;
    }
    mu_angle_matrix(j->angle, m);
    mu_vector_rotate(v, m, r);
    const float k = F_0_028 * j->scale;
    for (int q = 0; q < 3; ++q)
        r[q] = r[q] * k;
    for (int q = 0; q < 3; ++q)
        j->position[q] = j->position[q] + r[q];
    copy3(j->start, j->position);
    copy3(j->target_position, target_position);
    return 1;
}

/* rand() % (int)(span * s) - (int)(half * s) */
static float kanturu_jitter(const mu_jt_env *env, float s, float span, float half)
{
    const int32_t r = jrand(env);
    return (float)(imod(r, trunc_i32(span * s)) - trunc_i32(half * s));
}

/* MoveJoint 0x7f7d 0xd: max_tails - 5 steps of (target - start) / 50 from the start;
 * 0xc: a jittered walk from the start that closes 8% of the gap to the target each step;
 * 0xe/0xf: max_tails - 5 straight steps of 20 * 0.028w toward the target (0xe jittered in x and y), four steps
 * over a fifth of what is left, the last tail at the target; both fade (/1.2) below LifeTime 4. */
static void move_kanturu_bolt(mu_jt_joint *j, const mu_jt_env *env)
{
    float d[3] = {j->target_position[0] - j->start[0], j->target_position[1] - j->start[1],
                  j->target_position[2] - j->start[2]};
    copy3(j->position, j->start);
    float m[12];
    mu_angle_matrix(j->angle, m);
    if (j->subtype == 0xd) {
        for (int32_t i = 0; i < j->max_tails - 5; ++i) {
            for (int k = 0; k < 3; ++k)
                j->position[k] = d[k] / 50.0f + j->position[k];
            mu_jt_tail_shift(j, m);
        }
        if (j->lifetime < 4)
            for (int k = 0; k < 3; ++k)
                j->light[k] = j->light[k] / F_1_2;
        return;
    }
    if (j->subtype == 0xc) {
        for (int32_t i = 0; i < j->max_tails - 1; ++i) {
            const int32_t a = trunc_i32(j->scale / 5.0f);
            for (int k = 0; k < 3; ++k)
                j->position[k] = (float)(imod(jrand(env), (int32_t)((uint32_t)a << 1)) - a) + j->position[k];
            mu_jt_tail_shift(j, m);
            float g[3];
            for (int k = 0; k < 3; ++k)
                g[k] = j->target_position[k] - j->position[k];
            for (int k = 0; k < 3; ++k)
                g[k] = F_0_08 * g[k];
            for (int k = 0; k < 3; ++k)
                j->position[k] = j->position[k] + g[k];
        }
        copy3(j->position, j->target_position);
        mu_jt_tail_shift(j, m);
        return;
    }
    const float s = j->scale * F_0_028;
    normalize3(d);
    const float length = 20.0f * s;
    for (int k = 0; k < 3; ++k)
        d[k] = d[k] * length;
    const int jittered = j->subtype == 0xe;
    int32_t i = 0;
    for (; i < j->max_tails - 5; ++i) {
        for (int k = 0; k < 3; ++k)
            j->position[k] = j->position[k] + d[k];
        if (jittered) {
            const float y = kanturu_jitter(env, s, 10.0f, 5.0f);
            const float x = kanturu_jitter(env, s, 10.0f, 5.0f);
            j->position[0] = j->position[0] + x;
            j->position[1] = j->position[1] + y;
            j->position[2] = j->position[2] + 0.0f;
        }
        mu_jt_tail_shift(j, m);
    }
    float e[3];
    for (int k = 0; k < 3; ++k)
        e[k] = j->target_position[k] - j->position[k];
    for (int k = 0; k < 3; ++k)
        e[k] = F_0_2 * e[k];
    for (i = j->max_tails - 5; i < j->max_tails - 1; ++i) {
        for (int k = 0; k < 3; ++k)
            j->position[k] = j->position[k] + e[k];
        if (jittered) {
            const float y = kanturu_jitter(env, s, 10.0f, 5.0f);
            const float x = kanturu_jitter(env, s, 10.0f, 5.0f);
            j->position[0] = j->position[0] + x;
            j->position[1] = j->position[1] + y;
            j->position[2] = j->position[2] + 0.0f;
        } else {
            /* 0x015735b1: a jitter vector is built and never added (the rand() calls stay) */
            (void)kanturu_jitter(env, s, 20.0f, 10.0f);
            (void)kanturu_jitter(env, s, 20.0f, 10.0f);
        }
        mu_jt_tail_shift(j, m);
    }
    copy3(j->position, j->target_position);
    mu_jt_tail_shift(j, m);
    if (j->lifetime < 4)
        for (int k = 0; k < 3; ++k)
            j->light[k] = j->light[k] / F_1_2;
}

/* MoveJoint 0x7f7c 0x12: from the start, max_tails steps that turn toward the target (MoveHumming, 110),
 * jitter the angle by +-32 in x and z, shift the tails and step forward; at width >= 50 every step also lights
 * the terrain (range 2) with (f/10, f/10, f/2), f = (rand % 4 + 4) * 0.04. */
static void move_thunder_arc(mu_jt_joint *j, const mu_jt_env *env)
{
    copy3(j->position, j->start);
    for (int32_t i = 0; i < j->max_tails; ++i) {
        move_humming(j->position, j->angle, j->target_position, 110.0f);
        j->jitter[0] = (float)(imod(jrand(env), 64) - 32);
        j->jitter[2] = (float)(imod(jrand(env), 64) - 32);
        float a[3], m[12];
        for (int k = 0; k < 3; ++k)
            a[k] = j->angle[k] + j->jitter[k];
        mu_angle_matrix(a, m);
        mu_jt_tail_shift(j, m);
        if (j->scale >= 50.0f) {
            const float f = (float)(imod(jrand(env), 4) + 4) * F_0_04;
            mu_jt_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_JT_CALL_TERRAIN_LIGHT;
            c.position[0] = j->position[0];
            c.position[1] = j->position[1];
            c.light[0] = f * F_0_1;
            c.light[1] = f * F_0_1;
            c.light[2] = f * 0.5f;
            c.range = 2;
            c.owner = -1;
            jcall(env, &c);
        }
        const float v[3] = {0.0f, -j->velocity, 0.0f};
        add_rotated(j, v, m);
    }
}
