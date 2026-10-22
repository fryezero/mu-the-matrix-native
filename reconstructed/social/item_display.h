#ifndef MU_SOCIAL_ITEM_DISPLAY_H
#define MU_SOCIAL_ITEM_DISPLAY_H
#include "item_options.h"
/* Original selector/argument semantics. Text and CRT formatting stay at the
 * host boundary. kind: 0 literal, 1 integer, 2 real, 3 label+integer,
 * 4 label+real. Missing hero state returns 0, separately from numeric zero. */
typedef struct mu_social_display_value {
    int32_t text, label, kind, integer, suppressed;
    double real;
} mu_social_display_value;
int mu_social_ordinary_display(int code, int kind_a, unsigned id, int value, int context,
                               mu_social_display_value *);
int mu_social_excellent_display(int code, int kind_a, int kind_b, int category, int mode, int id,
                                double value, int hero_known, int hero_level, int record_level,
                                mu_social_display_value *);
int mu_social_socket_display(int type, float input, int hp_known, int max_hp, int mp_known, int max_mp,
                             mu_social_display_value *);
int mu_social_harmony_visible(const mu_social_item_wire *, const mu_social_item_context *);
int mu_social_normalized_slot(uint8_t slot);
#endif
