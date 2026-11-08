// Stage 3D-10H: cross-validate actual spatial_reology.cpp assembly against
// the P10C global EDV analytic linearization on the very same Tet10 mesh.
#define STAGE3D07D_LIBRARY
#include "spatial_reology.cpp"
#include "stage3d10c_tet10_global_adjoint.hpp"
#include "stage3d10e_bcsr_adjoint.hpp"
#include "stage3d10f_functional_adjoint.hpp"
#include <iomanip>
#include <map>
#include <chrono>
#include <cstring>

namespace {
void check(bool truth,const std::string& reason){
 if(!truth)throw std::runtime_error("P10H: "+reason);
}
struct Tiny{
 Mesh m;
 std::vector<uint8_t> bc;
 explicit Tiny(double shape=0.){
  // Two nondegenerate affine Tet10s, centered inside the fixed B6 region.
  m.nodes={V{0,0,.030},V{.004,0,.030},
           V{.00015*(1.+shape),.003*(1.+.05*shape),.03012+.00012*shape},
           V{0,0,.034},
           V{.00025+.00030*shape,.0003+.00020*shape,
             .030-.0035*(1.+.04*shape)}};
  std::map<std::pair<int,int>,int> edges;
  auto mid=[&](int a,int b){
   if(a>b)std::swap(a,b);
   if(auto it=edges.find({a,b});it!=edges.end())return it->second;
   const int i=int(m.nodes.size());
   m.nodes.push_back((m.nodes[size_t(a)]+m.nodes[size_t(b)])*.5);
   edges[{a,b}]=i;return i;
  };
  constexpr int edge[6][2]={{0,1},{1,2},{2,0},{0,3},{1,3},{2,3}};
  for(auto vertices:std::array<std::array<int,4>,2>{{{{0,1,2,3}},{{0,2,1,4}}}}){
   Tet t{};
   for(int a=0;a<4;++a)t[a]=vertices[a];
   for(int e=0;e<6;++e)t[4+e]=mid(vertices[edge[e][0]],vertices[edge[e][1]]);
   m.tets.push_back(t);
  }
  bc.assign(m.nodes.size()*3,0);
  for(int node:std::array<int,6>{0,1,3,mid(0,1),mid(0,3),mid(1,3)})
   for(int axis=0;axis<3;++axis)bc[size_t(3*node+axis)]=1;
 }
};
std::vector<double> temperatures(const Mesh& m,int step){
 std::vector<double> out(m.nodes.size());
 for(size_t j=0;j<out.size();++j)
  out[j]=-5.8+.35*std::sin(.47*j)+.22*std::sin(.30*step);
 return out;
}
double norm(const std::vector<double>& x){
 double sum=0;
 for(double v:x)sum+=v*v;
 return std::sqrt(sum);
}
double field_diff(const std::vector<State>& a,const std::vector<State>& b){
 check(a.size()==b.size(),"history size mismatch");
 double diff=0,scale=0;
 for(size_t i=0;i<a.size();++i)for(int c=0;c<6;++c){
  diff+=std::pow(a[i].e_d[c]-b[i].e_d[c],2);
  diff+=std::pow(a[i].e_v[c]-b[i].e_v[c],2);
  scale+=std::pow(a[i].e_d[c],2)+std::pow(a[i].e_v[c],2);
 }
 return std::sqrt(diff)/std::max(1e-14,std::sqrt(scale));
}
double rel(const std::vector<double>& a,const std::vector<double>& b){
 check(a.size()==b.size(),"vector size mismatch");
 std::vector<double> diff(a.size());
 for(size_t i=0;i<a.size();++i)diff[i]=a[i]-b[i];
 return norm(diff)/std::max({1e-12,norm(a),norm(b)});
}

struct Report {
 double residual=0,history=0,tangent=0;
 std::array<double,3> functional{};
 int steps=0;
};

struct ReplayReport{
 int files=0,replayed=0,maximum_window=0;
 bool checksum_detected=false,model_detected=false,budget_guard=false;
};
void identical_field(const Field& a,const Field& b){
 check(a.lastTime==b.lastTime&&a.u.size()==b.u.size()&&
       a.qstate.size()==b.qstate.size(),"retained dimensions/time mismatch");
 check(std::memcmp(a.u.data(),b.u.data(),a.u.size()*sizeof(double))==0,
       "retained displacement replay not bitwise equal");
 check(std::memcmp(a.qstate.data(),b.qstate.data(),
       a.qstate.size()*sizeof(State))==0,
       "retained EDV state replay not bitwise equal");
}

ReplayReport production_replay(const Tiny& tiny){
 ReplayReport report;
 constexpr int N=12,window=4;
 constexpr double dt=150.;
 const auto Q=volume_q(3);
 Setting setting;setting.name="EDV";setting.mod="VAR";
 setting.quad=3;setting.newtonTol=5e-11;setting.cgTol=3e-12;
 p06.optimized=false;p06.parallelAssembly=false;
 p06.graph.reset();p06.geometry.clear();p06.inB6.clear();
 p06.gaugeMass.clear();p06.gaugeVolume=0.;
 const auto stamp=std::chrono::steady_clock::now().time_since_epoch().count();
 const fs::path destination=fs::temp_directory_path()/
                             ("ice3d_p10h_prod_"+std::to_string(stamp));
 check(fs::create_directory(destination),"test temp directory collision");
 struct Cleanup{
  fs::path path;
  ~Cleanup(){std::error_code error;fs::remove_all(path,error);}
 } cleanup{destination};
 const ice3d::p10h::Budget policy{window,0.01};
 check(ice3d::p10h::estimated_total(policy,tiny.m,Q.size(),N)>0,
       "P10H capacity estimator returned zero");
 try{
  (void)ice3d::p10h::estimated_total({window,1e-12},tiny.m,Q.size(),N);
 }catch(const std::runtime_error&){report.budget_guard=true;}
 check(report.budget_guard,"P10H disk cap failed to reject oversized history");
 Field field;
 field.u.assign(tiny.m.nodes.size()*3,0.);
 field.qstate.resize(tiny.m.tets.size()*Q.size());
 std::vector<Field> reference{field};
 ice3d::p10h::retain(destination,tiny.m,setting,field,0);
 ++report.files;
 for(int n=1;n<=N;++n){
  p06.clear_step();Work completed;
  (void)nonlinear_step(tiny.m,Q,temperatures(tiny.m,n),field,dt,
                       setting,tiny.bc,completed);
  (void)zeroMeanZ(tiny.m,Q,field); // production post-step displacement gauge
  field.lastTime=dt*n;
  reference.push_back(field);
  if(ice3d::p10h::scheduled(policy,n,N)){
   ice3d::p10h::retain(destination,tiny.m,setting,field,n);
   ++report.files;
  }
 }
 check(report.files==4,"P10H wrong snapshot count");
 // Check that the writer cannot overwrite even a test-owned old state.
 bool collision_detected=false;
 try{ice3d::p10h::retain(destination,tiny.m,setting,field,N);}
 catch(const std::exception&){collision_detected=true;}
 check(collision_detected,"P10H snapshot collision was not detected");
 for(int begin=0;begin<N;begin+=window){
  Field restored=ice3d::p10h::recover(destination,tiny.m,setting,begin,
                                        dt*begin,Q.size());
  identical_field(restored,reference[size_t(begin)]);
  for(int n=begin+1;n<=begin+window;++n){
   p06.clear_step();Work completed;
   (void)nonlinear_step(tiny.m,Q,temperatures(tiny.m,n),restored,dt,
                        setting,tiny.bc,completed);
   (void)zeroMeanZ(tiny.m,Q,restored);
   restored.lastTime=dt*n;
   identical_field(restored,reference[size_t(n)]);
   ++report.replayed;
  }
  report.maximum_window=std::max(report.maximum_window,window);
  const auto endpoint=ice3d::p10h::recover(destination,tiny.m,setting,
                            begin+window,dt*(begin+window),Q.size());
  identical_field(restored,endpoint);
 }
 // Wrong constitutive model must fail even if all snapshot bytes are intact.
 Setting mismatch=setting;
 mismatch.mod="CONST";
 try{(void)ice3d::p10h::recover(destination,tiny.m,mismatch,
                               window,dt*window,Q.size());}
 catch(const std::exception&){report.model_detected=true;}
 // Copy a test-owned snapshot; never damage the authentic checkpoint.
 const auto corrupted=destination/"corrupted";
 fs::create_directories(corrupted/"adjoint_history");
 const auto original=ice3d::p10h::named_file(destination,window);
 const auto changed=ice3d::p10h::named_file(corrupted,window);
 fs::copy_file(original,changed);
 fs::copy_file(ice3d::p10h::integrity_path(original),
               ice3d::p10h::integrity_path(changed));
 {
  std::fstream f(changed,std::ios::binary|std::ios::in|std::ios::out);
  f.seekg(80);
  char byte=0;f.read(&byte,1);f.seekp(80);byte^=0x04;f.write(&byte,1);
  check(bool(f),"P10H corruption injection I/O failed");
 }
 try{(void)ice3d::p10h::recover(corrupted,tiny.m,setting,
                                window,dt*window,Q.size());}
 catch(const std::exception&){report.checksum_detected=true;}
 check(report.checksum_detected&&report.model_detected,
       "P10H corrupted/mismatched snapshot accepted");
 return report;
}

Report solver_parity(const Tiny& tiny){
 Report report;
 auto Q=volume_q(3);
 p06.optimized=false;p06.parallelAssembly=false;
 p06.graph.reset();p06.geometry.clear();p06.inB6.clear();
 for(const auto& material:std::array<std::string,3>{"E","ED","EDV"})
  for(const auto& modulus:std::array<std::string,2>{"CONST","VAR"}){
   Setting setting;setting.name=material;setting.mod=modulus;
   setting.quad=3;setting.newtonTol=5e-11;setting.cgTol=3e-12;
   setting.extraFunctionals=true;
   Field state;
   state.u.assign(3*tiny.m.nodes.size(),0.);
   state.qstate.resize(tiny.m.tets.size()*Q.size());
   for(int n=1;n<=3;++n){
    p06.clear_step();
    const Field previous=state;
    const auto T=temperatures(tiny.m,n);
    Work completed;
    const double dt=150.;
    const auto info=nonlinear_step(tiny.m,Q,T,state,dt,setting,tiny.bc,completed);
    check(info.ratio<1e-8 || info.residual<1e-10,"production Newton mismatch");
    Field frozen=state;
    frozen.qstate=previous.qstate;
    auto physical=assemble(tiny.m,Q,T,frozen,dt,setting,tiny.bc,true,true);
    const ice3d::p10c::Step step(tiny.m,Q,T,previous.qstate,dt,state.u,
       tiny.bc,(modulus=="VAR"?Modulus::VAR:Modulus::CONST),
       ice3d::p10b::Controls{material!="E",material=="EDV"});
    const auto out=step.evaluate();
    const std::array<double,3> observed{
       physical.j6,physical.peakPower6,
       physical.energy6/ice3d::p09b::energy_ref_pa};
    const std::array<double,3> adjoint_sources{
       ice3d::p10f::evaluate(step,ice3d::p10f::Kind::J6).value,
       ice3d::p10f::evaluate(step,ice3d::p10f::Kind::PeakMoment).value,
       ice3d::p10f::evaluate(step,ice3d::p10f::Kind::Energy).value};
    for(size_t function=0;function<observed.size();++function){
     const double relative=std::abs(observed[function]-adjoint_sources[function])/
         std::max({1e-14,std::abs(observed[function]),std::abs(adjoint_sources[function])});
     report.functional[function]=std::max(report.functional[function],relative);
    }
    auto f=physical.A.f;
    for(size_t i=0;i<f.size();++i)if(tiny.bc[i])f[i]=out.residual[i];
    // At converged equilibrium both residuals are almost zero. A relative
    // quotient would amplify floating-point roundoff; use absolute newtons.
    std::vector<double> residual_difference(f.size());
    for(size_t j=0;j<f.size();++j)
     residual_difference[j]=f[j]-out.residual[j];
    report.residual=std::max(report.residual,norm(residual_difference));
    report.history=std::max(report.history,field_diff(state.qstate,out.next));
    ice3d::p10c::Perturbation d;
    d.du.assign(state.u.size(),0.);
    d.dtemperature.assign(T.size(),0.);
    d.dprevious.resize(state.qstate.size());
    for(size_t j=0;j<d.du.size();++j)if(!tiny.bc[j])
     d.du[j]=1e-7*std::sin(.43*j+.11*n);
    const auto jvp=step.jvp(d);
    std::vector<double> Kdu;
    physical.A.K.mul(d.du,Kdu,tiny.bc);
    report.tangent=std::max(report.tangent,rel(Kdu,jvp.residual));
    ++report.steps;
   }
  }
 return report;
}

#ifdef STAGE3D10I_PRODUCTION_ADJOINT
#include "stage3d10i_production_adjoint.hpp"
#endif
}

