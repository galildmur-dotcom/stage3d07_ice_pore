// Stage 3D-08D: GH3 stochastic shape sensitivities of j6, EDV/VAR.
// Self-contained Qt Creator launcher, reuses the existing FEM executables.
// No nominal-geometry solve: the central FD of variance is computed exactly
// as 2*Cov_GH( (j_plus+j_minus)/2, (j_plus-j_minus)/(2 delta) ).
#include "qt_runner_paths.hpp"
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
using std::string;
struct Config {
 string mesh="H0", modes="R,tz,y20", reuse="auto";
 int dt=300,tend=3600,quad=3,
#ifdef STAGE3D08_NO_OPENMP
 threads=1;
#else
 threads=4;
#endif
 double delta_um=5,cutoff_mm=5;
 bool dry=false,report_only=false,selftest=false;
 fs::path root=fs::path(STAGE3D06_ROOT_DIR);
};
constexpr std::array<double,3> W{{1./6.,2./3.,1./6.}};
const std::array<double,3> XI{{-std::sqrt(3.),0.,std::sqrt(3.)}};
string num(double x){std::ostringstream o;o<<std::setprecision(17)<<x;return o.str();}
string tag(double x){std::ostringstream o;o<<std::fixed<<std::setprecision(3)<<x;string t=o.str();for(char&c:t)if(c=='.')c='p';return t;}
std::vector<string> split(const string&s,char d=',') {std::istringstream is(s);string x;std::vector<string>v;while(std::getline(is,x,d))v.push_back(x);return v;}
std::vector<string> get_modes(const string&input){auto v=split(input);if(v.empty())throw std::runtime_error("No modes");
 for(const auto&x:v){if(x!="R"&&x!="tz"&&x!="y20")throw std::runtime_error("Only R,tz,y20 are supported");if(std::count(v.begin(),v.end(),x)!=1)throw std::runtime_error("Duplicate mode");}return v;}
