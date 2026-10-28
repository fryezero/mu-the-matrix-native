/* domains/hero.c: the hero domain - apply and submit functions of ops/hero.ops over the verified
 * reconstructed/progress handlers, which run unchanged.
 *
 * The env adapter points the handlers at session records and turns their engine calls (env->emit
 * lines, progress.h's grammar) into cues in call order. A few of those calls are client routines
 * that change state; the adapter performs them at the point the handler calls them, exactly as the
 * demo session (core/mu_progress.c env_emit) did:
 *   call 00a00f4a   the level's experience (mu_prg_level_exp, verified)
 *   call 00a00fb7   the stat machine's recalculation flag: recalculated at once (calc_class + totals,
 *                   verified; equipment/buff inputs are zero until SESSION-HERO-002)
 *   call 00c51256   the HUD's experience bar (mu_prg_exp_bar, verified; master cap 0x546)
 *   call 00b40380   the character window's speed row (mu_prg_speed_row, verified; maximum 400 as live)
 *   call 00d51d4f   Send(a, b): remembered so the apply function sends what the handler built
 * Windows the handlers ask about (env->window) are the in-world HUD the demo also assumed: the main
 * frame 0x0095c50b, the level window 0x0095c5da and hudPlayerName 0x009a19ae. Character lookups
 * (env->character) find nothing until the viewport domain exists (SESSION-VIEWPORT-001), which is
 * the client's answer for a key outside CharactersClient.
 */
#include "../session_internal.h"
#include "audio_cue.h"
#include "layout_StatMachine.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef MU_SESSION_SEED
#include "../mu_session_seed.h"
#endif

static mu_prg_env hero_env(mu_session *s);

/* ---- the env adapter --------------------------------------------------------------------- */

static void cue_init(mu_session *s, mu_cue *c, mu_cue_kind kind)
{
    memset(c, 0, sizeof *c);
    c->kind = kind;
    c->handler = s->hero.handler;
}

static uint32_t hex_at(const char *p, const char **end)
{
    char *e;
    unsigned long v = strtoul(p, &e, 16);
    if (end)
        *end = e;
    return (uint32_t)v;
}

/* the JSON string the handler printed (mu_prg_json) back to text */
static void unjson(char *out, size_t cap, const char *q)
{
    size_t n = 0;
    if (*q == '"')
        ++q;
    while (*q && *q != '"' && n + 1 < cap) {
        if (*q == '\\' && q[1] == 'u' && q[2] && q[3] && q[4] && q[5]) {
            char hex[5] = {q[2], q[3], q[4], q[5], 0};
            out[n++] = (char)strtoul(hex, NULL, 16);
            q += 6;
        } else if (*q == '\\' && q[1]) {
            out[n++] = q[1];
            q += 2;
        } else {
            out[n++] = *q++;
        }
    }
    out[n] = 0;
}

static void hero_recalc(mu_session *s)
{
    mu_prg_env e = hero_env(s);
    static const int32_t zero[5] = {0, 0, 0, 0, 0};
    mu_prg_calc_class(&e, s->hero.attr[MU_PRG_A_CLASS] & 15, zero);
    mu_prg_calc_totals(s->hero.attr, s->hero.machine, zero);
    s->hero.recalculated = 1;
}

