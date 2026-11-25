// P10LR actual accepted M9 topology, synthetic tensor fields. No FEM solve.
#define STAGE3D10DD_FULL4D 1
#define STAGE3D10DK_M1_FULL4D 1
#include "stage3d10w_analytic_adjoint.cpp"
#include "p10lr_tet10_face_jump.hpp"
#include <iostream>

int main(int argc,char** argv){
 try{
  if(argc!=2)throw std::invalid_argument("P10LR requires exact M9 msh argument");
  const auto mesh=read_msh(fs::path(argv[1])).mesh;
  if(mesh.nodes.size()!=19236||mesh.tets.size()!=13166)
   throw std::runtime_error("P10LR unexpected M9 mesh dimensions");
  const auto quad=volume_q(3);
  const std::size_t nq=mesh.tets.size()*27;
  std::vector<std::array<double,6>> sigma(nq),dsigma(nq);
  for(auto& s:sigma)s={{1.,2.,3.,4.,5.,6.}};
  for(auto& s:dsigma)s={{-3.,2.,1.,0.,0.,0.}};
  const std::vector<std::uint8_t> mask(mesh.tets.size(),1);
  const auto p1=p10lr::evaluate(mesh,quad,sigma,dsigma,mask,1);
  const auto p2=p10lr::evaluate(mesh,quad,sigma,dsigma,mask,2);
  if(p1.interior_pairs!=25470||p2.interior_pairs!=25470||
     p1.observed_pairs!=25470||p2.observed_pairs!=25470)
   throw std::runtime_error("P10LR M9 face graph cardinality mismatch");
  if(p1.global.stress_frob_max>1.e-9||p2.global.stress_frob_max>1.e-9||
     p1.global.traction_max>1.e-9||p2.global.geom_jvp_max>1.e-9)
   throw std::runtime_error("P10LR constant tensor generated false face jump");
  // Deliberate interface discontinuity in one element at all 27 QPs.
  for(std::size_t i=0;i<27;++i){sigma[i][0]+=1000.;dsigma[i][2]-=500.;}
  const auto broken=p10lr::evaluate(mesh,quad,sigma,dsigma,mask,2);
  if(broken.global.stress_frob_max<900.||
     broken.global.geom_jvp_max<450.||
     broken.global.traction_max<=0.)
   throw std::runtime_error("P10LR failed to detect synthetic element jump");
  std::cout<<"P10LR_ACTUAL_M9_SYNTH_FACE_JUMP_PASS interior_faces="
           <<p2.interior_pairs<<" centroid_gap="<<p2.max_two_sided_centroid_gap
           <<" constant_jump_max="<<p2.global.stress_frob_max
           <<" injected_stress_jump="<<broken.global.stress_frob_max
           <<" injected_shape_jvp_jump="<<broken.global.geom_jvp_max
           <<" no_FEM=1\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P10LR_ACTUAL_M9_SYNTH_FACE_JUMP_FAIL "<<e.what()<<'\n';return 1;
 }
}