Config parse(int argc,char**argv){Config c;
 for(int i=1;i<argc;++i){string f=argv[i];auto val=[&](){if(i+1==argc)throw std::runtime_error("Missing value after "+f);return string(argv[++i]);};
  if(f=="--mesh")c.mesh=val();else if(f=="--modes")c.modes=val();else if(f=="--dt")c.dt=std::stoi(val());
  else if(f=="--tend")c.tend=std::stoi(val());else if(f=="--quad")c.quad=std::stoi(val());
  else if(f=="--delta-um")c.delta_um=std::stod(val());else if(f=="--cutoff-mm")c.cutoff_mm=std::stod(val());
  else if(f=="--threads")c.threads=std::stoi(val());else if(f=="--reuse-xi0")c.reuse=val();
  else if(f=="--root")c.root=fs::absolute(val());else if(f=="--dry-run")c.dry=true;
  else if(f=="--report-only")c.report_only=true;else if(f=="--selftest")c.selftest=true;
  else if(f=="--help"||f=="-h"){
   std::cout<<"Stage3D08D GH3 EDV/VAR: --mesh H0|H1|H2|H3|H4 --modes R,tz,y20"
   <<" --delta-um 5 --dt 300 --tend 3600 --quad 3 --threads 4"
   <<" --cutoff-mm 5 --reuse-xi0 auto|require|off"
   <<" [--dry-run|--report-only|--selftest] [--root PROJECT_FOLDER]\n"
   <<"Output: <root>/LOCAL_RUNS/SHAPE_STAGE08/P08D/...; no old results modified.\n";std::exit(0);}
  else throw std::runtime_error("Unknown option "+f);
 }
 if(c.mesh!="H0"&&c.mesh!="H1"&&c.mesh!="H2"&&c.mesh!="H3"&&c.mesh!="H4")throw std::runtime_error("Invalid --mesh");
 get_modes(c.modes);
 if(c.dt<1||c.tend<1||c.tend%c.dt!=0||c.quad<3||c.quad>4||c.threads<1||c.threads>32)throw std::runtime_error("Invalid dt/tend/quad/threads");
 if(!std::isfinite(c.delta_um)||!(c.delta_um>0&&c.delta_um<=20))throw std::runtime_error("Invalid delta");
 if(!std::isfinite(c.cutoff_mm)||!(c.cutoff_mm>3&&c.cutoff_mm<5.5))throw std::runtime_error("Invalid cutoff");
 if(c.reuse!="auto"&&c.reuse!="require"&&c.reuse!="off")throw std::runtime_error("Invalid --reuse-xi0");
 if(c.dry&&c.report_only)throw std::runtime_error("Choose one of --dry-run and --report-only");
 return c;
}
struct Moments {double mp=0,mm=0,vp=0,vm=0,dm=0,dv=0,mc=0,vc=0;std::array<double,3> dj{},mid{};};
Moments combine(const std::array<double,3>&plus,const std::array<double,3>&minus,double delta){
 if(!(delta>0))throw std::runtime_error("delta <=0");
 Moments m;
 for(int k=0;k<3;++k){if(!std::isfinite(plus[k])||!std::isfinite(minus[k]))throw std::runtime_error("Nonfinite j6");
  m.mp+=W[k]*plus[k];m.mm+=W[k]*minus[k];m.mid[k]=.5*(plus[k]+minus[k]);m.dj[k]=(plus[k]-minus[k])/(2*delta);}
 m.mc=.5*(m.mp+m.mm);
 for(int k=0;k<3;++k){double ep=plus[k]-m.mp,em=minus[k]-m.mm,ec=m.mid[k]-m.mc;
  m.vp+=W[k]*ep*ep;m.vm+=W[k]*em*em;m.vc+=W[k]*ec*ec;
  m.dm+=W[k]*m.dj[k];}
 for(int k=0;k<3;++k)m.dv+=2*W[k]*(m.mid[k]-m.mc)*(m.dj[k]-m.dm);
 // Check the identical central difference formula without subtracting E[j^2]-E[j]^2.
 const double ref=(m.vp-m.vm)/(2*delta);
 const double check_tol=128*std::numeric_limits<double>::epsilon()
   *std::max({std::abs(m.vp),std::abs(m.vm),std::abs(m.vc)})/delta
   +1e-10*std::max(std::abs(ref),std::abs(m.dv));
 if(std::abs(ref-m.dv)>check_tol)throw std::runtime_error("GH3 variance FD/covariance mismatch");
 return m;
}
void selftest(){double sw=std::accumulate(W.begin(),W.end(),0.);if(std::abs(sw-1)>1e-15)throw std::runtime_error("GH3 sum");
 for(int n=0;n<=5;++n){double q=0;for(int k=0;k<3;++k)q+=W[k]*std::pow(XI[k],n);
  double expected=n%2?0:(n==0?1:(n==2?1:3));if(std::abs(q-expected)>1e-13)throw std::runtime_error("GH3 Gaussian moment "+std::to_string(n));}
 for(double d:{5e-6,2.5e-6}){
  std::array<double,3>p{},m{};double c=.008,b=.001,a=.07,e=-.03;
  for(int k=0;k<3;++k){p[k]=c+b*XI[k]+d*(a+e*XI[k]);m[k]=c+b*XI[k]-d*(a+e*XI[k]);}
  auto r=combine(p,m,d);
  if(std::abs(r.dm-a)>1e-12||std::abs(r.dv-2*b*e)>1e-12||std::abs(r.vc-b*b)>1e-12)
   throw std::runtime_error("GH3 affine shape sensitivity analytic test");
 }
 {std::array<double,3> p{{.004,.005,.007}},m{{.003,.006,.008}};auto r=combine(p,m,5e-6);
 if(!(r.vp>=0&&r.vm>=0&&r.vc>=0))throw std::runtime_error("Negative variance");}
 std::cout<<"P08D_SELFTEST_OK: GH3 moments degree 0..5, derivatives of mean/variance, positivity\n";
}
uint64_t hash_file(const fs::path&p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot hash "+p.string());
 uint64_t h=14695981039346656037ull;char buf[8192];while(f.read(buf,sizeof(buf))||f.gcount())for(std::streamsize i=0;i<f.gcount();++i){h^=(unsigned char)buf[i];h*=1099511628211ull;}return h;}
