/* RENDER-EFFECTS-007: the bow arrows other than Arrow01 (0x43c..0x617), included by skill_fx.c.
 * CreateEffect's shared arrow body 0x013cb34d..0x013cd66f with the separate bodies of 0x471/0x458
 * (0x013ca9f2, 0x013cac12), 0x459 (0x013cae32), 0x442 (0x013ce0de) and 0x474 (0x013d8da1), and
 * their MoveEffect cases. See docs/research/client-render-effects-007.md. */

/* 0x013bce8f: the skills whose arrows keep their angle and height (no bow offset, no turn). */
static int arrow_straight_skill(uint16_t skill)
{
    return skill == 0x2d7 || skill == 0x7e7 || skill == 0x7fc || skill == 0x7fd || skill == 0x7fe;
}

/* The arrow types reconstructed here and the subtypes CreateArrow passes (0, 2 for 0x34/0x1a0, 0x63 for flag 2).
 * 0x615 and 0x617 are not: their MoveEffect cases place sprites at model bones looked up by name
 * (0x0129f18a "Line003", 0x012bd35a "red_01"), which no native service answers. */
static int arrow_kind(int32_t type)
{
    switch (type) {
    case 0x43c: case 0x43d: case 0x43e: case 0x43f: case 0x440: case 0x441: case 0x442: case 0x443:
    case 0x458: case 0x459: case 0x45a: case 0x45b: case 0x45c: case 0x45d: case 0x45e:
    case 0x471: case 0x474: case 0x47f: case 0x525: case 0x5b0: case 0x5b1:
    case 0x60a: case 0x60d: case 0x60e: case 0x60f: case 0x610: case 0x612: case 0x613: case 0x614: case 0x616:
        return 1;
    default:
        return 0;
    }
}

int mu_sfx_is_arrow(int32_t type)
{
    return type == MU_SFX_MODEL_ARROW || arrow_kind(type);
}

static int arrow_supported(int32_t type, int32_t sub)
{
    if (type == MU_SFX_MODEL_ARROW)
        return sub == 0 || sub == 2 || sub == 0x63;
    return arrow_kind(type) && (sub == 0 || sub == 2 || sub == 0x63);
}

/* CreateEffect 0x013c0eaa with its info key (argument 6) and scale (argument 10). */
static void call_effect_ks(const mu_sfx_env *env, mu_sfx_effect *e, int32_t type, const float position[3],
                           const float angle[3], const float light[3], int32_t subtype, int32_t owner, uint16_t key,
                           float scale)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_EFFECT;
    c.type = type;
    c.subtype = subtype;
    c.owner = owner;
    c.range = key;
    c.scale = scale;
    copy3(c.position, position);
    copy3(c.angle, angle);
    copy3(c.light, light);
    env_call(env, &c, e);
}

/* CreateJoint 0x0153b02c(type, pos, target pos, angle, sub, this effect, scale, arg7, arg8, 0, -1, light, -1, 0). */
static void call_joint_args(const mu_sfx_env *env, mu_sfx_effect *e, int32_t type, const float position[3],
                            const float target[3], const float angle[3], int32_t subtype, float scale, int32_t arg7,
                            int32_t arg8, const float *light)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_JOINT;
    c.type = type;
    c.subtype = subtype;
    c.owner = -2;
    c.scale = scale;
    c.arg7 = arg7;
    c.arg8 = arg8;
    copy3(c.position, position);
    copy3(c.target, target);
    copy3(c.angle, angle);
    if (light)
        copy3(c.light, light);
    env_call(env, &c, e);
}

/* CreateSprite 0x01692eb7(bitmap, pos, scale, light, this effect, rotation, 0, 4, ...). */
static void call_sprite(const mu_sfx_env *env, mu_sfx_effect *e, int32_t bitmap, const float position[3], float scale,
                        const float light[3], float rotation)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_SPRITE;
    c.type = bitmap;
    c.scale = scale;
    c.owner = -2;
    c.range = 4;
    c.angle[0] = rotation;
    copy3(c.position, position);
    copy3(c.light, light);
    env_call(env, &c, e);
}

static void set3(float v[3], float x, float y, float z)
{
    v[0] = x;
    v[1] = y;
    v[2] = z;
}

/* VectorRotate(v, AngleMatrix(angle)) */
static void rotate_by(const float v[3], const float angle[3], float out[3])
{
    float m[12];
    mu_angle_matrix(angle, m);
    mu_vector_rotate(v, m, out);
}

/* The 0x46c effect that follows an arrow of subtype 2 (and its own hit test). */
static void arrow_trail(const mu_sfx_env *env, mu_sfx_effect *e)
{
    call_effect_ks(env, e, 0x46c, e->position, e->angle, e->light, 0, -2, 0xffff, 0.0f);
    e->field_78 = 0;
    e->client_hit = 1;
}

/* CreateEffect for the arrow types. angle_arg / position_arg: the caller's vectors, which some types write
 * (CreateArrow passes locals it does not read again). Returns 0 for a refused request. */
