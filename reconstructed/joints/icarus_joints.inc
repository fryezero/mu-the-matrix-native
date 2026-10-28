/* World-10 joint movers, 0x0156d391 subtype 6 and 0x0156fb0f subtype 0.
 * Included after the common helpers so tail and humming arithmetic stay shared. */
static void move_icarus_swirl(mu_jt_joint *j, const mu_jt_env *env)
{
    if(j->lifetime>4) return;
    copy3(j->position,j->start);
    const mu_jt_object *owner=jobject(env,j->target);
    for(int i=0;i<j->max_tails;++i) {
        if(owner) {
            copy3(j->target_position,owner->position);
            j->target_position[0]=((float)(jrand(env)%200)+2050.0f)+j->target_position[0];
            j->target_position[1]=((float)(jrand(env)%200)+2050.0f)+j->target_position[1];
            j->target_position[2]-=10000.0f;
            float turn=(float)(jrand(env)%100+50);
            move_humming(j->position,j->angle,j->target_position,turn);
        }
        j->jitter[0]=(float)(jrand(env)%100+20);
        j->jitter[2]=(float)(jrand(env)%100+20);
        float a[3],m[12];
        for(int k=0;k<3;++k) a[k]=j->angle[k]+j->jitter[k];
        mu_angle_matrix(a,m);mu_jt_tail_shift(j,m);
        float v[3]={0,-j->velocity,0};add_rotated(j,v,m);
    }
}
static void move_icarus_bolt(mu_jt_joint *j, const mu_jt_env *env)
{
    if(j->lifetime<=15) { j->brightness-=10.12f; return; }
    float target[3]={((float)(jrand(env)%200)+j->target_position[0])-100.0f,
                     ((float)(jrand(env)%100)+j->target_position[1])-50.0f,j->target_position[2]};
    copy3(j->position,j->start);
    for(int i=0;i<j->max_tails;++i) {
        float turn=(float)(jrand(env)%80)+60.0f;
        move_humming(j->position,j->angle,target,turn);
        j->jitter[0]=(float)(jrand(env)%1400-700)/j->scale;
        j->jitter[2]=(float)(jrand(env)%1400-700)/j->scale;
        float a[3],m[12];
        for(int k=0;k<3;++k) a[k]=j->angle[k]+j->jitter[k];
        mu_angle_matrix(a,m);mu_jt_tail_shift(j,m);
        float v[3]={0,-j->velocity,0};add_rotated(j,v,m);
    }
}
