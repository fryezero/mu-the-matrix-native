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

void mu_perf_gpu_sample(mu_perf *p, double ms, int64_t frame) { if (!p) return; p->gpu_ms = ms; p->gpu_frame = frame; }
void mu_perf_gpu_gfx_sample(mu_perf *p, double ms, int64_t frame) { if (!p) return; p->gpu_gfx_ms = ms; p->gpu_gfx_frame = frame; }
int64_t mu_perf_frame_index(mu_perf *p) { return p ? p->frame : 0; }

int mu_perf_open(mu_perf *p, const char *path, int sync)
{
    mu_perf_close(p);
    if (!path || !path[0])
        return 0;
    p->log = fopen(path, "w");
    if (!p || !p->log)
        return 1;
    p->sync = sync;
    fprintf(p->log, "frame\tscene\ttotal_ms");
    for (int i = 0; i < MU_PERF_PHASES; ++i)
        fprintf(p->log, "\t%s_ms", names[i]);
    fprintf(p->log, "\tcpu_ms\tgpu_world_ms\tgpu_frame\tgpu_gfx_ms\tgpu_gfx_frame\n");
    p->cpu_last = cpu_now();
    p->gpu_ms = -1.0;
    p->gpu_frame = -1;
    p->gpu_gfx_ms = -1.0;
    p->gpu_gfx_frame = -1;
    memset(p->phase, 0, sizeof p->phase);
    p->last = mu_perf_now();
    p->frame = 0;
    return 0;
}

void mu_perf_close(mu_perf *p)
{
    if (p && p->log)
        fclose(p->log);
    if (p) memset(p, 0, sizeof *p);
}

int mu_perf_enabled(mu_perf *p) { return p && p->log != NULL; }

void mu_perf_set_sync(mu_perf *p, void (*finish)(void)) { if (p) p->finish = finish; }

double mu_perf_begin(mu_perf *p)
{
    if (!p || !p->log)
        return 0.0;
    if (p->sync && p->finish)
        p->finish();
    return mu_perf_now();
}

void mu_perf_end(mu_perf *p, int phase, double stamp)
{
    if (!p || !p->log || phase < 0 || phase >= MU_PERF_PHASES)
        return;
    if (p->sync && p->finish)
        p->finish();
    p->phase[phase] += mu_perf_now() - stamp;
}

void mu_perf_add(mu_perf *p, int phase, double ms)
{
    if (p && p->log && phase >= 0 && phase < MU_PERF_PHASES)
        p->phase[phase] += ms;
}

void mu_perf_frame(mu_perf *p, int32_t scene)
{
    if (!p || !p->log)
        return;
    double now = mu_perf_now(), cpu = cpu_now();
    fprintf(p->log, "%lld\t%d\t%.3f", (long long)p->frame, scene, now - p->last);
    for (int i = 0; i < MU_PERF_PHASES; ++i)
        fprintf(p->log, "\t%.3f", p->phase[i]);
    fprintf(p->log, "\t%.3f\t%.3f\t%lld\t%.3f\t%lld\n", cpu - p->cpu_last, p->gpu_ms, (long long)p->gpu_frame, p->gpu_gfx_ms, (long long)p->gpu_gfx_frame);
    p->cpu_last = cpu;
    p->gpu_ms = -1.0;
    p->gpu_frame = -1;
    p->gpu_gfx_ms = -1.0;
    p->gpu_gfx_frame = -1;
    memset(p->phase, 0, sizeof p->phase);
    p->last = now;
    ++p->frame;
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
        thread_t thread = mach_thread_self();
        thread_policy_set(thread, THREAD_TIME_CONSTRAINT_POLICY, (thread_policy_t)&p,
                          THREAD_TIME_CONSTRAINT_POLICY_COUNT);
        mach_port_deallocate(mach_task_self(), thread);
    } else {
        thread_standard_policy_data_t p;
        thread_t thread = mach_thread_self();
        thread_policy_set(thread, THREAD_STANDARD_POLICY, (thread_policy_t)&p,
                          THREAD_STANDARD_POLICY_COUNT);
        mach_port_deallocate(mach_task_self(), thread);
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

static void sleep_until(double deadline)
{
    double left;
    if (deadline <= mu_perf_now()) return;
    precise(1);
    while ((left = deadline - mu_perf_now()) > 0.3)
        nap(left - 0.2);
    while (deadline - mu_perf_now() > 0.0)
        sched_yield();
    precise(0);
}

void mu_perf_pace_begin(mu_perf *p) { p->pace_start = mu_perf_now(); }
void mu_perf_pace_end(mu_perf *p, int32_t client_sleep)
{
    const char *baseline = getenv("MU_PERF_003_BASELINE");
    if (mu_perf_baseline() || (baseline && baseline[0] == '1')) {
        if (client_sleep > 0) mu_sleep_ms((uint32_t)client_sleep);
        return;
    }
    sleep_until(p->pace_start + 40.0);
}

void mu_sleep_ms(uint32_t ms)
{
    if (!ms)
        return;
    if (mu_perf_baseline()) {   /* SDL_Delay's nanosleep */
        nap((double)ms);
        return;
    }
    sleep_until(mu_perf_now() + (double)ms);
}
