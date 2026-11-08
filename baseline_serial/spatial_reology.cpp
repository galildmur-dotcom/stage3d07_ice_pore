// Stage 3D-06: 3D quasi-static direct E/ED/EDV solver, Tet10, matched thermal history.
// Tensor strains use true shear components, not engineering gamma.
#define STAGE3D06_LIBRARY
#include "mechanical.cpp"
#include "edv_material.hpp"
#include <bit>
#include <cstdint>
// Win32 API is isolated in a dedicated translation unit to avoid global
// Windows macros and RPC `byte` colliding with our C++20 material headers.
#ifdef _WIN32
extern "C" long stage3d06_peak_memory_kb_windows();
#endif

using State = ice3d::edv::State;
using Tensor = ice3d::edv::Tensor;
using ice3d::edv::Response;
using ice3d::ed::Modulus;

struct Setting {string name="EDV",mod="VAR";int quad=3;double newtonTol=2e-7, cgTol=2e-7;int maxNewton=12, maxCG=3500;};
struct Field {vector<double> u; vector<State> qstate;double lastTime=0;};
struct Work {Assembled A;double normResidual=0,maxSigma=0,j6=0,jOmega=0,volume6=0,volume=0, freeReactionZ=0;double polarTopStress=0,polarBottomStress=0,polarTopVolume=0,polarBottomVolume=0;vector<array<double,8>> cell;vector<array<double,5>> qp_peak;vector<State> next;size_t maxElement=0,maxQ=0;V maxX{};int maxLocalIterations=0;};
static double quad_sigma_ref=9.5e9*(149e-6/3.)*3./(1.-.35);

uint64_t signature(const Mesh&m){
 uint64_t h=14695981039346656037ull;
 auto mix=[&](uint64_t b){h^=b;h*=1099511628211ull;};
 for(const auto&x:m.nodes){mix(bit_cast<uint64_t>(x.x));mix(bit_cast<uint64_t>(x.y));mix(bit_cast<uint64_t>(x.z));}
 for(const auto&t:m.tets)for(int a:t)mix(uint32_t(a));return h;
}

array<double,3> eigh3(Tensor sigma){
 double a[3][3]={{sigma[0],sigma[3],sigma[5]},{sigma[3],sigma[1],sigma[4]},{sigma[5],sigma[4],sigma[2]}};
 for(int sweep=0;sweep<30;++sweep){int p=0,q=1;double z=abs(a[0][1]);
  for(auto [i,j]:array<pair<int,int>,2>{{{0,2},{1,2}}})if(abs(a[i][j])>z){p=i;q=j;z=abs(a[i][j]);}
  if(z<1e-8)break;
  double tau=(a[q][q]-a[p][p])/(2*a[p][q]), tt=(tau>=0?1.:-1.)/(abs(tau)+sqrt(1+tau*tau));
  double c=1/sqrt(1+tt*tt),s=c*tt,ap=a[p][p],aq=a[q][q],apq=a[p][q];
  a[p][p]=ap-tt*apq;a[q][q]=aq+tt*apq;a[p][q]=a[q][p]=0;
  for(int k=0;k<3;++k)if(k!=p&&k!=q){double ak=a[k][p],bk=a[k][q];a[k][p]=a[p][k]=c*ak-s*bk;a[k][q]=a[q][k]=s*ak+c*bk;}
 }
 array<double,3> eig={a[0][0],a[1][1],a[2][2]};sort(eig.begin(),eig.end(),greater<double>());return eig;
}

double psi(const Tensor&s){auto eig=eigh3(s);double v=0;for(double ev:eig){double r=ev/quad_sigma_ref,p=.5*(r+sqrt(r*r+1e-6));v+=p*p;}return v;}

// Physical B^T sigma and consistent 3D tangent. The factor 2 for tensor shears is essential.
void basis(const double g[3],int component,Tensor&v){v={};
 if(component==0){v[0]=g[0];v[3]=g[1]*.5;v[5]=g[2]*.5;}
 if(component==1){v[1]=g[1];v[3]=g[0]*.5;v[4]=g[2]*.5;}
 if(component==2){v[2]=g[2];v[4]=g[1]*.5;v[5]=g[0]*.5;}
}

