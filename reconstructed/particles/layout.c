/* Client layouts of the particle and sprite records (validator and tests). */
#include <string.h>

#include "particles.h"

static void put32(uint8_t *b, uint32_t off, const void *v)
{
    memcpy(b + off, v, 4);
}

static void get32(const uint8_t *b, uint32_t off, void *v)
{
    memcpy(v, b + off, 4);
}

#define FIELDS(X)                                                                                     \
    X(0x0c, type) X(0x10, tex_type) X(0x14, subtype) X(0x18, scale) X(0x20, position[0])              \
    X(0x24, position[1]) X(0x28, position[2]) X(0x2c, angle[0]) X(0x30, angle[1]) X(0x34, angle[2])   \
    X(0x38, light[0]) X(0x3c, light[1]) X(0x40, light[2]) X(0x44, alpha) X(0x48, lifetime)             \
    X(0x54, owner_position[0])                                                                        \
    X(0x58, owner_position[1]) X(0x5c, owner_position[2]) X(0x60, rotation) X(0x64, frame)            \
    X(0x6c, gravity) X(0x70, velocity[0]) X(0x74, velocity[1]) X(0x78, velocity[2]) X(0x7c, field_7c) \
    X(0x88, start[0])                                                                                 \
    X(0x8c, start[1]) X(0x90, start[2]) X(0x94, start_angle[0]) X(0x98, start_angle[1])               \
    X(0x9c, start_angle[2]) X(0xac, time) X(0xb0, arg8) \
    X(0x4c, initial_lifetime) X(0x1c, initial_scale) X(0x80, field_80) X(0x84, field_84)

/* owner (+0x50) is a pointer in the client: the caller maps it. */
void mu_pt_particle_store(const mu_pt_particle *p, uint8_t out[MU_PT_RECORD_BYTES])
{
#define STORE(off, f) put32(out, off, &p->f);
    FIELDS(STORE)
#undef STORE
    out[0x08] = p->live;
    out[0x68] = p->moving;
}

void mu_pt_particle_load(mu_pt_particle *p, const uint8_t in[MU_PT_RECORD_BYTES])
{
#define LOAD(off, f) get32(in, off, &p->f);
    FIELDS(LOAD)
#undef LOAD
    p->live = in[0x08];
    p->moving = in[0x68];
}

void mu_pt_particle_mask(uint8_t out[MU_PT_RECORD_BYTES])
{
    memset(out, 0, MU_PT_RECORD_BYTES);
#define MASK(off, f) memset(out + off, 1, 4);
    FIELDS(MASK)
#undef MASK
    out[0x08] = 1;
    out[0x68] = 1;
}

#define SFIELDS(X)                                                                                    \
    X(0x5c, type) X(0x60, blend) X(0x8c, axes) X(0x90, sheet[0]) X(0x94, sheet[1]) X(0x98, sheet_time) \
    X(0xa0, scale) X(0xd0, alpha) X(0xec, light[0]) X(0xf0, light[1]) X(0xf4, light[2])               \
    X(0x110, start[0]) X(0x114, start[1]) X(0x118, start[2]) X(0x158, position[0])                    \
    X(0x15c, position[1]) X(0x160, position[2]) X(0x16c, rotation)

/* owner (+0x34c) is a pointer in the client: the caller maps it. */
void mu_pt_sprite_store(const mu_pt_sprite *s, uint8_t out[MU_PT_SPRITE_BYTES])
{
#define STORE(off, f) put32(out, off, &s->f);
    SFIELDS(STORE)
#undef STORE
    out[0x00] = s->live;
    out[0x0b] = s->visible;
}

void mu_pt_sprite_load(mu_pt_sprite *s, const uint8_t in[MU_PT_SPRITE_BYTES])
{
#define LOAD(off, f) get32(in, off, &s->f);
    SFIELDS(LOAD)
#undef LOAD
    s->live = in[0x00];
    s->visible = in[0x0b];
}

void mu_pt_sprite_mask(uint8_t out[MU_PT_SPRITE_BYTES])
{
    memset(out, 0, MU_PT_SPRITE_BYTES);
#define MASK(off, f) memset(out + off, 1, 4);
    SFIELDS(MASK)
#undef MASK
    out[0x00] = 1;
    out[0x0b] = 1;
}
