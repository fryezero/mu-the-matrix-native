/* RENDER-ITEMS-002U: the two kinds the wing pre-draw programs create (0x22ec, 0x248f; RENDER-ITEMS-002S),
 * CreateJoint 0x7f7c subtype 0xe (0x01544f3d) and 0x7fd3 subtype 4 (0x01540b34). Included by joints.c after
 * the MoveJoint helpers. docs/research/client-joints.md section 12.
 *
 * Both creates build a ten-tail streak from the position toward CreateJoint's target position argument (the
 * argument, not +0x58: with a target object the common part leaves +0x58 as the record held it) and end with
 * the head at +0x58; LifeTime 0, so the joint draws once and its first MoveJoint releases it. Neither case
 * reads the target object's fields (the creates only test the pointer, with equal branches). */

static int wing_joint_kind(int32_t type, int32_t subtype)
{
    return (type == MU_JT_BITMAP_THUNDER && subtype == 0xe) || (type == MU_JT_BITMAP_SPIRIT && subtype == 4);
}

/* The shared body of 0x01544f3d / 0x01540b34 (after the kind's prologue: 0x7f7c's scale, 50 tails and
 * velocity 50 at 0x01543f00; 0x7fd3's render type 3 at 0x01540809). */
static void create_wing_streak(mu_jt_joint *j, float scale, const float target_position[3])
{
    if (j->type == MU_JT_BITMAP_SPIRIT)
        j->render_type = 1;   /* 0x01540b37 */
    j->lifetime = 0;
    j->scale = scale;
    j->max_tails = 10;
    j->angle[0] = j->angle[1] = j->angle[2] = 0.0f;
    j->light[0] = F_0_3;
    j->light[1] = F_0_3;
    j->light[2] = 1.0f;
    /* +0x24 (the start field) holds the step: (target argument - position) / max_tails */
    const float n = (float)j->max_tails;
    for (int k = 0; k < 3; ++k)
        j->start[k] = (target_position[k] - j->position[k]) / n;
    float step[3];
    copy3(step, j->start);
    float m[12];
    mu_angle_matrix(j->angle, m);
    for (int32_t i = 0; i < j->max_tails - 1; ++i) {
        step[0] = j->start[0];
        step[1] = j->start[1];
        for (int k = 0; k < 3; ++k)
            j->position[k] = j->position[k] + step[k];
        mu_jt_tail_shift(j, m);
        /* x and y step back and forward again (z keeps the step) */
        j->position[0] = j->position[0] - step[0];
        j->position[0] = j->position[0] + j->start[0];
        j->position[1] = j->position[1] - step[1];
        j->position[1] = j->position[1] + j->start[1];
    }
    copy3(j->position, j->target_position);   /* 0x0154536c / 0x01540f6a */
}

/* MoveHumming 0x012af2f1 returns the length of (position - target) taken before the turn (0x00cfd020: the
 * float sum of squares through the double square root 0x00961a07). */
static float humming_length(const float position[3], float angle[3], const float target[3], float turn)
{
    float d[3] = {position[0] - target[0], position[1] - target[1], position[2] - target[2]};
    move_humming(position, angle, target, turn);
    float sum = d[0] * d[0] + d[1] * d[1];
    sum = sum + d[2] * d[2];
    return (float)sqrt((double)sum);
}

/* MoveJoint 0x7f7c 0xe: the subtype switch 0x0156d391 sends it straight to the loop 0x0156d9ef (no restart
 * from the start); each of max_tails steps turns toward +0x58 (MoveHumming, 25), jitters the angle by
 * (rand % 1024 - 512) / width in x and z (0x0156ed1f), shifts the tails, stops once 1.5 x velocity exceeds the
 * distance (at width 50 first CreateParticle 0x7f2b at the head and, on rand % 8 == 0, 0x7f5a at the head
 * after three discarded rand() offsets, 0x0156ef16..0x0156f0b5), otherwise steps forward. 0x7fd3 4 has no
 * case (0x01568ebe): the head motion and the closing tail shift only. */
static void move_wing_streak(mu_jt_joint *j, const mu_jt_env *env)
{
    if (j->type != MU_JT_BITMAP_THUNDER)
        return;
    for (int32_t i = 0; i < j->max_tails; ++i) {
        const float distance = humming_length(j->position, j->angle, j->target_position, 25.0f);
        j->jitter[0] = (float)(imod(jrand(env), 1024) - 512) / j->scale;
        j->jitter[2] = (float)(imod(jrand(env), 1024) - 512) / j->scale;
        float a[3], m[12];
        for (int k = 0; k < 3; ++k)
            a[k] = j->angle[k] + j->jitter[k];
        mu_angle_matrix(a, m);
        mu_jt_tail_shift(j, m);
        if (j->velocity * 1.5f > distance) {
            if (j->scale == 50.0f) {
                mu_jt_call c;
                memset(&c, 0, sizeof c);
                c.routine = MU_JT_CALL_PARTICLE;
                c.type = 0x7f2b;
                copy3(c.position, j->position);
                copy3(c.angle, j->angle);
                copy3(c.light, j->light);
                c.scale = 1.0f;
                c.owner = -1;
                jcall(env, &c);
                if (imod(jrand(env), 8) == 0) {
                    for (int k = 0; k < 3; ++k)
                        (void)jrand(env);   /* (rand % 64 - 32) + target, computed and never passed */
                    c.type = 0x7f5a;
                    jcall(env, &c);
                }
            }
            return;
        }
        const float v[3] = {0.0f, -j->velocity, 0.0f};
        add_rotated(j, v, m);
    }
}
