#include "item_formula.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct token {
    int kind, op;
    char text[256];
} token;
static int number(int c) {
    return (c >= '0' && c <= '9') || c == '.';
}
static int operator(int c) {
    return c && strchr("()+-*/ ^", c) != NULL;
}
static int next(const char *s, size_t *cursor, token *t) {
    memset(t, 0, sizeof *t);
    size_t n = strlen(s), used = 0;
    for (size_t i = *cursor; i < n; i++) {
        unsigned char c = (unsigned char)s[i];
        if (number(c)) {
            t->kind = 1;
            if (used + 1 >= sizeof t->text)
                return 0;
            t->text[used++] = (char)c;
            t->text[used] = 0;
            ++*cursor;
            if (i + 1 == n || !number((unsigned char)s[i + 1]))
                return 1;
        } else if (operator(c)) {
            t->kind = 2;
            t->text[0] = (char)c;
            t->text[1] = 0;
            used = 1;
            ++*cursor;
            if (c == '-' && (!i || s[i - 1] == ' ') && i + 1 < n && s[i + 1] != ' ')
                continue;
            t->op = c;
            return 1;
        } else
            return 0;
    }
    return t->kind != 0;
}
static int priority(int op, int top) {
    if (op == '(')
        return top ? 3 : 0;
    if (op == '*' || op == '/' || op == '^')
        return 1;
    if (op == '+' || op == '-')
        return 2;
    return -1;
}
static int emit(token *out, int *n, int op) {
    if (*n >= 255)
        return 0;
    memset(out + *n, 0, sizeof *out);
    out[*n].kind = 2;
    out[*n].op = op;
    ++*n;
    return 1;
}
int mu_social_formula_expand(const char *pattern, const mu_social_formula_arg *args, size_t count,
                             char out[256]) {
    size_t n = 0, a = 0;
    out[0] = 0;
    for (size_t i = 0; pattern && pattern[i]; i++) {
        if (pattern[i] != '%') {
            if (n >= 255)
                return MU_SOCIAL_FORMULA_OVERFLOW;
            out[n++] = pattern[i];
            continue;
        }
        int c = (unsigned char)pattern[++i];
        if (c == '%') {
            if (n >= 255)
                return MU_SOCIAL_FORMULA_OVERFLOW;
            out[n++] = '%';
            continue;
        }
        if (a >= count || !args)
            return MU_SOCIAL_FORMULA_INVALID;
        char text[384];
        int len;
        if (c == 'd' && args[a].kind == MU_SOCIAL_FORMULA_INTEGER)
            len = snprintf(text, sizeof text, "%d", args[a].integer);
        else if (c == 'f' && args[a].kind == MU_SOCIAL_FORMULA_REAL)
            len = snprintf(text, sizeof text, "%f", args[a].real);
        else
            return MU_SOCIAL_FORMULA_INVALID;
        a++;
        if (len < 0 || (size_t)len >= sizeof text || (size_t)len > 255 - n)
            return MU_SOCIAL_FORMULA_OVERFLOW;
        memcpy(out + n, text, (size_t)len);
        n += (size_t)len;
    }
    out[n] = 0;
    return MU_SOCIAL_FORMULA_OK;
}
int mu_social_formula_expression(const char *source, double *value) {
    if (!source || !*source || !value || strlen(source) > 255)
        return MU_SOCIAL_FORMULA_INVALID;
    char s[256];
    size_t size = 0;
    int open = 0, close = 0;
    for (size_t i = 0; source[i]; i++)
        if (source[i] != ' ') {
            s[size++] = source[i];
            open += source[i] == '(';
            close += source[i] == ')';
        }
    s[size] = 0;
    if (!size || open != close)
        return MU_SOCIAL_FORMULA_INVALID;
    token postfix[256], previous = {0};
    int output = 0, ops[256], depth = 0, negative = 0;
    for (size_t at = 0; at < size;) {
        token t;
        if (!next(s, &at, &t))
            return MU_SOCIAL_FORMULA_INVALID;
        if (t.kind == 1) {
            if (output >= 255)
                return MU_SOCIAL_FORMULA_OVERFLOW;
            if (negative) {
                size_t n = strlen(t.text);
                if (n + 1 >= sizeof t.text)
                    return MU_SOCIAL_FORMULA_OVERFLOW;
                memmove(t.text + 1, t.text, n + 1);
                t.text[0] = '-';
                negative = 0;
            }
            postfix[output++] = t;
        } else if ((t.op == '+' || t.op == '-') &&
                   (!previous.kind || (previous.kind == 2 && previous.op != ')'))) {
            if (t.op == '-')
                negative = !negative;
        } else if (negative && t.op == '(') {
            negative = 0;
            if (output >= 255 || depth > 253)
                return MU_SOCIAL_FORMULA_OVERFLOW;
            token minus_one = {0};
            minus_one.kind = 1;
            memcpy(minus_one.text, "-1", 3);
            postfix[output++] = minus_one;
            ops[depth++] = '*';
            ops[depth++] = '(';
        } else if (t.op == ')') {
            while (depth) {
                int p = ops[--depth];
                if (p == '(')
                    break;
                if (!emit(postfix, &output, p))
                    return MU_SOCIAL_FORMULA_OVERFLOW;
            }
        } else {
            while (depth && priority(ops[depth - 1], 1) <= priority(t.op, 0)) {
                int p = ops[--depth];
                if (p != '(' && !emit(postfix, &output, p))
                    return MU_SOCIAL_FORMULA_OVERFLOW;
            }
            if (depth >= 255)
                return MU_SOCIAL_FORMULA_OVERFLOW;
            ops[depth++] = t.op;
        }
        previous = t;
    }
    while (depth) {
        int p = ops[--depth];
        if (p != '(' && !emit(postfix, &output, p))
            return MU_SOCIAL_FORMULA_OVERFLOW;
    }
    double stack[256];
    int n = 0;
    for (int i = 0; i < output; i++) {
        token *t = postfix + i;
        if (t->kind == 1) {
            if (n >= 255)
                return MU_SOCIAL_FORMULA_OVERFLOW;
            stack[n++] = strtod(t->text, NULL);
            continue;
        }
        if (n < 2)
            return MU_SOCIAL_FORMULA_INVALID;
        double rhs = stack[--n], lhs = stack[--n], v;
        switch (t->op) {
        case '+':
            v = lhs + rhs;
            break;
        case '-':
            v = lhs - rhs;
            break;
        case '*':
            v = lhs * rhs;
            break;
        case '/':
            v = lhs / rhs;
            break;
        case '^':
            v = pow(lhs, rhs);
            break;
        default:
            return MU_SOCIAL_FORMULA_INVALID;
        }
#ifdef MU_SOCIAL2_MUTATION_FORMULA_ROUND
        stack[n++] = v;
#else
        char decimal[64];
        snprintf(decimal, sizeof decimal, "%.10g", v);
        stack[n++] = strtod(decimal, NULL);
#endif
    }
    if (n != 1)
        return MU_SOCIAL_FORMULA_INVALID;
    *value = stack[0];
    return MU_SOCIAL_FORMULA_OK;
}
int mu_social_formula_evaluate(const char *pattern, const mu_social_formula_arg *args, size_t count,
                               double *value) {
    if (!pattern) {
        if (!value)
            return MU_SOCIAL_FORMULA_INVALID;
        *value = 0;
        return MU_SOCIAL_FORMULA_MISSING;
    }
    char expression[256];
    int status = mu_social_formula_expand(pattern, args, count, expression);
    return status == MU_SOCIAL_FORMULA_OK ? mu_social_formula_expression(expression, value) : status;
}
