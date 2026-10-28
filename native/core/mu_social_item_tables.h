#ifndef MU_SOCIAL_ITEM_TABLES_H
#define MU_SOCIAL_ITEM_TABLES_H
#include "mu_data.h"
#include "../../reconstructed/social/item_formula.h"
typedef struct mu_social_item_tables mu_social_item_tables;
struct mu_lang;
const struct mu_lang *mu_social_item_tables_lang(const mu_social_item_tables *);
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
/* Ordinary and bonus value fields are family-8 formula indices. */
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
/* Valid rows imply availability; an authored header also represents loaded-empty families. */
int mu_social_item_table_available(const mu_social_item_tables *, const char *family);
int mu_social_excellent_available(const mu_social_item_tables *, int family);
int mu_social_excellent_get(const mu_social_item_tables *, int family, int category, int id,
                            mu_social_excellent_row *);
int mu_social_socket_get(const mu_social_item_tables *, int group, int index, mu_social_socket_row *);
int mu_social_harmony_get(const mu_social_item_tables *, int group, int id, mu_social_harmony_row *);
int mu_social_guardian_lookup_row(void *, int kind, int selector, int base, int32_t values[6]);
int mu_social_guardian_get(const mu_social_item_tables *, int base, int selector,
                           mu_social_guardian_option *);
int mu_social_guardian_bonus_get(const mu_social_item_tables *, int base, int selector,
                                 mu_social_guardian_option out[2]);
int mu_social_artifact_get(const mu_social_item_tables *, int selector, mu_social_artifact_row *);
const char *mu_social_artifact_text(const mu_social_item_tables *, int id, int *format);
int mu_social_advanced_get(const mu_social_item_tables *, int group, int id, mu_social_advanced_row *);
const char *mu_social_formula_get(const mu_social_item_tables *, int family, int id);
const char *mu_social_ancient_prefix(const mu_social_item_tables *, int code, uint8_t bits, uint8_t kind_b);
/* A missing table is unresolved; an absent expression in a loaded table is original numeric zero. */
int mu_social_formula_value(const mu_social_item_tables *, int family, int id, const mu_social_formula_arg *,
                            size_t, double *);
/* Exact exported row keys; returns numeric column count, zero on absence. */
int mu_social_option_find(const mu_social_item_tables *, const char *kind, const int32_t *keys, size_t nkeys,
                          int32_t values[40], const char **text);
int mu_social_earring_pair_get(const mu_social_item_tables *, int primary_id, int32_t values[40]);
/* Presence counts for local diagnostics; no private text is exposed. */
size_t mu_social_item_table_rows(const mu_social_item_tables *);
#endif
