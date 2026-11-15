#ifndef MU_DEMO_SKILL_FX_H
#define MU_DEMO_SKILL_FX_H
#include "skill_fx.h"
/* RENDER-EFFECTS-030. Explicit visual selectors, not class/power state.
 * The caller supplies the original base-selector result and learned-list index.
 * Only individually audited selector pairs are accepted. */
enum { MU_SKILL30_ARROW = 0x0158d5bd, MU_SKILL30_MAX_CALLS = 40 };
typedef struct mu_skill30_input {
    int32_t skill, base, learned_index, owner, model, action;
    uint8_t attack_time, tile[2];
    uint16_t target_index; /* CHARACTER +0x40: client character-table index */
    float frame, prior_frame, position[3], angle[3], light[3];
} mu_skill30_input;
typedef struct mu_skill30_call {
    mu_sfx_call visual;
    uint32_t site;             /* sound provenance, zero for other calls */
} mu_skill30_call;
typedef struct mu_skill30_plan {
    int32_t count, limit, target_index;
    mu_skill30_call calls[MU_SKILL30_MAX_CALLS];
} mu_skill30_plan;
/* Phase 0: attack-step helper; phase 1: selected end-of-attack body.
 * Only modeled visual writes are applied to input. No target state is written. */
int mu_skill30_select(int32_t skill, int32_t base);
int mu_skill30_plan_cast(mu_skill30_input *in, int end, mu_skill30_plan *out);
/* RENDER-EFFECTS-032. Authored presentation services, never item eligibility. */
typedef struct mu_skill32_context {
    int32_t bow_kind, wing, shield, mount;
} mu_skill32_context;
typedef struct mu_skill32_input {
    mu_skill30_input cast;
    uint16_t object_key, skill_word;
    int32_t random[6]; /* ordered CRT values for Crescent Moon Slash */
} mu_skill32_input;
typedef struct mu_skill32_call {
    mu_skill30_call call;
    int32_t skill; /* second CreateEffect word, distinct from key/default word8 */
} mu_skill32_call;
typedef struct mu_skill32_plan {
    int32_t count, limit, random_used;
    mu_skill32_call calls[10];
} mu_skill32_plan;
int mu_skill32_select(int32_t skill, int32_t base);
int mu_skill32_learned(int32_t skill, const uint16_t *skills, int32_t count);
/* -1 means no admitted pose. The bow-kind service and wing word are explicit. */
int mu_skill32_action(int32_t skill, int32_t class_byte, const mu_skill32_context *context);
/* Phase 0 is step, 1 is end, 2 is the bounded start sound. */
int mu_skill32_plan_cast(mu_skill32_input *in, int end, mu_skill32_plan *out);
#endif
