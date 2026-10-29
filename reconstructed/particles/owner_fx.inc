/* RENDER-EFFECTS-005: the rank-5 item owner particles (RenderPartObjectBody's
 * rank-5 owner block, 0x01747d6d and its three variants). Included after the
 * shared helpers; admission is limited to the two verified kind/subtype pairs:
 * 0x84e2/0 (Item\texture\lighting01_10cha.jpg) and 0x83de/4 (Effect\smoke_line03.jpg). */
static int mu_pt_owner_fx_kind(int32_t type, int32_t subtype)
{
    return (type == 0x84e2 && subtype == 0) || (type == 0x83de && subtype == 4);
}

static void mu_pt_owner_fx_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == 0x84e2) {                       /* 0x0160eb48 */
        p->initial_lifetime = 10;
        p->lifetime = 10;
        p->initial_scale = scale;
        p->scale = 0.0f;
        p->alpha = 0.0f;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        return;
    }
    p->initial_lifetime = 20;                      /* 0x015d1f29 */
    p->lifetime = 20;
    p->rotation = (float)(mu_pt_rand(h) % 360);
    p->initial_scale = scale;
    p->scale = 0.0f;
    p->alpha = 1.0f;
}

static void mu_pt_owner_fx_move(mu_pt_particle *p, const mu_pt_host *h)
{
    (void)h;
    p->scale = p->initial_scale / (float)p->initial_lifetime + p->scale;
    const float step = 1.0f / (float)p->initial_lifetime;
    if (p->type == 0x84e2) {                       /* 0x01686fa3: grows, fades in, then out */
        if (p->initial_lifetime < p->lifetime * 2)
            p->alpha = step * 2.0f + p->alpha;
        else
            p->alpha = p->alpha - step * 2.0f;
        return;
    }
    p->alpha = p->alpha - step;                    /* 0x0164455b */
}

/* 0x015a7540 / 0x015a3c58: the light times the record's alpha. */
static void mu_pt_owner_fx_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    if (mu_pt_owner_fx_kind(p->type, p->subtype))
        for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
}
