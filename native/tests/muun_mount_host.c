#include "../core/mu_muun_mount.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc, char **argv)
{
    if (argc != 4) return 2;
    mu_muun_visual *v = calloc(1, sizeof *v);
    mu_muun_mount *m = calloc(1, sizeof *m);
    if (!v || !m) return 2;
    mu_mv_owner o = {.key=77,.live=1,.position={12850,12450,180},.angle={0,0,45}};
    char error[512];int32_t code = (int32_t)strtol(argv[3], NULL, 10);
    if (mu_muun_visual_open(v,argv[1],argv[2],code,&o,3,error,sizeof error) ||
        mu_muun_mount_open(m,v,argv[1],error,sizeof error)) {
        fprintf(stderr,"%s\n",error);mu_muun_mount_close(m);mu_muun_visual_close(v);free(v);free(m);return 1;
    }
    int controls=1,poses=1,exact=1;
    const int actions[]={1,65,248};
    for (int k=0;k<3;++k) {
        mu_muun_mount_step(m,v,actions[k]);mu_muun_mount_frame(m,v,&o,v->info.item,0,0,0,1);
        poses &= m->visible && m->posed && m->attached && mu_model_action(&m->model)==(uint16_t)(k*2);
        float expected[3];mu_mv_riding_attachment(mu_model_bone_matrices(&m->model)+12*m->bone,
            m->model.params.body_scale,expected);expected[2]+=30.0f;
        exact &= !memcmp(expected,m->attachment,sizeof expected) && !memcmp(m->model.params.origin,o.position,sizeof o.position);
    }
    int bone=m->bone,bones=1;
    for (int bad=0;bad<3;++bad) {
        m->bone=bad==0 ? -1 : (bad==1 ? m->bmd.bone_count : bone);
        if (bad==2) m->bmd.bones[bone].dummy=1;
        mu_muun_mount_frame(m,v,&o,v->info.item,0,0,0,1);bones &= !m->attached;
        if (bad==2) m->bmd.bones[bone].dummy=0;
    }
    m->bone=bone;
    for (int gate=0;gate<5;++gate) {
        mu_muun_mount_frame(m,v,&o,gate==0 ? -1:v->info.item,gate==1,gate==2,gate==3,gate!=4);
        controls &= !m->visible && !m->attached;
    }
    mu_muun_mount_frame(m,v,&o,v->info.item,0,0,0,1);controls &= m->visible;
    o.key++;mu_muun_visual_frame(v,&o,3,1,.04f);mu_muun_mount_frame(m,v,&o,v->info.item,0,0,0,1);
    controls &= !v->live && !m->visible;
    o.key--;mu_muun_visual_step(v,&o,3);mu_muun_mount_frame(m,v,&o,v->info.item,0,0,0,1);controls &= !m->visible;
    int retired=1;
    for (int reason=0;reason<2;++reason) {
        mu_muun_visual_close(v);
        if (mu_muun_visual_open(v,argv[1],argv[2],code,&o,3,error,sizeof error)) return 1;
        if (reason==0) o.live=0;
        mu_muun_visual_frame(v,&o,reason==0 ? 3u:4u,1,.04f);
        mu_muun_mount_frame(m,v,&o,v->info.item,0,0,0,1);
        retired &= !v->live && !m->visible;
        o.live=1;
    }
    printf("{\"code\":%d,\"model\":%d,\"missing\":%d,\"bone\":%d,\"refused_bones\":%ld,\"poses\":%d,\"exact\":%d,\"controls\":%d,\"bones\":%d,\"retired\":%d}\n",
        code,m->model_code,m->textures.missing,m->bone,m->refused_bones,poses,exact,controls,bones,retired);
    mu_muun_mount_close(m);mu_muun_visual_close(v);free(m);free(v);return 0;
}