static void env_emit(void *user, const char *line)
{
    mu_session *s = user;
    mu_dom_hero *h = &s->hero;
    mu_cue c;
    if (!strncmp(line, "invoke ", 7)) {
        cue_init(s, &c, MU_CUE_WINDOW);
        c.u.window.verb = MU_WINDOW_INVOKE;
        const char *m = line + 7, *sp = strchr(m, ' ');
        size_t n = sp ? (size_t)(sp - m) : strlen(m);
        if (n >= sizeof c.u.window.method)
            n = sizeof c.u.window.method - 1;
        memcpy(c.u.window.method, m, n);
        if (sp)
            snprintf(c.u.window.json, sizeof c.u.window.json, "%s", sp + 1);
        if (!strcmp(c.u.window.method, "setExpData")) {
            snprintf(c.u.window.movie, sizeof c.u.window.movie, "main");
            snprintf(h->exp_json, sizeof h->exp_json, "%s", sp ? sp + 1 : "");
        }
        mu_session_cue(s, &c);
        return;
    }
    if (strncmp(line, "call ", 5) != 0)
        return;
    const char *rest;
    uint32_t addr = hex_at(line + 5, &rest);
    while (*rest == ' ')
        ++rest;
    switch (addr) {
    case 0x00a00f4au:
        mu_prg_level_exp(h->attr);
        return;
    case 0x00a00fb7u:
        hero_recalc(s);
        return;
    case 0x00c51256u: {
        mu_prg_env e = hero_env(s);
        mu_prg_exp_bar(&e, &h->bar, 0x546);   /* 0x016963bf: 1350 on a normal server */
        return;
    }
    case 0x00b40380u: {
        mu_prg_env e = hero_env(s);
        mu_prg_speed_row(&e, h->attr[MU_PRG_A_CLASS] & 15, 400, h->speed_row, 1);
        return;
    }
    case 0x00d51d4fu: {
        const char *end;
        h->send_args[0] = (int32_t)hex_at(rest, &end);
        h->send_args[1] = (int32_t)hex_at(end, NULL);
        h->send_seen = 1;
        return;
    }
    case 0x0153b02cu:   /* CreateJoint TYPE P1 P2 P3 SUB OWNER ... */
    case 0x013c0eaau: { /* CreateEffect TYPE P1 P2 P3 SUB OWNER ... */
        cue_init(s, &c, MU_CUE_EFFECT);
        const char *p = rest;
        c.u.effect.type = (int32_t)hex_at(p, &p);
        for (int i = 0; i < 3; ++i) {   /* the three position/angle operands (o+OFF) */
            while (*p == ' ')
                ++p;
            while (*p && *p != ' ')
                ++p;
        }
        c.u.effect.subtype = (int32_t)hex_at(p, NULL);
        c.u.effect.owner_key = -1;   /* the hero ("o") */
        mu_session_cue(s, &c);
        return;
    }
    case 0x00a6ac96u:
        mu_domain_sound_cue(s, line);
        return;

    case 0x01219a39u:   /* the chat window's system line */
    case 0x0095f547u: { /* its other line (master experience) */
        cue_init(s, &c, MU_CUE_CHAT);
        c.u.chat.channel = addr == 0x01219a39u ? 0 : 1;
        unjson(c.u.chat.text, sizeof c.u.chat.text, rest);
        mu_session_cue(s, &c);
        return;
    }
    case 0x016912aeu: { /* the damage number: POSITION DAMAGE COLOR... */
        cue_init(s, &c, MU_CUE_DAMAGE);
        const char *p = rest;
        while (*p && *p != ' ')
            ++p;
        c.u.damage.amount = (int32_t)hex_at(p, NULL);
        c.u.damage.target_key = h->cue_key;
        mu_session_cue(s, &c);
        return;
    }
    case 0x00b3e33fu: { /* the speed row's text: 15 "TEXT" */
        const char *q = strchr(rest, '"');
        if (q) {
            size_t n = 0;
            for (++q; *q && *q != '"' && n + 1 < sizeof h->speed_text; ++q)
                h->speed_text[n++] = *q;
            h->speed_text[n] = 0;
        }
        break;
    }
    default:
        break;
    }
    /* a client routine with no typed cue yet (window refreshes, the death routine, ...) */
    cue_init(s, &c, MU_CUE_CALL);
    c.u.call.address = addr;
    snprintf(c.u.call.args, sizeof c.u.call.args, "%s", rest);
    mu_session_cue(s, &c);
}

static const char *env_text(void *user, int32_t index)
{
    mu_session *s = user;
    const char *t = mu_session_global_text(s, index);
    if (index == 0x10be && !*t)
        return "%d / %d";   /* the speed row's format, needed to print the row at all (as the demo) */
    return t;
}

