/* Independent LEA-256 ECB asset reader. Format references in SOURCES.md.
 * MIT license, see ../LICENSE-analysis. Not an authentication component.
 */
#include <stddef.h>
#include <stdint.h>

static uint32_t rol(uint32_t x, unsigned n) {
    n &= 31;
    return (x << n) | (x >> ((32-n) & 31));
}
static uint32_t ror(uint32_t x, unsigned n) { return rol(x, 32-n); }
static uint32_t load(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static void store(uint8_t *p, uint32_t x) {
    for (unsigned i=0; i<4; ++i) p[i] = (uint8_t)(x >> (8*i));
}
int mu_lea256_decrypt(const uint8_t *input, size_t size, uint8_t *output,
                      const uint8_t *key, size_t key_size) {
    static const uint32_t delta[8] = {0xc3efe9db,0x44626b02,0x79e27c8a,0x78df30ec,
                                     0x715ea49e,0xc785da0a,0xe04ef22a,0xe5c40957};
    static const unsigned rotations[6] = {1,3,6,11,13,17};
    if (!input || !output || !key || key_size != 32 || size % 16) return -1;
    uint32_t words[8], keys[32][6];
    for (unsigned i=0; i<8; ++i) words[i] = load(key+4*i);
    for (unsigned i=0; i<32; ++i) {
        for (unsigned j=0; j<6; ++j) {
            unsigned index = (6*i+j) & 7;
            words[index] = rol(words[index] + rol(delta[i & 7],i+j),rotations[j]);
            keys[i][j] = words[index];
        }
    }
    for (size_t offset=0; offset<size; offset+=16) {
        uint32_t a=load(input+offset), b=load(input+offset+4),
                 c=load(input+offset+8), d=load(input+offset+12);
        for (unsigned r=32; r>0; --r) {
            const uint32_t *k = keys[r-1];
            uint32_t x=d, y=(ror(a,9)-(x ^ k[0])) ^ k[1],
                     z=(rol(b,5)-(y ^ k[2])) ^ k[3], w=(rol(c,3)-(z ^ k[4])) ^ k[5];
            a=x; b=y; c=z; d=w;
        }
        store(output+offset,a); store(output+offset+4,b);
        store(output+offset+8,c); store(output+offset+12,d);
    }
    return 0;
}
