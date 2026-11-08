// Global finite-element preflight: 2 connected Tet10 elements with a shared
// internal face and nontrivial Dirichlet boundary.  This is deliberately tiny
// enough to run on any compiler, but uses production geometric quadrature.
#define STAGE3D06_LIBRARY
#include "mechanical.cpp"
#include "stage3d10c_tet10_global_adjoint.hpp"
#include <iomanip>
#include <map>
#include <random>

namespace {
using namespace ice3d;
using ice3d::p10c::State;
using ice3d::p10c::Tensor;
using ice3d::p10c::Step;
using ice3d::p10c::Output;
using ice3d::p10c::Perturbation;
using ice3d::p10c::Pullback;

struct Fixture {
 Mesh mesh;
 std::vector<uint8_t> bc;
 std::map<std::pair<int,int>,int> mids;
 Fixture(){
  mesh.nodes={V{0,0,0},V{.004,0,0},V{0,.003,0},
              V{0,0,.004},V{.00025,.0003,-.0035}};
  auto midpoint=[&](int a,int b){
   if(a>b)std::swap(a,b);
   auto key=std::make_pair(a,b);
   if(auto it=mids.find(key);it!=mids.end())return it->second;
   const int n=int(mesh.nodes.size());
   mesh.nodes.push_back((mesh.nodes[a]+mesh.nodes[b])*.5);
   mids.emplace(key,n);
   return n;
  };
  constexpr int edges[6][2]={{0,1},{1,2},{2,0},{0,3},{1,3},{2,3}};
  for(const auto& corners:std::array<std::array<int,4>,2>{{{{0,1,2,3}},{{0,2,1,4}}}}){
   Tet t{};
   for(int i=0;i<4;++i)t[i]=corners[i];
   for(int e=0;e<6;++e)t[4+e]=midpoint(corners[edges[e][0]],corners[edges[e][1]]);
   mesh.tets.push_back(t);
  }
  bc.assign(3*mesh.nodes.size(),0);
  // Clamp face ABD (including its quadratic edge nodes), away from the shared
  // ABC face.  The two Tet10 subdomains then share free DOFs.
  for(int node:std::array<int,6>{0,1,3,midpoint(0,1),midpoint(0,3),midpoint(1,3)})
   for(int dir=0;dir<3;++dir)bc[3*node+dir]=1;
 }
};

Tensor random_deviator(std::mt19937_64& gen,double amplitude){
 std::uniform_real_distribution<double> dist(-amplitude,amplitude);
 Tensor v{};for(double& x:v)x=dist(gen);
 return edv::deviator(v);
}
double randrange(std::mt19937_64& gen,double scale){
 return std::uniform_real_distribution<double>(-scale,scale)(gen);
}
double dot_vec(const std::vector<double>& a,const std::vector<double>& b){
 if(a.size()!=b.size())throw std::runtime_error("P10C: invalid scalar product");
 double sum=0;for(size_t i=0;i<a.size();++i)sum+=a[i]*b[i];return sum;
}
double dot_state(const std::vector<State>& a,const std::vector<State>& b){
 if(a.size()!=b.size())throw std::runtime_error("P10C: invalid state pairing");
 double sum=0;
 for(size_t j=0;j<a.size();++j)
  sum+=p10b::euclid_dot(a[j].e_d,b[j].e_d)+p10b::euclid_dot(a[j].e_v,b[j].e_v);
 return sum;
}
double norm_vec(const std::vector<double>& a){return std::sqrt(dot_vec(a,a));}
double norm_state(const std::vector<State>& a){return std::sqrt(dot_state(a,a));}
double error_vec(const std::vector<double>& a,const std::vector<double>& b){
 std::vector<double> d=a;for(size_t i=0;i<a.size();++i)d[i]-=b[i];
 return norm_vec(d)/std::max({norm_vec(a),norm_vec(b),1e-15});
}
double error_state(const std::vector<State>& a,const std::vector<State>& b){
 auto d=a;
 for(size_t j=0;j<a.size();++j)for(int k=0;k<6;++k){
  d[j].e_d[k]-=b[j].e_d[k];d[j].e_v[k]-=b[j].e_v[k];
 }
 return norm_state(d)/std::max({norm_state(a),norm_state(b),1e-15});
}
void require_p10c(bool ok,const std::string& msg){
 if(!ok)throw std::runtime_error("P10C: "+msg);
}
Output fd(const Fixture& x,const std::vector<GaussQ>& quadrature,
          const std::vector<double>& T,const std::vector<State>& old,
          const std::vector<double>& u,const Perturbation& d,double h,
          p10b::Modulus mode,p10b::Controls flags){
 std::vector<double> ut=u,tt=T;
 std::vector<State> st=old;
 for(size_t j=0;j<ut.size();++j)ut[j]+=h*d.du[j];
 for(size_t j=0;j<tt.size();++j)tt[j]+=h*d.dtemperature[j];
 for(size_t j=0;j<st.size();++j)for(int k=0;k<6;++k){
  st[j].e_d[k]+=h*d.dprevious[j].e_d[k];
  st[j].e_v[k]+=h*d.dprevious[j].e_v[k];
 }
 return Step(x.mesh,quadrature,tt,st,150.0,ut,x.bc,mode,flags).evaluate();
}

void compare_classical_elastic(const Fixture& x,const std::vector<GaussQ>& quadrature,
                               const std::vector<double>& T,const std::vector<State>& old,
                               const std::vector<double>& u,const Perturbation& d){
 auto A=assemble_elastic(x.mesh,T,false,3,true);
 const Step step(x.mesh,quadrature,T,old,150.,u,x.bc,p10b::Modulus::CONST,{false,false});
 const auto R=step.evaluate();
 std::vector<double> classical;
 A.K.mul_legacy(u,classical,x.bc);
 for(size_t i=0;i<classical.size();++i)if(!x.bc[i])classical[i]-=A.f[i];
 require_p10c(error_vec(classical,R.residual)<3e-12,
         "E/CONST residual disagrees with original production BCSR assembly");
 Perturbation pure=d;
 std::fill(pure.dtemperature.begin(),pure.dtemperature.end(),0);
 pure.dprevious.assign(old.size(),{});
 const auto perturb=step.jvp(pure);
 std::vector<double> product;
 A.K.mul_legacy(pure.du,product,x.bc);
 require_p10c(error_vec(product,perturb.residual)<3e-12,
         "E/CONST JVP disagrees with original production BCSR stiffness");
}
}