static int arrow_create(mu_sfx_effect *e, int32_t type, int32_t subtype, float position_arg[3], float angle_arg[3],
                        const mu_sfx_info *info, const mu_sfx_env *env)
{
    const int straight = arrow_straight_skill(e->skill);
    if (info->skill == 0x2d8)
        return 0;   /* 0x013cd5b0: the arc skill's branch is not reconstructed */
    switch (type) {
    case 0x471: case 0x458:                     /* 0x013ca9f2 / 0x013cac12 */
        e->lifetime = 30;
        e->blend_mesh = -2;
        e->scale = 1.0f;
        if (!straight)
            e->position[2] = e->position[2] + 130.0f;
        set3(e->direction, 0.0f, -70.0f, 0.0f);
        copy3(e->field_188, e->position);
        call_joint_args(env, e, 0x7fd6, e->position, e->position, e->angle, 5, 100.0f, -1, 0, NULL);
        if (subtype != 0)
            arrow_trail(env, e);
        e->serial = env ? env->serial : 0;
        return 1;
    case 0x459: {                               /* 0x013cae32 */
        e->lifetime = 30;
        e->blend_mesh = -2;
        e->scale = 1.0f;
        if (!straight)
            e->position[2] = e->position[2] + 130.0f;
        set3(e->direction, 0.0f, -60.0f, 0.0f);
        static const float offset[3] = {-10.0f, -100.0f, 15.0f};
        float p[3];
        rotate_by(offset, e->angle, p);
        for (int k = 0; k < 3; ++k)
            e->impact[k] = e->position[k] + p[k];
        angle_arg[0] = 0.0f;
        angle_arg[1] = 0.0f;
        angle_arg[2] = e->angle[2];
        const int n = subtype == 1 ? 3 : subtype == 3 ? 8 : 4;
        const int32_t sub = subtype == 3 ? 0x37 : subtype == 1 ? 0x19 : 0xb;
        for (int k = 0; k < n; ++k)
            call_joint_args(env, e, 0x7f78, e->impact, e->impact, angle_arg, sub, 50.0f, -1,
                            subtype == 3 || k == 1, NULL);
        e->serial = env ? env->serial : 0;
        return 1;
    }
    case 0x442: {                               /* 0x013ce0de */
        e->velocity = 1.0f;
        e->lifetime = 30;
        if (straight) {
            memset(e, 0, sizeof *e);
            return 0;   /* the client rotates an unset stack vector here */
        }
        static const float offset[3] = {-10.0f, -60.0f, 135.0f};
        float p[3];
        rotate_by(offset, e->angle, p);
        for (int k = 0; k < 3; ++k)
            e->position[k] = e->position[k] + p[k];
        e->blend_mesh = 0;
        e->scale = 1.0f;
        e->direction[1] = -30.0f;
        e->gravity = -10.0f;
        e->lifetime = 40;
        if (subtype == 2) {
            e->field_78 = 0;
            e->client_hit = 1;
        }
        e->serial = env ? env->serial : 0;
        return 1;
    }
    case 0x474:                                 /* 0x013d8da1: subtypes 0 and 2 only */
        if (subtype != 0 && subtype != 2)
            return 1;
        e->lifetime = 30;
        e->blend_mesh = -2;
        e->scale = 1.0f;
        e->gravity = -10.0f;
        if (!straight)
            e->position[2] = e->position[2] + 130.0f;
        if (subtype != 0)
            arrow_trail(env, e);
        set3(e->direction, 0.0f, -70.0f, 0.0f);
        copy3(e->field_188, e->position);
        call_joint_args(env, e, 0x7fd6, e->position, e->position, e->angle, 5, 100.0f, -1, 0, NULL);
        e->serial = env ? env->serial : 0;
        return 1;
    case 0x5b0: case 0x5b1: {                   /* 0x013f5f8c / 0x013f6350 */
        e->lifetime = 30;
        e->scale = 1.5f;
        e->gravity = -10.0f;
        if (!straight)
            e->position[2] = e->position[2] + 130.0f;
        set3(e->direction, 0.0f, -60.0f, 0.0f);
        if (subtype == 2)
            arrow_trail(env, e);
        /* AngleToVector 0x00d015d5: VectorNormalize(VectorRotate((0, -1, 0), AngleMatrix(angle))) */
        static const float down[3] = {0.0f, -1.0f, 0.0f};
        float d[3], q[3];
        rotate_by(down, e->angle, d);
        vector_normalize(d);
        for (int k = 0; k < 3; ++k)
            d[k] = 18.0f * d[k];
        for (int k = 0; k < 3; ++k)
            q[k] = d[k] + e->position[k];
        float tint[3];
        if (type == 0x5b0) {
            set3(tint, F_0_9, F_0_2, 0.0f);
            call_joint_args(env, e, 0x814c, q, q, e->angle, 0xa, 40.0f, -1, 0, tint);
            set3(tint, F_0_1, 0.7f, 0.92f);
            call_joint_args(env, e, 0x8182, q, q, e->angle, 0xa, 80.0f, -1, 0, tint);
        } else {
            set3(tint, F_0_2, 1.0f, 0.38f);
            call_joint_args(env, e, 0x8185, q, q, e->angle, 0xa, 65.0f, -1, 0, tint);
        }
        e->serial = env ? env->serial : 0;
        return 1;
    }
    default:
        break;
    }

    /* the shared body 0x013cb34d */
    if (type == MU_SFX_MODEL_ARROW)
        e->blend_mesh = 1;
    else if (type == 0x441)
        e->blend_mesh = -2;
    else if (type == 0x43d || type == 0x43e || type == 0x43f || type == 0x443)
        e->blend_mesh = 0;
    e->velocity = 1.0f;
    e->lifetime = 30;
    const uint16_t s = info->word4;
    if (!(type == 0x45c && subtype == 1) && !(type == MU_SFX_MODEL_ARROW && subtype == 6) && s != 0x7e7 &&
        s != 0x7fc && s != 0x7fd && s != 0x7fe && s != 0x2d7) {
        static const float offset[3] = {-10.0f, -60.0f, 135.0f};
        float p[3];
        rotate_by(offset, e->angle, p);
        for (int k = 0; k < 3; ++k)
            e->position[k] = e->position[k] + p[k];
    }
    static const float header_light[3] = {0.3f, 0.8f, 1.0f};
    switch (type) {
    case 0x443:                                 /* 0x013cb5a3 */
        e->scale = 1.8f;
        e->direction[1] = -50.0f;
        e->gravity = -10.0f;
        break;
    case 0x45a:                                 /* 0x013cbb5a */
        e->scale = 1.0f;
        e->direction[1] = -70.0f;
        call_joint_args(env, e, 0x7f79, e->position, e->position, e->angle, 0xe, 50.0f, 0x28, 0, NULL);
        break;
    case 0x45c:
        e->scale = F_0_8;
        e->direction[1] = -70.0f;
        e->lifetime = 30;
        break;
    case 0x45d:                                 /* subtype 3 is not an arrow's */
        e->scale = 1.15f;
        e->direction[1] = -70.0f;
        e->lifetime = e->field_70 = 24;
        break;
    case 0x45e: {                               /* 0x013cbd62 */
        static const float offset[3] = {0.0f, -30.0f, 0.0f};
        float p[3];
        rotate_by(offset, angle_arg, p);
        for (int k = 0; k < 3; ++k)
            e->position[k] = e->position[k] + p[k];
        e->scale = 0.7f;
        e->direction[1] = -40.0f;
        e->lifetime = e->field_70 = 50;
        call_joint_args(env, e, 0x80e3, e->position, e->position, angle_arg, 4, 100.0f, -1, 0, NULL);
        break;
    }
    case 0x60a: {                               /* 0x013cbf60 */
        e->lifetime = 30;
        e->scale = 1.5f;
        e->gravity = -10.0f;
        set3(e->direction, 0.0f, -70.0f, 0.0f);
        copy3(angle_arg, e->angle);
        static const float up[3] = {0.0f, 100.0f, 0.0f};
        rotate_by(up, angle_arg, position_arg);
        float q[3];
        for (int k = 0; k < 3; ++k)
            q[k] = e->position[k] + position_arg[k];
        call_joint_args(env, e, 0x80e4, q, q, e->angle, 1, 20.0f, -1, 0, NULL);
        e->serial = env ? env->serial : 0;
        break;
    }
    case 0x60d: case 0x60e: case 0x60f: case 0x610: case 0x612: case 0x613: case 0x614: {
        e->field_70 = 30;
        e->lifetime = e->field_70;
        e->scale = F_0_2;
        e->gravity = -10.0f;
        set3(e->direction, 0.0f, -70.0f, 0.0f);
        copy3(e->light, header_light);
        if (type == 0x60d || type == 0x60e) {   /* 0x013cc2b6 / 0x013cc5cf */
            copy3(angle_arg, e->angle);
            static const float ahead[3] = {0.0f, 40.0f, 0.0f};
            rotate_by(ahead, angle_arg, position_arg);
            float q[3];
            for (int k = 0; k < 3; ++k)
                q[k] = e->position[k] + position_arg[k];
            if (type == 0x60d) {
                static const float tint[3] = {1.0f, 0.7f, 0.4f};
                call_joint_args(env, e, 0x80e3, q, e->position, angle_arg, 5, 15.0f, -1, 0, tint);
            } else {
                if (!straight)
                    e->angle[1] = (float)smod(env_rand(env), 360);
                call_joint_args(env, e, 0x7f79, e->position, q, e->angle, 0x16, 70.0f, 0x28, 0, NULL);
            }
        } else if (type == 0x60f) {
            static const float tint[3] = {0.1f, 0.36f, 0.55f};
            call_joint_args(env, e, 0x828c, e->position, e->position, e->angle, 2, 140.0f, -1, 0, tint);
        } else if (type == 0x610) {
            static const float tint[3] = {0.2f, 0.55f, 1.0f};
            call_joint_args(env, e, 0x80e3, e->position, e->position, e->angle, 5, 50.0f, -1, 0, tint);
        }
        e->serial = env ? env->serial : 0;
        break;
    }
    case 0x616:                                 /* 0x013ccebc */
        copy3(e->impact, e->position);
        e->field_70 = 30;
        e->lifetime = e->field_70;
        e->scale = 1.0f;
        e->gravity = -10.0f;
        set3(e->direction, 0.0f, -70.0f, 0.0f);
        copy3(e->light, header_light);
        e->serial = env ? env->serial : 0;
        break;
    case 0x525:                                 /* 0x013cd05a (subtype 3 is not an arrow's) */
        e->scale = F_0_8;
        e->direction[1] = -70.0f;
        e->lifetime = 30;
        break;
    default:                                    /* 0x013cd0f2 */
        e->scale = F_0_8;
        e->direction[1] = -70.0f;
        break;
    }
    /* 0x013cd121 */
    if (subtype == 2 || subtype == 6)
        arrow_trail(env, e);
    if (type == 0x47f) {                        /* 0x013cd3ed */
        e->blend_mesh = 1;
        if (!straight)
            e->angle[1] = (float)smod(env_rand(env), 360);
        call_joint_args(env, e, 0x7f79, e->position, e->position, e->angle, 0xc, 40.0f, 0x50, 0, NULL);
    } else if (type == 0x45b) {                 /* 0x013cd4ba */
        e->blend_mesh = 0;
        e->scale = 1.0f;
        e->direction[1] = -70.0f;
        if (!straight)
            e->angle[1] = (float)smod(env_rand(env), 360);
        call_joint_args(env, e, 0x7f79, e->position, e->position, e->angle, 0xf, 50.0f, 0x28, 0, NULL);
    }
    e->serial = env ? env->serial : 0;         /* 0x013cd66f */
    return 1;
}

