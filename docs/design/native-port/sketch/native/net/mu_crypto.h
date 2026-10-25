/* NET-CRYPTO-001 (sketch): the client's CryptoModule, reimplemented over Crypto++.
 *
 * Evidence: docs/research/client-net-protocol.md "C3 / C4 CryptoModule". Two
 * std::map<int, context*> instances (g_enc 0x06fce2fc, g_dec 0x06fce31c), each seeded from
 * the key string 98135003732920532106543021784355 (ctor 0x018df200). SetKey 0x018ea8d0
 * hashes the key through a hash chosen from the 10-entry table 0x018eaf30, picks one of 17
 * Crypto++ ciphers (index 9: sub-cipher key[0] & 7) and a rekey interval. Encrypt
 * 0x018df500 / Decrypt 0x018df460 run the channel's block cipher and rekey every interval.
 *
 * Verification (scripts/validate_crypto.py): the client's ctor/SetKey/Encrypt/Decrypt under
 * Unicorn against this module over seeded keys, channels, lengths and rekey boundaries; one
 * family per routine plus per-cipher KATs; planted mistakes -DMU_CRYPTO_MUTATION=k.
 *
 * Implementation: native/net/crypto.cpp (C++, Crypto++ already linked for BMD v14), C ABI.
 * Pure: no I/O, no globals; one mu_crypto per session (the client's two maps).
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

/* The ctor 0x018df200 for both maps. */
mu_crypto *mu_crypto_new(void);
void mu_crypto_free(mu_crypto *c);

/* SetKey 0x018ea8d0 on map `dir`, channel `channel`. Returns 0, or -1 for a key the client
 * rejects. Reports which cipher/sub-cipher and interval were chosen (for the validator). */
typedef struct mu_crypto_choice { int32_t hash, cipher, sub_cipher; uint32_t rekey_interval; } mu_crypto_choice;
int mu_crypto_set_key(mu_crypto *c, mu_crypto_dir dir, int32_t channel, const uint8_t *key, size_t key_len,
                      mu_crypto_choice *choice);

/* Encrypt 0x018df500 / Decrypt 0x018df460 in place. `cap` is the buffer capacity (block
 * padding may grow the payload: *out_len). Returns 0, or -1 (no context for the channel,
 * capacity) exactly where the client fails. */
int mu_crypto_run(mu_crypto *c, mu_crypto_dir dir, int32_t channel, uint8_t *buf, size_t len, size_t cap,
                  size_t *out_len);

/* The fixture server plays the other end: it runs the mirror direction with the same seed. */
mu_crypto *mu_crypto_new_server_side(void);

#ifdef __cplusplus
}
#endif

#endif /* MU_CRYPTO_H */
