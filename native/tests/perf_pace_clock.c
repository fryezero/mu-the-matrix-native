/* Deterministic host clock for mu_perf.c's window pacer. No renderer or
 * reconstructed clock is replaced in the application. */
#include <sched.h>
#include <time.h>
static double stamp;
void pace_test_clock(double ms) { stamp = ms; }
int fake_clock_gettime(clockid_t clock, struct timespec *out)
{
    (void)clock;
    stamp += 0.001;
    out->tv_sec = (time_t)(stamp / 1000.0);
    out->tv_nsec = (long)((stamp - (double)out->tv_sec * 1000.0) * 1e6);
    return 0;
}
int fake_nanosleep(const struct timespec *delay, struct timespec *remaining)
{
    (void)remaining;
    stamp += (double)delay->tv_sec * 1000.0 + (double)delay->tv_nsec / 1e6;
    return 0;
}
int fake_sched_yield(void) { stamp += 0.01; return 0; }

#include "../core/mu_perf.h"
static mu_perf test_perf;
void pace_test_begin(void) { mu_perf_pace_begin(&test_perf); }
void pace_test_end(int32_t sleep) { mu_perf_pace_end(&test_perf, sleep); }
