/* RENDER-EFFECTS-025: the two remaining pairs requested by the admitted bows.
 * CreateParticle 0x015afd35 / 0x015b1605; MoveParticles 0x01618ab4 / 0x0161acd9. */
static int mu_pt_item_bow_kind(int32_t type, int32_t subtype)
{
    return (type == 0x8109 && subtype == 7) || (type == 0x810a && subtype == 9);
}

static void mu_pt_item_bow_create(mu_pt_particle *p, const mu_pt_host *h)
{
    p->lifetime = p->type == 0x8109 ? 10 : 12;
    p->initial_lifetime = p->lifetime;
    p->initial_scale = p->scale;
    p->rotation = rand_range(h, 0.0f, 360.0f, 1);
    if (p->type == 0x8109)
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = rand_range(h, -2.5f, 2.5f, 1);
}

static void mu_pt_item_bow_move(mu_pt_particle *p, const mu_pt_host *h)
{
    const float ratio = (float)p->lifetime / (float)p->initial_lifetime;
    if (p->type == 0x8109) {
        p->scale = p->initial_scale * ratio;
        const int32_t axis = mu_pt_rand(h) % 3;
        p->velocity[axis] = p->velocity[axis] * ratio;
    } else {
        if (ratio > 0.5f)
            p->scale = p->scale + 0.035f;
        else
            p->scale = p->scale - 0.035f;
        if (0.0f > p->scale)
            p->scale = 0.0f;
    }
}
