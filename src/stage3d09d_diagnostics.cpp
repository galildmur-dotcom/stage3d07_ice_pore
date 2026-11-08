// Stage 3D-09D: no-FEM rerun, read-only final checkpoint stress diagnostics.
// Reuses the completed P09C y20 +/- EDV/VAR trajectories at xi=0 on H4/HP.
#include "qt_runner_paths.hpp"
#include <array>
#include <cmath>
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
#include <cerrno>
#include <cstring>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#endif
namespace fs=std::filesystem;
using std::string;
struct Cfg {fs::path root=STAGE3D06_ROOT_DIR;string mesh="ALL";int dt=300,tend=3600,quad=3,threads=4;double deltaUm=5.;bool selftest=false;};
static string tag(double n){std::ostringstream s;s<<std::fixed<<std::setprecision(3)<<n;string x=s.str();for(char&c:x)if(c=='.')c='p';return x;}
static fs::path path(const Cfg&c,const string&mesh){
 return c.root/"LOCAL_RUNS"/"SHAPE_STAGE09"/"P09C"/
 (mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.quad)+"_t"+std::to_string(c.tend)+"_GH3_p8_delta"+tag(c.deltaUm)+"um_modesy20_lawsEDV_EVAR");
}
static std::vector<string> csv(const string&s){std::istringstream in(s);string part;std::vector<string>v;
 while(std::getline(in,part,','))v.push_back(part);return v;}
static string read(const fs::path&p){std::ifstream in(p);if(!in)throw std::runtime_error("Missing "+p.string());return {std::istreambuf_iterator<char>(in),{}};}
static std::vector<double> numeric_line(const fs::path&p){std::ifstream in(p);string line,last;if(!in||!std::getline(in,line))throw std::runtime_error("Missing CSV header: "+p.string());
 while(std::getline(in,line))if(!line.empty())last=line;
 if(last.empty())throw std::runtime_error("Missing CSV data: "+p.string());std::vector<double> v;
 const auto fields=csv(last);
 for(size_t i=0;i<fields.size();++i){v.push_back((i==1||i==2)?0.0:std::stod(fields[i]));}return v;}
#ifdef _WIN32
static std::wstring quote(const std::wstring&s){std::wstring o=L"\"";size_t n=0;for(wchar_t c:s){if(c==L'\\'){++n;continue;}if(c==L'"'){o.append(2*n+1,L'\\');o+=c;n=0;continue;}o.append(n,L'\\');n=0;o+=c;}o.append(2*n,L'\\');return o+L'"';}
static int spawn(const fs::path&exe,const std::vector<string>&args){std::wstring cmd=quote(exe.wstring());for(const auto&a:args)cmd+=L" "+quote(fs::path(a).wstring());std::vector<wchar_t>buf(cmd.begin(),cmd.end());buf.push_back(0);
 STARTUPINFOW si{};si.cb=sizeof(si);PROCESS_INFORMATION pi{};
 if(!CreateProcessW(exe.c_str(),buf.data(),nullptr,nullptr,TRUE,0,nullptr,nullptr,&si,&pi))throw std::runtime_error("CreateProcessW error "+std::to_string(GetLastError()));
 CloseHandle(pi.hThread);WaitForSingleObject(pi.hProcess,INFINITE);DWORD code=1;if(!GetExitCodeProcess(pi.hProcess,&code))code=1;CloseHandle(pi.hProcess);return int(code);}
#else
static int spawn(const fs::path&exe,const std::vector<string>&args){pid_t pid=fork();if(pid<0)throw std::runtime_error("fork failed");
 if(pid==0){std::vector<string>v{exe.string()};v.insert(v.end(),args.begin(),args.end());std::vector<char*>pp;for(auto&s:v)pp.push_back(s.data());pp.push_back(nullptr);execv(exe.c_str(),pp.data());_exit(127);}
 int code=0;while(waitpid(pid,&code,0)<0){if(errno!=EINTR)throw std::runtime_error("waitpid failed");}return WIFEXITED(code)?WEXITSTATUS(code):128;}
