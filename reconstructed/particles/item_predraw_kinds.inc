/* RENDER-EFFECTS-021: the three particle kinds the item pre-draw programs (RenderObjDraw's own type case,
 * reconstructed/renderchar/item_owner_fx.h op 14, no owner) create and no other pool reconstructs. Included
 * after the shared helpers; admission is limited to the verified pairs (create in CreateParticle 0x015ae7b0,
 * move in MoveParticles 0x01616c80, render in RenderParticles 0x0159123f):
 *   Clud64 0x7ffd/0x1b   bow 0x1316: a cloud that grows and fades over 15 steps (create 0x015c304a in the
 *                        subtype chain from 0x015c07c8, move 0x0163274d, render 0x0159504f)
 *   Shiny01 0x7f66/5     0x230c, 0x2496: a glint that rises and dims (the Shiny01 case 0x015e5c73, subtype 5
 *                        0x015e60e5; move 0x01658bd3 in the case 0x016584c2; the default render 0x015ae2bf)
 *   shiny06 0x8180/5     0x23ef, 0x2400, 0x2405: subtype 5 has no block in any of the three switches. Create's
 *                        table 0x016167a0[5], move's 0x0168f700[5] and render's 0x015ae50f[5] go straight to
 *                        each switch's end (0x015e93ab, 0x0165c194, 0x0159a5a6). The record keeps the common
 *                        initialisation (LifeTime 2) and lives two steps. Its render binds the bitmap and sets
 *                        the common blend state but draws no sprite.
 * Neither kind has an owner (argument 7 is 0). */

static int mu_pt_item_predraw_kind(int32_t type, int32_t subtype)
{
    return (type == 0x7ffd && subtype == 0x1b) || (type == 0x7f66 && subtype == 5) ||
           (type == 0x8180 && subtype == 5);
}

static void mu_pt_item_predraw_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == 0x7ffd) {                       /* 0x015c304a */
        p->initial_lifetime = 15;
        p->lifetime = p->initial_lifetime;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        /* +0x38 = the light argument again (0x00cfc8f2), as the common block left it */
        p->alpha = 1.0f;
        for (int k = 0; k < 3; ++k)                /* 0x011ff622(-0.5, 0.5, 1): one rand each, always 0 */
            p->velocity[k] = rand_range(h, -0.5f, 0.5f, 1);
        return;
    }
    if (p->type == 0x7f66) {
        p->lifetime = 18;                          /* the Shiny01 case's head 0x015e5c73 */
        p->angle[0] = 45.0f;
        p->lifetime = mu_pt_rand(h) % 10 + 10;     /* 0x015e60e5 */
        p->scale = (float)(mu_pt_rand(h) % 10) * 0.02f + scale;
        p->position[0] = (float)(mu_pt_rand(h) % 10 - 5) + p->position[0];
        p->position[1] = (float)(mu_pt_rand(h) % 10 - 5) + p->position[1];
        p->gravity = -(float)(mu_pt_rand(h) % 10) * 0.3f;
    }
    /* 0x8180/5: nothing beyond the common block */
}

static void mu_pt_item_predraw_move(mu_pt_particle *p)
{
    if (p->type == 0x7ffd) {                       /* 0x0163274d */
        p->alpha = (float)p->lifetime / (float)p->initial_lifetime;
        p->scale = p->scale + 0.04f;
        return;
    }
    if (p->type == 0x7f66) {                       /* 0x01658bd3 */
        p->rotation = p->rotation + 10.0f;
        p->position[2] = p->position[2] + p->gravity;
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->light[k] / 1.02f;
        p->scale = p->scale - 0.01f;
    }
}

/* RenderParticles: Clud64/0x1b draws its light times its alpha (0x00cfcb3c), Shiny01/5 the plain sprite;
 * shiny06/5 returns 0 (the blend state without a sprite). */
static int mu_pt_item_predraw_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    if (p->type == 0x7ffd && p->subtype == 0x1b)
        for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
    return !(p->type == 0x8180 && p->subtype == 5);
}
