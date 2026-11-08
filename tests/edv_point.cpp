// Stage 3D-05 independent verification for the nonlinear EDV material update.
#include "edv_material.hpp"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <fstream>
#include <filesystem>
#include <functional>
#include <vector>
#include <map>
#include <algorithm>
#include <limits>
using namespace ice3d::edv;
using std::string;
namespace fs=std::filesystem;
void require(bool x,const string&msg){if(!x)throw std::runtime_error("G05 FAIL: "+msg);}
void near(double x,double y,double rel,double abs,const string&msg){
 if(!(std::abs(x-y)<=rel*std::max(std::abs(x),std::abs(y))+abs)){
  std::ostringstream s;s<<std::setprecision(17)<<"G05 "<<msg<<" got="<<x<<" expected="<<y;
  throw std::runtime_error(s.str());}}
Tensor strain(){return {0.0012,-0.0007,0.00032,0.00068,-0.00027,0.00018};}
State history(){State v;v.e_d={0.00013,-0.00009,-0.00004,0.00007,-0.00006,0.00011};
 v.e_v={0.00021,-0.00012,-0.00009,0.000032,0.000043,-0.000025}; return v;}
double max_C_rel=0,max_T_rel=0,max_energy_violation=0,max_residual=0;
std::array<std::array<double,3>,3> mat(const Tensor&v){return {{{v[0],v[3],v[5]},{v[3],v[1],v[4]},{v[5],v[4],v[2]}}};}
Tensor ten(const std::array<std::array<double,3>,3>&v){return {v[0][0],v[1][1],v[2][2],v[0][1],v[1][2],v[2][0]};}
Tensor rotate(const Tensor&v){
 auto x=mat(v);
 constexpr double phi=.48,psi=.61;
 double c=std::cos(phi),s=std::sin(phi),p=std::cos(psi),z=std::sin(psi);
 double Q[3][3]={{c*p,-s,c*z},{s*p,c,s*z},{-z,0,p}}; // Rz(phi)*Ry(psi)
 std::array<std::array<double,3>,3> out{};
 for(int i=0;i<3;i++)for(int j=0;j<3;j++)for(int a=0;a<3;a++)for(int b=0;b<3;b++)out[i][j]+=Q[i][a]*x[a][b]*Q[j][b];
 return ten(out);
}
void reference(){
 near(KN_ref_MPa,2.56e-7,1e-15,0,"K_N reference");
 near(KN_ref_SI*std::pow(1e6,m),2.56e-7,2e-15,0,"noninteger power MPa->Pa");
 near(arrhenius(T_arr_ref),1,1e-14,0,"Arrhenius reference");
 near(ice3d::ed::modulus(T_ref,Modulus::CONST),ice3d::ed::modulus(T_ref,Modulus::VAR),1e-14,0,"E branches Tref");
 for(auto mode:{Modulus::CONST,Modulus::VAR}){
  auto r=ice3d::edv::update({},T_ref,120,{},mode);
  near(r.q,0,0,0,"zero stress zero viscous creep");
  near(norm(r.new_state.e_v),0,0,0,"zero stress, zero viscous strain");
  Tensor hydro{0.0005,0.0005,0.0005,0,0,0};
  auto h=ice3d::edv::update(hydro,T_ref,120,{},mode);
  near(norm(h.new_state.e_d),0,0,1e-18,"purely hydrostatic ED");
  near(norm(h.new_state.e_v),0,0,1e-18,"purely hydrostatic EV");
  Tensor th{};for(int i=0;i<3;i++)th[i]=alpha*(245.15-T_ref);
  auto free=ice3d::edv::update(th,245.15,120,{},mode);
  near(norm(free.sigma),0,0,1e-7,"pure thermal strain has no stress");
  auto z=ice3d::edv::update(strain(),T_ref,0,{},mode);
  near(norm(z.new_state.e_d),0,0,0,"dt0 ED");
  near(norm(z.new_state.e_v),0,0,0,"dt0 EV");
 }
 bool threw=false;try{ice3d::edv::update(strain(),-20,20,{},Modulus::VAR);}catch(const std::invalid_argument&){threw=true;}
 require(threw,"Celsius input must be rejected");
 threw=false;try{auto state=history();state.e_v[0]=.2;ice3d::edv::update(strain(),T_ref,20,state,Modulus::VAR);}catch(const std::invalid_argument&){threw=true;}
 require(threw,"nondeviatoric EV history must be rejected");
 std::cout<<"G05_reference PASS: MPa^{-3.1} SI, T, hydrostatic, reference pair, no-load\n";
}
void implicit(){
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double TK:{240.15,T_ref,T_arr_ref})for(double dt:{0.,1.,10.,100.,600.}){
  auto pr=history();auto r=ice3d::edv::update(strain(),TK,dt,pr,mode);
  auto d=deviator(strain());
  Tensor diff=d;for(int i=0;i<6;i++)diff[i]-=r.new_state.e_d[i]+r.new_state.e_v[i];
  Tensor equilibrium=diff;for(int i=0;i<6;i++)equilibrium[i]=r.s[i]-2*r.G*diff[i];
  near(norm(equilibrium),0,0,2e-6,"deviatoric elastic closure");
  near(tr(r.s),0,0,2e-8,"deviatoric stress");
  near(tr(r.new_state.e_d),0,0,5e-17,"ED deviatoric");
  near(tr(r.new_state.e_v),0,0,5e-17,"EV deviatoric");
  const double b=dt*r.Ad;
  Tensor residualED{},residualEV{};
  for(int i=0;i<6;i++){
   residualED[i]=(1+b)*r.new_state.e_d[i]-pr.e_d[i]-b*a*r.s[i];
   residualEV[i]=r.new_state.e_v[i]-pr.e_v[i]-dt*1.5*r.KN*std::pow(r.q,m-1)*r.s[i];
  }
  near(norm(residualED),0,0,2e-16,"implicit ED residual");
  near(norm(residualEV),0,0,2e-16,"implicit EV residual");
  const double A=1/(2*r.G)+b*a/(1+b);
  Tensor rhs=deviator(strain());for(int i=0;i<6;i++)rhs[i]-=pr.e_v[i]+pr.e_d[i]/(1+b);
  double qtrial=std::sqrt(1.5)*norm(rhs)/A;
  double scal= r.q + (dt*1.5*r.KN/A)*std::pow(r.q,m)-qtrial;
  double rel=std::abs(scal)/std::max(1.0,qtrial);
  max_residual=std::max(max_residual,rel);
  require(rel<2e-12,"scalar nonlinear root residual");
  require(r.q>=0&&r.q<=qtrial*(1+1e-12),"nonnegative decreasing q");
 }
 // Deliberately strongly nonlinear, high-stress, nonzero-state test.
 for(double mult:{.01,1.,10.,50.}){
  auto ep=strain();for(auto&x:ep)x*=mult;
  auto r=ice3d::edv::update(ep,263.15,3600,history(),Modulus::VAR);
  require(r.iterations<100&&r.q>=0,"strong nonlinear root converges");
  require(std::abs(r.scalar_residual)<2e-12*std::max(1.,r.q_trial/MPa),"nonlinear root precision");
 }
 std::cout<<"G05_implicit PASS: back Euler, nonlinear root; max scalar relative residual="<<max_residual<<"\n";
}
void tangent(){
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double TK:{241.15,253.15,263.15})for(double dt:{0.,30.,300.,1800.}){
  auto ep=strain();auto pr=history(); auto r=ice3d::edv::update(ep,TK,dt,pr,mode);
  for(int j=0;j<6;j++){
   double h=1e-7;auto pp=ep,pm=ep;pp[j]+=h;pm[j]-=h;
   auto hi=ice3d::edv::update(pp,TK,dt,pr,mode),lo=ice3d::edv::update(pm,TK,dt,pr,mode);
   for(int i=0;i<6;i++){
    double fd=(hi.sigma[i]-lo.sigma[i])/(2*h);
    double rel=std::abs(fd-r.tangent[i][j])/std::max({1.,std::abs(fd),std::abs(r.tangent[i][j])});
    max_C_rel=std::max(rel,max_C_rel);
    require(rel<2e-7,"algorithmic tangent against central FD");
   }
  }
  // symmetry is weighted by tensor shear (engineering strain columns are different)
  for(int i=0;i<6;i++)for(int j=0;j<6;j++)
   near(r.tangent[i][j]/(j>=3?2.:1.),r.tangent[j][i]/(i>=3?2.:1.),5e-13,.000001,"energy symmetric tangent (engineering shear)");
  require(r.tangent[0][0]>0&&r.tangent[3][3]>0,"stable algorithmic stiffness");
 }
 std::cout<<"G05_tangent PASS: max rel="<<std::setprecision(12)<<max_C_rel<<"\n";
}
void temperature(){
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double TK:{243.15,253.15,263.15})for(double dt:{0.,20.,300.,1800.}){
  auto ep=strain();auto pr=history();auto r=ice3d::edv::update(ep,TK,dt,pr,mode);
  const double h=0.001;
  auto rp=ice3d::edv::update(ep,TK+h,dt,pr,mode),rm=ice3d::edv::update(ep,TK-h,dt,pr,mode);
  for(int i=0;i<6;i++){
   double fd=(rp.sigma[i]-rm.sigma[i])/(2*h);
   double rel=std::abs(fd-r.d_sigma_dT[i])/std::max({1.,std::abs(fd),std::abs(r.d_sigma_dT[i])});
   max_T_rel=std::max(max_T_rel,rel);
   require(rel<4e-7,"full temperature derivative E, Ad, KN, thermal strain");
  }
 }
 std::cout<<"G05_temperature PASS: max rel="<<std::setprecision(12)<<max_T_rel<<"\n";
}
void energy(){
 // Frozen temperature: discrete free-energy inequality including both inelastic mechanisms.
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double TK:{242.15,253.15,263.15})for(double dt:{0.1,5.,100.,900.}){
  auto pr=history();auto ep=strain();auto oldeps=ep;
  for(int i=0;i<6;i++)oldeps[i]*=.75;
  auto old=ice3d::edv::update(oldeps,TK,0,pr,mode);
  auto now=ice3d::edv::update(ep,TK,dt,pr,mode);
  const double work=dot(now.sigma,{ep[0]-oldeps[0],ep[1]-oldeps[1],ep[2]-oldeps[2],ep[3]-oldeps[3],ep[4]-oldeps[4],ep[5]-oldeps[5]});
  const double inequality=now.free_energy-old.free_energy+dt*now.dissipation_rate-work;
  max_energy_violation=std::max(max_energy_violation,inequality);
  require(inequality<1e-5*std::max({1.,std::abs(now.free_energy),std::abs(old.free_energy),std::abs(work)}),"isothermal discrete energy inequality");
  require(now.dissipation_ED>=0&&now.dissipation_EV>=0&&now.dissipation_rate>=0,"nonnegative dissipation");
 }
 std::cout<<"G05_energy PASS: positive ED+EV dissipation and discrete isothermal energy inequality\n";
}
void objectivity(){
 for(auto mode:{Modulus::CONST,Modulus::VAR}){
  auto ep=strain();auto pr=history();auto r=ice3d::edv::update(ep,249.15,300,pr,mode);
  State rp;rp.e_d=rotate(pr.e_d);rp.e_v=rotate(pr.e_v);
  auto rr=ice3d::edv::update(rotate(ep),249.15,300,rp,mode);
  auto rs=rotate(r.sigma),re=rotate(r.new_state.e_d),rv=rotate(r.new_state.e_v);
  for(int i=0;i<6;i++){
   near(rr.sigma[i],rs[i],1e-10,1e-5,"rotated stress");
   near(rr.new_state.e_d[i],re[i],1e-10,1e-16,"rotated ED history");
   near(rr.new_state.e_v[i],rv[i],1e-10,1e-16,"rotated EV history");
  }
  near(rr.free_energy,r.free_energy,1e-12,1e-4,"isotropic energy");
  near(rr.dissipation_rate,r.dissipation_rate,1e-12,1e-5,"isotropic dissipation");
 }
 std::cout<<"G05_objectivity PASS: 3D tensor rotation covariance\n";
}
void stress_control(){
 // Prescribed deviatoric stress -- independent analytic BE ED and linear-in-time EV.
 const double TK=T_arr_ref,dt=10,tf=3600;
 const Tensor imposed{1.2e6,-0.6e6,-0.6e6,0.4e6,0.,0.};
 const double q=std::sqrt(1.5)*norm(imposed);
 const double Ad=Ad_ref*arrhenius(TK),Kn=KN_ref_SI*arrhenius(TK);
 State s;
 for(int k=0;k<int(tf/dt);k++){
  for(int i=0;i<6;i++){
   s.e_d[i]=(s.e_d[i]+dt*Ad*a*imposed[i])/(1+dt*Ad);
   s.e_v[i]+=dt*1.5*Kn*std::pow(q,m-1)*imposed[i];
  }
 }
 for(int i=0;i<6;i++){
  near(s.e_d[i],a*imposed[i]*(1-std::pow(1+dt*Ad,-int(tf/dt))),3e-13,2e-16,"prescribed stress ED analytic BE");
  near(s.e_v[i],tf*1.5*Kn*std::pow(q,m-1)*imposed[i],3e-13,2e-16,"prescribed stress EV exact linear rate");
 }
 // Show consistency of strain-controlled material updater with imposed stress and prescribed history.
 const double G=ice3d::ed::modulus(TK,Modulus::CONST)/(2*(1+nu));
 State prev=history();
 const double b=dt*Ad,beta=dt*1.5*Kn;
 Tensor nextEd{},nextEv{},eps{};
 for(int i=0;i<6;i++){
  nextEd[i]=(prev.e_d[i]+b*a*imposed[i])/(1+b);
  nextEv[i]=prev.e_v[i]+beta*std::pow(q,m-1)*imposed[i];
  eps[i]=nextEd[i]+nextEv[i]+imposed[i]/(2*G);
 }
 auto r=ice3d::edv::update(eps,TK,dt,prev,Modulus::CONST);
 for(int i=0;i<6;i++)near(r.s[i],imposed[i],3e-12,2e-5,"EDV strain solver vs independently imposed stress");
 std::cout<<"G05_stress_control PASS: exact constant-stress viscous creep and ED backward Euler\n";
}
void limits(){
 // EDV disables e_v and must reproduce Stage 3D-04 ED exactly including C and dσ/dT.
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(double TK:{243.15,T_ref,263.15})for(double dt:{0.,30.,120.,600.}){
  auto ep=strain();ice3d::ed::State edst;edst.e_d=history().e_d;
  State st;st.e_d=edst.e_d;
  auto old=ice3d::ed::update(ep,TK,dt,edst,mode);
  auto now=ice3d::edv::update(ep,TK,dt,st,mode,{true,false});
  for(int i=0;i<6;i++){
   near(now.sigma[i],old.sigma[i],3e-14,1e-6,"ED-only stress");
   near(now.new_state.e_d[i],old.new_state.e_d[i],3e-14,1e-16,"ED-only internal state");
   near(now.d_sigma_dT[i],old.d_sigma_dT[i],2e-11,.01,"ED-only dσ/dT");
   for(int j=0;j<6;j++)near(now.tangent[i][j],old.tangent[i][j],2e-14,1e-5,"ED-only tangent");
  }
  near(norm(now.new_state.e_v),0,0,0,"EV off");
  auto pure=ice3d::edv::update(ep,TK,dt,{},mode,{false,false});
  auto pure0=ice3d::edv::update(ep,TK,0,{},mode);
  for(int i=0;i<6;i++)near(pure.sigma[i],pure0.sigma[i],3e-14,1e-7,"pure E limit");
 }
 std::cout<<"G05_limits PASS: EDV->ED->E exact backward compatibility\n";
}
void restart(){
 for(auto mode:{Modulus::CONST,Modulus::VAR}){
  State state;auto ep=strain();
  for(int k=0;k<12;k++){
   const auto r=ice3d::edv::update(ep,243.15+.4*k,35,state,mode);state=r.new_state;
  }
  std::stringstream ss;ss<<std::setprecision(17);
  for(double x:state.e_d)ss<<x<<" ";
  for(double x:state.e_v)ss<<x<<" ";
  State restore;for(double&x:restore.e_d)ss>>x;for(double&x:restore.e_v)ss>>x;
  auto a=ice3d::edv::update(ep,252.15,45,state,mode),b=ice3d::edv::update(ep,252.15,45,restore,mode);
  for(int i=0;i<6;i++){
   near(a.sigma[i],b.sigma[i],0,0,"restart stress");
   near(a.new_state.e_d[i],b.new_state.e_d[i],0,0,"restart ED");
   near(a.new_state.e_v[i],b.new_state.e_v[i],0,0,"restart EV");
  }
 }
 std::cout<<"G05_restart PASS: deterministic serialized history for both states\n";
}
void temporal(){
 // Convergence against a substantially finer BE solution (not claimed as exact solution).
 const double tf=600.;std::vector<std::pair<double,double>> seq;
 Tensor ep=strain();
 auto integrate=[&](int n){State st;Response r;const double dt=tf/n;
  for(int k=1;k<=n;k++){r=ice3d::edv::update(ep,T_ref,dt,st,Modulus::CONST);st=r.new_state;}
  return r;};
 const auto fine=integrate(8192);
 for(int n:{8,16,32,64,128,256,512}){
  auto r=integrate(n);
  seq.push_back({tf/n,norm({r.sigma[0]-fine.sigma[0],r.sigma[1]-fine.sigma[1],r.sigma[2]-fine.sigma[2],r.sigma[3]-fine.sigma[3],r.sigma[4]-fine.sigma[4],r.sigma[5]-fine.sigma[5]})});
 }
 for(std::size_t k=1;k<seq.size();k++) require(seq[k].second<seq[k-1].second,"time convergence EDV BE");
 require(seq.back().second<seq.front().second/10,"large convergence decrease");
 std::cout<<"G05_temporal PASS: EDV implicit time convergence; error coarse="<<seq[0].second<<" refined="<<seq.back().second<<" Pa\n";
}
void campaign(const fs::path&out){
 fs::create_directories(out);
 {
 std::ofstream csv(out/"G05_point_cooling.csv");
 csv<<"mode,time_s,T_K,T_C,eps_xy,sigma_xy_MPa,q_MPa,e_d_xy,e_v_xy,psi_J_m3,dissipation_W_m3,local_iters,scalar_residual\n";
 csv<<std::setprecision(17);
 for(auto mode:{Modulus::CONST,Modulus::VAR}){
  State state;const double dt=15,tf=3600;
  auto ep=strain();
  for(int k=0;k<=int(tf/dt);k++){
   const double t=k*dt;
   const double TK=T_ref-3*(1-std::exp(-t/300));
   auto r=ice3d::edv::update(ep,TK,(k==0?0:dt),state,mode);
   state=r.new_state;
   csv<<(mode==Modulus::CONST?"CONST":"VAR")<<','<<t<<','<<TK<<','<<TK-273.15<<','<<ep[3]<<','<<r.sigma[3]/MPa<<','<<r.q/MPa<<','<<state.e_d[3]<<','<<state.e_v[3]<<','<<r.free_energy<<','<<r.dissipation_rate<<','<<r.iterations<<','<<r.scalar_residual<<'\n';
  }
 }
 }
 {
 std::ofstream csv(out/"G05_time_convergence.csv");csv<<"n_steps,dt_s,sigma_xy_MPa,relative_stress_error_against_8192,ev_xy,ed_xy\n";csv<<std::setprecision(17);
 auto solve=[&](int n){State st;Response r;auto ep=strain();
 for(int i=0;i<n;i++){r=ice3d::edv::update(ep,T_ref,600./n,st,Modulus::CONST);st=r.new_state;}return r;};
 auto exact=solve(8192);
 for(int n:{8,16,32,64,128,256,512,1024,8192}){auto r=solve(n);
 csv<<n<<','<<600./n<<','<<r.sigma[3]/MPa<<','<<std::abs(r.sigma[3]-exact.sigma[3])/std::max(1.,std::abs(exact.sigma[3]))<<','<<r.new_state.e_v[3]<<','<<r.new_state.e_d[3]<<'\n';}
 }
 {
 std::ofstream csv(out/"G05_E_ED_EDV_pairs.csv");
 csv<<"model,mode,time_s,T_C,sigma_xy_MPa,q_MPa,e_d_xy,e_v_xy,free_energy_J_m3,dissipation_W_m3\n";
 csv<<std::setprecision(17);
 for(auto mode:{Modulus::CONST,Modulus::VAR})for(int model=0;model<3;model++){
  Controls flags{model>=1,model>=2};State state;
  for(int k=0;k<=240;k++){
   double t=15.*k,TK=T_ref-3*(1-std::exp(-t/300));
   auto r=ice3d::edv::update(strain(),TK,(k==0?0:15),state,mode,flags);
   state=r.new_state;
   csv<<(model==0?"E":model==1?"ED":"EDV")<<','<<(mode==Modulus::CONST?"CONST":"VAR")<<','<<t<<','<<TK-273.15<<','<<r.sigma[3]/MPa<<','<<r.q/MPa<<','<<state.e_d[3]<<','<<state.e_v[3]<<','<<r.free_energy<<','<<r.dissipation_rate<<'\n';
  }
 }
 }
 {
 std::ofstream csv(out/"G05_reference_STRESS_control.csv");csv<<"T_K,q_MPa,s_xy_MPa,ED_rate_xy_per_s,EV_rate_xy_per_s\n";
 for(double TK:{243.15,253.15,263.15}){
  Tensor s{1.2e6,-.6e6,-.6e6,.4e6,0,0};double q=std::sqrt(1.5)*norm(s);
  double Ar=arrhenius(TK);
  csv<<std::setprecision(17)<<TK<<','<<q/MPa<<','<<s[3]/MPa<<','<<Ad_ref*Ar*a*s[3]<<','<<1.5*KN_ref_SI*Ar*std::pow(q,m-1)*s[3]<<'\n';
 }
 }
}
int main(int argc,char**argv){
 try{
  std::map<string,std::function<void()>> tests={{"reference",reference},{"implicit",implicit},{"tangent",tangent},{"temperature",temperature},{"energy",energy},{"objectivity",objectivity},{"stress_control",stress_control},{"limits",limits},{"restart",restart},{"temporal",temporal}};
  string selected="all",out;
  for(int i=1;i<argc;i++){
   if(string(argv[i])=="--test"&&i+1<argc)selected=argv[++i];
   else if(string(argv[i])=="--out"&&i+1<argc)out=argv[++i];
   else throw std::invalid_argument("Usage: --test <name|all> [--out DIR]");
  }
  if(selected=="all")for(auto&[name,fun]:tests)fun();
  else{auto iter=tests.find(selected);if(iter==tests.end())throw std::invalid_argument("unknown test: "+selected);iter->second();}
  if(!out.empty()){campaign(out);std::cout<<"WROTE results in "<<out<<'\n';}
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
