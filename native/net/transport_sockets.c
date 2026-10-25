/* NET-LINK-001: the product transport - nonblocking BSD sockets with the endpoint allowlist and
 * the client lock (transport_lock.c).
 *
 * Readiness comes from kqueue on macOS (EVFILT_READ per link; a one-shot EVFILT_WRITE while a
 * connect is in progress) and from poll(2) on other hosts, so the portable tests build on Linux.
 * Everything runs on the caller's thread, with zero timeouts: poll() never blocks.
 *
 * Buffers. Inbound bytes are read into a per-link buffer of at most LINK_IN_CAP bytes; while it is
 * full the socket is not read and the peer's bytes stay in the kernel (backpressure, as the client,
 * whose recv 0x012907ee asks for at most 0x2000 - recvlen bytes). Outbound bytes are queued by
 * write and sent by flush; a partial send keeps the rest queued for the next flush, like the
 * client's FD_WRITE drain 0x012906d4.
 *
 * Name resolution (getaddrinfo) happens in open and may block on DNS; the allowlist is checked on
 * the configured host text before any lookup, so a refused endpoint is never resolved.
 */
#define _DARWIN_C_SOURCE 1
#define _DEFAULT_SOURCE 1
#include "mu_link.h"

#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#if defined(__APPLE__) || defined(__FreeBSD__)
#define MU_HAVE_KQUEUE 1
#include <sys/event.h>
#include <sys/time.h>
#else
#define MU_HAVE_KQUEUE 0
#include <poll.h>
#endif

#ifndef MSG_NOSIGNAL
#define MSG_NOSIGNAL 0
#endif

#define ALLOW_MAX 16
#define LINK_IN_CAP (64u * 1024u)

typedef struct sock_link {
    int used;
    int fd;
    mu_link_state state;
    int error;
    int eof;                     /* the peer closed; the buffered bytes are still readable */
    mu_endpoint ep;
    uint8_t *in;
    size_t in_len;
    uint8_t *out;
    size_t out_len, out_cap;
} sock_link;

typedef struct sockets {
    mu_endpoint allow[ALLOW_MAX];
    size_t nallow;
    sock_link links[MU_LINKS];
    int kq;
    mu_client_lock lock;
    mu_transport_counters c;
} sockets;

static int allowed(const sockets *s, const mu_endpoint *e)
{
    for (size_t i = 0; i < s->nallow; ++i)
        if (mu_endpoint_equal(&s->allow[i], e))
            return 1;
    return 0;
}

static int s_allow(void *self, const mu_endpoint *e)
{
    sockets *s = self;
    if (allowed(s, e))
        return 0;
    if (s->nallow >= ALLOW_MAX)
        return -1;
    s->allow[s->nallow++] = *e;
    return 0;
}

static void link_drop(sockets *s, sock_link *l, mu_link_state state, int error)
{
    if (l->fd >= 0) {
        close(l->fd);   /* closing also removes the fd's kqueue filters */
        l->fd = -1;
    }
    (void)s;
    l->state = state;
    l->error = error;
    l->out_len = 0;
}

static void watch(sockets *s, sock_link *l, int connecting)
{
#if MU_HAVE_KQUEUE
    struct kevent ev[2];
    int n = 0;
    void *udata = (void *)(intptr_t)(l - s->links);
    EV_SET(&ev[n++], (uintptr_t)l->fd, EVFILT_READ, EV_ADD, 0, 0, udata);
    if (connecting)
        EV_SET(&ev[n++], (uintptr_t)l->fd, EVFILT_WRITE, EV_ADD | EV_ONESHOT, 0, 0, udata);
    kevent(s->kq, ev, n, NULL, 0, NULL);
#else
    (void)s;
    (void)l;
    (void)connecting;
#endif
}

static mu_link_id s_open(void *self, const mu_endpoint *e)
{
    sockets *s = self;
    int slot = -1;
    for (int i = 0; i < MU_LINKS; ++i)
        if (!s->links[i].used) {
            slot = i;
            break;
        }
    if (slot < 0)
        return -1;
    sock_link *l = &s->links[slot];
    memset(l, 0, sizeof *l);
    l->used = 1;
    l->fd = -1;
    l->ep = *e;
    if (!allowed(s, e)) {
        l->state = MU_LINK_REFUSED;
        s->c.links_refused++;
        return slot;
    }
    l->in = malloc(LINK_IN_CAP);
    if (!l->in) {
        l->state = MU_LINK_CLOSED;
        l->error = ENOMEM;
        return slot;
    }
    s->c.connects_attempted++;
    char port[8];
    snprintf(port, sizeof port, "%u", (unsigned)e->port);
    struct addrinfo hints, *res = NULL;
    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    int gai = getaddrinfo(e->host, port, &hints, &res);
    if (gai != 0 || !res) {
        l->state = MU_LINK_CLOSED;
        l->error = EHOSTUNREACH;
        return slot;
    }
    int fd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (fd < 0) {
        l->state = MU_LINK_CLOSED;
        l->error = errno;
        freeaddrinfo(res);
        return slot;
    }
    int flags = fcntl(fd, F_GETFL, 0);
    fcntl(fd, F_SETFL, flags | O_NONBLOCK);
    fcntl(fd, F_SETFD, FD_CLOEXEC);
#ifdef SO_NOSIGPIPE
    int one = 1;
    setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof one);