static int env_window(void *user, uint32_t getter)
{
    (void)user;
    return getter == 0x0095c50bu || getter == 0x0095c5dau || getter == 0x009a19aeu;
}

static uint8_t *env_character(void *user, int32_t key, int32_t *index)
{
    (void)user;
    (void)key;
    (void)index;
    return NULL;   /* no CharactersClient before the viewport domain */
}

static mu_prg_env hero_env(mu_session *s)
{
    mu_prg_env e;
    memset(&e, 0, sizeof e);
    e.user = s;
    e.attr = s->hero.attr;
    e.hero_class = s->hero.record[0x12];
    e.emit = env_emit;
    e.global_text = env_text;
    e.window = env_window;
    e.hero = s->hero.record;
    e.character = env_character;
    return e;
}

/* before each handler: the record's motion from the world, the call's provenance */
static mu_prg_env hero_call(mu_session *s, uint32_t handler, int16_t key)
{
    int32_t tile[2];
    float position[3], angle[3];
    mu_session_hero_motion(s, tile, position, angle);
    mu_prg_set32(s->hero.record, MU_HERO_TILE_OFFSET, (uint32_t)tile[0]);
    mu_prg_set32(s->hero.record, MU_HERO_TILE_OFFSET + 4, (uint32_t)tile[1]);
    s->hero.handler = handler;
    s->hero.cue_key = key;
    s->hero.send_seen = 0;
    s->hero.send_args[0] = s->hero.send_args[1] = 0;
    return hero_env(s);
}

static void level_up_cue(mu_session *s)
{
    mu_cue c;
    cue_init(s, &c, MU_CUE_LEVEL_UP);
    c.u.level_up.level = mu_prg_i32(s->hero.attr, MU_PRG_A_LEVEL);
    c.u.level_up.master_level = mu_prg_master_level(s->hero.attr);
    mu_session_cue(s, &c);
}

/* ---- apply functions (ops/hero.ops) -------------------------------------------------------- */

mu_apply hero_kill_exp(mu_session *s, const mu_frame *f)
{
    mu_prg_env env = hero_call(s, 0x01234c08u, (int16_t)(((f->bytes[3] << 8) | f->bytes[4]) & 0x7fff));
    uint8_t report[5] = {0, 0, 0, 0, 0};
    int r = mu_prg_recv_kill_exp(&env, f->bytes, f->encrypted, report);   /* verified, unchanged */
    if (r == 0 && report[0] && s->hero.send_seen) {
        /* The client's own answer to a plaintext 0x16 (static reading of 0x01234c3b..0x01234cc1):
         * Begin(C1, 0x4D); AddData(&b, 1, 1) for 02, 00, 16 (each XorData-encoded); Send(1, 0): the
         * encrypted path of the wrap 0x00d51e87, so on the wire it is a C3 frame. Without the
         * CryptoModule (NET-DECODE-001) mu_session_send refuses it and the journal keeps the built
         * frame as unsent. */
        mu_packet p;
        mu_packet_begin(&p, report[0], report[1]);
        for (int i = 2; i < 5; ++i)
            mu_packet_add(&p, &report[i], 1, 1);
        mu_session_send(s, &p, s->hero.send_args[0]);
        return MU_APPLY_IGNORED;
    }
    mu_session_touch(s, MU_DOMAIN_HERO);
    return MU_APPLY_DONE;
}

mu_apply hero_levelup(mu_session *s, const mu_frame *f)
{
    mu_prg_env env = hero_call(s, 0x01250b05u, -1);
    mu_prg_recv_levelup(&env, f->bytes);         /* verified, unchanged */
    level_up_cue(s);
    mu_session_touch(s, MU_DOMAIN_HERO);
    return MU_APPLY_DONE;
}

mu_apply hero_point(mu_session *s, const mu_frame *f)
{
    mu_prg_env env = hero_call(s, 0x01223f04u, -1);
    mu_prg_recv_point(&env, f->bytes);
    mu_session_touch(s, MU_DOMAIN_HERO);
    return MU_APPLY_DONE;
}

