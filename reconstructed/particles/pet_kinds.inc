/* RENDER-EFFECTS-010: the pets' particle kinds (the visuals 0x00eaeaf8, docs/research/client-pets.md).
 * Included after the shared helpers; admission is limited to the verified kind/subtype pairs:
 *   Clud64 0x7ffd/0xb          the Demon's five bone clouds (create 0x015c1930, move 0x016305fa, render 0x01594faf)
 *   firehik03 0x8085/1         the Demon's flame at bone 0x2c (0x015d9074, 0x0164b824, the plain sprite 0x01594d3f)
 *   firehik_mono01 0x8086/4    the Skeleton's eye flames, owner = the pet (0x015d474d by the subtype table
 *   firehik_mono02 0x8087/8      0x01616648, 0x015b95cc, 0x015d980f; moves 0x0164723f, 0x016267a6, 0x0164c42b;
 *   firehik_mono03 0x8089/5      the plain sprites 0x015a43ca, 0x01597727, 0x01594f18)
 * The Panda's Impack01 0x7efa/1 shares 0x7efa/2's body (world_owned_fx.inc). */
/* The owner OBJECT's +0x158 as it is (the record's +0x54 copy has the terrain height for z). */
static int pet_owner_origin(const mu_pt_particle *p, const mu_pt_host *h, float out[3])
{
    if (p->owner == MU_PT_NO_OWNER || !h || !h->owner_position)
        return 0;
    h->owner_position(h->context, p->owner, out);
    return 1;
}

static int mu_pt_pet_kind(int32_t type, int32_t subtype)
{
    return (type == 0x7ffd && subtype == 0xb) || (type == 0x8085 && subtype == 1) ||
           (type == 0x8086 && subtype == 4) || (type == 0x8087 && subtype == 8) || (type == 0x8089 && subtype == 5);
}

static void mu_pt_pet_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    if (p->type == 0x7ffd) {                       /* 0x015c1945: a cloud, three in four drawn with smoke01 */
        if (mu_pt_rand(h) % 4 != 0)
            p->tex_type = MU_PT_BITMAP_SMOKE;
        p->lifetime = 30;
        p->scale = scale;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        for (int k = 0; k < 3; ++k)
            p->position[k] = (float)(mu_pt_rand(h) % 20 - 10) + p->position[k];
        p->gravity = -1.5f;
        return;
    }
    if (p->type == 0x8085) {                       /* 0x015d9089 */
        p->lifetime = mu_pt_rand(h) % 5 + 34;
        p->scale = (float)(mu_pt_rand(h) % 72 + 72) * 0.01f * scale;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->gravity = (float)(mu_pt_rand(h) % 24 + 74) * 0.1f;
    } else {                                       /* the three firehik_mono bodies are the same */
        p->lifetime = 8;
        p->scale = (float)(mu_pt_rand(h) % 42 + 12) * 0.01f * scale;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->gravity = (float)(mu_pt_rand(h) % 14 + 44) * 0.1f;
    }
    p->alpha = 0.0f;
    p->field_7c = p->light[0];                     /* the colour, faded in by the move */
    p->field_80 = p->light[1];
    p->field_84 = p->light[2];
    p->light[0] = p->light[1] = p->light[2] = 0.0f;
    float o[3];
    if (p->type != 0x8085 && pet_owner_origin(p, h, o))
        copy3(p->start, o);                        /* the owner's +0x158 (a NULL owner faults in the client) */
}

/* The fade both flame moves share: in by (rand % 2 + 2) / 10 up to 1, out by `fade` below `below` steps. */
static void pet_flame_fade(mu_pt_particle *p, const mu_pt_host *h, int32_t below, float fade)
{
    if (p->lifetime < below)
        p->alpha = p->alpha - fade;
    else if (1.0f > p->alpha)
        p->alpha = (float)(mu_pt_rand(h) % 2 + 2) * 0.1f + p->alpha;
    else
        p->alpha = 1.0f;
    if (0.1f > p->alpha)
        p->live = 0;
    p->light[0] = p->field_7c * p->alpha;
    p->light[1] = p->field_80 * p->alpha;
    p->light[2] = p->field_84 * p->alpha;
}

static void mu_pt_pet_move(mu_pt_particle *p, const mu_pt_host *h)
{
    if (p->type == 0x7ffd) {                       /* 0x0163060f */
        const float l = (float)p->lifetime / 10.0f;
        p->light[0] = p->light[1] = p->light[2] = l;
        p->gravity = p->gravity - 0.01f;
        p->position[2] = p->position[2] - p->gravity;
        p->scale = p->scale - 0.03f;
        p->alpha = p->alpha - 0.05f;
        return;
    }
    if (p->type == 0x8085) {                       /* 0x0164b839 */
        pet_flame_fade(p, h, 15, 0.2f);
        if (p->scale > 0.0f)
            p->scale = p->scale - (float)(mu_pt_rand(h) % 2 + 6) * 0.01f;
        else
            p->live = 0;
        p->position[2] = p->position[2] + p->gravity;
        p->rotation = p->rotation + 3.0f;
        return;
    }
    /* 0x0164724a (0x8089: below 4 steps, the others 5) */
    pet_flame_fade(p, h, p->type == 0x8089 ? 4 : 5, 0.1f);
    p->scale = (float)(mu_pt_rand(h) % 3 + 8) * 0.01f + p->scale;
    if (p->lifetime < 3)
        p->scale = (float)(10 - p->lifetime) * 0.02f + p->scale;
    float m[12], d[3];
    const float up[3] = {0.0f, -1.0f, 0.0f};
    mu_angle_matrix(p->angle, m);                  /* AngleMatrix 0x00cff32a, VectorRotate 0x00d000ad */
    mu_vector_rotate(up, m, d);
    for (int k = 0; k < 3; ++k)
        d[k] = 8.0f * d[k];
    for (int k = 0; k < 3; ++k)
        p->position[k] = p->position[k] + d[k];
    float o[3];
    if (pet_owner_origin(p, h, o)) {               /* follows the owner: minus its former, plus its new +0x158 */
        for (int k = 0; k < 3; ++k)
            p->position[k] = p->position[k] - p->start[k];
        copy3(p->start, o);
        for (int k = 0; k < 3; ++k)
            p->position[k] = p->position[k] + o[k];
    }
    p->rotation = p->rotation + 5.0f;
}
