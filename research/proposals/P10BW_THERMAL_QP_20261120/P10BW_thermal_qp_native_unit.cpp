// P10BW self-contained native unit, no nonlinear/thermal forward FEM solve.
// Compile with the two exact P10BM pinned sources in ../pinned and the
// proposal header in this folder. Test input is a small generated Tet10 mesh.
#define STAGE3D01_LIBRARY
#include "geometry_stage3d01.cpp"
#include "stage3d10l_thermal_adjoint.hpp"
#include "stage3d10bw_thermal_qp_partition.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string_view>

namespace H=ice3d::p10l;
namespace W=ice3d::p10bw;

std::vector<V> shape_velocity(const Mesh& mesh,std::string_view mode){
  std::vector<V> result;result.reserve(mesh.nodes.size());
  for(const auto& x:mesh.nodes){
    const V radial=x-V{0.,0.,.03};
    const double r=norm(radial),cutoff=.005;
    if(!(r>0.))throw std::runtime_error("P10BW invalid reference radius");
    double f=1.;
    if(r>=cutoff)f=0.;
    else if(r>RBASE){
      const double t=(r-RBASE)/(cutoff-RBASE);
      f=1.-t*t*(3.-2.*t);
    }
    const V n=radial/r;
    if(mode=="top"){
      result.push_back(x.z>.04?V{.2*x.x/.001,.1*x.y/.001,0.}:V{});
    }else if(mode=="R")result.push_back(n*f);
    else if(mode=="tz")result.push_back(V{0.,0.,f});
    else if(mode=="y20"){
      const double Y=std::sqrt(5./(16.*PI))*(3.*n.z*n.z-1.);
      result.push_back(n*(f*Y));
    }else throw std::runtime_error("P10BW unknown shape mode");
  }
  return result;
}

double contract_primal(const H::CSR& P,const std::vector<double>& psi,
                       const std::vector<double>& theta,
                       const std::vector<double>& previous,
                       double dt,double ambient){
  std::vector<double> diff(theta.size()),M,K;
  for(std::size_t i=0;i<theta.size();++i)diff[i]=theta[i]-previous[i];
  P.mul(P.mass,diff,M);
  P.mul(P.conduct,theta,K);
  double s=0.;for(std::size_t i=0;i<psi.size();++i)
    s+=psi[i]*(M[i]+dt*K[i]-dt*P.robinload[i]*ambient);
  return s;
}

void check_close(double a,double b,std::string_view label,
                 double rel=2.e-9,double abs=2.e-8){
  const double scale=std::max({abs,std::abs(a),std::abs(b)});
  if(!std::isfinite(a)||!std::isfinite(b)||std::abs(a-b)>rel*scale+abs){
    std::cerr<<label<<" mismatch a="<<std::setprecision(17)<<a
             <<" b="<<b<<" abs="<<std::abs(a-b)<<'\n';
    throw std::runtime_error("P10BW shape partition failed");
  }
}

void test_case(const Mesh& mesh,std::string_view mode,int dt){
  const auto V0=shape_velocity(mesh,mode);
  std::vector<double> theta(mesh.nodes.size()),previous(mesh.nodes.size()),
                      psi(mesh.nodes.size());
  for(std::size_t i=0;i<mesh.nodes.size();++i){
    const auto& x=mesh.nodes[i];
    theta[i]=-.9+2.2*x.z+0.17*std::sin(double(i)*.41);
    previous[i]=-.5+1.3*x.z+0.11*std::cos(double(i)*.23);
    psi[i]=.3+0.08*std::cos(double(i)*.37);
  }
  constexpr double amb=-2.1;
  const auto A=H::assemble(mesh,V0,double(dt));
  const auto local=W::contract_step(mesh,V0,psi,theta,previous,double(dt),amb);
  std::vector<double> diff(theta.size()),mass,conduct;
  for(std::size_t i=0;i<theta.size();++i)diff[i]=theta[i]-previous[i];
  A.shape.mul(A.shape.mass,diff,mass);
  A.shape.mul(A.shape.conduct,theta,conduct);
  double gmass=0.,gtherm=0.;
  for(std::size_t i=0;i<psi.size();++i){
    gmass+=psi[i]*mass[i];
    gtherm+=psi[i]*(double(dt)*conduct[i]-double(dt)*A.shape.robinload[i]*amb);
  }
  const auto x=local.total();
  check_close(x.mass,gmass,"mass",1.e-9,5.e-9);
  check_close(x.diffusion+x.robin,gtherm,"diffusion+robin",1.e-9,5.e-9);
  check_close(x.total(),gmass+gtherm,"all",1.e-9,5.e-9);
  if(local.thermal_qp_count()!=mesh.tets.size()*H::quadrature().size())
    throw std::runtime_error("P10BW volume QP count mismatch");
  std::size_t faces=0;for(const auto& f:mesh.faces)if(f.tag==2)++faces;
  if(local.top_qp_count!=16*faces)
    throw std::runtime_error("P10BW face QP count mismatch");
  if(!(local.thermal_qp_volume()>0.)||!(local.top_area>0.))
    throw std::runtime_error("P10BW nonpositive integrated geometry");
  double max_top_speed=0.;
  for(const auto& f:mesh.faces)if(f.tag==2)for(int j:f.nodes)
    max_top_speed=std::max(max_top_speed,norm(V0[std::size_t(j)]));
  if(mode=="top"){
    if(max_top_speed<1e-3||std::abs(x.robin)<1e-10)
      throw std::runtime_error("P10BW moving top Robin unexpectedly zero");
  }else if(max_top_speed>1e-14||std::abs(x.robin)>1e-13){
    throw std::runtime_error("P10BW R/tz/y20 remote top Robin not zero");
  }

  // Independent finite-difference check of the frozen *geometric operator*,
  // never used for the shape partial in the proposed production recorder.
  const double eps=2.e-8;
  Mesh plus=mesh,minus=mesh;
  for(std::size_t i=0;i<mesh.nodes.size();++i){
    plus.nodes[i]=plus.nodes[i]+V0[i]*eps;
    minus.nodes[i]=minus.nodes[i]-V0[i]*eps;
  }
  const std::vector<V> zero(mesh.nodes.size());
  const auto Ap=H::assemble(plus,zero,double(dt));
  const auto Am=H::assemble(minus,zero,double(dt));
  const double fd=(contract_primal(Ap.primal,psi,theta,previous,double(dt),amb)-
                   contract_primal(Am.primal,psi,theta,previous,double(dt),amb))
                 /(2.*eps);
  const double relative=std::abs(fd-x.total())/
                        std::max({1.e-10,std::abs(fd),std::abs(x.total())});
  if(relative>2.e-5)
    throw std::runtime_error("P10BW independent FD geometry check failed");
  std::cout<<std::scientific<<std::setprecision(12)
           <<"P10BW_NATIVE_UNIT_OK mode="<<mode<<" dt_s="<<dt
           <<" nodes="<<mesh.nodes.size()<<" tet10="<<mesh.tets.size()
           <<" volume_qp="<<local.thermal_qp_count()
           <<" top_qp="<<local.top_qp_count
           <<" mass="<<x.mass<<" diffusion="<<x.diffusion
           <<" robin="<<x.robin<<" total="<<x.total()
           <<" matrix_residual="<<x.total()-(gmass+gtherm)
           <<" independent_fd_rel="<<relative<<'\n';
}

