// Stage 3D-10R: cheap, read-only spatial diagnostic of the EXISTING P10N/P10P
// forward history. It never solves forward mechanics, heat or any adjoint.
// Reuse the production cache validator and the unmodified P10P type graph.
#define STAGE3D10P_NO_MAIN
#include "stage3d10p_partial_audit.cpp"

#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <string>
#include <vector>

namespace p10r {
namespace A=ice3d::p10c;

// Shells are labelled by distance in mm OUTSIDE the 1-mm spherical cavity.
// B6 contains additional ice up to about 6 mm from the pore centre; last
// shells may be empty, which is an acceptable diagnostic outcome.
constexpr std::array<double,10> shell_start_mm{0.,.02,.05,.1,.25,.5,1.,2.,5.,15.};
constexpr size_t nbins=shell_start_mm.size();
constexpr double pore_radius_m=.001;
constexpr double pore_center_z_m=.03;

struct Shell {
 std::uint64_t qps=0;
 double volume=0;
 double radial_weighted_mm=0;
 double max_sigma1_MPa=-std::numeric_limits<double>::infinity();
 double sigma1_volume_MPa=0;
 double moment_numerator_m3=0;
};

struct Summary {
 int step=0;
 double b6_volume_m3=0;
 double peak_moment=0;
 double largest_sigma1_MPa=-std::numeric_limits<double>::infinity();
 std::uint64_t counted_qps=0;
 std::uint64_t geometry_below_sphere_qps=0;
 double min_signed_distance_mm=std::numeric_limits<double>::infinity();
 std::array<Shell,nbins> bins{};
};

static size_t find_bin(double signed_distance_mm) {
 const double distance=std::max(0.0,signed_distance_mm);
 for(size_t k=1;k<nbins;++k)
  if(distance<shell_start_mm[k])return k-1;
 return nbins-1;
}

static double upper_edge(size_t k) {
 return k+1<nbins?shell_start_mm[k+1]:
     std::numeric_limits<double>::infinity();
}

static void selftest_bins(){
 p10k::require(find_bin(-1e-8)==0,"P10R negative roundoff shell mapping");
 p10k::require(find_bin(.0)==0,"P10R wall shell mapping");
 p10k::require(find_bin(.019999)==0,"P10R first shell mapping");
 p10k::require(find_bin(.02)==1,"P10R exact shell boundary mapping");
 p10k::require(find_bin(15.)==nbins-1,"P10R final shell mapping");
 std::cout<<"P10R_SPATIAL_BINS_SELFTEST_OK bins="<<nbins<<'\n';
}

static void check_cache_header(const fs::path& filename,const Mesh& mesh,
                               const p10k::Config& c){
 std::ifstream in(filename,std::ios::binary);
 p10k::require(bool(in),"P10R forward cache not found");
 const auto nq=mesh.tets.size()*volume_q(3).size();
 const std::array<std::uint64_t,10> expected{
  p10n::MAGIC,p10n::VERSION,std::uint64_t(sizeof(State)),
  ice3d::p09e::mesh_signature(mesh),std::uint64_t(mesh.nodes.size()),
  std::uint64_t(mesh.tets.size()),std::uint64_t(nq),
  std::uint64_t(c.steps),std::uint64_t(c.dt),
  std::bit_cast<std::uint64_t>(c.cutoff_mm)};
 for(size_t i=0;i<expected.size();++i){
  std::uint64_t got=0;
  p10n::read_scalar(in,got);
  p10k::require(got==expected[i],
    "P10R cache incompatible at header field "+std::to_string(i));
 }
}

static std::vector<std::uint8_t> qp_shell_map(const Mesh& mesh,
                   const std::vector<GaussQ>& qs,
                   std::uint64_t& qps_below_sphere,
                   double& minimum_signed_mm) {
 const size_t nq=mesh.tets.size()*qs.size();
 std::vector<std::uint8_t> bins(nq);
 qps_below_sphere=0;
 minimum_signed_mm=std::numeric_limits<double>::infinity();
 const V center{0,0,pore_center_z_m};
 for(size_t e=0;e<mesh.tets.size();++e){
  const auto& tet=mesh.tets[e];
  for(size_t t=0;t<qs.size();++t){
   V point{};
   for(int j=0;j<10;++j)point=point+mesh.nodes[tet[j]]*qs[t].N[j];
   const double dist_mm=(norm(point-center)-pore_radius_m)*1000.;
   minimum_signed_mm=std::min(minimum_signed_mm,dist_mm);
   if(dist_mm < -1.e-8)++qps_below_sphere;
   bins[e*qs.size()+t]=std::uint8_t(find_bin(dist_mm));
  }
 }
 return bins;
}

static double sigma1_MPa(const ice3d::p10c::QuadraturePoint& qp,
                         double& moment_value){
 const auto spectral=ice3d::p10f::jacobi_symmetric_3x3(qp.law.response.sigma);
 moment_value=0.;
 double maximum=-std::numeric_limits<double>::infinity();
 for(const double eig:spectral.eigen){
  maximum=std::max(maximum,eig);
  const auto p=ice3d::p10f::positive_and_derivative(
      eig,ice3d::p10f::Parameters{}.sigma_ref).first;
  moment_value+=std::pow(p,8);
 }
 return maximum*1.e-6;
}

static Summary inspect_step(const A::Step& step,const int number,
             const std::vector<uint8_t>& observation_mask,
             const std::vector<std::uint8_t>& qp_bin,const size_t nquad,
             const std::uint64_t geometry_below_sphere_qps,
             const double min_signed_distance_mm,
             const std::vector<double>& qp_mean_distance_mm){
 p10k::require(qp_bin.size()==step.qps.size()&&
               qp_mean_distance_mm.size()==step.qps.size(),
               "P10R geometry/QP mismatch");
 Summary result;
 result.step=number;
 result.geometry_below_sphere_qps=geometry_below_sphere_qps;
 result.min_signed_distance_mm=min_signed_distance_mm;
 for(size_t q=0;q<step.qps.size();++q){
  if(!observation_mask[q/nquad])continue;
  const auto& qp=step.qps[q];
  const size_t bin=qp_bin[q];
  auto& row=result.bins[bin];
  double moment=0;
  const double sig=sigma1_MPa(qp,moment);
  p10k::require(std::isfinite(sig)&&std::isfinite(moment)&&
                 qp.volume>0.,"P10R invalid stress/moment/volume");
  row.qps++;
  row.volume+=qp.volume;
  row.radial_weighted_mm+=qp.volume*qp_mean_distance_mm[q];
  row.sigma1_volume_MPa+=qp.volume*sig;
  row.max_sigma1_MPa=std::max(row.max_sigma1_MPa,sig);
  row.moment_numerator_m3+=qp.volume*moment;
  result.counted_qps++;
  result.b6_volume_m3+=qp.volume;
  result.largest_sigma1_MPa=std::max(result.largest_sigma1_MPa,sig);
 }
 p10k::require(result.b6_volume_m3>0.,"P10R empty B6 observation region");
 for(const auto& row:result.bins)
  result.peak_moment+=row.moment_numerator_m3/result.b6_volume_m3;
 return result;
}

static void write_report(const std::vector<Summary>& data,
                         const p10k::Config& c,
                         const double cached_jpeak,
                         const double reconstructed_jpeak){
 std::ofstream shell(c.out/"P10R_STRESS_SHELLS.csv");
 std::ofstream audit(c.out/"P10R_PROFILE_AUDIT.csv");
 p10k::require(bool(shell)&&bool(audit),"P10R CSV creation failed");
 shell<<std::setprecision(17);
 audit<<std::setprecision(17);
 shell<<"mesh,time_step,time_s,distance_lower_mm,distance_upper_mm,"
         "qp_count,volume_m3,mean_distance_mm,mean_sigma1_MPa,"
         "max_sigma1_MPa,approx_gradient_of_shell_mean_MPa_per_mm,"
         "p8_peak_moment_fraction,p8_peak_moment_contribution,"
         "p8_density_ratio_to_B6_mean\n";
 audit<<"mesh,time_step,time_s,observed_b6_volume_m3,"
        "peak_moment,global_max_sigma1_MPa,qp_count,"
        "qps_below_spherical_radius_all_mesh,"
        "min_signed_distance_to_pore_mm,shell_fraction_sum,"
        "wall_0_100um_volume_fraction,wall_0_100um_p8_fraction,"
        "wall_0_500um_volume_fraction,wall_0_500um_p8_fraction,"
        "cached_jpeak,reconstructed_jpeak,jpeak_parity_rel\n";
 for(const auto& frame:data){
  double shares=0.;
  double wall_100_volume=0.,wall_100_peak=0.;
  double wall_500_volume=0.,wall_500_peak=0.;
  const auto mean_dist=[&](size_t k){
   const auto& b=frame.bins[k];
   return b.radial_weighted_mm/b.volume;
  };
  const auto mean_sigma=[&](size_t k){
   const auto& b=frame.bins[k];
   return b.sigma1_volume_MPa/b.volume;
  };
  for(size_t k=0;k<nbins;++k){
   const auto& b=frame.bins[k];
   const double contribution=b.moment_numerator_m3/frame.b6_volume_m3;
   const double share=frame.peak_moment>0.?contribution/frame.peak_moment:0.;
   shares+=share;
   if(k<3){wall_100_volume+=b.volume;wall_100_peak+=share;}
   if(k<5){wall_500_volume+=b.volume;wall_500_peak+=share;}
   shell<<c.mesh.stem().string()<<','<<frame.step<<','<<frame.step*c.dt<<','
       <<shell_start_mm[k]<<',';
   if(k+1<nbins)shell<<upper_edge(k);
   shell<<','<<b.qps<<','<<b.volume<<',';
   if(b.qps) shell<<mean_dist(k);
   shell<<',';
   if(b.qps) shell<<mean_sigma(k);
   shell<<',';
   if(b.qps) shell<<b.max_sigma1_MPa;
   shell<<',';
   // Slope of the SHELL-MEAN field (not local spatial derivative).
   if(b.qps){
    size_t l=k,r=k;
    while(l>0){--l;if(frame.bins[l].qps)break;}
    while(r+1<nbins){++r;if(frame.bins[r].qps)break;}
    if(l!=r&&frame.bins[l].qps&&frame.bins[r].qps){
     const double dd=mean_dist(r)-mean_dist(l);
     if(dd>0.)shell<<(mean_sigma(r)-mean_sigma(l))/dd;
    }
   }
   shell<<','<<share<<','<<contribution<<',';
   if(b.volume>0.&&frame.peak_moment>0.)
    shell<<share/(b.volume/frame.b6_volume_m3);
   shell<<'\n';
  }
  p10k::require(std::abs(shares-1.)<1e-10,
     "P10R peak moment is not partitioned by shells");
  audit<<c.mesh.stem().string()<<','<<frame.step<<','<<frame.step*c.dt<<','
       <<frame.b6_volume_m3<<','<<frame.peak_moment<<','
       <<frame.largest_sigma1_MPa<<','<<frame.counted_qps<<','
       <<frame.geometry_below_sphere_qps<<','<<frame.min_signed_distance_mm
       <<','<<shares<<','<<wall_100_volume/frame.b6_volume_m3
       <<','<<wall_100_peak<<','<<wall_500_volume/frame.b6_volume_m3
       <<','<<wall_500_peak<<','<<cached_jpeak<<','<<reconstructed_jpeak
       <<','<<std::abs(cached_jpeak-reconstructed_jpeak)/
                 std::max({1.e-20,std::abs(cached_jpeak),
                           std::abs(reconstructed_jpeak)})<<'\n';
 }
 shell.close();audit.close();
 p10k::require(bool(shell)&&bool(audit),"P10R CSV write failed");
}

int run(const p10k::Config& c,const fs::path& cache){
 p10k::require(fs::is_regular_file(c.mesh),"P10R mesh missing");
 p10k::require(fs::is_regular_file(cache),"P10R forward cache missing");
 p10k::require(c.steps*c.dt==900,"P10R requires steps*dt=900 s");
 p10k::require(!fs::exists(c.out),"P10R --out must be a NEW folder");
 const Mesh mesh=read_msh(c.mesh).mesh;
 check_cache_header(cache,mesh,c);
 const auto quad=volume_q(3);
 const auto observation=p10k::observation_elements(mesh);
 std::cout<<"P10R_PREFLIGHT_OK mesh="<<c.mesh.stem().string()
          <<" nodes="<<mesh.nodes.size()<<" tet10="<<mesh.tets.size()
          <<" qps="<<mesh.tets.size()*quad.size()
          <<" steps="<<c.steps<<" dt="<<c.dt
          <<" forward_cache_bytes="<<fs::file_size(cache)
          <<" nonlinear_forward_solves=0 mechanical_adjoint_solves=0\n";
 if(c.preflight)return 0;
 fs::create_directories(c.out);
 const auto forward=p10n::load_forward(cache,mesh,c);
 std::uint64_t below=0;
 double min_signed=0;
 const auto bin=qp_shell_map(mesh,quad,below,min_signed);
 // Retain a read-only physical distance for the mean-radius diagnostic.
 std::vector<double> point_distance(bin.size(),0.);
 const V center{0,0,pore_center_z_m};
 for(size_t e=0;e<mesh.tets.size();++e){
  const auto& tet=mesh.tets[e];
  for(size_t t=0;t<quad.size();++t){
   V x{};
   for(int j=0;j<10;++j)x=x+mesh.nodes[tet[j]]*quad[t].N[j];
   point_distance[e*quad.size()+t]=
       std::max(0.,(norm(x-center)-pore_radius_m)*1000.);
  }
 }
 const auto pinned=p10k::adjoint_bc(mesh);
 std::vector<Summary> results;
 results.reserve(std::size_t(c.steps));
 for(int n=1;n<=c.steps;++n){
  const auto& frame=forward.frames.at(std::size_t(n-1));
  const A::Step state(mesh,quad,frame.temperature,frame.previous,
      double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
      ice3d::p10b::Controls{true,true});
  results.push_back(inspect_step(state,n,observation,bin,quad.size(),
                                below,min_signed,point_distance));
  double wall100_volume=0.,wall100_peak=0.;
  for(size_t b=0;b<3;++b){
   wall100_volume+=results.back().bins[b].volume;
   wall100_peak+=results.back().bins[b].moment_numerator_m3;
  }
  const double total_peak_numerator=results.back().peak_moment*
                                    results.back().b6_volume_m3;
  std::cout<<"P10R_STEP_OK time_s="<<n*c.dt
           <<" b6_moment="<<results.back().peak_moment
           <<" max_sigma1_MPa="<<results.back().largest_sigma1_MPa
           <<" wall_0_100um_volume_fraction="
           <<wall100_volume/results.back().b6_volume_m3
           <<" wall_0_100um_p8_fraction="
           <<(total_peak_numerator>0.?wall100_peak/total_peak_numerator:0.)
           <<'\n'
           <<std::flush;
 }
 double integrated_moment=.5/c.steps*
        ice3d::p10f::initial_time_value(ice3d::p10f::Kind::PeakMoment);
 for(int n=1;n<=c.steps;++n){
  const double weight=(n==c.steps?.5:1.)/c.steps;
  integrated_moment+=weight*results[size_t(n-1)].peak_moment;
 }
 p10k::require(integrated_moment>0.,"P10R nonpositive p8 time moment");
 const double jpeak=std::pow(integrated_moment,1./8.);
 const double cached=forward.objective[1];
 const double parity=std::abs(jpeak-cached)/
    std::max({1.e-20,std::abs(jpeak),std::abs(cached)});
 p10k::require(parity<2.e-5,
    "P10R shell integral does not reproduce saved jpeak objective");
 std::cout<<"P10R_JPEAK_PARITY cached="<<cached
          <<" reconstructed="<<jpeak<<" rel="<<parity<<'\n';
 write_report(results,c,cached,jpeak);
 std::cout<<"P10R_WALL_PROFILE_OK mesh="<<c.mesh.stem().string()
          <<" steps="<<c.steps<<" bins="<<nbins
          <<" forward_cache_reused=1 nonlinear_forward_solves=0"
          <<" mechanical_adjoint_solves=0\n";
 return 0;
}
} // namespace p10r

