#ifndef MU_CLIENT_FRAME_H
#define MU_CLIENT_FRAME_H

/* Frame driver timing of the client, 0x01851d39 (CLIENT-FRAME-001 and
 * NATIVE-FRAME-001; docs/research/client-frame-loop.md). Authored names.
 *
 *   frame:  pending = accumulator
 *           while pending >= 40: logic step; ++logic_steps; pending -= 40
 *           [if the pause byte 0x06fc9cb4 is set: return, accumulator unchanged]
 *           previous = frame_tick; frame_tick = GetTickCount(); ++frames
 *           render, SwapBuffers
 *           elapsed = frame_tick - previous
 *           if elapsed < 40: Sleep(40 - elapsed); frame_tick += 40 - elapsed; elapsed = 40
 *           accumulator = pending + elapsed
 *
 * Because the slept time is added to frame_tick, elapsed measures the
 * previous frame's work plus the wait; logic runs at 25 Hz. */

#include <stdint.h>

#define MU_FRAME_STEP_MS 40

typedef struct mu_frame_clock {
    int32_t accumulator;    /* 0x0bdc5ec0 */
    uint32_t frame_tick;    /* 0x0bdc5e64 */
    uint32_t logic_steps;   /* 0x0bdc5eb0 */
    uint32_t frames;        /* 0x0bdc5ebc */
    int32_t pending;        /* frame-local accumulator ([ebp-0x34]) */
    uint32_t previous_tick; /* frame-local ([ebp-0xb8]) */
} mu_frame_clock;

/* Loads the accumulator into the frame-local counter. */
void mu_frame_begin(mu_frame_clock *clock);
/* 0x01851d6b: returns 1 and consumes 40 ms when another logic step is due. */
int mu_frame_logic_step(mu_frame_clock *clock);
/* 0x018524e7..0x01852507 with GetTickCount() = now. */
void mu_frame_render_start(mu_frame_clock *clock, uint32_t now);
/* 0x0185265a..0x018526a0 and the store at 0x018544aa: returns the Sleep
 * argument, or -1 when the client does not call Sleep (elapsed >= 40). */
int32_t mu_frame_finish(mu_frame_clock *clock);

#endif
