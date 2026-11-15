#pragma once
// Stage 3D-10E: transitional sparse bridge for the Tet10 global adjoint.
// Uses the EXISTING production BCSR container and local consistent tangent.
// Inclusion contract: mechanical.cpp with STAGE3D06_LIBRARY and then
// stage3d10c_tet10_global_adjoint.hpp must be included before this header.
//
// SpMV transpose is exact also for nonsymmetric matrices and mixed Dirichlet
// constraints. The cached reverse graph permits OpenMP-parallel gathering with
// no atomics, no data races, and no symmetry assumption on numerical blocks.
// The solver uses block-Jacobi-preconditioned BiCGStab for K and K^T.
#include <algorithm>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace ice3d::p10e {

struct ReverseGraph {
 int n=0;
 std::vector<int> reversed_position;
 explicit ReverseGraph(const BCSR& K):n(K.n){
  const auto& rows=K.rows();
  const auto& cols=K.cols();
  reversed_position.resize(cols.size());
  for(int i=0;i<n;++i)for(int p=rows[i];p<rows[i+1];++p){
   const int j=cols[p];
   const auto first=cols.begin()+rows[j],last=cols.begin()+rows[j+1];
   const auto it=std::lower_bound(first,last,i);
   if(it==last || *it!=i)
    throw std::invalid_argument("P10E: transpose graph requires symmetric pattern");
   reversed_position[p]=int(it-cols.begin());
  }
 }
};

inline BCSR assemble_tangent_bcsr(
 const Mesh& mesh,const p10c::Step& step,
 std::shared_ptr<const BCSRTopology> graph={}){
 BCSR K;
 if(graph)K.set_topology(std::move(graph));else K.init(mesh);
 if(mesh.tets.empty() || step.qps.size()%mesh.tets.size()!=0)
  throw std::invalid_argument("P10E: inconsistent element/quadrature count");
 const size_t nq=step.qps.size()/mesh.tets.size();
 for(size_t e=0;e<mesh.tets.size();++e){
  const auto& nodes=mesh.tets[e];
  std::array<std::array<double,9>,100> localK{};
  for(size_t qi=0;qi<nq;++qi){
   const auto& qp=step.qps[e*nq+qi];
   if(qp.nodes!=nodes)throw std::invalid_argument("P10E: changed element ordering");
   p10c::Tensor CB[30]{};
   for(int j=0;j<30;++j)for(int k=0;k<6;++k)
    for(int l=0;l<6;++l)
     CB[j][k]+=qp.law.response.tangent[k][l]*qp.B[j][l];
   for(int i=0;i<30;++i)for(int j=0;j<30;++j){
    auto& block=localK[10*(i/3)+(j/3)];
    block[3*(i%3)+(j%3)]+=
      qp.volume*edv::dot(qp.B[i],CB[j]);
   }
  }
  for(int i=0;i<10;++i)for(int j=0;j<10;++j){
   const int pos=K.topology ? K.topology->elementPositions[e][10*i+j]
                              : K.pos(nodes[i],nodes[j]);
   auto& dest=K.a[pos];const auto& local=localK[10*i+j];
   for(int c=0;c<9;++c)dest[c]+=local[c];
  }
 }
 return K;
}

