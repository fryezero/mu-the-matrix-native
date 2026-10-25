/* domains/hero.c (sketch): apply and submit functions of ops/hero.ops. */
#include "../session_internal.h"

/* The env adapter: points the verified handlers at session records and turns their engine
 * calls into cues. Built per call, so mirrors can never go stale. */
static void hero_env(mu_session *s, mu_prg_env *env)
{
    /* TODO
     *   env->user = s; env->attr = s->hero.attr; env->hero = s->hero.record;
     *   env->hero_class = s->hero.record[0x12];
     *   refresh record motion offsets from mu_session_hero_motion (handlers place effects at the hero)
     *   env->emit         -> parse the handler's one-line call reports into MU_CUE_EFFECT / MU_CUE_SOUND /
     *                         MU_CUE_CHAT / MU_CUE_WINDOW in order (the line grammar is progress.h's)
     *   env->global_text  -> s->cfg.lang
     *   env->has_buff, item_* -> buffs and equipment domains (inventory domain's equipped slots)
     *   env->character    -> viewport domain: a 0x400-byte scratch projection of the mu_rp_character
     *                        the key names (see viewport.c "projection adapters"), written back after
     *   env->window       -> 1 for the windows a GFx view has registered as open (window domain)
     */
    (void)s; (void)env;
    MU_NOT_IMPLEMENTED();
}

mu_apply hero_levelup(mu_session *s, const mu_frame *f)
{
    mu_prg_env env;
    hero_env(s, &env);
    mu_prg_recv_levelup(&env, f->bytes);         /* verified, unchanged (0x01250b05) */
    mu_session_touch(s, MU_DOMAIN_HERO);
    /* TODO: MU_CUE_LEVEL_UP with the new level, after the handler's own effect/sound cues */
    return MU_APPLY_DONE;
}

mu_apply hero_kill_exp(mu_session *s, const mu_frame *f)
{
    /* TODO
     *   uint8_t report[5];
     *   r = mu_prg_recv_kill_exp(&env, f->bytes, f->encrypted, report)   // refuses plaintext 0x16
     *   if the handler produced the report packet: build C1 4D 02 00 16 with mu_packet, mu_session_send
     *       (this is the client's own answer to a plaintext frame; a fixture that sends 0x16 as C1
     *        must therefore see the report - test_fixture_hero.py asserts both paths)
     *   touch HERO
     */
    (void)s; (void)f;
    MU_NOT_IMPLEMENTED();
}

mu_apply hero_respawn(mu_session *s, const mu_frame *f)
{
    /* TODO
     *   mu_prg_respawn out; mu_prg_recv_respawn(&env, f->bytes, &out)    // attribute part (verified)
     *   s->hero.money = out.money  (the handler writes CharacterMachine +0x2d70; mirror kept only here)
     *   place = {out.map, {out.x, out.y}, out.angle, ++seq}; map domain owns place: map_set_place(s, &place)
     *   return out.map != current world ? MU_APPLY_WORLD_CHANGE : (port.place_hero(&place), MU_APPLY_DONE)
     */
    (void)s; (void)f;
    MU_NOT_IMPLEMENTED();
}

mu_submit hero_add_stat(mu_session *s, const mu_intent *in)
{
    /* TODO
     *   if mu_prg_stat_button(attr, row) < 0: REFUSED (no free points)          // verified rule
     *   uint8_t p[5]; n = mu_prg_stat_request(&env, &s->hero.last_stat_request, s->now, in->u.add_stat.stat, p)
     *   n == 0 -> THROTTLED (100 ms)
     *   mu_packet_begin(C1, p[2]); mu_packet_add(rest, encode as the client does); mu_session_send -> SENT
     */
    (void)s; (void)in;
    MU_NOT_IMPLEMENTED();
}

void mu_session_hero(const mu_session *s, mu_hero_stats *out)
{
    /* TODO: read MU_PRG_A_* offsets of s->hero.attr / machine; class formulas through mu_prg_calc_class
     * on a scratch copy (pure); name from s->hero.name */
    (void)s; (void)out;
    MU_NOT_IMPLEMENTED();
}

int64_t mu_session_money(const mu_session *s) { return s->hero.money; }
