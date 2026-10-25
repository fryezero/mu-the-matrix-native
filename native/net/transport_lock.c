/* NET-LINK-001: the client lock - one client at a time (operator rule, 2026-10-25).
 *
 * Three checks, in this order, before the sockets transport may connect anywhere:
 *   1. no original client runs: a process named main.exe or MuTheMatrix.exe (by its name or any
 *      argument's basename, the way mu-mac-tools' scripts find it with `pgrep -f`); the user is
 *      playing, and the native client must not log the account in elsewhere;
 *   2. under MU_AGENT=1 the shared game lock (mu-mac-tools GAME-LOCK.md) is held by this agent:
 *      $MU_GAME_LOCK_DIR/owner exists and its first line equals MU_LOCK_ID (mu-autologin.sh's
 *      check). The transport never creates or removes that lock;
 *   3. the per-user single-instance lock: flock(2) on MU_CLIENT_LOCK_PATH (or the per-user
 *      default), whose file then carries this process's owner line. flock locks belong to the
 *      open file description, so a second transport in the same process is refused too, and the
 *      kernel drops the lock if the process dies.
 */
#define _DARWIN_C_SOURCE 1
#define _DEFAULT_SOURCE 1
#include "mu_link.h"

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#if defined(__APPLE__)
#include <libproc.h>
#include <sys/sysctl.h>
#endif

#define DEFAULT_PROCESS_NAMES "main.exe,MuTheMatrix.exe"

static int name_listed(const char *names, const char *candidate)
{
    /* basename after the last '/' or '\\' */
    const char *base = candidate;
    for (const char *p = candidate; *p; ++p)
        if (*p == '/' || *p == '\\')
            base = p + 1;
    size_t blen = strlen(base);
    if (!blen)
        return 0;
    const char *n = names;
    while (*n) {
        const char *comma = strchr(n, ',');
        size_t len = comma ? (size_t)(comma - n) : strlen(n);
        while (len && isspace((unsigned char)*n)) {
            ++n;
            --len;
        }
        while (len && isspace((unsigned char)n[len - 1]))
            --len;
        if (len && len == blen && strncasecmp(n, base, len) == 0)
            return 1;
        if (!comma)
            break;
        n = comma + 1;
    }
    return 0;
}

#if defined(__APPLE__)
static int process_matches(pid_t pid, const char *names, char *what, size_t what_size)
{
    char name[2 * MAXCOMLEN + 1];
    if (proc_name(pid, name, sizeof name) > 0 && name_listed(names, name)) {
        snprintf(what, what_size, "pid %d %s", (int)pid, name);
        return 1;
    }
    int mib[3] = {CTL_KERN, KERN_ARGMAX, 0};
    int argmax = 0;
    size_t size = sizeof argmax;
    if (sysctl(mib, 2, &argmax, &size, NULL, 0) != 0 || argmax <= 0)
        return 0;
    char *buf = malloc((size_t)argmax);
    if (!buf)
        return 0;
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROCARGS2;
    mib[2] = (int)pid;
    size = (size_t)argmax;
    int found = 0;
    if (sysctl(mib, 3, buf, &size, NULL, 0) == 0 && size > sizeof(int)) {
        int argc;
        memcpy(&argc, buf, sizeof argc);
        char *p = buf + sizeof(int), *end = buf + size;
        /* the exec path, then NUL padding, then argc argument strings */
        while (p < end && *p)
            ++p;
        while (p < end && !*p)
            ++p;
        for (int i = 0; i < argc && p < end && !found; ++i) {
            char *arg = p;
            while (p < end && *p)
                ++p;
            if (p < end && name_listed(names, arg)) {
                snprintf(what, what_size, "pid %d %.200s", (int)pid, arg);
                found = 1;
            }
            ++p;
        }
    }
    free(buf);
    return found;
}

int mu_client_lock_find_process(const char *names, char *what, size_t what_size)
{
    int n = proc_listallpids(NULL, 0);
    if (n <= 0)
        return 0;
    size_t cap = (size_t)n + 64;
    pid_t *pids = calloc(cap, sizeof *pids);
    if (!pids)
        return 0;
    n = proc_listallpids(pids, (int)(cap * sizeof *pids));
    pid_t self = getpid();
    int hit = 0;
    for (int i = 0; i < n && !hit; ++i)
        if (pids[i] > 0 && pids[i] != self && process_matches(pids[i], names, what, what_size))
            hit = (int)pids[i];
    free(pids);
    return hit;
}
#elif defined(__linux__)
int mu_client_lock_find_process(const char *names, char *what, size_t what_size)
{
    DIR *d = opendir("/proc");
    if (!d)
        return 0;
    struct dirent *de;
    pid_t self = getpid();
    int hit = 0;
    while (!hit && (de = readdir(d))) {
        char *end;
        long pid = strtol(de->d_name, &end, 10);
        if (*end || pid <= 0 || pid == self)
            continue;
        char path[64], buf[4096];
        snprintf(path, sizeof path, "/proc/%ld/cmdline", pid);
        FILE *f = fopen(path, "rb");
        if (!f)
            continue;
        size_t len = fread(buf, 1, sizeof buf - 1, f);
        fclose(f);
        buf[len] = 0;
        for (size_t off = 0; off < len && !hit; off += strlen(buf + off) + 1)
            if (name_listed(names, buf + off)) {
                snprintf(what, what_size, "pid %ld %.200s", pid, buf + off);
                hit = (int)pid;
            }
    }
    closedir(d);
    return hit;
}
#else
int mu_client_lock_find_process(const char *names, char *what, size_t what_size)
{
    (void)names;
    (void)what;
    (void)what_size;
    return 0;
}
#endif

