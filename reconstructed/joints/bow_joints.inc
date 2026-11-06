/* RENDER-EFFECTS-012: bounded bow trails. Included before CreateJoint.
 * Addresses and remaining kinds: docs/research/client-render-effects-012.md. */
static int bow_joint_kind(int32_t type, int32_t sub)
{
    switch (type) {
    case 0x80e3: return sub == 4;
    case 0x80e4: return sub == 1;
    case 0x814c: case 0x8182: case 0x8185: return sub == 10;
    case 0x85cc: return sub == 0;
    case 0x828c: return sub == 2;
    case 0x7f79: return sub == 12 || sub == 18 || sub == 22;
    default: return 0;
    }
}

static void create_bow_joint(mu_jt_joint *j, float scale, const float target_position[3], const mu_jt_env *env)
{
    j->scale = scale;
    j->lifetime = 20;
    j->max_tails = 8;
    j->velocity = 70.0f;
    switch (j->type) {
    case 0x80e3: /* 0x015508d2 */
        j->velocity = 40.0f;
        j->field_a25 = 2;
        j->light[0] = 0.4f; j->light[1] = 0.9f; j->light[2] = 1.0f;
        break;
    case 0x80e4: /* 0x01550adc */
        j->faces = 2;
        j->light[0] = j->light[1] = 0.6f; j->light[2] = 1.0f;
        break;
    case 0x814c: case 0x8182: case 0x8185: /* 0x01550ec2, 0x015510b7, 0x01551101 */
        j->faces = 2;
        j->velocity = 60.0f;
        j->lifetime = 30;
        j->max_tails = j->type == 0x814c ? 8 : 10;
        break;
    case 0x85cc: /* 0x0154c01c */
        j->field_a25 = 5;
        copy3(j->target_position, target_position);
        break;
    case 0x828c: /* 0x015516c3 */
        j->max_tails = 6;
        j->num_tails = -1;
        j->field_a25 = 2;
        break;
    case 0x7f79: /* 0x0154c119, 0x0154cd27, 0x0154d03b, 0x0154d26f */
        j->lifetime = (int16_t)j->key;
        j->key = 0;
        j->max_tails = j->subtype == 12 ? 16 : j->subtype == 18 ? 7 : 9;
        j->render_type = j->subtype == 12 ? 4 : 1;
        if (j->subtype == 18 && !(env && env->has_creation_light)) {
            if (j->skill == 0) j->light[0] = j->light[1] = j->light[2] = 0.5f;
            else if (j->skill == 1) {
                j->light[0] = 1.0f; j->light[1] = 0.5f; j->light[2] = 0.0f;
            } else if (j->skill == 3) {
                const mu_jt_object *t = jobject(env, j->target);
                if (t) copy3(j->light, t->light);
            }
        }
        if (j->subtype == 12) {
            j->light[0] = 0.6f; j->light[1] = 0.2f; j->light[2] = 0.8f;
        } else if (j->subtype == 22) {
            j->light[0] = 1.0f; j->light[1] = 0.2f; j->light[2] = 0.0f;
        }
        copy3(j->target_position, target_position);
        break;
    }
}

/* Returns 1 only for the early return which omits MoveJoint's closing tail shift. */
static int move_bow_joint(mu_jt_joint *j, const mu_jt_env *env)
{
    const mu_jt_object *t = jobject(env, j->target);
    if (j->type == 0x80e3) { /* 0x01583f63 */
        if (!t || !t->live) j->lifetime = 0;
    } else if (j->type == 0x80e4) { /* 0x01584164 */
        if (!t || !t->live) { j->live = 0; return 1; }
    } else if (j->type == 0x828c) { /* 0x01585972 */
        if (!t || !t->live) j->live = 0;
        else {
            float m[12], d[3];
            const float down[3] = {0.0f, -1.0f, 0.0f};
            mu_angle_matrix(j->angle, m);
            mu_vector_rotate(down, m, d);
            normalize3(d);
            for (int k = 0; k < 3; ++k) j->position[k] = t->position[k] + d[k] * 15.0f;
        }
    } else if (j->type == 0x7f79) { /* 0x0157d2f5 */
        if (!t) { j->live = 0; return 0; }
        if (!t->live) j->live = 0;
        if (j->lifetime < 15)
            for (int k = 0; k < 3; ++k) j->light[k] = j->light[k] / 1.2f;
        if (j->subtype != 18) {
            const float l = (float)(imod(jrand(env), 4) + 8) * 0.03f;
            mu_jt_call c = {0};
            c.routine = MU_JT_CALL_TERRAIN_LIGHT;
            c.range = 2;
            c.position[0] = j->position[0]; c.position[1] = j->position[1];
            c.light[0] = l * 0.4f; c.light[1] = l; c.light[2] = l * 0.8f;
            jcall(env, &c);
        }
    } else { /* 0x01584f62, 0x015853fb, 0x0157c4e8 */
        if (!t || !t->live) j->live = 0;
    }
    return 0;
}
