#pragma once
// P10LR physical face geometry and paired *recovered* one-sided stress traces.
// Include after the production Tet10 Mesh/V/tetshape/volume_q declarations.
#include "p10lq_tet10_face_recovery.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <vector>

namespace p10lr {
using Tensor=std::array<double,6>;
struct FaceOwner {std::size_t tet;int side;};
struct FacePair {FaceOwner a,b;};

template<class MeshType>
std::vector<FacePair> interior_faces(const MeshType& mesh){
 std::map<std::array<int,3>,std::vector<FaceOwner>> edges;
 for(std::size_t e=0;e<mesh.tets.size();++e){
  const auto& tet=mesh.tets[e];
  for(int f=0;f<4;++f){
   auto sides=p10lq::tetra_faces[std::size_t(f)];
   std::array<int,3> key{{tet[sides[0]],tet[sides[1]],tet[sides[2]]}};
   std::sort(key.begin(),key.end());
   edges[key].push_back({e,f});
  }
 }
 std::vector<FacePair> pairs;
 for(const auto& [key,owners]:edges){
  if(owners.size()==2)pairs.push_back({owners[0],owners[1]});
  else if(owners.size()!=1)
   throw std::runtime_error("P10LR non-manifold shared face");
 }
 return pairs;
}

inline std::array<V,4> local_reference_vertices(){
 return {{{0,0,0},{1,0,0},{0,1,0},{0,0,1}}};
}
template<class MeshType>
std::pair<V,std::array<double,3>> face_center_normal(const MeshType& mesh,
                                                      FaceOwner face){
 const auto& ids=mesh.tets.at(face.tet);
 const auto corner=p10lq::tetra_faces.at(std::size_t(face.side));
 const auto ref=local_reference_vertices();
 const auto l=p10lq::face_center(face.side);
 const V d1=ref[std::size_t(corner[1])]-ref[std::size_t(corner[0])];
 const V d2=ref[std::size_t(corner[2])]-ref[std::size_t(corner[0])];
 std::array<double,10> N{};
 std::array<std::array<double,3>,10> dN{};
 tetshape(l[1],l[2],l[3],N,dN);
 V x{},t1{},t2{};
 for(int a=0;a<10;++a){
  const auto p=mesh.nodes.at(std::size_t(ids[a]));
  x=x+p*N[std::size_t(a)];
  t1=t1+p*(dN[std::size_t(a)][0]*d1.x+
           dN[std::size_t(a)][1]*d1.y+dN[std::size_t(a)][2]*d1.z);
  t2=t2+p*(dN[std::size_t(a)][0]*d2.x+
           dN[std::size_t(a)][1]*d2.y+dN[std::size_t(a)][2]*d2.z);
 }
 const auto n=cross(t1,t2);
 const double len=norm(n);
 if(!(len>0.)||!std::isfinite(len))throw std::runtime_error("P10LR degenerate curved face");
 return {x,{{n.x/len,n.y/len,n.z/len}}};
}

struct Moments {
 std::size_t faces=0;
 double stress_frob_sum=0.,stress_frob_square=0.,stress_frob_max=0.;
 double traction_sum=0.,traction_square=0.,traction_max=0.;
 double geom_jvp_frob_sum=0.,geom_jvp_square=0.,geom_jvp_max=0.;
 void add(double stress,double traction,double derivative){
  ++faces;
  stress_frob_sum+=stress;stress_frob_square+=stress*stress;
  traction_sum+=traction;traction_square+=traction*traction;
  geom_jvp_frob_sum+=derivative;geom_jvp_square+=derivative*derivative;
  stress_frob_max=std::max(stress_frob_max,stress);
  traction_max=std::max(traction_max,traction);
  geom_jvp_max=std::max(geom_jvp_max,derivative);
 }
};
struct Result {
 std::size_t interior_pairs=0,observed_pairs=0;
 double max_two_sided_centroid_gap=0.;
 std::array<Moments,1200> cells{};
 Moments global{};
};

// The mask chooses elements included in the near-pore observation region.
// Requires both elements of an interior face to be included, to avoid mixing
// physical B6 boundaries with an interelement stress discontinuity.
template<class MeshType,class Quad>
Result evaluate(const MeshType& mesh,const std::vector<Quad>& quad,
                const std::vector<Tensor>& sigma,
                const std::vector<Tensor>& geometric_dsigma,
                const std::vector<std::uint8_t>& element_mask,int degree){
 const std::size_t nq=mesh.tets.size()*27;
 if(quad.size()!=27||sigma.size()!=nq||geometric_dsigma.size()!=nq||
    element_mask.size()!=mesh.tets.size())
  throw std::invalid_argument("P10LR stress/velocity/QP dimensions");
 const auto recovery=p10lq::prepare(quad,degree);
 Result out;
 const auto pairs=interior_faces(mesh);
 out.interior_pairs=pairs.size();
 for(const auto& pair:pairs){
  if(!element_mask[pair.a.tet]||!element_mask[pair.b.tet])continue;
  const auto [x,n]=face_center_normal(mesh,pair.a);
  const auto [y,m]=face_center_normal(mesh,pair.b);
  const double gap=norm(x-y);
  out.max_two_sided_centroid_gap=std::max(out.max_two_sided_centroid_gap,gap);
  if(gap>1.e-10)throw std::runtime_error("P10LR faces do not share a physical curved centroid");
  const auto a=p10lq::recover(recovery,pair.a.side,sigma,pair.a.tet*27);
  const auto b=p10lq::recover(recovery,pair.b.side,sigma,pair.b.tet*27);
  const auto da=p10lq::recover(recovery,pair.a.side,geometric_dsigma,pair.a.tet*27);
  const auto db=p10lq::recover(recovery,pair.b.side,geometric_dsigma,pair.b.tet*27);
  const double js=p10lq::stress_jump_frobenius(a,b);
  const double jt=p10lq::traction_jump(a,b,n);
  const double jd=p10lq::stress_jump_frobenius(da,db);
  if(!std::isfinite(js)||!std::isfinite(jt)||!std::isfinite(jd))
   throw std::runtime_error("P10LR nonfinite face jump");
  const auto id=ice3d::p10dd::index(x);
  out.cells[id].add(js,jt,jd);
  out.global.add(js,jt,jd);
 }
 out.observed_pairs=out.global.faces;
 return out;
}
} // namespace p10lr
