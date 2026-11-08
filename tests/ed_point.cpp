// Stage 3D-04. Independent material-point verification; no spatial FE solve here.
#include "ed_material.hpp"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <fstream>
#include <filesystem>
#include <functional>
#include <vector>
#include <limits>
#include <cmath>
#include <algorithm>
#include <stdexcept>
#include <map>
using namespace ice3d::ed;
namespace fs=std::filesystem;
using std::string;
using std::vector;
void check(bool p,const string&what){if(!p)throw std::runtime_error("G04 FAIL: "+what);}
void near(double got,double expected,double rel,double abs_tol,const string&what){
 if(!(std::abs(got-expected)<=abs_tol+rel*std::max(std::abs(expected),std::abs(got)))){
 std::ostringstream s;s<<std::setprecision(17)<<what<<": got="<<got<<", expected="<<expected;
 throw std::runtime_error(s.str());}}
Tensor trial_strain(){return {0.0012,-0.0007,0.00032,0.00068,-0.00027,0.00018};}
State trial_state(){State s;s.e_d={0.00013,-0.00009,-0.00004,0.00007,-0.00006,0.00011};return s;}
double max_tangent_rel=0,max_temperature_rel=0;
void reference(){
 near(Kd_SI,1.2e-9,1e-15,0,"MPa^-1 --> Pa^-1");
 near(a,1.8e-9,1e-15,0,"3/2 Kd SI");
 near(arrhenius(T_arr_ref),1,1e-14,0,"Arrhenius ref");
 near(Ad_ref*arrhenius(T_arr_ref),1.5e-3,1e-14,0,"Ad(T_r)");
 near(modulus(T_ref,Modulus::VAR),modulus(T_ref,Modulus::CONST),1e-14,0,"Sinha reference");
 near(dmodulus(Modulus::VAR),-12431842.96619411,1e-13,0,"Sinha dEdT");
 Tensor strain=trial_strain();
 auto c=update(strain,T_ref,120,{},Modulus::CONST);
 auto v=update(strain,T_ref,120,{},Modulus::VAR);
 for(int i=0;i<6;i++)near(c.sigma[i],v.sigma[i],2e-14,1e-8,"E_CONST/E_VAR at Tref");
 for(int i=0;i<6;i++)near(c.new_state.e_d[i],v.new_state.e_d[i],2e-14,1e-17,"state at Tref");
 near(c.G,E_ref/(2*(1+nu)),1e-14,0,"G point");
 near(c.K,E_ref/(3*(1-2*nu)),1e-14,0,"K point");
 check(c.Ad>0 && c.b>0 && c.denom>1 && c.G_algorithmic>0,"positive ED moduli");
 for(auto mode:{Modulus::CONST,Modulus::VAR}){
   auto pure=update({},245.15,600,{},mode);
   near(norm(pure.new_state.e_d),0,0,1e-18,"no deviatoric ED from temperature alone");
   near(norm(pure.deviatoric_stress),0,0,1e-8,"no deviatoric thermal stress");
   Tensor thermal{};for(int i=0;i<3;i++)thermal[i]=alpha*(245.15-T_ref);
   auto free=update(thermal,245.15,600,{},mode);
   near(norm(free.sigma),0,0,1e-7,"unconstrained thermal expansion is stress-free");
   Tensor hydro{0.0008,0.0008,0.0008,0,0,0};
   auto bulk=update(hydro,T_ref,1000,{},mode);
   near(norm(bulk.new_state.e_d),0,0,1e-17,"ED does not relax hydrostatic stress");
   for(int i=0;i<3;i++)near(bulk.sigma[i],bulk.K*tr(hydro),1e-14,1e-7,"bulk stiffness");
   auto step0=update(strain,T_ref,0,{},mode);
   for(int i=0;i<6;i++)near(step0.sigma[i],2*step0.G*deviator(strain)[i]+(i<3?step0.K*tr(strain):0),1e-14,1e-8,"instantaneous limit");
 }
 bool threw=false;try{State invalid;invalid.e_d[0]=1;update({},T_ref,1,invalid,Modulus::CONST);}catch(const std::invalid_argument&){threw=true;}
 check(threw,"reject non-deviatoric state");
 threw=false;try{update({},-20.,1,{},Modulus::CONST);}catch(const std::invalid_argument&){threw=true;}
 check(threw,"reject Celsius accidentally passed as kelvin");
 std::cout<<"PASS G04 reference, MPa-->Pa, Arrhenius, pure thermal, bulk, E_CONST/E_VAR\n";
}
struct RelaxRow {double dt,err,stress,exact;};
vector<RelaxRow> relaxation_rows(Modulus mode,double TK=253.15){
 auto ep=trial_strain();double d=deviator(ep)[3];State initial;
 const double G=modulus(TK,mode)/(2*(1+nu)),A=Ad_ref*arrhenius(TK);
 const double eta=1+2*G*a,lam=A*eta,einf=2*G*a*d/eta;
 const double t_end=600;
 vector<RelaxRow> rows;
 for(int N:{2,4,8,16,32,64}){
  double dt=t_end/N;State state=initial;Response r;
  for(int k=0;k<N;k++){r=update(ep,TK,dt,state,mode);state=r.new_state;}
  double ed_exact=einf*(1-std::exp(-lam*t_end));
  double s_exact=2*G*(d-ed_exact);
  double err=std::abs(r.sigma[3]-s_exact);
  rows.push_back({dt,err,r.sigma[3],s_exact});
  near(state.e_d[3],einf*(1-std::pow(1+lam*dt,-N)),2e-13,1e-16,"closed form backward Euler fixed-strain relaxation");
 }
 return rows;
}
void relaxation(){
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double TK:{245.15,T_ref,T_arr_ref}){
   auto rows=relaxation_rows(mode,TK);
   for(size_t i=1;i<rows.size();i++)check(rows[i].err<rows[i-1].err,"temporal convergence to continuous exact relaxation");
   check(rows.back().err<rows.front().err/8,"strong convergence with dt");
   check(rows[0].stress>rows[0].exact,"implicit relaxation stress approaches exact from above");
 }
 std::cout<<"PASS G04 fixed-strain analytical relaxation, backward Euler, dt convergence\n";
}
void recovery(){
 // Independent stress-controlled ODE solution: e'_d=Ad(a*s-e_d).
 // This checks the material parameters and recoverable state independently
 // from the implicit strain-controlled constitutive solver.
 const double TK=T_ref,Ad=Ad_ref*arrhenius(TK),shear=1.7e6;
 for(int N:{2,4,8,16,32,64}){
   double dt=600./N,x=0;
   for(int k=0;k<N;k++)x=(x+dt*Ad*a*shear)/(1+dt*Ad);
   near(x,a*shear*(1-std::pow(1+dt*Ad,-N)),2e-13,1e-18,"stress controlled creep BE exact");
   double release=x;
   for(int k=0;k<2*N;k++)x/=1+dt*Ad;
   near(x,release*std::pow(1+dt*Ad,-2*N),2e-13,1e-18,"recovery BE exact");
   check(x>0&&x<release,"recovery nonincreasing toward zero");
 }
 // Strain-controlled sudden unloading induces back stress; ED state still relaxes.
 State s;s.e_d={2e-4,-1e-4,-1e-4,1e-4,0,0};
 double TK2=263.15,dt=30;
 auto r=update({},TK2,dt,s,Modulus::VAR);
 double factor=1/(1+dt*r.Ad*(1+2*r.G*a));
 for(int i=0;i<6;i++)near(r.new_state.e_d[i],s.e_d[i]*factor,2e-14,1e-16,"stress-assisted strain-controlled recovery");
 check(norm(r.new_state.e_d)<norm(s.e_d),"state recovers under zero strain");
 std::cout<<"PASS G04 stress-controlled and strain-controlled recovery\n";
}
void tangent(){
 max_tangent_rel=0;
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double TK:{244.15,253.15,263.15})for(double dt:{0.,30.,300.}){
  auto ep=trial_strain();auto state=trial_state();
  auto r=update(ep,TK,dt,state,mode);
  check(r.tangent[0][0]>0 && r.tangent[3][3]>0,"positive diagonal tangent");
  near(r.tangent[0][1],r.tangent[1][0],1e-14,0,"major symmetry");
  near(r.tangent[3][3],2*r.G_algorithmic,1e-14,0,"correct tensor-shear factor");
  for(int j=0;j<6;j++){
   double h=2e-7;auto epplus=ep,epminus=ep;epplus[j]+=h;epminus[j]-=h;
   auto plus=update(epplus,TK,dt,state,mode),minus=update(epminus,TK,dt,state,mode);
   for(int i=0;i<6;i++){
    double fd=(plus.sigma[i]-minus.sigma[i])/(2*h);
    double scale=std::max({1.,std::abs(fd),std::abs(r.tangent[i][j])});
    double rel=std::abs(fd-r.tangent[i][j])/scale;
    max_tangent_rel=std::max(max_tangent_rel,rel);
    check(rel<2e-8,"6x6 algorithmic tangent vs central FD");
   }
  }
 }
 std::cout<<"PASS G04 6x6 algorithmic tangent FD; max relative error="<<std::setprecision(12)<<max_tangent_rel<<"\n";
}
void temperature(){
 max_temperature_rel=0;
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double TK:{240.15,253.15,263.15})for(double dt:{0.,30.,300.}){
  auto ep=trial_strain();auto state=trial_state();auto r=update(ep,TK,dt,state,mode);
  const double h=.002;
  auto up=update(ep,TK+h,dt,state,mode),down=update(ep,TK-h,dt,state,mode);
  for(int i=0;i<6;i++){
   double fd=(up.sigma[i]-down.sigma[i])/(2*h);
   double rel=std::abs(fd-r.d_sigma_dT[i])/std::max({1.,std::abs(fd),std::abs(r.d_sigma_dT[i])});
   max_temperature_rel=std::max(max_temperature_rel,rel);
   check(rel<2e-8,"full derivative wrt T including Ad(T), G(T), K(T), expansion");
  }
 }
 double dAd=Ad_ref*arrhenius(253.15)*dlnarr_dT(253.15);
 double h=.001;
 near(dAd,Ad_ref*(arrhenius(253.15+h)-arrhenius(253.15-h))/(2*h),5e-9,0,"Arrhenius temperature derivative");
 std::cout<<"PASS G04 temperature derivative FD; max relative error="<<std::setprecision(12)<<max_temperature_rel<<"\n";
}
void energy(){
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double dt:{1.,20.,180.,600.}){
  auto strain=trial_strain();auto state=trial_state();
  const double TK=T_ref;
  auto oldr=update(strain,TK,0,state,mode);
  auto next=update(strain,TK,dt,state,mode);
  double decay=oldr.free_energy-next.free_energy;
  check(decay>=-1e-9,"isothermal fixed strain stored energy cannot increase");
  check(next.dissipation_rate>=0,"nonnegative dissipation");
  check(decay+1e-6>=dt*next.dissipation_rate,"isothermal BE energy inequality");
  // Variable strain, isothermal discrete Clausius-Duhem inequality.
  Tensor ep2=strain;ep2[0]+=.00016;ep2[1]-=.00009;ep2[3]+=.00018;
  auto r2=update(ep2,TK,dt,state,mode);
  Tensor delta{};for(int i=0;i<6;i++)delta[i]=ep2[i]-strain[i];
  double work=dot(r2.sigma,delta);
  double margin=work-(r2.free_energy-oldr.free_energy)-dt*r2.dissipation_rate;
  check(margin>-1e-5,"discrete material energy inequality with strain increment");
  // Discrete kinetic equation at end-of-step, both deviatoric and SI factors.
  for(int j=0;j<6;j++){
   double rate=(r2.new_state.e_d[j]-state.e_d[j])/dt;
   double rhs=r2.Ad*(a*r2.deviatoric_stress[j]-r2.new_state.e_d[j]);
   near(rate,rhs,1e-11,1e-17,"backward Euler evolution residual");
  }
 }
 std::cout<<"PASS G04 isothermal ED free energy, nonnegative dissipation, backward Euler residual\n";
}
using Mat3=std::array<std::array<double,3>,3>;
Tensor rotate_tensor(const Tensor&z,const Mat3&R){
 double A[3][3]={{z[0],z[3],z[5]},{z[3],z[1],z[4]},{z[5],z[4],z[2]}};
 double B[3][3]{};
 for(int i=0;i<3;i++)for(int j=0;j<3;j++)for(int k=0;k<3;k++)for(int l=0;l<3;l++)B[i][j]+=R[i][k]*A[k][l]*R[j][l];
 return {B[0][0],B[1][1],B[2][2],B[0][1],B[1][2],B[2][0]};
}
void objectivity(){
 double a0=.37,b0=.71,ca=cos(a0),sa=sin(a0),cb=cos(b0),sb=sin(b0);
 Mat3 R{{{cb,-sb*ca,sb*sa},{sb,cb*ca,-cb*sa},{0,sa,ca}}};
 auto ep=trial_strain();auto old=trial_state();
 for(auto mode:{Modulus::CONST,Modulus::VAR}){
   auto A=update(ep,247.15,130,old,mode);
   State transformed;transformed.e_d=rotate_tensor(old.e_d,R);
   auto B=update(rotate_tensor(ep,R),247.15,130,transformed,mode);
   auto rSig=rotate_tensor(A.sigma,R),rED=rotate_tensor(A.new_state.e_d,R);
   for(int i=0;i<6;i++){
    near(B.sigma[i],rSig[i],1e-12,1e-5,"tensor rotational equivariance of stress");
    near(B.new_state.e_d[i],rED[i],1e-12,1e-17,"tensor rotational equivariance of state");
   }
   near(B.free_energy,A.free_energy,1e-12,1e-4,"frame-independent free energy");
   near(B.dissipation_rate,A.dissipation_rate,1e-12,1e-9,"frame-independent ED dissipation");
 }
 std::cout<<"PASS G04 objectivity under 3D orthogonal rotation\n";
}
void restart(){
 std::vector<double> temperatures={253.15,250.15,249.15,251.15,253.15};
 std::vector<double> steps={18,70,170,40,210};
 auto eps=trial_strain();
 for(auto mode:{Modulus::CONST,Modulus::VAR}){
  State continuous,reloaded;
  for(size_t i=0;i<temperatures.size();i++){
   for(int k=0;k<6;k++)eps[k]+=(k%2==0?1.:-1.)*1e-5;
   continuous=update(eps,temperatures[i],steps[i],continuous,mode).new_state;
   reloaded=update(eps,temperatures[i],steps[i],reloaded,mode).new_state;
   // IEEE-double roundtrip as portable material state restart format.
   std::ostringstream mem;mem<<std::setprecision(std::numeric_limits<double>::max_digits10);
   for(auto v:reloaded.e_d)mem<<v<<"\n";
   std::istringstream rd(mem.str());for(auto&v:reloaded.e_d)check(bool(rd>>v),"restart parse");
   for(int k=0;k<6;k++)near(reloaded.e_d[k],continuous.e_d[k],1e-15,1e-19,"restart state invariance");
  }
 }
 std::cout<<"PASS G04 path-dependent history state, E branch, restart roundtrip\n";
}
void generate(fs::path out){
 fs::create_directories(out);
 std::ofstream relax(out/"G04_relaxation_history.csv");relax<<std::setprecision(17)<<"model,T_K,time_s,dt_s,eps_xy,ed_xy,shear_stress_MPa,analytic_shear_stress_MPa,free_energy_J_m3,dissipation_W_m3\n";
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double TK:{253.15,263.15}){
  auto eps=trial_strain();State state;double G=modulus(TK,mode)/(2*(1+nu));double d=deviator(eps)[3];double Ad=Ad_ref*arrhenius(TK);
  double eta=1+2*G*a;double edInf=2*G*a*d/eta;
  for(int k=1;k<=60;k++){
   double dt=10,t=k*dt;auto r=update(eps,TK,dt,state,mode);state=r.new_state;
   double sex=2*G*(d-edInf*(1-exp(-Ad*eta*t)));
   relax<<(mode==Modulus::CONST?"CONST":"VAR")<<","<<TK<<","<<t<<","<<dt<<","<<d<<","<<state.e_d[3]<<","<<r.sigma[3]/1e6<<","<<sex/1e6<<","<<r.free_energy<<","<<r.dissipation_rate<<"\n";
  }
 }
 std::ofstream conv(out/"G04_temporal_convergence.csv");conv<<std::setprecision(17)<<"mode,T_K,dt_s,absolute_error_Pa,computed_shear_Pa,exact_shear_Pa\n";
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double TK:{245.15,253.15,263.15})for(const auto&r:relaxation_rows(mode,TK))conv<<(mode==Modulus::CONST?"CONST":"VAR")<<","<<TK<<","<<r.dt<<","<<r.err<<","<<r.stress<<","<<r.exact<<"\n";
 std::ofstream mat(out/"G04_material_parameters.csv");mat<<std::setprecision(17)<<"T_C,T_K,Arrhenius,Ad_1_s,E_CONST_Pa,E_VAR_Pa,G_CONST_Pa,G_VAR_Pa,Kd_Pa_inv,a_Pa_inv\n";
 for(double TC=-40;TC<=-5;TC+=1){double TK=TC+273.15;mat<<TC<<","<<TK<<","<<arrhenius(TK)<<","<<Ad_ref*arrhenius(TK)<<","<<modulus(TK,Modulus::CONST)<<","<<modulus(TK,Modulus::VAR)<<","<<modulus(TK,Modulus::CONST)/(2*(1+nu))<<","<<modulus(TK,Modulus::VAR)/(2*(1+nu))<<","<<Kd_SI<<","<<a<<"\n";}
 // A stress controlled loading + unloading, independent closed-form reference.
 std::ofstream rec(out/"G04_stress_controlled_recovery.csv");rec<<std::setprecision(17)<<"time_s,applied_shear_MPa,ed_xy,analytic_ed_xy\n";
 double TK=T_ref,Ad=Ad_ref*arrhenius(TK),stress=1.7e6, dt=5,ed=0;
 for(int k=1;k<=360;k++){
   double t=k*dt,s=(t<=600?stress:0.);
   ed=(ed+dt*Ad*a*s)/(1+dt*Ad);
   double ref=t<=600 ? a*stress*(1-exp(-Ad*t)): a*stress*(1-exp(-Ad*600))*exp(-Ad*(t-600));
   rec<<t<<","<<s/1e6<<","<<ed<<","<<ref<<"\n";
 }
 // Nonuniform temperature and imposed strain: illustrative standalone POINT path, NOT FEM output.
 std::ofstream hist(out/"G04_cooling_point_pilot.csv");hist<<std::setprecision(17)<<"model,time_s,temperature_C,ed_xy,sigma_xy_MPa,G_alg_Pa,free_energy_J_m3,dissipation_W_m3\n";
 for(auto mode:{Modulus::CONST,Modulus::VAR}){
  State state;auto ep=trial_strain();for(int k=1;k<=240;k++){
   double t=15*k,TC=-20-3*(1-exp(-t/300));double TK=TC+273.15;
   auto r=update(ep,TK,15,state,mode);state=r.new_state;
   hist<<(mode==Modulus::CONST?"CONST":"VAR")<<","<<t<<","<<TC<<","<<state.e_d[3]<<","<<r.sigma[3]/1e6<<","<<r.G_algorithmic<<","<<r.free_energy<<","<<r.dissipation_rate<<"\n";
  }
 }
 std::cout<<"CAMPAIGN files written to "<<out<<"\n";
}
int main(int argc,char**argv){
 try{
  string which="all";fs::path output;
  for(int k=1;k<argc;k++){string a0=argv[k];if(a0=="--test"&&k+1<argc)which=argv[++k];else if(a0=="--out"&&k+1<argc)output=argv[++k];else throw std::invalid_argument("Usage: stage3d04_ed_point [--test NAME] [--out DIR]");}
  std::map<string,std::function<void()>> tests={{"reference",reference},{"relaxation",relaxation},{"recovery",recovery},{"tangent",tangent},{"temperature",temperature},{"energy",energy},{"objectivity",objectivity},{"restart",restart}};
  if(which=="all")for(const auto&test:tests)test.second();else {auto t=tests.find(which);if(t==tests.end())throw std::invalid_argument("Unknown G04 test "+which);t->second();}
  if(!output.empty())generate(output);
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
