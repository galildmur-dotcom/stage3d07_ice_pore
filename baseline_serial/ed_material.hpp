#pragma once
// Stage 3D-04 | pointwise thermomechanical ED material law.
// Canonical specification: 3D_BASELINE_SPEC_v4.md (2026-10-09).
// Six components: [xx, yy, zz, xy, yz, zx]; offdiagonal strains are tensor strains, NOT gamma=2e_xy.
// All inputs and outputs are SI: Pa, K, s; e_d dimensionless and deviatoric.
#include <array>
#include <cmath>
#include <stdexcept>
#include <algorithm>
#include <string>

namespace ice3d::ed {
using Tensor = std::array<double,6>;
using Matrix = std::array<std::array<double,6>,6>;
constexpr double E_ref = 9.5e9;
constexpr double nu = 0.35;
constexpr double alpha = 149e-6/3.;
constexpr double T_ref = 253.15; // T0, -20 Celsius
constexpr double T_arr_ref = 263.15; // Arrhenius reference, -10 Celsius
constexpr double gas_R = 8.31446261815324; // J/mol/K (CODATA)
constexpr double Q = 66.9e3; // J/mol
constexpr double Ad_ref = 1.5e-3; // 1/s
constexpr double Kd_MPa_inv = 1.2e-3; // 1/MPa
constexpr double Kd_SI = Kd_MPa_inv / 1e6; // 1/Pa
constexpr double a = 1.5*Kd_SI; // (3/2)*Kd, 1/Pa

enum class Modulus {CONST, VAR};
struct State {Tensor e_d{};};
struct Response {
 Tensor sigma{}, deviatoric_stress{};
 State new_state{};
 Matrix tangent{}; // d sigma_i / d epsilon_j; shear uses tensor strain e_xy
 Tensor d_sigma_dT{}; // derivative at fixed total strain and previous state, Pa/K
 double E{}, G{}, K{}, Ad{}, b{}, denom{}, G_algorithmic{};
 double free_energy{}; // J/m^3, stored energy including internal spring
 double dissipation_rate{}; // W/m^3; thermodynamic isothermal drive
};
inline double tr(const Tensor& v){return v[0]+v[1]+v[2];}
inline Tensor deviator(Tensor v){const double t=tr(v)/3;for(int i=0;i<3;i++)v[i]-=t;return v;}
inline double dot(const Tensor&a0,const Tensor&b0){
 double r=0;for(int i=0;i<6;i++)r+=(i<3?1.:2.)*a0[i]*b0[i];return r;
}
inline double norm(const Tensor&x){return std::sqrt(dot(x,x));}
inline double modulus(double TK, Modulus mode){
 double TC=TK-273.15;
 return mode==Modulus::CONST ? E_ref : E_ref*(8.93-0.012*TC)/9.17;
}
inline double dmodulus(Modulus mode){return mode==Modulus::CONST?0.:-E_ref*0.012/9.17;}
inline double arrhenius(double TK){return std::exp(-(Q/gas_R)*(1./TK-1./T_arr_ref));}
inline double dlnarr_dT(double TK){return Q/(gas_R*TK*TK);}
inline void validate(double TK,double dt,const State&state){
 if(!(TK>170 && TK<330) || !std::isfinite(TK))throw std::invalid_argument("T_K outside supported material range (170,330) K");
 if(!(dt>=0) || !std::isfinite(dt))throw std::invalid_argument("dt must be nonnegative and finite");
 for(double v:state.e_d)if(!std::isfinite(v))throw std::invalid_argument("Nonfinite ED state");
 if(std::abs(tr(state.e_d))>1e-11*std::max(1.,norm(state.e_d)))throw std::invalid_argument("ED state must be deviatoric");
}
// Backward Euler, closed-form implicit update, no Newton iterations:
//   e_d^(n+1) = e_d^n + dt Ad [ a s^(n+1) - e_d^(n+1) ]
//   s = 2G [dev(eps - eps_T) - e_d^(n+1)], eps_T=alpha(T-Tref)I
// => Z=1+b(1+2Ga); e_d^(n+1)=(e_d^n+2G b a dev(eps))/Z, b=dt Ad.
// C_alg=K I\otimes I + 2G(1+b)/Z Pdev.
inline Response update(const Tensor&strain,double TK,double dt,const State&prev,Modulus mode){
 validate(TK,dt,prev);
 for(double v:strain)if(!std::isfinite(v))throw std::invalid_argument("Nonfinite strain");
 Response r;
 r.E=modulus(TK,mode);
 if(!(r.E>0))throw std::invalid_argument("Nonpositive E");
 r.G=r.E/(2*(1+nu));r.K=r.E/(3*(1-2*nu));
 r.Ad=Ad_ref*arrhenius(TK);r.b=dt*r.Ad;
 auto d=deviator(strain);
 r.denom=1+r.b*(1+2*r.G*a);
 const double mult=2*r.G*r.b*a;
 for(int i=0;i<6;i++)r.new_state.e_d[i]=(prev.e_d[i]+mult*d[i])/r.denom;
 for(int i=0;i<6;i++)r.deviatoric_stress[i]=2*r.G*(d[i]-r.new_state.e_d[i]);
 double volume=tr(strain)-3*alpha*(TK-T_ref);
 r.sigma=r.deviatoric_stress;
 for(int i=0;i<3;i++)r.sigma[i]+=r.K*volume;
 r.G_algorithmic=r.G*(1+r.b)/r.denom;
 for(int i=0;i<3;i++)for(int j=0;j<3;j++)r.tangent[i][j]=r.K+2*r.G_algorithmic*((i==j?1.:0.)-1./3);
 for(int i=3;i<6;i++)r.tangent[i][i]=2*r.G_algorithmic;
 // Analytic full d sigma/dT; differentiates G(T), K(T), Ad(T) AND eps_T(T).
 double dE=dmodulus(mode),dG=dE/(2*(1+nu)),dK=dE/(3*(1-2*nu));
 double db=r.b*dlnarr_dT(TK);
 double dZ=db*(1+2*r.G*a)+r.b*2*a*dG;
 for(int i=0;i<6;i++){
  double dN=2*a*(r.b*dG+r.G*db)*d[i];
  double dEd=(dN-r.new_state.e_d[i]*dZ)/r.denom;
  r.d_sigma_dT[i]=2*dG*(d[i]-r.new_state.e_d[i])-2*r.G*dEd;
  if(i<3)r.d_sigma_dT[i]+=dK*volume-3*r.K*alpha;
 }
 Tensor residual=d;
 for(int i=0;i<6;i++)residual[i]-=r.new_state.e_d[i];
 r.free_energy=.5*r.K*volume*volume+r.G*dot(residual,residual)+dot(r.new_state.e_d,r.new_state.e_d)/(2*a);
 Tensor drive=r.deviatoric_stress;
 for(int i=0;i<6;i++)drive[i]-=r.new_state.e_d[i]/a;
 r.dissipation_rate=r.Ad*a*dot(drive,drive);
 return r;
}
} // namespace ice3d::ed
