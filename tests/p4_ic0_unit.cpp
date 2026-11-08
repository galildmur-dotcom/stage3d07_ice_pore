#include "p4_block_ic0.hpp"
#include <cmath>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>
using namespace stage3d06::p4;
struct TestMat{
 int n;std::vector<int> r,c;std::vector<B3>a;
 explicit TestMat(int nodes):n(nodes){r.push_back(0);
  for(int i=0;i<n;++i){for(int j=0;j<n;++j)if(std::abs(i-j)<=1){c.push_back(j);B3 b{};
   if(i==j){b={6.,.17,-.1, .17,5.1,.08, -.1,.08,4.6};}
   else{b={-.7,.03,0.,.03,-.65,.01,0.,.01,-.6};}
   a.push_back(b);
  }r.push_back((int)c.size());}
 }
 std::vector<double> mul(const std::vector<double>&v,const std::vector<uint8_t>&bc) const {
  std::vector<double>o(3*n,0);
  for(int i=0;i<n;++i)for(int p=r[i];p<r[i+1];++p)for(int a0=0;a0<3;++a0)for(int b0=0;b0<3;++b0){int ii=3*i+a0,jj=3*c[p]+b0;
   if(!bc[ii]&&!bc[jj])o[ii]+=a[p][3*a0+b0]*v[jj];}
  for(int i=0;i<3*n;++i)if(bc[i])o[i]=v[i];
  return o;
 }
};
static double dot(const std::vector<double>&a,const std::vector<double>&b){double s=0;for(size_t i=0;i<a.size();++i)s+=a[i]*b[i];return s;}
static double err(const std::vector<double>&a,const std::vector<double>&b){double s=0;for(size_t i=0;i<a.size();++i)s=std::max(s,std::abs(a[i]-b[i]));return s;}
static void need(bool p,const char*m){if(!p)throw std::runtime_error(m);}
int main(int argc,char**argv){try{
 std::string mode=argc>1?argv[1]:"--exact";
 if(mode=="--breakdown"){
  TestMat t(4);for(auto&x:t.a)x={};std::vector<uint8_t> bc(12,0);BlockIC0 ic;
  bool caught=false;try{ic.setup(t.n,t.r,t.c,t.a,bc);}catch(const std::runtime_error&){caught=true;}
  need(caught,"zero pivot was not rejected");std::cout<<"PASS IC0 rejects non-SPD matrix\n";return 0;
 }
 TestMat t(mode=="--mixed"?42:9);std::vector<uint8_t>bc(3*t.n,0);
 if(mode=="--mixed"){
  for(int i=0;i<t.n;++i){if(i%6==0)bc[3*i]=1;if(i%11==0)bc[3*i+2]=1;}
 }
 BlockIC0 ic;ic.setup(t.n,t.r,t.c,t.a,bc);
 std::vector<double>x(3*t.n),z,p;
 for(int i=0;i<3*t.n;++i)x[i]=bc[i]?0.:std::sin(.6*i)+std::cos(.17*i);
 auto rhs=t.mul(x,bc);ic.apply(rhs,z,bc);
 double e=err(x,z);need(e<2e-13,"IC0 must exactly factor tridiagonal 3x3 block SPD operator");
 for(int i=0;i<3*t.n;++i)need(!bc[i]||z[i]==0,"constrained component is nonzero");
 std::vector<double>v(3*t.n);for(int i=0;i<3*t.n;++i)v[i]=bc[i]?0.:std::sin(i*.3+1.);
 ic.apply(v,p,bc);std::vector<double>q;ic.apply(x,q,bc);
 need(dot(x,q)>0 && dot(v,p)>0,"IC0 inverse not positive definite");
 double symmetry=std::abs(dot(x,p)-dot(v,q));
 need(symmetry<3e-12*std::max({1.,std::abs(dot(x,p)),std::abs(dot(v,q))}),"IC0 inverse not symmetric");
 std::cout<<"PASS "<<mode<<" nodes="<<t.n<<" matrix_extraction_error="<<e<<" symmetry="<<symmetry<<" intersections="<<ic.intersections<<"\n";
 return 0;
 }catch(const std::exception&e){std::cerr<<"P4 unit FAIL: "<<e.what()<<"\n";return 2;}
}
