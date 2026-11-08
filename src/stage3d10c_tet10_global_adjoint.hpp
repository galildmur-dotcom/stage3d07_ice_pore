#pragma once
// Stage 3D-10C: one implicit mechanical step, assembled on the SAME curved
// Tet10 geometry and 27/64-point quadrature as the production spatial solver.
//
// Inclusion contract: include mechanical.cpp with STAGE3D06_LIBRARY defined
// before this header. This transitional adapter reuses its Mesh, GaussQ,
// tetshape, and vector geometry without duplicating the production geometry.
//
// Block linearization:
//       (u_free, T_nodes, z_old_qp) -> (R_free, z_new_qp).
// Dirichlet rows are R_bc=u_bc, while constrained values are projected to zero
// during constitutive evaluation. The adjoint is the EXACT transpose in the
// Euclidean coordinate and stored-Voigt pairings. Do not confuse this with a
// time-history adjoint or a continuous Hadamard shape derivative.
#include "stage3d10b_edv_linearization.hpp"
#include <array>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace ice3d::p10c {
using Tensor=p10b::Tensor;
using State=p10b::State;

inline Tensor displacement_strain_basis(const double g[3],int direction){
 Tensor b{};
 if(direction==0){b[0]=g[0];b[3]=.5*g[1];b[5]=.5*g[2];}
 if(direction==1){b[1]=g[1];b[3]=.5*g[0];b[4]=.5*g[2];}
 if(direction==2){b[2]=g[2];b[4]=.5*g[1];b[5]=.5*g[0];}
 return b;
}

struct Perturbation {
 std::vector<double> du;                 // displacement [m], 3*nodes
 std::vector<double> dtemperature;       // nodal offset from T_ref [K]
 std::vector<State> dprevious;           // prior local history at each QP
};
struct Output {
 std::vector<double> residual;           // mechanical nodal force [N]
 std::vector<State> next;                // history state at each QP
};
struct Pullback {
 std::vector<double> displacement;
 std::vector<double> temperature;
 std::vector<State> previous;
};

struct QuadraturePoint {
 std::array<int,10> nodes;
 std::array<Tensor,30> B;
 std::array<double,10> N;
 double volume;
 p10b::Linearization law;
 QuadraturePoint(const std::array<int,10>& ids,
                 const std::array<Tensor,30>& basis,
                 const std::array<double,10>& shape,double dv,
                 const Tensor& eps,double T,double dt,const State& old,
                 p10b::Modulus mode,p10b::Controls controls)
  : nodes(ids),B(basis),N(shape),volume(dv),
    law(eps,T,dt,old,mode,controls){}
};

struct Step {
 std::vector<QuadraturePoint> qps;
 std::vector<uint8_t> constrained;
 std::vector<double> u;
 size_t node_count=0;

 Step(const Mesh& mesh,const std::vector<GaussQ>& quadrature,
      const std::vector<double>& temperature_offset,
      const std::vector<State>& previous,double dt,
      const std::vector<double>& displacement,
      const std::vector<uint8_t>& prescribed,
      p10b::Modulus modulus,p10b::Controls flags)
      :constrained(prescribed),u(displacement),node_count(mesh.nodes.size()){
  if(temperature_offset.size()!=node_count || u.size()!=3*node_count ||
     constrained.size()!=u.size() ||
     previous.size()!=mesh.tets.size()*quadrature.size())
   throw std::invalid_argument("P10C: inconsistent mesh, DOF, or QP sizes");
  qps.reserve(previous.size());
  for(size_t e=0;e<mesh.tets.size();++e){
   const auto& ids=mesh.tets[e];
   for(size_t qi=0;qi<quadrature.size();++qi){
    const auto& b=quadrature[qi];
    V dr{},ds{},dtvec{};
    double T=edv::T_ref;
    for(int j=0;j<10;++j){
     const V x=mesh.nodes[ids[j]];
     dr=dr+x*b.d[j][0];ds=ds+x*b.d[j][1];dtvec=dtvec+x*b.d[j][2];
     T+=b.N[j]*temperature_offset[ids[j]];
    }
    const V co0=cross(ds,dtvec),co1=cross(dtvec,dr),co2=cross(dr,ds);
    const double jac=dot(dr,co0);
    if(!(jac>0))throw std::runtime_error("P10C: nonpositive Tet10 Jacobian");
    std::array<Tensor,30> B{};
    Tensor eps{};
    for(int j=0;j<10;++j){
     const V g=(co0*b.d[j][0]+co1*b.d[j][1]+co2*b.d[j][2])/jac;
     const double gg[3]={g.x,g.y,g.z};
     for(int dir=0;dir<3;++dir){
      const int local=3*j+dir,global=3*ids[j]+dir;
      B[local]=displacement_strain_basis(gg,dir);
      if(!constrained[global])for(int k=0;k<6;++k)
       eps[k]+=B[local][k]*u[global];
     }
    }
    qps.emplace_back(ids,B,b.N,b.w*jac,eps,T,dt,
                     previous[e*quadrature.size()+qi],modulus,flags);
   }
  }
 }

