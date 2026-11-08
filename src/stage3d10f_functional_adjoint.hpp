#pragma once
// Stage 3D-10F: analytic cotangents of the actual Stage09B observables,
// j6, pth power moment underlying j_peak, and normalized free energy j_en.
// The optional SafetySmooth is a PROTOTYPE requiring a separately justified
// ice strength threshold and smoothing widths; it is not part of Stage09C.
//
// Include mechanical.cpp with STAGE3D06_LIBRARY and the Stage10C adapter
// first.  This header reuses the canonical EDV material update and QP basis.
#include "stage3d09b_functionals.hpp"
#include "stage3d10c_tet10_global_adjoint.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

namespace ice3d::p10f {
using Tensor=p10c::Tensor;
using State=p10c::State;

enum class Kind { J6,PeakMoment,Energy,SafetySmooth };
struct Parameters {
 int peak_p=8;
 double sigma_ref=p09b::sigma_ref_pa;
 double energy_ref=p09b::energy_ref_pa;
 // SafetySmooth only: NONPHYSICAL diagnostic defaults, not an ice criterion.
 double test_threshold=.40*p09b::sigma_ref_pa;
 double test_threshold_width=.025*p09b::sigma_ref_pa;
 double test_eigen_softmax_width=.015*p09b::sigma_ref_pa;
};

struct Spectral {
 std::array<double,3> eigen{};
 std::array<std::array<double,3>,3> vectors{}; // columns are eigenvectors
};
inline Spectral jacobi_symmetric_3x3(const Tensor& sig){
 double A[3][3]={{sig[0],sig[3],sig[5]},
                 {sig[3],sig[1],sig[4]},
                 {sig[5],sig[4],sig[2]}};
 Spectral o;
 for(int i=0;i<3;++i)o.vectors[i][i]=1.;
 for(int iter=0;iter<60;++iter){
  int p=0,q=1;double largest=std::abs(A[0][1]);
  for(const auto pair:std::array<std::array<int,2>,2>{{{{0,2}},{{1,2}}}}){
   if(std::abs(A[pair[0]][pair[1]])>largest){
    p=pair[0];q=pair[1];largest=std::abs(A[p][q]);
   }
  }
  const double bound=2e-15*std::max({1.,std::abs(A[0][0]),
                                    std::abs(A[1][1]),std::abs(A[2][2])});
  if(largest<=bound)break;
  const double tau=(A[q][q]-A[p][p])/(2*A[p][q]);
  const double t=(tau>=0?1.:-1.)/(std::abs(tau)+std::hypot(1.,tau));
  const double c=1./std::hypot(1.,t),s=t*c;
  const double pp=A[p][p],qq=A[q][q],pq=A[p][q];
  A[p][p]=pp-t*pq;A[q][q]=qq+t*pq;A[p][q]=A[q][p]=0.;
  for(int k=0;k<3;++k)if(k!=p && k!=q){
   const double ap=A[k][p],aq=A[k][q];
   A[k][p]=A[p][k]=c*ap-s*aq;
   A[k][q]=A[q][k]=s*ap+c*aq;
  }
  for(int k=0;k<3;++k){
   const double vp=o.vectors[k][p],vq=o.vectors[k][q];
   o.vectors[k][p]=c*vp-s*vq;
   o.vectors[k][q]=s*vp+c*vq;
  }
 }
 for(int i=0;i<3;++i)o.eigen[i]=A[i][i];
 return o;
}
// Derivative with respect to the six STORED, tensor-shear Voigt components.
// Stress symmetric matrix contraction contributes a factor 2 for shear.
inline Tensor spectral_gradient(const Spectral& eig,
                                const std::array<double,3>& derivative){
 double G[3][3]{};
 for(int i=0;i<3;++i)for(int r=0;r<3;++r)for(int c=0;c<3;++c)
  G[r][c]+=derivative[i]*eig.vectors[r][i]*eig.vectors[c][i];
 return Tensor{G[0][0],G[1][1],G[2][2],2*G[0][1],2*G[1][2],2*G[2][0]};
}
inline std::pair<double,double> positive_and_derivative(double eig,double sigma_ref){
 const double r=eig/sigma_ref;
 const double root=std::hypot(r,.001);
 const double pos=.5*(r+root);
 const double derivative=.5*(1.+r/root)/sigma_ref;
 return {pos,derivative};
}

struct PointSource {
 double value=0;
 Tensor lambda_sigma{};
 State lambda_next{};
 Tensor direct_strain{};
 double direct_temperature=0;
};

inline PointSource point_source(const p10c::QuadraturePoint& qp,
                                Kind kind,const Parameters& opts={}){
 if(!(opts.sigma_ref>0&&opts.energy_ref>0))
  throw std::invalid_argument("P10F: invalid functional normalization");
 PointSource out;
 const auto& r=qp.law.response;
 if(kind==Kind::Energy){
  const double volum=qp.law.volumetric_strain();
  Tensor elastic=edv::deviator(qp.law.eps);
  for(int i=0;i<6;++i)
   elastic[i]-=r.new_state.e_d[i]+r.new_state.e_v[i];
  const double de=ice3d::ed::dmodulus(qp.law.mode);
  const double dG=de/(2*(1+edv::nu));
  const double dK=de/(3*(1-2*edv::nu));
  const Tensor dev_elastic=edv::deviator(elastic);
  out.value=r.free_energy/opts.energy_ref;
  for(int i=0;i<6;++i){
   const double w=i<3?1.:2.;
   out.direct_strain[i]=2*r.G*w*dev_elastic[i]/opts.energy_ref;
   if(i<3)out.direct_strain[i]+=r.K*volum/opts.energy_ref;
   out.lambda_next.e_d[i]=w*(-2*r.G*elastic[i]
             +r.new_state.e_d[i]/edv::a)/opts.energy_ref;
   out.lambda_next.e_v[i]=w*(-2*r.G*elastic[i])/opts.energy_ref;
  }
  out.direct_temperature=(.5*dK*volum*volum
     -3*edv::alpha*r.K*volum+dG*edv::dot(elastic,elastic))/opts.energy_ref;
  return out;
 }

 const auto eig=jacobi_symmetric_3x3(r.sigma);
 std::array<double,3> dev{};
 if(kind==Kind::J6 || kind==Kind::PeakMoment){
  const int p=kind==Kind::J6?2:opts.peak_p;
  if(kind==Kind::PeakMoment && p!=4 && p!=8 && p!=12)
   throw std::invalid_argument("P10F: unsupported peak exponent");
  for(int i=0;i<3;++i){
   const auto [pos,dp]=positive_and_derivative(eig.eigen[i],opts.sigma_ref);
   out.value+=std::pow(pos,p);
   dev[i]=p*std::pow(pos,p-1)*dp;
  }
 }else if(kind==Kind::SafetySmooth){
  if(!(opts.test_threshold_width>0&&opts.test_eigen_softmax_width>0))
   throw std::invalid_argument("P10F: invalid safety regularization widths");
  const double largest=*std::max_element(eig.eigen.begin(),eig.eigen.end());
  const double kappa=opts.test_eigen_softmax_width;
  std::array<double,3> w{};
  double sum=0;
  for(int i=0;i<3;++i){w[i]=std::exp((eig.eigen[i]-largest)/kappa);sum+=w[i];}
  const double softmax=largest+kappa*std::log(sum);
  const double d=softmax-opts.test_threshold;
  const double smooth=std::hypot(d,opts.test_threshold_width);
  out.value=.5*(1.+d/smooth);
  const double dh=.5*opts.test_threshold_width*opts.test_threshold_width/
                   (smooth*smooth*smooth);
  for(int i=0;i<3;++i)dev[i]=dh*w[i]/sum;
 }else throw std::invalid_argument("P10F: unknown observable");
 out.lambda_sigma=spectral_gradient(eig,dev);
 return out;
}

struct Sources {
 double value=0;
 std::vector<double> displacement;
 std::vector<double> temperature;
 std::vector<State> previous;
};

inline Sources evaluate(const p10c::Step& step,Kind kind,
                        const Parameters& opts={}){
 double volume=0;
 for(const auto& qp:step.qps)volume+=qp.volume;
 if(!(volume>0))throw std::invalid_argument("P10F: nonpositive integration volume");
 Sources result;
 result.displacement.assign(step.u.size(),0.);
 result.temperature.assign(step.node_count,0.);
 result.previous.resize(step.qps.size());
 for(size_t q=0;q<step.qps.size();++q){
  const auto& qp=step.qps[q];
  const auto src=point_source(qp,kind,opts);
  const double factor=qp.volume/volume;
  result.value+=factor*src.value;
  Tensor lstress=src.lambda_sigma;
  State lnew=src.lambda_next;
  for(int k=0;k<6;++k){
   lstress[k]*=factor;
   lnew.e_d[k]*=factor;lnew.e_v[k]*=factor;
  }
  const auto pb=qp.law.vjp(lstress,lnew);
  Tensor deps=pb.d_eps;
  for(int k=0;k<6;++k)deps[k]+=factor*src.direct_strain[k];
  const double dT=pb.d_T+factor*src.direct_temperature;
  for(int a=0;a<30;++a){
   const int index=3*qp.nodes[a/3]+a%3;
   if(!step.constrained[index])
    result.displacement[index]+=p10b::euclid_dot(qp.B[a],deps);
  }
  for(int a=0;a<10;++a)
   result.temperature[qp.nodes[a]]+=qp.N[a]*dT;
  result.previous[q]=pb.d_previous;
 }
 return result;
}

inline double initial_time_value(Kind kind,const Parameters& opts={}){
 if(kind==Kind::J6)return 7.5e-7; // Stage09C exact initial j6.
 if(kind==Kind::PeakMoment)return p09b::initial_peak_power(opts.peak_p);
 if(kind==Kind::Energy)return 0.;
 if(kind==Kind::SafetySmooth){
  const double softmax=opts.test_eigen_softmax_width*std::log(3.);
  const double d=softmax-opts.test_threshold;
  return .5*(1.+d/std::hypot(d,opts.test_threshold_width));
 }
 throw std::invalid_argument("P10F: invalid initial observable");
}
} // namespace ice3d::p10f
