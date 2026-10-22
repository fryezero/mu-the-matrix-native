/* The hero's skills on the game side of the interface (NATIVE-SKILL-001); see skill_use.h. */
#include "skill_use.h"

#include <stdio.h>
#include <string.h>

#ifndef MU_SKILL_MUTATION
#define MU_SKILL_MUTATION 0
#endif

static const mu_skill_record zero_record;

const mu_skill_record *mu_skill_record_of(const mu_skill_env *env, int32_t skill)
{
    const mu_skill_record *r = env && env->table ? mu_skill_table_get(env->table, skill) : NULL;
    return r ? r : &zero_record;
}

static int32_t base_of(const mu_skill_env *env, int32_t skill)
{
    return env && env->base_skill ? env->base_skill(env->user, skill) : skill;
}

static int has_buff(const mu_skill_env *env, int hero_list, int32_t buff)
{
    return env && env->buff ? env->buff(env->user, hero_list, buff) != 0 : 0;
}

int mu_skill_stats_ok(const mu_skill_env *env, const mu_skill_hero *hero, int32_t skill)
{
    const mu_skill_record *r = mu_skill_record_of(env, skill);
    if (r->index == 0)
        return 0;
    if (hero->class_index == 1 && r->req_strength != 0 && r->req_energy != 0) {
        if ((int32_t)hero->strength < r->req_strength && (int32_t)hero->energy < r->req_energy)
            return 0;
    } else {
        if ((int32_t)hero->strength < r->req_strength)
            return 0;
#if MU_SKILL_MUTATION == 3
        if ((int32_t)hero->energy <= r->req_energy)      /* planted: <= instead of < */
#else
        if ((int32_t)hero->energy < r->req_energy)
#endif
            return 0;
    }
    if ((int32_t)hero->agility < r->req_dexterity)
        return 0;
    if ((int32_t)hero->command < r->req_command)
        return 0;
    if ((int32_t)hero->vitality < r->req_vitality)
        return 0;
    return 1;
}

int32_t mu_skill_info_skill(int32_t skill)
{
    if (skill == 0x3a || skill == 0x28)
        return 0x28;
    if (skill == 0x18b || skill == 0x188)
        return 0x188;
    return skill;
}

int mu_skill_mana_ok(const mu_skill_env *env, const mu_skill_hero *hero, int32_t skill, int32_t base, int32_t mana,
                     int32_t ag, int *potion)
{
    if (skill == 0x28 || skill == 0x188)
        ag = 0;
    if (base == 0x18 && (has_buff(env, 0, 6) || has_buff(env, 0, 0x8f)))
        mana += hero->mana_bonus;
    if (has_buff(env, 0, 0x125) || has_buff(env, 0, 0x127) || has_buff(env, 0, 0x128))
        mana += 0xfa;
    if (has_buff(env, 0, 0x126) || has_buff(env, 0, 0x12a) || has_buff(env, 0, 0x12b))
#if MU_SKILL_MUTATION == 7
        ag += 3;                                     /* planted */
#else
        ag += 2;
#endif
    int ok = 1;
    if (potion)
        *potion = 0;
    if (hero->mana < mana) {
        if (potion)
            *potion = 1;
        ok = 0;
    }
    if (hero->ag < ag)
        ok = 0;
    return ok;
}

/* The class skill tree's adjustment shared by StartSkillDelay, IsSkillReady and the tooltip:
 * the node of the class's mapped skill (else the skill itself); value 0x3fb == 1 cancels the delay,
 * else value 0x3fa is subtracted.  Returns 1 when a node exists. */
static int tree_adjust(const mu_skill_env *env, int32_t skill, int32_t *cancel, int32_t *minus)
{
    int32_t key = skill;
    if (env && env->tree_map) {
        int32_t mapped = env->tree_map(env->user, env->class_index, skill);
        if (mapped != -1)
            key = mapped;
    }
    if (!env || !env->tree_node || !env->tree_node(env->user, key))
        return 0;
    *cancel = env->tree_value ? env->tree_value(env->user, key, 0x3fb) == 1 : 0;
    *minus = !*cancel && env->tree_value ? env->tree_value(env->user, key, 0x3fa) : 0;
    return 1;
}

