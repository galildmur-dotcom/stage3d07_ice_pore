// Stage 3D-10B: analytical JVP/VJP of the actual E/ED/EDV material update.
// Independent FD validation is used ONLY in this test, not in the operator.
#include "stage3d10b_edv_linearization.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Tensor=ice3d::p10b::Tensor;
using State=ice3d::p10b::State;
using Controls=ice3d::p10b::Controls;
using Modulus=ice3d::p10b::Modulus;
using Linearization=ice3d::p10b::Linearization;

double euclid(const Tensor&a,const Tensor&b){return ice3d::p10b::euclid_dot(a,b);}
double bilinear(const State&a,const State&b){return euclid(a.e_d,b.e_d)+euclid(a.e_v,b.e_v);}
void add(Tensor&v,const Tensor&u,double scale){for(int i=0;i<6;++i)v[i]+=scale*u[i];}
void add(State&v,const State&u,double scale){add(v.e_d,u.e_d,scale);add(v.e_v,u.e_v,scale);}
void set_dev(Tensor&v,int k,double h){
 if(k==0){v[0]=h;v[2]=-h;}
 else if(k==1){v[1]=h;v[2]=-h;}
 else v[k+1]=h;
}
struct Inputs{Tensor eps{};double T=0;State state{};};
Inputs base(int scene,Controls c){
 Inputs x;
 if(scene==0){
  x.eps={1.2e-4,-5e-5,-7e-5,2e-5,-3e-5,2e-5};x.T=251.65;
  if(c.delayed)x.state.e_d={4e-6,-2e-6,-2e-6,1e-6,2e-6,-1e-6};
  if(c.viscous)x.state.e_v={2e-7,-5e-7,3e-7,1e-7,-1e-7,3e-7};
 }else{
  x.eps={1.1e-4,1.1e-4,1.1e-4,0,0,0};x.T=253.15;
  // Zero deviatoric stress tests the q=0 constitutive branch.
 }
 return x;
}
struct Dir{Tensor eps{};double T=0;State previous{};};
Dir direction(int k,Controls c){
 Dir d;
 if(k<6)d.eps[k]=1e-4;
 else if(k==6)d.T=1.;
 else{
  int id=k-7;
  if(c.delayed){if(id<5){set_dev(d.previous.e_d,id,1e-6);return d;}id-=5;}
  if(c.viscous)set_dev(d.previous.e_v,id,2e-7);
 }
 return d;
}
ice3d::p10b::Differential fd(const Inputs&base,const Dir&d,double h,
                                 double dt,Modulus mod,Controls c){
 auto p=base,m=base;
 add(p.eps,d.eps,h);add(m.eps,d.eps,-h);
 p.T+=h*d.T;m.T-=h*d.T;
 add(p.state,d.previous,h);add(m.state,d.previous,-h);
 const auto rp=ice3d::edv::update(p.eps,p.T,dt,p.state,mod,c);
 const auto rm=ice3d::edv::update(m.eps,m.T,dt,m.state,mod,c);
 ice3d::p10b::Differential out;
 for(int i=0;i<6;++i){
  out.d_sigma[i]=(rp.sigma[i]-rm.sigma[i])/(2*h);
  out.d_new.e_d[i]=(rp.new_state.e_d[i]-rm.new_state.e_d[i])/(2*h);
  out.d_new.e_v[i]=(rp.new_state.e_v[i]-rm.new_state.e_v[i])/(2*h);
 }
 return out;
}
constexpr int historySteps=12;
constexpr double sigmaRef=1.0e6;
struct HistoryInput {Tensor eps{},d_eps_da{};double T=0,dT_da=.75;};
HistoryInput scripted(int n,double a){
 const double phase=.36*n;
 HistoryInput x;
 x.d_eps_da={2e-5*(.5+std::cos(phase)),-7e-6,3e-6,5e-6,2e-6,-4e-6};
 x.eps={1.30e-4*std::sin(phase),-0.50e-4*std::sin(phase),
        -0.35e-4*std::sin(phase),0.23e-4*std::cos(phase),
        -0.12e-4*std::sin(.7*phase),0.16e-4*std::cos(.8*phase)};
 add(x.eps,x.d_eps_da,a);
 x.T=250.-2.3*std::sin(.22*n)+a*x.dT_da;
 return x;
}
double history_integrand(const ice3d::p10b::Response&r,Controls c){
 const double sx=r.sigma[0]/sigmaRef,sxy=r.sigma[3]/sigmaRef;
 double stateEnergy=0;
 if(c.delayed)stateEnergy+=euclid(r.new_state.e_d,r.new_state.e_d);
 if(c.viscous)stateEnergy+=euclid(r.new_state.e_v,r.new_state.e_v);
 return (.23*sx+.12*sxy+.5*(sx*sx+sxy*sxy)+1e8*stateEnergy)/historySteps;
}
double history_forward(double a,Modulus mod,Controls c,std::vector<State>*states){
 State z{};double J=0;
 if(states){states->clear();states->push_back(z);}
 for(int n=1;n<=historySteps;++n){
  const auto x=scripted(n,a);
  const auto r=ice3d::edv::update(x.eps,x.T,300.,z,mod,c);
  J+=history_integrand(r,c);z=r.new_state;
  if(states)states->push_back(z);
 }
 return J;
}
double history_reverse(double a,Modulus mod,Controls c){
 std::vector<State> states;
 (void)history_forward(a,mod,c,&states);
 State lambda_future{};double grad=0;
 for(int n=historySteps;n>=1;--n){
  const auto x=scripted(n,a);
  const Linearization L(x.eps,x.T,300.,states[n-1],mod,c);
  const double sx=L.response.sigma[0]/sigmaRef;
  const double sxy=L.response.sigma[3]/sigmaRef;
  Tensor lambda_sigma{};
  lambda_sigma[0]=(.23+sx)/(historySteps*sigmaRef);
  lambda_sigma[3]=(.12+sxy)/(historySteps*sigmaRef);
  State lambda_new=lambda_future;
  for(int i=0;i<6;++i){
   if(c.delayed)lambda_new.e_d[i]+=2e8*states[n].e_d[i]/historySteps;
   if(c.viscous)lambda_new.e_v[i]+=2e8*states[n].e_v[i]/historySteps;
  }
  const auto pb=L.vjp(lambda_sigma,lambda_new);
  grad+=euclid(pb.d_eps,x.d_eps_da)+pb.d_T*x.dT_da;
  lambda_future=pb.d_previous;
 }
 return grad;
}
}
int main(){try{
 int cases=0,directions=0;double worstJvpRel=0,worstDot=0,worstTangent=0,worstHistoryRel=0;
 for(const std::string name:{"E","ED","EDV"})
 for(const Modulus mod:{Modulus::CONST,Modulus::VAR})
 for(int scene=0;scene<2;++scene){
  const Controls c{name!="E",name=="EDV"};
  const Inputs x=base(scene,c);
  constexpr double dt=300.;
  const Linearization L(x.eps,x.T,dt,x.state,mod,c);
  const int ndim=7+(c.delayed?5:0)+(c.viscous?5:0);
  State lambdaNew{};
  for(int i=0;i<6;++i){
   if(c.delayed)lambdaNew.e_d[i]=1.0e4*std::cos(.5*(i+1));
   if(c.viscous)lambdaNew.e_v[i]=2.0e4*std::sin(.8*(i+1));
  }
  Tensor lambdaSigma{};
  for(int i=0;i<6;++i)lambdaSigma[i]=1.0e-6*std::sin(.4*(i+1));
  const auto back=L.vjp(lambdaSigma,lambdaNew);
  for(int k=0;k<ndim;++k){
   const Dir d=direction(k,c);
   const auto exact=L.jvp(d.eps,d.T,d.previous);
   const auto numeric=fd(x,d,1.0e-4,dt,mod,c);
   double maxRel=0;
   for(int i=0;i<6;++i){
    const double ds=std::abs(exact.d_sigma[i]-numeric.d_sigma[i]);
    if(ds>0.03+5e-5*std::abs(numeric.d_sigma[i]))
     throw std::runtime_error("Stress JVP/FD mismatch: "+name);
    const double dd=std::abs(exact.d_new.e_d[i]-numeric.d_new.e_d[i]);
    const double dv=std::abs(exact.d_new.e_v[i]-numeric.d_new.e_v[i]);
    if(dd>3e-12+5e-4*std::abs(numeric.d_new.e_d[i])||
       dv>3e-12+5e-4*std::abs(numeric.d_new.e_v[i]))
     throw std::runtime_error("History JVP/FD mismatch: "+name);
    maxRel=std::max(maxRel,ds/std::max(1.,std::abs(numeric.d_sigma[i])));
   }
   worstJvpRel=std::max(worstJvpRel,maxRel);
   const double lhs=euclid(lambdaSigma,exact.d_sigma)+bilinear(lambdaNew,exact.d_new);
   const double rhs=euclid(back.d_eps,d.eps)+back.d_T*d.T+
                    bilinear(back.d_previous,d.previous);
   const double dotErr=std::abs(lhs-rhs)/std::max({1.,std::abs(lhs),std::abs(rhs)});
   worstDot=std::max(worstDot,dotErr);
   if(dotErr>2e-11)throw std::runtime_error("Analytic JVP/VJP transpose failure: "+name);
   ++directions;
  }
  // Validate stress derivatives against the already existing analytic tangents.
  for(int k=0;k<7;++k){
   Tensor de{};double dT=0;
   if(k<6)de[k]=1.;else dT=1.;
   const auto dx=L.jvp(de,dT,State{});
   for(int i=0;i<6;++i){
    const double old=k==6?L.response.d_sigma_dT[i]:L.response.tangent[i][k];
    const double err=std::abs(dx.d_sigma[i]-old)/std::max(1.,std::abs(old));
    worstTangent=std::max(worstTangent,err);
    if(err>2e-11)throw std::runtime_error("P10B tangent inconsistency: "+name);
   }
  }
  ++cases;
 }
 if(cases!=12||directions!=144)throw std::runtime_error("Missing case/direction");
 for(const std::string law:{"E","ED","EDV"})
 for(const Modulus mod:{Modulus::CONST,Modulus::VAR}){
  const Controls c{law!="E",law=="EDV"};
  constexpr double a=.037,h=5e-4;
  const double adj=history_reverse(a,mod,c);
  const double fullFD=(history_forward(a+h,mod,c,nullptr)-
                       history_forward(a-h,mod,c,nullptr))/(2*h);
  const double err=std::abs(adj-fullFD)/std::max(1e-10,std::abs(fullFD));
  worstHistoryRel=std::max(worstHistoryRel,err);
  if(err>3e-7)throw std::runtime_error("Analytic history reverse mismatch: "+law);
 }
 std::cout<<std::setprecision(12)
  <<"P10B_EDV_LINEARIZATION_OK models=6 scenes=2 directions="<<directions
  <<" worst_JVP_FD_rel="<<worstJvpRel
  <<" worst_transpose_rel="<<worstDot
  <<" worst_old_tangent_rel="<<worstTangent
  <<" worst_12step_history_rel="<<worstHistoryRel<<"\n";
 return 0;
}catch(const std::exception&e){
 std::cerr<<"P10B_EDV_LINEARIZATION_ERROR: "<<e.what()<<"\n";return 2;
}}
