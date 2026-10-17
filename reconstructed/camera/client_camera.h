#ifndef MU_CLIENT_CAMERA_H
#define MU_CLIENT_CAMERA_H

/* Camera, projection and mouse picking of the client (NATIVE-FRAME-001,
 * docs/research/client-camera-input.md). Authored names; the addresses in
 * the comments are the original routines in the pinned restored text.
 *
 * Every client operation here is binary32 (SSE MULSS/DIVSS/ADDSS) unless
 * noted, so the code must be built with -ffp-contract=off. Integer
 * conversions use the x86 CVTTSS2SI rule (out of range or NaN gives
 * INT32_MIN), see mu_cvtt. Matrices named camera_matrix are the client's
 * row-major 3x4 records; GL matrices are column-major float[16].
 *
 * The GL-side matrices (glRotatef, glTranslatef, gluPerspective) are not
 * client code: the client calls the driver and reads the modelview back
 * with glGetFloatv. They are computed here with the OpenGL/GLU reference
 * formulas (Mesa/Wine glu32 order) and labelled as such. */

#include <stdint.h>

#include "../record-math/record_math.h"

/* x86 CVTTSS2SI: truncation, INT32_MIN for NaN and out-of-range values. */
int32_t mu_cvtt(float value);

/* The client globals the camera reads and writes. */
typedef struct mu_client_view {
    uint32_t window_width, window_height;         /* 0x01cf1624, 0x01cf1628 (unsigned) */
    int32_t screen_x, screen_y;                   /* 0x0bdc58a8, 0x0bdc58ac */
    int32_t screen_width, screen_height;          /* 0x0bdc58dc, 0x0bdc58e0 */
    int32_t center_x, center_y, center_y_flip;    /* 0x0bdc58b8, 0x0bdc58bc, 0x0bdc58c0 */
    float perspective_x, perspective_y;           /* 0x0bdc58cc, 0x0bdc58d0 */
    float fov, view_near, view_far;               /* 0x01cf1634, 0x01cf162c, 0x01cf1630 */
    float angle[3];                               /* CameraAngle 0x0bdc58f0 (degrees) */
    float position[3];                            /* CameraPosition 0x0bdc5ab4 */
    uint8_t top_view;                             /* 0x0bdc58b7 */
    float camera_matrix[12];                      /* 0x0bdc5918, row-major 3x4 */
    float mouse_position[3];                      /* ray origin 0x0bdc5984 */
    float mouse_target[3];                        /* ray end 0x0bdc5990 */
    /* GL state produced by BeginOpengl (reference formulas, not client code) */
    int32_t gl_viewport[4];
    float projection[16], modelview[16];
} mu_client_view;

/* glViewport2 0x01849ec4: stores the screen rectangle and returns the
 * glViewport arguments (x, window_height - (y + h), w, h). */
void mu_view_viewport2(mu_client_view *view, int32_t x, int32_t y, int32_t width, int32_t height);

/* gluPerspective2 0x01849d76: gluPerspective, then the screen centres and
 * the two per-pixel perspective factors used by projection and picking:
 *   center_x = screen_w/2 + screen_x (C division), center_y likewise,
 *   center_y_flip = window_WIDTH - center_y (the client reads 0x01cf1624
 *     here, not the height; kept as observed),
 *   perspective_x = tan(fov*0.5*3.1415925/180) / (screen_w/2) * aspect,
 *   perspective_y = tan(...) / (screen_h/2) * (window_height / screen_h).
 * tan is the client wrapper 0x00a0cf72 (float -> double CRT tan -> float);
 * the _using variant takes the double tan, the default uses host libm. The
 * projection matrix is set to the GLU reference result. */
void mu_view_perspective2_using(mu_client_view *view, float fov, float aspect, float znear, float zfar,
                                mu_rotation_trig tangent);
void mu_view_perspective2(mu_client_view *view, float fov, float aspect, float znear, float zfar);

/* BeginOpengl 0x0184adc7 (camera part). Arguments are 640x480 virtual
 * coordinates scaled with unsigned 32-bit arithmetic by the window size.
 * Projection: gluPerspective2(fov, w/h, near, far*1.4). Modelview:
 * identity, Rotate(angle[1], 0,1,0), Rotate(angle[0], 1,0,0) unless
 * top_view, Rotate(angle[2], 0,0,1), Translate(-position). The camera
 * matrix is then read back (GetOpenGLMatrix 0x0184a569: m[r][c] = mv[r+4c]).
 * Uses the libm tan; mu_view_begin_opengl_using takes it explicitly. */
void mu_view_begin_opengl_using(mu_client_view *view, int32_t x, int32_t y, int32_t width, int32_t height,
                                mu_rotation_trig tangent);
void mu_view_begin_opengl(mu_client_view *view, int32_t x, int32_t y, int32_t width, int32_t height);
/* GetOpenGLMatrix 0x0184a569 alone: camera_matrix from a GL modelview. */
void mu_view_camera_matrix_from_gl(mu_client_view *view, const float modelview[16]);