inline void multiply_transpose(const BCSR& K,const std::vector<double>& x,
                               std::vector<double>& y,
                               const std::vector<uint8_t>& bc,
                               const ReverseGraph* reverse_graph=nullptr){
 const size_t ndof=3*size_t(K.n);
 if(x.size()!=ndof || bc.size()!=ndof)
  throw std::invalid_argument("P10E: transpose SpMV dimension mismatch");
 y.assign(ndof,0.);
 const auto& rows=K.rows();
 const auto& cols=K.cols();
 if(reverse_graph){
  if(reverse_graph->n!=K.n || reverse_graph->reversed_position.size()!=cols.size())
   throw std::invalid_argument("P10E: stale transpose graph");
  // Each destination row is owned by a single thread.  For numerical K(i,j),
  // output y(j) receives K(i,j)^T*x(i): reverse_position lets us gather it.
  #ifdef _OPENMP
  #pragma omp parallel for schedule(static) if(K.n>2000)
  #endif
  for(int j=0;j<K.n;++j){
   double sum[3]{};
   for(int p=rows[j];p<rows[j+1];++p){
    const int i=cols[p];
    const auto& a=K.a[reverse_graph->reversed_position[p]];
    for(int rr=0;rr<3;++rr){
     if(bc[3*j+rr])continue;
     for(int cc=0;cc<3;++cc)
      if(!bc[3*i+cc])sum[rr]+=a[3*cc+rr]*x[3*i+cc];
    }
   }
   for(int rr=0;rr<3;++rr){
    const int index=3*j+rr;
    y[index]=bc[index]?x[index]:sum[rr];
   }
  }
  return;
 }
 // Small reference implementation, independent of reverse-graph lookups.
 for(int i=0;i<K.n;++i){
  for(int p=rows[i];p<rows[i+1];++p){
   const int j=cols[p];
   const auto& a=K.a[p];
   for(int rr=0;rr<3;++rr){
    const int row=3*i+rr;
    if(bc[row])continue;
    for(int cc=0;cc<3;++cc){
     const int col=3*j+cc;
     if(!bc[col])y[col]+=a[3*rr+cc]*x[row];
    }
   }
  }
 }
 for(size_t k=0;k<ndof;++k)if(bc[k])y[k]=x[k];
}

inline void multiply(const BCSR& K,const std::vector<double>& x,
                     std::vector<double>& y,const std::vector<uint8_t>& bc,
                     bool transpose,const ReverseGraph* map=nullptr){
 if(transpose)multiply_transpose(K,x,y,bc,map);
 else K.mul_legacy(x,y,bc);
}
inline double product(const std::vector<double>& a,const std::vector<double>& b){
 if(a.size()!=b.size())throw std::invalid_argument("P10E: inner product size mismatch");
 double sum=0.;for(size_t i=0;i<a.size();++i)sum+=a[i]*b[i];return sum;
}
inline double norm(const std::vector<double>& a){return std::sqrt(product(a,a));}

struct IterativeResult{
 std::vector<double> x;
 int iterations=0;
 double relative_residual=0;
};

#ifdef STAGE3D10W_ANALYTIC_SHAPE
#include "stage3d10af_gmres_fallback.inc"
#include "stage3d10aj_projected_pcg_fallback.inc"
#endif

