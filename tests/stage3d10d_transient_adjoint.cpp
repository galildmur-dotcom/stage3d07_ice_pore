// Stage 3D-10D. Tiny but NONLINEAR multi-step global Tet10 discrete adjoint.
// Production Tet10 quadrature, analytic EDV JVP/VJP (P10B/10C), Newton solve
// at every time step, backward propagation of internal history.
// Geometric partial derivatives use symmetric mesh perturbations at FROZEN
// converged (u,z_old): a discrete semi-analytic shape-directional preflight,
// not a continuous surface gradient nor coupled thermal shape derivative.
#define STAGE3D06_LIBRARY
#include "mechanical.cpp"
#include "stage3d10c_tet10_global_adjoint.hpp"
#ifdef STAGE3D10E_SPARSE_ADJOINT
#include "stage3d10e_bcsr_adjoint.hpp"
#endif
#ifdef STAGE3D10F_PHYSICAL_FUNCTIONALS
#include "stage3d10f_functional_adjoint.hpp"
#endif
#ifdef STAGE3D10G_CHECKPOINT_REPLAY
#include "checkpoint_chunked_io.hpp"
#include <bit>
#include <filesystem>
#include <fstream>
#endif
#include <iomanip>
#include <map>
#include <numbers>

namespace {
using ice3d::p10c::State;
using ice3d::p10c::Step;
using ice3d::p10c::Output;
using ice3d::p10c::Perturbation;
using ice3d::p10c::Pullback;
using ice3d::p10b::Controls;
using ice3d::p10b::Modulus;

constexpr int Ntime=12;
constexpr double Dt=150.;
#ifdef STAGE3D10E_SPARSE_ADJOINT
int sparse_solves=0;
int sparse_iterations=0;
double sparse_worst_residual=0;
void record_sparse(const ice3d::p10e::IterativeResult& x){
 ++sparse_solves;
 sparse_iterations+=x.iterations;
 sparse_worst_residual=std::max(sparse_worst_residual,x.relative_residual);
}
#endif

void ensure(bool ok,const std::string& msg){
 if(!ok)throw std::runtime_error("P10D: "+msg);
}
double dot_vec(const std::vector<double>& a,const std::vector<double>& b){
 ensure(a.size()==b.size(),"vector inner-product size mismatch");
 double sum=0;for(size_t i=0;i<a.size();++i)sum+=a[i]*b[i];return sum;
}
double dot_states(const std::vector<State>& a,const std::vector<State>& b){
 ensure(a.size()==b.size(),"history inner-product size mismatch");
 double sum=0;
 for(size_t i=0;i<a.size();++i){
  sum+=ice3d::p10b::euclid_dot(a[i].e_d,b[i].e_d);
  sum+=ice3d::p10b::euclid_dot(a[i].e_v,b[i].e_v);
 }
 return sum;
}
double length(const std::vector<double>& v){return std::sqrt(dot_vec(v,v));}

// Dense partial-pivot solve is intentional: 42 DOFs here; the production
// implementation MUST replace it with the BCSR/preconditioned sparse solver.
std::vector<double> dense_solve(std::vector<std::vector<double>> A,
                                std::vector<double> b){
 const size_t n=A.size();ensure(b.size()==n,"dense RHS mismatch");
 for(size_t k=0;k<n;++k){
  size_t pivot=k;
  for(size_t i=k+1;i<n;++i)
   if(std::abs(A[i][k])>std::abs(A[pivot][k]))pivot=i;
  ensure(std::abs(A[pivot][k])>1e-18,"singular mechanical tangent");
  if(pivot!=k){std::swap(A[pivot],A[k]);std::swap(b[pivot],b[k]);}
  for(size_t i=k+1;i<n;++i){
   const double fac=A[i][k]/A[k][k];A[i][k]=0;
   for(size_t j=k+1;j<n;++j)A[i][j]-=fac*A[k][j];
   b[i]-=fac*b[k];
  }
 }
 std::vector<double> x(n,0.);
 for(int i=int(n)-1;i>=0;--i){
  double sum=b[i];
  for(size_t j=i+1;j<n;++j)sum-=A[i][j]*x[j];
  x[i]=sum/A[i][i];
 }
 return x;
}

struct Geometry {
 Mesh mesh;
 std::vector<uint8_t> bc;
 std::map<std::pair<int,int>,int> mid;
 explicit Geometry(double shape){
  // The clamp face ABD is unchanged. C and E deform; midpoint nodes track
  // endpoints exactly so the Tet10 map remains affine within each tetra.
  mesh.nodes={V{0,0,0}, V{.004,0,0},
              V{.00015*shape,.003*(1.+.05*shape),.00012*shape},
              V{0,0,.004},
              V{.00025+.00030*shape,.0003+.00020*shape,
                -.0035*(1.+.04*shape)}};
  auto midpoint=[&](int a,int b){
   if(a>b)std::swap(a,b);
   const auto pair=std::make_pair(a,b);
   if(auto it=mid.find(pair);it!=mid.end())return it->second;
   const int index=int(mesh.nodes.size());
   mesh.nodes.push_back((mesh.nodes[a]+mesh.nodes[b])*.5);
   mid[pair]=index;
   return index;
  };
  constexpr int edges[6][2]={{0,1},{1,2},{2,0},{0,3},{1,3},{2,3}};
  for(auto corners:std::array<std::array<int,4>,2>{{{{0,1,2,3}},{{0,2,1,4}}}}){
   Tet t{};
   for(int i=0;i<4;++i)t[i]=corners[i];
   for(int e=0;e<6;++e)
    t[4+e]=midpoint(corners[edges[e][0]],corners[edges[e][1]]);
   mesh.tets.push_back(t);
  }
  bc.assign(3*mesh.nodes.size(),0);
  for(int node:std::array<int,6>{0,1,3,midpoint(0,1),midpoint(0,3),midpoint(1,3)})
   for(int k=0;k<3;++k)bc[3*node+k]=1;
 }
};

struct Problem {
 Geometry geom;
 std::vector<GaussQ> quadrature;
 Controls flags;
 Modulus modulus;
 double temp_param;
#ifdef STAGE3D10E_SPARSE_ADJOINT
 std::shared_ptr<const BCSRTopology> topology;
 std::shared_ptr<const ice3d::p10e::ReverseGraph> reverse_graph;
#endif
 explicit Problem(double shape,double temp,Controls f,Modulus m)
  :geom(shape),quadrature(volume_q(3)),flags(f),modulus(m),temp_param(temp){
#ifdef STAGE3D10E_SPARSE_ADJOINT
  topology=build_bcsr_topology(geom.mesh);
  BCSR graph_only;
  graph_only.set_topology(topology);
  reverse_graph=std::make_shared<const ice3d::p10e::ReverseGraph>(graph_only);
#endif
 }

