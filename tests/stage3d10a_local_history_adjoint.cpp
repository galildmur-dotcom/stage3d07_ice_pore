// Stage 3D-10A: a fully time-discrete, material-point reverse recurrence.
// This is intentionally NOT a global FEM/shape adjoint: its local partial
// derivatives are computed by centered differences for independent testing.
// It tests state-history propagation, including E/ED/EDV and CONST/VAR.
#include "edv_material.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using State=ice3d::edv::State;
using Controls=ice3d::edv::Controls;
using Modulus=ice3d::ed::Modulus;
using Vector=std::vector<double>;
constexpr int steps=12;
constexpr double dt=300.;
constexpr double stress_ref=1.0e6;

int state_size(const Controls c){return (c.delayed?5:0)+(c.viscous?5:0);}

// Independent deviatoric coordinates: [xx, yy, xy, yz, zx], zz=-xx-yy.
void set_deviator(ice3d::edv::Tensor& t,const Vector&z,int offset){
 t[0]=z[offset];t[1]=z[offset+1];t[2]=-t[0]-t[1];
 t[3]=z[offset+2];t[4]=z[offset+3];t[5]=z[offset+4];
}
State unpack(const Vector&z,const Controls c){
 if(int(z.size())!=state_size(c))throw std::runtime_error("State dimension mismatch");
 State s;int pos=0;
 if(c.delayed){set_deviator(s.e_d,z,pos);pos+=5;}
 if(c.viscous){set_deviator(s.e_v,z,pos);}
 return s;
}
void append_deviator(Vector&z,const ice3d::edv::Tensor&t){
 z.insert(z.end(),{t[0],t[1],t[3],t[4],t[5]});
}
Vector pack(const State&s,const Controls c){
 Vector z;z.reserve(state_size(c));
 if(c.delayed)append_deviator(z,s.e_d);
 if(c.viscous)append_deviator(z,s.e_v);
 return z;
}
double dot(const Vector&a,const Vector&b){
 if(a.size()!=b.size())throw std::runtime_error("Dot dimension mismatch");
 double out=0;for(size_t i=0;i<a.size();++i)out+=a[i]*b[i];return out;
}
struct Step {Vector next;double integrand=0;};

// 'a' represents a dimensionless scalar control changing strain and thermal
// history. It is NOT yet a spherical-harmonic shape parameter.
Step evaluate(int n,double a,const Vector&z,Modulus mod,Controls c){
 if(n<1||n>steps)throw std::runtime_error("Invalid time step");
 const double phase=.36*n;
 ice3d::edv::Tensor eps{};
 eps[0]=1.30e-4*std::sin(phase)+a*2.0e-5*(.5+std::cos(phase));
 eps[1]=-0.50e-4*std::sin(phase)+a*(-7.0e-6);
 eps[2]=-0.35e-4*std::sin(phase)+a*3.0e-6;
 eps[3]=0.23e-4*std::cos(phase)+a*5.0e-6;
 eps[4]=-0.12e-4*std::sin(.7*phase)+a*2.0e-6;
 eps[5]=0.16e-4*std::cos(.8*phase)-a*4.0e-6;
 const double temp=250.0-2.3*std::sin(.22*n)+a*.75;
 const auto r=ice3d::edv::update(eps,temp,dt,unpack(z,c),mod,c);
 const Vector next=pack(r.new_state,c);
 const double sx=r.sigma[0]/stress_ref;
 const double sxy=r.sigma[3]/stress_ref;
 const double state_term=dot(next,next);
 // An original smooth, dimensionless history observable for this test only.
 const double g=(.23*sx+.12*sxy+.5*(sx*sx+sxy*sxy)
                +1.0e8*state_term)/steps;
 if(!std::isfinite(g))throw std::runtime_error("Nonfinite observable");
 return {next,g};
}
double forward(double a,Modulus mod,Controls c,std::vector<Vector>*saved){
 Vector z(state_size(c),0.);double J=0;
 if(saved){saved->clear();saved->push_back(z);}
 for(int n=1;n<=steps;++n){
  Step y=evaluate(n,a,z,mod,c);J+=y.integrand;z=std::move(y.next);
  if(saved)saved->push_back(z);
 }
 return J;
}
struct Result{double gradient=0;double J=0;};

// z_n=F_n(z_{n-1},a), J=sum_n g_n(z_{n-1},a).
// With p_N=0: p_{n-1}=g_{n,z} + F_{n,z}^T p_n,
// and dJ/da=sum_n (g_{n,a}+p_n^T F_{n,a}).
Result reverse(double a,Modulus mod,Controls c){
 std::vector<Vector>history;
 const double J=forward(a,mod,c,&history);
 const int dim=state_size(c);
 Vector p(dim,0.);double gradient=0;
 for(int n=steps;n>=1;--n){
  const Vector&z=history[n-1];
  constexpr double ha=1.0e-3;
  const Step ap=evaluate(n,a+ha,z,mod,c),am=evaluate(n,a-ha,z,mod,c);
  Vector dFda(dim,0.);
  for(int i=0;i<dim;++i)dFda[i]=(ap.next[i]-am.next[i])/(2*ha);
  gradient+=(ap.integrand-am.integrand)/(2*ha)+dot(p,dFda);
  Vector prev(dim,0.);
  for(int k=0;k<dim;++k){
   Vector zp=z,zm=z;
   const double h=k<5?1.0e-9:1.0e-10;
   zp[k]+=h;zm[k]-=h;
   const Step fplus=evaluate(n,a,zp,mod,c),fminus=evaluate(n,a,zm,mod,c);
   double back=0;
   for(int i=0;i<dim;++i)
    back+=p[i]*(fplus.next[i]-fminus.next[i])/(2*h);
   prev[k]=(fplus.integrand-fminus.integrand)/(2*h)+back;
  }
  p=std::move(prev);
 }
 if(!std::isfinite(gradient))throw std::runtime_error("Nonfinite reverse gradient");
 return {gradient,J};
}
} // namespace

int main(){try{
 int ok=0;
 for(const std::string law:{"E","ED","EDV"}){
  const Controls flags{law!="E",law=="EDV"};
  for(const Modulus mod:{Modulus::CONST,Modulus::VAR}){
   const double a=.037;
   const Result adj=reverse(a,mod,flags);
   // Two independently reevaluated complete trajectories, not local tangents.
   constexpr double h=5.0e-4;
   const double fd=(forward(a+h,mod,flags,nullptr)-
                    forward(a-h,mod,flags,nullptr))/(2*h);
   const double abserr=std::abs(adj.gradient-fd);
   const double rel=abserr/std::max(1e-10,std::abs(fd));
   if(rel>2.0e-4||abserr>1.0e-6)
    throw std::runtime_error("History reverse/FD mismatch: "+law+
                             " rel="+std::to_string(rel));
   std::cout<<std::setprecision(12)
            <<"P10A_CASE_OK law="<<law
            <<" mod="<<(mod==Modulus::CONST?"CONST":"VAR")
            <<" J="<<adj.J<<" adj="<<adj.gradient
            <<" FD="<<fd<<" abs_err="<<abserr
            <<" rel_err="<<rel<<" history_steps="<<steps<<"\n";
   ++ok;
  }
 }
 if(ok!=6)throw std::runtime_error("Missing model tests");
 std::cout<<"P10A_LOCAL_HISTORY_ADJOINT_OK models=6 steps=12 reverse_vs_full_history_FD\n";
 return 0;
}catch(const std::exception&e){
 std::cerr<<"P10A_LOCAL_HISTORY_ADJOINT_ERROR: "<<e.what()<<"\n";
 return 2;
}}
