/* NATIVE-NET-001 CLI: encode/decode synthetic MU packets with the
 * reconstructed framing + send obfuscation. No sockets, no server contact,
 * no client bytes: it only exercises native/core/mu_protocol.c on bytes you
 * supply on the command line. See docs/research/client-net-protocol.md. */
#include "../core/mu_protocol.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int hex_nibble(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* Parse a hex string (whitespace and ':' allowed) into bytes. Returns length or
 * -1 on error. */
static long parse_hex(const char *s, uint8_t *out, size_t cap)
{
    size_t n = 0;
    int hi = -1;
    for (; *s; ++s) {
        int c = (unsigned char)*s;
        if (isspace(c) || c == ':' || c == ',')
            continue;
        int v = hex_nibble(c);
        if (v < 0)
            return -1;
        if (hi < 0) {
            hi = v;
        } else {
            if (n >= cap)
                return -1;
            out[n++] = (uint8_t)((hi << 4) | v);
            hi = -1;
        }
    }
    if (hi >= 0)
        return -1;
    return (long)n;
}

static void print_hex(const uint8_t *b, size_t n)
{
    size_t i;
    for (i = 0; i < n; ++i)
        printf("%02x", b[i]);
    printf("\n");
}

static uint8_t head_from_arg(const char *a, int *ok)
{
    *ok = 1;
    if (!strcmp(a, "C1") || !strcmp(a, "c1") || !strcmp(a, "0xc1")) return MU_HEAD_C1;
    if (!strcmp(a, "C2") || !strcmp(a, "c2") || !strcmp(a, "0xc2")) return MU_HEAD_C2;
    if (!strcmp(a, "C3") || !strcmp(a, "c3") || !strcmp(a, "0xc3")) return MU_HEAD_C3;
    if (!strcmp(a, "C4") || !strcmp(a, "c4") || !strcmp(a, "0xc4")) return MU_HEAD_C4;
    *ok = 0;
    return 0;
}

static void frame_cb(const uint8_t *frame, size_t size, void *ud)
{
    (void)ud;
    printf("  frame head=%02x size=%zu : ", frame[0], size);
    print_hex(frame, size);
}

static int usage(void)
{
    fprintf(stderr,
        "usage: mu-proto <command> ...\n"
        "  build <C1|C2|C3|C4> <opcode-hex> <payload-hex> [--xor]\n"
        "        compose a packet; --xor applies the send obfuscation to the payload\n"
        "  parse <frame-hex>\n"
        "        classify one frame (head, size, header length, payload offset)\n"
        "  dechunk <stream-hex>\n"
        "        split a byte stream into frames like the receive loop\n"
        "  xor-encode <object-hex>   xor-decode <object-hex>\n"
        "        apply/undo the send obfuscation over a packet object\n"
        "        (2-byte LE size word + body); operates on body[0..size)\n");
    return 2;
}

static int cmd_build(int argc, char **argv)
{
    int ok;
    uint8_t head, op[1];
    uint8_t payload[MU_PACKET_CAP];
    long plen;
    int do_xor = 0;
    mu_packet p;
    uint32_t total;
    long oplen;

    if (argc < 3)
        return usage();
    head = head_from_arg(argv[0], &ok);
    if (!ok) { fprintf(stderr, "bad head %s\n", argv[0]); return 2; }
    oplen = parse_hex(argv[1], op, 1);
    if (oplen != 1) { fprintf(stderr, "opcode must be one hex byte\n"); return 2; }
    plen = parse_hex(argv[2], payload, sizeof payload);
    if (plen < 0) { fprintf(stderr, "bad payload hex\n"); return 2; }
    if (argc >= 4 && !strcmp(argv[3], "--xor"))
        do_xor = 1;

    mu_packet_begin(&p, head, op[0]);
    if (mu_packet_add(&p, payload, (size_t)plen, do_xor) != 0) {
        fprintf(stderr, "payload too large (max %u)\n", MU_PACKET_CAP);
        return 1;
    }
    total = mu_packet_finish(&p);
    printf("frame: ");
    print_hex(&p.obj[2], total);
    return 0;
}

static int cmd_parse(int argc, char **argv)
{
    uint8_t buf[MU_RECV_CAP];
    long n;
    mu_frame_info info;
    mu_frame_status st;

    if (argc < 1)
        return usage();
    n = parse_hex(argv[0], buf, sizeof buf);
    if (n < 0) { fprintf(stderr, "bad hex\n"); return 2; }
    st = mu_frame_parse(buf, (size_t)n, &info);
    if (st == MU_FRAME_BAD) { printf("status: BAD (head %02x)\n", n ? buf[0] : 0); return 1; }
    printf("head=%02x size=%u header_len=%u payload_off=%u encrypted=%d status=%s\n",
           info.head, info.size, info.header_len, info.payload_off, info.encrypted,
           st == MU_FRAME_OK ? "OK" : "NEED_MORE");
    if (st == MU_FRAME_OK && (size_t)n >= info.size) {
        printf("payload: ");
        print_hex(&buf[info.payload_off], info.size - info.payload_off);
    }
    return 0;
}

static int cmd_dechunk(int argc, char **argv)
{
    uint8_t buf[MU_RECV_CAP];
    long n;
    mu_recv r;
    size_t got;

    if (argc < 1)
        return usage();
    n = parse_hex(argv[0], buf, sizeof buf);
    if (n < 0) { fprintf(stderr, "bad hex\n"); return 2; }
    mu_recv_init(&r);
    if (mu_recv_push(&r, buf, (size_t)n) != 0) { fprintf(stderr, "stream too large\n"); return 1; }
    got = mu_recv_drain(&r, frame_cb, NULL);
    printf("frames=%zu leftover=%zu\n", got, r.len);
    return 0;
}

static int cmd_xor(int argc, char **argv, int decode)
{
    uint8_t obj[MU_PACKET_OBJ];
    long n;
    uint32_t size;

    if (argc < 1)
        return usage();
    n = parse_hex(argv[0], obj, sizeof obj);
    if (n < 2) { fprintf(stderr, "object needs a 2-byte size word + body\n"); return 2; }
    size = (uint32_t)obj[0] | ((uint32_t)obj[1] << 8);
    if ((long)size + 2 > n) { fprintf(stderr, "size word %u exceeds body\n", size); return 2; }
    if (decode)
        mu_send_xor_decode(obj, 0, size);
    else
        mu_send_xor_encode(obj, 0, size);
    printf("body: ");
    print_hex(&obj[2], size);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2)
        return usage();
    if (!strcmp(argv[1], "build"))    return cmd_build(argc - 2, argv + 2);
    if (!strcmp(argv[1], "parse"))    return cmd_parse(argc - 2, argv + 2);
    if (!strcmp(argv[1], "dechunk"))  return cmd_dechunk(argc - 2, argv + 2);
    if (!strcmp(argv[1], "xor-encode")) return cmd_xor(argc - 2, argv + 2, 0);
    if (!strcmp(argv[1], "xor-decode")) return cmd_xor(argc - 2, argv + 2, 1);
    return usage();
}
