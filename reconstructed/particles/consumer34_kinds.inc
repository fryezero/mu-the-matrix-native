/* RENDER-EFFECTS-034: particle pairs that world, item and Muun producers already request.
 * Original case addresses (CreateParticle 0x015ae7b0 / MoveParticles 0x01616c80 / RenderParticles 0x0159123f)
 * are in docs/research/client-render-effects-034.md. One table row per pair; the forms are:
 *   PLAIN   the pair's own short create/move case, the plain sprite
 *   ITEM    initial lifetime/scale words +0x4c/+0x1c, alpha +0x44, the light times alpha at draw
 *   FOLLOW  ITEM whose draw replaces the position by the owner point OBJECT +0x1f4 + 12 * arg8 plus its start
 *   PULSE   the saved colour +0x7c..+0x84 times an alpha that rises to the middle of the life and falls
 *   NODRAW  the blend state without a sprite (0x7efa's subtype table sends 3 to the exit) */
enum { MU_PT34_PLAIN, MU_PT34_ITEM, MU_PT34_FOLLOW, MU_PT34_PULSE, MU_PT34_NODRAW };

static const struct mu_pt34_row { int32_t type, subtype, form; } mu_pt34_rows[] = {
    {0x8016, 5, MU_PT34_PLAIN},  {0x7ef7, 11, MU_PT34_PLAIN}, {0x7f5a, 43, MU_PT34_PLAIN},
    {0x7f5a, 47, MU_PT34_PLAIN}, {0x7efa, 3, MU_PT34_NODRAW},
    {0x8616, 0, MU_PT34_ITEM},   {0x7fe0, 10, MU_PT34_ITEM},  {0x84d1, 2, MU_PT34_ITEM},
    {0x850b, 5, MU_PT34_ITEM},   {0x807e, 14, MU_PT34_ITEM},  {0x807f, 14, MU_PT34_ITEM},
    {0x8080, 14, MU_PT34_ITEM},  {0x855d, 2, MU_PT34_FOLLOW},
    {0x8081, 1, MU_PT34_PULSE},  {0x8082, 1, MU_PT34_PULSE},  {0x7ef7, 19, MU_PT34_PULSE},
};

static const struct mu_pt34_row *mu_pt34_row(int32_t type, int32_t subtype)
{
    for (size_t i = 0; i < sizeof mu_pt34_rows / sizeof mu_pt34_rows[0]; ++i)
        if (mu_pt34_rows[i].type == type && mu_pt34_rows[i].subtype == subtype)
            return &mu_pt34_rows[i];
    return NULL;
}

static int mu_pt_consumer34_kind(int32_t type, int32_t subtype)
{
    return mu_pt34_row(type, subtype) != NULL;
}

