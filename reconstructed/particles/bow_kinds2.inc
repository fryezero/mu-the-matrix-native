/* RENDER-EFFECTS-011: the bows' remaining particle kinds (the 33-bow scenes), after bow_kinds.inc.
 * Admission is limited to the verified kind/subtype pairs (create in CreateParticle 0x015ae7b0, move in
 * MoveParticles 0x01616c80, render in RenderParticles 0x0159123f):
 *   Flare 0x7f78/5           0x12fa's flares (create 0x015bea78, move 0x0162d771, render 0x015983fa)
 *   Smoke_line 0x83b3/1      0x1320/0x1323 (create 0x015cfe72, move 0x0164316e, plain sprite 0x015a3d78)
 *   Spark04 0x8155/2         0x1320/0x1323 (create 0x0160b267, move 0x01683a73, render 0x015a5aa0)
 *   smoke01 0x7f5a/0x18/0x4e 0x12fe/0x130e (create 0x015c6bcd, move 0x01636a33 / 0x0163e3c9, plain 0x01596eaa)
 *   smoke01 0x7f5a/0x7a      0x131e (create 0x015cb8ee, move 0x0163e5d1, plain sprite)
 *   firehik03 0x8085/0x11    0x1302 (create 0x015da370, move 0x0164dbdb, plain sprite 0x01594d3f)
 *   pin_star02_pupple 0x810c/0  0x131e (create 0x0160843e table, move 0x01681c64, plain sprite 0x015a4de5)
 *   Snow_Chip02_red 0x83b8/2 0x1326 (create 0x015e30d4, move 0x01657383, plain sprite 0x015aa005)
 *   firehik01 0x8084/0x1e    0x1326 (create 0x015d6c25, move 0x0164a207, render 0x015a4461)
 *   flare_mono 0x8184/1      0x12ff (create 0x015f95ef, move 0x0167252c, plain sprite 0x0159cf8f)
 *   lighting_mega01..03 0x8081..0x8083/0  0x130c (create 0x015d2e4c, move 0x01644e1d, plain sprite 0x015a006f) */

static int mu_pt_bow2_kind(int32_t type, int32_t subtype)
{
    switch (type) {
    case 0x7f78: return subtype == 5;
    case 0x83b3: return subtype == 1;
    case 0x8155: return subtype == 2;
    case MU_PT_BITMAP_SMOKE: return subtype == 0x18 || subtype == 0x4e || subtype == 0x7a;
    case 0x8085: return subtype == 0x11;
    case 0x810c: return subtype == 0;
    case 0x83b8: return subtype == 2;
    case 0x8084: return subtype == 0x1e;
    case 0x8184: return subtype == 1;
    case 0x8081: case 0x8082: case 0x8083: return subtype == 0;
    default: return 0;
    }
}

static void bow2_angle_rotate(const float angle[3], const float in[3], float out[3])
{   /* AngleMatrix 0x00cff32a, VectorRotate 0x00d000ad */
    float m[12];
    mu_angle_matrix(angle, m);
    mu_vector_rotate(in, m, out);
}

