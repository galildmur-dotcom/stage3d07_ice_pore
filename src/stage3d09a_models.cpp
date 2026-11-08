// Stage3D09A: matched E/ED/EDV x CONST/VAR comparison for nominal pore geometry.
// Native C++20 Qt Creator launcher; does not modify either FEM solver.
#include "qt_runner_paths.hpp"
#include "edv_material.hpp"
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
// <windows.h> (via windef.h) defines CONST as the macro `const`.
// The ice material model uses Modulus::CONST as an enum member.
// Remove the Windows macro *after* Windows headers have been parsed.
#ifdef CONST
# undef CONST
#endif
namespace fs=std::filesystem;
namespace {
using std::string;
struct Config {string mesh="H0",laws="ALL",moduli="ALL",quadrature="GH3";
 int dt=300,tend=3600,quad=3,
#ifdef STAGE3D08_NO_OPENMP
 threads=1;
#else
 threads=4;
#endif
 bool dry=false,report=false,test=false;
 fs::path root=STAGE3D06_ROOT_DIR;};
const std::array<double,3> GH3_X{{-std::sqrt(3.),0.,std::sqrt(3.)}};
const std::array<double,3> GH3_W{{1./6.,2./3.,1./6.}};
string as_string(double x){std::ostringstream o;o<<std::setprecision(17)<<x;return o.str();}
std::vector<string> split(string s,char delim=','){std::istringstream is(s);std::vector<string> v;string x;while(std::getline(is,x,delim))if(!x.empty())v.push_back(x);return v;}
std::vector<string> choices(const string&opts,const string&kind){auto v=opts=="ALL"?(kind=="law"?std::vector<string>{"E","ED","EDV"}:std::vector<string>{"CONST","VAR"}):split(opts);
 if(v.empty())throw std::runtime_error("Empty "+kind);
 for(const auto&x:v){if(std::count(v.begin(),v.end(),x)!=1)throw std::runtime_error("Repeated "+kind+": "+x);
  if(kind=="law" && x!="E"&&x!="ED"&&x!="EDV")throw std::runtime_error("Invalid law: "+x);
  if(kind=="mod" && x!="CONST"&&x!="VAR")throw std::runtime_error("Invalid modulus: "+x);
 }return v;}
Config parse(int argc,char**argv){Config c;
 for(int i=1;i<argc;++i){string k=argv[i];auto val=[&](){if(i+1>=argc)throw std::runtime_error("Missing value after "+k);return string(argv[++i]);};
 if(k=="--mesh")c.mesh=val();else if(k=="--laws")c.laws=val();else if(k=="--moduli")c.moduli=val();
 else if(k=="--xi-set")c.quadrature=val();else if(k=="--dt")c.dt=std::stoi(val());else if(k=="--tend")c.tend=std::stoi(val());
 else if(k=="--quad")c.quad=std::stoi(val());else if(k=="--threads")c.threads=std::stoi(val());
 else if(k=="--root")c.root=fs::absolute(val());else if(k=="--dry-run")c.dry=true;
 else if(k=="--report-only")c.report=true;else if(k=="--selftest")c.test=true;
 else if(k=="--help"||k=="-h"){
 std::cout<<"Stage3D09A matched constitutive comparison: --mesh H0|H1|H2|H3|H4 --laws ALL|E,ED,EDV --moduli ALL|CONST,VAR --xi-set ZERO|GH3 --dt 300 --tend 3600 --quad 3 --threads 4 [--dry-run|--report-only|--selftest] [--root path]\n";std::exit(0);
 }else throw std::runtime_error("Unknown flag: "+k);}
 if(c.mesh!="H0"&&c.mesh!="H1"&&c.mesh!="H2"&&c.mesh!="H3"&&c.mesh!="H4")throw std::runtime_error("Invalid mesh");
 choices(c.laws,"law");choices(c.moduli,"mod");
 if(c.quadrature!="ZERO"&&c.quadrature!="GH3")throw std::runtime_error("Expected --xi-set ZERO|GH3");
 if(c.quad!=3&&c.quad!=4)throw std::runtime_error("quad 3 or 4");
 if(c.dt<1||c.tend<1||c.tend%c.dt||c.threads<1||c.threads>32)throw std::runtime_error("Bad dt/tend/threads");
 if(c.report&&c.dry)throw std::runtime_error("Conflicting modes");return c;}
uint64_t fnv(const fs::path&p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot hash "+p.string());uint64_t h=14695981039346656037ull;char b[8192];while(f.read(b,sizeof(b))||f.gcount())for(std::streamsize k=0;k<f.gcount();++k){h^=(unsigned char)b[k];h*=1099511628211ull;}return h;}
string read(const fs::path&p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return string((std::istreambuf_iterator<char>(f)),{});}
void write(const fs::path&p,const string&s){fs::create_directories(p.parent_path());std::ofstream f(p,std::ios::binary|std::ios::trunc);if(!f)throw std::runtime_error("Cannot write "+p.string());f<<s;if(!f)throw std::runtime_error("Failed writing "+p.string());}
void guard(const fs::path&dir,const string&sig){fs::path file=dir/"P09A_GUARD.txt";
 if(fs::exists(file)){if(read(file)!=sig)throw std::runtime_error("Input signature mismatch: "+dir.string());}
 else{if(fs::exists(dir)&&!fs::is_empty(dir))throw std::runtime_error("Unsafe nonempty folder without guard: "+dir.string());fs::create_directories(dir);write(file,sig);}}
fs::path sibling(const fs::path&self,const string&name){
#ifdef _WIN32
 return self.parent_path()/(name+".exe");
#else
 return self.parent_path()/name;
#endif
}
#ifdef _WIN32
std::wstring quote(const std::wstring&s){std::wstring q=L"\"";size_t slash=0;for(wchar_t c:s){if(c==L'\\'){++slash;continue;}if(c==L'"'){q.append(2*slash+1,L'\\');q+=c;slash=0;continue;}q.append(slash,L'\\');slash=0;q+=c;}q.append(2*slash,L'\\');return q+L"\"";}
int run_process(const fs::path&exe,const std::vector<string>&a){std::wstring cmd=quote(exe.wstring());for(auto&s:a)cmd+=L" "+quote(fs::path(s).wstring());std::vector<wchar_t>b(cmd.begin(),cmd.end());b.push_back(0);STARTUPINFOW si{};si.cb=sizeof(si);PROCESS_INFORMATION pi{};
 if(!CreateProcessW(exe.c_str(),b.data(),nullptr,nullptr,TRUE,0,nullptr,nullptr,&si,&pi))throw std::runtime_error("CreateProcessW: "+std::to_string(GetLastError()));CloseHandle(pi.hThread);WaitForSingleObject(pi.hProcess,INFINITE);DWORD code=1;if(!GetExitCodeProcess(pi.hProcess,&code))code=1;CloseHandle(pi.hProcess);return int(code);}
#else
int run_process(const fs::path&exe,const std::vector<string>&args){pid_t pid=fork();if(pid<0)throw std::runtime_error("fork failed");if(pid==0){std::vector<string>a{exe.string()};for(auto&s:args)a.push_back(s);std::vector<char*> argv;for(auto&v:a)argv.push_back(v.data());argv.push_back(nullptr);execv(exe.c_str(),argv.data());std::cerr<<"execv error: "<<strerror(errno)<<"\n";_exit(127);}int st=0;while(waitpid(pid,&st,0)<0){if(errno==EINTR)continue;throw std::runtime_error("waitpid error");}return WIFEXITED(st)?WEXITSTATUS(st):128;}
#endif
void run(const fs::path&exe,const std::vector<string>&args){std::cout<<"[P09A RUN] "<<exe.filename().string()<<std::endl;int r=run_process(exe,args);if(r)throw std::runtime_error(exe.filename().string()+" exit "+std::to_string(r));}
std::vector<string> csv(const string&line){return split(line);}
struct Result {double j=0,final=0,maxStress=0;int steps=0;};
Result get_result(const fs::path&p,int dt,int tend){std::ifstream f(p);string h,line;if(!f||!std::getline(f,h)||h.find("Psi6")==string::npos)throw std::runtime_error("Bad mechanical history: "+p.string());Result o;double prior=7.5e-7;
 while(std::getline(f,line)){if(line.empty())continue;auto x=csv(line);if(x.size()<8)throw std::runtime_error("Bad mechanical row");double t=std::stod(x[0]),psi=std::stod(x[2]),smax=std::stod(x[4]);if(std::abs(t-(o.steps+1)*dt)>1e-8||!std::isfinite(psi)||psi<0||!std::isfinite(smax))throw std::runtime_error("Invalid mechanical history");o.j+=(prior+psi)*0.5*dt/tend;prior=psi;o.final=psi;o.maxStress=std::max(o.maxStress,smax);++o.steps;}
 if(o.steps!=tend/dt||!std::isfinite(o.j))throw std::runtime_error("Incomplete mechanical history: "+p.string());return o;}
void thermal_check(const fs::path&dir,const fs::path&mesh,int dt,int tend,double xi){std::ifstream f(dir/"summary.csv");string h,line;if(!f||!std::getline(f,h)||!std::getline(f,line)||h.find("t_end_s")==string::npos)throw std::runtime_error("Missing thermal summary");auto a=csv(line);if(a.size()<16||a[0]!=mesh.filename().string())throw std::runtime_error("Thermal mesh name mismatch");
 auto eq=[](double x,double y){return std::abs(x-y)<=1e-10*std::max({1.,std::abs(x),std::abs(y)});};
 if(!eq(std::stod(a[4]),dt)||!eq(std::stod(a[5]),tend)||!eq(std::stod(a[6]),xi))throw std::runtime_error("Thermal settings mismatch");
 std::ifstream ts(dir/"time_series.csv");if(!ts||!std::getline(ts,line)||line.find("xi")==string::npos)throw std::runtime_error("Thermal time history missing");int k=0;while(std::getline(ts,line)){if(line.empty())continue;auto v=csv(line);++k;if(v.size()<21||!eq(std::stod(v[0]),k*dt)||!eq(std::stod(v[1]),xi))throw std::runtime_error("Thermal step mismatch");}
 if(k!=tend/dt)throw std::runtime_error("Incomplete thermal time history");for(int t=dt;t<=tend;t+=dt)if(!fs::is_regular_file(dir/("thermal_"+std::to_string(t)+"s.vtu")))throw std::runtime_error("Thermal VTU missing");}
string times(int dt,int tend){string s;for(int t=dt;t<=tend;t+=dt){if(!s.empty())s+=',';s+=std::to_string(t);}return s;}
void test_material(){namespace m=ice3d::ed;using ice3d::edv::State;using ice3d::edv::Controls;using ice3d::edv::update;
 const double Tr=m::T_ref;double v=m::modulus(Tr,m::Modulus::VAR),c=m::modulus(Tr,m::Modulus::CONST);
 if(std::abs(v-c)>1e-3)throw std::runtime_error("CONST != VAR at reference temperature");
 for(double T:{243.15,253.15,263.15,273.15}){double E=m::modulus(T,m::Modulus::VAR), expected=m::E_ref*(8.93-0.012*(T-273.15))/9.17;
 if(std::abs(E-expected)>1e-6||E<=0)throw std::runtime_error("Relative E(T) law mismatch");double h=1e-3;double fd=(m::modulus(T+h,m::Modulus::VAR)-m::modulus(T-h,m::Modulus::VAR))/(2*h);if(std::abs(fd-m::dmodulus(m::Modulus::VAR))>1)throw std::runtime_error("Temperature slope mismatch");}
 m::Tensor e{{1.e-4,-2.e-5,-8.e-5,2.e-5,1.e-5,-1.e-5}};State prev{};
 for(auto law:{string("E"),string("ED"),string("EDV")})for(auto mode:{m::Modulus::CONST,m::Modulus::VAR}){
 Controls flags{law!="E",law=="EDV"};auto a=update(e,252.2,150.,prev,mode,flags);
 for(int j=0;j<6;++j){auto p=e,n=e;double h=1e-8;p[j]+=h;n[j]-=h;auto x=update(p,252.2,150.,prev,mode,flags),y=update(n,252.2,150.,prev,mode,flags);
 for(int i=0;i<6;++i){double fd=(x.sigma[i]-y.sigma[i])/(2*h), ref=a.tangent[i][j];if(std::abs(fd-ref)>5e-4*std::max(1.,std::abs(ref)))throw std::runtime_error("Stress/strain tangent mismatch: "+law);}}
 double dT=1e-4;auto x=update(e,252.2+dT,150.,prev,mode,flags),y=update(e,252.2-dT,150.,prev,mode,flags);
 for(int i=0;i<6;++i){double fd=(x.sigma[i]-y.sigma[i])/(2*dT);if(std::abs(fd-a.d_sigma_dT[i])>1e-3*std::max(1.,std::abs(a.d_sigma_dT[i])))throw std::runtime_error("Stress/temperature tangent mismatch: "+law);}
 }
 double sum=std::accumulate(GH3_W.begin(),GH3_W.end(),0.);if(std::abs(sum-1)>1e-14)throw std::runtime_error("GH3 normalization");std::cout<<"P09A_SELFTEST_OK: E(T), 6 constitutive tangents dSigma/deps and dSigma/dT, GH3\n";}
struct Node {string name;double xi,weight;};
std::vector<Node> nodes(const Config&c){return c.quadrature=="ZERO"?std::vector<Node>{{"xi0",0,1}}:std::vector<Node>{{"gh_m",GH3_X[0],GH3_W[0]},{"gh_0",0,GH3_W[1]},{"gh_p",GH3_X[2],GH3_W[2]}};}
void execute(const Config&c,const fs::path&self){const auto laws=choices(c.laws,"law"),moduli=choices(c.moduli,"mod");
 const fs::path mesh=c.root/"meshes"/(c.mesh+".msh"),thermal=sibling(self,"stage3d02_thermal"),mechanics=sibling(self,"stage3d06_spatial");for(const auto&p:{mesh,thermal,mechanics})if(!fs::is_regular_file(p))throw std::runtime_error("Missing prerequisite: "+p.string());
 string models=c.laws;for(char&ch:models)if(ch==',')ch='-';
 string evars=c.moduli;for(char&ch:evars)if(ch==',')ch='-';
 string folder=c.mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.quad)+"_t"+std::to_string(c.tend)+"_"+c.quadrature+"_laws"+models+"_E"+evars;
 auto base=c.root/"LOCAL_RUNS"/"MODEL_STAGE09"/"P09A"/folder;
 string sig="P09A_v1\nmesh_hash="+std::to_string(fnv(mesh))+"\nmesh="+c.mesh+"\ndt="+std::to_string(c.dt)+"\ntend="+std::to_string(c.tend)+"\nquad="+std::to_string(c.quad)+"\nxi_set="+c.quadrature+"\nlaws="+c.laws+"\nmoduli="+c.moduli+"\n";
 std::cout<<"P09A comparison output: "<<base<<"\n";
 if(c.dry){std::cout<<"P09A_DRY_RUN_OK: no files changed\n";return;}
 if(c.report&&!fs::is_regular_file(base/"P09A_GUARD.txt"))throw std::runtime_error("No completed project to report");guard(base,sig);
 if(!c.report)write(base/"P09A_STATUS.txt","status=RUNNING\n");
 std::ostringstream raw,agg,effects;raw<<std::setprecision(17);agg<<std::setprecision(17);effects<<std::setprecision(17);
 raw<<"mesh,dt_s,tend_s,xi,weight,law,modulus,j6,Psi6_final,max_sigma1_MPa,steps,source\n";
 agg<<"mesh,dt_s,tend_s,law,modulus,mean_j6,variance_j6,xi0_j6,xi_nodes\n";
 effects<<"law,mean_CONST,mean_VAR,relative_VAR_vs_CONST_pct,variance_CONST,variance_VAR,relative_var_change_pct\n";
 struct Acc {string law,mod;double mean=0,variance=0,xi0=std::numeric_limits<double>::quiet_NaN();std::vector<double> vals;};std::vector<Acc> as;
 for(const auto&law:laws)for(const auto&mod:moduli)as.push_back({law,mod});
 const auto xx=nodes(c);
 for(const auto&nd:xx){auto dir=base/nd.name;string nodeSig=sig+"xi="+as_string(nd.xi)+"\n";
 if(c.report&&!fs::is_regular_file(dir/"P09A_GUARD.txt"))throw std::runtime_error("Missing node guard");guard(dir,nodeSig);
 auto td=dir/"thermal";bool tvalid=false;try{thermal_check(td,mesh,c.dt,c.tend,nd.xi);tvalid=true;}catch(const std::exception&){}
 if(!tvalid){if(c.report)throw std::runtime_error("Missing thermal results");if(fs::exists(td)&&!fs::is_empty(td))throw std::runtime_error("Partial thermal results: "+td.string());
 run(thermal,{"--mesh",mesh.string(),"--out",td.string(),"--dt",std::to_string(c.dt),"--tend",std::to_string(c.tend),"--xi",as_string(nd.xi),"--every-step"});thermal_check(td,mesh,c.dt,c.tend,nd.xi);}else std::cout<<"[REUSE] complete thermal node "<<nd.name<<"\n";
 for(auto&v:as){auto md=dir/"mechanics";auto dest=md/(v.law+"_"+v.mod);Result r;bool mvalid=false;
 try{r=get_result(dest/"time_series.csv",c.dt,c.tend);mvalid=fs::is_regular_file(dest/"restart.bin");}catch(const std::exception&){}
 if(!mvalid){if(c.report)throw std::runtime_error("Missing model data: "+dest.string());run(mechanics,{"--mesh",mesh.string(),"--temp-dir",td.string(),"--out",md.string(),"--law",v.law,"--modulus",v.mod,"--times",times(c.dt,c.tend),"--quad",std::to_string(c.quad),"--cg-tol","2e-8","--preconditioner","jacobi","--optimization","on","--spmv","projected","--parallel-assembly","on","--threads",std::to_string(c.threads),"--resume","--final-vtu-only"});
 r=get_result(dest/"time_series.csv",c.dt,c.tend);if(!fs::is_regular_file(dest/"restart.bin"))throw std::runtime_error("No checkpoint: "+dest.string());}
 else std::cout<<"[REUSE] "<<nd.name<<" "<<v.law<<"_"<<v.mod<<"\n";
 v.mean+=nd.weight*r.j;v.vals.push_back(r.j);if(nd.xi==0)v.xi0=r.j;
 raw<<c.mesh<<','<<c.dt<<','<<c.tend<<','<<nd.xi<<','<<nd.weight<<','<<v.law<<','<<v.mod<<','<<r.j<<','<<r.final<<','<<r.maxStress<<','<<r.steps<<","<<(mvalid?"REUSED_LOCAL":"LOCAL_FEM")<<"\n";
 if(!c.report)write(base/"P09A_SCENARIOS.csv",raw.str());
 }
 }
 for(auto&v:as){for(size_t k=0;k<xx.size();++k)v.variance+=xx[k].weight*std::pow(v.vals[k]-v.mean,2);
 agg<<c.mesh<<','<<c.dt<<','<<c.tend<<','<<v.law<<','<<v.mod<<','<<v.mean<<','<<v.variance<<','<<v.xi0<<','<<xx.size()<<'\n';}
 for(const auto&law:laws){auto con=std::find_if(as.begin(),as.end(),[&](const Acc&a){return a.law==law&&a.mod=="CONST";});auto var=std::find_if(as.begin(),as.end(),[&](const Acc&a){return a.law==law&&a.mod=="VAR";});if(con==as.end()||var==as.end())continue;
 double dm=con->mean!=0?100*(var->mean-con->mean)/std::abs(con->mean):std::numeric_limits<double>::quiet_NaN();double dv=con->variance!=0?100*(var->variance-con->variance)/std::abs(con->variance):std::numeric_limits<double>::quiet_NaN();
 effects<<law<<','<<con->mean<<','<<var->mean<<','<<dm<<','<<con->variance<<','<<var->variance<<','<<dv<<'\n';}
 if(!c.report){write(base/"P09A_COMPARISON.csv",agg.str());write(base/"P09A_MODULUS_EFFECT.csv",effects.str());
 write(base/"P09A_STATUS.txt","status=SUCCESS\nmesh="+c.mesh+"\nxi_set="+c.quadrature+"\nmodels="+std::to_string(as.size())+"\nnode_trajectories="+std::to_string(as.size()*xx.size())+"\ndt="+std::to_string(c.dt)+"\ntend="+std::to_string(c.tend)+"\n");}
 std::cout<<"P09A_SUCCESS; scenarios="<<as.size()*xx.size()<<"; output "<<base<<"\n";
}
}
int main(int argc,char**argv){try{auto c=parse(argc,argv);if(c.test){test_material();return 0;}execute(c,fs::absolute(fs::path(argv[0])));return 0;}catch(const std::exception&e){std::cerr<<"P09A_ERROR: "<<e.what()<<"\n";return 2;}}
