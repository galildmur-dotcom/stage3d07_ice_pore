#include "stage3d09b_functionals.hpp"
#include "edv_material.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace ice3d;
static void require(bool okay,const char* message){if(!okay)throw std::runtime_error(message);}
static bool near(double a,double b,double eps=1e-10){return std::abs(a-b)<=eps*std::max({1.,std::abs(a),std::abs(b)});}
int main(){
 try{
  require(near(p09b::sigma_ref_pa,ed::E_ref*ed::alpha*3/(1-ed::nu)),"stress normalization");
  require(p09b::energy_ref_pa>0,"energy normalization");
  const std::array<double,3> s{0.,0.,0.};
  for(int p:{4,8,12}){require(near(p09b::peak_power(s,p09b::sigma_ref_pa,p),p09b::initial_peak_power(p)),"zero-stress smoothing");}
  const std::array<double,3> principal{1e6,-0.7e6,0.1e6};
  double sum2=0;for(double v:principal){auto x=p09b::positive(v);sum2+=x*x;}
  for(int p:{4,8,12}){
   double power=p09b::peak_power(principal,p09b::sigma_ref_pa,p);
   require(std::isfinite(power)&&power>0,"peak observable finite");
   if(p==8){const auto pert=std::array<double,3>{principal[0]+10.,principal[1],principal[2]};
    require(p09b::peak_power(pert,p09b::sigma_ref_pa,p)>power,"monotone tension");}
  }
  require(sum2>0,"legacy psi nonzero");
  auto i=p09b::integrate(.00000075,p09b::initial_peak_power(8),0,0.25,0.0625,1200,150,300);
  require(near(i.mean_j6,(.00000075+0.25)/4),"j6 trapezoid");
  require(near(i.mean_energy,300.),"energy trapezoid");
  require(near(i.peak_moment,(p09b::initial_peak_power(8)+0.0625)/4),"peak trapezoid");
  ed::Tensor eps{0.0001,-0.00002,-0.00008,0.00002,0.00001,-0.00001};edv::State prev{};
  for(const auto mod:{ed::Modulus::CONST,ed::Modulus::VAR})for(int law=0;law<3;++law){
   edv::Controls flags{law>0,law>1};const auto response=edv::update(eps,250.7,150,prev,mod,flags);
   require(std::isfinite(response.free_energy)&&response.free_energy>=0,"energy nonnegative");
   const auto derived=response.free_energy/p09b::energy_ref_pa;
   require(std::isfinite(derived)&&derived>=0,"normalized energy");
   if(law==0){require(ed::norm(response.new_state.e_d)<1e-14,"elastic delayed internal zero");
     require(ed::norm(response.new_state.e_v)<1e-14,"elastic viscous internal zero");}
  }
  std::cout<<"P09B_FUNCTIONALS_UNIT_OK: p=4,8,12; material six variants; quadrature and dimensional normalization\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
