/* RENDER-WORLDS-M: recorded Uruk nested consumers (world 100 handler
 * 0x00e6f3d5). Included after the shared helpers; admission is limited to
 * the verified kind/subtype pairs. 0x7fdd/3 belongs to RENDER-EFFECTS-004. */
static int mu_pt_worlds_m_kind(int32_t type, int32_t subtype)
{
    return (type == 0x7f5a && (subtype == 69 || subtype == 22)) ||
           (type == 0x7f89 && subtype == 25) || (type == 0x801b && subtype == 7) ||
           (type == 0x8184 && subtype == 2) || (type == 0x7fd5 && subtype == 0);
}

/* 0x0185c113(out, in, angle): Euler rotation by degrees without a matrix. */
static void mu_pt_worlds_m_rotate(float out[3], const float in[3], const float angle[3])
{
    float c[3], s[3];
    for (int k = 0; k < 3; ++k) {
        const float a = angle[k] * 0.01745329238474369f;
        c[k] = (float)cos((double)a);
        s[k] = (float)sin((double)a);
    }
    float t[3];
    t[0] = (c[2] * c[1]) * in[0] + ((c[2] * s[1]) * s[0] - s[2] * c[0]) * in[1] +
           ((c[2] * s[1]) * c[0] + s[2] * s[0]) * in[2];
    t[1] = (s[2] * c[1]) * in[0] + ((s[2] * s[1]) * s[0] + c[2] * c[0]) * in[1] +
           ((s[2] * s[1]) * c[0] - c[2] * s[0]) * in[2];
    t[2] = -s[1] * in[0] + (c[1] * s[0]) * in[1] + (c[1] * c[0]) * in[2];
    copy3(out, t);
}

