/* RENDER-WORLDS-L: recorded Karutan/Raklion nested consumers. Included after
 * the shared helpers; admission is deliberately limited to verified subtypes. */
static int mu_pt_worlds_l_kind(int32_t type, int32_t subtype)
{
    return (type == 0x801c && (subtype == 16 || subtype == 8)) ||
           (type == 0x801b && subtype == 4) || (type == 0x801e && subtype == 0) ||
           (type == 0x8086 && subtype == 2) ||
           (type == 0x8087 && subtype == 6) ||
           (type == 0x8089 && subtype == 2);
}

static void mu_pt_worlds_l_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == 0x801b) {                       /* 0x015f27cb, subtype 4 */
        p->lifetime = 30;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->scale = (float)(mu_pt_rand(h) % 6 + 6) * 0.1f;
        p->velocity[2] = -(float)(mu_pt_rand(h) % 3 + 3);
        for (int k = 0; k < 3; ++k) p->light[k] = h && h->scene_state == 5 ? 0.25f : 0.4f;
        p->position[0] += (float)(mu_pt_rand(h) % 20) - 10.0f;
        p->position[1] += (float)(mu_pt_rand(h) % 20) - 10.0f;
        p->position[2] += (float)(mu_pt_rand(h) % 40) - 20.0f;
        p->lifetime = 70;
        p->scale = (float)(mu_pt_rand(h) % 6 + 6) * 0.1f + scale;
        return;
    }
    if (p->type == 0x801c && p->subtype == 8) {    /* 0x015f4466, 0x015f48d5 */
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->scale = (float)(mu_pt_rand(h) % 10 + 10) * 0.02f;
        p->lifetime = 30;
        p->velocity[2] = (float)(mu_pt_rand(h) % 5 + 5);
        p->scale = (float)(mu_pt_rand(h) % 10 + 10) * 0.05f;
        p->position[0] += (float)(mu_pt_rand(h) % 40) - 20.0f;
        p->position[1] += (float)(mu_pt_rand(h) % 40) - 20.0f;
        p->position[2] += (float)(mu_pt_rand(h) % 20) - 10.0f;
        return;
    }
    if (p->type == 0x801e) {                       /* 0x015f1bf7 */
        p->lifetime = 30;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->scale = 1.6f;
        p->velocity[2] = -(float)(mu_pt_rand(h) % 5 + 7);
        p->light[0] = p->light[1] = p->light[2] = 0.2f;
        return;
    }
    if (p->type == 0x801c) {                       /* 0x015f3a6a..0x015f3b1c */
        p->lifetime = 30;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->scale = 0.6f + scale;
        p->velocity[2] = (float)(mu_pt_rand(h) % 3 + 5);
        return;                                   /* no common jitter tail */
    }
    /* 0x015d4350 / 0x015b911e / 0x015d9243. Keep the multiply order. */
    int32_t life = p->type == 0x8086 ? 27 : (p->type == 0x8087 ? 24 : 17);
    p->lifetime = mu_pt_rand(h) % 5 + life;
    p->scale = ((float)(mu_pt_rand(h) % 72 + 72) * 0.01f) * scale;
    p->rotation = (float)(mu_pt_rand(h) % 360);
    p->gravity = (float)(mu_pt_rand(h) % 24 + 100) * 0.1f;
    float drift = (float)(mu_pt_rand(h) % 50) * 0.03f;
    p->velocity[0] = 2.5f + drift;
    p->velocity[1] = (p->type == 0x8086 ? -7.0f : -5.0f) - drift;
    p->velocity[2] = 0.0f;
    p->alpha = 0.0f;
    p->field_7c = p->light[0]; p->field_80 = p->light[1]; p->field_84 = p->light[2];
    p->light[0] = p->light[1] = p->light[2] = 0.0f;
}

static void mu_pt_worlds_l_move(mu_pt_particle *p, const mu_pt_host *h)
{
    if (p->type == 0x801b) {                       /* 0x01668de1 */
        p->scale += 0.03f;
        p->velocity[0] = (float)(mu_pt_rand(h) % 20 - 10) * 0.1f;
        p->velocity[1] = (float)(mu_pt_rand(h) % 20 - 10) * 0.1f;
        p->velocity[2] += 0.1f;
        if (p->lifetime < 10)
            for (int k = 0; k < 3; ++k) p->light[k] /= 1.1f;
        p->rotation -= 1.1f;
        return;
    }
    if (p->type == 0x801c && p->subtype == 8) {    /* 0x01669dfc, no tail */
        p->scale += 0.05f;
        p->velocity[2] -= 0.6f;
        for (int k = 0; k < 3; ++k) p->light[k] /= 1.1f;
        return;
    }
    if (p->type == 0x801e) {                       /* 0x01667fae, 0x0166886e */
        p->scale -= 0.005f;
        p->velocity[2] += 0.1f;
        if (p->lifetime < 8) {
            for (int k = 0; k < 3; ++k) p->light[k] /= 1.2f;
        } else if (p->lifetime > 20) {
            for (int k = 0; k < 3; ++k) p->light[k] *= 1.1f;
        }
        return;
    }
    if (p->type == 0x801c) {                       /* 0x0166a8ca..0x0166aab8 */
        p->scale -= 0.005f;
        p->velocity[2] -= 0.1f;
        if (p->lifetime < 8) {
            for (int k = 0; k < 3; ++k) p->light[k] /= 1.2f;
        } else if (p->lifetime > 20) {
            for (int k = 0; k < 3; ++k) p->light[k] *= 1.1f;
        }
        return;                                   /* skips WATERFALL3's common tail */
    }
    /* 0x01646965 / 0x0162616c / 0x0164bb15. Common movement already ran. */
    if (p->lifetime < 10) p->alpha -= 0.2f;
    else if (1.0f > p->alpha) p->alpha += (float)(mu_pt_rand(h) % 2 + 2) * 0.1f;
    else p->alpha = 1.0f;
    if (0.1f > p->alpha) p->live = 0;
    p->light[0] = p->field_7c * p->alpha;
    p->light[1] = p->field_80 * p->alpha;
    p->light[2] = p->field_84 * p->alpha;
    if (p->scale > 0.0f)
        p->scale -= (float)(mu_pt_rand(h) % 3 + (p->type == 0x8087 ? 6 : 7)) * 0.01f;
    else p->live = 0;
    p->position[0] += p->velocity[0];
    p->position[1] += p->velocity[1];
    p->position[2] += p->gravity;
    p->rotation += 3.0f;
}
