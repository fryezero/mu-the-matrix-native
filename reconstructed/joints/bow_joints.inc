/* RENDER-EFFECTS-012: bounded bow trails. Included before CreateJoint.
 * Addresses and remaining kinds: docs/research/client-render-effects-012.md. */
static int bow_joint_kind(int32_t type, int32_t sub)
{
    switch (type) {
    case 0x80e3: return sub == 4 || sub == 5;
    case 0x80e4: return sub == 1;
    case 0x814c: case 0x8182: case 0x8185: return sub == 10;
    case 0x85cc: return sub == 0;
    case 0x828c: return sub == 2;
    case 0x7f79: return sub == 12 || sub == 14 || sub == 15 || sub == 18 || sub == 22;
    case 0x7f78: return sub == 11;   /* RENDER-EFFECTS-014: 0x459's guided flares */
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
        if (j->subtype == 5) j->velocity = 70.0f;
        j->field_a25 = 2;
        if (j->subtype == 4) {
            j->light[0] = 0.4f; j->light[1] = 0.9f; j->light[2] = 1.0f;
        } /* 0x01550963: subtype 5 preserves caller colour, or common white */
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
        if (j->subtype == 15) j->max_tails = 16;
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
        if (j->subtype == 15) { /* 0x0154ceaa */
            j->light[0] = 0.4f; j->light[1] = 0.9f; j->light[2] = 0.5f;
        } else if (j->subtype == 14) { /* 0x0154ce29: white, otherwise as /15 */
            j->light[0] = j->light[1] = j->light[2] = 1.0f;
            j->max_tails = 16;
        } else if (j->subtype == 12) {
            j->light[0] = 0.6f; j->light[1] = 0.2f; j->light[2] = 0.8f;
        } else if (j->subtype == 22) {
            j->light[0] = 1.0f; j->light[1] = 0.2f; j->light[2] = 0.0f;
        }
        copy3(j->target_position, target_position);
        break;
    case 0x7f78: /* 0x015496cb, subtype 0xb at 0x0154b471 */
        j->velocity = 0.0f;
        j->light[0] = 0.2f; j->light[1] = 0.2f; j->light[2] = 1.0f; /* Flare/b */
        j->phase = 0;
        j->lifetime = 30; /* Flare/b */
        j->max_tails = 15; /* Flare/b */
        j->jitter[0] = (float)imod(jrand(env), 3000);
        j->scale = 30.0f; /* Flare/b */
        copy3(j->target_position, target_position);
        break;
    }
}

/* 0x01579b40..0x0157ab78 with 0x0157c24e, Flare/b of the arrow 0x459: the head rides the ambient clock's
 * pseudo-random direction from the target point, blended toward the owner's +0x110 point plus a cosine
 * wobble. The joint created with skill 1 carries its arrow: it writes the owner's position and runs
 * CheckClientArrow (one report). A null or dead owner goes straight to the tail. */
static void move_flare_orbit(mu_jt_joint *j, const mu_jt_env *env, int32_t index)
{
    const mu_jt_object *t = jobject(env, j->target);
    if (!t) return;   /* 0x01579b64 */
    if (!t->live) { j->live = 0; j->lifetime = -1; return; }   /* 0x01579b7b */
    const int32_t clock = env ? env->ambient_clock : 0;
    const uint32_t c = (uint32_t)index * 0xd1e3u + (uint32_t)(index % 2 != 0 ? clock : -(int64_t)clock);
    float v[3] = {f32bits(0x3d449ba6u), f32bits(0x3d7b15b5u), f32bits(0x3de3f141u)};   /* 0x01acd974 */
    for (int k = 0; k < 3; ++k) v[k] = v[k] * 1.5f; /* Flare/b rates */
    const float a = (float)(int32_t)(c + 0xd903u) * v[0];
    const float b = (float)(int32_t)c * v[1];
    const float e = (float)(int32_t)(c + 0x2b67u) * v[2];
    const float r0 = fsin(a) * fcos(b), r1 = fsin(a) * fsin(b), r2 = fcos(a);
    const float s = fsin(e), co = fcos(e);
    float d[3];
    d[2] = r0;
    d[1] = s * r1 + co * r2;
    d[0] = co * r1 - s * r2;
    const float q = (float)j->lifetime * 40.0f / 30.0f;
    float blend = 20.0f > q ? q * 4.0f : q * 1.0f + 60.0f;
    blend = blend / (float)(int32_t)((uint32_t)j->phase + 30u) * 30.0f;
    if (j->lifetime == 30) {   /* 0x01579f9b: PlayBuffer(0x42, 0, 0) */
        mu_jt_call c0 = {0};
        c0.routine = MU_JT_CALL_SOUND; c0.type = 0x42; c0.owner = -1;
        jcall(env, &c0);
    }
    float reach = q - 10.0f;
    if (0.0f > reach) reach = 0.0f;
    reach = 150.0f > reach * 5.0f ? reach * 5.0f : 150.0f; /* Flare/b reach */
    for (int k = 0; k < 3; ++k) j->position[k] = d[k] * reach + j->target_position[k];
    for (int k = 0; k < 3; ++k) {
        const int32_t w = (int32_t)((uint32_t)index * 0xc81fu + (uint32_t)k * 0xe7fu + (uint32_t)((int32_t)c / 10));
        const float pull = (100.0f - blend) * (fcos((float)w * 0.01f) * 25.0f + t->impact[k]);
        j->position[k] = (blend * j->position[k] + pull) * 0.01f;
    }
    const float light[3] = {0.3f, 0.3f, 0.5f}; /* Flare/b sprites */
    if (j->skill == 1) {   /* 0x0157a6cb: owner position = head, then CheckClientArrow 0x013bd374 */
        mu_jt_call c1 = {0};
        c1.routine = MU_JT_CALL_CHECK_ARROW; c1.owner = j->target;
        copy3(c1.position, j->position);
        jcall(env, &c1);
    }
    static const int32_t bitmaps[3] = {0x7f67, 0x7ef7, 0x7ef7};
    for (int n = 0; n < 3; ++n) {   /* 0x0157a942: Shiny02 and two flare01 sprites on the owner */
        mu_jt_call c2 = {0};
        c2.routine = MU_JT_CALL_SPRITE; c2.type = bitmaps[n];
        c2.angle[0] = (float)imod(jrand(env), 360);
        c2.scale = (float)(imod(jrand(env), 2) + 8) * (n == 0 ? F_0_1 : f32bits(0x3e3851ecu));
        copy3(c2.position, j->position); copy3(c2.light, light);
        c2.owner = j->target; c2.subtype = 0; c2.range = 4;
        jcall(env, &c2);
    }
    /* 0x0157c24e: subtypes 5, 7 and 0xb skip the last-ten-steps fade */
}

