/* NET-LINK-001 (sketch): the transport's private side. Included only by native/net,
 * native/session and native/fixture (scripts/audit_includes.py fails the build otherwise).
 *
 * A link is one byte stream to one peer. mu_transport_ops is the extension point the three
 * transports implement; the session's connection layer (mu_conn.h) is the only caller of
 * mu_link_* in the client.
 */
#ifndef MU_LINK_H
#define MU_LINK_H

#include "mu_transport.h"

#define MU_LINKS 4               /* connect server, game server, chat server, one spare for a server change */

typedef int32_t mu_link_id;      /* -1: none */

typedef enum mu_link_state {
    MU_LINK_CONNECTING = 0, MU_LINK_OPEN, MU_LINK_CLOSED, MU_LINK_REFUSED
} mu_link_state;

typedef struct mu_transport_ops {
    mu_link_id (*open)(void *self, const mu_endpoint *e);               /* refuses non-allowed endpoints */
    int (*allow)(void *self, const mu_endpoint *e);                    /* add a session-learned endpoint */
    mu_link_state (*state)(void *self, mu_link_id id, int *error_code);
    size_t (*read)(void *self, mu_link_id id, uint8_t *out, size_t cap); /* bytes already polled */
    int (*write)(void *self, mu_link_id id, const uint8_t *p, size_t n); /* queue; flush sends */
    void (*close)(void *self, mu_link_id id);
    int (*poll)(void *self, uint32_t now_ms);
    size_t (*flush)(void *self);
    void (*free)(void *self);
} mu_transport_ops;

/* Wraps an implementation (used by the three constructors and by mu_fixture_transport). */
mu_transport *mu_transport_wrap(const mu_transport_ops *ops, void *self);

mu_link_id mu_link_open(mu_transport *t, const mu_endpoint *e);
int mu_link_allow(mu_transport *t, const mu_endpoint *e);
mu_link_state mu_link_state_of(mu_transport *t, mu_link_id id, int *error_code);
size_t mu_link_read(mu_transport *t, mu_link_id id, uint8_t *out, size_t cap);
int mu_link_write(mu_transport *t, mu_link_id id, const uint8_t *p, size_t n);
void mu_link_close(mu_transport *t, mu_link_id id);

#endif /* MU_LINK_H */