Work assemble(const Mesh&m,const vector<GaussQ>&quadrature,const vector<double>&T,const Field&f,
              double dt,const Setting&set,const vector<uint8_t>&bc,bool makeMatrix,bool needOutput){
 Work w;const size_t nq=quadrature.size();size_t ng=m.tets.size()*nq;
 if(f.qstate.size()!=ng)throw runtime_error("quadrature history size mismatch");
 if(makeMatrix)w.A.K.init(m);
 w.A.f.assign(3*m.nodes.size(),0);w.A.massN.assign(m.nodes.size(),0);
 if(needOutput){w.next.resize(ng);w.cell.resize(m.tets.size());w.qp_peak.resize(m.tets.size());}
 auto controls=ice3d::edv::Controls{set.name!="E",set.name=="EDV"};
 auto md=(set.mod=="CONST"?Modulus::CONST:Modulus::VAR);
 double sum6=0,sumAll=0,vol6=0,volAll=0, maxStress=-1e99;
 for(size_t e=0;e<m.tets.size();++e){const auto&t=m.tets[e];
  // Conforming Gmsh internal B6 interface: classify by element centroid.
  V center{};for(int j=0;j<4;++j)center=center+m.nodes[t[j]]*.25;
  bool in6=norm(center-V{0,0,.03})<.006;
  array<array<double,9>,100> localK{};array<double,30> localR{};
  array<double,8> integral{};double eVol=0;double peak=-1e99;int peakQ=-1;V peakX{};
  for(size_t iq=0;iq<nq;++iq){const auto&b=quadrature[iq];V dr{},ds{},dz{};double tk=ice3d::ed::T_ref;
   for(int j=0;j<10;++j){auto x=m.nodes[t[j]];dr=dr+x*b.d[j][0];ds=ds+x*b.d[j][1];dz=dz+x*b.d[j][2];tk+=b.N[j]*T[t[j]];}
   V c0=cross(ds,dz),c1=cross(dz,dr),c2=cross(dr,ds);double det=dot(dr,c0);
   if(!(det>0))throw runtime_error("negative Jacobian at element "+to_string(e));
   double dvol=b.w*det;volAll+=dvol;eVol+=dvol; if(in6)vol6+=dvol;
   double grad[10][3];for(int j=0;j<10;++j){V G=(c0*b.d[j][0]+c1*b.d[j][1]+c2*b.d[j][2])/det;grad[j][0]=G.x;grad[j][1]=G.y;grad[j][2]=G.z;
     if(makeMatrix)w.A.massN[t[j]]+=dvol*b.N[j];}
   Tensor eps{}; Tensor B[30];
   for(int a=0;a<10;++a)for(int dir=0;dir<3;++dir){int ix=3*a+dir;basis(grad[a],dir,B[ix]);double u=f.u[3*t[a]+dir];for(int j=0;j<6;++j)eps[j]+=B[ix][j]*u;}
   Response r=ice3d::edv::update(eps,tk,dt,f.qstate[e*nq+iq],md,controls);
   w.maxLocalIterations=max(w.maxLocalIterations,r.iterations);
   if(needOutput)w.next[e*nq+iq]=r.new_state;
   double ps=0;if(needOutput){ps=psi(r.sigma);sumAll+=dvol*ps;if(in6)sum6+=dvol*ps;
      const double s1=eigh3(r.sigma)[0];
      V qpos{};for(int j=0;j<10;++j)qpos=qpos+m.nodes[t[j]]*b.N[j];
      // Fixed physical polar observation caps (not a mesh-dependent top-N maximum).
      // Shell: 1.00..1.30 mm, polar half-angle: 25 degrees, equal top/bottom definitions.
      const V delta=qpos-V{0,0,.03};const double rr=norm(delta);
      if(rr>=RBASE && rr<=RBASE+0.00030 && rr>0){
        constexpr double cos25=0.9063077870366499;
        if(delta.z/rr>=cos25){w.polarTopStress+=dvol*max(0.0,s1/1e6);w.polarTopVolume+=dvol;}
        if(delta.z/rr<=-cos25){w.polarBottomStress+=dvol*max(0.0,s1/1e6);w.polarBottomVolume+=dvol;}
      }
      if(s1>peak){peak=s1;peakQ=int(iq);peakX=qpos;}
      if(s1>maxStress){maxStress=s1;w.maxElement=e;w.maxQ=iq;w.maxX=qpos;}
      for(int k=0;k<6;++k)integral[k]+=r.sigma[k]/1e6*dvol;
      integral[6]+=eigh3(r.sigma)[0]/1e6*dvol;
      double vm=sqrt(.5*(pow(r.sigma[0]-r.sigma[1],2)+pow(r.sigma[1]-r.sigma[2],2)+pow(r.sigma[2]-r.sigma[0],2))
                     +3*(r.sigma[3]*r.sigma[3]+r.sigma[4]*r.sigma[4]+r.sigma[5]*r.sigma[5]));
      integral[7]+=vm/1e6*dvol;}
   Tensor stress=r.sigma;
   for(int i=0;i<30;++i){localR[i]+=dvol*ice3d::ed::dot(B[i],stress);}
   if(makeMatrix){Tensor CB[30];
    for(int j=0;j<30;++j)for(int k=0;k<6;++k){double v=0;for(int l=0;l<6;++l)v+=r.tangent[k][l]*B[j][l];CB[j][k]=v;}
    for(int i=0;i<30;++i)for(int j=0;j<30;++j)
      localK[(i/3)*10+j/3][3*(i%3)+(j%3)]+=dvol*ice3d::ed::dot(B[i],CB[j]);
   }
  }
  for(int i=0;i<30;++i)w.A.f[3*t[i/3]+i%3]+=localR[i];
  if(makeMatrix)for(int i=0;i<10;++i)for(int j=0;j<10;++j){auto&glob=w.A.K.a[w.A.K.pos(t[i],t[j])];
     for(int k=0;k<9;++k)glob[k]+=localK[i*10+j][k];}
  if(needOutput){for(int k=0;k<8;++k)w.cell[e][k]=integral[k]/eVol;
    w.qp_peak[e]={peak/1e6,peakX.x,peakX.y,peakX.z,double(peakQ)};
  }
  if((e+1)%15000==0)cerr<<"integrated "<<e+1<<"/"<<m.tets.size()<<"\n"<<flush;
 }
 double res=0;for(size_t i=0;i<w.A.f.size();++i)if(!bc[i])res+=w.A.f[i]*w.A.f[i];
 w.normResidual=sqrt(res);w.j6=sum6/max(vol6,1e-40);w.jOmega=sumAll/max(volAll,1e-40);w.volume6=vol6;w.volume=volAll;w.maxSigma=maxStress;
 return w;
}

