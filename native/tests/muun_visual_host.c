/* Production fixture lease and posed attachment controls, MUUN-VISUAL-001. */
#include "../core/mu_muun_visual.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int hidden(const mu_muun_visual *v)
{
    for (uint32_t k=0;k<v->scene.instance_count;++k)
        if(v->scene.instances[k].owner.visible) return 0;
    return !v->visible;
}
int main(int argc,char **argv)
{
    if(argc!=4) return 2;
    mu_muun_visual *v=calloc(1,sizeof *v);
    if(!v) return 2;
    mu_mv_owner o={.key=77,.live=1,.position={12850,13050,180},.angle={0,0,45}};
    char error[512]; int code=(int)strtol(argv[3],NULL,10);
    if(mu_muun_visual_open(v,argv[1],argv[2],code,&o,3,error,sizeof error)) {
        fprintf(stderr,"%s\n",error);
        printf("{\"loaded\":false,\"code\":%d}\n",code); free(v); return 0;
    }
    int mesh_count=v->mesh_count;
    long refused_meshes=v->refused_meshes;
    int command_controls=!mu_muun_visual_command(v,49,o.position);
    float start[3];memcpy(start,v->state.position,sizeof start);
    int matrices=1,fields=1;
    for(int step=0;step<30;++step) {
        if(step==2){o.position[0]+=500;o.position[2]+=35;o.moving=1;}
        mu_muun_visual_step(v,&o,3);mu_muun_visual_frame(v,&o,3,1,0.04f);
        mu_effect_object object={0};
        memcpy(object.position,v->state.position,sizeof object.position);
        memcpy(object.angle,v->state.angle,sizeof object.angle);
        object.scale=v->state.scale;object.bones=mu_model_bone_matrices(&v->model);object.model_bones=v->bmd.bone_count;
        for(int32_t k=0;k<v->effects.count;++k) {
            const mu_object_effect_record *r=&v->effects.records[k];
            const mu_effect_instance *i=&v->scene.instances[r->handle];float expect[16];
            matrices &= mu_object_effect_matrix(expect,r,&object) && !memcmp(expect,i->external,sizeof expect);
            fields &= i->owner.visible && i->owner.flag5 && i->owner.flag6 && i->owner.action==v->state.action &&
                i->owner.frame==v->state.frame;
        }
    }
    int moved=memcmp(start,v->state.position,sizeof start)!=0;
    uint32_t instances=v->scene.instance_count;
    mu_muun_visual_frame(v,&o,3,0,0.04f);int invisible=hidden(v);
    mu_muun_visual_frame(v,&o,3,1,0.04f);int resumed=v->visible && v->scene.instance_count==instances;
    o.key++;mu_muun_visual_frame(v,&o,3,1,0.04f);int foreign=!v->live && hidden(v);
    o.key--;mu_muun_visual_step(v,&o,3);int terminal=!v->live;
    printf("{\"mesh_passes\":%d,\"refused_meshes\":%ld,\"loaded\":true,\"code\":%d,\"model\":%d,\"bones\":%d,\"actions\":%d,\"records\":%d,"
        "\"requested\":%ld,\"invalid\":%ld,\"refused_bones\":%ld,\"updates\":%ld,\"matrices\":%d,\"fields\":%d,"
        "\"moved\":%d,\"invisible\":%d,\"resumed\":%d,\"foreign\":%d,\"terminal\":%d,",
        mesh_count,refused_meshes,code,v->state.model,v->bmd.bone_count,v->bmd.action_count,v->effects.count,v->effects.requested,
        v->effects.invalid,v->refused_bones,v->effects.updates,matrices,fields,moved,invisible,resumed,foreign,terminal);
    mu_muun_visual_close(v);int dead=0,generation=0;
    if(!mu_muun_visual_open(v,argv[1],argv[2],code,&o,3,error,sizeof error)) {
        o.live=0;mu_muun_visual_step(v,&o,3);dead=!v->live && hidden(v);mu_muun_visual_close(v);
    }
    o.live=1;
    if(!mu_muun_visual_open(v,argv[1],argv[2],code,&o,3,error,sizeof error)) {
        for (int category=50;category<=51;++category) {
            int action=mu_mv_command_action(category);
            int accepted=mu_muun_visual_command(v,category,o.position);
            command_controls &= accepted == (action < v->bmd.action_count);
            if (accepted) {
                command_controls &= v->state.state == action && v->state.action == action;
                mu_muun_visual_frame(v,&o,3,1,0.04f);
                command_controls &= v->posed;
                for (int k=0;k<100 && v->state.state==action;++k) mu_muun_visual_step(v,&o,3);
                command_controls &= v->state.state != action;
            }
        }
        mu_muun_visual_frame(v,&o,4,1,0.04f);generation=!v->live && hidden(v);mu_muun_visual_close(v);
    }
    int bones=mu_muun_visual_bone_available(-1,0,0) && mu_muun_visual_bone_available(5,7,1) &&
        !mu_muun_visual_bone_available(5,7,0) && !mu_muun_visual_bone_available(7,7,1) &&
        !mu_muun_visual_bone_available(-2,7,1);
    printf("\"command_controls\":%d,\"dead\":%d,\"generation\":%d,\"bone_controls\":%d}\n",command_controls,dead,generation,bones);free(v);return 0;
}
