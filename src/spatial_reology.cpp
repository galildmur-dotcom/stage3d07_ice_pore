// Stage 3D-06: 3D quasi-static direct E/ED/EDV solver, Tet10, matched thermal history.
// Stage3D06-P3: MC-SGS integration
// Tensor strains use true shear components, not engineering gamma.
#define STAGE3D06_LIBRARY
#include "p09e_temperature_io.hpp"
#include "mechanical.cpp"
#include "edv_material.hpp"
#include "stage3d09b_functionals.hpp"
#include "p09d_spatial_diagnostics.hpp"
#include "p09d2_local.hpp"
#include "p09d3_pair.hpp"
#include "checkpoint_chunked_io.hpp"
#include "p09e2_checkpoint_policy.hpp"
#include <bit>
#include <cstdint>
#include <ctime>
#include <sstream>
// Win32 API is isolated in a dedicated translation unit to avoid global
// Windows macros and RPC `byte` colliding with our C++20 material headers.
#ifdef _WIN32
extern "C" long stage3d06_peak_memory_kb_windows();
#endif

using State = ice3d::edv::State;
using Tensor = ice3d::edv::Tensor;
using ice3d::edv::Response;
using ice3d::ed::Modulus;

struct Setting {string name="EDV",mod="VAR";int quad=3;double newtonTol=2e-7, cgTol=2e-7;int maxNewton=12, maxCG=3500;bool extraFunctionals=false,p09dDiagnostic=false,p09d2Diagnostic=false,p09d3Diagnostic=false;int peakP=8;};
struct Field {vector<double> u; vector<State> qstate;double lastTime=0;};
struct Work {Assembled A;double normResidual=0,maxSigma=0,j6=0,jOmega=0,peakPower6=0,energy6=0,volume6=0,volume=0, freeReactionZ=0;double polarTopStress=0,polarBottomStress=0,polarTopVolume=0,polarBottomVolume=0;ice3d::p09d::Diagnostic p09d;ice3d::p09d2::Diagnostic p09d2;vector<ice3d::p09d2::HotElement> hot;vector<ice3d::p09d3::Point> p09d3qp;vector<array<double,8>> cell;vector<array<double,5>> qp_peak;vector<State> next;size_t maxElement=0,maxQ=0;V maxX{};int maxLocalIterations=0;};
static double quad_sigma_ref=9.5e9*(149e-6/3.)*3./(1.-.35);
// Stage3D06-P: settings are algorithmic only; the model, quadrature and j6 are unchanged.
struct P06GeometryQP {
 double dv=0;
 double grad[10][3]{};
 V position{};
};
struct P06NewtonEvent{int iteration=0,cg=0;double residual=0,ratio=0,assembly_s=0,pcg_s=0,line_s=0;};
struct P06Runtime {
 bool optimized=true,profile=false,cacheGeometry=false,parallelAssembly=false;
 vector<P06GeometryQP> geometry;
 vector<uint8_t> inB6;
 double tGeometrySetup=0;
 vector<P06NewtonEvent> newtonEvents;
 shared_ptr<const BCSRTopology> graph;
 vector<double> gaugeMass;
 double gaugeVolume=0;
 double tGraph=0,tAssembly=0,tEDV=0,tGeometry=0,tScatter=0,tCG=0,tLine=0,tGauge=0,tOutput=0,tCheckpoint=0;
 long cgCalls=0;
 void clear_step(){tAssembly=tEDV=tGeometry=tScatter=tCG=tLine=tGauge=tOutput=tCheckpoint=0;cgCalls=0;
  newtonEvents.clear();stage06_cg_details.clear();}
};
static P06Runtime p06;
static double p06elapsed(Clock::time_point start){return chrono::duration<double>(Clock::now()-start).count();}


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

Work assemble_parallel(const Mesh&,const vector<GaussQ>&,const vector<double>&,const Field&,
 double,const Setting&,const vector<uint8_t>&,bool,bool,const vector<double>*);