static void mu_pt_bow2_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    switch (p->type) {
    case 0x7f78:                                   /* 0x015bea78: the shared flare body, subtype 5 */
        p->lifetime = 60;
        p->lifetime = 40;
        p->gravity = (float)(mu_pt_rand(h) % 100) / 100.0f * 5.0f + 1.0f;
        p->velocity[0] = (float)(mu_pt_rand(h) % 300 - 150);
        p->scale = (float)(mu_pt_rand(h) % 6) * 0.01f + scale;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->angle[0] = p->angle[1] = p->angle[2] = 0.0f;
        copy3(p->start, p->position);
        return;
    case 0x83b3:                                   /* 0x015cfe72 */
        p->lifetime = 20;
        p->initial_lifetime = p->lifetime;
        p->alpha = 1.0f;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->initial_scale = p->scale;
        return;
    case 0x8155:                                   /* 0x0160b267: Spark03/0x1e's body with five sizes */
        p->lifetime = mu_pt_rand(h) % 5 + 50;
        p->scale = (float)(mu_pt_rand(h) % 5) / 10.0f + 0.2f;
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = (float)(mu_pt_rand(h) % 5) + -2.0f;
        p->gravity = 0.5f;
        return;
    case MU_PT_BITMAP_SMOKE:                       /* 0x015c6bcd (0x18, 0x4e) / 0x015cb8ee (0x7a) */
        p->lifetime = 32;
        if (p->subtype == 0x7a) {
            p->initial_lifetime = p->lifetime;
            p->field_7c = p->light[0];             /* the colour, kept at +0x7c */
            p->field_80 = p->light[1];
            p->field_84 = p->light[2];
        }
        p->scale = (float)(mu_pt_rand(h) % 32 + 48) * 0.01f * scale + scale;
        p->angle[0] = (float)(mu_pt_rand(h) % 360);
        p->rotation = (float)(mu_pt_cvttss2si(h ? h->world_time : 0.0f) % 360);
        return;
    case 0x8085:                                   /* 0x015da370 */
        p->lifetime = 10;
        p->initial_lifetime = p->lifetime;
        p->initial_scale = scale;
        p->scale = scale;
        p->rotation = (float)mu_pt_rand(h);
        return;
    case 0x810c:                                   /* 0x0160844b */
        p->lifetime = 50;
        p->initial_lifetime = p->lifetime;
        p->scale = scale;
        p->initial_scale = scale;
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = rand_range(h, -1.0f, 1.0f, 10);
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        return;
    case 0x83b8: {                                 /* 0x015e30ef: a sideways jump, then a scattered fall */
        p->lifetime = 20;
        p->initial_lifetime = p->lifetime;
        p->initial_scale = p->scale;
        p->alpha = 1.0f;
        const float a = rand_range(h, -10.0f, 10.0f, 1);
        const float b = rand_range(h, -10.0f, 10.0f, 1);
        const float v[3] = {a, 0.0f, b};
        float d[3];
        bow2_angle_rotate(p->angle, v, d);
        for (int k = 0; k < 3; ++k)
            p->position[k] = p->position[k] + d[k];
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        const float z = rand_range(h, -0.0f, 6.0f, 1);   /* the arguments are evaluated last to first */
        const float y = rand_range(h, -3.0f, 3.0f, 1);
        const float x = rand_range(h, -3.0f, 3.0f, 1);
        p->velocity[0] = x;
        p->velocity[1] = y;
        p->velocity[2] = z;
        return;
    }
    case 0x8084: {                                 /* 0x015d6c25: a push of 7 along the angle */
        p->initial_lifetime = 10;
        p->lifetime = 10;
        p->initial_scale = scale;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->alpha = 1.0f;
        const float v[3] = {0.0f, -7.0f, 0.0f};
        bow2_angle_rotate(p->angle, v, p->velocity);
        return;
    }
    case 0x8184:                                   /* 0x015f960a */
        p->lifetime = 40;
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = (float)(mu_pt_rand(h) % 4 - 2);
        return;
    default:                                       /* 0x8081..0x8083/0, 0x015d2e4c: the colour kept, light 0 */
        p->lifetime = 5;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->gravity = 0.0f;
        p->alpha = 1.0f;
        p->field_7c = p->light[0];
        p->field_80 = p->light[1];
        p->field_84 = p->light[2];
        p->light[0] = p->light[1] = p->light[2] = 0.0f;
        return;
    }
}

static int mu_pt_owner_alive(const mu_pt_particle *p, const mu_pt_host *h)
{   /* the owner OBJECT's +0x00 (0x0095f977); NULL: dead */
    if (p->owner == MU_PT_NO_OWNER)
        return 0;
    return h && h->owner_live ? h->owner_live(h->context, p->owner) : 1;
}