string read_text(const fs::path&p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return string((std::istreambuf_iterator<char>(f)),{});}
void write_atomic(const fs::path&p,const string&s){fs::create_directories(p.parent_path());fs::path tmp=p;tmp+=".tmp";
 {std::ofstream f(tmp,std::ios::binary|std::ios::trunc);if(!f)throw std::runtime_error("Cannot write "+tmp.string());f<<s;if(!f)throw std::runtime_error("Failed writing "+tmp.string());}
 // Windows rename will not replace an existing file. Remove only our own report file.
 if(fs::exists(p))fs::remove(p);
 fs::rename(tmp,p);
}
void guard(const fs::path&dir,const string&filename,const string&signature){fs::path p=dir/filename;
 if(fs::exists(p)){if(read_text(p)!=signature)throw std::runtime_error("Input guard mismatch: "+p.string());}
 else{if(fs::exists(dir)&&!fs::is_empty(dir))throw std::runtime_error("Nonempty unguarded directory: "+dir.string());
  fs::create_directories(dir);write_atomic(p,signature);}}
fs::path sibling(const fs::path&self,const string&exe){
#ifdef _WIN32
 return self.parent_path()/(exe+".exe");
#else
 return self.parent_path()/exe;
#endif
}
#ifdef _WIN32
std::wstring quote(const std::wstring&s){std::wstring q=L"\"";size_t slash=0;
 for(wchar_t c:s){if(c==L'\\'){++slash;continue;}if(c==L'"'){q.append(2*slash+1,L'\\');q+=c;slash=0;continue;}
 q.append(slash,L'\\');slash=0;q+=c;}q.append(2*slash,L'\\');return q+L'"';}
int process(const fs::path&exe,const std::vector<fs::path>&args){std::wstring cmd=quote(exe.wstring());for(const auto&a:args)cmd+=L" "+quote(a.wstring());
 std::vector<wchar_t> b(cmd.begin(),cmd.end());b.push_back(0);STARTUPINFOW si{};si.cb=sizeof(si);PROCESS_INFORMATION pi{};
 if(!CreateProcessW(exe.c_str(),b.data(),nullptr,nullptr,TRUE,0,nullptr,nullptr,&si,&pi))throw std::runtime_error("CreateProcessW error "+std::to_string(GetLastError()));
 CloseHandle(pi.hThread);WaitForSingleObject(pi.hProcess,INFINITE);DWORD code=1;if(!GetExitCodeProcess(pi.hProcess,&code))code=1;CloseHandle(pi.hProcess);return static_cast<int>(code);}
#else
int process(const fs::path&exe,const std::vector<fs::path>&args){pid_t child=fork();if(child<0)throw std::runtime_error("fork error");
 if(child==0){std::vector<string>v{exe.string()};for(const auto&a:args)v.push_back(a.string());std::vector<char*> ap;for(auto&x:v)ap.push_back(x.data());ap.push_back(nullptr);
  execv(exe.c_str(),ap.data());std::cerr<<"execv "<<exe<<" failed: "<<strerror(errno)<<'\n';_exit(127);}
 int st=0;while(waitpid(child,&st,0)<0){if(errno==EINTR)continue;throw std::runtime_error("waitpid error");}return WIFEXITED(st)?WEXITSTATUS(st):128;}
#endif
void run(const fs::path&exe,std::vector<fs::path>args){std::cout<<"[RUN] "<<exe.filename().string();for(auto&a:args)std::cout<<" "<<a.string();std::cout<<std::endl;
 int rc=process(exe,args);if(rc)throw std::runtime_error("Child process failed code "+std::to_string(rc)+" "+exe.string());}
std::vector<double> parse_row(const string&line){std::vector<double>v;for(const auto&x:split(line)){
 size_t end=0;double d=std::stod(x,&end);if(end!=x.size()||!std::isfinite(d))throw std::runtime_error("Non-numeric CSV field");v.push_back(d);}return v;}
