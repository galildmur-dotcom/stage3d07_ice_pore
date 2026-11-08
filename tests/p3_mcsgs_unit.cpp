#include "p3_mcsgs.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif
using namespace std;
namespace p3=stage3d06::p3;
using Block=array<double,9>;

static Block invert(Block M){
 double A[3][6]{};
 for(int i=0;i<3;++i){for(int j=0;j<3;++j)A[i][j]=M[3*i+j];A[i][3+i]=1;}
 for(int k=0;k<3;++k){double pivot=A[k][k];if(!(pivot>0))throw runtime_error("block inverse pivot");
  for(double& x:A[k])x/=pivot;
  for(int i=0;i<3;++i)if(i!=k){const double m=A[i][k];for(int j=0;j<6;++j)A[i][j]-=m*A[k][j];}}
 Block X{};for(int i=0;i<3;++i)for(int j=0;j<3;++j)X[3*i+j]=A[i][3+j];return X;
}
struct System {
 int n=0;vector<int> row,col,diag;vector<Block> a,invd;
 vector<uint8_t> bc;p3::Coloring colors;
 void build(int nx,int ny,int nz){
  n=nx*ny*nz;row={0};bc.assign(3*n,0);diag.resize(n);
  auto idx=[&](int x,int y,int z){return x+nx*(y+ny*z);};
  for(int z=0;z<nz;++z)for(int y=0;y<ny;++y)for(int x=0;x<nx;++x){
   const int i=idx(x,y,z);vector<int> cols={i};
   for(auto [dx,dy,dz]:array<array<int,3>,6>{{{-1,0,0},{1,0,0},{0,-1,0},{0,1,0},{0,0,-1},{0,0,1}}}){
    int xx=x+dx,yy=y+dy,zz=z+dz;
    if(xx>=0&&xx<nx&&yy>=0&&yy<ny&&zz>=0&&zz<nz)cols.push_back(idx(xx,yy,zz));
   }
   sort(cols.begin(),cols.end());
   for(int j:cols){
    Block A{};
    if(j==i){A={4.2,0.10,0.03,0.10,4.5,0.05,0.03,0.05,4.8};diag[i]=int(col.size());}
    else {A={-0.43,0,0,0,-0.40,0,0,0,-0.38};}
    col.push_back(j);a.push_back(A);
   }row.push_back(int(col.size()));
   // Alternating partial BCs: every 19th node fixes x, every 31st fixes y,
   // all coordinates of node zero fixed.
   if(i%19==0)bc[3*i]=1;
   if(i%31==0)bc[3*i+1]=1;
  }
  bc[0]=bc[1]=bc[2]=1;
  for(int i=0;i<n;++i){auto D=a[diag[i]];
   for(int r=0;r<3;++r)if(bc[3*i+r]){
    for(int c=0;c<3;++c)D[3*r+c]=D[3*c+r]=0.0;
    D[3*r+r]=1.0;
   }invd.push_back(invert(D));
  }
  colors=p3::build_coloring(n,row,col);
 }
 // Two Tet10 elements sharing five vertices: each element makes a 10-vertex
 // clique, as in the actual FEM topology. Tests >2 graph colors and sharing.
 void build_tet10(){
  n=15;row={0};diag.assign(n,0);bc.assign(3*n,0);a.clear();col.clear();invd.clear();
  std::vector<std::vector<bool>> linked(n,std::vector<bool>(n,false));
  for(int shift: {0,5})for(int i=0;i<10;++i)for(int j=0;j<10;++j)
   linked[i+shift][j+shift]=true;
  for(int i=0;i<n;++i){
   for(int j=0;j<n;++j)if(linked[i][j]){
    Block B{};
    if(i==j){B={4.5,.07,.02,.07,4.7,.03,.02,.03,4.8};diag[i]=int(col.size());}
    else B={-.11,0,0,0,-.10,0,0,0,-.09};
    col.push_back(j);a.push_back(B);
   }
   row.push_back(int(col.size()));
  }
  bc[0]=bc[1]=bc[2]=1;bc[3*8+1]=1;bc[3*11+2]=1;
  for(int i=0;i<n;++i){Block D=a[diag[i]];
   for(int r=0;r<3;++r)if(bc[3*i+r]){
    for(int q=0;q<3;++q)D[3*r+q]=D[3*q+r]=0;
    D[3*r+r]=1;
   }
   invd.push_back(invert(D));
  }
  colors=p3::build_coloring(n,row,col);
 }
 void multiply(const vector<double>&x,vector<double>&y)const{
  y.assign(3*n,0);
  for(int i=0;i<n;++i)for(int p=row[i];p<row[i+1];++p){
   int j=col[p];for(int r=0;r<3;++r)if(!bc[3*i+r])
    for(int c=0;c<3;++c)if(!bc[3*j+c])y[3*i+r]+=a[p][3*r+c]*x[3*j+c];
  }
  for(int k=0;k<3*n;++k)if(bc[k])y[k]=x[k];
 }
 void precond(const vector<double>&b,vector<double>&x,bool mcsgs)const{
  if(mcsgs){p3::apply(colors,n,row,col,a,invd,diag,b,x,bc);return;}
  x.assign(3*n,0);
  for(int i=0;i<n;++i)for(int r=0;r<3;++r)if(!bc[3*i+r])
   for(int c=0;c<3;++c)x[3*i+r]+=invd[i][3*r+c]*(bc[3*i+c]?0:b[3*i+c]);
 }
};
static double dotp(const vector<double>&a,const vector<double>&b){double s=0;for(size_t k=0;k<a.size();++k)s+=a[k]*b[k];return s;}
static double normv(const vector<double>&v){return sqrt(dotp(v,v));}
static void require(bool ok,const string&desc){if(!ok)throw runtime_error(desc);}
struct Result{vector<double> x;int steps;double residual;};
static Result pcg(const System&A,const vector<double>&b,bool mc){
 vector<double>x(b.size(),0),r=b,z,p,Ap;
 A.precond(r,z,mc);p=z;double rz=dotp(r,z),bscale=normv(b);int it=0;
 for(;it<5000;++it){
  A.multiply(p,Ap);double den=dotp(p,Ap);require(den>0,"CG non-SPD step");
  const double alpha=rz/den;
  for(size_t k=0;k<x.size();++k){x[k]+=alpha*p[k];r[k]-=alpha*Ap[k];}
  if(normv(r)/bscale<1e-11){++it;break;}
  A.precond(r,z,mc);const double rz2=dotp(r,z);
  for(size_t k=0;k<x.size();++k)p[k]=z[k]+(rz2/rz)*p[k];
  rz=rz2;
 }
 A.multiply(x,Ap);for(size_t k=0;k<x.size();++k)Ap[k]-=b[k];
 return {move(x),it,normv(Ap)/bscale};
}
static void run_case(System& A){
 cout<<"P3 color graph nodes="<<A.n<<" blocks="<<A.a.size()<<" colors="<<A.colors.count()<<"\n";
 require(A.colors.count()>1,"coloring collapsed");
 vector<double> x(3*A.n),v(x.size());
 for(int i=0;i<int(x.size());++i){x[i]=sin(0.31*(i+1));v[i]=cos(0.117*(i+1));if(A.bc[i])x[i]=v[i]=0;}
 vector<double> px,pv;A.precond(x,px,true);A.precond(v,pv,true);
 vector<double> fast_x,fast_v;
 p3::apply_fast(A.colors,A.n,A.row,A.col,A.a,A.invd,A.diag,x,fast_x,A.bc);
 p3::apply_fast(A.colors,A.n,A.row,A.col,A.a,A.invd,A.diag,v,fast_v,A.bc);
 require(fast_x==px && fast_v==pv,"P3.1 indexed MC-SGS differs from reference");
 cout<<"PASS bitwise matching P3.1 preindexed/reference MC-SGS\n";
 #ifdef _OPENMP
 if(A.n>256){
  const int previous=omp_get_max_threads();
  omp_set_dynamic(0);omp_set_num_threads(1);
  vector<double> serial;A.precond(x,serial,true);
  omp_set_num_threads(4);
  vector<double> parallel;A.precond(x,parallel,true);
  omp_set_num_threads(previous);
  require(serial.size()==parallel.size(),"thread count changes dimensions");
  for(size_t k=0;k<serial.size();++k)
    require(serial[k]==parallel[k],"1-thread and 4-thread MC-SGS mismatch");
  cout<<"PASS 1-thread/4-thread bitwise equal preconditioner values\n";
 }
 #endif
 for(size_t i=0;i<x.size();++i)if(A.bc[i])require(px[i]==0&&pv[i]==0,"partial Dirichlet projection");
 const double sx=dotp(x,pv),sy=dotp(v,px);
 require(abs(sx-sy)<2e-11*max({1.0,abs(sx),abs(sy)}),"MC-SGS is not symmetric");
 require(dotp(x,px)>0.0,"MC-SGS is not positive definite");
 vector<double> b(x.size());for(int i=0;i<int(b.size());++i)b[i]=A.bc[i]?0:sin((i+1)*.297)+cos((i+2)*.053);
 auto jac=pcg(A,b,false),mc=pcg(A,b,true);
 cout<<setprecision(13)<<"jacobi_steps="<<jac.steps<<" mcsgs_steps="<<mc.steps
     <<" jacobi_residual="<<jac.residual<<" mcsgs_residual="<<mc.residual<<"\n";
 require(jac.residual<1.1e-11 && mc.residual<1.1e-11,"CG residual");
 vector<double> delta(jac.x.size());for(size_t i=0;i<delta.size();++i)delta[i]=jac.x[i]-mc.x[i];
 require(normv(delta)/max(1.0,normv(jac.x))<1e-9,"Jacobi/MC-SGS PCG solution mismatch");
 // Updated stiffness values with unchanged graph/coloring, simulating Newton steps.
 for(auto&blk:A.a)for(double&v:blk)v*=1.07;
 for(auto&iv:A.invd)for(double&v:iv)v/=1.07;
 A.precond(x,px,true);
 require(dotp(x,px)>0.0,"graph reuse after coefficient update");
 cout<<"PASS symmetry SPD partial-Dirichlet PCG numerical parity and graph reuse\n";
}
static void run(int nx,int ny,int nz){System A;A.build(nx,ny,nz);run_case(A);}
static void run_tet10(){System A;A.build_tet10();
 require(A.colors.count()>=10,"Tet10 clique requires at least 10 colors");run_case(A);}
int main(int argc,char**argv){try{
 string mode=argc>1?argv[1]:"--small";
 if(mode=="--small")run(4,4,4);
 else if(mode=="--parallel")run(12,12,4);
 else if(mode=="--tet10")run_tet10();
 else throw runtime_error("usage: --small | --parallel | --tet10");
 return 0;
 }catch(const exception&e){cerr<<"FAIL P3: "<<e.what()<<"\n";return 2;}
}
