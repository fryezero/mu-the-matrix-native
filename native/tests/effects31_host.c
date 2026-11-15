/* RENDER-EFFECTS-031: actual native bitmap routing, map-owner bounds, allocation and raster. */
#include "../core/mu_particles.c"
#include "../core/mu_png.h"
#include <assert.h>

int main(int argc, char **argv)
{
    assert(argc >= 2);
    const int32_t kinds[][2] = {{0x801c,3},{0x801c,4},{0x801c,7},{0x7f89,7},{0x7f89,10},
                               {0x7f89,26},{0x7f89,16},{0x7f42,7},{0x802a,1},{0x7f42,12},{0x7f26,2}};
    const float zero[3] = {0}, light[3] = {1,1,1};
    const float view[16] = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    const uint8_t background[4] = {128,128,128,255};
    for (unsigned k = 0; k < sizeof kinds / sizeof kinds[0]; ++k) {
        mu_world_particles *p = calloc(1, sizeof *p);
        mu_objects *objects = calloc(1, sizeof *objects);
        char error[128], path[2048];
        assert(p && objects && !mu_world_particles_open(p, argv[1], NULL, 38, 1, 0, error, sizeof error));
        objects->count = 1; objects->rt.ready = 1;
        objects->rt.images = calloc(1, MU_OBJ_SIZE);
        assert(objects->rt.images);
        objects->rt.images[MU_OBJF_LIVE] = 1;
        p->objects = objects;
        int slot = mu_world_particles_bitmap_slot(kinds[k][0]);
        assert(slot >= 0 && p->bitmap_present[slot]);
        assert(p->bitmaps.filter[slot] == 0x2601 && p->bitmaps.wrap[slot] == 0x2900);
        if (kinds[k][0] == 0x7f42) assert(abs((int)p->bitmaps.images[slot].rgba[0] - 64) <= 2);
        if (kinds[k][0] == 0x802a) assert(abs((int)p->bitmaps.images[slot].rgba[0] - 192) <= 2);
        const int owned = (kinds[k][0] == 0x7f89 && (kinds[k][1] == 7 || kinds[k][1] == 26)) || kinds[k][0] == 0x7f26;
        if (owned) {
            assert(!mu_world_particles_create_owned(p,kinds[k][0],zero,zero,light,kinds[k][1],1,-1));
            assert(!mu_world_particles_create_owned(p,kinds[k][0],zero,zero,light,kinds[k][1],1,77));
            assert(p->list.unsupported == 2 && !p->list.count);
        }
        assert(mu_world_particles_create_owned(p,kinds[k][0],zero,zero,light,kinds[k][1],1,owned ? 0 : -1));
        assert(p->list.created == 1 && p->list.unsupported == (uint64_t)(owned ? 2 : 0));
        mu_pt_particle *record = &p->list.records[0];
        /* Recenter for a camera-space raster control. Constructor/mover values are compared separately. */
        memcpy(record->position,zero,sizeof zero);
        memcpy(record->start,zero,sizeof zero);
        mu_world_particles_step(p,40);
        memcpy(record->position,zero,sizeof zero);
        if (record->light[0] == 0) record->light[0] = record->light[1] = record->light[2] = 0.1f;
        mu_raster raster;
        assert(!mu_raster_init(&raster,64,64));
        mu_raster_clear(&raster,background);
        memcpy(raster.view,view,sizeof view); memcpy(raster.projection,view,sizeof view);
        mu_world_particles_draw_raster(p,&raster,view);
        assert(p->stats.drawn_particles == 1 && raster.fragments > 0);
        if (argc > 2) {
            snprintf(path,sizeof path,"%s/%x-%d.png",argv[2],(unsigned)kinds[k][0],kinds[k][1]);
            assert(!mu_png_write(path,raster.color,64,64));
        }
        printf("{\"kind\":%d,\"subtype\":%d,\"slot\":%d,\"fragments\":%ld}\n",
               kinds[k][0],kinds[k][1],slot,raster.fragments);
        for (int n = 0; n < 502; ++n) mu_world_particles_step(p,(float)(80+40*n));
        assert(!p->list.count);
        p->objects = NULL;
        free(objects->rt.images); free(objects);
        mu_raster_free(&raster); mu_world_particles_close(p); free(p);
    }
    const int32_t joints[][2] = {{0x7f7d,8},{0x7f7d,9},{0x7f7d,10},{0x7fd5,5},{0x7fd3,2},{0x7f78,2}};
    for (unsigned k = 0; k < sizeof joints / sizeof joints[0]; ++k) {
        mu_world_particles *p = calloc(1, sizeof *p);
        char error[128], path[2048];
        assert(p && !mu_world_particles_open(p,argv[1],NULL,38,1,0,error,sizeof error));
        const int32_t index = mu_world_particles_joint(p,joints[k][0],zero,zero,zero,joints[k][1],-1,60,0xffff,0,0,0xffff,0,NULL);
        assert(index >= 0 && p->stats.joints_created == 1 && !p->stats.joints_unsupported);
        mu_world_particles_step(p,40);
        if (joints[k][0] == 0x7f78)
            while (p->joints[index].lifetime > 24) mu_world_particles_step(p,80);
        mu_raster raster;
        assert(!mu_raster_init(&raster,128,128));
        mu_raster_clear(&raster,background);
        memcpy(raster.view,view,sizeof view); memcpy(raster.projection,view,sizeof view);
        const float zoom = joints[k][0] == 0x7f7d ? 0.001f : joints[k][0] == 0x7f78 ? 0.01f : 0.02f;
        if (joints[k][0] == 0x7f78) {
            raster.view[5] = raster.view[10] = 0.70710677f;
            raster.view[6] = 0.70710677f; raster.view[9] = -0.70710677f;
        }
        raster.projection[0] = raster.projection[5] = raster.projection[10] = zoom;
        mu_world_particles_draw_raster(p,&raster,view);
        fprintf(stderr,"joint %x/%d quads %u fragments %ld\n",(unsigned)joints[k][0],joints[k][1],p->stats.drawn_joint_quads,raster.fragments);
        assert(p->stats.drawn_joint_quads > 0 && raster.fragments > 0);
        if (argc > 2) {
            snprintf(path,sizeof path,"%s/j%x-%d.png",argv[2],(unsigned)joints[k][0],joints[k][1]);
            assert(!mu_png_write(path,raster.color,128,128));
        }
        printf("{\"joint\":true,\"kind\":%d,\"subtype\":%d,\"fragments\":%ld}\n",joints[k][0],joints[k][1],raster.fragments);
        for (int n = 0; n < 80; ++n) mu_world_particles_step(p,(float)(80+40*n));
        assert(!mu_world_particles_live_joints(p));
        mu_raster_free(&raster); mu_world_particles_close(p); free(p);
    }
    const int effects[][2] = {{0x47a,0},{0x47a,1},{0x7f84,4},{0x7fd0,0},{0x7f42,6}};
    for (unsigned k = 0; k < sizeof effects / sizeof effects[0]; ++k) {
        mu_world_particles *p = calloc(1,sizeof *p);
        char error[128],path[2048];
        assert(p && !mu_world_particles_open(p,argv[1],NULL,38,1,0,error,sizeof error));
        mu_sfx_info info={0}; info.word4=4;
        assert(mu_world_particles_effect(p,effects[k][0],effects[k][1],zero,zero,light,-1,1,&info));
        mu_world_particles_step(p,40);
        if (effects[k][0]==0x7fd0) {
            assert(p->list.created==3 && p->list.unsupported==0);
            for (int n=0;n<3;++n) assert(p->list.records[n].owner==MU_WORLD_FX_SELF_BASE);
        }
        if (effects[k][0]==0x7f42) assert(p->list.created==1 && p->list.unsupported==0);
        mu_raster raster; assert(!mu_raster_init(&raster,128,128));
        mu_raster_clear(&raster,background);
        memcpy(raster.view,view,sizeof view); memcpy(raster.projection,view,sizeof view);
        raster.projection[0]=raster.projection[5]=raster.projection[10]=0.02f;
        const int draws=mu_world_particles_draw_models_raster(p,&raster);
        const int model=effects[k][0]==0x47a;
        assert(draws==model && (!model || raster.fragments>0));
        if (argc>2 && model) {
            snprintf(path,sizeof path,"%s/e%x-%d.png",argv[2],(unsigned)effects[k][0],effects[k][1]);
            assert(!mu_png_write(path,raster.color,128,128));
        }
        printf("{\"effect\":true,\"kind\":%d,\"subtype\":%d,\"draws\":%d,\"fragments\":%ld,\"equal\":true}\n",
               effects[k][0],effects[k][1],draws,raster.fragments);
        for (int n=0;n<60;++n) mu_world_particles_step(p,(float)(80+40*n));
        assert(!mu_world_particles_live_effects(p) && !p->list.count);
        /* Pool exhaustion retains the fixed caps; particle constructors still consume their RNG before overflow. */
        p->list.count=p->list.capacity;
        const uint64_t rand_before=p->rand_calls;
        assert(!mu_world_particles_create(p,0x801c,zero,zero,light,3,1));
        assert(p->list.overflow==1 && p->list.count==MU_WORLD_PT_CAPACITY && p->rand_calls>rand_before);
        for (int n=0;n<MU_WORLD_FX_EFFECTS;++n) p->effects[n].live=1;
        assert(!mu_world_particles_effect(p,0x47a,0,zero,zero,light,-1,1,NULL) && p->stats.effects_full==1);
        for (int n=0;n<MU_JT_JOINTS;++n) p->joints[n].live=1;
        assert(mu_world_particles_joint(p,0x7f7d,zero,zero,zero,8,-1,1,0,0,0,0,0,NULL)<0);
        assert(p->stats.joints_full==1);
        mu_raster_free(&raster); mu_world_particles_close(p); free(p);
    }
    if (argc > 3) { /* Optional installed-data proof; synthetic fixture remains portable. */
        mu_world_particles *p=calloc(1,sizeof *p); char error[128],path[2048];
        assert(p && !mu_world_particles_open(p,argv[3],NULL,38,1,0,error,sizeof error));
        int loaded=0;
        for (int n=0;n<MU_WORLD_FX_MODELS;++n) if (p->models[n].type==0x47a) loaded=p->models[n].loaded;
        assert(loaded);
        for (int sub=0;sub<2;++sub) {
            assert(mu_world_particles_effect(p,0x47a,sub,zero,zero,light,-1,1,NULL));
            mu_world_particles_step(p,40);
            mu_raster raster; assert(!mu_raster_init(&raster,256,256));
            mu_raster_clear(&raster,background);
            memcpy(raster.view,view,sizeof view); memcpy(raster.projection,view,sizeof view);
            raster.projection[0]=raster.projection[5]=raster.projection[10]=0.005f;
            assert(mu_world_particles_draw_models_raster(p,&raster)==1 && raster.fragments>0);
            snprintf(path,sizeof path,"%s/installed-47a-%d.png",argv[2],sub);
            assert(!mu_png_write(path,raster.color,256,256));
            printf("{\"effect\":true,\"installed\":true,\"subtype\":%d,\"fragments\":%ld,\"equal\":true}\n",sub,raster.fragments);
            for (int n=0;n<15;++n) mu_world_particles_step(p,80);
            assert(!mu_world_particles_live_effects(p)); mu_raster_free(&raster);
        }
        mu_world_particles_close(p); free(p);
    }
    return 0;
}
