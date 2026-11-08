// Stage 3D-09C: finite-difference shape sensitivities of three time-integrated
// observables: j6, j_peak(p), and j_en, with GH3 stochastic moments.
// Reuses VERIFIED P08D geometry/temperature histories, never old mechanical
// histories which do not contain the two new spatial-temporal functionals.
#include "qt_runner_paths.hpp"
#include "stage3d09b_functionals.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
# ifndef NOMINMAX
#  define NOMINMAX
# endif
# include <windows.h>
#else
# include <cerrno>
# include <cstring>
# include <sys/types.h>
# include <sys/wait.h>
# include <unistd.h>
#endif
#ifdef CONST
# undef CONST
#endif
namespace fs=std::filesystem;
namespace {
using std::string;
const std::array<double,3> XI{{-std::sqrt(3.),0.,std::sqrt(3.)}};
constexpr std::array<double,3> W{{1./6.,2./3.,1./6.}};
constexpr std::array<const char*,3> OBS{{"j6","jpeak","jen"}};
struct Config {
 string mesh="H0",modes="R,tz,y20",laws="EDV",moduli="VAR",reuse="auto";
 int dt=300,tend=3600,quad=3,peakP=8,
#ifdef STAGE3D08_NO_OPENMP
 threads=1;
#else
 threads=4;
#endif
 double deltaUm=5,cutoffMm=5;
 bool dry=false,report=false,selftest=false,geometryOnly=false;string storage="legacy";string mechanicalVtu="final";double checkpointHours=0.0;bool checkpointSpecified=false;
 fs::path root=STAGE3D06_ROOT_DIR;
};
bool is_hp_family(const string& s){return s=="HP"||s=="HP2"||s=="HP4"||s=="HP8";}
string number(double x){std::ostringstream s;s<<std::setprecision(17)<<x;return s.str();}
string tag(double x){std::ostringstream s;s<<std::fixed<<std::setprecision(3)<<x;string r=s.str();for(char&c:r)if(c=='.')c='p';return r;}
std::vector<string> split(const string&s,char delim=','){
 std::istringstream in(s);std::vector<string>out;string part;
 while(std::getline(in,part,delim))if(!part.empty())out.push_back(part);
 return out;
}
std::vector<string> opts(const string&s,const string&what){
 std::vector<string>v=(s=="ALL"?(what=="laws"?std::vector<string>{"E","ED","EDV"}:std::vector<string>{"CONST","VAR"}):split(s));
 if(v.empty())throw std::runtime_error("Empty "+what);
 for(const auto&x:v){
  if(std::count(v.begin(),v.end(),x)!=1)throw std::runtime_error("Repeated "+what+": "+x);
  if(what=="laws"?x!="E"&&x!="ED"&&x!="EDV":x!="CONST"&&x!="VAR")throw std::runtime_error("Invalid "+what+": "+x);
 }
 return v;
}
std::vector<string> modes(const string&s){auto v=split(s);if(v.empty())throw std::runtime_error("Empty modes");
 for(const auto&m:v){if(m!="R"&&m!="tz"&&m!="y20")throw std::runtime_error("Allowed modes: R,tz,y20");
  if(std::count(v.begin(),v.end(),m)!=1)throw std::runtime_error("Repeated mode");}
 return v;
}
Config parse(int argc,char**argv){Config c;
 for(int i=1;i<argc;++i){const string f=argv[i];auto val=[&](){if(i+1>=argc)throw std::runtime_error("Missing value for "+f);return string(argv[++i]);};
  if(f=="--mesh")c.mesh=val();else if(f=="--modes")c.modes=val();else if(f=="--laws")c.laws=val();else if(f=="--moduli")c.moduli=val();
  else if(f=="--dt")c.dt=std::stoi(val());else if(f=="--tend")c.tend=std::stoi(val());else if(f=="--quad")c.quad=std::stoi(val());
  else if(f=="--peak-p")c.peakP=std::stoi(val());else if(f=="--delta-um")c.deltaUm=std::stod(val());else if(f=="--cutoff-mm")c.cutoffMm=std::stod(val());
  else if(f=="--storage")c.storage=val();else if(f=="--mechanical-vtu")c.mechanicalVtu=val();
  else if(f=="--checkpoint-hours"){c.checkpointHours=std::stod(val());c.checkpointSpecified=true;}
  else if(f=="--threads")c.threads=std::stoi(val());else if(f=="--reuse-p08d")c.reuse=val();else if(f=="--root")c.root=fs::absolute(val());
  else if(f=="--selftest")c.selftest=true;else if(f=="--dry-run")c.dry=true;else if(f=="--report-only")c.report=true;else if(f=="--geometry-only")c.geometryOnly=true;
  else if(f=="--help"||f=="-h"){
   std::cout<<"Stage3D09C --mesh H0..H4|HP|HP2|HP4|HP8 --modes R,tz,y20 --laws EDV|E,ED,EDV|ALL --moduli VAR|CONST,VAR|ALL "
     "--dt 300 --tend 3600 --quad 3 --delta-um 5 --cutoff-mm 5 --peak-p 8 --threads 4 "
     "--reuse-p08d auto|off|require [--storage legacy|compact] [--mechanical-vtu none|final|all] [--checkpoint-hours 6] [--selftest|--dry-run|--geometry-only|--report-only] [--root PROJECT_ROOT]\n"
     "Compact outputs: LOCAL_RUNS/SHAPE_STAGE09/P09E; legacy: P09C. Earlier runs remain untouched.\n";
   std::exit(0);
  }else throw std::runtime_error("Unknown option "+f);
 }
 if(c.mesh!="H0"&&c.mesh!="H1"&&c.mesh!="H2"&&c.mesh!="H3"&&c.mesh!="H4"&&!is_hp_family(c.mesh))throw std::runtime_error("Unknown mesh");
 if(is_hp_family(c.mesh) && c.reuse=="require")throw std::runtime_error("HP-family meshes have no compatible P08D thermal histories; use --reuse-p08d off");
 modes(c.modes);opts(c.laws,"laws");opts(c.moduli,"moduli");
 if(c.dt<1||c.tend<1||c.tend%c.dt||c.quad<3||c.quad>4||c.threads<1||c.threads>32)throw std::runtime_error("Invalid time/quad/thread options");
 if(c.peakP!=4&&c.peakP!=8&&c.peakP!=12)throw std::runtime_error("--peak-p 4|8|12");
 if(!std::isfinite(c.deltaUm)||c.deltaUm<=0||c.deltaUm>20||!std::isfinite(c.cutoffMm)||c.cutoffMm<=3||c.cutoffMm>=5.5)throw std::runtime_error("Invalid shape options");
 if(!c.checkpointSpecified)c.checkpointHours=(c.storage=="compact"?6.0:0.0);
 if(!std::isfinite(c.checkpointHours)||c.checkpointHours<0||c.checkpointHours>240)throw std::runtime_error("P09E2: --checkpoint-hours 0..240");
 if(c.storage!="legacy"&&c.storage!="compact")throw std::runtime_error("P09E: --storage legacy|compact");
 if(c.mechanicalVtu!="none"&&c.mechanicalVtu!="final"&&c.mechanicalVtu!="all")throw std::runtime_error("P09E: --mechanical-vtu none|final|all");
 if(c.storage=="compact"&&c.reuse!="off")throw std::runtime_error("P09E: compact runs require --reuse-p08d off");
 if(c.reuse!="auto"&&c.reuse!="off"&&c.reuse!="require")throw std::runtime_error("Invalid --reuse-p08d");
 if((c.report&&c.dry)||(c.geometryOnly&&(c.report||c.dry)))throw std::runtime_error("Conflicting report/dry-run/geometry-only options");
 return c;
}
uint64_t hash_file(const fs::path&p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot hash "+p.string());
 uint64_t h=14695981039346656037ull;char b[8192];while(f.read(b,sizeof(b))||f.gcount())for(std::streamsize k=0;k<f.gcount();++k){h^=static_cast<unsigned char>(b[k]);h*=1099511628211ull;}return h;
}
string read(const fs::path&p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return string((std::istreambuf_iterator<char>(f)),{});}
void write(const fs::path&p,const string&s){fs::create_directories(p.parent_path());fs::path t=p;t+=".tmp";
 {std::ofstream f(t,std::ios::binary|std::ios::trunc);if(!f)throw std::runtime_error("Cannot write "+t.string());f<<s;if(!f)throw std::runtime_error("Cannot finish "+t.string());}
 if(fs::exists(p))fs::remove(p);
 fs::rename(t,p);
}
void guard(const fs::path&dir,const string&filename,const string&sig,bool report){const auto p=dir/filename;
 if(fs::exists(p)){if(read(p)!=sig)throw std::runtime_error("Guard mismatch: "+p.string());}
 else{if(report)throw std::runtime_error("Missing guard: "+p.string());
  if(fs::exists(dir)&&!fs::is_empty(dir))throw std::runtime_error("Unguarded nonempty folder: "+dir.string());
  fs::create_directories(dir);write(p,sig);}
}
fs::path sibling(const fs::path&self,const string&n){
#ifdef _WIN32
 return self.parent_path()/(n+".exe");
#else
 return self.parent_path()/n;
#endif
}
#ifdef _WIN32
std::wstring quote(const std::wstring&s){std::wstring out=L"\"";size_t n=0;
 for(wchar_t c:s){if(c==L'\\'){++n;continue;}if(c==L'"'){out.append(2*n+1,L'\\');out+=c;n=0;continue;}
  out.append(n,L'\\');n=0;out+=c;}
 out.append(2*n,L'\\');return out+L'"';
}
int spawn(const fs::path&exe,const std::vector<string>&args){std::wstring cmd=quote(exe.wstring());for(const auto&arg:args)cmd+=L" "+quote(fs::path(arg).wstring());
 std::vector<wchar_t>buffer(cmd.begin(),cmd.end());buffer.push_back(0);
 STARTUPINFOW si{};si.cb=sizeof(si);PROCESS_INFORMATION pi{};
 if(!CreateProcessW(exe.c_str(),buffer.data(),nullptr,nullptr,TRUE,0,nullptr,nullptr,&si,&pi))throw std::runtime_error("CreateProcessW "+std::to_string(GetLastError()));
 CloseHandle(pi.hThread);WaitForSingleObject(pi.hProcess,INFINITE);DWORD code=1;
 if(!GetExitCodeProcess(pi.hProcess,&code))code=1;CloseHandle(pi.hProcess);return int(code);
}
#else
int spawn(const fs::path&exe,const std::vector<string>&args){pid_t pid=fork();if(pid<0)throw std::runtime_error("fork failed");
 if(pid==0){std::vector<string>v{exe.string()};v.insert(v.end(),args.begin(),args.end());std::vector<char*>ptrs;for(auto&s:v)ptrs.push_back(s.data());ptrs.push_back(nullptr);
  execv(exe.c_str(),ptrs.data());std::cerr<<"execv "<<strerror(errno)<<"\n";_exit(127);}
 int status=0;while(waitpid(pid,&status,0)<0){if(errno==EINTR)continue;throw std::runtime_error("waitpid error");}
 return WIFEXITED(status)?WEXITSTATUS(status):128;
}
#endif
void run(const fs::path&exe,const std::vector<string>&args){std::cout<<"[P09C RUN] "<<exe.filename()<<std::flush;
 int rc=spawn(exe,args);if(rc)throw std::runtime_error("Child failed "+exe.string()+" exit="+std::to_string(rc));}
std::vector<double> numbers(const string&s){std::vector<double>v;for(const auto&tok:split(s)){
 size_t used=0;double a=std::stod(tok,&used);if(used!=tok.size()||!std::isfinite(a))throw std::runtime_error("Non-numeric CSV field");v.push_back(a);}return v;
}
string time_list(int dt,int tend){string out;for(int t=dt;t<=tend;t+=dt){if(!out.empty())out+=',';out+=std::to_string(t);}return out;}
void thermal_check(const fs::path&dir,const fs::path&mesh,int dt,int tend,double xi){
 std::ifstream info(dir/"summary.csv");string header,line;
 if(!info||!std::getline(info,header)||!std::getline(info,line)||header.find("t_end_s")==string::npos)throw std::runtime_error("Thermal summary missing");
 auto cells=split(line);if(cells.size()<16||cells[0]!=mesh.filename().string())throw std::runtime_error("Thermal mesh mismatch");
 const auto eq=[](double x,double y){return std::abs(x-y)<=1e-11*std::max({1.,std::abs(x),std::abs(y)});};
 if(!eq(std::stod(cells[4]),dt)||!eq(std::stod(cells[5]),tend)||!eq(std::stod(cells[6]),xi))throw std::runtime_error("Thermal settings mismatch");
 std::ifstream ts(dir/"time_series.csv");if(!ts||!std::getline(ts,line)||line.find("xi")==string::npos)throw std::runtime_error("Missing thermal time series");
 int step=0;while(std::getline(ts,line)){if(line.empty())continue;auto v=numbers(line);++step;
  if(v.size()<21||!eq(v[0],step*dt)||!eq(v[1],xi))throw std::runtime_error("Thermal time history mismatch");}
 if(step!=tend/dt)throw std::runtime_error("Incomplete thermal trajectory");
 for(int t=dt;t<=tend;t+=dt)if(!fs::is_regular_file(dir/("thermal_"+std::to_string(t)+"s.vtu"))&&
     !fs::is_regular_file(dir/("thermal_"+std::to_string(t)+"s.p09e")))throw std::runtime_error("Missing thermal field");
}
struct Result {std::array<double,3>j{};int steps=0;};
Result mechanics_check(const fs::path&dest,int dt,int tend,int peakP){
 std::ifstream f(dest/"time_series.csv");string line;
 if(!f||!std::getline(f,line)||line.find("Psi6")==string::npos)throw std::runtime_error("Missing mechanical time series");
 Result r;double previous=7.5e-7;
 while(std::getline(f,line)){if(line.empty())continue;auto x=numbers(line);
  if(x.size()<9||std::abs(x[0]-(r.steps+1)*dt)>1e-8||x[2]<0)throw std::runtime_error("Invalid j6 time series");
  r.j[0]+=(previous+x[2])*0.5*dt/tend;previous=x[2];++r.steps;}
 if(r.steps!=tend/dt)throw std::runtime_error("Incomplete mechanical trajectory");
 std::ifstream cfg(dest/"P09B_functionals_config.txt");int p=0;cfg>>p;
 if(!cfg||p!=peakP)throw std::runtime_error("P09B peak exponent mismatch");
 std::ifstream extra(dest/"P09B_functionals_history.csv");
 if(!extra||!std::getline(extra,line)||line!="time_s,dt_s,peak_power_B6,energy_density_B6_Pa,jpeak_instant,jen_instant,volume6_m3,peak_p,psi_ref_Pa")throw std::runtime_error("Invalid P09B history header");
 double oldPeak=ice3d::p09b::initial_peak_power(peakP),oldEnergy=0,peakMoment=0,energyRaw=0;int count=0;
 while(std::getline(extra,line)){if(line.empty())continue;auto x=numbers(line);
  if(x.size()!=9||std::abs(x[0]-(count+1)*dt)>1e-8||std::abs(x[1]-dt)>1e-8||int(x[7])!=peakP||
    !(x[2]>=0&&x[3]>=0&&x[6]>0)||std::abs(x[8]-ice3d::p09b::energy_ref_pa)>1e-9*std::abs(x[8])||
    std::abs(x[4]-std::pow(x[2],1.0/peakP))>1e-9*std::max(1.,x[4])||
    std::abs(x[5]-x[3]/x[8])>1e-9*std::max(1.,x[5]))throw std::runtime_error("Invalid energy/peak history");
  peakMoment+=(oldPeak+x[2])*0.5*dt/tend;energyRaw+=(oldEnergy+x[3])*0.5*dt/tend;
  oldPeak=x[2];oldEnergy=x[3];++count;}
 if(count!=r.steps)throw std::runtime_error("Incomplete triple-functional history");
 r.j[1]=std::pow(peakMoment,1.0/peakP);
 r.j[2]=energyRaw/ice3d::p09b::energy_ref_pa;
 for(double x:r.j)if(!std::isfinite(x)||x<0)throw std::runtime_error("Nonfinite functional");
 return r;
}
struct Moments {double plus=0,minus=0,meanDerivative=0,varPlus=0,varMinus=0,varDerivative=0,center=0,centerVar=0;
 std::array<double,3>dj{},middle{};};
Moments aggregate(const std::array<double,3>&p,const std::array<double,3>&m,double delta){
 if(!(delta>0))throw std::runtime_error("Nonpositive perturbation");
 Moments r;
 for(int k=0;k<3;++k){if(!std::isfinite(p[k])||!std::isfinite(m[k]))throw std::runtime_error("Nonfinite pair");
  r.plus+=W[k]*p[k];r.minus+=W[k]*m[k];r.middle[k]=0.5*(p[k]+m[k]);r.dj[k]=(p[k]-m[k])/(2*delta);}
 r.center=0.5*(r.plus+r.minus);
 for(int k=0;k<3;++k){r.varPlus+=W[k]*std::pow(p[k]-r.plus,2);r.varMinus+=W[k]*std::pow(m[k]-r.minus,2);
  r.centerVar+=W[k]*std::pow(r.middle[k]-r.center,2);r.meanDerivative+=W[k]*r.dj[k];}
 for(int k=0;k<3;++k)r.varDerivative+=2*W[k]*(r.middle[k]-r.center)*(r.dj[k]-r.meanDerivative);
 double ref=(r.varPlus-r.varMinus)/(2*delta);
 double tol=256*std::numeric_limits<double>::epsilon()*std::max({std::abs(r.varPlus),std::abs(r.varMinus),std::abs(r.centerVar)})/delta
   +1e-10*std::max({std::abs(ref),std::abs(r.varDerivative)});
 if(std::abs(ref-r.varDerivative)>tol)throw std::runtime_error("Variance central difference disagrees with covariance identity");
 return r;
}
void selftest(){
 for(int n=0;n<=5;++n){double sum=0;for(int k=0;k<3;++k)sum+=W[k]*std::pow(XI[k],n);
  double exact=n%2?0:(n==0?1:(n==2?1:3));if(std::abs(sum-exact)>1e-13)throw std::runtime_error("GH3 moment test failed");}
 for(double delta:{5e-6,10e-6})for(int obs=0;obs<3;++obs){
  // Each observable gets a different offset and derivative: both mean and variance derivatives known analytically.
  double a=0.015*(obs+1),s=0.001*(obs+1),d=0.04*(obs+1),b=-0.012*(obs+1);
  std::array<double,3>p{},m{};for(int k=0;k<3;++k){p[k]=a+s*XI[k]+delta*(d+b*XI[k]);m[k]=a+s*XI[k]-delta*(d+b*XI[k]);}
  auto v=aggregate(p,m,delta);if(std::abs(v.meanDerivative-d)>1e-11||std::abs(v.varDerivative-2*s*b)>1e-11)
   throw std::runtime_error("Analytic mean/variance derivative test failed for "+string(OBS[obs]));
 }
 if(modes("R,tz,y20").size()!=3||opts("ALL","laws").size()!=3||opts("ALL","moduli").size()!=2)throw std::runtime_error("Option expansion test failed");
 std::cout<<"P09C_SELFTEST_OK: three functionals, GH3, shape mean/variance FD and covariance\n";
}
fs::path base_path(const Config&c){string mm=c.modes,ll=c.laws,ee=c.moduli;for(auto*s:{&mm,&ll,&ee})for(char&ch:*s)if(ch==',')ch='-';
 return c.root/"LOCAL_RUNS"/"SHAPE_STAGE09"/(c.storage=="compact"?"P09E":"P09C")/(c.mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.quad)+"_t"+std::to_string(c.tend)+"_GH3_p"+std::to_string(c.peakP)+"_delta"+tag(c.deltaUm)+"um_modes"+mm+"_laws"+ll+"_E"+ee);
}
// The H2/H3 P08D archives may have been computed with more modes than this P09C run.
// Locate a *single* unambiguous compatible P08D campaign by its signed guard.
fs::path find_p08d(const Config&c,const fs::path&nominal){
 const fs::path root=c.root/"LOCAL_RUNS"/"SHAPE_STAGE08"/"P08D";
 if(!fs::is_directory(root))return {};
 std::vector<fs::path>matches;
 const string prefix="stage=P08D_GH3_v1\nmesh_hash="+std::to_string(hash_file(nominal))+"\nmesh="+c.mesh+"\n";
 for(const auto&item:fs::directory_iterator(root)){
  if(!item.is_directory()||!fs::is_regular_file(item.path()/"P08D_GUARD.txt"))continue;
  string text=read(item.path()/"P08D_GUARD.txt");
  if(text.rfind(prefix,0)!=0||text.find("delta_um="+tag(c.deltaUm)+"\n")==string::npos||
    text.find("dt="+std::to_string(c.dt)+"\n")==string::npos||text.find("tend="+std::to_string(c.tend)+"\n")==string::npos||
    text.find("quad="+std::to_string(c.quad)+"\n")==string::npos||text.find("cutoff="+tag(c.cutoffMm)+"\n")==string::npos)continue;
  bool allModes=true;for(const auto&mode:modes(c.modes)){
   auto rootMode=item.path()/mode;
   if(!fs::is_regular_file(rootMode/"geometry"/(c.mesh+"_P08_"+(mode=="R"?"radius":mode)+"_plus_"+tag(c.deltaUm)+"um.msh")))allModes=false;
  }
  if(allModes)matches.push_back(item.path());
 }
 if(matches.size()>1)throw std::runtime_error("Multiple matching P08D sources; --reuse-p08d off or remove ambiguity");
 return matches.empty()?fs::path{}:matches.front();
}
string p08d_settings(const Config&c,const string&mode,const string&sign,double xi){
 return "mode="+mode+"\nsign="+sign+"\ndelta_um="+tag(c.deltaUm)+"\ndt="+std::to_string(c.dt)+"\ntend="+std::to_string(c.tend)+"\nquad="+std::to_string(c.quad)+"\ncutoff_mm="+tag(c.cutoffMm)+"\nxi="+number(xi)+"\nlaw=EDV\nmodulus=VAR\n";
}
fs::path possible_old_thermal(const Config&c,const fs::path&old,const fs::path&shape,const string&mode,const string&sign,int k){
 if(old.empty())return {};
 const auto dir=old/mode/(sign+"_"+tag(c.deltaUm)+"um")/(k==0?"GH_minus":k==1?"GH_zero":"GH_plus");
 if(!fs::is_regular_file(dir/"P08D_CASE_GUARD.txt"))return {};
 const string wanted="mesh_hash="+std::to_string(hash_file(shape))+"\n"+p08d_settings(c,mode,sign,XI[k]);
 if(read(dir/"P08D_CASE_GUARD.txt")!=wanted)return {};
 const auto td=dir/"thermal";
 try{thermal_check(td,shape,c.dt,c.tend,XI[k]);return td;}catch(const std::exception&){return {};}
}
struct Observation {Result result;string heatSource,mechSource;fs::path thermal;};
Observation sample(const Config&c,const fs::path&base,const fs::path&old,const fs::path&shape,
 const fs::path&thermalExe,const fs::path&mechExe,const string&mode,const string&sign,int k,const string&law,const string&mod){
 const auto sub=base/mode/(sign+"_"+tag(c.deltaUm)+"um")/(k==0?"GH_minus":k==1?"GH_zero":"GH_plus");
 const auto caseDir=sub/(law+"_"+mod);
 const string signature="P09C_case_v1\nmesh_hash="+std::to_string(hash_file(shape))+"\nxi="+number(XI[k])+"\ndt="+std::to_string(c.dt)+"\ntend="+std::to_string(c.tend)+"\nquad="+std::to_string(c.quad)+"\npeak_p="+std::to_string(c.peakP)+"\nmodel="+law+"_"+mod+"\n";
 guard(caseDir,"P09C_CASE_GUARD.txt",signature,c.report);
 fs::path td=sub/"thermal";
 string heatSource="LOCAL_P09C";
 const auto provenance=sub/"P09C_THERMAL_SOURCE.txt";
 if(fs::is_regular_file(provenance)){
  auto lines=split(read(provenance),'\n');if(lines.size()<2)throw std::runtime_error("Invalid P09C thermal source file");
  heatSource=lines[0];td=fs::path(lines[1]);
  if(heatSource!="LOCAL_P09C"&&heatSource!="P08D_THERMAL")throw std::runtime_error("Invalid thermal source type");
  if(heatSource=="LOCAL_P09C"&&td!=sub/"thermal")throw std::runtime_error("Unexpected local thermal path");
  if(c.reuse=="off"&&heatSource=="P08D_THERMAL")throw std::runtime_error("Existing P09C results require P08D thermal reuse, but --reuse-p08d off was selected");
  if(heatSource=="P08D_THERMAL"&&td!=possible_old_thermal(c,old,shape,mode,sign,k))throw std::runtime_error("P08D reuse source is no longer valid");
 }else{
  if(fs::exists(td)&&!fs::is_empty(td)){
   thermal_check(td,shape,c.dt,c.tend,XI[k]);
  }else if(c.reuse!="off"){
   fs::path candidate=possible_old_thermal(c,old,shape,mode,sign,k);
   if(!candidate.empty()){td=candidate;heatSource="P08D_THERMAL";}
   else if(c.reuse=="require")throw std::runtime_error("P08D thermal reuse required, unavailable: "+mode+" "+sign+" k="+std::to_string(k));
  }
  if(!c.report)write(provenance,heatSource+"\n"+td.string()+"\n");
 }
 try{thermal_check(td,shape,c.dt,c.tend,XI[k]);}
 catch(const std::exception&){
  if(c.report||heatSource=="P08D_THERMAL")throw;
  if(fs::exists(td)&&!fs::is_empty(td))throw std::runtime_error("Incomplete thermal output (not overwritten): "+td.string());
  std::vector<std::string> args={"--mesh",shape.string(),"--out",td.string(),"--dt",std::to_string(c.dt),"--tend",std::to_string(c.tend),"--xi",number(XI[k])};
  if(c.storage=="compact")args.push_back("--compact");else args.push_back("--every-step");
  run(thermalExe,args);
  thermal_check(td,shape,c.dt,c.tend,XI[k]);
 }
 if(c.storage=="compact")for(int t=c.dt;t<=c.tend;t+=c.dt)
  if(!fs::is_regular_file(td/("thermal_"+std::to_string(t)+"s.p09e")))throw std::runtime_error("P09E: expected compact thermal field");
 const auto md=caseDir/"mechanics";
 const auto dest=md/(law+"_"+mod);
 Result r;bool valid=false;
 try{r=mechanics_check(dest,c.dt,c.tend,c.peakP);valid=fs::is_regular_file(dest/"restart.bin");}catch(const std::exception&){valid=false;}
 string mechSource="REUSED_LOCAL";
 if(!valid){
  if(c.report)throw std::runtime_error("Missing mechanical data: "+dest.string());
  run(mechExe,{"--mesh",shape.string(),"--temp-dir",td.string(),"--out",md.string(),"--law",law,"--modulus",mod,
   "--times",time_list(c.dt,c.tend),"--quad",std::to_string(c.quad),"--cg-tol","2e-8","--preconditioner","jacobi",
   "--optimization","on","--spmv","projected","--parallel-assembly","on","--threads",std::to_string(c.threads),
   "--functionals","triple","--peak-p",std::to_string(c.peakP),"--resume","--vtu",c.mechanicalVtu,
   "--checkpoint-hours",number(c.checkpointHours)});
  r=mechanics_check(dest,c.dt,c.tend,c.peakP);
  if(!fs::is_regular_file(dest/"restart.bin"))throw std::runtime_error("Missing mechanical checkpoint: "+dest.string());
  mechSource="LOCAL_FEM";
 }
 return {r,heatSource,mechSource,td};
}
// Refuse a mislabeled HP mesh before any thermal/mechanical computation.
// The criteria are based on the measured original H4 pore face statistics.
void verify_hp_pore_mesh(const fs::path&mesh,const string& meshName){
 std::ifstream in(mesh);if(!in)throw std::runtime_error("Cannot read HP mesh");
 string line;std::vector<std::array<double,3>>xyz;std::vector<double>edges;
 size_t poreFaces=0,b6Faces=0,tets=0;double maxWallError=0;
 while(std::getline(in,line)){
  if(line=="$MeshFormat"){
   if(!std::getline(in,line)||line.find("2.2 0")!=0)throw std::runtime_error("HP needs Gmsh MSH2.2 ASCII");
  }else if(line=="$Nodes"){
   size_t count=0;if(!(in>>count)||count<1000)throw std::runtime_error("Invalid HP nodes");
   xyz.resize(count+1);
   for(size_t i=0;i<count;++i){size_t id=0;double x,y,z;
    if(!(in>>id>>x>>y>>z)||id<1||id>count)throw std::runtime_error("Invalid HP node record");
    xyz[id]={x,y,z};}
   std::getline(in,line);
  }else if(line=="$Elements"){
   size_t count=0;if(!(in>>count)||count<1000||xyz.empty())throw std::runtime_error("Invalid HP elements");
   std::getline(in,line);
   for(size_t i=0;i<count;++i){
    if(!std::getline(in,line))throw std::runtime_error("Truncated HP element list");
    std::istringstream row(line);long long id;int type,ntags;
    if(!(row>>id>>type>>ntags)||ntags<1)throw std::runtime_error("Invalid HP element line");
    int phys=0;for(int k=0;k<ntags;++k){int a=0;row>>a;if(k==0)phys=a;}
    if(type==11){if(phys!=1)throw std::runtime_error("HP Tet10 must have physical tag 1");++tets;}
    if(type==9&&(phys==8||phys==9)){
     int face[6];for(int&v:face){if(!(row>>v)||v<1||size_t(v)>=xyz.size())throw std::runtime_error("Invalid HP Tri6");}
     if(phys==9){++b6Faces;continue;}
     ++poreFaces;
     for(int v:face){const auto&x=xyz[v];const double d=std::sqrt(x[0]*x[0]+x[1]*x[1]+(x[2]-.03)*(x[2]-.03));
      maxWallError=std::max(maxWallError,std::abs(d-.001));}
     for(int k=0;k<3;++k){const auto&a=xyz[face[k]],&b=xyz[face[(k+1)%3]];
      double dx=a[0]-b[0],dy=a[1]-b[1],dz=a[2]-b[2];edges.push_back(std::sqrt(dx*dx+dy*dy+dz*dz));}
    }
   }
  }
 }
 const int factor=meshName=="HP2"?2:meshName=="HP4"?4:meshName=="HP8"?8:1;
 if(poreFaces<=1698||tets<1000||b6Faces<100||maxWallError>5e-9||edges.empty())
  throw std::runtime_error("P09D4 pore mesh: invalid density/tags/spherical wall");
 std::nth_element(edges.begin(),edges.begin()+edges.size()/2,edges.end());
 const double median=edges[edges.size()/2];
 // The target is the actually measured HP median, not merely the Gmsh field input.
 // The 15% window tolerates different Gmsh versions while preventing mislabeled meshes.
 constexpr double hpMedian=0.00008452;
 const double target=hpMedian/factor;
 if(median<target*0.85||median>target*1.15)
  throw std::runtime_error("P09D4 "+meshName+" median wall edge="+number(median*1000)+
    " mm; expected near "+number(target*1000)+" mm (15% tolerance)");
 const size_t minFaces=static_cast<size_t>(4212.0*factor*factor*0.67);
 if(poreFaces<minFaces)throw std::runtime_error("P09D4 "+meshName+" pore surface has too few Tri6 faces");
 std::cout<<"P09D4_MESH_OK mesh="<<meshName<<" factor="<<factor<<" Tet10="<<tets
  <<" pore_Tri6="<<poreFaces<<" B6_Tri6="<<b6Faces
  <<" median_pore_edge_mm="<<median*1000<<" max_wall_radius_error_m="<<maxWallError<<"\n";
}
void execute(const Config&c,const fs::path&self){
 const auto ms=modes(c.modes),ll=opts(c.laws,"laws"),ee=opts(c.moduli,"moduli");
 const fs::path mesh=c.root/"meshes"/(c.mesh+".msh");const fs::path base=base_path(c);
 const auto geometryExe=sibling(self,"stage3d08_geometry"),thermalExe=sibling(self,"stage3d02_thermal"),mechExe=sibling(self,"stage3d06_spatial");
 for(const auto&p:{mesh,geometryExe,thermalExe,mechExe})if(!fs::is_regular_file(p))throw std::runtime_error("Missing prerequisite: "+p.string());
 if(is_hp_family(c.mesh))verify_hp_pore_mesh(mesh,c.mesh);
 fs::path old;if(c.reuse!="off" && !is_hp_family(c.mesh))old=find_p08d(c,mesh);
 // In strict reuse mode fail before creating any P09C output or executing FEM.
 if(c.reuse=="require"){
  if(old.empty())throw std::runtime_error("No compatible P08D campaign; strict thermal reuse unavailable");
  for(const auto&mode:ms){
   const string label=mode=="R"?"radius":mode;
   const fs::path oldGeo=old/mode/"geometry";
   for(const auto&sign:{string("plus"),string("minus")}){
    const fs::path shape=oldGeo/(c.mesh+"_P08_"+label+"_"+sign+"_"+tag(c.deltaUm)+"um.msh");
    if(!fs::is_regular_file(shape))throw std::runtime_error("Strict reuse: missing P08D geometry "+shape.string());
    for(int k=0;k<3;++k){
     if(possible_old_thermal(c,old,shape,mode,sign,k).empty())
      throw std::runtime_error("Strict reuse: incompatible P08D temperature "+mode+" "+sign+" node="+std::to_string(k));
    }
   }
  }
 }
 const string signature="P09C_v1\nmesh_hash="+std::to_string(hash_file(mesh))+"\nmesh="+c.mesh+"\nmodes="+c.modes+"\nlaws="+c.laws+"\nmoduli="+c.moduli+"\npeak_p="+std::to_string(c.peakP)+"\ndt="+std::to_string(c.dt)+"\ntend="+std::to_string(c.tend)+"\nquad="+std::to_string(c.quad)+"\ndelta_um="+tag(c.deltaUm)+"\ncutoff_mm="+tag(c.cutoffMm)+"\nreuse="+c.reuse+"\n";
 std::cout<<"P09C output: "<<base<<"\n";
 if(c.dry){std::cout<<"P09C_DRY_RUN_OK (no files changed); previous P08D="<<(old.empty()?"NONE":old.string())<<"\n";return;}
 guard(base,"P09C_GUARD.txt",signature,c.report);
 if(!c.report)write(base/"P09C_STATUS.txt","status=RUNNING\n");
 std::ostringstream raw,nodes,out;raw<<std::setprecision(17);nodes<<std::setprecision(17);out<<std::setprecision(17);
 raw<<"mode,sign,law,modulus,xi,weight,j6,jpeak,jen,steps,thermal_source,mechanics_source,mesh_hash\n";
 nodes<<"mode,law,modulus,functional,xi,weight,value_plus,value_minus,D_per_m,midpoint\n";
 out<<"mode,mesh,dt_s,tend_s,quad,delta_um,law,modulus,peak_p,functional,mean_plus,mean_minus,D_mean_per_m,variance_plus,variance_minus,D_variance_per_m,mean_midpoint,variance_midpoint,xi0_D_per_m\n";
 for(const auto&mode:ms){
  const fs::path gd=base/mode/"geometry";
  const string label=mode=="R"?"radius":mode;
  fs::path plus=gd/(c.mesh+"_P08_"+label+"_plus_"+tag(c.deltaUm)+"um.msh");
  fs::path minus=gd/(c.mesh+"_P08_"+label+"_minus_"+tag(c.deltaUm)+"um.msh");
  if(!fs::is_regular_file(plus)||!fs::is_regular_file(minus)||!fs::is_regular_file(gd/"P08_GEOMETRIC_DERIVATIVE.csv")){
   if(c.report)throw std::runtime_error("Missing geometry for "+mode);
   if(fs::exists(gd)&&!fs::is_empty(gd))throw std::runtime_error("Partial geometry output: "+gd.string());
   run(geometryExe,{"--mesh",mesh.string(),"--out",gd.string(),"--mode",label,"--delta-um",number(c.deltaUm),"--cutoff-mm",number(c.cutoffMm),"--quad",std::to_string(c.quad)});
  }
  if(!fs::is_regular_file(plus)||!fs::is_regular_file(minus)||!fs::is_regular_file(gd/"P08_GEOMETRIC_DERIVATIVE.csv"))throw std::runtime_error("Missing geometry audit");
  if(c.geometryOnly){std::cout<<"P09D4_GEOMETRY_VALIDATED mesh="<<c.mesh<<" mode="<<mode<<"\n";continue;}
  for(const auto&law:ll)for(const auto&mod:ee){
   std::array<Result,3>p{},m{};
   for(int k=0;k<3;++k){
    Observation pos=sample(c,base,old,plus,thermalExe,mechExe,mode,"plus",k,law,mod);
    Observation neg=sample(c,base,old,minus,thermalExe,mechExe,mode,"minus",k,law,mod);
    p[k]=pos.result;m[k]=neg.result;
    for(int s=0;s<2;++s){const Observation&a=(s==0?pos:neg);const fs::path&meshCase=s==0?plus:minus;
     raw<<mode<<','<<(s==0?"plus":"minus")<<','<<law<<','<<mod<<','<<XI[k]<<','<<W[k]<<','<<a.result.j[0]<<','<<a.result.j[1]<<','<<a.result.j[2]<<','<<a.result.steps<<','<<a.heatSource<<','<<a.mechSource<<','<<hash_file(meshCase)<<'\n';}
   }
   for(int obs=0;obs<3;++obs){std::array<double,3>pv{},mv{};for(int k=0;k<3;++k){pv[k]=p[k].j[obs];mv[k]=m[k].j[obs];}
    auto a=aggregate(pv,mv,c.deltaUm*1e-6);
    for(int k=0;k<3;++k)nodes<<mode<<','<<law<<','<<mod<<','<<OBS[obs]<<','<<XI[k]<<','<<W[k]<<','<<pv[k]<<','<<mv[k]<<','<<a.dj[k]<<','<<a.middle[k]<<'\n';
    out<<mode<<','<<c.mesh<<','<<c.dt<<','<<c.tend<<','<<c.quad<<','<<c.deltaUm<<','<<law<<','<<mod<<','<<c.peakP<<','<<OBS[obs]<<','<<a.plus<<','<<a.minus<<','<<a.meanDerivative<<','<<a.varPlus<<','<<a.varMinus<<','<<a.varDerivative<<','<<a.center<<','<<a.centerVar<<','<<a.dj[1]<<'\n';
    std::cout<<"[P09C GH3] "<<mode<<" "<<law<<"/"<<mod<<" "<<OBS[obs]<<" D_M="<<a.meanDerivative<<" D_V="<<a.varDerivative<<"\n";
   }
 if(!c.report){write(base/"P09C_SAMPLES.csv",raw.str());write(base/"P09C_NODES.csv",nodes.str());write(base/"P09C_SENSITIVITIES.csv",out.str());}
  }
 }
 if(c.geometryOnly){
  write(base/"P09D4_GEOMETRY_ONLY_OK.txt","status=SUCCESS\nmesh="+c.mesh+"\nmodes="+c.modes+"\n");
  write(base/"P09C_STATUS.txt","status=GEOMETRY_VALIDATED\nmesh="+c.mesh+"\n");
  std::cout<<"P09D4_GEOMETRY_ONLY_SUCCESS "<<base<<"\n";return;
 }
 if(!c.report){write(base/"P09C_SAMPLES.csv",raw.str());write(base/"P09C_NODES.csv",nodes.str());write(base/"P09C_SENSITIVITIES.csv",out.str());
  write(base/"P09C_STATUS.txt","status=SUCCESS\nmesh="+c.mesh+"\nmodes="+c.modes+"\nlaws="+c.laws+"\nmoduli="+c.moduli+"\npeak_p="+std::to_string(c.peakP)+"\ndt="+std::to_string(c.dt)+"\ntend="+std::to_string(c.tend)+"\n");}
 std::cout<<"P09C_SUCCESS "<<base<<"\n";
}
}
int main(int argc,char**argv){try{const auto c=parse(argc,argv);if(c.selftest){selftest();return 0;}
 execute(c,fs::absolute(fs::path(argv[0])));return 0;
 }catch(const std::exception&e){std::cerr<<"P09C_ERROR: "<<e.what()<<"\n";return 2;}}
