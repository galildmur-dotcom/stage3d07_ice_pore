#pragma once
// Stage 3D-10L. Exact discrete reverse time adjoint of Stage3D02's backward
// Euler Tet10/Tri6 heat equation, including the analytic mesh-coordinate
// derivative of consistent mass, diffusion and top Robin terms.
// Include AFTER geometry_stage3d01.cpp is visible (types Mesh, V, g4, Surf).
// No thermal perturbed forward solves are used by adjoint_derivative().
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <stdexcept>
#include <vector>

namespace ice3d::p10l {
constexpr double rhocp=920.3*1960.;
constexpr double conductivity=2.40;
constexpr double robin=24.;

inline double ambient(double t,double xi=0.){
 return -3.*(-std::expm1(-t/300.))+.48*xi;
}

struct CSR {
 int n=0;
 std::vector<int> offsets,cols;
 std::vector<double> mass,conduct,mat,diag,robinload;
 static uint64_t pack(int i,int j){
  return (uint64_t(uint32_t(i))<<32)|uint32_t(j);
 }
 void pattern(const Mesh& mesh){
  n=int(mesh.nodes.size());
  std::vector<uint64_t> pairs;
  pairs.reserve(mesh.tets.size()*100+mesh.faces.size()*36/3);
  for(const auto& t:mesh.tets)for(const auto i:t)for(const auto j:t)
   pairs.push_back(pack(i,j));
  for(const auto& f:mesh.faces)if(f.tag==2)
   for(const auto i:f.nodes)for(const auto j:f.nodes)
    pairs.push_back(pack(i,j));
  std::sort(pairs.begin(),pairs.end());
  pairs.erase(std::unique(pairs.begin(),pairs.end()),pairs.end());
  offsets.assign(n+1,0);cols.reserve(pairs.size());
  for(const auto entry:pairs){
   ++offsets[int(entry>>32)+1];cols.push_back(int(entry&0xffffffffu));
  }
  for(int i=0;i<n;++i)offsets[i+1]+=offsets[i];
  mass.assign(pairs.size(),0.);conduct.assign(pairs.size(),0.);
  mat.assign(pairs.size(),0.);diag.assign(n,0.);
  robinload.assign(n,0.);
 }
 int index(int i,int j)const{
  auto lo=cols.begin()+offsets[i],hi=cols.begin()+offsets[i+1];
  auto it=std::lower_bound(lo,hi,j);
  if(it==hi||*it!=j)throw std::runtime_error("P10L missing CSR entry");
  return int(it-cols.begin());
 }
 void rebuild(double dt){
  for(size_t i=0;i<mat.size();++i)mat[i]=mass[i]+dt*conduct[i];
  for(int i=0;i<n;++i){
   diag[i]=mat[index(i,i)];
   if(!(diag[i]>0))throw std::runtime_error("P10L nonpositive diagonal");
  }
 }
 void mul(const std::vector<double>& a,const std::vector<double>& v,
          std::vector<double>& out)const{
  out.assign(n,0.);
  for(int i=0;i<n;++i){
   double sum=0;
   for(int p=offsets[i];p<offsets[i+1];++p)sum+=a[p]*v[cols[p]];
   out[i]=sum;
  }
 }
};

struct Q {
 double w;
 std::array<double,10> N;
 std::array<std::array<double,3>,10> d;
};
inline const std::vector<Q>& quadrature(){
 static const std::vector<Q> result=[](){
  std::vector<Q> q;q.reserve(64);
  for(auto a:g4)for(auto b:g4)for(auto c:g4){
   const double r=a.x,s=(1-r)*b.x,t=(1-r)*(1-b.x)*c.x;
   Q point{};tetshape(r,s,t,point.N,point.d);
   point.w=a.w*b.w*c.w*(1-r)*(1-r)*(1-b.x);
   q.push_back(point);
  }
  return q;
 }();
 return result;
}

inline std::array<double,6> face_shape(double r,double s){
 const double L[3]{1-r-s,r,s};
 std::array<double,6> N{};
 for(int i=0;i<3;++i)N[i]=L[i]*(2*L[i]-1);
 N[3]=4*L[0]*L[1];N[4]=4*L[1]*L[2];N[5]=4*L[2]*L[0];
 return N;
}

struct Operator {
 CSR primal,shape;
 double max_ones_error=0,max_directional_ones_error=0;
 double max_jacobian_rel=0;
};

inline Operator assemble(const Mesh& mesh,const std::vector<V>& velocity,double dt){
 if(velocity.size()!=mesh.nodes.size())
  throw std::invalid_argument("P10L: geometry velocity has wrong size");
 Operator out;
 out.primal.pattern(mesh);
 out.shape.pattern(mesh);
 const auto& Qs=quadrature();
 for(const auto& tet:mesh.tets){
  double me[10][10]{},ke[10][10]{},dme[10][10]{},dke[10][10]{};
  for(const auto& q:Qs){
   V dr{},ds{},dv{},drp{},dsp{},dvp{};
   for(int i=0;i<10;++i){
    const V x=mesh.nodes[tet[i]],v=velocity[tet[i]];
    dr=dr+x*q.d[i][0];ds=ds+x*q.d[i][1];dv=dv+x*q.d[i][2];
    drp=drp+v*q.d[i][0];dsp=dsp+v*q.d[i][1];dvp=dvp+v*q.d[i][2];
   }
   const V a=cross(ds,dv),b=cross(dv,dr),c=cross(dr,ds);
   const V da=cross(dsp,dv)+cross(ds,dvp);
   const V db=cross(dvp,dr)+cross(dv,drp);
   const V dc=cross(drp,ds)+cross(dr,dsp);
   const double det=dot(dr,a),ddet=dot(drp,a)+dot(dr,da);
   if(!(det>0))throw std::runtime_error("P10L: nonpositive Jacobian");
   out.max_jacobian_rel=std::max(out.max_jacobian_rel,std::abs(ddet/det)*1e-6);
   const double w=q.w*det,dw=q.w*ddet;
   V grad[10],dgrad[10];
   for(int i=0;i<10;++i){
    const auto& d=q.d[i];
    grad[i]=(a*d[0]+b*d[1]+c*d[2])/det;
    dgrad[i]=(da*d[0]+db*d[1]+dc*d[2])/det-grad[i]*(ddet/det);
   }
   for(int i=0;i<10;++i)for(int j=0;j<10;++j){
    const double nij=q.N[i]*q.N[j],gj=dot(grad[i],grad[j]);
    me[i][j]+=rhocp*w*nij;
    dme[i][j]+=rhocp*dw*nij;
    ke[i][j]+=conductivity*w*gj;
    dke[i][j]+=conductivity*(dw*gj+w*(dot(dgrad[i],grad[j])+
                                             dot(grad[i],dgrad[j])));
   }
  }
  for(int i=0;i<10;++i)for(int j=0;j<10;++j){
   const int ix=out.primal.index(tet[i],tet[j]);
   out.primal.mass[ix]+=me[i][j];out.primal.conduct[ix]+=ke[i][j];
   out.shape.mass[ix]+=dme[i][j];out.shape.conduct[ix]+=dke[i][j];
  }
 }
 Mesh velocity_mesh=mesh;
 velocity_mesh.nodes=velocity;
 for(const auto& face:mesh.faces)if(face.tag==2){
  double re[6][6]{},dre[6][6]{},be[6]{},dbe[6]{};
  for(auto a:g4)for(auto b:g4){
   const double r=a.x,s=(1-r)*b.x;
   const auto x=seval(mesh,face.nodes,r,s);
   const auto v=seval(velocity_mesh,face.nodes,r,s);
   const V normal=cross(x.du,x.dv);
   const V dnormal=cross(v.du,x.dv)+cross(x.du,v.dv);
   const double size=norm(normal),area_w=a.w*b.w*(1-r)*size;
   if(!(size>0))throw std::runtime_error("P10L: zero top Tri6 area");
   const double darea_w=a.w*b.w*(1-r)*dot(normal,dnormal)/size;
   const auto N=face_shape(r,s);
   for(int i=0;i<6;++i){
    be[i]+=robin*area_w*N[i];dbe[i]+=robin*darea_w*N[i];
    for(int j=0;j<6;++j){
     re[i][j]+=robin*area_w*N[i]*N[j];
     dre[i][j]+=robin*darea_w*N[i]*N[j];
    }
   }
  }
  for(int i=0;i<6;++i){
   out.primal.robinload[face.nodes[i]]+=be[i];
   out.shape.robinload[face.nodes[i]]+=dbe[i];
   for(int j=0;j<6;++j){
    const int ix=out.primal.index(face.nodes[i],face.nodes[j]);
    out.primal.conduct[ix]+=re[i][j];out.shape.conduct[ix]+=dre[i][j];
   }
  }
 }
 for(int i=0;i<out.primal.n;++i){
  double p=0,d=0;
  for(int e=out.primal.offsets[i];e<out.primal.offsets[i+1];++e){
   p+=out.primal.conduct[e];d+=out.shape.conduct[e];
  }
  out.max_ones_error=std::max(out.max_ones_error,
                             std::abs(p-out.primal.robinload[i]));
  out.max_directional_ones_error=std::max(out.max_directional_ones_error,
                             std::abs(d-out.shape.robinload[i]));
 }
 out.primal.rebuild(dt);
 return out;
}

inline double inner(const std::vector<double>& a,const std::vector<double>& b){
 if(a.size()!=b.size())throw std::invalid_argument("P10L: vector size mismatch");
 double value=0;for(size_t i=0;i<a.size();++i)value+=a[i]*b[i];
 return value;
}

struct CGResult {int iterations=0;double relative=0;};
inline CGResult solve(const CSR& A,const std::vector<double>& rhs,
                      std::vector<double>& x,double tolerance=5e-11,
                      int maxiter=4000){
 const int n=A.n;
 if(int(rhs.size())!=n)throw std::invalid_argument("P10L PCG bad rhs size");
 if(int(x.size())!=n)x.assign(n,0.);
 std::vector<double> r(n),z(n),p(n),Ap;
 A.mul(A.mat,x,Ap);
 for(int i=0;i<n;++i){r[i]=rhs[i]-Ap[i];z[i]=r[i]/A.diag[i];p[i]=z[i];}
 const double r0=std::sqrt(inner(rhs,rhs));
 double rr=std::sqrt(inner(r,r));
 if(r0<1e-28)return{0,0};
 if(rr<tolerance*r0)return{0,rr/r0};
 double rz=inner(r,z);int it=0;
 for(;it<maxiter;++it){
  A.mul(A.mat,p,Ap);
  const double pp=inner(p,Ap);
  if(!(pp>0)||!std::isfinite(pp))throw std::runtime_error("P10L PCG not SPD");
  const double step=rz/pp;
  for(int i=0;i<n;++i){x[i]+=step*p[i];r[i]-=step*Ap[i];}
  if(it%10==0||it+1==maxiter){
   rr=std::sqrt(inner(r,r));if(rr<tolerance*r0)break;
  }
  for(int i=0;i<n;++i)z[i]=r[i]/A.diag[i];
  const double next=inner(r,z),beta=next/rz;
  for(int i=0;i<n;++i)p[i]=z[i]+beta*p[i];
  rz=next;
 }
 A.mul(A.mat,x,Ap);
 for(int i=0;i<n;++i)Ap[i]=rhs[i]-Ap[i];
 rr=std::sqrt(inner(Ap,Ap));
 const double rel=rr/r0;
 if(rel>5e-9||it>=maxiter)
  throw std::runtime_error("P10L PCG failed, relative="+std::to_string(rel));
 return{it+1,rel};
}

inline std::vector<std::vector<double>> solve_forward(const Operator& op,
                                                     int nsteps,double dt,
                                                     double xi=0.){
 const auto& A=op.primal;
 std::vector<std::vector<double>> temperature(size_t(nsteps+1),
                                              std::vector<double>(size_t(A.n),0.));
 for(int n=1;n<=nsteps;++n){
  std::vector<double> rhs;
  A.mul(A.mass,temperature[size_t(n-1)],rhs);
  const double amb=ambient(n*dt,xi);
  for(int i=0;i<A.n;++i)rhs[i]+=dt*A.robinload[i]*amb;
  temperature[size_t(n)]=temperature[size_t(n-1)];
  solve(A,rhs,temperature[size_t(n)]);
 }
 return temperature;
}

struct Gradient {
 double derivative=0;
 double worst_equilibrium=0;
 int iterations=0;
};

// q[n][i] = d(total objective)/d(theta_n,i), INCLUDING all mechanical
// reverse-time memory and direct functional terms. q[0] is ignored because
// the initial temperature is fixed independently of geometry.
inline Gradient adjoint_derivative(const Operator& op,double dt,
               const std::vector<std::vector<double>>& temperature,
               const std::vector<std::vector<double>>& q,double xi=0.){
 const int steps=int(temperature.size())-1;
 const auto& A=op.primal;
 const auto& D=op.shape;
 if(steps<1||q.size()!=temperature.size())
  throw std::invalid_argument("P10L thermal history count mismatch");
 std::vector<double> next(size_t(A.n),0.);
 Gradient result;
 for(int n=steps;n>=1;--n){
  if(int(q[size_t(n)].size())!=A.n ||
     int(temperature[size_t(n)].size())!=A.n||
     int(temperature[size_t(n-1)].size())!=A.n)
   throw std::invalid_argument("P10L thermal node count mismatch");
  std::vector<double> rhs;
  A.mul(A.mass,next,rhs);
  for(int i=0;i<A.n;++i)rhs[i]-=q[size_t(n)][size_t(i)];
  std::vector<double> psi(size_t(A.n),0.);
  const auto cg=solve(A,rhs,psi);
  result.iterations+=cg.iterations;
  std::vector<double> equilibrium;
  A.mul(A.mat,psi,equilibrium);
  for(int i=0;i<A.n;++i)equilibrium[i]-=rhs[i];
  result.worst_equilibrium=std::max(result.worst_equilibrium,
      std::sqrt(inner(equilibrium,equilibrium))/
      std::max(1e-25,std::sqrt(inner(rhs,rhs))));
  std::vector<double> difference(size_t(A.n),0.),part_mass,part_cond;
  for(int i=0;i<A.n;++i)
   difference[i]=temperature[size_t(n)][size_t(i)]-
                 temperature[size_t(n-1)][size_t(i)];
  D.mul(D.mass,difference,part_mass);
  D.mul(D.conduct,temperature[size_t(n)],part_cond);
  const double amb=ambient(n*dt,xi);
  for(int i=0;i<A.n;++i)
   result.derivative+=psi[i]*(part_mass[i]+dt*part_cond[i]-
                                              dt*D.robinload[i]*amb);
  next=std::move(psi);
 }
 return result;
}

inline double independent_thermal_fd(const std::vector<std::vector<double>>& q,
  const std::vector<std::vector<double>>& plus,
  const std::vector<std::vector<double>>& minus,double delta){
 if(q.size()!=plus.size()||q.size()!=minus.size())
  throw std::invalid_argument("P10L FD temporal mismatch");
 double sum=0.;
 for(size_t n=1;n<q.size();++n){
  if(q[n].size()!=plus[n].size()||q[n].size()!=minus[n].size())
   throw std::invalid_argument("P10L FD nodal mismatch");
  for(size_t i=0;i<q[n].size();++i)
   sum+=q[n][i]*(plus[n][i]-minus[n][i])/(2*delta);
 }
 return sum;
}
} // namespace ice3d::p10l