#endif
    l->fd = fd;
    int rc = connect(fd, res->ai_addr, res->ai_addrlen);
    freeaddrinfo(res);
    s->c.links_opened++;
    if (rc == 0) {
        l->state = MU_LINK_OPEN;
        watch(s, l, 0);
    } else if (errno == EINPROGRESS) {
        l->state = MU_LINK_CONNECTING;
        watch(s, l, 1);
    } else {
        link_drop(s, l, MU_LINK_CLOSED, errno);
    }
    return slot;
}

static sock_link *get(sockets *s, mu_link_id id)
{
    return id >= 0 && id < MU_LINKS && s->links[id].used ? &s->links[id] : NULL;
}

static mu_link_state s_state(void *self, mu_link_id id, int *error_code)
{
    sock_link *l = get(self, id);
    if (!l)
        return MU_LINK_CLOSED;
    if (error_code)
        *error_code = l->error;
    /* a peer close is reported once the bytes it sent before closing are consumed */
    if (l->eof && l->in_len == 0 && l->state == MU_LINK_OPEN)
        return MU_LINK_CLOSED;
    return l->state;
}

static size_t s_read(void *self, mu_link_id id, uint8_t *out, size_t cap)
{
    sock_link *l = get(self, id);
    if (!l || !l->in_len)
        return 0;
    size_t n = l->in_len < cap ? l->in_len : cap;
    memcpy(out, l->in, n);
    memmove(l->in, l->in + n, l->in_len - n);
    l->in_len -= n;
    return n;
}

static int s_write(void *self, mu_link_id id, const uint8_t *p, size_t n)
{
    sockets *s = self;
    sock_link *l = get(s, id);
    if (!l || (l->state != MU_LINK_OPEN && l->state != MU_LINK_CONNECTING) || l->eof)
        return -1;
    if (l->out_len + n > l->out_cap) {
        size_t cap = l->out_cap ? l->out_cap : 4096;
        while (cap < l->out_len + n)
            cap *= 2;
        uint8_t *q = realloc(l->out, cap);
        if (!q)
            return -1;
        l->out = q;
        l->out_cap = cap;
    }
    memcpy(l->out + l->out_len, p, n);
    l->out_len += n;
    return 0;
}

static void s_close(void *self, mu_link_id id)
{
    sockets *s = self;
    sock_link *l = get(s, id);
    if (!l)
        return;
    link_drop(s, l, MU_LINK_CLOSED, 0);
    free(l->in);
    free(l->out);
    memset(l, 0, sizeof *l);
    l->fd = -1;
}

/* read what the socket has, up to the inbound buffer's room; returns 1 when something changed */
static int link_readable(sockets *s, sock_link *l)
{
    int changed = 0;
    while (l->fd >= 0 && l->in_len < LINK_IN_CAP) {
        ssize_t n = recv(l->fd, l->in + l->in_len, LINK_IN_CAP - l->in_len, 0);
        if (n > 0) {
            l->in_len += (size_t)n;
            s->c.bytes_in += (uint64_t)n;
            changed = 1;
            continue;
        }
        if (n == 0) {
            l->eof = 1;
            close(l->fd);
            l->fd = -1;
            return 1;
        }
        if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)
            break;
        link_drop(s, l, MU_LINK_CLOSED, errno);
        return 1;
    }
    return changed;
}

static int link_connected(sockets *s, sock_link *l)
{
    if (l->state != MU_LINK_CONNECTING || l->fd < 0)
        return 0;
    int err = 0;
    socklen_t len = sizeof err;
    if (getsockopt(l->fd, SOL_SOCKET, SO_ERROR, &err, &len) != 0)
        err = errno;
    if (err)
        link_drop(s, l, MU_LINK_CLOSED, err);
    else
        l->state = MU_LINK_OPEN;
    return 1;
}