Work assemble(const Mesh&m,const vector<GaussQ>&quadrature,const vector<double>&T,const Field&f,
              double dt,const Setting&set,const vector<uint8_t>&bc,bool makeMatrix,bool needOutput,const vector<double>* trialDisplacement=nullptr){
 if(p06.parallelAssembly)return assemble_parallel(m,quadrature,T,f,dt,set,bc,makeMatrix,needOutput,trialDisplacement);
 const auto tAssemblyStart=Clock::now();
 Work w;const size_t nq=quadrature.size();size_t ng=m.tets.size()*nq;
 const auto& currentU=trialDisplacement?*trialDisplacement:f.u;
 if(f.qstate.size()!=ng)throw runtime_error("quadrature history size mismatch");
 if(makeMatrix){if(p06.optimized&&p06.graph)w.A.K.set_topology(p06.graph);else w.A.K.init(m);}
 w.A.f.assign(3*m.nodes.size(),0);w.A.massN.assign(m.nodes.size(),0);
 if(needOutput){w.next.resize(ng);w.cell.resize(m.tets.size());w.qp_peak.resize(m.tets.size());if(set.p09d2Diagnostic)w.hot.resize(m.tets.size());if(set.p09d3Diagnostic)w.p09d3qp.resize(ng);}
 auto controls=ice3d::edv::Controls{set.name!="E",set.name=="EDV"};
 auto md=(set.mod=="CONST"?Modulus::CONST:Modulus::VAR);
 double sum6=0,sumAll=0,peakPower6=0,energy6=0,vol6=0,volAll=0, maxStress=-1e99;
 for(size_t e=0;e<m.tets.size();++e){const auto&t=m.tets[e];
  // Conforming Gmsh internal B6 interface: classify by element centroid.
  V center{};if(p06.geometry.empty()){for(int j=0;j<4;++j)center=center+m.nodes[t[j]]*.25;}
  bool in6=p06.inB6.empty()?norm(center-V{0,0,.03})<.006:p06.inB6[e];
  array<array<double,9>,100> localK{};array<double,30> localR{};
  array<double,8> integral{};double eVol=0;double peak=-1e99;int peakQ=-1;V peakX{};
  for(size_t iq=0;iq<nq;++iq){auto geoStart=Clock::now();const auto&b=quadrature[iq];double tk=ice3d::ed::T_ref;
   for(int j=0;j<10;++j)tk+=b.N[j]*T[t[j]];
   double dvol=0;double grad[10][3];
   if(!p06.geometry.empty()){
     const auto&g=p06.geometry[e*nq+iq];dvol=g.dv;
     memcpy(grad,g.grad,sizeof(grad));
   }else{
     V dr{},ds{},dz{};
     for(int j=0;j<10;++j){auto x=m.nodes[t[j]];dr=dr+x*b.d[j][0];ds=ds+x*b.d[j][1];dz=dz+x*b.d[j][2];}
     V c0=cross(ds,dz),c1=cross(dz,dr),c2=cross(dr,ds);double det=dot(dr,c0);
     if(!(det>0))throw runtime_error("negative Jacobian at element "+to_string(e));
     dvol=b.w*det;
     for(int j=0;j<10;++j){V G=(c0*b.d[j][0]+c1*b.d[j][1]+c2*b.d[j][2])/det;grad[j][0]=G.x;grad[j][1]=G.y;grad[j][2]=G.z;}
   }
   volAll+=dvol;eVol+=dvol;if(in6)vol6+=dvol;
   if(makeMatrix)for(int j=0;j<10;++j)w.A.massN[t[j]]+=dvol*b.N[j];
   Tensor eps{}; Tensor B[30];
   for(int a=0;a<10;++a)for(int dir=0;dir<3;++dir){int ix=3*a+dir;basis(grad[a],dir,B[ix]);double u=currentU[3*t[a]+dir];for(int j=0;j<6;++j)eps[j]+=B[ix][j]*u;}
   if(p06.profile)p06.tGeometry+=p06elapsed(geoStart);
   auto edvStart=Clock::now();
   Response r=ice3d::edv::update(eps,tk,dt,f.qstate[e*nq+iq],md,controls);
   if(p06.profile)p06.tEDV+=p06elapsed(edvStart);
   w.maxLocalIterations=max(w.maxLocalIterations,r.iterations);
   if(needOutput)w.next[e*nq+iq]=r.new_state;
   double ps=0;if(needOutput){ps=psi(r.sigma);sumAll+=dvol*ps;if(in6)sum6+=dvol*ps;
      const auto eigenvalues=eigh3(r.sigma);const double s1=eigenvalues[0];
      if(set.extraFunctionals&&in6){peakPower6+=dvol*ice3d::p09b::peak_power(eigenvalues,quad_sigma_ref,set.peakP);energy6+=dvol*r.free_energy;}
      V qpos{};
      if(!p06.geometry.empty())qpos=p06.geometry[e*nq+iq].position;
      else for(int j=0;j<10;++j)qpos=qpos+m.nodes[t[j]]*b.N[j];
      if(in6&&(set.p09dDiagnostic||set.p09d2Diagnostic||set.p09d3Diagnostic)){
       const double rad_mm=1000.*norm(qpos-V{0,0,.03});
       if(set.p09dDiagnostic)ice3d::p09d::accumulate(w.p09d,rad_mm,dvol,eigenvalues,quad_sigma_ref,ps,r.free_energy);
       if(set.p09d2Diagnostic)ice3d::p09d2::accumulate(w.p09d2,w.hot[e],rad_mm,dvol,eigenvalues,quad_sigma_ref,ps,r.free_energy);
       if(set.p09d3Diagnostic)w.p09d3qp[e*nq+iq]=ice3d::p09d3::point(rad_mm,dvol,eigenvalues,quad_sigma_ref);
      }
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
  auto scatterStart=Clock::now();
  for(int i=0;i<30;++i)w.A.f[3*t[i/3]+i%3]+=localR[i];
  if(makeMatrix)for(int i=0;i<10;++i)for(int j=0;j<10;++j){auto&glob=w.A.K.a[(p06.optimized&&p06.graph)?p06.graph->elementPositions[e][i*10+j]:w.A.K.pos(t[i],t[j])];
     for(int k=0;k<9;++k)glob[k]+=localK[i*10+j][k];}
  if(p06.profile)p06.tScatter+=p06elapsed(scatterStart);
  if(needOutput){for(int k=0;k<8;++k)w.cell[e][k]=integral[k]/eVol;
    w.qp_peak[e]={peak/1e6,peakX.x,peakX.y,peakX.z,double(peakQ)};
  }
  if((e+1)%15000==0)cerr<<"integrated "<<e+1<<"/"<<m.tets.size()<<"\n"<<flush;
 }
 double res=0;for(size_t i=0;i<w.A.f.size();++i)if(!bc[i])res+=w.A.f[i]*w.A.f[i];
 w.normResidual=sqrt(res);w.j6=sum6/max(vol6,1e-40);w.jOmega=sumAll/max(volAll,1e-40);
 w.peakPower6=peakPower6/max(vol6,1e-40);w.energy6=energy6/max(vol6,1e-40);w.volume6=vol6;w.volume=volAll;w.maxSigma=maxStress;
 if(p06.profile)p06.tAssembly+=p06elapsed(tAssemblyStart);
 return w;
}

// Race-free OpenMP FEM assembly: evaluate distinct elements in parallel in bounded
// batches; scatter stiffness/RHS and reduce all observables in ORIGINAL element/QP
// order on one thread. Never atomically update global BCSR entries or EDV history.
Work assemble_parallel(const Mesh&m,const vector<GaussQ>&quadrature,const vector<double>&T,
    const Field&f,double dt,const Setting&set,const vector<uint8_t>&bc,
    bool makeMatrix,bool needOutput,const vector<double>*trialDisplacement){
 const auto assemblyStart=Clock::now();const size_t nq=quadrature.size(), ne=m.tets.size();
 if(nq>64||f.qstate.size()!=ne*nq)throw runtime_error("parallel QP layout mismatch");
 const auto& u=trialDisplacement?*trialDisplacement:f.u;
 Work w;if(makeMatrix){if(p06.optimized&&p06.graph)w.A.K.set_topology(p06.graph);else w.A.K.init(m);}
 w.A.f.assign(3*m.nodes.size(),0);w.A.massN.assign(m.nodes.size(),0);
 if(needOutput){w.next.resize(ne*nq);w.cell.resize(ne);w.qp_peak.resize(ne);if(set.p09d2Diagnostic)w.hot.resize(ne);if(set.p09d3Diagnostic)w.p09d3qp.resize(ne*nq);}
 const auto controls=ice3d::edv::Controls{set.name!="E",set.name=="EDV"};
 const auto md=(set.mod=="CONST"?Modulus::CONST:Modulus::VAR);
 struct Local {
  array<array<double,9>,100> K{};
  array<double,30> R{};
  array<double,10> mass{};
  array<double,8> integral{};
  ice3d::p09d::Diagnostic p09d;
  ice3d::p09d2::Diagnostic p09d2;ice3d::p09d2::HotElement hot;
  array<double,64> volumes{},weightedPsi{},weightedPeak{},weightedEnergy{},polarT{},polarB{},polarTV{},polarBV{};
  double eVol=0,peak=-1e99,tEDV=0,tGeometry=0;
  std::exception_ptr failure;
  int maxIter=0,peakQ=-1;
  V peakX{};
 };
 double sum6=0,sumAll=0,peakPower6=0,energy6=0,vol6=0,volAll=0,maxStress=-1e99;
 constexpr size_t batchSize=512;
 vector<Local> scratch(batchSize);
 for(size_t first=0;first<ne;first+=batchSize){
  const size_t count=min(batchSize,ne-first);
  #ifdef _OPENMP
  #pragma omp parallel for schedule(static) if(count>1)
  #endif
  for(int ii=0;ii<int(count);++ii){
   const size_t e=first+size_t(ii);const auto&t=m.tets[e];Local&l=scratch[size_t(ii)];l=Local{};
   try {for(size_t iq=0;iq<nq;++iq){
    const auto geoBegin=Clock::now();const auto&b=quadrature[iq];double tk=ice3d::ed::T_ref;
    for(int j=0;j<10;++j)tk+=b.N[j]*T[t[j]];
    double dv=0,grad[10][3];
    if(!p06.geometry.empty()){
     const auto&geo=p06.geometry[e*nq+iq];dv=geo.dv;memcpy(grad,geo.grad,sizeof(grad));
    }else{
     V dr{},ds{},dz{};
     for(int j=0;j<10;++j){auto x=m.nodes[t[j]];dr=dr+x*b.d[j][0];ds=ds+x*b.d[j][1];dz=dz+x*b.d[j][2];}
     V c0=cross(ds,dz),c1=cross(dz,dr),c2=cross(dr,ds);double det=dot(dr,c0);
     if(!(det>0)){
       // The sequential path performs the same detJ check; exceptions cannot cross OpenMP.
       dv=-1;continue;
     }
     dv=b.w*det;
     for(int j=0;j<10;++j){V G=(c0*b.d[j][0]+c1*b.d[j][1]+c2*b.d[j][2])/det;
      grad[j][0]=G.x;grad[j][1]=G.y;grad[j][2]=G.z;}
    }
    l.volumes[iq]=dv;l.eVol+=dv;
    if(makeMatrix)for(int j=0;j<10;++j)l.mass[j]+=dv*b.N[j];
    Tensor eps{},B[30];
    for(int a=0;a<10;++a)for(int dir=0;dir<3;++dir){int ix=3*a+dir;basis(grad[a],dir,B[ix]);
      double dis=u[3*t[a]+dir];for(int j=0;j<6;++j)eps[j]+=B[ix][j]*dis;}
    if(p06.profile)l.tGeometry+=p06elapsed(geoBegin);
    auto materialBegin=Clock::now();
    const Response r=ice3d::edv::update(eps,tk,dt,f.qstate[e*nq+iq],md,controls);
    if(p06.profile)l.tEDV+=p06elapsed(materialBegin);
    l.maxIter=max(l.maxIter,r.iterations);
    if(needOutput){
      w.next[e*nq+iq]=r.new_state;
      const double ps=psi(r.sigma);l.weightedPsi[iq]=dv*ps;
      const auto eigenvalues=eigh3(r.sigma);const double s1=eigenvalues[0];
      if(set.extraFunctionals){l.weightedPeak[iq]=dv*ice3d::p09b::peak_power(eigenvalues,quad_sigma_ref,set.peakP);l.weightedEnergy[iq]=dv*r.free_energy;}
      V qp{};if(!p06.geometry.empty())qp=p06.geometry[e*nq+iq].position;
      else for(int j=0;j<10;++j)qp=qp+m.nodes[t[j]]*b.N[j];
      if(set.p09dDiagnostic||set.p09d2Diagnostic||set.p09d3Diagnostic){
       const double rad_mm=1000.*norm(qp-V{0,0,.03});
       if(set.p09dDiagnostic)ice3d::p09d::accumulate(l.p09d,rad_mm,dv,eigenvalues,quad_sigma_ref,ps,r.free_energy);
       if(set.p09d2Diagnostic)ice3d::p09d2::accumulate(l.p09d2,l.hot,rad_mm,dv,eigenvalues,quad_sigma_ref,ps,r.free_energy);
       if(set.p09d3Diagnostic)w.p09d3qp[e*nq+iq]=ice3d::p09d3::point(rad_mm,dv,eigenvalues,quad_sigma_ref);
      }
      const V delta=qp-V{0,0,.03};const double rr=norm(delta);
      if(rr>=RBASE&&rr<=RBASE+.00030&&rr>0){constexpr double cos25=.9063077870366499;
       if(delta.z/rr>=cos25){l.polarT[iq]=dv*max(0.,s1/1e6);l.polarTV[iq]=dv;}
       if(delta.z/rr<=-cos25){l.polarB[iq]=dv*max(0.,s1/1e6);l.polarBV[iq]=dv;}}
      if(s1>l.peak){l.peak=s1;l.peakQ=int(iq);l.peakX=qp;}
      for(int k=0;k<6;++k)l.integral[k]+=r.sigma[k]/1e6*dv;
      l.integral[6]+=eigh3(r.sigma)[0]/1e6*dv;
      const double vm=sqrt(.5*(pow(r.sigma[0]-r.sigma[1],2)+pow(r.sigma[1]-r.sigma[2],2)+pow(r.sigma[2]-r.sigma[0],2))
                      +3*(r.sigma[3]*r.sigma[3]+r.sigma[4]*r.sigma[4]+r.sigma[5]*r.sigma[5]));
      l.integral[7]+=vm/1e6*dv;
    }
    const Tensor stress=r.sigma;
    for(int i=0;i<30;++i)l.R[i]+=dv*ice3d::ed::dot(B[i],stress);
    if(makeMatrix){Tensor CB[30];
      for(int j=0;j<30;++j)for(int k=0;k<6;++k){double v=0;for(int n=0;n<6;++n)v+=r.tangent[k][n]*B[j][n];CB[j][k]=v;}
      for(int i=0;i<30;++i)for(int j=0;j<30;++j)
       l.K[(i/3)*10+j/3][3*(i%3)+(j%3)]+=dv*ice3d::ed::dot(B[i],CB[j]);
    }
   }
   }catch(...){l.failure=std::current_exception();}
  }
  // Exactly the baseline traversal for vector/matrix assembly and scalar accumulation.
  const auto scatterStart=Clock::now();
  for(size_t ii=0;ii<count;++ii){const size_t e=first+ii;const auto&t=m.tets[e];const auto&l=scratch[ii];
   if(l.failure)std::rethrow_exception(l.failure);
   w.maxLocalIterations=max(w.maxLocalIterations,l.maxIter);
   if(p06.profile){p06.tEDV+=l.tEDV;p06.tGeometry+=l.tGeometry;}
   V ctr{};if(p06.inB6.empty())for(int j=0;j<4;++j)ctr=ctr+m.nodes[t[j]]*.25;
   const bool in6=p06.inB6.empty()?norm(ctr-V{0,0,.03})<.006:bool(p06.inB6[e]);
   for(size_t iq=0;iq<nq;++iq){const double dv=l.volumes[iq];if(!(dv>0))throw runtime_error("Invalid detJ in parallel assembly at tet "+to_string(e));
    volAll+=dv;if(in6)vol6+=dv;
    if(needOutput){sumAll+=l.weightedPsi[iq];if(in6){sum6+=l.weightedPsi[iq];if(set.extraFunctionals){peakPower6+=l.weightedPeak[iq];energy6+=l.weightedEnergy[iq];}}
     w.polarTopStress+=l.polarT[iq];w.polarTopVolume+=l.polarTV[iq];
     w.polarBottomStress+=l.polarB[iq];w.polarBottomVolume+=l.polarBV[iq];}}
   if(needOutput&&in6){
    if(set.p09dDiagnostic)ice3d::p09d::merge(w.p09d,l.p09d);
    if(set.p09d2Diagnostic){ice3d::p09d2::merge(w.p09d2,l.p09d2);w.hot[e]=l.hot;}
   }
   for(int i=0;i<30;++i)w.A.f[3*t[i/3]+i%3]+=l.R[i];
   if(makeMatrix){
    for(int j=0;j<10;++j)w.A.massN[t[j]]+=l.mass[j];
    for(int i=0;i<10;++i)for(int j=0;j<10;++j){
     auto&global=w.A.K.a[(p06.optimized&&p06.graph)?p06.graph->elementPositions[e][i*10+j]:w.A.K.pos(t[i],t[j])];
     for(int k=0;k<9;++k)global[k]+=l.K[i*10+j][k];}}
   if(needOutput){for(int k=0;k<8;++k)w.cell[e][k]=l.integral[k]/l.eVol;
    w.qp_peak[e]={l.peak/1e6,l.peakX.x,l.peakX.y,l.peakX.z,double(l.peakQ)};
    if(l.peak>maxStress){maxStress=l.peak;w.maxElement=e;w.maxQ=size_t(l.peakQ);w.maxX=l.peakX;}}
  }
  if(p06.profile)p06.tScatter+=p06elapsed(scatterStart);
 }
 double residual2=0;for(size_t i=0;i<w.A.f.size();++i)if(!bc[i])residual2+=w.A.f[i]*w.A.f[i];
 w.normResidual=sqrt(residual2);
 w.j6=sum6/max(vol6,1e-40);w.jOmega=sumAll/max(volAll,1e-40);
 w.peakPower6=peakPower6/max(vol6,1e-40);w.energy6=energy6/max(vol6,1e-40);
 w.volume6=vol6;w.volume=volAll;w.maxSigma=maxStress;
 if(p06.profile)p06.tAssembly+=p06elapsed(assemblyStart);
 return w;
}

struct IterData{int n=0,totalCG=0;double residual=0,ratio=0, wall=0;};
IterData nonlinear_step(const Mesh&m,const vector<GaussQ>&quad,const vector<double>&T,Field&field,
                        double dt,const Setting&set,const vector<uint8_t>&bc,Work&completed){
 auto start=Clock::now();IterData res;double baseline=-1;
 for(int it=0;it<set.maxNewton;++it){
   const double oldAssembly=p06.tAssembly;const double oldPCG=p06.tCG;const double oldLine=p06.tLine;
   auto w=assemble(m,quad,T,field,dt,set,bc,true,false);if(baseline<0)baseline=max(w.normResidual,1e-20);
   res.residual=w.normResidual;res.ratio=w.normResidual/baseline;
   if(p06.profile)p06.newtonEvents.push_back({it,0,res.residual,res.ratio,p06.tAssembly-oldAssembly,0,0});
   cerr<<set.name<<"_"<<set.mod<<" Newton "<<it<<" residual="<<setprecision(9)<<res.residual<<" rel="<<res.ratio<<"\n"<<flush;
   if(res.ratio<set.newtonTol || w.normResidual<1e-10){res.n=it;completed=assemble(m,quad,T,field,dt,set,bc,false,true);field.qstate=move(completed.next);completed.next.clear();
    double normNow=completed.normResidual;if(normNow>1.2*max(set.newtonTol*baseline,1e-10))throw runtime_error("final equilibrium residual verification failed");
    res.wall=chrono::duration<double>(Clock::now()-start).count();return res;}
   // The global residual is internal force - external traction (zero). Compute the Newton increment.
   for(double&v:w.A.f)v=-v;
   vector<double>du;auto cgStart=Clock::now();auto cg=solve(w.A,bc,du,set.cgTol,set.maxCG);
   if(p06.profile){p06.tCG+=p06elapsed(cgStart);++p06.cgCalls;
     p06.newtonEvents.back().cg=cg.iterations;
     p06.newtonEvents.back().pcg_s=p06.tCG-oldPCG;}
   res.totalCG+=cg.iterations;
   double lambda=1.;bool accepted=false;auto lineStart=Clock::now();
   for(int ls=0;ls<9;++ls){
     vector<double> trialU=field.u;
     for(size_t i=0;i<trialU.size();++i)trialU[i]+=lambda*du[i];
     auto wl=assemble(m,quad,T,field,dt,set,bc,false,false,&trialU);
     if(wl.normResidual < (1-1e-4*lambda)*res.residual || wl.normResidual<1e-10){field.u=move(trialU);accepted=true;break;}
     lambda*=.5;
   }
   if(p06.profile){p06.tLine+=p06elapsed(lineStart);p06.newtonEvents.back().line_s=p06.tLine-oldLine;}
   if(!accepted)throw runtime_error("global Newton line search failed without state commit");
 }
 throw runtime_error("global Newton did not converge; history not committed");
}

// Restrained z translation via one numerical pin only; the weighted mean is subtracted from stored u afterwards.
double zeroMeanZ(const Mesh&m,const vector<GaussQ>&quad,Field&field){
 if(p06.optimized&&!p06.gaugeMass.empty()){
  double wz=0;for(size_t k=0;k<m.nodes.size();++k)wz+=p06.gaugeMass[k]*field.u[3*k+2];
  const double shift=wz/p06.gaugeVolume;
  for(size_t k=0;k<m.nodes.size();++k)field.u[3*k+2]-=shift;
  double leftover=0;for(size_t k=0;k<m.nodes.size();++k)leftover+=p06.gaugeMass[k]*field.u[3*k+2];
  return leftover/p06.gaugeVolume;
 }
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
 const auto startCheckpointIO=Clock::now();
 const std::uint64_t ubytes=std::uint64_t(f.u.size())*sizeof(double);
 const std::uint64_t statebytes=std::uint64_t(f.qstate.size())*sizeof(State);
 cerr<<"[P09D5 CHECKPOINT] start displacement_bytes="<<ubytes
     <<" state_bytes="<<statebytes<<"\n"<<flush;
 ice3d::checkpoint_io::write_bytes(o,f.u.data(),ubytes);
 ice3d::checkpoint_io::write_bytes(o,f.qstate.data(),statebytes,"EDV history");
 o.close();
 cerr<<"[P09D5 CHECKPOINT] writing finished seconds="
     <<chrono::duration<double>(Clock::now()-startCheckpointIO).count()<<"\n"<<flush;
 if(!o)throw runtime_error("checkpoint incomplete");
 if(fs::exists(where))fs::remove(where);fs::rename(tmp,where);
}
int restore(const fs::path&where,const Mesh&m,const Setting&set,Field&f){
 ifstream in(where,ios::binary);if(!in)throw runtime_error("missing resume checkpoint");
 uint64_t magic,n,ng,sig;int32_t ord,idx;uint32_t imode,law;double time;
 auto rd=[&](auto&v){in.read(reinterpret_cast<char*>(&v),sizeof(v));};
 rd(magic);rd(n);rd(ng);rd(sig);rd(ord);rd(idx);rd(imode);rd(law);rd(time);
 if(!in||magic!=0x4943453344303602ull||n!=m.nodes.size()||ng!=f.qstate.size()||sig!=signature(m)||ord!=set.quad||imode!=(set.mod=="VAR")||law!=(set.name=="E"?0u:set.name=="ED"?1u:2u))throw runtime_error("checkpoint header/model/mesh mismatch");
 ice3d::checkpoint_io::read_bytes(in,f.u.data(),std::uint64_t(f.u.size())*sizeof(double));
 ice3d::checkpoint_io::read_bytes(in,f.qstate.data(),std::uint64_t(f.qstate.size())*sizeof(State));
 if(!in)throw runtime_error("checkpoint truncated");char x;if(in.read(&x,1))throw runtime_error("checkpoint trailing bytes");
 if(idx<0)throw runtime_error("checkpoint invalid step");
 f.lastTime=time;return idx;
}

#include "stage3d10h_retained_history.hpp"

void save_fields(const Mesh&m,const vector<double>&dT,const Field&f,const Work&w,const fs::path&path,double time){
 ElementStats ev;ev.values=w.cell; // Compatible cell names + additional Psi diagnostic.
 save_mech_vtu(m,f.u,dT,ev,path,time,&w.qp_peak);
}

#ifndef STAGE3D07D_LIBRARY
int main(int argc,char**argv){try{
 fs::path mesh,tempdir,out;string laws="ALL",mods="ALL",strTimes="900,1800,3600";Setting base;bool resume=false, postprocessOnly=false, finalVtuOnly=false;string vtuMode="";int requestedThreads=0;double checkpointHours=0.0;
 ice3d::p10h::Budget adjointRetention;
 bool adjointBudgetSpecified=false;
 for(int i=1;i<argc;++i){string a=argv[i];auto val=[&](){if(i+1>=argc)throw runtime_error("Missing value for "+a);return string(argv[++i]);};
 if(a=="--mesh")mesh=val();else if(a=="--temp-dir")tempdir=val();else if(a=="--out")out=val();
 else if(a=="--law")laws=val();else if(a=="--modulus")mods=val();else if(a=="--times")strTimes=val();
 else if(a=="--quad")base.quad=stoi(val());
 else if(a=="--functionals") {auto m=val();if(m!="triple")throw runtime_error("--functionals triple");base.extraFunctionals=true;}
 else if(a=="--p09d-diagnostic") {base.p09dDiagnostic=true;base.extraFunctionals=true;}
 else if(a=="--p09d2-diagnostic") {base.p09dDiagnostic=true;base.p09d2Diagnostic=true;base.extraFunctionals=true;}
 else if(a=="--p09d3-diagnostic") {base.p09d3Diagnostic=true;base.extraFunctionals=true;}
 else if(a=="--peak-p") {base.peakP=stoi(val());if(base.peakP!=4&&base.peakP!=8&&base.peakP!=12)throw runtime_error("--peak-p 4|8|12");}
 else if(a=="--profile")p06.profile=true;
 else if(a=="--parallel-assembly") {auto v=val();if(v!="on"&&v!="off")throw runtime_error("--parallel-assembly on|off");p06.parallelAssembly=(v=="on");}
 else if(a=="--geometry-cache") {auto v=val();if(v!="on"&&v!="off")throw runtime_error("--geometry-cache on|off");p06.cacheGeometry=(v=="on");}
 else if(a=="--optimization") {auto v=val();if(v!="on"&&v!="off")throw runtime_error("--optimization on|off");p06.optimized=(v=="on");}
 else if(a=="--preconditioner") {auto v=val();if(v!="jacobi"&&v!="sgs"&&v!="mcsgs"&&v!="mcsgs-fast"&&v!="ic0"&&v!="as0"&&v!="as1")throw runtime_error("--preconditioner jacobi|sgs|mcsgs|mcsgs-fast|ic0|as0|as1");stage06_sgs=(v=="sgs");stage06_mcsgs=(v=="mcsgs"||v=="mcsgs-fast");stage06_mcsgs_fast=(v=="mcsgs-fast");stage06_ic0=(v=="ic0");stage06_schwarz_overlap=(v=="as0"?0:v=="as1"?1:-1);}
 else if(a=="--spmv") {auto v=val();if(v!="legacy"&&v!="projected")throw runtime_error("--spmv legacy|projected");stage06_p2_projected_spmv=(v=="projected");}
 else if(a=="--schwarz-core")stage06_schwarz_core=stoi(val());
 else if(a=="--threads")requestedThreads=stoi(val());else if(a=="--newton-tol")base.newtonTol=stod(val());
 else if(a=="--vtu") {vtuMode=val();if(vtuMode!="none"&&vtuMode!="final"&&vtuMode!="all")throw runtime_error("P09E: --vtu none|final|all");}
 else if(a=="--checkpoint-hours")checkpointHours=stod(val());
 else if(a=="--adjoint-snapshot-steps")adjointRetention.interval=stoi(val());
 else if(a=="--adjoint-max-disk-gb"){adjointRetention.max_gib=stod(val());adjointBudgetSpecified=true;}
 else if(a=="--cg-tol")base.cgTol=stod(val());else if(a=="--resume")resume=true;else if(a=="--postprocess-only")postprocessOnly=true;else if(a=="--final-vtu-only")finalVtuOnly=true;
 else throw runtime_error("unknown argument: "+a);
 }
 #ifdef _OPENMP
 if(requestedThreads>0){if(requestedThreads>32)throw runtime_error("threads must be 1..32");omp_set_dynamic(0);omp_set_num_threads(requestedThreads);}
 #else
 if(requestedThreads>1)throw runtime_error("OpenMP support not built; --threads 1 only");
 #endif
 ice3d::p09e2::should_checkpoint(checkpointHours,0,false); // validate input
 if(adjointRetention.interval<0)throw runtime_error("P10H snapshot period must be >=0");
 if(adjointRetention.interval==0&&adjointBudgetSpecified)
  throw runtime_error("P10H disk budget requires --adjoint-snapshot-steps");
 if(adjointRetention.interval>0&&
   (resume||postprocessOnly||laws=="ALL"||mods=="ALL"))
  throw runtime_error("P10H initial integration: snapshots require one law/modulus and no --resume or --postprocess-only");
 if(stage06_schwarz_core<1||stage06_schwarz_core>1024)throw runtime_error("--schwarz-core must be 1..1024");
 stage06_cg_profile=p06.profile;
 // This fast SpMV mode is a solver implementation choice, not a model change.
 if(stage06_p2_projected_spmv && (stage06_sgs || stage06_mcsgs || stage06_ic0 || stage06_schwarz_overlap>=0))
  cerr<<"Projected SpMV with symmetric preconditioning: constrained CG vectors remain zero.\n";

 if(mesh.empty()||tempdir.empty()||out.empty())throw runtime_error("Need --mesh MSH --temp-dir thermal_folder --out DIR");
 vector<int> times;{istringstream in(strTimes);string tok;while(getline(in,tok,',')){int t=stoi(tok);if(t<=0||(!times.empty()&&t<=times.back()))throw runtime_error("times not increasing");times.push_back(t);}}
 if(times.empty())throw runtime_error("no times");if(base.quad!=3&&base.quad!=4)throw runtime_error("quad 3 or 4");
 auto imported=read_msh(mesh);auto&m=imported.mesh;auto Q=volume_q(base.quad);auto bc=bc_candidate(m);
 if(adjointRetention.interval>0){
  const auto bytes=ice3d::p10h::estimated_total(adjointRetention,m,Q.size(),int(times.size()));
  cerr<<"[P10H] named adjoint-history snapshots enabled, interval_steps="
      <<adjointRetention.interval<<" estimated_total_gib="
      <<double(bytes)/(1024.*1024.*1024.)<<" max_gib="
      <<adjointRetention.max_gib<<" (legacy restart.bin unchanged)\n"<<flush;
 }
 if(p06.optimized){auto start=Clock::now();p06.graph=build_bcsr_topology(m);p06.tGraph=p06elapsed(start);}
 if(p06.optimized&&p06.cacheGeometry){
   auto geoBegin=Clock::now();p06.geometry.resize(m.tets.size()*Q.size());p06.inB6.resize(m.tets.size());
   for(size_t e=0;e<m.tets.size();++e){const auto&t=m.tets[e];V center{};
    for(int j=0;j<4;++j)center=center+m.nodes[t[j]]*.25;
    p06.inB6[e]=(norm(center-V{0,0,.03})<.006);
    for(size_t iq=0;iq<Q.size();++iq){const auto&b=Q[iq];auto&g=p06.geometry[e*Q.size()+iq];
     V dr{},ds{},dz{};
     for(int j=0;j<10;++j){const auto x=m.nodes[t[j]];dr=dr+x*b.d[j][0];ds=ds+x*b.d[j][1];dz=dz+x*b.d[j][2];}
     V c0=cross(ds,dz),c1=cross(dz,dr),c2=cross(dr,ds);double det=dot(dr,c0);
     if(!(det>0))throw runtime_error("negative cached Tet10 Jacobian at element "+to_string(e));
     g.dv=b.w*det;
     for(int j=0;j<10;++j){const V G=(c0*b.d[j][0]+c1*b.d[j][1]+c2*b.d[j][2])/det;
       g.grad[j][0]=G.x;g.grad[j][1]=G.y;g.grad[j][2]=G.z;
       g.position=g.position+m.nodes[t[j]]*b.N[j];}
    }
   }
   p06.tGeometrySetup=p06elapsed(geoBegin);
 }
 if(p06.optimized){ // exact same order of mass quadrature and nodal accumulation as zeroMeanZ
   p06.gaugeMass.assign(m.nodes.size(),0);
   for(const auto&t:m.tets)for(const auto&q:Q){V a{},b{},c{};
     for(int j=0;j<10;++j){a=a+m.nodes[t[j]]*q.d[j][0];b=b+m.nodes[t[j]]*q.d[j][1];c=c+m.nodes[t[j]]*q.d[j][2];}
     double dv=q.w*dot(a,cross(b,c));p06.gaugeVolume+=dv;
     for(int j=0;j<10;++j)p06.gaugeMass[t[j]]+=dv*q.N[j];}
   if(!(p06.gaugeVolume>0))throw runtime_error("non-positive gauge volume");
 }
 fs::create_directories(out);cout<<"mesh nodes="<<m.nodes.size()<<" tet="<<m.tets.size()<<" q="<<Q.size()<<" hash="<<signature(m)<<"\n"<<flush;
 if(postprocessOnly){
  if(laws=="ALL"||mods=="ALL")throw runtime_error("postprocess-only requires one law and one modulus");
  Setting set=base;set.name=laws;set.mod=mods;
  const auto dest=out/(laws+"_"+mods);
  Field state;state.u.assign(3*m.nodes.size(),0);state.qstate.resize(m.tets.size()*Q.size());
  const int restored=restore(dest/"restart.bin",m,set,state);
  if(restored!=int(times.size()) || abs(state.lastTime-times.back())>1e-8)
    throw runtime_error("postprocess-only: checkpoint does not match requested time schedule");
  const auto dT=fs::exists(tempdir/("thermal_"+to_string(times.back())+"s.p09e")) ? ice3d::p09e::load(tempdir,m,times.back()) : load_vtu_temp(m,tempdir/("thermal_"+to_string(times.back())+"s.vtu"));
  // dt=0 evaluates the *committed* stress at fixed e_d/e_v without evolving history.
  // The existing checkpoint and standard simulation fields are not modified.
  const Work w=assemble(m,Q,dT,state,0,set,bc,false,true);
  if(set.p09d3Diagnostic){
   ice3d::p09d3::selftest();
   const auto outbin=dest/"P09D3_QPOINTS_FINAL.bin";
   const auto stats=ice3d::p09d3::write_points(outbin,m.nodes.size(),m.tets,p06.inB6,m.nodes,Q.size(),w.p09d3qp);
   const double rel=ice3d::p09d3::rel_error(stats.p8,w.peakPower6*w.volume6);
   const double relvol=ice3d::p09d3::rel_error(stats.vol,w.volume6);
   if(rel>2e-9||relvol>2e-9)throw runtime_error("P09D3 failed total raw moment or volume conservation");
   // Independent check against the ORIGINAL committed P09B final history.
   {ifstream hist(dest/"P09B_functionals_history.csv");string h,line,last;
    if(!hist||!getline(hist,h))throw runtime_error("P09D3 missing original P09B history");
    while(getline(hist,line))if(!line.empty())last=line;
    istringstream cells(last);vector<double>numeric;string v;
    while(getline(cells,v,','))numeric.push_back(stod(v));
    if(numeric.size()!=9||abs(numeric[0]-times.back())>1e-8||
       ice3d::p09d3::rel_error(numeric[2],w.peakPower6)>2e-9||
       ice3d::p09d3::rel_error(numeric[3],w.energy6)>2e-9)
      throw runtime_error("P09D3 final checkpoint disagrees with original P09B functional history");
   }
   cout<<"P09D3_QPOINTS_OK: "<<stats.active<<" B6 tets, "<<stats.nqp<<" QPs; p8 and volume PASS\n";
  }
  if(set.p09dDiagnostic){
   ice3d::p09d::selftest();
   const auto d=ice3d::p09d::total(w.p09d);
   const auto require=[&](double a,double b,const string&name){
    if(ice3d::p09d::relative_error(a,b)>2e-9)throw runtime_error("P09D conservation check failed: "+name);
   };
   require(d.volume,w.volume6,"B6 volume");
   require(d.psi6,w.j6*w.volume6,"j6 raw integral");
   require(d.energy,w.energy6*w.volume6,"energy raw integral");
   require((set.peakP==4?d.power4:set.peakP==8?d.power8:d.power12),w.peakPower6*w.volume6,"selected p raw integral");
   // Cross-check against the original completed p-moment at final time.
   {
    ifstream f(dest/"P09B_functionals_history.csv");string hdr,line,last;
    if(!f||!getline(f,hdr))throw runtime_error("P09D missing P09B history");
    while(getline(f,line))if(!line.empty())last=line;
    if(last.empty())throw runtime_error("P09D empty P09B history");
    istringstream in(last);vector<double> nums;string cell;
    while(getline(in,cell,','))nums.push_back(stod(cell));
    if(nums.size()!=9||std::abs(nums[0]-times.back())>1e-8)throw runtime_error("P09D mismatch time in history");
    require(nums[2],w.peakPower6,"stored p-moment");
    require(nums[3],w.energy6,"stored energy");
   }
   const auto binsPath=dest/"P09D_RADIAL_FINAL.csv";
   ofstream bins(binsPath);
   bins<<"bin,inner_mm,outer_mm,actual_min_mm,actual_max_mm,nqp,volume_m3,raw_p4_m3,raw_p8_m3,raw_p12_m3,raw_psi6_m3,raw_energy_J,p8_share\n";
   bins<<setprecision(17);
   for(size_t ib=0;ib<w.p09d.bins.size();++ib){const auto &b=w.p09d.bins[ib];
    bins<<ib<<","<<ice3d::p09d::radial_edges_mm[ib]<<","<<ice3d::p09d::radial_edges_mm[ib+1]<<",";
    if(b.nqp)bins<<b.rmin_mm<<","<<b.rmax_mm;else bins<<"nan,nan";
    bins<<","<<b.nqp<<","<<b.volume<<","<<b.power4<<","<<b.power8<<","<<b.power12<<","<<b.psi6<<","<<b.energy<<","<<(d.power8?b.power8/d.power8:0)<<"\n";
   }
   ofstream summary(dest/"P09D_MOMENTS_FINAL.csv");summary<<setprecision(17);
   summary<<"time_s,law,modulus,quad,peak_p,volume6_m3,raw_p4_m3,raw_p8_m3,raw_p12_m3,jpeak4_instant,jpeak8_instant,jpeak12_instant,raw_psi6_m3,raw_energy_J,total_nqp\n";
   summary<<times.back()<<","<<laws<<","<<mods<<","<<set.quad<<","<<set.peakP<<","<<d.volume<<","<<d.power4<<","<<d.power8<<","<<d.power12<<",";
   summary<<pow(d.power4/d.volume,.25)<<","<<pow(d.power8/d.volume,.125)<<","<<pow(d.power12/d.volume,1./12)<<","<<d.psi6<<","<<d.energy<<","<<d.nqp<<"\n";
   if(!bins||!summary)throw runtime_error("P09D cannot write diagnostic csv");
   cout<<"P09D_DIAGNOSTIC_OK: final state, p4/p8/p12, 8 radial bins, all conservation checks PASS\n";
  }
  if(set.p09d2Diagnostic){
   ice3d::p09d2::selftest();
   const auto hard=ice3d::p09d2::total(w.p09d2.hard);
   const auto smooth=ice3d::p09d2::total(w.p09d2.smooth);
   auto check=[&](double x,double y,const string&name){
    if(ice3d::p09d2::rel_error(x,y)>2e-9)throw runtime_error("P09D2 conservation: "+name);
   };
   for(const auto*b:{&hard,&smooth}){
    check(b->volume,w.volume6,"B6 volume");
    check(b->p4,ice3d::p09d::total(w.p09d).power4,"p4");
    check(b->p8,w.peakPower6*w.volume6,"p8");
    check(b->p12,ice3d::p09d::total(w.p09d).power12,"p12");
    check(b->psi,w.j6*w.volume6,"j6");
    check(b->energy,w.energy6*w.volume6,"energy");
   }
   ofstream fine(dest/"P09D2_RADIAL_FINAL.csv");fine<<setprecision(17);
   fine<<"kind,bin,inner_mm,outer_mm,volume_m3,raw_p4_m3,raw_p8_m3,raw_p12_m3,raw_psi6_m3,raw_energy_J,nqp_nonzero_weight\n";
   for(int kind=0;kind<2;++kind){const auto&bins=kind?w.p09d2.smooth:w.p09d2.hard;
    for(size_t j=0;j<bins.size();++j){const auto&b=bins[j];
     fine<<(kind?"smooth":"hard")<<","<<j<<","<<ice3d::p09d2::edges_mm[j]<<","<<ice3d::p09d2::edges_mm[j+1]<<",";
     fine<<b.volume<<","<<b.p4<<","<<b.p8<<","<<b.p12<<","<<b.psi<<","<<b.energy<<","<<b.nqp<<"\n";
    }
   }
   ofstream faces(dest/"P09D2_INTERFACES_FINAL.csv");faces<<setprecision(17);
   faces<<"edge_mm,halfwidth_mm,nqp,band_volume_m3,band_raw_p8_m3\n";
   for(size_t k=0;k<ice3d::p09d2::ninterface;++k){const auto&b=w.p09d2.interfaces[k];
    faces<<ice3d::p09d2::edges_mm[k+1]<<","<<ice3d::p09d2::halfwidth_mm<<","<<b.nqp<<","<<b.volume<<","<<b.p8<<"\n";
   }
   // Sort element integrals (not stresses) to avoid a mesh-dependent point maximum.
   ofstream hot(dest/"P09D2_HOT_FINAL.csv");hot<<setprecision(17);
   hot<<"power,active_elements,top1pct_share,top5pct_share,top10pct_share,n_for_50pct,n_for_80pct,n_for_95pct,top_element_fraction,top_element_rpeak_mm,top_element_sigma_positive_over_ref\n";
   for(int power:{8,12}){
    vector<const ice3d::p09d2::HotElement*> elem;
    for(const auto&x:w.hot)if(x.nqp>0)elem.push_back(&x);
    sort(elem.begin(),elem.end(),[&](const auto*a,const auto*b){return (power==8?a->p8:a->p12)>(power==8?b->p8:b->p12);});
    const size_t n=elem.size();double total=0;
    for(const auto*x:elem)total+=(power==8?x->p8:x->p12);
    if(!(total>0)||!n)throw runtime_error("P09D2 no active peak elements");
    double cum=0,s1=0,s5=0,s10=0;size_t n50=0,n80=0,n95=0;
    const size_t k1=max<size_t>(1,size_t(ceil(.01*n))),k5=max<size_t>(1,size_t(ceil(.05*n))),k10=max<size_t>(1,size_t(ceil(.10*n)));
    for(size_t j=0;j<n;++j){cum+=(power==8?elem[j]->p8:elem[j]->p12);
     if(j+1==k1)s1=cum/total;if(j+1==k5)s5=cum/total;if(j+1==k10)s10=cum/total;
     if(!n50&&cum/total>=.5)n50=j+1;if(!n80&&cum/total>=.8)n80=j+1;if(!n95&&cum/total>=.95)n95=j+1;
    }
    hot<<power<<","<<n<<","<<s1<<","<<s5<<","<<s10<<","<<n50<<","<<n80<<","<<n95<<",";
    hot<<(power==8?elem.front()->p8:elem.front()->p12)/total<<","<<elem.front()->radius_at_peak_mm<<","<<elem.front()->peak_positive<<"\n";
   }
   if(!fine||!faces||!hot)throw runtime_error("P09D2 cannot write diagnostic outputs");
   cout<<"P09D2_DIAGNOSTIC_OK: refined 0.05mm shells, smoothed partition, hotspot summaries PASS\n";
  }

  const auto path=dest/("qp_diagnostics_"+to_string(times.back())+"s.vtu");
  if(!set.p09dDiagnostic)save_fields(m,dT,state,w,path,times.back());
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
 vector<vector<double>> thermal;for(int t:times){
   const auto bin=tempdir/("thermal_"+to_string(t)+"s.p09e");
   if(fs::is_regular_file(bin))thermal.push_back(ice3d::p09e::load(tempdir,m,t));
   else thermal.push_back(load_vtu_temp(m,tempdir/("thermal_"+to_string(t)+"s.vtu")));
 }
 ofstream campaign;
 ofstream profileStep,profileCg,profileNewton;
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
    if(adjointRetention.interval>0){
      ice3d::p10h::retain(dest,m,set,state,0);
      cerr<<"[P10H] retained initial state step=0\n"<<flush;
    }
    // If a crash occurred after the last checkpoint, trim unsaved CSV steps
    // before reopening append streams, so no stale or duplicate functional rows.
    if(start>0){
      for(const auto& name: {"time_series.csv","max_location.csv", "polar_caps_history.csv"})
        ice3d::p09e2::trim_step_history(dest/name,times,start);
      if(set.extraFunctionals)
        ice3d::p09e2::trim_step_history(dest/"P09B_functionals_history.csv",times,start);
    }
    const int savedTime = start>0?times[start-1]:0;
    if(campaign.is_open())campaign.close();
    ice3d::p09e2::trim_campaign(out/"G06_campaign.csv",law,mod,savedTime);
    campaign.open(out/"G06_campaign.csv",ios::app);
    if(!campaign)throw runtime_error("P09E2: cannot open campaign");
    if(campaign.tellp()==0)campaign<<"law,modulus,time_s,dt_s,nodes,tet10,quad,Newton_steps,CG_steps,relative_residual,max_principal_MPa,Psi6,PsiOmega,volume6_m3,volume_m3,gauge_mean_uz_m,wall_seconds,max_local_NT,VmHWM_kB\n";
    if(p06.profile){
      if(profileStep.is_open())profileStep.close();
      if(profileCg.is_open())profileCg.close();
      if(profileNewton.is_open())profileNewton.close();
      for(const auto& name: {"profile_per_step.csv","profile_cg.csv","profile_newton.csv"})
        ice3d::p09e2::trim_campaign(out/name,law,mod,savedTime);
      profileStep.open(out/"profile_per_step.csv",ios::app);
      if(profileStep.tellp()==0)profileStep<<"law,modulus,time_s,dt_s,wall_s,cpu_s,graph_once_s,assembly_s,edv_s,geometry_s,scatter_s,pcg_s,gauge_s,output_s,checkpoint_s,newton_n,cg_n,relative_residual,peak_rss_kb,preconditioner,threads\n";
      profileCg.open(out/"profile_cg.csv",ios::app);
      if(profileCg.tellp()==0)profileCg<<"law,modulus,time_s,cg_calls,cg_iterations,pcg_total_s,pcg_s_per_iteration,preconditioner,precond_setup_s,precond_apply_s,spmv_s,dot_s,vector_s\n";
      profileNewton.open(out/"profile_newton.csv",ios::app);
      if(profileNewton.tellp()==0)profileNewton<<"law,modulus,time_s,newton_iteration,residual_abs,residual_rel,cg_iterations,assembly_s,pcg_s,line_search_s\n";
    }
    ofstream loc(dest/"max_location.csv",start?ios::app:ios::trunc);
    if(!start)loc<<"time_s,element_id_0based,qp_id_0based,x_m,y_m,z_m,r_from_pore_center_mm,distance_to_pore_surface_mm,sigma1_QP_max_MPa,sigma1_element_volume_avg_MPa,inside_fixed_B6\n";
    ofstream ts(dest/"time_series.csv",start?ios::app:ios::trunc);if(!start)ts<<"time_s,dt_s,Psi6,PsiOmega,maxS1_MPa,Newton,CG,residual_rel,wall_s\n";
    // Stage09B functional history is deliberately separate from legacy time_series.csv.
    // Reject resume from old checkpoints with no matching functional rows.
    if(set.extraFunctionals && start>0){
      ifstream check(dest/"P09B_functionals_history.csv");string line;int n=-1;
      if(!check)throw runtime_error("P09B: --resume requires complete functional history; old checkpoints cannot be retrofitted from time_series.csv");
      while(getline(check,line))if(!line.empty())++n;
      if(n!=start)throw runtime_error("P09B: functional history/checkpoint count mismatch; do not silently reuse old output");
      ifstream meta(dest/"P09B_functionals_config.txt");int p=-1;meta>>p;
      if(!meta||p!=set.peakP)throw runtime_error("P09B: peak-p changed between checkpoint and resume");
    }
    ofstream extra;
    if(set.extraFunctionals){
      extra.open(dest/"P09B_functionals_history.csv",start?ios::app:ios::trunc);
      if(!extra)throw runtime_error("P09B: cannot open functional history");
      if(!start){extra<<"time_s,dt_s,peak_power_B6,energy_density_B6_Pa,jpeak_instant,jen_instant,volume6_m3,peak_p,psi_ref_Pa\n";
        ofstream cfg(dest/"P09B_functionals_config.txt");cfg<<set.peakP<<"\n";}
    }
    ofstream polar(dest/"polar_caps_history.csv",start?ios::app:ios::trunc);
    if(!start)polar<<"time_s,top_cap_mean_positive_sigma1_MPa,bottom_cap_mean_positive_sigma1_MPa,top_cap_volume_m3,bottom_cap_volume_m3\n";
    auto lastCheckpointTick=Clock::now();
    for(int k=start;k<int(times.size());++k){
     p06.clear_step();auto stepStart=Clock::now();const std::clock_t cpuStart=std::clock();
     double dt=times[k]-state.lastTime;
     if(!(dt>0))throw runtime_error("non-positive dt; inconsistent checkpoint/time list");
     Work w;auto solveInfo=nonlinear_step(m,Q,thermal[k],state,dt,set,bc,w);
     auto gaugeStart=Clock::now();double gaugeUz=zeroMeanZ(m,Q,state);
     if(p06.profile)p06.tGauge+=p06elapsed(gaugeStart);
     state.lastTime=times[k];
     cout<<law<<" "<<mod<<" time="<<times[k]<<" Newton="<<solveInfo.n<<" CG="<<solveInfo.totalCG<<" residual="<<solveInfo.ratio
         <<" maxStress="<<w.maxSigma/1e6<<" Psi6="<<w.j6<<" PsiOmega="<<w.jOmega<<" wall="<<solveInfo.wall<<"\n"<<flush;
     ts<<setprecision(15)<<times[k]<<","<<dt<<","<<w.j6<<","<<w.jOmega<<","<<w.maxSigma/1e6<<","<<solveInfo.n<<","<<solveInfo.totalCG<<","<<solveInfo.ratio<<","<<solveInfo.wall<<"\n"<<flush;
     if(set.extraFunctionals){
       const double peak=std::pow(w.peakPower6,1.0/set.peakP);
       const double jen=w.energy6/ice3d::p09b::energy_ref_pa;
       if(!(std::isfinite(peak)&&std::isfinite(jen)&&w.peakPower6>=0&&w.energy6>=0))throw runtime_error("P09B: invalid integrated functional");
       extra<<setprecision(17)<<times[k]<<","<<dt<<","<<w.peakPower6<<","<<w.energy6<<","<<peak<<","<<jen<<","<<w.volume6<<","<<set.peakP<<","<<ice3d::p09b::energy_ref_pa<<"\n"<<flush;
     }
     polar<<setprecision(15)<<times[k]<<","<<(w.polarTopVolume>0?w.polarTopStress/w.polarTopVolume:0)<<","<<(w.polarBottomVolume>0?w.polarBottomStress/w.polarBottomVolume:0)<<","<<w.polarTopVolume<<","<<w.polarBottomVolume<<"\n"<<flush;
     auto outputStart=Clock::now();
     if((vtuMode.empty() && (!finalVtuOnly || k==int(times.size())-1)) || vtuMode=="all" || (vtuMode=="final" && k==int(times.size())-1))save_fields(m,thermal[k],state,w,dest/("mechanics_"+to_string(times[k])+"s.vtu"),times[k]);
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
     if(p06.profile)p06.tOutput+=p06elapsed(outputStart);
     const double sinceCheckpoint=chrono::duration<double>(Clock::now()-lastCheckpointTick).count();
     if(ice3d::p09e2::should_checkpoint(checkpointHours,sinceCheckpoint,k+1==int(times.size()))){
       auto checkpointStart=Clock::now();
       cerr<<"[P09E2 CHECKPOINT] writing at t="<<times[k]
           <<" step="<<(k+1)<<" elapsed_since_checkpoint_s="<<sinceCheckpoint<<"\n"<<flush;
       checkpoint(dest/"restart.bin",m,set,state,k+1);
       lastCheckpointTick=Clock::now();
       if(p06.profile)p06.tCheckpoint+=p06elapsed(checkpointStart);
     } else {
       cerr<<"[P09E2 CHECKPOINT] skipped t="<<times[k]
           <<" elapsed_since_checkpoint_s="<<sinceCheckpoint<<"\n"<<flush;
     }
     if(ice3d::p10h::scheduled(adjointRetention,k+1,int(times.size()))){
       ice3d::p10h::retain(dest,m,set,state,k+1);
       cerr<<"[P10H] retained step="<<(k+1)
           <<" time_s="<<times[k]<<"\n"<<flush;
     }
     long peak=peakMemoryKB();
     if(p06.profile){
      const double totalWall=p06elapsed(stepStart);const double totalCpu=double(std::clock()-cpuStart)/CLOCKS_PER_SEC;
      profileStep<<setprecision(15)<<law<<","<<mod<<","<<times[k]<<","<<dt<<","<<totalWall<<","<<totalCpu<<","<<p06.tGraph<<","<<p06.tAssembly<<","<<p06.tEDV<<","<<p06.tGeometry<<","<<p06.tScatter<<","<<p06.tCG<<","<<p06.tGauge<<","<<p06.tOutput<<","<<p06.tCheckpoint<<","<<solveInfo.n<<","<<solveInfo.totalCG<<","<<solveInfo.ratio<<","<<peak<<","<<(stage06_schwarz_overlap>=0?(stage06_schwarz_overlap?"as1":"as0"):(stage06_ic0?"ic0":(stage06_mcsgs_fast?"mcsgs-fast":(stage06_mcsgs?"mcsgs":(stage06_sgs?"sgs":"jacobi")))))<<",";
      #ifdef _OPENMP
      profileStep<<omp_get_max_threads();
      #else
      profileStep<<1;
      #endif
      profileStep<<"\n"<<flush;
      profileCg<<setprecision(15)<<law<<","<<mod<<","<<times[k]<<","<<p06.cgCalls<<","<<solveInfo.totalCG<<","<<p06.tCG<<","<<(solveInfo.totalCG?p06.tCG/solveInfo.totalCG:0)<<","<<(stage06_schwarz_overlap>=0?(stage06_schwarz_overlap?"as1":"as0"):(stage06_ic0?"ic0":(stage06_mcsgs_fast?"mcsgs-fast":(stage06_mcsgs?"mcsgs":(stage06_sgs?"sgs":"jacobi")))))<<","<<stage06_cg_details.setup<<","<<stage06_cg_details.apply<<","<<stage06_cg_details.spmv<<","<<stage06_cg_details.dot<<","<<stage06_cg_details.vec<<"\n"<<flush;
      for(const auto&ev:p06.newtonEvents)profileNewton<<setprecision(15)<<law<<","<<mod<<","<<times[k]<<","<<ev.iteration<<","<<ev.residual<<","<<ev.ratio<<","<<ev.cg<<","<<ev.assembly_s<<","<<ev.pcg_s<<","<<ev.line_s<<"\n";
      profileNewton.flush();
     }
     campaign<<setprecision(15)<<law<<","<<mod<<","<<times[k]<<","<<dt<<","<<m.nodes.size()<<","<<m.tets.size()<<","<<set.quad<<","<<solveInfo.n<<","<<solveInfo.totalCG<<","<<solveInfo.ratio<<","<<w.maxSigma/1e6<<","<<w.j6<<","<<w.jOmega<<","<<w.volume6<<","<<w.volume<<","<<gaugeUz<<","<<solveInfo.wall<<","<<w.maxLocalIterations<<","<<peak<<"\n"<<flush;
    }
  }
 }
 return 0;
 }catch(const exception&e){cerr<<"G06 FAILED: "<<e.what()<<"\n";return 2;}}

#endif // STAGE3D07D_LIBRARY (diagnostic uses existing mechanics/constitutive code)