/* p = position + (rand % (2a) - a, rand % (2b) - b, rand % (2a) - a), the z, y, x order of the calls being x, y, z */
static void arrow_scatter(const mu_sfx_env *env, const float position[3], int32_t a, int32_t b, float out[3])
{
    out[0] = (float)(smod(env_rand(env), 2 * a) - a);
    out[1] = (float)(smod(env_rand(env), 2 * b) - b);
    out[2] = (float)(smod(env_rand(env), 2 * a) - a);
    for (int k = 0; k < 3; ++k)
        out[k] = out[k] + position[k];
}

/* 0x011ff622(lo, hi, 1): rand() % (hi - lo + 1) + lo, clamped (whole steps only here). */
static float arrow_rand_range(const mu_sfx_env *env, float lo, float hi)
{
    const int32_t a = trunc_i32(lo), b = trunc_i32(hi);
    float r = (float)(smod(env_rand(env), b - a + 1) + a) / 1.0f;
    if (lo > r)
        r = lo;
    else if (r > hi)
        r = hi;
    return r;
}

/* p = position + (f(-32, 32), f(-64, 32), f(-32, 32)) */
static void arrow_jitter(const mu_sfx_env *env, const float position[3], float out[3])
{
    const float d = 32.0f;
    copy3(out, position);
    out[0] = arrow_rand_range(env, -d, d) + out[0];
    out[1] = arrow_rand_range(env, -d * 2.0f, d) + out[1];
    out[2] = arrow_rand_range(env, -d, d) + out[2];
}

