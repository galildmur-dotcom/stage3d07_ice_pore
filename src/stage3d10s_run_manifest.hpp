#pragma once

// Stage3D10S-only reproducibility manifest. Standard C++20; no FEM dependencies.
// The file is placed in --out after the solver creates that directory.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#ifndef STAGE3D10S_GIT_COMMIT_AT_CONFIGURE
#define STAGE3D10S_GIT_COMMIT_AT_CONFIGURE "UNKNOWN"
#endif

namespace ice3d::stage3d10s_manifest {
namespace fs = std::filesystem;

inline std::vector<std::string>& arguments() {
  static std::vector<std::string> args;
  return args;
}
inline void set_arguments(int argc, char** argv) {
  auto& out = arguments();
  out.clear();
  for (int i = 0; i < argc; ++i) out.emplace_back(argv[i] ? argv[i] : "");
}

inline std::string json_string(const std::string& source) {
  std::ostringstream out;
  out << '"';
  static constexpr char hex[] = "0123456789abcdef";
  for (unsigned char c : source) {
    switch (c) {
      case '"': out << "\\\""; break;
      case '\\': out << "\\\\"; break;
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default:
        if (c < 32) out << "\\u00" << hex[c >> 4] << hex[c & 15];
        else out << static_cast<char>(c);
    }
  }
  out << '"';
  return out.str();
}

inline std::string utc_now() {
  const auto time = std::chrono::system_clock::to_time_t(
      std::chrono::system_clock::now());
  const std::tm* utc = std::gmtime(&time);
  if (!utc) throw std::runtime_error("Cannot obtain UTC time");
  std::ostringstream out;
  out << std::put_time(utc, "%Y-%m-%dT%H:%M:%SZ");
  return out.str();
}

class Sha256 {
  std::array<std::uint32_t, 8> state_{{0x6a09e667, 0xbb67ae85, 0x3c6ef372,
      0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19}};
  std::array<std::uint8_t, 64> block_{};
  std::uint64_t bytes_ = 0;
  std::size_t buffered_ = 0;
  static constexpr std::array<std::uint32_t, 64> k_{{
      0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
      0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
      0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
      0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
      0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
      0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
      0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
      0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2}};
  static std::uint32_t rotate(std::uint32_t x, unsigned n) {
    return (x >> n) | (x << (32 - n));
  }
  void compress() {
    std::array<std::uint32_t, 64> w{};
    for (std::size_t i = 0; i < 16; ++i) {
      const std::size_t p = 4 * i;
      w[i] = (std::uint32_t(block_[p]) << 24) |
             (std::uint32_t(block_[p+1]) << 16) |
             (std::uint32_t(block_[p+2]) << 8) | std::uint32_t(block_[p+3]);
    }
    for (std::size_t i = 16; i < 64; ++i) {
      const auto s0 = rotate(w[i-15],7) ^ rotate(w[i-15],18) ^ (w[i-15] >> 3);
      const auto s1 = rotate(w[i-2],17) ^ rotate(w[i-2],19) ^ (w[i-2] >> 10);
      w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    std::uint32_t a = state_[0], b = state_[1], c = state_[2], d = state_[3];
    std::uint32_t e = state_[4], f = state_[5], g = state_[6], h = state_[7];
    for (std::size_t i = 0; i < 64; ++i) {
      const auto s1 = rotate(e,6) ^ rotate(e,11) ^ rotate(e,25);
      const auto ch = (e & f) ^ (~e & g);
      const auto t1 = h + s1 + ch + k_[i] + w[i];
      const auto s0 = rotate(a,2) ^ rotate(a,13) ^ rotate(a,22);
      const auto maj = (a & b) ^ (a & c) ^ (b & c);
      const auto t2 = s0 + maj;
      h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    const std::array<std::uint32_t, 8> result{{a,b,c,d,e,f,g,h}};
    for (std::size_t i = 0; i < 8; ++i) state_[i] += result[i];
  }
public:
  void update(const std::uint8_t* data, std::size_t count) {
    bytes_ += count;
    while (count) {
      const auto copy = std::min(count, block_.size() - buffered_);
      std::copy_n(data, copy, block_.data() + buffered_);
      data += copy; count -= copy; buffered_ += copy;
      if (buffered_ == block_.size()) { compress(); buffered_ = 0; }
    }
  }
  std::string finish_hex() {
    const std::uint64_t bits = bytes_ * 8;
    const std::uint8_t one = 0x80;
    update(&one, 1);
    const std::uint8_t zero = 0;
    while (buffered_ != 56) update(&zero, 1);
    std::array<std::uint8_t, 8> length{};
    for (unsigned i = 0; i < 8; ++i)
      length[7 - i] = std::uint8_t(bits >> (8 * i));
    update(length.data(), length.size());
    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (std::uint32_t value : state_) out << std::setw(8) << value;
    return out.str();
  }
};

inline std::string sha256_file(const fs::path& path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) throw std::runtime_error("Manifest cannot open file: " + path.string());
  Sha256 hash;
  std::array<char, 1024 * 1024> buffer{};
  while (input) {
    input.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
    const auto size = input.gcount();
    if (size > 0) hash.update(reinterpret_cast<const std::uint8_t*>(buffer.data()),
                              static_cast<std::size_t>(size));
  }
  if (!input.eof()) throw std::runtime_error("Manifest read error: " + path.string());
  return hash.finish_hex();
}

class RunManifest {
  fs::path out_, mesh_, reuse_, cache_;
  std::vector<double> deltas_;
  std::string started_, mesh_hash_, executable_hash_, error_;
  std::chrono::steady_clock::time_point started_clock_;
  double dt_;
  int steps_, threads_;
  double cutoff_;
  std::string mode_;
  bool preflight_;
  bool finalized_ = false;

