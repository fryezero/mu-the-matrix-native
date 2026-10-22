/* The usability check of a skill (NATIVE-SKILL-002); see skill_canuse.h. */
#include "skill_canuse.h"

#ifndef MU_SKILL_MUTATION
#define MU_SKILL_MUTATION 0
#endif

static int buff(const mu_skill_use_env *env, int list, int32_t id)
{
    const mu_skill_env *s = env->skills;
    return s && s->buff ? s->buff(s->user, list, id) != 0 : 0;
}

static int kind(const mu_skill_use_env *env, int slot, int k)
{
    return env->item_kind ? env->item_kind(env->user, slot, k) != 0 : 0;
}

static int32_t base_of(const mu_skill_use_env *env, int32_t skill)
{
    const mu_skill_env *s = env->skills;
    if (s && s->base_skill)
        return s->base_skill(s->user, skill);
    /* 0x00bb1c32 over the table */
    const mu_skill_record *r = mu_skill_record_of(s, skill);
    if (r->index == 0)
        return skill;
    int32_t last = skill;
    for (int32_t b = r->brand; b != 0 && b != 0x4b;) {
        const mu_skill_record *n = mu_skill_record_of(s, b);
        last = n->index;
        b = n->brand;
    }
    return last;
}

int mu_skill_illusion_temple(int32_t w) { return (w >= 0x62 && w <= 0x63) || (w >= 0x2d && w <= 0x32); }
int mu_skill_chaos_castle(int32_t w) { return (w >= 0x12 && w <= 0x17) || w == 0x35 || w == 0x61; }
int mu_skill_blood_castle(int32_t w) { return (w >= 0xb && w <= 0x11) || w == 0x34; }

int mu_skill_hero_knows(const mu_skill_env *skills, const mu_skill_hero *hero, int32_t skill)
{
    for (int i = 0; i < hero->count; i++) {
        int32_t s = hero->skills[i];
        if (s == skill)
            return 1;
        for (int32_t b = mu_skill_record_of(skills, s)->brand; b != 0; b = mu_skill_record_of(skills, b)->brand)
            if (b == skill)
                return 1;
    }
    return 0;
}

int mu_skill_require_ok(const mu_skill_use_env *env, const mu_skill_hero *hero, int32_t skill)
{
    int32_t need = 0, master = 0, level = 0;
    if (!env->skill_require || !env->skill_require(env->user, base_of(env, skill), &need, &master, &level))
        return 1;
    if (!mu_skill_hero_knows(env->skills, hero, need))
        return 0;
    int have = env->master_level ? (uint8_t)env->master_level(env->user, master) : 0;
    return level <= have;
}

int mu_skill_world_ok(const mu_skill_use_env *env, int32_t base)
{
    int32_t w = env->world;
    if (mu_skill_illusion_temple(w)) {
        int relic = env->it_relic ? env->it_relic(env->user) != 0 : 0;
        if (base == 0x3f && !relic)
            return 0;
        if (base == 0xd4 && relic)
            return 0;
        if (base == 0x26c && relic)
            return 0;
        return 1;
    }
    if (mu_skill_chaos_castle(w)) {
        if ((base >= 0x1e && base <= 0x24) || base == 0x1b0 || base == 0x282)
            return 0;
        if (base == 0x3e || base == 0x31 || base == 0x4c)
            return 0;
        return 1;
    }
    if (w >= 0x52 && w <= 0x5a)
        return base != 0x3f;
    if (env->event_flag)
        return base != 0x3f;
    if (env->event_map && env->event_map(env->user, w) == 1)
        return 1;
    if (w == 0x1e && env->siege == 1)
        return 1;
    if (w == 0xa || w == 0x84)
        return !((base >= 0x1e && base <= 0x24) || base == 0x1b0);
    return 1;
}

/* 0x0139d994: 1 bow (kind 8), 2 crossbow (kind 9) in the weapon slot */
static int bow_kind(const mu_skill_use_env *env)
{
    return kind(env, 0, 8) ? 1 : kind(env, 0, 9) ? 2 : 0;
}

static int arrows(const mu_skill_use_env *env, int auto_reload)
{
    return env->arrows ? env->arrows(env->user, auto_reload) != 0 : 1;
}

/* 0x01092597: rings 13/10 (code 0x1a0a) below level 2 or above, and 13/68 (0x1a44) block skills */
static int ring_blocks(const mu_skill_use_env *env)
{
    for (int i = 10; i <= 11; i++) {
        int32_t c = env->items[i].code;
        int level = (env->items[i].level_bits >> 3) & 0xf;
        if ((c == 0x1a0a && level != 2) || c == 0x1a44)
            return 1;
    }
    return 0;
}

