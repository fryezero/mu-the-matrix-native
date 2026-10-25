// NET-CRYPTO-001: the client's C3/C4 CryptoModule over Crypto++. See mu_crypto.h and
// docs/research/client-crypto.md. Every rule below names the client instruction it restates.
//
// Planted mistakes for scripts/validate_crypto.py: -DMU_CRYPTO_MUTATION=k (k = 1..14) changes
// one rule each; the default build (0) is the reconstruction.
#define CRYPTOPP_ENABLE_NAMESPACE_WEAK 1
#include <cryptopp/3way.h>
#include <cryptopp/cast.h>
#include <cryptopp/des.h>
#include <cryptopp/gost.h>
#include <cryptopp/idea.h>
#include <cryptopp/mars.h>
#include <cryptopp/md4.h>
#include <cryptopp/md5.h>
#include <cryptopp/rc5.h>
#include <cryptopp/rc6.h>
#include <cryptopp/ripemd.h>
#include <cryptopp/safer.h>
#include <cryptopp/sha.h>
#include <cryptopp/skipjack.h>
#include <cryptopp/tea.h>
#include <cryptopp/twofish.h>

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <map>
#include <memory>
#include <new>
#include <string>
#include <vector>

#include "mu_crypto.h"

#ifndef MU_CRYPTO_MUTATION
#define MU_CRYPTO_MUTATION 0
#endif

namespace {

// The constructor 0x018df200 assigns this 32-byte string (data 0x01b278f8) to module +0x08.
constexpr char kSeed[] = "98135003732920532106543021784355";
static_assert(sizeof(kSeed) == MU_CRYPTO_SEED_LEN + 1, "seed string length");

constexpr std::size_t kBuffer = MU_CRYPTO_BUFFER;   // the wrappers' 0x1000-byte stack buffers
constexpr std::size_t kDigestBuffer = 0x800;        // SetKey's zero-filled digest buffer

// One factory case: class, its fixed key length (the push before each SetKey call) and its rekey
// interval (ConcreteCipher<T, interval>, written to wrapper +4 by the class's SetKey).
struct CaseInfo {
    const char *name;
    unsigned key_len;
    std::uint32_t interval;
};

constexpr CaseInfo kCases[MU_CRYPTO_CASES] = {
    {"TEA", 16, 0x800},      {"3-Way", 12, 0x800},   {"CAST-128", 16, 0x800}, {"GOST", 32, 0x800},
    {"RC5", 16, 0x800},      {"RC6", 16, 0x800},     {"MARS", 16, 0x800},     {"IDEA", 16, 0x800},
    {"GOST", 32, 0x800},     {"Twofish", 16, 8},     {"DES", 8, 8},           {"DES-EDE2", 16, 8},
    {"DES-EDE3", 24, 0x20},  {"DES-XEX3", 24, 8},
#if MU_CRYPTO_MUTATION == 6
    {"SKIPJACK", 10, 8},
#else
    {"SKIPJACK", 10, 0x20},
#endif
    {"SAFER-K", 16, 8},      {"SAFER-SK", 16, 0x20},
};

template <typename Algorithm>
void make_pair(std::unique_ptr<CryptoPP::BlockCipher> &enc, std::unique_ptr<CryptoPP::BlockCipher> &dec,
               const std::uint8_t *key, unsigned key_len) {
    auto e = std::make_unique<typename Algorithm::Encryption>();
    auto d = std::make_unique<typename Algorithm::Decryption>();
    // The class SetKey calls SetKey(key, fixed length, g_nullNameValuePairs) on both objects:
    // Crypto++'s default rounds.
    e->SetKey(key, key_len);
    d->SetKey(key, key_len);
    enc = std::move(e);
    dec = std::move(d);
}

}  // namespace

// The wrapper object a factory case builds (vtable: dtor, SetKey, Encrypt, Decrypt; +4 interval).
struct mu_crypto_cipher {
    int cipher_case = 0;
    std::uint32_t interval = 0;
    std::size_t block = 8;
    std::unique_ptr<CryptoPP::BlockCipher> enc, dec;
};

