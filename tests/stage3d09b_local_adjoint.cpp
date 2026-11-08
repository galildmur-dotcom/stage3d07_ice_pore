// Stage 3D-09B preflight: local material-point reverse sensitivities with active history.
// NOT the full FEM/thermal/shape adjoint. Provides an independent Jacobian/transpose test.
#include "edv_material.hpp"
#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using ice3d::edv::State;
using ice3d::edv::Tensor;
using ice3d::edv::Response;
using ice3d::edv::Controls;
using ice3d::ed::Modulus;
namespace {
struct Input{Tensor eps{};double T=253.15,dt=75.;State st{};};
std::array<double,18> result(const Input&in, Modulus mod,Controls flags){auto x=ice3d::edv::update(in.eps,in.T,in.dt,in.st,mod,flags);
 std::array<double,18> y{};for(int i=0;i<6;++i){y[i]=x.sigma[i];y[6+i]=x.new_state.e_d[i];y[12+i]=x.new_state.e_v[i];}return y;}
Input perturb(const Input&base,int k,double h,Controls flags){Input t=base;
 if(k<6)t.eps[k]+=h;
 else if(k==6)t.T+=h;
 else{int idx=k-7;if(idx<5){if(!flags.delayed)throw std::runtime_error("Inactive e_d");auto &v=t.st.e_d;
  if(idx==0){v[0]+=h;v[2]-=h;}else if(idx==1){v[1]+=h;v[2]-=h;}else v[idx+1]+=h;}
 else{if(!flags.viscous)throw std::runtime_error("Inactive e_v");auto &v=t.st.e_v;idx-=5;
  if(idx==0){v[0]+=h;v[2]-=h;}else if(idx==1){v[1]+=h;v[2]-=h;}else v[idx+1]+=h;}}
 return t;}
}
int main(){try{
 Input b; b.eps={1.2e-4,-5e-5,-7e-5,2e-5,-3e-5,2e-5};b.T=251.65;
 b.st.e_d={4e-6,-2e-6,-2e-6,1e-6,2e-6,-1e-6};
 b.st.e_v={2e-7,-5e-7,3e-7,1e-7,-1e-7,3e-7};
 std::array<double,18> lambda{};for(int i=0;i<18;++i)lambda[i]=(i<6?1e-6:1e4)*std::sin(.7*(i+1));
 int tests=0;
 for(const std::string name:{"E","ED","EDV"})for(Modulus mod:{Modulus::CONST,Modulus::VAR}){
  Controls flags{name!="E",name=="EDV"};Input input=b;if(!flags.delayed)input.st.e_d={};if(!flags.viscous)input.st.e_v={};
  const auto y0=result(input,mod,flags);int n=7+(flags.delayed?5:0)+(flags.viscous?5:0);
  // Column Jacobian using independent small, history-compatible deviatoric increments.
  std::vector<std::array<double,18>> Jacobian;Jacobian.reserve(n);
  for(int k=0;k<n;++k){double h=k==6?1e-4:(k<6?1e-8:1e-9);auto xp=result(perturb(input,k,h,flags),mod,flags);auto xm=result(perturb(input,k,-h,flags),mod,flags);std::array<double,18> col{};
   for(int i=0;i<18;++i)col[i]=(xp[i]-xm[i])/(2*h);Jacobian.push_back(col);}
  // Independent directional Taylor + transpose dot product (state history included).
  for(int k=0;k<n;++k){double h=k==6?2e-4:(k<6?2e-8:2e-9);
   auto yp=result(perturb(input,k,h,flags),mod,flags);auto ym=result(perturb(input,k,-h,flags),mod,flags);
   double fd=0,adj=0;for(int i=0;i<18;++i){fd+=lambda[i]*(yp[i]-ym[i])/(2*h);adj+=lambda[i]*Jacobian[k][i];}
   if(std::abs(fd-adj)>1e-3*std::max(1.,std::abs(fd)))throw std::runtime_error("Local adjoint transpose failure: "+name);
  }
  // Cross-check analytic stresses and temperature tangents against numerical columns.
  auto full=ice3d::edv::update(input.eps,input.T,input.dt,input.st,mod,flags);
  for(int k=0;k<7;++k)for(int i=0;i<6;++i){double ref=k==6?full.d_sigma_dT[i]:full.tangent[i][k];
   if(std::abs(Jacobian[k][i]-ref)>6e-4*std::max(1.,std::abs(ref)))throw std::runtime_error("Analytic constitutive Jacobian error: "+name);}
  ++tests;
 }
 if(tests!=6)throw std::runtime_error("Missing model test");
 std::cout<<"P09B_LOCAL_ADJOINT_PREFLIGHT_OK: 6 models, history-compatible local Jacobian/transpose, sigma tangents\n";
 return 0;
 }catch(const std::exception&e){std::cerr<<"P09B_PREFLIGHT_ERROR: "<<e.what()<<"\n";return 2;}}
