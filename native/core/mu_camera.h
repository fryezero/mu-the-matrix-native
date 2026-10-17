#ifndef MU_CAMERA_H
#define MU_CAMERA_H

/* Orbit camera and matrices for the viewer (viewer code, not client code).
 * Z is up, as in the client's world. Matrices are column-major float[16]
 * (OpenGL glLoadMatrixf order). Trigonometry uses mu_det_sin/mu_det_cos,
 * fixed polynomials in binary64 basic operations, so the matrices are
 * bit-identical on every IEEE host (no libm dependence) when built with
 * -ffp-contract=off. */

typedef struct mu_camera {
    float target[3];
    float yaw, pitch;      /* degrees; yaw about +Z from +X, pitch above the XY plane */
    float distance;
    float fov_y;           /* degrees */
    float near_plane, far_plane;
} mu_camera;

double mu_det_sin(double x);
double mu_det_cos(double x);

void mu_camera_view(const mu_camera *camera, float view[16]);
void mu_camera_projection(const mu_camera *camera, float aspect, float projection[16]);
void mu_camera_eye(const mu_camera *camera, float eye[3]);

/* Frames an axis-aligned box: target at its centre, distance so that its
 * bounding sphere fits the vertical field of view, planes around it. */
void mu_camera_frame(mu_camera *camera, const float lo[3], const float hi[3]);

/* out = a * b (column-major 4x4), fixed evaluation order. */
void mu_mat4_multiply(const float a[16], const float b[16], float out[16]);

#endif