static void arrow_light(const mu_sfx_env *env, mu_sfx_effect *e, float light[3], float lum, float r, float g, float b)
{
    light[0] = lum * r;
    light[1] = lum * g;
    light[2] = lum * b;
    call_terrain_light(env, e, light, 2);
}

/* The two spinning Shiny sprites 0x441/0x443/0x442 draw at the arrow (rotation = (int)WorldTime * 0.1). */
static void arrow_spin(const mu_sfx_env *env, mu_sfx_effect *e, int32_t bitmap, const float light[3], float s1,
                       float s2)
{
    const int32_t t = trunc_i32(env ? env->world_time : 0.0f);
    call_sprite(env, e, bitmap, e->position, s1, light, (float)t * F_0_1);
    call_sprite(env, e, bitmap, e->position, s2, light, (float)(int32_t)(0u - (uint32_t)t) * F_0_1);   /* neg eax */
}

static int arrow_model(const mu_sfx_env *env, const mu_sfx_effect *e)
{
    int16_t keys = 1;
    return !env || !env->model || env->model(env->context, e->type, e->action, &keys);
}

/* The model pose and TransformByObjectBone(out, o, bone, 0). */
static void arrow_pose(const mu_sfx_env *env, mu_sfx_effect *e)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_POSE;
    c.type = e->type;
    c.owner = -2;
    env_call(env, &c, e);
}

