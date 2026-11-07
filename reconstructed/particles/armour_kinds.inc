/* RENDER-EFFECTS-017: the particle kinds the armour owner-effect programs request (RENDER-ITEMS-002Q,
 * reconstructed/renderchar/item_owner_fx.h), after the shared helpers. Admission is limited to the verified
 * kind/subtype pairs (create in CreateParticle 0x015ae7b0, move in MoveParticles 0x01616c80, render in
 * RenderParticles 0x0159123f):
 *   0x810a/7     sparks thrown at the OBJECT angle (create 0x015b143f, move 0x0161a91d, plain sprite 0x0159f7e9)
 *   0x810a/0xf   a drift along the request's direction (create 0x015b227a, move 0x0161b3d8, plain sprite 0x0159f7e9)
 *   Spark03 0x7f26/0x26  falling sparks (create 0x015e1113 = jump table 0x016166cc entry 0x25, move 0x01654b63 =
 *                table 0x0168f628 entry 0x26, plain sprite 0x015a531f)
 * 0x810a's three subtypes share the subtype chain of 0x810a's case (0x015b1435, 0x0161a913, 0x0159f7ae); the
 * render subtype table 0x015ae557 sends 7 to the plain sprite that 0xf, 0x14 and 0x15 reach by compare. */

static int mu_pt_armour_kind(int32_t type, int32_t subtype)
{
    return (type == 0x810a && (subtype == 7 || subtype == 0xf)) || (type == MU_PT_BITMAP_SPARK3 && subtype == 0x26);
}

static void mu_pt_armour_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == MU_PT_BITMAP_SPARK3) {          /* 0x015e1113 */
        p->lifetime = mu_pt_rand(h) % 5 + 30;
        p->scale = (float)(mu_pt_rand(h) % 5) / 10.0f + 0.2f;
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = (float)(mu_pt_rand(h) % 5) + -2.0f;
        p->gravity = 2.5f;
        /* light = vec3(light argument) (0x009fa1cb, then 0x00cfc8f2): the light it already holds */
        return;
    }
    if (p->subtype == 7) {                         /* 0x015b143f */
        p->lifetime = mu_pt_rand(h) % 5 + 50;
        p->scale = scale;
        p->velocity[0] = (float)(mu_pt_rand(h) % 3) + -1.0f;
        p->velocity[1] = (float)(mu_pt_rand(h) % 5);
        p->velocity[2] = (float)(mu_pt_rand(h) % 3) + -1.0f;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        return;
    }
    p->lifetime = 30;                              /* 0x015b227a */
    p->initial_lifetime = p->lifetime;
    p->initial_scale = p->scale;
    p->rotation = rand_range(h, 0.0f, 360.0f, 1);
    copy3(p->velocity, p->angle);                  /* 0x00cfc8f2: the request's direction becomes the velocity */
    p->angle[0] = p->angle[1] = p->angle[2] = 0.0f; /* 0x00cfcede(0) */
}

static void mu_pt_armour_move(mu_pt_particle *p, const mu_pt_host *h)
{
    if (p->type == MU_PT_BITMAP_SPARK3) {          /* 0x01654b63 */
        p->velocity[0] = (float)sin((double)((float)(mu_pt_rand(h) % 360) * 0.017453292f)) + p->velocity[0];
        p->velocity[1] = (float)cos((double)((float)(mu_pt_rand(h) % 360) * 0.017453292f)) + p->velocity[1];
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = p->velocity[k] * 0.85f;   /* 0x00cfcd74 */
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->light[k] / 1.05f;         /* 0x00cfcddf */
        p->scale = p->scale - 0.01f;
        p->position[2] = p->position[2] - p->gravity;
        p->lifetime = p->lifetime - 1;
        if (p->lifetime <= 0)
            p->live = 0;
        return;
    }
    if (p->subtype == 7) {                         /* 0x0161a91d */
        if (p->lifetime <= 45) {
            p->velocity[0] = (float)sin((double)((float)(mu_pt_rand(h) % 360) * 0.017453292f)) + p->velocity[0];
            p->velocity[1] = (float)cos((double)((float)(mu_pt_rand(h) % 360) * 0.017453292f)) + p->velocity[1];
        }
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->light[k] / 1.005f;
        p->rotation = rand_range(h, -10.0f, 10.0f, 1) + p->rotation;
        {   /* MovePosition 0x012af52d(position, -angle (0x00cfca12), velocity): the reverse turn */
            const float back[3] = {-p->angle[0], -p->angle[1], -p->angle[2]};
            float m[12], d[3];
            mu_angle_matrix(back, m);
            mu_vector_rotate(p->velocity, m, d);
            for (int k = 0; k < 3; ++k)
                p->position[k] = p->position[k] + d[k];
        }
        p->scale = p->scale - 0.01f;
        p->lifetime = (int32_t)((double)p->lifetime - 0.1);   /* cvtsi2sd, subsd 0.1, cvttsd2si */
        if (p->lifetime <= 0 || 0.0f >= p->scale)
            p->live = 0;
        return;
    }
    if ((float)p->lifetime / (float)p->initial_lifetime > 0.5f)   /* 0x0161b3d8 */
        p->scale = p->scale + 0.015f;
    else
        p->scale = p->scale - 0.015f;
    if (0.0f > p->scale)
        p->scale = 0.0f;
    p->rotation = p->rotation + 10.0f;
    p->velocity[0] = rand_range(h, -0.5f, 0.5f, 10) + p->velocity[0];
    p->velocity[1] = rand_range(h, -0.5f, 0.5f, 10) + p->velocity[1];
    p->velocity[2] = p->velocity[2] - 0.15f;
}

/* RenderParticles: all three take the plain sprite (the record's light, rotation, full cell, axes 4). */
