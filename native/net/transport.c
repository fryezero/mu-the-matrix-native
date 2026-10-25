/* NET-LINK-001: the transport wrapper (the one interface over sockets, fixture loopback and
 * replay), the link calls and endpoint helpers. See mu_transport.h and mu_link.h. */
#include "mu_link.h"

#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

struct mu_transport {
    const mu_transport_ops *ops;
    void *self;
};

mu_transport *mu_transport_wrap(const mu_transport_ops *ops, void *self)
{
    if (!ops)
        return NULL;
    mu_transport *t = calloc(1, sizeof *t);
    if (!t)
        return NULL;
    t->ops = ops;
    t->self = self;
    return t;
}

void *mu_transport_impl(const mu_transport *t, const mu_transport_ops *ops)
{
    return t && t->ops == ops ? t->self : NULL;
}

void mu_transport_free(mu_transport *t)
{
    if (!t)
        return;
    if (t->ops->free)
        t->ops->free(t->self);
    free(t);
}

int mu_transport_poll(mu_transport *t, uint32_t now_ms)
{
    return t && t->ops->poll ? t->ops->poll(t->self, now_ms) : 0;
}

size_t mu_transport_flush(mu_transport *t)
{
    return t && t->ops->flush ? t->ops->flush(t->self) : 0;
}

void mu_transport_counters_get(const mu_transport *t, mu_transport_counters *out)
{
    memset(out, 0, sizeof *out);
    if (t && t->ops->counters)
        t->ops->counters(t->self, out);
}

mu_link_id mu_link_open(mu_transport *t, const mu_endpoint *e)
{
    return t && e && t->ops->open ? t->ops->open(t->self, e) : -1;
}

int mu_link_allow(mu_transport *t, const mu_endpoint *e)
{
    return t && e && t->ops->allow ? t->ops->allow(t->self, e) : -1;
}

mu_link_state mu_link_state_of(mu_transport *t, mu_link_id id, int *error_code)
{
    if (error_code)
        *error_code = 0;
    if (!t || id < 0 || !t->ops->state)
        return MU_LINK_CLOSED;
    return t->ops->state(t->self, id, error_code);
}

size_t mu_link_read(mu_transport *t, mu_link_id id, uint8_t *out, size_t cap)
{
    if (!t || id < 0 || !cap || !t->ops->read)
        return 0;
    return t->ops->read(t->self, id, out, cap);
}

int mu_link_write(mu_transport *t, mu_link_id id, const uint8_t *p, size_t n)
{
    if (!t || id < 0 || !t->ops->write)
        return -1;
    if (!n)
        return 0;
    return t->ops->write(t->self, id, p, n);
}

void mu_link_close(mu_transport *t, mu_link_id id)
{
    if (t && id >= 0 && t->ops->close)
        t->ops->close(t->self, id);
}

int mu_endpoint_equal(const mu_endpoint *a, const mu_endpoint *b)
{
    return a->port == b->port && strcasecmp(a->host, b->host) == 0;
}

int mu_endpoint_parse(mu_endpoint *e, const char *text)
{
    memset(e, 0, sizeof *e);
    if (!text)
        return -1;
    const char *colon = strrchr(text, ':');
    if (!colon || colon == text)
        return -1;
    size_t n = (size_t)(colon - text);
    if (n >= sizeof e->host)
        return -1;
    memcpy(e->host, text, n);
    e->host[n] = 0;
    char *end = NULL;
    long port = strtol(colon + 1, &end, 10);
    if (!end || *end || port <= 0 || port > 65535)
        return -1;
    e->port = (uint16_t)port;
    return 0;
}

int mu_endpoint_is_loopback(const mu_endpoint *e)
{
    if (!strcasecmp(e->host, "localhost") || !strcmp(e->host, "::1"))
        return 1;
    /* 127.0.0.0/8 in dotted form only (no DNS lookup decides this) */
    if (strncmp(e->host, "127.", 4) != 0)
        return 0;
    int dots = 0;
    for (const char *p = e->host; *p; ++p) {
        if (*p == '.')
            ++dots;
        else if (!isdigit((unsigned char)*p))
            return 0;
    }
    return dots == 3;
}