 Output evaluate()const{
  Output out;
  out.residual.assign(u.size(),0);
  out.next.reserve(qps.size());
  for(const auto& q:qps){
   out.next.push_back(q.law.response.new_state);
   for(int j=0;j<30;++j){
    const int global=3*q.nodes[j/3]+j%3;
    if(!constrained[global])
     out.residual[global]+=q.volume*edv::dot(q.B[j],q.law.response.sigma);
   }
  }
  for(size_t i=0;i<u.size();++i)if(constrained[i])out.residual[i]=u[i];
  return out;
 }

 Output jvp(const Perturbation& d)const{
  check(d.du,d.dtemperature,d.dprevious);
  Output out;
  out.residual.assign(u.size(),0);
  out.next.reserve(qps.size());
  for(size_t iq=0;iq<qps.size();++iq){
   const auto& q=qps[iq];
   Tensor deps{};
   for(int j=0;j<30;++j){
    const int global=3*q.nodes[j/3]+j%3;
    if(!constrained[global])for(int k=0;k<6;++k)
     deps[k]+=q.B[j][k]*d.du[global];
   }
   double dT=0;
   for(int j=0;j<10;++j)dT+=q.N[j]*d.dtemperature[q.nodes[j]];
   const auto local=q.law.jvp(deps,dT,d.dprevious[iq]);
   out.next.push_back(local.d_new);
   for(int j=0;j<30;++j){
    const int global=3*q.nodes[j/3]+j%3;
    if(!constrained[global])
     out.residual[global]+=q.volume*edv::dot(q.B[j],local.d_sigma);
   }
  }
  for(size_t i=0;i<u.size();++i)if(constrained[i])out.residual[i]=d.du[i];
  return out;
 }

 Pullback vjp(const Output& lambda)const{
  if(lambda.residual.size()!=u.size() || lambda.next.size()!=qps.size())
   throw std::invalid_argument("P10C: incompatible adjoint dimensions");
  Pullback result;
  result.displacement.assign(u.size(),0);
  result.temperature.assign(node_count,0);
  result.previous.resize(qps.size());
  for(size_t iq=0;iq<qps.size();++iq){
   const auto& q=qps[iq];
   Tensor lstress{};
   for(int j=0;j<30;++j){
    const int global=3*q.nodes[j/3]+j%3;
    if(!constrained[global])for(int k=0;k<6;++k)
     lstress[k]+=q.volume*q.B[j][k]*lambda.residual[global];
   }
   // Physical stress contraction in R=B^T:sigma carries a factor of two
   // on the shear components, but local VJP uses Euclidean Voigt pairing.
   lstress=p10b::weighted(lstress,false);
   const auto back=q.law.vjp(lstress,lambda.next[iq]);
   result.previous[iq]=back.d_previous;
   for(int j=0;j<30;++j){
    const int global=3*q.nodes[j/3]+j%3;
    if(!constrained[global])
     result.displacement[global]+=p10b::euclid_dot(q.B[j],back.d_eps);
   }
   for(int j=0;j<10;++j)
    result.temperature[q.nodes[j]]+=q.N[j]*back.d_T;
  }
  for(size_t i=0;i<u.size();++i)if(constrained[i])
   result.displacement[i]+=lambda.residual[i];
  return result;
 }

 void check(const std::vector<double>& du,const std::vector<double>& dT,
            const std::vector<State>& dprev)const{
  if(du.size()!=u.size() || dT.size()!=node_count || dprev.size()!=qps.size())
   throw std::invalid_argument("P10C: incompatible perturbation dimensions");
 }
};
} // namespace ice3d::p10c
