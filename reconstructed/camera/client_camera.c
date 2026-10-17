/* Camera, projection and picking. See client_camera.h. */
#include "client_camera.h"

#include <math.h>
#include <string.h>

int32_t mu_cvtt(float value)
{
    if (!(value > -2147483904.0f && value < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)value;
}

/* (float) of an unsigned 32-bit value as the client converts it: CVTSI2SD of
 * the signed value plus 2^32 when the sign bit is set, then CVTSD2SS. */
static float unsigned_to_float(uint32_t value)
{
    double widened = (double)(int32_t)value;
    if (value & 0x80000000u)
        widened = widened + 4294967296.0;
    return (float)widened;
}

/* ---- GL reference matrices (not client code) ---- */

static void gl_identity(float m[16])
{
    memset(m, 0, 16 * sizeof(float));
    m[0] = m[5] = m[10] = m[15] = 1.0f;
}

/* product = a * b, column-major, Mesa matmul4 summation order. */
static void gl_multiply(float a[16], const float b[16])
{
    float p[16];
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j) {
            float sum = a[i] * b[4 * j];
            sum = sum + a[4 + i] * b[4 * j + 1];
            sum = sum + a[8 + i] * b[4 * j + 2];
            sum = sum + a[12 + i] * b[4 * j + 3];
            p[4 * j + i] = sum;
        }
    memcpy(a, p, sizeof p);
}

/* glRotatef with the axis-aligned cases the client uses (Mesa
 * _math_matrix_rotate optimized branches); a general axis falls back to the
 * normalized Rodrigues form. */
static void gl_rotate(float m[16], float angle, float x, float y, float z)
{
    float r[16];
    float s = (float)sin((double)angle * 3.14159265358979323846 / 180.0);
    float c = (float)cos((double)angle * 3.14159265358979323846 / 180.0);
    gl_identity(r);
#define R(row, col) r[(col) * 4 + (row)]
    if (x == 0.0f && y == 0.0f && z != 0.0f) {
        R(0, 0) = c;
        R(1, 1) = c;
        R(0, 1) = z < 0.0f ? s : -s;
        R(1, 0) = z < 0.0f ? -s : s;
    } else if (x == 0.0f && z == 0.0f && y != 0.0f) {
        R(0, 0) = c;
        R(2, 2) = c;
        R(0, 2) = y < 0.0f ? -s : s;
        R(2, 0) = y < 0.0f ? s : -s;
    } else if (y == 0.0f && z == 0.0f && x != 0.0f) {
        R(1, 1) = c;
        R(2, 2) = c;
        R(1, 2) = x < 0.0f ? s : -s;
        R(2, 1) = x < 0.0f ? -s : s;
    } else {
        float mag = sqrtf(x * x + y * y + z * z);
        if (mag <= 1.0e-4f)
            return;
        x /= mag;
        y /= mag;
        z /= mag;
        float one_c = 1.0f - c;
        R(0, 0) = (one_c * x * x) + c;
        R(0, 1) = (one_c * x * y) - z * s;
        R(0, 2) = (one_c * z * x) + y * s;
        R(1, 0) = (one_c * x * y) + z * s;
        R(1, 1) = (one_c * y * y) + c;
        R(1, 2) = (one_c * y * z) - x * s;
        R(2, 0) = (one_c * z * x) - y * s;
        R(2, 1) = (one_c * y * z) + x * s;
        R(2, 2) = (one_c * z * z) + c;
    }
#undef R
    gl_multiply(m, r);
}

static void gl_translate(float m[16], float x, float y, float z)
{
    m[12] = m[0] * x + m[4] * y + m[8] * z + m[12];
    m[13] = m[1] * x + m[5] * y + m[9] * z + m[13];
    m[14] = m[2] * x + m[6] * y + m[10] * z + m[14];
    m[15] = m[3] * x + m[7] * y + m[11] * z + m[15];
}

/* gluPerspective (Wine glu32 / SGI reference), applied with glMultMatrixd
 * (doubles converted to float, then multiplied). */
