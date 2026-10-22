#ifndef MU_SOCIAL_ITEM_TABLES_H
#define MU_SOCIAL_ITEM_TABLES_H
#include "mu_data.h"
typedef struct mu_social_item_tables mu_social_item_tables;
typedef struct mu_social_excellent_row {
    char text[101];
    int32_t value_type, value, format;
    uint8_t equipment[7];
} mu_social_excellent_row;
typedef struct mu_social_socket_row {
    int32_t index, element, option, value_type, values[20];
    char name[65];
    uint8_t requirements[6];
} mu_social_socket_row;
typedef struct mu_social_harmony_row {
    int32_t id, min_level, values[14], zen[14];
    char name[61];
} mu_social_harmony_row;
typedef struct mu_social_guardian_option {
    int32_t id, value, auxiliary;
    const char *text;
} mu_social_guardian_option;
typedef struct mu_social_artifact_row {
    int32_t selector, text_id, pairs[10][2], tail[5];
    const char *name;
} mu_social_artifact_row;
typedef struct mu_social_advanced_row {
    int32_t group, id, values[4], format;
    const char *name;
} mu_social_advanced_row;
mu_social_item_tables *mu_social_item_tables_load(const char *game_root, const char *lang_dir,
                                                  const mu_data_table *items);
void mu_social_item_tables_free(mu_social_item_tables *);
int mu_social_excellent_get(const mu_social_item_tables *, int family, int category, int id,
                            mu_social_excellent_row *);
int mu_social_socket_get(const mu_social_item_tables *, int group, int index, mu_social_socket_row *);
int mu_social_harmony_get(const mu_social_item_tables *, int group, int id, mu_social_harmony_row *);
int mu_social_guardian_get(const mu_social_item_tables *, int base, int selector,
                           mu_social_guardian_option *);
int mu_social_guardian_bonus_get(const mu_social_item_tables *, int base, int selector,
                                 mu_social_guardian_option out[2]);
int mu_social_artifact_get(const mu_social_item_tables *, int selector, mu_social_artifact_row *);
const char *mu_social_artifact_text(const mu_social_item_tables *, int id, int *format);
int mu_social_advanced_get(const mu_social_item_tables *, int group, int id, mu_social_advanced_row *);
const char *mu_social_formula_get(const mu_social_item_tables *, int family, int id);
const char *mu_social_ancient_prefix(const mu_social_item_tables *, int code, uint8_t bits, uint8_t kind_b);
/* Presence counts for local diagnostics; no private text is exposed. */
size_t mu_social_item_table_rows(const mu_social_item_tables *);
#endif
