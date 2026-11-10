/* RENDER-EFFECTS-025: clouds/28, CreateParticle 0x015edeaf,
 * MoveParticles 0x0166200c. Included with the shared particle helpers. */
static int mu_pt_ferea_cloud_kind(int32_t type, int32_t subtype)
{
    return type == 0x7f89 && subtype == 28;
}

static void mu_pt_ferea_cloud_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    p->lifetime = 300;
    p->initial_lifetime = p->lifetime;
    const float dx = rand_range(h, -250.0f, 250.0f, 10) * scale;
    const float dy = rand_range(h, -250.0f, 250.0f, 10) * scale;
    p->position[0] = p->position[0] + dx;
    p->position[1] = p->position[1] + dy;
    copy3(p->start, p->position);
    p->scale = rand_range(h, 0.5f, 1.5f, 100) * scale;
    p->rotation = rand_range(h, 0.0f, 360.0f, 10);
    p->alpha = 0.0f;
}

static void mu_pt_ferea_cloud_move(mu_pt_particle *p, const mu_pt_host *h)
{
    const float phase = ((1.0f - (float)p->lifetime / (float)p->initial_lifetime) * 360.0f + 180.0f) *
                         0.01745329238474369f;
    p->alpha = ((float)cos((double)phase) + 1.0f) * 0.5f;
    const float speed = rand_range(h, 0.3f, 1.3f, 10);
    const float time = (h ? h->world_time : 0.0f) * 0.00019999999494757503f;
    const float center[3] = {p->position[0], p->position[1] + (float)sin((double)time) * speed, p->position[2]};
    const float angle = p->angle[2] * 0.01745329238474369f;
    const float dx = center[0] - p->position[0], dy = center[1] - p->position[1];
    p->position[0] = p->position[0] + ((float)cos((double)angle) * dx - (float)sin((double)angle) * dy);
    p->position[1] = p->position[1] + ((float)sin((double)angle) * dx + (float)cos((double)angle) * dy);
    p->rotation = p->rotation + 0.7f;
}
