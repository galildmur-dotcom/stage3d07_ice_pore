// Stage3D03: isotropic 3D quasi-static thermoelasticity E on Tet10 (no inertia, ED, EDV).
// Shares Tet10 geometry and Gmsh/VTK node-ordering conventions with the verified thermal stage.
#include "tet10_shared.hpp"
#include <chrono>
#include <limits>
#include <cstring>
#include <random>
#include <chrono>
using namespace std;
using Clock = chrono::steady_clock;
constexpr double Eref=9.5e9, nu=.35, alphaT=149e-6/3., DT0=3.;
constexpr double dEdT=-Eref*0.012/9.17;
constexpr double lunit=nu/((1+nu)*(1-2*nu)), munit=1/(2*(1+nu));
struct Material{
 static double E(double theta,bool vary,double kappa=1){return Eref*(1+(vary?kappa:0)*(-.012*theta/9.17));}
 static double dE(bool vary,double kappa=1){return vary?kappa*dEdT:0;}
 static void sigma(const double strain[6],double theta,bool vary,double out[6],bool useThermal=true,double kappa=1){
   double ee[6];for(int i=0;i<6;++i)ee[i]=strain[i]-(useThermal&&i<3?alphaT*theta:0.);
   double tr=ee[0]+ee[1]+ee[2],e=E(theta,vary,kappa);
   for(int i=0;i<6;++i)out[i]=e*((i<3?lunit*tr:0)+2*munit*ee[i]);
 }
 static void dsigma_dT(const double strain[6],double theta,bool vary,double out[6]){
   double e[6];for(int i=0;i<6;++i)e[i]=strain[i]-(i<3?alphaT*theta:0.);
   double tr=e[0]+e[1]+e[2];
   for(int i=0;i<6;++i)out[i]=dE(vary)*((i<3?lunit*tr:0)+2*munit*e[i]) - (i<3?E(theta,vary)*alphaT*(3*lunit+2*munit):0);
 }
};
struct BCSR { // 3x3 block row CSR indexed by nodes, row-major block coefficients
 int n=0; vector<int> row,col;vector<array<double,9>> a;
 vector<array<double,9>> invdiag;
 static uint64_t key(int i,int j){return (uint64_t(uint32_t(i))<<32)|uint32_t(j);}
 void init(const Mesh&m){
  n=(int)m.nodes.size();vector<uint64_t> keys;keys.reserve(m.tets.size()*100);
  for(auto &t:m.tets)for(int i:t)for(int j:t)keys.push_back(key(i,j));
  sort(keys.begin(),keys.end());keys.erase(unique(keys.begin(),keys.end()),keys.end());
  row.assign(n+1,0);col.reserve(keys.size());for(uint64_t k:keys){row[(k>>32)+1]++;col.push_back(int(uint32_t(k)));}
  for(int i=0;i<n;++i)row[i+1]+=row[i];a.resize(keys.size());
 }
 int pos(int i,int j)const{auto lo=col.begin()+row[i],hi=col.begin()+row[i+1];auto it=lower_bound(lo,hi,j);
  if(it==hi||*it!=j)throw runtime_error("Missing block in stiffness matrix");return int(it-col.begin());}
 void mul(const vector<double>&x,vector<double>&out,const vector<uint8_t>&bc)const{
  out.assign(3*n,0);
  for(int i=0;i<n;++i){double o[3]={};for(int p=row[i];p<row[i+1];++p){int j=col[p];auto&v=a[p];
   for(int c=0;c<3;++c){int off=3*j+c;if(bc[off])continue;
    for(int r=0;r<3;++r)o[r]+=v[3*r+c]*x[off];}}
   for(int r=0;r<3;++r){int ir=3*i+r;out[ir]=bc[ir]?x[ir]:o[r];}
  }
 }
 static array<double,9> invert(array<double,9> M){
  // Gauss Jordan 3x3 for symmetric positive definite diagonal nodal blocks.
  double A[3][6]{};for(int i=0;i<3;++i){for(int j=0;j<3;++j)A[i][j]=M[3*i+j];A[i][3+i]=1;}
  for(int k=0;k<3;++k){double p=A[k][k];if(!(p>0))throw runtime_error("Bad block Jacobi pivot");for(int j=0;j<6;++j)A[k][j]/=p;
   for(int i=0;i<3;++i)if(i!=k){double q=A[i][k];for(int j=0;j<6;++j)A[i][j]-=q*A[k][j];}}
  array<double,9> O{};for(int i=0;i<3;++i)for(int j=0;j<3;++j)O[3*i+j]=A[i][3+j];return O;
 }
 void build_preconditioner(const vector<uint8_t>&bc){
  invdiag.resize(n);for(int i=0;i<n;++i){auto A=a[pos(i,i)];
   for(int c=0;c<3;++c)if(bc[3*i+c]){for(int d=0;d<3;++d)A[3*c+d]=A[3*d+c]=0;A[3*c+c]=1;}
   invdiag[i]=invert(A);
  }
 }
 void precond(const vector<double>&v,vector<double>&out,const vector<uint8_t>&bc)const{
  out.resize(3*n);for(int i=0;i<n;++i)for(int r=0;r<3;++r){int ir=3*i+r;if(bc[ir]){out[ir]=v[ir];continue;}
   out[ir]=0;for(int c=0;c<3;++c)out[ir]+=invdiag[i][3*r+c]*v[3*i+c];}
 }
};
struct Assembled {BCSR K;vector<double> f,massN;double vol=0,minDet=1e99,maxE=0,minE=1e99;};
struct GaussQ{double w;array<double,10>N;array<array<double,3>,10>d;};
vector<GaussQ> volume_q(int order){
 vector<GaussQ> q;auto add=[&](auto A,auto B,auto C){for(auto a:A)for(auto b:B)for(auto c:C){
  double r=a.x,s=(1-r)*b.x,t=(1-r)*(1-b.x)*c.x;GaussQ p;
  p.w=a.w*b.w*c.w*(1-r)*(1-r)*(1-b.x);tetshape(r,s,t,p.N,p.d);q.push_back(p);
 }};
 if(order==3)add(g3,g3,g3);else if(order==4)add(g4,g4,g4);else throw runtime_error("quadrature order 3 or 4 only");return q;
}
Assembled assemble_elastic(const Mesh&m,const vector<double>&theta,bool vary,int quad=3,bool thermal=true){
 if(theta.size()!=m.nodes.size())throw runtime_error("Temperature node count mismatch");Assembled A;A.K.init(m);
 A.f.assign(m.nodes.size()*3,0.);A.massN.assign(m.nodes.size(),0.);
 auto q=volume_q(quad);int elemno=0;
 for(const auto&t:m.tets){array<array<double,9>,100> ke{};double fe[30]{},me[10]{};
  for(const auto&b:q){
   V dr{},ds{},dt{};double Th=0;for(int i=0;i<10;++i){auto x=m.nodes[t[i]];dr=dr+x*b.d[i][0];ds=ds+x*b.d[i][1];dt=dt+x*b.d[i][2];Th+=theta[t[i]]*b.N[i];}
   V co0=cross(ds,dt),co1=cross(dt,dr),co2=cross(dr,ds);double jac=dot(dr,co0);
   if(!(jac>0))throw runtime_error("Invalid detJ in elasticity at tet "+to_string(elemno));
   A.minDet=min(A.minDet,jac);double w=b.w*jac;A.vol+=w;
   double E=Material::E(Th,vary);if(!(E>1e8&&E<1e11))throw runtime_error("Modulus outside physical model bounds");
   A.minE=min(A.minE,E);A.maxE=max(A.maxE,E);
   double lam=lunit*E,mu=munit*E,thermalStress=(3*lam+2*mu)*alphaT*Th;
   double g[10][3];for(int i=0;i<10;++i){V v=(co0*b.d[i][0]+co1*b.d[i][1]+co2*b.d[i][2])/jac;g[i][0]=v.x;g[i][1]=v.y;g[i][2]=v.z;me[i]+=b.N[i]*w;
     if(thermal)for(int r=0;r<3;++r)fe[3*i+r]+=thermalStress*g[i][r]*w;
   }
   for(int i=0;i<10;++i)for(int j=0;j<10;++j){double gg=g[i][0]*g[j][0]+g[i][1]*g[j][1]+g[i][2]*g[j][2];auto& k=ke[10*i+j];
     for(int r=0;r<3;++r)for(int c=0;c<3;++c)k[3*r+c]+=w*(lam*g[i][r]*g[j][c]+mu*g[i][c]*g[j][r]+(r==c?mu*gg:0));
   }
  }
  int ids[10][10];for(int i=0;i<10;++i)for(int j=0;j<10;++j)ids[i][j]=A.K.pos(t[i],t[j]);
  for(int i=0;i<10;++i){A.massN[t[i]]+=me[i];for(int r=0;r<3;++r)A.f[3*t[i]+r]+=fe[3*i+r];
    for(int j=0;j<10;++j){auto& K=A.K.a[ids[i][j]];auto& L=ke[i*10+j];for(int p=0;p<9;++p)K[p]+=L[p];}}
  ++elemno;
  if(elemno%15000==0)cerr<<"assembled "<<elemno<<" / "<<m.tets.size()<<"\n"<<flush;
 }
 return A;
}
vector<uint8_t> bc_candidate(const Mesh&m,bool pinZ=true){vector<uint8_t>bc(m.nodes.size()*3,0);int zpin=0;
 for(size_t i=0;i<m.nodes.size();++i){auto x=m.nodes[i];if(abs(abs(x.x)-.03)<1e-9)bc[3*i]=1;if(abs(abs(x.y)-.03)<1e-9)bc[3*i+1]=1;
  if(norm(x-V{0,0,0})<norm(m.nodes[zpin]-V{0,0,0}))zpin=int(i);
 }
 if(pinZ)bc[3*zpin+2]=1;
 return bc;
}
struct SolverInfo{int iterations=0;double rel=0,rz=0;double wall=0;};
static double vdot(const vector<double>&a,const vector<double>&b){double s=0;for(size_t i=0;i<a.size();++i)s+=a[i]*b[i];return s;}
SolverInfo solve(Assembled&A,const vector<uint8_t>&bc,vector<double>&u,double tol=1e-8,int maxit=3000){
 auto tic=Clock::now();size_t n=A.f.size();u.assign(n,0);vector<double> b=A.f,r,p,z,Ap;
 for(size_t i=0;i<n;++i)if(bc[i])b[i]=0;
 A.K.build_preconditioner(bc);A.K.precond(b,z,bc);r=b;p=z;double rz=vdot(r,z),base=sqrt(vdot(b,b));
 if(base==0)return{};
 int it=0;double rn=1;
 for(;it<maxit;++it){A.K.mul(p,Ap,bc);double denom=vdot(p,Ap);if(!(denom>0))throw runtime_error("Non SPD CG step");double a=rz/denom;
  for(size_t k=0;k<n;++k){u[k]+=a*p[k];r[k]-=a*Ap[k];}
  if((it%15)==0 || it==maxit-1){rn=sqrt(vdot(r,r))/base;if(rn<tol)break;}
  A.K.precond(r,z,bc);double rz2=vdot(r,z);double beta=rz2/rz;
  for(size_t k=0;k<n;++k)p[k]=z[k]+beta*p[k];rz=rz2;
  if((it+1)%300==0)cerr<<"CG iteration "<<it+1<<" residual "<<rn<<"\n"<<flush;
 }
 A.K.mul(u,Ap,bc);for(size_t i=0;i<n;++i)Ap[i]=b[i]-Ap[i];rn=sqrt(vdot(Ap,Ap))/base;
 if(rn>tol*1.2)throw runtime_error("CG failed final relative residual "+to_string(rn));
 return {it+1,rn,rz,chrono::duration<double>(Clock::now()-tic).count()};
}
void gauge(const vector<double>& mass,vector<double>&u){double s=0,vol=0;for(size_t i=0;i<mass.size();++i){vol+=mass[i];s+=mass[i]*u[3*i+2];}if(vol<=0)throw runtime_error("Bad gauge mass");double c=s/vol;for(size_t i=0;i<mass.size();++i)u[3*i+2]-=c;}
// tensor epsilon from nodal vector displacement
void strain_at(const Mesh&m,const Tet&t,const array<array<double,3>,10>& d, const vector<double>&u,double eps[6]){
 V dr{},ds{},dt{};for(int i=0;i<10;++i){auto x=m.nodes[t[i]];dr=dr+x*d[i][0];ds=ds+x*d[i][1];dt=dt+x*d[i][2];}
 V co0=cross(ds,dt),co1=cross(dt,dr),co2=cross(dr,ds);double J=dot(dr,co0);
 if(!(J>0))throw runtime_error("Negative det stress evaluation");
 double D[3][3]{};for(int i=0;i<10;++i){V grad=(co0*d[i][0]+co1*d[i][1]+co2*d[i][2])/J;
  for(int r=0;r<3;++r){double ur=u[3*t[i]+r];D[r][0]+=ur*grad.x;D[r][1]+=ur*grad.y;D[r][2]+=ur*grad.z;}}
 eps[0]=D[0][0];eps[1]=D[1][1];eps[2]=D[2][2];eps[3]=.5*(D[0][1]+D[1][0]);eps[4]=.5*(D[1][2]+D[2][1]);eps[5]=.5*(D[2][0]+D[0][2]);
}
double principal_max(const double s[6]){
 // Symmetric 3x3 eigenvalues by Jacobi sweeps, avoids reliance on closed-form branch logic.
 double a[3][3]={{s[0],s[3],s[5]},{s[3],s[1],s[4]},{s[5],s[4],s[2]}};
 for(int sweep=0;sweep<12;++sweep){int p=0,q=1;double z=abs(a[0][1]);for(auto pair:array<pair<int,int>,2>{{{0,2},{1,2}}})if(abs(a[pair.first][pair.second])>z){p=pair.first;q=pair.second;z=abs(a[p][q]);}
  if(z<1e-13)break;double tau=(a[q][q]-a[p][p])/(2*a[p][q]);double t=(tau>=0?1:-1)/(abs(tau)+sqrt(1+tau*tau));double c=1/sqrt(1+t*t),srot=t*c;
  double ap=a[p][p],aq=a[q][q],apq=a[p][q];a[p][p]=ap-t*apq;a[q][q]=aq+t*apq;a[p][q]=a[q][p]=0;
  for(int k=0;k<3;++k)if(k!=p && k!=q){double akp=a[k][p],akq=a[k][q];a[k][p]=a[p][k]=c*akp-srot*akq;a[k][q]=a[q][k]=srot*akp+c*akq;}
 }
 return max({a[0][0],a[1][1],a[2][2]});
}
vector<double> load_vtu_temp(const Mesh&m,fs::path file){ifstream f(file);if(!f)throw runtime_error("No temperature VTU: "+file.string());string all((istreambuf_iterator<char>(f)),{});
 auto parse=[&](string start,string end,int count){auto p=all.find(start);if(p==string::npos)throw runtime_error("Missing VTK array: "+start);
  if(start.rfind("<Points>",0)==0)p=all.find("<DataArray",p);p=all.find('>',p);if(p==string::npos)throw runtime_error("Invalid VTK array header");auto stop=all.find(end,p);
  if(stop==string::npos)throw runtime_error("Missing VTK array close");istringstream in(all.substr(p+1,stop-p-1));vector<double>v(count);
  for(auto&x:v)if(!(in>>x))throw runtime_error("VTK array too short");double extra;if(in>>extra)throw runtime_error("VTK array too long");return v;};
 auto xyz=parse("<Points><DataArray","</DataArray>",3*int(m.nodes.size()));double maxerr=0;
 for(size_t i=0;i<m.nodes.size();++i){auto x=m.nodes[i];maxerr=max({maxerr,abs(x.x-xyz[3*i]),abs(x.y-xyz[3*i+1]),abs(x.z-xyz[3*i+2])});}
 if(maxerr>5e-11)throw runtime_error("Node ordering mismatch thermal VTU vs mechanical MSH "+to_string(maxerr));
 return parse("Name=\"dT_K\"","</DataArray>",int(m.nodes.size()));
}
struct ElementStats {vector<array<double,8>> values;double maxS1=0,minS1=1e100,maxVM=0;};
ElementStats evaluate_stress(const Mesh&m,const vector<double>&theta,const vector<double>&u,bool vary){
 ElementStats z;z.values.reserve(m.tets.size());array<double,10>N;array<array<double,3>,10>d;tetshape(.25,.25,.25,N,d);
 for(auto t:m.tets){double e[6];strain_at(m,t,d,u,e);double Th=0;for(int i=0;i<10;++i)Th+=N[i]*theta[t[i]];
  double sigm[6];Material::sigma(e,Th,vary,sigm);double s1=principal_max(sigm);
  double vm=sqrt(.5*(pow(sigm[0]-sigm[1],2)+pow(sigm[1]-sigm[2],2)+pow(sigm[2]-sigm[0],2))+3*(sigm[3]*sigm[3]+sigm[4]*sigm[4]+sigm[5]*sigm[5]));
  z.maxS1=max(z.maxS1,s1);z.minS1=min(z.minS1,s1);z.maxVM=max(z.maxVM,vm);
  z.values.push_back({sigm[0]/1e6,sigm[1]/1e6,sigm[2]/1e6,sigm[3]/1e6,sigm[4]/1e6,sigm[5]/1e6,s1/1e6,vm/1e6});
 }
 return z;
}
void save_mech_vtu(const Mesh&m,const vector<double>&u,const vector<double>&theta,const ElementStats&st,fs::path out,double time_s,const vector<array<double,5>>* qp_peak=nullptr){fs::create_directories(out.parent_path());ofstream f(out);f<<setprecision(14);
 f<<"<?xml version=\"1.0\"?><VTKFile type=\"UnstructuredGrid\" version=\"0.1\" byte_order=\"LittleEndian\"><UnstructuredGrid><Piece NumberOfPoints=\""<<m.nodes.size()<<"\" NumberOfCells=\""<<m.tets.size()<<"\">\n";
 f<<"<FieldData><DataArray type=\"Float64\" Name=\"TIME\" NumberOfTuples=\"1\" format=\"ascii\">"<<time_s<<"</DataArray></FieldData>\n";
 f<<"<Points><DataArray type=\"Float64\" NumberOfComponents=\"3\" format=\"ascii\">\n";
 for(auto v:m.nodes)f<<v.x<<" "<<v.y<<" "<<v.z<<"\n";f<<"</DataArray></Points><Cells><DataArray type=\"Int32\" Name=\"connectivity\" format=\"ascii\">\n";
 for(auto t:m.tets){for(int i:t)f<<i<<" ";f<<"\n";}f<<"</DataArray><DataArray type=\"Int64\" Name=\"offsets\" format=\"ascii\">\n";
 for(size_t i=1;i<=m.tets.size();++i)f<<10*i<<" ";f<<"</DataArray><DataArray type=\"UInt8\" Name=\"types\" format=\"ascii\">\n";
 for(size_t i=0;i<m.tets.size();++i)f<<"24 ";f<<"</DataArray></Cells>\n";
 f<<"<PointData><DataArray type=\"Float64\" Name=\"Displacement_m\" NumberOfComponents=\"3\" format=\"ascii\">\n";
 for(size_t i=0;i<m.nodes.size();++i)f<<u[3*i]<<" "<<u[3*i+1]<<" "<<u[3*i+2]<<"\n";f<<"</DataArray><DataArray type=\"Float64\" Name=\"Temperature_C\" format=\"ascii\">\n";
 for(double v:theta)f<<v-20<<" ";f<<"</DataArray></PointData>\n<CellData>\n";
 static const char* label[8]={"Sigma_xx_MPa","Sigma_yy_MPa","Sigma_zz_MPa","Sigma_xy_MPa","Sigma_yz_MPa","Sigma_zx_MPa","Principal_max_MPa","Von_Mises_MPa"};
 for(int c=0;c<8;++c){f<<"<DataArray type=\"Float64\" Name=\""<<label[c]<<"\" format=\"ascii\">\n";for(const auto&v:st.values)f<<v[c]<<" ";f<<"</DataArray>\n";}
 if(qp_peak){
   if(qp_peak->size()!=m.tets.size())throw runtime_error("QP peak array and mesh cell count mismatch");
   static const char* nm[5]={"Principal_QP_max_MPa","QP_max_x_m","QP_max_y_m","QP_max_z_m","QP_max_index"};
   for(int c=0;c<5;++c){f<<"<DataArray type=\"Float64\" Name=\""<<nm[c]<<"\" format=\"ascii\">\n";
     for(const auto &v:*qp_peak)f<<v[c]<<" ";f<<"</DataArray>\n";}
 }
 f<<"</CellData></Piece></UnstructuredGrid></VTKFile>\n";
}
struct Diagnostics{double maxUxBC=0,maxUyBC=0,uzIntegral=0,freeResidual=0,rootZReaction=0,maxUM=0,minT=1e100,maxT=-1e100;};
Diagnostics diagnostics(const Mesh&m,const Assembled&A,const vector<double>&theta,const vector<double>&u,const vector<uint8_t>&bc){
 Diagnostics d;vector<double>force;vector<uint8_t>none(bc.size(),0);A.K.mul(u,force,none);double bnorm=sqrt(vdot(A.f,A.f));double rnorm=0;double wz=0;
 for(size_t i=0;i<m.nodes.size();++i){double mag=0;for(int j=0;j<3;++j){int k=3*i+j;mag+=u[k]*u[k];double rr=force[k]-A.f[k];if(!bc[k])rnorm+=rr*rr;else if(j==2)d.rootZReaction+=rr;}
  d.maxUM=max(d.maxUM,sqrt(mag));d.maxUxBC=max(d.maxUxBC,bc[3*i]?abs(u[3*i]):0.);
  d.maxUyBC=max(d.maxUyBC,bc[3*i+1]?abs(u[3*i+1]):0.);
  wz+=A.massN[i]*u[3*i+2];d.minT=min(d.minT,theta[i]-20);d.maxT=max(d.maxT,theta[i]-20);
 }
 d.freeResidual=sqrt(rnorm)/max(bnorm,1e-50);d.uzIntegral=wz;return d;
}
void require(bool ok,const string&msg){if(!ok)throw runtime_error("TEST FAIL: "+msg);}
void material_tests(fs::path out){fs::create_directories(out);ofstream tab(out/"MAT_T01_T02_T03.csv");tab<<setprecision(16)<<"T_C,T_K,E_CONST_Pa,E_VAR_Pa,dE_VAR_dT_Pa_K,bulk_VAR_Pa,shear_VAR_Pa,kappa0_E_Pa\n";
 double temps[]={-40,-35,-30,-25,-23,-22,-21,-20,-19,-17,-15,-10,-5,0};for(double t:temps){double th=t+20,e=Material::E(th,true);
   tab<<t<<","<<t+273.15<<","<<Eref<<","<<e<<","<<dEdT<<","<<e/(3*(1-2*nu))<<","<<e/(2*(1+nu))<<","<<Material::E(th,true,0)<<"\n";
   require(e>0 && dEdT<0 && abs(Material::E(th,true,0)-Eref)<1e-6,"positive material, zero slope");
   require(abs(Material::E(th,true)-Eref*(8.93-.012*t)/9.17)<1e-4,"Kelvin / Celsius reference");
 }
 require(abs(Material::E(0,true)-Eref)<1e-8,"E(Tref)");require(abs(dEdT+12431842.96619411)<.01,"E slope");
 ofstream res(out/"MAT_T06.csv");res<<setprecision(16)<<"T_C,mode,component,analytic_dsigma_dT_Pa_K,FD_dsigma_dT_Pa_K,relative_error\n";
 const double eps[6]={.0008,-.00045,.00023,.00019,-.0001,.00031};
 for(bool varying:{false,true})for(double th:{-4.,0.,2.}){double deriv[6];Material::dsigma_dT(eps,th,varying,deriv);double h=.001;
  double plus[6],minus[6];Material::sigma(eps,th+h,varying,plus);Material::sigma(eps,th-h,varying,minus);
  for(int c=0;c<6;++c){double fd=(plus[c]-minus[c])/(2*h),re=abs(fd-deriv[c])/max(1.,abs(deriv[c]));
   res<<th-20<<","<<(varying?"VAR":"CONST")<<","<<c<<","<<deriv[c]<<","<<fd<<","<<re<<"\n";require(re<1e-8,"MAT-T06 numerical dSigma/dT");}}
 cout<<"PASS MAT-T01/02/03/06\n";
}
// Independent patch test on arbitrary curved mesh: linear u(x)=F*x, uniform theta=0.
// Exact div sigma=0, exact traction is integral sigma*n on all exterior faces.
// Compare assembled K u against independently face-integrated stress traction.
void patch_test(const Mesh&m,const Assembled&A,fs::path out){
 fs::create_directories(out);const double F[3][3]={{.001,.0002,-.0001},{.0002,-.0006,.00015},{-.0001,.00015,.0003}};
 vector<double>u(3*m.nodes.size()),boundary(3*m.nodes.size());
 for(size_t i=0;i<m.nodes.size();++i){auto x=m.nodes[i];double xcoord[3]={x.x,x.y,x.z};for(int c=0;c<3;++c){for(int k=0;k<3;++k)u[3*i+c]+=F[c][k]*xcoord[k];}}
 double e[6]={F[0][0],F[1][1],F[2][2],F[0][1],F[1][2],F[2][0]},s[6];Material::sigma(e,0,false,s,false);
 for(auto&face:m.faces)for(auto ga:g4)for(auto gb:g4){double r=ga.x,v=(1-r)*gb.x;auto S=seval(m,face.nodes,r,v);
  V n=cross(S.du,S.dv);double orient=1;V expect{};
  if(face.tag==2)expect={0,0,1};else if(face.tag==3)expect={0,0,-1};else if(face.tag==4)expect={-1,0,0};else if(face.tag==5)expect={1,0,0};else if(face.tag==6)expect={0,-1,0};else if(face.tag==7)expect={0,1,0};else if(face.tag==8)expect=unit(V{0,0,.03}-S.p);
  else throw runtime_error("Unknown patch face tag");
  if(dot(n,expect)<0)orient=-1;n=n*orient;
  double w=ga.w*gb.w*(1-r);auto shape=triN(r,v);
  double traction[3]={s[0]*n.x+s[3]*n.y+s[5]*n.z,s[3]*n.x+s[1]*n.y+s[4]*n.z,s[5]*n.x+s[4]*n.y+s[2]*n.z};
  for(int i=0;i<6;++i)for(int c=0;c<3;++c)boundary[3*face.nodes[i]+c]+=w*shape[i]*traction[c];
 }
 vector<double>Ku;vector<uint8_t>no(u.size());A.K.mul(u,Ku,no);double err=0,scale=sqrt(vdot(boundary,boundary));
 for(size_t i=0;i<u.size();++i)err+=(Ku[i]-boundary[i])*(Ku[i]-boundary[i]);double rel=sqrt(err)/scale;
 ofstream f(out/"G03_patch.csv");f<<setprecision(16)<<"case,relative_residual,max_stress_expected_MPa\nlinear_strain_boundary_traction,"<<rel<<","<<principal_max(s)/1e6<<"\n";
 cout<<"Patch test residual "<<rel<<"\n";require(rel<4e-6,"G03 affine patch / normals");
}
// Manufactured elastic stress with E(z) and analytic linear u. dE/dz known.
void mms_test(const Mesh&m,fs::path out){
 fs::create_directories(out);vector<double>theta(m.nodes.size()),u(3*m.nodes.size()),rhs(3*m.nodes.size());
 double F[3][3]={{.0012,.00021,0},{.00021,-.0007,.00014},{0,.00014,.00031}};
 for(size_t i=0;i<m.nodes.size();++i){auto x=m.nodes[i];theta[i]=80*x.z;double q[3]={x.x,x.y,x.z};for(int c=0;c<3;++c)for(int k=0;k<3;++k)u[3*i+c]+=F[c][k]*q[k];}
 auto A=assemble_elastic(m,theta,true,3,false);
 double eps[6]={F[0][0],F[1][1],F[2][2],F[0][1],F[1][2],F[2][0]};double S[6];Material::sigma(eps,0,false,S,false);
 for(double&x:S)x/=Eref; // dimensionless stress per elastic E.
 // -div sigma: ∂z σ_iz = dE/dz * S_i3.
 double b[3]={-dEdT*80*S[5],-dEdT*80*S[4],-dEdT*80*S[2]};
 for(auto &t:m.tets)for(auto ga:volume_q(3)){
  V dr{},ds{},dt{};for(int i=0;i<10;++i){auto p=m.nodes[t[i]];dr=dr+p*ga.d[i][0];ds=ds+p*ga.d[i][1];dt=dt+p*ga.d[i][2];}double w=ga.w*dot(dr,cross(ds,dt));
  for(int i=0;i<10;++i)for(int c=0;c<3;++c)rhs[3*t[i]+c]+=w*ga.N[i]*b[c];
 }
 for(auto&face:m.faces)for(auto a:g4)for(auto bq:g4){double r=a.x,s=(1-r)*bq.x;auto se=seval(m,face.nodes,r,s);V target{};
  if(face.tag==2)target={0,0,1};if(face.tag==3)target={0,0,-1};if(face.tag==4)target={-1,0,0};if(face.tag==5)target={1,0,0};if(face.tag==6)target={0,-1,0};if(face.tag==7)target={0,1,0};
  if(norm(target)==0)throw runtime_error("MMS only works on no-hole slab");
  V nn=cross(se.du,se.dv);if(dot(nn,target)<0)nn=nn*(-1);double w=a.w*bq.w*(1-r),E=Material::E(80*se.p.z,true);
  double traction[3]={E*(S[0]*nn.x+S[3]*nn.y+S[5]*nn.z),E*(S[3]*nn.x+S[1]*nn.y+S[4]*nn.z),E*(S[5]*nn.x+S[4]*nn.y+S[2]*nn.z)};
  auto shape=triN(r,s);for(int i=0;i<6;++i)for(int c=0;c<3;++c)rhs[3*face.nodes[i]+c]+=w*shape[i]*traction[c];
 }
 vector<double>Ku;vector<uint8_t>bc(u.size());A.K.mul(u,Ku,bc);
 double err=0,scale=sqrt(vdot(rhs,rhs));for(size_t i=0;i<rhs.size();++i)err+=(Ku[i]-rhs[i])*(Ku[i]-rhs[i]);double relative=sqrt(err)/scale;
 cout<<"MMS heterogeneous E(z) residual: "<<relative<<"\n";
 ofstream f(out/"MAT_T05.csv");f<<setprecision(16)<<"case,relative_residual,dE_dz_Pa_m,exact_body_force_z_N_m3\nlinear_Ez_affine_u,"<<relative<<","<<dEdT*80<<","<<b[2]<<"\n";
 require(relative<2e-6,"MAT-T05 linear heterogeneous E manufactured equilibrium");
}
// Zero-strain rigid-body modes and free uniform expansion on the curved pore mesh.
void rigid_and_pure(const Mesh&m,fs::path out,bool pure){
 fs::create_directories(out);
 vector<double>theta(m.nodes.size(),pure?-3.:0.);
 auto A=assemble_elastic(m,theta,pure,3,pure);
 vector<uint8_t>bc(3*m.nodes.size(),0);
 ofstream f(out/(pure?"G03_pure_expansion.csv":"G03_rigid_modes.csv"));f<<setprecision(16);
 if(pure){
  f<<"theta_K,relative_residual,max_stress_Pa\n";
  vector<double>u(3*m.nodes.size());for(size_t i=0;i<m.nodes.size();++i){auto x=m.nodes[i];u[3*i]=alphaT*(-3)*x.x;u[3*i+1]=alphaT*(-3)*x.y;u[3*i+2]=alphaT*(-3)*x.z;}
  vector<double>Ku;A.K.mul(u,Ku,bc);double err=0,ref=vdot(A.f,A.f);
  for(size_t i=0;i<Ku.size();++i)err+=pow(Ku[i]-A.f[i],2);
  double e[6]={};array<double,10>N;array<array<double,3>,10>d;tetshape(.25,.25,.25,N,d);double stressMax=0;
  for(auto t:m.tets){strain_at(m,t,d,u,e);double sig[6];Material::sigma(e,-3,true,sig);for(double v:sig)stressMax=max(stressMax,abs(v));}
  double rel=sqrt(err/ref);cout<<"Pure thermal expansion free pore relative="<<rel<<" sigma_Pa="<<stressMax<<"\n";
  f<<"-3,"<<rel<<","<<stressMax<<"\n";require(rel<1e-10 && stressMax<1e-5,"G03 pure thermal expansion and zero stress");
 }else{
  f<<"mode,relative_Ku_vs_diagonal_scale\n";
  for(int mode=0;mode<6;++mode){vector<double>u(3*m.nodes.size()),Ku;
    for(size_t i=0;i<m.nodes.size();++i){auto x=m.nodes[i];
      if(mode<3)u[3*i+mode]=1.;
      if(mode==3){u[3*i+1]=-x.z;u[3*i+2]=x.y;}
      if(mode==4){u[3*i]=-x.z;u[3*i+2]=x.x;}
      if(mode==5){u[3*i]=-x.y;u[3*i+1]=x.x;}
    }
    A.K.mul(u,Ku,bc);double nr=sqrt(vdot(Ku,Ku)),scale=0;
    for(int i=0;i<A.K.n;++i){auto D=A.K.a[A.K.pos(i,i)];for(int c=0;c<3;++c)scale+=pow(D[3*c+c]*u[3*i+c],2);}
    double rel=nr/max(sqrt(scale),1e-30);f<<mode<<","<<rel<<"\n";
    require(rel<2e-11,"G03 free elastic rigid translation/rotation nullspace");
  }
  cout<<"PASS all six free-body modes\n";
 }
}
void test_slab_candidate(const Mesh&m,fs::path out){
 // Uniform cooldown with laterally constrained box: ux=uy=0, uz=alpha*theta*(1+nu)/(1-nu)*(z-H/2).
 vector<double>theta(m.nodes.size(),-3),u(3*m.nodes.size());
 auto A=assemble_elastic(m,theta,false,3,true);auto bc=bc_candidate(m);
 auto solver=solve(A,bc,u,1e-9);gauge(A.massN,u);
 double slope=alphaT*(-3)*(1+nu)/(1-nu),err=0,exactnorm=0;
 for(size_t i=0;i<m.nodes.size();++i){double ex=slope*(m.nodes[i].z-.025);err=max(err,abs(u[3*i+2]-ex));exactnorm=max(exactnorm,abs(ex));}
 auto st=evaluate_stress(m,theta,u,false);
 double xx=-Eref*alphaT*(-3)/(1-nu)/1e6;
 double maxStressError=0;for(auto v:st.values){maxStressError=max({maxStressError,abs(v[0]-xx),abs(v[1]-xx),abs(v[2])});}
 auto diag=diagnostics(m,A,theta,u,bc);ofstream f(out/"G03_slab_candidate.csv");
 f<<setprecision(16)<<"solver_it,solver_relative,max_u_z_error_m,exact_u_z_max_m,analytic_sigma_xx_MPa,max_sigma_error_MPa,gauge_integral_m4,free_residual\n"<<solver.iterations<<","<<solver.rel<<","<<err<<","<<exactnorm<<","<<xx<<","<<maxStressError<<","<<diag.uzIntegral<<","<<diag.freeResidual<<"\n";
 cout<<"Slab Candidate A: disp error "<<err<<" stress error MPa "<<maxStressError<<" it "<<solver.iterations<<"\n";
 require(err<5e-9 && maxStressError<.002 && solver.rel<2e-9,"G03 Candidate A analytical slab");
}
void tref_branch(const Mesh&m,fs::path out){
 vector<double>theta(m.nodes.size(),0);auto a=assemble_elastic(m,theta,false,3,false),b=assemble_elastic(m,theta,true,3,false);
 double err=0,scale=0;for(size_t i=0;i<a.K.a.size();++i)for(int j=0;j<9;++j){double p=a.K.a[i][j],q=b.K.a[i][j];err=max(err,abs(p-q));scale=max(scale,abs(p));}
 require(err==0,"MAT-T04 E_const/var stiffness identical at Tref");
 // Nonzero manufactured horizontal body loading in both systems.
 for(size_t i=0;i<m.nodes.size();++i){a.f[3*i]=a.massN[i]*1200.;b.f[3*i]=b.massN[i]*1200.;}
 auto bc=bc_candidate(m);vector<double>ua,ub;auto ra=solve(a,bc,ua,5e-10),rb=solve(b,bc,ub,5e-10);gauge(a.massN,ua);gauge(b.massN,ub);
 double delta=0,maxDisp=0;for(size_t i=0;i<ua.size();++i){delta=max(delta,abs(ua[i]-ub[i]));maxDisp=max(maxDisp,abs(ua[i]));}
 ofstream f(out/"MAT_T04.csv");f<<setprecision(16)<<"relative_stiffness_delta,max_u_difference_m,max_u_m,iteration_CONST,iteration_VAR\n"<<(scale>0?err/scale:0)<<","<<delta<<","<<maxDisp<<","<<ra.iterations<<","<<rb.iterations<<"\n";
 cout<<"Tref branches exact compare: delta="<<delta<<" nonzero u="<<maxDisp<<"\n";
 require(maxDisp>1e-12 && delta<1e-15,"MAT-T04 nontrivial solution, same E at Tref");
}
#ifndef STAGE3D06_LIBRARY
int main(int argc,char**argv){try{
 fs::path mesh,temp,out;string variant="both",mode="solve";int quad=3;double xi=0, time_s=3600;
 for(int i=1;i<argc;++i){string a=argv[i];if(a=="--mesh"&&i+1<argc)mesh=argv[++i];else if(a=="--temp"&&i+1<argc)temp=argv[++i];else if(a=="--out"&&i+1<argc)out=argv[++i];else if(a=="--model"&&i+1<argc)variant=argv[++i];else if(a=="--mode"&&i+1<argc)mode=argv[++i];else if(a=="--quad"&&i+1<argc)quad=stoi(argv[++i]);else if(a=="--xi"&&i+1<argc)xi=stod(argv[++i]);else if(a=="--time"&&i+1<argc)time_s=stod(argv[++i]);else throw runtime_error("Unknown argument "+a);}
 if(out.empty())throw runtime_error("Missing --out DIR");fs::create_directories(out);
 if(mode=="material"){material_tests(out);return 0;}
 if(mesh.empty())throw runtime_error("Missing --mesh");bool slab=mode=="slab"||mode=="mms"||mode=="tref";
 auto imp=read_msh(mesh,slab);auto&m=imp.mesh;cout<<"Loaded "<<mesh.filename()<<" nodes="<<m.nodes.size()<<" Tet10="<<m.tets.size()<<"\n"<<flush;
 if(mode=="mms"){mms_test(m,out);return 0;}
 if(mode=="rigid" || mode=="pure"){rigid_and_pure(m,out,mode=="pure");return 0;}
 if(mode=="tref"){tref_branch(m,out);return 0;}
 if(mode=="slab"){test_slab_candidate(m,out);return 0;}
 if(mode=="patch"){
  vector<double>theta(m.nodes.size());auto A=assemble_elastic(m,theta,false,quad,false);patch_test(m,A,out);return 0;
 }
 if(mode!="solve")throw runtime_error("Unknown --mode");
 if(temp.empty())throw runtime_error("Need --temp thermal VTU from matching H0/H1/H2");
 auto theta=load_vtu_temp(m,temp);vector<uint8_t>bc=bc_candidate(m);
 ofstream csv(out/"mechanical_summary.csv");csv<<setprecision(16)<<"model,time_s,nodes,tet10,quad,xi,T_C_min,T_C_max,E_min_Pa,E_max_Pa,volume_m3,min_detJ,iterations,solver_rel,max_disp_m,max_s1_MPa,min_s1_MPa,max_VM_MPa,max_bc_ux_m,max_bc_uy_m,gauge_integral_m4,free_residual_rel,vertical_pin_reaction_N,wall_seconds\n";
 for(bool vary:{false,true}){
  if(variant!="both" && variant!=(vary?"VAR":"CONST"))continue;
  cout<<"Assembling "<<(vary?"VAR":"CONST")<<" quadrature="<<quad<<"\n"<<flush;
  auto A=assemble_elastic(m,theta,vary,quad,true);cout<<"Assembled blocks="<<A.K.a.size()<<" DOF="<<A.f.size()<<"\n"<<flush;
  auto t1=Clock::now();vector<double>u;auto sol=solve(A,bc,u,2e-8,4500);gauge(A.massN,u);
  auto stats=evaluate_stress(m,theta,u,vary);auto d=diagnostics(m,A,theta,u,bc);
  double elapsed=chrono::duration<double>(Clock::now()-t1).count();string label=(vary?"E_VAR":"E_CONST");
  csv<<label<<","<<time_s<<","<<m.nodes.size()<<","<<m.tets.size()<<","<<quad<<","<<xi<<","<<d.minT<<","<<d.maxT<<","<<A.minE<<","<<A.maxE<<","<<A.vol<<","<<A.minDet<<","<<sol.iterations<<","<<sol.rel<<","<<d.maxUM<<","<<stats.maxS1/1e6<<","<<stats.minS1/1e6<<","<<stats.maxVM/1e6<<","<<d.maxUxBC<<","<<d.maxUyBC<<","<<d.uzIntegral<<","<<d.freeResidual<<","<<d.rootZReaction<<","<<elapsed<<"\n"<<flush;
  cout<<label<<" CG "<<sol.iterations<<" residual="<<sol.rel<<" max-s1 MPa="<<stats.maxS1/1e6<<" gauge="<<d.uzIntegral<<"\n"<<flush;
  require(d.freeResidual<1e-6 && abs(d.uzIntegral)<1e-16 && abs(d.rootZReaction)<1e-4,"mechanical equilibrium and gauge");
  save_mech_vtu(m,u,theta,stats,out/(label+"_t"+to_string(int(time_s))+".vtu"),time_s);
 }
 return 0;
 }catch(const exception&e){cerr<<"ERROR: "<<e.what()<<"\n";return 2;}}

#endif // STAGE3D06_LIBRARY