/* CreateScreenVector 0x01849f08: mouse ray in world space.
 *   sx' = (float)window_width * sx / 640, sy' = (float)window_height * sy / 480
 *   p1 = ((sx'-cx)*F*px, -(sy'-cy)*F*py, -F), F = view_far, or 2000 when !fix_view
 *   mouse_position = IRotate(-camera_matrix[.][3]); target = mouse_position + IRotate(p1). */
void mu_view_create_screen_vector(mu_client_view *view, float sx, float sy, float target[3], int fix_view);

/* World to screen. 0x0184a244: integer 640x480 coordinates (signed IMUL/IDIV
 * by the window size). 0x0184a3ce: float window pixels. 0x0184a2e8: as
 * 0x0184a3ce, divided by 0.83 when the window is lower than 700 pixels.
 * 0x0184a455 (TransformPosition): rotate (pos - camera position), screen y
 * relative to center_y_flip. All use the camera matrix. */
void mu_view_projection(const mu_client_view *view, const float position[3], int32_t *sx, int32_t *sy);
void mu_view_projection_float(const mu_client_view *view, const float position[3], float *sx, float *sy);
void mu_view_projection_float_scaled(const mu_client_view *view, const float position[3], float *sx, float *sy);
void mu_view_transform_position(const mu_client_view *view, const float position[3], float out[3], int32_t *sx,
                                int32_t *sy);

/* ---- picking ---- */

/* FaceNormalize 0x00d01206: cleared, then the binary32 cross product of
 * (b-a) and (c-a) divided (in binary64) by (double)(float)sqrt(len2) unless
 * that length is zero. */
void mu_face_normalize(const float a[3], const float b[3], const float c[3], float normal[3]);

/* InsideTest 0x018506bc: 2D edge test of point (x,y,z) against n vertices
 * (vertex pointers a,b,c,d) on the plane selected by axis 1 (y,z), 2 (z,x)
 * or 4 (x,y); when type > 0 the axis is shifted left by 3 and the sign test
 * flips. Returns 1 inside, 0 outside; an unknown axis returns 1. */
int mu_inside_test(float x, float y, float z, int32_t n, const float *a, const float *b, const float *c,
                   const float *d, int32_t axis, float type);

/* Picking state: nearest accepted ray parameter 0x0bdc58c8 (reset to 9999999
 * by 0x0184f957 before a picking pass) and the hit point 0x0bdc58e4. */
typedef struct mu_pick_state {
    float nearest;
    float collision[3];
} mu_pick_state;

void mu_pick_reset(mu_pick_state *pick);

/* CollisionDetectLineToFace 0x0184f96c(origin, target, n, a,b,c,d, normal,
 * store). t = -(N.origin - N.a) / N.(target-origin) must satisfy
 * 0 <= t <= nearest; the hit X = dir*t + origin must lie inside the segment's
 * box on the two axes other than the one with the smallest |dir|; then
 * InsideTest on the plane of the largest normal component (|n| >= 0.5,
 * checked x, y, z). On success with store set, nearest = t and collision = X. */
int mu_collision_line_face(mu_pick_state *pick, const float origin[3], const float target[3], int32_t n,
                           const float a[3], const float b[3], const float c[3], const float d[3],
                           const float normal[3], int store);

/* Terrain inputs read by the tile test 0x016ccda5 (client arrays, 256x256,
 * index y*256 + x without wrapping): heights 0x0b6f5420 (float), wall flags
 * 0x0b795420 (uint16; 0x40 = water tile, its corners use water_height
 * 0x01cf15dc). */
typedef struct mu_terrain_heights {
    const float *height;
    const uint16_t *wall;
    float water_height;
} mu_terrain_heights;

/* RenderTerrainTile 0x016ccda5 with Flag set (the picking path). Corners
 * (xf*100 [+100], yf*100 [+100], height of tile (xi[+lod], yi[+lod])); the ray
 * is mouse_position -> mouse_target. Tests triangle (v0,v1,v2) then
 * (v0,v2,v3) with polygon count 3. On a hit sets *select_flag = 1 and
 * select_xf/yf (0x0b5e3ea6, 0x0b7f5420/4). Returns 1 on a hit. */
int mu_terrain_tile_pick(mu_pick_state *pick, const mu_client_view *view, const mu_terrain_heights *terrain,
                         float xf, float yf, int32_t xi, int32_t yi, float lodf, int32_t lodi,
                         uint8_t *select_flag, float *select_xf, float *select_yf);

/* Whole-terrain pick (authored driver): resets the pick state, tests every
 * tile of the inclusive rectangle in client block order (rows of x within
 * y) and returns 1 with the last accepted tile, the hit point in
 * pick->collision and the target tile (int)(collision/100) as 0x016a5063 does. */
int mu_terrain_pick(mu_pick_state *pick, const mu_client_view *view, const mu_terrain_heights *terrain,
                    int32_t x0, int32_t y0, int32_t x1, int32_t y1, int32_t *tile_x, int32_t *tile_y);

#endif
