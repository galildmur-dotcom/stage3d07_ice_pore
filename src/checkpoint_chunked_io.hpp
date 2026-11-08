#pragma once
// Stage 3D-09D5: bounded-size binary checkpoint I/O for Windows MinGW.
// Never pass multi-gigabyte counts to a single std::filebuf::xsputn/xsgetn.
// Preserve the existing checkpoint header and byte-for-byte binary layout.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace ice3d::checkpoint_io {
inline constexpr std::size_t block_bytes = 16u * 1024u * 1024u;
inline constexpr std::uint64_t progress_bytes = 512ull * 1024ull * 1024ull;

inline void write_bytes(std::ofstream& out, const void* data, std::uint64_t size,
                        const char* label = nullptr) {
  const char* p = static_cast<const char*>(data);
  std::uint64_t done = 0;
  std::uint64_t next_progress = progress_bytes;
  while (done < size) {
    const auto block = static_cast<std::size_t>(std::min<std::uint64_t>(size - done, block_bytes));
    out.write(p + static_cast<std::size_t>(done), static_cast<std::streamsize>(block));
    if (!out) throw std::runtime_error("checkpoint write failed (disk/stream error)");
    done += block;
    if (label && (done >= next_progress || done == size)) {
      std::cerr << "[P09D5 CHECKPOINT] " << label << " " << done << "/" << size << " bytes\n" << std::flush;
      next_progress = done + progress_bytes;
    }
  }
}

inline void read_bytes(std::ifstream& in, void* data, std::uint64_t size) {
  char* p = static_cast<char*>(data);
  std::uint64_t done = 0;
  while (done < size) {
    const auto block = static_cast<std::size_t>(std::min<std::uint64_t>(size - done, block_bytes));
    in.read(p + static_cast<std::size_t>(done), static_cast<std::streamsize>(block));
    if (!in) throw std::runtime_error("checkpoint read failed (truncated/stream error)");
    done += block;
  }
}
} // namespace ice3d::checkpoint_io
