#ifndef MU_DATA_CODEC_H
#define MU_DATA_CODEC_H

#include <stdint.h>

/* Client data-table codecs (NATIVE-DATA-001). Authored logical API, not
 * original symbol names. Every routine works in place on caller memory.
 * See docs/research/client-data-tables.md for addresses and evidence.
 */

/* The three-byte table key. The client reads it from the uncaptured global
 * 0x01cf0448 (and 0x01cf0ea8 for the package decoder); the ServerList decoder
 * 0x01072ebc stores the same three bytes as immediates on its stack.
 */
extern const uint8_t mu_data_key3[3];

/* Client 0x00976855: buffer[i] ^= key[i % 3] for 0 <= i < size (signed
 * comparison). size <= 0 or a NULL pointer performs no access. Each call
 * restarts the key phase at buffer[0], so the decode unit lengths a loader
 * passes are part of the format.
 */
void mu_data_xor3(uint8_t *buffer, int32_t size, const uint8_t key[3]);

/* Client 0x01072ebc (thiscall, ecx unused): the same loop with the key held
 * in local immediates FC CF AB.
 */
void mu_data_xor3_local(uint8_t *buffer, int32_t size);

/* Client 0x00976895: 32-bit table checksum over size bytes, read as
 * little-endian words at offsets 0, 4, ... while offset <= size-4; trailing
 * bytes beyond the last whole word are ignored. Only the low 16 bits of key
 * are used. size < 4 makes the client's unsigned bound wrap (an unbounded
 * read); it is outside this contract and returns key << 9 without reading.
 */
uint32_t mu_data_checksum(const uint8_t *buffer, uint32_t size, uint32_t key);

/* Client 0x00f1600f, the Lang.mpr payload decoder: for 0 <= i < size
 * (unsigned), buffer[i] ^= key3[i % 3], then buffer[i] ^= low byte of key.
 */
void mu_data_xor3_key(uint8_t *buffer, uint32_t size, const uint8_t key3[3], uint32_t key);

#endif
