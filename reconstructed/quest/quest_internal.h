/* Shared internals of reconstructed/quest (NATIVE-QUEST-001). */
#ifndef MU_QUEST_INTERNAL_H
#define MU_QUEST_INTERNAL_H

#include "quest.h"

#if defined(__clang__) || defined(__GNUC__)
__attribute__((format(printf, 2, 3)))
#endif
void mu_quest_logf(mu_quest_log *log, const char *fmt, ...);

mu_quest *mu_quest_activate(mu_quest_client *c, int32_t index);      /* 0x00fe16e4 */
void mu_quest_deactivate(mu_quest_client *c, int32_t index);         /* 0x00fe17db */
void mu_quest_reset_active(mu_quest_client *c);                      /* 0x00fe18c4 */
void mu_quest_value_set(mu_quest_system *qs, int32_t index, int32_t value);   /* 0x00fe1984 */
void mu_quest_value_erase(mu_quest_system *qs, int32_t index);       /* 0x00fe19a3 */

/* The client's sprintf 0x009619dd as the validator models it: conversions d i u x X c (an int) and s (a
 * string), with flags, width, precision and the l/h length letters; %% prints '%'.  `ints`/`strs` are taken
 * in order of the conversions of their kind's position: args[k] is the k-th argument, is_str[k] its kind. */
typedef struct mu_qarg {
    int is_str;
    int32_t i;
    const char *s;
} mu_qarg;
void mu_quest_sprintf(char *out, size_t cap, const char *fmt, const mu_qarg *args, int nargs);

const char *mu_quest_text(const mu_quest_client *c, int32_t index);          /* GlobalText ("" unknown) */
const char *mu_quest_utf8(const mu_quest_client *c, const char *src, char *dst, size_t cap);
/* JSON string literal of a client string (bytes >= 0x80 kept, " \\ and controls escaped). */
void mu_quest_json(char *out, size_t cap, const char *s);

/* NATIVE-QUEST-002: effect helpers shared by the windows (quest_ui.c). */
/* 0x00aae7e0(window, method, fmt, ...): the arguments by the format's tokens (%s a C string, %d an int32_t, %b an
 * int as a bool), logged as a JSON array. */
void mu_quest_invoke(mu_quest_client *c, const char *window, const char *method, const char *fmt, ...);
void mu_quest_show(mu_quest_client *c, const char *window);
void mu_quest_hide(mu_quest_client *c, const char *window);
/* A packet the client builds (C1 header added; the length byte computed) and sends with the two send arguments. */
void mu_quest_send(mu_quest_client *c, const uint8_t *body, int n, int a, int b);
void mu_quest_notice(mu_quest_client *c, const char *text);          /* 0x0095f4ec */
/* 0x00b3967c(owner, id, text, title, a, b, c) / 0x00b39648(owner, id, text, button, a, b, c, d) */
void mu_quest_msgbox(mu_quest_client *c, const char *owner, int32_t id, const char *text, const char *title,
                     int32_t a, int32_t b, int32_t d);
void mu_quest_msgbox2(mu_quest_client *c, const char *owner, int32_t id, const char *text, const char *button,
                      int32_t a, int32_t b, int32_t d, int32_t e);
uint32_t mu_quest_rgba(int r, int g, int b, int a);                  /* 0x00b4c6aa (ABGR) */
uint32_t mu_quest_list_color(int32_t state, int32_t kind);           /* 0x00c8b9f9 */
/* QuestSummary hooks of the quest system (quest_summary.c): no-ops without the HUD. */
void mu_quest_tab_other(mu_quest_client *c, int32_t tab, int init);   /* tabs 0 / 1 */
void mu_summary_add(mu_quest_client *c, int32_t index);              /* 0x00c89ff9 */
void mu_summary_remove(mu_quest_client *c, int32_t index);           /* 0x00c8a072 */
void mu_summary_clear(mu_quest_client *c);                           /* 0x00c8a0ce */

/* NATIVE-QUEST-002: effect helpers shared by the windows (quest_ui.c). */
/* 0x00aae7e0(window, method, fmt, ...): the arguments by the format's tokens (%s a C string, %d an int32_t, %b an
 * int as a bool), logged as a JSON array. */
void mu_quest_invoke(mu_quest_client *c, const char *window, const char *method, const char *fmt, ...);
void mu_quest_show(mu_quest_client *c, const char *window);
void mu_quest_hide(mu_quest_client *c, const char *window);
/* A packet the client builds (C1 header added; the length byte computed) and sends with the two send arguments. */
void mu_quest_send(mu_quest_client *c, const uint8_t *body, int n, int a, int b);
void mu_quest_notice(mu_quest_client *c, const char *text);          /* 0x0095f4ec */
/* 0x00b3967c(owner, id, text, title, a, b, c) / 0x00b39648(owner, id, text, button, a, b, c, d) */
void mu_quest_msgbox(mu_quest_client *c, const char *owner, int32_t id, const char *text, const char *title,
                     int32_t a, int32_t b, int32_t d);
void mu_quest_msgbox2(mu_quest_client *c, const char *owner, int32_t id, const char *text, const char *button,
                      int32_t a, int32_t b, int32_t d, int32_t e);
uint32_t mu_quest_rgba(int r, int g, int b, int a);                  /* 0x00b4c6aa (ABGR) */
uint32_t mu_quest_list_color(int32_t state, int32_t kind);           /* 0x00c8b9f9 */
/* QuestSummary hooks of the quest system (quest_summary.c): no-ops without the HUD. */
void mu_summary_add(mu_quest_client *c, int32_t index);              /* 0x00c89ff9 */
void mu_summary_remove(mu_quest_client *c, int32_t index);           /* 0x00c8a072 */
void mu_summary_clear(mu_quest_client *c);                           /* 0x00c8a0ce */

#endif
