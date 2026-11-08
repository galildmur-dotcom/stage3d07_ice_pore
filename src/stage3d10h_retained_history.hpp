#pragma once
// Stage 3D-10H: opt-in production EDV history retention for future adjoint
// replay. Inclusion contract: include AFTER spatial_reology.cpp checkpoint()
// and restore() definitions. No changes to legacy restart.bin/6-hour policy.
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>

namespace ice3d::p10h {

inline constexpr std::uint64_t fnv_seed=14695981039346656037ull;
inline constexpr std::uint64_t fnv_multiplier=1099511628211ull;

struct Budget {
 int interval=0;
 double max_gib=1.0;
};

inline std::uint64_t checksum(const fs::path& file){
 std::ifstream in(file,std::ios::binary);
 if(!in)throw std::runtime_error("P10H cannot open history snapshot for checksum");
 std::array<char,1<<16> block{};
 std::uint64_t h=fnv_seed;
 while(in){
  in.read(block.data(),std::streamsize(block.size()));
  for(std::streamsize i=0;i<in.gcount();++i){
   h^=static_cast<unsigned char>(block[size_t(i)]);
   h*=fnv_multiplier;
  }
 }
 if(!in.eof())throw std::runtime_error("P10H checksum streaming error");
 return h;
}

inline fs::path integrity_path(const fs::path& checkpoint_file){
 fs::path result=checkpoint_file;
 result+=".fnv64";
 return result;
}

inline fs::path named_file(const fs::path& destination,int step){
 if(step<0)throw std::runtime_error("P10H negative snapshot step");
 std::ostringstream name;
 name<<"step_"<<std::setw(6)<<std::setfill('0')<<step<<".bin";
 return destination/"adjoint_history"/name.str();
}

inline std::uint64_t estimate_single_bytes(const Mesh& mesh,size_t nq){
 // Exact P09D5 header: 4 uint64, 2 int32, 2 uint32, 1 double = 56 bytes.
 const long double size=56.L+
       3.L*mesh.nodes.size()*sizeof(double)+
       static_cast<long double>(mesh.tets.size())*nq*sizeof(State);
 if(!std::isfinite(size)||size>static_cast<long double>(
      std::numeric_limits<std::uint64_t>::max()))
  throw std::runtime_error("P10H snapshot byte size overflow");
 return std::uint64_t(size);
}

inline std::uint64_t estimated_total(const Budget& policy,const Mesh& mesh,
                                   size_t nq,int steps){
 if(policy.interval<=0)throw std::runtime_error(
      "P10H --adjoint-snapshot-steps must be positive");
 if(steps<=0)throw std::runtime_error("P10H empty time sequence");
 if(!(std::isfinite(policy.max_gib)&&policy.max_gib>0))throw std::runtime_error(
      "P10H --adjoint-max-disk-gb must be finite and positive");
 const std::uint64_t count=1+std::uint64_t((steps-1)/policy.interval+1);
 const long double bytes=(static_cast<long double>(estimate_single_bytes(mesh,nq))+8)*count;
 if(bytes>policy.max_gib*(1024.L*1024.L*1024.L)){
  std::ostringstream e;
  e<<"P10H preflight budget exceeded: would retain "
   <<std::setprecision(5)<<double(bytes/(1024.L*1024.L*1024.L))
   <<" GiB, configured limit "<<policy.max_gib<<" GiB";
  throw std::runtime_error(e.str());
 }
 if(bytes>static_cast<long double>(std::numeric_limits<std::uint64_t>::max()))
  throw std::runtime_error("P10H aggregate disk overflow");
 return std::uint64_t(bytes);
}

inline bool scheduled(const Budget& policy,int completed,int total){
 if(policy.interval<=0)return false;
 return completed==0||completed==total||completed%policy.interval==0;
}

inline void retain(const fs::path& dest,const Mesh& mesh,const Setting& setting,
                   const Field& state,int completed){
 const auto path=named_file(dest,completed);
 const auto verify=integrity_path(path);
 if(fs::exists(path)||fs::exists(verify))
  throw std::runtime_error("P10H retained snapshot already exists: "+path.string());
 checkpoint(path,mesh,setting,state,completed);
 const std::uint64_t hash=checksum(path);
 auto partial=verify;partial+=".part";
 if(fs::exists(partial))throw std::runtime_error("P10H checksum staging file exists");
 {
  std::ofstream side(partial,std::ios::binary|std::ios::trunc);
  if(!side)throw std::runtime_error("P10H cannot create checksum sidecar");
  side.write(reinterpret_cast<const char*>(&hash),sizeof(hash));
  side.close();
  if(!side)throw std::runtime_error("P10H checksum sidecar write failed");
 }
 fs::rename(partial,verify);
}

inline Field recover(const fs::path& dest,const Mesh& mesh,const Setting& setting,
                     int completed,double expected_time,size_t nq){
 const auto path=named_file(dest,completed);
 const auto verify=integrity_path(path);
 std::ifstream side(verify,std::ios::binary);
 std::uint64_t expected_hash=0;
 side.read(reinterpret_cast<char*>(&expected_hash),sizeof(expected_hash));
 char extra{};
 if(!side||side.read(&extra,1))throw std::runtime_error(
     "P10H checksum sidecar missing or malformed");
 if(checksum(path)!=expected_hash)throw std::runtime_error(
     "P10H retained snapshot checksum mismatch");
 Field state;
 state.u.resize(mesh.nodes.size()*3);
 state.qstate.resize(mesh.tets.size()*nq);
 const int loaded=restore(path,mesh,setting,state);
 if(loaded!=completed||!std::isfinite(state.lastTime)||
    std::abs(state.lastTime-expected_time)>1e-8)
  throw std::runtime_error("P10H retained snapshot step/time mismatch");
 return state;
}
} // namespace ice3d::p10h
