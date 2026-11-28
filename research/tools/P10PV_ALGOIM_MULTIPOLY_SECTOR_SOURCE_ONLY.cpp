// Stage3D07 P10PV: TRUE upstream Algoim multi-polynomial geometric pilot.
// Geometry-only; NO MESH GENERATION, NO FEM, NO EDV/adjoint evaluation.
// Depends on upstream Algoim quadrature_multipoly.hpp + Reference-LAPACKE.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>

#include "quadrature_multipoly.hpp"

using algoim::real;
using algoim::SparkStack;
using V=algoim::uvector<real,3>;
using Arr=algoim::xarray<real,3>;

static constexpr double pi=3.141592653589793238462643383279502884;
static constexpr double r0=0.08,r1=0.22,mu0=0.8,phi1=pi/3.;

static bool inside(int n,const V& v){
 const double r2=v(0)*v(0)+v(1)*v(1)+v(2)*v(2);
 if(r2>1.)return false;                       // Outer sphere
 if(n>=2&&v(2)*v(2)<mu0*mu0*r2)return false; // Cone; z>=0 in box
 if(n>=3&&v(1)>std::tan(phi1)*v(0))return false; // Phi half-plane
 if(n>=4&&r2<(r0/r1)*(r0/r1))return false;   // Inner sphere
 return true;
}

static double reference(int n){
 const double rr=n==4?(r1*r1*r1-r0*r0*r0):r1*r1*r1;
 // Box first octant: for whole sphere, angle = 4pi/8 = pi/2.
 const double solid=n==1?pi/2:(n==2?(1-mu0)*pi/2:
                                                  (1-mu0)*phi1);
 return rr*solid/3.;
}

static double polynomial(int k,const V& x){
 const double r2=x(0)*x(0)+x(1)*x(1)+x(2)*x(2);
 switch(k){
  case 0:return r2-1.;
  case 1:return mu0*mu0*r2-x(2)*x(2);
  case 2:return x(1)-std::tan(phi1)*x(0);
  case 3:return (r0/r1)*(r0/r1)-r2;
 }
 throw std::runtime_error("invalid polynomial");
}

int main(int argc,char** argv){
 try{
  int limit=argc>1?std::atoi(argv[1]):4;
  if(limit<1||limit>4)throw std::runtime_error("max polynomial count 1..4");
  std::cout<<std::setprecision(15);
  const algoim::uvector<int,3> extent{3,3,3};
  Arr p0(nullptr,extent),p1(nullptr,extent),p2(nullptr,extent),p3(nullptr,extent);
  algoim_spark_alloc(real,p0,p1,p2,p3);
  Arr* polys[]={&p0,&p1,&p2,&p3};
  for(int i=0;i<4;++i){
   algoim::bernstein::bernsteinInterpolate<3>(
      [i](const V& x){return polynomial(i,x);},*polys[i]);
  }
  for(int n=1;n<=limit;++n){
   std::cout<<"P10PV_BUILD_BEGIN n_poly="<<n<<std::endl;
   auto started=std::chrono::steady_clock::now();
   algoim::ImplicitPolyQuadrature<3> quad;
   for(int i=0;i<n;++i){
      auto mask=algoim::detail::nonzeroMask(
         *polys[i],algoim::booluarray<3,ALGOIM_M>(true));
      if(!algoim::detail::maskEmpty(mask))quad.phi.push_back(*polys[i],mask);
   }
   quad.build(true,false);
   const double build_s=std::chrono::duration<double>(
           std::chrono::steady_clock::now()-started).count();
   std::cout<<"P10PV_BUILD_END n_poly="<<n<<" time_s="<<build_s<<std::endl;
   for(int q:{2,3,4,6,8,12}){
     auto t=std::chrono::steady_clock::now();
     double volume=0,total=0,minweight=1e100;
     std::size_t nodes=0,active=0;
     quad.integrate(algoim::AutoMixed,q,[&](const V& x,real w){
       ++nodes;
       total+=w;
       minweight=std::min(minweight,double(w));
       if(inside(n,x)){++active;volume+=w;}
     });
     volume*=r1*r1*r1;
     total*=r1*r1*r1;
     const double exact=reference(n);
     const double error=std::abs(volume-exact)/exact;
     const double wall_s=std::chrono::duration<double>(
              std::chrono::steady_clock::now()-t).count();
     if(!(minweight>0)||!std::isfinite(error))
       throw std::runtime_error("nonpositive multipoly weight or nonfinite error");
     if(std::abs(total-r1*r1*r1)>1e-7*r1*r1*r1)
       throw std::runtime_error("global cube quadrature not conservative");
     std::cout<<"P10PV_MULTIPOLY n_poly="<<n<<" q="<<q
       <<" volume="<<volume<<" exact="<<exact
       <<" relative_error="<<error<<" nodes="<<nodes
       <<" active="<<active<<" min_weight="<<minweight
       <<" run_s="<<wall_s<<std::endl;
     if(q==4&&error>0.02)
       throw std::runtime_error("not converged for synthetic sector");
   }
  }
  std::cout<<"P10PV_TRUE_MULTIPOLY_SOURCE_ONLY_PASS"<<std::endl;
 }catch(const std::exception& e){
  std::cerr<<"P10PV_STOP "<<e.what()<<std::endl;return 2;
 }
}
