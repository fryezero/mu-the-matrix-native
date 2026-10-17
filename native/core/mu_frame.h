#ifndef MU_FRAME_H
#define MU_FRAME_H

/* Native frame-loop skeleton (NATIVE-FRAME-001).
 *
 * Wires the reconstructed client pieces (reconstructed/camera) into a
 * platform-neutral loop:
 *   - fixed 40 ms logic steps and the 40 ms frame cap of the frame driver
 *     0x01851d39 (client_frame);
 *   - the client's in-world camera (MoveMainCamera 0x0185498e), BeginOpengl
 *     matrices and wheel FOV zoom (client_camera, client_world_camera);
 *   - the client's input state: per-step GetAsyncKeyState-style key scan
 *     and the window-procedure mouse globals (client_input);
 *   - click-to-move as the client starts it: mouse ray (CreateScreenVector
 *     in the render pass), terrain pick on the next logic step
 *     (RenderTerrain(1) / RenderTerrainTile picking), target tile =
 *     (int)(collision / 100).
 * What is NOT client behaviour and is marked as a placeholder: the flat
 * terrain, the straight-line hero walk (no path finding, constant speed)
 * and the action log for keys whose client handlers are not ported. */

#include <stdint.h>

#include "../../reconstructed/camera/client_camera.h"
#include "../../reconstructed/camera/client_frame.h"
#include "../../reconstructed/camera/client_input.h"
#include "../../reconstructed/camera/client_world_camera.h"
#include "mu_scene.h"

#define MU_TERRAIN_SIZE 256
#define MU_FRAME_LOG 32

/* Windows virtual-key code for a USB HID keyboard usage (the numbering SDL
 * scancodes use), 0 when the key has no mapping. */
int mu_vk_from_hid(int usage);
/* Short label of the client action bound to a virtual key in the in-world
 * hotkey dispatcher 0x00efbfd0 and its neighbours (static reading,
 * docs/research/client-camera-input.md), or NULL. */
const char *mu_vk_action(int vk);

typedef struct mu_frame_world {
    mu_client_view view;
    mu_world_camera camera;
    mu_frame_clock clock;
    mu_key_input keys;
    mu_key_sample sample;      /* current key-down state; scanned once per logic step */
    mu_mouse mouse;
    mu_pick_state pick;
    float heights[MU_TERRAIN_SIZE * MU_TERRAIN_SIZE];
    uint16_t walls[MU_TERRAIN_SIZE * MU_TERRAIN_SIZE];
    mu_terrain_heights terrain;
    /* hero placeholder */
    float hero[3];
    float hero_angle;          /* degrees about +Z, model facing */
    int32_t target_tile[2];
    float target[3];
    uint8_t moving;
    float walk_speed;          /* units per logic step (placeholder) */
    /* bookkeeping */
    uint32_t now;              /* GetTickCount equivalent supplied by the front end */
    int32_t picks, pick_hits;
    char log[MU_FRAME_LOG][64];
    int32_t log_count;
} mu_frame_world;

/* Flat terrain at height 0, window size in pixels, hero on tile (x, y). */
void mu_frame_world_init(mu_frame_world *world, uint32_t window_width, uint32_t window_height, int32_t tile_x,
                         int32_t tile_y);
/* Window message in Win32 form (front ends translate their events). Mouse
 * coordinates in lparam are window pixels; scale is set from the window. */
void mu_frame_world_message(mu_frame_world *world, uint32_t message, uint32_t wparam, uint32_t lparam);
/* Sets the down state of a virtual key (sampled at the next logic step). */
void mu_frame_world_key(mu_frame_world *world, int vk, int down);
/* Runs the logic steps that are due (client accumulator) and returns how
 * many ran. now is the tick used by tick-based timers during the steps. */
int32_t mu_frame_world_update(mu_frame_world *world, uint32_t now);
/* One logic step (also used directly by tests). */
void mu_frame_world_step(mu_frame_world *world);
/* Frame start tick (the client reads GetTickCount after the logic steps),
 * MoveMainCamera, BeginOpengl(0, 0, 640, 480) and the mouse ray of the
 * render pass. After this, view.projection/view.modelview are the frame's
 * GL matrices. */
void mu_frame_world_begin_render(mu_frame_world *world, uint32_t now);
/* Frame cap after the render: returns the milliseconds to sleep, -1 for none. */
int32_t mu_frame_world_end_render(mu_frame_world *world);

/* Placeholder scene through a GL-shaped backend: terrain tiles within
 * `radius` tiles of the hero (checker colours, darker every 10th line), the
 * click target marker, and a box at the hero when no model is drawn.
 * Returns the number of triangles emitted. */
long mu_frame_draw_world(const mu_frame_world *world, const mu_render_backend *backend, int32_t radius, int draw_box);

#endif
