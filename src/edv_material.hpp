#pragma once
// Stage 3D-05: canonical E + ED + EDV pointwise constitutive update.
// SI inputs/outputs: strains are dimensionless, sigma in Pa, time s, T in K.
// Tensor order [xx,yy,zz,xy,yz,zx], tensor shear (not engineering shear).
// State holds separate, deviatoric e_d and e_v; does not modify previous state.
#include "ed_material.hpp"
#include <limits>
#include <numbers>

namespace ice3d::edv {
using ed::Tensor; using ed::Matrix; using ed::Modulus;
using ed::tr; using ed::norm; using ed::dot; using ed::deviator;
using ed::E_ref; using ed::nu; using ed::alpha; using ed::T_ref;
using ed::T_arr_ref; using ed::gas_R; using ed::Q;
using ed::Ad_ref; using ed::Kd_SI; using ed::a;
constexpr double KN_ref_MPa = 2.56e-7; // MPa^{-m} / second
constexpr double m=3.1;
constexpr double MPa=1.0e6;
inline const double KN_ref_SI=KN_ref_MPa/std::pow(MPa,m); // Pa^{-m}/s
inline const double C_ref_SI=1.5*KN_ref_SI; // 3/2 K_N
struct State { Tensor e_d{}, e_v{}; };
struct Controls { bool delayed=true; bool viscous=true; };
struct Response {
 Tensor sigma{}, s{}, d_sigma_dT{};
 State new_state{};
 Matrix tangent{};
 double E=0,G=0,K=0,Ad=0,KN=0,q=0,q_trial=0;
 double scalar_residual=0,local_factor=0;
 int iterations=0;
 double free_energy=0,dissipation_rate=0,dissipation_ED=0,dissipation_EV=0;
};
inline double arrhenius(double TK) {return ed::arrhenius(TK);}
inline void validate_state(const State& st,double TK,double dt) {
 if(!std::isfinite(TK)|| !(TK>170 && TK<330))throw std::invalid_argument("EDV: temperature in Kelvin must be in (170,330)");
 if(!std::isfinite(dt)||dt<0)throw std::invalid_argument("EDV: dt must be nonnegative");
 for(const Tensor* t:{&st.e_d,&st.e_v}){
  for(double x:*t)if(!std::isfinite(x))throw std::invalid_argument("EDV: nonfinite history");
  if(std::abs(tr(*t))>1e-11*std::max(1.,norm(*t)))throw std::invalid_argument("EDV: nondeviatoric history");
 }
}
// Scalar equation in MPa, x=q/1e6; x + theta*x^m = x_trial;
// monotonically increasing for x>=0. Safeguarded Newton with [0,x_trial].
struct ScalarRoot {double x=0,residual=0; int iterations=0;};
inline ScalarRoot scalar_root(double xtrial,double theta){
 if(!(xtrial>=0 && theta>=0)||!std::isfinite(xtrial)||!std::isfinite(theta))
  throw std::invalid_argument("EDV: invalid scalar input");
 if(xtrial==0||theta==0)return {xtrial,0,0};
 double lo=0,hi=xtrial;
 double x=xtrial/(1+theta*std::pow(xtrial,m-1));
 if(!(x>0 && x<hi))x=hi*.5;
 double f=0;
 int i=0;
 for(;i<100;i++){
  const double xm=std::pow(x,m-1);
  f=x*(1+theta*xm)-xtrial;
  if(std::abs(f)<=4e-14*std::max(1.,xtrial))break;
  if(f>0)hi=x; else lo=x;
  const double dx=f/(1+m*theta*xm);
  const double next=x-dx;
  x=(next>lo&&next<hi&&std::isfinite(next))?next:(lo+hi)*.5;
 }
 const double res=x*(1+theta*std::pow(x,m-1))-xtrial;
 if(i>=100 || std::abs(res)>2e-12*std::max(1.,xtrial))
  throw std::runtime_error("EDV: scalar nonlinear solve did not converge");
 return {x,res,i};
}
// Inverse derivative of A*s+beta*q^{m-1}*s = rhs, decomposed along s and perpendicular to s.
// A [Pa^-1], beta [Pa^-m], q [Pa].
inline Tensor inverse_apply(Tensor rhs, const Tensor& s, double q,double A,double beta){
 double f= (q>0 && beta>0)?(beta*std::pow(q,m-1)):0;
 double perp=1/(A+f), radial=1/(A+m*f);
 if(q==0)return {rhs[0]*perp,rhs[1]*perp,rhs[2]*perp,rhs[3]*perp,rhs[4]*perp,rhs[5]*perp};
 const double ss=dot(s,s);
 const double proj=dot(s,rhs)/ss;
 for(int i=0;i<6;i++)rhs[i]=perp*rhs[i]+(radial-perp)*s[i]*proj;
 return rhs;
}
inline Response update(const Tensor& eps,double TK,double dt,const State& prev,Modulus mode,Controls flags={}){
 validate_state(prev,TK,dt);
 for(double x:eps)if(!std::isfinite(x))throw std::invalid_argument("EDV: nonfinite input strain");
 if(!flags.delayed && norm(prev.e_d)>1e-16)throw std::invalid_argument("EDV: disabling ED requires zero ED history");
 if(!flags.viscous && norm(prev.e_v)>1e-16)throw std::invalid_argument("EDV: disabling EV requires zero EV history");
 Response r; r.E=ed::modulus(TK,mode);
 if(!(r.E>0))throw std::invalid_argument("EDV: nonpositive modulus");
 r.G=r.E/(2*(1+nu));r.K=r.E/(3*(1-2*nu));
 const double Af=arrhenius(TK);
 r.Ad= flags.delayed ? Ad_ref*Af:0;
 r.KN= flags.viscous ? KN_ref_SI*Af:0;
 const double b=dt*r.Ad, beta=dt*1.5*r.KN;
 // e_d=(e_d^n + b*a*s)/(1+b); e_v=e_v^n+beta*q^{m-1}*s
 const double A=1/(2*r.G) + b*a/(1+b);
 const double dA_dT =-ed::dmodulus(mode)/(2*(1+nu)*2*r.G*r.G)
                     + a*(b*ed::dlnarr_dT(TK))/((1+b)*(1+b));
 const double dBeta_dT =beta*ed::dlnarr_dT(TK);
 const double db_dT=b*ed::dlnarr_dT(TK);
 Tensor d=deviator(eps), rhs=d;
 for(int i=0;i<6;i++)rhs[i]-=prev.e_v[i]+prev.e_d[i]/(1+b);
 // First scalar magnitude equation in MPa; beta*q^(m-1)/A = theta*(q/MPa)^(m-1)
 const double trialq=std::sqrt(1.5)*norm(rhs)/A;
 r.q_trial=trialq;
 const double theta= (beta==0)?0:(beta*std::pow(MPa,m-1)/A);
 auto root=scalar_root(trialq/MPa,theta);
 r.iterations=root.iterations;
 r.scalar_residual=root.residual;
 r.q=root.x*MPa;
 r.local_factor=(trialq==0)?1.:r.q/trialq;
 for(int i=0;i<6;i++)r.s[i]=(rhs[i]/A)*r.local_factor;
 const double qpow=(r.q==0)?0:std::pow(r.q,m-1);
 for(int i=0;i<6;i++){
  r.new_state.e_d[i]=(prev.e_d[i]+b*a*r.s[i])/(1+b);
  r.new_state.e_v[i]=prev.e_v[i]+beta*qpow*r.s[i];
 }
 const double volum=tr(eps)-3*alpha*(TK-T_ref);
 r.sigma=r.s;for(int i=0;i<3;i++)r.sigma[i]+=r.K*volum;
 const double dE=ed::dmodulus(mode),dK=dE/(3*(1-2*nu));
 // d rhs/dT = e_d^old * b'/(1+b)^2 (prev states fixed during local differentiation)
 Tensor temp_rhs{};
 for(int i=0;i<6;i++) temp_rhs[i]=prev.e_d[i]*db_dT/((1+b)*(1+b))
                -(dA_dT+dBeta_dT*qpow)*r.s[i];
 auto dsdt=inverse_apply(temp_rhs,r.s,r.q,A,beta);
 for(int i=0;i<6;i++)r.d_sigma_dT[i]=dsdt[i]+(i<3?dK*volum-3*r.K*alpha:0);
 // Consistent 6x6 tangent with tensor shear; dot product weights off-diagonals by 2.
 const double perp=1/(A+beta*qpow);
 const double radial=1/(A+m*beta*qpow);
 const double ss=dot(r.s,r.s);
 for(int j=0;j<6;j++){
  Tensor ej{};ej[j]=1;
  Tensor pd=deviator(ej);
  Tensor col=pd;
  double projection=ss>0?dot(r.s,pd)/ss:0;
  for(int i=0;i<6;i++)col[i]=perp*pd[i]+(radial-perp)*r.s[i]*projection;
  for(int i=0;i<6;i++)r.tangent[i][j]=col[i]+(i<3&&j<3?r.K:0);
 }
 Tensor elastic=d;
 for(int i=0;i<6;i++)elastic[i]-=r.new_state.e_d[i]+r.new_state.e_v[i];
 r.free_energy=0.5*r.K*volum*volum + r.G*dot(elastic,elastic)+dot(r.new_state.e_d,r.new_state.e_d)/(2*a);
 Tensor drive=r.s;
 for(int i=0;i<6;i++)drive[i]-=r.new_state.e_d[i]/a;
 r.dissipation_ED=r.Ad*a*dot(drive,drive);
 r.dissipation_EV=(r.q==0?0:1.5*r.KN*qpow*dot(r.s,r.s));
 r.dissipation_rate=r.dissipation_ED+r.dissipation_EV;
 if(!std::isfinite(r.free_energy)||!std::isfinite(r.dissipation_rate))
   throw std::runtime_error("EDV: nonfinite energy/dissipation");
 return r;
}
} // namespace ice3d::edv