int main(){try{
#ifdef _OPENMP
 omp_set_dynamic(0);omp_set_num_threads(4);
#endif
#ifdef STAGE3D10I_PRODUCTION_ADJOINT
 return p10i::run_tests();
#else
 const Tiny tiny;
 const auto report=solver_parity(tiny);
 std::cerr<<std::scientific<<std::setprecision(12)
  <<"P10H_DIAGNOSTIC residual="<<report.residual
  <<" history="<<report.history<<" tangent="<<report.tangent<<'\n';
 check(report.steps==18,"case count");
 check(report.residual<1e-10,"spatial residual and P10C diverge");
 check(report.history<1e-9,"spatial EDV history and P10C diverge");
 check(report.tangent<1e-8,"BCSR mechanical tangent and P10C JVP diverge");
 for(size_t i=0;i<3;++i)
  check(report.functional[i]<1e-8,"P09B observable and P10F source disagree");
 const auto replay=production_replay(tiny);
 check(replay.replayed==12&&replay.maximum_window==4,
       "P10H production replay count mismatch");
 std::cout<<std::scientific<<std::setprecision(12)
  <<"P10H_PRODUCTION_REPLAY_OK settings=6 parity_steps="<<report.steps
  <<" residual_abs_N="<<report.residual
  <<" state_rel="<<report.history
  <<" bcsr_tangent_rel="<<report.tangent
  <<" j6_parity_rel="<<report.functional[0]
  <<" jpeak_power_parity_rel="<<report.functional[1]
  <<" jen_parity_rel="<<report.functional[2]
  <<" retained_snapshots="<<replay.files
  <<" replayed_steps="<<replay.replayed
  <<" max_window="<<replay.maximum_window
  <<" disk_guard="<<replay.budget_guard
  <<" checksum_rejection="<<replay.checksum_detected
  <<" model_rejection="<<replay.model_detected<<'\n';
 return 0;
#endif
}catch(const std::exception& e){
 std::cerr<<e.what()<<'\n';return 2;
}}
