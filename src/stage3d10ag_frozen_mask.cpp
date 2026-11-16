// Stage3D10AG: re-integrate peak moment on a fixed, verified P10N forward
// history. Does NOT solve the mechanical, thermal or adjoint systems.
// This diagnostic intentionally uses the production geometry / EDV / PeakMoment
// routines; alternate QP-domain indicators only probe the *functional value*.
// They are NOT shape-gradient estimates because moving indicator boundaries
// require separate distributional / interface terms.
#define STAGE3D10W_ANALYTIC_SHAPE
#define STAGE3D10P_NO_MAIN
#include "stage3d10p_partial_audit.cpp"
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <string>
#ifdef _OPENMP
#include <omp.h>
#endif

namespace lit08 {
using A=std::array<double,4>;
using AL=std::array<long double,4>;
constexpr std::array<const char*,4> names{"element_centroid_B6", "qp_radius_6p00mm", "qp_radius_5p99mm", "qp_radius_6p01mm"};
constexpr double cutoffs[4]{0.006,0.006,0.00599,0.00601};
using ice3d::p10f::Kind;
struct Totals{
 A volume{}, moment{};
 AL volume_ld{},moment_ld{};
 std::array<std::uint64_t,4> included{};
 std::uint64_t qps_processed=0;
};

Totals integrate(const Mesh& m, const std::vector<GaussQ>& quad,
                 const std::vector<uint8_t>& bc, const p10k::Forward& f,
                 double dt, int threads){
 p10k::require(f.frames.size()==6,"LIT08 needs six forward frames");
 const auto oldmask=p10k::observation_elements(m);
#ifdef _OPENMP
 omp_set_dynamic(0);
 omp_set_num_threads(threads);
#else
 p10k::require(threads==1,"LIT08 compiled without OpenMP, use --threads 1");
#endif
 const std::size_t nq=quad.size();
 const std::array<double,3> centre{0.,0.,0.03};
 const auto sqr=[](double a){return a*a;};
 Totals out;
 for(std::size_t n=0;n<f.frames.size();++n){
  const auto& fr=f.frames[n];
  p10k::require(fr.temperature.size()==m.nodes.size() &&
                fr.repinned_u.size()==3*m.nodes.size() &&
                fr.previous.size()==m.tets.size()*nq,
                "LIT08 cached frame dimension mismatch");
  const double time_weight=(n+1==f.frames.size()?.5:1.)/f.frames.size();
#ifdef _OPENMP
  const int nt=threads;
#else
  const int nt=1;
#endif
  std::vector<Totals> partial(std::size_t(nt),Totals{});
  std::atomic<bool> invalid_jacobian{false};
#ifdef _OPENMP
#pragma omp parallel for schedule(static)
#endif
  for(std::int64_t ie=0;ie<static_cast<std::int64_t>(m.tets.size());++ie){
#ifdef _OPENMP
   const int worker=omp_get_thread_num();
#else
   const int worker=0;
#endif
   auto& t=partial[std::size_t(worker)];
   const std::size_t e=std::size_t(ie);
   const auto& ids=m.tets[e];
   for(std::size_t iq=0;iq<nq;++iq){
    const auto& b=quad[iq];
    V qp{},dr{},ds{},dz{};
    for(int a=0;a<10;++a){
     const V x=m.nodes[ids[a]];
     qp=qp+x*b.N[a];
     dr=dr+x*b.d[a][0]; ds=ds+x*b.d[a][1]; dz=dz+x*b.d[a][2];
    }
    const double rq=norm(qp-V{centre[0],centre[1],centre[2]});
    const bool chosen[4]{oldmask[e]!=0,rq<cutoffs[1],rq<cutoffs[2],rq<cutoffs[3]};
    if(!chosen[0]&&!chosen[1]&&!chosen[2]&&!chosen[3])continue;
    const V c0=cross(ds,dz),c1=cross(dz,dr),c2=cross(dr,ds);
    const double det=dot(dr,c0);
    if(!(det>0)){invalid_jacobian.store(true,std::memory_order_relaxed);continue;}
    const double dv=b.w*det;
    if(n==0)for(int k=0;k<4;++k)if(chosen[k]){
      t.volume[k]+=dv;
      t.volume_ld[k]+=static_cast<long double>(dv);
      t.included[k]++;
    }
    ice3d::p10b::Tensor eps{};
    double T=ice3d::edv::T_ref;
    for(int a=0;a<10;++a){
     T+=b.N[a]*fr.temperature[ids[a]];
     const V g=(c0*b.d[a][0]+c1*b.d[a][1]+c2*b.d[a][2])/det;
     const double gg[3]{g.x,g.y,g.z};
     for(int dir=0;dir<3;++dir){
      const int idx=3*ids[a]+dir;
      if(bc[idx])continue;
      const auto B=ice3d::p10c::displacement_strain_basis(gg,dir);
      for(int c=0;c<6;++c)eps[c]+=B[c]*fr.repinned_u[idx];
     }
    }
    ice3d::p10b::Linearization law(eps,T,dt,fr.previous[e*nq+iq],
        ice3d::edv::Modulus::VAR,ice3d::p10b::Controls{true,true});
    const auto eig=ice3d::p10f::jacobi_symmetric_3x3(law.response.sigma);
    double local=0.;
    for(double ev:eig.eigen){
      const double p=ice3d::p10f::positive_and_derivative(ev,ice3d::p09b::sigma_ref_pa).first;
      local+=std::pow(p,8);
    }
    for(int k=0;k<4;++k)if(chosen[k]){
      const double v=time_weight*dv*local;
      t.moment[k]+=v;
      t.moment_ld[k]+=static_cast<long double>(time_weight)*static_cast<long double>(dv)*static_cast<long double>(local);
    }
    t.qps_processed++;
   }
  }
  p10k::require(!invalid_jacobian.load(std::memory_order_relaxed),
               "LIT08 nonpositive Q3 Jacobian");
  for(const auto& t:partial)for(int k=0;k<4;++k){
   if(n==0){out.volume[k]+=t.volume[k];out.volume_ld[k]+=t.volume_ld[k];out.included[k]+=t.included[k];}
   out.moment[k]+=t.moment[k];out.moment_ld[k]+=t.moment_ld[k];
  }
  for(const auto& t:partial)out.qps_processed+=t.qps_processed;
  std::cout<<"LIT08_STEP_OK step="<<n+1<<"/6\n"<<std::flush;
 }
 for(int k=0;k<4;++k){
  p10k::require(out.volume[k]>0,"LIT08 zero observation volume");
  out.moment[k]+=(.5/6.)*ice3d::p10f::initial_time_value(Kind::PeakMoment)*out.volume[k];
  out.moment_ld[k]+=(.5L/6.L)*static_cast<long double>(ice3d::p10f::initial_time_value(Kind::PeakMoment))*out.volume_ld[k];
 }
 return out;
}

int selftest(){
 Tiny m{};
 p10k::Forward f;
 f.frames.resize(6);
 const auto quad=volume_q(3);
 for(int n=0;n<6;++n){
  auto& z=f.frames[std::size_t(n)];
  z.temperature.resize(m.m.nodes.size());
  for(std::size_t i=0;i<z.temperature.size();++i)z.temperature[i]=-8+.7*std::sin(.17*i+n*.3);
  z.repinned_u.assign(m.m.nodes.size()*3,0.);
  for(std::size_t i=0;i<z.repinned_u.size();++i)if(!m.bc[i])
   z.repinned_u[i]=1e-7*std::sin(double(i+n));
  z.previous.resize(m.m.tets.size()*quad.size());
 }
 const auto got=integrate(m.m,quad,m.bc,f,150,1);
 const auto mask=p10k::observation_elements(m.m);
 double base_moment=.5/6.*ice3d::p10f::initial_time_value(Kind::PeakMoment);
 for(int n=0;n<6;++n){
  const auto& fr=f.frames[std::size_t(n)];
  const ice3d::p10c::Step step(m.m,quad,fr.temperature,fr.previous,150,
       fr.repinned_u,m.bc,ice3d::edv::Modulus::VAR,ice3d::p10b::Controls{true,true});
  const auto source=p10k::evaluate_b6(step,Kind::PeakMoment,mask,quad.size());
  base_moment+=(n==5?.5:1.)/6.*source.value;
 }
 const double v=got.moment[0]/got.volume[0];
 const double err=std::abs(v-base_moment)/std::max(1e-30,std::abs(base_moment));
 p10k::require(err<1e-11,"LIT08 synthetic parity failed");
 // Verify the exact production P10N binary-format writer/reader, including
 // every hashed frame and the mesh/time/cutoff header compatibility.
 f.objective[1]=std::pow(base_moment,1./8.);
 f.final_state.u.assign(3*m.m.nodes.size(),0.);
 f.final_state.qstate.resize(m.m.tets.size()*quad.size());
 f.final_state.lastTime=900.;
 const auto stamp=std::chrono::steady_clock::now().time_since_epoch().count();
 const fs::path temp=fs::temp_directory_path()/("lit08_cache_test_"+std::to_string(stamp));
 p10k::require(fs::create_directory(temp),"LIT08 temp dir exists");
 struct Cleanup {fs::path folder;~Cleanup(){std::error_code ec;fs::remove_all(folder,ec);}} cleanup{temp};
 p10k::Config c;c.steps=6;c.dt=150;c.cutoff_mm=5.;
 const auto cache=temp/"forward_history.bin";
 p10n::save_forward(cache,f,m.m,c);
 const auto loaded=p10n::load_forward(cache,m.m,c);
 p10k::require(loaded.objective[1]==f.objective[1] &&
               loaded.frames.size()==6 &&
               loaded.frames[0].previous.size()==f.frames[0].previous.size(),
               "LIT08 forward cache roundtrip failed");
 std::cout<<"LIT08_SELFTEST_OK relative_peakmoment_error="<<std::scientific<<err
          <<" sizeof_state="<<sizeof(ice3d::edv::State)
          <<" cache_roundtrip=1\n";
 return 0;
}

int run(int argc,char**argv){
 fs::path meshPath,cachePath,outDir;
 int threads=1;
 bool selftest_only=false;
 for(int i=1;i<argc;++i){
  const std::string s=argv[i];
  auto val=[&](){p10k::require(i+1<argc,"LIT08 missing argument after "+s);return std::string(argv[++i]);};
  if(s=="--mesh")meshPath=val();
  else if(s=="--reuse-forward")cachePath=val();
  else if(s=="--out")outDir=val();
  else if(s=="--threads")threads=std::stoi(val());
  else if(s=="--selftest")selftest_only=true;
  else if(s=="--help"){
   std::cout<<"stage3d10ag_frozen_mask --selftest | --mesh MSH --reuse-forward BIN --out NEW_DIR [--threads 1|4]\n";
   return 0;
  } else throw std::invalid_argument("LIT08 unknown option "+s);
 }
 p10k::require(threads>=1&&threads<=4,"LIT08 threads must be 1..4");
 if(selftest_only)return selftest();
 p10k::require(!meshPath.empty()&&!cachePath.empty()&&!outDir.empty(),"LIT08 missing paths");
 p10k::require(fs::is_regular_file(meshPath)&&fs::is_regular_file(cachePath),"LIT08 missing input file");
 p10k::require(!fs::exists(outDir),"LIT08 --out directory must not exist");
 const auto begin=std::chrono::steady_clock::now();
 const auto mesh=read_msh(meshPath).mesh;
 p10k::Config c;c.steps=6;c.dt=150;c.cutoff_mm=5.;
 const auto f=p10n::load_forward(cachePath,mesh,c); // FULL hashes and strict mesh signature
 const auto bc=p10k::adjoint_bc(mesh);
 const auto totals=integrate(mesh,volume_q(3),bc,f,150,threads);
 fs::create_directories(outDir);
 std::ofstream csv(outDir/"LIT08_FROZEN_MASK_PEAK.csv");
 csv<<std::setprecision(17);
 csv<<"mask,volume_m3,peak_numerator_m3,peak_moment,jpeak,delta_jpeak_vs_original,relative_parity_error,peak_moment_longdouble,jpeak_longdouble,qp_count\n";
 double parity=0.;
 for(int k=0;k<4;++k){
  const double j=std::pow(totals.moment[k]/totals.volume[k],1./8.);
  const long double ld=std::pow(totals.moment_ld[k]/totals.volume_ld[k],1.L/8.L);
  if(k==0)parity=std::abs(j-f.objective[1])/std::max(1e-30,std::abs(f.objective[1]));
  csv<<names[k]<<','<<totals.volume[k]<<','<<totals.moment[k]<<','
     <<totals.moment[k]/totals.volume[k]<<','<<j<<','<<j-f.objective[1]<<','
     <<std::abs(j-f.objective[1])/std::max(1e-30,std::abs(f.objective[1]))<<','
     <<static_cast<double>(totals.moment_ld[k]/totals.volume_ld[k])<<','
     <<static_cast<double>(ld)<<','<<totals.included[k]<<'\n';
 }
 csv.close();p10k::require(bool(csv),"LIT08 unable to write summary CSV");
 const auto end=std::chrono::steady_clock::now();
 std::cout<<std::scientific<<std::setprecision(11)
 <<"LIT08_BASELINE_PARITY relative="<<parity
 <<" cache_jpeak="<<f.objective[1]<<" threads="<<threads
 <<" wall_s="<<std::chrono::duration<double>(end-begin).count()<<'\n';
 p10k::require(parity<2.e-5,"LIT08 baseline parity failed versus P10W cache");
 std::cout<<"LIT08_FROZEN_MASK_OK file="<<(outDir/"LIT08_FROZEN_MASK_PEAK.csv").string()<<'\n';
 return 0;
}
} // namespace lit08
int main(int argc,char**argv){try{return lit08::run(argc,argv);}catch(const std::exception& e){std::cerr<<"LIT08_ERROR: "<<e.what()<<'\n';return 2;}}
