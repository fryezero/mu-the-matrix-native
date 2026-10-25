/* NET-CRYPTO-001: the client's C3/C4 CryptoModule, reimplemented over Crypto++.
 *
 * Evidence and method: docs/research/client-crypto.md. Addresses are virtual addresses in the
 * pinned main.exe (restored text 2bd5f2e9..., second image section c985e2e6...).
 *
 * The client keeps two module objects, g_enc 0x06fce2fc and g_dec 0x06fce31c. Each is a
 * std::map<int, context *> plus the seed string 98135003732920532106543021784355 (constructor
 * 0x018df200). A context (0x98 bytes, CreateCtx 0x018df700) holds the channel, an encrypt and a
 * decrypt packet counter (both start at 1), a 128-byte state table filled with 0x63 and a cipher
 * holder. SetKey 0x018ea8d0 hashes a key with one of the hashes of the table 0x018eaf30, takes
 * cipher index = digest[j] % 10 and calls the factory 0x018ea540, which builds one of 17
 * Crypto++ block ciphers (index 9: sub-cipher digest[0] & 7) keyed from the zero-filled digest
 * buffer; each cipher class carries its rekey interval (8, 32 or 0x800). Encrypt 0x018df500 and
 * Decrypt 0x018df460 run the cipher in ECB over zero-padded blocks plus one trailing pad-count
 * byte, record up to 8 plaintext bytes into the state table (state[b & 0x7f] = b) and, when the
 * direction's counter equals the interval, rekey with SetKey(state, 128) and restart the
 * counter at 1.
 *
 * Verification: scripts/validate_crypto.py runs the client's own instructions under Unicorn
 * against this module (ctor, CreateCtx/Remove/getters, SetKey, factory, Encrypt, Decrypt), and
 * native/tests/test_crypto*.py check public test vectors and mirror round trips.
 *
 * Pure: no I/O and no globals. One mu_crypto per session holds both maps. Every buffer is
 * caller-owned with an explicit length. Not thread-safe per object.
 */
#ifndef MU_CRYPTO_H
#define MU_CRYPTO_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_crypto mu_crypto;

typedef enum mu_crypto_dir { MU_CRYPTO_ENC = 0, MU_CRYPTO_DEC = 1 } mu_crypto_dir;   /* g_enc / g_dec */

enum {
    MU_CRYPTO_SEED_LEN = 32,      /* the seed string, without terminator */
    MU_CRYPTO_STATE_LEN = 128,    /* context +0x0c */
    MU_CRYPTO_BUFFER = 0x1000,    /* the wrappers' stack buffers: largest output or input */
    MU_CRYPTO_CASES = 17,         /* factory cases: indices 0..8 and 9.0..9.7 */
    MU_CRYPTO_OUTSIDE = -2        /* native-only refusal: outside the client's buffers or dst_cap */
};

/* Hash algorithms of the SetKey table 0x018eaf30. */
typedef enum mu_crypto_hash {
    MU_CRYPTO_SHA256 = 0, MU_CRYPTO_SHA512 = 1, MU_CRYPTO_SHA384 = 2, MU_CRYPTO_MD4 = 3, MU_CRYPTO_MD5 = 4,
    MU_CRYPTO_RIPEMD160 = 5, MU_CRYPTO_RIPEMD320 = 6, MU_CRYPTO_RIPEMD128 = 7, MU_CRYPTO_RIPEMD256 = 8
} mu_crypto_hash;

/* Factory cases (0..16): index 0..8, then 9 + sub-cipher. */
typedef enum mu_crypto_case {
    MU_CRYPTO_TEA = 0, MU_CRYPTO_3WAY = 1, MU_CRYPTO_CAST128 = 2, MU_CRYPTO_GOST_3 = 3, MU_CRYPTO_RC5 = 4,
    MU_CRYPTO_RC6 = 5, MU_CRYPTO_MARS = 6, MU_CRYPTO_IDEA = 7, MU_CRYPTO_GOST_8 = 8, MU_CRYPTO_TWOFISH = 9,
    MU_CRYPTO_DES = 10, MU_CRYPTO_DES_EDE2 = 11, MU_CRYPTO_DES_EDE3 = 12, MU_CRYPTO_DES_XEX3 = 13,
    MU_CRYPTO_SKIPJACK = 14, MU_CRYPTO_SAFER_K = 15, MU_CRYPTO_SAFER_SK = 16
} mu_crypto_case;

