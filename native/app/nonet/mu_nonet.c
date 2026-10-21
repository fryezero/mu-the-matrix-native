/* mu-nonet: the preview app's network guard (NATIVE-APP-001).
 *
 * The native client has no network layer (the protocol is out of scope), and the
 * preview app promises "no server connection". The launcher loads this library into
 * mu-client with DYLD_INSERT_LIBRARIES (the bundle is ad-hoc signed without the
 * hardened runtime, so dyld honours it) and dyld's interposing routes every call of
 * the socket API below, from mu-client and from every library it loads, here:
 *
 *   socket / socketpair   AF_UNIX (local IPC some system frameworks use) is counted
 *                         and allowed unless MU_NONET_STRICT=1; every other family
 *                         (AF_INET, AF_INET6, AF_SYSTEM, AF_ROUTE, ...) fails with EACCES;
 *   connect / connectx    to anything but AF_UNIX: EACCES;
 *   getaddrinfo           EAI_FAIL (no name lookups).
 *
 * Every refusal is printed to stderr (the launcher's log). MU_NONET_REPORT=FILE names a
 * JSON report, written when the library loads (proof that the guard is active) and
 * again at exit: {"guard": "mu-nonet", "pid": ..., "inet_denied": N, "other_denied": N,
 * "unix_sockets": N, "connects_denied": N, "lookups_denied": N}. */
#include <errno.h>
#include <netdb.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define INTERPOSE(replacement, replacee)                                                                    \
    __attribute__((used)) static const struct {                                                              \
        const void *r;                                                                                       \
        const void *e;                                                                                       \
    } interpose_##replacee __attribute__((section("__DATA,__interpose"))) = {(const void *)&replacement,       \
                                                                             (const void *)&replacee}

static volatile long inet_denied, other_denied, unix_sockets, connects_denied, lookups_denied;

static int strict_mode(void)
{
    const char *v = getenv("MU_NONET_STRICT");
    return v && v[0] == '1';
}

static void note(const char *what, int value)
{
    char line[160];
    int n = snprintf(line, sizeof line, "mu-nonet: refused %s (%d) in pid %d\n", what, value, (int)getpid());
    if (n > 0)
        (void)!write(2, line, (size_t)n < sizeof line ? (size_t)n : sizeof line - 1);
}

static void write_report(const char *phase)
{
    const char *path = getenv("MU_NONET_REPORT");
    if (!path || !path[0])
        return;
    FILE *f = fopen(path, "w");
    if (!f)
        return;
    fprintf(f,
            "{\"guard\": \"mu-nonet\", \"phase\": \"%s\", \"pid\": %d, \"strict\": %d, \"inet_denied\": %ld, "
            "\"other_denied\": %ld, \"unix_sockets\": %ld, \"connects_denied\": %ld, \"lookups_denied\": %ld}\n",
            phase, (int)getpid(), strict_mode(), inet_denied, other_denied, unix_sockets, connects_denied,
            lookups_denied);
    fclose(f);
}

__attribute__((constructor)) static void nonet_load(void)
{
    write_report("loaded");
}

__attribute__((destructor)) static void nonet_unload(void)
{
    write_report("exit");
}

static int family_allowed(int domain, const char *call)
{
    if (domain == AF_UNIX && !strict_mode()) {
        __atomic_add_fetch(&unix_sockets, 1, __ATOMIC_RELAXED);
        return 1;
    }
    if (domain == AF_INET || domain == AF_INET6)
        __atomic_add_fetch(&inet_denied, 1, __ATOMIC_RELAXED);
    else
        __atomic_add_fetch(&other_denied, 1, __ATOMIC_RELAXED);
    note(call, domain);
    return 0;
}

static int nonet_socket(int domain, int type, int protocol)
{
    if (!family_allowed(domain, "socket(domain)")) {
        errno = EACCES;
        return -1;
    }
    return socket(domain, type, protocol);
}
INTERPOSE(nonet_socket, socket);

static int nonet_socketpair(int domain, int type, int protocol, int sv[2])
{
    if (!family_allowed(domain, "socketpair(domain)")) {
        errno = EACCES;
        return -1;
    }
    return socketpair(domain, type, protocol, sv);
}
INTERPOSE(nonet_socketpair, socketpair);

static int nonet_connect(int fd, const struct sockaddr *address, socklen_t length)
{
    if (!address || address->sa_family != AF_UNIX || strict_mode()) {
        __atomic_add_fetch(&connects_denied, 1, __ATOMIC_RELAXED);
        note("connect(family)", address ? address->sa_family : -1);
        errno = EACCES;
        return -1;
    }
    return connect(fd, address, length);
}
INTERPOSE(nonet_connect, connect);

static int nonet_connectx(int fd, const sa_endpoints_t *endpoints, sae_associd_t associd, unsigned int flags,
                          const struct iovec *iov, unsigned int iovcnt, size_t *len, sae_connid_t *connid)
{
    (void)fd, (void)associd, (void)flags, (void)iov, (void)iovcnt, (void)len, (void)connid;
    __atomic_add_fetch(&connects_denied, 1, __ATOMIC_RELAXED);
    note("connectx(family)", endpoints && endpoints->sae_dstaddr ? endpoints->sae_dstaddr->sa_family : -1);
    errno = EACCES;
    return -1;
}
INTERPOSE(nonet_connectx, connectx);

static int nonet_getaddrinfo(const char *node, const char *service, const struct addrinfo *hints,
                             struct addrinfo **result)
{
    (void)service, (void)hints;
    __atomic_add_fetch(&lookups_denied, 1, __ATOMIC_RELAXED);
    note(node ? "getaddrinfo(node)" : "getaddrinfo", 0);
    if (result)
        *result = NULL;
    return EAI_FAIL;
}
INTERPOSE(nonet_getaddrinfo, getaddrinfo);
