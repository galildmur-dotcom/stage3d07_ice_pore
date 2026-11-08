#pragma once
// Stage 3D-10B: analytic JVP and Euclidean-Voigt VJP of the fully discrete
// E/ED/EDV update. No local finite differences are used by these operators.
// Tensor order: xx,yy,zz,xy,yz,zx (tensor shear). Physical contraction of
// deviatoric tensors uses weights (1,1,1,2,2,2); algebraic VJP uses the
// ordinary Euclidean pairing of the six stored Voigt components.
#include "edv_material.hpp"
#include <algorithm>
#include <cmath>

namespace ice3d::p10b {
using Tensor=edv::Tensor;
using State=edv::State;
using Controls=edv::Controls;
using Modulus=edv::Modulus;
using Response=edv::Response;

inline double euclid_dot(const Tensor& a,const Tensor& b){
 double v=0;for(int i=0;i<6;++i)v+=a[i]*b[i];return v;
}
inline Tensor weighted(Tensor v,bool inverse){
 for(int i=3;i<6;++i)v[i]*=inverse?.5:2.;
 return v;
}
inline Tensor apply_q_derivative(const Tensor& v,const Response& r){
 Tensor out{};
 if(r.q<=0)return out;
 const double qpow=std::pow(r.q,edv::m-1);
 const double ss=edv::dot(r.s,r.s);
 const double proj=(ss>0)?edv::dot(r.s,v)/ss:0.;
 for(int i=0;i<6;++i)out[i]=qpow*(v[i]+(edv::m-1)*r.s[i]*proj);
 return out;
}
// Transpose in the *Euclidean* Voigt pairing of a tensor-self-adjoint map.
inline Tensor apply_q_transpose(const Tensor& lambda,const Response& r){
 return weighted(apply_q_derivative(weighted(lambda,true),r),false);
}
inline Tensor apply_implicit_transpose(const Tensor& lambda,
                                      const Response& r,double A,double beta){
 return weighted(edv::inverse_apply(weighted(lambda,true),r.s,r.q,A,beta),false);
}
struct Differential {Tensor d_sigma{};State d_new{};};
struct Pullback {Tensor d_eps{};double d_T=0;State d_previous{};};

struct Linearization {
 Tensor eps{};
 double T=0,dt=0;
 State previous{};
 Modulus mode=Modulus::CONST;
 Controls flags{};
 Response response{};

 Linearization(const Tensor& e,double temperature,double time_step,
               const State& s,Modulus md,Controls c)
  :eps(e),T(temperature),dt(time_step),previous(s),mode(md),flags(c),
   response(edv::update(e,temperature,time_step,s,md,c)){}

 double b()const{return dt*response.Ad;}
 double beta()const{return dt*1.5*response.KN;}
 double A()const{return 1/(2*response.G)+b()*edv::a/(1+b());}
 double volumetric_strain()const{return edv::tr(eps)-3*edv::alpha*(T-edv::T_ref);}

 Differential jvp(const Tensor& d_eps,double d_T,const State& d_previous)const{
  const double b0=b(),beta0=beta(),den=1+b0;
  const double dE=ed::dmodulus(mode)*d_T;
  const double dG=dE/(2*(1+edv::nu));
  const double dK=dE/(3*(1-2*edv::nu));
  const double dln=ed::dlnarr_dT(T)*d_T;
  const double db=b0*dln,d_beta=beta0*dln;
  const double dA=-dG/(2*response.G*response.G)+edv::a*db/(den*den);
  const double qpow=response.q>0?std::pow(response.q,edv::m-1):0.;
  Tensor rhs=edv::deviator(d_eps);
  for(int i=0;i<6;++i){
   rhs[i]-=d_previous.e_v[i]+d_previous.e_d[i]/den;
   rhs[i]+=previous.e_d[i]*db/(den*den);
   rhs[i]-=(dA+d_beta*qpow)*response.s[i];
  }
  const Tensor ds=edv::inverse_apply(rhs,response.s,response.q,A(),beta0);
  const Tensor dq=apply_q_derivative(ds,response);
  Differential out;
  const double dvol=edv::tr(d_eps)-3*edv::alpha*d_T;
  for(int i=0;i<6;++i){
   out.d_sigma[i]=ds[i]+(i<3?dK*volumetric_strain()+response.K*dvol:0.);
   out.d_new.e_d[i]=d_previous.e_d[i]/den
    +(b0*edv::a/den)*ds[i]
    +(edv::a*response.s[i]-previous.e_d[i])*db/(den*den);
   out.d_new.e_v[i]=d_previous.e_v[i]+d_beta*qpow*response.s[i]+beta0*dq[i];
  }
  return out;
 }

 Pullback vjp(const Tensor& lambda_sigma,const State& lambda_new)const{
  const double b0=b(),beta0=beta(),den=1+b0;
  const double qpow=response.q>0?std::pow(response.q,edv::m-1):0.;
  // First accumulate the cotangent of the implicitly determined deviatoric stress.
  Tensor lambda_s=lambda_sigma;
  const Tensor qadj=apply_q_transpose(lambda_new.e_v,response);
  for(int i=0;i<6;++i)
   lambda_s[i]+=(b0*edv::a/den)*lambda_new.e_d[i]+beta0*qadj[i];
  const Tensor v=apply_implicit_transpose(lambda_s,response,A(),beta0);
  Pullback out;
  out.d_eps=edv::deviator(v);
  const double sum_normal=lambda_sigma[0]+lambda_sigma[1]+lambda_sigma[2];
  for(int i=0;i<3;++i)out.d_eps[i]+=response.K*sum_normal;
  for(int i=0;i<6;++i){
   out.d_previous.e_d[i]=(lambda_new.e_d[i]-v[i])/den;
   out.d_previous.e_v[i]=lambda_new.e_v[i]-v[i];
  }
  const double dE=ed::dmodulus(mode);
  const double dG=dE/(2*(1+edv::nu));
  const double dK=dE/(3*(1-2*edv::nu));
  const double dln=ed::dlnarr_dT(T);
  const double db=b0*dln,d_beta=beta0*dln;
  const double dA=-dG/(2*response.G*response.G)+edv::a*db/(den*den);
  out.d_T=sum_normal*(dK*volumetric_strain()-3*response.K*edv::alpha);
  for(int i=0;i<6;++i){
   const double drhs=previous.e_d[i]*db/(den*den)
                     -(dA+d_beta*qpow)*response.s[i];
   out.d_T+=v[i]*drhs;
   out.d_T+=lambda_new.e_d[i]*(edv::a*response.s[i]-previous.e_d[i])*db/(den*den);
   out.d_T+=lambda_new.e_v[i]*d_beta*qpow*response.s[i];
  }
  return out;
 }
};
} // namespace ice3d::p10b