/* What one SetKey chose. */
typedef struct mu_crypto_choice {
    int32_t selector;          /* selector byte % 11: picks the table 0x018eaf30 entry (0 and 2: the default) */
    int32_t hash;              /* mu_crypto_hash */
    int32_t cipher;            /* factory index digest[j] % 10, stored at context +0x94 */
    int32_t sub_cipher;        /* index 9: digest[0] & 7; otherwise -1 */
    int32_t cipher_case;       /* mu_crypto_case */
    uint32_t rekey_interval;   /* the cipher class's interval (wrapper +4) */
    uint32_t key_len;          /* the length SetKey passes to the factory (the digest size) */
    uint8_t key[64];           /* the first 64 bytes of SetKey's zero-filled 0x800-byte digest buffer */
} mu_crypto_choice;

/* One context, as the client's 0x98-byte record holds it. */
typedef struct mu_crypto_view {
    int32_t channel;                       /* +0x00 */
    int32_t enc_count;                     /* +0x04 */
    int32_t dec_count;                     /* +0x08 */
    uint8_t state[MU_CRYPTO_STATE_LEN];    /* +0x0c */
    int32_t word_8c;                       /* +0x8c, written 0 by CreateCtx, never read */
    mu_crypto_choice choice;               /* the last SetKey (+0x90 holder, +0x94 index) */
    uint32_t keyings;                      /* native only: SetKey runs on this context so far */
} mu_crypto_view;

/* The constructor 0x018df200 for both maps: empty maps, both seeded with the key string. */
mu_crypto *mu_crypto_new(void);
/* The fixture server's end. The cipher is symmetric in its state (both sides record plaintext,
 * count packets and rekey alike), so the server's ENC map mirrors the client's DEC map and vice
 * versa: this is mu_crypto_new under a name that says which end it plays. */
mu_crypto *mu_crypto_new_server_side(void);
void mu_crypto_free(mu_crypto *c);

/* The seed string of map `dir` (module +0x08). Returns its length; copies min(len, cap) bytes. */
size_t mu_crypto_seed(const mu_crypto *c, mu_crypto_dir dir, uint8_t *out, size_t cap);

/* CreateCtx 0x018df700: (re)creates the context for `channel` (an existing one is destroyed
 * first, as the client does) and keys it from the seed string. Returns the client's result, 1. */
int mu_crypto_open(mu_crypto *c, mu_crypto_dir dir, int32_t channel);
/* Remove 0x018df3f0: destroys the channel's context; no effect when there is none. */
void mu_crypto_close(mu_crypto *c, mu_crypto_dir dir, int32_t channel);

/* SetKeyChannel 0x018df5c0 -> SetKey 0x018ea8d0 on map `dir`, channel `channel`. Returns the
 * client's result (1), or -1 when the channel has no context (the client then returns an
 * unrelated pointer and changes nothing) or key_len is 0 (the client would read key[0] anyway).
 * `choice` (may be NULL) reports what was chosen. Counters and the state table are unchanged. */
int mu_crypto_set_key(mu_crypto *c, mu_crypto_dir dir, int32_t channel, const uint8_t *key, size_t key_len,
                      mu_crypto_choice *choice);

