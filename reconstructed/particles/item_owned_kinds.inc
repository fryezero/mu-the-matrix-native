/* RENDER-EFFECTS-020: the two particle kinds the wings 0x2384/0x2385 create with their OBJECT as owner
 * (RenderObjDraw's pre-draw case, reconstructed/renderchar/item_owner_fx.h op 25), after the shared helpers.
 * Admission is limited to the verified pairs (create in CreateParticle 0x015ae7b0, move in MoveParticles
 * 0x01616c80, render in RenderParticles 0x0159123f):
 *   0x810a/0x11  pin_star03 sparks that shrink and fade (create 0x015b25a3, move 0x0161b6ba, render 0x0159faca)
 *   0x81cf/0     magic_ground12, a ring that grows and fades on its owner (create 0x0160baa3, move 0x0168418b,
 *                render 0x015a5eec)
 * Neither reads its OBJECT owner beyond the common block: CreateParticle and MoveParticles copy the owner's
 * +0x158 into +0x54 with z = RequestTerrainHeight (0x01616fee..0x01617071), and 0x81cf/0's move ends a particle
 * whose owner word +0x50 is NULL. Nothing reads the owner's angle +0x164, bones +0x318, scale or live/visible bytes,
 * and the position does not follow the owner: both retire by LifeTime. */

static int mu_pt_item_owned_kind(int32_t type, int32_t subtype)
{
    return (type == 0x810a && subtype == 0x11) || (type == 0x81cf && subtype == 0);
}

static void mu_pt_item_owned_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == 0x81cf) {                       /* 0x0160baa3 (subtypes 0 and 1) */
        p->lifetime = 20;
        p->initial_lifetime = p->lifetime;
        p->initial_scale = scale;
        p->scale = 0.0f;
        p->alpha = 1.0f;
        return;
    }
    p->initial_lifetime = 30;                      /* 0x015b25a3 */
    p->lifetime = p->initial_lifetime;
    p->scale = rand_range(h, 0.5f, 1.0f, 100) * scale;
    p->initial_scale = p->scale;
    p->alpha = 1.0f;
    p->rotation = rand_range(h, 0.0f, 360.0f, 1);
    for (int k = 0; k < 3; ++k)
        p->position[k] = rand_range(h, -10.0f, 10.0f, 1) + p->position[k];
    for (int k = 0; k < 3; ++k)
        p->velocity[k] = rand_range(h, -15.0f, 15.0f, 1) * 0.2f;
}

static void mu_pt_item_owned_move(mu_pt_particle *p)
{
    if (p->type == 0x81cf) {                       /* 0x0168418b */
        if (p->owner == MU_PT_NO_OWNER) {          /* +0x50 == NULL */
            p->live = 0;
            return;
        }
        p->scale = p->initial_scale / (float)p->initial_lifetime + p->scale;
        const int32_t half = p->initial_lifetime / 2;   /* cdq; sub eax, edx; sar eax, 1 */
        if (p->lifetime < half)
            p->alpha = p->alpha - 1.0f / (float)half;
        return;
    }
    p->scale = p->scale - p->initial_scale / (float)p->initial_lifetime;   /* 0x0161b6ba */
    p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;
}

/* RenderParticles: both draw the record's light times its alpha. */
static void mu_pt_item_owned_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    if (mu_pt_item_owned_kind(p->type, p->subtype))
        for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
}
