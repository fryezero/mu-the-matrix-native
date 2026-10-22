/* Internal helpers of reconstructed/progress (NATIVE-PROGRESS-001). */
#ifndef MU_PROGRESS_INTERNAL_H
#define MU_PROGRESS_INTERNAL_H

#include <stdarg.h>
#include <stdio.h>

#include "progress.h"

#ifndef MU_PROGRESS_MUTATION
#define MU_PROGRESS_MUTATION 0
#endif

#if defined(__GNUC__)
__attribute__((format(printf, 2, 3)))
#endif
static inline void mu_prg_emitf(const mu_prg_env *e, const char *fmt, ...)
{
    char line[2048];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    if (e && e->emit)
        e->emit(e->user, line);
}

/* JSON string body of s (Latin-1 bytes, the movies' GFx strings), into out */
static inline void mu_prg_json(char *out, size_t cap, const char *s)
{
    size_t n = 0;
    if (cap < 3) {
        if (cap)
            out[0] = 0;
        return;
    }
    out[n++] = '"';
    for (; s && *s && n + 7 < cap; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') {
            out[n++] = '\\';
            out[n++] = (char)c;
        } else if (c < 0x20) {
            n += (size_t)snprintf(out + n, cap - n, "\\u%04x", c);
        } else {
            out[n++] = (char)c;
        }
    }
    out[n++] = '"';
    out[n] = 0;
}

/* cvttsd2si / cvttss2si: out of range or NaN gives 0x80000000 */
static inline int32_t mu_prg_cvtt(double v)
{
    if (!(v > -2147483649.0 && v < 2147483648.0))
        return INT32_MIN;
    return (int32_t)v;
}

/* __dtol3 0x0191c250: double -> int64 truncation; out of range gives 0x8000000000000000 */
static inline int64_t mu_prg_dtol(double v)
{
    if (!(v >= -9223372036854775808.0 && v < 9223372036854775808.0))
        return INT64_MIN;
    return (int64_t)v;
}

#endif