static void glu_perspective(float m[16], double fovy, double aspect, double znear, double zfar)
{
    double radians = fovy / 2 * 3.14159265358979323846 / 180;
    double delta = zfar - znear;
    double sine = sin(radians);
    if (delta == 0 || sine == 0 || aspect == 0)
        return;
    double cotangent = cos(radians) / sine;
    double p[16] = {0};
    p[0] = cotangent / aspect;
    p[5] = cotangent;
    p[10] = -(zfar + znear) / delta;
    p[11] = -1;
    p[14] = -2 * znear * zfar / delta;
    float f[16];
    for (int i = 0; i < 16; ++i)
        f[i] = (float)p[i];
    gl_multiply(m, f);
}

/* ---- client routines ---- */

void mu_view_viewport2(mu_client_view *v, int32_t x, int32_t y, int32_t width, int32_t height)
{
    v->screen_x = x;
    v->screen_y = y;
    v->screen_width = width;
    v->screen_height = height;
    v->gl_viewport[0] = x;
    v->gl_viewport[1] = (int32_t)(v->window_height - ((uint32_t)y + (uint32_t)height));
    v->gl_viewport[2] = width;
    v->gl_viewport[3] = height;
}

static double libm_tan(double x)
{
    return tan(x);
}

void mu_view_perspective2_using(mu_client_view *v, float fov, float aspect, float znear, float zfar,
                                mu_rotation_trig tangent)
{
    glu_perspective(v->projection, (double)fov, (double)aspect, (double)znear, (double)zfar);
    v->center_x = v->screen_width / 2 + v->screen_x;
    v->center_y = v->screen_height / 2 + v->screen_y;
    v->center_y_flip = (int32_t)(v->window_width - (uint32_t)v->center_y);
    float aspect_y = unsigned_to_float(v->window_height) / (float)v->screen_height;
    const float half = 0.5f, pi = 0x1.921fb0p+1f /* 0x40490fd8, as stored */, degrees = 180.0f;
    float radians = fov * half;
    radians = radians * pi;
    radians = radians / degrees;
    float t = (float)tangent((double)radians);
    float px = t / (float)(v->screen_width / 2);
    v->perspective_x = px * aspect;
    radians = fov * half;
    radians = radians * pi;
    radians = radians / degrees;
    t = (float)tangent((double)radians);
    float py = t / (float)(v->screen_height / 2);
    v->perspective_y = py * aspect_y;
}

void mu_view_perspective2(mu_client_view *v, float fov, float aspect, float znear, float zfar)
{
    mu_view_perspective2_using(v, fov, aspect, znear, zfar, libm_tan);
}

void mu_view_camera_matrix_from_gl(mu_client_view *v, const float mv[16])
{
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 4; ++c)
            v->camera_matrix[r * 4 + c] = mv[r + 4 * c];
}

void mu_view_begin_opengl_using(mu_client_view *v, int32_t x, int32_t y, int32_t width, int32_t height,
                                mu_rotation_trig tangent)
{
    uint32_t sx = (uint32_t)x * v->window_width / 640u;
    uint32_t sy = (uint32_t)y * v->window_height / 480u;
    uint32_t sw = (uint32_t)width * v->window_width / 640u;
    uint32_t sh = (uint32_t)height * v->window_height / 480u;
    gl_identity(v->projection);
    mu_view_viewport2(v, (int32_t)sx, (int32_t)sy, (int32_t)sw, (int32_t)sh);
    float far_plane = v->view_far * 1.4f;
    float aspect = (float)(int32_t)sw / (float)(int32_t)sh;
    mu_view_perspective2_using(v, v->fov, aspect, v->view_near, far_plane, tangent);
    gl_identity(v->modelview);
    gl_rotate(v->modelview, v->angle[1], 0.0f, 1.0f, 0.0f);
    if (!v->top_view)
        gl_rotate(v->modelview, v->angle[0], 1.0f, 0.0f, 0.0f);
    gl_rotate(v->modelview, v->angle[2], 0.0f, 0.0f, 1.0f);
    gl_translate(v->modelview, -v->position[0], -v->position[1], -v->position[2]);
    mu_view_camera_matrix_from_gl(v, v->modelview);
}

