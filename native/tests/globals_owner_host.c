#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../world/world_rt_internal.h"
#include "../core/mu_lang.h"
#include "../core/mu_perf.h"
#include "../core/mu_audio_host.h"
#include "../core/mu_png.h"
#include "../fixture/skills_model.h"

static void draw(mu_world_rt *a, char hash[65])
{
    mu_raster r;
    assert(!mu_raster_init(&r, 64, 64));
    mu_world_rt_draw_soft(a, &r);
    mu_sha256_hex(r.color, 64u * 64u * 4u, hash);
    mu_raster_free(&r);
}
int main(int argc, char **argv)
{
    assert(argc == 6);
    char error[512], before[65], after[65];
    mu_world_rt_options o;
    mu_world_rt_default_options(&o);
    o.root = argv[1]; o.width = o.height = 64;
    o.audio = 0; o.no_env = o.no_particles = 1; o.helper = "imp";
    assert(!setenv("MU_LANG_DIR", argv[2], 1));
    mu_world_rt *a = mu_world_rt_open(&o, error, sizeof error);
    assert(a); mu_world_rt_set_clock(a, 100000); mu_world_rt_frame(a, 100052); draw(a, before);
    assert(a->helpers && a->helpers->stats.drawn_imps == 1);
    assert(!strcmp(mu_lang_text(a->lang, 484), "visit-0"));
    assert(!setenv("MU_LANG_DIR", argv[3], 1));
    mu_world_rt *b = mu_world_rt_open(&o, error, sizeof error);
    assert(b); mu_world_rt_set_clock(b, 100000); mu_world_rt_frame(b, 100052); draw(b, after);
    assert(!strcmp(mu_lang_text(b->lang, 484), "visit-1"));
    mu_world_rt_close(b);
    draw(a, after);
    assert(!strcmp(before, after));
    assert(!strcmp(mu_lang_text(a->lang, 484), "visit-0"));
    mu_world_rt_close(a);

    mu_skill_demo one = {0}, two = {0};
    assert(mu_skill_demo_load(&one, argv[4]) == 1);
    assert(mu_skill_demo_load(&two, argv[5]) == 1);
    mu_skill_book *book = mu_skill_book_open(NULL, NULL, NULL);
    assert(book);
    mu_skill_book_demo_login(&one, book, 1);
    assert(mu_skill_learned_index(mu_skill_book_hero(book), 19) >= 0 && mu_skill_learned_index(mu_skill_book_hero(book), 41) < 0);
    mu_skill_book_demo_login(&two, book, 1);
    assert(mu_skill_learned_index(mu_skill_book_hero(book), 41) >= 0 && mu_skill_learned_index(mu_skill_book_hero(book), 19) < 0);
    mu_skill_book_close(book);

    mu_perf p = {0}, q = {0};
    assert(!mu_perf_open(&p, argv[4], 0));
    assert(!mu_perf_open(&q, argv[5], 0));
    mu_perf_add(&p, MU_PERF_LOGIC, 7); mu_perf_add(&q, MU_PERF_LOGIC, 11);
    assert(p.phase[MU_PERF_LOGIC] == 7 && q.phase[MU_PERF_LOGIC] == 11);
    mu_perf_frame(&p, 6);
    assert(p.frame == 1 && q.frame == 0 && q.phase[MU_PERF_LOGIC] == 11);
    mu_perf_close(&p);
    assert(mu_perf_enabled(&q));
    mu_perf_frame(&q, 6); mu_perf_close(&q);
    assert(!p.finish && p.frame == 0 && !mu_perf_enabled(&p));
    for (int i = 4; i < 6; ++i) {
        char log[4096];
        snprintf(log, sizeof log, "%s.audio", argv[i]);
        assert(!setenv("MU_AUDIO_CUE_LOG", log, 1));
        mu_audio_host_config cfg = {0}; cfg.skip_options = 1; cfg.engine.game_root = "/";
        mu_audio_host *host = mu_audio_host_new(&cfg, error, sizeof error);
        assert(host); mu_audio_host_free(host);
    }
    puts("independent world, language, helper, skill demo and perf owners");
    return 0;
}
