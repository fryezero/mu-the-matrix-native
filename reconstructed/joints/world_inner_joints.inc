/* RENDER-EFFECTS-031: Remain joints, original create 0x015462ac/0x0154646c/0x015465ba,
 * move 0x01570fd4/0x015714b8/0x01571923. Common allocation/tail/render remain shared. */
static int world_inner_joint_kind(int32_t type, int32_t sub)
{
    return (type == 0x7f7d && sub >= 8 && sub <= 10) || (type == 0x7fd5 && sub == 5);
}

static void create_world_inner_joint(mu_jt_joint *j, float scale, const float target[3], const mu_jt_env *env)
{
    if (j->type == 0x7fd5) { /* 0x01543595 */
        j->scale = 2.0f;
        j->velocity = (float)(jrand(env) % 20 + 6);
        j->lifetime = jrand(env) % 8 + 8;
        j->max_tails = 2;
        j->light[0] = 0.7f; j->light[1] = j->light[2] = 0.1f;
        return;
    }
    j->scale = scale;
    j->tex_type = MU_JT_BITMAP_THUNDER;
    j->max_tails = 50;
    j->lifetime = 20;
    j->tail_update = 0;
    if (j->subtype == 8) {
        j->position[0] = (float)(jrand(env) % 10 - 5) + j->position[0];
        j->position[1] = (float)(jrand(env) % 10 - 5) + j->position[1];
        j->position[2] = j->position[2] + 1100.0f;
    } else if (j->subtype == 9) j->position[0] = j->position[0] - 50.0f;
    else j->position[1] = j->position[1] - 350.0f;
    j->angle[0] = j->angle[1] = j->angle[2] = 0.0f;
    copy3(j->target_position, target);
    copy3(j->start, j->position);
}

static void move_world_inner_joint(mu_jt_joint *j, const mu_jt_env *env)
{
    if (j->type == 0x7fd5) return; /* common forward movement and closing tail only */
    copy3(j->position, j->start);
    float m[12];
    mu_angle_matrix(j->angle, m);
    for (int32_t n = 0; n < j->max_tails - 5; ++n) {
        if (j->subtype == 8) {
            j->position[0] = (float)(jrand(env) % 10 - 5) + j->position[0];
            j->position[1] = (float)(jrand(env) % 10 - 5) + j->position[1];
            j->position[2] = j->position[2] - 20.0f;
        } else if (j->subtype == 9) j->position[0] = j->position[0] + 21.0f;
        else j->position[1] = j->position[1] + 20.0f;
        mu_jt_tail_shift(j, m);
    }
    float step[3];
    for (int k = 0; k < 3; ++k) step[k] = F_0_2 * (j->target_position[k] - j->position[k]);
    for (int32_t n = j->max_tails - 5; n < j->max_tails - 1; ++n) {
        for (int k = 0; k < 3; ++k) j->position[k] = j->position[k] + step[k];
        const int range = j->subtype == 8 ? 10 : 20;
        const int first_axis = j->subtype == 9 ? 1 : 0;
        const int other_axis = j->subtype == 8 ? 1 : 2;
        j->position[first_axis] = (float)(jrand(env) % range - range / 2) + j->position[first_axis];
        j->position[other_axis] = (float)(jrand(env) % range - range / 2) + j->position[other_axis];
        mu_jt_tail_shift(j, m);
    }
    copy3(j->position, j->target_position);
    mu_jt_tail_shift(j, m);
    if (j->lifetime < 4)
        for (int k = 0; k < 3; ++k) j->light[k] = j->light[k] / F_1_2;
}
