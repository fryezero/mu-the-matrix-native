/* NET-LINK-001: the transport's private side. Included only by native/net, native/session and
 * native/fixture (scripts/audit_includes.py fails `make test` otherwise).
 *
 * A link is one byte stream to one peer. mu_transport_ops is the extension point the
 * transports implement; the connection layer (mu_conn.h) is the only caller of mu_link_* in
 * the client. mu_transport_wrap is the loopback hook: the fixture server implements the ops
 * in-process and hands the wrapped transport to a session exactly where the product passes
 * mu_transport_sockets.
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
    int (*allow)(void *self, const mu_endpoint *e);                     /* add a session-learned endpoint */
    mu_link_state (*state)(void *self, mu_link_id id, int *error_code);
    size_t (*read)(void *self, mu_link_id id, uint8_t *out, size_t cap); /* bytes already polled */
    int (*write)(void *self, mu_link_id id, const uint8_t *p, size_t n); /* queue; flush sends */
    void (*close)(void *self, mu_link_id id);
    int (*poll)(void *self, uint32_t now_ms);
    size_t (*flush)(void *self);
    void (*free)(void *self);
    /* optional (NULL: zero counters) */
    void (*counters)(const void *self, mu_transport_counters *out);
} mu_transport_ops;

/* Wraps an implementation (used by the constructors and by mu_fixture_transport). The wrapper
 * owns `self` once wrapped: mu_transport_free calls ops->free(self). NULL on allocation failure. */
mu_transport *mu_transport_wrap(const mu_transport_ops *ops, void *self);
/* The implementation behind a wrapper when its ops are `ops` (else NULL): lets the fixture find
 * its own state from the transport it handed out. */
void *mu_transport_impl(const mu_transport *t, const mu_transport_ops *ops);

/* A link id is valid until mu_link_close; a refused or failed open still returns an id whose
 * state is MU_LINK_REFUSED / MU_LINK_CLOSED (so the caller has one place to read why), or -1
 * when every link slot is in use. */
mu_link_id mu_link_open(mu_transport *t, const mu_endpoint *e);
int mu_link_allow(mu_transport *t, const mu_endpoint *e);
mu_link_state mu_link_state_of(mu_transport *t, mu_link_id id, int *error_code);
size_t mu_link_read(mu_transport *t, mu_link_id id, uint8_t *out, size_t cap);
int mu_link_write(mu_transport *t, mu_link_id id, const uint8_t *p, size_t n);
void mu_link_close(mu_transport *t, mu_link_id id);

/* Endpoint equality as the allowlist compares (case-insensitive host, equal port). */
int mu_endpoint_equal(const mu_endpoint *a, const mu_endpoint *b);

/* The client lock (transport_lock.c), taken by mu_transport_sockets; rules in mu_transport.h. */
typedef struct mu_client_lock {
    int fd;                      /* the flock(2)ed per-user lock file, -1 when not held */
} mu_client_lock;
mu_transport_status mu_client_lock_take(mu_client_lock *lock, char *error, size_t error_size);
void mu_client_lock_release(mu_client_lock *lock);
/* The first running process (other than this one) whose name or argument list names one of the
 * comma-separated `names` (basename after '/' or '\\', case-insensitive). Returns its pid and a
 * short description, or 0. */
int mu_client_lock_find_process(const char *names, char *what, size_t what_size);

#endif /* MU_LINK_H */
