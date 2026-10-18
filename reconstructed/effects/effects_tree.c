/* Reconstructed effect layer above the particle system (NATIVE-FX-002): the
 * effect tree (children, parent transforms, parentduration), the owner (action
 * gate, visibility, tint), template instancing, bounding boxes and the
 * EffectManager's octree, frustum and render pass. See effects.h and
 * docs/research/client-effect-manager.md. Each function names the client
 * routine it mirrors; statements keep the client's binary32 operation order. */
#include "effects.h"
#include "effects_internal.h"

#include <stdlib.h>
#include <string.h>

const float MU_FX_OCTREE_ROOT[6] = {-12750.0f, -12750.0f, -25500.0f, 38250.0f, 38250.0f, 25500.0f};

/* ---- matrices ---- */

/* 0x00cf0db8: out = a * b (column-major), sums in index order. */
static void m_multiply(float out[16], const float a[16], const float b[16])
{
    float t[16];
    for (int c = 0; c < 4; ++c)
        for (int r = 0; r < 4; ++r) {
            float s = a[r] * b[4 * c];
            s = s + a[r + 4] * b[4 * c + 1];
            s = s + a[r + 8] * b[4 * c + 2];
            s = s + a[r + 12] * b[4 * c + 3];
            t[4 * c + r] = s;
        }
    memcpy(out, t, sizeof t);
}

/* 0x00cee51c: diagonal near 1, then every off-diagonal entry near 0. */
static int m_is_identity(const float m[16])
{
    static const int diagonal[4] = {0, 5, 10, 15};
    static const int other[12] = {1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14};
    for (int k = 0; k < 4; ++k)
        if (!near_equal(m[diagonal[k]], 1.0f))
            return 0;
    for (int k = 0; k < 12; ++k)
        if (!near_zero(m[other[k]]))
            return 0;
    return 1;
}

/* 0x00a76dfe */
void mu_fx_transform(mu_fx_effect *e, const float *external)
{
    mu_fx_update_transform(e);   /* local part: R * scale, position, world scale = scale */
    if (external && !m_is_identity(external)) {
        m_multiply(e->matrix, external, e->matrix);
    } else if (e->parent && !m_is_identity(e->parent->matrix)) {
        e->world_scale = e->parent->world_scale * e->world_scale;
        m_multiply(e->matrix, e->parent->matrix, e->matrix);
    }
    v3_set(e->world_position, e->matrix[12], e->matrix[13], e->matrix[14]);   /* 0x00cfcead */
}

/* ---- bounding boxes ---- */

/* 0x00ce7225: inner inside outer; comparisons as the client orders them. */
static int box_contains(const float outer[6], const float inner[6])
{
    if (outer[0] > inner[0] || inner[3] > outer[3])
        return 0;
    if (outer[1] > inner[1] || inner[4] > outer[4])
        return 0;
    if (outer[2] > inner[2] || inner[5] > outer[5])
        return 0;
    return 1;
}

/* 0x00cf2417: box through the matrix, accumulated per row from the translation. */
static void box_transform(float out[6], const float m[16], const float box[6])
{
    float lo[3] = {m[12], m[13], m[14]}, hi[3] = {m[12], m[13], m[14]};
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j) {
            float a = m[i + 4 * j] * box[j];
            float b = m[i + 4 * j] * box[3 + j];
            if (b > a) {
                lo[i] = lo[i] + a;
                hi[i] = hi[i] + b;
            } else {
                lo[i] = lo[i] + b;
                hi[i] = hi[i] + a;
            }
        }
    v3_copy(out, lo);
    v3_copy(out + 3, hi);
}