#ifndef STAGE3D10R_NO_MAIN
int main(int argc,char** argv){
 try{
  fs::path cache;
  std::vector<char*> filtered{argv[0]};
  bool explicit_mesh=false,explicit_out=false;
  for(int i=1;i<argc;++i){
   const std::string flag=argv[i];
   if(flag=="--help"){
    std::cout<<"stage3d10r_wall_profile --mesh MSH --forward-cache P10N_BIN "
     "--out NEW_DIR --steps 6 --dt 150 --threads 4 "
     "[--preflight] [--cutoff-mm 5]\n";
    return 0;
   }
   if(flag=="--forward-cache"){
    p10k::require(i+1<argc,"P10R missing --forward-cache path");
    cache=argv[++i];
   }else{
    if(flag=="--mesh")explicit_mesh=true;
    if(flag=="--out")explicit_out=true;
    filtered.push_back(argv[i]);
   }
  }
  const auto c=p10k::parse(int(filtered.size()),filtered.data());
  if(c.selftest){p10r::selftest_bins();return 0;}
  p10k::require(explicit_mesh&&explicit_out&&!cache.empty(),
    "P10R requires explicit --mesh, --out, --forward-cache");
  return p10r::run(c,cache);
 }catch(const std::exception& e){
  std::cerr<<"P10R_ERROR: "<<e.what()<<'\n';return 2;
 }
}
#endif // STAGE3D10R_NO_MAIN
