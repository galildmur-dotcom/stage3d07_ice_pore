// Actual Stage3D07 27-QP scheme against stand-alone P10LQ recovery.
#define STAGE3D10DD_FULL4D 1
#define STAGE3D10DK_M1_FULL4D 1
#include "stage3d10w_analytic_adjoint.cpp"
#include "p10lq_tet10_face_recovery.hpp"
#include <iostream>
#include <stdexcept>

int main(){
 try{
  const auto quad=volume_q(3);
  const auto p1=p10lq::prepare(quad,1);
  const auto p2=p10lq::prepare(quad,2);
  double worst=0.;
  for(int f=0;f<4;++f){
   std::vector<std::array<double,6>> quadratic;
   for(const auto& q:quad){
    const auto l=p10lq::barycentric(q.N);
    std::array<double,6> t{};
    for(int k=0;k<6;++k)t[k]=1.+k+3*l[0]-2*l[1]+5*l[2]*l[3];
    quadratic.push_back(t);
   }
   const auto actual=p10lq::recover(p2,f,quadratic,0);
   const auto l=p10lq::face_center(f);
   for(int k=0;k<6;++k){
    const double expected=1.+k+3*l[0]-2*l[1]+5*l[2]*l[3];
    worst=std::max(worst,std::abs(actual[k]-expected));
   }
  }
  if(worst>1.e-10)throw std::runtime_error("P10LQ production 27QP quadratic mismatch");
  std::cout<<"P10LQ_PRODUCTION_27QP_RECOVERY_PASS p1_const_err="
           <<p1.max_constant_error<<" p2_const_err="<<p2.max_constant_error
           <<" worst_quadratic_err="<<worst<<" no_FEM=1\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P10LQ_PRODUCTION_27QP_RECOVERY_FAIL "<<e.what()<<'\n';return 1;
 }
}