struct Hist {double j=0,phi=0;int steps=0;};
Hist history(const fs::path&p,int dt,int tend){std::ifstream f(p);if(!f)throw std::runtime_error("Missing history "+p.string());
 string line;if(!std::getline(f,line)||line.find("Psi6")==string::npos)throw std::runtime_error("Bad EDV history header "+p.string());
 Hist h;double prev=7.5e-7;while(std::getline(f,line)){if(line.empty())continue;auto v=parse_row(line);
 if(v.size()<8||std::abs(v[0]-(h.steps+1)*dt)>1e-7||v[2]<0)throw std::runtime_error("Invalid history row "+p.string());
 h.j+=(prev+v[2])*0.5*dt/tend;prev=v[2];h.phi=v[2];++h.steps;}
 if(h.steps!=tend/dt)throw std::runtime_error("Incomplete EDV history "+p.string());
 return h;
}
void checked_thermal(const fs::path&dir,const fs::path&mesh,int dt,int tend,double xi){
 std::ifstream f(dir/"summary.csv");string h,line;
 if(!f||!std::getline(f,h)||!std::getline(f,line)||h.find("t_end_s")==string::npos)throw std::runtime_error("Missing/bad thermal summary: "+dir.string());
 auto cols=split(line);if(cols.size()<16||cols[0]!=mesh.filename().string())throw std::runtime_error("Thermal mesh mismatch");
 const auto eq=[](double a,double b){return std::abs(a-b)<=1e-11*std::max({1.,std::abs(a),std::abs(b)});};
 if(!eq(std::stod(cols[4]),dt)||!eq(std::stod(cols[5]),tend)||!eq(std::stod(cols[6]),xi))throw std::runtime_error("Thermal dt/tend/xi mismatch: "+dir.string());
 std::ifstream ts(dir/"time_series.csv");if(!ts||!std::getline(ts,line)||line.find("xi")==string::npos)throw std::runtime_error("Missing thermal history");
 int k=0;while(std::getline(ts,line)){if(line.empty())continue;auto v=parse_row(line);++k;if(v.size()<21||!eq(v[0],k*dt)||!eq(v[1],xi))throw std::runtime_error("Thermal time/xi mismatch");}
 if(k!=tend/dt)throw std::runtime_error("Incomplete thermal time series");
 for(int t=dt;t<=tend;t+=dt)if(!fs::is_regular_file(dir/("thermal_"+std::to_string(t)+"s.vtu")))throw std::runtime_error("Missing thermal VTU at t="+std::to_string(t));
}
struct Sample {Hist h;string source;fs::path path;};
string settings(const string&mode,const string&sign,const Config&c,double xi,bool legacy_radial){
 string s="mode="+mode+"\nsign="+sign+"\ndelta_um="+tag(c.delta_um)+"\ndt="+std::to_string(c.dt)+"\ntend="+std::to_string(c.tend)+"\nquad="+std::to_string(c.quad);
 if(!legacy_radial||std::abs(c.cutoff_mm-5)>1e-12)s+="\ncutoff_mm="+(legacy_radial?std::to_string(c.cutoff_mm):tag(c.cutoff_mm));
 return s+"\nxi="+num(xi)+"\nlaw=EDV\nmodulus=VAR\n";
}
string tlist(int dt,int tend){string s;for(int t=dt;t<=tend;t+=dt){if(!s.empty())s+=',';s+=std::to_string(t);}return s;}
fs::path output_base(const Config&c){string modes=c.modes;for(char&ch:modes)if(ch==',')ch='-';
 return c.root/"LOCAL_RUNS"/"SHAPE_STAGE08"/"P08D"/(c.mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.quad)+"_t"+std::to_string(c.tend)+"_EDV_VAR_cutoff"+tag(c.cutoff_mm)+"mm_delta"+tag(c.delta_um)+"um_modes"+modes);}
