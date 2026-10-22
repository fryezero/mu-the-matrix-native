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

#endif