static int truthy(const char *v)
{
    return v && *v && strcmp(v, "0") != 0;
}

static void first_line(const char *path, char *out, size_t cap, int *exists)
{
    out[0] = 0;
    *exists = 0;
    FILE *f = fopen(path, "r");
    if (!f)
        return;
    *exists = 1;
    if (fgets(out, (int)cap, f)) {
        size_t n = strlen(out);
        while (n && (out[n - 1] == '\n' || out[n - 1] == '\r'))
            out[--n] = 0;
    }
    fclose(f);
}

static void make_parent(const char *path)
{
    char dir[1024];
    snprintf(dir, sizeof dir, "%s", path);
    for (char *p = dir + 1; *p; ++p)
        if (*p == '/') {
            *p = 0;
            mkdir(dir, 0700);   /* EEXIST is the common case */
            *p = '/';
        }
}

static int default_lock_path(char *out, size_t cap)
{
    const char *home = getenv("HOME");
    if (!home || !*home)
        return -1;
#if defined(__APPLE__)
    snprintf(out, cap, "%s/Library/Application Support/MuTheMatrixNative/client.lock", home);
#else
    snprintf(out, cap, "%s/.mu-the-matrix-native.lock", home);
#endif
    return 0;
}

mu_transport_status mu_client_lock_take(mu_client_lock *lock, char *error, size_t error_size)
{
    char what[256];
    lock->fd = -1;
    if (error_size)
        error[0] = 0;

    /* 1. the user is playing the original client */
    const char *names = getenv("MU_CLIENT_PROCESS_NAMES");
    if (!names || !*names)
        names = DEFAULT_PROCESS_NAMES;
    int pid = mu_client_lock_find_process(names, what, sizeof what);
    if (pid) {
        snprintf(error, error_size, "client lock: an original client is running (%s); one client at a time", what);
        return MU_TRANSPORT_LOCKED;
    }

    /* 2. agents: the shared game lock, owner line == MU_LOCK_ID */
    if (truthy(getenv("MU_AGENT"))) {
        const char *dir = getenv("MU_GAME_LOCK_DIR");
        if (!dir || !*dir) {
            snprintf(error, error_size, "client lock: MU_AGENT=1 needs MU_GAME_LOCK_DIR (no lock path is compiled in)");
            return MU_TRANSPORT_ERROR;
        }
        char owner_path[1024], owner[512];
        int exists;
        snprintf(owner_path, sizeof owner_path, "%s/owner", dir);
        first_line(owner_path, owner, sizeof owner, &exists);
        if (!exists) {
            snprintf(error, error_size, "client lock: the game lock %s is not held (no owner file); acquire it first",
                     dir);
            return MU_TRANSPORT_LOCKED;
        }
        const char *id = getenv("MU_LOCK_ID");
        if (!id || strcmp(id, owner) != 0) {
            snprintf(error, error_size, "client lock: the game lock is held by \"%.300s\" (MU_LOCK_ID does not match)",
                     owner);
            return MU_TRANSPORT_LOCKED;
        }
    }

    /* 3. the per-user single-instance lock */
    char path[1024];
    const char *override = getenv("MU_CLIENT_LOCK_PATH");
    if (override && *override) {
        snprintf(path, sizeof path, "%s", override);
    } else {
        if (default_lock_path(path, sizeof path) != 0) {
            snprintf(error, error_size, "client lock: no HOME for the per-user lock (set MU_CLIENT_LOCK_PATH)");
            return MU_TRANSPORT_ERROR;
        }
        make_parent(path);
    }
    int fd = open(path, O_RDWR | O_CREAT | O_CLOEXEC, 0600);
    if (fd < 0) {
        snprintf(error, error_size, "client lock: cannot open %s: %s", path, strerror(errno));
        return MU_TRANSPORT_ERROR;
    }
    if (flock(fd, LOCK_EX | LOCK_NB) != 0) {
        int err = errno;
        char holder[512];
        int exists;
        first_line(path, holder, sizeof holder, &exists);
        close(fd);
        if (err == EWOULDBLOCK) {
            snprintf(error, error_size, "client lock: another native client holds %s (%.300s)", path,
                     holder[0] ? holder : "no owner line");
            return MU_TRANSPORT_LOCKED;
        }
        snprintf(error, error_size, "client lock: flock %s: %s", path, strerror(err));
        return MU_TRANSPORT_ERROR;
    }
    char line[128];
    int n = snprintf(line, sizeof line, "mu-native pid %d\n", (int)getpid());
    if (ftruncate(fd, 0) == 0 && n > 0) {
        ssize_t w = pwrite(fd, line, (size_t)n, 0);
        (void)w;
    }
    lock->fd = fd;
    return MU_TRANSPORT_OK;
}

void mu_client_lock_release(mu_client_lock *lock)
{
    if (lock->fd >= 0) {
        flock(lock->fd, LOCK_UN);
        close(lock->fd);
        lock->fd = -1;
    }
}