void mu_view_begin_opengl(mu_client_view *v, int32_t x, int32_t y, int32_t width, int32_t height)
{
    mu_view_begin_opengl_using(v, x, y, width, height, libm_tan);
}

void mu_view_create_screen_vector(mu_client_view *v, float sx, float sy, float target[3], int fix_view)
{
    sx = unsigned_to_float(v->window_width) * sx;
    sx = sx / 640.0f;
    sy = unsigned_to_float(v->window_height) * sy;
    sy = sy / 480.0f;
    float p1[3], p2[3];
    float distance = fix_view ? v->view_far : 2000.0f;
    float value = sx - (float)v->center_x;
    value = value * distance;
    p1[0] = value * v->perspective_x;
    value = -(sy - (float)v->center_y);
    value = value * distance;
    p1[1] = value * v->perspective_y;
    p1[2] = fix_view ? -v->view_far : -2000.0f;
    for (int i = 0; i < 3; ++i)
        p2[i] = -v->camera_matrix[i * 4 + 3];
    mu_vector_irotate(p2, v->camera_matrix, v->mouse_position);
    mu_vector_irotate(p1, v->camera_matrix, p2);
    for (int i = 0; i < 3; ++i)
        target[i] = v->mouse_position[i] + p2[i];
}

void mu_view_projection(const mu_client_view *v, const float position[3], int32_t *sx, int32_t *sy)
{
    float t[3];
    mu_vector_transform(position, v->camera_matrix, t);
    float value = t[0] / v->perspective_x;
    value = value / t[2];
    *sx = (int32_t)((uint32_t)v->center_x - (uint32_t)mu_cvtt(value));
    value = t[1] / v->perspective_y;
    value = value / t[2];
    *sy = (int32_t)((uint32_t)mu_cvtt(value) + (uint32_t)v->center_y);
    /* IMUL by 640/480 (low 32 bits), signed IDIV by the window size. */
    int32_t px = (int32_t)((uint32_t)*sx * 640u);
    *sx = px / (int32_t)v->window_width;
    int32_t py = (int32_t)((uint32_t)*sy * 480u);
    *sy = py / (int32_t)v->window_height;
}

void mu_view_projection_float(const mu_client_view *v, const float position[3], float *sx, float *sy)
{
    float t[3];
    mu_vector_transform(position, v->camera_matrix, t);
    float value = t[0] / v->perspective_x;
    value = value / t[2];
    *sx = -value + (float)v->center_x;
    value = t[1] / v->perspective_y;
    value = value / t[2];
    *sy = value + (float)v->center_y;
}

void mu_view_projection_float_scaled(const mu_client_view *v, const float position[3], float *sx, float *sy)
{
    mu_view_projection_float(v, position, sx, sy);
    if (700.0f > unsigned_to_float(v->window_height)) {
        *sx = *sx / 0.83f;
        *sy = *sy / 0.83f;
    }
}

void mu_view_transform_position(const mu_client_view *v, const float position[3], float out[3], int32_t *sx,
                                int32_t *sy)
{
    float d[3];
    for (int i = 0; i < 3; ++i)
        d[i] = position[i] - v->position[i];
    mu_vector_rotate(d, v->camera_matrix, out);
    float value = out[0] / v->perspective_x;
    value = value / -out[2];
    *sx = (int32_t)((uint32_t)mu_cvtt(value) + (uint32_t)v->center_x);
    value = out[1] / v->perspective_y;
    value = value / -out[2];
    *sy = (int32_t)((uint32_t)mu_cvtt(value) + (uint32_t)v->center_y_flip);
}

/* ---- picking ---- */

