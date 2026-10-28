/* Frame-time breakdown (NATIVE-PERF-001). See mu_perf.h. */
#define _POSIX_C_SOURCE 200809L
#ifdef __APPLE__
#define _DARWIN_C_SOURCE 1
#endif
#include "mu_perf.h"

#ifdef __APPLE__
#include <mach/mach.h>
#include <mach/mach_time.h>
#include <mach/thread_policy.h>
#endif

#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static const char *const names[MU_PERF_PHASES] = {
    "events", "logic", "terrain", "objects", "characters", "items", "env", "particles",
    "effects", "labels", "scene", "gfx", "overlay", "present", "swap", "sleep",
};

static struct {
    FILE *log;
    int sync;
    void (*finish)(void);
    double phase[MU_PERF_PHASES];
    double last, cpu_last, gpu_ms;
    int64_t gpu_frame;
    int64_t frame;
} P;

double mu_perf_now(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec * 1000.0 + (double)t.tv_nsec / 1.0e6;
}

static double cpu_now(void)
{
    struct timespec t;
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t);
    return (double)t.tv_sec * 1000.0 + (double)t.tv_nsec / 1.0e6;
}

void mu_perf_gpu_sample(double ms, int64_t frame) { P.gpu_ms = ms; P.gpu_frame = frame; }
int64_t mu_perf_frame_index(void) { return P.frame; }

int mu_perf_open(const char *path, int sync)
{
    mu_perf_close();
    if (!path || !path[0])
        return 0;
    P.log = fopen(path, "w");
    if (!P.log)
        return 1;
    P.sync = sync;
    fprintf(P.log, "frame\tscene\ttotal_ms");
    for (int i = 0; i < MU_PERF_PHASES; ++i)
        fprintf(P.log, "\t%s_ms", names[i]);
    fprintf(P.log, "\tcpu_ms\tgpu_world_ms\tgpu_frame\n");
    P.cpu_last = cpu_now();
    P.gpu_ms = -1.0;
    P.gpu_frame = -1;
    memset(P.phase, 0, sizeof P.phase);
    P.last = mu_perf_now();
    P.frame = 0;
    return 0;
}

void mu_perf_close(void)
{
    if (P.log)
        fclose(P.log);
    P.log = NULL;
}

int mu_perf_enabled(void) { return P.log != NULL; }

void mu_perf_set_sync(void (*finish)(void)) { P.finish = finish; }

double mu_perf_begin(void)
{
    if (!P.log)
        return 0.0;
    if (P.sync && P.finish)
        P.finish();
    return mu_perf_now();
}

void mu_perf_end(int phase, double stamp)
{
    if (!P.log || phase < 0 || phase >= MU_PERF_PHASES)
        return;
    if (P.sync && P.finish)
        P.finish();
    P.phase[phase] += mu_perf_now() - stamp;
}

void mu_perf_add(int phase, double ms)
{
    if (P.log && phase >= 0 && phase < MU_PERF_PHASES)
        P.phase[phase] += ms;
}

void mu_perf_frame(int32_t scene)
{
    if (!P.log)
        return;
    double now = mu_perf_now(), cpu = cpu_now();
    fprintf(P.log, "%lld\t%d\t%.3f", (long long)P.frame, scene, now - P.last);
    for (int i = 0; i < MU_PERF_PHASES; ++i)
        fprintf(P.log, "\t%.3f", P.phase[i]);
    fprintf(P.log, "\t%.3f\t%.3f\t%lld\n", cpu - P.cpu_last, P.gpu_ms, (long long)P.gpu_frame);
    P.cpu_last = cpu;
    P.gpu_ms = -1.0;
    P.gpu_frame = -1;
    memset(P.phase, 0, sizeof P.phase);
    P.last = now;
    ++P.frame;
}

static void nap(double ms)
{
    struct timespec t;
    t.tv_sec = (time_t)(ms / 1000.0);
    t.tv_nsec = (long)((ms - (double)t.tv_sec * 1000.0) * 1.0e6);
    nanosleep(&t, NULL);
}

#ifdef __APPLE__
/* macOS coalesces the timers of ordinary threads: a 27.5 ms nanosleep woke
 * 1 to 10 ms late (measured on the M5, more when the window is in the
 * background).  For the sleep only, the thread takes the time-constraint
 * (real-time) policy, which wakes it within 0.02 ms, and returns to the
 * standard policy before any game work runs. */
static void precise(int on)
{
    if (on) {
        mach_timebase_info_data_t tb;
        mach_timebase_info(&tb);
        const double ms = 1.0e6 * (double)tb.denom / (double)tb.numer;
        thread_time_constraint_policy_data_t p;
        p.period = 0;
        p.computation = (uint32_t)(1.0 * ms);
        p.constraint = (uint32_t)(2.0 * ms);
        p.preemptible = 1;
        thread_policy_set(mach_thread_self(), THREAD_TIME_CONSTRAINT_POLICY, (thread_policy_t)&p,
                          THREAD_TIME_CONSTRAINT_POLICY_COUNT);
    } else {
        thread_standard_policy_data_t p;
        thread_policy_set(mach_thread_self(), THREAD_STANDARD_POLICY, (thread_policy_t)&p,
                          THREAD_STANDARD_POLICY_COUNT);
    }
}
#else
static void precise(int on) { (void)on; }
#endif

int mu_perf_baseline(void)
{
    const char *v = getenv("MU_PERF_BASELINE");
    return v && v[0] == '1';
}

int mu_perf_batching(void)
{
    const char *v = getenv("MU_NO_GL_BATCH");
    return !(v && v[0] == '1') && !mu_perf_baseline();
}

void mu_sleep_ms(uint32_t ms)
{
    if (!ms)
        return;
    if (mu_perf_baseline()) {   /* SDL_Delay's nanosleep */
        nap((double)ms);
        return;
    }
    const double deadline = mu_perf_now() + (double)ms;
    double left;
    precise(1);
    while ((left = deadline - mu_perf_now()) > 0.3)
        nap(left - 0.2);
    while (deadline - mu_perf_now() > 0.0)
        sched_yield();
    precise(0);
}