static void mu_pt_bow2_move(mu_pt_particle *p, const mu_pt_host *h)
{
    switch (p->type) {
    case 0x7f78: {                                 /* 0x0162d786: circles about a drifting start, sinking */
        const float t = ((float)p->lifetime + p->velocity[0]) * 0.1f;
        p->position[0] = (float)sin((double)t) * 40.0f + p->start[0];
        p->position[1] = p->start[1] - (float)cos((double)t) * 40.0f;
        p->position[2] = p->position[2] - p->gravity;
        p->scale = p->scale - 0.002f;
        p->start[0] = p->start[0] + 2.5f;
        if (p->lifetime <= 20)                     /* 0x0162dea7 */
            for (int k = 0; k < 3; ++k)
                p->light[k] = p->light[k] / 1.1f;
        return;
    }
    case 0x83b3: {                                 /* 0x0164316e */
        const float step = 1.0f / (float)p->initial_lifetime;
        p->scale = p->scale + step;
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->light[k] - step;
        return;
    }
    case 0x8155:                                   /* 0x01683a73: Spark03/0x1e's move */
        if (p->lifetime <= 45) {
            p->velocity[0] = (float)sin((double)((float)(mu_pt_rand(h) % 360) * 0.017453292f)) + p->velocity[0];
            p->velocity[1] = (float)cos((double)((float)(mu_pt_rand(h) % 360) * 0.017453292f)) + p->velocity[1];
        }
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->light[k] / 1.05f;
        p->scale = p->scale - 0.01f;
        p->lifetime = p->lifetime - 1;
        if (p->lifetime <= 0)
            p->live = 0;
        return;
    case MU_PT_BITMAP_SMOKE:
        if (p->subtype == 0x7a) {                  /* 0x0163e5d1 */
            const float d = (float)p->initial_lifetime;
            p->light[0] = p->light[0] - p->field_7c / d;
            p->light[1] = p->light[1] - p->field_80 / d;
            p->light[2] = p->light[2] - p->field_84 / d;
            p->gravity = p->gravity + 0.1f;
            p->position[2] = p->position[2] + p->gravity;
            p->scale = p->scale + 0.05f;
            p->alpha = (float)p->lifetime / (float)p->initial_lifetime;
            p->position[2] = p->position[2] + 5.0f;
            return;
        }
        {
            const float l = (float)p->lifetime / 32.0f;
            if (p->subtype == 0x18) {              /* 0x01636a33 */
                p->light[0] = l * 0.2f;
                p->light[1] = l * 0.5f;
                p->light[2] = l * 0.35f;
                p->gravity = p->gravity + 0.1f;
                p->position[2] = p->position[2] + p->gravity;
                p->scale = p->scale + 0.05f;
                return;
            }
            p->light[0] = l * 0.05f;               /* 0x4e: 0x0163e3c9, a falling, swaying puff */
            p->light[1] = l * 0.25f;
            p->light[2] = l * 0.6f;
            p->rotation = p->rotation + 0.05f;
            p->gravity = p->gravity - 0.1f;
            p->position[0] = (float)sin((double)(h ? h->world_time : 0.0f)) * p->gravity * 0.05f + p->position[0];
            p->position[2] = p->position[2] + p->gravity;
            p->scale = p->scale + 0.15f;
        }
        return;
    case 0x8085: {                                 /* 0x0164dbf6: flies on with its owner, 300 units a second */
        const float a = (float)p->lifetime / (float)p->initial_lifetime;
        p->light[0] = (float)((double)a * 0.8);
        p->light[1] = (float)((double)a * 0.9);
        p->light[2] = a;
        if (!mu_pt_owner_alive(p, h)) {
            p->live = 0;
            p->lifetime = 0;
            return;
        }
        const float speed = (h ? h->frame_time : 0.0f) * 300.0f;
        const float forward[3] = {0.0f, -1.0f, 0.0f};
        float d[3];
        mu_pt_worlds_m_rotate(d, forward, p->angle);   /* 0x0185c113 */
        for (int k = 0; k < 3; ++k)
            d[k] = speed * d[k];
        for (int k = 0; k < 3; ++k)
            p->position[k] = p->position[k] + d[k];
        return;
    }
    case 0x810c: {                                 /* 0x01681c64 */
        if (p->lifetime <= 30) {
            p->velocity[0] = (float)sin((double)((float)(mu_pt_rand(h) % 360) * 0.017453292f)) + p->velocity[0];
            p->velocity[1] = (float)cos((double)((float)(mu_pt_rand(h) % 360) * 0.017453292f)) + p->velocity[1];
            p->velocity[2] = (float)sin((double)((float)(mu_pt_rand(h) % 360) * 0.017453292f)) + p->velocity[2];
            for (int k = 0; k < 3; ++k)
                p->velocity[k] = p->velocity[k] * 0.9f;
        }
        for (int k = 0; k < 3; ++k)
            p->light[k] = p->light[k] / 1.005f;
        p->rotation = rand_range(h, -10.0f, 10.0f, 1) + p->rotation;
        {   /* MovePosition 0x012af52d(position, -angle, velocity) */
            const float back[3] = {-p->angle[0], -p->angle[1], -p->angle[2]};
            float d[3];
            bow2_angle_rotate(back, p->velocity, d);
            for (int k = 0; k < 3; ++k)
                p->position[k] = p->position[k] + d[k];
        }
        p->scale = p->scale - p->initial_scale / (float)p->initial_lifetime;
        p->lifetime = (int32_t)((double)p->lifetime - 0.1);   /* cvttsd2si: towards zero */
        if (p->lifetime <= 0 || 0.0f >= p->scale)
            p->live = 0;
        return;
    }
    case 0x83b8: {                                 /* 0x0165739e */
        p->scale = (float)p->lifetime / (float)p->initial_lifetime * p->initial_scale;
        p->alpha = (float)p->lifetime / (float)p->initial_lifetime;
        if (p->lifetime % 8 < 4)
            p->rotation = p->rotation + 3.0f;
        else
            p->rotation = p->rotation - 3.0f;
        return;
    }
    case 0x8084:                                   /* 0x0164a207 */
        p->scale = p->scale - p->initial_scale / (float)p->initial_lifetime;
        p->alpha = (float)p->lifetime / (float)p->initial_lifetime;
        for (int k = 0; k < 3; ++k)
            p->position[k] = p->position[k] + p->velocity[k];
        return;
    case 0x8184:                                   /* 0x01672543 */
        if (p->lifetime > 20)
            p->scale = p->scale + 0.01f;
        else
            p->scale = p->scale - 0.011f;
        return;
    default:                                       /* 0x8081..0x8083/0, 0x01644e1d */
        p->alpha = p->alpha - 0.15f;
        if (0.1f > p->alpha)
            p->live = 0;
        {
            const float alpha = p->alpha;
            p->light[0] = p->field_7c * alpha;
            p->light[1] = p->field_80 * alpha;
            p->light[2] = p->field_84 * alpha;
        }
        return;
    }
}

/* RenderParticles: Spark04/2 and firehik01/0x1e take the light times the record's alpha; Flare/5 draws nothing
 * at lifetime 60 (0x01598426); the others draw the plain sprite. Returns 0 when no sprite is drawn. */
static int mu_pt_bow2_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    if (!mu_pt_bow2_kind(p->type, p->subtype))
        return 1;
    if (p->type == 0x7f78)
        return p->lifetime != 60;
    if (p->type == 0x8155 || p->type == 0x8084)
        for (int k = 0; k < 3; ++k)
            s->light[k] = p->light[k] * p->alpha;
    return 1;
}