void mu_face_normalize(const float a[3], const float b[3], const float c[3], float n[3])
{
    n[0] = n[1] = n[2] = 0.0f;
    float nx = (b[1] - a[1]) * (c[2] - a[2]);
    nx = nx - (c[1] - a[1]) * (b[2] - a[2]);
    float ny = (b[2] - a[2]) * (c[0] - a[0]);
    ny = ny - (c[2] - a[2]) * (b[0] - a[0]);
    float nz = (b[0] - a[0]) * (c[1] - a[1]);
    nz = nz - (c[0] - a[0]) * (b[1] - a[1]);
    float sum = nx * nx;
    sum = sum + ny * ny;
    sum = sum + nz * nz;
    double length = (double)(float)sqrt((double)sum);
    if (length == 0.0)
        return;
    n[0] = (float)((double)nx / length);
    n[1] = (float)((double)ny / length);
    n[2] = (float)((double)nz / length);
}

/* One edge term of InsideTest: (v[i][p]-P)*(v[j][q]-Q) - (v[j][p]-P)*(v[i][q]-Q). */
static float edge(const float *vi, const float *vj, int p, int q, float pv, float qv)
{
    float left = vi[p] - pv;
    left = left * (vj[q] - qv);
    float right = vj[p] - pv;
    right = right * (vi[q] - qv);
    return left - right;
}

int mu_inside_test(float x, float y, float z, int32_t n, const float *a, const float *b, const float *c,
                   const float *d, int32_t axis, float type)
{
    float vertex[4][3];
    const float *source[4] = {a, b, c, d};
    for (int k = 0; k < 4; ++k)
        memcpy(vertex[k], source[k], sizeof vertex[k]);
    if (type > 0.0f)
        axis = (int32_t)((uint32_t)axis << 3);
    const float point[3] = {x, y, z};
    int p, q;
    switch (axis) {
    case 1: case 8: p = 1; q = 2; break;
    case 2: case 16: p = 2; q = 0; break;
    case 4: case 32: p = 0; q = 1; break;
    default: return 1;
    }
    int32_t j = n - 1;
    for (int32_t i = 0; i < n; j = i, ++i) {
        float value = edge(vertex[i], vertex[j], p, q, point[p], point[q]);
        if (axis < 8) {
            if (0.0f >= value)   /* COMISS 0,d / JB: NaN continues */
                return 0;
        } else if (value >= 0.0f) {
            return 0;
        }
    }
    return 1;
}

void mu_pick_reset(mu_pick_state *pick)
{
    pick->nearest = 9999999.0f; /* 0x4b18967f */
}

static float client_fabs(float x)
{
    return 0.0f > x ? -x : x;
}

static float client_min(float a, float b)
{
    return a > b ? b : a;
}

static float client_max(float a, float b)
{
    return a > b ? a : b;
}

static float dot(const float a[3], const float b[3])
{
    float sum = a[0] * b[0];
    sum = sum + a[1] * b[1];
    sum = sum + a[2] * b[2];
    return sum;
}

/* Inside the segment's range on one axis: X >= min(o,t) and max(o,t) >= X
 * (COMISS/JB: a NaN fails both). */
static int within(float x, float o, float t)
{
    if (!(x >= client_min(o, t)))
        return 0;
    return client_max(o, t) >= x;
}

int mu_collision_line_face(mu_pick_state *pick, const float origin[3], const float target[3], int32_t n,
                           const float a[3], const float b[3], const float c[3], const float d[3],
                           const float normal[3], int store)
{
    float dir[3] = {target[0] - origin[0], target[1] - origin[1], target[2] - origin[2]};
    float denominator = dot(dir, normal);
    float t1 = dot(origin, normal);
    float t2 = dot(a, normal);
    float t = -(t1 - t2) / denominator;
    if (!(t >= 0.0f))
        return 0;
    if (!(pick->nearest >= t))
        return 0;
    float x[3];
    for (int i = 0; i < 3; ++i) {
        float product = dir[i] * t;
        x[i] = product + origin[i];
    }
    float a2 = client_fabs(dir[2]), a1 = client_fabs(dir[1]), a0 = client_fabs(dir[0]);
    float smallest = client_min(client_min(a0, a1), a2);
    int count = 0;
    if (smallest == client_fabs(dir[0])) {
        if (within(x[1], origin[1], target[1]) && within(x[2], origin[2], target[2]))
            ++count;
    } else if (smallest == client_fabs(dir[1])) {
        if (within(x[2], origin[2], target[2]) && within(x[0], origin[0], target[0]))
            ++count;
    } else {
        if (within(x[0], origin[0], target[0]) && within(x[1], origin[1], target[1]))
            ++count;
    }
    if (count == 0)
        return 0;
    int inside;
    if (-0.5f >= normal[0] || normal[0] >= 0.5f)
        inside = mu_inside_test(x[0], x[1], x[2], n, a, b, c, d, 1, normal[0]);
    else if (-0.5f >= normal[1] || normal[1] >= 0.5f)
        inside = mu_inside_test(x[0], x[1], x[2], n, a, b, c, d, 2, normal[1]);
    else
        inside = mu_inside_test(x[0], x[1], x[2], n, a, b, c, d, 4, normal[2]);
    if (!inside)
        return 0;
    if (store) {
        pick->nearest = t;
        memcpy(pick->collision, x, sizeof x);
    }
    return 1;
}

