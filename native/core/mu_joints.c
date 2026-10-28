/* The client's joint pool in the native session (NATIVE-JOINT-001). See mu_joints.h. */
#include "mu_joints.h"

#include <string.h>

int32_t mu_joints_create(mu_jt_joint *pool, int32_t count, int32_t type, const float position[3],
                         const float target_position[3], const float angle[3], int32_t subtype, int32_t target,
                         float scale, uint16_t key, uint16_t skill, uint8_t byte10, uint16_t word13, int32_t arg14,
                         const mu_jt_env *env)
{
    for (int32_t i = 0; i < count; ++i) {
        mu_jt_joint *j = &pool[i];
        if (j->live)
            continue;   /* 0x0153b09e */
        if (!mu_jt_create(j, type, position, target_position, angle, subtype, target, scale, key, skill, byte10,
                          word13, arg14, env)) {
            j->live = 0;   /* not reconstructed: released (native choice) */
            return -2;
        }
        return i;
    }
    return -1;
}

int32_t mu_joints_move_all(mu_jt_joint *pool, int32_t count, const mu_jt_env *env, float time_step,
                           mu_joints_inputs_fn inputs, void *inputs_context)
{
    int32_t moved = 0;
    for (int32_t i = 0; i < count; ++i) {
        mu_jt_joint *j = &pool[i];
        if (!j->live)
            continue;
        mu_jt_move_inputs in = {time_step, 0, 0, i, 0};
        if (inputs)
            inputs(inputs_context, j, &in);
        in.time_step = time_step;
        in.index = i;
        if (!mu_jt_move(j, env, &in)) {
            j->live = 0;
            continue;
        }
        ++moved;
    }
    return moved;
}

typedef struct quad_sink {
    mu_joint_quad *quads;
    int32_t max, count, corner;
    float color[3];
    int32_t bitmap;
    uint8_t render_type;
    mu_joint_quad current;
} quad_sink;

static void q_color(void *c, float r, float g, float b)
{
    quad_sink *q = c;
    q->color[0] = r;
    q->color[1] = g;
    q->color[2] = b;
}

static void q_bind(void *c, int32_t bitmap)
{
    ((quad_sink *)c)->bitmap = bitmap;
}

static void q_begin(void *c, int32_t mode)
{
    (void)mode;
    ((quad_sink *)c)->corner = 0;
}

static void q_tex(void *c, float u, float v)
{
    quad_sink *q = c;
    if (q->corner < 4) {
        q->current.uv[q->corner][0] = u;
        q->current.uv[q->corner][1] = v;
    }
}

static void q_vertex(void *c, const float v[3])
{
    quad_sink *q = c;
    if (q->corner < 4)
        memcpy(q->current.position[q->corner], v, sizeof q->current.position[0]);
    q->corner++;
}

static void q_end(void *c)
{
    quad_sink *q = c;
    if (q->corner != 4 || q->count >= q->max)
        return;
    mu_joint_quad *out = &q->quads[q->count++];
    *out = q->current;
    memcpy(out->color, q->color, sizeof out->color);
    out->bitmap = q->bitmap;
    out->render_type = q->render_type;
}

int32_t mu_joints_quads(const mu_jt_joint *pool, int32_t count, uint8_t mode, float world_time, mu_joint_quad *quads,
                        int32_t max)
{
    quad_sink q;
    memset(&q, 0, sizeof q);
    q.quads = quads;
    q.max = max;
    q.color[0] = q.color[1] = q.color[2] = 1.0f;
    const mu_jt_gl gl = {&q, NULL, q_bind, q_color, q_begin, q_tex, q_vertex, q_end};
    for (int32_t i = 0; i < count && q.count < max; ++i) {
        q.render_type = pool[i].render_type;
        mu_jt_render(&pool[i], mode, world_time, &gl);
    }
    return q.count;
}

void mu_joints_state(uint8_t render_type, mu_meshdraw_state *s)
{
    s->blend = 1;
    s->cull = 0;
    s->texture = 1;
    switch (render_type) {
    case 2:   /* EnableAlphaTest(1) */
        s->src = MU_GL_SRC_ALPHA;
        s->dst = MU_GL_ONE_MINUS_SRC_ALPHA;
        s->depth_mask = 1;
        s->alpha_test = 1;
        break;
    case 3:   /* EnableAlphaBlendMinus */
        s->src = MU_GL_ZERO;
        s->dst = MU_GL_ONE_MINUS_SRC_COLOR;
        s->depth_mask = 0;
        s->alpha_test = 0;
        break;
    case 4:   /* 0x0184ab46 */
        s->src = MU_GL_ONE_MINUS_SRC_COLOR;
        s->dst = MU_GL_ONE;
        s->depth_mask = 0;
        s->alpha_test = 0;
        break;
    default:  /* 1: EnableAlphaBlend (ONE, ONE) */
        s->src = MU_GL_ONE;
        s->dst = MU_GL_ONE;
        s->depth_mask = 0;
        s->alpha_test = 0;
        break;
    }
}

int32_t mu_joints_live(const mu_jt_joint *pool, int32_t count)
{
    int32_t n = 0;
    for (int32_t i = 0; i < count; ++i)
        n += pool[i].live != 0;
    return n;
}