void mu_fx_bounding_box(mu_fx_effect *e)
{
    float *box = e->bbox;
    if (e->type == MU_FX_BILLBOARD) {                          /* 0x00a6ed9b */
        float d = e->width * e->width;
        d = d + e->height * e->height;
        float r = crt_sqrtf(d) * 0.5f;
        r = r * e->world_scale;
        const float *p = e->world_position;
        box[0] = p[0] - r; box[1] = p[1] - r; box[2] = p[2] - r;
        box[3] = p[0] + r; box[4] = p[1] + r; box[5] = p[2] + r;
        return;
    }
    /* 0x00a88970; the origin is the static zero vector 0x01ec7e3c in local space. */
    static const float zero[3] = {0.0f, 0.0f, 0.0f};
    const float *origin = e->space_is_local ? zero : e->world_position;
    v3_copy(box, origin);
    v3_copy(box + 3, origin);
    const float root2 = crt_sqrtf(2.0f);                       /* magic static 0x01d1e704 */
    for (uint32_t i = 0; i < e->count; ++i) {
        const mu_fx_particle *p = &e->particles[i];
        float r = p->size * 0.5f;
        r = r * root2;
        if (e->billboarding == MU_FX_BILLBOARD_DIRECTIONAL) {
            float l = v3_length(p->velocity) * e->speed_scale;
            l = l + e->length_scale;
            r = l * r;
        }
        for (int k = 0; k < 3; ++k) {
            if (box[k] > p->position[k] - r)
                box[k] = p->position[k] - r;
            if (p->position[k] + r > box[3 + k])
                box[3 + k] = p->position[k] + r;
        }
    }
    if (e->space_is_local) {
        float out[6];
        box_transform(out, e->matrix, box);
        memcpy(box, out, sizeof out);
    }
}

/* ---- node update ---- */

/* Owner action gate (0x00a7572b..0x00a75824). */
static void action_gate(mu_fx_effect *e, const mu_fx_owner *owner)
{
    if (e->action_count == 0 || !owner)
        return;
    int found = 0;
    for (uint32_t i = 0; i < e->action_count && !found; ++i)   /* std::find, int against the zero-extended action */
        found = e->actions[i] == (int32_t)owner->action;
    if (!found) {
        e->playing = 0;
        return;
    }
    if (e->start_frame >= 0.0f) {
        if (owner->frame >= e->start_frame && !e->playing)
            e->playing = 1;
    } else if (e->start_frame * -1.0f >= owner->frame && !e->playing) {
        e->playing = 1;
    }
}

int mu_fx_node_update(mu_fx_effect *e, float dt, const float *external, const mu_fx_owner *owner, mu_fx_rng *rng,
                      const mu_fx_terrain *terrain, mu_fx_octree_node *tree)
{
    if (e->faulted)
        return 0;
    mu_fx_transform(e, external);
    action_gate(e, owner);
    if (!mu_fxi_type_update(e, dt, rng, terrain))
        return 0;
    mu_fx_bounding_box(e);
    if (e->managed && tree) {
        if (e->cell && !box_contains(e->cell->bbox, e->bbox))
            mu_fx_octree_remove(e->cell, e);
        if (!e->cell)
            mu_fx_octree_insert(tree, e);
    }
    for (uint32_t i = 0; i < e->child_count; ++i)
        if (!mu_fx_node_update(e->children[i], dt, NULL, owner, rng, terrain, tree))
            return 0;
    return 1;
}

void mu_fx_set_owner(mu_fx_effect *e, const mu_fx_owner *owner)
{
    e->owner = owner;
    for (uint32_t i = 0; i < e->child_count; ++i)
        mu_fx_set_owner(e->children[i], owner);
}

uint32_t mu_fx_tree_count(const mu_fx_effect *e)
{
    uint32_t n = 1;
    for (uint32_t i = 0; i < e->child_count; ++i)
        n += mu_fx_tree_count(e->children[i]);
    return n;
}

mu_fx_effect *mu_fx_tree_node(mu_fx_effect *e, uint32_t index)
{
    if (index == 0)
        return e;
    index -= 1;
    for (uint32_t i = 0; i < e->child_count; ++i) {
        uint32_t n = mu_fx_tree_count(e->children[i]);
        if (index < n)
            return mu_fx_tree_node(e->children[i], index);
        index -= n;
    }
    return NULL;
}

/* ---- template instancing ---- */