static void arrow_bone(const mu_sfx_env *env, mu_sfx_effect *e, int32_t bone, float out[3])
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_BONE;
    c.type = e->type;
    c.range = bone;
    c.owner = -2;
    env_call(env, &c, e);
    if (env && env->bone)
        env->bone(env->context, e, bone, out);
    else
        copy3(out, e->position);
}

/* 0x0150de66: fall by the gravity, bounce off the terrain (gravity and forward speed x 0.4). */
static void arrow_bounce(const mu_sfx_env *env, mu_sfx_effect *e)
{
    e->position[2] = e->position[2] + e->gravity;
    e->gravity = e->gravity - 1.0f;
    const float ground = env_height(env, e->position[0], e->position[1]);
    if (ground > e->position[2]) {
        e->position[2] = ground;
        e->gravity = -e->gravity * F_0_4;
        e->direction[1] = e->direction[1] * F_0_4;
    }
}

/* MoveEffect for the arrow types (after the prologue's luminosity). Returns 0 when the case jumps straight to the
 * common tail without its hit check. */
static void arrow_move(mu_sfx_effect *e, const mu_sfx_env *env, float light[3], float lum)
{
    const int32_t type = e->type, sub = e->subtype;
    const int straight = arrow_straight_skill(e->skill);
    float p[3], c[3];
    switch (type) {
    case 0x43c: case 0x43d: case 0x43e: case 0x43f: case 0x440: case 0x45e: case 0x5b0:
        break;
    case 0x441: case 0x443: {                   /* 0x014652c7 / 0x014659fd */
        arrow_spin(env, e, 0x7f37, e->light, 0.5f, 1.0f);
        for (int k = 0; k < 4; ++k) {
            if (type == 0x441) {
                arrow_scatter(env, e->position, 16, 32, p);
                call_particle(env, e, 0x7f73 + smod(env_rand(env), 3), p, e->angle, e->light, 0, 1.0f, -1);
            } else {
                arrow_scatter(env, e->position, 8, 8, p);
                call_particle(env, e, 0x7fcd, p, e->angle, e->light, 1, 1.0f, -1);
            }
        }
        if (type == 0x443)
            call_particle(env, e, 0x7f5a, e->position, e->angle, e->light, 0, 1.0f, -1);
        else if (!straight)
            e->angle[1] = e->angle[1] + 30.0f;
        arrow_light(env, e, light, lum, 0.6f, F_0_8, F_0_8);
        break;
    }
    case 0x47f:                                 /* 0x01465641 */
        if (!straight)
            e->angle[1] = e->angle[1] + 60.0f;
        if ((e->lifetime & 1) == 0) {
            for (int k = 0; k < 3; ++k) {
                arrow_scatter(env, e->position, 16, 32, p);
                set3(light, F_0_4, F_0_2, 1.0f);
                call_particle(env, e, 0x7f78, p, e->angle, light, 5, F_0_2, -1);
            }
        }
        copy3(e->field_188, e->position);
        call_effect_ks(env, e, 0x477, e->position, e->angle, e->light, 3, -1, 0, 0.0f);
        arrow_light(env, e, light, lum, 0.6f, F_0_2, F_0_8);
        break;
    case 0x45a:                                 /* 0x0146681c */
        if (!straight)
            e->angle[1] = e->angle[1] + 35.0f;
        break;
    case 0x45b:                                 /* 0x0146687a */
        copy3(e->field_188, e->position);
        set3(e->light, 0.0f, 1.0f, F_0_1);
        call_effect_ks(env, e, 0x477, e->position, e->angle, e->light, 4, -1, 0, 0.0f);
        arrow_light(env, e, light, lum, 0.6f, F_0_2, F_0_8);
        break;
    case 0x442: {                               /* 0x01466aeb */
        set3(light, 1.0f, 0.6f, F_0_4);
        arrow_spin(env, e, MU_SFX_BITMAP_FLARE, light, 1.0f, 2.0f);
        for (int k = 0; k < 4; ++k) {
            arrow_scatter(env, e->position, 8, 8, p);
            call_particle(env, e, 0x7fcd, p, e->angle, e->light, 1, 1.0f, -1);
        }
        arrow_bounce(env, e);
        if (e->lifetime == 1) {
            mu_sfx_inferno_burst(e->position, 1, env);
            if (is_hero_owner(e, env) && sub != 0x63)
                call_area(env, e, 100.0f);
        }
        arrow_light(env, e, light, lum, 0.6f, F_0_8, F_0_8);
        break;
    }
    case 0x45c: {                               /* 0x01466ec5 */
        if (sub == 0x63)
            return;
        check(env, e, MU_SFX_CALL_CHECK_ARROW);
        if (!arrow_model(env, e))
            return;
        set3(light, 0.6f, 0.7f, F_0_9);
        arrow_pose(env, e);
        float b[3], d[3];
        arrow_bone(env, e, 0, b);
        rotate_by(e->direction, e->angle, d);
        for (int k = 0; k < 3; ++k)
            p[k] = b[k] + d[k];
        call_sprite(env, e, MU_SFX_BITMAP_FLARE, p, 3.0f, light, 0.0f);
        call_sprite(env, e, MU_SFX_BITMAP_FLARE, p, 2.0f, light, 0.0f);
        if (e->lifetime == 30 || e->lifetime == 28 || e->lifetime == 26 || e->lifetime == 24) {
            const int32_t n = smod(env_rand(env), 3);
            set3(light, 0.6f, 0.7f, F_0_9);
            arrow_bone(env, e, 1, p);
            for (int32_t k = 0; k < n; ++k) {
                call_effect_ks(env, e, 0x45f, p, e->angle, light, 0, -1, 0xffff, 0.6f);
                call_effect_ks(env, e, 0x45f, p, e->angle, light, 1, -1, 0xffff, 0.6f);
            }
        }
        if (e->lifetime == 30) {
            arrow_bone(env, e, 1, p);
            set3(light, F_0_4, F_0_4, F_0_9);
            call_joint_args(env, e, 0x7f79, p, p, e->angle, 0x12, 90.0f, 0x28, 0, light);
        }
        return;
    }
    case 0x45d: {                               /* 0x0146765c */
        check(env, e, MU_SFX_CALL_CHECK_ARROW);
        if (sub != 0 || !arrow_model(env, e))
            return;
        float b[3] = {0.0f, 0.0f, 0.0f}, d[3];
        arrow_pose(env, e);
        arrow_bone(env, e, 0, b);
        rotate_by(e->direction, e->angle, d);
        for (int k = 0; k < 3; ++k)
            b[k] = b[k] + d[k];
        set3(light, 1.0f, 1.0f, 1.0f);
        float t = (float)e->lifetime / (float)e->field_70;
        if (t > 0.88f)
            t = 1.1f - t;
        else if (t > 0.66f)
            t = t - 0.66f;
        else
            t = 0.0f;
        t = t * 6.0f;
        call_particle(env, e, 0x8085, b, e->angle, light, 0x11, t, -2);
        return;
    }
    case 0x471: case 0x474: {                   /* 0x01464238 / 0x014712e8 */
        if (type == 0x474) {
            if (sub == 0x63)
                return;
            if (!straight)
                e->angle[1] = e->angle[1] + 30.0f;
            for (int k = 0; k < 3; ++k)
                call_particle(env, e, 0x7f5a, e->position, e->angle, light, 0xd, 1.0f, -1);
            if (e->lifetime == 1)
                mu_sfx_inferno_burst(e->position, 1, env);
        } else {
            e->blend_light = e->lifetime > 25 ? (float)(30 - e->lifetime) / 40.0f : 1.0f;
            if (!straight)
                e->angle[1] = (float)smod(env_rand(env), 60) + 30.0f + e->angle[1];
        }
        copy3(e->field_188, e->position);
        float d[3];
        rotate_by(e->direction, e->angle, d);
        for (int k = 0; k < 3; ++k)
            e->field_188[k] = e->field_188[k] + d[k];
        arrow_light(env, e, light, lum, 1.0f, F_0_4, F_0_2);
        break;
    }
    case 0x458:                                 /* 0x0146457a */
        if (!straight)
            e->angle[1] = e->angle[1] + 30.0f;
        copy3(e->field_188, e->position);
        arrow_light(env, e, light, lum, F_0_2, F_0_4, 1.0f);
        break;
    case 0x459:                                 /* 0x014646f9: subtype 2 only */
        if (sub != 2)
            return;
        e->angle[1] = e->angle[1] + 30.0f;
        light[0] = lum * F_0_2;
        light[1] = lum * F_0_4;
        light[2] = lum * 1.0f;
        {
            mu_sfx_call t;
            memset(&t, 0, sizeof t);
            t.routine = MU_SFX_CALL_TERRAIN_LIGHT;
            t.position[0] = e->impact[0];
            t.position[1] = e->impact[1];
            copy3(t.light, light);
            t.range = 2;
            t.owner = MU_SFX_NO_OWNER;
            env_call(env, &t, e);
        }
        if (e->lifetime == 13)
            call_effect_ks(env, e, 0x46c, e->position, e->angle, e->light, 0, -2, 0xffff, 0.0f);
        else if (e->lifetime == 30) {
            e->field_78 = 0;
            e->client_hit = 1;
        }
        return;
    case 0x525: {                               /* 0x014681fe */
        set3(c, F_0_2, F_0_8, 0.5f);
        if (!straight)
            e->angle[1] = e->angle[1] + 60.0f;
        for (int k = 0; k < 2; ++k) {
            arrow_scatter(env, e->position, 16, 32, p);
            call_particle(env, e, MU_SFX_BITMAP_SPARK3, p, e->angle, c, 0x1e, 1.0f, -1);
        }
        copy3(e->field_188, e->position);
        call_particle(env, e, 0x7f5a, e->position, e->angle, c, 0x18, 1.0f, -1);
        arrow_light(env, e, c, lum, F_0_2, F_0_8, 0.5f);
        break;
    }
    case 0x5b1:                                 /* 0x014abb4f */
        if (smod(env_rand(env), 3) == 0) {
            set3(c, F_0_4, 0.95f, 1.0f);
            call_particle(env, e, 0x8184, e->position, e->angle, c, 1, F_0_1, -1);
        }
        break;
    case 0x60a: {                               /* 0x014685de */
        if (!arrow_model(env, e))
            return;
        static const float back[3] = {0.0f, -70.0f, 0.0f};
        set3(light, 1.0f, F_0_1, 1.0f);
        float d[3];
        rotate_by(back, e->angle, d);
        for (int k = 0; k < 3; ++k)
            p[k] = e->position[k] + d[k];
        call_sprite(env, e, 0x7f7a, p, 2.0f, e->light, 0.0f);
        set3(light, 1.0f, F_0_3, 1.0f);
        const float s = (float)smod(env_rand(env), 20) / 42.5f + 0.5f;
        call_sprite(env, e, 0x7f6c, p, s, light, 0.0f);
        set3(light, F_0_1, 0.0f, 1.0f);
        call_sprite(env, e, 0x8108, p, s, light, 0.0f);
        set3(light, 0.0f, 0.6f, 1.0f);
        call_effect_ks(env, e, 0x60b, e->position, e->angle, light, 0, -2, 0xffff, 0.0f);
        break;
    }
    case 0x60d:                                 /* 0x01468c0a */
        if (!straight)
            e->angle[1] = e->angle[1] - 30.0f;
        set3(c, F_0_3, F_0_3, 1.0f);
        if (smod(env_rand(env), 4) == 0)
            call_effect_ks(env, e, 0x477, e->position, e->angle, c, 4, -1, 0, 0.0f);
        set3(c, 0.5f, 0.5f, 1.0f);
        for (int k = 0; k < 3; ++k)
            c[k] = c[k] * lum;
        call_terrain_light(env, e, c, 2);
        break;
    case 0x60e: {                               /* 0x01468dbb */
        e->scale = 1.5f;
        if (!straight)
            e->angle[1] = e->angle[1] - 45.0f;
        float d[3];
        rotate_by(e->direction, e->angle, d);
        for (int k = 0; k < 3; ++k)
            p[k] = e->position[k] + d[k];
        set3(c, 1.0f, 0.65f, F_0_2);
        const int32_t kind = smod(env_rand(env), 3);
        const float s = (float)(smod(env_rand(env), 60) + 10) * F_0_01 * 1.0f;
        static const float zero[3] = {0.0f, 0.0f, 0.0f};
        call_particle(env, e, 0x8081 + kind, e->position, zero, c, 0, s, -1);
        static const float white[3] = {1.0f, 1.0f, 1.0f};
        call_sprite(env, e, 0x7fe0, p, 1.6f, white, 0.0f);
        const float g = (float)smod(env_rand(env), 15) / 37.5f + 0.5f;
        const float glow[3] = {g, g, g};
        call_sprite(env, e, 0x8108, p, 0.6f, glow, 0.0f);
        break;
    }
    case 0x60f: {                               /* 0x014691e9 */
        e->scale = 1.8f;
        set3(c, 0.5f, 1.3f, 2.0f);
        float q[3];
        copy3(q, e->position);
        q[2] = env_height(env, q[0], q[1]);
        if (e->lifetime % 3 == 0)
            call_effect_ks(env, e, 0x38b5, q, e->angle, c, 1, -1, 0xffff, F_0_2);
        arrow_jitter(env, e->position, q);
        set3(c, 0.15f, 0.45f, 1.0f);
        call_particle(env, e, 0x7f5a, e->position, e->angle, c, 0x4e, 0.5f, -1);
        set3(c, 0.7f, F_0_8, 1.0f);
        call_particle(env, e, MU_SFX_BITMAP_SPARK3, q, e->angle, c, 0x1e, 1.0f, -1);
        break;
    }
    case 0x610: {                               /* 0x01469582 */
        e->scale = 1.8f;
        if (!arrow_model(env, e))
            return;
        /* 0x0185caa4(0, 15, 70, 0.5): 0x011ff622(0, 15, 1) / 70 + 0.5 */
        float g = arrow_rand_range(env, 0.0f, 15.0f) / 70.0f + 0.5f;
        set3(c, g, g, g);
        call_particle(env, e, 0x810c, e->position, e->angle, c, 0, 0.5f, -1);
        g = arrow_rand_range(env, 0.0f, 15.0f) / 70.0f + 0.5f;
        set3(c, 0.6f * g, F_0_1 * g, F_0_8 * g);
        call_particle(env, e, 0x7f5a, e->position, e->angle, c, 0x7a, 1.5f, -1);
        if ((e->lifetime & 1) == 0) {
            set3(c, F_0_4, 0.5f, 1.0f);
            call_effect_ks(env, e, 0x611, e->position, e->angle, c, 0, -2, 0xffff, 0.5f);
        }
        break;
    }
    case 0x612: case 0x613: {                   /* 0x014698ef / 0x01469b71 */
        e->scale = 1.4f;
        if (!arrow_model(env, e))
            return;
        float q[3];
        arrow_jitter(env, e->position, q);
        if (smod(env_rand(env), type == 0x612 ? 2 : 4) != 0) {
            set3(c, 0.5f, 0.7f, 1.0f);
            call_particle(env, e, 0x83b3, e->position, e->angle, c, 1, 1.1f, -1);
            set3(c, 1.0f, 1.0f, 1.0f);
            call_particle(env, e, 0x8155, q, e->angle, c, 2, 1.0f, -1);
        }
        if (type == 0x613) {
            const float s = arrow_rand_range(env, F_0_3, 0.6f);
            set3(c, F_0_4, 0.5f, 1.0f);
            call_particle(env, e, 0x810a, q, e->angle, c, 0xe, s, -1);
            set3(c, F_0_4, 1.0f, 0.7f);
            call_particle(env, e, 0x810a, q, e->angle, c, 0xe, s, -1);
        }
        break;
    }
    case 0x614: {                               /* 0x01469f18 */
        e->scale = 1.2f;
        if (!arrow_model(env, e))
            return;
        set3(c, 1.0f, 1.0f, 1.0f);
        call_sprite(env, e, 0x7fe0, e->position, F_0_4, c, 0.0f);
        call_sprite(env, e, 0x81ec, e->position, F_0_4, c, 0.0f);
        call_sprite(env, e, 0x81ec, e->position, F_0_8, c, 0.0f);
        call_particle(env, e, 0x83b8, e->position, e->angle, c, 2, 0.6f, -1);
        (void)env_rand(env);   /* rand() % 3 & 0: always the first case */
        call_particle(env, e, 0x8084, e->position, e->angle, c, 0x1e, 2.0f, -1);
        break;
    }
    case 0x616: {                               /* 0x0146aa05 */
        if (!arrow_model(env, e))
            return;
        set3(c, 1.0f, 1.0f, 1.0f);
        if (e->lifetime == 30) {
            float q[3];
            copy3(q, e->position);
            set3(c, 1.0f, 0.7f, F_0_3);
            call_joint_args(env, e, 0x85cc, q, q, e->angle, 0, 20.0f, -1, 0, c);
        }
        set3(c, F_0_3, 0.7f, 1.0f);
        call_sprite(env, e, 0x85c3, e->position, F_0_4, c, 0.0f);
        call_sprite(env, e, 0x7f78, e->position, 0.15f, c, 0.0f);
        for (int k = 0; k < 5; ++k) {
            arrow_jitter(env, e->position, p);
            const float s = (float)smod(env_rand(env), 3) * F_0_1 + 1.5f;
            set3(c, F_0_2, F_0_3, F_0_8);
            call_particle(env, e, 0x7f5a, p, e->angle, c, 0x86, s, -1);
        }
        for (int k = 0; k < 5; ++k) {
            copy3(p, e->position);
            set3(c, 1.0f, 0.7f, F_0_3);
            const float s = (float)smod(env_rand(env), 3) * F_0_1 + 0.15f;
            call_particle(env, e, 0x810a, p, e->angle, c, 0x24, s, -1);
        }
        break;
    }
    default:
        return;
    }
    check(env, e, MU_SFX_CALL_CHECK_ARROW);
}

