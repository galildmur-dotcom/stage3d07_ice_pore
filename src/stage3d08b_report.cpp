// Stage3D08B: read-only, provenance-aware spatial/temporal convergence audit
// for central radius finite differences. No thermal/mechanical solve is launched.
#include "qt_runner_paths.hpp"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
namespace {
struct Case {std::string id,mesh;int dt;double cutoff;std::vector<double> expected;};
const std::vector<Case> cases={
 {"H0_300","H0",300,5,{10,5,2.5}},
 {"H0_150","H0",150,5,{5,2.5}},
 {"H1_300","H1",300,5,{5,2.5}},
 {"H1_150","H1",150,5,{5,2.5}},
 {"H2_150","H2",150,5,{5}},
 {"H0_300_cutoff4","H0",300,4,{5}}
};
struct D {double amp,plus,minus,value,relative,phi_plus,phi_minus;int steps;};
struct Result {Case spec;std::string state="MISSING",message;fs::path path;std::map<double,D> data;};
std::string tag(double x){std::ostringstream s;s<<std::fixed<<std::setprecision(3)<<x;auto a=s.str();for(char&c:a)if(c=='.')c='p';return a;}
std::string dir_name(const Case &c){std::string s=c.mesh+"_dt"+std::to_string(c.dt)+"_q3_t3600_EDV_VAR_XI0";
 if(std::fabs(c.cutoff-5)>1e-12)s+="_cutoff"+tag(c.cutoff)+"mm";return s;}
std::string read_text(const fs::path&p){std::ifstream in(p);if(!in)throw std::runtime_error("file missing");return {std::istreambuf_iterator<char>(in),{}};}
std::vector<std::string> split(const std::string&s){std::stringstream ss(s);std::string v;std::vector<std::string> o;while(std::getline(ss,v,',')){while(!v.empty()&&(v.back()=='\r'||v.back()=='\n'||v.back()==' '||v.back()=='\t'))v.pop_back();o.push_back(v);}return o;}
double real(const std::string &x){size_t pos=0;double d=std::stod(x,&pos);if(pos!=x.size()||!std::isfinite(d))throw std::runtime_error("nonfinite/invalid numeric field");return d;}
int integer(const std::string&x){size_t pos=0;auto n=std::stoi(x,&pos);if(pos!=x.size())throw std::runtime_error("invalid integer field");return n;}
bool includes(const std::string&s,const std::string&v){return s.find(v)!=std::string::npos;}
Result load(const fs::path&base,Case spec){Result r;r.spec=std::move(spec);r.path=base/dir_name(r.spec);
 const auto csv=r.path/"P08_J6_RADIUS_FD.csv";
 if(!fs::exists(csv)){r.message="No finite-difference table";return r;}
 try {
  auto status=read_text(r.path/"P08_RUN_STATUS.txt");
  if(!includes(status,"status=SUCCESS"))throw std::runtime_error("P08 status is not SUCCESS");
  if(!includes(status,"mesh="+r.spec.mesh))throw std::runtime_error("status mesh mismatch");
  std::ifstream in(csv);if(!in)throw std::runtime_error("cannot open CSV");
  std::string header;if(!std::getline(in,header)||!includes(header,"D_R_j6_per_m"))throw std::runtime_error("wrong CSV header");
  std::string line;
  while(std::getline(in,line)){
   if(line.empty())continue;auto x=split(line);if(x.size()!=12)throw std::runtime_error("CSV requires 12 columns");
   if(x[0]!=r.spec.mesh||integer(x[1])!=r.spec.dt||integer(x[2])!=3600||integer(x[3])!=3)throw std::runtime_error("mesh/dt/horizon/quadrature mismatch");
   D v{real(x[4]),real(x[5]),real(x[6]),real(x[7]),real(x[8]),real(x[9]),real(x[10]),integer(x[11])};
   if(v.steps!=3600/r.spec.dt||v.amp<=0||v.amp>20)throw std::runtime_error("step count or amplitude mismatch");
   auto check=(v.plus-v.minus)/(2*v.amp*1e-6);
   if(std::fabs(check-v.value)>1e-9*std::max(1.,std::fabs(check)))throw std::runtime_error("finite-difference arithmetic inconsistent");
   if(std::fabs(v.relative-(.001*v.value/(.5*(v.plus+v.minus))))>1e-9)throw std::runtime_error("normalized sensitivity inconsistent");
   if(!r.data.emplace(v.amp,v).second)throw std::runtime_error("duplicate perturbation amplitude");
  }
  bool all=!r.data.empty();for(double e:r.spec.expected)all=all&&r.data.count(e);
  // Never classify a table with foreign/extra amplitudes as a completed preset.
  if(r.data.size()>r.spec.expected.size())throw std::runtime_error("unexpected amplitudes in table");
  for(const auto& [amp,_]:r.data)if(std::find(r.spec.expected.begin(),r.spec.expected.end(),amp)==r.spec.expected.end())throw std::runtime_error("unexpected amplitude");
  r.state=all?"COMPLETE":"PARTIAL";r.message=all?"All prescribed pairs validated":"Some prescribed delta pairs missing";
 }catch(const std::exception&e){r.state="INVALID";r.message=e.what();r.data.clear();}
 return r;
}
std::string escape(const std::string &s){std::string x=s;for(char&c:x)if(c==','||c=='\r'||c=='\n')c=' ';return x;}
std::string nv(double v){if(!std::isfinite(v))return "";std::ostringstream s;s<<std::setprecision(16)<<v;return s.str();}
void write(const fs::path&p,const std::string&s){std::ofstream o(p);if(!o)throw std::runtime_error("cannot write "+p.string());o<<s;}
}
int main(int argc,char**argv){try{
 fs::path root(STAGE3D06_ROOT_DIR);bool dry=false;
 for(int i=1;i<argc;++i){std::string a=argv[i];if(a=="--help"){std::cout<<"Stage3D08B report: [--root PROJECT_DIR] [--dry-run] (no FEM computation)\n";return 0;}
 else if(a=="--root"&&i+1<argc)root=argv[++i];else if(a=="--dry-run")dry=true;else throw std::runtime_error("unknown argument "+a);}
 const fs::path base=root/"LOCAL_RUNS"/"SHAPE_STAGE08";std::vector<Result> all;
 for(auto c:cases)all.push_back(load(base,c));
 if(dry){for(const auto&r:all)std::cout<<r.spec.id<<' '<<r.state<<' '<<r.message<<'\n';return 0;}
 const auto out=base/"P08B";fs::create_directories(out);
 std::ostringstream states,derivs,compare,rich,actions;
 states<<"case,mesh,dt_s,tend_s,quad,cutoff_mm,expected_amplitudes,available_amplitudes,state,message,folder\n";
 derivs<<"case,mesh,dt_s,tend_s,quad,cutoff_mm,delta_um,j6_plus,j6_minus,D_R_j6_per_m,relative_radius_sensitivity,steps_verified\n";
 rich<<"case,mesh,dt_s,cutoff_mm,D_5um,D_2p5um,Richardson_O_delta2,estimated_delta_truncation,Richardson_available\n";
 compare<<"comparison,reference_case,target_case,delta_um,reference_D,target_D,difference,target_minus_reference_percent,status\n";
 std::map<std::string,Result> byid;
 for(const auto&r:all){byid.emplace(r.spec.id,r);
  states<<r.spec.id<<','<<r.spec.mesh<<','<<r.spec.dt<<",3600,3,"<<r.spec.cutoff<<',';
  for(size_t i=0;i<r.spec.expected.size();++i){if(i)states<<'|';states<<r.spec.expected[i];}
  states<<',';bool first=true;for(const auto&[amp,d]:r.data){if(!first)states<<'|';first=false;states<<amp;
   derivs<<r.spec.id<<','<<r.spec.mesh<<','<<r.spec.dt<<",3600,3,"<<r.spec.cutoff<<','<<nv(amp)<<','<<nv(d.plus)<<','<<nv(d.minus)<<','<<nv(d.value)<<','<<nv(d.relative)<<','<<d.steps<<'\n';}
  states<<','<<r.state<<','<<escape(r.message)<<','<<r.path.generic_string()<<'\n';
  const auto a=r.data.find(5),b=r.data.find(2.5);
  rich<<r.spec.id<<','<<r.spec.mesh<<','<<r.spec.dt<<','<<r.spec.cutoff<<',';
  if(a!=r.data.end()&&b!=r.data.end()){
   auto d=(4*b->second.value-a->second.value)/3;
   rich<<nv(a->second.value)<<','<<nv(b->second.value)<<','<<nv(d)<<','<<nv(std::fabs(d-b->second.value))<<",YES\n";
  }else{if(a!=r.data.end())rich<<nv(a->second.value);rich<<",,,,NO\n";}
 }
 // Comparisons are meaningful only at identical delta, model, xi, quadrature and horizon.
 struct Comp {std::string title,left,right;double delta;};
 std::vector<Comp> comparisons={
  {"temporal_H0_300_to_150_d5","H0_300","H0_150",5},
  {"temporal_H0_300_to_150_d2p5","H0_300","H0_150",2.5},
  {"spatial_H0_to_H1_dt300_d5","H0_300","H1_300",5},
  {"spatial_H0_to_H1_dt300_d2p5","H0_300","H1_300",2.5},
  {"spatial_H0_to_H1_dt150_d5","H0_150","H1_150",5},
  {"spatial_H0_to_H1_dt150_d2p5","H0_150","H1_150",2.5},
  {"temporal_H1_300_to_150_d5","H1_300","H1_150",5},
  {"temporal_H1_300_to_150_d2p5","H1_300","H1_150",2.5},
  {"spatial_H1_to_H2_dt150_d5","H1_150","H2_150",5},
  {"extension_cutoff5_to_4_H0_dt300_d5","H0_300","H0_300_cutoff4",5},
 };
 for(const auto&c:comparisons){const auto &a=byid.at(c.left),&b=byid.at(c.right);
  compare<<c.title<<','<<c.left<<','<<c.right<<','<<c.delta<<',';
  if(a.data.count(c.delta)&&b.data.count(c.delta)){
   auto x=a.data.at(c.delta).value,y=b.data.at(c.delta).value;
   compare<<nv(x)<<','<<nv(y)<<','<<nv(y-x)<<','<<(x==0?"":nv(100*(y-x)/x))<<",READY\n";
  }else compare<<",,,,WAITING\n";
 }
 actions<<"# Stage 3D-08B — текущая готовность кампании\n\n"
       <<"Отчёт только читает готовые P08_J6_RADIUS_FD.csv и P08_RUN_STATUS.txt; не запускает решатели.\n\n";
 bool any=false;
 for(const auto&r:all)if(r.state!="COMPLETE"){
  any=true;actions<<"- "<<r.spec.id<<": "<<r.state<<" — "<<r.message<<".\n";
 }
 if(!any)actions<<"Все шесть сценариев готовы; можно анализировать согласованность сетки, времени и способа продолжения.\n";
 actions<<"\nВажно: H0/300 считается готовым только при наличии локальной таблицы и SUCCESS; никаких контрольных Linux/Windows чисел автоматически не подставляется.\n"
 <<"Сравнивайте прежде всего одинаковые δR=5 мкм, а экстраполяцию по δ используйте как дополнительную оценку.\n"
 <<"Это проверка дискретной производной при ξ=0, не GH3 и не доказательство непрерывной shape-производной.\n";
 write(out/"P08B_CASES.csv",states.str());write(out/"P08B_DERIVATIVES.csv",derivs.str());
 write(out/"P08B_RICHARDSON.csv",rich.str());write(out/"P08B_COMPARISON.csv",compare.str());
 write(out/"P08B_NEXT_ACTION_RU.md",actions.str());
 std::cout<<"P08B_REPORT_OK: "<<out<<'\n';for(const auto&r:all)std::cout<<"  "<<r.spec.id<<" "<<r.state<<'\n';return 0;
 }catch(const std::exception&e){std::cerr<<"P08B_REPORT_ERROR: "<<e.what()<<'\n';return 2;}}
