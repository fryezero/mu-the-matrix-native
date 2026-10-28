#include "../core/mu_map.h"
#include "../fixture/mu_fixture.h"
#include "../gfx/mu_gfx_layer.h"
#include "../session/mu_session.h"
#include "../session/mu_session_seed.h"
#include "../world/world_gfx_map.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void movie_check(mu_gfx_layer *l, unsigned tick)
{
    const char *root = mu_gfx_layer_channel_path(l, "hudMap");
    assert(root && *root);
    const char *names[] = {"_iconsType0", "_iconsType1", "_iconsTypeUser", "_iconsTypeMonster"};
    int expected[4] = {tick >= 3 && tick < 7, tick < 9, tick >= 4 && tick < 8, tick >= 4 && tick < 8};
    for (int i = 0; i < 4; ++i) {
        char path[512];
        snprintf(path, sizeof path, "%s.mcWideScale.mcRot._map.%s._arrIcons.length", root, names[i]);
        const char *v = mu_gfx_layer_get_variable(l, MU_GFX_MAIN, path);
        if (!v || atoi(v) != expected[i])
            fprintf(stderr, "tick %u %s got %s expected %d\n", tick, path, v ? v : "NULL", expected[i]);
        assert(v && atoi(v) == expected[i]);
    }
    printf("real hudMap tick %u: %d portals, %d NPCs, %d users, %d monsters\n", tick, expected[0],
           expected[1], expected[2], expected[3]);
    const char *out = getenv("MU_MAP_OVERLAY_RENDER_DIR");
    if (out && (tick == 4 || tick == 8 || tick == 9)) {
        uint8_t *rgba = calloc(1280 * 800, 4);
        assert(rgba);
        mu_gfx_layer_composite(l, rgba, 1280, 800);
        char path[4096];
        snprintf(path, sizeof path, "%s/frame-%u.ppm", out, tick);
        FILE *f = fopen(path, "wb");
        assert(f);
        fprintf(f, "P6\n1280 800\n255\n");
        for (int i = 0; i < 1280 * 800; ++i)
            fwrite(rgba + 4 * i, 1, 3, f);
        fclose(f);
        free(rgba);
    }
}

static void frame(mu_gfx_layer *l, world_gfx_map *g, unsigned tick)
{
    float pos[2] = {12050, 12050};
    (void)tick;
    mu_gfx_layer_advance(l, 40);
    world_gfx_map_frame(g, pos, 90);
}
int main(int argc, char **argv)
{
    assert(argc >= 2);
    char error[512];
    mu_fixture_options options = {argv[1], NULL, 7};
    mu_fixture *fx = mu_fixture_open(&options, error, sizeof error);
    assert(fx);
    mu_transport *t = mu_fixture_transport(fx);
    mu_session_config cfg = {0};
    cfg.transport = t;
    mu_fixture_endpoint(fx, "game", &cfg.connect_server);
    mu_session_seed seed = {0};
    mu_session *s = mu_session_open_seeded(&cfg, &seed, error, sizeof error);
    assert(s);
    mu_map_session *map = calloc(1, sizeof *map);
    assert(map);
    mu_map_session_init(map, NULL, 0, 120, 120);
    mu_map_bind_overlay(map, s);
    mu_gfx_layer *l = NULL;
    world_gfx_map *g = NULL;
    if (argc == 3 && !strcmp(argv[2], "capacity")) {
        for (unsigned tick = 1; tick <= 4; ++tick) {
            mu_transport_poll(t, tick * 40);
            mu_session_pump(s, tick * 40);
            mu_map_overlay_view v = mu_session_map_overlay(s);
            assert(v.count == 128);
            if (tick == 1)
                assert(v.revision == 128);
            if (tick == 2)
                assert(v.revision == 128); /* full, new key refused atomically */
            if (tick == 3)
                assert(v.revision == 129 && v.markers[1].x == 500);
            if (tick == 4)
                assert(v.revision == 131 && v.markers[127].key == 200);
        }
        goto finish;
    }
    if (argc >= 5) {
        mu_gfx_layer_config c = {
            .movie_dir = argv[2], .lib_path = argv[3], .width = 1280, .height = 800, .shared = 1};
        l = mu_gfx_layer_open(&c, error, sizeof error);
        if (!l)
            fprintf(stderr, "%s\n", error);
        assert(l);
        g = world_gfx_map_open(l, map, argv[4]);
        assert(g);
        for (unsigned i = 0; i < 120; ++i)
            frame(l, g, i);
        if (argc == 6)
            mu_gfx_layer_invoke(l, MU_GFX_MAIN, NULL, "testCall", "[\"hudMap\",\"onLoad\",\"_level0.map\"]");
        frame(l, g, 121);
        map->hud.available = 1;
        world_gfx_map_action(g, "tab", 0);
    }
    for (unsigned tick = 1; tick <= 10; ++tick) {
        mu_transport_poll(t, tick * 40);
        mu_session_pump(s, tick * 40);
        mu_map_overlay_view v = mu_session_map_overlay(s);
        if (tick == 1)
            assert(v.count == 1 && v.markers[0].key == 7 && v.revision == 1);
        if (tick == 2)
            assert(v.count == 1 && v.markers[0].state == 6 && v.markers[0].x == 244 &&
                   !strcmp(v.markers[0].text, "Updated guide"));
        if (tick == 3)
            assert(v.count == 2 && v.markers[1].type == 0);
        if (tick == 4)
            assert(v.detected_count == 2 && v.detected[0].key == 0 && v.detected[0].type == 2 &&
                   v.detected[1].type == 3);
        if (tick == 5 || tick == 6)
            assert(v.count == 2 && v.detected_count == 2 && v.revision == 4);
        if (tick == 7)
            assert(v.count == 1 && v.markers[0].type == 1);
        if (tick == 8)
            assert(v.detected_count == 0 && v.count == 1 && v.detector_seq == 2);
        if (tick >= 9)
            assert(v.count == 0 && v.detected_count == 0);
        if (l) {
            frame(l, g, 121 + tick);
            if (argc == 5)
                movie_check(l, tick);
        }
        if (tick == 4) {
            mu_session_detach_world(s);
            if (g)
                world_gfx_map_close(g);
            mu_map_bind_overlay(map, NULL);
            mu_map_bind_overlay(map, s);
            if (l) {
                g = world_gfx_map_open(l, map, argv[4]);
                frame(l, g, 125);
            }
            assert(mu_session_map_overlay(s).detected_count == 2);
        }
        if (argc == 3 && tick == 4) {
            mu_sim sim = mu_session_sim_begin(s);
            ((mu_map_unit *)v.markers)[0].key = 88;
            mu_session_sim_end(s, &sim); /* deliberate illegal replicated write must abort */
            abort();
        }
    }
finish:;
    mu_session_status status;
    mu_session_status_get(s, &status);
    assert(status.unhandled == 0 && status.undecodable == 0);
    if (g)
        world_gfx_map_close(g);
    if (l)
        mu_gfx_layer_close(l);
    mu_map_bind_overlay(map, NULL);
    free(map);
    mu_session_close(s);
    mu_transport_free(t);
    mu_fixture_close(fx);
    puts("map overlay lifecycle passed: 10 ticks, malformed atomicity, empty refresh, detach/rebind");
    return 0;
}