int mu_skill_can_use(const mu_skill_use_env *env, const mu_skill_hero *hero, int32_t skill)
{
    const mu_skill_env *s = env->skills;
    int32_t base = base_of(env, skill);
    const mu_skill_record *rb = mu_skill_record_of(s, base);
    const mu_skill_record *rs = mu_skill_record_of(s, skill);
    /* 0x016a500c: the siege rule 0x016a8342, then use type 2 needs buff 0x13 on the character's list */
    if (rs->brand == 0x4b && !(env->world == 0x1e && env->siege != 0))
        return 0;
    if (rs->use_type == 2 && !buff(env, 0, 0x13))
        return 0;
    if (!mu_skill_stats_ok(s, hero, skill))
        return 0;
    int transformed = env->transform != 0xffff;
    if (rb->xb0 == 1 && !transformed)
        return 0;
    if (rb->xb0 == 2 && transformed)
        return 0;
    switch (rb->weapon) {
    case 1:
        if (env->special_item && !env->special_item(env->user, skill))
            return 0;
        if (bow_kind(env) && !arrows(env, 1))
            return 0;
        break;
    case 2:
        if (!(kind(env, 0, 1) || kind(env, 0, 2) || kind(env, 0, 3) || kind(env, 0, 4) || kind(env, 0, 5) ||
              kind(env, 0, 6) || kind(env, 0, 7) || kind(env, 0, 0x51) || kind(env, 0, 0x54) || kind(env, 0, 0x7b)))
            return 0;
        break;
    case 3:
        if (!(kind(env, 0, 1) || kind(env, 0, 2)))
            return 0;
        break;
    case 4:
        if (!kind(env, 0, 7))
            return 0;
        break;
    case 5:
        if (!bow_kind(env) || !arrows(env, 1))
            return 0;
        break;
    case 6:
        if (!(kind(env, 0, 0xc) || kind(env, 0, 0xd) || kind(env, 1, 0xe)))
            return 0;
        break;
    case 7:
        if (!(kind(env, 1, 3) || kind(env, 0, 3)))
            return 0;
        break;
    case 8:
        if (!kind(env, 1, 0xf))
            return 0;
        break;
    case 9:
        if (!(kind(env, 1, 0x4e) || kind(env, 0, 0x4e)))
            return 0;
        break;
    case 10:
        if (!kind(env, 0, 0xd))
            return 0;
        break;
    case 11:
        if (!kind(env, 1, 0xe))
            return 0;
        break;
    case 12:
        if (!(kind(env, 0, 0x51) || kind(env, 1, 0x51)))
            return 0;
        break;
    case 13:
        if (!(kind(env, 0, 0x54) || kind(env, 1, 0x54)))
            return 0;
        break;
    case 14:
        if (!kind(env, 0, 0x5a))
            return 0;
        break;
    case 15: {
        int32_t m = env->part_model[0];
        if (!(m == 0x28f8 || m == 0x28f9 || m == 0x28fa || m == 0x2900))
            return 0;
        break;
    }
    case 16:
        if (env->part_model[1] != 0x28f7)
            return 0;
        break;
    case 17:
        if (!kind(env, 0, 0x73))
            return 0;
        break;
    case 18:
        if (!kind(env, 0, 0x7b))
            return 0;
        break;
    default:
        break;
    }
    if (ring_blocks(env))
        return 0;
    if (!mu_skill_world_ok(env, base))
        return 0;
    if (base == 0x3e && !buff(env, 1, 0xcf) && !buff(env, 1, 0x1ae))
        return 0;
    if (base == 0x7ef) {
        if (buff(env, 1, 0x199))
            return 0;
        if (mu_skill_chaos_castle(env->world))
            return 0;
    }
    if (base == 0x4d) {
        if (!((kind(env, 0, 8) && kind(env, 1, 0xa)) || (kind(env, 0, 8) && kind(env, 1, 0x4b)) ||
              (kind(env, 0, 9) && kind(env, 1, 0xb)) || (kind(env, 0, 9) && kind(env, 1, 0x4b))))
            return 0;
        if (buff(env, 1, 6) || buff(env, 1, 0x8f))
            return 0;
    }
    if (base == 0xe9 && (buff(env, 1, 0x52) || buff(env, 1, 0x8a) || buff(env, 1, 0x8b)))
        return 0;
    if (base == 0x7de && env->items[0].byte1a == 0)
        return 0;
    if (base == 0x7df && env->items[0].byte1a != 0)
        return 0;
    if (base == 0x82a) {
        if (!(env->confusion_world && env->confusion_world(env->user, env->world)))
            return 0;
        if (env->confusion_flag != 0)
            return 0;
#if MU_SKILL_MUTATION == 20
        if (!buff(env, 1, 0x1bb))
#else
        if (buff(env, 1, 0x1bb))       /* 0x01092042: JZ continues; the present buff blocks the skill */
#endif
            return 0;
    }
    if (!mu_skill_require_ok(env, hero, skill))
        return 0;
    if (base == 0x33b && env->party && !env->party(env->user))
        return 0;
    int ut = rs->use_type;
#if MU_SKILL_MUTATION == 19
    if (ut == 7 || ut == 8) {
#else
    if (ut == 7 || ut == 8 || ut == 9) {
#endif
        if (!(s && s->tree_learned ? s->tree_learned(s->user, skill) != 0 : 1))
            return 0;
    }
    if (skill == 0x127 || skill == 0x31a) {
        if (env->map_open && !env->map_open(env->user))
            return 0;
        if (mu_skill_illusion_temple(env->world) || env->world == 0x73)
            return 0;
    }
    return 1;
}