mu_apply hero_master_levelup(mu_session *s, const mu_frame *f)
{
    mu_prg_env env = hero_call(s, 0x01285b68u, -1);
    mu_prg_recv_master_levelup(&env, f->bytes);
    level_up_cue(s);
    mu_session_touch(s, MU_DOMAIN_HERO);
    return MU_APPLY_DONE;
}

mu_apply hero_master_exp(mu_session *s, const mu_frame *f)
{
    mu_prg_env env = hero_call(s, 0x01285efau, -1);
    mu_prg_recv_master_exp(&env, f->bytes);
    mu_session_touch(s, MU_DOMAIN_HERO);
    return MU_APPLY_DONE;
}

mu_apply hero_stats(mu_session *s, const mu_frame *f)
{
    mu_prg_env env = hero_call(s, 0x0122a5f6u, -1);
    mu_prg_recv_stats(&env, &s->hero.stat_window, f->bytes);
    /* what the window shows from now on (the window copy +0x119.., as core/mu_progress.c keeps it) */
    for (int k = 0; k < 5; k++)
        s->hero.stat_window.shown[2 * k] = (uint16_t)(f->bytes[4 + 4 * k] | f->bytes[5 + 4 * k] << 8);
    mu_session_touch(s, MU_DOMAIN_HERO);
    return MU_APPLY_DONE;
}

mu_apply hero_speed(mu_session *s, const mu_frame *f)
{
    mu_prg_env env = hero_call(s, 0x0122a13du, -1);
    mu_prg_recv_speed(&env, f->bytes);
    mu_session_touch(s, MU_DOMAIN_HERO);
    return MU_APPLY_DONE;
}

mu_apply hero_respawn(mu_session *s, const mu_frame *f)
{
    mu_prg_env env = hero_call(s, 0x0127bd9eu, -1);
    mu_prg_respawn out;
    memset(&out, 0, sizeof out);
    mu_prg_recv_respawn(&env, f->bytes, &out);   /* the attribute part, verified */
    s->hero.money = out.money;                   /* CharacterMachine +0x2d70 (+0x1c) */
    mu_session_touch(s, MU_DOMAIN_HERO);
    /* the rest is a static reading (progress.h): the hero recreated at +4/+5 with the angle
     * (+8 - 1) * 45, and when +6 differs from World [0x01cf15fc] the world changes */
    int32_t old_world = s->place.world;
    mu_place place = {out.map, {out.x, out.y}, out.angle, 0};
    mu_session_set_place(s, &place);
    if (out.map != old_world)
        return MU_APPLY_WORLD_CHANGE;
    if (s->has_port && s->port.place_hero)
        s->port.place_hero(s->port.context, &s->place);
    return MU_APPLY_DONE;
}

/* ---- submit functions ------------------------------------------------------------------------- */

mu_submit hero_add_stat(mu_session *s, const mu_intent *in)
{
    /* the CharacterInfoSetup row ids of the five "+" buttons (0x00b469c4) */
    static const double ROW[5] = {8, 13, 24, 29, 42};
    mu_submit r = {MU_SUBMIT_REFUSED, -1};
    int32_t stat = in->u.add_stat.stat;
    if (stat < 0 || stat > 4)
        return r;
    if (s->phase != MU_PHASE_IN_WORLD) {
        r.status = MU_SUBMIT_NOT_NOW;
        return r;
    }
    if (mu_prg_stat_button(s->hero.attr, ROW[stat]) < 0)
        return r;                                /* no free points: the client sends nothing */
    mu_prg_env env = hero_call(s, 0x00b48acau, -1);
    uint8_t req[5];
    if (!mu_prg_stat_request(&env, &s->hero.last_stat_request, s->now, stat, req)) {
        r.status = MU_SUBMIT_THROTTLED;
        return r;
    }
    /* the builder calls of 0x00b48aca (static reading): Begin(C1, 0x01); 0x0095c204(0) and
     * 0x0095c204(stat), each AddData(&b, 1, 1) (XorData-encoded); Send(0, 0): sent as built */
    mu_packet p;
    mu_packet_begin(&p, req[0], req[2]);
    mu_packet_add(&p, &req[3], 1, 1);
    mu_packet_add(&p, &req[4], 1, 1);
    int rc = mu_session_send(s, &p, s->hero.send_seen ? s->hero.send_args[0] : 0);
    r.status = rc == MU_SEND_OK ? MU_SUBMIT_SENT : MU_SUBMIT_NOT_NOW;
    return r;
}

