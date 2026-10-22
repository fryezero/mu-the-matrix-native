/* The main HUD's experience bar (setExpData, 0x00c5125b) (NATIVE-PROGRESS-001).  See progress.h. */
#include <inttypes.h>
#include <string.h>

#include "progress_internal.h"

int32_t mu_prg_class_stage(uint8_t class_byte)
{
    int v = class_byte >> 4 & 0xf;
    if (v == 0)
        return 1;
    for (int i = 3; i >= 0; i--)
        if (v >> i & 1)
            return i + 2;
    return 1;
}

int mu_prg_exp_bar(const mu_prg_env *e, const mu_prg_bar_cache *cache, int32_t master_cap)
{
    const uint8_t *a = e->attr;
    mu_prg_bar_cache now;
    memset(&now, 0, sizeof now);
    int full = 0;
    now.stage = mu_prg_class_stage(e->hero_class);
    if (now.stage >= (MU_PROGRESS_MUTATION == 2 ? 4 : 3)) {
        now.exp = mu_prg_u64(a, MU_PRG_A_MEXP);
        now.next = mu_prg_u64(a, MU_PRG_A_MNEXT_EXP);
        if (mu_prg_master_level(a) >= master_cap)
            full = 1;
    } else {
        now.exp = mu_prg_u64(a, MU_PRG_A_EXP);
        now.next = mu_prg_u64(a, MU_PRG_A_NEXT_EXP);
    }
    if (cache && cache->stage == now.stage && cache->exp == now.exp && cache->next == now.next)
        return 0;
    /* __ltod3 0x0191c350: signed 64-bit -> double */
    double max = full ? 0.0 : (double)(int64_t)now.next;
    double cur = (int64_t)now.exp >= 0 ? (double)(int64_t)now.exp : 0.0;
    char json[512];
    if (!(0.0 < max)) {
        snprintf(json, sizeof json, "{\"ClassLevel\":%d,\"curExp\":\"0\",\"maxExp\":\"0\",\"page\":0,\"rate\":0}",
                 now.stage);
    } else {
        double seg = max / 10.0;
        int32_t page = mu_prg_cvtt(cur / seg);
        double rest = cur - (double)page * seg;
        int32_t rate = mu_prg_cvtt(rest / seg * (MU_PROGRESS_MUTATION == 3 ? 10.0 : 100.0));
        snprintf(json, sizeof json,
                 "{\"ClassLevel\":%d,\"curExp\":\"%" PRId64 "\",\"maxExp\":\"%" PRId64 "\",\"page\":%d,\"rate\":%d}",
                 now.stage, mu_prg_dtol(cur), mu_prg_dtol(max), page, rate);
    }
    mu_prg_emitf(e, "invoke setExpData %s", json);
    return 1;
}
