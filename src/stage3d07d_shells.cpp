// Stage3D07D - read-only stress reconstruction and comparable fixed-geometry observation zones.
// Uses exactly the established Tet10, ED/EDV checkpoint layout and constitutive update.
#define STAGE3D07D_LIBRARY
#include "spatial_reology.cpp"
#include "qt_runner_paths.hpp"
#include <iomanip>
#include <optional>
#include <map>

namespace p07d {
constexpr V pore{0.,0.,.03};
constexpr double cos25=0.9063077870366499;
constexpr double sin25=0.42261826174069944;
struct ZoneSpec {const char* kind;double inner_um,outer_um;};
constexpr std::array<ZoneSpec,12> zones{{
 {"BAND",0,10},{"BAND",10,25},{"BAND",25,50},{"BAND",50,100},
 {"BAND",100,200},{"BAND",200,300},{"BAND",300,500},
 {"CUMULATIVE",0,50},{"CUMULATIVE",0,100},{"CUMULATIVE",0,200},
 {"CUMULATIVE",0,300},{"CUMULATIVE",0,500}
}};
constexpr std::array<const char*,4> regions{{"ALL","TOP25","BOTTOM25","EQUATOR25"}};
struct Stats {
 double v=0,s1=0,pos=0,s1sq=0,maximum=-std::numeric_limits<double>::infinity();
 uint64_t count=0;
 std::vector<std::pair<double,double>> distribution;
 void add(double s,double dv){
  if(!(dv>0) || !std::isfinite(s))throw std::runtime_error("P07D invalid QP weight or stress");
  v+=dv;s1+=dv*s;pos+=dv*std::max(0.,s);s1sq+=dv*s*s;
  maximum=std::max(maximum,s);++count;distribution.emplace_back(s,dv);
 }
 double quantile(double frac){
  if(!count)return std::numeric_limits<double>::quiet_NaN();
  std::sort(distribution.begin(),distribution.end(),[](auto a,auto b){return a.first<b.first;});
  double w=0;for(const auto& [x,dv]:distribution){w+=dv;if(w>=frac*v)return x;}
  return distribution.back().first;
 }
};
#ifdef STAGE3D07E_SMOOTH
// P07E: compact C1 mollified observation weights. These weights do NOT alter
// the original finite-element fields, material update, or P07D results.
constexpr std::array<double,3> widths_um{{2.,5.,10.}};
constexpr double angular_transition_cos=0.01; // half-width in cos(theta)
constexpr double pi_p07e=3.14159265358979323846264338327950288;
struct SmoothStats {
 double volume=0, sum=0, sum_pos=0, sum_sq=0, weight_sq=0;
 uint64_t supported=0;
 void add(double sigma,double dv,double weight){
  if(!(weight>0))return;
  if(!(dv>0)||!std::isfinite(sigma)||!std::isfinite(weight))
   throw std::runtime_error("P07E invalid stress/weight");
  const double w=dv*weight;
  volume+=w;sum+=w*sigma;sum_pos+=w*std::max(0.,sigma);
  sum_sq+=w*sigma*sigma;weight_sq+=w*w;++supported;
 }
 double mean()const {return volume>0?sum/volume:std::numeric_limits<double>::quiet_NaN();}
 double positive()const {return volume>0?sum_pos/volume:std::numeric_limits<double>::quiet_NaN();}
 double rms()const {return volume>0?std::sqrt(sum_sq/volume):std::numeric_limits<double>::quiet_NaN();}
 double neff()const {return weight_sq>0?volume*volume/weight_sq:0;}
};
// Continuous C1 transition from 0 at x<=-epsilon to 1 at x>=epsilon.
double smooth_heaviside(double x,double epsilon){
 if(epsilon<=0)return x>=0?1.:0.;
 if(x<=-epsilon)return 0.;if(x>=epsilon)return 1.;
 const double t=(x+epsilon)/(2*epsilon);
 return t*t*(3-2*t);
}
double effective_width(const ZoneSpec&z,double user_um){
 return std::min(user_um,.2*(z.outer_um-z.inner_um));
}
double radial_weight(const ZoneSpec&z,double gap_um,double user_um){
 if(gap_um<0)return 0.; // never integrate within the analytic pore
 const double eps=effective_width(z,user_um);
 const double lower=z.inner_um==0?1.:smooth_heaviside(gap_um-z.inner_um,eps);
 const double upper=1.-smooth_heaviside(gap_um-z.outer_um,eps);
 return std::max(0.,lower*upper);
}
double region_weight(int region,double mu){
 switch(region){
  case 0:return 1.;
  case 1:return smooth_heaviside(mu-cos25,angular_transition_cos);
  case 2:return smooth_heaviside(-mu-cos25,angular_transition_cos);
  case 3:return smooth_heaviside(mu+sin25,angular_transition_cos)*
                 (1.-smooth_heaviside(mu-sin25,angular_transition_cos));
  default:throw std::runtime_error("P07E invalid region");
 }
}
// Separable, exact-geometry reference is evaluated to high-order numerical
// precision; it is NOT an FEM estimate. Integrate analytic sphere volume form.
template<class F> double simpson(F f,double a,double b,int n=4096){
 if(n%2)throw std::runtime_error("Simpson requires even n");
 const double h=(b-a)/n;double sum=f(a)+f(b);
 for(int k=1;k<n;++k)sum+=(k%2?4.:2.)*f(a+h*k);
 return sum*h/3.;
}
double analytical_volume(const ZoneSpec&z,int region,double user_um){
 const double eps=effective_width(z,user_um);
 const double rupper=z.outer_um+eps;
 const double radial=simpson([&](double g){
  const double radius=RBASE+g*1e-6;
  return radial_weight(z,g,user_um)*radius*radius*1e-6;
 },0.,rupper);
 const double angular=simpson([&](double mu){return region_weight(region,mu);},-1.,1.);
 return 2*pi_p07e*radial*angular;
}
double sharp_volume(const ZoneSpec&z,int region){
 const double a=RBASE+z.inner_um*1e-6,b=RBASE+z.outer_um*1e-6;
 const double all=(4*pi_p07e/3.)*(b*b*b-a*a*a);
 const double fraction=region==0?1.:(region==3?sin25:(1.-cos25)/2.);
 return all*fraction;
}
std::string quality(double rel,uint64_t n,double neff){
 if(n==0||neff<20)return "LOW_SUPPORT";
 if(std::abs(rel)>5)return "UNRELIABLE_VOLUME";
 if(std::abs(rel)>1)return "CAUTION_VOLUME";
 return "VOLUME_OK";
}
#endif // STAGE3D07E_SMOOTH
struct Results {
 std::array<std::array<Stats,4>,zones.size()> stats;
 double v6=0,sum6=0,volume=0,sumAll=0,maxS1=-1e100;
 uint64_t nq=0,inside=0;double min_gap_um=0;
#ifdef STAGE3D07E_SMOOTH
 std::array<std::array<std::array<SmoothStats,4>,zones.size()>,widths_um.size()> smooth{};
#endif
 double polar_top=0,polar_bottom=0,polar_topvol=0,polar_bottomvol=0;
};
std::string csv_quote(const std::string& s){
 std::string o="\"";for(char c:s){if(c=='\"')o+="\"\"";else if(c=='\r'||c=='\n')o+=' ';else o+=c;}return o+'\"';
}
std::string num(double x){if(!std::isfinite(x))return "NA";std::ostringstream o;o<<std::setprecision(16)<<x;return o.str();}
std::vector<std::string> split(const std::string&s){std::vector<std::string>v;std::istringstream in(s);std::string x;while(std::getline(in,x,','))v.push_back(x);return v;}

// Independent QP loop, but IDENTICAL material, finite-element basis, interpolation,
// Gauss quadrature, principal-stress definition and B6 classification as Stage3D06.
Results evaluate(const Mesh&m,const std::vector<GaussQ>&q,const std::vector<double>&temp,
                 const Field&field,const Setting&set){
 if(temp.size()!=m.nodes.size()||field.u.size()!=3*m.nodes.size()||field.qstate.size()!=m.tets.size()*q.size())
  throw std::runtime_error("P07D displacement/temperature/internal-variable dimensions mismatch");
 Results res;const auto md=(set.mod=="CONST"?Modulus::CONST:Modulus::VAR);
 const auto controls=ice3d::edv::Controls{set.name!="E",set.name=="EDV"};
 for(size_t e=0;e<m.tets.size();++e){
  const auto&t=m.tets[e];V center{};for(int j=0;j<4;++j)center=center+m.nodes[t[j]]*.25;
  const bool in6=norm(center-pore)<.006;
  for(size_t iq=0;iq<q.size();++iq){
   const auto&g=q[iq];V dr{},ds{},dz{},x{};double tk=ice3d::ed::T_ref;
   for(int j=0;j<10;++j){const V pt=m.nodes[t[j]];
    dr=dr+pt*g.d[j][0];ds=ds+pt*g.d[j][1];dz=dz+pt*g.d[j][2];
    x=x+pt*g.N[j];tk+=g.N[j]*temp[t[j]];
   }
   const V c0=cross(ds,dz),c1=cross(dz,dr),c2=cross(dr,ds);
   const double det=dot(dr,c0);if(!(det>0))throw std::runtime_error("P07D detJ <= 0 at element "+std::to_string(e));
   const double dv=g.w*det;
   Tensor eps{};for(int j=0;j<10;++j){
    const V G=(c0*g.d[j][0]+c1*g.d[j][1]+c2*g.d[j][2])/det;
    const double grad[3]={G.x,G.y,G.z};
    for(int dir=0;dir<3;++dir){Tensor B{};basis(grad,dir,B);
     const double uj=field.u[3*t[j]+dir];for(int k=0;k<6;++k)eps[k]+=B[k]*uj;}
   }
   // dt=0: recompute committed stresses without stepping ED or EDV variables.
   const Response r=ice3d::edv::update(eps,tk,0.0,field.qstate[e*q.size()+iq],md,controls);
   const double s=eigh3(r.sigma)[0]/1e6;const double ps=psi(r.sigma);
   res.volume+=dv;res.sumAll+=dv*ps;
   if(in6){res.v6+=dv;res.sum6+=dv*ps;}
   res.maxS1=std::max(res.maxS1,s);++res.nq;
   const V delta=x-pore;const double rad=norm(delta);if(!(rad>0))continue;
   const double gap_um=(rad-RBASE)*1e6,cosang=delta.z/rad;
   res.min_gap_um=std::min(res.min_gap_um,gap_um);
   if(gap_um < -1e-7){++res.inside;continue;}
#ifdef STAGE3D07E_SMOOTH
   // Same stress at the very same QP; only the observation weight differs.
   // A single radial profile is reused across all angular regions.
   if(gap_um<=zones.back().outer_um+widths_um.back())
   for(size_t wi=0;wi<widths_um.size();++wi)
    for(size_t zi=0;zi<zones.size();++zi){
     const double rw=radial_weight(zones[zi],gap_um,widths_um[wi]);
     if(!(rw>0))continue;
     for(int a=0;a<4;++a){const double aw=region_weight(a,cosang);
      if(aw>0)res.smooth[wi][zi][a].add(s,dv,rw*aw);
     }
    }
#endif
   if(gap_um<=300.0){
    if(cosang>=cos25){res.polar_top+=dv*std::max(0.,s);res.polar_topvol+=dv;}
    if(cosang<=-cos25){res.polar_bottom+=dv*std::max(0.,s);res.polar_bottomvol+=dv;}
   }
   for(size_t z=0;z<zones.size();++z){const auto&zone=zones[z];
    if(gap_um<zone.inner_um||gap_um>zone.outer_um||
       (gap_um==zone.outer_um && std::string_view(zone.kind)=="BAND"))continue;
    for(int a=0;a<4;++a){bool matches=a==0||(a==1&&cosang>=cos25)||
                    (a==2&&cosang<=-cos25)||(a==3&&std::abs(cosang)<=sin25);
     if(matches)res.stats[z][a].add(s,dv);
    }
   }
  }
  if((e+1)%25000==0)std::cerr<<"P07D integrated "<<(e+1)<<" / "<<m.tets.size()<<" elements\n"<<std::flush;
 }
 return res;
}
struct Case {std::string mesh="H2",law="EDV",mod="VAR";int dt=25,quad=3,time=3600;};
std::string scenario(const Case&c){return c.mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.quad);}
struct Inputs {fs::path checkpoint,temperature,history,polar;};
Inputs inputs(const fs::path&root,const Case&c){
 const auto base=root/"LOCAL_RUNS"/scenario(c);
 return {base/"mechanics"/(c.law+"_"+c.mod)/"restart.bin",
         base/"thermal"/("thermal_"+std::to_string(c.time)+"s.vtu"),
         base/"mechanics"/(c.law+"_"+c.mod)/"time_series.csv",
         base/"mechanics"/(c.law+"_"+c.mod)/"polar_caps_history.csv"};
}
struct Stored {double t=0,phi=0,omega=0,max=0;};
Stored last_history(const fs::path&file){
 std::ifstream f(file);std::string line,last;
 if(!std::getline(f,line))throw std::runtime_error("P07D missing history: "+file.string());
 while(std::getline(f,line))if(!line.empty())last=line;
 auto x=split(last);if(x.size()<5)throw std::runtime_error("P07D incomplete time_series.csv");
 Stored s; s.t=std::stod(x[0]);s.phi=std::stod(x[2]);s.omega=std::stod(x[3]);s.max=std::stod(x[4]);return s;
}
struct CaseReport {Case c;Results result;double refPhi=0,refMax=0;std::string status,message;};
CaseReport run_case(const fs::path&root,const Case&c,bool skipHistoryCheck=false){
 CaseReport report;report.c=c;
 const fs::path meshfile=root/"meshes"/(c.mesh+".msh");const Inputs in=inputs(root,c);
 for(const auto&file:{meshfile,in.checkpoint,in.temperature})
  if(!fs::is_regular_file(file))throw std::runtime_error("P07D missing input: "+file.string());
 auto imported=read_msh(meshfile);const Mesh& m=imported.mesh;
 const auto q=volume_q(c.quad);
 Setting set;set.name=c.law;set.mod=c.mod;set.quad=c.quad;
 Field state;state.u.assign(3*m.nodes.size(),0);state.qstate.resize(m.tets.size()*q.size());
 const int restored=restore(in.checkpoint,m,set,state);
 if(restored*c.dt!=c.time||std::abs(state.lastTime-c.time)>1e-7)
  throw std::runtime_error("P07D checkpoint step/time does not match the requested scenario");
 auto T=load_vtu_temp(m,in.temperature);
 report.result=evaluate(m,q,T,state,set);
 if(!(report.result.v6>0))throw std::runtime_error("P07D empty B6 gauge volume");
 const double phi=report.result.sum6/report.result.v6;
 const double omega=report.result.sumAll/report.result.volume;
 if(!skipHistoryCheck){
  const Stored saved=last_history(in.history);report.refPhi=saved.phi;report.refMax=saved.max;
  if(std::abs(saved.t-c.time)>1e-7 || std::abs(saved.phi-phi)>2e-9 ||
     std::abs(saved.omega-omega)>2e-9 ||std::abs(saved.max-report.result.maxS1)>2e-7)
    throw std::runtime_error("P07D committed checkpoint stresses mismatch time_series.csv");
  if(fs::is_regular_file(in.polar)){
   std::ifstream polar(in.polar);std::string line,last;std::getline(polar,line);
   while(std::getline(polar,line))if(!line.empty())last=line;
   auto x=split(last);if(x.size()<5)throw std::runtime_error("P07D truncated polar cap history");
   const double top=report.result.polar_topvol?report.result.polar_top/report.result.polar_topvol:0;
   const double bottom=report.result.polar_bottomvol?report.result.polar_bottom/report.result.polar_bottomvol:0;
   if(std::abs(std::stod(x[0])-c.time)>1e-7 ||
      std::abs(std::stod(x[1])-top)>2e-7 || std::abs(std::stod(x[2])-bottom)>2e-7)
    throw std::runtime_error("P07D polar-cap mean mismatch previously saved history");
  }
 }
 report.status="PASS";
 return report;
}
void emit_shells(std::ostream&out,CaseReport&report){
 const Case&c=report.c;auto&R=report.result;
 for(size_t z=0;z<zones.size();++z)for(size_t a=0;a<regions.size();++a){
  auto&S=R.stats[z][a];
  out<<c.mesh<<','<<c.dt<<','<<c.quad<<','<<c.law<<','<<c.mod<<','
     <<zones[z].kind<<','<<num(zones[z].inner_um)<<','<<num(zones[z].outer_um)<<','
     <<regions[a]<<','<<S.count<<','<<num(S.v)<<',';
  if(!S.count)out<<"NA,NA,NA,NA,NA,NA,NA,EMPTY\n";
  else{
   const double mean=S.s1/S.v;
   out<<num(mean)<<','<<num(S.pos/S.v)<<','<<num(std::sqrt(S.s1sq/S.v))<<','
      <<num(std::sqrt(std::max(0.,S.s1sq/S.v-mean*mean)))<<','
      <<num(S.quantile(.95))<<','<<num(S.quantile(.99))<<','<<num(S.maximum)<<",OK\n";
  }
 }
}
struct Row {std::string mesh,kind,region;double in=0,out=0,mean=0,positive=0,vol=0;uint64_t nq=0;};
std::vector<Row> summary(CaseReport&r){
 std::vector<Row>v;for(size_t z=0;z<zones.size();++z)for(size_t a=0;a<regions.size();++a){
 auto&S=r.result.stats[z][a];if(!S.count)continue;
 v.push_back({r.c.mesh,zones[z].kind,regions[a],zones[z].inner_um,zones[z].outer_um,S.s1/S.v,S.pos/S.v,S.v,S.count});}
 return v;
}
void compare(std::ostream&out,const std::map<std::string,CaseReport>&reports){
 if(reports.size()<2)return;
 for(auto it=reports.begin();it!=reports.end();++it)for(auto jt=std::next(it);jt!=reports.end();++jt){
  auto&left=const_cast<CaseReport&>(it->second);auto&right=const_cast<CaseReport&>(jt->second);
  const auto a=summary(left),b=summary(right);
  for(const auto&x:a)for(const auto&y:b){if(x.kind!=y.kind||x.region!=y.region||x.in!=y.in||x.out!=y.out)continue;
   const double denom=std::max(std::abs(x.positive),1e-30);
   out<<x.mesh<<','<<y.mesh<<','<<x.kind<<','<<x.in<<','<<x.out<<','<<x.region<<','
      <<num(x.mean)<<','<<num(y.mean)<<','<<num(x.positive)<<','<<num(y.positive)<<','
      <<num(100*(y.positive-x.positive)/denom)<<','<<num(x.vol)<<','<<num(y.vol)<<','
      <<num(100*(y.vol-x.vol)/std::max(x.vol,1e-30))<<','<<x.nq<<','<<y.nq<<'\n';
  }
 }
}
void write_report(std::ostream&out,const std::map<std::string,CaseReport>&passed,const std::vector<std::string>&failed){
 const int t=passed.empty()?0:passed.begin()->second.c.time;
 out<<"# Stage 3D-07D — диагностика напряжений в фиксированных областях\n\n"
    <<"Только постпроцессинг сохранённых checkpoint при t="<<t<<" с; новые уравнения теплопроводности и механики не решались.\n\n"
    <<"Подтверждённых сценариев: **"<<passed.size()<<"**. Ошибок/отсутствующих входов: **"<<failed.size()<<"**.\n\n";
 for(auto&err:failed)out<<"- "<<err<<"\n";
 out<<"\n## Проверки\n\n"
    <<"Проверяются полная двоичная сигнатура сетки и состояние EDV, порядок квадратуры, модель, номер шага, время, VTU-нумерация узлов,"
    <<" совпадение Phi6, PsiOmega и абсолютного QP-максимума с сохранённым time_series.csv; при наличии полярной истории — средние напряжения.\n\n"
    <<"Таблица P07D_SHELLS.csv содержит объёмно-взвешенные средние и квантили в фиксированных радиальных слоях, а P07D_COMPARISON.csv — разности на сопоставимых областях.\n"
    <<"Слои указаны в **мкм от поверхности сферы R=1 мм**; углы TOP25/BOTTOM25 — полуугол 25 градусов, EQUATOR25 — ±25 градусов от экватора.\n"
    <<"Квантили взвешены по физическим весам квадратуры, а не по числу точек.\n\n"
    <<"Важно: классификация по точкам квадратуры лишь приближает интегралы по слоям, пересечённым элементами; числа N_QP и оценка объёма могут различаться между сетками."
    <<" Отсутствующий слой обозначен EMPTY, а не нулевым напряжением. Это прямые расчёты при ξ=0, не GH3 и не производные формы.\n\n"
    <<"## Результаты проверки историй\n\n| Сетка | Phi6 | QP max, МПа | QP внутри идеальной сферы | Мин. радиальный зазор, мкм |\n|---|---:|---:|---:|---:|\n";
 for(const auto&[name,r]:passed)out<<'|'<<name<<'|'<<num(r.result.sum6/r.result.v6)<<'|'<<num(r.result.maxS1)<<'|'<<r.result.inside<<'|'<<num(r.result.min_gap_um)<<"|\n";
 out<<"\nНа криволинейной аппроксимации Tet10 отдельные точки квадратуры могут оказаться внутри идеальной аналитической сферы на малую глубину; такие точки исключены из приповерхностных слоёв, но не из исходного интеграла Phi6.\n";
 out<<"\nКритерий пригодности для статьи — стабилизация средних напряжений и оценённых объёмов в фиксированных областях, а не совпадение top-100 по номерам элементов."
    <<" Для вывода о регулярности предельных напряжений потребуется отдельное исследование.\n";
}
#ifdef STAGE3D07E_SMOOTH
struct SmoothRow {
 std::string mesh,zone,region;
 double bandwidth=0,inner=0,outer=0,mean=0,positive=0,rel=0;
 std::string quality_label;
};
std::vector<SmoothRow> emit_smooth(std::ostream&out,std::ostream&audit,CaseReport&report){
 const auto&c=report.c;auto&res=report.result;
 std::vector<SmoothRow> summaries;
 for(size_t wi=0;wi<widths_um.size();++wi)
  for(size_t zi=0;zi<zones.size();++zi)
   for(size_t a=0;a<regions.size();++a){
    const auto&zone=zones[zi];const auto&S=res.smooth[wi][zi][a];
    const double vref=analytical_volume(zone,int(a),widths_um[wi]);
    const double vsharp=sharp_volume(zone,int(a));
    const double error=100*(S.volume-vref)/vref;
    const std::string grade=quality(error,S.supported,S.neff());
    const auto&hard=res.stats[zi][a];
    audit<<c.mesh<<','<<widths_um[wi]<<','<<zone.kind<<','<<zone.inner_um<<','<<zone.outer_um
       <<','<<regions[a]<<','<<num(vsharp)<<','<<num(vref)<<','<<num(hard.v)
       <<','<<num(100*(hard.v-vsharp)/vsharp)<<','<<num(S.volume)<<','<<num(error)
       <<','<<S.supported<<','<<num(S.neff())<<','<<grade<<'\n';
    out<<c.mesh<<','<<c.dt<<','<<c.quad<<','<<c.law<<','<<c.mod<<','<<widths_um[wi]
       <<','<<zone.kind<<','<<zone.inner_um<<','<<zone.outer_um<<','<<regions[a]
       <<','<<num(effective_width(zone,widths_um[wi]))<<','<<num(S.volume)
       <<','<<num(vref)<<','<<num(error)<<','<<S.supported<<','<<num(S.neff())
       <<','<<num(S.mean())<<','<<num(S.positive())<<','<<num(S.rms())<<','<<grade<<'\n';
    summaries.push_back({c.mesh,zone.kind,regions[a],widths_um[wi],zone.inner_um,
                        zone.outer_um,S.mean(),S.positive(),error,grade});
   }
 return summaries;
}
void emit_smooth_compare(std::ostream&out,const std::map<std::string,std::vector<SmoothRow>>& rows){
 for(auto i=rows.begin();i!=rows.end();++i)for(auto j=std::next(i);j!=rows.end();++j){
  if(i->second.size()!=j->second.size())throw std::runtime_error("P07E mismatched zone tables");
  for(size_t k=0;k<i->second.size();++k){const auto&a=i->second[k],&b=j->second[k];
   if(a.zone!=b.zone||a.region!=b.region||a.inner!=b.inner||a.outer!=b.outer||a.bandwidth!=b.bandwidth)
    throw std::runtime_error("P07E comparison misaligned");
   const double change=100*(b.positive-a.positive)/std::max(std::abs(a.positive),1e-30);
   const bool both=(a.quality_label=="VOLUME_OK"&&b.quality_label=="VOLUME_OK");
   out<<i->first<<','<<j->first<<','<<a.bandwidth<<','<<a.zone<<','<<a.inner<<','<<a.outer
      <<','<<a.region<<','<<num(a.mean)<<','<<num(b.mean)<<','<<num(change)
      <<','<<num(a.rel)<<','<<num(b.rel)<<','<<(both?"COMPARABLE":"VOLUME_WARNING")<<'\n';
  }
 }
}
void emit_smooth_notes(std::ostream&out,const std::map<std::string,std::vector<SmoothRow>>&rows){
 out<<"# Stage 3D-07E — сглаженные радиальные зоны наблюдения\n\n"
    <<"Физическое состояние, история EDV, квадратура, Phi6 и напряжения не изменены. "
      "Исходные таблицы P07D сохраняются в отдельном каталоге.\n\n"
    <<"Рассчитаны сглаженные веса с номинальной полушириной перехода "
      "2, 5 и 10 мкм (ограничение 20% толщины зоны), а для полярных областей "
      "сглаживание по cos(theta) с полушириной 0.01.\n\n"
    <<"Объёмы сопоставлены с интегралом самой весовой функции по идеальной сфере, "
      "а также с точным объёмом несглаженной оболочки. "
      "Сглаженные зоны являются ДРУГИМИ функционалами наблюдения и их объём "
      "может отличаться от жёстко отсечённого; сравнивать надо одинаковую ширину сглаживания.\n\n"
    <<"Статус VOLUME_OK: ошибка не более 1%, CAUTION_VOLUME: 1–5%, "
      "UNRELIABLE_VOLUME: более 5%, LOW_SUPPORT: эффективное число точек <20. "
      "Достаточный контроль объёма не является доказательством сходимости напряжений.\n\n"
    <<"Сохранённые исходные значения из P07D и новые усреднения рассчитываются "
      "в одном QP-проходе, без повторного решения механики.\n\n"
    <<"## Отмеченные ненадёжные зоны (в том числе узкие полосы)\n\n";
 for(const auto&[m,v]:rows){size_t warn=0;for(const auto&x:v)if(x.quality_label!="VOLUME_OK")++warn;
  out<<"- "<<m<<": "<<warn<<" / "<<v.size()<<" зон с предупреждениями.\n";
 }
 out<<"\nЭто данные прямого расчёта EDV/VAR при xi=0, а не GH3 или производные формы.\n";
}
#endif
} // namespace p07d

