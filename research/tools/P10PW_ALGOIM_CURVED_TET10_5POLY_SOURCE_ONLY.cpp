// Stage3D07 P10PW: TRUE Algoim multipoly on a reference tetrahedron and
// a genuinely quadratic 10-node isoparametric map, geometry only.
// NO Gmsh, NO mesh mutation, NO transient FEM, NO adjoint, NO EDV.
// Requires upstream Algoim + Reference-LAPACKE. With C++20 apply P10PV patch.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

#include "quadrature_multipoly.hpp"

using V=algoim::uvector<algoim::real,3>;
using Arr=algoim::xarray<algoim::real,3>;
using algoim::SparkStack;
static constexpr double pi=3.141592653589793238462643383279502884;
static constexpr double ro=.35,ri=ro*(.08/.22),mu0=.8,phi=pi/3.;

static V exact_map(const V& p,double alpha){
 return V{p(0),p(1),p(2)*(1.+alpha*p(0))};
}
static V midpoint(const V& a,const V& b){return (a+b)*.5;}

struct Tet10{
 double alpha;
 std::array<V,10> nodes;
 explicit Tet10(double a):alpha(a){
  const std::array<V,4> t{V{0,0,0},V{1,0,0},V{0,1,0},V{0,0,1}};
  const std::array<std::array<int,2>,6> edges{{{{0,1}},{{0,2}},{{0,3}},
                                             {{1,2}},{{1,3}},{{2,3}}}};
  for(int i=0;i<4;++i)nodes[i]=exact_map(t[i],alpha);
  for(int i=0;i<6;++i)
   nodes[i+4]=exact_map(midpoint(t[edges[i][0]],t[edges[i][1]]),alpha);
 }
 struct Eval{V x;double det;};
 Eval at(const V& p)const{
  const double u=p(0),v=p(1),w=p(2);
  const std::array<double,4> l{1.-u-v-w,u,v,w};
  const std::array<V,4> grad{V{-1,-1,-1},V{1,0,0},V{0,1,0},V{0,0,1}};
  const std::array<std::array<int,2>,6> edges{{{{0,1}},{{0,2}},{{0,3}},
                                             {{1,2}},{{1,3}},{{2,3}}}};
  V x{0,0,0};
  double J[3][3]{};
  auto accumulate=[&](int n,double N,const V& dN){
   x+=nodes[n]*N;
   for(int i=0;i<3;++i)for(int j=0;j<3;++j)
      J[i][j]+=nodes[n](i)*dN(j);
  };
  for(int i=0;i<4;++i){
   accumulate(i,l[i]*(2*l[i]-1),grad[i]*(4*l[i]-1));
  }
  for(int i=0;i<6;++i){
   const int a=edges[i][0],b=edges[i][1];
   accumulate(i+4,4*l[a]*l[b],
              (grad[a]*l[b]+grad[b]*l[a])*4.);
  }
  const double det=J[0][0]*(J[1][1]*J[2][2]-J[1][2]*J[2][1])
                  -J[0][1]*(J[1][0]*J[2][2]-J[1][2]*J[2][0])
                  +J[0][2]*(J[1][0]*J[2][1]-J[1][1]*J[2][0]);
  return {x,det};
 }
 void self_check()const{
  for(const V p:{V{.1,.2,.3},V{.14,.1,.4},V{.23,.3,.11},V{.8,.1,.1}}){
   const auto e=at(p);
   const V target=exact_map(p,alpha);
   for(int j=0;j<3;++j)if(std::abs(e.x(j)-target(j))>1e-13)
      throw std::runtime_error("Tet10 mapped position fails analytic parity");
   if(std::abs(e.det-(1.+alpha*p(0)))>1e-13||e.det<=0.)
      throw std::runtime_error("Tet10 Jacobian fails analytic parity");
  }
 }
};

static double poly(int k,const V& p,const Tet10& map){
 if(k==4)return p(0)+p(1)+p(2)-1.;  // Reference simplex constraint
 const V x=map.at(p).x;
 const double rr=x(0)*x(0)+x(1)*x(1)+x(2)*x(2);
 switch(k){
  case 0:return rr-ro*ro;
  case 1:return mu0*mu0*rr-x(2)*x(2);
  case 2:return x(1)-std::tan(phi)*x(0);
  case 3:return ri*ri-rr;
 }
 throw std::runtime_error("bad polynomial index");
}
static bool inside(const V& p,const Tet10& map){
 for(int i=0;i<5;++i)if(poly(i,p,map)>0.)return false;
 return true;
}
static double reference_sector(){
 return (ro*ro*ro-ri*ri*ri)/3.*(1-mu0)*phi;
}

