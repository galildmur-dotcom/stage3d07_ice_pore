// Stage 3D-08C: read-only audit of central difference derivatives for eight shape modes.
// No FEM solve, no assumptions that discretely symmetric modes are exactly zero.
#include "qt_runner_paths.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
namespace {
constexpr std::array<const char*,8> names={"tx","ty","tz","y20","y21c","y21s","y22c","y22s"};
struct Opt {fs::path root,out;std::string mesh="H0";int dt=300,tend=3600,quad=3;double cutoff=5.;};
std::string label(double n){std::ostringstream s;s<<std::fixed<<std::setprecision(3)<<n;auto t=s.str();std::replace(t.begin(),t.end(),'.','p');return t;}
Opt parse(int argc,char**argv){Opt o;
 for(int i=1;i<argc;++i){std::string a=argv[i];auto val=[&](){if(i+1>=argc)throw std::runtime_error("Missing "+a);return std::string(argv[++i]);};
  if(a=="--root")o.root=val();else if(a=="--out")o.out=val();else if(a=="--mesh")o.mesh=val();
  else if(a=="--dt")o.dt=std::stoi(val());else if(a=="--tend")o.tend=std::stoi(val());
  else if(a=="--quad")o.quad=std::stoi(val());else if(a=="--cutoff-mm")o.cutoff=std::stod(val());
  else if(a=="--help"){std::cout<<"Stage3D08C report: --mesh H0 --dt 300 --tend 3600 --quad 3 --cutoff-mm 5 [--root DIRECTORY] [--out DIRECTORY]. READ ONLY FEM outputs.\n";std::exit(0);}
  else throw std::runtime_error("Unknown argument: "+a);
 }
 if(o.mesh!="H0"&&o.mesh!="H1"&&o.mesh!="H2"&&o.mesh!="H3"&&o.mesh!="H4")throw std::runtime_error("Bad mesh");
 if(o.dt<=0||o.tend<=0||o.tend%o.dt||!(o.quad==3||o.quad==4)||!std::isfinite(o.cutoff)||o.cutoff<=3||o.cutoff>=5.5)throw std::runtime_error("Bad parameters");
 if(o.root.empty())o.root=fs::path(STAGE3D06_ROOT_DIR)/"LOCAL_RUNS"/"SHAPE_STAGE08"/"P08C"/(o.mesh+"_dt"+std::to_string(o.dt)+"_q"+std::to_string(o.quad)+"_t"+std::to_string(o.tend)+"_EDV_VAR_XI0_cutoff"+label(o.cutoff)+"mm");
 if(o.out.empty())o.out=o.root/"P08C_REPORT";
 return o;
}
std::string trim(std::string s){while(!s.empty()&&(s.back()=='\r'||s.back()=='\n'||s.back()==' '))s.pop_back();return s;}
std::vector<std::string> split(const std::string&s){std::vector<std::string>r;std::string x;std::istringstream in(s);while(std::getline(in,x,','))r.push_back(trim(x));return r;}
std::map<std::string,std::string> read_status(const fs::path&path){std::ifstream f(path);if(!f)throw std::runtime_error("Missing status");
 std::map<std::string,std::string> a;std::string line;while(std::getline(f,line)){auto k=line.find('=');if(k!=std::string::npos)a.emplace(trim(line.substr(0,k)),trim(line.substr(k+1)));}return a;}
struct Measure {double delta=0,plus=0,minus=0,D=0,normalized=0,phi_plus=0,phi_minus=0,volume_D=0;};
struct Mode {std::string name,status="MISSING",reason="no files";std::vector<Measure> data;bool complete=false;};
std::string field(const std::map<std::string,std::string>& m,const std::string& name){auto it=m.find(name);return it==m.end()?std::string():it->second;}
double num(const std::string&s){size_t p=0;const double v=std::stod(s,&p);if(p!=s.size()||!std::isfinite(v))throw std::runtime_error("Invalid finite number: "+s);return v;}
void approx(double x,double y,double tol,const std::string& m){if(std::fabs(x-y)>tol*std::max({1.,std::fabs(x),std::fabs(y)}))throw std::runtime_error(m);}
Mode read_mode(const Opt&o,const std::string& name){Mode m;m.name=name;
 const auto dir=o.root/name;
 if(!fs::is_regular_file(dir/"P08C_MODE_GUARD.txt"))return m;
 m.status="PARTIAL";m.reason="incomplete mode result";
 try {
  auto st=read_status(dir/"P08C_MODE_STATUS.txt");
  if(field(st,"status")!="SUCCESS"||field(st,"mode")!=name||field(st,"mesh")!=o.mesh||
     field(st,"dt")!=std::to_string(o.dt)||field(st,"tend")!=std::to_string(o.tend))throw std::runtime_error("Mode status mismatch");
  std::ifstream in(dir/"P08C_MODE_FD.csv");if(!in)throw std::runtime_error("Missing mode CSV");
  std::string line;if(!std::getline(in,line))throw std::runtime_error("Missing mode header");
  if(trim(line)!="mode,mesh,dt_s,tend_s,quad,delta_um,j6_plus,j6_minus,D_j6_per_m,normalized_by_j6_over_R,Phi6_final_plus,Phi6_final_minus,steps_verified")throw std::runtime_error("Unexpected mode CSV header");
  while(std::getline(in,line)){if(trim(line).empty())continue;auto c=split(line);if(c.size()!=13)throw std::runtime_error("Wrong number of columns");
   if(c[0]!=name||c[1]!=o.mesh||num(c[2])!=o.dt||num(c[3])!=o.tend||num(c[4])!=o.quad||num(c[12])!=o.tend/o.dt)throw std::runtime_error("Wrong mode settings");
   Measure a;a.delta=num(c[5]);a.plus=num(c[6]);a.minus=num(c[7]);a.D=num(c[8]);a.normalized=num(c[9]);a.phi_plus=num(c[10]);a.phi_minus=num(c[11]);
   if(a.delta<=0||a.delta>20||a.plus<=0||a.minus<=0)throw std::runtime_error("Invalid delta or functional");
   const auto expected=(a.plus-a.minus)/(2*a.delta*1e-6);
   if(std::abs(a.D-expected)>1e-8*std::max(1.,std::abs(expected)))throw std::runtime_error("Finite difference identity failed");
   const auto norm=.001*expected/(.5*(a.plus+a.minus));
   if(std::abs(a.normalized-norm)>1e-8*std::max(1.,std::abs(norm)))throw std::runtime_error("Relative derivative identity failed");
   for(const auto& b:m.data)if(std::abs(a.delta-b.delta)<1e-10)throw std::runtime_error("Duplicate delta");
   m.data.push_back(a);
  }
  if(m.data.size()!=2)throw std::runtime_error("Need both 5 and 2.5 um amplitudes");
  std::sort(m.data.begin(),m.data.end(),[](const auto&a,const auto&b){return a.delta>b.delta;});
  if(std::fabs(m.data[0].delta-5)>1e-9||std::fabs(m.data[1].delta-2.5)>1e-9)throw std::runtime_error("Expected 5 and 2.5 um");
  const auto geo=dir/"geometry"/"P08_GEOMETRIC_DERIVATIVE.csv";
  std::ifstream g(geo);if(!g||!std::getline(g,line))throw std::runtime_error("Missing geometric volume audit");
  if(trim(line)!="mode,delta_um,dV_ice_damplitude_m2,exact_dV_radial_m2,relative_error_radial,expected_zero_nonradial")throw std::runtime_error("Unexpected geometry header");
  int volumes=0;while(std::getline(g,line)){if(trim(line).empty())continue;auto c=split(line);
    if(c.size()!=6||c[0]!=name)throw std::runtime_error("Unexpected geometry row");
    const auto d=num(c[1]),v=num(c[2]);if(num(c[5])!=1)throw std::runtime_error("Nonradial mode must be zero-volume to first order");
    if(std::fabs(v)>0.02*4*3.14159265358979323846*1e-6)throw std::runtime_error("Geometric first variation of volume too large");
    bool found=false;for(auto& a:m.data)if(std::abs(a.delta-d)<1e-9){a.volume_D=v;found=true;++volumes;}
    if(!found)throw std::runtime_error("Unrecognized geometry delta");
  }
  if(volumes!=2)throw std::runtime_error("Geometric audit needs two amplitudes");
  m.complete=true;m.status="COMPLETE";m.reason="validated central FD and first variation of volume";
 }catch(const std::exception&e){m.complete=false;m.status="INVALID";m.reason=e.what();}
 return m;
}
}
int main(int argc,char**argv){try{
 const auto o=parse(argc,argv);fs::create_directories(o.out);
 std::ofstream cases(o.out/"P08C_CASES.csv",std::ios::trunc),derivs(o.out/"P08C_DERIVATIVES.csv",std::ios::trunc),sym(o.out/"P08C_SYMMETRY.csv",std::ios::trunc);
 if(!cases||!derivs||!sym)throw std::runtime_error("Cannot write reports");
 cases<<"mode,group,status,delta_count,reason\n";
 derivs<<"mode,delta_um,j6_plus,j6_minus,D_j6_per_m,relative_sensitivity,volume_first_variation_m2,Richardson_to_zero,amplitude_change_relative\n";
 sym<<"mode,expected_first_derivative_zero_by_symmetry,reference_D_m_inv,D_at_5um_m_inv,Richardson_m_inv,abs_Richardson_over_reference,comparison_note\n";
 cases<<std::setprecision(17);derivs<<std::setprecision(17);sym<<std::setprecision(17);
 std::vector<Mode> modes;for(const auto*name:names){auto m=read_mode(o,name);cases<<name<<','<<(name[0]=='t'?"translation":"quadrupole")<<','<<m.status<<','<<m.data.size()<<','<<m.reason<<'\n';modes.push_back(std::move(m));}
 // Reference is a diagnostic scale, not a theorem of exact zero.
 double reference=0;for(const auto&m:modes)if(m.complete&&(m.name=="tz"||m.name=="y20"))reference=std::max(reference,std::abs((4*m.data[1].D-m.data[0].D)/3.));
 for(const auto&m:modes){if(!m.complete)continue;
  const auto& a=m.data[0],&b=m.data[1];const double extrap=(4*b.D-a.D)/3.;
  const double rel=(std::abs(b.D-a.D)/std::max({1e-14,std::abs(extrap),std::abs(a.D)}));
  for(const auto&x:m.data)derivs<<m.name<<','<<x.delta<<','<<x.plus<<','<<x.minus<<','<<x.D<<','<<x.normalized<<','<<x.volume_D<<','<<extrap<<','<<rel<<'\n';
  const bool expected_zero=m.name=="tx"||m.name=="ty"||m.name=="y21c"||m.name=="y21s"||m.name=="y22c"||m.name=="y22s";
  const double normalized=reference>0?std::abs(extrap)/reference:-1.;
  sym<<m.name<<','<<(expected_zero?1:0)<<','<<reference<<','<<a.D<<','<<extrap<<','<<normalized<<','
   <<(reference>0?"compare_only_not_a_pass_criterion":"reference_missing")<<'\n';
 }
 int done=0;for(const auto&m:modes)if(m.complete)++done;
 std::ofstream next(o.out/"P08C_NEXT_ACTION_RU.md");next<<"# P08C: status "<<done<<"/8 modes\n\n";
 next<<"Diagnostic only: xi=0, fixed H, dt. Expected zero derivatives are symmetry hypotheses for the continuum; discrete errors, mesh asymmetry and cancellation must be assessed.\n\n";
 if(done<8){next<<"Awaiting:\n";for(const auto&m:modes)if(!m.complete)next<<"- "<<m.name<<" : "<<m.status<<" ("<<m.reason<<")\n";}
 else next<<"All eight modes available. Compare central differences and geometric audits; proceed with selected modes to finer meshes only after review.\n";
 std::cout<<"P08C_REPORT_OK complete="<<done<<"/8 out="<<o.out<<"\n";
 return 0;
 }catch(const std::exception&e){std::cerr<<"P08C_REPORT_ERROR: "<<e.what()<<"\n";return 2;}}
