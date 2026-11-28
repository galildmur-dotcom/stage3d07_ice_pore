// P10PX real accepted M8 Tet10 geometry, read-only pilot with true Algoim.
// No Gmsh, no FEM/EDV, no mesh change. Local physical coordinates in metres.
// Input: deterministic sample nodes emitted by P10PX_M8_CONSERVATIVE_TET10_TRIAGE.py.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include "quadrature_multipoly.hpp"

using V=algoim::uvector<algoim::real,3>;
using Arr=algoim::xarray<algoim::real,3>;
using algoim::SparkStack;
static constexpr double pi=3.141592653589793238462643383279502884;
static constexpr double pore=.001,mu=.8,phi=pi/6;
static const V center{0.,0.,.03};
static constexpr std::array<std::array<int,2>,6> edges{{{{0,1}},{{0,2}},{{0,3}},
                                                        {{1,2}},{{1,3}},{{2,3}}}};
struct Tet10{
 int eid;
 std::string pole;
 std::array<int,6> certified_status; // radial lo/hi, hemisphere, cone, phi lo/hi
 std::array<V,10> X;
 struct Eval{V x;double det;};
 Eval at(const V& p)const{
  const std::array<double,4> L{1.-p(0)-p(1)-p(2),p(0),p(1),p(2)};
  const std::array<V,4> grad{V{-1,-1,-1},V{1,0,0},V{0,1,0},V{0,0,1}};
  V x{0,0,0},a{0,0,0},b{0,0,0},c{0,0,0};
  auto add=[&](int i,double w,const V& g){
    x+=X[i]*w;a+=X[i]*g(0);b+=X[i]*g(1);c+=X[i]*g(2);
  };
  for(int i=0;i<4;++i)add(i,L[i]*(2*L[i]-1),grad[i]*(4*L[i]-1));
  for(int i=0;i<6;++i){
    const int j=edges[i][0],k=edges[i][1];
    add(i+4,4*L[j]*L[k],(grad[j]*L[k]+grad[k]*L[j])*4.);
  }
  const V cross{b(1)*c(2)-b(2)*c(1),b(2)*c(0)-b(0)*c(2),b(0)*c(1)-b(1)*c(0)};
  const double det=a(0)*cross(0)+a(1)*cross(1)+a(2)*cross(2);
  return {x,det};
 }
};
static Tet10 read_one(const std::string& file,int index){
 std::ifstream f(file);if(!f)throw std::runtime_error("sample input missing");
 std::string marker;std::getline(f,marker);
 if(marker!="P10PX_M8_TET10_SAMPLE_V1")throw std::runtime_error("sample marker mismatch");
 int count;f>>count;
 if(index<0||index>=count)throw std::runtime_error("sample index out of range");
 Tet10 out{};
 for(int i=0;i<count;++i){
   int id;std::string pole;f>>id>>pole;
   std::array<int,6> status{};
   for(int& x:status)f>>x;
   std::array<V,10> x;
   for(int k=0;k<10;++k){double a,b,c;f>>a>>b>>c;x[k]=V{a,b,c};}
   if(!f)throw std::runtime_error("truncated sampled M8 Tet10");
   if(i==index){out.eid=id;out.pole=pole;out.X=x;out.certified_status=status;}
 }
 return out;
}
static double polynomial(int k,const V& u,const Tet10& t){
 if(k==6)return u(0)+u(1)+u(2)-1.;
 const V v=(t.at(u).x-center)*(1./pore);
 const double r2=v(0)*v(0)+v(1)*v(1)+v(2)*v(2);
 switch(k){
  case 0:return r2-1.5*1.5;             // radial outer, signed4D radial_bin=4
  case 1:return 1.25*1.25-r2;           // radial inner
  case 2:return mu*mu*r2-v(2)*v(2);    // polar cone
  case 3:return -v(1);                  // azimuth phi>=0
  case 4:return v(1)-std::tan(phi)*v(0);// azimuth phi<=30 degrees
  case 5:return (t.pole=="north"?-1.:1.)*v(2);
 }
 throw std::runtime_error("bad polynomial");
}
static double reference_tet_volume(const Tet10& t){
  // The detJ polynomial is degree <=3. Duffy 4x4x4 GL integrates it.
  const std::array<double,4> nodes{.0694318442029737,.3300094782075719,
                                    .6699905217924281,.9305681557970262};
  const std::array<double,4> weights{.1739274225687269,.3260725774312731,
                                      .3260725774312731,.1739274225687269};
  double total=0;
  for(int ia=0;ia<4;++ia)for(int ib=0;ib<4;++ib)for(int ic=0;ic<4;++ic){
    const double a=nodes[ia],b=nodes[ib],c=nodes[ic];
    const V u{a,(1-a)*b,(1-a)*(1-b)*c};
    const auto e=t.at(u);
    if(e.det<=0)throw std::runtime_error("bad detJ inside M8 Tet10");
    total+=weights[ia]*weights[ib]*weights[ic]*(1-a)*(1-a)*(1-b)*e.det;
  }
  return total;
}
int main(int argc,char** argv){
 try{
  if(argc<5)throw std::runtime_error("usage: worker SAMPLE index n_poly qmax");
  const auto sample=read_one(argv[1],std::atoi(argv[2]));
  const int mode=std::atoi(argv[3]),maxq=std::atoi(argv[4]);
  if(mode!=2&&mode!=3&&mode!=4&&mode!=7)
    throw std::runtime_error("only 2/3/4/7 active polynomial modes");
  if(maxq<2||maxq>8)throw std::runtime_error("qmax must be 2..8");
  const double exact=reference_tet_volume(sample);
  std::cout<<std::setprecision(16)
   <<"P10PX_M8_REAL_TET10_PREFLIGHT_PASS element="<<sample.eid
   <<" pole="<<sample.pole<<" mode="<<mode<<" reference_volume="<<exact<<std::endl;
  const algoim::uvector<int,3> e5{5,5,5},e3{3,3,3},e2{2,2,2};
  Arr p0(nullptr,e5),p1(nullptr,e5),p2(nullptr,e5),p3(nullptr,e3),
      p4(nullptr,e3),p5(nullptr,e3),p6(nullptr,e2);
  algoim_spark_alloc(algoim::real,p0,p1,p2,p3,p4,p5,p6);
  Arr* ps[]={&p0,&p1,&p2,&p3,&p4,&p5,&p6};
  const std::array<int,7> order{0,1,2,3,4,5,6};
  std::array<bool,7> active{};
  if(mode==2){active[0]=true;active[6]=true;}
  else if(mode==3){active[0]=true;active[1]=true;active[6]=true;}
  else if(mode==4){active[0]=true;active[1]=true;active[2]=true;active[6]=true;}
  else active.fill(true);
  // Skip surfaces certified *fully inside* the selected 4D bin over the
  // entire exact quadratic Tet10 using Bezier convex-hull interval bounds.
  constexpr std::array<int,7> poly_to_status{1,0,3,4,5,2,-1};
  int kept=0,skipped=0;
  for(int i=0;i<7;++i){
    if(!active[i])continue;
    const int j=poly_to_status[i];
    if(j<0){++kept;continue;}
    if(sample.certified_status[j]==-1)throw std::runtime_error("certified-outside selected Tet10");
    if(sample.certified_status[j]==1){active[i]=false;++skipped;}
    else ++kept;
  }
  std::cout<<"P10PX_M8_CERTIFIED_ACTIVE_POLYNOMIALS element="<<sample.eid
    <<" requested="<<mode<<" retained="<<kept<<" skipped="<<skipped<<std::endl;
  // Upstream multipoly currently suffers resultant degree explosion for
  // combinations of two genuine quartic cuts on real curved Tet10.
  // Refuse that expensive mode before constructing polynomial matrices.
  const int quartic_count=int(active[0])+int(active[1])+int(active[2]);
  if(quartic_count>=2){
    std::cout<<"P10PX_M8_UNSUPPORTED_MULTIPLE_QUARTIC_CUTS element="<<sample.eid
      <<" quartic_active="<<quartic_count
      <<" requires_piecewise_or_hierarchical_method=1"<<std::endl;
    return 3;
  }
  for(int i:order){if(!active[i])continue;
    algoim::bernstein::bernsteinInterpolate<3>(
      [i,&sample](const V& x){return polynomial(i,x,sample);},*ps[i]);
    for(const V x:{V{.11,.2,.3},V{.2,.3,.1}}){
      const double a=algoim::bernstein::evalBernsteinPoly<3>(*ps[i],x);
      const double b=polynomial(i,x,sample);
      if(std::abs(a-b)>2e-9)throw std::runtime_error("true quartic mismatch");
    }
  }
  std::cout<<"P10PX_M8_BERNSTEIN_PARITY_PASS element="<<sample.eid<<std::endl;
  algoim::ImplicitPolyQuadrature<3> quad;
  for(int i:order){if(!active[i])continue;
    auto mask=algoim::detail::nonzeroMask(
       *ps[i],algoim::booluarray<3,ALGOIM_M>(true));
    if(!algoim::detail::maskEmpty(mask))quad.phi.push_back(*ps[i],mask);
  }
  std::cout<<"P10PX_M8_BUILD_BEGIN element="<<sample.eid<<" mode="<<mode<<std::endl;
  quad.build(true,false);
  std::cout<<"P10PX_M8_BUILD_DONE element="<<sample.eid<<" mode="<<mode<<std::endl;
  for(int q:{2,3,4,6,8}){
    if(q>maxq)continue;
    double cut=0,tet=0,positive_tet_weight_min=1e100;
    std::size_t points=0,cutpoints=0;
    quad.integrate(algoim::AutoMixed,q,[&](const V& u,algoim::real weight){
      ++points;
      const auto geo=sample.at(u);
      if(u(0)+u(1)+u(2)<=1.){
        if(geo.det<=0)throw std::runtime_error("nonpositive M8 tet detJ");
        positive_tet_weight_min=std::min(positive_tet_weight_min,weight*geo.det);
        tet+=weight*geo.det;
      }
      bool keep=true;
      for(int i:order)if(active[i]&&polynomial(i,u,sample)>0.){keep=false;break;}
      if(keep){cut+=weight*geo.det;++cutpoints;}
    });
    const double rel=std::abs(tet-exact)/exact;
    if(!(cut>=0&&cut<=1.05*exact&&positive_tet_weight_min>0)&&points)
      throw std::runtime_error("invalid cut volume / weight");
    if(!std::isfinite(rel))throw std::runtime_error("nonfinite tetra volume");
    std::cout<<"P10PX_M8_ALGOIM element="<<sample.eid<<" pole="<<sample.pole
     <<" mode="<<mode<<" q="<<q<<" tet_rel="<<rel
     <<" cut_volume="<<cut<<" cut_frac="<<cut/exact
     <<" points="<<points<<" active="<<cutpoints<<std::endl;
  }
  std::cout<<"P10PX_M8_ALGOIM_SOURCE_ONLY_PASS"<<std::endl;
 }catch(const std::exception& e){std::cerr<<"P10PX_STOP "<<e.what()<<std::endl;return 2;}
}
