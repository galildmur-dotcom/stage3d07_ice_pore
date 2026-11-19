#pragma once
// Stage3D-10V: exact directional derivative of the *discrete* curved-Tet10
// mechanical residual, EDV internal update and normalized B6 observables.
//
// Inclusion contract: mechanical.cpp (STAGE3D06_LIBRARY) must be visible first.
// The linearized constitutive update is the existing production P10B JVP;
// no finite difference or perturbed mechanical solve is used here.
#include "stage3d10f_functional_adjoint.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace ice3d::p10v {
using Tensor=p10c::Tensor;
using State=p10c::State;

// Exact derivative at amplitude zero of Stage3D08's X(a)=X(0)+a*f(r)*mode.
// The coordinates, radius and smoothing support are evaluated on the BASE mesh.
inline V velocity_at(const V& x,std::string_view mode,double cutoff_m){
 const V centre{0.,0.,.03};
 const V radial=x-centre;
 const double r=norm(radial);
 if(!(r>0.) || !(cutoff_m>RBASE))
  throw std::invalid_argument("P10V: invalid reference radius or cutoff");
 double f=1.;
 if(r>=cutoff_m)f=0.;
 else if(r>RBASE){
  const double t=(r-RBASE)/(cutoff_m-RBASE);
  f=1.-t*t*(3.-2.*t);
 }
 const V n=radial/r;
 if(mode=="R" || mode=="radius")return n*f;
 if(mode=="tx")return V{f,0,0};
 if(mode=="ty")return V{0,f,0};
 if(mode=="tz")return V{0,0,f};
 double Y=0.;
 if(mode=="y20")Y=std::sqrt(5./(16.*PI))*(3.*n.z*n.z-1.);
 else if(mode=="y21c")Y=std::sqrt(15./(4.*PI))*n.x*n.z;
 else if(mode=="y21s")Y=std::sqrt(15./(4.*PI))*n.y*n.z;
 else if(mode=="y22c")Y=std::sqrt(15./(16.*PI))*(n.x*n.x-n.y*n.y);
 else if(mode=="y22s")Y=std::sqrt(15./(4.*PI))*n.x*n.y;
 else throw std::invalid_argument("P10V: unsupported shape mode");
 return n*(f*Y);
}

inline std::vector<V> velocity(const Mesh& mesh,std::string_view mode,
                               double cutoff_mm){
 if(!(cutoff_mm>1000.*RBASE))
  throw std::invalid_argument("P10V: cutoff must exceed pore radius");
 std::vector<V> result;
 result.reserve(mesh.nodes.size());
 for(const V& x:mesh.nodes)
  result.push_back(velocity_at(x,mode,cutoff_mm*1e-3));
 return result;
}

struct Derivative {
 p10c::Output operator_change; // dR/dshape, dPhi/dshape at frozen state
 std::vector<double> objective; // normalized spatial dJ/dshape for each kind
 double observed_volume=0.,observed_volume_derivative=0.;
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
 // Only the diagnostic target stores a shell decomposition. Production P10W
 // retains its original memory use and exactly the same numerical path.
 std::vector<std::vector<double>> objective_by_shell;
 std::vector<std::vector<double>> equilibrium_by_shell;
#endif
};

#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
// P10AZ: diagnostic-only capture of exact frozen-state Q3 contributions.
// The recorder is active only for the selected peak functional, bins and
// steps. It never changes the residual, objective or EDV update.
#ifdef STAGE3D10AZ_QP_PROBE
struct QpProbeRecord {
 std::size_t element=0,qp=0,bin=0;
 double distance_mm=0,volume=0,d_volume=0,d_numerator=0;
 double equilibrium=0,history=0;
#ifdef STAGE3D10BA_POLAR_AUDIT
 double polar_mu=0.; // cos(theta) about actual spherical pore centre
#endif
};
struct QpProbe {
 const std::vector<State>* futures=nullptr;
 std::size_t objective_index=1; // peak moment in [j6,peak,energy]
 double weight=1.;
 double observed_volume=0.,average=0.;
 std::vector<QpProbeRecord> records;
};
#endif
struct ShellAudit {
 const std::vector<std::uint8_t>& qp_shells;
 std::vector<const std::vector<double>*> adjoints;
 std::size_t bin_count=0;
#ifdef STAGE3D10AZ_QP_PROBE
 QpProbe* probe=nullptr;
#endif
};
#endif

