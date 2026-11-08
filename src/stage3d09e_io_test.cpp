#include "p09e_temperature_io.hpp"
#include <array>
#include <iostream>
#include <cmath>
#include <string>
#include <cstdlib>
struct Node{double x,y,z;};
struct Mesh{std::vector<Node>nodes;std::vector<std::array<int,10>>tets;};
int main(int argc,char**argv){try{
 namespace fs=std::filesystem;
 fs::path out=argc>1?argv[1]:fs::temp_directory_path()/"p09e_io_test.p09e";
 Mesh m; m.nodes={{.0,.01,.02},{.001,.01,.02},{.002,.01,.02}};m.tets.push_back({0,1,2,0,1,2,0,1,2,0});
 std::vector<double> v={-0.5,0.0,0.123456789012345};
 ice3d::p09e::write(out,m,v,300);
 auto r=ice3d::p09e::read(out,m,300);
 if(v!=r)throw std::runtime_error("P09E selftest: bit-identical double failed");
 bool badtime=false;try{(void)ice3d::p09e::read(out,m,600);}catch(const std::runtime_error&){badtime=true;}
 if(!badtime)throw std::runtime_error("P09E selftest: wrong time accepted");
 Mesh changed=m;changed.nodes[0].x+=.000001;
 bool badmesh=false;try{(void)ice3d::p09e::read(out,changed,300);}catch(const std::runtime_error&){badmesh=true;}
 if(!badmesh)throw std::runtime_error("P09E selftest: wrong mesh accepted");
 {std::fstream f(out,std::ios::binary|std::ios::in|std::ios::out);f.seekp(48+8);char byte=0x5a;f.write(&byte,1);}
 bool corruption=false;try{(void)ice3d::p09e::read(out,m,300);}catch(const std::runtime_error&){corruption=true;}
 if(!corruption)throw std::runtime_error("P09E selftest: corrupted payload accepted");
 fs::remove(out);
 std::cout<<"P09E_IO_SELFTEST_OK bit_exact=1 wrong_mesh=reject wrong_time=reject checksum=verified\n";
 return 0;
 }catch(const std::exception&e){std::cerr<<"P09E_IO_SELFTEST_FAIL: "<<e.what()<<"\n";return 2;}}