struct IterData{int n=0,totalCG=0;double residual=0,ratio=0, wall=0;};
IterData nonlinear_step(const Mesh&m,const vector<GaussQ>&quad,const vector<double>&T,Field&field,
                        double dt,const Setting&set,const vector<uint8_t>&bc,Work&completed){
 auto start=Clock::now();IterData res;double baseline=-1;
 for(int it=0;it<set.maxNewton;++it){
   auto w=assemble(m,quad,T,field,dt,set,bc,true,false);if(baseline<0)baseline=max(w.normResidual,1e-20);
   res.residual=w.normResidual;res.ratio=w.normResidual/baseline;
   cerr<<set.name<<"_"<<set.mod<<" Newton "<<it<<" residual="<<setprecision(9)<<res.residual<<" rel="<<res.ratio<<"\n"<<flush;
   if(res.ratio<set.newtonTol || w.normResidual<1e-10){res.n=it;completed=assemble(m,quad,T,field,dt,set,bc,false,true);field.qstate=move(completed.next);completed.next.clear();
    double normNow=completed.normResidual;if(normNow>1.2*max(set.newtonTol*baseline,1e-10))throw runtime_error("final equilibrium residual verification failed");
    res.wall=chrono::duration<double>(Clock::now()-start).count();return res;}
   // The global residual is internal force - external traction (zero). Compute the Newton increment.
   for(double&v:w.A.f)v=-v;
   vector<double>du;auto cg=solve(w.A,bc,du,set.cgTol,set.maxCG);res.totalCG+=cg.iterations;
   double lambda=1.;bool accepted=false;
   for(int ls=0;ls<9;++ls){Field trial=field;for(size_t i=0;i<trial.u.size();++i)trial.u[i]+=lambda*du[i];
     auto wl=assemble(m,quad,T,trial,dt,set,bc,false,false);
     if(wl.normResidual < (1-1e-4*lambda)*res.residual || wl.normResidual<1e-10){field.u=move(trial.u);accepted=true;break;}
     lambda*=.5;
   }
   if(!accepted)throw runtime_error("global Newton line search failed without state commit");
 }
 throw runtime_error("global Newton did not converge; history not committed");
}

