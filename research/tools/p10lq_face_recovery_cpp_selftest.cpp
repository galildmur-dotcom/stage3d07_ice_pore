#include "p10lq_tet10_face_recovery.hpp"
#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

struct Q {std::array<double,10> N;double w;};
using T=std::array<double,6>;
void check(bool b,const char* m){if(!b)throw std::runtime_error(m);}

int main(){
 try{
  std::vector<Q> q;
  for(double r:{.13,.39,.73})for(double s0:{.13,.39,.73})
   for(double t0:{.13,.39,.73}){
    const double s=(1-r)*s0,t=(1-r)*(1-s0)*t0;
    const std::array<double,4> l{{1-r-s-t,r,s,t}};
    q.push_back({p10lq::quadratic(l),1.});
   }
  const auto p1=p10lq::prepare(q,1),p2=p10lq::prepare(q,2);
  check(p1.max_constant_error<1e-11&&p2.max_constant_error<1e-11,
        "constant reconstruction");
  std::vector<T> linear,quadratic;
  for(const auto& x:q){
   const auto l=p10lq::barycentric(x.N);
   T a{},b{};
   for(int j=0;j<6;++j){
    a[j]=1.+j+2*l[0]-3*l[1]+4*l[2]+7*l[3];
    b[j]=a[j]+(1+j*.25)*l[0]*l[1]+2*l[2]*l[3];
   }
   linear.push_back(a);quadratic.push_back(b);
  }
  double max_linear=0.,max_quadratic=0.,sensitivity=0.;
  for(int face=0;face<4;++face){
   const auto l=p10lq::face_center(face);
   const auto v1=p10lq::recover(p1,face,linear,0);
   const auto v2=p10lq::recover(p2,face,quadratic,0);
   const auto vlow=p10lq::recover(p1,face,quadratic,0);
   for(int j=0;j<6;++j){
    const double exact_linear=1.+j+2*l[0]-3*l[1]+4*l[2]+7*l[3];
    const double exact_q=exact_linear+(1+j*.25)*l[0]*l[1]+2*l[2]*l[3];
    max_linear=std::max(max_linear,std::abs(v1[j]-exact_linear));
    max_quadratic=std::max(max_quadratic,std::abs(v2[j]-exact_q));
    sensitivity=std::max(sensitivity,std::abs(vlow[j]-v2[j]));
   }
  }
  check(max_linear<1e-10,"P1 linear polynomial not exact");
  check(max_quadratic<1e-10,"P2 quadratic polynomial not exact");
  check(sensitivity>1e-5,"P1/P2 reconstruction sensitivity not detected");
  const T left{{1,2,3,4,5,6}},right{{0,0,0,0,0,0}};
  check(std::abs(p10lq::stress_jump_frobenius(left,right)-std::sqrt(168.))<1e-12,
        "Voigt shear weights wrong");
  check(std::abs(p10lq::traction_jump(left,right,{{1,0,0}})-std::sqrt(53.))<1e-12,
        "traction normal projection wrong");
  bool rejected=false;
  try{std::vector<Q> singular(27,q.front());(void)p10lq::prepare(singular,2);}
  catch(const std::runtime_error&){rejected=true;}
  check(rejected,"degenerate QP basis not rejected");
  std::cout<<"P10LQ_FACE_RECOVERY_CPP_SELFTEST_PASS P1_err="<<max_linear
           <<" P2_err="<<max_quadratic
           <<" sensitivity="<<sensitivity
           <<" singular_rejected=1 no_FEM=1\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P10LQ_FACE_RECOVERY_CPP_FAIL "<<e.what()<<'\n';return 1;
 }
}