/* Encrypt 0x018df500 on the ENC map, Decrypt 0x018df460 on the DEC map, with the client's
 * argument shape: separate dst and src. Returns the client's result: the output length, or -1
 * (no context; Decrypt: dst NULL, len % block != 1, recovered length outside 1..0x1000).
 * Encrypt with dst NULL is the client's size query (no counter or state change).
 * MU_CRYPTO_OUTSIDE without any change when dst_cap is too small or the call lies outside the
 * client's 0x1000-byte buffers (Encrypt output > 0x1000, Decrypt input > 0x1000 with a
 * recovered length inside 1..0x1000), where the client would overrun its own stack. */
int32_t mu_crypto_call(mu_crypto *c, mu_crypto_dir dir, int32_t channel, uint8_t *dst, size_t dst_cap,
                       const uint8_t *src, size_t len);

/* The sketch's in-place form of mu_crypto_call: buf holds len bytes and has cap bytes of room.
 * Returns 0 and the result length in *out_len, -1 where the client fails, or MU_CRYPTO_OUTSIDE.
 * Encrypt records the plaintext, as the client does with its separate buffers. */
int mu_crypto_run(mu_crypto *c, mu_crypto_dir dir, int32_t channel, uint8_t *buf, size_t len, size_t cap,
                  size_t *out_len);

/* The client's getters (no in-image callers): 0x018df610 cipher index (-1 without context),
 * 0x018df660 decrypt counter and 0x018df6b0 encrypt counter (0 without context). */
int32_t mu_crypto_cipher_index(const mu_crypto *c, mu_crypto_dir dir, int32_t channel);
int32_t mu_crypto_dec_count(const mu_crypto *c, mu_crypto_dir dir, int32_t channel);
int32_t mu_crypto_enc_count(const mu_crypto *c, mu_crypto_dir dir, int32_t channel);

/* Inspection for the validator and the tests. mu_crypto_view_channel returns 0, or -1 without
 * context. mu_crypto_channels returns the number of contexts and copies up to cap channel
 * numbers in the client's map order (ascending, signed). */
int mu_crypto_view_channel(const mu_crypto *c, mu_crypto_dir dir, int32_t channel, mu_crypto_view *out);
size_t mu_crypto_channels(const mu_crypto *c, mu_crypto_dir dir, int32_t *out, size_t cap);

/* ---- one cipher holder, below the maps ----------------------------------------------------- */

typedef struct mu_crypto_cipher mu_crypto_cipher;

/* The factory 0x018ea540: index % 10 picks the class (9: key[0] & 7 picks the sub-cipher) and
 * the class keys itself with its fixed key length from `key`. The client's only caller passes
 * a zero-filled 0x800-byte buffer, so bytes past key_len are taken as zero. NULL on allocation
 * failure. */
mu_crypto_cipher *mu_crypto_cipher_new(uint32_t index, const uint8_t *key, size_t key_len);
void mu_crypto_cipher_free(mu_crypto_cipher *h);
int32_t mu_crypto_cipher_case(const mu_crypto_cipher *h);
uint32_t mu_crypto_cipher_interval(const mu_crypto_cipher *h);
uint32_t mu_crypto_cipher_block(const mu_crypto_cipher *h);
uint32_t mu_crypto_cipher_key_len(const mu_crypto_cipher *h);
/* The class's Encrypt (vtable slot 2) and Decrypt (slot 3), without counters or state:
 * same results as mu_crypto_call. */
int32_t mu_crypto_cipher_encrypt(mu_crypto_cipher *h, uint8_t *dst, size_t dst_cap, const uint8_t *src, size_t len);
int32_t mu_crypto_cipher_decrypt(mu_crypto_cipher *h, uint8_t *dst, size_t dst_cap, const uint8_t *src, size_t len);

/* One ECB block of factory case `cipher_case` with the class's key length and default rounds
 * (key zero-extended past key_len), for known-answer tests. Returns 0, or -1 for a bad case. */
int mu_crypto_block(int32_t cipher_case, int decrypt, const uint8_t *key, size_t key_len, const uint8_t *in,
                    uint8_t *out);

#ifdef __cplusplus
}
#endif

#endif /* MU_CRYPTO_H */
