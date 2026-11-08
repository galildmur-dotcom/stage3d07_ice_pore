// Stage3D02. 3D Tet10 backward-Euler transient heat equation, Robin on TOP only.
// SI units, nodal unknown theta=T(K)-253.15(K), xi frozen within each trajectory.
// Library-free CSR matrix / Jacobi-PCG, Gmsh ASCII 2.2 curved Tet10/Tri6.
#define STAGE3D01_LIBRARY
#include "geometry_stage3d01.cpp"
#include "p09e_temperature_io.hpp"
#include <chrono>
#include <limits>
#include <cctype>
using Clock=chrono::steady_clock;
constexpr double rho=920.3, cp=1960., kice=2.40, robin_h=24., T0=253.15;
constexpr double tc=300., Delta=3., sig=0.48, H=.05, alpha=kice/(rho*cp);
struct Imported {Mesh mesh;vector<Face> internal;};
Imported read_msh(const fs::path& file,bool slab=false){
  ifstream f(file);if(!f)throw runtime_error("Cannot read "+file.string());
  Imported a;Mesh&m=a.mesh;m.center={0,0,.03};m.radius=.001;
  unordered_map<int,int> ids;string s;
  while(f>>s){
    if(s=="$MeshFormat"){string ver;int binary,sz;f>>ver>>binary>>sz;if(ver!="2.2"||binary)throw runtime_error("Expected ASCII Gmsh MSH 2.2");}
    else if(s=="$Nodes"){int n;f>>n;m.nodes.resize(n);ids.reserve(2*n);
      for(int i=0;i<n;++i){int id;f>>id>>m.nodes[i].x>>m.nodes[i].y>>m.nodes[i].z;ids.emplace(id,i);}}
    else if(s=="$Elements"){int nel;f>>nel;
      for(int e=0;e<nel;++e){int id,type,nt;f>>id>>type>>nt;vector<int> tags(nt);
        for(int&x:tags)f>>x;if(tags.empty())throw runtime_error("Missing physical tag");
        if(type==11){if(tags[0]!=1)throw runtime_error("Non-ice Tet10");Tet t;
          for(int&v:t){int idn;f>>idn;v=ids.at(idn);}swap(t[8],t[9]);m.tets.push_back(t);}
        else if(type==9){Face q;q.tag=tags[0];for(int&v:q.nodes){int idn;f>>idn;v=ids.at(idn);}if(q.tag==9)a.internal.push_back(q);else m.faces.push_back(q);}
        else throw runtime_error("Unexpected Gmsh element type "+to_string(type));
      }}
  }
  if(m.nodes.empty()||m.tets.empty()||m.faces.empty()||(!slab&&a.internal.empty()))throw runtime_error("Incomplete mesh or absent B6 interface");
  array<int,10> ct{};for(auto&face:m.faces){if(face.tag<2||face.tag>8)throw runtime_error("Unknown thermal face tag");ct[face.tag]++;}for(int j=2;j<=(slab?7:8);++j)if(!ct[j])throw runtime_error("Missing surface tag");
  return a;
}
struct CSR {
  int n=0;vector<int> offsets,cols;vector<double> mass,conduct,mat,diag,capacity,robinload;
  static uint64_t pack(int i,int j){return (uint64_t(uint32_t(i))<<32)|uint32_t(j);}
  void pattern(const Mesh&m){
    n=(int)m.nodes.size();vector<uint64_t> pairs;pairs.reserve(m.tets.size()*100 + m.faces.size()*36/3);
    for(auto&t:m.tets)for(int i:t)for(int j:t)pairs.push_back(pack(i,j));
    for(auto&q:m.faces)if(q.tag==2)for(int i:q.nodes)for(int j:q.nodes)pairs.push_back(pack(i,j));
    sort(pairs.begin(),pairs.end());pairs.erase(unique(pairs.begin(),pairs.end()),pairs.end());
    offsets.assign(n+1,0);cols.reserve(pairs.size());
    for(auto code:pairs){int i=int(code>>32),j=int(code&0xffffffffu);offsets[i+1]++;cols.push_back(j);}
    for(int i=0;i<n;++i)offsets[i+1]+=offsets[i];
    mass.assign(pairs.size(),0);conduct.assign(pairs.size(),0);mat.assign(pairs.size(),0);
    capacity.assign(n,0);robinload.assign(n,0);diag.assign(n,0);
  }
  inline int index(int i,int j)const {
    auto lo=cols.begin()+offsets[i],hi=cols.begin()+offsets[i+1];auto it=lower_bound(lo,hi,j);
    if(it==hi||*it!=j)throw runtime_error("Missing CSR entry");return int(it-cols.begin());
  }
  void rebuild(double dt){for(size_t i=0;i<mat.size();++i)mat[i]=mass[i]+dt*conduct[i];for(int i=0;i<n;++i){diag[i]=mat[index(i,i)];if(diag[i]<=0)throw runtime_error("Non-positive diagonal");}}
  void mul(const vector<double>& a,const vector<double>&v,vector<double>&out)const{
    fill(out.begin(),out.end(),0);for(int i=0;i<n;++i){double s=0;for(int t=offsets[i];t<offsets[i+1];++t)s+=a[t]*v[cols[t]];out[i]=s;}
  }
};
struct Q {double w;array<double,10> N;array<array<double,3>,10> d;};
vector<Q> tetra_q(){vector<Q> out;out.reserve(64);for(auto a:g4)for(auto b:g4)for(auto c:g4){double r=a.x,s=(1-r)*b.x,t=(1-r)*(1-b.x)*c.x;Q q;tetshape(r,s,t,q.N,q.d);q.w=a.w*b.w*c.w*(1-r)*(1-r)*(1-b.x);out.push_back(q);}return out;}
array<double,6> triN(double r,double s){double L[]={1-r-s,r,s};array<double,6>N;
  for(int i=0;i<3;++i)N[i]=L[i]*(2*L[i]-1);
  N[3]=4*L[0]*L[1];N[4]=4*L[1]*L[2];N[5]=4*L[2]*L[0];return N;
}
struct Assembly {CSR csr;double volume=0,area=0,minDet=1e100,maxKones=0;};
Assembly assemble(const Mesh&m){
  Assembly a;CSR& A=a.csr;A.pattern(m);const auto qs=tetra_q();
  for(auto&t:m.tets){double me[10][10]{},ke[10][10]{};
    for(const auto&q:qs){
      V dr{},ds{},dt{};for(int i=0;i<10;++i){auto p=m.nodes[t[i]];dr=dr+p*q.d[i][0];ds=ds+p*q.d[i][1];dt=dt+p*q.d[i][2];}
      V aa=cross(ds,dt),bb=cross(dt,dr),cc=cross(dr,ds);double jac=dot(dr,aa);
      if(!(jac>0))throw runtime_error("Negative isoparametric detJ");a.minDet=min(a.minDet,jac);double w=q.w*jac;a.volume+=w;
      V grad[10];for(int i=0;i<10;++i)grad[i]=(aa*q.d[i][0]+bb*q.d[i][1]+cc*q.d[i][2])/jac;
      for(int i=0;i<10;++i)for(int j=0;j<10;++j){me[i][j]+=rho*cp*w*q.N[i]*q.N[j];ke[i][j]+=kice*w*dot(grad[i],grad[j]);}
    }
    for(int i=0;i<10;++i)for(int j=0;j<10;++j){int id=A.index(t[i],t[j]);A.mass[id]+=me[i][j];A.conduct[id]+=ke[i][j];}
  }
  for(auto&face:m.faces)if(face.tag==2){double re[6][6]{},be[6]{};
    for(auto x:g4)for(auto y:g4){double r=x.x,s=(1-r)*y.x;Surf b=seval(m,face.nodes,r,s);
      double w=x.w*y.w*(1-r)*norm(cross(b.du,b.dv));a.area+=w;auto N=triN(r,s);
      for(int i=0;i<6;++i){be[i]+=robin_h*w*N[i];for(int j=0;j<6;++j)re[i][j]+=robin_h*w*N[i]*N[j];}
    }
    for(int i=0;i<6;++i){A.robinload[face.nodes[i]]+=be[i];for(int j=0;j<6;++j)A.conduct[A.index(face.nodes[i],face.nodes[j])]+=re[i][j];}
  }
  for(int i=0;i<A.n;++i)for(int p=A.offsets[i];p<A.offsets[i+1];++p)A.capacity[i]+=A.mass[p];
  // Exact partition of unity for stiffness and Robin matrix, even with isoparametric curvature.
  for(int i=0;i<A.n;++i){double sum=0;for(int p=A.offsets[i];p<A.offsets[i+1];++p)sum+=A.conduct[p];a.maxKones=max(a.maxKones,abs(sum-A.robinload[i]));}
  return a;
}
static inline double sp(const vector<double>&a,const vector<double>&b){double z=0;for(size_t i=0;i<a.size();++i)z+=a[i]*b[i];return z;}
struct CGResult{int iterations;double relative;};
CGResult pcg(const CSR&A,const vector<double>&rhs,vector<double>&x,double tol=5e-11,int maxiter=4000){
  int n=A.n;vector<double> r(n),p(n),z(n),Ap(n);A.mul(A.mat,x,Ap);
  for(int i=0;i<n;++i){r[i]=rhs[i]-Ap[i];z[i]=r[i]/A.diag[i];p[i]=z[i];}
  double r0=sqrt(sp(rhs,rhs)),rr=sqrt(sp(r,r));if(r0<1e-28)return{0,0};if(rr<tol*r0)return{0,rr/r0};
  double rz=sp(r,z);int it=0;
  for(;it<maxiter;++it){A.mul(A.mat,p,Ap);double pp=sp(p,Ap);if(pp<=0||!isfinite(pp))throw runtime_error("PCG not SPD");double step=rz/pp;
    for(int i=0;i<n;++i){x[i]+=step*p[i];r[i]-=step*Ap[i];}
    if((it%10)==0 || it+1==maxiter){rr=sqrt(sp(r,r));if(rr<tol*r0)break;}
    for(int i=0;i<n;++i)z[i]=r[i]/A.diag[i];double rz2=sp(r,z),beta=rz2/rz;for(int i=0;i<n;++i)p[i]=z[i]+beta*p[i];rz=rz2;
  }
  A.mul(A.mat,x,Ap);for(int i=0;i<n;++i)Ap[i]=rhs[i]-Ap[i];rr=sqrt(sp(Ap,Ap));
  return{it+1,rr/r0};
}
// 1D no-pore slab: z=0 insulated, z=H Robin, ambient constant-in-space.
// Eigenvalues lambda*tan(lambda)=Bi, eigenvectors cos(lambda z/H).
double bisect_lambda(int n,double Bi){double lo=n*PI+1e-13,hi=(n+.5)*PI-1e-13;
  for(int k=0;k<70;++k){double mid=.5*(lo+hi);if(mid*tan(mid)>Bi)hi=mid;else lo=mid;}return .5*(lo+hi);
}
double analytic_1d(double z,double t,double xi=0,int modes=250){
  if(t<=0)return 0;double e=exp(-t/tc),sum=0,step=0,Bi=robin_h*H/kice;
  for(int n=0;n<modes;++n){double l=bisect_lambda(n,Bi);
    double beta=alpha*(l/H)*(l/H),denom=.5+sin(2*l)/(4*l),an=(sin(l)/l)/denom;
    double q=an*cos(l*z/H),bb=beta-1/tc;
    double part=abs(bb)<1e-12?(t/tc)*exp(-beta*t):(e-exp(-beta*t))/(tc*bb);
    sum+=q*part;step+=q*exp(-beta*t);
  }
  return -Delta*(1-e)+Delta*sum+sig*xi*(1-step);
}
struct Test1D {int nz;double dt,linf,rms,exact_surface,fe_surface;};
Test1D solve_1d(int nz,double dt){
  int n=nz+1,steps=llround(3600/dt);if(abs(steps*dt-3600)>1e-9)throw runtime_error("Bad 1D dt");double dz=H/nz;
  vector<double> md(n,0),mo(n-1,0),kd(n,0),ko(n-1,0),a(n),b(n-1),t(n,0),rhs(n),c(n-1),d(n);
  for(int i=0;i<nz;++i){double mm=rho*cp*dz/6,kk=kice/dz;md[i]+=2*mm;md[i+1]+=2*mm;mo[i]+=mm;kd[i]+=kk;kd[i+1]+=kk;ko[i]-=kk;}
  kd.back()+=robin_h;
  for(int i=0;i<n;++i)a[i]=md[i]+dt*kd[i];for(int i=0;i<n-1;++i)b[i]=mo[i]+dt*ko[i];
  for(int s=1;s<=steps;++s){double time=s*dt,amb=-Delta*(-expm1(-time/tc));
    for(int i=0;i<n;++i)rhs[i]=md[i]*t[i]+(i?mo[i-1]*t[i-1]:0)+(i<n-1?mo[i]*t[i+1]:0);
    rhs.back()+=dt*robin_h*amb;
    c[0]=b[0]/a[0];d[0]=rhs[0]/a[0];
    for(int i=1;i<n;++i){double z=a[i]-b[i-1]*c[i-1];if(i<n-1)c[i]=b[i]/z;d[i]=(rhs[i]-b[i-1]*d[i-1])/z;}
    t[n-1]=d[n-1];for(int i=n-2;i>=0;--i)t[i]=d[i]-c[i]*t[i+1];
  }
  double maxe=0,sq=0;for(int i=0;i<n;++i){double e=t[i]-analytic_1d(i*dz,3600);maxe=max(maxe,abs(e));sq+=e*e;}
  return{nz,dt,maxe,sqrt(sq/n),analytic_1d(H,3600),t.back()};
}
int write_1d(const fs::path& path){fs::create_directories(path.parent_path());ofstream f(path);if(!f)throw runtime_error("1D file cannot open");f<<setprecision(15)<<"nz,dt_s,Linf_K,RMS_K,analytic_top_dT_K,fe_top_dT_K\n";
  double previous=1e100;
  for(auto [n,dt]:vector<pair<int,double>>{{50,300},{100,150},{200,75},{400,37.5}}){auto a=solve_1d(n,dt);f<<a.nz<<","<<a.dt<<","<<a.linf<<","<<a.rms<<","<<a.exact_surface<<","<<a.fe_surface<<"\n";cout<<"1D nz="<<n<<" dt="<<dt<<" error="<<a.linf<<" K\n";
    if(a.linf>=previous)throw runtime_error("1D analytic benchmark error did not decrease");previous=a.linf;}
  if(previous>=.002)throw runtime_error("1D analytical benchmark tolerance not satisfied");return 0;
}
void save_vtu(const Mesh&m,const vector<double>&u,double time,fs::path out){fs::create_directories(out.parent_path());ofstream f(out);if(!f)throw runtime_error("Cannot create "+out.string());
  f<<setprecision(12)<<"<?xml version=\"1.0\"?><VTKFile type=\"UnstructuredGrid\" version=\"0.1\" byte_order=\"LittleEndian\"><UnstructuredGrid><Piece NumberOfPoints=\""<<m.nodes.size()<<"\" NumberOfCells=\""<<m.tets.size()<<"\">\n";
  f<<"<FieldData><DataArray type=\"Float64\" Name=\"TIME\" NumberOfTuples=\"1\" format=\"ascii\">"<<time<<"</DataArray></FieldData>\n";
  f<<"<Points><DataArray type=\"Float64\" NumberOfComponents=\"3\" format=\"ascii\">\n";
  for(auto v:m.nodes)f<<v.x<<" "<<v.y<<" "<<v.z<<"\n";f<<"</DataArray></Points><Cells><DataArray type=\"Int32\" Name=\"connectivity\" format=\"ascii\">\n";
  for(auto t:m.tets){for(int v:t)f<<v<<" ";f<<"\n";}f<<"</DataArray><DataArray type=\"Int64\" Name=\"offsets\" format=\"ascii\">\n";
  for(size_t i=1;i<=m.tets.size();++i)f<<10*i<<" ";f<<"</DataArray><DataArray type=\"UInt8\" Name=\"types\" format=\"ascii\">\n";
  for(size_t i=0;i<m.tets.size();++i)f<<"24 ";f<<"</DataArray></Cells><PointData Scalars=\"Temperature_C\">\n";
  f<<"<DataArray type=\"Float64\" Name=\"Temperature_C\" format=\"ascii\">\n";for(auto x:u)f<<x-20<<" ";f<<"</DataArray>\n";
  f<<"<DataArray type=\"Float64\" Name=\"Temperature_K\" format=\"ascii\">\n";for(auto x:u)f<<T0+x<<" ";f<<"</DataArray>\n";
  f<<"<DataArray type=\"Float64\" Name=\"dT_K\" format=\"ascii\">\n";for(auto x:u)f<<x<<" ";f<<"</DataArray>\n";
  f<<"</PointData></Piece></UnstructuredGrid></VTKFile>\n";
}
int near_node(const Mesh&m,V target){int best=0;double mind=1e99;for(int i=0;i<(int)m.nodes.size();++i){double ds=norm(m.nodes[i]-target);if(ds<mind){mind=ds;best=i;}}return best;}
struct RunConfig{fs::path mesh,out;double dt=300,tend=3600,xi=0;bool testUniform=false,novtu=false,slab=false,checkAnalytic=false,everyStep=false,compact=false;};
int run(const RunConfig&cfg){auto tic=Clock::now();auto imp=read_msh(cfg.mesh,cfg.slab);auto &m=imp.mesh;
  cout<<"Reading "<<cfg.mesh.filename()<<" n="<<m.nodes.size()<<" tets="<<m.tets.size()<<"\n"<<flush;
  auto aa=assemble(m);auto&A=aa.csr;
  cout<<"Assembly nnz="<<A.mat.size()<<" min det="<<aa.minDet<<" volume="<<aa.volume<<" top_area="<<aa.area<<" K1 mismatch="<<aa.maxKones<<"\n"<<flush;
  if(aa.maxKones>1e-7 || abs(aa.area-.0036)>1e-8)throw runtime_error("Stiffness partition / Robin area check failed");
  int nsteps=llround(cfg.tend/cfg.dt);if(abs(nsteps*cfg.dt-cfg.tend)>1e-8)throw runtime_error("tend not divisible by dt");A.rebuild(cfg.dt);
  fs::create_directories(cfg.out);ofstream times(cfg.out/"time_series.csv");times<<setprecision(16)<<"time_s,xi,ambient_C,volume_mean_C,top_mean_C,min_C,max_C,energy_J,energy_balance_J,energy_balance_rel,solver_iterations,solver_residual_rel,far_node_z_m,far_node_C,slab_1D_at_far_C,far_minus_1D_K,pore_near_node_C,corner_top_C,corner_bottom_C,corner_top_minus_1D_K,corner_bottom_minus_1D_K\n";
  auto far=near_node(m,{.022,.022,.03});auto near=near_node(m,{.0012,0,.03});
  auto cornerTop=near_node(m,{.03,.03,.05});auto cornerBottom=near_node(m,{.03,.03,0.});
  if(norm(m.nodes[cornerTop]-V{.03,.03,.05})>1e-9 || norm(m.nodes[cornerBottom]-V{.03,.03,0.})>1e-9)throw runtime_error("Fixed corner probes are missing");
  vector<double>theta(A.n,cfg.testUniform?1.:0.),rhs(A.n),z(A.n),oldmass(A.n);double prev_energy=sp(A.capacity,theta);
  double max_balance=0,max_rr=0,mincgit=1e9,maxcgit=0,uniformerr=0;
  for(int step=1;step<=nsteps;++step){double time=cfg.dt*step,amb=cfg.testUniform?1.:(-Delta*(-expm1(-time/tc))+sig*cfg.xi);
    A.mul(A.mass,theta,rhs);for(int i=0;i<A.n;++i)rhs[i]+=cfg.dt*A.robinload[i]*amb;
    auto r=pcg(A,rhs,theta);if(r.relative>5e-9)throw runtime_error("PCG residual too large "+to_string(r.relative));
    double energy=sp(A.capacity,theta),flux=sp(A.robinload,theta)-amb*accumulate(A.robinload.begin(),A.robinload.end(),0.);
    double balance=(energy-prev_energy)+cfg.dt*flux;
    double abs_scale=max({abs(energy-prev_energy),abs(cfg.dt*flux),1e-12});double rel=abs(balance)/abs_scale;
    if(rel>1e-6)throw runtime_error("Energy balance not satisfied: "+to_string(rel));
    double top_mean=sp(A.robinload,theta)/(robin_h*aa.area);
    auto [mni,mxi]=minmax_element(theta.begin(),theta.end());
    if(cfg.testUniform){uniformerr=max(uniformerr,max(abs(*mni-1),abs(*mxi-1)));if(uniformerr>1e-6)throw runtime_error("Uniform field not reproduced");}
    double zfar=m.nodes[far].z,far_ref=analytic_1d(zfar,time,cfg.xi);
    times<<time<<","<<cfg.xi<<","<<T0-273.15+amb<<","<<T0-273.15+energy/(rho*cp*aa.volume)<<","<<T0-273.15+top_mean<<","<<T0-273.15+*mni<<","<<T0-273.15+*mxi<<","<<energy<<","<<balance<<","<<rel<<","<<r.iterations<<","<<r.relative<<","<<zfar<<","<<T0-273.15+theta[far]<<","<<-20+far_ref<<","<<theta[far]-far_ref<<","<<T0-273.15+theta[near]<<","<<T0-273.15+theta[cornerTop]<<","<<T0-273.15+theta[cornerBottom]<<","<<theta[cornerTop]-analytic_1d(.05,time,cfg.xi)<<","<<theta[cornerBottom]-analytic_1d(0,time,cfg.xi)<<"\n";
    prev_energy=energy;max_balance=max(max_balance,rel);max_rr=max(max_rr,r.relative);mincgit=min(mincgit,double(r.iterations));maxcgit=max(maxcgit,double(r.iterations));
    if(cfg.compact){
      ice3d::p09e::write(cfg.out/("thermal_"+std::to_string(int(time))+"s.p09e"),m,theta,int(time));
    }
    if(!cfg.compact&&!cfg.novtu&&(cfg.everyStep||step==nsteps|| (abs(time-900)<1e-9)||abs(time-1800)<1e-9)){
      ostringstream name;name<<"thermal_"<<int(time)<<"s.vtu";save_vtu(m,theta,time,cfg.out/name.str());}
    if(step==1||step%4==0||step==nsteps)cout<<"step="<<step<<"/"<<nsteps<<" t="<<time<<" top="<<top_mean<<" avg="<<energy/(rho*cp*aa.volume)<<" balance_rel="<<rel<<" CG="<<r.iterations<<"\n"<<flush;
  }
  if(cfg.checkAnalytic){
    if(!cfg.slab||cfg.testUniform||cfg.xi!=0)throw runtime_error("Analytic 3D slab benchmark requires --slab and xi=0");
    double linf=0,rmse=0;for(int i=0;i<A.n;++i){double ex=analytic_1d(m.nodes[i].z,cfg.tend);double err=theta[i]-ex;linf=max(linf,abs(err));rmse+=err*err;}
    rmse=sqrt(rmse/A.n);ofstream bmk(cfg.out/"slab_3D_vs_analytic.csv");
    bmk<<setprecision(16)<<"nodes,tet10,dt_s,tend_s,Linf_K,RMS_K,top_mean_C\n"<<A.n<<","<<m.tets.size()<<","<<cfg.dt<<","<<cfg.tend<<","<<linf<<","<<rmse<<","<<(-20+sp(A.robinload,theta)/(robin_h*aa.area))<<"\n";
    cout<<"3D slab vs exact analytical 1D: Linf="<<linf<<" RMS="<<rmse<<" K\n";
    if(linf>0.012)throw runtime_error("3D slab exact 1D check too inaccurate");
  }
  auto runtime=chrono::duration<double>(Clock::now()-tic).count();ofstream sm(cfg.out/"summary.csv");sm<<setprecision(16)<<"mesh,nodes,tet10,nnz,dt_s,t_end_s,xi,volume_m3,top_area_m2,min_detJ_m3,max_stiffness_partition_error,max_energy_balance_rel,max_pcg_residual_rel,max_pcg_iterations,uniform_err_K,wall_seconds\n";
  sm<<cfg.mesh.filename().string()<<","<<m.nodes.size()<<","<<m.tets.size()<<","<<A.mat.size()<<","<<cfg.dt<<","<<cfg.tend<<","<<cfg.xi<<","<<aa.volume<<","<<aa.area<<","<<aa.minDet<<","<<aa.maxKones<<","<<max_balance<<","<<max_rr<<","<<maxcgit<<","<<uniformerr<<","<<runtime<<"\n";
  cout<<"Finished "<<cfg.mesh.filename()<<" seconds="<<runtime<<" uniformerr="<<uniformerr<<" max balance="<<max_balance<<"\n";return 0;
}
int main(int argc,char**argv){try{
    if(argc>=2 && string(argv[1])=="--selftest-1d"){if(argc<3)throw runtime_error("Missing output 1D.csv");return write_1d(argv[2]);}
    RunConfig c;for(int i=1;i<argc;++i){string s=argv[i];if(s=="--mesh"&&i+1<argc)c.mesh=argv[++i];else if(s=="--out"&&i+1<argc)c.out=argv[++i];else if(s=="--dt"&&i+1<argc)c.dt=stod(argv[++i]);else if(s=="--tend"&&i+1<argc)c.tend=stod(argv[++i]);else if(s=="--xi"&&i+1<argc)c.xi=stod(argv[++i]);else if(s=="--check-uniform")c.testUniform=true;else if(s=="--slab")c.slab=true;else if(s=="--check-analytic")c.checkAnalytic=true;else if(s=="--no-vtu")c.novtu=true;else if(s=="--every-step")c.everyStep=true;else if(s=="--compact")c.compact=true;else throw runtime_error("Unknown arg "+s);}
    if(c.mesh.empty()||c.out.empty())throw runtime_error("Usage: stage3d02_thermal --mesh H0.msh --out output --dt 300 --tend 3600 --xi 0 [--check-uniform] [--no-vtu]");
    if(c.dt<=0||c.tend<=0)throw runtime_error("Invalid time");if(c.compact&&c.novtu)throw runtime_error("P09E: --compact and --no-vtu are incompatible");return run(c);
  }catch(const exception&e){cerr<<"ERROR: "<<e.what()<<"\n";return 2;}}
