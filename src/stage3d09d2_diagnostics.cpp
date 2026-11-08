// Stage 3D-09D2: fine-shell and smooth-window final checkpoint diagnostics.
// Reuses the completed P09C y20 +/- EDV/VAR trajectories at xi=0 on H4/HP.
#include "qt_runner_paths.hpp"
#include <algorithm>
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
 while(std::getline(in,part,','))v.push_back(part);
 return v;}
static string read(const fs::path&p){std::ifstream in(p);if(!in)throw std::runtime_error("Missing "+p.string());return {std::istreambuf_iterator<char>(in),{}};}
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
 else if(a=="--selftest")c.selftest=true;else if(a=="--help"){std::cout<<"stage3d09d2_diagnostics [--mesh H4|HP|ALL] [--threads 4] [--root Stage3D07] --selftest\n";std::exit(0);}
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
// All P09D2 quantities are read from the committed checkpoint postprocessor output.
struct Shell {string kind;int bin=0;double r0=0,r1=0,vol=0,p4=0,p8=0,p12=0,psi=0,energy=0;long long nqp=0;};
struct Band {double edge=0,h=0,nqp=0,volume=0,p8=0;};
struct Hot {int p=0;double nelem=0,s1=0,s5=0,s10=0,n50=0,n80=0,n95=0,top=0,r=0,sigma=0;};
struct ResultCase {RunCase src;std::vector<Shell>shell;std::vector<Band>band;std::vector<Hot>hot;};
static std::vector<std::vector<string>> read_rows(const fs::path&p,size_t fields,size_t rows){
 std::ifstream in(p);if(!in)throw std::runtime_error("Missing "+p.string());
 string line; if(!std::getline(in,line))throw std::runtime_error("Missing header "+p.string());
 std::vector<std::vector<string>>out;
 while(std::getline(in,line))if(!line.empty()){
  auto v=csv(line);if(v.size()!=fields)throw std::runtime_error("Wrong columns in "+p.string());out.push_back(v);
 }
 if(out.size()!=rows)throw std::runtime_error("Wrong number of rows in "+p.string());
 return out;
}
static void load(ResultCase&x){
 const auto base=x.src.mech;
 const auto a=read_rows(base/"P09D2_RADIAL_FINAL.csv",11,22);
 for(const auto&v:a){Shell t;t.kind=v[0];t.bin=std::stoi(v[1]);t.r0=std::stod(v[2]);t.r1=std::stod(v[3]);
  t.vol=std::stod(v[4]);t.p4=std::stod(v[5]);t.p8=std::stod(v[6]);t.p12=std::stod(v[7]);
  t.psi=std::stod(v[8]);t.energy=std::stod(v[9]);t.nqp=std::stoll(v[10]);x.shell.push_back(t);}
 for(int k=0;k<2;++k)for(int b=0;b<11;++b){const auto&t=x.shell[11*k+b];
  if(t.kind!=(k?"smooth":"hard")||t.bin!=b||t.r0>=t.r1)
   throw std::runtime_error("P09D2 malformed radial bins: "+base.string());}
 const auto bands=read_rows(base/"P09D2_INTERFACES_FINAL.csv",5,5);
 for(const auto&v:bands){Band b;b.edge=std::stod(v[0]);b.h=std::stod(v[1]);b.nqp=std::stod(v[2]);b.volume=std::stod(v[3]);b.p8=std::stod(v[4]);x.band.push_back(b);}
 const auto hotspots=read_rows(base/"P09D2_HOT_FINAL.csv",11,2);
 for(const auto&v:hotspots){Hot h;h.p=std::stoi(v[0]);h.nelem=std::stod(v[1]);h.s1=std::stod(v[2]);h.s5=std::stod(v[3]);h.s10=std::stod(v[4]);
 h.n50=std::stod(v[5]);h.n80=std::stod(v[6]);h.n95=std::stod(v[7]);h.top=std::stod(v[8]);h.r=std::stod(v[9]);h.sigma=std::stod(v[10]);x.hot.push_back(h);}
 if(x.hot[0].p!=8||x.hot[1].p!=12)throw std::runtime_error("P09D2 peak powers not 8/12");
 for(int k=0;k<2;++k){double a=0,b=0;for(int j=0;j<11;++j){a+=x.shell[k*11+j].p8;b+=x.shell[k*11+j].vol;}
 if(!(a>0&&b>0)||!std::isfinite(a)||!std::isfinite(b))throw std::runtime_error("P09D2 zero moments");}
}
static void execute(const Cfg&c,const fs::path&self){
 const fs::path exe=self.parent_path()/
#ifdef _WIN32
 "stage3d06_spatial.exe";
#else
 "stage3d06_spatial";
#endif
 if(!fs::is_regular_file(exe))throw std::runtime_error("Missing solver "+exe.string());
 std::vector<ResultCase>run;
 for(const auto&mesh:(c.mesh=="ALL"?std::vector<string>{"H4","HP"}:std::vector<string>{c.mesh}))
  for(const auto&sign:{string("plus"),string("minus")}){ResultCase x;x.src=prepare(c,mesh,sign);run.push_back(x);}
 for(auto&x:run){const auto&v=x.src;
  std::cout<<"P09D2_FINAL_DIAGNOSTICS: "<<v.mesh<<" "<<v.sign<<std::endl;
  std::vector<string>args={"--mesh",v.meshPath.string(),"--temp-dir",v.therm.string(),"--out",v.mech.parent_path().string(),
   "--law","EDV","--modulus","VAR","--times",time_list(c.dt,c.tend),"--quad",std::to_string(c.quad),
   "--functionals","triple","--peak-p","8","--p09d2-diagnostic","--postprocess-only",
   "--optimization","on","--parallel-assembly","on","--threads",std::to_string(c.threads)};
  if(int rc=spawn(exe,args))throw std::runtime_error("P09D2 postprocessing failed: "+v.mesh+" "+v.sign+" exit="+std::to_string(rc));
  load(x);
 }
 const auto out=c.root/"LOCAL_RUNS"/"DIAG_STAGE09"/"P09D2";fs::create_directories(out);
 fs::remove(out/"P09D2_STATUS.txt");
 std::ofstream radial(out/"P09D2_RADIAL_DERIVATIVES.csv"),faces(out/"P09D2_INTERFACE_AUDIT.csv"),hot(out/"P09D2_HOTSPOTS.csv");
 std::ostringstream status;
 radial<<std::setprecision(17);faces<<std::setprecision(17);hot<<std::setprecision(17);
 radial<<"mesh,kind,bin,inner_mm,outer_mm,plus_raw_p8_m3,minus_raw_p8_m3,D_raw_p8_per_m,D_raw_p4_per_m,D_raw_p12_per_m,D_volume_per_m,plus_nqp,minus_nqp,plus_volume_m3,minus_volume_m3\n";
 faces<<"mesh,edge_mm,halfwidth_mm,plus_nqp,minus_nqp,plus_band_volume_m3,minus_band_volume_m3,plus_raw_p8_m3,minus_raw_p8_m3,D_band_raw_p8_per_m\n";
 hot<<"mesh,sign,power,active_elements,top1pct_share,top5pct_share,top10pct_share,n_for_50pct,n_for_80pct,n_for_95pct,top_element_share,top_element_rpeak_mm,top_element_sigma_positive_over_ref\n";
 status<<"status=SUCCESS\nstage=P09D2\nmesh="<<c.mesh<<"\nxi=0\ntime_s="<<c.tend<<"\ndelta_um="<<c.deltaUm<<"\nquad="<<c.quad<<"\n";
 for(size_t i=0;i<run.size();i+=2){const auto&p=run[i],&m=run[i+1];
  if(p.src.sign!="plus"||m.src.sign!="minus"||p.src.mesh!=m.src.mesh)throw std::runtime_error("P09D2 invalid paired cases");
  const double denom=2*c.deltaUm*1e-6;
  for(size_t k=0;k<p.shell.size();++k){const auto&a=p.shell[k],&b=m.shell[k];
   if(a.kind!=b.kind||a.bin!=b.bin||a.r0!=b.r0||a.r1!=b.r1)throw std::runtime_error("P09D2 mismatched shell layout");
   radial<<p.src.mesh<<","<<a.kind<<","<<a.bin<<","<<a.r0<<","<<a.r1<<","<<a.p8<<","<<b.p8<<","<<(a.p8-b.p8)/denom<<","<<(a.p4-b.p4)/denom<<","<<(a.p12-b.p12)/denom<<","<<(a.vol-b.vol)/denom<<","<<a.nqp<<","<<b.nqp<<","<<a.vol<<","<<b.vol<<"\n";
  }
  for(size_t k=0;k<p.band.size();++k){const auto&a=p.band[k],&b=m.band[k];
   if(a.edge!=b.edge||a.h!=b.h)throw std::runtime_error("P09D2 mismatched edge layout");
   faces<<p.src.mesh<<","<<a.edge<<","<<a.h<<","<<a.nqp<<","<<b.nqp<<","<<a.volume<<","<<b.volume<<","<<a.p8<<","<<b.p8<<","<<(a.p8-b.p8)/denom<<"\n";
  }
  for(const auto&x:{&p,&m})for(const auto&a:x->hot)
   hot<<x->src.mesh<<","<<x->src.sign<<","<<a.p<<","<<a.nelem<<","<<a.s1<<","<<a.s5<<","<<a.s10<<","<<a.n50<<","<<a.n80<<","<<a.n95<<","<<a.top<<","<<a.r<<","<<a.sigma<<"\n";
  double hard=0,smooth=0;
  for(size_t k=0;k<11;++k){hard+=(p.shell[k].p8-m.shell[k].p8)/denom;smooth+=(p.shell[11+k].p8-m.shell[11+k].p8)/denom;}
  if(std::abs(hard-smooth)>1e-10*std::max({std::abs(hard),std::abs(smooth),1e-20}))throw std::runtime_error("P09D2 smooth/hard derivative nonconservation");
  status<<p.src.mesh<<"_D_raw_p8_per_m="<<std::setprecision(17)<<hard<<"\n";
 }
 if(!radial||!faces||!hot)throw std::runtime_error("P09D2 cannot write summary files");
 radial.close();faces.close();hot.close();
 if(!radial||!faces||!hot)throw std::runtime_error("P09D2 cannot finalize summary files");
 std::ofstream success(out/"P09D2_STATUS.txt");success<<status.str();success.close();
 if(!success)throw std::runtime_error("P09D2 cannot write SUCCESS status");
 std::cout<<"P09D2_SUCCESS: read-only final checkpoint, "<<run.size()<<" cases; outputs in "<<out<<std::endl;
}
int main(int argc,char**argv){try{const Cfg c=parse(argc,argv);
 if(c.selftest){
  if(tag(5)!="5p000"||time_list(300,900)!="300,600,900"||path(c,"HP").filename().string().find("HP_dt300")!=0)
   throw std::runtime_error("P09D2 launcher selftest failed");
  std::cout<<"P09D2_SELFTEST_OK\n";return 0;}
 execute(c,fs::absolute(argv[0]));return 0;
}catch(const std::exception&e){std::cerr<<"P09D2_ERROR: "<<e.what()<<std::endl;return 2;}}
