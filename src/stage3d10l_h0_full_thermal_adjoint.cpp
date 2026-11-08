// Stage 3D-10L: real H0, fully discrete heat+EDV_VAR shape adjoint.
// Mechanical history and functional B6 restrictions are imported unchanged
// from the independently verified P10K harness.  Thermal backward Euler
// admits an exact analytical mesh-coordinate directional derivative.
#define STAGE3D10K_NO_MAIN
#include "stage3d10k_h0_coupled_pilot.cpp"
#include "stage3d10l_thermal_adjoint.hpp"

namespace p10l {
namespace H=ice3d::p10l;
namespace A=ice3d::p10c;
namespace E=ice3d::p10e;
namespace F=ice3d::p10f;

struct Result {
 double mechanical=0,thermal_adjoint=0,thermal_fd=0,full_fd=0;
 double rel_full=0,rel_thermal=0;
 double mechanical_eq=0,heat_eq=0;
 int heat_cg=0;
};

std::vector<V> geometry_velocity(const Mesh& plus,const Mesh& minus,
                                  double delta){
 p10k::require(plus.nodes.size()==minus.nodes.size(),
               "P10L geometry node map mismatch");
 std::vector<V> v(plus.nodes.size());
 for(size_t i=0;i<v.size();++i)
  v[i]=(plus.nodes[i]-minus.nodes[i])/(2*delta);
 return v;
}

struct ScenarioPack {
 std::array<p10k::Scenario,3> s;
};

ScenarioPack load_scenarios(const p10k::Config& c){
 const auto geom=c.out/"geometry";
 const std::string geo_mode=c.mode=="R"?"radius":c.mode;
 p10k::run_external(c.geometry_exe,{"--mesh",c.mesh.string(),
  "--out",geom.string(),"--mode",geo_mode,"--delta-um",
  std::to_string(c.delta_um),"--cutoff-mm",std::to_string(c.cutoff_mm),
  "--quad","3"});
 const auto core=c.mesh.stem().string()+"_P08_"+geo_mode+"_";
 const auto end="_"+p10k::tag(c.delta_um)+"um.msh";
 const std::array<fs::path,3> meshes{
   c.mesh,geom/(core+"plus"+end),geom/(core+"minus"+end)};
 const std::array<std::string,3> names{"base","plus","minus"};
 ScenarioPack pack;
 for(int j=0;j<3;++j){
  const auto dir=c.out/("thermal_"+names[size_t(j)]);
  p10k::run_external(c.thermal_exe,{"--mesh",meshes[size_t(j)].string(),
    "--out",dir.string(),"--dt",std::to_string(c.dt),"--tend",
    std::to_string(c.steps*c.dt),"--xi","0","--compact"});
  auto& s=pack.s[size_t(j)];
  s.mesh=read_msh(meshes[size_t(j)]).mesh;
  s.temperatures=p10k::read_thermal(s.mesh,dir,c);
  s.tag=names[size_t(j)];
 }
 for(int j=1;j<3;++j){
  p10k::require(pack.s[0].mesh.nodes.size()==pack.s[size_t(j)].mesh.nodes.size(),
                "P10L nonmatching node map");
  p10k::require(pack.s[0].mesh.tets==pack.s[size_t(j)].mesh.tets,
                "P10L nonmatching Tet10 connectivity");
 }
 return pack;
}

double max_heat_parity(const H::Operator& op,
                      const p10k::Scenario& base,const p10k::Config& c){
 const auto regenerated=H::solve_forward(op,c.steps,double(c.dt));
 double largest=0;
 for(int n=1;n<=c.steps;++n)
  for(size_t i=0;i<regenerated[size_t(n)].size();++i)
   largest=std::max(largest,std::abs(regenerated[size_t(n)][i]-
                                  base.temperatures[size_t(n)][i]));
 return largest;
}

// Independent verification of geometry derivatives for all three thermal
// operators, assembled afresh on the +delta and -delta curved Tet10 grids.
double geometry_tangent_parity(const H::Operator& a,const Mesh& plus,
                              const Mesh& minus,double dt,double delta){
 const std::vector<V> zero(plus.nodes.size());
 const auto p=H::assemble(plus,zero,dt);
 const auto m=H::assemble(minus,zero,dt);
 auto compare=[&](const std::vector<double>& exact,
                 const std::vector<double>& p,
                 const std::vector<double>& m){
  double num=0,den=0;
  p10k::require(exact.size()==p.size()&&p.size()==m.size(),
                "P10L operator matrix pattern mismatch");
  for(size_t i=0;i<exact.size();++i){
   const double fd=(p[i]-m[i])/(2*delta);
   const double difference=fd-exact[i];
   num+=difference*difference;
   den+=exact[i]*exact[i];
  }
  return std::sqrt(num)/std::max(1e-20,std::sqrt(den));
 };
 double worst=0;
 worst=std::max(worst,compare(a.shape.mass,p.primal.mass,m.primal.mass));
 worst=std::max(worst,compare(a.shape.conduct,p.primal.conduct,m.primal.conduct));
 worst=std::max(worst,compare(a.shape.robinload,p.primal.robinload,
                              m.primal.robinload));
 return worst;
}

std::array<Result,3> backward(const p10k::Scenario& base,
                              const p10k::Scenario& plus,
                              const p10k::Scenario& minus,
                              const p10k::Config& c,
                              const p10k::Forward& nominal,
                              const p10k::Forward& fp,
                              const p10k::Forward& fm,
                              const H::Operator& heat){
 const auto quadrature=volume_q(3);
 const auto masks=p10k::observation_elements(base.mesh);
 const auto maskp=p10k::observation_elements(plus.mesh);
 const auto maskm=p10k::observation_elements(minus.mesh);
 const auto pinned=p10k::adjoint_bc(base.mesh);
 p10k::require(pinned==p10k::adjoint_bc(plus.mesh)&&
               pinned==p10k::adjoint_bc(minus.mesh),
               "P10L moving mechanical constraints");
 const auto topology=build_bcsr_topology(base.mesh);
 BCSR sparse;sparse.set_topology(topology);
 const E::ReverseGraph reverse(sparse);
 const size_t nq=base.mesh.tets.size()*quadrature.size();
 const double delta=c.delta_um*1e-6;
 const std::array<F::Kind,3> kinds{
    F::Kind::J6,F::Kind::PeakMoment,F::Kind::Energy};
 std::array<Result,3> results{};
 for(size_t obs=0;obs<3;++obs){
  const auto kind=kinds[obs];
  const double chain=kind==F::Kind::PeakMoment
    ?std::pow(nominal.objective[obs],1.-8.)/8.:1.;
  std::vector<State> future(nq);
  std::vector<std::vector<double>> heat_source(
      size_t(c.steps+1),std::vector<double>(base.mesh.nodes.size(),0.));
  auto& r=results[obs];
  for(int n=c.steps;n>=1;--n){
   const auto& frame=nominal.frames.at(size_t(n-1));
   const A::Step step(base.mesh,quadrature,frame.temperature,frame.previous,
          double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
          ice3d::p10b::Controls{true,true});
   const auto source=p10k::evaluate_b6(step,kind,masks,quadrature.size());
   const double weight=chain*(n==c.steps?.5:1.)/c.steps;
   A::Output lambda;
   lambda.residual.assign(frame.repinned_u.size(),0.);
   lambda.next=future;
   const auto feedback=step.vjp(lambda);
   std::vector<double> rhs(frame.repinned_u.size());
   for(size_t i=0;i<rhs.size();++i)
    rhs[i]=-(weight*source.displacement[i]+feedback.displacement[i]);
   auto K=E::assemble_tangent_bcsr(base.mesh,step,topology);
   auto solution=E::solve_bicgstab(K,pinned,rhs,true,1e-8,800,&reverse);
   lambda.residual=std::move(solution.x);
   const auto pullback=step.vjp(lambda);
   double eq=0,ref=0;
   for(size_t i=0;i<rhs.size();++i)if(!pinned[i]){
    const double val=pullback.displacement[i]+weight*source.displacement[i];
    eq+=val*val;ref+=std::pow(weight*source.displacement[i],2);
   }
   r.mechanical_eq=std::max(r.mechanical_eq,
                           std::sqrt(eq)/std::max(1.,std::sqrt(ref)));
   for(size_t i=0;i<heat_source[size_t(n)].size();++i)
    heat_source[size_t(n)][i]=pullback.temperature[i]+
                              weight*source.temperature[i];
   const A::Step sp(plus.mesh,quadrature,frame.temperature,frame.previous,
        double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
        ice3d::p10b::Controls{true,true});
   const A::Step sm(minus.mesh,quadrature,frame.temperature,frame.previous,
        double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
        ice3d::p10b::Controls{true,true});
   const auto op=sp.evaluate(),om=sm.evaluate();
   const double jp=p10k::evaluate_b6(sp,kind,maskp,quadrature.size()).value;
   const double jm=p10k::evaluate_b6(sm,kind,maskm,quadrature.size()).value;
   r.mechanical+=weight*(jp-jm)/(2*delta);
   for(size_t i=0;i<lambda.residual.size();++i)
    r.mechanical+=lambda.residual[i]*(op.residual[i]-om.residual[i])/(2*delta);
   for(size_t i=0;i<nq;++i)for(int k=0;k<6;++k){
    r.mechanical+=future[i].e_d[k]*(op.next[i].e_d[k]-om.next[i].e_d[k])/(2*delta);
    r.mechanical+=future[i].e_v[k]*(op.next[i].e_v[k]-om.next[i].e_v[k])/(2*delta);
   }
   for(size_t i=0;i<nq;++i)for(int k=0;k<6;++k){
    future[i].e_d[k]=pullback.previous[i].e_d[k]+weight*source.previous[i].e_d[k];
    future[i].e_v[k]=pullback.previous[i].e_v[k]+weight*source.previous[i].e_v[k];
   }
  }
  const auto h=H::adjoint_derivative(heat,double(c.dt),base.temperatures,
                                    heat_source);
  r.thermal_adjoint=h.derivative;r.heat_eq=h.worst_equilibrium;
  r.heat_cg=h.iterations;
  r.thermal_fd=H::independent_thermal_fd(heat_source,plus.temperatures,
                                        minus.temperatures,delta);
  r.rel_thermal=p10k::relative(r.thermal_adjoint,r.thermal_fd);
  r.full_fd=(fp.objective[obs]-fm.objective[obs])/(2*delta);
  r.rel_full=p10k::relative(r.mechanical+r.thermal_adjoint,r.full_fd);
 }
 return results;
}

int run(const p10k::Config& c){
 p10k::require(fs::is_regular_file(c.mesh),"P10L H0 mesh not found");
 p10k::require(!fs::exists(c.out),"P10L --out must be a new directory");
 fs::create_directories(c.out);
 auto group=load_scenarios(c);
 auto& base=group.s[0];auto& plus=group.s[1];auto& minus=group.s[2];
 const double delta=c.delta_um*1e-6;
 const auto velocity=geometry_velocity(plus.mesh,minus.mesh,delta);
 const auto heat=H::assemble(base.mesh,velocity,double(c.dt));
 const double parity=max_heat_parity(heat,base,c);
 const double matparity=geometry_tangent_parity(heat,plus.mesh,minus.mesh,
                                               double(c.dt),delta);
 std::cout<<std::scientific<<std::setprecision(12)
   <<"P10L_HEAT_PREFLIGHT max_forward_temperature_diff_K="<<parity
   <<" max_geometry_operator_rel="<<matparity
   <<" partition_error="<<heat.max_ones_error
   <<" directional_partition_error="<<heat.max_directional_ones_error<<'\n';
 p10k::require(parity<1e-7,"P10L does not reproduce Stage3D02 thermal state");
 p10k::require(matparity<5e-3,"P10L analytic heat geometry derivative mismatch");
 if(c.preflight){
  // Verify the full time-adjoint identity on H0 before any EDV mechanics:
  // the independent temperature histories on +/- geometries are used only
  // as a reference for this synthetic, deterministic temperature objective.
  std::vector<std::vector<double>> q(size_t(c.steps+1),
                            std::vector<double>(base.mesh.nodes.size(),0.));
  for(int n=1;n<=c.steps;++n)for(size_t i=0;i<q[size_t(n)].size();++i){
   const V x=base.mesh.nodes[i]-V{0,0,.03};
   if(norm(x)<.006)
    q[size_t(n)][i]=(1+.1*n)*std::sin(.0143*double(i)+n);
  }
  const auto ad=H::adjoint_derivative(heat,double(c.dt),base.temperatures,q);
  const auto fd=H::independent_thermal_fd(q,plus.temperatures,
                                         minus.temperatures,delta);
  const double relative=p10k::relative(ad.derivative,fd);
  std::cout<<"P10L_THERMAL_ONLY_ADJOINT_"
    <<(relative<1e-2&&ad.worst_equilibrium<1e-7?"OK":"FAIL")
    <<" steps="<<c.steps<<" analytic="<<ad.derivative<<" fd="<<fd
    <<" rel="<<relative<<" heat_eq="<<ad.worst_equilibrium
    <<" CG="<<ad.iterations<<" forward_solves=0\n";
  return relative<1e-2&&ad.worst_equilibrium<1e-7?0:3;
 }
 const auto nominal=p10k::forward(base,c,true,c.out/"retained");
 const auto fp=p10k::forward(plus,c,false);
 const auto fm=p10k::forward(minus,c,false);
 // Mechanical checkpoint replay verification, same as the verified P10K.
 const auto quad=volume_q(3);
 auto replay=ice3d::p10h::recover(c.out/"retained",base.mesh,
                                  p10k::setting(),0,0.,quad.size());
 p10k::configure();
 for(int n=1;n<=c.steps;++n){
  p06.clear_step();Work w;
  (void)nonlinear_step(base.mesh,quad,base.temperatures[size_t(n)],
          replay,double(c.dt),p10k::setting(),p10k::mechanical_bc(base.mesh),w);
  (void)zeroMeanZ(base.mesh,quad,replay);replay.lastTime=n*double(c.dt);
 }
 p10i::configure_production();
 identical_field(replay,ice3d::p10h::recover(c.out/"retained",base.mesh,
                      p10k::setting(),c.steps,c.steps*double(c.dt),quad.size()));
 const auto result=backward(base,plus,minus,c,nominal,fp,fm,heat);
 std::ofstream csv(c.out/"P10L_H0_THERMAL_ADJOINT.csv");
 csv<<std::setprecision(17)
   <<"functional,mechanical_partial_per_m,thermal_adjoint_per_m,"
   <<"thermal_chain_reference_FD_per_m,total_adjoint_per_m,full_FD_per_m,"
   <<"thermal_adjoint_rel,full_shape_rel,mechanical_equilibrium_rel,"
   <<"thermal_equilibrium_rel,thermal_CG_iterations\n";
 double worst=0,worst_thermal=0,worst_meq=0,worst_teq=0;
 const std::array<std::string,3> names{"j6","jpeak","jen"};
 for(size_t j=0;j<3;++j){
  const auto& x=result[j];
  csv<<names[j]<<','<<x.mechanical<<','<<x.thermal_adjoint<<','<<x.thermal_fd
    <<','<<(x.mechanical+x.thermal_adjoint)<<','<<x.full_fd<<','
    <<x.rel_thermal<<','<<x.rel_full<<','<<x.mechanical_eq<<','
    <<x.heat_eq<<','<<x.heat_cg<<'\n';
  worst=std::max(worst,x.rel_full);
  worst_thermal=std::max(worst_thermal,x.rel_thermal);
  worst_meq=std::max(worst_meq,x.mechanical_eq);
  worst_teq=std::max(worst_teq,x.heat_eq);
  std::cout<<std::scientific<<std::setprecision(10)
      <<"P10L_FUNCTIONAL name="<<names[j]
      <<" mechanical="<<x.mechanical
      <<" thermal_adjoint="<<x.thermal_adjoint
      <<" thermal_reference="<<x.thermal_fd
      <<" full_fd="<<x.full_fd
      <<" rel_full="<<x.rel_full<<" rel_thermal="<<x.rel_thermal<<'\n';
 }
 csv.close();p10k::require(bool(csv),"P10L CSV write failure");
 const bool accepted=worst<5e-3&&worst_thermal<1e-2&&
                    worst_meq<1e-5&&worst_teq<1e-7;
 std::cout<<(accepted?"P10L_FULL_THERMAL_ADJOINT_OK":
                      "P10L_FULL_THERMAL_ADJOINT_FAIL")
   <<" nodes="<<base.mesh.nodes.size()<<" tet10="<<base.mesh.tets.size()
   <<" steps="<<c.steps<<" dt="<<c.dt<<" mode="<<c.mode
   <<" max_full_FD_rel="<<worst
   <<" max_thermal_chain_rel="<<worst_thermal
   <<" max_mechanical_equilibrium_rel="<<worst_meq
   <<" max_thermal_equilibrium_rel="<<worst_teq
   <<" base_thermal_parity_K="<<parity
   <<" analytic_geometry_matrix_rel="<<matparity
   <<" checkpoint_replay_bitwise=1"
   <<" thermal_shape_derivative=ANALYTIC"
   <<" thermal_adjoint=DISCRETE_BACKWARD_EULER\n";
 return accepted?0:3;
}
} // namespace p10l

#ifndef STAGE3D10L_NO_MAIN
int main(int argc,char** argv){
 try{
  const auto c=p10k::parse(argc,argv);
#ifdef _OPENMP
  omp_set_dynamic(0);omp_set_num_threads(c.threads);
#endif
  if(c.selftest)return p10i::run_tests();
  return p10l::run(c);
 }catch(const std::exception& e){
  std::cerr<<"P10L_ERROR: "<<e.what()<<'\n';return 2;
 }
}
#endif