static int dup(void **out, const void *in, size_t bytes)
{
    *out = NULL;
    if (!in || bytes == 0)
        return 1;
    *out = malloc(bytes);
    if (!*out)
        return 0;
    memcpy(*out, in, bytes);
    return 1;
}

#define DUP_KEYS(field, type) dup((void **)&o->field.keys, s->field.keys, (size_t)s->field.count * sizeof(type))

/* Deep copy of the parameters the type clones pass on (0x00a8986a for
 * particles, 0x00a6fb0a for billboards, each component's clone). */
static int copy_parameters(mu_fx_effect *o, const mu_fx_effect *s)
{
    *o = *s;
    o->particles = NULL;
    o->emitter.count_curve.keys = NULL; o->emitter.bursts = NULL;
    o->emitter.color.color.keys = NULL; o->emitter.color.alpha.keys = NULL; o->emitter.color.brightness.keys = NULL;
    o->emitter.lifetime.curve.keys = NULL; o->emitter.rotation.curve.keys = NULL;
    o->emitter.size.curve.keys = NULL; o->emitter.speed.curve.keys = NULL;
    o->color_lifetime.color.keys = NULL; o->color_lifetime.alpha.keys = NULL;
    for (int k = 0; k < 3; ++k) {
        o->force_lifetime.curve[k].keys = NULL;
        o->bb_force.curve[k].keys = NULL;
    }
    o->rotation_lifetime.curve.keys = NULL; o->size_lifetime.curve.keys = NULL; o->speed_lifetime.curve.keys = NULL;
    o->texcoord.tiles.keys = NULL;
    o->bb_color.color.keys = NULL; o->bb_color.alpha.keys = NULL; o->bb_rotation.curve.keys = NULL;
    o->bb_size.curve.keys = NULL; o->bb_texcoord.tiles.keys = NULL;
    o->children = NULL; o->child_count = o->child_capacity = 0;
    o->actions = NULL; o->action_count = 0;
    int ok = 1;
    if (s->capacity) {
        o->particles = calloc(s->capacity, sizeof *o->particles);
        ok = o->particles != NULL;
    }
    ok = ok && DUP_KEYS(emitter.count_curve, mu_fx_curve_key) &&
         dup((void **)&o->emitter.bursts, s->emitter.bursts, (size_t)s->emitter.burst_count * sizeof(mu_fx_burst)) &&
         DUP_KEYS(emitter.color.color, mu_fx_grad3_key) && DUP_KEYS(emitter.color.alpha, mu_fx_grad1_key) &&
         DUP_KEYS(emitter.color.brightness, mu_fx_grad1_key) && DUP_KEYS(emitter.lifetime.curve, mu_fx_curve_key) &&
         DUP_KEYS(emitter.rotation.curve, mu_fx_curve_key) && DUP_KEYS(emitter.size.curve, mu_fx_curve_key) &&
         DUP_KEYS(emitter.speed.curve, mu_fx_curve_key) && DUP_KEYS(color_lifetime.color, mu_fx_grad3_key) &&
         DUP_KEYS(color_lifetime.alpha, mu_fx_grad1_key) && DUP_KEYS(force_lifetime.curve[0], mu_fx_curve_key) &&
         DUP_KEYS(force_lifetime.curve[1], mu_fx_curve_key) && DUP_KEYS(force_lifetime.curve[2], mu_fx_curve_key) &&
         DUP_KEYS(bb_force.curve[0], mu_fx_curve_key) && DUP_KEYS(bb_force.curve[1], mu_fx_curve_key) &&
         DUP_KEYS(bb_force.curve[2], mu_fx_curve_key) && DUP_KEYS(rotation_lifetime.curve, mu_fx_curve_key) &&
         DUP_KEYS(size_lifetime.curve, mu_fx_curve_key) && DUP_KEYS(speed_lifetime.curve, mu_fx_curve_key) &&
         DUP_KEYS(texcoord.tiles, mu_fx_curve_key) && DUP_KEYS(bb_color.color, mu_fx_grad3_key) &&
         DUP_KEYS(bb_color.alpha, mu_fx_grad1_key) && DUP_KEYS(bb_rotation.curve, mu_fx_curve_key) &&
         DUP_KEYS(bb_size.curve, mu_fx_curve_key) && DUP_KEYS(bb_texcoord.tiles, mu_fx_curve_key);
    return ok;
}