inline Derivative directional(const Mesh& mesh,const std::vector<GaussQ>& quad,
                              const p10c::Step& step,
                              const std::vector<V>& nodal_velocity,
                              const std::vector<uint8_t>& observation_mask,
                              const std::vector<p10f::Kind>& kinds
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
                              ,const ShellAudit* shell_audit=nullptr
#endif
                              ){
 if(nodal_velocity.size()!=mesh.nodes.size() ||
    observation_mask.size()!=mesh.tets.size() ||
    step.qps.size()!=mesh.tets.size()*quad.size() ||
    step.u.size()!=3*mesh.nodes.size() || kinds.empty())
  throw std::invalid_argument("P10V: inconsistent directional dimensions");
 Derivative out;
 out.operator_change.residual.assign(step.u.size(),0.);
 out.operator_change.next.resize(step.qps.size());
 out.objective.assign(kinds.size(),0.);
 std::vector<double> numerator(kinds.size(),0.),d_numerator(kinds.size(),0.);
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
 std::vector<double> shell_dvolume;
 std::vector<std::vector<double>> shell_dnumerator;
 if(shell_audit){
  if(shell_audit->qp_shells.size()!=step.qps.size() ||
     shell_audit->adjoints.size()!=kinds.size() ||
     shell_audit->bin_count==0)
   throw std::invalid_argument("P10Y: invalid shell audit dimensions");
  for(const auto* a:shell_audit->adjoints)
   if(!a || a->size()!=step.u.size())
    throw std::invalid_argument("P10Y: invalid adjoint dimensions");
  out.objective_by_shell.assign(kinds.size(),
                      std::vector<double>(shell_audit->bin_count,0.));
  out.equilibrium_by_shell=out.objective_by_shell;
  shell_dnumerator=out.objective_by_shell;
  shell_dvolume.assign(shell_audit->bin_count,0.);
#ifdef STAGE3D10AZ_QP_PROBE
  if(shell_audit->probe){
   const auto* history=shell_audit->probe->futures;
   if(!history||history->size()!=step.qps.size()||
      shell_audit->probe->objective_index>=kinds.size())
    throw std::invalid_argument("P10AZ invalid QP probe dimensions");
   shell_audit->probe->records.clear();
  }
#endif
 }
#endif

 for(size_t e=0;e<mesh.tets.size();++e){
  const auto& ids=mesh.tets[e];
  for(size_t iq=0;iq<quad.size();++iq){
   const auto qid=e*quad.size()+iq;
   const auto& b=quad[iq];
   const auto& qp=step.qps[qid];
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
   std::size_t bin=0;
   if(shell_audit){
    bin=shell_audit->qp_shells[qid];
    if(bin>=shell_audit->bin_count)
     throw std::invalid_argument("P10Y: QP shell index out of range");
   }
#endif
   V dr{},ds{},dt{},d_dr{},d_ds{},d_dt{};
   for(int a=0;a<10;++a){
    const V x=mesh.nodes[ids[a]],v=nodal_velocity[ids[a]];
    dr=dr+x*b.d[a][0];ds=ds+x*b.d[a][1];dt=dt+x*b.d[a][2];
    d_dr=d_dr+v*b.d[a][0];d_ds=d_ds+v*b.d[a][1];
    d_dt=d_dt+v*b.d[a][2];
   }
   const V c0=cross(ds,dt),c1=cross(dt,dr),c2=cross(dr,ds);
   const V dc0=cross(d_ds,dt)+cross(ds,d_dt);
   const V dc1=cross(d_dt,dr)+cross(dt,d_dr);
   const V dc2=cross(d_dr,ds)+cross(dr,d_ds);
   const double jac=dot(dr,c0),djac=dot(d_dr,c0)+dot(dr,dc0);
   if(!(jac>0.))throw std::runtime_error("P10V: nonpositive Tet10 Jacobian");
   const double dv=b.w*djac;
   std::array<Tensor,30> dB{};
   Tensor deps{};
   for(int a=0;a<10;++a){
    const auto& d=b.d[a];
    const V grad=(c0*d[0]+c1*d[1]+c2*d[2])/jac;
    const V dgrad=(dc0*d[0]+dc1*d[1]+dc2*d[2])/jac-
                   grad*(djac/jac);
    const double xyz[3]{dgrad.x,dgrad.y,dgrad.z};
    for(int dir=0;dir<3;++dir){
     const int loc=3*a+dir,global=3*ids[a]+dir;
     dB[loc]=p10c::displacement_strain_basis(xyz,dir);
     if(!step.constrained[global])for(int k=0;k<6;++k)
      deps[k]+=dB[loc][k]*step.u[global];
    }
   }
   const auto law=qp.law.jvp(deps,0.,State{});
   out.operator_change.next[qid]=law.d_new;
#ifdef STAGE3D10AZ_QP_PROBE
   QpProbeRecord probe_record;
   bool probe_selected=false;
   if(shell_audit && shell_audit->probe && (bin==1||bin==2)){
    probe_selected=true;
    V x{};
    for(int a=0;a<10;++a)x=x+mesh.nodes[ids[a]]*b.N[a];
    probe_record.element=e;
    probe_record.qp=iq;
    probe_record.bin=bin;
    probe_record.distance_mm=(norm(x-V{0.,0.,.03})-.001)*1000.;
#ifdef STAGE3D10BA_POLAR_AUDIT
    const V radial=x-V{0.,0.,.03};
    const double r=norm(radial);
    if(!(r>0.))throw std::runtime_error("P10BA QP at pore centre");
    probe_record.polar_mu=std::clamp(radial.z/r,-1.,1.);
#endif
    probe_record.volume=qp.volume;
    probe_record.d_volume=dv;
    const auto& fut=(*shell_audit->probe->futures)[qid];
    for(int a=0;a<6;++a){
     probe_record.history+=fut.e_d[a]*law.d_new.e_d[a];
     probe_record.history+=fut.e_v[a]*law.d_new.e_v[a];
    }
   }
#endif
   for(int a=0;a<30;++a){
    const int global=3*ids[a/3]+a%3;
    if(step.constrained[global])continue;
    const double local_change=
      dv*edv::dot(qp.B[a],qp.law.response.sigma)+
      qp.volume*(edv::dot(dB[a],qp.law.response.sigma)+
                 edv::dot(qp.B[a],law.d_sigma));
    out.operator_change.residual[global]+=local_change;
#ifdef STAGE3D10AZ_QP_PROBE
    if(probe_selected)
     probe_record.equilibrium+=
       (*shell_audit->adjoints[shell_audit->probe->objective_index])[global]*
       local_change;
#endif
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
    if(shell_audit)for(std::size_t k=0;k<kinds.size();++k)
     out.equilibrium_by_shell[k][bin]+=
         (*shell_audit->adjoints[k])[global]*local_change;
#endif
   }
#ifdef STAGE3D10AZ_QP_PROBE
   if(probe_selected && !observation_mask[e]){
    probe_record.d_volume=0.; // outside B6: no objective numerator OR denominator
    shell_audit->probe->records.push_back(probe_record);
   }
#endif
   if(!observation_mask[e])continue;
   out.observed_volume+=qp.volume;
   out.observed_volume_derivative+=dv;
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
   if(shell_audit)shell_dvolume[bin]+=dv;
#endif
   for(size_t k=0;k<kinds.size();++k){
    const auto src=p10f::point_source(qp,kinds[k]);
    const double d_point=p10b::euclid_dot(src.lambda_sigma,law.d_sigma)+
        p10b::euclid_dot(src.lambda_next.e_d,law.d_new.e_d)+
        p10b::euclid_dot(src.lambda_next.e_v,law.d_new.e_v)+
        p10b::euclid_dot(src.direct_strain,deps);
    numerator[k]+=qp.volume*src.value;
    d_numerator[k]+=dv*src.value+qp.volume*d_point;
#ifdef STAGE3D10AZ_QP_PROBE
    if(probe_selected && k==shell_audit->probe->objective_index)
     probe_record.d_numerator=dv*src.value+qp.volume*d_point;
#endif
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
    if(shell_audit){
     shell_dnumerator[k][bin]+=dv*src.value+qp.volume*d_point;
    }
#endif
   }
#ifdef STAGE3D10AZ_QP_PROBE
   if(probe_selected) shell_audit->probe->records.push_back(probe_record);
#endif
  }
 }
 if(!(out.observed_volume>0.))
  throw std::runtime_error("P10V: empty observation region");
 for(size_t k=0;k<kinds.size();++k){
  const double average=numerator[k]/out.observed_volume;
#ifdef STAGE3D10AZ_QP_PROBE
   if(shell_audit && shell_audit->probe &&
      k==shell_audit->probe->objective_index){
    shell_audit->probe->observed_volume=out.observed_volume;
    shell_audit->probe->average=average;
   }
#endif
  out.objective[k]=(d_numerator[k]-
         average*out.observed_volume_derivative)/out.observed_volume;
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
  if(shell_audit)for(std::size_t bin=0;bin<shell_audit->bin_count;++bin)
   out.objective_by_shell[k][bin]=
      (shell_dnumerator[k][bin]-average*shell_dvolume[bin])/
       out.observed_volume;
#endif
 }
 return out;
}
} // namespace ice3d::p10v
