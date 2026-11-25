// P10LJ: execute the real 27-QP P10LG mechanical_step on one synthetic Tet10.
// No assembled FEM, linear solver, Gmsh, physical mesh or one-shot marker.
#define STAGE3D10DD_FULL4D 1
#define STAGE3D10DK_M1_FULL4D 1
#include "stage3d10w_analytic_adjoint.cpp"

#include <iostream>
#include <stdexcept>

namespace {
void require(bool yes,const char* reason){if(!yes)throw std::runtime_error(reason);}
}

int main(){
 try{
  Mesh mesh;
  const std::array<V,4> vertex{{
    V{.0014,.0003,.0297},V{.0034,.0003,.0297},
    V{.0014,.0023,.0297},V{.0014,.0003,.0317}}};
  for(const auto& p:vertex)mesh.nodes.push_back(p);
  constexpr int edges[6][2]={{0,1},{1,2},{2,0},{0,3},{1,3},{2,3}};
  for(const auto& edge:edges)
   mesh.nodes.push_back((vertex[edge[0]]+vertex[edge[1]])*.5);
  mesh.tets.push_back(Tet{0,1,2,3,4,5,6,7,8,9});
  auto quad=volume_q(3);
  require(quad.size()==27,"Tet10 quadrature must have 27 points");
  const int nn=int(mesh.nodes.size());
  std::vector<double> u(3*std::size_t(nn),0.);
  std::vector<V> velocity(static_cast<std::size_t>(nn),V{});
  for(int k=0;k<nn;++k){
   const auto x=mesh.nodes[std::size_t(k)];
   const double dx=x.x-.0014,dy=x.y-.0003,dz=x.z-.0297;
   u[3*k+0]=.00012*dx+.00003*dy;
   u[3*k+1]=-.00008*dy+.00002*dz;
   u[3*k+2]=.00005*dz;
   velocity[std::size_t(k)]=V{.16*dx+.04*dy,-.12*dy,.05*dz};
  }
  // Two independent mid-edge variations produce a non-affine strain field
  // and a non-affine smooth velocity on this quadratic element.
  u[3*5+0]+=.00000009;
  u[3*8+1]-=.00000012;
  velocity[5].x+=.00018;
  velocity[8].z-=.00015;
  const std::vector<std::uint8_t> constrained(3*std::size_t(nn),0);
  const std::vector<std::uint8_t> mask{1};
  const std::vector<double> temperature(std::size_t(nn),0.);
  const std::vector<ice3d::p10c::State> previous(27);
  const std::vector<ice3d::p10c::State> futures(27);
  const std::vector<double> lambda(3*std::size_t(nn),0.);
  const ice3d::p10c::Step step(mesh,quad,temperature,previous,150.,u,
                         constrained,ice3d::p10b::Modulus::CONST,{});
  const auto result=ice3d::p10dd::mechanical_step(mesh,quad,step,velocity,
                                 mask,lambda,futures,1.);
  require(result.mechanical_qps()==27,"unexpected QP count");
  require(result.observed_volume>0.,"empty observation mask");
  double geom=0.,stress=0.;std::size_t occupied=0;
  for(const auto& c:result.cells){
   geom+=c.explicit_geometry;stress+=c.explicit_stress;
   if(c.mechanical_qp)++occupied;
  }
  const double original=result.sum().explicit_objective;
  require(std::isfinite(geom)&&std::isfinite(stress),"nonfinite split");
  require(std::abs(geom)>1.e-18,"geometry term unexpectedly zero");
  require(std::abs(stress)>1.e-18,"stress term unexpectedly zero");
  ice3d::p10dd::expect_close(geom+stress,original,"P10LJ exact 27-QP total",1.e-10);
  // Analytic directional linearity: a velocity sign reversal must negate
  // both independent contributions, and zero velocity must annihilate both.
  auto minus_velocity=velocity;
  for(auto& v:minus_velocity)v=v*(-1.);
  const auto reversed=ice3d::p10dd::mechanical_step(mesh,quad,step,minus_velocity,
                                 mask,lambda,futures,1.);
  double reversed_geom=0.,reversed_stress=0.;
  for(const auto& c:reversed.cells){
   reversed_geom+=c.explicit_geometry;reversed_stress+=c.explicit_stress;
  }
  ice3d::p10dd::expect_close(reversed_geom,-geom,"P10LJ odd geometry",1.e-10);
  ice3d::p10dd::expect_close(reversed_stress,-stress,"P10LJ odd stress",1.e-10);
  const std::vector<V> zero_velocity(std::size_t(nn),V{});
  const auto zero=ice3d::p10dd::mechanical_step(mesh,quad,step,zero_velocity,
                                 mask,lambda,futures,1.);
  ice3d::p10dd::expect_close(zero.sum().explicit_objective,0.,
                             "P10LJ zero velocity",1.e-10);
  for(const auto& c:zero.cells){
   require(c.explicit_geometry==0.&&c.explicit_stress==0.,
           "zero velocity produced nonzero per-cell contribution");
  }
  std::cout<<std::setprecision(17)
           <<"P10LJ_CPP_TET10_MECHANICAL_STEP_PASS qps=27 bins="<<occupied
           <<" volume="<<result.observed_volume
           <<" geometry="<<geom<<" stress="<<stress
           <<" explicit="<<original<<" odd_velocity=PASS zero_velocity=PASS no_FEM=1\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P10LJ_CPP_TET10_MECHANICAL_STEP_FAIL "<<e.what()<<'\n';return 1;
 }
}
