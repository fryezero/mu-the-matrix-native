/* RENDER-EFFECTS-010: the most requested particle kinds of the other bows' arrows (the 33-bow scenes).
 * Included after the shared helpers; admission is limited to the verified kind/subtype pairs:
 *   smoke01 0x7f5a/0x86     0x616's smoke (create 0x015cc802, move 0x0163eec2, render 0x01596575)
 *   0x810a/0x24             0x616's flight sparks (create 0x015b4d61, move 0x0161d606, render 0x0159faca)
 *   0x810a/0xe              0x613's glints (create 0x015b2166, move 0x0161b194, render 0x0159faca)
 *   Spark03 0x7f26/0x1e     0x525's sparks (create 0x015e033d, move 0x01653bcc, the plain sprite 0x015a531f) */
static float rand_range(const mu_pt_host *h, float lo, float hi, int32_t steps);   /* defined below */

static int mu_pt_bow_kind(int32_t type, int32_t subtype)
{
    return (type == MU_PT_BITMAP_SMOKE && subtype == 0x86) || (type == 0x810a && (subtype == 0x24 || subtype == 0xe)) ||
           (type == MU_PT_BITMAP_SPARK3 && subtype == 0x1e);
}

static void mu_pt_bow_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == MU_PT_BITMAP_SMOKE) {           /* 0x015cc802 */
        p->lifetime = 20;
        p->initial_lifetime = 20;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        return;
    }
    if (p->type == MU_PT_BITMAP_SPARK3) {          /* 0x015e033d: a spark thrown up and falling */
        p->lifetime = mu_pt_rand(h) % 5 + 50;
        p->scale = (float)(mu_pt_rand(h) % 10) / 10.0f + 0.2f;
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = (float)(mu_pt_rand(h) % 5) + -2.0f;
        p->gravity = 0.5f;
        return;
    }
    if (p->subtype == 0xe) {                       /* 0x015b2166 */
        p->lifetime = 25;
        p->initial_lifetime = p->lifetime;
        p->scale = rand_range(h, 0.5f, 1.0f, 100) * scale;
        p->initial_scale = p->scale;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        p->alpha = 1.0f;
        return;
    }
    p->lifetime = 20;                              /* 0x015b4d61: flies back along the angle, spinning */
    p->initial_lifetime = p->lifetime;
    p->alpha = 1.0f;
    p->rotation = rand_range(h, 0.0f, 360.0f, 1);
    p->field_84 = rand_range(h, -20.0f, 20.0f, 1) * 0.1f;
    p->scale = scale;
    p->initial_scale = p->scale;
    p->angle[2] = p->angle[2] - 180.0f;
    p->moving = 0;
    {   /* AngleToVector 0x00d015d5: (0, -1, 0) rotated by the angle, then VectorNormalize 0x00cff0d3 (divides by
         * the length; zero below 1e-6) */
        float m[12];
        const float forward[3] = {0.0f, -1.0f, 0.0f};
        mu_angle_matrix(p->angle, m);
        mu_vector_rotate(forward, m, p->velocity);
        const float length = (float)sqrt((double)(p->velocity[0] * p->velocity[0] + p->velocity[1] * p->velocity[1] +
                                                  p->velocity[2] * p->velocity[2]));
        if (0x1.0c6f7ap-20f > length)   /* 1e-6 */
            p->velocity[0] = p->velocity[1] = p->velocity[2] = 0.0f;
        else
            for (int k = 0; k < 3; ++k)
                p->velocity[k] = p->velocity[k] / length;
    }
    for (int k = 0; k < 3; ++k)
        p->velocity[k] = 10.0f * p->velocity[k];
    float jitter[3];
    for (int k = 0; k < 3; ++k)
        jitter[k] = rand_range(h, -3.0f, 3.0f, 1);
    for (int k = 0; k < 3; ++k)
        p->velocity[k] = p->velocity[k] + jitter[k];
}

static void mu_pt_bow_move(mu_pt_particle *p, const mu_pt_host *h)
{
    if (p->type == MU_PT_BITMAP_SMOKE) {           /* 0x0163eec2 */
        p->alpha = (float)p->lifetime / (float)p->initial_lifetime;
        p->scale = p->scale + 0.04f;
        return;
    }
    if (p->type == MU_PT_BITMAP_SPARK3) {          /* 0x01653bcc: wanders after 5 steps, dims, shrinks, lives twice as fast */
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
    }
    if (p->subtype == 0xe) {                       /* 0x0161b194 */
        if (p->lifetime < p->initial_lifetime / 2)
            p->alpha = p->alpha - 1.0f / (float)(p->initial_lifetime / 2);
        p->scale = p->scale - p->initial_scale / (float)p->initial_lifetime;
        p->rotation = p->rotation - 10.0f;
        p->velocity[0] = rand_range(h, -2.0f, 2.0f, 10) + p->velocity[0];
        p->velocity[1] = rand_range(h, 0.0f, 2.0f, 10) + p->velocity[1];
        p->velocity[2] = rand_range(h, -2.0f, 2.0f, 10) + p->velocity[2];
        return;
    }
    p->rotation = p->rotation + p->field_84;      /* 0x0161d606 */
    for (int k = 0; k < 3; ++k)
        p->position[k] = p->position[k] + p->velocity[k];
    p->alpha = (float)p->lifetime / (float)p->initial_lifetime;
    p->scale = (float)p->lifetime * p->initial_scale / (float)p->initial_lifetime;
}

/* RenderParticles: smoke01/0x86 and 0x810a take the light times the record's alpha; Spark03/0x1e the plain sprite. */
static void mu_pt_bow_render(const mu_pt_particle *p, mu_pt_sprite_call *s)
{
    if (!mu_pt_bow_kind(p->type, p->subtype) || p->type == MU_PT_BITMAP_SPARK3)
        return;
    for (int k = 0; k < 3; ++k)
        s->light[k] = p->light[k] * p->alpha;
}
