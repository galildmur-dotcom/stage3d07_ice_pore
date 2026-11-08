#pragma once
// P09D: read-only diagnostics of the committed stress state at quadrature points.
// No changes to material law, FEM residual, tangent or the existing functionals.
#include "stage3d09b_functionals.hpp"
#include <array>
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace ice3d::p09d {
constexpr std::array<double,9> radial_edges_mm{{1.0,1.10,1.25,1.50,2.0,3.0,4.0,5.0,6.0}};
struct Bin {
 double volume=0, power4=0, power8=0, power12=0, psi6=0, energy=0;
 double rmin_mm=std::numeric_limits<double>::infinity(),rmax_mm=0;
 unsigned long long nqp=0;
};
struct Diagnostic {
 std::array<Bin,8> bins{};
 // Volumes in all bins must exactly reproduce the legacy B6 centroid classification.
 // For integration points beyond nominal 6mm in a B6 element, the outermost bin owns them.
};
inline int bin_index(double radius_mm){
 if(!std::isfinite(radius_mm))throw std::runtime_error("P09D nonfinite radius");
 for(int j=0;j<7;++j)if(radius_mm<radial_edges_mm[j+1])return j;
 return 7;
}
inline void accumulate(Diagnostic&out,double radius_mm,double dv,
  const std::array<double,3>& principal_pa,double sigma_ref_pa,double psi6,double energy_pa){
 if(!(dv>0)&&std::isfinite(dv))throw std::runtime_error("P09D nonpositive volume");
 if(!(std::isfinite(dv)&&std::isfinite(psi6)&&std::isfinite(energy_pa)))
  throw std::runtime_error("P09D nonfinite QP diagnostic");
 Bin&b=out.bins[bin_index(radius_mm)];
 b.volume+=dv;
 b.power4+=dv*ice3d::p09b::peak_power(principal_pa,sigma_ref_pa,4);
 b.power8+=dv*ice3d::p09b::peak_power(principal_pa,sigma_ref_pa,8);
 b.power12+=dv*ice3d::p09b::peak_power(principal_pa,sigma_ref_pa,12);
 b.psi6+=dv*psi6;b.energy+=dv*energy_pa;
 b.rmin_mm=std::min(b.rmin_mm,radius_mm);
 b.rmax_mm=std::max(b.rmax_mm,radius_mm);
 ++b.nqp;
}
inline void merge(Diagnostic&to,const Diagnostic&from){
 for(size_t i=0;i<to.bins.size();++i){auto&a=to.bins[i];const auto&b=from.bins[i];
  a.volume+=b.volume;a.power4+=b.power4;a.power8+=b.power8;a.power12+=b.power12;
  a.psi6+=b.psi6;a.energy+=b.energy;a.nqp+=b.nqp;
  a.rmin_mm=std::min(a.rmin_mm,b.rmin_mm);a.rmax_mm=std::max(a.rmax_mm,b.rmax_mm);
 }
}
inline Bin total(const Diagnostic&d){Bin b;
 for(const auto&x:d.bins){b.volume+=x.volume;b.power4+=x.power4;b.power8+=x.power8;b.power12+=x.power12;
  b.psi6+=x.psi6;b.energy+=x.energy;b.nqp+=x.nqp;
  b.rmin_mm=std::min(b.rmin_mm,x.rmin_mm);b.rmax_mm=std::max(b.rmax_mm,x.rmax_mm);}
 return b;
}
inline double relative_error(double a,double b){return std::abs(a-b)/std::max({std::abs(a),std::abs(b),1e-30});}
inline void selftest(){
 Diagnostic d;std::array<double,3>s{{1.,2.,3.}};
 accumulate(d,1.01,2.,s,2.,5.,7.);
 accumulate(d,1.30,3.,s,2.,8.,11.);
 const auto b=total(d);
 if(std::abs(b.volume-5.)>1e-14||std::abs(b.psi6-34.)>1e-14||
    std::abs(b.energy-47.)>1e-14||b.nqp!=2||
    std::abs(b.power8-5.*ice3d::p09b::peak_power(s,2.,8))>1e-12)
  throw std::runtime_error("P09D shell accounting failed");
 Diagnostic copy;merge(copy,d);
 if(std::abs(total(copy).power12-b.power12)>1e-11)throw std::runtime_error("P09D merge failed");
 if(bin_index(6.01)!=7||bin_index(1.15)!=1||bin_index(1.49)!=2)
  throw std::runtime_error("P09D shell classification failed");
}
}