namespace {

int case_of(std::uint32_t index, std::uint8_t first_key_byte) {
    // 0x018ea578..0x018ea598: index % 10 through the jump table 0x018ea884;
    // 0x018ea6eb: index 9 dispatches on key[0] & 7 through 0x018ea8ac.
    const std::uint32_t i = index % 10U;
    if (i < 9U) return static_cast<int>(i);
    return 9 + (first_key_byte & 7);
}

// One class keyed from `k` (64 bytes, zero past the caller's key): the class SetKey reads its
// fixed key length from the buffer whatever length the factory was given.
std::unique_ptr<mu_crypto_cipher> build_case(int c, const std::uint8_t *k) {
    auto h = std::make_unique<mu_crypto_cipher>();
    h->cipher_case = c;
    h->interval = kCases[c].interval;
    const unsigned n = kCases[c].key_len;
    switch (c) {
        case MU_CRYPTO_TEA: make_pair<CryptoPP::TEA>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_3WAY: make_pair<CryptoPP::ThreeWay>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_CAST128: make_pair<CryptoPP::CAST128>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_GOST_3:
        case MU_CRYPTO_GOST_8: make_pair<CryptoPP::GOST>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_RC5: make_pair<CryptoPP::RC5>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_RC6: make_pair<CryptoPP::RC6>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_MARS: make_pair<CryptoPP::MARS>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_IDEA: make_pair<CryptoPP::IDEA>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_TWOFISH: make_pair<CryptoPP::Twofish>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_DES: make_pair<CryptoPP::DES>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_DES_EDE2: make_pair<CryptoPP::DES_EDE2>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_DES_EDE3: make_pair<CryptoPP::DES_EDE3>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_DES_XEX3: make_pair<CryptoPP::DES_XEX3>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_SKIPJACK: make_pair<CryptoPP::SKIPJACK>(h->enc, h->dec, k, n); break;
        case MU_CRYPTO_SAFER_K: make_pair<CryptoPP::SAFER_K>(h->enc, h->dec, k, n); break;
        default: make_pair<CryptoPP::SAFER_SK>(h->enc, h->dec, k, n); break;
    }
    h->block = h->enc->BlockSize();
    return h;
}

// The factory 0x018ea540.
std::unique_ptr<mu_crypto_cipher> factory(std::uint32_t index, const std::uint8_t *key, std::size_t key_len) {
    std::uint8_t k[64] = {0};
    if (key_len != 0) std::memcpy(k, key, key_len < sizeof k ? key_len : sizeof k);
#if MU_CRYPTO_MUTATION == 5
    return build_case(case_of(index, k[1]), k);
#else
    return build_case(case_of(index, k[0]), k);
#endif
}

// The class Encrypt (e.g. TEA 0x018e9b40, 3-Way 0x018e9c60): pad = block - len % block (0 when
// aligned), out = len + pad + 1; ECB over the zero-padded input while i < out (the last,
// all-zero block is computed and discarded); the byte at out - 1 is the pad count.
std::int32_t wrapper_encrypt(const mu_crypto_cipher &h, std::uint8_t *dst, const std::uint8_t *src,
                             std::size_t len, bool *outside) {
    *outside = false;
    if (len > 0x7fff0000U) {
        *outside = true;
        return MU_CRYPTO_OUTSIDE;
    }
    const std::size_t b = h.block;
    const std::size_t r = len % b;
#if MU_CRYPTO_MUTATION == 7
    const std::size_t pad = b - r;
#else
    const std::size_t pad = r ? b - r : 0;
#endif
    const std::size_t out = len + 1 + pad;
    if (dst == nullptr) return static_cast<std::int32_t>(out);
    if (out > kBuffer) {
        *outside = true;
        return MU_CRYPTO_OUTSIDE;
    }
    std::uint8_t in[kBuffer + 16] = {0}, ob[kBuffer + 16] = {0};
    if (len != 0) std::memcpy(in, src, len);
    for (std::size_t i = 0; i < out; i += b) h.enc->ProcessBlock(in + i, ob + i);
    ob[out - 1] = static_cast<std::uint8_t>(pad);
    std::memcpy(dst, ob, out);
    return static_cast<std::int32_t>(out);
}

// The recovered length of a Decrypt input, or -1 (the class Decrypt's early checks: len % block
// must be 1; n = len - src[len - 1] - 1).
bool decrypt_length(const mu_crypto_cipher &h, const std::uint8_t *src, std::size_t len, std::int32_t *n) {
    const std::uint32_t l32 = static_cast<std::uint32_t>(len);
    const std::uint32_t r = l32 % static_cast<std::uint32_t>(h.block);
#if MU_CRYPTO_MUTATION == 11
    if (r > 1U) return false;
    if (r == 0U && l32 == 0U) return false;
#else
    if (r != 1U) return false;
#endif
    *n = static_cast<std::int32_t>(l32 - src[l32 - 1U] - 1U);
    return true;
}

// The class Decrypt (e.g. TEA 0x018e8870): -1 unless len % block == 1; n = len - pad - 1;
// with dst: -1 unless 1 <= n <= 0x1000; ECB over the blocks covering n bytes; copies n bytes.
std::int32_t wrapper_decrypt(const mu_crypto_cipher &h, std::uint8_t *dst, const std::uint8_t *src,
                             std::size_t len) {
    if (len > 0xffffffffU) return MU_CRYPTO_OUTSIDE;
    std::int32_t n = 0;
    if (!decrypt_length(h, src, len, &n)) return -1;
    if (dst == nullptr) return n;
    if (static_cast<std::uint32_t>(n) - 1U > 0xfffU) return -1;
    // n <= 0x1000 but the client would clear and copy len > 0x1000 bytes into its 0x1000-byte
    // stack buffer (overrunning its frame): outside the client's defined behaviour.
    if (len > kBuffer) return MU_CRYPTO_OUTSIDE;
    std::uint8_t in[kBuffer + 16] = {0}, ob[kBuffer + 16] = {0};
    std::memcpy(in, src, len);
    const std::size_t want = static_cast<std::size_t>(n);
    for (std::size_t i = 0; i < want; i += h.block) h.dec->ProcessBlock(in + i, ob + i);
    std::memcpy(dst, ob, want);
    return n;
}

struct Hashed {
    int selector;
    int hash;
    std::size_t index_byte;
    std::uint32_t key_len;
};

// SetKey 0x018ea8d0: the selector byte, then the table 0x018eaf30.
Hashed select_hash(const std::uint8_t *key, std::size_t key_len) {
    std::uint8_t sel;
#if MU_CRYPTO_MUTATION == 14
    const bool long_key = key_len > 10;
#else
    const bool long_key = key_len >= 10;   // cmp [ebx+0xc], 0xa; jae (unsigned)
#endif
    if (!long_key) {
        sel = key[0];
    } else {
        const int a = key[0] ^ key[1];
        const int b = key[2] % 3;
#if MU_CRYPTO_MUTATION == 1
        const std::uint8_t lt = a <= b ? 1 : 0;
#else
        const std::uint8_t lt = a < b ? 1 : 0;   // setl
#endif
        sel = static_cast<std::uint8_t>((lt | key[3]) ^ key[4]);
    }
#if MU_CRYPTO_MUTATION == 2
    const int s = sel % 10;
#else
    const int s = sel % 11;
#endif
    // Each case: the hash class (RTTI of its vtable), the digest byte taken % 10 for the cipher
    // index, and the length passed to the factory.
    switch (s) {
        case 1: return {s, MU_CRYPTO_SHA256, 0, 32};
        case 3: return {s, MU_CRYPTO_SHA512, 1, 64};
        case 4: return {s, MU_CRYPTO_SHA384, 2, 48};
        case 5: return {s, MU_CRYPTO_MD4, 3, 16};
        case 6: return {s, MU_CRYPTO_MD5, 4, 16};
        case 7: return {s, MU_CRYPTO_RIPEMD160, 5, 20};
        case 8: return {s, MU_CRYPTO_RIPEMD320, 6, 40};
#if MU_CRYPTO_MUTATION == 3
        case 9: return {s, MU_CRYPTO_RIPEMD256, 7, 32};
        case 10: return {s, MU_CRYPTO_RIPEMD128, 8, 16};
#else
        case 9: return {s, MU_CRYPTO_RIPEMD128, 7, 16};
        case 10: return {s, MU_CRYPTO_RIPEMD256, 8, 32};
#endif
        default:   // 0 (dec eax wraps past 9) and 2 (table slot 1): the handler 0x018eae48
#if MU_CRYPTO_MUTATION == 4
            return {s, MU_CRYPTO_MD5, 4, 16};
#else
            return {s, MU_CRYPTO_MD5, 9, 16};
#endif
    }
}

template <typename H>
void digest_into(const std::uint8_t *key, std::size_t key_len, std::uint8_t *out) {
    H h;
    h.Update(key, key_len);
    h.TruncatedFinal(out, h.DigestSize());
}

void run_hash(int hash, const std::uint8_t *key, std::size_t key_len, std::uint8_t *out) {
    switch (hash) {
        case MU_CRYPTO_SHA256: digest_into<CryptoPP::SHA256>(key, key_len, out); break;
        case MU_CRYPTO_SHA512: digest_into<CryptoPP::SHA512>(key, key_len, out); break;
        case MU_CRYPTO_SHA384: digest_into<CryptoPP::SHA384>(key, key_len, out); break;
        case MU_CRYPTO_MD4: digest_into<CryptoPP::Weak::MD4>(key, key_len, out); break;
        case MU_CRYPTO_MD5: digest_into<CryptoPP::Weak::MD5>(key, key_len, out); break;
        case MU_CRYPTO_RIPEMD160: digest_into<CryptoPP::RIPEMD160>(key, key_len, out); break;
        case MU_CRYPTO_RIPEMD320: digest_into<CryptoPP::RIPEMD320>(key, key_len, out); break;
        case MU_CRYPTO_RIPEMD128: digest_into<CryptoPP::RIPEMD128>(key, key_len, out); break;
        default: digest_into<CryptoPP::RIPEMD256>(key, key_len, out); break;
    }
}

struct Context {
    std::int32_t channel = 0;
    std::int32_t enc_count = 1;   // CreateCtx: +4 = 1, +8 = 1
    std::int32_t dec_count = 1;
    std::uint8_t state[MU_CRYPTO_STATE_LEN];
    std::int32_t word_8c = 0;
    std::unique_ptr<mu_crypto_cipher> cipher;   // holder +0x90
    mu_crypto_choice choice{};                   // holder +0x94 is choice.cipher
    std::uint32_t keyings = 0;
};

// SetKey 0x018ea8d0 on a holder: hash, cipher index, factory. Returns al (1).
int set_key(Context &ctx, const std::uint8_t *key, std::size_t key_len) {
    std::vector<std::uint8_t> digest(kDigestBuffer, 0);
    const Hashed sel = select_hash(key, key_len);
    run_hash(sel.hash, key, key_len, digest.data());
    const std::int32_t index = digest[sel.index_byte] % 10;
    ctx.cipher = factory(static_cast<std::uint32_t>(index), digest.data(), digest.size());
    mu_crypto_choice &ch = ctx.choice;
    ch.selector = sel.selector;
    ch.hash = sel.hash;
    ch.cipher = index;
    ch.sub_cipher = index == 9 ? (ctx.cipher->cipher_case - 9) : -1;
    ch.cipher_case = ctx.cipher->cipher_case;
    ch.rekey_interval = ctx.cipher->interval;
    ch.key_len = sel.key_len;
    std::memcpy(ch.key, digest.data(), sizeof ch.key);
    ++ctx.keyings;
    return 1;
}

// Update 0x018dfed0: nothing for n == 0; n > 8 (signed): the first 8 bytes; otherwise the first
// byte; each recorded at state[b & 0x7f].
void update(Context &ctx, const std::uint8_t *data, std::int32_t n) {
    if (n == 0) return;
#if MU_CRYPTO_MUTATION == 8
    const int count = n >= 8 ? 8 : 1;
#else
    const int count = n > 8 ? 8 : 1;
#endif
    for (int i = 0; i < count; ++i) {
#if MU_CRYPTO_MUTATION == 9
        ctx.state[data[i] & 0x3f] = data[i];
#else
        ctx.state[data[i] & 0x7f] = data[i];
#endif
    }
}

// Rekey 0x018df9c0: SetKey(state, 0x80).
void rekey(Context &ctx) {
    std::uint8_t key[MU_CRYPTO_STATE_LEN];
    std::memcpy(key, ctx.state, sizeof key);
    set_key(ctx, key, sizeof key);
}

// The counter step after a successful call (Encrypt 0x018df578, Decrypt 0x018df4b5): equal to
// the interval: record, rekey, counter = 1; otherwise record, counter + 1.
void count(Context &ctx, std::int32_t &counter, const std::uint8_t *plain, std::int32_t n) {
    if (static_cast<std::uint32_t>(counter) == ctx.cipher->interval) {
        update(ctx, plain, n);
        rekey(ctx);
#if MU_CRYPTO_MUTATION == 10
        counter = 0;
#else
        counter = 1;
#endif
    } else {
        update(ctx, plain, n);
        ++counter;
    }
}

using Map = std::map<std::int32_t, std::unique_ptr<Context>>;

}  // namespace