static void mu_pt_worlds_m_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == 0x7f5a) {                       /* 69: 0x015c92c4, 22: 0x015c6af3 */
        p->lifetime = 60;
        p->scale = (float)(mu_pt_rand(h) % 64 + 64) * p->scale * 0.005f;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        if (p->subtype == 22) {
            p->gravity = (float)(mu_pt_rand(h) % 32 + 60) * 0.1f;
        } else {
            p->gravity = (float)(mu_pt_rand(h) % 16 + 30) * 0.1f;
            copy3(p->angle, p->light);             /* the light is kept in the angle */
        }
        return;
    }
    if (p->type == 0x7f89) {                       /* 0x015ed94f: the 0x14 sheet, narrower */
        p->lifetime = 300;
        p->gravity = (float)(mu_pt_rand(h) % 1000);
        p->alpha = 0.1f;
        p->position[0] = (float)(mu_pt_rand(h) % 200 - 100) + p->position[0];
        p->position[1] = (float)(mu_pt_rand(h) % 200 - 100) + p->position[1];
        p->position[2] = (float)(mu_pt_rand(h) % 20 - 20) + p->position[2];
        p->start[1] = (float)(mu_pt_rand(h) % 100) / 100.0f;
        p->start[2] = p->position[2];
        p->scale = (float)(mu_pt_rand(h) % 20 + 180) * 0.01f * p->scale;
        p->field_7c = (float)(mu_pt_rand(h) % 10) / 100.0f;
        p->velocity[0] = p->velocity[1] = p->velocity[2] = 0.0f;
        return;
    }
    if (p->type == 0x801b) {                       /* 0x015f27cb, subtype 7 0x015f29c6 */
        p->lifetime = 30;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->lifetime = mu_pt_rand(h) % 50 + 20;
        p->gravity = (float)(mu_pt_rand(h) % 20 + 10);
        p->scale *= 0.2f;
        copy3(p->start, p->position);
        p->velocity[2] = (float)(-(mu_pt_rand(h) % 3 + 3));
        if (h && h->scene_state == 5)              /* 0x009b0bc1(SceneFlag) */
            p->light[0] = p->light[1] = p->light[2] = 0.25f;
        p->position[0] = ((float)(mu_pt_rand(h) % 20) - 10.0f) + p->position[0];
        p->position[1] = ((float)(mu_pt_rand(h) % 20) - 10.0f) + p->position[1];
        p->position[2] = ((float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[2];
        return;
    }
    if (p->type == 0x8184) {                       /* 0x015f96f1, ignores the scale argument */
        p->scale = (float)(mu_pt_rand(h) % 100) / 300.0f + 0.2f;
        p->lifetime = mu_pt_rand(h) % 10 + 30;
        p->light[0] = p->light[1] = p->light[2] = 1.0f;
        p->velocity[0] = p->velocity[1] = 0.0f;
        p->velocity[2] = (float)(mu_pt_rand(h) % 100) / 50.0f;
        return;
    }
    /* 0x7fd5/0: 0x015faa34 */
    p->lifetime = mu_pt_rand(h) % 20 + 70;
    p->initial_lifetime = p->lifetime;
    p->rotation = (float)mu_pt_rand(h);
    p->initial_scale = scale;
    float c = (float)cos((double)(float)mu_pt_rand(h));
    c = 0.0f > c ? -c : c;                         /* 0x0184f8ff */
    p->scale = (float)((double)(c + 1.0f) * 0.0075 * (double)scale);
    p->field_7c = p->light[0]; p->field_80 = p->light[1]; p->field_84 = p->light[2];
}

static void mu_pt_worlds_m_move(mu_pt_particle *p, const mu_pt_host *h)
{
    if (p->type == 0x7f5a) {                       /* 69: 0x0163a666, 22: 0x0163685b */
        const float l = (float)p->lifetime / 50.0f;
        if (p->subtype == 22) {
            p->light[0] = l * 0.9f; p->light[1] = l * 0.5f; p->light[2] = l * 0.5f;
            p->gravity -= 0.1f;
        } else {
            for (int k = 0; k < 3; ++k) p->light[k] = l * p->angle[k];
            p->gravity -= 0.04f;
        }
        const float wave = (float)sin((double)(h ? h->world_time : 0.0f));
        p->position[0] = wave * p->gravity * 0.05f + p->position[0];
        p->position[2] = p->position[2] + p->gravity;
        p->scale += 0.04f;
        return;
    }
    if (p->type == 0x7f89) {                       /* 0x01661b07 */
        if (!(p->lifetime > 0)) {
            p->live = 0;
        } else if (p->lifetime > 150) {
            if (1.0f > p->alpha)
                p->alpha = (float)((double)p->alpha + 0.04);
            p->position[2] = p->position[2] + 2.0f;
        } else {
            if (p->alpha > 0.1f)
                p->alpha = p->alpha - 0.025f;
            p->position[2] = p->position[2] - 1.0f;
        }
        return;
    }
    if (p->type == 0x801b) {                       /* 0x01668de1, subtype 7 0x0166920a */
        p->scale += 0.03f;
        p->velocity[0] = (float)(mu_pt_rand(h) % 20 - 10) * 0.1f;
        p->velocity[1] = (float)(mu_pt_rand(h) % 20 - 10) * 0.1f;
        p->velocity[2] += 0.1f;                    /* subtype 7 skips the fade below 10 */
        const float r = (float)(mu_pt_rand(h) % 5);
        p->gravity = (r + ((float)p->lifetime / 5.0f) * 1.5f) + p->gravity;
        p->velocity[0] += 1.0f;
        p->velocity[0] -= (20.0f / (float)p->lifetime) * 100.0f;
        p->rotation += 50.0f;
        float m[12], d[3];
        mu_angle_matrix(p->angle, m);
        mu_vector_rotate(p->velocity, m, d);
        for (int k = 0; k < 3; ++k) p->position[k] = p->start[k] + d[k];
        p->scale = (float)((double)p->scale + (1.0 / (double)p->lifetime) * 2.0);
        p->light[0] *= 0.8f; p->light[1] *= 0.77f; p->light[2] *= 0.77f;
        copy3(p->position, p->start);              /* overwrites the rotated offset */
        p->start[2] = ((float)(mu_pt_rand(h) % 5) + p->start[2]) + 10.0f;
        p->position[2] = p->start[2] + p->gravity;
        return;
    }
    if (p->type == 0x8184) {                       /* 0x016725c5 */
        p->scale = (float)((double)p->scale / 1.05);
        p->velocity[2] += 0.4f;
        if (p->velocity[2] > 8.0f) p->velocity[2] = 8.0f;
        if (p->lifetime < 15)
            for (int k = 0; k < 3; ++k) p->light[k] /= 1.2f;
        return;
    }
    /* 0x7fd5/0: 0x01673f85, a widening spiral about the start */
    const float ratio = (float)p->lifetime / (float)p->initial_lifetime;
    const float t = p->time * 3.1415927410125732f;
    p->position[0] = (float)cos((double)t) * p->initial_scale * ratio;
    p->position[1] = (float)sin((double)t) * p->initial_scale * ratio;
    p->position[2] = t * p->initial_scale;
    mu_pt_worlds_m_rotate(p->position, p->position, p->angle);
    for (int k = 0; k < 3; ++k) p->position[k] = p->start[k] + p->position[k];
    p->rotation = t * ratio * 4.0f + p->rotation;
    p->alpha = (float)sin((double)(ratio * 3.1415927410125732f));
    p->light[0] = p->alpha * p->field_7c;
    p->light[1] = p->alpha * p->field_80;
    p->light[2] = p->alpha * p->field_84;
}

/* 0x01599629: clouds/25 joins 8/9/0x14/0x15 in drawing light times alpha. */
static void mu_pt_worlds_m_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    if (p->type == 0x7f89 && p->subtype == 25)
        for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
}