static int clone_node(mu_fx_effect *o, const mu_fx_effect *s, const float position[3], const float rotation[3],
                      float scale, int owner_tint, const int32_t *actions, uint32_t action_count, float start)
{
    if (!copy_parameters(o, s)) {
        mu_fx_free(o);
        return 0;
    }
    /* Constructor state (base 0x00a76b51, particles 0x00a8a436, billboard 0x00a6fea9). */
    v3_copy(o->position, position);
    v3_copy(o->rotation, rotation);
    o->scale = scale;
    o->world_scale = scale;
    o->parent = NULL;
    o->cell = NULL;
    o->owner = NULL;
    o->playing = 1;
    o->drawn = 0;
    o->faulted = 0;
    o->count = 0;
    o->time_left = o->duration;
    memset(o->bbox, 0, sizeof o->bbox);
    if (o->emitter.present) {   /* emitter constructor 0x00a81787 (its clone 0x00a80633 constructs anew) */
        o->emitter.delay_left = o->emitter.delay;
        o->emitter.accumulated = 0.0f;
        if (o->emitter.frequency == 0)
            o->emitter.frequency = 1;   /* so instances never reach the rand() % 0 of a loaded template */
    }
    mu_fx_update_transform(o);
    /* 0x00a75934 */
    if (action_count) {
        o->actions = malloc(action_count * sizeof *o->actions);
        if (!o->actions) {
            mu_fx_free(o);
            return 0;
        }
        memcpy(o->actions, actions, action_count * sizeof *o->actions);
        o->action_count = action_count;
    }
    o->start_frame = start;
    o->owner_tint = (uint8_t)(owner_tint != 0);
    if (s->child_count) {
        o->children = calloc(s->child_count, sizeof *o->children);
        if (!o->children) {
            mu_fx_free(o);
            return 0;
        }
        o->child_capacity = s->child_count;
    }
    for (uint32_t i = 0; i < s->child_count; ++i) {
        const mu_fx_effect *c = s->children[i];
        mu_fx_effect *n = calloc(1, sizeof *n);
        if (!n || !clone_node(n, c, c->position, c->rotation, c->scale, owner_tint, actions, action_count, start)) {
            free(n);
            mu_fx_free(o);
            return 0;
        }
        n->parent = o;
        o->children[o->child_count++] = n;
    }
    return 1;
}

int mu_fx_clone(mu_fx_effect *out, const mu_fx_effect *source, const float position[3], const float rotation[3],
                float scale, int owner_tint, const int32_t *actions, uint32_t action_count, float start_frame)
{
    return clone_node(out, source, position, rotation, scale, owner_tint, actions, action_count, start_frame);
}

/* ---- frustum ---- */

/* 0x00a8de01 -> 0x00cf65af: plane (n, d) scaled by 1 / |n|; (1, 0, 0, 0) when |n|^2 is near zero. */
static void plane_set(float plane[4], const float n[3], float d)
{
    float l = n[0] * n[0];
    l = l + n[1] * n[1];
    l = l + n[2] * n[2];
    if (near_zero(l)) {
        plane[0] = 1.0f; plane[1] = 0.0f; plane[2] = 0.0f; plane[3] = 0.0f;
        return;
    }
    float inverse = 1.0f / crt_sqrtf(l);
    plane[0] = n[0] * inverse;
    plane[1] = n[1] * inverse;
    plane[2] = n[2] * inverse;
    plane[3] = d * inverse;
}

/* 0x00cf66a4: plane through three points; the edge vectors are normalised
 * before the cross product and the normal after it. */
static void plane_from_points(float plane[4], const float a[3], const float b[3], const float c[3])
{
    float u[3], v[3], n[3];
    v3_sub(u, b, a);
    v3_sub(v, c, a);
    v3_normalize(u);
    v3_normalize(v);
    v3_cross(n, u, v);
    v3_normalize(n);
    v3_copy(plane, n);
    plane[3] = -v3_dot(n, a);
}