struct mu_crypto {
    Map maps[2];
    std::string seed[2];
};

namespace {

Map *map_of(mu_crypto *c, mu_crypto_dir dir) {
    if (c == nullptr || (dir != MU_CRYPTO_ENC && dir != MU_CRYPTO_DEC)) return nullptr;
    return &c->maps[dir];
}

const Map *map_of(const mu_crypto *c, mu_crypto_dir dir) {
    if (c == nullptr || (dir != MU_CRYPTO_ENC && dir != MU_CRYPTO_DEC)) return nullptr;
    return &c->maps[dir];
}

Context *find(mu_crypto *c, mu_crypto_dir dir, std::int32_t channel) {
    Map *m = map_of(c, dir);
    if (m == nullptr) return nullptr;
    auto it = m->find(channel);
    return it == m->end() ? nullptr : it->second.get();
}

const Context *find(const mu_crypto *c, mu_crypto_dir dir, std::int32_t channel) {
    const Map *m = map_of(c, dir);
    if (m == nullptr) return nullptr;
    auto it = m->find(channel);
    return it == m->end() ? nullptr : it->second.get();
}

// Encrypt 0x018df500.
std::int32_t encrypt_call(Context &ctx, std::uint8_t *dst, std::size_t dst_cap, const std::uint8_t *src,
                          std::size_t len) {
    bool outside = false;
    const std::int32_t size = wrapper_encrypt(*ctx.cipher, nullptr, src, len, &outside);
    if (dst == nullptr || outside) return size;
    if (static_cast<std::size_t>(size) > dst_cap) return MU_CRYPTO_OUTSIDE;
    const std::int32_t r = wrapper_encrypt(*ctx.cipher, dst, src, len, &outside);
    if (outside) return r;
    count(ctx, ctx.enc_count, src, static_cast<std::int32_t>(len));
    return r;
}

// Decrypt 0x018df460 (after its dst and channel checks).
std::int32_t decrypt_call(Context &ctx, std::uint8_t *dst, std::size_t dst_cap, const std::uint8_t *src,
                          std::size_t len) {
    std::int32_t want = 0;
    if (len <= 0xffffffffU && decrypt_length(*ctx.cipher, src, len, &want) &&
        static_cast<std::uint32_t>(want) - 1U <= 0xfffU && static_cast<std::size_t>(want) > dst_cap) {
        return MU_CRYPTO_OUTSIDE;
    }
    const std::int32_t n = wrapper_decrypt(*ctx.cipher, dst, src, len);
    if (n <= 0) return n;
#if MU_CRYPTO_MUTATION == 12
    count(ctx, ctx.dec_count, src, n);
#else
    count(ctx, ctx.dec_count, dst, n);
#endif
    return n;
}

}  // namespace

