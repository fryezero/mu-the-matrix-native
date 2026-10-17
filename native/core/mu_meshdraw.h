#ifndef MU_MESHDRAW_H
#define MU_MESHDRAW_H

#include <stdint.h>

/* Platform-neutral port of the client's mesh draw 0x012b8d1d (ret 0x2c,
 * body to 0x012bb35a), its body loop 0x012bb35a (ret 0x2c), the cached GL
 * state wrappers 0x0184a6b7..0x0184acf6 it calls, and the per-mesh texcoord
 * table it writes at 0x072acfd8.
 *
 * Every rule here was read from the instructions and is compared, call for
 * call and bit for bit, with the actual routine executed under Unicorn
 * (scripts/validate_meshdraw.py; docs/research/client-meshdraw-exec.md).
 * The port emits the literal GL call stream through mu_gl_sink: every
 * glEnable/glDisable/glBlendFunc/glDepthMask/glBindTexture the wrappers issue
 * when their caches change, glColor3f/glColor3fv/glColor4f, glBegin(GL_TRIANGLES),
 * glTexCoord2f, glVertex3fv, glEnd, and glPushMatrix/glPopMatrix from the body.
 *
 * Differences from the client, all authored conventions:
 *  - explicit host pointers instead of client addresses (vertex, normal and
 *    light arrays per mesh, scratch for the 0x089c2120 colour table and the
 *    0x072acfd8 texcoord table);
 *  - a mesh whose indices fall outside the supplied counts (or that has more
 *    than MU_MESHDRAW_MAX_ENTRIES normals) is refused before any call; the
 *    client bounds nothing;
 *  - the bitmap lookup 0x00c97c2d / 0x00ebbec8 is a caller callback.
 * The client's trig (0x009fa20d cos, 0x00968117/0x009681bd sin) and pow
 * (0x009f4218) round a binary64 result to binary32; the port does the same
 * with the host libm (equal in every executed comparison). Build with
 * -ffp-contract=off. */

#define MU_MESHDRAW_MAX_ENTRIES 15000
#define MU_MESHDRAW_ALPHA_THRESHOLD 0.99f /* binary32 at 0x01a82fe0 */

/* GL enums the routine uses. */
enum {
    MU_GL_TRIANGLES = 4,
    MU_GL_ZERO = 0, MU_GL_ONE = 1, MU_GL_SRC_COLOR = 0x300, MU_GL_ONE_MINUS_SRC_COLOR = 0x301,
    MU_GL_SRC_ALPHA = 0x302, MU_GL_ONE_MINUS_SRC_ALPHA = 0x303,
    MU_GL_CULL_FACE = 0xb44, MU_GL_FOG = 0xb60, MU_GL_DEPTH_TEST = 0xb71, MU_GL_ALPHA_TEST = 0xbc0,
    MU_GL_BLEND = 0xbe2, MU_GL_TEXTURE_2D = 0xde1
};

/* One recorded GL call. Float arguments are carried as their binary32 bits. */
enum {
    MU_GL_OP_BEGIN = 1,        /* w0 mode */
    MU_GL_OP_END = 2,
    MU_GL_OP_TEXCOORD2F = 3,   /* s, t */
    MU_GL_OP_COLOR3F = 4,      /* r, g, b */
    MU_GL_OP_COLOR3FV = 5,     /* r, g, b (the pointed values at call time) */
    MU_GL_OP_COLOR4F = 6,      /* r, g, b, a */
    MU_GL_OP_VERTEX3FV = 7,    /* x, y, z */
    MU_GL_OP_ENABLE = 8,       /* cap */
    MU_GL_OP_DISABLE = 9,      /* cap */
    MU_GL_OP_BLEND_FUNC = 10,  /* sfactor, dfactor */
    MU_GL_OP_DEPTH_MASK = 11,  /* flag */
    MU_GL_OP_BIND_TEXTURE = 12,/* target, name */
    MU_GL_OP_PUSH_MATRIX = 13,
    MU_GL_OP_POP_MATRIX = 14
};

typedef struct mu_gl_sink {
    void *context;
    void (*call)(void *context, uint32_t op, const uint32_t words[4]);
} mu_gl_sink;

/* The client's GL state caches (globals read and written by the wrappers). */
typedef struct mu_gl_cache {
    uint8_t depth_test;   /* 0x0bdc597e */
    uint8_t cull;         /* 0x0bdc597f */
    uint8_t depth_mask;   /* 0x0bdc5980 */
    uint8_t alpha_test;   /* 0x0bdc58b5 */
    uint8_t texture;      /* 0x0bdc597d (GL_TEXTURE_2D) */
    uint8_t fog;          /* 0x0bdc597c fog setting (only read) */
    int32_t blend;        /* 0x0bdc58c4: 0 off, 1..8 blend wrapper id */
    int32_t bound;        /* 0x01cf1620: last bound bitmap index */
} mu_gl_cache;

/* State after the client's scene setup 0x0184adc7 (0x0184afe1..0x0184b031):
 * alpha test off, texture/depth/cull/depth mask on, blend cache untouched. */
void mu_gl_cache_scene_defaults(mu_gl_cache *cache);

/* Bitmap record fields the routine reads (record +0x204, +0x208, +0x214,
 * +0x215, +0x21a). */
typedef struct mu_bitmap {
    float width, height;      /* +0x204, +0x208 (power-of-two upload size) */
    int8_t components;        /* +0x214: 3 JPEG, 4 TGA */
    uint32_t name;            /* +0x215: GL texture object */
    const uint8_t *pixels;    /* +0x21a (mode 0x8000 reads one byte per corner) */
    uint32_t pixel_bytes;     /* bound for the port's check */
} mu_bitmap;

