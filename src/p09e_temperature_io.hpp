#pragma once
// P09E: exact double precision thermal field, one fixed-layout file per time step.
// Intentionally independent of the Mesh class used in either solver.
#include <bit>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
#include <algorithm>

namespace ice3d::p09e {
namespace fs=std::filesystem;
static constexpr std::uint64_t MAGIC=0x45524D4854333950ULL; // P9THMRE (byte-identifiable)
static constexpr std::uint64_t VERSION=1;
static constexpr std::uint64_t FNV_START=14695981039346656037ULL;
static constexpr std::uint64_t FNV_PRIME=1099511628211ULL;
static constexpr std::uint64_t MAX_CHUNK=16ULL*1024*1024;

inline std::uint64_t mix(std::uint64_t h,std::uint64_t x){return (h^x)*FNV_PRIME;}
template <class Mesh> std::uint64_t mesh_signature(const Mesh&m){
 std::uint64_t h=FNV_START;
 for(const auto&x:m.nodes){h=mix(h,std::bit_cast<std::uint64_t>(x.x));h=mix(h,std::bit_cast<std::uint64_t>(x.y));h=mix(h,std::bit_cast<std::uint64_t>(x.z));}
 for(const auto&t:m.tets)for(int a:t)h=mix(h,static_cast<std::uint32_t>(a));
 return h;
}
inline std::uint64_t checksum(const std::vector<double>&v){
 std::uint64_t h=FNV_START;
 const auto*bytes=reinterpret_cast<const unsigned char*>(v.data());
 for(std::size_t i=0;i<v.size()*sizeof(double);++i)h=mix(h,bytes[i]);
 return h;
}
template<class T> void scalar_write(std::ofstream&out,const T&v){out.write(reinterpret_cast<const char*>(&v),sizeof(v));if(!out)throw std::runtime_error("P09E: header write failed");}
template<class T> void scalar_read(std::ifstream&in,T&v){in.read(reinterpret_cast<char*>(&v),sizeof(v));if(!in)throw std::runtime_error("P09E: truncated header");}
inline void write_chunks(std::ofstream&o,const void*data,std::uint64_t n){
 const auto*p=static_cast<const char*>(data);
 while(n){const auto part=static_cast<std::streamsize>(std::min(n,MAX_CHUNK));o.write(p,part);if(!o)throw std::runtime_error("P09E: field write failed");p+=part;n-=static_cast<std::uint64_t>(part);}
}
inline void read_chunks(std::ifstream&i,void*data,std::uint64_t n){
 auto*p=static_cast<char*>(data);
 while(n){const auto part=static_cast<std::streamsize>(std::min(n,MAX_CHUNK));i.read(p,part);if(!i)throw std::runtime_error("P09E: truncated thermal field");p+=part;n-=static_cast<std::uint64_t>(part);}
}
struct Header{std::uint64_t magic=0,version=0,nodes=0,signature=0,step=0,hash=0;};
inline Header header(const fs::path&file){
 std::ifstream in(file,std::ios::binary);if(!in)throw std::runtime_error("P09E: missing thermal field: "+file.string());
 Header h;scalar_read(in,h.magic);scalar_read(in,h.version);scalar_read(in,h.nodes);scalar_read(in,h.signature);scalar_read(in,h.step);scalar_read(in,h.hash);
 if(h.magic!=MAGIC||h.version!=VERSION)throw std::runtime_error("P09E: invalid thermal field header");
 return h;
}
template<class Mesh> void write(const fs::path&path,const Mesh&m,const std::vector<double>&theta,int step){
 if(theta.size()!=m.nodes.size()||step<=0)throw std::runtime_error("P09E: invalid thermal field dimensions/time");
 for(double x:theta)if(!std::isfinite(x))throw std::runtime_error("P09E: nonfinite temperature");
 fs::create_directories(path.parent_path());const fs::path tmp=path.string()+".part";
 std::ofstream o(tmp,std::ios::binary|std::ios::trunc);if(!o)throw std::runtime_error("P09E: cannot create "+tmp.string());
 for(auto v: {MAGIC,VERSION,std::uint64_t(theta.size()),mesh_signature(m),std::uint64_t(step),checksum(theta)})scalar_write(o,v);
 write_chunks(o,theta.data(),theta.size()*sizeof(double));o.close();if(!o)throw std::runtime_error("P09E: failed closing thermal file");
 if(fs::exists(path))fs::remove(path);
 fs::rename(tmp,path);
}
template<class Mesh> std::vector<double> read(const fs::path&path,const Mesh&m,int step){
 std::ifstream in(path,std::ios::binary);if(!in)throw std::runtime_error("P09E: cannot open "+path.string());
 Header h;scalar_read(in,h.magic);scalar_read(in,h.version);scalar_read(in,h.nodes);scalar_read(in,h.signature);scalar_read(in,h.step);scalar_read(in,h.hash);
 if(h.magic!=MAGIC||h.version!=VERSION||h.nodes!=m.nodes.size()||h.signature!=mesh_signature(m)||h.step!=std::uint64_t(step))
  throw std::runtime_error("P09E: mesh signature, node count or time mismatch: "+path.string());
 if(h.nodes>(std::numeric_limits<std::size_t>::max()/sizeof(double)))throw std::runtime_error("P09E: invalid node count");
 std::vector<double>theta(static_cast<std::size_t>(h.nodes));read_chunks(in,theta.data(),h.nodes*sizeof(double));
 char extra;if(in.get(extra))throw std::runtime_error("P09E: trailing bytes in thermal file");
 if(checksum(theta)!=h.hash)throw std::runtime_error("P09E: temperature checksum mismatch: "+path.string());
 for(double x:theta)if(!std::isfinite(x))throw std::runtime_error("P09E: nonfinite temperature in file");
 return theta;
}
template<class Mesh> std::vector<double> load(const fs::path&dir,const Mesh&m,int step){
 const auto bin=dir/("thermal_"+std::to_string(step)+"s.p09e");
 if(!fs::is_regular_file(bin))throw std::runtime_error("P09E: missing compact field "+bin.string());
 return read(bin,m,step);
}
} // namespace ice3d::p09e
