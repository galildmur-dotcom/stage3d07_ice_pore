#pragma once
// Stage3D06-P4: zero-fill block IC(0), 3x3 nodal blocks.
// M=(I+L)D(I+L)^T, with SPD 3x3 diagonal D and strictly lower L.
// Symmetric Dirichlet elimination is applied only to the factorization input:
// frozen DOF rows/columns are zeroed and their diagonal entries set to 1.
// Not thread-parallel: triangular dependencies are intrinsically sequential.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace stage3d06::p4 {
using B3=std::array<double,9>;
inline B3 mul(const B3&A,const B3&B){B3 C{};
 for(int i=0;i<3;++i)for(int k=0;k<3;++k)for(int j=0;j<3;++j) C[3*i+j]+=A[3*i+k]*B[3*k+j]; return C;}
inline B3 mult_t(const B3&A,const B3&B){B3 C{};
 for(int i=0;i<3;++i)for(int k=0;k<3;++k)for(int j=0;j<3;++j) C[3*i+j]+=A[3*i+k]*B[3*j+k]; return C;}
inline void minus_product(B3&dst,const B3&A,const B3&B){auto C=mul(A,B);for(int k=0;k<9;++k)dst[k]-=C[k];}
inline void minus_product_t(B3&dst,const B3&A,const B3&B){auto C=mult_t(A,B);for(int k=0;k<9;++k)dst[k]-=C[k];}
inline void symmetrize(B3&b){for(int i=0;i<3;++i)for(int j=i+1;j<3;++j){double x=.5*(b[3*i+j]+b[3*j+i]);b[3*i+j]=b[3*j+i]=x;}}
// Inverse of symmetric-positive-definite block using Cholesky; FAIL LOUDLY on breakdown.
inline B3 invert_spd(const B3&D,int node){
 double c[3][3]{};
 for(int i=0;i<3;++i)for(int j=0;j<=i;++j){
  double v=D[3*i+j];for(int k=0;k<j;++k)v-=c[i][k]*c[j][k];
  if(i==j){if(!(v>0.0) || !std::isfinite(v))
    throw std::runtime_error("P4 IC0 non-SPD pivot at node "+std::to_string(node)+", component "+std::to_string(i));c[i][j]=std::sqrt(v);}
  else c[i][j]=v/c[j][j];
 }
 B3 inv{};
 for(int col=0;col<3;++col){double y[3]{},x[3]{};
  for(int i=0;i<3;++i){double rhs=(i==col)?1.:0.;for(int j=0;j<i;++j)rhs-=c[i][j]*y[j];y[i]=rhs/c[i][i];}
  for(int i=2;i>=0;--i){double rhs=y[i];for(int j=i+1;j<3;++j)rhs-=c[j][i]*x[j];x[i]=rhs/c[i][i];}
  for(int i=0;i<3;++i)inv[3*i+col]=x[i];
 }return inv;
}
struct BlockIC0 {
 int n=0;
 std::vector<int> row, col, lower_end, upper_row, upper_neighbor, upper_pos;
 std::vector<B3> lower, diagonal, inverse;
 mutable std::vector<double> scratch;
 long long intersections=0;
 void setup(int nodeCount,const std::vector<int>&r,const std::vector<int>&c,
            const std::vector<B3>&a,const std::vector<uint8_t>&bc){
  n=nodeCount;if(n<1 || (int)r.size()!=n+1 || r.back()!=(int)c.size() || c.size()!=a.size() || bc.size()!=size_t(3*n))
   throw std::runtime_error("P4 IC0 invalid BCSR inputs");
  row=r;col=c;lower.assign(c.size(),{});lower_end.resize(n);diagonal.resize(n);inverse.resize(n);intersections=0;
  // For lower triangular rows, lower[p] is L_ij (j<i), all other entries unused.
  for(int i=0;i<n;++i){
   int first=row[i],last=row[i+1];int d=first;
   while(d<last&&col[d]<i)++d;
   if(d==last||col[d]!=i)throw std::runtime_error("P4 IC0 missing diagonal block");
   lower_end[i]=d;
   B3 D=a[d];
   for(int rr=0;rr<3;++rr)for(int cc=0;cc<3;++cc)
    if(bc[3*i+rr]||bc[3*i+cc])D[3*rr+cc]=(rr==cc&&bc[3*i+rr])?1.:0.;
   for(int p=first;p<d;++p){
    const int j=col[p]; if(j<0||j>=i)throw std::runtime_error("P4 IC0 invalid column order");
    B3 C=a[p];
    for(int rr=0;rr<3;++rr)for(int cc=0;cc<3;++cc)
     if(bc[3*i+rr]||bc[3*j+cc])C[3*rr+cc]=0;
    int q=first, h=row[j];
    // Intersection of lower patterns of rows i and j, restricted to k<j.
    while(q<p&&h<lower_end[j]){
     if(col[q]==col[h]){
      auto t=mul(lower[q],diagonal[col[q]]);
      minus_product_t(C,t,lower[h]);++intersections;++q;++h;
     }else if(col[q]<col[h])++q;else ++h;
    }
    lower[p]=mul(C,inverse[j]);
    auto t=mul(lower[p],diagonal[j]);
    minus_product_t(D,t,lower[p]);
   }
   symmetrize(D);
   diagonal[i]=D;
   inverse[i]=invert_spd(D,i);
  }
  // Column adjacency for backward triangular solve: transposed lower factors.
  upper_row.assign(n+1,0);
  for(int i=0;i<n;++i)for(int p=row[i];p<lower_end[i];++p)++upper_row[col[p]+1];
  for(int i=0;i<n;++i)upper_row[i+1]+=upper_row[i];
  upper_neighbor.resize(upper_row[n]);upper_pos.resize(upper_row[n]);
  auto cursor=upper_row;
  for(int i=0;i<n;++i)for(int p=row[i];p<lower_end[i];++p){int dst=cursor[col[p]]++;upper_neighbor[dst]=i;upper_pos[dst]=p;}
  scratch.assign(3*n,0.);
 }
 void apply(const std::vector<double>&v,std::vector<double>&out,const std::vector<uint8_t>&bc)const{
  if(v.size()!=size_t(3*n)||bc.size()!=v.size())throw std::runtime_error("P4 IC0 vector dimension mismatch");
  if(scratch.size()!=v.size())scratch.resize(v.size());
  std::copy(v.begin(),v.end(),scratch.begin());
  // (I+L)y=b. Enforce zero at constrained DOFs, including mixed BC blocks.
  for(int i=0;i<n;++i){double* const yi=scratch.data()+3*i;
   for(int p=row[i];p<lower_end[i];++p){const double* const yj=scratch.data()+3*col[p];const B3&B=lower[p];
    for(int k=0;k<3;++k)yi[k]-=B[3*k]*yj[0]+B[3*k+1]*yj[1]+B[3*k+2]*yj[2];}
   for(int k=0;k<3;++k)if(bc[3*i+k])yi[k]=0.;
  }
  // D z=y; then (I+L)^T x=z, using transposed lower adjacency.
  out.assign(3*n,0.);
  for(int i=n-1;i>=0;--i){const B3&B=inverse[i];const double*yi=scratch.data()+3*i;double*xi=out.data()+3*i;
   for(int k=0;k<3;++k)xi[k]=B[3*k]*yi[0]+B[3*k+1]*yi[1]+B[3*k+2]*yi[2];
   for(int q=upper_row[i];q<upper_row[i+1];++q){int j=upper_neighbor[q];const B3&L=lower[upper_pos[q]];const double*xj=out.data()+3*j;
    for(int k=0;k<3;++k)xi[k]-=L[k]*xj[0]+L[3+k]*xj[1]+L[6+k]*xj[2];}
   for(int k=0;k<3;++k)if(bc[3*i+k])xi[k]=0.;
  }
 }
};
} // namespace stage3d06::p4
