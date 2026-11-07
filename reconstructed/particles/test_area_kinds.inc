/* RENDER-EFFECTS-019: the three kinds Test Area 121's custom slot 0x00d58bd8 asks for besides 0x801c/8
 * (docs/research/client-render-effects-019.md §2). Raklion's custom slot 0x00e949f8 (worlds 57/58) is a copy of
 * it with the same 28 call sites. Each is its own branch of its bitmap's subtype chain in CreateParticle 0x015ae7b0
 * and MoveParticles 0x01616c80, after the shared create and move code (MovePosition with the rotated velocity
 * already ran); RenderParticles draws 0x801e and 0x801b through its default case 0x015ae2bf and 0x801c through
 * 0x015a0297, the same as their other subtypes.
 *   0x801e/7  create 0x015f236c: the drawn bitmap +0x10 becomes WATERFALL4 0x801d or stays WATERFALL5 0x801e
 *             (rand % 2); move 0x016684c6, then 0x801e's light gates 0x0166886e
 *   0x801c/9  create: the prefix 0x015f4466 shared by the subtypes after 0x19, branch 0x015f496e, the position
 *             jitter 0x015f5079; move 0x0166b810 (no WATERFALL3 tail)
 *   0x801b/5  create: the prefix 0x015f27cb..0x015f2daa shared with 0x801b/4 (worlds_l.inc), branch 0x015f30e0;
 *             move 0x01668bc8 (tested before the other subtypes) */

static int mu_pt_test_area_kind(int32_t type, int32_t subtype)
{
    return (type == 0x801e && subtype == 7) || (type == 0x801c && subtype == 9) || (type == 0x801b && subtype == 5);
}

static void mu_pt_test_area_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == 0x801e) {
        p->tex_type = mu_pt_rand(h) % 2 == 0 ? 0x801d : 0x801e;
        p->lifetime = 30;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->scale = (float)(mu_pt_rand(h) % 50) * 0.05f + scale;
        p->velocity[0] = (float)-(mu_pt_rand(h) % 2 + 1);
        p->velocity[1] = (float)-(mu_pt_rand(h) % 2 + 3);
        p->velocity[2] = (float)(mu_pt_rand(h) % 3 + 3);
        return;
    }
    if (p->type == 0x801c) {
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->scale = (float)(mu_pt_rand(h) % 10 + 10) * 0.02f;
        p->lifetime = 30;
        p->velocity[2] = (float)(mu_pt_rand(h) % 5 + 2);
        p->scale = (float)(mu_pt_rand(h) % 5 + 5) * 0.05f + scale;
        p->position[0] = ((float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[0];
        p->position[1] = ((float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[1];
        p->position[2] = ((float)(mu_pt_rand(h) % 20) - 10.0f) + p->position[2];
        return;
    }
    p->lifetime = 30;   /* 0x801b: the shared prefix */
    p->rotation = (float)(mu_pt_rand(h) % 360);
    p->scale = (float)(mu_pt_rand(h) % 6 + 6) * 0.1f;
    p->velocity[2] = (float)-(mu_pt_rand(h) % 3 + 3);
    for (int k = 0; k < 3; ++k)
        p->light[k] = h && h->scene_state == 5 ? 0.25f : 0.4f;
    p->position[0] = ((float)(mu_pt_rand(h) % 20) - 10.0f) + p->position[0];
    p->position[1] = ((float)(mu_pt_rand(h) % 20) - 10.0f) + p->position[1];
    p->position[2] = ((float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[2];
    p->lifetime = 40;   /* subtype 5 */
    p->rotation = (float)(mu_pt_rand(h) % 360);
    p->gravity = (float)(mu_pt_rand(h) % 2 + 2);
    p->scale = (float)(mu_pt_rand(h) % 6 + 6) * 0.1f + scale;
    p->velocity[0] = (float)-(mu_pt_rand(h) % 2 + 2);
    p->velocity[1] = (float)-(mu_pt_rand(h) % 2 + 2);
    p->velocity[2] = (float)(mu_pt_rand(h) % 2 + 1);
    p->position[0] = ((float)(mu_pt_rand(h) % 60) - 30.0f) + p->position[0];
    p->position[1] = ((float)(mu_pt_rand(h) % 60) - 30.0f) + p->position[1];
    p->position[2] = (float)(mu_pt_rand(h) % 10) + p->position[2];
}

static void mu_pt_test_area_move(mu_pt_particle *p)
{
    if (p->type == 0x801e) {
        p->scale = p->scale - 0.005f;
        p->rotation = p->rotation + 1.0f;
        for (int k = 0; k < 3; ++k)
            p->position[k] = p->position[k] + p->velocity[k];
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->light[k] / 1.1f;
        if (p->lifetime < 8) {
            for (int k = 0; k < 3; ++k)
                p->light[k] = p->light[k] / 1.2f;
        } else if (p->lifetime > 20) {
            for (int k = 0; k < 3; ++k)
                p->light[k] = p->light[k] * 1.1f;
        }
        return;
    }
    if (p->type == 0x801c) {
        p->scale = p->scale + 0.005f;
        p->velocity[2] = p->velocity[2] - 2.5f;
    } else {
        p->scale = p->scale + 0.03f;
        p->velocity[2] = p->velocity[2] + 0.1f;
        p->position[0] = p->position[0] + p->velocity[0];
        p->position[1] = p->position[1] + p->velocity[1];
        p->position[2] = (p->gravity + p->velocity[2]) + p->position[2];
    }
    for (int k = 0; k < 3; ++k)
        p->light[k] = p->light[k] / 1.1f;
}
