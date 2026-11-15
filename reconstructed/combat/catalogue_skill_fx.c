#include "catalogue_skill_fx.h"
#include "../record-math/record_math.h"
#include <string.h>

/* RENDER-EFFECTS-035: one table for the uniform groups. Each row is the case
 * body selected for that base skill; scripts/validate_render_effects35.py runs
 * the same body on the same authored records and compares every request. */
enum { GROUP_A = 1, GROUP_B, GROUP_C, GROUP_D, GROUP_E };
enum { DK = 1, ELF = 2, BOTH = 3 };
enum { GUARD_NONE, GUARD_NOT_HERO, GUARD_KEYS };
enum { POSE_NONE, POSE_ACTION, POSE_MAGIC, POSE_ATTACK };
enum { KEY_DEFAULT, KEY_SOURCE, KEY_TARGET, KEY_PACKET };
typedef struct row35 {
    uint16_t skill;
    uint8_t group, classes, position, guard, pose;
    uint16_t action;
    int16_t alternative;
    uint16_t effect, subtype;
    uint8_t key;
    uint16_t second;             /* C: the unowned pair; D: the target effect; A: arrows index */
    uint16_t sound;
    uint32_t site;
    uint8_t flags;
} row35;
enum {
    F_WHITE_BLUE = 1,            /* 740: light (0.7, 0.7, 1) instead of OBJECT Light */
    F_HERO_BYTE = 2,             /* 77: hero data +0x2ded = 10 */
    F_TIME = 4,                  /* 651: source AttackTime = 1 */
    F_SCALE_ONE = 8,             /* 2023: scale 1 */
    F_SKILL_WORD = 16,           /* 2047: the base skill as the effect's second word */
    F_BONE_TARGET = 32,          /* 1502: the bone is the target OBJECT's */
    F_INDEX = 64,                /* 1500, 1502: target OBJECT +0x364 = source index */
    F_ACTION_FIRST = 128         /* 1503, 2024: the pose precedes the effect */
};
static const row35 ROWS[] = {
    /* A caster-frame: magic receive */
    {740, GROUP_A, BOTH, 0, GUARD_KEYS, POSE_ACTION, 0x9a, 0x12c, 0x608, 0, KEY_DEFAULT, 0, 0, 0, F_WHITE_BLUE},
    {77, GROUP_A, ELF, 0, GUARD_NONE, POSE_NONE, 0, 0, 0x4b3, 0, KEY_DEFAULT, 0, 0x2e1, 0x01257627, F_HERO_BYTE},
    {652, GROUP_A, ELF, 0, GUARD_NONE, POSE_NONE, 0, 0, 0x4b3, 2, KEY_DEFAULT, 0, 0x2e1, 0x01259255, 0},
    {651, GROUP_A, ELF, 0, GUARD_NONE, POSE_NONE, 0, 0, 0, 0, KEY_DEFAULT, 0, 0, 0, F_TIME},
    {727, GROUP_A, ELF, 0, GUARD_NOT_HERO, POSE_ATTACK, 0, 0, 0x70e, 0, KEY_TARGET, 0, 0, 0, 0},
    /* A caster-frame: position-skill receive */
    {2023, GROUP_A, ELF, 1, GUARD_NONE, POSE_ACTION, 0x107, -1, 0x70a, 0, KEY_SOURCE, 0, 0, 0, F_SCALE_ONE},
    {2025, GROUP_A, ELF, 1, GUARD_NONE, POSE_MAGIC, 0, 0, 0x708, 0, KEY_PACKET, 0, 0x55f, 0x0125f899, 0},
    {2047, GROUP_A, ELF, 1, GUARD_NONE, POSE_MAGIC, 0, 0, 0x708, 0, KEY_PACKET, 0x7ff, 0x55f, 0x0125f806, F_SKILL_WORD},
    /* B bone-frame buff */
    {1500, GROUP_B, DK, 0, GUARD_NONE, POSE_ACTION, 0x9c, 0x11d, 0x69d, 1, KEY_DEFAULT, 0, 0, 0, F_INDEX},
    {1502, GROUP_B, DK, 0, GUARD_NONE, POSE_ACTION, 0x9c, 0x11d, 0x69c, 1, KEY_DEFAULT, 0, 0, 0, F_INDEX | F_BONE_TARGET},
    {1503, GROUP_B, DK, 0, GUARD_NONE, POSE_ACTION, 0x9c, 0x11d, 0x69e, 0, KEY_DEFAULT, 0, 0, 0, F_ACTION_FIRST},
    /* C triple storm */
    {1125, GROUP_C, BOTH, 0, GUARD_NONE, POSE_NONE, 0, 0, 0x635, 0, KEY_DEFAULT, 0x8263, 0, 0, 0},
    {1126, GROUP_C, BOTH, 0, GUARD_NONE, POSE_NONE, 0, 0, 0x636, 0, KEY_DEFAULT, 0x8264, 0, 0, 0},
    {1127, GROUP_C, BOTH, 0, GUARD_NONE, POSE_NONE, 0, 0, 0x637, 0, KEY_DEFAULT, 0x8265, 0, 0, 0},
    /* D heal family */
    {425, GROUP_D, ELF, 0, GUARD_NOT_HERO, POSE_ACTION, 0xd9, 0x125, 0x8021, 1, KEY_DEFAULT, 0x593, 0x334, 0x01258f59, 0},
    {430, GROUP_D, ELF, 0, GUARD_NOT_HERO, POSE_ACTION, 0xd9, 0x125, 0x8021, 3, KEY_DEFAULT, 0x594, 0x334, 0x01259193, 0},
    {2024, GROUP_D, ELF, 0, GUARD_NONE, POSE_ACTION, 0x106, -1, 0x8021, 3, KEY_DEFAULT, 0x594, 0x334, 0x0125c0d1, F_ACTION_FIRST},
    /* D, larger target part: 0x012552d1 (magic) and 0x0125ddd7 (position, sound 0x350) */
    {234, GROUP_D, ELF, 0, GUARD_NOT_HERO, POSE_ACTION, 0xd9, 0x125, 0x8021, 0, KEY_DEFAULT, 0, 0x350, 0x0125e243, 0},
    /* E existing end body: the buff start 0x0125594d, then an end body */
    {432, GROUP_E, ELF, 0, GUARD_NOT_HERO, POSE_MAGIC, 0, 0, 0x7f84, 3, KEY_DEFAULT, 0, 0x6f, 0x01255962, 0},
    {2026, GROUP_E, ELF, 0, GUARD_NOT_HERO, POSE_MAGIC, 0, 0, 0x7f84, 3, KEY_DEFAULT, 0, 0x6f, 0x01255962, 0},
    {2027, GROUP_E, ELF, 0, GUARD_NOT_HERO, POSE_MAGIC, 0, 0, 0x7f84, 2, KEY_DEFAULT, 0, 0x6f, 0x01255962, 0},
};