int main(){try{
 Fixture x;
 const auto quadrature=volume_q(3);
 require_p10c(x.mesh.tets.size()==2 && x.mesh.nodes.size()==14 && quadrature.size()==27,
         "incorrect two-Tet10 geometry or quadrature");
 std::mt19937_64 gen(20261104);
 std::vector<double> u(3*x.mesh.nodes.size()),T(x.mesh.nodes.size());
 Perturbation d;
 d.du.resize(u.size());d.dtemperature.resize(T.size());
 for(size_t i=0;i<u.size();++i){u[i]=randrange(gen,3e-7);d.du[i]=randrange(gen,5e-7);}
 for(size_t i=0;i<T.size();++i){T[i]=-4.+randrange(gen,1.);d.dtemperature[i]=randrange(gen,1.);}
 double worst_fd_R=0,worst_fd_state=0,worst_transpose=0;
 int models=0;
 for(const auto& model:std::array<std::pair<const char*,p10b::Controls>,3>{{
       {"E",{false,false}},{"ED",{true,false}},{"EDV",{true,true}}
      }}){
  const auto [name,flags]=model;
  for(auto mod:std::array{p10b::Modulus::CONST,p10b::Modulus::VAR}){
   const size_t nq=x.mesh.tets.size()*quadrature.size();
   std::vector<State> old(nq);
   d.dprevious.resize(nq);
   for(size_t j=0;j<nq;++j){
    if(flags.delayed){old[j].e_d=random_deviator(gen,7e-6);
                      d.dprevious[j].e_d=random_deviator(gen,5e-6);}
    if(flags.viscous){old[j].e_v=random_deviator(gen,7e-6);
                      d.dprevious[j].e_v=random_deviator(gen,5e-6);}
    if(!flags.delayed){old[j].e_d={};d.dprevious[j].e_d={};}
    if(!flags.viscous){old[j].e_v={};d.dprevious[j].e_v={};}
   }
   const Step step(x.mesh,quadrature,T,old,150.0,u,x.bc,mod,flags);
   const auto linear=step.jvp(d);
   Output lambda;
   lambda.residual.resize(u.size());lambda.next.resize(nq);
   for(double& v:lambda.residual)v=randrange(gen,.2);
   for(State& st:lambda.next){
    for(double& v:st.e_d)v=randrange(gen,1.e6);
    for(double& v:st.e_v)v=randrange(gen,1.e6);
   }
   const Pullback adjoint=step.vjp(lambda);
   const double lhs=dot_vec(lambda.residual,linear.residual)
                   +dot_state(lambda.next,linear.next);
   const double rhs=dot_vec(adjoint.displacement,d.du)
                   +dot_vec(adjoint.temperature,d.dtemperature)
                   +dot_state(adjoint.previous,d.dprevious);
   const double transpose=std::abs(lhs-rhs)/std::max({1.,std::abs(lhs),std::abs(rhs)});
   worst_transpose=std::max(worst_transpose,transpose);
   require_p10c(transpose<1e-11,std::string(name)+" transpose identity failed");
   const double h=1e-4;
   const auto plus=fd(x,quadrature,T,old,u,d,h,mod,flags);
   const auto minus=fd(x,quadrature,T,old,u,d,-h,mod,flags);
   Output numerical;
   numerical.residual=plus.residual;
   numerical.next=plus.next;
   for(size_t i=0;i<numerical.residual.size();++i)
    numerical.residual[i]=(plus.residual[i]-minus.residual[i])/(2*h);
   for(size_t iq=0;iq<nq;++iq)for(int k=0;k<6;++k){
    numerical.next[iq].e_d[k]=(plus.next[iq].e_d[k]-minus.next[iq].e_d[k])/(2*h);
    numerical.next[iq].e_v[k]=(plus.next[iq].e_v[k]-minus.next[iq].e_v[k])/(2*h);
   }
   const double residual_error=error_vec(numerical.residual,linear.residual);
   const double state_error=error_state(numerical.next,linear.next);
   worst_fd_R=std::max(worst_fd_R,residual_error);
   worst_fd_state=std::max(worst_fd_state,state_error);
   require_p10c(residual_error<3e-6,std::string(name)+" global residual FD failed");
   require_p10c(state_error<3e-6,std::string(name)+" global history FD failed");
   if(std::string(name)=="E" && mod==p10b::Modulus::CONST)
    compare_classical_elastic(x,quadrature,T,old,u,d);
   ++models;
  }
 }
 std::cout<<std::scientific<<std::setprecision(12)
          <<"P10C_TET10_GLOBAL_ADJOINT_OK models="<<models
          <<" tet10="<<x.mesh.tets.size()
          <<" qp="<<quadrature.size()*x.mesh.tets.size()
          <<" dof="<<u.size()
          <<" worst_residual_FD_rel="<<worst_fd_R
          <<" worst_history_FD_rel="<<worst_fd_state
          <<" worst_transpose_rel="<<worst_transpose<<'\n';
 return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
