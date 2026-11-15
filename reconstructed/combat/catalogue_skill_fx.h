#ifndef MU_CATALOGUE_SKILL_FX_H
#define MU_CATALOGUE_SKILL_FX_H
#include "skill_fx.h"
/* RENDER-EFFECTS-035. Request side of class-tree skills outside the learned demo
 * set: the case bodies of the magic receive switch (0x01253f73), of the
 * position-skill receive switch (0x0125c9c3) and three end bodies, as ordered
 * presentation requests over authored CHARACTER/OBJECT views.
 *
 * Nothing here parses a receive record, decides eligibility or writes target
 * state. The caller supplies every service answer (hero identity, model, mount,
 * bone, presence, joint search). Consumers are separate: a request whose
 * consumer is missing stays a counted refusal in the native adapter. */
enum {
    MU_SKILL35_ACTION = 0x012b001a,        /* SkillAction(c, skill, action, alternative): type, subtype */
    MU_SKILL35_MAGIC_POSE = 0x013944d9,    /* SetPlayerMagic(c, skill) */
    MU_SKILL35_ATTACK_POSE = 0x01392bde,   /* SetPlayerAttack(c) */
    MU_SKILL35_KEY_LIST = 0x009fd745,      /* push_back(type) on the owner OBJECT's +0x1dc list */
    MU_SKILL35_ARROWS = 0x0158d5bd,        /* CreateArrows(c, o, 0, range, subtype, type) */
    MU_SKILL35_MAX_CALLS = 24
};
enum { MU_SKILL35_SOURCE = 0, MU_SKILL35_TARGET = 1, MU_SKILL35_NO_OWNER = -1 };
typedef struct mu_skill35_actor {
    int32_t owner;               /* the adapter's object handle for this OBJECT */
    uint16_t key, index;         /* CHARACTER +0x3e; client character-table index */
    int16_t class_word;          /* CHARACTER +0x146 */
    uint16_t height_word;        /* CHARACTER +0x158 */
    float position[3], angle[3], light[3];
} mu_skill35_actor;
typedef struct mu_skill35_input {
    int32_t skill, base;
    mu_skill35_actor source, target;
    uint8_t source_is_hero;      /* the source CHARACTER is the hero (pointer identity) */
    uint8_t model_present;       /* model getter 0x00eaa8cf answered a model */
    uint8_t mounted;             /* mount service 0x0106bdb7 on the target: not admitted when set */
    uint8_t presence_18, presence_2;   /* visual presence 0x12 on the source, 2 on the target */
    uint8_t joint_4, joint_9;    /* a live 0x472 joint of subtype 4 / 9 owned by the target */
    uint8_t flag_7;              /* source CHARACTER +7 */
    uint8_t attack_time, hero_attack_time;   /* CHARACTER +0x21 of the source and of the hero */
    uint16_t hero_key;           /* hero CHARACTER +0x3e */
    uint16_t source_key, target_key;   /* the receive record's two key words (frame -0x80, -0x40) */
    uint16_t packet_word;        /* position receive frame -0x28 */
    uint16_t target_word;        /* source CHARACTER +0x40 */
    float bone[3];               /* TransformByObjectBone answer */
} mu_skill35_input;
typedef struct mu_skill35_call {
    mu_sfx_call visual;
    uint32_t site;               /* sound provenance, zero otherwise */
    int32_t skill;               /* effect: second word; joint: fourth word after the key */
} mu_skill35_call;
typedef struct mu_skill35_plan {
    int32_t count;
    int32_t attack_time, hero_attack_time;   /* after the body */
    int32_t target_index;        /* target OBJECT +0x364 when written, else -1 */
    int32_t hero_byte;           /* hero data +0x2ded when written, else 0 */
    int32_t frame_reset;         /* source OBJECT +0xd0 = 0 */
    mu_skill35_call calls[MU_SKILL35_MAX_CALLS];
} mu_skill35_plan;
/* Group of an admitted row for this class byte: 1 A caster-frame, 2 B bone-frame
 * buff, 3 C triple storm, 4 D heal family, 5 E existing end body; 0 refused.
 * Only exact catalogue ids are accepted: no alias, no masked brand. */
int mu_skill35_select(int32_t skill, int32_t class_byte);
/* 1 when the row's visual is in the position-skill receive switch. */
int mu_skill35_position(int32_t skill);
/* An active learned entry within min(count, 150), as the original lookup caps it. */
int mu_skill35_learned(int32_t skill, const uint16_t *skills, int32_t count);
/* SkillAction's selection 0x012b0035..0x012b0087: the alternative is the mounted pose. */
int mu_skill35_action(int32_t action, int32_t alternative, int32_t mounted, int32_t flag_31e8);
/* The attack-step body of an admitted row (the default 0x0139b454). Returns the
 * AttackTime cutoff (15), or 0 for a refused row. */
int mu_skill35_step(int32_t skill, int32_t model, int32_t action, float frame, uint8_t *attack_time);
/* Phase 0: receive case body. Phase 1: end body (group E only). Returns 0 for a
 * refused row, phase or service context (mounted bone-frame rows). */
int mu_skill35_plan_cast(const mu_skill35_input *in, int phase, mu_skill35_plan *out);
#endif
