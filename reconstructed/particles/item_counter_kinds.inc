/* RENDER-EFFECTS-022: mace 0x0f1f/0x0f20's counter-gated particles.
 * CreateParticle 0x015ae7b0: 0x810a/0x25 0x015b51f0, 0x855d/1 0x01610e81, 0x84d1/1 0x0160c861.
 * MoveParticles: 0x0161d801, 0x01689aa8, 0x016855a9. RenderParticles: 0x0159f880, 0x015aa71c, 0x015a743f.
 * The first kind's render reads OBJECT +0x1f4 + 12*arg8, not +0x158. mu_pt_item_counter_follow supplies that
 * render-time write before the ordinary sprite calculation. Only the verified argument domain 0..2 is hosted. */
static int mu_pt_item_counter_kind(int32_t type, int32_t subtype)
{
    return (type == 0x810a && subtype == 0x25) || ((type == 0x855d || type == 0x84d1) && subtype == 1);
}

static void mu_pt_item_counter_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == 0x810a) {
        if (p->owner == MU_PT_NO_OWNER) {
            p->live = 0;
            return;
        }
        p->lifetime = mu_pt_rand(h) % 11 + 20;
        p->initial_lifetime = p->lifetime;
        p->scale = 0.0f;
        p->initial_scale = scale / (float)(p->lifetime / 2);
        p->alpha = 1.0f;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        copy3(p->start, p->position);
        return;
    }
    p->lifetime = p->type == 0x855d ? 20 : 50;
    p->initial_lifetime = p->lifetime;
    p->scale = scale;
    p->initial_scale = scale / (float)p->lifetime;
    p->alpha = p->type == 0x855d ? 1.0f : 0.0f;
    if (p->type == 0x855d)
        p->moving = 1;
    p->rotation = rand_range(h, 0.0f, 360.0f, 1);
    p->angle[0] = p->angle[1] = p->angle[2] = 0.0f;
    if (p->type == 0x84d1) {
        p->velocity[0] = p->velocity[1] = 0.0f;
        p->velocity[2] = rand_range(h, 1.8f, 2.5f, 100);
        return;
    }
    /* 0x00d01fc6(out, 0, 1, 180, 0, 360, 0): min >= max fixes radius at 1 without drawing rand(). */
    const float radians = 0.017453292f, radius = 1.0f;
    const float theta = rand_range(h, 0.0f, 180.0f * radians, 100);
    const float phi = rand_range(h, 0.0f, 360.0f * radians, 100);
    const float x = (float)sin((double)theta) * radius;
    p->velocity[0] = x * (float)cos((double)phi);
    const float y = (float)sin((double)theta) * radius;
    p->velocity[1] = y * (float)sin((double)phi);
    p->velocity[2] = (float)cos((double)theta) * radius;
    const float speed = rand_range(h, 1.5f, 3.0f, 100);
    for (int k = 0; k < 3; ++k) p->velocity[k] = speed * p->velocity[k];
}

static void mu_pt_item_counter_move(mu_pt_particle *p)
{
    if (p->type == 0x810a && p->owner == MU_PT_NO_OWNER) {
        p->live = 0;
        return;
    }
    const int half = p->initial_lifetime / 2;
    if (p->type == 0x84d1) {
        if (p->lifetime > half) p->alpha = 1.0f / (float)half + p->alpha;
        else p->alpha = p->alpha - 1.0f / (float)half;
    } else {
        p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;
    }
    if (p->type == 0x810a && p->lifetime > half) p->scale = p->scale + p->initial_scale;
    else p->scale = p->scale - p->initial_scale;
}

/* RenderParticles writes position and clears live on a NULL owner. No owner live-byte test. */
int mu_pt_item_counter_follow(mu_pt_particle *p, const float point[3])
{
    if (p->type != 0x810a || p->subtype != 0x25)
        return 1;
    if (p->owner == MU_PT_NO_OWNER || !point) {
        p->live = 0;
        return 0;
    }
    for (int k = 0; k < 3; ++k) p->position[k] = point[k] + p->start[k];
    return 1;
}

static void mu_pt_item_counter_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    if (mu_pt_item_counter_kind(p->type, p->subtype))
        for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
}
