/* RENDER-EFFECTS-031. Original addresses and proof in client-particles.md. */
static int mu_pt_world_inner_kind(int32_t type, int32_t sub)
{
    return (type == 0x801c && (sub == 3 || sub == 4 || sub == 7)) ||
           (type == 0x7f89 && (sub == 7 || sub == 10 || sub == 16 || sub == 26)) ||
           (type == 0x7f42 && (sub == 7 || sub == 12)) || (type == 0x7f26 && sub == 2) || (type == 0x802a && sub == 1);
}

static void mu_pt_world_inner_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == 0x7f26) { /* 0x015dd610: converge on the charge OBJECT */
        p->lifetime = 15;
        p->angle[0] = p->angle[1] = p->angle[2] = 0.0f;
        copy3(p->start, p->position);
        float owner[3] = {0};
        (void)pet_owner_origin(p, h, owner);
        for (int k = 0; k < 3; ++k) p->velocity[k] = (owner[k] - p->position[k]) / 10.0f;
        return;
    }
    if (p->type == 0x7f42 && p->subtype == 12) { /* 0x015bd15b */
        p->lifetime = 10;
        p->velocity[0] = p->velocity[1] = 0.0f;
        p->velocity[2] = (float)(mu_pt_rand(h) % 128 + 128) * 0.15f;
        p->scale = ((float)(mu_pt_rand(h) % 64 + 64) * scale) * 0.01f;
        return;
    }
    if (p->type == 0x7f89) {
        if (p->subtype == 10 || p->subtype == 16) { /* 0x015eaf56 / 0x015ebca4 */
            p->light[0] = p->light[1] = p->light[2] = 0.0f;
            p->lifetime = 500;
            for (int k = 0; k < 3; ++k)
                p->position[k] = (float)(mu_pt_rand(h) % 400 - 200) + p->position[k];
            copy3(p->start, p->position);
            if (p->subtype == 16) p->rotation = (float)(mu_pt_rand(h) % 360);
            p->scale = (float)(mu_pt_rand(h) % 15 + 10) / 15.0f + scale;
            const float v = (float)(mu_pt_rand(h) % 10 + 5) * (p->subtype == 16 ? 0.05f : 0.12f);
            p->velocity[0] = p->velocity[1] = v;
            return;
        }
        /* /7 is the common constructor; /26 multiplies its random scale. */
        p->lifetime = 30;
        p->gravity = (float)(mu_pt_rand(h) % 1000);
        for (int k = 0; k < 2; ++k)
            p->position[k] = (float)(mu_pt_rand(h) % 500 - 250) + p->position[k];
        p->position[2] = (float)(mu_pt_rand(h) % 20 + 20) + p->position[2];
        p->start[1] = (float)(mu_pt_rand(h) % 100) / 100.0f;
        p->start[2] = p->position[2];
        const float size = (float)(mu_pt_rand(h) % 20 + 180);
        p->scale = p->subtype == 26 ? (size * p->scale) * 0.01f : size * 0.01f;
        p->field_7c = (float)(mu_pt_rand(h) % 30) / 100.0f + scale;
        return;
    }
    if (p->type == 0x802a) { /* 0x015c4627, common tail 0x015c4b6d */
        p->lifetime = mu_pt_rand(h) % 10 + 20;
        p->scale = (float)(mu_pt_rand(h) % 32 + 50) * 0.01f;
        p->position[0] = (float)(mu_pt_rand(h) % 80 - 40) + p->position[0];
        p->position[1] = (float)(mu_pt_rand(h) % 80 - 40) + p->position[1];
        p->position[2] = (float)(mu_pt_rand(h) % 80) + p->position[2];
        p->angle[0] = (float)(mu_pt_rand(h) % 360);
        p->angle[2] = (float)(mu_pt_rand(h) % 360);
        p->gravity = (float)(mu_pt_rand(h) % 10 + 20) * 0.1f;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        return;
    }
    if (p->type == 0x7f42) { /* 0x015bc141 */
        p->lifetime = 33;
        p->scale = (-(float)(mu_pt_rand(h) % 20) / 100.0f) + p->scale;
        p->rotation = (float)(mu_pt_rand(h) % 360) - 180.0f;
        p->start[0] = p->position[0];
        p->position[0] = (((float)(mu_pt_rand(h) % 2) / 2.0f - 0.0f) * p->scale) + p->position[0];
        p->gravity = ((float)(mu_pt_rand(h) % 100) / 100.0f + 1.8f) * p->scale;
        float v = 0.0f;
        if (mu_pt_rand(h) % 10 >= 3)
            v = ((float)(mu_pt_rand(h) % 20) / 10.0f - 1.0f) * p->scale;
        p->velocity[1] = v;
        p->position[1] = (p->position[0] - p->start[0]) + p->position[1];
        return;
    }
    if (p->subtype == 3) { /* 0x015f3751 */
        p->lifetime = 60;
        p->velocity[2] = -1.0f;
        p->scale = ((float)(mu_pt_rand(h) % 10 + 15) * p->scale) * 0.02f;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->position[0] = ((float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[0];
        p->position[2] = ((float)(mu_pt_rand(h) % 25) - 10.0f) + p->position[2];
        return;
    }
    /* 0x015f4466: this random scale is overwritten for /4 and used by /7. */
    p->rotation = (float)(mu_pt_rand(h) % 360);
    p->scale = (float)(mu_pt_rand(h) % 10 + 10) * 0.02f;
    if (p->subtype == 4) {
        p->lifetime = 20;
        p->velocity[2] = (float)(mu_pt_rand(h) % 5 + 2);
        p->scale = (float)(mu_pt_rand(h) % 10 + 10) * 0.02f + scale;
    } else if (p->subtype == 7) {
        p->lifetime = 60;
        p->velocity[2] = (float)(mu_pt_rand(h) % 4) * 0.1f + 0.8f;
        p->scale = ((float)(mu_pt_rand(h) % 10 + 15) * p->scale) * 0.02f;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->position[0] = ((float)(mu_pt_rand(h) % 18) - 9.0f) + p->position[0];
        p->position[2] = ((float)(mu_pt_rand(h) % 18) - 9.0f) + p->position[2];
        return;
    }
    /* 0x015f5079, subtype 4 position jitter. */
    p->position[0] = ((float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[0];
    p->position[1] = ((float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[1];
    p->position[2] = ((float)(mu_pt_rand(h) % 20) - 10.0f) + p->position[2];
}

static void mu_pt_world_inner_move(mu_pt_particle *p, const mu_pt_host *h)
{
    if (p->type == 0x7f26) { /* 0x01650cc6 */
        if (p->lifetime > 5 && !mu_pt_owner_alive(p, h)) p->lifetime = 5;
        for (int k = 0; k < 3; ++k) p->light[k] = (float)p->lifetime / 5.0f;
        p->scale = p->scale + 0.05f;
        for (int k = 0; k < 3; ++k) p->position[k] = p->start[k] + p->velocity[k];
        copy3(p->start, p->position);
        return;
    }
    if (p->type == 0x7f42 && p->subtype == 12) return; /* 0x0162b8cd: common advance only */
    if (p->type == 0x802a) {
        p->scale = p->scale - 0.013f;
        p->position[2] = p->position[2] + p->gravity;
        p->alpha = p->alpha - 0.05f;
        for (int k = 0; k < 3; ++k) p->light[k] = p->light[k] / 1.02f;
        return;
    }
    if (p->type == 0x7f42) {
        p->rotation = p->position[0] > p->start[0] ? p->rotation + 2.0f : p->rotation - 2.0f;
        p->position[2] = p->position[2] + p->gravity;
        p->scale = p->scale - p->gravity / 95.0f;
        if (0.0f >= p->scale) p->live = 0;
        for (int k = 0; k < 3; ++k) p->light[k] = p->light[k] / 1.007f;
        return;
    }
    if (p->type == 0x7f89) {
        if (p->subtype != 10 && p->subtype != 16) {
            mu_pt_icarus_cloud_move(p, h);
            if (p->subtype == 26)
                p->rotation = (((h ? h->world_time : 0.0f) * 0.02f) * p->field_7c) + p->start[1];
            return;
        }
        if (p->subtype == 16 && p->lifetime <= 10) p->live = 0; /* 0x0165fe20 */
        for (int k = 0; k < 3; ++k) p->position[k] = p->position[k] + p->velocity[k];
        if (p->subtype == 10) p->field_7c = 1.5f;
        float d[3];
        for (int k = 0; k < 3; ++k) d[k] = p->position[k] - p->start[k];
        const float distance = (float)sqrt((double)(d[0]*d[0] + d[1]*d[1] + d[2]*d[2]));
        if (p->subtype == 16) {
            p->rotation = ((float)(mu_pt_rand(h) % 2) + 0.5f) + p->rotation;
            if (50.0f >= distance) {
                for (int k = 0; k < 3; ++k) p->light[k] = p->light[k] + 0.01f;
                if (p->light[0] >= 0.2f) p->light[0] = p->light[1] = p->light[2] = 0.2f;
            } else {
                for (int k = 0; k < 3; ++k) p->light[k] = p->light[k] / 1.05f;
                if (0.001f > p->light[0]) p->live = 0;
            }
            if (distance >= 100.0f) p->live = 0;
            return;
        }
        if (300.0f >= distance) {
            for (int k = 0; k < 3; ++k) p->light[k] = p->light[k] + 0.01f;
            if (p->light[0] >= 0.15f) p->light[0] = p->light[1] = p->light[2] = 0.15f;
        } else if (distance > 300.0f && 500.0f >= distance) {
            for (int k = 0; k < 3; ++k) p->light[k] = p->light[k] / 1.05f;
        } else p->live = 0;
        return;
    }
    if (p->subtype == 3) {
        p->scale = p->scale + 0.005f;
        p->velocity[2] = p->velocity[2] - 0.05f;
        for (int k = 0; k < 3; ++k) p->light[k] = p->light[k] * 0.97f;
    } else if (p->subtype == 7) {
        p->velocity[2] = p->velocity[2] + 0.01f;
        for (int k = 0; k < 3; ++k) p->light[k] = p->light[k] * 0.97f;
    } else {
        p->scale = p->scale + 0.005f;
        p->velocity[2] = p->velocity[2] - 2.5f;
        for (int k = 0; k < 3; ++k) p->light[k] = p->light[k] / 1.1f;
    }
}