static int32_t terrain_index(int32_t x, int32_t y)
{
    return (int32_t)(((uint32_t)y << 8) + (uint32_t)x);
}

int mu_terrain_tile_pick(mu_pick_state *pick, const mu_client_view *view, const mu_terrain_heights *terrain,
                         float xf, float yf, int32_t xi, int32_t yi, float lodf, int32_t lodi,
                         uint8_t *select_flag, float *select_xf, float *select_yf)
{
    (void)lodf;
    int32_t index[4] = {terrain_index(xi, yi), terrain_index(xi + lodi, yi), terrain_index(xi + lodi, yi + lodi),
                        terrain_index(xi, yi + lodi)};
    float sx = xf * 100.0f, sy = yf * 100.0f;
    float v[4][3] = {{sx, sy, terrain->height[index[0]]},
                     {sx + 100.0f, sy, terrain->height[index[1]]},
                     {sx + 100.0f, sy + 100.0f, terrain->height[index[2]]},
                     {sx, sy + 100.0f, terrain->height[index[3]]}};
    for (int k = 0; k < 4; ++k)
        if (terrain->wall[index[k]] & 0x40)
            v[k][2] = terrain->water_height;
    float normal[3];
    mu_face_normalize(v[0], v[1], v[2], normal);
    int hit = mu_collision_line_face(pick, view->mouse_position, view->mouse_target, 3, v[0], v[1], v[2], v[3],
                                     normal, 1);
    if (!hit) {
        mu_face_normalize(v[0], v[2], v[3], normal);
        hit = mu_collision_line_face(pick, view->mouse_position, view->mouse_target, 3, v[0], v[2], v[3], v[1],
                                     normal, 1);
    }
    if (hit == 1) {
        *select_flag = 1;
        *select_xf = xf;
        *select_yf = yf;
    }
    return hit;
}

int mu_terrain_pick(mu_pick_state *pick, const mu_client_view *view, const mu_terrain_heights *terrain,
                    int32_t x0, int32_t y0, int32_t x1, int32_t y1, int32_t *tile_x, int32_t *tile_y)
{
    uint8_t flag = 0;
    float select_xf = 0, select_yf = 0;
    mu_pick_reset(pick);
    for (int32_t y = y0; y <= y1; ++y)
        for (int32_t x = x0; x <= x1; ++x)
            mu_terrain_tile_pick(pick, view, terrain, (float)x, (float)y, x, y, 1.0f, 1, &flag, &select_xf,
                                 &select_yf);
    if (!flag)
        return 0;
    /* 0x016a5063 re-tests the selected tile, then takes (int)(collision/100). */
    mu_terrain_tile_pick(pick, view, terrain, select_xf, select_yf, mu_cvtt(select_xf), mu_cvtt(select_yf), 1.0f, 1,
                         &flag, &select_xf, &select_yf);
    *tile_x = mu_cvtt(pick->collision[0] / 100.0f);
    *tile_y = mu_cvtt(pick->collision[1] / 100.0f);
    return 1;
}