/* Returns 1 only for the early return which omits MoveJoint's closing tail shift, 2 to go straight to it. */
static int move_bow_joint(mu_jt_joint *j, const mu_jt_env *env, int32_t index)
{
    const mu_jt_object *t = jobject(env, j->target);
    if (j->type == 0x7f78) {
        move_flare_orbit(j, env, index);
        return 2;
    }
    if (j->type == 0x80e3) { /* 0x01583f63 */
        if (j->subtype == 4) {
            if (!t || !t->live) j->lifetime = 0;
        } else if (!t || !t->live || t->lifetime <= 0) {
            j->lifetime = 0;
            if (j->subtype == 5) j->live = 0; /* 0x01583f8d; closing tail still runs */
        }
    } else if (j->type == 0x80e4) { /* 0x01584164 */
        if (!t || !t->live) { j->live = 0; return 1; }
    } else if (j->type == 0x828c) { /* 0x01585972 */
        if (!t || !t->live) j->live = 0;
        else {
            float m[12], d[3];
            const float down[3] = {0.0f, -1.0f, 0.0f};
            mu_angle_matrix(j->angle, m);
            mu_vector_rotate(down, m, d);
            /* AngleToVector calls 0x00cff0d3: divide each component by the float length.
             * normalize3's reciprocal multiplication is a different client helper (0x00cfd15f). */
            const float length = sqrtf(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
            for (int k = 0; k < 3; ++k) {
                d[k] = F_TINY > length ? 0.0f : d[k] / length;
                j->position[k] = t->position[k] + d[k] * 15.0f;
            }
        }
    } else if (j->type == 0x7f79) { /* 0x0157d2f5 */
        if (!t) { j->live = 0; return 0; }
        if (!t->live) j->live = 0;
        if (j->subtype == 14 && j->live == 1) { /* 0x0157d395: Spark03 sprite, red smoke, sparks */
            mu_jt_call c = {0};
            c.routine = MU_JT_CALL_SPRITE; c.type = 0x7f26; c.scale = 5.0f; c.owner = -1; c.range = 4;
            copy3(c.position, j->position); copy3(c.light, j->light);
            jcall(env, &c);
            memset(&c, 0, sizeof c);
            c.routine = MU_JT_CALL_PARTICLE; c.type = 0x7f5a; c.owner = -1; c.scale = 1.0f;
            copy3(c.position, j->position); copy3(c.angle, j->angle); copy3(c.light, j->light);
            c.subtype = 0x22; jcall(env, &c);
            c.subtype = 0x23; jcall(env, &c); /* Flare02/e smoke */
            j->light[0] = 0.7f; j->light[1] = 0.3f; j->light[2] = 0.3f; /* Flare02/e spark colour */
            c.type = 0x7f26; c.subtype = 0xa; c.scale = 4.0f;
            copy3(c.light, j->light);
            jcall(env, &c);
            j->light[0] = 1.0f; j->light[1] = 1.0f; j->light[2] = 0.2f; /* Flare02/e after */
        }
        if (j->subtype == 15 && j->live == 1) { /* 0x0157d54d: two particles, before fade */
            mu_jt_call c = {0};
            c.routine = MU_JT_CALL_PARTICLE; c.type = 0x7f66;
            c.subtype = 3; c.owner = -1; c.scale = 0.5f;
            copy3(c.position, j->position); copy3(c.angle, j->angle); copy3(c.light, j->light);
            for (int n = 0; n < 2; ++n) jcall(env, &c);
        }
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
