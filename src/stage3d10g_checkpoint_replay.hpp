// Stage 3D-10G: bounded-in-time replay of the verified P10F discrete adjoint.
// Inclusion contract: inside the P10D test anonymous namespace, AFTER the
// definitions of Problem, Frame, equilibrium, physical_value and physical_reverse.
// This is a two-Tet10 proof-of-algorithm, NOT the HP4/HP8 adjoint solver.
// Checkpoint payload has the exact P09D5/P09E2 restart.bin binary layout.
// An independent FNV64 .checksum sidecar detects silent payload bit corruption.
// The production overwrite-in-place policy is intentionally NOT modified.
#pragma once
#include <chrono>
#include <cstring>
#include <limits>
#include <memory>

namespace ice3d_p10g_test {
namespace fs10g=std::filesystem;

struct Snapshot {
 int step=0;
 std::vector<double> u;
 std::vector<State> state;
};

constexpr int Interval=4;
static_assert(Ntime%Interval==0);
static_assert(std::is_trivially_copyable_v<State>);

std::uint64_t mesh_signature(const Mesh& mesh){
 std::uint64_t h=14695981039346656037ull;
 const auto mix=[&](std::uint64_t x) {h^=x;h*=1099511628211ull;};
 for(const auto& p:mesh.nodes){
  mix(std::bit_cast<std::uint64_t>(p.x));
  mix(std::bit_cast<std::uint64_t>(p.y));
  mix(std::bit_cast<std::uint64_t>(p.z));
 }
 for(const auto& tet:mesh.tets)for(int node:tet)mix(std::uint32_t(node));
 return h;
}

std::uint64_t file_checksum(const fs10g::path& file){
 std::ifstream in(file,std::ios::binary);
 ensure(bool(in),"P10G checksum: missing input");
 std::array<char,8192> buf{};
 std::uint64_t h=14695981039346656037ull;
 while(in){
  in.read(buf.data(),std::streamsize(buf.size()));
  const auto size=in.gcount();
  for(std::streamsize i=0;i<size;++i){
   h^=static_cast<unsigned char>(buf[size_t(i)]);
   h*=1099511628211ull;
  }
 }
 ensure(in.eof(),"P10G checksum: read error");
 return h;
}

fs10g::path sidecar(const fs10g::path& path){
 auto result=path;
 result+=".checksum";
 return result;
}

std::uint32_t law_code(const Problem& p){
 return p.flags.viscous?2u:(p.flags.delayed?1u:0u);
}

void write_snapshot(const fs10g::path& path,const Problem& p,
                    const Snapshot& snap){
 ensure(snap.u.size()==p.geom.bc.size(),"P10G write: u size mismatch");
 ensure(snap.state.size()==p.geom.mesh.tets.size()*p.quadrature.size(),
        "P10G write: state size mismatch");
 auto part=path;part+=".part";
 std::ofstream out(part,std::ios::binary|std::ios::trunc);
 ensure(bool(out),"P10G unable to create named snapshot");
 const std::uint64_t magic=0x4943453344303602ull;
 const std::uint64_t nodes=p.geom.mesh.nodes.size();
 const std::uint64_t qps=snap.state.size();
 const std::uint64_t sig=mesh_signature(p.geom.mesh);
 const std::int32_t order=3,step=snap.step;
 const std::uint32_t mod=(p.modulus==Modulus::VAR?1u:0u),law=law_code(p);
 const double time=double(step)*Dt;
 auto write_field=[&](const auto& x){
  out.write(reinterpret_cast<const char*>(&x),sizeof(x));
 };
 write_field(magic);write_field(nodes);write_field(qps);write_field(sig);
 write_field(order);write_field(step);write_field(mod);write_field(law);
 write_field(time);
 ice3d::checkpoint_io::write_bytes(out,snap.u.data(),
             std::uint64_t(snap.u.size())*sizeof(double));
 ice3d::checkpoint_io::write_bytes(out,snap.state.data(),
             std::uint64_t(snap.state.size())*sizeof(State));
 out.close();
 ensure(bool(out),"P10G snapshot write incomplete");
 const std::uint64_t checksum=file_checksum(part);
 auto checkpart=sidecar(path);checkpart+=".part";
 {
  std::ofstream c(checkpart,std::ios::binary|std::ios::trunc);
  c.write(reinterpret_cast<const char*>(&checksum),sizeof(checksum));
  c.close();
  ensure(bool(c),"P10G sidecar write incomplete");
 }
 fs10g::rename(part,path);
 fs10g::rename(checkpart,sidecar(path));
}

Snapshot read_snapshot(const fs10g::path& path,const Problem& p,int expected){
 std::ifstream check(sidecar(path),std::ios::binary);
 std::uint64_t expected_checksum=0;
 check.read(reinterpret_cast<char*>(&expected_checksum),sizeof(expected_checksum));
 char sentinel{};
 ensure(bool(check)&&!check.read(&sentinel,1),
        "P10G missing/invalid checksum sidecar");
 ensure(file_checksum(path)==expected_checksum,"P10G checksum mismatch");
 std::ifstream in(path,std::ios::binary);
 ensure(bool(in),"P10G missing named snapshot");
 std::uint64_t magic=0,nodes=0,qps=0,sig=0;
 std::int32_t ord=-1,step=-1;
 std::uint32_t mod=99,law=99;
 double time=std::numeric_limits<double>::quiet_NaN();
 auto read_field=[&](auto& x){
  in.read(reinterpret_cast<char*>(&x),sizeof(x));
 };
 read_field(magic);read_field(nodes);read_field(qps);read_field(sig);
 read_field(ord);read_field(step);read_field(mod);read_field(law);
 read_field(time);
 ensure(bool(in)&&magic==0x4943453344303602ull &&
        nodes==p.geom.mesh.nodes.size() &&
        qps==p.geom.mesh.tets.size()*p.quadrature.size() &&
        sig==mesh_signature(p.geom.mesh) &&ord==3 &&step==expected &&
        mod==(p.modulus==Modulus::VAR?1u:0u) &&law==law_code(p) &&
        time==double(step)*Dt,"P10G snapshot header/model/mesh/time mismatch");
 Snapshot snap;
 snap.step=step;
 snap.u.resize(p.geom.bc.size());snap.state.resize(size_t(qps));
 ice3d::checkpoint_io::read_bytes(in,snap.u.data(),
              std::uint64_t(snap.u.size())*sizeof(double));
 ice3d::checkpoint_io::read_bytes(in,snap.state.data(),
              std::uint64_t(snap.state.size())*sizeof(State));
 ensure(!in.read(&sentinel,1),"P10G trailing bytes in snapshot");
 return snap;
}

void identical(const Snapshot& a,const Snapshot& b){
 ensure(a.step==b.step && a.u.size()==b.u.size() &&
        a.state.size()==b.state.size(),"P10G replay dimensions mismatch");
 ensure(std::memcmp(a.u.data(),b.u.data(),a.u.size()*sizeof(double))==0,
        "P10G replay displacement differs bitwise");
 ensure(std::memcmp(a.state.data(),b.state.data(),a.state.size()*sizeof(State))==0,
        "P10G replay history differs bitwise");
}

const std::array<f10::Kind,4> kinds{
 f10::Kind::J6,f10::Kind::PeakMoment,
 f10::Kind::Energy,f10::Kind::SafetySmooth
};

struct ForwardCheckpoints{
 std::array<double,4> objectives{};
 std::array<fs10g::path,Ntime/Interval+1> paths;
};

ForwardCheckpoints forward_checkpointed(const Problem& p,
                                        const fs10g::path& directory){
 ForwardCheckpoints data;
 auto name=[&](int n){return directory/("step_"+std::to_string(n)+".bin");};
 Snapshot snap;
 snap.u.assign(p.geom.bc.size(),0.);
 snap.state.resize(p.geom.mesh.tets.size()*p.quadrature.size());
 write_snapshot(name(0),p,snap);
 data.paths[0]=name(0);
 std::array<double,4> moments{};
 for(size_t kind=0;kind<kinds.size();++kind)
  moments[kind]=.5/double(Ntime)*f10::initial_time_value(kinds[kind],{});
 for(int n=1;n<=Ntime;++n){
  const Frame frame=equilibrium(p,n,snap.state,snap.u);
  const Step step(p.geom.mesh,p.quadrature,frame.T,frame.previous,
                  Dt,frame.u,p.geom.bc,p.modulus,p.flags);
  const double coefficient=(n==Ntime?.5:1.)/double(Ntime);
  for(size_t kind=0;kind<kinds.size();++kind)
   moments[kind]+=coefficient*f10::evaluate(step,kinds[kind]).value;
  snap.step=n;snap.u=frame.u;snap.state=frame.next;
  if(n%Interval==0){
   write_snapshot(name(n),p,snap);
   data.paths[size_t(n/Interval)]=name(n);
  }
 }
 for(size_t kind=0;kind<kinds.size();++kind){
  data.objectives[kind]=kinds[kind]==f10::Kind::PeakMoment
     ?std::pow(moments[kind],1./f10::Parameters{}.peak_p):moments[kind];
 }
 return data;
}

struct ReplayResult {
 Gradients gradient;
 int replay_steps=0,max_frames=0;
};

ReplayResult replay_reverse(const Problem& problem,
                            const ForwardCheckpoints& checkpoints,
                            f10::Kind kind,double J){
 const size_t nq=problem.geom.mesh.tets.size()*problem.quadrature.size();
 std::vector<State> future(nq);
 ReplayResult result;
 auto& gradient=result.gradient;
 constexpr double geom_fd_step=2e-4;
 const Geometry plus(geom_fd_step),minus(-geom_fd_step);
 const double moment=(kind==f10::Kind::PeakMoment)
     ?std::pow(J,f10::Parameters{}.peak_p):1.;
 const double chain=(kind==f10::Kind::PeakMoment)
     ?std::pow(moment,1./f10::Parameters{}.peak_p-1)/f10::Parameters{}.peak_p:1.;
 for(int segment=Ntime/Interval-1;segment>=0;--segment){
  const int first=segment*Interval,last=first+Interval;
  Snapshot state=read_snapshot(checkpoints.paths[size_t(segment)],problem,first);
  std::vector<Frame> frames;
  frames.reserve(Interval);
  for(int n=first+1;n<=last;++n){
   Frame frame=equilibrium(problem,n,state.state,state.u);
   state.step=n;state.state=frame.next;state.u=frame.u;
   frames.push_back(std::move(frame));
   ++result.replay_steps;
  }
  result.max_frames=std::max(result.max_frames,int(frames.size()));
  identical(state,read_snapshot(checkpoints.paths[size_t(segment+1)],problem,last));
  for(int i=int(frames.size())-1;i>=0;--i){
   const int n=first+i+1;
   const Frame& frame=frames[size_t(i)];
   const Step step(problem.geom.mesh,problem.quadrature,frame.T,frame.previous,
                   Dt,frame.u,problem.geom.bc,problem.modulus,problem.flags);
   const auto src=f10::evaluate(step,kind);
   const double coefficient=chain*(n==Ntime?.5:1.)/double(Ntime);
   Output lambda;
   lambda.residual.assign(frame.u.size(),0.);
   lambda.next=future;
   const auto memory=step.vjp(lambda);
   std::vector<double> rhs(frame.u.size());
   for(size_t k=0;k<rhs.size();++k)
    rhs[k]=-(coefficient*src.displacement[k]+memory.displacement[k]);
   auto K=ice3d::p10e::assemble_tangent_bcsr(
                problem.geom.mesh,step,problem.topology);
   const auto solve=ice3d::p10e::solve_bicgstab(K,problem.geom.bc,rhs,true,
                            2e-13,400,problem.reverse_graph.get());
   record_sparse(solve);
   lambda.residual=solve.x;
   const auto back=step.vjp(lambda);
   double err_sq=0,source_sq=0;
   for(size_t k=0;k<rhs.size();++k){
    const double source=coefficient*src.displacement[k];
    err_sq+=std::pow(back.displacement[k]+source,2);
    source_sq+=source*source;
   }
   gradient.max_adjoint_equilibrium_residual=std::max(
    gradient.max_adjoint_equilibrium_residual,
    std::sqrt(err_sq)/std::max(1.,std::sqrt(source_sq)));
   const auto dTdp=problem.temperature_direction(n);
   for(size_t k=0;k<dTdp.size();++k)
    gradient.temperature+=(back.temperature[k]+coefficient*src.temperature[k])*dTdp[k];
   const Step sp(plus.mesh,problem.quadrature,frame.T,frame.previous,
                 Dt,frame.u,problem.geom.bc,problem.modulus,problem.flags);
   const Step sm(minus.mesh,problem.quadrature,frame.T,frame.previous,
                 Dt,frame.u,problem.geom.bc,problem.modulus,problem.flags);
   const auto op=sp.evaluate(),om=sm.evaluate();
   const double valuep=f10::evaluate(sp,kind).value;
   const double valuem=f10::evaluate(sm,kind).value;
   gradient.shape+=coefficient*(valuep-valuem)/(2*geom_fd_step);
   for(size_t k=0;k<lambda.residual.size();++k)
    gradient.shape+=lambda.residual[k]*(op.residual[k]-om.residual[k])/(2*geom_fd_step);
   for(size_t k=0;k<nq;++k)for(int c=0;c<6;++c){
    gradient.shape+=future[k].e_d[c]*(op.next[k].e_d[c]-om.next[k].e_d[c])/(2*geom_fd_step);
    gradient.shape+=future[k].e_v[c]*(op.next[k].e_v[c]-om.next[k].e_v[c])/(2*geom_fd_step);
   }
   for(size_t k=0;k<nq;++k)for(int c=0;c<6;++c){
    future[k].e_d[c]=back.previous[k].e_d[c]+coefficient*src.previous[k].e_d[c];
    future[k].e_v[c]=back.previous[k].e_v[c]+coefficient*src.previous[k].e_v[c];
   }
  }
 }
 return result;
}

bool rejects_corruption(const Problem& p,const ForwardCheckpoints& checkpoints,
                         const fs10g::path& directory){
 const auto copy=directory/"corrupted_copy.bin";
 fs10g::copy_file(checkpoints.paths[1],copy,fs10g::copy_options::none);
 fs10g::copy_file(sidecar(checkpoints.paths[1]),sidecar(copy),
                  fs10g::copy_options::none);
 {
  std::fstream f(copy,std::ios::binary|std::ios::in|std::ios::out);
  f.seekg(80);
  char original=0;
  f.read(&original,1);
  f.seekp(80);
  original^=0x20;
  f.write(&original,1);
  ensure(bool(f),"P10G corrupt test injection failed");
 }
 try{(void)read_snapshot(copy,p,Interval);}
 catch(const std::exception&){return true;}
 return false;
}

int run_checkpoint_tests(){
 const std::array<std::pair<Controls,Modulus>,6> cases{{
  {Controls{false,false},Modulus::CONST},
  {Controls{false,false},Modulus::VAR},
  {Controls{true,false},Modulus::CONST},
  {Controls{true,false},Modulus::VAR},
  {Controls{true,true},Modulus::CONST},
  {Controls{true,true},Modulus::VAR}
 }};
 const auto unique=std::chrono::steady_clock::now().time_since_epoch().count();
 const fs10g::path directory=fs10g::temp_directory_path()/
                       ("ice3d_p10g_test_"+std::to_string(unique));
 ensure(fs10g::create_directory(directory),"P10G test output dir already exists");
 struct AutoCleanup {
  fs10g::path directory;
  ~AutoCleanup(){std::error_code error;fs10g::remove_all(directory,error);}
 } cleanup{directory};
 double worst_J=0,worst_T=0,worst_shape=0,worst_equilibrium=0;
 bool corruption_detected=false,wrong_model_detected=false;
 int replay_steps=0,max_frames=0,comparisons=0,checkpoints_written=0;
 for(size_t i=0;i<cases.size();++i){
  const auto [flags,mod]=cases[i];
  const Problem problem(0,0,flags,mod);
  const auto full=forward(problem);
  const auto case_dir=directory/("model_"+std::to_string(i));
  fs10g::create_directory(case_dir);
  const auto cp=forward_checkpointed(problem,case_dir);
  checkpoints_written+=int(cp.paths.size());
  if(i==0){
   corruption_detected=rejects_corruption(problem,cp,case_dir);
   const Problem wrong(0,0,flags,Modulus::VAR);
   try{(void)read_snapshot(cp.paths[1],wrong,Interval);}
   catch(const std::exception&){wrong_model_detected=true;}
  }
  for(size_t k=0;k<kinds.size();++k){
   const double J=physical_value(problem,full,kinds[k]);
   const double J_error=relative_error(J,cp.objectives[k]);
   worst_J=std::max(worst_J,J_error);
   const auto reference=physical_reverse(problem,full,kinds[k],J);
   const auto trial=replay_reverse(problem,cp,kinds[k],cp.objectives[k]);
   const double T_error=relative_error(reference.temperature,trial.gradient.temperature);
   const double S_error=relative_error(reference.shape,trial.gradient.shape);
   worst_T=std::max(worst_T,T_error);
   worst_shape=std::max(worst_shape,S_error);
   worst_equilibrium=std::max(worst_equilibrium,
                     trial.gradient.max_adjoint_equilibrium_residual);
   max_frames=std::max(max_frames,trial.max_frames);
   replay_steps+=trial.replay_steps;
   ensure(J_error<1e-12,"P10G objective changed under checkpointing");
   ensure(T_error<1e-11,"P10G temperature adjoint changed under replay");
   ensure(S_error<1e-11,"P10G shape adjoint changed under replay");
   ensure(trial.gradient.max_adjoint_equilibrium_residual<1e-8,
          "P10G adjoint equilibrium error");
   ++comparisons;
  }
 }
 ensure(corruption_detected,"P10G checksum failed to reject modified payload");
 ensure(wrong_model_detected,"P10G header failed to reject wrong material model");
 ensure(max_frames==Interval,"P10G max buffered time frames incorrect");
 ensure(replay_steps==int(cases.size()*kinds.size())*Ntime,
        "P10G replay count mismatch");
 std::cout<<std::scientific<<std::setprecision(12)
  <<"P10G_CHECKPOINT_REPLAY_OK models="<<cases.size()
  <<" observables="<<kinds.size()<<" comparisons="<<comparisons
  <<" checkpoint_files="<<checkpoints_written
  <<" max_frames="<<max_frames<<" total_replayed_steps="<<replay_steps
  <<" objective_rel="<<worst_J
  <<" temperature_gradient_rel="<<worst_T
  <<" shape_gradient_rel="<<worst_shape
  <<" worst_adjoint_equilibrium_rel="<<worst_equilibrium
  <<" checksum_bitflip_detected="<<corruption_detected
  <<" mismatched_model_detected="<<wrong_model_detected
  <<'\n';
 return 0;
}
} // namespace ice3d_p10g_test