 std::vector<double> temperature(int n)const{
  std::vector<double> T(geom.mesh.nodes.size());
  for(size_t j=0;j<T.size();++j){
   const double base=-5.8+0.35*std::sin(.47*double(j))+.22*std::sin(.30*n);
   const double shape=.9+.12*std::cos(.27*double(j));
   T[j]=base+temp_param*shape*(.6+.4*std::sin(.2*n));
  }
  return T;
 }
 std::vector<double> temperature_direction(int n)const{
  std::vector<double> dT(geom.mesh.nodes.size());
  for(size_t j=0;j<dT.size();++j)
   dT[j]=(.9+.12*std::cos(.27*double(j)))*(.6+.4*std::sin(.2*n));
  return dT;
 }
 std::vector<double> nodal_force(int n)const{
  std::vector<double> f(geom.bc.size());
  for(size_t i=0;i<f.size();++i)if(!geom.bc[i])
   f[i]=.22*(1.+.08*n)*std::sin(.31*double(i)+.15*n);
  return f;
 }
};

using Matrix=std::vector<std::vector<double>>;
Matrix jacobian(const Step& step){
 const size_t ndof=step.u.size();
 Matrix K(ndof,std::vector<double>(ndof,0.));
 Perturbation direction;
 direction.du.assign(ndof,0.);
 direction.dtemperature.assign(step.node_count,0.);
 direction.dprevious.resize(step.qps.size());
 for(size_t j=0;j<ndof;++j){
  direction.du[j]=1.;
  const auto out=step.jvp(direction);
  for(size_t i=0;i<ndof;++i)K[i][j]=out.residual[i];
  direction.du[j]=0.;
 }
 return K;
}

struct Frame {
 std::vector<double> u,T,force;
 std::vector<State> previous,next;
 int newton_iterations=0;
 double final_residual=0;
};

Frame equilibrium(const Problem& p,int n,const std::vector<State>& previous,
                  const std::vector<double>& start){
 Frame result;
 result.T=p.temperature(n);result.force=p.nodal_force(n);
 result.previous=previous;result.u=start;
 for(size_t i=0;i<result.u.size();++i)if(p.geom.bc[i])result.u[i]=0;
 for(int it=0;it<12;++it){
  const Step step(p.geom.mesh,p.quadrature,result.T,previous,Dt,
                  result.u,p.geom.bc,p.modulus,p.flags);
  const Output out=step.evaluate();
  std::vector<double> r=out.residual;
  for(size_t i=0;i<r.size();++i)r[i]-=result.force[i];
  result.final_residual=length(r);
  if(result.final_residual<3e-10){
   result.newton_iterations=it;
   result.next=out.next;
   return result;
  }
  for(double& value:r)value=-value;
#ifdef STAGE3D10E_SPARSE_ADJOINT
  auto K=ice3d::p10e::assemble_tangent_bcsr(p.geom.mesh,step,p.topology);
  const auto solved=ice3d::p10e::solve_bicgstab(K,p.geom.bc,r,false,
                                                2e-13,400,p.reverse_graph.get());
  record_sparse(solved);
  const auto& correction=solved.x;
#else
  const auto K=jacobian(step);
  const auto correction=dense_solve(K,r);
#endif
  for(size_t i=0;i<result.u.size();++i)result.u[i]+=correction[i];
 }
 throw std::runtime_error("P10D: nonlinear equilibrium did not converge");
}

struct Trajectory{
 std::vector<Frame> frames;
 double J=0;
 int newton_total=0;
 double max_residual=0;
};

std::vector<double> objective_u(const Geometry& g,int n){
 std::vector<double> c(g.bc.size());
 const double w=.065+.025*n/Ntime;
 for(size_t i=0;i<c.size();++i)if(!g.bc[i])
  c[i]=w*2.e5*std::sin(.35*double(i)+.23*n);
 return c;
}
std::vector<State> objective_state(size_t count,int n){
 std::vector<State> c(count);
 const double w=.065+.025*n/Ntime;
 for(size_t i=0;i<count;++i)for(int k=0;k<6;++k){
  c[i].e_d[k]=w*5000.*std::sin(.23*double(i)+.37*k+.11*n);
  c[i].e_v[k]=w*5000.*std::cos(.19*double(i)+.41*k+.07*n);
 }
 return c;
}
Trajectory forward(const Problem& p){
 Trajectory path;
 std::vector<State> previous(p.geom.mesh.tets.size()*p.quadrature.size());
 std::vector<double> u(p.geom.bc.size(),0.);
 path.frames.reserve(Ntime);
 for(int n=1;n<=Ntime;++n){
  Frame frame=equilibrium(p,n,previous,u);
  const auto c=objective_u(p.geom,n);
  const auto l=objective_state(previous.size(),n);
  path.J+=dot_vec(c,frame.u)+dot_states(l,frame.next);
  path.newton_total+=frame.newton_iterations;
  path.max_residual=std::max(path.max_residual,frame.final_residual);
  previous=frame.next;u=frame.u;
  path.frames.push_back(std::move(frame));
 }
 return path;
}

struct Gradients{
 double temperature=0,shape=0;
 double max_adjoint_equilibrium_residual=0;
};

Gradients reverse(const Problem& p,const Trajectory& path,bool propagate_history=true){
 const size_t qcount=p.geom.mesh.tets.size()*p.quadrature.size();
 std::vector<State> future(qcount);
 Gradients gradient;
 const double geometry_h=8.e-4;
 const Geometry plus(geometry_h),minus(-geometry_h);
 for(int i=Ntime-1;i>=0;--i){
  const int n=i+1;
  const auto& frame=path.frames[i];
  const Step step(p.geom.mesh,p.quadrature,frame.T,frame.previous,Dt,
                  frame.u,p.geom.bc,p.modulus,p.flags);
  auto state_cotangent=objective_state(qcount,n);
  for(size_t j=0;j<qcount;++j)for(int k=0;k<6;++k){
   state_cotangent[j].e_d[k]+=future[j].e_d[k];
   state_cotangent[j].e_v[k]+=future[j].e_v[k];
  }
  Output lambda;
  lambda.residual.assign(frame.u.size(),0.);
  lambda.next=state_cotangent;
  const auto through_memory=step.vjp(lambda);
  const auto direct=objective_u(p.geom,n);
  std::vector<double> rhs(direct.size());
  for(size_t j=0;j<rhs.size();++j)
   rhs[j]=-(direct[j]+through_memory.displacement[j]);
#ifdef STAGE3D10E_SPARSE_ADJOINT
  auto K=ice3d::p10e::assemble_tangent_bcsr(p.geom.mesh,step,p.topology);
  const auto solved=ice3d::p10e::solve_bicgstab(K,p.geom.bc,rhs,true,
                                                2e-13,400,p.reverse_graph.get());
  record_sparse(solved);
  lambda.residual=solved.x;
#else
  auto K=jacobian(step);
  Matrix KT=K;
  for(size_t j=0;j<K.size();++j)for(size_t k=0;k<K.size();++k)KT[j][k]=K[k][j];
  lambda.residual=dense_solve(std::move(KT),rhs);
#endif
  const auto back=step.vjp(lambda);
  double adjoint_residual=0,adjoint_norm=0;
  for(size_t j=0;j<rhs.size();++j){
   const double err=back.displacement[j]+direct[j];
   adjoint_residual+=err*err;
   adjoint_norm+=direct[j]*direct[j];
  }
  gradient.max_adjoint_equilibrium_residual=std::max(
   gradient.max_adjoint_equilibrium_residual,
   std::sqrt(adjoint_residual)/std::max(1.,std::sqrt(adjoint_norm)));
  gradient.temperature+=dot_vec(back.temperature,p.temperature_direction(n));
  const auto positive=Step(plus.mesh,p.quadrature,frame.T,frame.previous,Dt,
                           frame.u,p.geom.bc,p.modulus,p.flags).evaluate();
  const auto negative=Step(minus.mesh,p.quadrature,frame.T,frame.previous,Dt,
                           frame.u,p.geom.bc,p.modulus,p.flags).evaluate();
  for(size_t j=0;j<lambda.residual.size();++j)
   gradient.shape+=lambda.residual[j]*(positive.residual[j]-negative.residual[j])/(2*geometry_h);
  for(size_t j=0;j<qcount;++j)for(int k=0;k<6;++k){
   gradient.shape+=lambda.next[j].e_d[k]*
    (positive.next[j].e_d[k]-negative.next[j].e_d[k])/(2*geometry_h);
   gradient.shape+=lambda.next[j].e_v[k]*
    (positive.next[j].e_v[k]-negative.next[j].e_v[k])/(2*geometry_h);
  }
  if(propagate_history)future=back.previous;
  else future.assign(qcount,{}); // intentional ablation: discard temporal memory
 }
 return gradient;
}
double relative_error(double a,double b){
 return std::abs(a-b)/std::max({1e-7,std::abs(a),std::abs(b)});
}

#ifdef STAGE3D10F_PHYSICAL_FUNCTIONALS
namespace f10=ice3d::p10f;

double physical_value(const Problem& problem,const Trajectory& path,
                      f10::Kind kind,const f10::Parameters& options={}){
 double moment=.5/Ntime*f10::initial_time_value(kind,options);
 for(int i=0;i<Ntime;++i){
  const auto& frame=path.frames[i];
  const Step step(problem.geom.mesh,problem.quadrature,frame.T,frame.previous,
                  Dt,frame.u,problem.geom.bc,problem.modulus,problem.flags);
  moment+=((i==Ntime-1)?.5:1.)/Ntime*
    f10::evaluate(step,kind,options).value;
 }
 if(kind==f10::Kind::PeakMoment){
  ensure(moment>0,"P10F: nonpositive peak power moment");
  return std::pow(moment,1./options.peak_p);
 }
 return moment;
}

Gradients physical_reverse(const Problem& problem,const Trajectory& path,
                           f10::Kind kind,double J,
                           const f10::Parameters& options={}){
 const size_t nq=problem.geom.mesh.tets.size()*problem.quadrature.size();
 std::vector<State> future(nq);
 Gradients gradient;
 constexpr double geom_fd_step=2e-4;
 const Geometry plus(geom_fd_step),minus(-geom_fd_step);
 const double moment=(kind==f10::Kind::PeakMoment)?std::pow(J,options.peak_p):1.;
 const double chain=(kind==f10::Kind::PeakMoment)
    ?std::pow(moment,1./options.peak_p-1)/options.peak_p:1.;
 for(int i=Ntime-1;i>=0;--i){
  const int n=i+1;
  const auto& frame=path.frames[i];
  const Step step(problem.geom.mesh,problem.quadrature,frame.T,frame.previous,
                  Dt,frame.u,problem.geom.bc,problem.modulus,problem.flags);
  const auto src=f10::evaluate(step,kind,options);
  const double coefficient=chain*((n==Ntime)?.5:1.)/Ntime;
  Output lambda;
  lambda.residual.assign(frame.u.size(),0.);
  lambda.next=future;
  const auto memory=step.vjp(lambda);
  std::vector<double> rhs(frame.u.size());
  for(size_t k=0;k<rhs.size();++k)
   rhs[k]=-(coefficient*src.displacement[k]+memory.displacement[k]);

  auto K=ice3d::p10e::assemble_tangent_bcsr(problem.geom.mesh,step,problem.topology);
  const auto solved=ice3d::p10e::solve_bicgstab(K,problem.geom.bc,rhs,true,
                                2e-13,400,problem.reverse_graph.get());
  record_sparse(solved);
  lambda.residual=solved.x;
  const auto back=step.vjp(lambda);
  double residual_sq=0,source_sq=0;
  for(size_t k=0;k<rhs.size();++k){
   const double source=coefficient*src.displacement[k];
   residual_sq+=std::pow(back.displacement[k]+source,2);
   source_sq+=source*source;
  }
  gradient.max_adjoint_equilibrium_residual=std::max(
    gradient.max_adjoint_equilibrium_residual,
    std::sqrt(residual_sq)/std::max(1.,std::sqrt(source_sq)));
  const auto dTdp=problem.temperature_direction(n);
  for(size_t k=0;k<dTdp.size();++k)
   gradient.temperature+=(back.temperature[k]+coefficient*src.temperature[k])*dTdp[k];

  // At frozen u, T, z_previous: explicit shape partial of mechanical
  // residual, updated history, and volume-normalized objective itself.
  const Step qp(plus.mesh,problem.quadrature,frame.T,frame.previous,
                Dt,frame.u,problem.geom.bc,problem.modulus,problem.flags);
  const Step qm(minus.mesh,problem.quadrature,frame.T,frame.previous,
                Dt,frame.u,problem.geom.bc,problem.modulus,problem.flags);
  const auto outp=qp.evaluate(),outm=qm.evaluate();
  const double valuep=f10::evaluate(qp,kind,options).value;
  const double valuem=f10::evaluate(qm,kind,options).value;
  gradient.shape+=coefficient*(valuep-valuem)/(2*geom_fd_step);
  for(size_t k=0;k<lambda.residual.size();++k)
   gradient.shape+=lambda.residual[k]*(outp.residual[k]-outm.residual[k])/(2*geom_fd_step);
  for(size_t k=0;k<nq;++k)for(int c=0;c<6;++c){
   gradient.shape+=future[k].e_d[c]*(outp.next[k].e_d[c]-outm.next[k].e_d[c])/(2*geom_fd_step);
   gradient.shape+=future[k].e_v[c]*(outp.next[k].e_v[c]-outm.next[k].e_v[c])/(2*geom_fd_step);
  }
  for(size_t k=0;k<nq;++k)for(int c=0;c<6;++c){
   future[k].e_d[c]=back.previous[k].e_d[c]+coefficient*src.previous[k].e_d[c];
   future[k].e_v[c]=back.previous[k].e_v[c]+coefficient*src.previous[k].e_v[c];
  }
 }
 return gradient;
}

double check_instant_functional_source(){
 const Problem problem(0,0,Controls{true,true},Modulus::VAR);
 const auto trajectory=forward(problem);
 const auto& frame=trajectory.frames[2];
 const Step step(problem.geom.mesh,problem.quadrature,frame.T,frame.previous,
                 Dt,frame.u,problem.geom.bc,problem.modulus,problem.flags);
 Perturbation d;
 d.du.resize(frame.u.size());
 d.dtemperature.resize(frame.T.size());
 d.dprevious.resize(frame.previous.size());
 for(size_t j=0;j<d.du.size();++j)d.du[j]=2e-7*std::sin(.2*double(j));
 for(size_t j=0;j<d.dtemperature.size();++j)
  d.dtemperature[j]=.25*std::cos(.13*double(j));
 for(size_t j=0;j<d.dprevious.size();++j){
  double normals[3]{.7e-6*std::sin(.31*double(j)),
                    .4e-6*std::cos(.21*double(j)),
                    .3e-6*std::sin(.14*double(j))};
  const double mean=(normals[0]+normals[1]+normals[2])/3.;
  for(int k=0;k<3;++k){
   d.dprevious[j].e_d[k]=normals[k]-mean;
   d.dprevious[j].e_v[k]=.8*(normals[k]-mean);
  }
  for(int k=3;k<6;++k){
   d.dprevious[j].e_d[k]=.4e-6*std::sin(.15*j+.17*k);
   d.dprevious[j].e_v[k]=.2e-6*std::cos(.16*j+.13*k);
  }
 }
 const double h=2e-5;
 auto plus_u=frame.u,minus_u=frame.u;
 auto plus_T=frame.T,minus_T=frame.T;
 auto plus_old=frame.previous,minus_old=frame.previous;
 for(size_t i=0;i<plus_u.size();++i){
  plus_u[i]+=h*d.du[i];minus_u[i]-=h*d.du[i];
 }
 for(size_t i=0;i<plus_T.size();++i){
  plus_T[i]+=h*d.dtemperature[i];minus_T[i]-=h*d.dtemperature[i];
 }
 for(size_t i=0;i<plus_old.size();++i)for(int k=0;k<6;++k){
  plus_old[i].e_d[k]+=h*d.dprevious[i].e_d[k];
  plus_old[i].e_v[k]+=h*d.dprevious[i].e_v[k];
  minus_old[i].e_d[k]-=h*d.dprevious[i].e_d[k];
  minus_old[i].e_v[k]-=h*d.dprevious[i].e_v[k];
 }
 double worst=0;
 int ki=0;
 for(auto kind:std::array{f10::Kind::J6,f10::Kind::PeakMoment,
                          f10::Kind::Energy,f10::Kind::SafetySmooth}){
  const auto src=f10::evaluate(step,kind);
  const double predicted=dot_vec(src.displacement,d.du)
       +dot_vec(src.temperature,d.dtemperature)
       +dot_states(src.previous,d.dprevious);
  const Step sp(problem.geom.mesh,problem.quadrature,plus_T,plus_old,
                Dt,plus_u,problem.geom.bc,problem.modulus,problem.flags);
  const Step sm(problem.geom.mesh,problem.quadrature,minus_T,minus_old,
                Dt,minus_u,problem.geom.bc,problem.modulus,problem.flags);
  const double observed=(f10::evaluate(sp,kind).value-
                         f10::evaluate(sm,kind).value)/(2*h);
  const double err=relative_error(predicted,observed);
  std::cerr<<std::scientific<<std::setprecision(8)
           <<"P10F singleQP_kind="<<ki++<<" predicted="<<predicted
           <<" FD="<<observed<<" relative="<<err<<'\n';
  worst=std::max(worst,err);
 }
 ensure(worst<1e-5,"P10F: instantaneous functional cotangent failed FD");
 return worst;
}

int run_physical_tests(){
 const double instant_worst=check_instant_functional_source();
 const std::array<std::pair<Controls,Modulus>,6> cases{{
  {Controls{false,false},Modulus::CONST},
  {Controls{false,false},Modulus::VAR},
  {Controls{true,false},Modulus::CONST},
  {Controls{true,false},Modulus::VAR},
  {Controls{true,true},Modulus::CONST},
  {Controls{true,true},Modulus::VAR}
 }};
 const std::array<f10::Kind,4> observables{
  f10::Kind::J6,f10::Kind::PeakMoment,f10::Kind::Energy,f10::Kind::SafetySmooth
 };
 const std::array<const char*,4> names{"j6","jpeak","jen","safety_smooth_TEST"};
 std::array<double,4> worst_T{},worst_shape{};
 double worst_equilibrium=0;
 int combinations=0;
 const double ht=2e-4,hs=5e-4;
 for(size_t model=0;model<cases.size();++model){
  const auto [flags,mod]=cases[model];
  const Problem normal(0,0,flags,mod),
                temp_plus(0,ht,flags,mod),temp_minus(0,-ht,flags,mod),
                geom_plus(hs,0,flags,mod),geom_minus(-hs,0,flags,mod);
  const auto path=forward(normal),
             pt=forward(temp_plus),mt=forward(temp_minus),
             ps=forward(geom_plus),ms=forward(geom_minus);
  for(size_t f=0;f<observables.size();++f){
   const auto kind=observables[f];
   const double J=physical_value(normal,path,kind);
   const auto grad=physical_reverse(normal,path,kind,J);
   const double dTfd=(physical_value(temp_plus,pt,kind)-
                      physical_value(temp_minus,mt,kind))/(2*ht);
   const double dSfd=(physical_value(geom_plus,ps,kind)-
                      physical_value(geom_minus,ms,kind))/(2*hs);
   const double errT=relative_error(grad.temperature,dTfd);
   const double errS=relative_error(grad.shape,dSfd);
   worst_T[f]=std::max(worst_T[f],errT);
   worst_shape[f]=std::max(worst_shape[f],errS);
   worst_equilibrium=std::max(worst_equilibrium,
                               grad.max_adjoint_equilibrium_residual);
   std::cerr<<std::scientific<<std::setprecision(5)
       <<"P10F model="<<model<<" observable="<<names[f]<<" J="<<J
       <<" temp_adjoint="<<grad.temperature<<" temp_FD="<<dTfd
       <<" shape_adjoint="<<grad.shape<<" shape_FD="<<dSfd
       <<" T_rel="<<errT<<" shape_rel="<<errS<<'\n';
   ensure(errT<5e-4,"P10F: full temperature derivative mismatch for "+std::string(names[f]));
   ensure(errS<5e-4,"P10F: full geometry derivative mismatch for "+std::string(names[f]));
   ensure(grad.max_adjoint_equilibrium_residual<1e-8,
          "P10F: adjoint equation residual failed");
   ++combinations;
  }
 }
 std::cout<<std::scientific<<std::setprecision(12)
  <<"P10F_PHYSICAL_FUNCTIONAL_ADJOINT_OK models=6 observables=4 cases="<<combinations
  <<" instant_FD_rel="<<instant_worst
  <<" j6_temp_rel="<<worst_T[0]<<" j6_shape_rel="<<worst_shape[0]
  <<" jpeak_temp_rel="<<worst_T[1]<<" jpeak_shape_rel="<<worst_shape[1]
  <<" jen_temp_rel="<<worst_T[2]<<" jen_shape_rel="<<worst_shape[2]
  <<" safety_test_temp_rel="<<worst_T[3]
  <<" safety_test_shape_rel="<<worst_shape[3]
  <<" worst_adjoint_equilibrium_rel="<<worst_equilibrium<<'\n';
 return 0;
}

#endif // STAGE3D10F_PHYSICAL_FUNCTIONALS

#ifdef STAGE3D10G_CHECKPOINT_REPLAY
#include "stage3d10g_checkpoint_replay.hpp"
#endif

#ifdef STAGE3D10E_SPARSE_ADJOINT
struct SparseChecks {
 double assembled_jvp=0;
 double nonsymmetric_transpose=0;
 double transpose_gather_vs_scatter=0;
 double nonsymmetric_solve=0;
 double large_graph_transpose=0;
 double large_graph_identity=0;
};
SparseChecks check_sparse_independently(){
 const Problem p(0,0,Controls{true,true},Modulus::VAR);
 const size_t nq=p.geom.mesh.tets.size()*p.quadrature.size();
 std::vector<double> u(p.geom.bc.size(),0.);
 for(size_t i=0;i<u.size();++i)if(!p.geom.bc[i])
  u[i]=2e-7*std::sin(.19*double(i));
 const Step step(p.geom.mesh,p.quadrature,p.temperature(1),
                 std::vector<State>(nq),Dt,u,p.geom.bc,p.modulus,p.flags);
 BCSR K=ice3d::p10e::assemble_tangent_bcsr(p.geom.mesh,step,p.topology);
 Perturbation direction;
 direction.du.resize(u.size());
 direction.dtemperature.assign(p.geom.mesh.nodes.size(),0.);
 direction.dprevious.resize(nq);
 for(size_t i=0;i<u.size();++i)direction.du[i]=std::sin(.41*double(i));
 const auto analytical=step.jvp(direction).residual;
 std::vector<double> assembled;
 K.mul_legacy(direction.du,assembled,p.geom.bc);
 std::vector<double> delta=analytical;
 for(size_t i=0;i<delta.size();++i)delta[i]-=assembled[i];
 SparseChecks result;
 result.assembled_jvp=length(delta)/std::max({1.,length(analytical),length(assembled)});
 ensure(result.assembled_jvp<3e-13,"BCSR tangent does not match Stage10C JVP");

 // Break block symmetry on a free-free offdiagonal entry. This ensures that
 // the transpose SpMV test cannot pass merely because elasticity is symmetric.
 K.a[K.pos(2,4)][2]+=1.8e6;
 K.a[K.pos(4,2)][6]-=.65e6;
 std::vector<double> x(u.size()),y(u.size());
 for(size_t i=0;i<x.size();++i){
  x[i]=std::sin(.17*double(i)+.2);
  y[i]=std::cos(.27*double(i)-.1);
 }
 std::vector<double> Ky,KT_x;
 K.mul_legacy(y,Ky,p.geom.bc);
 ice3d::p10e::multiply_transpose(K,x,KT_x,p.geom.bc);
 std::vector<double> KT_gather;
 ice3d::p10e::multiply_transpose(K,x,KT_gather,p.geom.bc,p.reverse_graph.get());
 std::vector<double> difference=KT_x;
 for(size_t i=0;i<difference.size();++i)difference[i]-=KT_gather[i];
 result.transpose_gather_vs_scatter=length(difference)/
   std::max({1.,length(KT_x),length(KT_gather)});
 ensure(result.transpose_gather_vs_scatter<1e-14,
        "parallel-ready transpose gather differs from reference scatter");
 const double lhs=dot_vec(x,Ky),rhs=dot_vec(KT_x,y);
 result.nonsymmetric_transpose=std::abs(lhs-rhs)/
   std::max({1.,std::abs(lhs),std::abs(rhs)});
 ensure(result.nonsymmetric_transpose<1e-13,
        "nonsymmetric BCSR transpose identity failed");
 for(size_t i=0;i<x.size();++i)if(p.geom.bc[i])
  ensure(KT_x[i]==x[i],"Dirichlet row in transpose is not identity");
 // Manufactured exact solution with homogeneous Dirichlet values.
 std::vector<double> exact(x.size());
 for(size_t i=0;i<exact.size();++i)if(!p.geom.bc[i])
  exact[i]=std::sin(.14*double(i)+.3);
 std::vector<double> rhs_t;
 ice3d::p10e::multiply_transpose(K,exact,rhs_t,p.geom.bc);
 const auto recovered=ice3d::p10e::solve_bicgstab(K,p.geom.bc,rhs_t,true,
                                                  2e-13,400,p.reverse_graph.get());
 record_sparse(recovered);
 delta=exact;
 for(size_t i=0;i<delta.size();++i)delta[i]-=recovered.x[i];
 result.nonsymmetric_solve=length(delta)/std::max(1.,length(exact));
 ensure(result.nonsymmetric_solve<2e-10,
        "nonsymmetric K^T BiCGStab failed manufactured solution");

 // Larger *synthetic BCSR graph* (>2000 nodes) executes the OpenMP gather
 // branch when the test is compiled with OpenMP. No physical mesh is claimed.
 Mesh big;
 constexpr int blocks=211;
 big.nodes.resize(blocks*10);
 big.tets.resize(blocks);
 for(int e=0;e<blocks;++e)for(int a=0;a<10;++a)
  big.tets[e][a]=10*e+a;
 BCSR synthetic;
 synthetic.init(big);
 for(size_t p=0;p<synthetic.a.size();++p)
  for(int k=0;k<9;++k)
   synthetic.a[p][k]=.4*std::sin(.01*double(p)+.29*k)+
                     .2*std::cos(.021*double(p)+.17*k);
 const ice3d::p10e::ReverseGraph big_graph(synthetic);
 std::vector<uint8_t> big_bc(3*big.nodes.size());
 std::vector<double> big_x(big_bc.size()),big_y(big_bc.size());
 for(size_t i=0;i<big_x.size();++i){
  big_bc[i]=(i%23==0)?1:0;
  big_x[i]=std::sin(.137*double(i));big_y[i]=std::cos(.193*double(i));
 }
 std::vector<double> scatter,gather,big_forward;
 ice3d::p10e::multiply_transpose(synthetic,big_x,scatter,big_bc);
 ice3d::p10e::multiply_transpose(synthetic,big_x,gather,big_bc,&big_graph);
 delta=scatter;
 for(size_t i=0;i<delta.size();++i)delta[i]-=gather[i];
 result.large_graph_transpose=length(delta)/
   std::max({1.,length(scatter),length(gather)});
 synthetic.mul_legacy(big_y,big_forward,big_bc);
 const double left=dot_vec(big_x,big_forward),right=dot_vec(gather,big_y);
 result.large_graph_identity=std::abs(left-right)/
   std::max({1.,std::abs(left),std::abs(right)});
 ensure(result.large_graph_transpose<4e-14,
        "large BCSR transpose gather/scatter mismatch");
 ensure(result.large_graph_identity<5e-13,
        "large BCSR transpose dot identity failed");
 return result;
}
#endif
}

