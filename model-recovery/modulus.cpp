// Independently implemented BMD v14 envelope reader. See SOURCES.md.
// Crypto++ supplies the block ciphers; no original game code is executed.
#include <cryptopp/3way.h>
#include <cryptopp/cast.h>
#include <cryptopp/gost.h>
#include <cryptopp/idea.h>
#include <cryptopp/mars.h>
#include <cryptopp/rc5.h>
#include <cryptopp/rc6.h>
#include <cryptopp/tea.h>

#include <cstddef>
#include <cstdio>
#include <cstring>
#include <exception>
#include <memory>
#include <stdexcept>
#include <vector>

namespace {
constexpr std::size_t max_input = 128U * 1024U * 1024U;
constexpr std::size_t prefix_size = 34;
// Published asset-format constant, not a user authentication credential.
constexpr unsigned char outer_key[] = "webzen#@!01webzen#@!01webzen#@!0";
static_assert(sizeof(outer_key) == 33, "Expected 32-byte format key");

template <typename Algorithm>
std::unique_ptr<CryptoPP::BlockCipher> cipher(const unsigned char* key) {
    auto result = std::make_unique<typename Algorithm::Decryption>();
    // The published format uses each algorithm's default key length, even
    // though the envelope reserves 32 bytes for every embedded key.
    result->SetKey(key, Algorithm::DEFAULT_KEYLENGTH);
    return result;
}

std::unique_ptr<CryptoPP::BlockCipher> select(unsigned char selector,
                                           const unsigned char* key) {
    switch (selector & 7U) {
        case 0: return cipher<CryptoPP::TEA>(key);
        case 1: return cipher<CryptoPP::ThreeWay>(key);
        case 2: return cipher<CryptoPP::CAST128>(key);
        case 3: return cipher<CryptoPP::RC5>(key);
        case 4: return cipher<CryptoPP::RC6>(key);
        case 5: return cipher<CryptoPP::MARS>(key);
        case 6: return cipher<CryptoPP::IDEA>(key);
        case 7: return cipher<CryptoPP::GOST>(key);
    }
    throw std::runtime_error("Invalid cipher selector");
}

void decrypt_range(CryptoPP::BlockCipher& algorithm,
                   std::vector<unsigned char>& bytes,
                   std::size_t offset, std::size_t length) {
    const std::size_t block = algorithm.BlockSize();
    if (offset > bytes.size() || length > bytes.size() - offset ||
        block == 0 || length % block != 0) {
        throw std::runtime_error("Cipher range exceeds envelope bounds");
    }
    for (std::size_t i = 0; i < length; i += block) {
        algorithm.ProcessBlock(bytes.data() + offset + i);
    }
}
}  // namespace

extern "C" int mu_modulus_decrypt(const unsigned char* input, std::size_t length,
                                  unsigned char* output, std::size_t capacity,
                                  std::size_t* written,
                                  char* error, std::size_t error_capacity) noexcept {
    if (written != nullptr) *written = 0;
    if (error != nullptr && error_capacity != 0) error[0] = '\0';
    try {
        if (input == nullptr || output == nullptr || written == nullptr ||
            length < prefix_size || length > max_input ||
            capacity < length - prefix_size) {
            throw std::runtime_error("Invalid v14 buffer or size");
        }
        std::vector<unsigned char> bytes(input, input + length);
        const std::size_t body = length - prefix_size;
        auto outer = select(bytes[1], outer_key);
        const std::size_t span = 1024U - (1024U % outer->BlockSize());
        // These windows may overlap. Undo them in reverse encoding order.
        if (body > 4U * span) {
            decrypt_range(*outer, bytes, 2U + body / 2U, span);
        }
        if (body > span) {
            decrypt_range(*outer, bytes, length - span, span);
            decrypt_range(*outer, bytes, 2U, span);
        }
        auto inner = select(bytes[0], bytes.data() + 2U);
        const std::size_t aligned = body - body % inner->BlockSize();
        decrypt_range(*inner, bytes, prefix_size, aligned);
        // The final partial inner block is stored unchanged, not padded.
        std::memcpy(output, bytes.data() + prefix_size, body);
        *written = body;
        return 0;
    } catch (const std::exception& failure) {
        if (error != nullptr && error_capacity != 0) {
            std::snprintf(error, error_capacity, "%s", failure.what());
        }
    } catch (...) {
        if (error != nullptr && error_capacity != 0) {
            std::snprintf(error, error_capacity, "Unknown v14 decoding error");
        }
    }
    return 1;
}