static int s_poll(void *self, uint32_t now_ms)
{
    sockets *s = self;
    (void)now_ms;
    int changed = 0;
    uint8_t touched[MU_LINKS] = {0};
#if MU_HAVE_KQUEUE
    struct kevent ev[2 * MU_LINKS];
    struct timespec zero = {0, 0};
    int n = kevent(s->kq, NULL, 0, ev, 2 * MU_LINKS, &zero);
    for (int i = 0; i < n; ++i) {
        intptr_t k = (intptr_t)ev[i].udata;
        if (k < 0 || k >= MU_LINKS || !s->links[k].used || s->links[k].fd != (int)ev[i].ident)
            continue;
        sock_link *l = &s->links[k];
        if (ev[i].filter == EVFILT_WRITE)
            touched[k] |= (uint8_t)link_connected(s, l);
        else if (ev[i].filter == EVFILT_READ && l->state == MU_LINK_OPEN)
            touched[k] |= (uint8_t)link_readable(s, l);
    }
#else
    struct pollfd p[MU_LINKS];
    int idx[MU_LINKS], n = 0;
    for (int k = 0; k < MU_LINKS; ++k) {
        sock_link *l = &s->links[k];
        if (!l->used || l->fd < 0)
            continue;
        p[n].fd = l->fd;
        p[n].events = (short)(l->state == MU_LINK_CONNECTING ? POLLOUT : POLLIN);
        p[n].revents = 0;
        idx[n++] = k;
    }
    if (n > 0 && poll(p, (nfds_t)n, 0) > 0)
        for (int i = 0; i < n; ++i) {
            sock_link *l = &s->links[idx[i]];
            if (l->state == MU_LINK_CONNECTING && (p[i].revents & (POLLOUT | POLLERR | POLLHUP)))
                touched[idx[i]] |= (uint8_t)link_connected(s, l);
            else if (l->state == MU_LINK_OPEN && (p[i].revents & (POLLIN | POLLHUP | POLLERR)))
                touched[idx[i]] |= (uint8_t)link_readable(s, l);
        }
#endif
    for (int k = 0; k < MU_LINKS; ++k)
        changed += touched[k] ? 1 : 0;
    return changed;
}

static size_t s_flush(void *self)
{
    sockets *s = self;
    size_t pending = 0;
    for (int k = 0; k < MU_LINKS; ++k) {
        sock_link *l = &s->links[k];
        if (!l->used || !l->out_len)
            continue;
        if (l->state == MU_LINK_OPEN && l->fd >= 0) {
            size_t sent = 0;
            while (sent < l->out_len) {
                ssize_t n = send(l->fd, l->out + sent, l->out_len - sent, MSG_NOSIGNAL);
                if (n > 0) {
                    sent += (size_t)n;
                    s->c.bytes_out += (uint64_t)n;
                    continue;
                }
                if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR))
                    break;
                link_drop(s, l, MU_LINK_CLOSED, n < 0 ? errno : EPIPE);
                sent = 0;
                break;
            }
            if (sent) {
                memmove(l->out, l->out + sent, l->out_len - sent);
                l->out_len -= sent;
            }
        }
        pending += l->out_len;
    }
    return pending;
}

static void s_counters(const void *self, mu_transport_counters *out)
{
    const sockets *s = self;
    *out = s->c;
}

static void s_free(void *self)
{
    sockets *s = self;
    for (int k = 0; k < MU_LINKS; ++k)
        if (s->links[k].used)
            s_close(s, k);
#if MU_HAVE_KQUEUE
    if (s->kq >= 0)
        close(s->kq);
#endif
    mu_client_lock_release(&s->lock);
    free(s);
}

static const mu_transport_ops SOCKET_OPS = {
    .open = s_open,
    .allow = s_allow,
    .state = s_state,
    .read = s_read,
    .write = s_write,
    .close = s_close,
    .poll = s_poll,
    .flush = s_flush,
    .free = s_free,
    .counters = s_counters,
};

mu_transport *mu_transport_sockets(const mu_endpoint *allowed_eps, size_t count, mu_transport_status *status,
                                   char *error, size_t error_size)
{
    mu_transport_status st_local;
    if (!status)
        status = &st_local;
    *status = MU_TRANSPORT_ERROR;
    if (error_size)
        error[0] = 0;
    if (count > ALLOW_MAX) {
        snprintf(error, error_size, "sockets transport: at most %d allowed endpoints", ALLOW_MAX);
        return NULL;
    }
    sockets *s = calloc(1, sizeof *s);
    if (!s) {
        snprintf(error, error_size, "sockets transport: out of memory");
        return NULL;
    }
    s->kq = -1;
    for (int k = 0; k < MU_LINKS; ++k)
        s->links[k].fd = -1;
    mu_transport_status lock = mu_client_lock_take(&s->lock, error, error_size);
    if (lock != MU_TRANSPORT_OK) {
        *status = lock;
        free(s);
        return NULL;
    }
#if MU_HAVE_KQUEUE
    s->kq = kqueue();
    if (s->kq < 0) {
        snprintf(error, error_size, "sockets transport: kqueue: %s", strerror(errno));
        mu_client_lock_release(&s->lock);
        free(s);
        return NULL;
    }
    fcntl(s->kq, F_SETFD, FD_CLOEXEC);
#endif
    for (size_t i = 0; i < count; ++i)
        s_allow(s, &allowed_eps[i]);
    mu_transport *t = mu_transport_wrap(&SOCKET_OPS, s);
    if (!t) {
        s_free(s);
        snprintf(error, error_size, "sockets transport: out of memory");
        return NULL;
    }
    *status = MU_TRANSPORT_OK;
    return t;
}
