// P10PT — geometric-only cut-cell pilot for a reference Tet10 element.
// Literature-inspired adaptive subdivision; no FEM/Gmsh/physical state.
// IMPORTANT: this is a bounded synthetic feasibility test, NOT production
// cut-cell quadrature. Production requires a higher-order curved interface
// reconstruction and positive-weight mapping across intersected Tet10.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

using V=std::array<double,3>;
using T=std::array<V,4>;

static constexpr double pi=3.141592653589793238462643383279502884;
static V add(V a,V b){return {a[0]+b[0],a[1]+b[1],a[2]+b[2]};}
static V sub(V a,V b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
static V mul(V a,double v){return {a[0]*v,a[1]*v,a[2]*v};}
static double dot(V a,V b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static double norm2(V a){return dot(a,a);}
static V cross(V a,V b){return {a[1]*b[2]-a[2]*b[1],
 a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
static double vol(const T& t){return std::abs(dot(sub(t[1],t[0]),
  cross(sub(t[2],t[0]),sub(t[3],t[0]))))/6.;}

// Exact quadratic Tet10 shape interpolation of the volume-preserving curved
// map x=u, y=v, z=w+alpha*u*v, det(dx/du)=1 identically.
static V curved_exact(V uvw,double alpha){
 return {uvw[0],uvw[1],uvw[2]+alpha*uvw[0]*uvw[1]};
}
static V tet10_interpolation(V uvw,double alpha,bool perturb=false){
 const std::array<V,4> ref{V{0,0,0},V{1,0,0},V{0,1,0},V{0,0,1}};
 const std::array<std::array<int,2>,6> edges{{{{0,1}},{{0,2}},{{0,3}},
   {{1,2}},{{1,3}},{{2,3}}}};
 std::array<V,10> nodes{};
 for(int k=0;k<4;++k)nodes[k]=curved_exact(ref[k],alpha);
 for(int k=0;k<6;++k){const auto& e=edges[k];
  nodes[k+4]=curved_exact(mul(add(ref[e[0]],ref[e[1]]),.5),alpha);}
 if(perturb)nodes[7][2]+=.001;
 const std::array<double,4> l{1.-uvw[0]-uvw[1]-uvw[2],
                                   uvw[0],uvw[1],uvw[2]};
 V value{0,0,0};
 for(int i=0;i<4;++i)value=add(value,mul(nodes[i],l[i]*(2*l[i]-1)));
 for(int k=0;k<6;++k){const auto& e=edges[k];
  value=add(value,mul(nodes[k+4],4*l[e[0]]*l[e[1]]));}
 return value;
}

enum class Mode{Plane,PolarSector};
struct Region{
 Mode mode;
 double plane=0.28;
 double r0=0.08,r1=0.22,mu0=0.8,phi1=pi/3;
 bool contains(V q)const{
  if(mode==Mode::Plane)return q[0]<plane;
  const double rr=std::sqrt(norm2(q));
  return rr>=r0&&rr<=r1&&q[2]>=mu0*rr&&q[1]<=std::tan(phi1)*q[0];
 }
 double reference()const{
  if(mode==Mode::Plane)return (1.-std::pow(1.-plane,3))/6.;
  // Sphere sector contained in reference tetra: r1*sqrt(3)<1.
  return (std::pow(r1,3)-std::pow(r0,3))/3.*(1.-mu0)*phi1;
 }
};
enum class Position{Outside,Inside,Crossing};

static Position classify(const T& t,const Region& r){
 if(r.mode==Mode::Plane){
  double lo=t[0][0],hi=lo;
  for(const auto& x:t){lo=std::min(lo,x[0]);hi=std::max(hi,x[0]);}
  if(lo>=r.plane)return Position::Outside;
  if(hi<=r.plane)return Position::Inside;
  return Position::Crossing;
 }
 // Certified-conservative axis-aligned bounds for the affine synthetic
 // geometry. These bounds CANNOT be used unchanged on a curved Tet10 map.
 V lo=t[0],hi=t[0];
 for(const auto& x:t)for(int j=0;j<3;++j){
  lo[j]=std::min(lo[j],x[j]);hi[j]=std::max(hi[j],x[j]);}
 if(lo[0]<0||lo[1]<0||lo[2]<0)
  throw std::runtime_error("P10PT invalid octant synthetic geometry");
 const double radial_min=std::sqrt(norm2(lo));
 const double radial_max=std::sqrt(norm2(hi));
 if(radial_max<=r.r0||radial_min>=r.r1)return Position::Outside;
 const double tang=std::tan(r.phi1);
 double phi_lo=std::numeric_limits<double>::infinity();
 double phi_hi=-phi_lo;
 for(const auto& x:t){const double g=x[1]-tang*x[0];
  phi_lo=std::min(phi_lo,g);phi_hi=std::max(phi_hi,g);}
 if(phi_lo>=0)return Position::Outside;
 const double k=r.mu0/std::sqrt(1.-r.mu0*r.mu0);
 const double rho_min=std::hypot(lo[0],lo[1]);
 const double rho_max=std::hypot(hi[0],hi[1]);
 if(hi[2]<=k*rho_min)return Position::Outside;
 if(radial_min>=r.r0&&radial_max<=r.r1&&phi_hi<=0&&
    lo[2]>=k*rho_max)return Position::Inside;
 return Position::Crossing;
}

static double cut_point_fraction(const T& t,const Region& r){
 // Symmetric positive degree-two tetrahedral quadrature; all weights 1/4.
 constexpr double a=0.5854101966249685,b=0.1381966011250105;
 double n=0;
 for(int i=0;i<4;++i){V q{0,0,0};
  for(int j=0;j<4;++j)q=add(q,mul(t[j],i==j?a:b));
  n+=r.contains(q)?0.25:0.;
 }
 return n;
}

struct Run{double inside=0,outside=0;std::uint64_t visited=0,leaves=0,
 cut_leaves=0,fully_classified=0;};
static void integrate(const T& t,const Region& r,int remaining,Run& out){
 ++out.visited;
 const double volume=vol(t);
 const auto status=classify(t,r);
 if(status==Position::Inside){out.inside+=volume;++out.leaves;
  ++out.fully_classified;return;}
 if(status==Position::Outside){out.outside+=volume;++out.leaves;
  ++out.fully_classified;return;}
 if(!remaining){const double frac=cut_point_fraction(t,r);
  out.inside+=volume*frac;out.outside+=volume*(1-frac);
  ++out.leaves;++out.cut_leaves;return;}
 int ia=0,ib=1;double best=-1;
 for(int i=0;i<4;++i)for(int j=i+1;j<4;++j){
  const double d=norm2(sub(t[i],t[j]));
  if(d>best){best=d;ia=i;ib=j;}}
 const V mid=mul(add(t[ia],t[ib]),.5);
 T left=t,right=t;
 left[ia]=mid;
 right[ib]=mid;
 integrate(left,r,remaining-1,out);
 integrate(right,r,remaining-1,out);
}

static void check(bool good,const std::string& what){
 if(!good)throw std::runtime_error("P10PT_STOP "+what);
}
int main(){
 try{
  const T tet{V{0,0,0},V{1,0,0},V{0,1,0},V{0,0,1}};
  check(std::abs(vol(tet)-1./6.)<1.e-15,"reference volume");
  for(const V p:{V{.2,.3,.1},V{.1,.7,.05},V{.4,.1,.2}}){
   check(std::sqrt(norm2(sub(tet10_interpolation(p,.5),
                        curved_exact(p,.5))))<1.e-14,"Tet10 quadratic map");
  }
  // Negative test: a deliberately corrupted edge node must be detected.
  const V test{.2,.3,.1};
  check(std::sqrt(norm2(sub(tet10_interpolation(test,.5,true),
                  curved_exact(test,.5))))>1.e-5,"corrupt midpoint rejection");
  std::cout<<std::setprecision(15);
  for(const auto mode:{Mode::Plane,Mode::PolarSector}){
   const Region r{mode};
   const char* label=mode==Mode::Plane?"CURVED_TET10_PLANE":"AFFINE_TET_POLAR_SECTOR";
   double previous=std::numeric_limits<double>::infinity();
   for(const int depth:{0,8,12,16,20,24}){
    Run out;
    integrate(tet,r,depth,out);
    const double exact=r.reference();
    const double error=std::abs(out.inside-exact)/exact;
    check(std::abs(out.inside+out.outside-1./6.)<1.e-10,
          "conservative complementary partition");
    check(out.inside>=0&&out.outside>=0&&
          std::isfinite(error),"nonnegative finite partition");
    std::cout<<"P10PT_MEASURE "<<label<<" depth="<<depth
      <<" estimate="<<out.inside<<" reference="<<exact
      <<" relative_error="<<error<<" visited="<<out.visited
      <<" cut_leaves="<<out.cut_leaves<<"\n";
    if(depth==24){
      const double tolerance=mode==Mode::Plane?5.e-4:1.e-2;
      check(error<tolerance,"final cut-cell accuracy threshold");
      check(error<previous,"refinement improvement");
    }
    previous=error;
   }
  }
  std::cout<<"P10PT_SOURCE_ONLY_SYNTHETIC_GEOMETRY_PASS\n";
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 2;}
}