// Restrained z translation via one numerical pin only; the weighted mean is subtracted from stored u afterwards.
double zeroMeanZ(const Mesh&m,const vector<GaussQ>&quad,Field&field){
 vector<double> nodalMass(m.nodes.size(),0.);
 double vol=0;
 for(const auto&t:m.tets)for(const auto&q:quad){
   V a{},b{},c{};
   for(int k=0;k<10;++k){a=a+m.nodes[t[k]]*q.d[k][0];b=b+m.nodes[t[k]]*q.d[k][1];c=c+m.nodes[t[k]]*q.d[k][2];}
   double dv=q.w*dot(a,cross(b,c));vol+=dv;
   for(int k=0;k<10;++k)nodalMass[t[k]]+=dv*q.N[k];
 }
 if(!(vol>0))throw runtime_error("non-positive integration volume for z gauge");
 double wz=0;for(size_t k=0;k<m.nodes.size();++k)wz+=nodalMass[k]*field.u[3*k+2];
 double shift=wz/vol;
 for(size_t k=0;k<m.nodes.size();++k)field.u[3*k+2]-=shift;
 double leftover=0;for(size_t k=0;k<m.nodes.size();++k)leftover+=nodalMass[k]*field.u[3*k+2];
 return leftover/vol;
}

long peakMemoryKB(){
#ifdef _WIN32
 return stage3d06_peak_memory_kb_windows();
#elif defined(__linux__)
 long peak=0;ifstream status("/proc/self/status");string line;
 while(getline(status,line))if(line.rfind("VmHWM:",0)==0){istringstream inp(line.substr(6));inp>>peak;break;}
 return peak;
#else
 return 0;
#endif
}

void checkpoint(const fs::path&where,const Mesh&m,const Setting&set,const Field&f,int step){
 fs::create_directories(where.parent_path());auto tmp=where;tmp+=".part";
 ofstream o(tmp,ios::binary|ios::trunc);if(!o)throw runtime_error("cannot write checkpoint");
 uint64_t magic=0x4943453344303602ull,n=m.nodes.size(),ng=f.qstate.size(),sig=signature(m);
 int32_t ord=set.quad, idx=step;uint32_t imode=(set.mod=="VAR"?1u:0u),law=(set.name=="E"?0u:set.name=="ED"?1u:2u);
 auto wr=[&](auto&v){o.write(reinterpret_cast<const char*>(&v),sizeof(v));};
 wr(magic);wr(n);wr(ng);wr(sig);wr(ord);wr(idx);wr(imode);wr(law);wr(f.lastTime);
 o.write(reinterpret_cast<const char*>(f.u.data()),f.u.size()*sizeof(double));
 o.write(reinterpret_cast<const char*>(f.qstate.data()),f.qstate.size()*sizeof(State));o.close();
 if(!o)throw runtime_error("checkpoint incomplete");
 if(fs::exists(where))fs::remove(where);fs::rename(tmp,where);
}
int restore(const fs::path&where,const Mesh&m,const Setting&set,Field&f){
 ifstream in(where,ios::binary);if(!in)throw runtime_error("missing resume checkpoint");
 uint64_t magic,n,ng,sig;int32_t ord,idx;uint32_t imode,law;double time;
 auto rd=[&](auto&v){in.read(reinterpret_cast<char*>(&v),sizeof(v));};
 rd(magic);rd(n);rd(ng);rd(sig);rd(ord);rd(idx);rd(imode);rd(law);rd(time);
 if(!in||magic!=0x4943453344303602ull||n!=m.nodes.size()||ng!=f.qstate.size()||sig!=signature(m)||ord!=set.quad||imode!=(set.mod=="VAR")||law!=(set.name=="E"?0u:set.name=="ED"?1u:2u))throw runtime_error("checkpoint header/model/mesh mismatch");
 in.read(reinterpret_cast<char*>(f.u.data()),f.u.size()*sizeof(double));
 in.read(reinterpret_cast<char*>(f.qstate.data()),f.qstate.size()*sizeof(State));
 if(!in)throw runtime_error("checkpoint truncated");char x;if(in.read(&x,1))throw runtime_error("checkpoint trailing bytes");
 if(idx<0)throw runtime_error("checkpoint invalid step");
 f.lastTime=time;return idx;
}

