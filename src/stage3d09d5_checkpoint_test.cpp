// Independent binary I/O test for checkpoints larger than Windows 2-GiB boundary.
// Self-contained; uses the exact bounded read/write routines of the FEM solver.
#include "checkpoint_chunked_io.hpp"
#include <array>
#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
int main(int argc, char** argv) {
  try {
    bool large = false;
    fs::path dest = "P09D5_IO_CHECK.bin";
    for (int k=1;k<argc;++k) {
      const std::string s=argv[k];
      if(s=="--large")large=true;
      else if(s=="--small")large=false;
      else if(s=="--out"&&k+1<argc)dest=argv[++k];
      else throw std::runtime_error("Usage: [--small|--large] [--out PATH]");
    }
    constexpr std::size_t block = 8u*1024u*1024u;
    const std::uint64_t total = large ? 3ull*1024*1024*1024 + 64ull*1024*1024 : 40ull*1024*1024;
    std::vector<std::uint8_t> a(block), b(block);
    for(std::size_t i=0;i<a.size();++i)a[i]=static_cast<std::uint8_t>((i*131u+i/1231u+17u)&255u);
    struct RemoveOnExit {fs::path p; ~RemoveOnExit(){std::error_code ec;fs::remove(p,ec);}} cleanup{dest};
    {
      std::ofstream out(dest,std::ios::binary|std::ios::trunc);
      if(!out)throw std::runtime_error("cannot create test file: "+dest.string());
      for(std::uint64_t pos=0;pos<total;pos+=block){
        const auto len=static_cast<std::size_t>(std::min<std::uint64_t>(block,total-pos));
        ice3d::checkpoint_io::write_bytes(out,a.data(),len);
      }
      out.close();
      if(!out)throw std::runtime_error("cannot complete test file");
    }
    if(fs::file_size(dest)!=total)throw std::runtime_error("file size mismatch");
    {
      std::ifstream in(dest,std::ios::binary);
      if(!in)throw std::runtime_error("cannot reopen test file");
      for(std::uint64_t pos=0;pos<total;pos+=block){
        const auto len=static_cast<std::size_t>(std::min<std::uint64_t>(block,total-pos));
        ice3d::checkpoint_io::read_bytes(in,b.data(),len);
        if(!std::equal(a.begin(),a.begin()+len,b.begin()))throw std::runtime_error("readback data mismatch");
        if(large && (pos % (512ull*1024*1024) == 0))
          std::cerr<<"[P09D5 IO TEST] verified "<<pos/(1024*1024)<<" MiB\n";
      }
      char trailing=0;
      if(in.read(&trailing,1))throw std::runtime_error("trailing bytes");
    }
    std::cout << "P09D5_IO_TEST_OK bytes=" << total << " large=" << (large?1:0) << '\n';
    return 0;
  } catch (const std::exception& e){
    std::cerr << "P09D5_IO_TEST_FAILED: " << e.what() << '\n';
    return 1;
  }
}