int main(int argc,char** argv){
 try{
  const double alpha=(argc>1&&std::string(argv[1])=="curved")?.3:0.;
  const int qmax=argc>2?std::atoi(argv[2]):6;
  if(qmax<2||qmax>12)throw std::runtime_error("qmax must be in 2..12");
  const Tet10 map(alpha);
  map.self_check();
  std::cout<<std::setprecision(15)
    <<"P10PW_PREFLIGHT_TET10_PARITY_PASS alpha="<<alpha
    <<" qmax="<<qmax<<std::endl;
  // Exact bound: for all x in spherical sector, u+v+w <= sqrt(3)*ro < 1,
  // since w=z/(1+alpha*x) <= z. Thus the sector lies INSIDE the tetra.
  if(std::sqrt(3.)*ro>=1.)throw std::runtime_error("sector outside simplex");

  // Although z^2 has total degree 4 (u^2*w^2), the degree in EACH
  // reference coordinate is only 2: tensor-product Bernstein (3,3,3).
  // A careless (5,5,5) over-embedding triggers huge resultant degrees.
  const algoim::uvector<int,3> extent{3,3,3};
  Arr p0(nullptr,extent),p1(nullptr,extent),p2(nullptr,extent),
      p3(nullptr,extent),p4(nullptr,extent);
  algoim_spark_alloc(algoim::real,p0,p1,p2,p3,p4);
  Arr* polys[]={&p0,&p1,&p2,&p3,&p4};
  for(int i=0;i<5;++i){
   std::cout<<"P10PW_BERNSTEIN_BEGIN k="<<i
      <<" P0="<<polys[i]->ext(0)<<" P1="<<polys[i]->ext(1)
      <<" P2="<<polys[i]->ext(2)<<std::endl;
   algoim::bernstein::bernsteinInterpolate<3>(
     [&map,i](const V& p){return poly(i,p,map);},*polys[i]);
   std::cout<<"P10PW_BERNSTEIN_DONE k="<<i<<std::endl;
  }
  // Degree-4 interpolation must reproduce all physical polynomials.
  for(const V p:{V{.17,.22,.35},V{.31,.16,.24},V{.5,.1,.04}})
   for(int i=0;i<5;++i){
    const double fitted=algoim::bernstein::evalBernsteinPoly<3>(*polys[i],p);
    if(std::abs(fitted-poly(i,p,map))>2e-12)
       throw std::runtime_error("tensor-quadratic Bernstein representation mismatch");
   }

  const auto start=std::chrono::steady_clock::now();
  algoim::ImplicitPolyQuadrature<3> quad;
  for(int i=0;i<5;++i){
   auto mask=algoim::detail::nonzeroMask(
      *polys[i],algoim::booluarray<3,ALGOIM_M>(true));
   if(!algoim::detail::maskEmpty(mask))quad.phi.push_back(*polys[i],mask);
  }
  quad.build(true,false);
  std::cout<<"P10PW_BUILD_PASS elapsed_s="<<
     std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()
     <<std::endl;
  for(int q:{2,3,4,6,8,12}){
   if(q>qmax)continue;
   double sector=0,tetra=0,cube=0,minWeight=std::numeric_limits<double>::infinity();
   std::size_t nodes=0,sectorNodes=0,tetNodes=0;
   const auto began=std::chrono::steady_clock::now();
   quad.integrate(algoim::AutoMixed,q,[&](const V& p,algoim::real weight){
      ++nodes;
      minWeight=std::min(minWeight,double(weight));
      const auto mapped=map.at(p);
      if(!(mapped.det>0))throw std::runtime_error("nonpositive Tet10 Jacobian");
      cube+=weight*mapped.det;
      if(p(0)+p(1)+p(2)<=1.){tetra+=weight*mapped.det;++tetNodes;}
      if(inside(p,map)){sector+=weight*mapped.det;++sectorNodes;}
   });
   const double exactSector=reference_sector();
   const double errSector=std::abs(sector-exactSector)/exactSector;
   const double exactTet=1./6.+alpha/24.;
   const double errTet=std::abs(tetra-exactTet)/exactTet;
   const double exactCube=1.+alpha/2.;
   const double errCube=std::abs(cube-exactCube)/exactCube;
   if(minWeight<=0.||errCube>1e-7||!std::isfinite(errSector))
      throw std::runtime_error("nonpositive weight or loss of full cube closure");
   if(q==8&&alpha==0.&&errSector>1e-5)
      throw std::runtime_error("affine reference-tetra sector q8 threshold");
   if(q==12&&errTet>1e-6)
      throw std::runtime_error("curved Tet10 full tetra volume threshold");
   if(q==12&&alpha!=0.&&errSector>1e-6)
      throw std::runtime_error("curved Tet10 sector q12 threshold");
   std::cout<<"P10PW_TET10_MULTIPOLY alpha="<<alpha<<" q="<<q
     <<" sector="<<sector<<" sector_exact="<<exactSector
     <<" sector_rel="<<errSector
     <<" tetra="<<tetra<<" tetra_exact="<<exactTet<<" tetra_rel="<<errTet
     <<" cube_rel="<<errCube
     <<" nodes="<<nodes<<" tet_nodes="<<tetNodes
     <<" sector_nodes="<<sectorNodes<<" min_weight="<<minWeight
     <<" run_s="<<std::chrono::duration<double>(
                    std::chrono::steady_clock::now()-began).count()
     <<std::endl;
  }
  std::cout<<"P10PW_TRUE_FIVE_POLYNOMIAL_CURVED_TET10_SOURCE_ONLY_PASS"<<std::endl;
 }catch(const std::exception& e){
  std::cerr<<"P10PW_STOP "<<e.what()<<std::endl;return 2;
 }
}
