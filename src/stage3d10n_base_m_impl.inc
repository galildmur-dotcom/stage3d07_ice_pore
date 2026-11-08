// Stage 3D-10M: mesh/time convergence of the TRUE coupled P10L shape adjoint.
// One base EDV_VAR forward and three reverse functionals. The two perturbed
// meshes are used ONLY to differentiate the mechanical operator at a FROZEN
// state; no +/- thermal/mechanical forward histories are solved here.
// P10L's H0 independent +/- nonlinear verification remains the reference.
#define STAGE3D10L_NO_MAIN
#include "stage3d10l_h0_full_thermal_adjoint.cpp"
#include <chrono>

namespace p10m {
namespace H=ice3d::p10l;
namespace A=ice3d::p10c;
namespace E=ice3d::p10e;
namespace F=ice3d::p10f;

struct Result {
 double mechanical=0,thermal=0,mechanical_eq=0,thermal_eq=0;
 int thermal_cg=0;
};

double pore_median_edge(const Mesh& mesh,int& pore_faces){
 std::vector<double> edges;
 for(const auto& f:mesh.faces)if(f.tag==8){
  ++pore_faces;
  for(int j=0;j<3;++j)
   edges.push_back(norm(mesh.nodes[f.nodes[j]]-
                        mesh.nodes[f.nodes[(j+1)%3]]));
 }
 p10k::require(!edges.empty(),"P10M missing pore Tri6");
 auto middle=edges.begin()+edges.size()/2;
 std::nth_element(edges.begin(),middle,edges.end());
 return *middle;
}

double b6_volume(const Mesh& mesh,const std::vector<uint8_t>& mask){
 double volume=0;
 for(size_t e=0;e<mesh.tets.size();++e){
  if(!mask[e])continue;
  for(auto a:g4)for(auto b:g4)for(auto c:g4){
   const double r=a.x,s=(1-r)*b.x,t=(1-r)*(1-b.x)*c.x;
   volume+=teval(mesh,mesh.tets[e],r,s,t).det*
              a.w*b.w*c.w*(1-r)*(1-r)*(1-b.x);
  }
 }
 p10k::require(volume>0,"P10M empty B6 mask");
 return volume;
}

std::array<Result,3> reverse_only(const p10k::Scenario& base,
                                  const p10k::Scenario& plus,
                                  const p10k::Scenario& minus,
                                  const p10k::Config& c,
                                  const p10k::Forward& nominal,
                                  const H::Operator& heat){
 const auto quad=volume_q(3);
 const auto mask=p10k::observation_elements(base.mesh);
 const auto maskp=p10k::observation_elements(plus.mesh);
 const auto maskm=p10k::observation_elements(minus.mesh);
 p10k::require(mask==maskp&&mask==maskm,
               "P10M B6 mask changed under +/- geometry deformation");
 const auto pinned=p10k::adjoint_bc(base.mesh);
 p10k::require(pinned==p10k::adjoint_bc(plus.mesh)&&
               pinned==p10k::adjoint_bc(minus.mesh),
               "P10M moving mechanical constraints");
 const auto topology=build_bcsr_topology(base.mesh);
 BCSR sparse;sparse.set_topology(topology);
 const E::ReverseGraph graph(sparse);
 const size_t nq=base.mesh.tets.size()*quad.size();
 const double delta=c.delta_um*1e-6;
 const std::array<F::Kind,3> kinds{
   F::Kind::J6,F::Kind::PeakMoment,F::Kind::Energy};
 std::array<Result,3> result{};
 std::array<std::vector<State>,3> futures;
 std::array<std::vector<std::vector<double>>,3> source_heats;
 std::array<double,3> chains{};
 for(size_t obs=0;obs<3;++obs){
  futures[obs].resize(nq);
  source_heats[obs].assign(size_t(c.steps+1),
                             std::vector<double>(base.mesh.nodes.size(),0.));
  chains[obs]=kinds[obs]==F::Kind::PeakMoment
      ?std::pow(nominal.objective[obs],1.-8.)/8.:1.;
 }
 // The nonlinear tangent and frozen-state geometric operators depend on the
 // STATE, not on the objective. Assemble them ONCE per backward time step,
 // then solve the three independent functional adjoints against the same K.
 for(int n=c.steps;n>=1;--n){
  const auto reverse_begin=std::chrono::steady_clock::now();
  const auto& frame=nominal.frames.at(size_t(n-1));
  const A::Step state(base.mesh,quad,frame.temperature,frame.previous,
                     double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
                     ice3d::p10b::Controls{true,true});
  auto tangent=E::assemble_tangent_bcsr(base.mesh,state,topology);
  const A::Step state_p(plus.mesh,quad,frame.temperature,frame.previous,
      double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
      ice3d::p10b::Controls{true,true});
  const A::Step state_m(minus.mesh,quad,frame.temperature,frame.previous,
      double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
      ice3d::p10b::Controls{true,true});
  const auto op=state_p.evaluate(),om=state_m.evaluate();
  for(size_t obs=0;obs<3;++obs){
   auto& out=result[obs];
   auto& future=futures[obs];
   const auto kind=kinds[obs];
   const auto src=p10k::evaluate_b6(state,kind,mask,quad.size());
   const double weight=chains[obs]*(n==c.steps?.5:1.)/c.steps;
   A::Output lambda;
   lambda.residual.assign(frame.repinned_u.size(),0.);
   lambda.next=future;
   const auto feedback=state.vjp(lambda);
   std::vector<double> rhs(frame.repinned_u.size());
   for(size_t i=0;i<rhs.size();++i)
    rhs[i]=-(weight*src.displacement[i]+feedback.displacement[i]);
   // On increasingly fine meshes a block-Jacobi BiCGStab solve can need
   // more than 1200 iterations, and near-machine-precision stopping can
   // stagnate even when the actual discrete adjoint equilibrium is accurate.
   // Each attempt is independently checked against the TRUE K^T residual
   // inside P10E.  The physical VJP equilibrium is checked again below.
   const std::array<std::pair<double,int>,3> attempts{{
       {1e-11,2400},{2e-10,3600},{1e-9,5000}}};
   E::IterativeResult solution;
   bool solved=false;
   for(size_t retry=0;retry<attempts.size();++retry){
    const auto [tol,maxiter]=attempts[retry];
    try{
     solution=E::solve_bicgstab(tangent,pinned,rhs,true,tol,maxiter,&graph);
     solved=true;
     std::cout<<"P10M_LINEAR_SOLVED step="<<n
              <<" functional="<<obs<<" retry="<<retry
              <<" tolerance="<<tol<<" iterations="<<solution.iterations
              <<" verified_relative_residual="<<solution.relative_residual
              <<'\n'<<std::flush;
     break;
    }catch(const std::runtime_error& e){
     if(std::string(e.what()).find("P10E: BiCGStab")!=0)throw;
     std::cout<<"P10M_LINEAR_RETRY step="<<n
              <<" functional="<<obs<<" retry="<<retry
              <<" tolerance="<<tol<<" iterations_limit="<<maxiter
              <<" reason="<<e.what()<<'\n'<<std::flush;
    }
   }
   p10k::require(solved,"P10M adjoint BiCGStab exhausted verified retries");
   lambda.residual=std::move(solution.x);
   const auto back=state.vjp(lambda);
   double eq=0,ref=0;
   for(size_t i=0;i<rhs.size();++i)if(!pinned[i]){
    const double residual=back.displacement[i]+weight*src.displacement[i];
    eq+=residual*residual;
    ref+=std::pow(weight*src.displacement[i],2);
   }
   out.mechanical_eq=std::max(out.mechanical_eq,
                              std::sqrt(eq)/std::max(1.,std::sqrt(ref)));
   p10k::require(out.mechanical_eq<1e-6,
     "P10M adjoint VJP equilibrium is insufficient after linear solve");
   for(size_t i=0;i<source_heats[obs][size_t(n)].size();++i)
    source_heats[obs][size_t(n)][i]=back.temperature[i]+weight*src.temperature[i];
   const double jplus=p10k::evaluate_b6(state_p,kind,maskp,quad.size()).value;
   const double jminus=p10k::evaluate_b6(state_m,kind,maskm,quad.size()).value;
   out.mechanical+=weight*(jplus-jminus)/(2*delta);
   for(size_t i=0;i<lambda.residual.size();++i)
    out.mechanical+=lambda.residual[i]*
                (op.residual[i]-om.residual[i])/(2*delta);
   for(size_t i=0;i<nq;++i)for(int k=0;k<6;++k){
    out.mechanical+=future[i].e_d[k]*
       (op.next[i].e_d[k]-om.next[i].e_d[k])/(2*delta);
    out.mechanical+=future[i].e_v[k]*
       (op.next[i].e_v[k]-om.next[i].e_v[k])/(2*delta);
   }
   for(size_t i=0;i<nq;++i)for(int k=0;k<6;++k){
    future[i].e_d[k]=back.previous[i].e_d[k]+weight*src.previous[i].e_d[k];
    future[i].e_v[k]=back.previous[i].e_v[k]+weight*src.previous[i].e_v[k];
   }
  }
  std::cout<<"P10M_ADJOINT_BACKWARD step="<<n<<"/"<<c.steps
           <<" wall_s="<<std::chrono::duration<double>(
                std::chrono::steady_clock::now()-reverse_begin).count()
           <<'\n'<<std::flush;
 }
 for(size_t obs=0;obs<3;++obs){
  auto& out=result[obs];
  const auto heat_grad=H::adjoint_derivative(heat,double(c.dt),
                         base.temperatures,source_heats[obs]);
  out.thermal=heat_grad.derivative;
  out.thermal_eq=heat_grad.worst_equilibrium;
  out.thermal_cg=heat_grad.iterations;
  std::cout<<std::scientific<<std::setprecision(11)
    <<"P10M_GRAD functional="<<(obs==0?"j6":obs==1?"jpeak":"jen")
    <<" mechanical="<<out.mechanical<<" thermal="<<out.thermal
    <<" total="<<out.mechanical+out.thermal
    <<" mechanical_eq="<<out.mechanical_eq
    <<" thermal_eq="<<out.thermal_eq<<'\n';
 }
 return result;
}

int run(const p10k::Config& c){
 const auto wallstart=std::chrono::steady_clock::now();
 p10k::require(fs::is_regular_file(c.mesh),"P10M mesh not found");
 p10k::require(c.steps*c.dt==900,
               "P10M requires fixed physical horizon 900 s; steps * dt != 900");
 p10k::require(!fs::exists(c.out),"P10M --out must be a NEW folder");
 fs::create_directories(c.out);
 const auto geom=c.out/"geometry";
 const std::string geomode=c.mode=="R"?"radius":c.mode;
 p10k::run_external(c.geometry_exe,{"--mesh",c.mesh.string(),
       "--out",geom.string(),"--mode",geomode,
       "--delta-um",std::to_string(c.delta_um),"--cutoff-mm",
       std::to_string(c.cutoff_mm),"--quad","3"});
 const auto stem=c.mesh.stem().string()+"_P08_"+geomode+"_";
 const auto suffix="_"+p10k::tag(c.delta_um)+"um.msh";
 p10k::Scenario base,plus,minus;
 base.mesh=read_msh(c.mesh).mesh;
 plus.mesh=read_msh(geom/(stem+"plus"+suffix)).mesh;
 minus.mesh=read_msh(geom/(stem+"minus"+suffix)).mesh;
 p10k::require(base.mesh.tets==plus.mesh.tets&&
               base.mesh.tets==minus.mesh.tets&&
               base.mesh.nodes.size()==plus.mesh.nodes.size()&&
               base.mesh.nodes.size()==minus.mesh.nodes.size(),
               "P10M mismatch in +/- Tet10 mesh connectivity");
 const auto mask=p10k::observation_elements(base.mesh);
 p10k::require(mask==p10k::observation_elements(plus.mesh)&&
               mask==p10k::observation_elements(minus.mesh),
               "P10M moving observation elements in B6");
 int pore_faces=0;
 const double hedge=pore_median_edge(base.mesh,pore_faces);
 const double vB6=b6_volume(base.mesh,mask);
 const double delta=c.delta_um*1e-6;
 const auto velocity=p10l::geometry_velocity(plus.mesh,minus.mesh,delta);
 const auto heat=H::assemble(base.mesh,velocity,double(c.dt));
 p10k::require(heat.max_ones_error<1e-7&&
               heat.max_directional_ones_error<1e-7,
               "P10M thermal operator violates constant-temperature identity");
 base.temperatures=H::solve_forward(heat,c.steps,double(c.dt));
 base.tag="base_only";
 const auto nq=base.mesh.tets.size()*volume_q(3).size();
 const double history_gib=double(c.steps)*double(nq)*sizeof(State)/
                          (1024.*1024.*1024.);
 const double state_buffers_gib=double(c.steps+4)*double(nq)*sizeof(State)/
                                (1024.*1024.*1024.);
 const double final_checkpoint_gib=double(
          ice3d::p10h::estimate_single_bytes(base.mesh,volume_q(3).size()))/
          (1024.*1024.*1024.);
 p10k::require(state_buffers_gib<8.,
   "P10M estimated persistent state buffers exceed 8 GiB; "
   "use a windowed checkpoint adjoint for this mesh/time resolution");
 p10k::require(final_checkpoint_gib<2.,
   "P10M final checkpoint exceeds 2 GiB disk budget; "
   "use a windowed checkpoint adjoint for this mesh/time resolution");
 std::cout<<std::scientific<<std::setprecision(11)
   <<"P10M_PREFLIGHT mesh="<<c.mesh.stem().string()
   <<" nodes="<<base.mesh.nodes.size()<<" tet10="<<base.mesh.tets.size()
   <<" pore_tri6="<<pore_faces<<" pore_median_edge_mm="<<hedge*1e3
   <<" B6_volume_m3="<<vB6<<" steps="<<c.steps
   <<" dt="<<c.dt<<" delta_um="<<c.delta_um
   <<" estimated_held_history_gib="<<history_gib
   <<" estimated_state_buffers_gib="<<state_buffers_gib
   <<" estimated_final_checkpoint_gib="<<final_checkpoint_gib
   <<" retained_checkpoints=1"
   <<" thermal_constant_error="<<heat.max_ones_error
   <<" thermal_directional_constant_error="<<heat.max_directional_ones_error
   <<" thermal_perturbed_forward_solves=0\n";
 if(c.preflight){
  const double parity=p10l::geometry_tangent_parity(heat,plus.mesh,minus.mesh,
                                                    double(c.dt),delta);
  p10k::require(parity<5e-3,
                "P10M thermal matrix derivative preflight mismatch");
  std::cout<<"P10M_PREFLIGHT_OK mesh="<<c.mesh.stem().string()
           <<" heat_operator_derivative_rel="<<parity
           <<" mechanical_forward_solves=0\n";
  return 0;
 }
 // P10K's 0.2-GiB disk budget reserves TWO snapshots (initial and final).
 // P10M keeps the complete short history in RAM and only re-reads the FINAL
 // state to test bitwise checkpoint correctness. Retain exactly that final
 // state, under the explicit 2-GiB single-snapshot budget checked above.
 // This leaves legacy P10K/P10L and their retention policies unchanged.
 const auto nominal=p10k::forward(base,c,true);
 const auto history_dir=c.out/"retained";
 fs::create_directories(history_dir/"adjoint_history");
 ice3d::p10h::retain(history_dir,base.mesh,p10k::setting(),
                     nominal.final_state,c.steps);
 const auto qs=volume_q(3);
 const auto restored=ice3d::p10h::recover(history_dir,base.mesh,
        p10k::setting(),c.steps,c.steps*double(c.dt),qs.size());
 p10i::configure_production();
 identical_field(restored,nominal.final_state);
 const auto grads=reverse_only(base,plus,minus,c,nominal,heat);
 const double wall=std::chrono::duration<double>(
          std::chrono::steady_clock::now()-wallstart).count();
 const fs::path csvpath=c.out/"P10M_SHAPE_GRADIENT.csv";
 std::ofstream csv(csvpath);
 p10k::require(bool(csv),"P10M cannot open result CSV");
 csv<<std::setprecision(17)
   <<"mesh,nodes,tet10,pore_tri6,pore_median_edge_mm,B6_volume_m3,"
   <<"dt_s,steps,horizon_s,delta_um,mode,law,modulus,functional,objective,"
   <<"mechanical_partial_per_m,thermal_adjoint_per_m,total_adjoint_per_m,"
   <<"mechanical_equilibrium_rel,thermal_equilibrium_rel,thermal_CG_iterations,"
   <<"estimated_history_gib,wall_s\n";
 const std::array<std::string,3> names{"j6","jpeak","jen"};
 double worst_mech=0,worst_heat=0;
 for(size_t k=0;k<3;++k){
  const auto& r=grads[k];
  csv<<c.mesh.stem().string()<<','<<base.mesh.nodes.size()<<','
     <<base.mesh.tets.size()<<','<<pore_faces<<','<<hedge*1e3<<','<<vB6<<','
     <<c.dt<<','<<c.steps<<','<<c.steps*c.dt<<','<<c.delta_um<<','
     <<c.mode<<",EDV,VAR,"<<names[k]<<','<<nominal.objective[k]<<','
     <<r.mechanical<<','<<r.thermal<<','<<(r.mechanical+r.thermal)<<','
     <<r.mechanical_eq<<','<<r.thermal_eq<<','<<r.thermal_cg<<','
     <<history_gib<<','<<wall<<'\n';
  worst_mech=std::max(worst_mech,r.mechanical_eq);
  worst_heat=std::max(worst_heat,r.thermal_eq);
 }
 csv.close();p10k::require(bool(csv),"P10M CSV write failure");
 const bool ok=worst_mech<1e-5&&worst_heat<1e-7;
 std::cout<<(ok?"P10M_COUPLED_SHAPE_GRADIENT_OK":"P10M_COUPLED_SHAPE_GRADIENT_FAIL")
   <<" mesh="<<c.mesh.stem().string()<<" steps="<<c.steps<<" dt="<<c.dt
   <<" nodes="<<base.mesh.nodes.size()<<" tet10="<<base.mesh.tets.size()
   <<" delta_um="<<c.delta_um<<" wall_s="<<wall
   <<" max_mechanical_equilibrium_rel="<<worst_mech
   <<" max_thermal_equilibrium_rel="<<worst_heat
   <<" checkpoint_roundtrip_bitwise=1"
   <<" nonlinear_forward_solves=1"
   <<" thermal_perturbed_forward_solves=0"
   <<" mechanical_perturbed_forward_solves=0"
   <<" mechanical_shape_partial=LOCAL_CENTERED_FD"
   <<" thermal_shape_partial=ANALYTIC\n";
 return ok?0:3;
}
} // namespace p10m

int stage3d10n_hidden_stage3d10m_main(int argc,char** argv){
 try{
  bool explicit_mesh=false,explicit_out=false;
  for(int i=1;i<argc;++i){
   const std::string arg=argv[i];
   if(arg=="--mesh")explicit_mesh=true;
   if(arg=="--out")explicit_out=true;
  }
  const auto c=p10k::parse(argc,argv);
#ifdef _OPENMP
  omp_set_dynamic(0);omp_set_num_threads(c.threads);
#endif
  if(c.selftest)return p10i::run_tests();
  p10k::require(explicit_mesh&&explicit_out,
    "P10M requires explicit --mesh and --out; refusing implicit P10K defaults");
  return p10m::run(c);
 }catch(const std::exception& e){
  std::cerr<<"P10M_ERROR: "<<e.what()<<'\n';return 2;
 }
}
