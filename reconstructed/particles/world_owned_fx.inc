/* RENDER-EFFECTS-006: the particle kinds of the world objects' owned effects and of Old Kethotum type 15.
 * Included after the shared helpers; admission is limited to the verified kind/subtype pairs:
 *   flare01 0x7ef7/9    the shoal effect 0x199's trail (MoveEffect 0x01435dfb)
 *   Spark02 0x7f25/15   the sea leaf 0x59a/3's sparks, owned by the effect (0x014eda39)
 *   0x7efa/2            Old Kethotum type 15's mist (RENDER-WORLDS-P, scale 0.25)
 *   Spark03 0x7f26/14   Old Kethotum type 15's sparks (scale 0.06) */
static int mu_pt_world_owned_kind(int32_t type, int32_t subtype)
{
    return (type == 0x7ef7 && subtype == 9) || (type == 0x7f25 && subtype == 15) ||
           (type == 0x7efa && subtype == 2) || (type == 0x7f26 && subtype == 14);
}

static void mu_pt_world_owned_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    switch (p->type) {
    case 0x7ef7:                                   /* 0x015eece3: lives 40 steps per unit of scale */
        p->lifetime = mu_pt_cvttss2si(40.0f * p->scale);
        break;
    case 0x7f25:                                   /* 0x015dc098 (the kind's shared size), 0x015dce61 */
        p->scale = (float)(mu_pt_rand(h) % 4 + 4) * 0.1f;
        p->lifetime = mu_pt_rand(h) % 12 + 12;
        p->scale = scale;
        copy3(p->start, p->light);
        break;
    case 0x7efa: {                                 /* 0x015c336e, subtypes 1 and 2 */
        float m[12], v[3];
        p->scale = 0.1f;
        p->start[0] = scale;                       /* subtype 2 only (0x015c3397) */
        p->lifetime = mu_pt_rand(h) % 10 + 20;
        for (int k = 0; k < 3; ++k)
            p->position[k] = (float)(mu_pt_rand(h) % 50 - 25) + p->position[k];
        p->gravity = 1.0f;
        for (int k = 0; k < 3; ++k)
            p->angle[k] = (float)(mu_pt_rand(h) % 360);
        mu_angle_matrix(p->angle, m);
        for (int k = 0; k < 3; ++k)
            v[k] = 0.8f * 0.5f;
        mu_vector_rotate(v, m, p->velocity);
        p->rotation = (float)(mu_pt_rand(h) % 20 - 10);
        break;
    }
    case 0x7f26:                                   /* 0x015de717 (jump table 0x016166cc, entry 13) */
        if (mu_pt_rand(h) % 2 != 0)
            break;                                 /* the common LifeTime 2 */
        p->alpha = 1.0f;
        p->velocity[0] = (float)(mu_pt_rand(h) % 4) + -4.0f;
        p->velocity[1] = (float)(mu_pt_rand(h) % 4);
        p->velocity[2] = (float)(mu_pt_rand(h) % 4);
        p->lifetime = 30;
        p->scale = (float)(mu_pt_rand(h) % 5) / 10.0f + 0.4f;
        break;
    default:
        break;
    }
}

static void mu_pt_world_owned_move(mu_pt_particle *p, const mu_pt_host *h)
{
    switch (p->type) {
    case 0x7ef7:                                   /* 0x01663eaf: shrinks; brightens while young, then dims */
        p->scale = p->scale - 0.011f;   /* 0x01aa6334 */
        if (!p->live)
            p->lifetime = 0;
        if (0.0f >= p->scale)
            p->lifetime = 0;
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->lifetime >= 75 ? p->light[k] * 1.05f : p->light[k] / 1.05f;
        break;
    case 0x7f25: {                                 /* 0x0165006b (subtype 15: 0x01650167, default fall 0x016506bc) */
        const float l = (float)p->lifetime / 16.0f;
        if (p->lifetime < 0)
            p->live = 0;
        for (int k = 0; k < 3; ++k)
            p->light[k] = l;
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->light[k] * p->start[k];   /* the creation colour */
        p->position[2] = p->position[2] + p->gravity;
        p->gravity = p->gravity - 2.0f;
        const float ground = h && h->terrain_height ? h->terrain_height(h->context, p->position[0], p->position[1])
                                                    : 0.0f;
        if (ground > p->position[2]) {
            p->position[2] = ground;
            p->gravity = -p->gravity * 0.6f;
            p->lifetime = p->lifetime - 4;
        }
        for (int k = 0; k < 3; ++k)
            p->position[k] = p->position[k] + p->velocity[k];
        break;
    }
    case 0x7efa:                                   /* 0x016329f8: swells and shrinks with its lifetime */
        p->scale = (float)sin((double)((float)p->lifetime * 2.0f * 0.0174532924f)) * p->start[0];   /* pi / 180 */
        break;
    case 0x7f26:                                   /* 0x01651e01 (jump table 0x0168f628) */
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->light[k] / 1.05f;
        p->scale = p->scale - 0.01f;
        p->alpha = p->alpha - 0.001f;   /* 0x01a7e308 */
        if (0.0f >= p->alpha)
            p->live = 0;
        break;
    default:
        break;
    }
}

/* RenderParticles: 0x7ef7/9, 0x7f25/15 and 0x7f26/14 take the kinds' plain sprite; 0x7efa's subtype table
 * 0x015ae4bf sends subtype 2 to 0x015954cc, past the sprite: only the blend state is set. Returns 0 then. */
static int mu_pt_world_owned_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    (void)s;
    return !(p->type == 0x7efa && p->subtype == 2);
}