int32_t mu_skill_delay_of(const mu_skill_env *env, int32_t skill)
{
    int32_t delay = mu_skill_record_of(env, skill)->delay;
    if (env && env->master_has_delay && env->master_has_delay(env->user, skill)) {
        float value = env->master_value ? env->master_value(env->user, skill, 2) : 0.0f;
        delay -= (int32_t)(value * 1000.0f);     /* cvttss2si of value * [0x01a7e950] (1000.0) */
    }
    int32_t cancel = 0, minus = 0;
    if (tree_adjust(env, skill, &cancel, &minus))
        delay = cancel ? 0 : delay - minus;
    return delay;
}

int mu_skill_delay_start(const mu_skill_env *env, mu_skill_hero *hero, int32_t skill, int32_t out_events[2][2])
{
    int events = 0;
    int32_t delay = mu_skill_delay_of(env, skill);
    if (delay <= 0)
        return 0;
    for (int i = 0; i < hero->count; i++)
        if (hero->skills[i] == skill && hero->timers[i] == 0)
            hero->timers[i] = delay;
    out_events[events][0] = skill;
    out_events[events][1] = delay;
    events++;
    /* 0x01696ca6: skills whose base is 0xdd or 0xde share the delay */
    int32_t base = base_of(env, skill), other = base == 0xdd ? 0xde : base == 0xde ? 0xdd : 0;
    if (!other)
        return events;
    int32_t last = 0;
    for (int i = 0; i < hero->count; i++)
        if (base_of(env, hero->skills[i]) == other && hero->timers[i] == 0) {
            hero->timers[i] = delay;
            last = hero->skills[i];
        }
    if (last) {
        out_events[events][0] = last;
        out_events[events][1] = delay;
        events++;
    }
    return events;
}

int mu_skill_ready(const mu_skill_env *env, const mu_skill_hero *hero, int index)
{
    int32_t skill = hero->skills[index];
    int32_t delay = mu_skill_record_of(env, skill)->delay;
    int32_t cancel = 0, minus = 0;
    if (tree_adjust(env, skill, &cancel, &minus))
        delay = cancel ? 0 : delay - minus;
    return !(delay > 0 && hero->timers[index] > 0);
}

void mu_skill_delay_tick(mu_skill_hero *hero, int32_t dt)
{
    int n = hero->count < MU_SKILL_TICK_MAX ? hero->count : MU_SKILL_TICK_MAX;
    for (int i = 0; i < n; i++) {
        if (hero->timers[i] <= 0)
            continue;
        hero->timers[i] -= dt;
#if MU_SKILL_MUTATION == 6
        (void)0;                                     /* planted: a timer that crosses 0 is not clamped */
#else
        if (hero->timers[i] <= 0)
            hero->timers[i] = 0;
#endif
    }
}