typedef const mu_bitmap *(*mu_bitmap_lookup)(void *context, int32_t index);

typedef struct mu_meshdraw_mesh {
    uint8_t flag;                  /* mesh +0x00: nonzero skips the environment group */
    int16_t texture_slot;          /* mesh +0x02 */
    int16_t normal_count;          /* mesh +0x06 */
    int16_t triangle_count;        /* mesh +0x0a */
    const float *texcoords;        /* mesh +0x14: two floats per texcoord */
    const uint8_t *triangles;      /* mesh +0x18: 0x24-byte records */
    const uint8_t *sub;            /* mesh +0x1c: five flag bytes, or NULL */
    int32_t vertex_count, texcoord_count;  /* for the port's index check */
    const float *vertices;         /* transform output (vertices arg + mesh*0x2bf20) */
    const float *normals;          /* normals arg + mesh*0x2bf20 */
    const float *lights;           /* lights arg + mesh*0xea60 */
    const float *secondary;        /* 0x075a9ee8 + mesh*0xea60 */
} mu_meshdraw_mesh;

typedef struct mu_meshdraw_model {
    int16_t mesh_count;            /* +0x24 */
    const mu_meshdraw_mesh *meshes;/* +0x28 */
    const int32_t *texture_index;  /* +0x38, by texture slot */
    const int32_t *texture_type;   /* +0x3c, by texture slot */
    int32_t texture_count;         /* for the port's slot check */
    int32_t hide_typed;            /* +0x40: > 0 skips meshes whose type is 1 or 2 */
    float alt_color[3];            /* +0x44 */
    uint8_t lighting;              /* +0x50 */
    float color[3];                /* +0x54: read and written */
    float origin[3];               /* +0x78 */
    int8_t light_mesh;             /* +0x94 */
    int8_t skin_shift;             /* +0xa4 */
    uint8_t flag_a5, flag_a6;      /* +0xa5, +0xa6 */
    uint8_t alt_on_skin;           /* +0xca */
    uint8_t secondary_light;       /* +0xcb */
} mu_meshdraw_model;

/* Globals the routine reads. */
typedef struct mu_meshdraw_globals {
    float time;                    /* 0x06fce370 */
    float env_vector[3];           /* 0x0a381de0 (flag 0x800) */
    int32_t skin_base;             /* 0x0b6b53e0 (texture 0x76f8) */
} mu_meshdraw_globals;

typedef struct mu_meshdraw_args {
    uint32_t flags;                /* [ebp+0x0c] */
    float alpha;                   /* [ebp+0x1c] */
    int32_t select;                /* [ebp+0x20] */
    float color_scale;             /* [ebp+0x24] */
    float u_offset, v_offset;      /* [ebp+0x28], [ebp+0x2c] */
    int32_t texture;               /* [ebp+0x30], -1 for none */
} mu_meshdraw_args;

/* Scratch tables and an optional observer of what the routine wrote. */
typedef struct mu_meshdraw_scratch {
    float *light_colors;           /* 3 * MU_MESHDRAW_MAX_ENTRIES floats */
    float *normal_texcoords;       /* 2 * (MU_MESHDRAW_MAX_ENTRIES + 1) floats */
    void *context;
    void (*tables)(void *context, int32_t mesh, int32_t light_count, const float *light_colors,
                   int32_t texcoord_count, const float *normal_texcoords);
} mu_meshdraw_scratch;

typedef struct mu_meshdraw_env {
    mu_meshdraw_model *model;
    const mu_meshdraw_globals *globals;
    mu_gl_cache *cache;
    const mu_gl_sink *sink;
    mu_bitmap_lookup bitmap;
    void *bitmap_context;
    mu_meshdraw_scratch *scratch;
} mu_meshdraw_env;

enum {
    MU_MESHDRAW_DRAWN = 0,     /* reached glEnd */
    MU_MESHDRAW_RETURNED = 1,  /* one of the routine's early returns (no glBegin) */
    MU_MESHDRAW_REFUSED = 2    /* index outside the supplied counts: nothing emitted */
};

/* The mesh draw 0x012b8d1d for one mesh. *corners receives the corners visited. */
int mu_meshdraw_mesh_draw(const mu_meshdraw_env *env, int32_t mesh, const mu_meshdraw_args *args, long *corners);

/* The body 0x012bb35a: glPushMatrix, the mesh draw of every mesh except
 * `skip` (with the sub-object passes), glPopMatrix. Counts are optional. */
typedef struct mu_meshdraw_counts {
    long drawn, returned, refused, corners;
} mu_meshdraw_counts;
void mu_meshdraw_body(const mu_meshdraw_env *env, const mu_meshdraw_args *args, int32_t skip,
                      mu_meshdraw_counts *counts);

/* Effective fixed-function state implied by a GL call stream: an adapter
 * for backends that do not issue GL themselves (software rasterizer). */
typedef struct mu_meshdraw_state {
    uint8_t blend, depth_test, depth_mask, cull, alpha_test, texture, fog;
    uint32_t src, dst;             /* GL blend factors */
    uint32_t texture_name;         /* bound GL texture object (0 = none) */
} mu_meshdraw_state;
void mu_meshdraw_state_defaults(mu_meshdraw_state *state);
/* Applies one state call (ENABLE/DISABLE/BLEND_FUNC/DEPTH_MASK/BIND_TEXTURE);
 * returns 1 if the op was a state call. */
int mu_meshdraw_state_apply(mu_meshdraw_state *state, uint32_t op, const uint32_t words[4]);

#endif