static const row35 *find(int32_t skill)
{
    for (size_t i = 0; i < sizeof ROWS / sizeof ROWS[0]; ++i)
        if (ROWS[i].skill == skill) return &ROWS[i];
    return NULL;
}

int mu_skill35_select(int32_t skill, int32_t class_byte)
{
    const row35 *r = find(skill);
    int cls = class_byte & 15;
    if (!r || (cls != DK && cls != ELF) || !(r->classes & cls)) return 0;
    return r->group;
}

int mu_skill35_position(int32_t skill)
{
    const row35 *r = find(skill);
    return r && r->position;
}

int mu_skill35_learned(int32_t skill, const uint16_t *skills, int32_t count)
{
    if (!find(skill)) return 0;
    for (int i = 0; skills && i < count && i < 150; ++i)
        if (skills[i] == skill) return 1;
    return 0;
}

int mu_skill35_action(int32_t action, int32_t alternative, int32_t mounted, int32_t flag_31e8)
{
    return mounted && !flag_31e8 && alternative != -1 ? alternative : action;
}

/* The default attack-step body 0x0139b454 that every admitted row selects. The
 * exceptional hero item 0x815 (its separate spark burst) is excluded by the
 * adapter's admission, as for the EFFECTS-032 default-step rows. */
int mu_skill35_step(int32_t skill, int32_t model, int32_t action, float frame, uint8_t *attack_time)
{
    if (!find(skill)) return 0;
    if (model == 0xa91 && action == 0x8f && frame >= 1.0f) *attack_time = 15;
    else if (frame >= 5.0f &&
        ((model == 0xa91 && action >= 0x6f && action < 0x133) ||
         (model >= 0x7a5 && model < 0x9fd && action >= 3 && action <= 4))) *attack_time = 15;
    return 15;   /* the cutoff written at 0x01396738 */
}

