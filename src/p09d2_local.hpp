#pragma once
// Stage3D09D2: read-only, final-state refined radial diagnostics.
// Hard and C1-smoothed radial partitions both conserve the ORIGINAL B6 integrals.
#include "stage3d09b_functionals.hpp"
#include <array>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>

namespace ice3d::p09d2 {
constexpr std::array<double,12> edges_mm{{1.,1.05,1.10,1.15,1.20,1.25,1.50,2.,3.,4.,5.,6.}};
constexpr double halfwidth_mm=0.010; // smoothstep transition interval: [edge-h,edge+h]
constexpr std::size_t nbin=edges_mm.size()-1;
constexpr std::size_t ninterface=5; // internal fine-shell faces 1.05..1.25mm
struct Bin {
 double volume=0,p4=0,p8=0,p12=0,psi=0,energy=0;
 unsigned long long nqp=0;
};
struct Interface {double volume=0,p8=0;unsigned long long nqp=0;};
struct HotElement {double volume=0,p8=0,p12=0,peak_positive=0,radius_at_peak_mm=0;unsigned long long nqp=0;};
struct Diagnostic {
 std::array<Bin,nbin> hard{},smooth{};
 std::array<Interface,ninterface> interfaces{};
};
inline double smooth_step(double radius_mm,double threshold_mm){
 const double x=(radius_mm-threshold_mm+halfwidth_mm)/(2*halfwidth_mm);
 if(x<=0)return 0.;if(x>=1)return 1.;return x*x*(3-2*x);
}
inline unsigned hard_bin(double r){
 if(!std::isfinite(r))throw std::runtime_error("P09D2: nonfinite radius");
 for(std::size_t i=1;i<nbin;++i)if(r<edges_mm[i])return unsigned(i-1);
 return unsigned(nbin-1);
}
inline void add(Bin& b,double weight,double dv,double p4,double p8,double p12,double psi,double en){
 if(!(weight>0))return;
 const double v=weight*dv;
 b.volume+=v;b.p4+=v*p4;b.p8+=v*p8;b.p12+=v*p12;
 b.psi+=v*psi;b.energy+=v*en;++b.nqp;
}
inline void accumulate(Diagnostic&d,HotElement&hot,double r,double dv,
                       const std::array<double,3>&sigma,double sigma_ref,double psi,double energy){
 if(!std::isfinite(r)||!(dv>0)||!std::isfinite(dv)||!std::isfinite(psi)||!std::isfinite(energy))
  throw std::runtime_error("P09D2 invalid quadrature input");
 const double p4=ice3d::p09b::peak_power(sigma,sigma_ref,4);
 const double p8=ice3d::p09b::peak_power(sigma,sigma_ref,8);
 const double p12=ice3d::p09b::peak_power(sigma,sigma_ref,12);
 add(d.hard[hard_bin(r)],1,dv,p4,p8,p12,psi,energy);
 // This is a partition of unity even for quadrature points with r<1mm or r>6mm.
 double left=0.;
 for(std::size_t k=0;k<nbin-1;++k){
  const double right=smooth_step(r,edges_mm[k+1]);
  add(d.smooth[k],(k==0?1.-right:left-right),dv,p4,p8,p12,psi,energy);
  left=right;
 }
 add(d.smooth[nbin-1],left,dv,p4,p8,p12,psi,energy);
 for(std::size_t i=0;i<ninterface;++i)if(std::abs(r-edges_mm[i+1])<=halfwidth_mm){
  auto&b=d.interfaces[i];b.volume+=dv;b.p8+=dv*p8;++b.nqp;
 }
 hot.volume+=dv;hot.p8+=dv*p8;hot.p12+=dv*p12;++hot.nqp;
 const double pk=std::max({0.,sigma[0],sigma[1],sigma[2]})/sigma_ref;
 if(pk>hot.peak_positive){hot.peak_positive=pk;hot.radius_at_peak_mm=r;}
}
inline void merge_bin(Bin&a,const Bin&b){
 a.volume+=b.volume;a.p4+=b.p4;a.p8+=b.p8;a.p12+=b.p12;
 a.psi+=b.psi;a.energy+=b.energy;a.nqp+=b.nqp;
}
inline void merge(Diagnostic&a,const Diagnostic&b){
 for(std::size_t i=0;i<nbin;++i){merge_bin(a.hard[i],b.hard[i]);merge_bin(a.smooth[i],b.smooth[i]);}
 for(std::size_t i=0;i<ninterface;++i){a.interfaces[i].volume+=b.interfaces[i].volume;
  a.interfaces[i].p8+=b.interfaces[i].p8;a.interfaces[i].nqp+=b.interfaces[i].nqp;}
}
inline Bin total(const std::array<Bin,nbin>&bins){Bin sum;
 for(const auto&b:bins)merge_bin(sum,b);return sum;
}
inline double rel_error(double a,double b){return std::abs(a-b)/std::max({std::abs(a),std::abs(b),1e-30});}
inline void selftest(){
 Diagnostic d;HotElement e;
 const std::array<double,3>s{{1.,2.,3.}};
 for(double r:{0.990,1.049,1.051,1.100,1.149,1.199,1.249,1.270,6.05})
  accumulate(d,e,r,2.,s,2.,5.,7.);
 auto a=total(d.hard),b=total(d.smooth);
 for(auto [x,y]:std::array<std::pair<double,double>,6>{{{a.volume,b.volume},{a.p4,b.p4},{a.p8,b.p8},{a.p12,b.p12},{a.psi,b.psi},{a.energy,b.energy}}})
  if(rel_error(x,y)>1e-13)throw std::runtime_error("P09D2 partition conservation failed");
 if(rel_error(e.p8,a.p8)>1e-13||rel_error(e.p12,a.p12)>1e-13||
    rel_error(a.volume,18.)>1e-13||rel_error(a.psi,90.)>1e-13||
    rel_error(a.energy,126.)>1e-13||hard_bin(.999)!=0||hard_bin(1.101)!=2||hard_bin(6.3)!=nbin-1)
  throw std::runtime_error("P09D2 unit conservation failed");
 Diagnostic copy;merge(copy,d);
 if(rel_error(total(copy.hard).p8,a.p8)>1e-13)throw std::runtime_error("P09D2 merge failed");
 for(std::size_t j=1;j<nbin;++j){const auto x=smooth_step(edges_mm[j],edges_mm[j]);
  if(std::abs(x-.5)>1e-14)throw std::runtime_error("P09D2 smoothstep discontinuity");}
}
}
