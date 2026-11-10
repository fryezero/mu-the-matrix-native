/* RENDER-EFFECTS-027. Included after the common movement helpers.
 * No rand() in the 0x472/2 move. The pool ordinal and ambient clock seed
 * the client's direction helper 0x0158bac2, at frequency 1.4. */
static void move_death_stab(mu_jt_joint *j, const mu_jt_object *t, const mu_jt_env *env, int32_t index)
{
    j->scale = (float)j->lifetime * 3.0f;
    float blend = (float)(j->lifetime - 10) / 10.0f;
    if (blend >= 1.0f) blend = 1.0f;
    if (0.0f > blend) blend = 0.0f;
    const float pull = 1.0f - blend;
    const uint32_t phase = (uint32_t)index * 0x4539u + (uint32_t)(env ? env->ambient_clock : 0);
    const float a = (float)(int32_t)(phase + 0xd903u) * (f32bits(0x3d449ba6u) * f32bits(0x3fb33333u));
    const float b = (float)(int32_t)phase * (f32bits(0x3d7b15b5u) * f32bits(0x3fb33333u));
    const float c = (float)(int32_t)(phase + 0x2b67u) * (f32bits(0x3de3f141u) * f32bits(0x3fb33333u));
    const float x = fsin(a) * fcos(b), y = fsin(a) * fsin(b), z = fcos(a);
    const float s = fsin(c), co = fcos(c);
    float d[3] = {co * y - s * z, s * y + co * z, x};
    for (int k = 0; k < 3; ++k) d[k] = 300.0f * d[k];
    for (int k = 0; k < 3; ++k) d[k] = d[k] + j->target_position[k];
    for (int k = 0; k < 3; ++k)
        j->position[k] = pull * t->sword_position[k] + blend * d[k];
}

static void move_death_stab_flare(mu_jt_joint *j)
{
    const float phase = ((float)j->lifetime + j->jitter[0]) * F_0_1;
    const float x = -fcos(phase) * 26.0f;
    const float y = fsin(phase) * 26.0f - (float)(90 - j->lifetime) * F_0_3;
    j->target_position[0] = j->target_position[0] + j->jitter[1];
    j->target_position[1] = j->target_position[1] + j->jitter[2];
    const float radians = (90.0f - j->angle[2]) * f32bits(0x40490fdbu) / 180.0f;
    j->position[0] = fsin(radians) * x + j->target_position[0];
    j->position[1] = fcos(radians) * x + j->target_position[1];
    j->position[2] = y + j->target_position[2];
    if (j->lifetime < 10)
        for (int k = 0; k < 3; ++k) j->light[k] = j->light[k] / f32bits(0x3fa66666u);
}