void mu_fx_frustum_set(mu_fx_frustum *f, const float eye[3], const float forward[3], const float up[3], float fov,
                       float aspect, float near_plane, float far_plane)
{
    mu_fx_camera *c = &f->camera;
    v3_copy(c->position, eye);
    v3_copy(c->forward, forward);
    v3_copy(c->up, up);
    v3_cross(c->right, c->forward, c->up);
    float half_height = (float)tan((double)(fov / 2.0f)) * far_plane;   /* CRT tan through 0x00a0cf72 */
    float half_width = half_height * aspect;
    float t[3], u[3], r[3], top_left[3], bottom_left[3], top_right[3], bottom_right[3];
    v3_scale(u, c->up, half_height);
    v3_scale(r, c->right, -half_width);
    v3_scale(t, c->forward, far_plane);
    v3_add(t, t, c->position);
    v3_add(t, t, r);
    v3_add(top_left, t, u);
    v3_scale(u, c->up, half_height * 2.0f);
    v3_sub(bottom_left, top_left, u);
    v3_scale(r, c->right, half_width * 2.0f);
    v3_add(top_right, top_left, r);
    v3_sub(bottom_right, top_right, u);
    float d = v3_dot(c->forward, c->position);
    plane_set(f->planes[0], c->forward, -d - near_plane);
    float back[3];
    v3_set(back, -c->forward[0], -c->forward[1], -c->forward[2]);   /* 0x00cfca12 negation */
    plane_set(f->planes[1], back, d + far_plane);
    plane_from_points(f->planes[2], c->position, bottom_left, top_left);
    plane_from_points(f->planes[3], c->position, top_left, top_right);
    plane_from_points(f->planes[4], c->position, top_right, bottom_right);
    plane_from_points(f->planes[5], c->position, bottom_right, bottom_left);
}

int mu_fx_frustum_sphere(const mu_fx_frustum *f, const float center[3], float radius_squared)
{
    for (int i = 0; i < 6; ++i) {
        float d = v3_dot(f->planes[i], center) + f->planes[i][3];   /* 0x00a8de49 */
        if (0.0f > d && d * d > radius_squared)
            return 0;
    }
    return 1;
}

/* ---- octree ---- */

mu_fx_octree_node *mu_fx_octree_create(const float bbox[6], uint32_t depth)
{
    mu_fx_octree_node *n = calloc(1, sizeof *n);
    if (n) {
        memcpy(n->bbox, bbox, sizeof n->bbox);
        n->depth = depth;
    }
    return n;
}

void mu_fx_octree_free(mu_fx_octree_node *n)
{
    if (!n)
        return;
    for (int i = 0; i < 8; ++i)
        mu_fx_octree_free(n->child[i]);
    for (uint32_t i = 0; i < n->count; ++i)
        if (n->items[i]->cell == n)
            n->items[i]->cell = NULL;
    free(n->items);
    free(n);
}

/* 0x00a8f249: box centre (min + max) / 2. */
static void box_center(float out[3], const float box[6])
{
    float s[3];
    v3_add(s, box, box + 3);
    out[0] = s[0] / 2.0f;
    out[1] = s[1] / 2.0f;
    out[2] = s[2] / 2.0f;
}

/* 0x00ce7121: squared half diagonal. */
static float box_radius_squared(const float box[6])
{
    float x = (box[3] - box[0]) / 2.0f;
    float y = (box[4] - box[1]) / 2.0f;
    float z = (box[5] - box[2]) / 2.0f;
    float s = x * x;
    s = s + y * y;
    s = s + z * z;
    return s;
}

void mu_fx_octree_remove(mu_fx_octree_node *n, mu_fx_effect *e)
{
    for (uint32_t i = 0; i < n->count; ++i)
        if (n->items[i] == e) {
            memmove(n->items + i, n->items + i + 1, (n->count - i - 1) * sizeof *n->items);
            n->count--;
            e->cell = NULL;
            return;
        }
}

