/* SESSION-VIEWPORT-001: the former --players server, now a loopback behavior.
 * All routing, ranges, timings, guild/party metadata and HP are synthetic. */
#define _POSIX_C_SOURCE 200809L
#include "../behavior.h"
#include "../characters_demo.h"
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
static uint32_t demo_rand(mu_world_players *p)
{
    p->rng = p->rng * 1103515245u + 12345u;
    return (p->rng >> 8) & 0xffffffu;
}

typedef struct fx_characters {
    mu_world_players players;
    int32_t hero[2];
    int32_t defer;
} fx_characters;

void mu_characters_demo_observe(void *self, const mu_world_players *view)
{
    fx_characters *f = self;
    f->hero[0] = view->walk->hero.tile[0];
    f->hero[1] = view->walk->hero.tile[1];
    f->players.view_range = view->view_range;
    for (int i = 0; i < view->count && i < f->players.count; ++i) {
        if (!view->list[i].session_generation) continue;
        f->players.list[i].c = view->list[i].c;
        f->players.list[i].fade = view->list[i].fade;
    }
}

static int send_frame(mu_fixture_ctx *ctx, const uint8_t *b, size_t n)
{
    mu_packet p;
    mu_packet_begin(&p, b[0], b[0] == 0xc2 ? b[3] : b[2]);
    size_t header = b[0] == 0xc2 ? 4u : 3u;
    mu_packet_add(&p, b + header, n - header, 0);
    return mu_fx_send(ctx, MU_CONN_GAME, &p, 0);
}

static void viewport_create(mu_fixture_ctx *ctx, mu_world_players *p, mu_world_player *q, int created)
{
    uint8_t packet[5 + 0x44] = {0xc2, 0, 5 + 0x44, 0x12, 1};
    mu_world_players_encode_viewport(p, q, created, packet + 5, 0x44);
    if (send_frame(ctx, packet, sizeof packet) != 0) return;
    q->in_view = 1; ++q->creates;
}

static void viewport_destroy(mu_fixture_ctx *ctx, mu_world_player *q)
{
    uint8_t b[] = {0xc1,6,0x14,1,(uint8_t)(q->key >> 8),(uint8_t)q->key};
    if (send_frame(ctx,b,sizeof b) != 0) return;
    q->in_view = 0;
}

static void move_packet(mu_fixture_ctx *ctx, mu_world_players *p, mu_world_player *q, int x, int y)
{
    uint8_t b[] = {0xc1,8,0x3d,(uint8_t)(q->key >> 8),(uint8_t)q->key,(uint8_t)x,(uint8_t)y,
                  (uint8_t)((demo_rand(p)%8u+1u)<<4)};
    send_frame(ctx,b,sizeof b);
}

static void store_packet(mu_fixture_ctx *ctx, mu_world_player *q)
{
    uint8_t b[6+0x2f] = {0xc1,6+0x2f,0x3f,2,0,1};
    b[6]=(uint8_t)(q->key>>8); b[7]=(uint8_t)q->key;
    memcpy(b+8,q->spec.store_title,strlen(q->spec.store_title));
    send_frame(ctx,b,sizeof b); q->store_open=1;
}

static void *characters_open(mu_fixture_ctx *ctx, const char *args, char *error, size_t cap)
{
    (void)ctx;
    fx_characters *f = calloc(1,sizeof *f);
    if (!f) return NULL;
    f->defer=mu_fx_arg_int(args,"defer",0);
    mu_world_players *p=&f->players;
    p->rng=0x9a7e2026u; p->view_range=12;
    f->hero[0]=mu_fx_arg_int(args,"x",120); f->hero[1]=mu_fx_arg_int(args,"y",120);
    char file[1024];
    const char *file_arg = strstr(args, "file=");
    if (file_arg) {
        /* file= is last, so authored filenames may contain spaces. */
        snprintf(file, sizeof file, "%s", file_arg + 5);
        FILE *in=fopen(file,"r");
        if (!in) { snprintf(error,cap,"characters: cannot open %s",file); free(f); return NULL; }
        char line[1024]; int number=0;
        while (fgets(line,sizeof line,in)) {
            ++number;
            char *hash=strchr(line,'#'); if(hash) *hash=0;
            char *s=line; while(isspace((unsigned char)*s)) ++s;
            if(!*s) continue;
            char *end=strchr(s,'\n'); if(end) *end=0;
            if(p->count==MU_WORLD_PLAYERS_MAX ||
               mu_characters_parse_player(&p->list[p->count].spec,s,number,error,cap)) {
                fclose(in); free(f); return NULL;
            }
            ++p->count;
        }
        fclose(in);
    }
    for(int i=0;i<p->count;++i) {
        mu_world_player *q=&p->list[i]; q->key=0x200+i;
        q->c.tile[0]=q->spec.start[0]; q->c.tile[1]=q->spec.start[1];
        q->c.target[0]=(uint8_t)q->spec.start[0]; q->c.target[1]=(uint8_t)q->spec.start[1];
        q->c.direction=q->spec.direction;
        q->wait=10+(int32_t)(demo_rand(p)%30u);
    }
    return f;
}

