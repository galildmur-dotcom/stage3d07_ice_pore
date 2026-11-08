// Stage3D09D3: checkpoint-only paired Gaussian-quadrature finite differences.
// Does NOT advance the thermal/mechanical solution or change the EDV state.
#include "qt_runner_paths.hpp"
#include "p09d3_pair.hpp"
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#endif
namespace fs=std::filesystem;
using std::string;
using ice3d::p09d3::Paired;
struct Config{fs::path root=STAGE3D06_ROOT_DIR;string mesh="ALL";int dt=300,tf=3600,quad=3,threads=4;double delta=5.;bool selftest=false;};
static string tag(double n){std::ostringstream s;s<<std::fixed<<std::setprecision(3)<<n;string x=s.str();for(char&c:x)if(c=='.')c='p';return x;}
static fs::path campaign(const Config&c,const string&mesh){return c.root/"LOCAL_RUNS"/"SHAPE_STAGE09"/"P09C"/
 (mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.quad)+"_t"+std::to_string(c.tf)+"_GH3_p8_delta"+tag(c.delta)+"um_modesy20_lawsEDV_EVAR");}
static string times(const Config&c){string out;for(int t=c.dt;t<=c.tf;t+=c.dt){if(!out.empty())out+=",";out+=std::to_string(t);}return out;}
#ifdef _WIN32
static std::wstring quote(const std::wstring&s){std::wstring o=L"\"";size_t n=0;for(wchar_t c:s){if(c==L'\\'){++n;continue;}if(c==L'"'){o.append(2*n+1,L'\\');o+=c;n=0;continue;}o.append(n,L'\\');n=0;o+=c;}o.append(2*n,L'\\');return o+L"\"";}
static int spawn(const fs::path&exe,const std::vector<string>&args){std::wstring cmd=quote(exe.wstring());for(const auto&a:args)cmd+=L" "+quote(fs::path(a).wstring());std::vector<wchar_t>buf(cmd.begin(),cmd.end());buf.push_back(0);
 STARTUPINFOW si{};si.cb=sizeof(si);PROCESS_INFORMATION pi{};
 if(!CreateProcessW(exe.c_str(),buf.data(),nullptr,nullptr,TRUE,0,nullptr,nullptr,&si,&pi))throw std::runtime_error("CreateProcessW error "+std::to_string(GetLastError()));
 CloseHandle(pi.hThread);WaitForSingleObject(pi.hProcess,INFINITE);DWORD code=1;if(!GetExitCodeProcess(pi.hProcess,&code))code=1;CloseHandle(pi.hProcess);return int(code);}
#else
static int spawn(const fs::path&exe,const std::vector<string>&args){pid_t pid=fork();if(pid<0)throw std::runtime_error("fork failed");
 if(pid==0){std::vector<string>v{exe.string()};v.insert(v.end(),args.begin(),args.end());std::vector<char*>pp;for(auto&s:v)pp.push_back(s.data());pp.push_back(nullptr);execv(exe.c_str(),pp.data());_exit(127);}
 int code=0;while(waitpid(pid,&code,0)<0){if(errno!=EINTR)throw std::runtime_error("waitpid failed");}return WIFEXITED(code)?WEXITSTATUS(code):128;}
#endif
static Config parse(int argc,char**argv){Config c;for(int i=1;i<argc;++i){string a=argv[i];auto val=[&](){if(i+1>=argc)throw std::runtime_error("Missing value for "+a);return string(argv[++i]);};
 if(a=="--root")c.root=fs::absolute(val());else if(a=="--mesh")c.mesh=val();else if(a=="--threads")c.threads=std::stoi(val());
 else if(a=="--dt")c.dt=std::stoi(val());else if(a=="--tend")c.tf=std::stoi(val());else if(a=="--quad")c.quad=std::stoi(val());else if(a=="--delta-um")c.delta=std::stod(val());
 else if(a=="--selftest")c.selftest=true;else if(a=="--help"){std::cout<<"stage3d09d3_diagnostics --mesh ALL|H4|HP --threads 4 [--selftest]\n";std::exit(0);}
 else throw std::runtime_error("Unknown option "+a);
 }
 if(c.mesh!="H4"&&c.mesh!="HP"&&c.mesh!="ALL")throw std::runtime_error("mesh must be H4|HP|ALL");
 if(c.dt<1||c.tf%c.dt||c.threads<1||c.threads>32||c.quad!=3||!(c.delta>0))throw std::runtime_error("Invalid numerical options");return c;}
