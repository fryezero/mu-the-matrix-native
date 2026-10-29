/* RENDER-EFFECTS-005: the rank-5 owner block, a separate hook beside the body
 * executor. RenderPartObjectBody continues after the lit rank-5 meshes
 * (0x01747d6d, 0x0174888d, 0x01749294, 0x01749cc5, one per type list) only
 * when OBJECT bones 35 and 26 are readable through 0x0129f12c (+0x318 set and
 * the bone below the OBJECT model's bone count). Included at the end of
 * renderchar.c; rank5_body calls it only through mu_rc_item_draws_owner. */

typedef struct rank5_owner_variant {
    float bone35[3], bone26[3], sprite[3]; /* TransformPosition local points */
    int32_t modulo[3];                     /* jitter rand() % m, in call order z, y, x */
    float centre[3];
    float scale;                           /* 0x84e2 scale */
} rank5_owner_variant;

/* Type lists built at 0x01746fac..0x0174710e; blue first, then 0x1c2b, B, A. */
static const rank5_owner_variant rank5_owner_variants[4] = {
    {{-25.0f, 0.0f, 20.0f}, {-20.0f, 0.0f, -15.0f}, {10.0f, 0.0f, 10.0f}, {24, 20, 10}, {12.0f, 10.0f, 5.0f}, 0.4f},
    {{-27.0f, 0.0f, 15.0f}, {-27.0f, 0.0f, -15.0f}, {8.0f, 0.0f, 15.0f}, {30, 20, 20}, {15.0f, 10.0f, 10.0f}, 0.4f},
    {{-25.0f, 0.0f, 18.0f}, {-20.0f, 0.0f, -25.0f}, {10.0f, 0.0f, 20.0f}, {20, 10, 20}, {10.0f, 5.0f, 10.0f}, 0.5f},
    {{-30.0f, 0.0f, 15.0f}, {-30.0f, 0.0f, -15.0f}, {10.0f, 0.0f, 20.0f}, {30, 10, 10}, {15.0f, 5.0f, 5.0f}, 0.4f},
};

static int rank5_owner_variant_of(int32_t type)
{
    switch (type) {
    case 0x1c26: case 0x1c27: case 0x1c2c: case 0x1c2e: case 0x1c2f: case 0x1c33: case 0x1c44: return 0;
    case 0x1c2b: return 1;
    case 0x1c25: case 0x1c29: case 0x1c31: case 0x1c32: return 2;
    default: return 3;
    }
}

static int32_t owner_random(const mu_rc_owner_host *h)
{
    return h->random ? h->random(h->context) : 0;
}

static void owner_emit(const mu_rc_owner_host *h, int32_t kind, int32_t bitmap, int32_t subtype,
                       const float position[3], const float light[3], float scale)
{
    mu_rc_owner_fx fx;
    fx.kind = kind;
    fx.bitmap = bitmap;
    fx.subtype = subtype;
    for (int k = 0; k < 3; ++k) {
        fx.position[k] = position[k];
        fx.light[k] = light[k];
    }
    fx.scale = scale;
    if (h->emit)
        h->emit(h->context, &fx);
}

static void owner_draw(sink *s, int32_t mesh, uint32_t flags, float alpha, int32_t blend, float light, float uv,
                       int32_t texture)
{
    mu_rc_item item = *s->item;
    item.blend_mesh = blend;
    item.blend_light = light;
    item.u = uv;
    item.v = uv;
    const mu_rc_item *saved = s->item;
    s->item = &item;
    emit(s, MU_RC_ENTRY_MESH, mesh, flags, alpha, -1, texture);
    s->item = saved;
}

/* Called at the end of the lit rank-5 body, before RenderObjDraw's later glow passes. */
static void rank5_owner(sink *s, const mu_rc_owner_host *h)
{
    const mu_rc_item *it = s->item;
    if (h->bones <= 35)
        return;
    const rank5_owner_variant *v = &rank5_owner_variants[rank5_owner_variant_of(it->type)];
    float a[3], b[3], c[3];
    h->transform(h->context, 35, v->bone35, a);
    h->transform(h->context, 26, v->bone26, b);
    h->transform(h->context, 35, v->sprite, c);
    static const float bolt[3] = {0.7f, 0.8f, 2.0f};
    for (int i = 0; i < 2; ++i) {
        float *targets[2] = {a, b};
        for (int t = 0; t < 2; ++t) {
            float z = v->centre[0] - (float)(owner_random(h) % v->modulo[0]);
            float y = v->centre[1] - (float)(owner_random(h) % v->modulo[1]);
            float x = v->centre[2] - (float)(owner_random(h) % v->modulo[2]);
            targets[t][0] = targets[t][0] + x;
            targets[t][1] = targets[t][1] + y;
            targets[t][2] = targets[t][2] + z;
        }
        owner_emit(h, MU_RC_OWNER_PARTICLE, 0x84e2, 0, b, bolt, v->scale);
        owner_emit(h, MU_RC_OWNER_PARTICLE, 0x84e2, 0, a, bolt, v->scale);
    }
    /* 0x0185caa4(0, 4, 5, 0.5) over 0x011ff622(0, 4, 1): (rand() % 5) / 5 + 0.5 */
    float glint = (float)(owner_random(h) % 5) / 1.0f / 5.0f + 0.5f;
    const float glow[3] = {glint, glint, glint};
    owner_emit(h, MU_RC_OWNER_SPRITE, 0x7fdd, 0, c, glow, 0.8f);
    static const float smoke[3] = {0.2f, 0.2f, 0.4f};
    owner_emit(h, MU_RC_OWNER_PARTICLE, 0x83de, 4, c, smoke, 0.2f);
    /* RenderPartObjectBody's level word: supplied only above the +7 quality cap
     * (the same rule as the body executor's level split). */
    if (it->quality <= 1 || mu_rc_item_glow_level(it) < 9 || it->item_level == -1 ||
        ((it->item_level >> 3) & 15) < 9)
        return;
    const float uv = it->time * 0.0001f;
    const float pulse = mesh_light_pulse(it->time);
    if (v == &rank5_owner_variants[0]) {
        /* 0x017484a4 / 0x01748562: Item1161_Blue.jpg, then Item1161_Black.jpg */
        owner_draw(s, s->context->blue_mesh, 2, 1.0f, s->context->blue_mesh, pulse, uv, 0x8239);
        owner_draw(s, h->black_mesh, 6, 0.26f, h->black_mesh, it->blend_light, uv, -1);
    } else {
        owner_draw(s, 1, 2, 1.0f, 1, pulse, uv, 0x8239);
    }
}

int mu_rc_item_draws_owner(const mu_rc_item *it, mu_rc_model *model, mu_rc_draw *out, int32_t capacity,
                           int32_t *count, const mu_rc_item_context *context, const mu_rc_owner_host *host)
{
    owner_host = host && host->transform ? host : NULL;
    int status = mu_rc_item_draws_context(it, model, out, capacity, count, context);
    owner_host = NULL;
    return status;
}