void save_fields(const Mesh&m,const vector<double>&dT,const Field&f,const Work&w,const fs::path&path,double time){
 ElementStats ev;ev.values=w.cell; // Compatible cell names + additional Psi diagnostic.
 save_mech_vtu(m,f.u,dT,ev,path,time,&w.qp_peak);
}

int main(int argc,char**argv){try{
 fs::path mesh,tempdir,out;string laws="ALL",mods="ALL",strTimes="900,1800,3600";Setting base;bool resume=false, postprocessOnly=false, finalVtuOnly=false;
 for(int i=1;i<argc;++i){string a=argv[i];auto val=[&](){if(i+1>=argc)throw runtime_error("Missing value for "+a);return string(argv[++i]);};
 if(a=="--mesh")mesh=val();else if(a=="--temp-dir")tempdir=val();else if(a=="--out")out=val();
 else if(a=="--law")laws=val();else if(a=="--modulus")mods=val();else if(a=="--times")strTimes=val();
 else if(a=="--quad")base.quad=stoi(val());else if(a=="--newton-tol")base.newtonTol=stod(val());
 else if(a=="--cg-tol")base.cgTol=stod(val());else if(a=="--resume")resume=true;else if(a=="--postprocess-only")postprocessOnly=true;else if(a=="--final-vtu-only")finalVtuOnly=true;
 else throw runtime_error("unknown argument: "+a);
 }
 if(mesh.empty()||tempdir.empty()||out.empty())throw runtime_error("Need --mesh MSH --temp-dir thermal_folder --out DIR");
 vector<int> times;{istringstream in(strTimes);string tok;while(getline(in,tok,',')){int t=stoi(tok);if(t<=0||(!times.empty()&&t<=times.back()))throw runtime_error("times not increasing");times.push_back(t);}}
 if(times.empty())throw runtime_error("no times");if(base.quad!=3&&base.quad!=4)throw runtime_error("quad 3 or 4");
 auto imported=read_msh(mesh);auto&m=imported.mesh;auto Q=volume_q(base.quad);auto bc=bc_candidate(m);
 fs::create_directories(out);cout<<"mesh nodes="<<m.nodes.size()<<" tet="<<m.tets.size()<<" q="<<Q.size()<<" hash="<<signature(m)<<"\n"<<flush;
 if(postprocessOnly){
  if(laws=="ALL"||mods=="ALL")throw runtime_error("postprocess-only requires one law and one modulus");
  Setting set=base;set.name=laws;set.mod=mods;
  const auto dest=out/(laws+"_"+mods);
  Field state;state.u.assign(3*m.nodes.size(),0);state.qstate.resize(m.tets.size()*Q.size());
  const int restored=restore(dest/"restart.bin",m,set,state);
  if(restored!=int(times.size()) || abs(state.lastTime-times.back())>1e-8)
    throw runtime_error("postprocess-only: checkpoint does not match requested time schedule");
  const auto dT=load_vtu_temp(m,tempdir/("thermal_"+to_string(times.back())+"s.vtu"));
  // dt=0 evaluates the *committed* stress at fixed e_d/e_v without evolving history.
  // The existing checkpoint and standard simulation fields are not modified.
  const Work w=assemble(m,Q,dT,state,0,set,bc,false,true);
  const auto path=dest/("qp_diagnostics_"+to_string(times.back())+"s.vtu");
  save_fields(m,dT,state,w,path,times.back());
  const auto summary=dest/("qp_diagnostics_"+to_string(times.back())+"s.csv");
  ofstream fout(summary);
  const V delta=w.maxX-V{0,0,.03};const double radius=norm(delta);
  fout<<"time_s,element_id_0based,qp_id_0based,x_m,y_m,z_m,r_mm,gap_from_pore_mm,QP_max_MPa,Phi6,PhiOmega\n";
  fout<<setprecision(16)<<times.back()<<","<<w.maxElement<<","<<w.maxQ<<","<<w.maxX.x<<","<<w.maxX.y<<","<<w.maxX.z<<","<<radius*1e3<<","<<(radius-RBASE)*1e3<<","<<w.maxSigma/1e6<<","<<w.j6<<","<<w.jOmega<<"\n";
  vector<size_t> order(m.tets.size());iota(order.begin(),order.end(),size_t(0));
  const size_t top=min(order.size(),size_t(100));
  partial_sort(order.begin(),order.begin()+top,order.end(),[&](size_t a,size_t b){return w.qp_peak[a][0]>w.qp_peak[b][0];});
  ofstream tops(dest/("qp_top100_"+to_string(times.back())+"s.csv"));
  tops<<"rank,element_id_0based,qp_id_0based,sigma1_QP_max_MPa,sigma1_element_volume_avg_MPa,x_m,y_m,z_m,r_mm,gap_from_pore_mm\n";
  for(size_t i=0;i<top;++i){size_t e=order[i];const auto&v=w.qp_peak[e];
   double r=norm(V{v[1],v[2],v[3]}-V{0,0,.03});
   tops<<setprecision(16)<<(i+1)<<","<<e<<","<<int(v[4])<<","<<v[0]<<","<<w.cell[e][6]<<","<<v[1]<<","<<v[2]<<","<<v[3]<<","<<r*1e3<<","<<(r-RBASE)*1e3<<"\n";
  }
  // Cross-check against the last stored history row, if present.
  const auto ts=dest/"time_series.csv";
  if(fs::exists(ts)){
    ifstream f(ts);string header,line,last;
    getline(f,header);
    while(getline(f,line)){if(!line.empty())last=line;}
    if(last.empty())throw runtime_error("postprocess: empty time history");
    istringstream in(last);string val;vector<double> row;
    while(getline(in,val,','))row.push_back(stod(val));
    if(row.size()<5 || abs(row[0]-times.back())>1e-9 ||
       abs(row[2]-w.j6)>2e-9 || abs(row[3]-w.jOmega)>2e-9 ||
       abs(row[4]-w.maxSigma/1e6)>2e-7)
      throw runtime_error("postprocess-only: checkpoint stresses disagree with stored time_series.csv");
  }
  cout<<"POSTPROCESS PASS: "<<laws<<"_"<<mods<<" t="<<times.back()
      <<" max_sigma1="<<setprecision(13)<<w.maxSigma/1e6
      <<" MPa, Phi6="<<w.j6<<", location=("<<w.maxX.x<<","<<w.maxX.y<<","<<w.maxX.z
      <<") m, gap="<<(radius-RBASE)*1e3<<" mm\n"
      <<"VTU: "<<path<<"\nCSV: "<<summary<<"\n"<<flush;
  return 0;
 }
 vector<vector<double>> thermal;for(int t:times){auto p=tempdir/("thermal_"+to_string(t)+"s.vtu");thermal.push_back(load_vtu_temp(m,p));}
 ofstream campaign(out/"G06_campaign.csv",ios::app);
 if(campaign.tellp()==0)campaign<<"law,modulus,time_s,dt_s,nodes,tet10,quad,Newton_steps,CG_steps,relative_residual,max_principal_MPa,Psi6,PsiOmega,volume6_m3,volume_m3,gauge_mean_uz_m,wall_seconds,max_local_NT,VmHWM_kB\n";
 for(string law: {"E","ED","EDV"}){if(laws!="ALL"&&laws!=law)continue;
  for(string mod:{"CONST","VAR"}){if(mods!="ALL"&&mods!=mod)continue;
    Setting set=base;set.name=law;set.mod=mod;
    auto dest=out/(law+"_"+mod);fs::create_directories(dest);
    Field state;state.u.assign(3*m.nodes.size(),0);state.qstate.resize(m.tets.size()*Q.size());
    int start=0;if(resume&&fs::exists(dest/"restart.bin")){
      start=restore(dest/"restart.bin",m,set,state);
      if(start>int(times.size())||(start>0 && abs(state.lastTime-times[start-1])>1e-8))
         throw runtime_error("checkpoint incompatible with requested time grid");
    }
    ofstream loc(dest/"max_location.csv",start?ios::app:ios::trunc);
    if(!start)loc<<"time_s,element_id_0based,qp_id_0based,x_m,y_m,z_m,r_from_pore_center_mm,distance_to_pore_surface_mm,sigma1_QP_max_MPa,sigma1_element_volume_avg_MPa,inside_fixed_B6\n";
    ofstream ts(dest/"time_series.csv",start?ios::app:ios::trunc);if(!start)ts<<"time_s,dt_s,Psi6,PsiOmega,maxS1_MPa,Newton,CG,residual_rel,wall_s\n";
    ofstream polar(dest/"polar_caps_history.csv",start?ios::app:ios::trunc);
    if(!start)polar<<"time_s,top_cap_mean_positive_sigma1_MPa,bottom_cap_mean_positive_sigma1_MPa,top_cap_volume_m3,bottom_cap_volume_m3\n";
    for(int k=start;k<int(times.size());++k){double dt=times[k]-state.lastTime;
     if(!(dt>0))throw runtime_error("non-positive dt; inconsistent checkpoint/time list");
     Work w;auto solveInfo=nonlinear_step(m,Q,thermal[k],state,dt,set,bc,w);
     double gaugeUz=zeroMeanZ(m,Q,state);
     state.lastTime=times[k];
     cout<<law<<" "<<mod<<" time="<<times[k]<<" Newton="<<solveInfo.n<<" CG="<<solveInfo.totalCG<<" residual="<<solveInfo.ratio
         <<" maxStress="<<w.maxSigma/1e6<<" Psi6="<<w.j6<<" PsiOmega="<<w.jOmega<<" wall="<<solveInfo.wall<<"\n"<<flush;
     ts<<setprecision(15)<<times[k]<<","<<dt<<","<<w.j6<<","<<w.jOmega<<","<<w.maxSigma/1e6<<","<<solveInfo.n<<","<<solveInfo.totalCG<<","<<solveInfo.ratio<<","<<solveInfo.wall<<"\n"<<flush;
     polar<<setprecision(15)<<times[k]<<","<<(w.polarTopVolume>0?w.polarTopStress/w.polarTopVolume:0)<<","<<(w.polarBottomVolume>0?w.polarBottomStress/w.polarBottomVolume:0)<<","<<w.polarTopVolume<<","<<w.polarBottomVolume<<"\n"<<flush;
     if(!finalVtuOnly || k==int(times.size())-1)save_fields(m,thermal[k],state,w,dest/("mechanics_"+to_string(times[k])+"s.vtu"),times[k]);
     const V dc=w.maxX-V{0,0,.03};const double radius=norm(dc);
     loc<<setprecision(16)<<times[k]<<","<<w.maxElement<<","<<w.maxQ<<","<<w.maxX.x<<","<<w.maxX.y<<","<<w.maxX.z<<","<<radius*1e3<<","<<(radius-RBASE)*1e3<<","<<w.maxSigma/1e6<<","<<w.cell.at(w.maxElement)[6]<<","<<(radius<.006?1:0)<<"\n"<<flush;
     // Detailed rankings of elementwise quadrature maxima, sampled at the final time only.
     if(k==int(times.size())-1){
       vector<size_t> order(m.tets.size());iota(order.begin(),order.end(),size_t(0));
       size_t top=min(order.size(),size_t(100));
       partial_sort(order.begin(),order.begin()+top,order.end(),[&](size_t a,size_t b){return w.qp_peak[a][0]>w.qp_peak[b][0];});
       ofstream topfile(dest/"top100_qp_max_3600s.csv");
       topfile<<"rank,element_id_0based,qp_id_0based,sigma1_QP_max_MPa,sigma1_element_volume_avg_MPa,x_m,y_m,z_m,r_from_pore_center_mm,gap_from_pore_surface_mm,in_fixed_B6\n";
       for(size_t rank=0;rank<top;++rank){size_t j=order[rank];const auto&v=w.qp_peak[j];
         double rad=norm(V{v[1],v[2],v[3]}-V{0,0,.03});
         topfile<<setprecision(16)<<(rank+1)<<","<<j<<","<<int(v[4])<<","<<v[0]<<","<<w.cell[j][6]<<","<<v[1]<<","<<v[2]<<","<<v[3]<<","<<rad*1e3<<","<<(rad-RBASE)*1e3<<","<<(rad<.006?1:0)<<"\n";
       }
     }
     checkpoint(dest/"restart.bin",m,set,state,k+1);
     long peak=peakMemoryKB();
     campaign<<setprecision(15)<<law<<","<<mod<<","<<times[k]<<","<<dt<<","<<m.nodes.size()<<","<<m.tets.size()<<","<<set.quad<<","<<solveInfo.n<<","<<solveInfo.totalCG<<","<<solveInfo.ratio<<","<<w.maxSigma/1e6<<","<<w.j6<<","<<w.jOmega<<","<<w.volume6<<","<<w.volume<<","<<gaugeUz<<","<<solveInfo.wall<<","<<w.maxLocalIterations<<","<<peak<<"\n"<<flush;
    }
  }
 }
 return 0;
 }catch(const exception&e){cerr<<"G06 FAILED: "<<e.what()<<"\n";return 2;}}
