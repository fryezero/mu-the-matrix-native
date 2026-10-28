// Native Data provenance and integrity, DATA-ACQ-004. No game-specific bytes.
#include "manifest.h"
#include <cryptopp/sha.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <map>
#include <set>
#include <vector>
#include <stdexcept>
#include <cstdio>
#include <cstdlib>
#include <unistd.h>
namespace fs = std::filesystem;
#ifndef MU_CLIENT_SHA256
#define MU_CLIENT_SHA256 "3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a"
#endif
namespace {
const char *name = "native-data.manifest";
struct Entry { std::string hash; uintmax_t size; bool operator==(const Entry &b) const { return hash == b.hash && size == b.size; } };
using Entries = std::map<std::string, Entry>;
std::string message(const std::string &why) {
    return "Native Data cannot be used: " + why + ". Re-acquire Native Data for this client build in a new folder, then run Setup again.";
}
void require(bool ok, const std::string &why) { if (!ok) throw std::runtime_error(why); }
bool digest(const std::string &s) { return s.size() == 64 && s.find_first_not_of("0123456789abcdef") == std::string::npos; }
bool safe(const std::string &s) {
    if (s.empty() || s.front() == '/' || s.find_first_of("\r\n\t\\") != std::string::npos) return false;
    for (const auto &part : fs::path(s)) if (part == ".." || part == "." || part.empty()) return false;
    return true;
}
Entry hashFile(const fs::path &p) {
    require(fs::is_regular_file(fs::symlink_status(p)), "missing file or symlink: " + p.filename().string());
    std::ifstream f(p, std::ios::binary); require(bool(f), "cannot read " + p.filename().string());
    CryptoPP::SHA256 sha; char buf[65536]; uintmax_t size = 0;
    while (f.read(buf, sizeof buf) || f.gcount()) {
        auto n = static_cast<size_t>(f.gcount()); sha.Update(reinterpret_cast<const CryptoPP::byte *>(buf), n); size += n;
    }
    require(f.eof(), "read failed: " + p.filename().string());
    CryptoPP::byte bytes[32]; sha.Final(bytes); const char *hex = "0123456789abcdef"; std::string out;
    for (auto b : bytes) { out += hex[b >> 4]; out += hex[b & 15]; }
    return {out, size};
}
Entries inventory(const fs::path &dir) {
    require(fs::is_directory(dir) && !fs::is_symlink(fs::symlink_status(dir)), "missing data directory");
    Entries rows;
    for (const auto &e : fs::recursive_directory_iterator(dir)) {
        require(!e.is_symlink(), "symlink in Native Data");
        if (e.is_directory()) continue;
        auto rel = e.path().lexically_relative(dir).generic_string();
        if (rel == name || rel == "setup.json" || rel == "gfx-convert.json") continue;
        require(safe(rel), "unsafe entry path");
        rows.emplace(rel, hashFile(e.path()));
    }
    return rows;
}
struct Manifest { std::string build, producer; Entries inputs, files; };
fs::path managedRoot(const char *path) {
    if (!path || !*path) return {};
    fs::path managed;
    for (auto d = fs::absolute(path).lexically_normal(); !d.empty(); d = d.parent_path()) {
        if (fs::exists(d / name) || fs::exists(d / "setup.json") || d.filename() == "Native Data") managed = d;
        if (d == d.root_path()) break;
    }
    return managed;
}
Manifest read(const fs::path &dir) {
    require(fs::is_regular_file(fs::symlink_status(dir / name)), "missing manifest or symlink manifest");
    std::ifstream f(dir / name); require(bool(f), "missing manifest");
    Manifest m; std::string line; require(bool(std::getline(f, line)) && line == "MU_NATIVE_DATA 1", "invalid manifest version");
    require(bool(std::getline(f, line)) && line.rfind("client ", 0) == 0, "missing client build"); m.build = line.substr(7);
    require(digest(m.build), "invalid client build");
    require(bool(std::getline(f, line)) && line.rfind("producer ", 0) == 0 && safe(line.substr(9)), "missing producer"); m.producer = line.substr(9);
    bool end = false;
    while (std::getline(f, line)) {
        if (line.rfind("complete ", 0) == 0) {
            require(line == "complete " + std::to_string(m.files.size()) && !m.inputs.empty(), "incomplete manifest");
            end = true; break;
        }
        std::istringstream s(line); std::string kind, hash, bytes, path;
        require(bool(s >> kind >> hash >> bytes) && bool(std::getline(s, path)) && path.size() > 1 && path[0] == ' ', "malformed manifest entry");
        path.erase(0, 1);
        require((kind == "input" || kind == "file") && digest(hash) && safe(path) && bytes.find_first_not_of("0123456789") == std::string::npos, "invalid manifest entry");
        Entry e{hash, std::stoull(bytes)}; auto &rows = kind == "input" ? m.inputs : m.files;
        require(rows.emplace(path, e).second, "duplicate manifest entry");
    }
    require(end && !std::getline(f, line), "partial or trailing manifest");
    return m;
}
void check(const fs::path &dir, const fs::path &client = {}) {
    auto m = read(dir); require(m.build == MU_CLIENT_SHA256, "client build mismatch");
    if (!client.empty()) require(hashFile(client).hash == m.build, "installed main.exe build mismatch");
    require(inventory(dir) == m.files, "missing, added or tampered data entry");
    for (const auto &row : m.files) {
        fs::path path(row.first);
        if (path.filename() == name) check(dir / path.parent_path());
    }
}
[[maybe_unused]] void write(const fs::path &dir, const fs::path &client, const std::string &producer, const std::vector<fs::path> &sources) {
    auto build = hashFile(client).hash; require(build == MU_CLIENT_SHA256, "unsupported main.exe build");
    require(safe(producer) && !sources.empty(), "producer and source inputs required");
    // Incremental world exports retain the provenance of earlier worlds.
    Entries inputs;
    if (fs::exists(dir / name)) {
        auto previous = read(dir);
        require(previous.build == build, "previous export build mismatch");
        inputs = previous.inputs;
    }
    auto generation = std::to_string(inputs.size()) + "/";
    for (size_t i = 0; i < sources.size(); ++i) {
        auto prefix = generation + std::to_string(i) + "/";
        if (fs::is_directory(sources[i])) {
            auto rows = inventory(sources[i]); require(!rows.empty(), "empty source input");
            for (const auto &r : rows) inputs.emplace(prefix + r.first, r.second);
            if (fs::exists(sources[i] / name)) inputs.emplace(prefix + name, hashFile(sources[i] / name));
        } else inputs.emplace(prefix + sources[i].filename().string(), hashFile(sources[i]));
    }
    auto rows = inventory(dir);
    auto tmp = dir / (std::string(name) + ".tmp-" + std::to_string(getpid()));
    try {
        std::ofstream f(tmp); require(bool(f), "cannot create manifest");
        f << "MU_NATIVE_DATA 1\nclient " << build << "\nproducer " << producer << '\n';
        for (const auto &r : inputs) { require(safe(r.first), "unsafe input name"); f << "input " << r.second.hash << ' ' << r.second.size << ' ' << r.first << '\n'; }
        for (const auto &r : rows) f << "file " << r.second.hash << ' ' << r.second.size << ' ' << r.first << '\n';
        f << "complete " << rows.size() << '\n'; f.close(); require(bool(f), "cannot finish manifest");
        fs::rename(tmp, dir / name);
    } catch (...) { fs::remove(tmp); throw; }
}
}
extern "C" int mu_native_data_check_args(int argc, char **argv) {
    try {
        std::set<fs::path> roots;
        std::vector<fs::path> paths;
        for (int i = 1; i < argc; ++i) {
            // Display text may itself say "Native Data"; it is not a path.
            std::string arg = argv[i];
            if (arg == "--label" || arg == "--title" || arg == "--gfx-open") { ++i; continue; }
            paths.emplace_back(arg);
            auto p = managedRoot(argv[i]); if (!p.empty()) roots.insert(p);
        }
        for (const auto *key : {"MU_LANG_DIR", "MU_OBJECTS_PLAIN_DIR", "MU_GFX_DIR", "MU_AUDIO_TABLE"}) {
            auto p = managedRoot(std::getenv(key)); if (!p.empty()) roots.insert(p);
        }
        for (const auto &root : roots) check(root);
        if (!roots.empty()) {
            for (const auto &path : paths) {
                fs::path exe = path / "main.exe";
                if (fs::exists(exe)) require(hashFile(exe).hash == MU_CLIENT_SHA256, "installed main.exe build mismatch");
            }
        }
        return 1;
    } catch (const std::exception &e) { std::fprintf(stderr, "%s\n", message(e.what()).c_str()); return 0; }
}
#ifdef MU_MANIFEST_TOOL
int main(int argc, char **argv) {
    try {
        require(argc >= 3, "usage: mu-native-data pin MAIN.EXE | check DIR [MAIN.EXE] | write DIR MAIN.EXE PRODUCER INPUT...");
        std::string action = argv[1];
        if (action == "pin") { require(argc == 3 && hashFile(argv[2]).hash == MU_CLIENT_SHA256, "unsupported main.exe build"); }
        else if (action == "check") { require(argc == 3 || argc == 4, "invalid check arguments"); check(argv[2], argc == 4 ? fs::path(argv[3]) : fs::path()); }
        else if (action == "write") { require(argc >= 6, "source inputs required"); std::vector<fs::path> src; for (int i = 5; i < argc; ++i) src.emplace_back(argv[i]); write(argv[2], argv[3], argv[4], src); }
        else throw std::runtime_error("unknown manifest action");
        std::puts("Native Data manifest OK"); return 0;
    } catch (const std::exception &e) { std::fprintf(stderr, "%s\n", message(e.what()).c_str()); return 1; }
}
#endif