int main(int argc,char**argv){try{
 using namespace p07d;
 fs::path root=STAGE3D06_ROOT_DIR;fs::path output;std::string meshes="H2,H3,H4";
 int dt=25,quad=3,time=3600;std::string law="EDV",mod="VAR";bool help=false,dryrun=false,skipHistory=false;
 for(int i=1;i<argc;++i){const std::string f=argv[i];auto value=[&](){if(i+1>=argc)throw std::runtime_error("Missing value after "+f);return std::string(argv[++i]);};
  if(f=="--root")root=value();else if(f=="--out")output=value();else if(f=="--meshes")meshes=value();
  else if(f=="--dt")dt=std::stoi(value());else if(f=="--quad")quad=std::stoi(value());
  else if(f=="--time")time=std::stoi(value());else if(f=="--law")law=value();else if(f=="--modulus")mod=value();
  else if(f=="--dry-run")dryrun=true;else if(f=="--skip-history-check")skipHistory=true;
  else if(f=="--help"||f=="-h")help=true;else throw std::runtime_error("Unknown option: "+f);
 }
 if(help){std::cout<<"Stage3D07D fixed-shell QP stress postprocessor\n"
   <<"Default: H2,H3,H4 dt25 q3 EDV VAR t3600; source <root>/LOCAL_RUNS/; no FEM solve.\n"
   <<"[--root DIR] [--out DIR] [--meshes H2,H3,H4] [--dt 25] [--quad 3] [--time 3600]"
   <<" [--law EDV] [--modulus VAR] [--dry-run]\n";return 0;}
 if(dt<=0||time<=0||time%dt!=0||(quad!=3&&quad!=4)||
    (law!="E"&&law!="ED"&&law!="EDV")||(mod!="CONST"&&mod!="VAR"))
    throw std::runtime_error("Invalid dt/time/quad/law/modulus");
#ifdef STAGE3D07E_SMOOTH
 if(output.empty())output=root/"LOCAL_RUNS"/"REFINEMENT_CAMPAIGN"/"P07E";
#else
 if(output.empty())output=root/"LOCAL_RUNS"/"REFINEMENT_CAMPAIGN"/"P07D";
#endif
 const auto targets=split(meshes);if(targets.empty())throw std::runtime_error("Missing meshes");
 std::map<std::string,CaseReport> passed;std::vector<std::string>failed;
 for(const auto&name:targets){if(name!="H0"&&name!="H1"&&name!="H2"&&name!="H3"&&name!="H4")
    throw std::runtime_error("Invalid mesh ID: "+name);
  const Case c{name,law,mod,dt,quad,time};const auto in=inputs(root,c);
  if(dryrun){std::cout<<name<<" mesh="<<(root/"meshes"/(name+".msh"))<<" checkpoint="<<in.checkpoint
    <<" thermal="<<in.temperature<<" checkpoint_exists="<<fs::is_regular_file(in.checkpoint)
    <<" thermal_exists="<<fs::is_regular_file(in.temperature)<<'\n';continue;}
  try{
   std::cout<<"P07D "<<scenario(c)<<"/"<<law<<"_"<<mod<<" t="<<time<<" - restoring\n"<<std::flush;
   auto r=run_case(root,c,skipHistory);passed.emplace(name,std::move(r));
   std::cout<<"P07D "<<name<<" PASS; Phi6="<<passed[name].result.sum6/passed[name].result.v6
       <<" max sigma1="<<passed[name].result.maxS1<<" MPa\n"<<std::flush;
  }catch(const std::exception&e){const std::string err=name+": "+e.what();failed.push_back(err);
   std::cerr<<"P07D ERROR "<<err<<'\n';}
 }
 if(dryrun)return 0;
 fs::create_directories(output);
 std::ofstream status(output/"P07D_STATUS.csv");
 status<<"mesh,status,reason,dt_s,quad,time_s,Phi6,QP_max_sigma1_MPa,inside_pore_qp,min_gap_um\n";
 for(const auto&[name,r]:passed)status<<name<<",PASS,,"<<dt<<','<<quad<<','<<time<<','<<num(r.result.sum6/r.result.v6)<<','<<num(r.result.maxS1)<<','<<r.result.inside<<','<<num(r.result.min_gap_um)<<'\n';
 for(const auto&e:failed){auto n=e.substr(0,e.find(':'));status<<n<<",FAILED,"<<csv_quote(e)<<','<<dt<<','<<quad<<','<<time<<",NA,NA,NA,NA\n";}
 std::ofstream shells(output/"P07D_SHELLS.csv");
 shells<<"mesh,dt_s,quad,law,modulus,zone_type,inner_um,outer_um,region,qp_count,volume_m3,mean_sigma1_MPa,mean_positive_sigma1_MPa,rms_sigma1_MPa,stdev_sigma1_MPa,weighted_p95_MPa,weighted_p99_MPa,QP_max_sigma1_MPa,status\n";
 for(auto&[name,r]:passed)emit_shells(shells,r);
 std::ofstream cmp(output/"P07D_COMPARISON.csv");
 cmp<<"mesh_a,mesh_b,zone_type,inner_um,outer_um,region,mean_sigma1_a_MPa,mean_sigma1_b_MPa,mean_positive_a_MPa,mean_positive_b_MPa,positive_diff_percent,volume_a_m3,volume_b_m3,volume_diff_percent,qp_a,qp_b\n";
 compare(cmp,passed);
 std::ofstream report(output/"P07D_REPORT_RU.md");write_report(report,passed,failed);
#ifdef STAGE3D07E_SMOOTH
 std::ofstream eout(output/"P07E_SMOOTH_SHELLS.csv"),audit(output/"P07E_VOLUME_AUDIT.csv");
 eout<<"mesh,dt_s,quad,law,modulus,bandwidth_um,zone_type,inner_um,outer_um,region,"
       "effective_bandwidth_um,smoothed_volume_m3,reference_weighted_volume_m3,"
       "volume_error_percent,qp_supported,effective_qp_count,mean_sigma1_MPa,"
       "mean_positive_sigma1_MPa,rms_sigma1_MPa,volume_quality\n";
 audit<<"mesh,bandwidth_um,zone_type,inner_um,outer_um,region,analytic_sharp_volume_m3,"
        "analytic_smoothed_volume_m3,qp_sharp_volume_m3,sharp_error_percent,"
        "qp_smoothed_volume_m3,smoothed_error_percent,qp_supported,effective_qp_count,"
        "smoothed_quality\n";
 std::map<std::string,std::vector<SmoothRow>> smooth_rows;
 for(auto&[name,r]:passed)smooth_rows.emplace(name,emit_smooth(eout,audit,r));
 std::ofstream ec(output/"P07E_COMPARISON.csv");
 ec<<"mesh_a,mesh_b,bandwidth_um,zone_type,inner_um,outer_um,region,"
      "mean_sigma1_a_MPa,mean_sigma1_b_MPa,mean_positive_diff_percent,"
      "volume_error_a_percent,volume_error_b_percent,comparison_quality\n";
 emit_smooth_compare(ec,smooth_rows);
 std::ofstream er(output/"P07E_REPORT_RU.md");emit_smooth_notes(er,smooth_rows);
#endif
 std::cout<<"P07D DONE: passed="<<passed.size()<<" failed="<<failed.size()<<" out="<<output<<'\n'<<std::flush;
 return failed.empty()?0:3;
 }catch(const std::exception&e){std::cerr<<"P07D FATAL: "<<e.what()<<'\n';return 2;}}
