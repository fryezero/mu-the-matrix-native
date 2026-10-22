#ifndef MU_SOCIAL_ITEM_FORMULA_H
#define MU_SOCIAL_ITEM_FORMULA_H
#include <stddef.h>
/* 117b5eb / 12008f2 / 120102b. Host printf/strtod/pow and decimal conversion
 * are explicit CRT boundaries. Missing formulas evaluate to numeric zero;
 * empty/malformed expressions have a distinct safe native error status. */
typedef struct mu_social_formula_arg {
    int kind, integer;
    double real;
} mu_social_formula_arg;
enum { MU_SOCIAL_FORMULA_INTEGER, MU_SOCIAL_FORMULA_REAL };
enum {
    MU_SOCIAL_FORMULA_OK = 1,
    MU_SOCIAL_FORMULA_MISSING = 2,
    MU_SOCIAL_FORMULA_INVALID = 0,
    MU_SOCIAL_FORMULA_OVERFLOW = -1
};
int mu_social_formula_expand(const char *, const mu_social_formula_arg *, size_t, char out[256]);
int mu_social_formula_expression(const char *, double *value);
int mu_social_formula_evaluate(const char *pattern, const mu_social_formula_arg *, size_t, double *value);
#endif
