/* RENDER-EFFECTS-017: the native routes of 017. No argument: portable self-checks (the armour owner-effect particle
 * kinds 0x810a/7, 0x810a/0xf and Spark03 0x7f26/0x26 are admitted, have world particle slots and are created through
 * the owner route's consumer; the raster's GL_CLAMP bitmaps sample clamp to edge). "sample": one texture lookup per
 * stdin line "w h wrap filter s t rgba-hex" (s, t as binary32 hex), printed as four binary32 hex words
 * (scripts/validate_render_effects17.py compares them with the GL clamp-to-edge / repeat rule). */
#include "../core/mu_raster.c"
#include "mu_particles.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

static float bits_float(uint32_t u)
{
    float f;
    memcpy(&f, &u, sizeof f);
    return f;
}

static uint32_t float_bits(float f)
{
    uint32_t u;
    memcpy(&u, &f, sizeof u);
    return u;
}

static void lookup(const mu_image *image, uint32_t wrap, uint32_t filter, float s, float t, float out[4])
{
    mu_raster r;
    memset(&r, 0, sizeof r);
    r.texture = image;
    r.state.texture = 1;
    r.texture_slot = 0;
    r.texture_wrap = &wrap;
    r.texture_filter = &filter;
    sample(&r, s, t, out);
}

static int samples(void)
{
    static char line[(1 << 20) + 256], hex[(1 << 20) + 256];
    static uint8_t rgba[4 * 256 * 256];
    while (fgets(line, sizeof line, stdin)) {
        int w, h;
        unsigned wrap, filter, sb, tb;
        if (sscanf(line, "%d %d %x %x %x %x %s", &w, &h, &wrap, &filter, &sb, &tb, hex) != 7 || w < 1 || h < 1 ||
            w * h > 256 * 256 || strlen(hex) != (size_t)(8 * w * h))
            return 2;
        for (int i = 0; i < 4 * w * h; ++i) {
            unsigned byte;
            sscanf(hex + 2 * i, "%2x", &byte);
            rgba[i] = (uint8_t)byte;
        }
        mu_image image = {w, h, 4, rgba};
        float out[4];
        lookup(&image, wrap, filter, bits_float(sb), bits_float(tb), out);
        printf("%08x %08x %08x %08x\n", float_bits(out[0]), float_bits(out[1]), float_bits(out[2]), float_bits(out[3]));
    }
    return 0;
}

int main(int argc, char **argv)
{
    if (argc > 1 && !strcmp(argv[1], "sample"))
        return samples();
    /* the armour programs' particle kinds (RENDER-ITEMS-002Q) */
    assert(mu_pt_kind_supported(0x810a, 7) && mu_pt_kind_supported(0x810a, 0xf) && mu_pt_kind_supported(0x7f26, 0x26));
    assert(!mu_pt_kind_supported(0x810a, 8) && !mu_pt_kind_supported(0x7f26, 0x27));
    assert(mu_world_particles_bitmap_slot(0x810a) >= 0 && mu_world_particles_bitmap_slot(0x7f26) >= 0);
    mu_world_particles *p = calloc(1, sizeof *p);
    char error[128];
    if (!p || mu_world_particles_open(p, "", NULL, 0, 1, 1, error, sizeof error))
        return 1;
    const float position[3] = {12800.0f, 12800.0f, 150.0f}, angle[3] = {0.0f, 0.0f, 45.0f}, light[3] = {1, 1, 1};
    const float direction[3] = {0.0f, 0.6f, 0.8f};
    assert(mu_world_particles_create(p, 0x810a, position, angle, light, 7, 1.0f));
    assert(mu_world_particles_create(p, 0x810a, position, direction, light, 0xf, 0.5f));
    assert(mu_world_particles_create(p, 0x7f26, position, angle, light, 0x26, 1.0f));
    assert(p->stats.unsupported == 0 && p->list.count == 3);
    /* 0x810a/0xf: the request's direction becomes the velocity, the angle is zeroed (0x015b227a) */
    const mu_pt_particle *drift = &p->list.records[1];
    assert(drift->velocity[1] == 0.6f && drift->velocity[2] == 0.8f && drift->angle[2] == 0.0f && drift->lifetime == 30);
    assert(p->list.records[2].gravity == 2.5f);
    mu_world_particles_close(p);
    free(p);
    /* clamp to edge: a red | blue texture keeps the edge texel in the outer half texels */
    const uint8_t two[8] = {255, 0, 0, 255, 0, 0, 255, 255};
    const mu_image image = {2, 1, 4, (uint8_t *)two};
    float out[4];
    lookup(&image, 0x2900, 0x2601, 0.1f, 0.5f, out);
    assert(out[0] == 1.0f && out[2] == 0.0f);
    lookup(&image, 0x2900, 0x2601, 0.9f, 0.5f, out);
    assert(out[0] == 0.0f && out[2] == 1.0f);
    lookup(&image, 0x2901, 0x2601, 0.1f, 0.5f, out);   /* GL_REPEAT still wraps */
    assert(out[0] > 0.0f && out[2] > 0.0f);
    printf("armour particle kinds 0x810a/7, 0x810a/0xf, 0x7f26/0x26 and the raster's clamp to edge through native "
           "routes: OK\n");
    return 0;
}
