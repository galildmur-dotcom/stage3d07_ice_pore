// Stage 3D-10N: multi-delta verification with one nonlinear forward history,
// one set of discrete mechanical adjoints, and delta-dependent frozen-state
// geometric partials.  The validated 10M H3/H4 adjoint solver remains intact.
#include "stage3d10n_base_m_impl.inc"

#include <bit>
#include <cstdint>
#include <cstring>
#include <limits>
#include <optional>
#include <type_traits>

namespace p10n {
namespace H=ice3d::p10l;
namespace A=ice3d::p10c;
namespace E=ice3d::p10e;
namespace F=ice3d::p10f;

constexpr std::uint64_t MAGIC=0x314E303133454349ULL; // ICE310N1
constexpr std::uint64_t VERSION=1;
constexpr std::uint64_t CHUNK=16ULL*1024*1024;

struct DeltaPair {
 double delta_um=0;
 p10k::Scenario plus,minus;
 H::Operator thermal;
};
struct Partial {
 double mechanical=0,thermal=0,mechanical_eq=0,thermal_eq=0;
 int thermal_cg=0;
};
using GradientSet=std::array<Partial,3>;

void check_finite(double v,const std::string& name){
 p10k::require(std::isfinite(v),"P10N nonfinite "+name);
}

std::uint64_t fnv(const void* ptr,std::uint64_t count){
 std::uint64_t h=ice3d::p09e::FNV_START;
 const auto* p=static_cast<const unsigned char*>(ptr);
 for(std::uint64_t i=0;i<count;++i)h=(h^p[i])*ice3d::p09e::FNV_PRIME;
 return h;
}

template<class T> void write_scalar(std::ofstream& out,const T& v){
 static_assert(std::is_trivially_copyable_v<T>);
 out.write(reinterpret_cast<const char*>(&v),sizeof v);
 p10k::require(bool(out),"P10N cache scalar write failed");
}
template<class T> void read_scalar(std::ifstream& in,T& v){
 static_assert(std::is_trivially_copyable_v<T>);
 in.read(reinterpret_cast<char*>(&v),sizeof v);
 p10k::require(bool(in),"P10N truncated cache scalar");
}

template<class T> void write_vector(std::ofstream& out,const std::vector<T>& v){
 static_assert(std::is_trivially_copyable_v<T>);
 const auto bytes=std::uint64_t(v.size())*sizeof(T);
 write_scalar(out,fnv(v.data(),bytes));
 const char* data=reinterpret_cast<const char*>(v.data());
 for(std::uint64_t i=0;i<bytes;){
  const auto n=static_cast<std::streamsize>(std::min(CHUNK,bytes-i));
  out.write(data+i,n);
  p10k::require(bool(out),"P10N cache vector write failed");
  i+=std::uint64_t(n);
 }
}
template<class T> void read_vector(std::ifstream& in,std::vector<T>& v,
                                  std::size_t count){
 static_assert(std::is_trivially_copyable_v<T>);
 std::uint64_t expected=0;read_scalar(in,expected);
 v.resize(count);
 const auto bytes=std::uint64_t(count)*sizeof(T);
 char* data=reinterpret_cast<char*>(v.data());
 for(std::uint64_t i=0;i<bytes;){
  const auto n=static_cast<std::streamsize>(std::min(CHUNK,bytes-i));
  in.read(data+i,n);
  p10k::require(bool(in),"P10N truncated cache vector");
  i+=std::uint64_t(n);
 }
 p10k::require(fnv(v.data(),bytes)==expected,
               "P10N forward cache checksum mismatch");
}

void save_forward(const fs::path& path,const p10k::Forward& f,
                  const Mesh& mesh,const p10k::Config& c){
 static_assert(std::is_trivially_copyable_v<State>);
 static_assert(std::endian::native==std::endian::little);
 p10k::require(!fs::exists(path),"P10N cache target exists (will not overwrite): "+path.string());
 p10k::require(f.frames.size()==std::size_t(c.steps),"P10N bad forward frame count");
 const auto nq=mesh.tets.size()*volume_q(3).size();
 fs::create_directories(path.parent_path());
 const fs::path tmp=path.string()+".part";
 p10k::require(!fs::exists(tmp),"P10N unfinished cache .part exists: "+tmp.string());
 std::ofstream out(tmp,std::ios::binary);
 p10k::require(bool(out),"P10N cannot create forward cache");
 for(auto x:{MAGIC,VERSION,std::uint64_t(sizeof(State)),
             ice3d::p09e::mesh_signature(mesh),std::uint64_t(mesh.nodes.size()),
             std::uint64_t(mesh.tets.size()),std::uint64_t(nq),
             std::uint64_t(c.steps),std::uint64_t(c.dt),
             std::bit_cast<std::uint64_t>(c.cutoff_mm)})write_scalar(out,x);
 for(double x:f.objective)write_scalar(out,x);
 for(const auto& frame:f.frames){
  p10k::require(frame.temperature.size()==mesh.nodes.size()&&
                frame.repinned_u.size()==3*mesh.nodes.size()&&
                frame.previous.size()==nq,"P10N inconsistent forward frame");
  write_vector(out,frame.temperature);
  write_vector(out,frame.repinned_u);
  write_vector(out,frame.previous);
 }
 p10k::require(f.final_state.u.size()==3*mesh.nodes.size()&&
               f.final_state.qstate.size()==nq,"P10N inconsistent final state");
 write_vector(out,f.final_state.u);
 write_vector(out,f.final_state.qstate);
 write_scalar(out,f.final_state.lastTime);
 out.close();p10k::require(bool(out),"P10N cache close failed");
 fs::rename(tmp,path);
 std::cout<<"P10N_FORWARD_CACHE_SAVED path="<<path.string()
          <<" bytes="<<fs::file_size(path)<<'\n'<<std::flush;
}

p10k::Forward load_forward(const fs::path& path,const Mesh& mesh,
                           const p10k::Config& c){
 static_assert(std::is_trivially_copyable_v<State>);
 std::ifstream in(path,std::ios::binary);
 p10k::require(bool(in),"P10N forward cache missing: "+path.string());
 const auto nq=mesh.tets.size()*volume_q(3).size();
 const std::array<std::uint64_t,10> expected{
  MAGIC,VERSION,std::uint64_t(sizeof(State)),
  ice3d::p09e::mesh_signature(mesh),std::uint64_t(mesh.nodes.size()),
  std::uint64_t(mesh.tets.size()),std::uint64_t(nq),
  std::uint64_t(c.steps),std::uint64_t(c.dt),
  std::bit_cast<std::uint64_t>(c.cutoff_mm)};
 for(std::size_t i=0;i<expected.size();++i){
  std::uint64_t got=0;read_scalar(in,got);
  p10k::require(got==expected[i],
    "P10N cache incompatible: mesh/quad/time/cutoff/layout field "+
    std::to_string(i));
 }
 p10k::Forward f;
 for(double& x:f.objective){read_scalar(in,x);check_finite(x,"objective");}
 f.frames.resize(std::size_t(c.steps));
 for(auto& frame:f.frames){
  read_vector(in,frame.temperature,mesh.nodes.size());
  read_vector(in,frame.repinned_u,3*mesh.nodes.size());
  read_vector(in,frame.previous,nq);
 }
 read_vector(in,f.final_state.u,3*mesh.nodes.size());
 read_vector(in,f.final_state.qstate,nq);
 read_scalar(in,f.final_state.lastTime);
 p10k::require(f.final_state.lastTime==double(c.steps*c.dt),
               "P10N cache final time mismatch");
 char extra=0;
 p10k::require(!in.get(extra),"P10N cache trailing bytes");
 p10k::require(in.eof(),"P10N cache read failure");
 std::cout<<"P10N_FORWARD_CACHE_LOADED path="<<path.string()
          <<" frames="<<f.frames.size()<<'\n'<<std::flush;
 return f;
}

std::vector<double> parse_deltas(const std::string& csv){
 std::vector<double> result;
 std::istringstream input(csv);
 std::string token;
 while(std::getline(input,token,',')){
  p10k::require(!token.empty(),"P10N empty delta");
  std::size_t end=0;const double d=std::stod(token,&end);
  p10k::require(end==token.size()&&std::isfinite(d)&&d>0&&d<=10,
                "P10N invalid delta: "+token);
  p10k::require(std::find(result.begin(),result.end(),d)==result.end(),
                "P10N duplicate delta");
  result.push_back(d);
 }
 p10k::require(!result.empty()&&result.size()<=8,"P10N delta count outside 1..8");
 return result;
}

std::vector<DeltaPair> build_pairs(const p10k::Config& c,
                                   const p10k::Scenario& base,
                                   const std::vector<double>& deltas){
 std::vector<DeltaPair> pairs;
 pairs.reserve(deltas.size());
 const auto mask=p10k::observation_elements(base.mesh);
 const auto pinned=p10k::adjoint_bc(base.mesh);
 const std::string mode=c.mode=="R"?"radius":c.mode;
 for(double delta_um:deltas){
  const fs::path geom=c.out/"geometry"/("d"+p10k::tag(delta_um));
  p10k::run_external(c.geometry_exe,{"--mesh",c.mesh.string(),
    "--out",geom.string(),"--mode",mode,
    "--delta-um",std::to_string(delta_um),
    "--cutoff-mm",std::to_string(c.cutoff_mm),"--quad","3"});
  const auto stem=c.mesh.stem().string()+"_P08_"+mode+"_";
  const auto suffix="_"+p10k::tag(delta_um)+"um.msh";
  DeltaPair p;
  p.delta_um=delta_um;
  p.plus.mesh=read_msh(geom/(stem+"plus"+suffix)).mesh;
  p.minus.mesh=read_msh(geom/(stem+"minus"+suffix)).mesh;
  const auto& plus=p.plus.mesh;
  const auto& minus=p.minus.mesh;
  p10k::require(plus.tets==base.mesh.tets&&minus.tets==base.mesh.tets&&
                plus.nodes.size()==base.mesh.nodes.size()&&
                minus.nodes.size()==base.mesh.nodes.size(),
                "P10N changed mesh connectivity");
  p10k::require(p10k::observation_elements(plus)==mask&&
                p10k::observation_elements(minus)==mask,
                "P10N changed B6 elements");
  p10k::require(p10k::adjoint_bc(plus)==pinned&&
                p10k::adjoint_bc(minus)==pinned,
                "P10N changed mechanical gauge");
  auto v=p10l::geometry_velocity(plus,minus,delta_um*1e-6);
  p.thermal=H::assemble(base.mesh,v,double(c.dt));
  p10k::require(p.thermal.max_ones_error<1e-7&&
                p.thermal.max_directional_ones_error<1e-7,
                "P10N thermal constant-temperature check failed");
  pairs.push_back(std::move(p));
 }
 return pairs;
}

std::vector<GradientSet> reverse_scan(const p10k::Scenario& base,
                                       const p10k::Config& c,
                                       const p10k::Forward& nominal,
                                       const std::vector<DeltaPair>& pairs){
 const auto quad=volume_q(3);
 const auto mask=p10k::observation_elements(base.mesh);
 const auto pinned=p10k::adjoint_bc(base.mesh);
 const auto topology=build_bcsr_topology(base.mesh);
 BCSR sparse;sparse.set_topology(topology);
 const E::ReverseGraph graph(sparse);
 const size_t nq=base.mesh.tets.size()*quad.size();
 const std::array<F::Kind,3> kinds{
  F::Kind::J6,F::Kind::PeakMoment,F::Kind::Energy};
 std::array<std::vector<State>,3> futures;
 std::array<std::vector<std::vector<double>>,3> heat_sources;
 std::array<double,3> chains{};
 for(size_t obs=0;obs<3;++obs){
  futures[obs].resize(nq);
  heat_sources[obs].assign(std::size_t(c.steps+1),
                           std::vector<double>(base.mesh.nodes.size(),0.));
  chains[obs]=obs==1?std::pow(nominal.objective[obs],1.-8.)/8.:1.;
 }
 std::vector<GradientSet> result(pairs.size());
 for(int n=c.steps;n>=1;--n){
  const auto begin=std::chrono::steady_clock::now();
  const auto& frame=nominal.frames.at(std::size_t(n-1));
  const A::Step state(base.mesh,quad,frame.temperature,frame.previous,
     double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
     ice3d::p10b::Controls{true,true});
  auto tangent=E::assemble_tangent_bcsr(base.mesh,state,topology);
  std::array<A::Output,3> adjoints;
  std::array<F::Sources,3> sources;
  std::array<A::Pullback,3> pullbacks;
  std::array<double,3> weights{};
  for(size_t obs=0;obs<3;++obs){
   const auto kind=kinds[obs];
   sources[obs]=p10k::evaluate_b6(state,kind,mask,quad.size());
   weights[obs]=chains[obs]*(n==c.steps?.5:1.)/c.steps;
   auto& lambda=adjoints[obs];
   lambda.residual.assign(frame.repinned_u.size(),0.);
   lambda.next=futures[obs];
   const auto feedback=state.vjp(lambda);
   std::vector<double> rhs(frame.repinned_u.size());
   for(size_t i=0;i<rhs.size();++i)
    rhs[i]=-(weights[obs]*sources[obs].displacement[i]+
              feedback.displacement[i]);
   const std::array<std::pair<double,int>,3> attempts{{
     {1e-11,2400},{2e-10,3600},{1e-9,5000}}};
   E::IterativeResult solution;
   bool solved=false;
   for(size_t retry=0;retry<attempts.size();++retry){
    const auto [tol,maxiter]=attempts[retry];
    try{
     solution=E::solve_bicgstab(tangent,pinned,rhs,true,tol,maxiter,&graph);
     solved=true;
     std::cout<<"P10N_LINEAR_SOLVED step="<<n<<" functional="<<obs
              <<" retry="<<retry<<" iterations="<<solution.iterations
              <<" verified_relative_residual="<<solution.relative_residual
              <<'\n'<<std::flush;
     break;
    }catch(const std::runtime_error& e){
     if(std::string(e.what()).find("P10E: BiCGStab")!=0)throw;
     std::cout<<"P10N_LINEAR_RETRY step="<<n<<" functional="<<obs
              <<" retry="<<retry<<" reason="<<e.what()<<'\n'<<std::flush;
    }
   }
   p10k::require(solved,"P10N adjoint BiCGStab exhausted verified retries");
   lambda.residual=std::move(solution.x);
   pullbacks[obs]=state.vjp(lambda);
   double eq=0,ref=0;
   for(size_t i=0;i<rhs.size();++i)if(!pinned[i]){
    const double r=pullbacks[obs].displacement[i]+
                   weights[obs]*sources[obs].displacement[i];
    eq+=r*r;
    ref+=std::pow(weights[obs]*sources[obs].displacement[i],2);
   }
   const double equilibrium=std::sqrt(eq)/std::max(1.,std::sqrt(ref));
   p10k::require(equilibrium<1e-6,
                 "P10N adjoint VJP equilibrium insufficient");
   for(auto& g:result)g[obs].mechanical_eq=
                        std::max(g[obs].mechanical_eq,equilibrium);
   for(size_t i=0;i<base.mesh.nodes.size();++i)
    heat_sources[obs][std::size_t(n)][i]=
       pullbacks[obs].temperature[i]+weights[obs]*sources[obs].temperature[i];
  }

  // The same adjoints and future history multipliers are reused for EVERY
  // delta.  No extra nonlinear solve, tangent assembly, or adjoint solve.
  for(size_t k=0;k<pairs.size();++k){
   const auto& pair=pairs[k];
   const A::Step sp(pair.plus.mesh,quad,frame.temperature,frame.previous,
      double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
      ice3d::p10b::Controls{true,true});
   const A::Step sm(pair.minus.mesh,quad,frame.temperature,frame.previous,
      double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
      ice3d::p10b::Controls{true,true});
   const auto op=sp.evaluate(),om=sm.evaluate();
   const double factor=1./(2*pair.delta_um*1e-6);
   for(size_t obs=0;obs<3;++obs){
    auto& out=result[k][obs];
    const double jp=p10k::evaluate_b6(sp,kinds[obs],mask,quad.size()).value;
    const double jm=p10k::evaluate_b6(sm,kinds[obs],mask,quad.size()).value;
    out.mechanical+=weights[obs]*(jp-jm)*factor;
    for(size_t i=0;i<adjoints[obs].residual.size();++i)
     out.mechanical+=adjoints[obs].residual[i]*
                       (op.residual[i]-om.residual[i])*factor;
    for(size_t i=0;i<nq;++i)for(int a=0;a<6;++a){
     out.mechanical+=futures[obs][i].e_d[a]*
           (op.next[i].e_d[a]-om.next[i].e_d[a])*factor;
     out.mechanical+=futures[obs][i].e_v[a]*
           (op.next[i].e_v[a]-om.next[i].e_v[a])*factor;
    }
   }
  }
  for(size_t obs=0;obs<3;++obs){
   for(size_t i=0;i<nq;++i)for(int a=0;a<6;++a){
    futures[obs][i].e_d[a]=pullbacks[obs].previous[i].e_d[a]+
                              weights[obs]*sources[obs].previous[i].e_d[a];
    futures[obs][i].e_v[a]=pullbacks[obs].previous[i].e_v[a]+
                              weights[obs]*sources[obs].previous[i].e_v[a];
   }
  }
  std::cout<<"P10N_ADJOINT_BACKWARD step="<<n<<'/'<<c.steps
    <<" deltas="<<pairs.size()<<" wall_s="<<std::chrono::duration<double>(
        std::chrono::steady_clock::now()-begin).count()<<'\n'<<std::flush;
 }
 // A and M are primal matrices and do NOT depend on the perturbation delta.
 // Solve the thermal adjoint once per observable, then contract each delta's
 // analytical shape operator with the SAME thermal multipliers.
 const auto& heat=pairs.front().thermal.primal;
 for(size_t k=1;k<pairs.size();++k){
  const auto& other=pairs[k].thermal.primal;
  p10k::require(heat.n==other.n&&heat.mat==other.mat&&
                 heat.mass==other.mass&&heat.robinload==other.robinload,
                 "P10N primal thermal operator changed with delta");
 }
 for(size_t obs=0;obs<3;++obs){
  std::vector<double> next(std::size_t(heat.n),0.);
  double worst=0;int iterations=0;
  for(int n=c.steps;n>=1;--n){
   std::vector<double> rhs;
   heat.mul(heat.mass,next,rhs);
   for(int i=0;i<heat.n;++i)
    rhs[std::size_t(i)]-=heat_sources[obs][std::size_t(n)][std::size_t(i)];
   std::vector<double> psi(std::size_t(heat.n),0.);
   const auto cg=H::solve(heat,rhs,psi);
   iterations+=cg.iterations;
   std::vector<double> equilibrium;
   heat.mul(heat.mat,psi,equilibrium);
   for(int i=0;i<heat.n;++i)equilibrium[std::size_t(i)]-=rhs[std::size_t(i)];
   worst=std::max(worst,std::sqrt(H::inner(equilibrium,equilibrium))/
                 std::max(1e-25,std::sqrt(H::inner(rhs,rhs))));
   std::vector<double> difference(std::size_t(heat.n));
   for(int i=0;i<heat.n;++i)
    difference[std::size_t(i)]=base.temperatures[std::size_t(n)][std::size_t(i)]-
                               base.temperatures[std::size_t(n-1)][std::size_t(i)];
   const double ambient=H::ambient(n*double(c.dt),0.);
   for(size_t k=0;k<pairs.size();++k){
    const auto& D=pairs[k].thermal.shape;
    std::vector<double> mass,conduct;
    D.mul(D.mass,difference,mass);
    D.mul(D.conduct,base.temperatures[std::size_t(n)],conduct);
    for(int i=0;i<heat.n;++i)
     result[k][obs].thermal+=psi[std::size_t(i)]*(mass[std::size_t(i)]+
              double(c.dt)*conduct[std::size_t(i)]-
              double(c.dt)*D.robinload[std::size_t(i)]*ambient);
   }
   next=std::move(psi);
  }
  for(auto& row:result){row[obs].thermal_eq=worst;row[obs].thermal_cg=iterations;}
 }
 return result;
}

int run(const p10k::Config& c,const std::vector<double>& deltas,
        const fs::path& reuse,const fs::path& cache){
 const auto start=std::chrono::steady_clock::now();
 p10k::require(fs::is_regular_file(c.mesh),"P10N mesh not found");
 p10k::require(c.steps*c.dt==900,"P10N requires steps*dt=900 s");
 p10k::require(!fs::exists(c.out),"P10N --out must be a NEW folder");
 p10k::require(reuse.empty()||fs::is_regular_file(reuse),
               "P10N --reuse-forward file does not exist");
 if(reuse.empty()&&!cache.empty()){
  p10k::require(!fs::exists(cache),
    "P10N explicit forward cache already exists (will not overwrite)");
  p10k::require(!fs::exists(fs::path(cache.string()+".part")),
    "P10N explicit forward cache has unfinished .part file");
 }
 p10k::Scenario base;
 base.mesh=read_msh(c.mesh).mesh;
 base.tag="base_only";
 int pore_faces=0;
 const double hedge=p10m::pore_median_edge(base.mesh,pore_faces);
 const auto mask=p10k::observation_elements(base.mesh);
 const double vb6=p10m::b6_volume(base.mesh,mask);
 const auto nq=base.mesh.tets.size()*volume_q(3).size();
 const double held=double(c.steps)*nq*sizeof(State)/1073741824.;
 const double buffers=double(c.steps+4)*nq*sizeof(State)/1073741824.;
 p10k::require(buffers<8.,"P10N history >8 GiB: requires windowed adjoint");
 p10k::require(double(ice3d::p10h::estimate_single_bytes(
                   base.mesh,volume_q(3).size()))/1073741824.<2.,
               "P10N final checkpoint >2 GiB");
 fs::create_directories(c.out);
 const auto pairs=build_pairs(c,base,deltas);
 base.temperatures=H::solve_forward(pairs.at(0).thermal,c.steps,double(c.dt));
 std::cout<<std::scientific<<std::setprecision(11)
    <<"P10N_PREFLIGHT mesh="<<c.mesh.stem().string()
    <<" nodes="<<base.mesh.nodes.size()<<" tet10="<<base.mesh.tets.size()
    <<" pore_tri6="<<pore_faces<<" pore_median_edge_mm="<<hedge*1e3
    <<" B6_volume_m3="<<vb6<<" steps="<<c.steps<<" dt="<<c.dt
    <<" deltas="<<deltas.size()<<" history_gib="<<held
    <<" state_buffers_gib="<<buffers<<'\n'<<std::flush;
 if(c.preflight){
  for(size_t k=0;k<pairs.size();++k){
   const double parity=p10l::geometry_tangent_parity(
     pairs[k].thermal,pairs[k].plus.mesh,pairs[k].minus.mesh,
     double(c.dt),pairs[k].delta_um*1e-6);
   p10k::require(parity<5e-3,"P10N thermal geometry parity failed");
   std::cout<<"P10N_PREFLIGHT_DELTA delta_um="<<pairs[k].delta_um
            <<" thermal_matrix_parity="<<parity<<'\n';
  }
  std::cout<<"P10N_PREFLIGHT_OK nonlinear_forward_solves=0\n";
  return 0;
 }
 p10k::Forward nominal;
 if(reuse.empty()){
  nominal=p10k::forward(base,c,true);
  const auto path=cache.empty()?c.out/"forward_history.bin":cache;
  save_forward(path,nominal,base.mesh,c);
 }else nominal=load_forward(reuse,base.mesh,c);
 // The cached per-step temperatures must be identical to the regenerated
 // primal thermal history; otherwise this is not the same coupled state.
 for(int n=1;n<=c.steps;++n){
  const auto& a=base.temperatures[std::size_t(n)];
  const auto& b=nominal.frames[std::size_t(n-1)].temperature;
  p10k::require(a.size()==b.size()&&
    std::memcmp(a.data(),b.data(),a.size()*sizeof(double))==0,
    "P10N cached thermal field differs from regenerated base history");
 }
 const auto checkpoint=c.out/"retained";
 fs::create_directories(checkpoint/"adjoint_history");
 ice3d::p10h::retain(checkpoint,base.mesh,p10k::setting(),
                    nominal.final_state,c.steps);
 const auto restored=ice3d::p10h::recover(checkpoint,base.mesh,
                  p10k::setting(),c.steps,double(c.steps*c.dt),
                  volume_q(3).size());
 p10i::configure_production();
 identical_field(restored,nominal.final_state);
 auto grads=reverse_scan(base,c,nominal,pairs);
 const double wall=std::chrono::duration<double>(
      std::chrono::steady_clock::now()-start).count();
 std::ofstream csv(c.out/"P10N_DELTA_SCAN.csv");
 p10k::require(bool(csv),"P10N CSV creation failed");
 csv<<"mesh,nodes,tet10,pore_tri6,pore_median_edge_mm,B6_volume_m3,"
       "dt_s,steps,horizon_s,delta_um,mode,law,modulus,functional,objective,"
       "mechanical_partial_per_m,thermal_adjoint_per_m,total_adjoint_per_m,"
       "mechanical_equilibrium_rel,thermal_equilibrium_rel,thermal_CG_iterations,"
       "history_gib,wall_s,forward_solve_count,adjoint_solve_count\n";
 csv<<std::setprecision(17);
 const std::array<std::string,3> names{"j6","jpeak","jen"};
 double worst_mech=0,worst_heat=0;
 for(size_t k=0;k<pairs.size();++k)for(size_t obs=0;obs<3;++obs){
  const auto& g=grads[k][obs];
  csv<<c.mesh.stem().string()<<','<<base.mesh.nodes.size()<<','
      <<base.mesh.tets.size()<<','<<pore_faces<<','<<hedge*1e3<<','<<vb6<<','
      <<c.dt<<','<<c.steps<<','<<c.steps*c.dt<<','<<pairs[k].delta_um<<','
      <<c.mode<<",EDV,VAR,"<<names[obs]<<','<<nominal.objective[obs]<<','
      <<g.mechanical<<','<<g.thermal<<','<<g.mechanical+g.thermal<<','
      <<g.mechanical_eq<<','<<g.thermal_eq<<','<<g.thermal_cg<<','
      <<held<<','<<wall<<','<<(reuse.empty()?1:0)<<','<<c.steps*3<<'\n';
  worst_mech=std::max(worst_mech,g.mechanical_eq);
  worst_heat=std::max(worst_heat,g.thermal_eq);
 }
 csv.close();p10k::require(bool(csv),"P10N CSV write failed");
 const bool good=worst_mech<1e-6&&worst_heat<1e-7;
 std::cout<<(good?"P10N_DELTA_SCAN_OK":"P10N_DELTA_SCAN_FAIL")
     <<" mesh="<<c.mesh.stem().string()<<" deltas="<<deltas.size()
     <<" steps="<<c.steps<<" dt="<<c.dt
     <<" nonlinear_forward_solves="<<(reuse.empty()?1:0)
     <<" reused_forward="<<(!reuse.empty())
     <<" mechanical_adjoint_solves="<<c.steps*3
     <<" max_mechanical_equilibrium_rel="<<worst_mech
     <<" max_thermal_equilibrium_rel="<<worst_heat
     <<" checkpoint_roundtrip_bitwise=1 wall_s="<<wall<<'\n';
 return good?0:3;
}
} // namespace p10n

