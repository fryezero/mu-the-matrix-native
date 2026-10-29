#ifndef MU_FRAME_TIME_H
#define MU_FRAME_TIME_H
/* RENDER-WORLDS-AFTER: the client's per-frame timing 0x012aeb2b up to its scene call 0x012aec9f
 * (docs/research/client-worlds-after.md). Frame time [0x01cf103c] = (int)(now - prior) / 1000 s, or
 * 0x38d1b718 (about 0.0001) when timeGetTime did not advance; the image initialises it to 0.1 before the first frame.
 *
 * The native consumers (effects, particles, object visuals and moves) read mu_frame_time_value(). It stays
 * 0.1 unless a caller ticks the clock: only the interactive viewer loop does (mu_frame_time_tick), so the
 * deterministic fidelity tour and the headless tools keep the earlier 0.1 and their hashes. */
#include <stdint.h>
typedef uint32_t (*mu_time_get_fn)(void *context);   /* timeGetTime, 0x01a7c9a4 */
typedef struct mu_frame_time {
    uint8_t started;        /* 0x06fce378 */
    uint32_t base;          /* 0x06fce37c: start of the FPS window */
    uint32_t next_base;     /* 0x06fce380 */
    uint32_t now;           /* 0x06fce384 */
    uint32_t prior;         /* 0x06fce388 */
    int32_t frames;         /* 0x06fce38c: frames in the FPS window */
    int32_t next_frames;    /* 0x06fce390 */
    float fps;              /* 0x06fce36c (-1 while the window is empty) */
    float world_time;       /* 0x06fce370 = (float)(double)timeGetTime() */
    float frame_time;       /* 0x01cf103c */
    int32_t delta;          /* [ebp-8] = now - prior, the skill tick's argument */
} mu_frame_time;
void mu_frame_time_init(mu_frame_time *t);   /* the image's state: zeros, frame time 0.1 */
void mu_frame_time_update(mu_frame_time *t, mu_time_get_fn get, void *context);
/* Process-wide value for the native consumers (0.1 until ticked). */
float mu_frame_time_value(void);
void mu_frame_time_tick(uint32_t now_ms);
void mu_frame_time_reset(void);
#endif