  void write(const std::string& status, const std::optional<int>& exit_code) const {
    const fs::path output = out_ / "RUN_MANIFEST.json";
    const fs::path temporary = out_ / "RUN_MANIFEST.json.tmp";
    std::ofstream file(temporary, std::ios::binary | std::ios::trunc);
    if (!file) throw std::runtime_error("Cannot create RUN_MANIFEST.json.tmp");
    file << "{\n  \"schema_version\": 1,\n"
         << "  \"run_id\": " << json_string(out_.filename().string()) << ",\n"
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
         << "  \"program\": \"stage3d10y_analytic_shell_audit\",\n"
#else
         << "  \"program\": \"stage3d10s_spatial_partial\",\n"
#endif
         << "  \"status\": " << json_string(status) << ",\n"
         << "  \"started_at_utc\": " << json_string(started_) << ",\n"
         << "  \"updated_at_utc\": " << json_string(utc_now()) << ",\n"
         << "  \"exit_code\": ";
    if (exit_code) file << *exit_code; else file << "null";
    file << ",\n  \"elapsed_manifest_wall_s\": " << std::setprecision(15)
         << std::chrono::duration<double>(std::chrono::steady_clock::now()-started_clock_).count()
         << ",\n  \"code\": {\n"
         << "    \"git_commit_at_cmake_configure\": "
         << json_string(STAGE3D10S_GIT_COMMIT_AT_CONFIGURE) << ",\n"
         << "    \"executable_sha256\": ";
    if (executable_hash_.empty()) file << "null";
    else file << json_string(executable_hash_);
    file << "\n  },\n  \"input\": {\n"
         << "    \"mesh\": " << json_string(mesh_.string()) << ",\n"
         << "    \"mesh_sha256\": ";
    if (mesh_hash_.empty()) file << "null";
    else file << json_string(mesh_hash_);
    file << ",\n    \"output_dir\": " << json_string(out_.string()) << ",\n"
         << "    \"model\": \"EDV\",\n"
         << "    \"temperature_model\": \"VAR\",\n"
         << "    \"stochastic_quadrature\": null,\n"
         << "    \"dt_s\": " << std::setprecision(17) << dt_ << ",\n"
         << "    \"steps\": " << steps_ << ",\n"
         << "    \"geometry_mode\": " << json_string(mode_) << ",\n"
         << "    \"delta_um\": [";
    for (std::size_t i = 0; i < deltas_.size(); ++i) {
      if (i) file << ", ";
      file << std::setprecision(17) << deltas_[i];
    }
    file << "],\n    \"threads\": " << threads_ << ",\n"
         << "    \"cutoff_mm\": " << std::setprecision(17) << cutoff_ << ",\n"
         << "    \"preflight\": " << (preflight_ ? "true" : "false") << ",\n"
         << "    \"reuse_forward\": " << json_string(reuse_.string()) << ",\n"
         << "    \"forward_cache\": " << json_string(cache_.string())
         << "\n  },\n  \"argv\": [";
    for (std::size_t i = 0; i < arguments().size(); ++i) {
      if (i) file << ", ";
      file << json_string(arguments()[i]);
    }
    file << "],\n  \"produced_files\": [";
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
    constexpr std::array<const char*, 6> expected{{
       "P10N_DELTA_SCAN.csv", "P10P_PARTIAL_COMPONENTS.csv", "P10P_STEP_COMPONENTS.csv",
       "P10Y_PARTITION_AUDIT.csv", "P10Y_SHELL_SUMMARY.csv", "P10Y_STEP_SHELL_COMPONENTS.csv"}};
#else
    constexpr std::array<const char*, 6> expected{{
       "P10N_DELTA_SCAN.csv", "P10P_PARTIAL_COMPONENTS.csv", "P10P_STEP_COMPONENTS.csv",
       "P10S_PARTITION_AUDIT.csv", "P10S_SHELL_SUMMARY.csv", "P10S_STEP_SHELL_COMPONENTS.csv"}};
#endif
    bool first = true;
    for (const auto* filename : expected) {
      if (fs::is_regular_file(out_ / filename)) {
        if (!first) file << ", ";
        file << json_string(filename); first = false;
      }
    }
    file << "],\n  \"exception_message\": ";
    if (error_.empty()) file << "null"; else file << json_string(error_);
    file << "\n}\n";
    file.close();
    if (!file) throw std::runtime_error("RUN_MANIFEST.json.tmp write failure");
    fs::rename(temporary, output); // atomic replacement in the same directory
  }
public:
  RunManifest(fs::path out, fs::path mesh, std::vector<double> deltas,
              double dt, int steps, std::string mode, int threads,
              double cutoff, bool preflight, fs::path reuse, fs::path cache)
      : out_(std::move(out)), mesh_(std::move(mesh)),
        reuse_(std::move(reuse)), cache_(std::move(cache)),
        deltas_(std::move(deltas)), started_(utc_now()),
        started_clock_(std::chrono::steady_clock::now()),
        dt_(dt), steps_(steps), threads_(threads), cutoff_(cutoff),
        mode_(std::move(mode)), preflight_(preflight) {
    if (!fs::is_directory(out_))
      throw std::runtime_error("Manifest output directory must exist");
    if (!std::isfinite(dt_) || !std::isfinite(cutoff_) ||
        std::any_of(deltas_.begin(), deltas_.end(),
                    [](double x) { return !std::isfinite(x); }))
      throw std::runtime_error("Manifest cannot record nonfinite parameters");
    write("running", std::nullopt);
    mesh_hash_ = sha256_file(mesh_);
    if (!arguments().empty()) {
      const fs::path executable = fs::absolute(arguments()[0]);
      if (fs::is_regular_file(executable)) executable_hash_ = sha256_file(executable);
    }
    write("running", std::nullopt);
  }
  void complete(int code) {
    write(preflight_ && code == 0 ? "preflight_ok" :
          (code == 0 ? "completed" : "failed_checks"), code);
    finalized_ = true;
  }
  ~RunManifest() noexcept {
    if (!finalized_) {
      try { write("failed_exception", 2); } catch (...) { /* keep solver exception */ }
    }
  }
};
} // namespace ice3d::stage3d10s_manifest