#endif
static Cfg parse(int argc,char**argv){Cfg c;for(int i=1;i<argc;++i){string a=argv[i];auto val=[&](){if(i+1>=argc)throw std::runtime_error("Missing value for "+a);return string(argv[++i]);};
 if(a=="--root")c.root=fs::absolute(val());else if(a=="--mesh")c.mesh=val();else if(a=="--threads")c.threads=std::stoi(val());
 else if(a=="--dt")c.dt=std::stoi(val());else if(a=="--tend")c.tend=std::stoi(val());else if(a=="--quad")c.quad=std::stoi(val());else if(a=="--delta-um")c.deltaUm=std::stod(val());
 else if(a=="--selftest")c.selftest=true;else if(a=="--help"){std::cout<<"stage3d09d_diagnostics [--mesh H4|HP|ALL] [--threads 4] [--root Stage3D07] --selftest\n";std::exit(0);}
 else throw std::runtime_error("Unknown option "+a);
 }
 if(c.mesh!="H4"&&c.mesh!="HP"&&c.mesh!="ALL")throw std::runtime_error("Allowed mesh: H4|HP|ALL");
 if(c.dt<1||c.tend%c.dt||c.threads<1||c.threads>32||c.quad<3||c.quad>4||c.deltaUm<=0)throw std::runtime_error("Invalid numerical settings");
 return c;}