int main(int argc,char**argv){
 try{
  std::string delta_csv;
  fs::path reuse,cache;
  std::vector<char*> filtered{argv[0]};
  bool explicit_mesh=false,explicit_out=false;
  for(int i=1;i<argc;++i){
   const std::string flag=argv[i];
   if(flag=="--help"){
    std::cout<<"stage3d10n_delta_scan --mesh MSH --out NEW_DIR "
      "--steps N --dt SECONDS --mode y20|R|tz "
      "--delta-scan-um 1.25,2.5,5 [--threads 4] [--preflight] "
      "[--reuse-forward CACHED_BIN] [--forward-cache NEW_BIN] "
      "[--geometry-exe PATH] [--cutoff-mm 5] [--selftest]\n";
    return 0;
   }
   if(flag=="--delta-scan-um"||flag=="--reuse-forward"||
      flag=="--forward-cache"){
    p10k::require(i+1<argc,"P10N missing value after "+flag);
    const auto value=std::string(argv[++i]);
    if(flag=="--delta-scan-um")delta_csv=value;
    else if(flag=="--reuse-forward")reuse=value;
    else cache=value;
   }else{
    if(flag=="--mesh")explicit_mesh=true;
    if(flag=="--out")explicit_out=true;
    filtered.push_back(argv[i]);
   }
  }
  const auto c=p10k::parse(int(filtered.size()),filtered.data());
#ifdef _OPENMP
  omp_set_dynamic(0);omp_set_num_threads(c.threads);
#endif
  if(c.selftest)return p10i::run_tests();
  p10k::require(explicit_mesh&&explicit_out,
      "P10N requires explicit --mesh and --out");
  p10k::require(!delta_csv.empty(),"P10N requires --delta-scan-um LIST");
  return p10n::run(c,p10n::parse_deltas(delta_csv),reuse,cache);
 }catch(const std::exception& e){
  std::cerr<<"P10N_ERROR: "<<e.what()<<'\n';return 2;
 }
}