static void mu_pt_consumer34_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    switch (p->type) {
    case 0x8016:                                     /* 0x015f16b2, then subtype 0's 0x015f1827 */
        p->lifetime = 20;
        p->velocity[0] = (float)(mu_pt_rand(h) % 10 - 5) * 0.4f;
        p->velocity[1] = 0.0f;
        p->velocity[2] = (float)(mu_pt_rand(h) % 10 + 5) * 0.2f;
        copy3(p->start, p->position);
        return;
    case 0x7ef7:
        if (p->subtype == 11) {                      /* 0x015ef0ac */
            p->lifetime = mu_pt_rand(h) % 10 + 130;
            p->gravity = (float)(mu_pt_rand(h) % 2) + 2.0f;
            p->scale = (((float)(mu_pt_rand(h) % 20) + 20.0f) / 100.0f) * scale;
            return;
        }
        break;                                       /* /19: 0x015ef979, the pulse below */
    case 0x7f5a:
        if (p->subtype == 43) {                      /* 0x015c7859: Clud64 */
            p->tex_type = 0x7ffd;
            p->lifetime = 40;
            p->rotation = (float)(mu_pt_rand(h) % 360);
            p->angle[0] = 90.0f;
            p->velocity[0] = (float)(mu_pt_rand(h) % 20) / 10.0f - 1.0f;
            p->velocity[1] = 2.0f;
            p->velocity[2] = 15.0f;
            return;
        }
        p->tex_type = 0x7f84;                        /* 0x015c7d85: Explotion01's sheet word, drawn whole */
        p->lifetime = 5;
        p->scale = (float)(mu_pt_rand(h) % 50) * 0.01f + p->scale;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        return;
    case 0x7efa:                                     /* 0x015c36fb */
        p->lifetime = 20;
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = (float)(mu_pt_rand(h) % 4 - 2);
        return;
    case 0x8616:                                     /* 0x0161472d */
        p->lifetime = 4;
        p->initial_lifetime = p->lifetime;
        p->scale = scale;
        p->alpha = 1.0f;
        return;
    case 0x7fe0:                                     /* 0x015e59d3 */
        p->lifetime = 16;
        p->initial_lifetime = p->lifetime;
        p->scale = scale;
        p->initial_scale = scale / (float)p->lifetime;
        p->alpha = 1.0f;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        for (int k = 0; k < 3; ++k)
            p->angle[k] = rand_range(h, 0.0f, 360.0f, 1);
        p->velocity[2] = rand_range(h, 1.5f, 3.0f, 100);
        p->velocity[0] = p->velocity[1] = 0.0f;
        return;
    case 0x84d1:                                     /* 0x0160ca17 */
    case 0x850b:                                     /* 0x015d2a0d */
        p->lifetime = p->type == 0x84d1 ? 30 : 20;
        p->initial_lifetime = p->lifetime;
        p->alpha = 0.0f;
        p->scale = scale;
        p->initial_scale = (scale * (p->type == 0x84d1 ? 1.2f : 2.0f) - scale) / (float)p->lifetime;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        if (p->type == 0x84d1)
            p->angle[0] = p->angle[1] = p->angle[2] = 0.0f;
        p->velocity[2] = rand_range(h, 1.5f, 2.5f, 100);
        p->velocity[0] = p->velocity[1] = 0.0f;
        return;
    case 0x807e: case 0x807f: case 0x8080:           /* 0x015cee63 */
        p->lifetime = 20;
        p->initial_lifetime = p->lifetime;
        p->scale = (rand_range(h, 50.0f, 100.0f, 1) * 0.01f) * scale;
        p->initial_scale = p->scale;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        p->alpha = 1.0f;
        p->velocity[2] = 2.5f;
        return;
    case 0x855d:                                     /* 0x0161113b */
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
    default:
        break;
    }
    /* PULSE: 0x8081, 0x8082 /1 0x015d2f7e (life 5); 0x7ef7/19 0x015ef979 (life 7) */
    p->initial_lifetime = p->type == 0x7ef7 ? 7 : 5;
    p->lifetime = p->initial_lifetime;
    p->initial_scale = scale - (scale / 10.0f) * (float)(mu_pt_rand(h) % 5);
    p->alpha = 0.0f;
    p->rotation = (float)(mu_pt_rand(h) % 360);
    p->gravity = 0.0f;
    p->field_7c = p->light[0];
    p->field_80 = p->light[1];
    p->field_84 = p->light[2];
    p->light[0] = p->light[1] = p->light[2] = 0.0f;
}

