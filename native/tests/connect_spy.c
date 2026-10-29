/* The connect spy (TEST-FLAKE-001): a test-only library that records the calls a process makes at
 * the socket boundary and passes every one of them through unchanged.
 *
 * native/tests/test_transport.py loads it into a child interpreter (DYLD_INSERT_LIBRARIES on macOS,
 * LD_PRELOAD elsewhere) to prove the allowlist refuses an endpoint before any socket(2), getaddrinfo
 * or connect(2): the proof is what the process itself called, so no other process can disturb it (a
 * listener's accept window can: an app that probes new loopback listeners connects to it).
 *
 * Recorded: getaddrinfo (the port text), socket (the family), connect and connectx (the destination
 * port of an AF_INET/AF_INET6 address, else 0). mu_connect_spy_reset clears the record and
 * mu_connect_spy_events copies it out. Whether the hooks are live (the library was inserted, not
 * merely dlopen'ed) is shown by the test's positive control: the allowed open must be recorded. */
#define _GNU_SOURCE
#include <netdb.h>
#include <netinet/in.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <sys/types.h>

#define SPY_CAP 64

enum { SPY_GETADDRINFO = 1, SPY_SOCKET = 2, SPY_CONNECT = 3 };

static int kinds[SPY_CAP];
static int values[SPY_CAP];
static volatile int count;

static void record(int kind, int value)
{
    int i = __atomic_fetch_add(&count, 1, __ATOMIC_RELAXED);
    if (i < SPY_CAP) {
        kinds[i] = kind;
        values[i] = value;
    }
}

static int port_of(const struct sockaddr *a)
{
    if (a && a->sa_family == AF_INET)
        return ntohs(((const struct sockaddr_in *)(const void *)a)->sin_port);
    if (a && a->sa_family == AF_INET6)
        return ntohs(((const struct sockaddr_in6 *)(const void *)a)->sin6_port);
    return 0;
}

static int service_port(const char *service)
{
    return service ? atoi(service) : -1;
}

void mu_connect_spy_reset(void)
{
    __atomic_store_n(&count, 0, __ATOMIC_RELAXED);
}

/* copies up to cap events; returns how many were recorded (more than cap means some were dropped) */
int mu_connect_spy_events(int *out_kinds, int *out_values, int cap)
{
    int n = __atomic_load_n(&count, __ATOMIC_RELAXED);
    for (int i = 0; i < n && i < cap && i < SPY_CAP; ++i) {
        out_kinds[i] = kinds[i];
        out_values[i] = values[i];
    }
    return n;
}

#ifdef __APPLE__

#define INTERPOSE(replacement, replacee)                                                                    \
    __attribute__((used)) static const struct {                                                              \
        const void *r;                                                                                       \
        const void *e;                                                                                       \
    } interpose_##replacee __attribute__((section("__DATA,__interpose"))) = {(const void *)&replacement,       \
                                                                             (const void *)&replacee}

static int spy_socket(int domain, int type, int protocol)
{
    if (domain != AF_UNIX)
        record(SPY_SOCKET, domain);
    return socket(domain, type, protocol);
}
INTERPOSE(spy_socket, socket);

static int spy_connect(int fd, const struct sockaddr *address, socklen_t length)
{
    if (!address || address->sa_family != AF_UNIX)
        record(SPY_CONNECT, port_of(address));
    return connect(fd, address, length);
}
INTERPOSE(spy_connect, connect);

static int spy_connectx(int fd, const sa_endpoints_t *endpoints, sae_associd_t associd, unsigned int flags,
                        const struct iovec *iov, unsigned int iovcnt, size_t *len, sae_connid_t *connid)
{
    record(SPY_CONNECT, endpoints ? port_of(endpoints->sae_dstaddr) : 0);
    return connectx(fd, endpoints, associd, flags, iov, iovcnt, len, connid);
}
INTERPOSE(spy_connectx, connectx);

static int spy_getaddrinfo(const char *node, const char *service, const struct addrinfo *hints,
                           struct addrinfo **result)
{
    record(SPY_GETADDRINFO, service_port(service));
    return getaddrinfo(node, service, hints, result);
}
INTERPOSE(spy_getaddrinfo, getaddrinfo);

#else

#include <dlfcn.h>

/* LD_PRELOAD: these definitions come first in symbol lookup; the real calls are the next ones */
int socket(int domain, int type, int protocol)
{
    static int (*real)(int, int, int);
    if (!real)
        real = (int (*)(int, int, int))dlsym(RTLD_NEXT, "socket");
    if (domain != AF_UNIX)
        record(SPY_SOCKET, domain);
    return real(domain, type, protocol);
}

int connect(int fd, const struct sockaddr *address, socklen_t length)
{
    static int (*real)(int, const struct sockaddr *, socklen_t);
    if (!real)
        real = (int (*)(int, const struct sockaddr *, socklen_t))dlsym(RTLD_NEXT, "connect");
    if (!address || address->sa_family != AF_UNIX)
        record(SPY_CONNECT, port_of(address));
    return real(fd, address, length);
}

int getaddrinfo(const char *node, const char *service, const struct addrinfo *hints, struct addrinfo **result)
{
    static int (*real)(const char *, const char *, const struct addrinfo *, struct addrinfo **);
    if (!real)
        real = (int (*)(const char *, const char *, const struct addrinfo *, struct addrinfo **))dlsym(
            RTLD_NEXT, "getaddrinfo");
    record(SPY_GETADDRINFO, service_port(service));
    return real(node, service, hints, result);
}

#endif
