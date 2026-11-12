/* RENDER-EFFECTS-026: the five particle pairs added by the later item programs.
 * Create / move branch addresses are recorded in research part 39. */
static int mu_pt_item_later_kind(int32_t type, int32_t subtype)
{
    return (type == 0x8500 && subtype == 2) || (type == 0x810b && subtype == 8) ||
           (type == 0x810a && subtype == 12) || (type == 0x81cf && subtype == 1) ||
           (type == 0x8569 && subtype == 0);
}

static void mu_pt_item_later_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    switch (p->type) {
    case 0x8500:                                      /* 0x0160d351 */
        p->lifetime = mu_pt_rand(h) % 11 + 20;
        p->initial_lifetime = p->lifetime;
        p->initial_scale = scale / (float)p->lifetime;
        p->alpha = 1.0f;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        p->field_84 = rand_range(h, -20.0f, 20.0f, 1);
        p->velocity[0] = rand_range(h, -2.0f, 2.0f, 100);
        p->velocity[1] = rand_range(h, -2.0f, 2.0f, 100);
        p->velocity[2] = rand_range(h, -2.0f, 0.8f, 100);
        break;
    case 0x810b:                                      /* 0x01601dca */
        p->lifetime = 25;
        p->initial_lifetime = p->lifetime;
        p->initial_scale = scale / (float)(p->lifetime / 2);
        p->alpha = 1.0f;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = rand_range(h, -1.2f, 1.2f, 100);
        break;
    case 0x810a:                                      /* 0x015b1a73 */
        p->lifetime = 20;
        p->initial_lifetime = p->lifetime;
        p->scale = rand_range(h, 0.5f, 1.0f, 100) * scale;
        p->initial_scale = p->scale;
        p->alpha = 1.0f;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        for (int k = 0; k < 3; ++k)
            p->position[k] = rand_range(h, -10.0f, 10.0f, 1) + p->position[k];
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = rand_range(h, -10.0f, 10.0f, 1) * 0.2f;
        break;
    default:                                         /* 0x0160baa3 / 0x01610b2d */
        p->lifetime = p->type == 0x81cf ? 20 : 30;
        p->initial_lifetime = p->lifetime;
        p->initial_scale = scale;
        p->scale = 0.0f;
        p->alpha = 1.0f;
        break;
    }
}

static void mu_pt_item_later_move(mu_pt_particle *p, const mu_pt_host *h)
{
    switch (p->type) {
    case 0x8500:                                      /* 0x01685e1b */
    case 0x810b:                                      /* 0x0167be27 */
        if (p->lifetime < p->initial_lifetime / 2)
            p->scale = p->scale - p->initial_scale;
        p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;
        if (p->type == 0x8500) {
            p->rotation = p->rotation + p->field_84;
            p->velocity[0] = p->velocity[0] + rand_range(h, -0.2f, 0.2f, 100);
            p->velocity[1] = p->velocity[1] + rand_range(h, -0.2f, 0.2f, 100);
            p->velocity[2] = p->velocity[2] + rand_range(h, -0.2f, 0.1f, 100);
        }
        break;
    case 0x810a:                                      /* 0x0161b036 */
        p->scale = p->scale - p->initial_scale / (float)p->initial_lifetime;
        p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;
        break;
    default:                                         /* 0x01684277 / 0x016896de */
        if (p->owner == MU_PT_NO_OWNER) {
            p->live = 0;
            return;
        }
        if (p->type == 0x81cf) {
            p->scale = p->initial_scale / (float)p->initial_lifetime + p->scale;
            const int32_t half = p->initial_lifetime / 2;
            if (p->lifetime < half)
                p->alpha = p->alpha - 1.0f / (float)half;
        } else {
            if (p->lifetime < p->initial_lifetime)
                p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;
            p->scale = p->initial_scale / (float)p->initial_lifetime + p->scale;
        }
        break;
    }
}

static void mu_pt_item_later_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    if (mu_pt_item_later_kind(p->type, p->subtype))
        for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
}

/* RenderParticles 0x015aa1a0: no start offset, and no write for NULL owner. */
int mu_pt_item_later_follow(mu_pt_particle *p, const float point[3])
{
    if (p->type != 0x8569 || p->subtype != 0 || p->owner == MU_PT_NO_OWNER)
        return 1;
    if (!point) {
        p->live = 0;   /* unknown/stale native owner, outside the hosted domain */
        return 0;
    }
    copy3(p->position, point);
    return 1;
}
