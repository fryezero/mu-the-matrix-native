/* RENDER-EFFECTS-018: Uruk Mountain's keyed effect, included by skill_fx.c after bow_fx.inc. Uruk's
 * RenderObjectVisual (0x00e6f3d5) asks for it from type 108 while the weather word [0x01cf15ec] is 1
 * (0x00e70014): CreateEffect 0x013c0eaa(0x806e, position, angle, (1, 1, 1), 12, the object, -1, 0,
 * (u16)(int)(cos(rand) + 0.5), 0, 0.0, -1, 0, 0) (0x00e7022f).
 *   create 0x013c4a45 (0x806e's case 0x013c47b3, subtype chain): LifeTime 20, then the common code
 *   move 0x01439417 (0x806e's case 0x014388c6): each step one flame particle around the position, scale
 *        (rand % 5 + 13) x 0.05 x the effect's scale: 0x8084/1, 0x806e/5 or 0x8085/1 by rand % 3, with the
 *        effect's angle and light and no owner; then the common code (0x0143a5f6)
 *   render: RenderEffects' 0x806e case (0x0151898f) draws nothing (0x01519939). */

static int uruk_effect_kind(int32_t type, int32_t sub)
{
    return type == 0x806e && sub == 12;
}

static int uruk_effect_create(mu_sfx_effect *e)
{
    e->lifetime = 20;
    return 1;
}

static void uruk_effect_move(mu_sfx_effect *e, const mu_sfx_env *env)
{
    float p[3];
    p[0] = (float)(smod(env_rand(env), 50) - 25) * 1.0f + e->position[0];
    p[1] = (float)(smod(env_rand(env), 50) - 25) * 1.0f + e->position[1];
    p[2] = (float)(smod(env_rand(env), 10) + 5) * 1.0f + e->position[2];
    const float scale = (float)(smod(env_rand(env), 5) + 13) * f32bits(0x3d4ccccdu) * e->scale;   /* 0.05 */
    switch (smod(env_rand(env), 3)) {
    case 0: call_particle(env, e, 0x8084, p, e->angle, e->light, 1, scale, MU_SFX_NO_OWNER); break;
    case 1: call_particle(env, e, 0x806e, p, e->angle, e->light, 5, scale, MU_SFX_NO_OWNER); break;
    case 2: call_particle(env, e, 0x8085, p, e->angle, e->light, 1, scale, MU_SFX_NO_OWNER); break;
    default: break;
    }
}