Mesh synthetic_mesh(){
  // Two face-sharing curved Tet10 near the pore and one *separate* remote top
  // Tri6. This is an operator unit mesh, not a valid physical ice FEM domain.
  Mesh m;
  m.center={0.,0.,.03};m.radius=RBASE;
  const std::array<V,5> corner{{
      {.001,0.,.03},{.0014,0.,.03},
      {.001,.0004,.03},{.001,0.,.0304},
      {.0014,.0004,.0304}}};
  for(const auto& x:corner)m.nodes.push_back(x);
  constexpr int edges[6][2]{{0,1},{1,2},{2,0},{0,3},{1,3},{2,3}};
  std::map<Edge,int> midpoints;
  auto middle=[&](int a,int b){
    const Edge key=edge(a,b);
    auto it=midpoints.find(key);
    if(it!=midpoints.end())return it->second;
    V x=(corner[a]+corner[b])*.5;
    if(key==edge(1,2))x.z+=.000005; // curved shared edge
    const int id=int(m.nodes.size());m.nodes.push_back(x);
    midpoints.emplace(key,id);return id;
  };
  for(std::array<int,4> corners: {std::array<int,4>{0,1,2,3},
                                   std::array<int,4>{1,2,3,4}}){
    if(jac_linear(corner[corners[0]],corner[corners[1]],
                  corner[corners[2]],corner[corners[3]])<0)
      std::swap(corners[1],corners[2]);
    Tet ten{};
    for(int i=0;i<4;++i)ten[i]=corners[i];
    for(int e=0;e<6;++e)
      ten[4+e]=middle(corners[edges[e][0]],corners[edges[e][1]]);
    m.tets.push_back(ten);
  }
  const std::array<V,3> top{{
      {0.,0.,.05},{.001,0.,.05},{0.,.001,.05}}};
  const int base=int(m.nodes.size());
  for(const auto& x:top)m.nodes.push_back(x);
  for(int e=0;e<3;++e){
    const V x=(top[e]+top[(e+1)%3])*.5;
    m.nodes.push_back(x);
  }
  Face f;f.tag=2;
  // Tri6 nodes: corners (0,1,2) and edges (01,12,20).
  for(int j=0;j<6;++j)f.nodes[j]=base+j;
  m.faces.push_back(f);
  return m;
}

int main(){
  try{
    const Mesh mesh=synthetic_mesh();
    int tested=0;
    for(const int dt:{150,75,50,25}){
      test_case(mesh,"R",dt);++tested;
    }
    for(const auto mode:{"tz","y20"}){
      test_case(mesh,mode,150);++tested;
    }
    test_case(mesh,"top",75);++tested;
    std::cout<<"P10BW_EXACT_P10L_QP_PARTITION_UNIT_OK tests="<<tested
             <<" FEM=0 production_patch_applied=NO\n";
  }catch(const std::exception& e){
    std::cerr<<"P10BW_STOP reason="<<e.what()<<'\n';return 2;
  }
}
