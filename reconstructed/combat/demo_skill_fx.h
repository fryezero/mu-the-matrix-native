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
    uint16_t target_key;
    float frame, prior_frame, position[3], angle[3], light[3];
} mu_skill30_input;
typedef struct mu_skill30_call {
    mu_sfx_call visual;
    uint32_t site;             /* sound provenance, zero for other calls */
} mu_skill30_call;
typedef struct mu_skill30_plan {
    int32_t count, limit, target_key;
    mu_skill30_call calls[MU_SKILL30_MAX_CALLS];
} mu_skill30_plan;
/* Phase 0: attack-step helper; phase 1: selected end-of-attack body.
 * Only modeled visual writes are applied to input. No target state is written. */
int mu_skill30_select(int32_t skill, int32_t base);
int mu_skill30_plan_cast(mu_skill30_input *in, int end, mu_skill30_plan *out);
#endif