static mu_sfx_call *request(mu_skill35_plan *p, int routine, int type, int sub)
{
    mu_sfx_call *c = &p->calls[p->count++].visual;
    c->routine = routine; c->type = type; c->subtype = sub;
    c->owner = MU_SKILL35_NO_OWNER; c->range = -1; c->arg7 = -1;
    return c;
}
/* CreateEffect at an actor's own position, angle and light, with the default words. */
static mu_sfx_call *effect_at(mu_skill35_plan *p, int type, int sub, const mu_skill35_actor *a)
{
    mu_sfx_call *c = request(p, MU_SFX_CALL_EFFECT, type, sub);
    memcpy(c->position, a->position, sizeof c->position);
    memcpy(c->angle, a->angle, sizeof c->angle);
    memcpy(c->light, a->light, sizeof c->light);
    c->owner = a->owner;
    return c;
}
static void sound(mu_skill35_plan *p, const row35 *r)
{
    request(p, MU_SFX_CALL_SOUND, r->sound, 0);
    p->calls[p->count-1].site = r->site;
}
static void pose(mu_skill35_plan *p, const row35 *r)
{
    if (r->pose == POSE_ACTION) request(p, MU_SKILL35_ACTION, r->action, r->alternative);
    else if (r->pose == POSE_MAGIC) request(p, MU_SKILL35_MAGIC_POSE, 0, 0);
    else if (r->pose == POSE_ATTACK) request(p, MU_SKILL35_ATTACK_POSE, 0, 0);
}

static int guarded(const row35 *r, const mu_skill35_input *s)
{
    if (r->guard == GUARD_NOT_HERO) return s->source_is_hero;
    if (r->guard == GUARD_KEYS)   /* 0x012598ab: movsx of the hero key against the record's words */
        return (int32_t)(int16_t)s->hero_key == (int32_t)s->source_key || s->source_key == s->target_key;
    return 0;
}

static void group_a(const row35 *r, const mu_skill35_input *s, mu_skill35_plan *p)
{
    if (r->flags & F_TIME) p->attack_time = 1;                 /* 0x0125983f */
    if (guarded(r, s)) return;
    if (r->flags & F_HERO_BYTE) p->hero_byte = 10;             /* 0x012575bc */
    pose(p, r);
    if (r->key == KEY_TARGET) {                                /* 0x01255bba..0x01255bf5 */
        mu_sfx_call *c = request(p, MU_SKILL35_KEY_LIST, (int16_t)s->target.key, 0);
        c->owner = s->source.owner;
    }
    if (r->effect) {
        mu_sfx_call *c = effect_at(p, r->effect, r->subtype, &s->source);
        if (r->flags & F_WHITE_BLUE) { c->light[0] = c->light[1] = 0.7f; c->light[2] = 1.0f; }
        if (r->key == KEY_SOURCE) c->range = s->source.key;
        if (r->key == KEY_TARGET) c->range = s->target.key;
        if (r->key == KEY_PACKET) c->range = s->packet_word;
        if (r->flags & F_SCALE_ONE) c->scale = 1.0f;
        if (r->flags & F_SKILL_WORD) p->calls[p->count-1].skill = s->base;
    }
    if (r->sound) sound(p, r);
    if (r->second) {                                           /* 0x0125f80e: CreateArrows(c, o, 0, 0x7ff, 1, 0) */
        mu_sfx_call *c = request(p, MU_SKILL35_ARROWS, 0, 1);
        c->range = r->second; c->owner = s->source.owner;
    }
}