static void mu_pt_consumer34_move(mu_pt_particle *p, const mu_pt_host *h)
{
    (void)h;
    const int32_t half = p->initial_lifetime / 2;    /* cdq; sub eax, edx; sar eax, 1 */
    switch (p->type) {
    case 0x8016:                                     /* 0x01667872, subtype 0's body */
        p->scale = p->scale - 0.02f;
        if (0.0f > p->scale)
            p->scale = 0.0f;
        p->velocity[0] = p->velocity[0] * 0.95f;
        p->velocity[1] = p->velocity[1] * 0.95f;
        p->position[2] = p->position[2] + 1.0f;
        p->light[0] = (float)p->lifetime / 25.0f;
        p->light[1] = p->light[0];
        p->light[2] = p->light[0];
        return;
    case 0x7ef7:
        if (p->subtype == 11) {                      /* 0x0166412b */
            p->position[2] = p->position[2] + p->gravity;
            p->scale = p->scale - 0.0005f;
            return;
        }
        break;                                       /* /19: 0x01664f41 */
    case 0x7f5a:
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->light[k] / 1.02f;
        if (p->subtype == 43) {                      /* 0x01637b46 */
            p->scale = p->scale + 0.08f;
            return;
        }
        if (0.05f >= p->light[0])                    /* 0x016380a2 */
            p->lifetime = 0;
        p->scale = p->scale + 1.0f;
        return;
    case 0x7efa:                                     /* 0x01632a95 */
        if (p->lifetime > 10)
            p->scale = p->scale + 0.02f;
        else
            p->scale = p->scale - 0.021f;
        return;
    case 0x8616:                                     /* 0x0168c63c */
        p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;
        return;
    case 0x7fe0:                                     /* 0x0162ee1b */
        p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;
        p->scale = p->scale - p->initial_scale;
        return;
    case 0x84d1:                                     /* 0x016856a7 */
    case 0x850b:                                     /* 0x01644ac1 */
        if (p->lifetime > half)
            p->alpha = 1.0f / (float)half + p->alpha;
        else
            p->alpha = p->alpha - 1.0f / (float)half;
        p->scale = p->scale + p->initial_scale;
        return;
    case 0x807e: case 0x807f: case 0x8080:           /* 0x01642509 */
        if (p->lifetime < half)
            p->alpha = p->alpha - 1.0f / (float)half;
        p->scale = p->scale - p->initial_scale / (float)p->initial_lifetime;
        return;
    case 0x855d:                                     /* 0x01689b2d */
        if (p->owner == MU_PT_NO_OWNER) {
            p->live = 0;
            return;
        }
        if (p->lifetime > half)
            p->scale = p->scale + p->initial_scale;
        else
            p->scale = p->scale - p->initial_scale;
        p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;
        return;
    default:
        break;
    }
    /* PULSE: 0x01644f6a / 0x01664f41 */
    const float span = (float)p->initial_lifetime - (float)half;
    const float t = (p->lifetime > half ? (float)(p->initial_lifetime - p->lifetime) : (float)p->lifetime) / span;
    p->alpha = t * 0.9f + 0.1f;
    p->scale = (t * 0.5f + 0.5f) * p->initial_scale;
    if (0.1f > p->alpha)
        p->live = 0;
    p->light[0] = p->field_7c * p->alpha;
    p->light[1] = p->field_80 * p->alpha;
    p->light[2] = p->field_84 * p->alpha;
}

/* RenderParticles: 0 when the pair sets its blend state and draws no sprite. */
static int mu_pt_consumer34_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    const struct mu_pt34_row *row = mu_pt34_row(p->type, p->subtype);
    if (!row)
        return 1;
    if (row->form == MU_PT34_NODRAW)
        return 0;
    if (row->form == MU_PT34_ITEM || row->form == MU_PT34_FOLLOW)
        for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
    return 1;
}

/* RenderParticles 0x015aa801 (0x855d/2): a NULL owner clears live; otherwise the position becomes the owner
 * point OBJECT +0x1f4 + 12 * arg8 plus the record's start, before the sprite. Other pairs are left alone. */
int mu_pt_consumer34_follow(mu_pt_particle *p, const float point[3])
{
    const struct mu_pt34_row *row = mu_pt34_row(p->type, p->subtype);
    if (!row || row->form != MU_PT34_FOLLOW)
        return 1;
    if (p->owner == MU_PT_NO_OWNER || !point) {
        p->live = 0;
        return 0;
    }
    for (int k = 0; k < 3; ++k) p->position[k] = point[k] + p->start[k];
    return 1;
}
