/* Icarus persistent clouds, CreateParticle 0x015ee424 / 0x015ea74c (subtype 3),
 * MoveParticles 0x01662551..0x01662839. Included after the common helpers. */
static void mu_pt_icarus_cloud_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    p->lifetime = 30;
    p->gravity = (float)(mu_pt_rand(h) % 1000);
    for (int k = 0; k < 2; ++k)
        p->position[k] = (float)(mu_pt_rand(h) % 500 - 250) + p->position[k];
    p->position[2] = (float)(mu_pt_rand(h) % 20 + 20) + p->position[2];
    p->start[1] = (float)(mu_pt_rand(h) % 100) / 100.0f;
    p->start[2] = p->position[2];
    p->scale = (float)(mu_pt_rand(h) % 20 + 180) * 0.01f;
    float sign = 1.0f;
    if (p->subtype == 3) sign = mu_pt_rand(h) % 2 == 0 ? -1.0f : 1.0f;
    p->field_7c = sign * ((float)(mu_pt_rand(h) % 30) / 100.0f + scale);
    p->velocity[0] = p->velocity[1] = p->velocity[2] = 0.0f;
}
static void mu_pt_icarus_cloud_move(mu_pt_particle *p, const mu_pt_host *h)
{
    int visible = h && h->cloud_owner && h->cloud_owner(h->context, p->owner, 0);
    if (visible) p->lifetime = 50;
    if (p->lifetime <= 1) {
        if (h && h->cloud_owner) h->cloud_owner(h->context, p->owner, 1);
        p->live = 0;
    }
    float time = h ? h->world_time : 0.0f;
    p->position[2] = p->start[2] + (float)sin((double)((time + p->gravity) / 5000.0f)) * 20.0f;
    if (p->subtype == 1 || p->subtype == 4)
        p->rotation = (time * 0.02f) * p->field_7c + p->start[1];
    else if (p->subtype == 2 || p->subtype == 5)
        p->rotation = (time * -0.02f) * p->field_7c + p->start[1];
}