static string time_list(int dt,int tf){string out;for(int t=dt;t<=tf;t+=dt){if(!out.empty())out+=',';out+=std::to_string(t);}return out;}
struct RunCase {string mesh,sign;fs::path meshPath,therm,mech;
 std::array<double,15>mom{}; // first 15 numeric columns
 std::array<std::array<double,13>,8>shells{};
};
static RunCase prepare(const Cfg&c,const string&mesh,const string&sign){
 RunCase x;x.mesh=mesh;x.sign=sign;auto base=path(c,mesh);
 x.meshPath=base/"y20"/"geometry"/(mesh+"_P08_y20_"+sign+"_"+tag(c.deltaUm)+"um.msh");
 const auto sub=base/"y20"/(sign+"_"+tag(c.deltaUm)+"um")/"GH_zero";
 x.mech=sub/"EDV_VAR"/"mechanics"/"EDV_VAR";
 for(const auto&p:{x.meshPath,x.mech/"restart.bin",x.mech/"P09B_functionals_history.csv",x.mech/"P09C_CASE_GUARD.txt"}){
  // P09C_CASE_GUARD lives one level above mechanics; check separately.
  if(p.filename()=="P09C_CASE_GUARD.txt")continue;
  if(!fs::is_regular_file(p))throw std::runtime_error("Missing completed FEM source: "+p.string());
 }
 if(!fs::is_regular_file(sub/"EDV_VAR"/"P09C_CASE_GUARD.txt"))throw std::runtime_error("Missing P09C guard");
 auto source=read(sub/"P09C_THERMAL_SOURCE.txt");std::istringstream in(source);string type,dir;std::getline(in,type);std::getline(in,dir);
 if(type!="LOCAL_P09C"&&type!="P08D_THERMAL")throw std::runtime_error("Unrecognized thermal source");
 x.therm=fs::path(dir);if(!fs::is_regular_file(x.therm/("thermal_"+std::to_string(c.tend)+"s.vtu")))throw std::runtime_error("Missing terminal thermal field: "+x.therm.string());
 return x;
}
static void collect(RunCase&x){auto a=numeric_line(x.mech/"P09D_MOMENTS_FINAL.csv");if(a.size()!=15)throw std::runtime_error("P09D invalid global summary");
 for(size_t i=0;i<15;++i)x.mom[i]=a[i];
 std::ifstream in(x.mech/"P09D_RADIAL_FINAL.csv");string line;
 if(!in||!std::getline(in,line))throw std::runtime_error("P09D invalid radial summary");
 for(size_t i=0;i<8;++i){if(!std::getline(in,line))throw std::runtime_error("P09D truncated radial summary");
  auto cells=csv(line);if(cells.size()!=13)throw std::runtime_error("P09D radial column count mismatch");
  for(size_t j=0;j<13;++j){if(j==3||j==4){x.shells[i][j]=cells[j]=="nan"?0:std::stod(cells[j]);}else x.shells[i][j]=std::stod(cells[j]);}
  if(size_t(x.shells[i][0])!=i)throw std::runtime_error("P09D radial bin order mismatch");
 }
}
static void execute(const Cfg&c,const fs::path&self){
 const fs::path exe=self.parent_path()/
#ifdef _WIN32
 "stage3d06_spatial.exe";
#else
 "stage3d06_spatial";
#endif
 if(!fs::is_regular_file(exe))throw std::runtime_error("Missing solver: "+exe.string());
 std::vector<RunCase>run;
 for(const auto&mesh:(c.mesh=="ALL"?std::vector<string>{"H4","HP"}:std::vector<string>{c.mesh}))for(const auto&sign:{string("plus"),string("minus")})run.push_back(prepare(c,mesh,sign));
 for(auto&x:run){fs::path out=x.mech.parent_path();std::cout<<"P09D_FINAL_DIAGNOSTICS: "<<x.mesh<<" "<<x.sign<<std::endl;
  std::vector<string>args={"--mesh",x.meshPath.string(),"--temp-dir",x.therm.string(),"--out",out.string(),
   "--law","EDV","--modulus","VAR","--times",time_list(c.dt,c.tend),"--quad",std::to_string(c.quad),
   "--functionals","triple","--peak-p","8","--p09d-diagnostic","--postprocess-only",
   "--optimization","on","--parallel-assembly","on","--threads",std::to_string(c.threads)};
  int rc=spawn(exe,args);if(rc)throw std::runtime_error("P09D postprocess failed: "+x.mesh+" "+x.sign+" status="+std::to_string(rc));
  collect(x);
 }
 const auto output=c.root/"LOCAL_RUNS"/"DIAG_STAGE09"/"P09D";
 fs::create_directories(output);
 std::ofstream result(output/"P09D_FINAL_DERIVATIVES.csv"),radial(output/"P09D_RADIAL_DERIVATIVES.csv"), cases(output/"P09D_CASES.csv");
 result<<std::setprecision(17);radial<<std::setprecision(17);cases<<std::setprecision(17);
 cases<<"mesh,sign,xi,time_s,volume6_m3,raw_p4_m3,raw_p8_m3,raw_p12_m3,jpeak4_instant,jpeak8_instant,jpeak12_instant,raw_psi6_m3,raw_energy_J,total_nqp\n";
 for(const auto&x:run){const auto&a=x.mom;cases<<x.mesh<<","<<x.sign<<",0,"<<a[0]<<","<<a[5]<<","<<a[6]<<","<<a[7]<<","<<a[8]<<","<<a[9]<<","<<a[10]<<","<<a[11]<<","<<a[12]<<","<<a[13]<<","<<a[14]<<"\n";}
 result<<"mesh,quantity,final_plus,final_minus,D_per_m,delta_um,note\n";
 radial<<"mesh,bin,inner_mm,outer_mm,D_raw_p4_per_m,D_raw_p8_per_m,D_raw_p12_per_m,D_raw_psi6_per_m,D_raw_energy_per_m,D_volume_per_m,share_abs_Dp8\n";
 for(size_t k=0;k+1<run.size();k+=2){const auto&plus=run[k],&minus=run[k+1];if(plus.sign!="plus"||minus.sign!="minus"||plus.mesh!=minus.mesh)throw std::runtime_error("P09D case order invalid");
  double h=2*c.deltaUm*1e-6;
  for(const auto&f:std::array<std::pair<const char*,int>,5>{{{"jpeak4_instant",9},{"jpeak8_instant",10},{"jpeak12_instant",11},{"volume6_m3",5},{"raw_psi6_m3",12}}}){
   const double p=plus.mom[f.second],m=minus.mom[f.second];
   result<<plus.mesh<<","<<f.first<<","<<p<<","<<m<<","<<(p-m)/h<<","<<c.deltaUm<<",deterministic_xi0_final_time_only\n";
  }
  double sumAbs=0;for(int j=0;j<8;++j)sumAbs+=std::abs(plus.shells[j][8]-minus.shells[j][8]);
  for(int j=0;j<8;++j){const auto&a=plus.shells[j],&b=minus.shells[j];
   radial<<plus.mesh<<","<<j<<","<<a[1]<<","<<a[2]<<","<<(a[7]-b[7])/h<<","<<(a[8]-b[8])/h<<","<<(a[9]-b[9])/h<<","<<(a[10]-b[10])/h<<","<<(a[11]-b[11])/h<<","<<(a[6]-b[6])/h<<","<<(sumAbs?std::abs(a[8]-b[8])/sumAbs:0)<<"\n";
  }
 }
 if(!result||!radial||!cases)throw std::runtime_error("P09D CSV output failure");
 std::cout<<"P09D_SUCCESS: no new heat or mechanical solves; diagnostics for "<<run.size()<<" committed states\n"<<output<<std::endl;
}
int main(int argc,char**argv){try{const Cfg c=parse(argc,argv);if(c.selftest){if(tag(5)!="5p000"||time_list(300,900)!="300,600,900"||path(c,"H4").filename().string().find("H4_dt300")!=0)throw std::runtime_error("P09D selftest failed");std::cout<<"P09D_SELFTEST_OK\n";return 0;}execute(c,fs::absolute(argv[0]));return 0;}catch(const std::exception&e){std::cerr<<"P09D_ERROR: "<<e.what()<<std::endl;return 2;}}
