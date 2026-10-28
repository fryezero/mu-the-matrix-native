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

/* 0x01569cda, 0x0156a997 and 0x0156b4dc..0x0156c050, subtype 1 only. */
static void move_icarus_emitter(mu_jt_joint *j, const mu_jt_env *env, int32_t index)
{
    const mu_jt_object *o = jobject(env, j->target);
    copy3(j->target_position, o->position);
    j->target_position[2] += 10.0f;
    uint32_t clock = (uint32_t)env->ambient_clock;
    uint32_t phase = (uint32_t)index * 0xd1e3u + (index % 2 ? clock : 0u - clock);
    float a = (float)(int32_t)(phase + 0xd903u) * (0.048f * 0.5f);
    float b = (float)(int32_t)phase * (0.0613f * 0.5f);
    float c = (float)(int32_t)(phase + 0x2b67u) * (0.1113f * 0.5f);
    float sn = (float)sin((double)a);
    float x = sn * (float)cos((double)b);
    float y = sn * (float)sin((double)b);
    float z = (float)cos((double)a);
    float sc = (float)sin((double)c), cc = (float)cos((double)c);
    j->position[0] = j->target_position[0] + (cc * y - sc * z) * 70.0f;
    j->position[1] = j->target_position[1] + (sc * y + cc * z) * 70.0f;
    j->position[2] = j->target_position[2] + x * 140.0f;
    j->light[0] = j->light[1] = 0.2f;
    j->light[2] = 0.2f * sc + 0.4f;
}