/* Bow 0x12f9's sparks after CreateArrows' shots (0x0158dfdc). bone: the shooter's weapon bone
 * (character + 0x19b1, read through its own index); bone_ok: 0x0129f12c found it (the model has the bone). */
int mu_sfx_bow_sparks(int16_t weapon, int32_t object, int has_model, int32_t bone, int bone_ok, const mu_sfx_env *env)
{
    if (weapon != 0x12f9 || !has_model || !bone_ok)
        return 0;
    static const float offset[3] = {0.0f, 10.0f, -130.0f};
    static const float white[3] = {1.0f, 1.0f, 1.0f};
    float p[3];
    if (env && env->owner_bone)   /* TransformPosition(bone matrix, (0, 10, -130), p, 1) */
        env->owner_bone(env->context, object, bone, offset, p);
    else
        copy3(p, offset);
    int n = 0;
    for (int k = 0; k < 15; ++k) {
        float a[3];
        a[0] = (float)smod(env_rand(env), 360);
        a[1] = 0.0f;
        a[2] = 0.0f;
        if (smod(env_rand(env), 2) == 0) {
            mu_sfx_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_SFX_CALL_JOINT;
            c.type = 0x7fd5;
            c.subtype = 3;
            c.owner = -1;
            c.scale = 10.0f;
            c.arg7 = -1;
            copy3(c.position, p);
            copy3(c.target, p);
            copy3(c.angle, a);
            env_call(env, &c, NULL);
        }
        call_particle(env, NULL, 0x7f25, p, a, white, 0, 1.0f, -1);
        ++n;
    }
    return n;
}