extern "C" {

mu_crypto *mu_crypto_new(void) {
    mu_crypto *c = new (std::nothrow) mu_crypto;
    if (c == nullptr) return nullptr;
    c->seed[0] = kSeed;
    c->seed[1] = kSeed;
    return c;
}

mu_crypto *mu_crypto_new_server_side(void) { return mu_crypto_new(); }

void mu_crypto_free(mu_crypto *c) { delete c; }

size_t mu_crypto_seed(const mu_crypto *c, mu_crypto_dir dir, uint8_t *out, size_t cap) {
    if (map_of(c, dir) == nullptr) return 0;
    const std::string &s = c->seed[dir];
    if (out != nullptr) std::memcpy(out, s.data(), s.size() < cap ? s.size() : cap);
    return s.size();
}

int mu_crypto_open(mu_crypto *c, mu_crypto_dir dir, int32_t channel) {
    Map *m = map_of(c, dir);
    if (m == nullptr) return -1;
    try {
        m->erase(channel);   // an existing context is destroyed and its node erased first
        auto ctx = std::make_unique<Context>();
        ctx->channel = channel;
#if MU_CRYPTO_MUTATION == 13
        ctx->enc_count = 0;
        ctx->dec_count = 0;
#endif
        std::memset(ctx->state, 0x63, sizeof ctx->state);
        const std::string &s = c->seed[dir];
        set_key(*ctx, reinterpret_cast<const std::uint8_t *>(s.data()), s.size());
        (*m)[channel] = std::move(ctx);
        return 1;
    } catch (...) {
        return -1;
    }
}

void mu_crypto_close(mu_crypto *c, mu_crypto_dir dir, int32_t channel) {
    Map *m = map_of(c, dir);
    if (m != nullptr) m->erase(channel);
}

int mu_crypto_set_key(mu_crypto *c, mu_crypto_dir dir, int32_t channel, const uint8_t *key, size_t key_len,
                      mu_crypto_choice *choice) {
    Context *ctx = find(c, dir, channel);
    if (ctx == nullptr || key == nullptr || key_len == 0) return -1;
    try {
        const int r = set_key(*ctx, key, key_len);
        if (choice != nullptr) *choice = ctx->choice;
        return r;
    } catch (...) {
        return -1;
    }
}

int32_t mu_crypto_call(mu_crypto *c, mu_crypto_dir dir, int32_t channel, uint8_t *dst, size_t dst_cap,
                       const uint8_t *src, size_t len) {
    if (dir == MU_CRYPTO_DEC && dst == nullptr) return -1;   // 0x018df46b: test edi, edi
    Context *ctx = find(c, dir, channel);
    if (ctx == nullptr) return -1;
    if (src == nullptr && len != 0) return MU_CRYPTO_OUTSIDE;
    try {
        return dir == MU_CRYPTO_ENC ? encrypt_call(*ctx, dst, dst_cap, src, len)
                                    : decrypt_call(*ctx, dst, dst_cap, src, len);
    } catch (...) {
        return MU_CRYPTO_OUTSIDE;
    }
}

int mu_crypto_run(mu_crypto *c, mu_crypto_dir dir, int32_t channel, uint8_t *buf, size_t len, size_t cap,
                  size_t *out_len) {
    if (out_len != nullptr) *out_len = 0;
    if (buf == nullptr || len > cap || len > kBuffer + 0x100) return MU_CRYPTO_OUTSIDE;
    std::vector<std::uint8_t> copy(buf, buf + len);
    const std::int32_t r = mu_crypto_call(c, dir, channel, buf, cap, copy.data(), len);
    if (r < 0) return r == MU_CRYPTO_OUTSIDE ? MU_CRYPTO_OUTSIDE : -1;
    if (out_len != nullptr) *out_len = static_cast<size_t>(r);
    return 0;
}

int32_t mu_crypto_cipher_index(const mu_crypto *c, mu_crypto_dir dir, int32_t channel) {
    const Context *ctx = find(c, dir, channel);
    return ctx == nullptr ? -1 : ctx->choice.cipher;
}

int32_t mu_crypto_dec_count(const mu_crypto *c, mu_crypto_dir dir, int32_t channel) {
    const Context *ctx = find(c, dir, channel);
    return ctx == nullptr ? 0 : ctx->dec_count;
}

int32_t mu_crypto_enc_count(const mu_crypto *c, mu_crypto_dir dir, int32_t channel) {
    const Context *ctx = find(c, dir, channel);
    return ctx == nullptr ? 0 : ctx->enc_count;
}

int mu_crypto_view_channel(const mu_crypto *c, mu_crypto_dir dir, int32_t channel, mu_crypto_view *out) {
    const Context *ctx = find(c, dir, channel);
    if (ctx == nullptr || out == nullptr) return -1;
    out->channel = ctx->channel;
    out->enc_count = ctx->enc_count;
    out->dec_count = ctx->dec_count;
    std::memcpy(out->state, ctx->state, sizeof out->state);
    out->word_8c = ctx->word_8c;
    out->choice = ctx->choice;
    out->keyings = ctx->keyings;
    return 0;
}

size_t mu_crypto_channels(const mu_crypto *c, mu_crypto_dir dir, int32_t *out, size_t cap) {
    const Map *m = map_of(c, dir);
    if (m == nullptr) return 0;
    size_t i = 0;
    for (const auto &entry : *m) {
        if (out != nullptr && i < cap) out[i] = entry.first;
        ++i;
    }
    return i;
}

mu_crypto_cipher *mu_crypto_cipher_new(uint32_t index, const uint8_t *key, size_t key_len) {
    if (key == nullptr && key_len != 0) return nullptr;
    try {
        static const std::uint8_t zero[1] = {0};
        return factory(index, key ? key : zero, key ? key_len : 0).release();
    } catch (...) {
        return nullptr;
    }
}

void mu_crypto_cipher_free(mu_crypto_cipher *h) { delete h; }

int32_t mu_crypto_cipher_case(const mu_crypto_cipher *h) { return h ? h->cipher_case : -1; }
uint32_t mu_crypto_cipher_interval(const mu_crypto_cipher *h) { return h ? h->interval : 0; }
uint32_t mu_crypto_cipher_block(const mu_crypto_cipher *h) { return h ? static_cast<uint32_t>(h->block) : 0; }
uint32_t mu_crypto_cipher_key_len(const mu_crypto_cipher *h) { return h ? kCases[h->cipher_case].key_len : 0; }

int32_t mu_crypto_cipher_encrypt(mu_crypto_cipher *h, uint8_t *dst, size_t dst_cap, const uint8_t *src, size_t len) {
    if (h == nullptr || (src == nullptr && len != 0)) return MU_CRYPTO_OUTSIDE;
    bool outside = false;
    const std::int32_t size = wrapper_encrypt(*h, nullptr, src, len, &outside);
    if (dst == nullptr || outside) return size;
    if (static_cast<std::size_t>(size) > dst_cap) return MU_CRYPTO_OUTSIDE;
    return wrapper_encrypt(*h, dst, src, len, &outside);
}

int32_t mu_crypto_cipher_decrypt(mu_crypto_cipher *h, uint8_t *dst, size_t dst_cap, const uint8_t *src, size_t len) {
    if (h == nullptr || (src == nullptr && len != 0)) return MU_CRYPTO_OUTSIDE;
    std::int32_t want = 0;
    if (dst != nullptr && len <= 0xffffffffU && decrypt_length(*h, src, len, &want) &&
        static_cast<std::uint32_t>(want) - 1U <= 0xfffU && static_cast<std::size_t>(want) > dst_cap) {
        return MU_CRYPTO_OUTSIDE;
    }
    return wrapper_decrypt(*h, dst, src, len);
}

int mu_crypto_block(int32_t cipher_case, int decrypt, const uint8_t *key, size_t key_len, const uint8_t *in,
                    uint8_t *out) {
    if (cipher_case < 0 || cipher_case >= MU_CRYPTO_CASES || in == nullptr || out == nullptr) return -1;
    if (key == nullptr && key_len != 0) return -1;
    std::uint8_t k[64] = {0};
    if (key != nullptr && key_len != 0) std::memcpy(k, key, key_len < sizeof k ? key_len : sizeof k);
    try {
        // The class alone, without the factory's selection (index 9 would tie key[0] & 7 to
        // the class, which published vectors do not follow).
        auto h = build_case(cipher_case, k);
        if (decrypt) h->dec->ProcessBlock(in, out);
        else h->enc->ProcessBlock(in, out);
        return 0;
    } catch (...) {
        return -1;
    }
}

}  // extern "C"
