/* RENDER-EFFECTS-010: the particle kinds of arrows 0x615 lightning_arrow and 0x617 Imperial_arrow (MoveEffect
 * 0x0146a1f9 / 0x0146af38, RENDER-EFFECTS-009). Included after the shared helpers; admission is limited to the
 * verified kind/subtype pairs:
 *   0x8081, 0x8082, 0x8083 / 8   0x615's sparks: one body (create 0x015d377c by the subtype table 0x01616620,
 *                                move 0x01645975 by 0x0168f57c, render 0x0159feab)
 *   0x85fb/2                     0x617's trail (create 0x01613d5d, move 0x0168bbdf, render 0x015ac327)
 *   0x8450/4                     0x617's trail (create 0x0160fc08, move 0x01687e08, render 0x015a86ac)
 *   0x7f73, 0x7f74, 0x7f75 / 0   ArrowNature 0x441's leaves: one body (create 0x015b5a9d, move 0x0161dd24, the
 *                                plain sprite 0x015ae2bf) */
static float rand_range(const mu_pt_host *h, float lo, float hi, int32_t steps);   /* defined below */
static void state(mu_pt_render_call *c, int32_t wrapper, int32_t argument);

static int mu_pt_arrow_kind(int32_t type, int32_t subtype)
{
    return (type >= 0x8081 && type <= 0x8083 && subtype == 8) || (type == 0x85fb && subtype == 2) ||
           (type == 0x8450 && subtype == 4) || (type >= 0x7f73 && type <= 0x7f75 && subtype == 0);
}

static int arrow_leaf(int32_t type)
{
    return type >= 0x7f73 && type <= 0x7f75;
}

static void mu_pt_arrow_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (arrow_leaf(p->type)) {                     /* 0x015b5a9d: a leaf scattered from the arrow */
        p->lifetime = mu_pt_rand(h) % 10 + 15;
        p->scale = (float)(mu_pt_rand(h) % 8 + 4) * 0.03f;
        p->light[0] = p->light[1] = p->light[2] = 1.0f;
        p->velocity[0] = (float)(mu_pt_rand(h) % 32 - 16) * 0.1f;
        p->velocity[1] = (float)(mu_pt_rand(h) % 32 - 16) * 0.1f;
        p->velocity[2] = (float)(mu_pt_rand(h) % 32 - 32) * 0.1f;
        return;
    }
    if (p->subtype == 8) {                         /* 0x015d377c */
        p->initial_lifetime = 5;
        p->lifetime = 5;
        p->scale = scale;
        p->initial_scale = p->scale;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->alpha = 1.0f;
        return;
    }
    p->initial_lifetime = 20;                      /* 0x01613d5d / 0x0160fc08 */
    p->lifetime = 20;
    p->initial_scale = scale;
    p->scale = scale;
    p->rotation = (float)(mu_pt_rand(h) % 360);
    copy3(p->velocity, p->angle);                  /* the angle argument is the flight direction */
    const float speed = rand_range(h, 7.0f, 10.0f, 10);
    for (int k = 0; k < 3; ++k)
        p->velocity[k] = p->velocity[k] * speed;
    p->angle[0] = p->angle[1] = p->angle[2] = 0.0f;   /* 0x00cfcf7b */
}

static void mu_pt_arrow_move(mu_pt_particle *p, const mu_pt_host *h)
{
    if (arrow_leaf(p->type)) {                     /* 0x0161dd24: flutters down until it lies on the ground */
        if (p->frame == 0) {
            for (int k = 0; k < 3; ++k)
                p->velocity[k] = (float)(mu_pt_rand(h) % 32 - 16) * 0.1f + p->velocity[k];
            for (int k = 0; k < 3; ++k)
                p->position[k] = p->position[k] + p->velocity[k];
        }
        const float ground = h && h->terrain_height ? h->terrain_height(h->context, p->position[0], p->position[1])
                                                    : 0.0f;
        if (ground > p->position[2]) {
            p->position[2] = ground;
            p->velocity[0] = p->velocity[1] = p->velocity[2] = 0.0f;
            p->frame = 1;
        }
        p->rotation = (float)(mu_pt_rand(h) % 16) + p->rotation;
        return;
    }
    p->alpha = (float)p->lifetime / (float)p->initial_lifetime;
    if (p->subtype == 8)
        p->scale = p->scale - 0.018f;
    else
        p->scale = p->initial_scale * (p->type == 0x85fb ? 0.4f : 0.2f) + p->scale;
}

/* RenderParticles: the light times the record's alpha; 0x8450/4 subtracts (0x015a86ac). */
static void mu_pt_arrow_render(const mu_pt_particle *p, mu_pt_render_call *out, mu_pt_sprite_call *s)
{
    if (!mu_pt_arrow_kind(p->type, p->subtype) || arrow_leaf(p->type))
        return;   /* the leaves take the plain sprite */
    for (int k = 0; k < 3; ++k)
        s->light[k] = p->light[k] * p->alpha;
    if (p->type == 0x8450)
        state(out, MU_PT_STATE_SUBTRACT, 0);
}
