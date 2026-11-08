#include "p5_schwarz.hpp"
#include <cmath>
#include <iostream>
#include <numeric>
#include <string>
using namespace stage3d06::p5;
struct Data {
 int n;
 std::vector<int> row,col;
 std::vector<B3> a;
 std::vector<uint8_t> bc;
};
Data make_data(int n=125){
 Data d;d.n=n;d.row.assign(n+1,0);d.bc.assign(3*n,0);
 const int nx=5,ny=5;
 for(int i=0;i<n;++i){
  std::vector<int> neigh{i};
  if(i%nx)neigh.push_back(i-1);
  if(i%nx<nx-1 && i+1<n)neigh.push_back(i+1);
  if((i/nx)%ny)neigh.push_back(i-nx);
  if((i/nx)%ny<ny-1 && i+nx<n)neigh.push_back(i+nx);
  if(i>=nx*ny)neigh.push_back(i-nx*ny);
  if(i+nx*ny<n)neigh.push_back(i+nx*ny);
  std::sort(neigh.begin(),neigh.end());neigh.erase(std::unique(neigh.begin(),neigh.end()),neigh.end());
  for(int j:neigh){
   B3 a{};
   if(i==j){for(int k=0;k<3;++k)a[3*k+k]=4.+neigh.size()+k*.25;
    a[1]=a[3]=.11;a[2]=a[6]=.07;a[5]=a[7]=.13;
   }else{for(int k=0;k<3;++k)a[3*k+k]=-.55; a[1]=a[3]=-.03;}
   d.col.push_back(j);d.a.push_back(a);
  }
  d.row[i+1]=int(d.col.size());
 }
 d.bc[0]=1;d.bc[8]=1;d.bc[3*(n-1)+2]=1;
 return d;
}
void demand(bool flag,const char*msg){if(!flag)throw std::runtime_error(msg);}
double dot(const std::vector<double>&a,const std::vector<double>&b){double z=0;for(size_t i=0;i<a.size();++i)z+=a[i]*b[i];return z;}
double relative(const std::vector<double>&a,const std::vector<double>&b){double err=0,norm=0;for(size_t i=0;i<a.size();++i){err+=(a[i]-b[i])*(a[i]-b[i]);norm+=a[i]*a[i];}return std::sqrt(err)/std::max(std::sqrt(norm),1e-30);}
void mul(const Data&d,const std::vector<double>&x,std::vector<double>&out){
 out.assign(x.size(),0);
 for(int i=0;i<d.n;++i)for(int p=d.row[i];p<d.row[i+1];++p)
  for(int k=0;k<3;++k)for(int l=0;l<3;++l)if(!d.bc[3*i+k]&&!d.bc[3*d.col[p]+l])out[3*i+k]+=d.a[p][3*k+l]*x[3*d.col[p]+l];
 for(size_t i=0;i<x.size();++i)if(d.bc[i])out[i]=x[i];
}
std::vector<double> vec(const Data&d,int version){
 std::vector<double> v(3*d.n);for(int i=0;i<3*d.n;++i)v[i]=d.bc[i]?0:(.05*std::sin(.22*i+version)+.2*std::cos(.11*i+.7*version));return v;
}
int cg(const Data&d,Schwarz &P,const std::vector<double>&rhs,std::vector<double>&x){
 std::vector<double> r=rhs,z,p,Ap;x.assign(rhs.size(),0);P.apply(r,z,d.bc);p=z;double rz=dot(r,z),norm=std::sqrt(dot(rhs,rhs));
 for(int it=0;it<250;++it){mul(d,p,Ap);const double alpha=rz/dot(p,Ap);
  for(size_t i=0;i<r.size();++i){x[i]+=alpha*p[i];r[i]-=alpha*Ap[i];}
  if(std::sqrt(dot(r,r))<norm*1e-10)return it+1;
  P.apply(r,z,d.bc);double nr=dot(r,z),beta=nr/rz;rz=nr;
  for(size_t i=0;i<p.size();++i)p[i]=z[i]+beta*p[i];
 }
 throw std::runtime_error("P5 CG did not converge on synthetic SPD system");
}
void test_partition(){auto a=make_data();auto p0=partition(a.n,a.row,a.col,12,0),p1=partition(a.n,a.row,a.col,12,1);
 demand(p0.local.size()==p1.local.size(),"AS0 and AS1 core partition differs");
 std::vector<int>cover(a.n,0);
 for(size_t j=0;j<p0.local.size();++j){const auto&l=p0.local[j];
  for(int i:l.nodes)++cover[i];
  for(int i:l.nodes)demand(std::binary_search(p1.local[j].nodes.begin(),p1.local[j].nodes.end(),i),"AS1 loses core vertex");
  for(size_t k=0;k<l.col.size();++k){int src=l.source[k];demand(a.col[src]==l.nodes[l.col[k]],"Local BCSR wrong index");}
 }
 demand(std::all_of(cover.begin(),cover.end(),[](int k){return k==1;}),"AS0 is not disjoint");
 demand(p1.totalMembers>p0.totalMembers,"AS1 missing overlap");
 for(int i=0;i<a.n;++i)demand(p0.gatherRow[i+1]-p0.gatherRow[i]==1,"AS0 gather coverage");
 std::cout<<"partition: "<<p0.local.size()<<" domains, AS0 members="<<p0.totalMembers<<" AS1="<<p1.totalMembers<<"\n";
}
void test_spd(){auto d=make_data();auto x=vec(d,1),y=vec(d,2);
 for(int overlap:{0,1}){Schwarz P;P.setup(d.n,d.row,d.col,d.a,d.bc,12,overlap);
  std::vector<double>Px,Py;P.apply(x,Px,d.bc);P.apply(y,Py,d.bc);
  double symmetry=std::abs(dot(x,Py)-dot(y,Px))/std::max(1.,std::abs(dot(x,Py)));
  demand(symmetry<2e-12,"Schwarz operator not symmetric");
  demand(dot(x,Px)>1e-9,"Schwarz not SPD");
  for(int i=0;i<3*d.n;++i)if(d.bc[i])demand(Px[i]==0,"Fixed DOF not projected");
  std::cout<<"AS"<<overlap<<" symmetric rel="<<symmetry<<" positive="<<dot(x,Px)<<"\n";
 }
}
void test_threads(){auto d=make_data(200);auto x=vec(d,3);
 for(int overlap:{0,1}){Schwarz P;P.setup(d.n,d.row,d.col,d.a,d.bc,12,overlap);
  std::vector<double>reference,parallel;
  #ifdef _OPENMP
  omp_set_dynamic(0);omp_set_num_threads(1);
  #endif
  P.apply(x,reference,d.bc);
  #ifdef _OPENMP
  omp_set_num_threads(4);
  #endif
  P.apply(x,parallel,d.bc);
  demand(reference==parallel,"OpenMP changes deterministic Schwarz gather result");
 }
}
void test_regression(){auto d=make_data();auto x=vec(d,2);std::vector<double>b;mul(d,x,b);
 for(int overlap:{0,1}){Schwarz P;P.setup(d.n,d.row,d.col,d.a,d.bc,12,overlap);
  std::vector<double>found,Ax;int its=cg(d,P,b,found);mul(d,found,Ax);
  double err=relative(x,found),res=relative(b,Ax);
  demand(err<2e-9&&res<1e-9,"Schwarz PCG solution not equivalent");
  std::cout<<"AS"<<overlap<<" PCG iterations="<<its<<" relative x error="<<err<<" residual="<<res<<"\n";
 }
}
int main(int argc,char**argv){try{
 std::string mode=argc>1?argv[1]:"--all";
 if(mode=="--partition"||mode=="--all")test_partition();
 if(mode=="--symmetric"||mode=="--mixed_spd"||mode=="--all")test_spd();
 if(mode=="--threads"||mode=="--all")test_threads();
 if(mode=="--regression"||mode=="--all")test_regression();
 std::cout<<"P5 "<<mode<<" PASS\n";return 0;
 }catch(const std::exception&e){std::cerr<<"P5 FAIL "<<e.what()<<"\n";return 2;}}