static int group_b(const row35 *r, const mu_skill35_input *s, mu_skill35_plan *p)
{
    if (!s->model_present) return 1;                           /* the body leaves without a request */
    if (r->flags & F_INDEX) p->target_index = s->source.index;
    mu_sfx_call *c = request(p, MU_SFX_CALL_BONE, 0, 0);
    c->range = 0x11;
    c->owner = r->flags & F_BONE_TARGET ? s->target.owner : s->source.owner;
    if (s->mounted) return 0;                                  /* the mount position service is not admitted */
    if (r->flags & F_ACTION_FIRST) pose(p, r);
    c = effect_at(p, r->effect, r->subtype, &s->target);
    memcpy(c->position, s->bone, sizeof c->position);
    if (!(r->flags & F_ACTION_FIRST)) pose(p, r);
    return 1;
}

static void group_c(const row35 *r, const mu_skill35_input *s, mu_skill35_plan *p)
{
    effect_at(p, r->effect, r->subtype, &s->target);
    for (int n = 0; n < 2; ++n) {
        mu_sfx_call *c = effect_at(p, r->second, 0, &s->target);
        c->position[2] = ((float)s->target.height_word + 30.0f) + s->target.position[2];
        c->light[0] = c->light[1] = c->light[2] = 1.0f;
        c->owner = MU_SKILL35_NO_OWNER;
    }
}

/* Recovery's target part, 0x01255497..0x012558fa and 0x0125ddd7..0x0125e238: nineteen
 * joints and four ground effects at the actor, then two effects at random bones.
 * The body returns early when the actor's model is missing. */
static void recovery_part(const mu_skill35_input *s, mu_skill35_plan *p, const mu_skill35_actor *a)
{
    for (int n = 0; n < 19; ++n) {
        mu_sfx_call *c = request(p, MU_SFX_CALL_JOINT, 0x7f78, 0x2f);
        memcpy(c->position, a->position, sizeof c->position);
        memcpy(c->target, a->position, sizeof c->target);
        memcpy(c->angle, a->angle, sizeof c->angle);
        c->owner = a->owner; c->scale = 40.0f; c->arg7 = 2; c->arg8 = 0;
        p->calls[p->count-1].skill = -1;
    }
    static const struct { uint16_t type, subtype; } ground[4] = {{0x4bd, 0}, {0x809e, 0}, {0x809e, 1}, {0x809e, 2}};
    for (int n = 0; n < 4 + 2; ++n) {
        if (n >= 4) {
            if (!s->model_present) return;
            if (s->bone_count <= 0) continue;
            request(p, MU_SKILL35_RAND, 0, 0);
            mu_sfx_call *bone = request(p, MU_SFX_CALL_BONE, 0, 0);
            bone->range = s->random[n-4] % s->bone_count; bone->owner = a->owner;
        }
        mu_sfx_call *c = effect_at(p, n < 4 ? ground[n].type : 0x7f78, n < 4 ? ground[n].subtype : 3, a);
        if (n >= 4) memcpy(c->position, s->bones[n-4], sizeof c->position);
        c->light[0] = 0.3f; c->light[1] = 0.2f; c->light[2] = 0.1f;
        c->owner = MU_SKILL35_NO_OWNER;
    }
}

static void group_d(const row35 *r, const mu_skill35_input *s, mu_skill35_plan *p)
{
    if (r->flags & F_ACTION_FIRST) pose(p, r);                 /* 0x0125bf1c */
    if (!guarded(r, s)) {
        static const float hand[3] = {0.0f, -220.0f, 130.0f};
        float matrix[12], offset[3];
        mu_angle_matrix(s->source.angle, matrix);
        mu_vector_rotate(hand, matrix, offset);
        mu_sfx_call *c = effect_at(p, r->effect, r->subtype, &s->source);
        for (int k = 0; k < 3; ++k) c->position[k] = offset[k] + s->source.position[k];
        c->light[0] = r->subtype == 1 ? 0.2f : 1.0f;
        c->light[1] = r->subtype == 1 ? 1.0f : 0.92f;
        c->light[2] = 0.4f;
        if (r->skill == 234) { c->light[0] = 0.7f; c->light[1] = 0.6f; c->light[2] = 0.0f; }
        if (!(r->flags & F_ACTION_FIRST)) {
            pose(p, r);
            p->attack_time = 1;
            if (r->skill != 234) p->hero_attack_time = 1;      /* 0x01258f3a..0x01258f46 */
        }
    }
    if (r->skill == 234) { recovery_part(s, p, &s->target); return; }
    sound(p, r);
    effect_at(p, r->second, 0, r->flags & F_ACTION_FIRST ? &s->source : &s->target);
}

