#include "item_actions.h"
#include <stddef.h>

#ifndef MU_MIX_MUTANT
#define MU_MIX_MUTANT 0
#endif
static int compound(uint8_t k) {
    return k == 0x2d || k == 0x2e || k == 0x2f || k == 0x30 || k == 0x31 || k == 0x38;
}
static int common_kind(uint8_t k) {
    return k == 1 || k == 3 || k == 6 || k == 0xf || k == 0xe || k == 0x12 || k == 0x1b || k == 0x21;
}
static int blocked(const mu_jewel_target *s) {
    return s->period == 1 || s->type == 4 || s->kind_a == 0x1a || s->kind_b == 0x2c ||
           s->kind_a == 0x22 || compound(s->kind_a);
}
int mu_jewel_allowed(int32_t jewel, const mu_jewel_target *s, int mix_visible) {
    if (!s || s->type == 5) return 0;
    int valid = s->code >= 0 && s->code <= 0x2c00;
    int kind = valid && (common_kind(s->kind_a) || s->kind_a == 0x19 ||
               (s->kind_a == 0x37 && s->kind_b != 0xa && s->kind_b != 0xb));
    int limit = jewel == 0x1c0d ? 5 : 8;
    if (MU_MIX_MUTANT == 1) ++limit;
    if ((jewel == 0x1c0d || jewel == 0x1c0e) && s->level >= 0 && s->level <= limit && !mix_visible) {
        if (jewel == 0x1c0d && (s->code == 0x29 || (s->code == 0x1b0c && s->durability > 0 && s->durability < 255)))
            kind = 1;
        return kind && !blocked(s);
    }
    if (jewel == 0x1c10 && s->option >= 0 && s->option < 4) {
        /* Preserve the client's direct branches for the first eight kinds. */
        if (valid && common_kind(s->kind_a)) return s->period == 0;
        return valid && s->kind_a == 0x37 && s->kind_b != 0xa && s->kind_b != 0xb &&
               !blocked(s) && s->kind_a != 0x19 && s->period == 0;
    }
    return 0;
}
void mu_jewel_request(uint8_t out[6], uint8_t source, uint8_t target, uint8_t mode) {
    out[0] = 0xc1; out[1] = 6; out[2] = MU_MIX_MUTANT==10 ? 0x32 : 0x31;
    out[3] = source; out[4] = target; out[5] = mode;
}
