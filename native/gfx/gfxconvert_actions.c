/* The same authored AVM1 host bridge as gfxconvert.py, assembled without a VM. */
#include "gfxconvert.h"
#include <string.h>
#include <stdlib.h>
#include <errno.h>
static Buf push_string(const char *s) { Buf b = {0}; byte(&b, 0); strz(&b, s); return b; }
static Buf push_int(int32_t i) { Buf b = {0}; byte(&b, 7); dword(&b, (uint32_t)i); return b; }
static void push(Buf *b, Buf values) { byte(b, 0x96); if (values.n > 65535) fail("AVM push too long"); word(b, (unsigned)values.n); add(b, values.p, values.n); }
static void ps(Buf *b, const char *s) { push(b, push_string(s)); }
static void both(Buf *b, const char *a, const char *c) { Buf v = push_string(a); Buf w = push_string(c); add(&v, w.p, w.n); push(b, v); }
static void function(Buf *b, const char **params, unsigned n, Buf body) {
    Buf p = {0}; byte(&p, 0); word(&p, n); for (unsigned i = 0; i < n; i++) strz(&p, params[i]);
    word(&p, (unsigned)body.n); byte(b, 0x9b); word(b, (unsigned)p.n); add(b, p.p, p.n); add(b, body.p, body.n);
}
static void callback(Buf *b, const char *name, const char **params, unsigned n, Buf body) {
    function(b, params, n, body);
    Buf v = {0}; byte(&v, 2); Buf s = push_string(name); add(&v, s.p, s.n);
    s = push_int(3); add(&v, s.p, s.n); s = push_string("flash"); add(&v, s.p, s.n); push(b, v);
    byte(b, 0x1c); ps(b, "external"); byte(b, 0x4e); ps(b, "ExternalInterface"); byte(b, 0x4e);
    ps(b, "addCallback"); byte(b, 0x52); byte(b, 0x17);
}
Buf host_actions(char **vars, int count, int bridge) {
    Buf b = {0};
    for (int i = 0; i < count; i++) {
        const char *eq = strchr(vars[i], '='); size_t n = eq ? (size_t)(eq - vars[i]) : strlen(vars[i]);
        char *key = mem(n + 1); memcpy(key, vars[i], n); const char *value = eq ? eq + 1 : "";
        // Python's dict keeps the first position and the last value for a repeated key.
        int first = 1;
        for (int j = 0; j < count; j++) {
            const char *other = strchr(vars[j], '=');
            size_t len = other ? (size_t)(other - vars[j]) : strlen(vars[j]);
            if (len == n && !memcmp(key, vars[j], n)) {
                if (j < i) first = 0;
                if (j > i) value = other ? other + 1 : "";
            }
        }
        if (!first) continue;
        Buf v = push_string(key);
        if (!strcmp(value, "true") || !strcmp(value, "false")) { byte(&v, 5); byte(&v, !strcmp(value, "true")); }
        else {
            char *end; errno = 0; long long integer = strtoll(value, &end, 10);
            if (*value && !*end) {
                if (errno || integer < INT32_MIN || integer > INT32_MAX) fail("AVM integer out of range");
                Buf w = push_int((int32_t)integer); add(&v, w.p, w.n);
            } else { Buf w = push_string(value); add(&v, w.p, w.n); }
        }
        push(&b, v); byte(&b, 0x1d);
    }
    if (bridge) {
        Buf invoke = {0}, setter = {0}, getter = {0};
        both(&invoke, "o", "path"); byte(&invoke, 0x1c); byte(&invoke, 0x1c); byte(&invoke, 0x3c);
        ps(&invoke, "args"); byte(&invoke, 0x1c); ps(&invoke, "o"); byte(&invoke, 0x1c); push(&invoke, push_int(2));
        ps(&invoke, "o"); byte(&invoke, 0x1c); ps(&invoke, "method"); byte(&invoke, 0x1c); byte(&invoke, 0x4e);
        ps(&invoke, "apply"); byte(&invoke, 0x52); byte(&invoke, 0x3e);
        ps(&setter, "path"); byte(&setter, 0x1c); ps(&setter, "value"); byte(&setter, 0x1c); byte(&setter, 0x1d);
        ps(&getter, "path"); byte(&getter, 0x1c); byte(&getter, 0x1c); byte(&getter, 0x3e);
        const char *ip[] = {"path", "method", "args"}, *sp[] = {"path", "value"}, *gp[] = {"path"};
        callback(&b, "__mu_invoke", ip, 3, invoke); callback(&b, "__mu_set", sp, 2, setter); callback(&b, "__mu_get", gp, 1, getter);
    }
    byte(&b, 0); return b;
}
