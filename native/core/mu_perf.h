#ifndef MU_PERF_H
#define MU_PERF_H

/* Frame-time breakdown for the native front ends (NATIVE-PERF-001).
 *
 * Native measurement only: it times the host's own phases (logic, the 3D
 * passes, the GFx layer, presentation) and never changes what is computed or
 * drawn.  Off by default: every call is a cheap test of one global until a
 * front end opens a log (mu-client/mu-world --perf FILE).  With `sync`, each
 * phase end first waits for the GPU (the front end's glFinish hook), so a
 * phase's time includes the GPU work it queued (diagnostic mode: it costs
 * frame time itself).
 *
 * Log: one tab-separated line per frame, a header line first:
 *   frame scene total_ms <phase>_ms ...
 * native/tools/perf_report.py turns logs into percentiles. */

#include <stdint.h>

enum {
    MU_PERF_EVENTS,      /* event pump, input */
    MU_PERF_LOGIC,       /* scene logic: due logic steps, camera, terrain frame, effects update */
    MU_PERF_TERRAIN,     /* RenderTerrain */
    MU_PERF_OBJECTS,     /* RenderObjects */
    MU_PERF_CHARACTERS,  /* hero and actors (with shadows) */
    MU_PERF_ITEMS,       /* ground items */
    MU_PERF_ENV,         /* ambient creatures */
    MU_PERF_PARTICLES,   /* particles, sprites, joints, effect models */
    MU_PERF_EFFECTS,     /* actor effects, combat */
    MU_PERF_LABELS,      /* item labels, stand-in names */
    MU_PERF_SCENE,       /* character-select / login 3D scene (single phase) */
    MU_PERF_GFX,         /* the GFx interface (movies, compositing) */
    MU_PERF_OVERLAY,     /* the 2D layer: read back, software overlay */
    MU_PERF_PRESENT,     /* screen upload / overlay draw */
    MU_PERF_SWAP,        /* SwapWindow */
    MU_PERF_SLEEP,       /* the client's frame cap */
    MU_PERF_PHASES
};

/* Opens the log (NULL or "" leaves profiling off).  Returns 0 on success. */
int mu_perf_open(const char *path, int sync);
void mu_perf_close(void);
int mu_perf_enabled(void);
/* The front end's GPU wait for sync mode (glFinish). */
void mu_perf_set_sync(void (*finish)(void));

double mu_perf_now(void);   /* milliseconds, monotonic */
/* Phase timing: mu_perf_begin returns a stamp (0 when off), mu_perf_end adds
 * the elapsed time to the phase. */
double mu_perf_begin(void);
void mu_perf_end(int phase, double stamp);
void mu_perf_add(int phase, double ms);
/* Ends a frame: writes its line (total = time since the previous frame end). */
void mu_perf_frame(int32_t scene);
/* Diagnostic CPU thread time and asynchronous world GL timer queries. GPU results
 * carry their source frame; -1 means unavailable. Ruffle/Metal is outside this query. */
void mu_perf_gpu_sample(double ms, int64_t frame);
/* Separate, non-overlapping GL query around the complete GFx compositor/item pass. */
void mu_perf_gpu_gfx_sample(double ms, int64_t frame);
int64_t mu_perf_frame_index(void);

/* The host's Sleep(ms) for the client's frame cap: wakes at the requested
 * time (a coarse sleep, then short sleeps and a final spin under 0.2 ms)
 * instead of SDL_Delay's oversleep of one to two milliseconds on macOS,
 * which turned the login/title cap Sleep(40 - elapsed) into 23.9 fps. */
void mu_sleep_ms(uint32_t ms);
/* Host window pacing. Measure this frame's work against a 40 ms deadline;
 * the reconstructed integer clock and headless simulation stay untouched. */
void mu_perf_pace_begin(void);
void mu_perf_pace_end(int32_t client_sleep);

/* MU_PERF_BASELINE=1: the paths before NATIVE-PERF-001, for before/after measurements on any machine:
 * plain sleeps at the cap, the software 2D layer over a read-back frame, immediate-mode draws. */
int mu_perf_baseline(void);
/* The draw batching is on (off with MU_NO_GL_BATCH=1 or the baseline). */
int mu_perf_batching(void);

#endif
