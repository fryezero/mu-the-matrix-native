/* behaviors/progress.c (sketch): core/mu_progress.c's demo queue, now answering real requests. */
#include "../behavior.h"

typedef struct fx_progress { int32_t exp_rate, latency; /* pending answers with due steps */ } fx_progress;

static int progress_on_request(void *self, mu_fixture_ctx *ctx, const mu_fixture_request *rq)
{
    /* TODO
     *   the stat request (the bytes mu_prg_stat_request produced, after the server-side XorData decode):
     *       queue A0 11 {accepted | stat, new maxima} at now + latency
     *   a kill notification from the combat behavior (fixture-internal call, not a frame):
     *       queue 0x16 as C3 (encrypted: the client refuses a plaintext 0x16 and sends 4D 02 00 16)
     *       and A0 06 when the level threshold (mu_prg_exp_table, the client's own table) is crossed
     */
    (void)self; (void)ctx; (void)rq;
    return 0;
}

const mu_fixture_behavior mu_fx_progress = {
    .name = "progress",
    .on_request = progress_on_request,
};
