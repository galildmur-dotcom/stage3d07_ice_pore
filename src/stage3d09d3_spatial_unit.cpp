#include "p09d3_pair.hpp"
#include <array>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <vector>
struct P {double x,y,z;};
int main(){
 namespace d=ice3d::p09d3;namespace fs=std::filesystem;
 d::selftest();
 const fs::path dir=fs::temp_directory_path()/"P09D3_pair_unit_v1";
 fs::create_directories(dir);
 const auto a=dir/"plus.bin",b=dir/"minus.bin",corrupted=dir/"bad.bin";
 try{
  const std::vector<P>nodes={{0,0,.03},{.001,0,.03},{0,.001,.03},{0,0,.031},{.02,0,.03},{.02,.001,.03},{.02,0,.031},{.022,0,.03},{.022,.001,.03},{.022,0,.031},{.002,0,.032},{.023,.001,.031}};
  std::vector<std::array<int,10>>tet={{{0,1,2,3,4,5,6,7,8,9}},{{4,5,6,7,8,9,0,1,2,3}}};
  const std::vector<std::uint8_t>mask={1,0};
  const std::vector<d::Point>pa={{2.,1.02,2.,3.,4.},{3.,1.08,4.,6.,7.},{},{}};
  const std::vector<d::Point>ma={{2.5,1.025,4.,5.,6.},{2.,1.079,3.,4.,5.},{},{}};
  const auto sa=d::write_points(a,nodes.size(),tet,mask,nodes,2,pa);
  const auto sb=d::write_points(b,nodes.size(),tet,mask,nodes,2,ma);
  if(sa.nqp!=2||sb.nqp!=2||sa.active!=1||sb.active!=1)throw std::runtime_error("P09D3 QP binary write failed");
  auto r=d::pair_files(a,b,5e-6);
  if(r.h.active!=1||r.all.nqp!=2||d::rel_error(r.all.p8.full,(sa.p8-sb.p8)/(1e-5))>1e-12)
   throw std::runtime_error("P09D3 paired binary identity failed");
  if(r.bins[0].nqp!=1||r.bins[1].nqp!=1)throw std::runtime_error("P09D3 radial paired classification failed");
  tet[0][0]=1;
  d::write_points(corrupted,nodes.size(),tet,mask,nodes,2,ma);
  bool rejected=false;
  try{(void)d::pair_files(a,corrupted,5e-6);}catch(const std::runtime_error&){rejected=true;}
  if(!rejected)throw std::runtime_error("P09D3 failed to reject mismatched connectivity");
  fs::remove_all(dir);
  std::cout<<"P09D3_PAIR_BINARY_SELFTEST_OK\n";
 }catch(...){fs::remove_all(dir);throw;}
}
