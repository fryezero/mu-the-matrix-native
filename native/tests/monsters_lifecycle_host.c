/* Synthetic decoded-frame/cache lifecycle check, no live transport. */
#define MU_WORLD_NO_GL
#define MU_SESSION_SEED
#include "../world/world_rt_internal.h"
#include "../session/session_internal.h"
#include <stdio.h>
mu_apply characters_destroy(mu_session *s,const mu_frame *f);
mu_apply characters_monsters(mu_session *s,const mu_frame *f);
void world_rt_actors_sync(mu_world_rt *a);
int main(int argc, char **argv) {
    if(argc!=3) return 2;
    mu_world_rt_options o; mu_world_rt_default_options(&o);
    o.root=argv[1];o.placement=argv[2];o.audio=0;o.tile[0]=120;o.tile[1]=120;
    char error[1024];mu_world_rt *a=mu_world_rt_open(&o,error,sizeof error);
    if(!a) {fprintf(stderr,"%s\n",error);return 2;}
    if(a->actors.count!=3||a->actors.effect_instances!=1)return 3;
    uint8_t b[]={0xc1,6,0x14,1,4,2};
    mu_frame f={.head=0xc1,.opcode=0x14,.length=sizeof b};
    memcpy(f.bytes,b,sizeof b);
    characters_destroy(a->actors.session,&f);world_rt_actors_sync(a);
    if(a->actors.count!=2||a->actors.effect_instances!=0)return 4;
    uint8_t p[33]={0xc2,0,33,0x13,1,0x84,2,0,251,120,120,120,120,0x50};
    f=(mu_frame){.head=0xc2,.opcode=0x13,.length=sizeof p};
    memcpy(f.bytes,p,sizeof p);
    characters_monsters(a->actors.session,&f);world_rt_actors_sync(a);
    if(a->actors.count!=3||a->actors.list[2].server_class!=251||a->actors.effect_instances!=0)return 5;
    mu_world_rt_close(a);
    puts("{\"lifecycle\":3,\"destroyed_effects\":1,\"reused_identity\":1}");return 0;
}
