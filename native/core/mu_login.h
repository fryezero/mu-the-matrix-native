#ifndef MU_LOGIN_SESSION_H
#define MU_LOGIN_SESSION_H

/* Native login scene: the 3D world behind the login and server-select screens (NATIVE-LOGIN-001,
 * docs/research/client-login-scene.md).
 *
 * One session of scene state 3 built from the reconstructed client routines:
 *   - world 0x5e (Data/World95) terrain through mu_terrain;
 *   - the camera through MoveMainCamera's scene-3 record path (reconstructed/camera), i.e. the fixed
 *     World95 Camera_Angle_Position record (angle -84.5, 0, -45, FOV 35), BeginOpengl(0, 0, 640, 480)
 *     and CreateFrustrum(width / 640, record position, 0); CameraViewFar = 2400 * Distance * Z_Distance;
 *   - per logic step the scene-3 tick head (mu_scenemgr_login_tick_head): the frame-light copy over the
 *     last frustum box and MoveObjects with the login world's handler (reconstructed/objects/login_world);
 *   - per frame the login render's 3D part (mu_scenemgr_login_render_3d): RenderTerrain(0),
 *     RenderObjects (CreateObject/RenderObject/RenderObjectVisual with CGMLogInScene_Ex),
 *     RenderObjects_AfterCharacter (the ship's glow meshes), then the sprites and particles.
 *
 * Placements come from a local decoded EncTerrain95.plain (the installed .obj files do not decode in the
 * captured code; docs/research/client-objects.md): without one only the terrain is drawn.
 *
 * Stand-ins (not client code): the sprite and particle systems (CreateSprite 0x01692eb7 and
 * CreateParticle 0x0168fafd are not reconstructed) draw as additive billboards of the client's bitmaps;
 * the boids/bugs passes 0x00c9e4e3/0x00c9e24a, 0x00c9fd8d/0x00c9eb04, the joints, blurs and effects of the
 * render are not drawn (the login world creates none of them through the code reconstructed here). */

#include <stdint.h>

#include "mu_frame.h"
#include "mu_objects.h"
#include "mu_raster.h"
#include "mu_terrain.h"
#include "mu_walk.h"

#define MU_LOGIN_SCENE 3
#define MU_LOGIN_WORLD_INDEX 0x5e
#define MU_LOGIN_MESHES 32

typedef struct mu_login_session {
    mu_frame_world *frame;          /* clock, camera, view (heap: large) */
    mu_world *map;
    mu_camera_info info;
    mu_objects objects;
    int has_objects;
    mu_terrain_frustum frustum;
    float view_far;                 /* CameraViewFar [0x01cf1630] of the last render */
    int draw_3d;                    /* the render drew the 3D part (the credit window was closed) */
    uint32_t steps, frames;
    long objects_drawn, after_meshes, billboards;
    char error[256];
} mu_login_session;

/* Loads World95, its camera record and (objects_dir not NULL) the local EncTerrain95.plain with the models
 * and the object lifecycle. window_* are drawable pixels; near_plane 20 is CameraViewNear. Returns 0 on
 * success (error text in s->error). A missing plaintext is not an error (terrain only). */
int mu_login_init(mu_login_session *s, const char *game_root, const char *objects_dir, uint32_t window_width,
                  uint32_t window_height, float near_plane);
void mu_login_free(mu_login_session *s);
void mu_login_resize(mu_login_session *s, uint32_t window_width, uint32_t window_height);

/* One logic step of the scene-3 tick head: the frame-light copy over the last frustum box (+3 tiles) and
 * MoveObjects. now: the frame clock (ms, GetTickCount). */
void mu_login_step(mu_login_session *s, uint32_t now);
/* Due logic steps at `now` (the 40 ms logic clock); returns how many ran. */
int32_t mu_login_update(mu_login_session *s, uint32_t now);
/* The render's camera part: MoveMainCamera (record path), BeginOpengl(0, 0, 640, 480), the frustum and
 * CameraViewFar. draw_3d: whether the render's 3D block runs (credit window closed). */
void mu_login_begin_render(mu_login_session *s, uint32_t now, int draw_3d);

/* A frame without drawing (warm-up of headless captures): begin_render, RenderObjects with
 * RenderObject/RenderObjectVisual per drawn object, the after-character visibility. */
void mu_login_frame(mu_login_session *s, uint32_t now);

/* Software draw of the 3D part into raster (cleared to black, glClearColor(0, 0, 0, 1)). Returns the
 * terrain faces drawn. */
long mu_login_draw_soft(mu_login_session *s, mu_raster *raster);

/* Camera eye and a point ahead of it (billboard orientation). */
void mu_login_eye(const mu_login_session *s, float eye[3], float target[3]);

/* JSON summary of the session (one line, no newline) into out. */
void mu_login_report(const mu_login_session *s, char *out, size_t size);

#endif
