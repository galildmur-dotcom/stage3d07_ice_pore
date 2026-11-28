// Stage3D07 P10PU - source-only integration pilot with REAL upstream Algoim.
// Only geometric octant spherical shells, NOT physical FEM/EDV, NOT full 4D bins.
// Build: g++ -std=c++17 -O2 -I/path/to/algoim/algoim this.cpp -o pilot
// Provenance: https://github.com/algoim/algoim (upstream, BSD-like license).
#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

#include "quadrature_general.hpp"

struct Sphere{
 double radius_squared;
 template<typename T> T operator()(const algoim::uvector<T,3>& p)const{
  return p(0)*p(0)+p(1)*p(1)+p(2)*p(2)-radius_squared;
 }
 template<typename T> algoim::uvector<T,3> grad(const algoim::uvector<T,3>& p)const{
  return algoim::uvector<T,3>(2.*p(0),2.*p(1),2.*p(2));
 }
};

struct ReferenceTet{
 template<typename T> T operator()(const algoim::uvector<T,3>& p)const{
  return p(0)+p(1)+p(2)-1.;
 }
 template<typename T> algoim::uvector<T,3> grad(const algoim::uvector<T,3>&)const{
  return algoim::uvector<T,3>(1.,1.,1.);
 }
};

int main(){
 try{
  constexpr double r0=.08,r1=.22;
  constexpr double pi=3.141592653589793238462643383279502884;
  const double reference=pi/6.*(r1*r1*r1-r0*r0*r0);
  const algoim::uvector<double,3> lower{0.,0.,0.},upper{r1,r1,r1};
  const algoim::HyperRectangle<double,3> box(lower,upper);
  const Sphere outer{r1*r1}, inner{r0*r0};
  std::cout<<std::setprecision(16);
  for(int q:{2,3,4,5,6,8}){
   auto start=std::chrono::steady_clock::now();
   const auto out=algoim::quadGen<3>(outer,box,-1,-1,q);
   const auto in=algoim::quadGen<3>(inner,box,-1,-1,q);
   auto elapsed=std::chrono::duration<double>(
       std::chrono::steady_clock::now()-start).count();
   const double estimate=out.sumWeights()-in.sumWeights();
   const double error=std::abs(estimate-reference)/reference;
   const bool weights_positive=std::all_of(out.nodes.begin(),out.nodes.end(),
       [](const auto& pt){return pt.w>0&&std::isfinite(pt.w);})&&
       std::all_of(in.nodes.begin(),in.nodes.end(),
       [](const auto& pt){return pt.w>0&&std::isfinite(pt.w);});
   if(!weights_positive||!(estimate>0)||!std::isfinite(error))
     throw std::runtime_error("P10PU invalid positive weights or shell volume");
   std::cout<<"P10PU_ALGOIM_SHELL q="<<q<<" integral="<<estimate
     <<" reference="<<reference<<" relative_error="<<error
     <<" nodes_outer="<<out.nodes.size()<<" nodes_inner="<<in.nodes.size()
     <<" elapsed_s="<<elapsed<<" positive_weights=1\n";
   if(q==8 && error>0.001)
     throw std::runtime_error("P10PU final source-only shell accuracy");
  }
  // A true quadratic curved Tet10 map is x=u, y=v, z=w*(1+alpha*u).
  // Its physical Jacobian is 1+alpha*u. The reference-tetra domain
  // is cut by an independent rectangular cap u<=a. Unlike our first
  // sphere test, this tests reference-element geometry and a nonconstant
  // Jacobian (but STILL not several implicit level-set cuts at once).
  constexpr double a=.28,alpha=.3;
  const double cap_reference=.5*((a-a*a+a*a*a/3.)+
       alpha*(a*a/2.-2.*a*a*a/3.+a*a*a*a/4.));
  const algoim::HyperRectangle<double,3> cap_box(
      algoim::uvector<double,3>{0,0,0},algoim::uvector<double,3>{a,1,1});
  const ReferenceTet tet;
  // Exactly match P10PT's quadratic shear F(u,v,w)=(u,v,w+0.5*u*v),
  // det DF = 1 and the same cap a=.28.
  const auto matched=algoim::quadGen<3>(tet,cap_box,-1,-1,4);
  const double matched_reference=.5*(a-a*a+a*a*a/3.);
  const double matched_error=std::abs(matched.sumWeights()-matched_reference)/matched_reference;
  if(matched_error>1.e-12)
    throw std::runtime_error("P10PU versus P10PT exact curved shear cap mismatch");
  std::cout<<"P10PU_ALGOIM_P10PT_MATCHED_CAP q=4 integral="
      <<matched.sumWeights()<<" reference="<<matched_reference
      <<" relative_error="<<matched_error
      <<" nodes="<<matched.nodes.size()<<"\n";
  for(int q:{2,3,4,5,6,8}){
   const auto start=std::chrono::steady_clock::now();
   const auto quad=algoim::quadGen<3>(tet,cap_box,-1,-1,q);
   const double estimate=quad([&](const algoim::uvector<double,3>& p){
       return 1.+alpha*p(0);});
   const double error=std::abs(estimate-cap_reference)/cap_reference;
   const double elapsed=std::chrono::duration<double>(
       std::chrono::steady_clock::now()-start).count();
   const bool positive=std::all_of(quad.nodes.begin(),quad.nodes.end(),
       [](const auto& pt){return pt.w>0&&std::isfinite(pt.w);});
   if(!positive||!std::isfinite(error)||!(estimate>0)||
      (q==8&&error>1.e-8))
      throw std::runtime_error("P10PU curved Tet10 cap geometry QA");
   std::cout<<"P10PU_ALGOIM_CURVED_TET10_CAP q="<<q
       <<" integral="<<estimate<<" reference="<<cap_reference
       <<" relative_error="<<error<<" nodes="<<quad.nodes.size()
       <<" elapsed_s="<<elapsed<<" positive_weights=1\n";
  }
  std::cout<<"P10PU_ALGOIM_SINGLE_LEVELSET_SHELL_SOURCE_ONLY_PASS\n";
 }catch(const std::exception& e){std::cerr<<"P10PU_STOP "<<e.what()<<"\n";return 2;}
}
