#ifndef MU_SOCIAL_ITEM_PRESENT_H
#define MU_SOCIAL_ITEM_PRESENT_H
#include <stddef.h>
#include <stdint.h>
/* Original option consumers at the table/formula/string boundary. The output
 * records the formatter arguments, not a guessed option description. */
typedef struct mu_social_present_env {
    void *context;
    int (*formula)(void *, int family, int index, const int32_t *arguments, size_t count, double *);
} mu_social_present_env;
typedef struct mu_social_present_args {
    int32_t mode, count, global_text[2]; /* 0 absent, 1 row formatter, 2 literal GlobalText */
    int32_t kind[3], integer[3];         /* 0 integer, 1 double, 2 supplied row name, 3 GlobalText string */
    double real[3];
} mu_social_present_args;
typedef struct mu_social_guardian_entry {
    int32_t id, index, auxiliary, name_key, name_present;
} mu_social_guardian_entry;
/* Lookup kinds: ordinary value/name, bonus value/name. Value rows contain
 * (id,index,auxiliary), or two (id,index,unused) triples. */
typedef int (*mu_social_guardian_lookup)(void *, int kind, int selector, int base, int32_t values[6]);
void mu_social_guardian_construct(int base, const uint8_t selectors[5], int enabled,
                                  mu_social_guardian_lookup, void *, mu_social_guardian_entry ordinary[4],
                                  int *ordinary_count, mu_social_guardian_entry bonus[2], int *bonus_count);
int mu_social_guardian_present(int bonus, int id, int formula_index, int auxiliary, int level_word,
                               const mu_social_present_env *, mu_social_present_args *);
typedef struct mu_social_artifact_option {
    int32_t selector, text_id, pairs[10][2], formula_index, threshold, divisor;
} mu_social_artifact_option;
typedef struct mu_social_artifact_entry {
    int32_t selector, text_id, display_value, threshold_flag, raw_value, position, position_percent;
} mu_social_artifact_entry;
int mu_social_artifact_construct(const mu_social_artifact_option *, int selector, int raw, int level,
                                 const mu_social_present_env *, mu_social_artifact_entry *);
int mu_social_artifact_present(const mu_social_artifact_entry *, int text_present, int format,
                               mu_social_present_args *);
int mu_social_earring_present(int id, int format, int row_value, int selector_present, int level,
                              int other_present, int other_level, const mu_social_present_env *,
                              mu_social_present_args *);
int mu_social_pentagram_present(int required_level, const int32_t rank[4], const mu_social_present_env *,
                                mu_social_present_args *);
typedef struct mu_social_errtel_line {
    int32_t physical, ordinal, level, option;
} mu_social_errtel_line;
/* Returns count, zero for invalid count, or -1 at the uncaptured mastery boundary. */
int mu_social_errtel_plan(int count, const uint8_t slots[5], int grade, mu_social_errtel_line out[5]);
int mu_social_errtel_request(uint8_t byte, int physical_index, int32_t keys[3]);
int mu_social_errtel_present(const int32_t values[11], int level, mu_social_present_args *);
int mu_social_advanced_present(int format, int value, mu_social_present_args *);
/* Literal option names are data; earring format 2 retains the original two percent characters. */
size_t mu_social_present_literal(char *, size_t, const char *, int value, int prefix_only, int percent_count);
int mu_social_advanced_threshold(const int32_t thresholds[4], int value);
#endif
