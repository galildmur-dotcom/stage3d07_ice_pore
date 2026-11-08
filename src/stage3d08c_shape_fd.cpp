// Stage3D08C: coupled shape-mode central differences of j6, reusing P08A physics.
// Fresh thermal + coupled EDV/VAR solves at each R+delta and R-delta; NO reuse
// of the unperturbed thermal field. All results are isolated under P08_FD.
#include "qt_runner_paths.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#else
#include <cerrno>
#include <cstring>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#endif
namespace fs=std::filesystem;
namespace {
struct Opt {
 std::string mesh="H0", delta="5,2.5", modes="tx,ty,tz";
 int dt=300,tend=3600,quad=3,
#ifdef STAGE3D08_NO_OPENMP
 threads=1;
#else
 threads=4;
#endif
 double cutoff_mm=5.; bool dry=false,clean=false;
 Opt(){
#ifdef STAGE3D08C_HARMONICS
 modes="y20,y21c,y21s,y22c,y22s";
#endif
 }
};
const std::vector<std::string> allowed_modes={"tx","ty","tz","y20","y21c","y21s","y22c","y22s"};
std::vector<std::string> modes_list(const std::string& s){
 std::istringstream in(s);std::string token;std::vector<std::string> modes;
 while(std::getline(in,token,',')){
  if(std::find(allowed_modes.begin(),allowed_modes.end(),token)==allowed_modes.end())throw std::runtime_error("Unsupported mode: "+token);
  if(std::find(modes.begin(),modes.end(),token)!=modes.end())throw std::runtime_error("Duplicate mode: "+token);
  modes.push_back(token);
 }
 if(modes.empty())throw std::runtime_error("Empty --modes");
 return modes;
}
Opt parse(int argc,char**argv){Opt o;
 for(int i=1;i<argc;++i){std::string k=argv[i];auto val=[&](){if(i+1>=argc)throw std::runtime_error("Missing argument for "+k);return std::string(argv[++i]);};
  if(k=="--mesh")o.mesh=val();else if(k=="--delta-um")o.delta=val();else if(k=="--modes")o.modes=val();
  else if(k=="--mode")o.modes=val();else if(k=="--dt")o.dt=std::stoi(val());
  else if(k=="--tend")o.tend=std::stoi(val());else if(k=="--quad")o.quad=std::stoi(val());
  else if(k=="--threads")o.threads=std::stoi(val());else if(k=="--cutoff-mm")o.cutoff_mm=std::stod(val());
  else if(k=="--dry-run")o.dry=true;else if(k=="--clean")o.clean=true;
  else if(k=="--help"){
   std::cout<<"P08C shape finite differences: --mesh H0 --modes tx,ty,tz|y20,y21c,y21s,y22c,y22s --delta-um 5,2.5 --dt 300 --tend 3600 --quad 3 --threads 4 [--cutoff-mm 5] [--dry-run] [--clean]\n";
   std::exit(0);
  }else throw std::runtime_error("Unknown argument "+k);
 }
 if(o.mesh!="H0"&&o.mesh!="H1"&&o.mesh!="H2"&&o.mesh!="H3"&&o.mesh!="H4")throw std::runtime_error("Unknown mesh");
 if(o.dt<=0||o.tend<=0||o.tend%o.dt||o.threads<1||o.threads>32||(o.quad!=3&&o.quad!=4))throw std::runtime_error("Invalid dt/tend/threads/quad");
 if(!std::isfinite(o.cutoff_mm)||o.cutoff_mm<=3.||o.cutoff_mm>=5.5)throw std::runtime_error("cutoff must be >3 and <5.5 mm");
 if(o.dry&&o.clean)throw std::runtime_error("--dry-run and --clean cannot be combined");
 modes_list(o.modes);return o;
}
std::vector<double> deltas(const std::string& d){std::istringstream s(d);std::string x;std::vector<double>out;
 while(std::getline(s,x,',')){size_t p=0;double um=std::stod(x,&p);if(p!=x.size()||!std::isfinite(um)||um<=0||um>20)throw std::runtime_error("delta must be (0,20] um");out.push_back(um);}
 if(out.empty())throw std::runtime_error("no delta");
 return out;
}
std::string tag(double um){std::ostringstream s;s<<std::fixed<<std::setprecision(3)<<um;std::string v=s.str();for(char&c:v)if(c=='.')c='p';return v;}
std::string times_csv(int dt,int tend){std::string s;for(int t=dt;t<=tend;t+=dt){if(!s.empty())s+=',';s+=std::to_string(t);}return s;}
fs::path sibling(const fs::path& p,const std::string& exe){
#ifdef _WIN32
return p.parent_path()/(exe+".exe");
#else
return p.parent_path()/exe;
#endif
}
#ifdef _WIN32
std::wstring quote(const std::wstring&s){std::wstring q=L"\"";size_t slash=0;
 for(wchar_t c:s){if(c==L'\\'){++slash;continue;}if(c==L'"'){q.append(2*slash+1,L'\\');q+=c;slash=0;continue;}
 q.append(slash,L'\\');slash=0;q+=c;}q.append(2*slash,L'\\');return q+L'"';}
int process(const fs::path&exe,const std::vector<fs::path>&args){std::wstring cmd=quote(exe.wstring());for(const auto&a:args)cmd+=L" "+quote(a.wstring());
 std::vector<wchar_t>b(cmd.begin(),cmd.end());b.push_back(0);STARTUPINFOW si{};si.cb=sizeof(si);PROCESS_INFORMATION pi{};
 if(!CreateProcessW(exe.c_str(),b.data(),nullptr,nullptr,TRUE,0,nullptr,nullptr,&si,&pi))throw std::runtime_error("CreateProcessW code "+std::to_string(GetLastError()));
 CloseHandle(pi.hThread);WaitForSingleObject(pi.hProcess,INFINITE);DWORD code=1;if(!GetExitCodeProcess(pi.hProcess,&code))code=1;CloseHandle(pi.hProcess);return static_cast<int>(code);}
#else
int process(const fs::path&exe,const std::vector<fs::path>&args){pid_t child=fork();if(child<0)throw std::runtime_error("fork failed");
 if(child==0){std::vector<std::string>v{exe.string()};for(const auto&a:args)v.push_back(a.string());std::vector<char*>ap;for(auto&x:v)ap.push_back(x.data());ap.push_back(nullptr);
 execv(exe.c_str(),ap.data());std::cerr<<"execv "<<exe<<" failed: "<<strerror(errno)<<'\n';_exit(127);}int st=0;
 while(waitpid(child,&st,0)<0){if(errno==EINTR)continue;throw std::runtime_error("waitpid failed");}return WIFEXITED(st)?WEXITSTATUS(st):128;}
#endif
void run(const fs::path&exe,std::vector<fs::path>args){std::cout<<"[RUN] "<<exe.filename().string()<<std::endl;
 if(int x=process(exe,args))throw std::runtime_error("Process "+exe.filename().string()+" failed with code "+std::to_string(x));}
uint64_t hash_file(const fs::path&path){std::ifstream f(path,std::ios::binary);if(!f)throw std::runtime_error("Cannot hash "+path.string());uint64_t h=14695981039346656037ull;char buf[8192];
 while(f.read(buf,sizeof buf)||f.gcount()) {
  for(std::streamsize i=0;i<f.gcount();++i){h^=static_cast<unsigned char>(buf[i]);h*=1099511628211ull;}
 }
 return h;}
bool complete_thermal(const fs::path&dir,int dt,int tend){if(!fs::is_regular_file(dir/"summary.csv"))return false;
 for(int i=dt;i<=tend;i+=dt) {
  if(!fs::is_regular_file(dir/("thermal_"+std::to_string(i)+"s.vtu")))return false;
 }
 return true;}
struct History{double j=0,end=0;int count=0;};
History history(const fs::path&path,int dt,int tend){std::ifstream f(path);if(!f)throw std::runtime_error("missing "+path.string());
 std::string line;if(!std::getline(f,line)||line.find("Psi6")==std::string::npos)throw std::runtime_error("unexpected time_series header: "+path.string());
 History v;double previous=7.5e-7;while(std::getline(f,line)){if(line.empty())continue;std::istringstream in(line);std::string token;std::vector<double>x;
 while(std::getline(in,token,',')) x.push_back(std::stod(token));
 if(x.size()<8)throw std::runtime_error("truncated time_series: "+path.string());
 if(std::fabs(x[0]-(v.count+1)*dt)>1e-8||!std::isfinite(x[2]))throw std::runtime_error("time series mismatch");
 v.j+=(previous+x[2])*0.5*dt/tend;previous=x[2];v.end=x[2];++v.count;}
 if(v.count!=tend/dt)throw std::runtime_error("incomplete time series");
 return v;
}
void guard_input(const fs::path&out,const fs::path&mesh,const std::string&settings){const fs::path token=out/"P08_SOURCE_GUARD.txt";
 std::string signature="mesh_hash="+std::to_string(hash_file(mesh))+"\n"+settings;
 if(fs::exists(token)){std::ifstream f(token);std::string old((std::istreambuf_iterator<char>(f)),{});
 if(old!=signature)throw std::runtime_error("Existing output from different mesh/settings; use --clean on P08 only");}
 else{if(fs::exists(out/"thermal")||fs::exists(out/"mechanics"))throw std::runtime_error("Results exist without P08 guard; refusing unsafe resume");
 fs::create_directories(out);std::ofstream f(token);f<<signature;}
}
}
int main(int argc,char**argv){try{
 const Opt o=parse(argc,argv);const auto dd=deltas(o.delta);const auto mm=modes_list(o.modes);
 const fs::path root(STAGE3D06_ROOT_DIR),mesh=root/"meshes"/(o.mesh+".msh");
 const fs::path self=fs::absolute(fs::path(argv[0]));
 const auto geometry=sibling(self,"stage3d08_geometry"),heat=sibling(self,"stage3d02_thermal"),mechanics=sibling(self,"stage3d06_spatial");
 const auto base=root/"LOCAL_RUNS"/"SHAPE_STAGE08"/"P08C"/(o.mesh+"_dt"+std::to_string(o.dt)+"_q"+std::to_string(o.quad)+"_t"+std::to_string(o.tend)+"_EDV_VAR_XI0_cutoff"+tag(o.cutoff_mm)+"mm");
 for(const auto&p:{mesh,geometry,heat,mechanics})if(!fs::is_regular_file(p))throw std::runtime_error("Missing input/executable "+p.string());
 std::cout<<"P08C: "<<o.mesh<<" dt="<<o.dt<<"s, modes="<<o.modes<<", delta="<<o.delta<<" um; EDV/VAR xi=0\n";
 if(o.dry){std::cout<<"DRY_RUN_OK; no files changed\n";return 0;}
 if(o.clean){for(const auto&mode:mm){const fs::path sub=base/mode; if(sub.parent_path()!=base||!fs::exists(sub))continue;
   if(!fs::is_regular_file(sub/"P08C_MODE_GUARD.txt"))throw std::runtime_error("Refusing cleanup without P08C_MODE_GUARD.txt: "+sub.string());
   fs::remove_all(sub);}}
 fs::create_directories(base);
 const auto status=base/(mm.size()==3&&o.modes=="tx,ty,tz"?"P08C_TRANSLATIONS_STATUS.txt":mm.size()==5&&o.modes=="y20,y21c,y21s,y22c,y22s"?"P08C_HARMONICS_STATUS.txt":"P08C_CUSTOM_STATUS.txt");
 {std::ofstream st(status,std::ios::trunc);st<<"status=RUNNING\nmesh="<<o.mesh<<"\nmodes="<<o.modes<<"\n";}
 for(const std::string& mode:mm){
  const auto out=base/mode,generated=out/"geometry";
  fs::create_directories(out);
  const std::string mode_signature="mode="+mode+"\nmesh="+o.mesh+"\ndt="+std::to_string(o.dt)+"\ntend="+std::to_string(o.tend)+"\nquad="+std::to_string(o.quad)+"\ndeltas="+o.delta+"\ncutoff="+tag(o.cutoff_mm)+"\n";
  const fs::path mode_guard=out/"P08C_MODE_GUARD.txt";
  if(fs::is_regular_file(mode_guard)){
   std::ifstream f(mode_guard);std::string s((std::istreambuf_iterator<char>(f)),{});
   if(s!=mode_signature)throw std::runtime_error("P08C mode previously run with other settings: "+out.string());
  }else{
   if(fs::exists(out/"P08C_MODE_FD.csv")||fs::exists(out/"thermal"))throw std::runtime_error("Unsafe output directory without mode guard");
   std::ofstream f(mode_guard);f<<mode_signature;
  }
  std::cout<<"[MODE] "<<mode<<"\n";
  run(geometry,{"--mesh",mesh,"--out",generated,"--mode",mode,"--delta-um",o.delta,"--cutoff-mm",std::to_string(o.cutoff_mm),"--quad",std::to_string(o.quad)});
  std::ofstream table(out/"P08C_MODE_FD.csv",std::ios::trunc);
  table<<std::setprecision(17)<<"mode,mesh,dt_s,tend_s,quad,delta_um,j6_plus,j6_minus,D_j6_per_m,normalized_by_j6_over_R,Phi6_final_plus,Phi6_final_minus,steps_verified\n";
  for(double um:dd){History h[2];for(int j=0;j<2;++j){const bool plus=j==0;const std::string sign=plus?"plus":"minus";
   const auto gmesh=generated/(o.mesh+"_P08_"+mode+"_"+sign+"_"+tag(um)+"um.msh");
   const auto sub=out/(mode+"_"+sign+"_"+tag(um)+"um"),td=sub/"thermal",md=sub/"mechanics";
   const std::string settings="mode="+mode+"\nsign="+sign+"\ndelta_um="+tag(um)+"\ndt="+std::to_string(o.dt)+"\ntend="+std::to_string(o.tend)+"\nquad="+std::to_string(o.quad)+"\ncutoff_mm="+tag(o.cutoff_mm)+"\nxi=0\nlaw=EDV\nmodulus=VAR\n";
   guard_input(sub,gmesh,settings);
   if(!complete_thermal(td,o.dt,o.tend))run(heat,{"--mesh",gmesh,"--out",td,"--dt",std::to_string(o.dt),"--tend",std::to_string(o.tend),"--xi","0","--every-step"});
   if(!complete_thermal(td,o.dt,o.tend))throw std::runtime_error("Thermal history incomplete: "+td.string());
   auto ts=md/"EDV_VAR"/"time_series.csv";bool done=false;
   try{h[j]=history(ts,o.dt,o.tend);done=fs::is_regular_file(md/"EDV_VAR"/"restart.bin");}catch(const std::exception&){done=false;}
   if(!done){run(mechanics,{"--mesh",gmesh,"--temp-dir",td,"--out",md,"--law","EDV","--modulus","VAR",
    "--times",times_csv(o.dt,o.tend),"--quad",std::to_string(o.quad),"--cg-tol","2e-8","--preconditioner","jacobi",
    "--optimization","on","--spmv","projected","--parallel-assembly","on","--threads",std::to_string(o.threads),"--resume","--final-vtu-only"});
    h[j]=history(ts,o.dt,o.tend);
    if(!fs::is_regular_file(md/"EDV_VAR"/"restart.bin"))throw std::runtime_error("Missing final mechanical checkpoint: "+md.string());
   }
   std::cout<<"[CHECK] "<<mode<<" "<<sign<<" "<<um<<"um j6="<<std::setprecision(16)<<h[j].j<<std::endl;
  }
   const double D=(h[0].j-h[1].j)/(2*um*1e-6),avg=.5*(h[0].j+h[1].j);
   table<<mode<<','<<o.mesh<<','<<o.dt<<','<<o.tend<<','<<o.quad<<','<<um<<','<<h[0].j<<','<<h[1].j<<','<<D<<','<<(.001*D/avg)<<','<<h[0].end<<','<<h[1].end<<','<<h[0].count<<'\n'<<std::flush;
  }
  {std::ofstream st(out/"P08C_MODE_STATUS.txt",std::ios::trunc);st<<"status=SUCCESS\nmode="<<mode<<"\nmesh="<<o.mesh<<"\ndt="<<o.dt<<"\ntend="<<o.tend<<"\n";}
 }
 {std::ofstream st(status,std::ios::trunc);st<<"status=SUCCESS\nmesh="<<o.mesh<<"\nmodes="<<o.modes<<"\ndt="<<o.dt<<"\ntend="<<o.tend<<"\n";}
 std::cout<<"P08C_OK: "<<base<<std::endl;return 0;
 }catch(const std::exception&e){std::cerr<<"P08C_ERROR: "<<e.what()<<std::endl;return 2;}
}
