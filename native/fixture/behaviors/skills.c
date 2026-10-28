/* SESSION-SKILL-001. Independent synthetic server model. Only emitted plaintext frames reach client state. */
#include "../behavior.h"
#include "../skills_model.h"
#include "../skills_demo.h"
#include "../../core/mu_lang.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct skills_fixture {
    mu_lang *lang;
    mu_skill_book *book;
    mu_skill_tree4 *tree;
    mu_fixture_ctx *ctx;
    int ready, cls;
    char dir[4096], root[4096], file[4096];
} skills_fixture;
static int emit(void *user, const uint8_t *b, size_t n)
{
    skills_fixture *s = user;
    size_t h = b[0] == 0xc2 ? 4u : 3u;
    mu_packet p;
    mu_packet_begin(&p, b[0], b[h-1]);
    mu_packet_add(&p, b+h, n-h, 0);
    return mu_fx_send(s->ctx, MU_CONN_GAME, &p, 0) == 0;
}
static void dispose_model(skills_fixture *s)
{
    mu_skill_tree4_close(s->tree); mu_skill_book_close(s->book); mu_lang_free(s->lang);
    s->tree = NULL; s->book = NULL; s->lang = NULL;
}
static int login(skills_fixture *s, int cls, int points)
{
    dispose_model(s); s->cls = cls;
    s->lang = mu_lang_load(s->dir);
    s->book = mu_skill_book_open(s->lang, s->dir, s->root);
    s->tree = mu_skill_tree4_open(s->dir, s->book);
    if (!s->book || !s->tree) return -1;
    extern void mu_skill_demo_reset(void);
    mu_skill_demo_reset();
    if (s->file[0]) mu_skill_demo_load(s->file);
    mu_skill_book_demo_login_emit(s->book, cls, emit, s);
    mu_skill_tree4_enter(s->tree, cls & 15);
    mu_skill_tree4_demo_login_emit(s->tree, points, emit, s);
    mu_skill_tree4_demo_side_emit(s->tree, emit, s);
    s->ready = 1;
    return 0;
}
static void *open_skills(mu_fixture_ctx *ctx, const char *args, char *err, size_t cap)
{
    (void)args; (void)err; (void)cap;
    skills_fixture *s = calloc(1, sizeof *s);
    if (s) {
        s->ctx = ctx;
        snprintf(s->dir, sizeof s->dir, "%s", getenv("MU_LANG_DIR") ? getenv("MU_LANG_DIR") : ".");
        snprintf(s->root, sizeof s->root, "%s", getenv("MU_GAME_ROOT") ? getenv("MU_GAME_ROOT") : ".");
        snprintf(s->file, sizeof s->file, "%s", getenv("MU_SKILL_DEMO") ? getenv("MU_SKILL_DEMO") : "");
    }
    return s;
}
static int command(void *self, mu_fixture_ctx *ctx, const char *line, char *err, size_t cap)
{
    skills_fixture *s = self; s->ctx = ctx;
    int cls, points = 30, skill;
    if (!strncmp(line, "data ", 5)) { snprintf(s->dir, sizeof s->dir, "%s", line+5); return 0; }
    if (!strncmp(line, "root ", 5)) { snprintf(s->root, sizeof s->root, "%s", line+5); return 0; }
    if (!strncmp(line, "file ", 5)) { snprintf(s->file, sizeof s->file, "%s", line+5); return 0; }
    if (sscanf(line, "login %d %d", &cls, &points) >= 1) return login(s, cls, points);
    if (s->ready && sscanf(line, "learn %d", &skill) == 1) {
        mu_skill_book_demo_learn_emit(s->book, skill, 0, emit, s); return 0;
    }
    if (s->ready && sscanf(line, "forget %d", &skill) == 1) {
        mu_skill_book_demo_learn_emit(s->book, skill, 1, emit, s); return 0;
    }
    snprintf(err, cap, "skills: unsupported command: %s", line); return -1;
}
int mu_skills_demo_change(void *self,int32_t skill,int forget)
{
    skills_fixture *s=self;
    return s && s->ready ? mu_skill_book_demo_learn_emit(s->book,skill,forget,emit,s) : 0;
}
static int request(void *self, mu_fixture_ctx *ctx, const mu_fixture_request *rq)
{
    skills_fixture *s = self; s->ctx = ctx;
    if (!s->ready) return 0;
    if (rq->opcode == 1 && rq->length == 8 && rq->bytes[3] == 0x16)
        return mu_skill_book_demo_master_request_emit(s->book, rq->bytes, rq->length, emit, s);
    if (rq->opcode == 0x7e && rq->length == 9 && rq->bytes[3] == 1)
        return mu_skill_tree4_demo_request_emit(s->tree, rq->bytes, rq->length, emit, s);
    if (rq->opcode == 0x7e && rq->length == 7 && rq->bytes[3] == 5)
        return mu_skill_tree4_demo_side_request_emit(s->tree, rq->bytes, rq->length, emit, s);
    if (rq->opcode == 1 && rq->length == 41 && rq->bytes[3] == 0x30) {
        uint8_t a[24] = {0xc1,24,0xa0,3}; memcpy(a+4,rq->bytes+4,20);
        mu_skill_book_receive(s->book,a,sizeof a); return emit(s,a,sizeof a);
    }
    return 0;
}
static void close_skills(void *self) { skills_fixture *s=self; dispose_model(s); free(s); }
const mu_fixture_behavior mu_fx_skills = {.name="skills", .open=open_skills, .on_plain_request=request,
                                         .on_command=command, .close=close_skills};