inline IterativeResult solve_bicgstab_core(BCSR& K,const std::vector<uint8_t>& bc,
                                     const std::vector<double>& rhs,
                                     bool transpose,
                                     double tolerance=2e-13,int maxiter=400,
                                     const ReverseGraph* map=nullptr){
 const size_t n=rhs.size();
 if(n!=3*size_t(K.n) || bc.size()!=n)
  throw std::invalid_argument("P10E: BiCGStab dimensions mismatch");
 IterativeResult result;
 result.x.assign(n,0.);
 const double base=norm(rhs);
 if(base==0)return result;
 K.build_preconditioner(bc); // Reuse existing 3x3 block Jacobi.
 std::vector<double> r=rhs,rhat=r,p(n,0.),v(n,0.),s(n),t;
 std::vector<double> phat,shat;
 double rho_old=1.,alpha=1.,omega=1.;
 double relative=1.;
 for(int iter=0;iter<maxiter;++iter){
  const double rho=product(rhat,r);
  if(std::abs(rho)<1e-80)throw std::runtime_error("P10E: BiCGStab rho breakdown");
  const double beta=(rho/rho_old)*(alpha/omega);
  for(size_t i=0;i<n;++i)p[i]=r[i]+beta*(p[i]-omega*v[i]);
  K.precond(p,phat,bc);
  multiply(K,phat,v,bc,transpose,map);
  const double rv=product(rhat,v);
  if(std::abs(rv)<1e-80)throw std::runtime_error("P10E: BiCGStab alpha breakdown");
  alpha=rho/rv;
  for(size_t i=0;i<n;++i)s[i]=r[i]-alpha*v[i];
  if(norm(s)/base<tolerance){
   for(size_t i=0;i<n;++i)result.x[i]+=alpha*phat[i];
   result.iterations=iter+1;
   break;
  }
  K.precond(s,shat,bc);
  multiply(K,shat,t,bc,transpose,map);
  const double tt=product(t,t);
  if(tt<1e-90)throw std::runtime_error("P10E: BiCGStab omega breakdown");
  omega=product(t,s)/tt;
  if(std::abs(omega)<1e-80)throw std::runtime_error("P10E: BiCGStab omega zero");
  for(size_t i=0;i<n;++i){
   result.x[i]+=alpha*phat[i]+omega*shat[i];
   r[i]=s[i]-omega*t[i];
  }
  result.iterations=iter+1;
  relative=norm(r)/base;
  if(relative<tolerance)break;
  rho_old=rho;
 }
 std::vector<double> Ax;
 multiply(K,result.x,Ax,bc,transpose,map);
 for(size_t i=0;i<n;++i)Ax[i]-=rhs[i];
 result.relative_residual=norm(Ax)/base;
#ifdef STAGE3D10W_ANALYTIC_SHAPE
 if(!std::isfinite(result.relative_residual))
  throw std::runtime_error("P10E: BiCGStab nonfinite verified residual");
 if(result.relative_residual>std::max(2e-11,5*tolerance))
  std::cout<<"P10AF_BICGSTAB_REJECTED iterations="<<result.iterations
           <<" requested_tolerance="<<tolerance
           <<" verified_relative_residual="<<result.relative_residual
           <<'\n'<<std::flush;
#endif
 if(result.relative_residual>std::max(2e-11,5*tolerance))
  throw std::runtime_error("P10E: BiCGStab failed verified residual");
 return result;
}


// Keep the original public API. In P10W only, the final unsuccessful
// BiCGStab retry falls back to a different Krylov method on the SAME system.
// No change is made to the constitutive law, the adjoint RHS or acceptance
// criteria. Non-P10W targets always use the original solver exclusively.
inline IterativeResult solve_bicgstab(BCSR& K,const std::vector<uint8_t>& bc,
                                      const std::vector<double>& rhs,
                                      bool transpose,
                                      double tolerance=2e-13,int maxiter=400,
                                      const ReverseGraph* map=nullptr){
#ifdef STAGE3D10W_ANALYTIC_SHAPE
 try{
  return solve_bicgstab_core(K,bc,rhs,transpose,tolerance,maxiter,map);
 }catch(const std::runtime_error& e){
  // The existing P10P caller tries 1e-11/2400, 2e-10/3600,
  // and 1e-9/5000. Only the THIRD failure activates the fallback.
  if(!(tolerance>=1e-9 && maxiter>=5000) ||
     std::string(e.what()).rfind("P10E: BiCGStab",0)!=0)throw;
  std::cout<<"P10AJ_PROJECTED_PCG_FALLBACK after=BiCGStab_retries"
           <<" maxiter=2000 projected_tolerance=2e-10\n"<<std::flush;
  const auto answer=solve_projected_pcg_fallback(K,bc,rhs,transpose,map,
                                                 2e-10,2000);
  std::cout<<"P10AJ_PROJECTED_PCG_SOLVED iterations="<<answer.iterations
           <<" verified_relative_residual="<<answer.relative_residual
           <<'\n'<<std::flush;
  return answer;
 }
#else
 return solve_bicgstab_core(K,bc,rhs,transpose,tolerance,maxiter,map);
#endif
}

} // namespace ice3d::p10e