static void group_e_start(const row35 *r, const mu_skill35_input *s, mu_skill35_plan *p)
{
    if (s->source.class_word != 0x4d) sound(p, r);             /* 0x0125594d */
    if (!guarded(r, s)) { pose(p, r); p->frame_reset = 1; }
    p->attack_time = 1;
}

static void group_e_end(const row35 *r, const mu_skill35_input *s, mu_skill35_plan *p)
{
    if (r->skill == 432) { effect_at(p, r->effect, r->subtype, &s->source); return; }   /* 0x013a9449 */
    if (r->skill == 2027 && !s->flag_7) return;                /* 0x013b16c1 */
    if (s->presence_18) return;
    effect_at(p, r->effect, r->subtype, &s->target);
    if (r->skill != 2027 || (s->presence_2 && (s->joint_4 || s->joint_9))) return;
    for (int n = 0; n < 5; ++n) {                              /* 0x013b177c / 0x013b183d */
        mu_sfx_call *c = request(p, MU_SFX_CALL_JOINT, 0x472, 4);
        memcpy(c->position, s->target.position, sizeof c->position);
        memcpy(c->target, s->target.position, sizeof c->target);
        memcpy(c->angle, s->target.angle, sizeof c->angle);
        c->owner = s->target.owner; c->scale = 20.0f; c->arg7 = -1; c->arg8 = 0;
        p->calls[p->count-1].skill = (int16_t)s->target_word;
    }
}

int mu_skill35_plan_cast(const mu_skill35_input *s, int phase, mu_skill35_plan *p)
{
    memset(p, 0, sizeof *p);
    p->attack_time = s->attack_time; p->hero_attack_time = s->hero_attack_time;
    p->target_index = -1;
    const row35 *r = find(s->skill);
    if (!r || s->base != s->skill || phase < 0 || phase > 2) return 0;
    if (phase == 2) {                                          /* 0x0125ddd7 */
        if (r->skill != 234) return 0;
        recovery_part(s, p, &s->source);
        if (s->model_present) sound(p, r);
        return 1;
    }
    if (phase == 1) {
        if (r->group != GROUP_E) return 0;
        group_e_end(r, s, p);
        return 1;
    }
    switch (r->group) {
    case GROUP_A: group_a(r, s, p); break;
    case GROUP_B:
        if (!group_b(r, s, p)) { memset(p, 0, sizeof *p); return 0; }
        break;
    case GROUP_C: group_c(r, s, p); break;
    case GROUP_D: group_d(r, s, p); break;
    default: group_e_start(r, s, p); break;
    }
    if (s->source_is_hero) p->hero_attack_time = p->attack_time;   /* one CHARACTER */
    return 1;
}

/* The cast end bodies of the learned buffs 27 (0x013afb06) and 28 (0x013afcea).
 * They are the bodies of 2027 and 2026 again, at other addresses: the presence
 * tests, the ground effect on the target and, for 27, the five 0x472/4 joints. */
int mu_skill35_buff_end(const mu_skill35_input *s, mu_skill35_plan *p)
{
    memset(p, 0, sizeof *p);
    p->attack_time = s->attack_time; p->hero_attack_time = s->hero_attack_time;
    p->target_index = -1;
    if (s->base != s->skill || (s->skill != 27 && s->skill != 28)) return 0;
    group_e_end(find(s->skill == 27 ? 2027 : 2026), s, p);
    return 1;
}
