/* Orbit camera and deterministic matrices. See mu_camera.h. */
#include "mu_camera.h"

static const double pi = 3.14159265358979323846;

/* Reduce to [-pi/4, pi/4] with a quadrant, then Taylor series to x^21 (error
 * far below binary32 resolution for the camera's purposes). */
static double reduce(double x, int *quadrant)
{
    double turns = x / (pi / 2);
    double k = (double)(long long)(turns >= 0 ? turns + 0.5 : turns - 0.5);
    *quadrant = (int)((long long)k & 3);
    return x - k * (pi / 2);
}

static double series_sin(double r)
{
    double r2 = r * r, term = r, sum = r;
    for (int n = 1; n <= 10; ++n) {
        term = -term * r2 / (double)((2 * n) * (2 * n + 1));
        sum = sum + term;
    }
    return sum;
}

static double series_cos(double r)
{
    double r2 = r * r, term = 1.0, sum = 1.0;
    for (int n = 1; n <= 10; ++n) {
        term = -term * r2 / (double)((2 * n - 1) * (2 * n));
        sum = sum + term;
    }
    return sum;
}

double mu_det_sin(double x)
{
    int q;
    double r = reduce(x, &q);
    switch (q) {
    case 0: return series_sin(r);
    case 1: return series_cos(r);
    case 2: return -series_sin(r);
    default: return -series_cos(r);
    }
}

double mu_det_cos(double x)
{
    int q;
    double r = reduce(x, &q);
    switch (q) {
    case 0: return series_cos(r);
    case 1: return -series_sin(r);
    case 2: return -series_cos(r);
    default: return series_sin(r);
    }
}

static double det_sqrt(double x)
{
    /* Newton iterations from a safe start; IEEE sqrt would also be exact, but
     * this keeps the module free of libm. */
    if (x <= 0)
        return 0;
    double y = x > 1 ? x : 1;
    for (int k = 0; k < 64; ++k) {
        double next = 0.5 * (y + x / y);
        if (next >= y)
            break;
        y = next;
    }
    return y;
}

void mu_camera_eye(const mu_camera *c, float eye[3])
{
    double yaw = (double)c->yaw * pi / 180.0, pitch = (double)c->pitch * pi / 180.0;
    double cp = mu_det_cos(pitch), sp = mu_det_sin(pitch), cy = mu_det_cos(yaw), sy = mu_det_sin(yaw);
    eye[0] = (float)((double)c->target[0] + (double)c->distance * cp * cy);
    eye[1] = (float)((double)c->target[1] + (double)c->distance * cp * sy);
    eye[2] = (float)((double)c->target[2] + (double)c->distance * sp);
}

void mu_camera_view(const mu_camera *c, float m[16])
{
    float eyef[3];
    mu_camera_eye(c, eyef);
    double eye[3] = {eyef[0], eyef[1], eyef[2]};
    double f[3] = {(double)c->target[0] - eye[0], (double)c->target[1] - eye[1], (double)c->target[2] - eye[2]};
    double fl = det_sqrt(f[0] * f[0] + f[1] * f[1] + f[2] * f[2]);
    if (fl == 0)
        fl = 1;
    f[0] /= fl; f[1] /= fl; f[2] /= fl;
    double up[3] = {0, 0, 1};
    double s[3] = {f[1] * up[2] - f[2] * up[1], f[2] * up[0] - f[0] * up[2], f[0] * up[1] - f[1] * up[0]};
    double sl = det_sqrt(s[0] * s[0] + s[1] * s[1] + s[2] * s[2]);
    if (sl == 0) {
        s[0] = 1; s[1] = 0; s[2] = 0; sl = 1;
    }
    s[0] /= sl; s[1] /= sl; s[2] /= sl;
    double u[3] = {s[1] * f[2] - s[2] * f[1], s[2] * f[0] - s[0] * f[2], s[0] * f[1] - s[1] * f[0]};
    double t[3] = {-(s[0] * eye[0] + s[1] * eye[1] + s[2] * eye[2]),
                   -(u[0] * eye[0] + u[1] * eye[1] + u[2] * eye[2]),
                   (f[0] * eye[0] + f[1] * eye[1] + f[2] * eye[2])};
    m[0] = (float)s[0]; m[4] = (float)s[1]; m[8] = (float)s[2]; m[12] = (float)t[0];
    m[1] = (float)u[0]; m[5] = (float)u[1]; m[9] = (float)u[2]; m[13] = (float)t[1];
    m[2] = (float)-f[0]; m[6] = (float)-f[1]; m[10] = (float)-f[2]; m[14] = (float)t[2];
    m[3] = 0; m[7] = 0; m[11] = 0; m[15] = 1;
}

void mu_camera_projection(const mu_camera *c, float aspect, float m[16])
{
    double half = (double)c->fov_y * pi / 360.0;
    double cot = mu_det_cos(half) / mu_det_sin(half);
    double n = c->near_plane, f = c->far_plane;
    for (int k = 0; k < 16; ++k)
        m[k] = 0;
    m[0] = (float)(cot / (double)aspect);
    m[5] = (float)cot;
    m[10] = (float)((f + n) / (n - f));
    m[11] = -1;
    m[14] = (float)(2 * f * n / (n - f));
}

void mu_camera_frame(mu_camera *c, const float lo[3], const float hi[3])
{
    double radius2 = 0;
    for (int k = 0; k < 3; ++k) {
        c->target[k] = (float)(((double)lo[k] + (double)hi[k]) * 0.5);
        double half = ((double)hi[k] - (double)lo[k]) * 0.5;
        radius2 += half * half;
    }
    double radius = det_sqrt(radius2);
    if (radius < 1)
        radius = 1;
    double half = (double)c->fov_y * pi / 360.0;
    double distance = radius / mu_det_sin(half) * 0.8;
    c->distance = (float)distance;
    c->near_plane = (float)(distance - radius * 1.5 > distance * 0.01 ? distance - radius * 1.5 : distance * 0.01);
    c->far_plane = (float)(distance + radius * 3.0);
}

void mu_mat4_multiply(const float a[16], const float b[16], float out[16])
{
    float r[16];
    for (int col = 0; col < 4; ++col)
        for (int row = 0; row < 4; ++row) {
            float sum = a[row] * b[4 * col];
            sum = sum + a[4 + row] * b[4 * col + 1];
            sum = sum + a[8 + row] * b[4 * col + 2];
            sum = sum + a[12 + row] * b[4 * col + 3];
            r[4 * col + row] = sum;
        }
    for (int k = 0; k < 16; ++k)
        out[k] = r[k];
}