mu_submit hero_master_point(mu_session *s, const mu_intent *in)
{
    return mu_session_unrecovered(s, in, "the master skill point request is not reconstructed");
}

/* ---- domain hooks ----------------------------------------------------------------------------- */

void mu_dom_hero_init(mu_session *s)
{
    memset(&s->hero, 0, sizeof s->hero);
    s->hero.cue_key = -1;
}

void mu_dom_hero_free(mu_session *s)
{
    (void)s;
}

void mu_dom_hero_zones(const mu_session *s, mu_audit_zones *z)
{
    const mu_dom_hero *h = &s->hero;
    mu_audit_layout(z, "hero.attr", h->attr, sizeof h->attr, &MU_CharacterAttribute_LAYOUT);
    mu_audit_layout(z, "hero.machine", h->machine, sizeof h->machine, &MU_StatMachine_LAYOUT);
    mu_audit_layout(z, "hero.record", h->record, sizeof h->record, &MU_CHARACTER_LAYOUT);
    mu_audit_add(z, "hero.money", (const uint8_t *)&h->money, 0, sizeof h->money, MU_ZONE_REPLICATED, "money");
}

void mu_dom_hero_step(mu_session *s, const mu_sim *sim)
{
    (void)s;
    (void)sim;   /* the hero's handlers keep no timers */
}

#ifdef MU_SESSION_SEED
void mu_dom_hero_seed(mu_session *s, const struct mu_session_seed *seed)
{
    mu_dom_hero *h = &s->hero;
    h->record[0x12] = seed->class_byte;
    h->attr[MU_PRG_A_CLASS] = seed->class_byte;
    mu_prg_set32(h->attr, MU_PRG_A_LEVEL, (uint32_t)(seed->level > 0 ? seed->level : 1));
    snprintf(h->name, sizeof h->name, "%s", seed->name);
    mu_session_touch(s, MU_DOMAIN_HERO);
}
#endif

/* ---- the public getters (domains/hero.h) -------------------------------------------------------- */

