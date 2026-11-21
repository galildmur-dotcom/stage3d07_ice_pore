#pragma once
// P10BX isolated, opt-in diagnostic for the EXACT P10P thermal reverse step.
// Inclusion contract: geometry_stage3d01.cpp, stage3d10l_thermal_adjoint.hpp
// must have been included. The caller keeps its original production CSR sum.
#include "stage3d10bw_thermal_qp_partition.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace ice3d::p10bx {

struct Audit {
  p10bw::Snapshot qp;
  double csr_mass=0.,csr_conduct_with_robin=0.,csr_robin_load=0.;
  double csr_total=0.,absolute_error=0.,tolerance=0.,relative_scaled=0.;
};

inline Audit audit_step(const Mesh& mesh,const std::vector<V>& velocity,
                        const p10l::CSR& shape,
                        const std::vector<double>& psi,
                        const std::vector<double>& temperature,
                        const std::vector<double>& previous,
                        double dt,double ambient){
  const std::size_t nn=mesh.nodes.size();
  if(shape.n!=int(nn)||psi.size()!=nn||temperature.size()!=nn||
     previous.size()!=nn||velocity.size()!=nn)
    throw std::invalid_argument("P10BX thermal CSR/QP node count mismatch");
  std::vector<double> difference(nn),mass,conduct;
  for(std::size_t i=0;i<nn;++i)
    difference[i]=temperature[i]-previous[i];
  shape.mul(shape.mass,difference,mass);
  shape.mul(shape.conduct,temperature,conduct);
  Audit result;
  for(std::size_t i=0;i<nn;++i){
    result.csr_mass+=psi[i]*mass[i];
    result.csr_conduct_with_robin+=dt*psi[i]*conduct[i];
    result.csr_robin_load-=dt*ambient*psi[i]*shape.robinload[i];
  }
  result.csr_total=result.csr_mass+result.csr_conduct_with_robin+
                   result.csr_robin_load;
  result.qp=p10bw::contract_step(mesh,velocity,psi,temperature,previous,
                                dt,ambient);
  const auto q=result.qp.total();
  const double scale=std::max({std::abs(q.mass)+std::abs(q.diffusion)+
      std::abs(q.robin),std::abs(result.csr_mass)+
      std::abs(result.csr_conduct_with_robin)+
      std::abs(result.csr_robin_load),std::abs(result.csr_total)});
  result.absolute_error=std::abs(q.total()-result.csr_total);
  result.relative_scaled=result.absolute_error/std::max(1.e-10,scale);
  result.tolerance=1.e-10+1.e-8*scale;
  // P10L's conduct matrix includes both diffusion and Robin stiffness;
  // compare mass separately and diffusion+Robin+load as one physical term.
  const double nonmass_csr=result.csr_conduct_with_robin+
                           result.csr_robin_load;
  const double nonmass_qp=q.diffusion+q.robin;
  if(!(std::isfinite(result.csr_total)&&std::isfinite(q.total()))||
      result.absolute_error>result.tolerance||
      std::abs(q.mass-result.csr_mass)>result.tolerance||
      std::abs(nonmass_qp-nonmass_csr)>result.tolerance)
    throw std::runtime_error("P10BX thermal QP partition disagrees with P10P CSR");
  return result;
}

} // namespace ice3d::p10bx
