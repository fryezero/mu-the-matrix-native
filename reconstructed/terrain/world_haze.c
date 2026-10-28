#include "world_haze.h"
#include <math.h>
#include <limits.h>

/* RenderBitmapUV 0x0184f4ba..0x0184f793. Keep binary32 operation order. */
void mu_world_haze_quad(int32_t texture, float x, float y, float width, float height,
                        float u, float v, float du, float dv, uint32_t screen_width,
                        uint32_t screen_height, const mu_terrain_sink *s)
{
    x = (float)screen_width * x / 640.0f;
    y = (float)screen_height * y / 480.0f;
    width = (float)screen_width * width / 640.0f;
    height = (float)screen_height * height / 480.0f;
    y = (float)screen_height - y;
    const float xy[4][3] = {{x,y,0}, {x,y-height,0}, {x+width,y-height,0}, {x+width,y,0}};
    const float uv[4][2] = {{u,v+dv*0.25f}, {u,(v+dv)-dv*0.25f}, {u+du,v+dv}, {u+du,v}};
    s->bind(s->context,texture);
    s->begin(s->context,6);
    for (int k=0;k<4;++k) {
        s->texcoord(s->context,uv[k][0],uv[k][1]);
        s->vertex(s->context,xy[k]);
    }
    s->end(s->context);
}

static int32_t clock_integer(float time)
{
    return !isfinite(time) || time >= 2147483648.0f || time < -2147483648.0f ? INT32_MIN : (int32_t)time;
}

/* Tarkan 0x016b247c..0x016b2627, Raklion slot +0x40 0x00e9eae8..0x00e9ec6a. */
void mu_world_haze_draw(int32_t world, float time, uint32_t width, uint32_t height,
                        const mu_terrain_sink *s)
{
    if (world!=8 && world!=57 && world!=58) return;
    float phase=(float)(clock_integer(time)%100000);
    if (world==8) {
        s->state(s->context,2,1);
        s->color4(s->context,1,1,1,0.5f);
    }
    s->state(s->context,3,0); /* ONE, ONE; depth writes and alpha test off */
    const float sand[3]={0.3f,0.3f,0.25f}, snow[3]={0.4f,0.4f,0.45f};
    s->color3(s->context,world==8?sand:snow);
    if (world==8) {
        mu_world_haze_quad(0x7f21,0,0,640,480,phase*0.0002f,0,0.3f,0.3f,width,height,s);
        mu_world_haze_quad(0x7f22,0,0,640,480,phase*0.001f,0,3,2,width,height,s);
    } else {
        mu_world_haze_quad(0x7f22,0,0,640,480,phase*0.0006f,(-phase)*0.0006f,3,2,width,height,s);
        mu_world_haze_quad(0x7f21,0,0,640,480,phase*0.0001f,0,0.3f,0.3f,width,height,s);
    }
}

const char *mu_world_haze_texture(int32_t world, int slot)
{
    if (slot<0 || slot>1) return 0;
    if (world==8) return slot ? "Object9/sand02.jpg" : "Object9/sand01.jpg";
    if (world==57 || world==58) return slot ? "Object9/sand02.jpg" : "Effect/Map_Smoke1.jpg";
    return 0;
}
