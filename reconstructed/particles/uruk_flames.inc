/* RENDER-EFFECTS-018: two of the flame kinds Uruk's keyed effect 0x806e/12 emits (reconstructed/combat/uruk_fx.inc),
 * after the shared helpers. Each is its own branch of the bitmap's subtype chain, shaped like the Karutan flames
 * (world_flames.c) with its own lifetime and shrink:
 *   0x8084/1  create 0x015d41ab (LifeTime rand % 5 + 20), move 0x0164669e (dims below LifeTime 20, shrinks
 *             (rand % 2 + 4) x 0.01)
 *   0x806e/5  create 0x015b8f64 (rand % 5 + 24), move 0x01625e90 (below 15, (rand % 2 + 5) x 0.01)
 * Both rise (rand % 24 + 74) x 0.1 a step and turn 3 degrees; RenderParticles draws them as the bitmap's other
 * subtypes (0x8084 0x015a439f, 0x806e 0x01597633). The third, firehik03 0x8085/1 (create 0x015d9089, move
 * 0x0164b839: rand % 5 + 34, below 15, (rand % 2 + 6) x 0.01), is the Demon's flame of pet_kinds.inc
 * (RENDER-EFFECTS-010). */

static int mu_pt_uruk_flame_kind(int32_t type, int32_t subtype)
{
    return (type == 0x8084 && subtype == 1) || (type == 0x806e && subtype == 5);
}

static void mu_pt_uruk_flame_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    p->lifetime = mu_pt_rand(h) % 5 + (p->type == 0x8084 ? 20 : 24);
    p->scale = (float)(mu_pt_rand(h) % 72 + 72) * 0.01f * scale;
    p->rotation = (float)(mu_pt_rand(h) % 360);
    p->gravity = (float)(mu_pt_rand(h) % 24 + 74) * 0.1f;
    p->alpha = 0;
    p->field_7c = p->light[0];
    p->field_80 = p->light[1];
    p->field_84 = p->light[2];
    p->light[0] = p->light[1] = p->light[2] = 0;
}

static void mu_pt_uruk_flame_move(mu_pt_particle *p, const mu_pt_host *h)
{
    if (p->lifetime < (p->type == 0x8084 ? 20 : 15))
        p->alpha -= 0.2f;
    else if (1.0f > p->alpha)
        p->alpha += (float)(mu_pt_rand(h) % 2 + 2) * 0.1f;
    else
        p->alpha = 1.0f;
    if (0.1f > p->alpha)
        p->live = 0;
    p->light[0] = p->field_7c * p->alpha;
    p->light[1] = p->field_80 * p->alpha;
    p->light[2] = p->field_84 * p->alpha;
    if (p->scale > 0)
        p->scale -= (float)(mu_pt_rand(h) % 2 + (p->type == 0x8084 ? 4 : 5)) * 0.01f;
    else
        p->live = 0;
    p->position[2] += p->gravity;
    p->rotation += 3.0f;
}
