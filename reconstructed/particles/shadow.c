/* RenderBodyShadow 0x012bc07a and the bone helpers (NATIVE-PARTICLE-001). */
#include <string.h>

#include "particles.h"
#include "particles_internal.h"
#include "../record-math/record_math.h"

static int16_t rd16(const uint8_t *p)
{
    return (int16_t)(uint16_t)(p[0] | (p[1] << 8));
}

int32_t mu_pt_render_body_shadow(const mu_pt_shadow_mesh *meshes, int32_t mesh_count, const float origin[3],
                                 int32_t hide_texture, int32_t hide_mesh, int32_t first_mesh, int32_t end_mesh,
                                 int32_t z_offset, const mu_pt_host *h, const mu_pt_gl *gl)
{
    if (mesh_count == 0)
        return 0;
    /* 0x0184a783(0): depth mask on (0x0184a743), alpha test off, texture off; then depth mask off (0x0184a763) */
    if (gl) {
        if (gl->state) {
            gl->state(gl->context, MU_PT_STATE_UNTEXTURED, 0);
            gl->state(gl->context, MU_PT_STATE_DEPTH_OFF, 0);
        }
        if (gl->push_matrix)
            gl->push_matrix(gl->context);   /* 0x012b7e53(1.0) */
    }
    int32_t start = 0, end = mesh_count;
    if (first_mesh != -1)
        start = first_mesh;
    if (end_mesh != -1)
        end = end_mesh;
    float k1 = 2000.0f;
    const float k2 = 4000.0f;
    const int32_t world = h ? h->world : 0;
    if (world == 0x1e)   /* 0x0095fb7c */
        k1 = 2500.0f;
    int32_t sent = 0;
    for (int32_t i = start; i < end; ++i) {
        if (i == hide_mesh)
            continue;
        if (i < 0 || i >= mesh_count)
            continue;   /* the client reads past the mesh array; the C refuses */
        const mu_pt_shadow_mesh *m = &meshes[i];
        if (m->triangle_count <= 0 || m->texture == hide_texture)
            continue;
        if (gl && gl->begin)
            gl->begin(gl->context, MU_PT_GL_TRIANGLES);
        for (int32_t t = 0; t < m->triangle_count; ++t) {
            const uint8_t *tri = m->triangles + 0x24 * t;
            const int32_t corners = (int8_t)tri[0];
            for (int32_t c = 0; c < corners; ++c) {
                const int32_t vi = rd16(tri + 2 + 2 * c);
                float v[3] = {0.0f, 0.0f, 0.0f};
                const float *src = (vi >= 0 && vi < m->vertex_count) ? m->vertices + 3 * vi : v;
                v[0] = src[0] - origin[0];
                v[1] = src[1] - origin[1];
                v[2] = src[2] - origin[2];
                v[0] = (v[0] + k1) * v[2] / (v[2] - k2) + v[0];
                v[2] = 5.0f;
                v[0] = v[0] + origin[0];
                v[1] = v[1] + origin[1];
                v[2] = v[2] + origin[2];
                float ground = h && h->terrain_height ? h->terrain_height(h->context, v[0], v[1]) : 0.0f;
                v[2] = ground + 2.0f;
                v[2] = (float)z_offset + v[2];
                if (world == 0x91) {   /* 0x00d79e40: no terrain, z 10 above the origin */
                    v[0] = src[0] - origin[0];
                    v[1] = src[1] - origin[1];
                    v[2] = src[2] - origin[2];
                    v[0] = (v[0] + k1) * v[2] / (v[2] - k2) + v[0];
                    v[2] = 10.0f;
                    v[0] = v[0] + origin[0];
                    v[1] = v[1] + origin[1];
                    v[2] = v[2] + origin[2];
                    v[2] = (float)z_offset + v[2];
                }
                if (gl && gl->vertex)
                    gl->vertex(gl->context, v);
                sent++;
            }
        }
        if (gl && gl->end)
            gl->end(gl->context);
    }
    if (gl) {
        if (gl->pop_matrix)
            gl->pop_matrix(gl->context);   /* 0x012b7e65 */
        if (gl->state)
            gl->state(gl->context, MU_PT_STATE_DEPTH_ON, 0);
    }
    return sent;
}

int32_t mu_pt_find_bone(const char *const *names, int32_t bone_count, const char *name)
{
    if (!names || !name)
        return -1;
    for (int32_t i = 0; i < bone_count; ++i)
        if (names[i] && strcmp(names[i], name) == 0)
            return i;
    return -1;
}

void mu_pt_transform_position(const float matrix[12], const float in[3], float out[3], int translate,
                              float body_scale, const float body_origin[3])
{
    if (!matrix)
        return;
    if (!translate) {
        mu_vector_transform(in, matrix, out);
        return;
    }
    float t[3];
    mu_vector_transform(in, matrix, t);
    for (int k = 0; k < 3; ++k)
        t[k] = body_scale * t[k];
    for (int k = 0; k < 3; ++k)
        out[k] = t[k] + body_origin[k];
}