fs::path external_xi0(const Config&c,const string&mode,const string&sign){
 fs::path root=c.root/"LOCAL_RUNS"/"SHAPE_STAGE08";
 if(mode=="R"){
  string ext=c.mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.quad)+"_t"+std::to_string(c.tend)+"_EDV_VAR_XI0";
  if(std::abs(c.cutoff_mm-5)>1e-12)ext+="_cutoff"+tag(c.cutoff_mm)+"mm";
  return root/ext/("radius_"+sign+"_"+tag(c.delta_um)+"um");
 }
 return root/"P08C"/(c.mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.quad)+"_t"+std::to_string(c.tend)+"_EDV_VAR_XI0_cutoff"+tag(c.cutoff_mm)+"mm")/mode/(mode+"_"+sign+"_"+tag(c.delta_um)+"um");
}
bool usable_external(const Config&c,const fs::path&mesh,const fs::path&path,const string&mode,const string&sign,Hist&h,string&why){
 try{
  if(!fs::is_regular_file(path/"P08_SOURCE_GUARD.txt"))throw std::runtime_error("missing P08_SOURCE_GUARD.txt");
  string legacy=mode=="R"?"radius":mode;
  const string expected="mesh_hash="+std::to_string(hash_file(mesh))+"\n"+settings(legacy,sign,c,0,mode=="R");
  if(read_text(path/"P08_SOURCE_GUARD.txt")!=expected)throw std::runtime_error("input signature differs (mesh/physics/xi)");
  checked_thermal(path/"thermal",mesh,c.dt,c.tend,0);
  if(!fs::is_regular_file(path/"mechanics"/"EDV_VAR"/"restart.bin"))throw std::runtime_error("missing mechanical checkpoint");
  h=history(path/"mechanics"/"EDV_VAR"/"time_series.csv",c.dt,c.tend);
  return true;
 }catch(const std::exception&e){why=e.what();return false;}
}
string csv(const string&s){string q="\"";for(char c:s){if(c=='"')q+="\"";q+=c;}return q+"\"";}
Sample get_sample(const Config&c,const fs::path&base,const fs::path&mesh,const fs::path&heat,const fs::path&mechanics,
 const string&mode,const string&sign,int k,bool report_only){
 fs::path sub=base/mode/(sign+"_"+tag(c.delta_um)+"um")/(k==0?"GH_minus":k==1?"GH_zero":"GH_plus");
 const fs::path td=sub/"thermal",md=sub/"mechanics";
 const double xi=XI[k];
 // Saved external-source selection is authoritative across resumes and report-only calls.
 const fs::path link=sub/"P08D_SOURCE.txt";
 const string sig="mesh_hash="+std::to_string(hash_file(mesh))+"\n"+settings(mode,sign,c,xi,false);
 if(fs::exists(sub/"P08D_CASE_GUARD.txt")&&read_text(sub/"P08D_CASE_GUARD.txt")!=sig)throw std::runtime_error("P08D case input changed "+sub.string());
 if(fs::is_regular_file(link)){
  auto lines=split(read_text(link),'\n');if(lines.size()<2)throw std::runtime_error("Invalid source link");
  string source=lines[0];fs::path location=fs::path(lines[1]);
  if(source=="EXTERNAL_XI0"){
   Hist h;string why;if(k!=1||!usable_external(c,mesh,location,mode,sign,h,why))throw std::runtime_error("Existing xi0 source invalid: "+why);
   return {h,source,location};
  }
  if(source!="LOCAL_FEM"||location!=sub)throw std::runtime_error("Bad case source link: "+sub.string());
 }
 if(!fs::exists(sub/"P08D_CASE_GUARD.txt")){
  if(fs::exists(sub)&&!fs::is_empty(sub))throw std::runtime_error("Unsafe unguarded P08D case: "+sub.string());
  if(report_only)throw std::runtime_error("Missing case: "+sub.string());
  guard(sub,"P08D_CASE_GUARD.txt",sig);
 }
 if(!fs::exists(link)&&k==1&&c.reuse!="off"){
  const auto ext=external_xi0(c,mode,sign);Hist h;string why;
  if(usable_external(c,mesh,ext,mode,sign,h,why)){
   if(!report_only)write_atomic(link,"EXTERNAL_XI0\n"+ext.string()+"\n");
   return {h,"EXTERNAL_XI0",ext};
  }
  std::cout<<"[XI0 NOT REUSED] "<<mode<<" "<<sign<<": "<<why<<"\n";
  if(c.reuse=="require")throw std::runtime_error("--reuse-xi0 require failed for "+ext.string());
 }
 Hist h;bool valid=false;
 try{checked_thermal(td,mesh,c.dt,c.tend,xi);
  h=history(md/"EDV_VAR"/"time_series.csv",c.dt,c.tend);
  valid=fs::is_regular_file(md/"EDV_VAR"/"restart.bin");}catch(const std::exception&){valid=false;}
 if(valid){if(!fs::exists(link)&&!report_only)write_atomic(link,"LOCAL_FEM\n"+sub.string()+"\n");return {h,"LOCAL_FEM",sub};}
 if(report_only)throw std::runtime_error("Incomplete local FEM case: "+sub.string());
 // If thermal summary already exists, require complete fields: no overwrite of incomplete thermal runs.
 if(fs::is_regular_file(td/"summary.csv"))checked_thermal(td,mesh,c.dt,c.tend,xi);
 else{
  if(fs::exists(td)&&!fs::is_empty(td))throw std::runtime_error("Incomplete thermal output (do not overwrite): "+td.string());
  run(heat,{"--mesh",mesh,"--out",td,"--dt",std::to_string(c.dt),"--tend",std::to_string(c.tend),"--xi",num(xi),"--every-step"});
 }
 checked_thermal(td,mesh,c.dt,c.tend,xi);
 run(mechanics,{"--mesh",mesh,"--temp-dir",td,"--out",md,"--law","EDV","--modulus","VAR",
  "--times",tlist(c.dt,c.tend),"--quad",std::to_string(c.quad),"--cg-tol","2e-8","--preconditioner","jacobi",
  "--optimization","on","--spmv","projected","--parallel-assembly","on","--threads",std::to_string(c.threads),"--resume","--final-vtu-only"});
 h=history(md/"EDV_VAR"/"time_series.csv",c.dt,c.tend);
 if(!fs::is_regular_file(md/"EDV_VAR"/"restart.bin"))throw std::runtime_error("No mechanical checkpoint: "+md.string());
 write_atomic(link,"LOCAL_FEM\n"+sub.string()+"\n");return {h,"LOCAL_FEM",sub};
}
void execute(const Config&c,const fs::path&self){
 const auto ms=get_modes(c.modes);const fs::path mesh=c.root/"meshes"/(c.mesh+".msh");const auto base=output_base(c);
 const auto geo=sibling(self,"stage3d08_geometry"),heat=sibling(self,"stage3d02_thermal"),mech=sibling(self,"stage3d06_spatial");
 if(!fs::is_regular_file(mesh))throw std::runtime_error("Missing original mesh "+mesh.string());
 for(auto exe:{geo,heat,mech})if(!fs::is_regular_file(exe))throw std::runtime_error("Missing sibling executable "+exe.string());
 string projectSig="stage=P08D_GH3_v1\nmesh_hash="+std::to_string(hash_file(mesh))+"\nmesh="+c.mesh+"\nmodes="+c.modes+"\n"
  +"delta_um="+tag(c.delta_um)+"\ndt="+std::to_string(c.dt)+"\ntend="+std::to_string(c.tend)+"\nquad="+std::to_string(c.quad)+"\ncutoff="+tag(c.cutoff_mm)+"\nEDV_VAR\n";
 std::cout<<"P08D GH3 "<<c.mesh<<" modes="<<c.modes<<" delta="<<c.delta_um<<"um dt="<<c.dt<<"s tend="<<c.tend<<"s\n";
 std::cout<<"P08D output: "<<base<<"\n";
 if(c.dry){std::cout<<"P08D_DRY_RUN_OK; no files changed\n";return;}
 if(c.report_only&&!fs::is_regular_file(base/"P08D_GUARD.txt"))throw std::runtime_error("No P08D run to report");
 guard(base,"P08D_GUARD.txt",projectSig);
 if(!c.report_only)write_atomic(base/"P08D_STATUS.txt","status=RUNNING\nmesh="+c.mesh+"\nmodes="+c.modes+"\n");
 std::ostringstream raw,nodes,summary;raw<<std::setprecision(17);nodes<<std::setprecision(17);summary<<std::setprecision(17);
 raw<<"mode,sign,delta_um,xi,weight,j6,Phi6_final,steps,source,source_directory,mesh_fnv64\n";
 nodes<<"mode,mesh,dt_s,tend_s,quad,delta_um,xi,weight,j6_plus,j6_minus,D_j6_per_m,j6_midpoint\n";
 summary<<"mode,mesh,dt_s,tend_s,quad,delta_um,mean_plus,mean_minus,D_mean_per_m,variance_plus,variance_minus,D_variance_per_m,mean_midpoint,variance_midpoint,xi0_D_j6_per_m\n";
 for(const auto&mode:ms){fs::path dir=base/mode,gd=dir/"geometry";
  string gmode=mode=="R"?"radius":mode;
  fs::path gp=gd/(c.mesh+"_P08_"+gmode+"_plus_"+tag(c.delta_um)+"um.msh");
  fs::path gm=gd/(c.mesh+"_P08_"+gmode+"_minus_"+tag(c.delta_um)+"um.msh");
  if(!fs::is_regular_file(gp)||!fs::is_regular_file(gm)){
   if(c.report_only)throw std::runtime_error("Missing P08D geometry "+mode);
   if(fs::exists(gd)&&!fs::is_empty(gd))throw std::runtime_error("Partial geometry output: "+gd.string());
   run(geo,{"--mesh",mesh,"--out",gd,"--mode",gmode,"--delta-um",num(c.delta_um),"--cutoff-mm",num(c.cutoff_mm),"--quad",std::to_string(c.quad)});
  }
  if(!fs::is_regular_file(gd/"P08_GEOMETRIC_DERIVATIVE.csv"))throw std::runtime_error("Geometry audit missing");
  std::array<double,3> p{},m{};double d0=0;
  for(int k=0;k<3;++k){Sample cases[2];
   for(int s=0;s<2;++s){const string sign=s==0?"plus":"minus";const auto&shape=s==0?gp:gm;
    cases[s]=get_sample(c,base,shape,heat,mech,mode,sign,k,c.report_only);
    raw<<mode<<','<<sign<<','<<c.delta_um<<','<<XI[k]<<','<<W[k]<<','<<cases[s].h.j<<','<<cases[s].h.phi<<','<<cases[s].h.steps<<','<<cases[s].source<<','<<csv(cases[s].path.string())<<','<<hash_file(shape)<<'\n';
    std::cout<<"[CHECK] "<<mode<<" "<<sign<<" xi="<<num(XI[k])<<" j6="<<num(cases[s].h.j)<<" source="<<cases[s].source<<"\n";
   }
   p[k]=cases[0].h.j;m[k]=cases[1].h.j;
  }
  auto M=combine(p,m,c.delta_um*1e-6);d0=M.dj[1];
  for(int k=0;k<3;++k)nodes<<mode<<','<<c.mesh<<','<<c.dt<<','<<c.tend<<','<<c.quad<<','<<c.delta_um<<','<<XI[k]<<','<<W[k]<<','<<p[k]<<','<<m[k]<<','<<M.dj[k]<<','<<M.mid[k]<<'\n';
  summary<<mode<<','<<c.mesh<<','<<c.dt<<','<<c.tend<<','<<c.quad<<','<<c.delta_um<<','<<M.mp<<','<<M.mm<<','<<M.dm<<','<<M.vp<<','<<M.vm<<','<<M.dv<<','<<M.mc<<','<<M.vc<<','<<d0<<'\n';
  if(!c.report_only){write_atomic(base/"P08D_SAMPLES.csv",raw.str());write_atomic(base/"P08D_NODES.csv",nodes.str());write_atomic(base/"P08D_SENSITIVITIES.csv",summary.str());}
  std::cout<<"[GH3] "<<mode<<" D_mean="<<num(M.dm)<<" /m D_variance="<<num(M.dv)<<" /m\n";
 }
 // All-or-nothing status: a partial run is never marked successful.
 if(!c.report_only){write_atomic(base/"P08D_SAMPLES.csv",raw.str());write_atomic(base/"P08D_NODES.csv",nodes.str());write_atomic(base/"P08D_SENSITIVITIES.csv",summary.str());
  write_atomic(base/"P08D_STATUS.txt","status=SUCCESS\nmesh="+c.mesh+"\nmodes="+c.modes+"\ndt="+std::to_string(c.dt)+"\ntend="+std::to_string(c.tend)+"\n");}
 std::cout<<"P08D_GH3_OK "<<base<<"\n";
}
}
int main(int argc,char**argv){try{Config c=parse(argc,argv);if(c.selftest){selftest();return 0;}
 execute(c,fs::absolute(fs::path(argv[0])));return 0;
 }catch(const std::exception&e){std::cerr<<"P08D_ERROR: "<<e.what()<<'\n';return 2;}}