void mu_session_hero(const mu_session *s, mu_hero_stats *v)
{
    memset(v, 0, sizeof *v);
    if (!s)
        return;
    const uint8_t *a = s->hero.attr;
    uint8_t cls = mu_layout_CHARACTER_class_byte(s->hero.record, sizeof s->hero.record, 0);
    snprintf(v->name, sizeof v->name, "%s", s->hero.name);
    v->class_byte = a[MU_PRG_A_CLASS];
    v->class_index = a[MU_PRG_A_CLASS] & 15;
    v->stage = mu_prg_class_stage(cls);
    v->level = mu_layout_CharacterAttribute_level(a, sizeof s->hero.attr, 0);
    v->master_level = mu_prg_master_level(a);
    v->points = mu_layout_CharacterAttribute_points(a, sizeof s->hero.attr, 0);
    v->master_points = mu_layout_CharacterAttribute_mpoints(a, sizeof s->hero.attr, 0);
    v->exp = (int64_t)mu_layout_CharacterAttribute_exp(a, sizeof s->hero.attr, 0);
    v->next_exp = (int64_t)mu_layout_CharacterAttribute_next_exp(a, sizeof s->hero.attr, 0);
    v->master_exp = (int64_t)mu_layout_CharacterAttribute_mexp(a, sizeof s->hero.attr, 0);
    v->master_next_exp = (int64_t)mu_layout_CharacterAttribute_mnext_exp(a, sizeof s->hero.attr, 0);
    static const size_t BASE[5] = {MU_PRG_A_STRENGTH, MU_PRG_A_DEXTERITY, MU_PRG_A_VITALITY, MU_PRG_A_ENERGY,
                                   MU_PRG_A_COMMAND};
    static const size_t ADD[5] = {MU_PRG_A_ADD_STR, MU_PRG_A_ADD_DEX, MU_PRG_A_ADD_VIT, MU_PRG_A_ADD_ENE,
                                  MU_PRG_A_ADD_CMD};
    for (int i = 0; i < 5; i++) {
        v->stats[i] = mu_prg_u16(a, BASE[i]);
        v->added[i] = mu_prg_u16(a, ADD[i]);
    }
    /* setHPMP 0x00c71772 (static): a third-class hero's maxima are +0x40..+0x4c */
    int third = (cls >> 5 & 1) == 1;
    v->hp = mu_layout_CharacterAttribute_life(a, sizeof s->hero.attr, 0);
    v->mp = mu_layout_CharacterAttribute_mana(a, sizeof s->hero.attr, 0);
    v->sd = mu_layout_CharacterAttribute_shield(a, sizeof s->hero.attr, 0);
    v->ag = mu_layout_CharacterAttribute_ag(a, sizeof s->hero.attr, 0);
    v->max_hp = mu_prg_i32(a, third ? MU_PRG_A_MLIFE_MAX : MU_PRG_A_LIFE_MAX);
    v->max_mp = mu_prg_i32(a, third ? MU_PRG_A_MLIFE_MAX + 4 : MU_PRG_A_MANA_MAX);
    v->max_sd = mu_prg_i32(a, third ? MU_PRG_A_MLIFE_MAX + 8 : MU_PRG_A_SHIELD_MAX);
    v->max_ag = mu_prg_i32(a, third ? MU_PRG_A_MLIFE_MAX + 12 : MU_PRG_A_AG_MAX);
    v->attack_speed = mu_layout_CharacterAttribute_atk_speed(a, sizeof s->hero.attr, 0);
    v->magic_speed = mu_layout_CharacterAttribute_magic_speed(a, sizeof s->hero.attr, 0);
    v->has_derived = s->hero.recalculated;
    v->dmg_min = mu_layout_CharacterAttribute_dmg_min_r(a, sizeof s->hero.attr, 0);
    v->dmg_max = mu_layout_CharacterAttribute_dmg_max_r(a, sizeof s->hero.attr, 0);
    v->atk_rate = mu_layout_CharacterAttribute_atk_rate(a, sizeof s->hero.attr, 0);
    v->pvp_rate = mu_layout_CharacterAttribute_pvp_rate(a, sizeof s->hero.attr, 0);
    v->defense = mu_layout_CharacterAttribute_defense(a, sizeof s->hero.attr, 0);
    v->def_rate = mu_layout_CharacterAttribute_def_rate(a, sizeof s->hero.attr, 0);
    v->pvp_defrate = mu_layout_CharacterAttribute_pvp_defrate(a, sizeof s->hero.attr, 0);
    v->magic_min = mu_layout_CharacterAttribute_magic_min(a, sizeof s->hero.attr, 0);
    v->magic_max = mu_layout_CharacterAttribute_magic_max(a, sizeof s->hero.attr, 0);
    v->curse_min = mu_layout_CharacterAttribute_curse_min(a, sizeof s->hero.attr, 0);
    v->curse_max = mu_layout_CharacterAttribute_curse_max(a, sizeof s->hero.attr, 0);
}

int64_t mu_session_money(const mu_session *s)
{
    return s ? (int64_t)s->hero.money : 0;
}

const char *mu_session_hero_exp_bar(const mu_session *s)
{
    return s ? s->hero.exp_json : "";
}

const char *mu_session_hero_speed_text(const mu_session *s)
{
    return s ? s->hero.speed_text : "";
}
