/* Exercises the K producers' consumer entry points against native bitmap dispatch. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../core/mu_particles.h"

static mu_world_particles particles;
static int vertices;
static void vertex(void *ctx, const float p[3]) { (void)ctx; (void)p; ++vertices; }
static void prepare(void *ctx, const mu_meshdraw_state *state, int32_t texture)
{ (void)ctx; (void)state; assert(texture >= 0); }
static void noop(void *ctx) { (void)ctx; }
static void texcoord(void *ctx, float u, float v) { (void)ctx; (void)u; (void)v; }
static void color(void *ctx, float r, float g, float b, float a)
{ (void)ctx; (void)r; (void)g; (void)b; (void)a; }
static int backend(void *ctx, const mu_world_particles *p, mu_render_backend *out)
{
    (void)ctx; (void)p;
    memset(out, 0, sizeof *out);
    out->prepare = prepare; out->begin = noop; out->end = noop;
    out->sink.vertex = vertex; out->sink.texcoord = texcoord; out->sink.color4 = color;
    return 0;
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    char error[256];
    assert(mu_world_particles_open(&particles, argv[1], NULL, 0, 1, 0, error, sizeof error) == 0);
    const float pos[3] = {100, 100, 100}, zero[3] = {0}, light[3] = {1, 1, 1};
    const int subtypes[] = {4, 6, 7, 8};
    assert(mu_world_particles_create(&particles, 0x7ef7, pos, zero, light, 0, 1));
    for (int i = 0; i < 4; ++i)
        assert(mu_world_particles_create(&particles, 0x7f5a, pos, zero, light, subtypes[i], 1));
    assert(mu_world_particles_create(&particles, 0x7f54, pos, zero, light, 0, 1));
    mu_world_particles_step(&particles, 123456);
    assert(particles.list.count == 6 && particles.stats.unsupported == 0);
    const int ids[] = {0x7f84, 0x7f38, 0x8021};
    for (int i = 0; i < 3; ++i)
        assert(mu_world_particles_sprite(&particles, ids[i], pos, 1, light, -1, 0, 0, 4) >= 0);
    const float identity[16] = {1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    const mu_world_particles_target target = {NULL, backend};
    assert(mu_world_particles_draw(&particles, identity, &target) == 9);
    assert(particles.stats.drawn_sprites == 3 && particles.stats.drawn_particles == 6 && vertices == 54);
    /* Last three effect slots, before rain02/rain03; actual loader sampling metadata. */
    for (int i = MU_WORLD_PT_BITMAPS - 5; i < MU_WORLD_PT_BITMAPS - 2; ++i) {
        assert(particles.bitmaps.slots[i] && particles.bitmaps.filter[i] == 0x2601);
        assert(particles.bitmaps.wrap[i] == 0x2900 && particles.bitmaps.components[i] == 3);
    }
    mu_world_particles_close(&particles);
    puts("five consumers, explosion, three registered sprites, nine quads, exact sampling: OK");
    return 0;
}