int mu_fx_octree_insert(mu_fx_octree_node *n, mu_fx_effect *e)
{
    if (!box_contains(n->bbox, e->bbox))
        return 0;
    if (n->depth < 6) {
        float c[3], ec[3];
        box_center(c, n->bbox);
        box_center(ec, e->bbox);
        int bx = c[0] < ec[0], by = ec[1] < c[1], bz = c[2] < ec[2];
        int index = bx + bz * 2 + by * 4;
        if (n->child[index]) {
            if (mu_fx_octree_insert(n->child[index], e))
                return 1;
        } else {
            float eighth = (n->bbox[3] - n->bbox[0]) / 8.0f;
            float quarter = (n->bbox[3] - n->bbox[0]) / 4.0f;
            c[0] = c[0] + (bx ? eighth : -eighth);
            c[1] = c[1] + (by ? -eighth : eighth);
            c[2] = c[2] + (bz ? eighth : -eighth);
            float box[6];
            box[3] = c[0] + quarter; box[4] = c[1] + quarter; box[5] = c[2] + quarter;
            box[0] = c[0] - quarter; box[1] = c[1] - quarter; box[2] = c[2] - quarter;
            if (box_contains(box, e->bbox)) {
                n->child[index] = mu_fx_octree_create(box, n->depth + 1);
                if (n->child[index] && mu_fx_octree_insert(n->child[index], e))
                    return 1;
            }
        }
    }
    if (e->cell)
        mu_fx_octree_remove(e->cell, e);
    if (n->count == n->capacity) {
        uint32_t capacity = n->capacity ? 2u * n->capacity : 8u;
        mu_fx_effect **grown = realloc(n->items, capacity * sizeof *grown);
        if (!grown)
            return 0;
        n->items = grown;
        n->capacity = capacity;
    }
    n->items[n->count++] = e;   /* std::list push_back */
    e->cell = n;
    return 1;
}

static void query(const mu_fx_octree_node *n, const mu_fx_frustum *f, mu_fx_effect **out, uint32_t capacity,
                  uint32_t *found)
{
    float c[3];
    box_center(c, n->bbox);
    if (!mu_fx_frustum_sphere(f, c, box_radius_squared(n->bbox)))
        return;
    for (uint32_t i = 0; i < n->count; ++i) {
        mu_fx_effect *e = n->items[i];
        box_center(c, e->bbox);
        if (mu_fx_frustum_sphere(f, c, box_radius_squared(e->bbox))) {
            if (*found < capacity)
                out[*found] = e;
            (*found)++;
        }
    }
    for (int i = 0; i < 8; ++i)
        if (n->child[i])
            query(n->child[i], f, out, capacity, found);
}

uint32_t mu_fx_octree_query(const mu_fx_octree_node *n, const mu_fx_frustum *f, mu_fx_effect **out, uint32_t capacity)
{
    uint32_t found = 0;
    if (n)
        query(n, f, out, capacity, &found);
    return found;
}

/* ---- EffectManager render 0x00a7a30e ---- */

