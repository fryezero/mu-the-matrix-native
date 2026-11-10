/* RENDER-EFFECTS-025: synthetic pre-bone record and cloud pool/raster consumer. */
#include "../core/mu_renderchar.c"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    assert(argc == 2);
    mu_renderchar_env env;
    mu_renderchar_default_env(&env);
    assert(env.item_before_matrix);
    for (int i = 0; i < 12; ++i) assert(env.item_before_matrix[i] == 0.0f);
    mu_model model = {0};
    model.params.body_scale = 2.0f;
    const float origin[3] = {100, 200, 300};
    memcpy(model.params.origin, origin, sizeof origin);
    const float before[12] = {1,2,3,11, 4,5,6,-7, 7,8,9,3};
    owner_services services = {0};
    services.model = &model;
    services.item_before_matrix = before;
    float out[3];
    item_before_transform(&services, out);
    assert(out[0] == 122 && out[1] == 186 && out[2] == 306);
    services.item_before_matrix = env.item_before_matrix;
    item_before_transform(&services, out);
    assert(!memcmp(out, origin, sizeof out));

    mu_world_particles *p = calloc(1, sizeof *p);
    char error[128];
    assert(p && !mu_world_particles_open(p, argv[1], NULL, 0, 1, 0, error, sizeof error));
    const float zero[3] = {0}, light[3] = {1,1,1};
    assert(mu_world_particles_create(p, 0x7f89, zero, zero, light, 28, 1));
    assert(p->list.created == 1 && p->list.unsupported == 0);
    mu_world_particles_step(p, 123456);
    mu_pt_particle *cloud = &p->list.records[0];
    assert(cloud->lifetime == 299);
    memcpy(cloud->position, zero, sizeof zero);
    cloud->scale = 0.01f;
    cloud->alpha = 0.5f;
    const float view[16] = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    mu_raster raster;
    assert(!mu_raster_init(&raster, 32, 32));
    mu_world_particles_draw_raster(p, &raster, view);
    assert(p->stats.drawn_particles == 1);
    /* Exercise the real draw adapter, not only the compatibility transform. */
    mu_bmd bmd = {0};
    mu_bmd_bone bones[15] = {0};
    const char *names[] = {"c001", "c002", "c003", "head001", "head002", "mid01", "mid02", "up01 ",
                           "up02", "under01"};
    for (int i = 0; i < 10; ++i) strcpy(bones[i].name, names[i]);
    bmd.bone_count = 15;
    bmd.bones = bones;
    model.bmd = &bmd;
    float pose[15 * 12] = {0};
    long counts[2] = {0};
    uint32_t frame = 1;
    env.particles = p;
    env.item_bones = pose;
    env.pre_counts = counts;
    env.frame_counter = &frame;
    env.item_before_matrix = NULL;
    mu_renderchar_glow glow = {.type = 0x0f29};
    mu_draw_options options = {0};
    mu_render_backend backend = {0};
    mu_renderchar_stats stats = {0};
    mu_draw_stats draw_stats = {0};
    mu_renderchar_draw_item(&model, &glow, &env, light, 1, &options, &backend, &draw_stats, &stats);
    const long created = counts[0], refused = counts[1];
    assert(refused == 1);
    counts[0] = counts[1] = 0;
    env.item_before_matrix = before;
    mu_renderchar_draw_item(&model, &glow, &env, light, 1, &options, &backend, &draw_stats, &stats);
    assert(counts[0] == created + 1 && counts[1] == 0);
    mu_raster_free(&raster);
    mu_world_particles_close(p);
    free(p);
    puts("explicit pre-bone transforms and clouds/28 raster routing OK");
    return 0;
}
