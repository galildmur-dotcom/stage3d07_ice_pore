// Stage 3D-10K: first real H0 end-to-end verification of shape derivative.
// Thermal tangent is computed independently by centered *thermal-only*
// perturbed-grid solves. Mechanical transient adjoint is analytical (P10I).
// Thus this is a HYBRID coupled check, not yet a thermal Hadamard adjoint.
// This TU reuses the tested production solver and P10I harness without
// changing either one. CMake must provide src/ and tests/ include dirs.
#define STAGE3D10I_PRODUCTION_ADJOINT
#define main stage3d10k_unused_prior_test_main
#include "stage3d10h_production_preflight.cpp"
#undef main
#include <cstdlib>
#include <iomanip>
#include <sstream>

#ifndef STAGE3D10K_SOURCE_ROOT
#define STAGE3D10K_SOURCE_ROOT STAGE3D06_ROOT_DIR
#endif

namespace p10k {
namespace f10=ice3d::p10f;
namespace a10=ice3d::p10c;
namespace e10=ice3d::p10e;
namespace h10=ice3d::p10h;

struct Config{
 fs::path root=STAGE3D10K_SOURCE_ROOT;
 fs::path mesh,out,geometry_exe,thermal_exe;
 std::string mode="y20";
 int steps=3,dt=300,threads=4;
 double delta_um=5,cutoff_mm=5;
 bool selftest=false;
};

void require(bool test,const std::string& message){
 if(!test)throw std::runtime_error("P10K: "+message);
}

std::string tag(double value){
 std::ostringstream o;o<<std::fixed<<std::setprecision(3)<<value;
 std::string s=o.str();for(char& c:s)if(c=='.')c='p';return s;
}

Config parse(int argc,char**argv){
 Config c;
 const fs::path executable=fs::absolute(argv[0]).parent_path();
#ifdef _WIN32
 const std::string suffix=".exe";
#else
 const std::string suffix="";
#endif
 c.geometry_exe=executable/("stage3d08_geometry"+suffix);
 c.thermal_exe=executable/("stage3d02_thermal"+suffix);
 for(int i=1;i<argc;++i){
  const std::string flag=argv[i];
  auto val=[&](){require(i+1<argc,"missing value after "+flag);return std::string(argv[++i]);};
  if(flag=="--root")c.root=val();
  else if(flag=="--mesh")c.mesh=val();
  else if(flag=="--out")c.out=val();
  else if(flag=="--geometry-exe")c.geometry_exe=val();
  else if(flag=="--thermal-exe")c.thermal_exe=val();
  else if(flag=="--mode")c.mode=val();
  else if(flag=="--steps")c.steps=std::stoi(val());
  else if(flag=="--dt")c.dt=std::stoi(val());
  else if(flag=="--threads")c.threads=std::stoi(val());
  else if(flag=="--delta-um")c.delta_um=std::stod(val());
  else if(flag=="--cutoff-mm")c.cutoff_mm=std::stod(val());
  else if(flag=="--selftest")c.selftest=true;
  else if(flag=="--help"){
   std::cout<<"stage3d10k_h0_coupled_pilot [--selftest] [--mesh H0.msh] "
       "[--out NEW_DIRECTORY] [--steps 3] [--dt 300] [--mode y20|R|tz] "
       "[--delta-um 5] [--threads 4] [--geometry-exe PATH] "
       "[--thermal-exe PATH] [--root PROJECT]\n";
   std::exit(0);
  }else throw std::runtime_error("P10K unknown argument: "+flag);
 }
 if(c.mesh.empty())c.mesh=c.root/"meshes"/"H0.msh";
 if(c.out.empty())c.out=c.root/"LOCAL_RUNS"/"P10K_H0_3STEP_PILOT";
 require(c.steps>=1&&c.steps<=12&&c.dt>=1&&c.threads>=1&&c.threads<=8,
         "invalid steps/dt/threads");
 require(c.mode=="R"||c.mode=="tz"||c.mode=="y20","mode must be R,tz,y20");
 require(c.delta_um>0&&c.delta_um<=10&&c.cutoff_mm>3&&c.cutoff_mm<5.5,
         "invalid delta/cutoff");
 return c;
}

// Controlled execution of the already approved geometry and heat solvers;
// input is quoted, no arbitrary shell options are concatenated.
std::string quoted(const fs::path& p){
 const auto s=p.string();
 require(s.find('"')==std::string::npos,"double quote in path is unsupported");
 return '"'+s+'"';
}
void run_external(const fs::path& exe,const std::vector<std::string>& args){
 require(fs::is_regular_file(exe),"missing solver: "+exe.string());
 std::string command=quoted(exe);
 for(const auto& a:args){
  require(a.find('"')==std::string::npos,"double quote in subprocess argument");
  command+=' '+('"'+a+'"');
 }
 const int result=std::system(command.c_str());
 require(result==0,"subprocess failed (exit="+std::to_string(result)+"): "+exe.string());
}

struct Scenario{
 Mesh mesh;
 std::vector<std::vector<double>> temperatures; // theta = T(K) - T0
 std::string tag;
};

std::vector<std::vector<double>> read_thermal(const Mesh& mesh,const fs::path& folder,
                                               const Config& c){
 std::vector<std::vector<double>> data(size_t(c.steps+1));
 data[0].assign(mesh.nodes.size(),0.);
 for(int n=1;n<=c.steps;++n)
  data[size_t(n)]=ice3d::p09e::load(folder,mesh,n*c.dt);
 return data;
}

struct HistoryFrame{
 std::vector<double> temperature,repinned_u;
 std::vector<State> previous;
};
struct Forward{
 std::array<double,3> objective{};
 std::vector<HistoryFrame> frames;
 Field final_state;
};

std::vector<uint8_t> observation_elements(const Mesh& mesh);
f10::Sources evaluate_b6(const a10::Step& step,f10::Kind kind,
                         const std::vector<uint8_t>& mask,size_t nquad);

std::vector<uint8_t> mechanical_bc(const Mesh& mesh){return bc_candidate(mesh);}
std::vector<uint8_t> adjoint_bc(const Mesh& mesh){
 auto bc=mechanical_bc(mesh);
 // Use exactly the production pin (at the mesh node closest to the origin).
 // An extra pin would spuriously suppress a physical vertical deformation.
 require(std::count_if(bc.begin(),bc.end(),[](uint8_t x){return x!=0;})>0,
         "missing mechanical boundary conditions");
 return bc;
}
std::vector<double> repin(const Mesh& mesh,const std::vector<double>&u){
 std::vector<double> v=u;
 const auto bc=mechanical_bc(mesh);
 size_t pin=u.size();
 for(size_t i=2;i<bc.size();i+=3)if(bc[i]){
  require(pin==u.size(),"multiple vertical gauge pins");pin=i;
 }
 require(pin<u.size(),"missing vertical gauge pin");
 const double dz=u.at(pin);
 for(size_t i=0;i<v.size()/3;++i)v[3*i+2]-=dz;
 return v;
}
Setting setting(){
 Setting s;s.name="EDV";s.mod="VAR";s.quad=3;s.peakP=8;
 s.extraFunctionals=true;s.newtonTol=2e-8;s.cgTol=2e-9;
 s.maxCG=3500;return s;
}
void configure(){
 p06.optimized=false;p06.parallelAssembly=false;p06.graph.reset();
 p06.geometry.clear();p06.inB6.clear();p06.gaugeMass.clear();p06.gaugeVolume=0.;
}

Forward forward(const Scenario& s,const Config& c,bool save_frames,
                const fs::path& checkpoints={}){
 configure();const auto qs=volume_q(3);
 const auto bc=mechanical_bc(s.mesh);
 auto cfg=setting();
 Field state;
 state.u.assign(3*s.mesh.nodes.size(),0.);
 state.qstate.resize(s.mesh.tets.size()*qs.size());
 Forward result;
 if(!checkpoints.empty()){
  const h10::Budget budget{c.steps,0.20};
  (void)h10::estimated_total(budget,s.mesh,qs.size(),c.steps);
  h10::retain(checkpoints,s.mesh,cfg,state,0);
 }
 std::array<double,3> moment{};
 const std::array<f10::Kind,3> kinds{f10::Kind::J6,f10::Kind::PeakMoment,f10::Kind::Energy};
 for(int k=0;k<3;++k)moment[size_t(k)]=.5/c.steps*f10::initial_time_value(kinds[size_t(k)]);
 for(int n=1;n<=c.steps;++n){
  p06.clear_step();
  const auto previous=state.qstate;
  Work work;
  const auto stat=nonlinear_step(s.mesh,qs,s.temperatures[size_t(n)],
                                 state,double(c.dt),cfg,bc,work);
  require(std::isfinite(stat.residual)&&std::isfinite(stat.ratio),"Newton failure");
  if(save_frames){
   const a10::Step check(s.mesh,qs,s.temperatures[size_t(n)],previous,
                        double(c.dt),repin(s.mesh,state.u),adjoint_bc(s.mesh),
                        Modulus::VAR,ice3d::p10b::Controls{true,true});
   const auto region=observation_elements(s.mesh);
   const std::array<double,3> recorded{work.j6,work.peakPower6,
                       work.energy6/ice3d::p09b::energy_ref_pa};
   const std::array<f10::Kind,3> check_kind{f10::Kind::J6,
                         f10::Kind::PeakMoment,f10::Kind::Energy};
   for(size_t k=0;k<3;++k){
    const double recomputed=evaluate_b6(check,check_kind[k],region,qs.size()).value;
    const double err=std::abs(recomputed-recorded[k])/
                           std::max({1e-20,std::abs(recomputed),std::abs(recorded[k])});
    std::cout<<"P10K_INSTANT_PARITY functional="<<k<<" step="<<n
             <<" relative="<<std::scientific<<err<<'\n';
    require(err<2e-5,"P10F source is not the production B6 functional");
   }
  }
  if(save_frames)result.frames.push_back({s.temperatures[size_t(n)],repin(s.mesh,state.u),previous});
  const std::array<double,3> j{work.j6,work.peakPower6,
                               work.energy6/ice3d::p09b::energy_ref_pa};
  const double w=(n==c.steps?.5:1.)/c.steps;
  for(int k=0;k<3;++k)moment[size_t(k)]+=w*j[size_t(k)];
  (void)zeroMeanZ(s.mesh,qs,state);
  state.lastTime=double(n*c.dt);
  std::cout<<"P10K_FORWARD scenario="<<s.tag<<" step="<<n<<"/"<<c.steps
           <<" residual="<<stat.residual<<" ratio="<<stat.ratio<<'\n';
 }
 for(int k=0;k<3;++k)result.objective[size_t(k)]=
  kinds[size_t(k)]==f10::Kind::PeakMoment
   ?std::pow(moment[size_t(k)],1./8.):moment[size_t(k)];
 if(!checkpoints.empty())h10::retain(checkpoints,s.mesh,cfg,state,c.steps);
 result.final_state=std::move(state);
 return result;
}

double relative(double x,double y){
 return std::abs(x-y)/std::max({1e-7,std::abs(x),std::abs(y)});
}

struct Derivative{
 double thermal=0,mechanical=0,fd=0,relative_error=0;
 double adjoint_residual=0;
};

// Production Work::j6, peakPower6 and energy6 integrate over the fixed B6
// observation subdomain, not over the whole ice specimen. P10F's generic
// evaluate() intentionally integrates the entire mesh; this masked variant
// reproduces the production B6 contract on the real H0 mesh.
std::vector<uint8_t> observation_elements(const Mesh& mesh){
 std::vector<uint8_t> mask(mesh.tets.size(),0);
 for(size_t e=0;e<mesh.tets.size();++e){
  V center{};
  for(int j=0;j<4;++j)center=center+mesh.nodes[mesh.tets[e][j]]*.25;
  mask[e]=uint8_t(norm(center-V{0,0,.03})<.006);
 }
 return mask;
}

f10::Sources evaluate_b6(const a10::Step& step,f10::Kind kind,
                         const std::vector<uint8_t>& mask,size_t nquad){
 require(step.qps.size()==mask.size()*nquad,"B6 observation mask mismatch");
 double volume=0;
 for(size_t q=0;q<step.qps.size();++q)
  if(mask[q/nquad])volume+=step.qps[q].volume;
 require(volume>0,"empty B6 observation region");
 f10::Sources result;
 result.displacement.assign(step.u.size(),0.);
 result.temperature.assign(step.node_count,0.);
 result.previous.resize(step.qps.size());
 for(size_t q=0;q<step.qps.size();++q){
  if(!mask[q/nquad])continue;
  const auto& qp=step.qps[q];
  const auto src=f10::point_source(qp,kind);
  const double factor=qp.volume/volume;
  result.value+=factor*src.value;
  auto lstress=src.lambda_sigma;
  auto lnew=src.lambda_next;
  for(int k=0;k<6;++k){
   lstress[k]*=factor;
   lnew.e_d[k]*=factor;lnew.e_v[k]*=factor;
  }
  const auto pb=qp.law.vjp(lstress,lnew);
  auto deps=pb.d_eps;
  for(int k=0;k<6;++k)deps[k]+=factor*src.direct_strain[k];
  const double dT=pb.d_T+factor*src.direct_temperature;
  for(int a=0;a<30;++a){
   const int index=3*qp.nodes[a/3]+a%3;
   if(!step.constrained[index])
    result.displacement[index]+=ice3d::p10b::euclid_dot(qp.B[a],deps);
  }
  for(int a=0;a<10;++a)result.temperature[qp.nodes[a]]+=qp.N[a]*dT;
  result.previous[q]=pb.d_previous;
 }
 return result;
}

std::array<Derivative,3> backward(const Scenario& base,const Scenario& plus,
                                 const Scenario& minus,const Config& c,
                                 const Forward& nom,const Forward& fp,
                                 const Forward& fm){
 const auto qs=volume_q(3);
 const auto mask0=observation_elements(base.mesh);
 const auto maskp=observation_elements(plus.mesh);
 const auto maskm=observation_elements(minus.mesh);
 const auto physical=mechanical_bc(base.mesh);
 const auto pinned=adjoint_bc(base.mesh);
 require(physical==mechanical_bc(plus.mesh)&&physical==mechanical_bc(minus.mesh),
         "shape changes the constrained DOF set");
 const auto topology=build_bcsr_topology(base.mesh);
 BCSR stub;stub.set_topology(topology);
 const e10::ReverseGraph reverse(stub);
 const auto cfg=setting();
 const auto nq=base.mesh.tets.size()*qs.size();
 const double delta=c.delta_um*1e-6;
 const std::array<f10::Kind,3> kinds{f10::Kind::J6,f10::Kind::PeakMoment,f10::Kind::Energy};
 std::array<Derivative,3> results{};
 for(size_t obs=0;obs<3;++obs){
  std::vector<State> future(nq);
  const auto kind=kinds[obs];
  const double chain=kind==f10::Kind::PeakMoment
       ?std::pow(nom.objective[obs],1.-8.)/8.:1.;
  for(int n=c.steps;n>=1;--n){
   const auto& f=nom.frames.at(size_t(n-1));
   const a10::Step step(base.mesh,qs,f.temperature,f.previous,double(c.dt),
                       f.repinned_u,pinned,Modulus::VAR,
                       ice3d::p10b::Controls{true,true});
   const auto source=evaluate_b6(step,kind,mask0,qs.size());
   const double weight=chain*(n==c.steps?.5:1.)/c.steps;
   a10::Output lambda;
   lambda.residual.assign(f.repinned_u.size(),0.);
   lambda.next=future;
   const auto feedback=step.vjp(lambda);
   std::vector<double> rhs(f.repinned_u.size());
   for(size_t i=0;i<rhs.size();++i)
    rhs[i]=-(weight*source.displacement[i]+feedback.displacement[i]);
   auto K=e10::assemble_tangent_bcsr(base.mesh,step,topology);
   auto linear=e10::solve_bicgstab(K,pinned,rhs,true,1e-8,800, &reverse);
   lambda.residual=std::move(linear.x);
   const auto back=step.vjp(lambda);
   double eq=0,ref=0;
   for(size_t i=0;i<rhs.size();++i)if(!pinned[i]){
    const double val=back.displacement[i]+weight*source.displacement[i];
    eq+=val*val;ref+=std::pow(weight*source.displacement[i],2);
   }
   results[obs].adjoint_residual=std::max(results[obs].adjoint_residual,
                          std::sqrt(eq)/std::max(1.,std::sqrt(ref)));
   // Thermal shape tangent is computed from the *full* transient thermal
   // solves on perturbed real H0 geometries, not from a thermal adjoint yet.
   for(size_t i=0;i<f.temperature.size();++i){
    const double dT=(plus.temperatures[size_t(n)][i]-
                     minus.temperatures[size_t(n)][i])/(2*delta);
    results[obs].thermal+=(back.temperature[i]+weight*source.temperature[i])*dT;
   }
   const a10::Step sp(plus.mesh,qs,f.temperature,f.previous,double(c.dt),
                     f.repinned_u,pinned,Modulus::VAR,
                     ice3d::p10b::Controls{true,true});
   const a10::Step sm(minus.mesh,qs,f.temperature,f.previous,double(c.dt),
                     f.repinned_u,pinned,Modulus::VAR,
                     ice3d::p10b::Controls{true,true});
   const auto op=sp.evaluate(),om=sm.evaluate();
   const auto jplus=evaluate_b6(sp,kind,maskp,qs.size()).value;
   const auto jminus=evaluate_b6(sm,kind,maskm,qs.size()).value;
   results[obs].mechanical+=weight*(jplus-jminus)/(2*delta);
   for(size_t i=0;i<lambda.residual.size();++i)
    results[obs].mechanical+=lambda.residual[i]*(op.residual[i]-om.residual[i])/(2*delta);
   for(size_t i=0;i<nq;++i)for(int k=0;k<6;++k){
    results[obs].mechanical+=future[i].e_d[k]*(op.next[i].e_d[k]-om.next[i].e_d[k])/(2*delta);
    results[obs].mechanical+=future[i].e_v[k]*(op.next[i].e_v[k]-om.next[i].e_v[k])/(2*delta);
   }
   for(size_t i=0;i<nq;++i)for(int k=0;k<6;++k){
    future[i].e_d[k]=back.previous[i].e_d[k]+weight*source.previous[i].e_d[k];
    future[i].e_v[k]=back.previous[i].e_v[k]+weight*source.previous[i].e_v[k];
   }
  }
  results[obs].fd=(fp.objective[obs]-fm.objective[obs])/(2*delta);
  results[obs].relative_error=relative(results[obs].mechanical+
                                            results[obs].thermal,results[obs].fd);
 }
 return results;
}

int run(const Config& c){
 require(fs::is_regular_file(c.mesh),"H0 mesh not found: "+c.mesh.string());
 require(!fs::exists(c.out),"output already exists; choose a NEW --out directory");
 fs::create_directories(c.out);
 const auto geom=c.out/"geometry";
 const std::string geo_mode=c.mode=="R"?"radius":c.mode;
 run_external(c.geometry_exe,{"--mesh",c.mesh.string(),"--out",geom.string(),
   "--mode",geo_mode,"--delta-um",std::to_string(c.delta_um),
   "--cutoff-mm",std::to_string(c.cutoff_mm),"--quad","3"});
 const auto core=c.mesh.stem().string()+"_P08_"+geo_mode+"_";
 const auto ending="_"+tag(c.delta_um)+"um.msh";
 const fs::path plus_mesh=geom/(core+"plus"+ending);
 const fs::path minus_mesh=geom/(core+"minus"+ending);
 const std::array<fs::path,3> meshes{c.mesh,plus_mesh,minus_mesh};
 const std::array<std::string,3> names{"base","plus","minus"};
 std::array<Scenario,3> s;
 for(int j=0;j<3;++j){
  const auto td=c.out/("thermal_"+names[size_t(j)]);
  run_external(c.thermal_exe,{"--mesh",meshes[size_t(j)].string(),
    "--out",td.string(),"--dt",std::to_string(c.dt),
    "--tend",std::to_string(c.steps*c.dt),"--xi","0","--compact"});
  s[size_t(j)].mesh=read_msh(meshes[size_t(j)]).mesh;
  s[size_t(j)].temperatures=read_thermal(s[size_t(j)].mesh,td,c);
  s[size_t(j)].tag=names[size_t(j)];
 }
 require(s[0].mesh.nodes.size()==s[1].mesh.nodes.size()&&
         s[0].mesh.nodes.size()==s[2].mesh.nodes.size(),"node mapping changed");
 require(s[0].mesh.tets.size()==s[1].mesh.tets.size()&&
         s[0].mesh.tets.size()==s[2].mesh.tets.size(),"Tet10 mapping changed");
 auto base=forward(s[0],c,true,c.out/"retained");
 auto fp=forward(s[1],c,false);
 auto fm=forward(s[2],c,false);
 // Reproducible replay of the whole real-H0 nonlinear constitutive history.
 const auto Q=volume_q(3);
 auto replay=h10::recover(c.out/"retained",s[0].mesh,setting(),0,0.,Q.size());
 configure();
 for(int n=1;n<=c.steps;++n){
  p06.clear_step();Work w;
  (void)nonlinear_step(s[0].mesh,Q,s[0].temperatures[size_t(n)],
                       replay,double(c.dt),setting(),mechanical_bc(s[0].mesh),w);
  (void)zeroMeanZ(s[0].mesh,Q,replay);
  replay.lastTime=n*double(c.dt);
 }
 p10i::configure_production();
 identical_field(replay,h10::recover(c.out/"retained",s[0].mesh,setting(),
                                     c.steps,c.steps*double(c.dt),Q.size()));
 const auto derivatives=backward(s[0],s[1],s[2],c,base,fp,fm);
 const std::array<const char*,3> namesJ{"j6","jpeak","jen"};
 std::ofstream csv(c.out/"P10K_H0_COUPLED_CHECK.csv");
 csv<<std::setprecision(17)
    <<"functional,mechanical_partial_per_m,thermal_chain_per_m,hybrid_total_per_m,full_FD_per_m,relative_error,adjoint_equilibrium_rel\n";
 double worst=0,worst_eq=0;
 for(int j=0;j<3;++j){
  const auto& x=derivatives[size_t(j)];
  csv<<namesJ[size_t(j)]<<','<<x.mechanical<<','<<x.thermal<<','
     <<(x.mechanical+x.thermal)<<','<<x.fd<<','<<x.relative_error<<','
     <<x.adjoint_residual<<'\n';
  std::cout<<std::scientific<<std::setprecision(10)
    <<"P10K_FUNCTIONAL name="<<namesJ[size_t(j)]
    <<" mechanical="<<x.mechanical<<" thermal="<<x.thermal
    <<" full_fd="<<x.fd<<" rel="<<x.relative_error<<'\n';
  worst=std::max(worst,x.relative_error);
  worst_eq=std::max(worst_eq,x.adjoint_residual);
 }
 csv.close();require(bool(csv),"failed to finish output CSV");
 require(std::isfinite(worst)&&std::isfinite(worst_eq),"nonfinite adjoint output");
 // Acceptance conditions apply to this coarse-mesh pilot, not to mesh/time
 // convergence of the physical shape gradient or a completed thermal adjoint.
 const bool accepted=(worst<5e-3&&worst_eq<1e-5);
 std::cout<<(accepted?"P10K_H0_HYBRID_OK":"P10K_H0_HYBRID_FAIL")
   <<" mesh="<<c.mesh.filename().string()
   <<" nodes="<<s[0].mesh.nodes.size()<<" tet10="<<s[0].mesh.tets.size()
   <<" steps="<<c.steps<<" dt="<<c.dt<<" mode="<<c.mode
   <<" delta_um="<<c.delta_um<<" replay_bitwise=1"
   <<" worst_coupled_FD_rel="<<std::scientific<<worst
   <<" worst_adjoint_equilibrium_rel="<<worst_eq
   <<" thermal_tangent=FD_full_history thermal_adjoint=NOT_YET_IMPLEMENTED\n";
 return accepted?0:3;
}
} // namespace p10k

int main(int argc,char**argv){
 try{
  const auto config=p10k::parse(argc,argv);
#ifdef _OPENMP
  omp_set_dynamic(0);omp_set_num_threads(config.threads);
#endif
  if(config.selftest)return p10i::run_tests();
  return p10k::run(config);
 }catch(const std::exception& error){
  std::cerr<<"P10K_ERROR: "<<error.what()<<'\n';return 2;
 }
}
