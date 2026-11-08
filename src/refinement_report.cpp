// Stage3D06 convergence statistics from saved CSV. No Python requirement.
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
#include <string>
#include <vector>
namespace fs=std::filesystem;
struct Point{double t=0,p6=0,pO=0,smax=0;};
struct Result{std::string mesh,law,mod;int dt=0,q=0,n=0;double j6=0,jO=0,phi6=0,smax=0,top=-1,bottom=-1,wall=0;bool complete=false;};
static std::vector<std::string> split(const std::string&s){std::istringstream in(s);std::string t;std::vector<std::string>v;while(std::getline(in,t,','))v.push_back(t);return v;}
static std::map<double,Point> read(const fs::path&file){
 std::ifstream f(file);std::string line;std::map<double,Point>v;if(!std::getline(f,line))return v;
 while(std::getline(f,line))try{auto x=split(line);if(x.size()<9)continue;
  Point p;p.t=std::stod(x[0]);p.p6=std::stod(x[2]);p.pO=std::stod(x[3]);p.smax=std::stod(x[4]);if(!std::isfinite(p.p6)||!std::isfinite(p.pO)||!std::isfinite(p.smax))continue;v[p.t]=p;
 }catch(...){continue;}return v;
}
static bool integrate(const std::map<double,Point>&samples,int dt,Result&r){
 constexpr double initialPsi=7.5e-7;const int count=3600/dt;
 if(samples.size()!=size_t(count))return false;
 double lastT=0,last6=initialPsi,lastO=initialPsi;
 for(int i=1;i<=count;++i){auto it=samples.find(double(i*dt));if(it==samples.end())return false;
  const Point p=it->second;
  r.j6+=(last6+p.p6)*.5*(p.t-lastT)/3600.;r.jO+=(lastO+p.pO)*.5*(p.t-lastT)/3600.;
  lastT=p.t;last6=p.p6;lastO=p.pO;
 }
 r.phi6=last6;r.smax=samples.rbegin()->second.smax;r.n=count;r.complete=true;return true;
}
static void polar(const fs::path&p,Result&r){std::ifstream f(p);std::string row,last;std::getline(f,row);while(std::getline(f,row))if(!row.empty())last=row;
 if(last.empty())return;try{auto z=split(last);if(z.size()>=5){r.top=std::stod(z[1]);r.bottom=std::stod(z[2]);}}catch(...){}
}
static double pct(double a,double b){return b!=0?100.0*(a-b)/std::abs(b):0;}
int main(){
 try {
 auto root=fs::path(STAGE3D06_ROOT_DIR), base=root/"LOCAL_RUNS";
 auto dir=base/"REFINEMENT_CAMPAIGN";fs::create_directories(dir);
 std::vector<Result>data;
 for(const std::string m:{"H0","H1","H2","H3","H4"})for(int dt:{300,150,75,25})for(int quad:{3,4})
 for(const std::string mod:{"VAR","CONST"}){
  auto where=base/(m+"_dt"+std::to_string(dt)+"_q"+std::to_string(quad))/"mechanics"/("EDV_"+mod);
  auto samples=read(where/"time_series.csv");if(samples.empty())continue;
  Result r;r.mesh=m;r.law="EDV";r.mod=mod;r.dt=dt;r.q=quad;
  if(!integrate(samples,dt,r))continue;polar(where/"polar_caps_history.csv",r);data.push_back(r);
 }
 std::sort(data.begin(),data.end(),[](const Result&a,const Result&b){if(a.mesh!=b.mesh)return a.mesh<b.mesh;if(a.q!=b.q)return a.q<b.q;if(a.mod!=b.mod)return a.mod<b.mod;return a.dt>b.dt;});
 std::ofstream table(dir/"CONVERGENCE_TABLE.csv");table<<std::setprecision(14)<<"mesh,law,modulus,dt_s,quadrature,n_steps,j6,jOmega,Phi6_3600,QP_sigma1_max_MPa,top_polar_cap_mean_MPa,bottom_polar_cap_mean_MPa\n";
 for(const auto&r:data)table<<r.mesh<<','<<r.law<<','<<r.mod<<','<<r.dt<<','<<r.q<<','<<r.n<<','<<r.j6<<','<<r.jO<<','<<r.phi6<<','<<r.smax<<','<<r.top<<','<<r.bottom<<'\n';
 std::ofstream pair(dir/"CONVERGENCE_PAIRS.csv");pair<<"comparison,mesh_a,mesh_b,dt_a,dt_b,quadrature_a,quadrature_b,mod_a,mod_b,j6_diff_percent,smax_diff_percent,top_cap_diff_percent,bottom_cap_diff_percent\n";
 auto writepair=[&](const std::string&name,const Result&a,const Result&b){pair<<std::setprecision(12)<<name<<','<<a.mesh<<','<<b.mesh<<','<<a.dt<<','<<b.dt<<','<<a.q<<','<<b.q<<','<<a.mod<<','<<b.mod<<','<<pct(a.j6,b.j6)<<','<<pct(a.smax,b.smax)<<','<<(a.top>=0&&b.top>=0?std::to_string(pct(a.top,b.top)):"NA")<<','<<(a.bottom>=0&&b.bottom>=0?std::to_string(pct(a.bottom,b.bottom)):"NA")<<'\n';};
 for(const auto&a:data)for(const auto&b:data){
  if(&a==&b)continue;
  if(a.mesh==b.mesh&&a.q==b.q&&a.mod==b.mod&&a.dt<b.dt)writepair("time_refinement",a,b);
  if(a.dt==b.dt&&a.q==b.q&&a.mod==b.mod&&a.mesh>b.mesh)writepair("mesh_refinement",a,b);
  if(a.mesh==b.mesh&&a.dt==b.dt&&a.mod==b.mod&&a.q>b.q)writepair("quadrature",a,b);
  if(a.mesh==b.mesh&&a.dt==b.dt&&a.q==b.q&&a.mod=="VAR"&&b.mod=="CONST")writepair("E_T_sensitivity",a,b);
 }
 std::ofstream md(dir/"CONVERGENCE_STATUS_RU.md");
 md<<"# Кампания Stage 3D-06: текущий статус сходимости\n\n";
 md<<"Испытано законченных сценариев: **"<<data.size()<<"**. Это автоматически найденные полные временные истории; незавершённые сценарии исключены.\n\n";
 md<<"Определения: j6 = (1/3600) integral_0^3600 Phi6 dt, составная трапеция; Phi6(0)=7.5e-7 — гладкая нормировка при нулевых напряжениях.\n\n";
 md<<"| Сетка | dt, с | Q | E | j6 | sigma1_QP max, MPa | top cap, MPa | bottom cap, MPa |\n|---|---:|---:|---|---:|---:|---:|---:|\n";
 md<<std::setprecision(8);
 for(auto&r:data)md<<"| "<<r.mesh<<" | "<<r.dt<<" | "<<r.q<<" | "<<r.mod<<" | "<<r.j6<<" | "<<r.smax<<" | "<<r.top<<" | "<<r.bottom<<" |\n";
 md<<"\n**Важно:** достижение сеточной и временной сходимости этим скриптом автоматически НЕ утверждается."
      <<" Нужны устойчивость наблюдаемых при уточнении по обеим осям, анализ начального переходного процесса и независимая проверка температурного/материального алгоритма.\n"
      <<"\nПодробные попарные различия — CONVERGENCE_PAIRS.csv; значения точечных максимумов не являются аналитическим пределом напряжений на гладкой сфере.\n";
 std::cout<<"CONVERGENCE REPORT: "<<data.size()<<" complete scenarios.\n"<<(dir/"CONVERGENCE_TABLE.csv")<<"\n"<<(dir/"CONVERGENCE_PAIRS.csv")<<"\n";return 0;
 }catch(const std::exception&e){std::cerr<<"Report failed: "<<e.what()<<"\n";return 2;}
}
