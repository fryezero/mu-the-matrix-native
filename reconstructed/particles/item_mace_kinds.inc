/* RENDER-EFFECTS-023: the remaining particle pairs of mace pre-draw programs.
 * CreateParticle 0x015ae7b0, MoveParticles 0x01616c80, RenderParticles 0x0159123f.
 * Original-instruction comparisons: scripts/validate_render_effects23.py. */
static int mu_pt_item_mace_kind(int32_t type, int32_t subtype)
{
    switch (type) {
    case 0x85bc: return subtype == 5;
    case 0x83b8: return subtype == 8;
    case 0x85fc: return subtype == 1 || subtype == 2;
    case 0x8315: case 0x8316: case 0x8317: return subtype == 4;
    case 0x7ffb: return subtype == 0;
    case 0x83b3: return subtype == 0x13;
    case 0x8109: return subtype == 0xe;
    case 0x8549: return subtype == 1;
    case 0x82f2: return subtype == 0x1a;
    case 0x810b: return subtype == 0xa;
    case 0x807e: case 0x807f: case 0x8080: return subtype == 0x18;
    case 0x8081: case 0x8082: case 0x8083: return subtype == 9;
    default: return 0;
    }
}

static void mu_pt_item_mace_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    const int fire = p->type >= 0x8315 && p->type <= 0x8317;
    const int smoke = p->type >= 0x807e && p->type <= 0x8080;
    const int lightning = p->type >= 0x8081 && p->type <= 0x8083;
    if (p->type == 0x7ffb || p->type == 0x85fc) {
        /* 0x016147ae / 0x01613f98 / 0x0161400a. No random rotation. */
        p->lifetime = p->type == 0x85fc && p->subtype == 2 ? 50 : 30;
        p->initial_lifetime = p->lifetime;
        p->scale = 0.0f;
        p->initial_scale = scale;
        p->alpha = 1.0f;
        return;
    }
    if (p->type == 0x8549 || lightning) {
        /* 0x01615d4e / 0x015d3821. */
        p->lifetime = 4;
        p->initial_lifetime = p->lifetime;
        p->scale = scale;
        p->alpha = 1.0f;
        if (lightning) p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        return;
    }
    if (p->type == 0x83b8 || p->type == 0x8109 || p->type == 0x810b) {
        /* 0x015e407f / 0x015b0907 / 0x01602041. Velocity saves the input angle before jitter. */
        p->lifetime = p->type == 0x83b8 ? mu_pt_rand(h) % 11 + 20 : (p->type == 0x8109 ? 30 : 20);
        p->initial_lifetime = p->lifetime;
        p->scale = p->type == 0x8109 ? rand_range(h, 0.5f, 1.0f, 100) * scale : scale;
        if (p->type == 0x8109) p->initial_scale = p->scale;
        else if (p->type == 0x810b) p->initial_scale = (scale - scale * 0.5f) / (float)p->initial_lifetime;
        else p->initial_scale = scale / (float)p->initial_lifetime;
        p->alpha = 1.0f;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        copy3(p->velocity, p->angle);
        const float bound = p->type == 0x83b8 ? 30.0f : 20.0f;
        for (int k = 0; k < 3; ++k) p->angle[k] = rand_range(h, -bound, bound, 1);
        return;
    }
    /* 0x01612d8e (red line), 0x016065fd (fire), 0x015d19c4 / 0x01605f17 (expanding smoke),
     * 0x015cfc7a (smokelines). Preserve both products and the subtraction before division. */
    p->lifetime = fire ? 16 : 30;
    p->initial_lifetime = p->lifetime;
    p->scale = scale;
    if (p->type == 0x85bc) p->initial_scale = (scale - scale * 0.3f) / (float)p->initial_lifetime;
    else if (fire) p->initial_scale = (scale - scale * 0.5f) / (float)p->initial_lifetime;
    else p->initial_scale = (scale * 2.0f - scale) / (float)p->initial_lifetime;
    p->alpha = 0.0f;
    p->rotation = rand_range(h, 0.0f, 360.0f, 1);
    if (fire || p->type == 0x85bc) {
        p->velocity[0] = p->velocity[1] = 0.0f;
        p->velocity[2] = fire ? 2.5f : 2.2f;
    } else if (smoke) {
        p->field_84 = rand_range(h, -5.0f, 5.0f, 100);
        p->velocity[0] = p->velocity[1] = 0.0f;
        p->velocity[2] = rand_range(h, 1.0f, 2.0f, 100);
    }
}

static void mu_pt_item_mace_move(mu_pt_particle *p, const mu_pt_host *h)
{
    const int half = p->initial_lifetime / 2;
    if (p->type == 0x7ffb || p->type == 0x85fc) {
        /* 0x0168c6ab / 0x0168be7c: NULL owner clears live; render itself does not clear it. */
        if (p->owner == MU_PT_NO_OWNER) { p->live = 0; return; }
        if (p->lifetime < half) p->alpha = p->alpha - 1.0f / (float)half;
        p->scale = p->initial_scale / (float)p->initial_lifetime + p->scale;
        return;
    }
    if (p->type == 0x8549 || (p->type >= 0x8081 && p->type <= 0x8083)) {
        p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;
        return;
    }
    if (p->type == 0x83b8 || p->type == 0x8109 || p->type == 0x810b) {
        if (p->lifetime < half) p->alpha = p->alpha - 1.0f / (float)half;
        if (p->type != 0x8109) p->scale = p->scale - p->initial_scale;
        if (p->type != 0x810b) {
            p->rotation = p->rotation + p->angle[2];
            const float bound = p->type == 0x83b8 ? 0.5f : 0.4f;
            for (int k = 0; k < 3; ++k) p->velocity[k] = rand_range(h, -bound, bound, 100) + p->velocity[k];
        }
        return;
    }
    if (p->type >= 0x8315 && p->type <= 0x8317) {
        /* 0x0168076d: the SAME one-rand displacement on x and y. */
        const float jitter = (float)(mu_pt_rand(h) % 21 - 10) * 0.01f;
        p->position[0] = p->position[0] + jitter;
        p->position[1] = p->position[1] + jitter;
    }
    if (p->lifetime > half) p->alpha = 1.0f / (float)half + p->alpha;
    else p->alpha = p->alpha - 1.0f / (float)half;
    if (p->type == 0x85bc || (p->type >= 0x8315 && p->type <= 0x8317)) p->scale = p->scale - p->initial_scale;
    else p->scale = p->scale + p->initial_scale;
    if (p->type >= 0x807e && p->type <= 0x8080) p->rotation = p->rotation + p->field_84;
}

/* 0x015ac52a / 0x015ace36: replace position with the selected OBJECT point, without the spark's start offset.
 * NULL owner leaves position unchanged here; its move branch retires it. The native adapter validates the slot
 * generation and bounds before supplying a point. */
void mu_pt_item_mace_follow(mu_pt_particle *p, const float point[3])
{
    if ((p->type == 0x7ffb || p->type == 0x85fc) && mu_pt_item_mace_kind(p->type, p->subtype) &&
        p->owner != MU_PT_NO_OWNER && point) copy3(p->position, point);
}

static void mu_pt_item_mace_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    if (mu_pt_item_mace_kind(p->type, p->subtype))
        for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
}