struct Case {fs::path mesh,temp,mechanics;};
static Case locate(const Config&c,const string&mesh,const string&sign){
 const auto base=campaign(c,mesh);Case x;
 x.mesh=base/"y20"/"geometry"/(mesh+"_P08_y20_"+sign+"_"+tag(c.delta)+"um.msh");
 const auto sub=base/"y20"/(sign+"_"+tag(c.delta)+"um")/"GH_zero";
 x.mechanics=sub/"EDV_VAR"/"mechanics"/"EDV_VAR";
 if(!fs::is_regular_file(x.mesh)||!fs::is_regular_file(x.mechanics/"restart.bin")||
    !fs::is_regular_file(x.mechanics/"P09B_functionals_history.csv")||
    !fs::is_regular_file(sub/"EDV_VAR"/"P09C_CASE_GUARD.txt"))throw std::runtime_error("P09D3 missing committed mechanical/mesh case: "+x.mechanics.string());
 std::ifstream f(sub/"P09C_THERMAL_SOURCE.txt");string type,folder;std::getline(f,type);std::getline(f,folder);
 if(type!="LOCAL_P09C"&&type!="P08D_THERMAL")throw std::runtime_error("P09D3 bad thermal source: "+sub.string());
 x.temp=fs::path(folder);
 if(!fs::is_regular_file(x.temp/("thermal_"+std::to_string(c.tf)+"s.vtu")))throw std::runtime_error("P09D3 missing terminal temperature: "+x.temp.string());
 return x;
}
static void emit_row(std::ofstream&f,const string&mesh,const string&zone,int bin,double a,double b,const ice3d::p09d3::Moment&m,double d){
 const auto&v=m.p8;
 f<<mesh<<","<<zone<<","<<bin<<","<<a<<","<<b<<","<<m.nqp<<","<<v.field<<","<<v.geom<<","<<v.full<<","<<((v.plus-v.minus)/(2*d))<<",";
 f<<m.p4.field<<","<<m.p4.geom<<","<<m.p4.full<<","<<m.p12.field<<","<<m.p12.geom<<","<<m.p12.full<<",";
 f<<v.plus<<","<<v.minus<<","<<m.volume_plus<<","<<m.volume_minus<<","<<(m.volume_plus-m.volume_minus)/(2*d)<<"\n";
}
static void execute(const Config&c,const fs::path&self){
 const fs::path solver=self.parent_path()/
#ifdef _WIN32
 "stage3d06_spatial.exe";
#else
 "stage3d06_spatial";
#endif
 if(!fs::is_regular_file(solver))throw std::runtime_error("Missing stage3d06_spatial alongside diagnostic program");
 const fs::path out=c.root/"LOCAL_RUNS"/"DIAG_STAGE09"/"P09D3";fs::create_directories(out);
 fs::remove(out/"P09D3_STATUS.txt");
 std::ofstream components(out/"P09D3_COMPONENTS.csv");std::ofstream totals(out/"P09D3_TOTALS.csv");
 if(!components||!totals)throw std::runtime_error("Cannot create P09D3 output files");
 components<<std::setprecision(17);totals<<std::setprecision(17);
 components<<"mesh,region,bin,inner_mm,outer_mm,nqp,D_field_p8_per_m,D_geometry_p8_per_m,D_full_p8_per_m,D_direct_p8_per_m,D_field_p4_per_m,D_geometry_p4_per_m,D_full_p4_per_m,D_field_p12_per_m,D_geometry_p12_per_m,D_full_p12_per_m,plus_raw_p8_m3,minus_raw_p8_m3,plus_volume_m3,minus_volume_m3,D_volume_per_m\n";
 totals<<"mesh,nodes,tets,qpoints_per_tet,B6_tets,B6_qpoints,topology_hash,raw_p8_plus_m3,raw_p8_minus_m3,D_field_p8_per_m,D_geometry_p8_per_m,D_full_p8_per_m,D_direct_p8_per_m,D_field_over_abs_sum,D_geometry_over_abs_sum,relative_identity_error,D_full_p4_per_m,D_full_p12_per_m,D_volume_per_m\n";
 std::ostringstream status;status<<"status=SUCCESS\nstage=P09D3\nmesh="<<c.mesh<<"\nxi=0\ntime_s="<<c.tf<<"\ndelta_um="<<c.delta<<"\nquad="<<c.quad<<"\n";
 for(const auto&mesh:c.mesh=="ALL"?std::vector<string>{"H4","HP"}:std::vector<string>{c.mesh}){
  std::array<fs::path,2> data;
  for(int i=0;i<2;++i){const string sign=i==0?"plus":"minus";const auto x=locate(c,mesh,sign);
   std::cout<<"P09D3 checkpoint postprocessing: "<<mesh<<" "<<sign<<std::endl;
   const std::vector<string>args={"--mesh",x.mesh.string(),"--temp-dir",x.temp.string(),"--out",x.mechanics.parent_path().string(),
    "--law","EDV","--modulus","VAR","--times",times(c),"--quad",std::to_string(c.quad),"--functionals","triple","--peak-p","8",
    "--p09d3-diagnostic","--postprocess-only","--optimization","on","--parallel-assembly","on","--threads",std::to_string(c.threads)};
   if(const int rc=spawn(solver,args))throw std::runtime_error("P09D3 solver postprocessing failure "+mesh+" "+sign+" exit "+std::to_string(rc));
   data[i]=x.mechanics/"P09D3_QPOINTS_FINAL.bin";
   if(!fs::is_regular_file(data[i]))throw std::runtime_error("P09D3 binary output missing");
  }
  const auto r=ice3d::p09d3::pair_files(data[0],data[1],c.delta*1e-6);
  const double denom=2*c.delta*1e-6;const auto&v=r.all.p8;
  const double direct=(v.plus-v.minus)/denom;
  const double err=ice3d::p09d3::rel_error(v.full,direct);
  const double totalmag=std::abs(v.field)+std::abs(v.geom);
  for(std::size_t i=0;i<r.bins.size();++i)emit_row(components,mesh,"shell",int(i),ice3d::p09d2::edges_mm[i],ice3d::p09d2::edges_mm[i+1],r.bins[i],c.delta*1e-6);
  emit_row(components,mesh,"ALL",-1,1.,6.,r.all,c.delta*1e-6);
  totals<<mesh<<","<<r.h.nodes<<","<<r.h.elems<<","<<r.h.nq<<","<<r.h.active<<","<<r.all.nqp<<","<<r.h.connectivity<<","<<v.plus<<","<<v.minus<<","<<v.field<<","<<v.geom<<","<<v.full<<","<<direct<<","<<std::abs(v.field)/std::max(totalmag,1e-300)<<","<<std::abs(v.geom)/std::max(totalmag,1e-300)<<","<<err<<","<<r.all.p4.full<<","<<r.all.p12.full<<","<<(r.all.volume_plus-r.all.volume_minus)/denom<<"\n";
  status<<mesh<<"_D_raw_p8_per_m="<<std::setprecision(17)<<v.full<<"\n";
  status<<mesh<<"_topology_hash="<<r.h.connectivity<<"\n";
  std::cout<<"P09D3_"<<mesh<<"_OK D(field)="<<v.field<<" D(geom)="<<v.geom<<" D(total)="<<v.full<<"\n";
 }
 components.close();totals.close();if(!components||!totals)throw std::runtime_error("P09D3 incomplete CSV outputs");
 std::ofstream successful(out/"P09D3_STATUS.txt");successful<<status.str();successful.close();if(!successful)throw std::runtime_error("Cannot finalize P09D3 status");
 std::cout<<"P09D3_SUCCESS: "+out.string()<<std::endl;
}
int main(int argc,char**argv){try{auto c=parse(argc,argv);if(c.selftest){ice3d::p09d3::selftest();
 if(tag(5)!="5p000"||times(c).find("300,600")!=0||campaign(c,"HP").filename().string().find("HP_dt300")!=0)throw std::runtime_error("P09D3 launcher test failure");
 std::cout<<"P09D3_SELFTEST_OK\n";return 0;}
 execute(c,fs::absolute(argv[0]));return 0;
}catch(const std::exception&e){std::cerr<<"P09D3_ERROR: "<<e.what()<<"\n";return 2;}}