static void characters_step(void *self, mu_fixture_ctx *ctx, uint32_t now)
{
    (void)now;
    fx_characters *f=self; mu_world_players *p=&f->players;
    if (f->defer > 0) { --f->defer; return; }
    for(int i=0;i<p->count;++i) {
        mu_world_player *q=&p->list[i]; const mu_world_player_spec *s=&q->spec;
        int dx=abs(q->c.tile[0]-f->hero[0]),dy=abs(q->c.tile[1]-f->hero[1]);
        int dist=dx>dy?dx:dy;
        if(!q->in_view) {
            if(q->respawn_in>0) {
                if(--q->respawn_in==0) {
                    q->c.tile[0]=s->start[0];q->c.tile[1]=s->start[1];
                    q->c.target[0]=(uint8_t)s->start[0];q->c.target[1]=(uint8_t)s->start[1];
                    q->c.direction=s->direction;q->c.dead=0;q->fade.removed=0;q->next_leg=0;
                    viewport_create(ctx,p,q,1);
                }
                continue;
            }
            if(q->fade.removed||q->c.dead)continue;
            if(dist<=p->view_range) viewport_create(ctx,p,q,q->creates==0&&p->steps==0);
            continue;
        }
        if(q->fade.removed) {
            q->in_view=0;q->respawn_in=s->respawn_steps;
            viewport_destroy(ctx,q);continue;
        }
        if(dist>p->view_range+3&&!q->c.dead) {viewport_destroy(ctx,q);continue;}
        if((int32_t)p->steps==s->die_step&&!q->c.dead) {
            uint8_t b[]={0xc1,5,0x17,(uint8_t)(q->key>>8),(uint8_t)q->key};
            send_frame(ctx,b,sizeof b);
        }
        if((int32_t)p->steps==s->store_step&&!q->store_open&&!q->c.dead) store_packet(ctx,q);
        if(!q->c.dead&&!q->c.movement&&!q->store_open&&s->route_count>0) {
            if(q->wait>0)--q->wait;
            else {
                const int32_t *leg=s->route[q->next_leg%s->route_count];
                q->next_leg=(q->next_leg+1)%s->route_count;
                q->wait=s->idle_steps+(int32_t)(demo_rand(p)%20u);
                move_packet(ctx,p,q,leg[0],leg[1]);
            }
        }
    }
    ++p->steps;
}

static int characters_command(void *self, mu_fixture_ctx *ctx, const char *command, char *error, size_t cap)
{
    fx_characters *f=self;
    if(!strncmp(command,"player ",7)) {
        if(f->players.count==MU_WORLD_PLAYERS_MAX)return -1;
        char line[1024];snprintf(line,sizeof line,"%s",command);
        mu_world_player *q=&f->players.list[f->players.count];
        if(mu_characters_parse_player(&q->spec,line,0,error,cap))return -1;
        q->key=0x200+f->players.count++;
        q->c.tile[0]=q->spec.start[0];q->c.tile[1]=q->spec.start[1];
        q->c.target[0]=(uint8_t)q->spec.start[0];q->c.target[1]=(uint8_t)q->spec.start[1];
        viewport_create(ctx,&f->players,q,1);return 0;
    }
    snprintf(error,cap,"characters: unknown command %s",command);return -1;
}

const mu_fixture_behavior mu_fx_characters = {
    .name="characters", .open=characters_open, .on_step=characters_step,
    .on_command=characters_command, .close=free
};