int mu_skill_special_ok(const mu_skill_env *env, int32_t skill)
{
    int32_t cls = env ? env->class_index : 0;
#if MU_SKILL_MUTATION == 11
    if (cls == 4) {                                  /* planted */
#else
    if (cls == 5) {
#endif
        int32_t base = base_of(env, skill);
        if (base == 0xdf || base == 0xe0 || base == 0xe1 || base == 0x120 || base == 0x80b || base == 0x80c)
            return has_buff(env, 2, 0x12d);
    }
    if (cls == 1 && base_of(env, skill) == 0x5df)
        return has_buff(env, 2, 0x145);
    return 1;
}

int32_t mu_skill_selected_slot(const mu_skill_hotkeys *h)
{
    if (h->selected != 0)
        for (int i = 0; i < MU_SKILL_SLOTS; i++)
            if (h->slots[i] == h->selected)
                return i;
    for (int i = 0; i < MU_SKILL_SLOTS; i++)
        if (h->slots[i] != 0)
            return i;
    return 0;
}

static int usable_of(mu_skill_usable_fn fn, void *user, int32_t skill)
{
    return skill != 0 && fn && fn(user, skill) != 0;
}

int mu_skill_bar_feed(const mu_skill_env *env, mu_skill_bar *bar, const mu_skill_hero *hero,
                      const mu_skill_hotkeys *hotkeys, mu_skill_usable_fn usable, void *usable_user, char *json,
                      size_t cap)
{
    if (bar->elemental != hero->elemental) {
        bar->dirty = 1;
        bar->elemental = hero->elemental;
    }
    int32_t slot = mu_skill_selected_slot(hotkeys);
    if (bar->select_slot != slot) {
        bar->dirty = 1;
        bar->select_slot = slot;
    }
    int32_t skill = hotkeys->selected;
    uint8_t use = (uint8_t)usable_of(usable, usable_user, skill);
    if (bar->select_skill != skill) {
        bar->dirty = 1;
        bar->select_skill = skill;
    }
    if (bar->select_use != use) {
        bar->dirty = 1;
        bar->select_use = use;
    }
    for (int i = 0; i < MU_SKILL_SLOTS; i++) {
        int32_t s = hotkeys->slots[i];
        uint8_t u = (uint8_t)usable_of(usable, usable_user, s);
#if MU_SKILL_MUTATION == 4
        if (bar->slots[i].skill != s) {     /* planted: a usability change alone is not noticed */
#else
        if (bar->slots[i].use != u || bar->slots[i].skill != s) {
#endif
            bar->dirty = 1;
            bar->slots[i].use = u;
            bar->slots[i].skill = s;
            bar->slots[i].damage_type = mu_skill_record_of(env, s)->damage_type;
        }
    }
    if (!bar->dirty)
        return 0;
    bar->dirty = 0;
    if (json && cap) {
        size_t n = (size_t)snprintf(json, cap,
                                    "{\"Elemental\":%d,\"SelectSlot\":%d,\"SelectUseSkill\":%s,\"SelectSkill\":%d,"
                                    "\"SelectSkill_damageType\":%d,\"arrSlots\":[",
                                    bar->elemental, bar->select_slot, bar->select_use ? "true" : "false",
                                    bar->select_skill, mu_skill_record_of(env, skill)->damage_type);
        for (int i = 0; i < MU_SKILL_SLOTS && n < cap; i++)
            n += (size_t)snprintf(json + n, cap - n, "%s{\"slot\":%d,\"skill\":%d,\"isUse\":%s,\"damageType\":%d}",
                                  i ? "," : "", i, bar->slots[i].skill, bar->slots[i].use ? "true" : "false",
                                  bar->slots[i].damage_type);
        if (n < cap)
            snprintf(json + n, cap - n, "]}");
    }
    return 1;
}

int mu_skill_learned_index(const mu_skill_hero *hero, int32_t skill)
{
    if (skill == 0)
        return -1;
    for (int i = 0; i < hero->count; i++)
        if (hero->skills[i] == skill)
            return i;
    return -1;
}

int mu_skill_select(const mu_skill_env *env, mu_skill_hero *hero, mu_skill_hotkeys *hotkeys, int32_t slot_skill)
{
    int index = mu_skill_learned_index(hero, slot_skill);
    if (index < 0 || hero->current == index)
        return 0;
    if (hero->mounted && hero->mount_kind == 7 && mu_skill_record_of(env, hero->skills[index])->type != 7)
        return 0;
    hero->current = (uint8_t)index;
    int32_t skill = hero->skills[hero->current];
    if (hotkeys->selected != skill)
        hotkeys->selected = skill;          /* 0x00a081eb: the hotkeys select it (and tell the server) */
    return 1;
}

int mu_skill_icon_of(const mu_skill_env *env, int32_t base, int32_t learned, int usable, float cell_w, float cell_h,
                     mu_skill_icon *out)
{
    uint16_t skill = (uint16_t)(learned ? learned : base);
    if (!skill)
        return 0;
    const mu_skill_record *r = mu_skill_record_of(env, skill);
    int32_t kind = r->use_type, sheet = r->icon / 0x1c2, cell = r->icon % 0x1c2;
    if (skill >= 0x78 && skill <= 0x7c)
        cell = skill;
    int on = usable && learned;
    int32_t bitmap = 0;
    if (kind == 0 || kind == 1)
        bitmap = on ? 0x7c40 : 0x7c43;
    else if (kind == 3 || kind == 4)
        bitmap = sheet + (on ? 0x7e18 : 0x7e1a);
    else if (kind == 7 || kind == 8 || kind == 9) {
        if (usable && env && env->tree_learned)
            usable = env->tree_learned(env->user, skill);
        bitmap = usable && learned ? 0x7e1c : 0x7e1d;
    } else if (kind == 0xe)
        bitmap = on ? 0x7e22 : 0x7e23;
    if (!bitmap)
        return 0;
    out->bitmap = bitmap;
#if MU_SKILL_MUTATION == 9
    out->u = cell_w / 512.0f * (float)(cell % 24);   /* planted */
#else
    out->u = cell_w / 512.0f * (float)(cell % 25);
#endif
    out->v = cell_h / 512.0f * (float)(cell / 25);
    out->uw = cell_w / 512.0f;
    out->vh = cell_h / 512.0f;
    return 1;
}