uint32_t mu_fx_manager_render_calls(const mu_fx_gl_state *s, uint32_t visible, mu_fx_gl_call out[24])
{
    enum { GL_ALPHA_TEST = 0x0bc0, GL_TEXTURE_2D = 0x0de1, GL_BLEND = 0x0be2, GL_BLEND_SRC = 0x0be1,
           GL_BLEND_DST = 0x0be0, GL_DEPTH_WRITEMASK = 0x0b72 };
    uint32_t n = 0;
#define CALL(o, x, y) (out[n].op = (o), out[n].a = (x), out[n].b = (y), n++)
    if (visible == 0)
        return 0;
    CALL(MU_FX_GL_GET_BOOLEAN, GL_ALPHA_TEST, 0);
    CALL(MU_FX_GL_GET_BOOLEAN, GL_TEXTURE_2D, 0);
    CALL(MU_FX_GL_GET_BOOLEAN, GL_BLEND, 0);
    CALL(MU_FX_GL_GET_INTEGER, GL_BLEND_SRC, 0);
    CALL(MU_FX_GL_GET_INTEGER, GL_BLEND_DST, 0);
    CALL(MU_FX_GL_GET_BOOLEAN, GL_DEPTH_WRITEMASK, 0);
    if (s->depth_mask)
        CALL(MU_FX_GL_DEPTH_MASK, 0, 0);
    if (s->alpha_test)
        CALL(MU_FX_GL_DISABLE, GL_ALPHA_TEST, 0);
    CALL(MU_FX_GL_DRAW_EFFECTS, visible, 0);
    CALL(MU_FX_GL_BIND_TEXTURE, GL_TEXTURE_2D, 0);
    CALL(s->texture_2d ? MU_FX_GL_ENABLE : MU_FX_GL_DISABLE, GL_TEXTURE_2D, 0);
    CALL(MU_FX_GL_BLEND_FUNC, s->blend_src, s->blend_dst);
    CALL(s->blend ? MU_FX_GL_ENABLE : MU_FX_GL_DISABLE, GL_BLEND, 0);
    if (s->depth_mask)
        CALL(MU_FX_GL_DEPTH_MASK, 1, 0);
    if (s->alpha_test)
        CALL(MU_FX_GL_ENABLE, GL_ALPHA_TEST, 0);
#undef CALL
    return n;
}

/* ---- effect texture upload 0x00a90987 ---- */

uint32_t mu_fx_texture_upload_calls(int has_pixels, int32_t width, int32_t height, uint32_t format, uint32_t filter,
                                    uint32_t wrap, int mipmap, mu_fx_gl_call out[12])
{
    enum { GL_TEXTURE_2D = 0x0de1, GL_TEXTURE_MAG_FILTER = 0x2800, GL_TEXTURE_MIN_FILTER = 0x2801,
           GL_TEXTURE_WRAP_S = 0x2802, GL_TEXTURE_WRAP_T = 0x2803, GL_TEXTURE_ENV = 0x2300,
           GL_TEXTURE_ENV_MODE = 0x2200, GL_MODULATE = 0x2100, GL_LINEAR = 0x2601,
           GL_LINEAR_MIPMAP_NEAREST = 0x2701, GL_NEAREST_MIPMAP_NEAREST = 0x2700 };
    uint32_t n = 0;
#define CALL(o, x, y) (out[n].op = (o), out[n].a = (x), out[n].b = (y), n++)
    if (!has_pixels || width == 0 || height == 0)
        return 0;
    CALL(MU_FX_GL_GEN_TEXTURES, 1, 0);
    CALL(MU_FX_GL_BIND_TEXTURE, GL_TEXTURE_2D, MU_FX_GL_NEW_TEXTURE);
    CALL(MU_FX_GL_TEX_PARAMETER, GL_TEXTURE_WRAP_S, wrap);
    CALL(MU_FX_GL_TEX_PARAMETER, GL_TEXTURE_WRAP_T, wrap);
    CALL(MU_FX_GL_TEX_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
    if (mipmap) {
        CALL(MU_FX_GL_TEX_PARAMETER, GL_TEXTURE_MIN_FILTER,
             filter == GL_LINEAR ? GL_LINEAR_MIPMAP_NEAREST : GL_NEAREST_MIPMAP_NEAREST);
        CALL(MU_FX_GL_TEX_PARAMETER, GL_TEXTURE_MAG_FILTER, filter);
        CALL(MU_FX_GL_BUILD_MIPMAPS, (uint32_t)width, (uint32_t)height);
    } else {
        CALL(MU_FX_GL_TEX_PARAMETER, GL_TEXTURE_MIN_FILTER, filter);
        CALL(MU_FX_GL_TEX_PARAMETER, GL_TEXTURE_MAG_FILTER, filter);
        CALL(MU_FX_GL_TEX_IMAGE, (uint32_t)width, (uint32_t)height);
    }
    (void)format;
#undef CALL
    return n;
}