int main(){try{
#ifdef STAGE3D10G_CHECKPOINT_REPLAY
 #ifdef _OPENMP
 omp_set_dynamic(0);
 omp_set_num_threads(4);
 #endif
 return ice3d_p10g_test::run_checkpoint_tests();
#endif
#ifdef STAGE3D10F_PHYSICAL_FUNCTIONALS
 #ifdef _OPENMP
 omp_set_dynamic(0);
 omp_set_num_threads(4);
 #endif
 return run_physical_tests();
#endif
#ifdef STAGE3D10E_SPARSE_ADJOINT
 #ifdef _OPENMP
 omp_set_dynamic(0);
 omp_set_num_threads(4);
 #endif
 const auto sparse_check=check_sparse_independently();
#endif
 double worst_temperature=0,worst_shape=0,worst_adjoint_equilibrium=0;
 double worst_no_history_temperature=0,worst_no_history_shape=0;
 int models=0,steps=0,total_newton=0;
 const std::array<std::pair<Controls,Modulus>,6> cases{{
  {Controls{false,false},Modulus::CONST},
  {Controls{false,false},Modulus::VAR},
  {Controls{true,false},Modulus::CONST},
  {Controls{true,false},Modulus::VAR},
  {Controls{true,true},Modulus::CONST},
  {Controls{true,true},Modulus::VAR}
 }};
 for(auto setting:cases){
  const Problem original(0,0,setting.first,setting.second);
  const auto path=forward(original);
  const auto grad=reverse(original,path);
  const double htemp=6.e-4,hshape=1.5e-3;
  const double temp_plus=forward(Problem(0,htemp,setting.first,setting.second)).J;
  const double temp_minus=forward(Problem(0,-htemp,setting.first,setting.second)).J;
  const double shape_plus=forward(Problem(hshape,0,setting.first,setting.second)).J;
  const double shape_minus=forward(Problem(-hshape,0,setting.first,setting.second)).J;
  const double temp_fd=(temp_plus-temp_minus)/(2*htemp);
  const double shape_fd=(shape_plus-shape_minus)/(2*hshape);
  const double temp_error=relative_error(grad.temperature,temp_fd);
  const double shape_error=relative_error(grad.shape,shape_fd);
  worst_temperature=std::max(worst_temperature,temp_error);
  worst_shape=std::max(worst_shape,shape_error);
  worst_adjoint_equilibrium=std::max(worst_adjoint_equilibrium,
                                      grad.max_adjoint_equilibrium_residual);
  if(setting.first.delayed || setting.first.viscous){
   const auto truncated=reverse(original,path,false);
   worst_no_history_temperature=std::max(worst_no_history_temperature,
       relative_error(truncated.temperature,temp_fd));
   worst_no_history_shape=std::max(worst_no_history_shape,
       relative_error(truncated.shape,shape_fd));
  }
  std::cerr<<std::scientific<<std::setprecision(6)
           <<"P10D model="<<models<<" J="<<path.J
           <<" temp_adjoint="<<grad.temperature<<" temp_FD="<<temp_fd
           <<" shape_adjoint="<<grad.shape<<" shape_FD="<<shape_fd
           <<" temp_rel="<<temp_error<<" shape_rel="<<shape_error<<'\n';
  ensure(path.max_residual<3e-10,"equilibrium residual failed");
  ensure(grad.max_adjoint_equilibrium_residual<1e-8,
         "adjoint equilibrium residual failed");
  ensure(temp_error<2e-4,"full-history temperature adjoint/FD mismatch");
  ensure(shape_error<4e-4,"full-history geometry adjoint/FD mismatch");
  ++models;steps+=Ntime;total_newton+=path.newton_total;
 }
 ensure(std::max(worst_no_history_temperature,worst_no_history_shape)>1e-2,
        "history ablation must measurably differ from full adjoint");
 std::cout<<std::scientific<<std::setprecision(12)
#ifdef STAGE3D10E_SPARSE_ADJOINT
   <<"P10E_BCSR_TRANSIENT_ADJOINT_OK models="<<models<<" steps="<<steps
#else
   <<"P10D_TRANSIENT_ADJOINT_OK models="<<models<<" steps="<<steps
#endif
   <<" newton_iterations="<<total_newton
   <<" worst_temperature_gradient_rel="<<worst_temperature
   <<" worst_geometry_gradient_rel="<<worst_shape
   <<" worst_adjoint_equilibrium_rel="<<worst_adjoint_equilibrium
   <<" ablated_history_temperature_rel="<<worst_no_history_temperature
   <<" ablated_history_geometry_rel="<<worst_no_history_shape
#ifdef STAGE3D10E_SPARSE_ADJOINT
   <<" bcsr_JVP_rel="<<sparse_check.assembled_jvp
   <<" nonsymmetric_transpose_rel="<<sparse_check.nonsymmetric_transpose
   <<" transpose_gather_rel="<<sparse_check.transpose_gather_vs_scatter
   <<" nonsymmetric_solve_rel="<<sparse_check.nonsymmetric_solve
   <<" large_graph_transpose_rel="<<sparse_check.large_graph_transpose
   <<" large_graph_identity_rel="<<sparse_check.large_graph_identity
   <<" sparse_solves="<<sparse_solves
   <<" sparse_iterations="<<sparse_iterations
   <<" worst_sparse_residual_rel="<<sparse_worst_residual
#endif
   <<'\n';
 return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
