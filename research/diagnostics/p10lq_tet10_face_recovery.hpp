#pragma once
#include <algorithm>
// P10LQ: source-only, no solver dependencies, weighted-volume-QP least squares.
// Recovered traces are NOT exact EDV face stresses. The caller must disclose
// the reconstruction order and its effect on measured interelement jumps.
#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace p10lq {

constexpr std::array<std::array<int,3>,4> tetra_faces{{
  {{1,2,3}},{{0,3,2}},{{0,1,3}},{{0,2,1}}
}};

inline std::array<double,4> barycentric(const std::array<double,10>& n){
 return {{n[0]+.5*(n[4]+n[6]+n[7]),
          n[1]+.5*(n[4]+n[5]+n[8]),
          n[2]+.5*(n[5]+n[6]+n[9]),
          n[3]+.5*(n[7]+n[8]+n[9])}};
}

inline std::array<double,10> quadratic(const std::array<double,4>& l){
 return {{l[0]*(2*l[0]-1),l[1]*(2*l[1]-1),
          l[2]*(2*l[2]-1),l[3]*(2*l[3]-1),
          4*l[0]*l[1],4*l[1]*l[2],4*l[2]*l[0],
          4*l[0]*l[3],4*l[1]*l[3],4*l[2]*l[3]}};
}

inline std::array<double,4> face_center(int face){
 if(face<0||face>3)throw std::invalid_argument("P10LQ invalid face id");
 std::array<double,4> l{};
 for(int vertex:tetra_faces[std::size_t(face)])l[std::size_t(vertex)]=1./3.;
 return l;
}

// Partial pivoting is deterministic, and a nearly singular Gram matrix is
// considered a hard failure, not a silent source of huge recovered jumps.
inline std::vector<double> solve(std::vector<std::vector<double>> a,
                                 std::vector<double> b){
 const std::size_t n=b.size();
 if(a.size()!=n)throw std::invalid_argument("P10LQ linear system size");
 double scale=0.;
 for(const auto& row:a){
  if(row.size()!=n)throw std::invalid_argument("P10LQ nonsquare Gram matrix");
  for(double x:row){
   if(!std::isfinite(x))throw std::invalid_argument("P10LQ nonfinite Gram");
   scale=std::max(scale,std::abs(x));
  }
 }
 if(!(scale>0.))throw std::runtime_error("P10LQ zero Gram matrix");
 for(std::size_t k=0;k<n;++k){
  std::size_t pivot=k;
  for(std::size_t i=k+1;i<n;++i)
   if(std::abs(a[i][k])>std::abs(a[pivot][k]))pivot=i;
  if(std::abs(a[pivot][k])<1.e-12*scale)
   throw std::runtime_error("P10LQ ill-conditioned Gram matrix");
  if(pivot!=k){std::swap(a[k],a[pivot]);std::swap(b[k],b[pivot]);}
  const double diag=a[k][k];
  for(std::size_t i=k+1;i<n;++i){
   const double m=a[i][k]/diag;
   for(std::size_t j=k+1;j<n;++j)a[i][j]-=m*a[k][j];
   b[i]-=m*b[k];a[i][k]=0.;
  }
 }
 std::vector<double> x(n);
 for(std::size_t t=0;t<n;++t){
  const std::size_t i=n-1-t;
  double v=b[i];
  for(std::size_t j=i+1;j<n;++j)v-=a[i][j]*x[j];
  x[i]=v/a[i][i];
 }
 return x;
}

struct Recovery {
 int degree=0;
 std::array<std::vector<double>,4> faces;
 double max_constant_error=0.;
};

// GaussQ is the pinned Stage3D07 struct with .N and reference .w.
// The weights are reference-volume weights, not physical QP volumes;
// this deliberately avoids giving a different projection to elements
// simply because their curved Jacobians differ.
template<class Quad>
Recovery prepare(const std::vector<Quad>& quad,int degree){
 if(degree!=1&&degree!=2)throw std::invalid_argument("P10LQ degree must be 1 or 2");
 if(quad.size()!=27)throw std::invalid_argument("P10LQ requires 27 Tet10 volume QPs");
 const std::size_t n=degree==1?4:10;
 std::vector<std::vector<double>> gram(n,std::vector<double>(n,0.));
 std::vector<std::array<double,10>> basis(quad.size());
 for(std::size_t q=0;q<quad.size();++q){
  basis[q]=degree==1?std::array<double,10>{}:quad[q].N;
  if(degree==1){
   const auto l=barycentric(quad[q].N);
   for(std::size_t i=0;i<4;++i)basis[q][i]=l[i];
  }
  if(!(quad[q].w>0.)||!std::isfinite(quad[q].w))
   throw std::invalid_argument("P10LQ invalid QP weight");
  for(std::size_t i=0;i<n;++i)
   for(std::size_t j=0;j<n;++j)
    gram[i][j]+=quad[q].w*basis[q][i]*basis[q][j];
 }
 Recovery r;r.degree=degree;
 for(int face=0;face<4;++face){
  const auto l=face_center(face);
  const auto v=quadratic(l);
  std::vector<double> rhs(n);
  for(std::size_t i=0;i<n;++i)rhs[i]=degree==1?l[i]:v[i];
  const auto x=solve(gram,rhs);
  r.faces[std::size_t(face)].resize(quad.size());
  double sum=0.;
  for(std::size_t q=0;q<quad.size();++q){
   double w=0.;
   for(std::size_t i=0;i<n;++i)w+=basis[q][i]*x[i];
   w*=quad[q].w;
   r.faces[std::size_t(face)][q]=w;sum+=w;
  }
  r.max_constant_error=std::max(r.max_constant_error,std::abs(sum-1.));
  if(std::abs(sum-1.)>1.e-9)
   throw std::runtime_error("P10LQ constant reproduction failure");
 }
 return r;
}

template<class Tensor>
Tensor recover(const Recovery& r,int face,const std::vector<Tensor>& values,
               std::size_t first_qp){
 if(face<0||face>3)throw std::invalid_argument("P10LQ face id");
 const auto& weights=r.faces[std::size_t(face)];
 if(first_qp+weights.size()>values.size())throw std::invalid_argument("P10LQ QP slice");
 Tensor answer{};
 for(std::size_t q=0;q<weights.size();++q)
  for(std::size_t k=0;k<answer.size();++k)
   answer[k]+=weights[q]*values[first_qp+q][k];
 return answer;
}

// [xx,yy,zz,xy,yz,zx]; traction jump is sigma_jump * common unit normal.
template<class Tensor>
double stress_jump_frobenius(const Tensor& a,const Tensor& b){
 double sum=0.;
 for(std::size_t k=0;k<6;++k){
  const double d=a[k]-b[k];sum+=(k<3?1.:2.)*d*d;
 }
 return std::sqrt(sum);
}
template<class Tensor>
double traction_jump(const Tensor& a,const Tensor& b,
                     const std::array<double,3>& n){
 const double xx=a[0]-b[0],yy=a[1]-b[1],zz=a[2]-b[2];
 const double xy=a[3]-b[3],yz=a[4]-b[4],zx=a[5]-b[5];
 const double x=xx*n[0]+xy*n[1]+zx*n[2];
 const double y=xy*n[0]+yy*n[1]+yz*n[2];
 const double z=zx*n[0]+yz*n[1]+zz*n[2];
 return std::sqrt(x*x+y*y+z*z);
}
} // namespace p10lq
