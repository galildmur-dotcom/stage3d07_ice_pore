#pragma once
// P10BW review-only diagnostic companion for the EXACT P10L operator.
// Include AFTER geometry_stage3d01.cpp (STAGE3D01_LIBRARY) and
// stage3d10l_thermal_adjoint.hpp. Does not change the production operator,
// solve, or adjoint. No source file is patched in the user's Windows tree.
#include <array>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace ice3d::p10bw {

constexpr std::array<double,10> shell_lower_mm{
    0., .02, .05, .1, .25, .5, 1., 2., 5., 15.};
constexpr int polar_bands=10;

struct Contributions {
  double mass=0.,diffusion=0.,robin=0.;
  double total()const{return mass+diffusion+robin;}
  void add(const Contributions& x){
    mass+=x.mass;diffusion+=x.diffusion;robin+=x.robin;
  }
};
struct Cell {
  Contributions part;
  std::size_t qp_count=0;
  double volume=0.,theta_integral=0.;
};
struct Snapshot {
  std::array<Cell,100> cells{};
  Contributions top_robin;
  std::size_t top_qp_count=0;
  double top_area=0.;
  Contributions total()const{
    Contributions s=top_robin;
    for(const auto& c:cells)s.add(c.part);
    return s;
  }
  std::size_t thermal_qp_count()const{
    std::size_t n=0;for(const auto& c:cells)n+=c.qp_count;return n;
  }
  double thermal_qp_volume()const{
    double v=0;for(const auto& c:cells)v+=c.volume;return v;
  }
};

inline std::size_t shell_bin(double wall_distance_mm){
  const double d=std::max(0.,wall_distance_mm);
  for(std::size_t k=1;k<shell_lower_mm.size();++k)
    if(d<shell_lower_mm[k])return k-1;
  return shell_lower_mm.size()-1;
}

inline int polar_bin(double mu){
  const double clamped=std::clamp(mu,-1.,1.);
  return std::clamp(int((clamped+1.)*5.),0,polar_bands-1);
}

// Exactly the P10L 4x4x4 curved Tet10 geometry, but contract it with frozen
// psi/theta vectors at the QP before the ordinary assembly loses localization.
// In the full adjoint psi_n already contains all time weights/shape chains.
inline Snapshot contract_step(const Mesh& mesh,const std::vector<V>& velocity,
                            const std::vector<double>& psi,
                            const std::vector<double>& theta,
                            const std::vector<double>& previous,
                            double dt,double ambient){
  const std::size_t nn=mesh.nodes.size();
  if(velocity.size()!=nn||psi.size()!=nn||theta.size()!=nn||
     previous.size()!=nn||!(dt>0.)||!std::isfinite(dt)||
     !std::isfinite(ambient))
    throw std::invalid_argument("P10BW: bad input size/time");
  for(std::size_t i=0;i<nn;++i){
    const V v=velocity[i];
    if(!std::isfinite(v.x)||!std::isfinite(v.y)||!std::isfinite(v.z)||
       !std::isfinite(psi[i])||!std::isfinite(theta[i])||
       !std::isfinite(previous[i]))
      throw std::invalid_argument("P10BW: nonfinite field/velocity input");
  }
  Snapshot result;
  const V centre{0.,0.,.03};
  const auto& qs=ice3d::p10l::quadrature();
  for(const auto& tet:mesh.tets)for(const auto& q:qs){
    V dr{},ds{},dv{},drp{},dsp{},dvp{},x{};
    for(int i=0;i<10;++i){
      const V node=mesh.nodes[tet[i]],v=velocity[tet[i]];
      dr=dr+node*q.d[i][0];ds=ds+node*q.d[i][1];
      dv=dv+node*q.d[i][2];
      drp=drp+v*q.d[i][0];dsp=dsp+v*q.d[i][1];
      dvp=dvp+v*q.d[i][2];
      x=x+node*q.N[i];
    }
    const V a=cross(ds,dv),b=cross(dv,dr),c=cross(dr,ds);
    const V da=cross(dsp,dv)+cross(ds,dvp);
    const V db=cross(dvp,dr)+cross(dv,drp);
    const V dc=cross(drp,ds)+cross(dr,dsp);
    const double det=dot(dr,a),ddet=dot(drp,a)+dot(dr,da);
    if(!(det>0.))throw std::runtime_error("P10BW: nonpositive Tet10 Jacobian");
    const double w=q.w*det,dw=q.w*ddet;
    V grad_psi{},grad_theta{},dgrad_psi{},dgrad_theta{};
    double psi_q=0.,diff_q=0.,theta_q=0.;
    for(int i=0;i<10;++i){
      const std::size_t j=std::size_t(tet[i]);
      const auto& d=q.d[i];
      const V grad=(a*d[0]+b*d[1]+c*d[2])/det;
      const V dgrad=(da*d[0]+db*d[1]+dc*d[2])/det-grad*(ddet/det);
      grad_psi=grad_psi+grad*psi[j];
      grad_theta=grad_theta+grad*theta[j];
      dgrad_psi=dgrad_psi+dgrad*psi[j];
      dgrad_theta=dgrad_theta+dgrad*theta[j];
      psi_q+=q.N[i]*psi[j];
      diff_q+=q.N[i]*(theta[j]-previous[j]);
      theta_q+=q.N[i]*theta[j];
    }
    const V radial=x-centre;
    const double r=norm(radial);
    if(!(r>0.))throw std::runtime_error("P10BW: QP at pore centre");
    const std::size_t ishell=shell_bin((r-RBASE)*1000.);
    const int ipolar=polar_bin(radial.z/r);
    Cell& bin=result.cells[ishell*10+std::size_t(ipolar)];
    bin.qp_count+=1;
    bin.volume+=w;
    bin.theta_integral+=w*theta_q;
    bin.part.mass+=ice3d::p10l::rhocp*dw*psi_q*diff_q;
    bin.part.diffusion+=dt*ice3d::p10l::conductivity*(
        dw*dot(grad_psi,grad_theta)+
        w*(dot(dgrad_psi,grad_theta)+dot(grad_psi,dgrad_theta)));
  }
  // Keep top Robin surface separate, including both dK_robin and dload.
  Mesh velocity_mesh; // seval needs only nodes: no expensive tet/face copy.
  velocity_mesh.nodes=velocity;
  for(const auto& face:mesh.faces)if(face.tag==2){
    for(auto ga:g4)for(auto gb:g4){
      const double r=ga.x,s=(1-r)*gb.x;
      const auto x=seval(mesh,face.nodes,r,s);
      const auto v=seval(velocity_mesh,face.nodes,r,s);
      const V normal=cross(x.du,x.dv);
      const V dnormal=cross(v.du,x.dv)+cross(x.du,v.dv);
      const double size=norm(normal);
      if(!(size>0.))throw std::runtime_error("P10BW: zero top Tri6 area");
      const double weight=ga.w*gb.w*(1-r);
      const double darea=weight*dot(normal,dnormal)/size;
      const auto N=ice3d::p10l::face_shape(r,s);
      double psi_q=0.,theta_q=0.;
      for(int i=0;i<6;++i){
        const std::size_t j=std::size_t(face.nodes[i]);
        psi_q+=N[i]*psi[j];theta_q+=N[i]*theta[j];
      }
      result.top_qp_count+=1;
      result.top_area+=weight*size;
      result.top_robin.robin+=dt*ice3d::p10l::robin*darea*psi_q*(theta_q-ambient);
    }
  }
  return result;
}

} // namespace ice3d::p10bw
