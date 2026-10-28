/* hudPlayerName's game side in the walk-around world (NATIVE-NAMES-001); see mu_world_names.h. */
#include "mu_world_names.h"

#include "mu_lang.h"

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int32_t actor_key(const mu_world_names *wn, int32_t i) { return wn->actor_key0 + i; }

static int monster_alive(const mu_world_names *wn, int32_t i)
{
    if (!wn->combat)
        return 1;
    return !wn->combat->monsters[i].dead && !wn->combat->monsters[i].removed;
}

static void hero_record(mu_world_names *wn)
{
    mu_hn_character *c = mu_names_find(&wn->names, wn->hero_key);
    if (!c)
        return;
    c->class_byte = wn->walk->hero.class_byte;
    c->wing = (int16_t)(wn->hero_wing ? 0 : -1);   /* the wing type word; only -1 / not -1 matters here */
    memcpy(c->position, wn->walk->hero.position, sizeof c->position);
    if (wn->combat) {
        c->hp = (uint32_t)(wn->combat->hero_hp > 0 ? wn->combat->hero_hp : 0);
        c->max_hp = (uint32_t)(wn->combat->config.hero_hp > 0 ? wn->combat->config.hero_hp : 1);
        c->live = !wn->combat->hero_dead;
    }
}

static void actor_record(mu_world_names *wn, int32_t i)
{
    mu_hn_character *c = mu_names_find(&wn->names, actor_key(wn, i));
    if (!c)
        return;
    const mu_world_actor *a = &wn->actors->list[i];
    memcpy(c->position, a->position, sizeof c->position);
    c->live = (uint8_t)monster_alive(wn, i);
}

int mu_world_names_init(mu_world_names *wn, const mu_world_names_config *cfg, mu_walk *walk,
                        mu_world_actors *actors, mu_combat *combat)
{
    memset(wn, 0, sizeof *wn);
    mu_names_init(&wn->names);
    wn->walk = walk;
    wn->actors = actors;
    wn->combat = combat;
    wn->hero_key = combat ? combat->hero_key : 0x1234;
    wn->actor_key0 = 0x100;
    wn->hovered = -1;
    wn->hover_enabled = 1;
    mu_names_set_monster_view(&wn->names, cfg && !cfg->monster_view ? 0 : 1);
    wn->has_fonts = mu_label_fonts_open(&wn->fonts, cfg ? cfg->font_face : NULL) == 0;
    /* the Npcname(kor) table of NATIVE-LANG-001 (MU_LANG_DIR or the config's directory) */
    if (cfg && cfg->lang_dir) {
        wn->own_lang = mu_lang_load(cfg->lang_dir);
        wn->lang = wn->own_lang;
    } else
    {
        wn->own_lang = mu_lang_load_default();
        wn->lang = wn->own_lang;
    }
    int32_t hero_level = cfg && cfg->hero_level > 0 ? cfg->hero_level : 400;
    wn->names.env.hero_level = hero_level;
    /* the hero: the join packet's CreateHero, then addInfo (0x0124cc64) */
    mu_hn_character *hero = mu_names_character(&wn->names, wn->hero_key);
    if (hero) {
        snprintf(hero->name, sizeof hero->name, "%s", cfg && cfg->hero_name ? cfg->hero_name : "Nighty");
        hero->kind = MU_HN_PLAYER;
        hero->level = (uint16_t)hero_level;
        hero->pk = 3;
        hero->max_hp = hero->hp = 100;
        mu_names_set_hero(&wn->names, wn->hero_key);
        hero_record(wn);
    }
    /* monsters and NPCs: the viewport packet's CreateMonster + SetMonsterInfo, then addInfo */
    for (int32_t i = 0; actors && i < actors->count && i < MU_WORLD_ACTORS_MAX; ++i) {
        const mu_world_actor *a = &actors->list[i];
        mu_hn_character *c = mu_names_character(&wn->names, actor_key(wn, i));
        if (!c)
            break;
        int32_t cls = a->server_class;
        c->monster_class = (int16_t)cls;
        c->kind = mu_hn_monster_kind(cls);
        /* SetMonsterInfo 0x013b8ade: name 0x011427c7, name height +0x1c, mark +0x20 */
        const mu_lang_npc *npc = wn->lang ? mu_lang_npc_get(wn->lang, cls) : NULL;
        if (npc && npc->name) {
            snprintf(c->name, sizeof c->name, "%s", npc->name);
            c->height = (uint16_t)npc->x1c;
            c->mark = npc->x20;
            wn->npc_count++;
        } else {   /* placeholders: the placement label, title case; height 200 */
            snprintf(c->name, sizeof c->name, "%s", a->label[0] ? a->label : "Monster");
            for (char *p = c->name; *p; ++p)
                if (p == c->name || p[-1] == ' ')
                    *p = (char)toupper((unsigned char)*p);
            c->height = 200;
        }
        c->level = 0;   /* DEMO: the server's monster level */
        /* Damage frames do not supply remote HP. Until an HP route is recovered, use only viewport values. */
        c->max_hp = combat && combat->monsters[i].max_hp ? combat->monsters[i].max_hp : 1;
        c->hp = combat ? combat->monsters[i].hp : 0;
        wn->hp_seen[i] = c->hp;
        actor_record(wn, i);
    }
    return 0;
}

/* The join packet's addInfo for the hero and the viewport packets' for the others: on the first frame, once the
 * camera exists (the clips take their first position from addInfo's x/y in onLoad). */
