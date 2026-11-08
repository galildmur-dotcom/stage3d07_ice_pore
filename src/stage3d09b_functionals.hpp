#pragma once
// Stage 3D-09B: observational functionals; physics and legacy j6 are unchanged.
#include "ed_material.hpp"
#include <array>
#include <cmath>
#include <stdexcept>
namespace ice3d::p09b {
// Exactly the sigma normalization already used by legacy psi()/j6.
inline constexpr double sigma_ref_pa=ice3d::ed::E_ref*ice3d::ed::alpha*3/(1-ice3d::ed::nu);
// Fixed normalizer across E/ED/EDV and CONST/VAR, dimensions J/m^3 = Pa.
inline constexpr double energy_ref_pa=sigma_ref_pa*sigma_ref_pa/ice3d::ed::E_ref;
inline double positive(double sigma,double sigma_ref=sigma_ref_pa){
 if(!(sigma_ref>0))throw std::invalid_argument("positive: sigma_ref must be positive");
 const double r=sigma/sigma_ref;
 return 0.5*(r+std::hypot(r,0.001));
}
inline double peak_power(const std::array<double,3>&eigenvalues,double sigma_ref,int p){
 if(p!=4&&p!=8&&p!=12)throw std::invalid_argument("p must be 4,8,12");
 double sum=0;
 for(double eig:eigenvalues)sum+=std::pow(positive(eig,sigma_ref),p);
 return sum;
}
inline double initial_peak_power(int p){return 3.*std::pow(0.0005,p);}
struct TimeValues {double mean_j6=0,peak_moment=0,mean_energy=0;};
inline TimeValues integrate(double prior_j6,double prior_peak_power,double prior_energy,
 double now_j6,double now_peak_power,double now_energy,double dt,double total){
 if(!(dt>0&&total>=dt))throw std::invalid_argument("invalid time integration interval");
 return {(prior_j6+now_j6)*0.5*dt/total,(prior_peak_power+now_peak_power)*0.5*dt/total,(prior_energy+now_energy)*0.5*dt/total};
}
}