static void create_all(mu_world_names *wn)
{
    wn->created = 1;
    mu_names_add(&wn->names, wn->hero_key);
    for (int32_t i = 0; wn->actors && i < wn->actors->count && i < MU_WORLD_ACTORS_MAX; ++i)
        wn->shown[i] = (uint8_t)mu_names_add(&wn->names, actor_key(wn, i));
}

void mu_world_names_free(mu_world_names *wn)
{
    if (wn->has_fonts)
        mu_label_fonts_close(&wn->fonts);
    if (wn->own_lang)
        mu_lang_free(wn->own_lang);
    memset(wn, 0, sizeof *wn);
}

void mu_world_names_step(mu_world_names *wn)
{
    if (!wn->combat || !wn->actors || !wn->created)
        return;
    for (int32_t i = 0; i < wn->actors->count && i < MU_WORLD_ACTORS_MAX; ++i) {
        mu_hn_character *c = mu_names_find(&wn->names, actor_key(wn, i));
        if (!c || c->kind != MU_HN_MONSTER)
            continue;
        const mu_combat_monster *m = &wn->combat->monsters[i];
        c->max_hp=m->max_hp?m->max_hp:1;
        int32_t key = actor_key(wn, i);
        if (m->dead >= 15 && !wn->dead_seen[i]) {
            /* MoveCharacter calls SetPlayerDie 0x01393a61 from dead counter 15 on (mu_combat); for a
             * non-Player model it removes the plate (removeInfo) */
            wn->dead_seen[i] = 1;
            mu_names_remove(&wn->names, key, 0);
            wn->shown[i] = 0;
        }
        if (!m->dead && !m->removed && wn->dead_seen[i]) {
            /* DEMO respawn: the server creates the monster again (viewport packet -> addInfo) */
            wn->dead_seen[i] = 0;
            c->hp = m->hp;
            wn->hp_seen[i] = m->hp;
            actor_record(wn, i);
            wn->shown[i] = (uint8_t)mu_names_add(&wn->names, key);
        }
        if (!wn->dead_seen[i] && m->hp != wn->hp_seen[i]) {
            /* Session viewport HP changed. A separate HP-update route remains unrecovered here. */
            wn->hp_seen[i] = m->hp;
            c->hp = m->hp;
            mu_names_set_hp(&wn->names, key, c->hp, c->max_hp);
        }
    }
}

/* Demo picking of the character under the cursor (mu_combat's cylinder rule over every actor). */
static int32_t pick(const mu_world_names *wn)
{
    if (!wn->actors)
        return -1;
    const mu_client_view *v = &wn->walk->frame.view;
    float o[3] = {v->position[0], v->position[1], v->position[2]};
    float d[3] = {v->mouse_target[0] - o[0], v->mouse_target[1] - o[1], v->mouse_target[2] - o[2]};
    float len = sqrtf(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
    if (!(len > 0.0f))
        return -1;
    for (int k = 0; k < 3; ++k)
        d[k] /= len;
    int32_t best = -1;
    float best_t = 1e30f;
    for (int32_t i = 0; i < wn->actors->count && i < MU_WORLD_ACTORS_MAX; ++i) {
        if (!monster_alive(wn, i))
            continue;
        const mu_world_actor *a = &wn->actors->list[i];
        float scale = a->actor.spec.scale > 0.0f ? a->actor.spec.scale : 1.0f;
        float radius = 70.0f * scale, height = 200.0f * scale;
        for (int s = 0; s <= 8; ++s) {
            float axis[3] = {a->position[0], a->position[1], a->position[2] + height * (float)s / 8.0f};
            float w[3] = {axis[0] - o[0], axis[1] - o[1], axis[2] - o[2]};
            float t = w[0] * d[0] + w[1] * d[1] + w[2] * d[2];
            if (t <= 0.0f)
                continue;
            float q[3] = {o[0] + d[0] * t - axis[0], o[1] + d[1] * t - axis[1], o[2] + d[2] * t - axis[2]};
            if (q[0] * q[0] + q[1] * q[1] + q[2] * q[2] <= radius * radius && t < best_t) {
                best_t = t;
                best = i;
            }
        }
    }
    return best;
}

static void project(void *context, const float position[3], float *x, float *y)
{
    const mu_world_names *wn = context;
    mu_view_projection_float(&wn->walk->frame.view, position, x, y);   /* 0x0184a3ce */
}

void mu_world_names_frame(mu_world_names *wn, uint32_t now_ms)
{
    hero_record(wn);
    for (int32_t i = 0; wn->actors && i < wn->actors->count && i < MU_WORLD_ACTORS_MAX; ++i)
        actor_record(wn, i);
    if (wn->combat) {
        wn->names.env.hero_hp = wn->combat->hero_hp;
        wn->names.env.hero_max_hp = wn->combat->config.hero_hp > 0 ? wn->combat->config.hero_hp : 1;
    }
    if (!wn->created)
        create_all(wn);
    if (wn->hover_enabled) {
        int32_t i = pick(wn);
        wn->hovered = i;
        mu_names_hover(&wn->names, i >= 0 ? actor_key(wn, i) : -1);
    }
    mu_names_update(&wn->names, project, wn, now_ms);
}

void mu_world_names_chat(mu_world_names *wn, const char *name, const char *text)
{
    mu_names_chat(&wn->names, name, text, 0);
}

void mu_world_names_draw(mu_world_names *wn, uint8_t *frame, int32_t width, int32_t height)
{
    if (wn->has_fonts)
        mu_names_draw(&wn->names, &wn->fonts, frame, width, height);
}
