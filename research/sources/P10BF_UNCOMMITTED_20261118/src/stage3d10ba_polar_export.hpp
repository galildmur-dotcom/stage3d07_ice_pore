#pragma once
// P10BA: optional polar-by-radial QP decomposition of the *existing* P10AZ
// discrete analytic mechanical shape derivative. Included only by P10BA.
// Inclusion order: stage3d10az_probe_export.hpp has already been included.
#ifndef STAGE3D10BA_POLAR_AUDIT
#error "P10BA exporter requires STAGE3D10BA_POLAR_AUDIT"
#endif
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>

namespace ice3d::p10ba {

constexpr int radial_count=10;
constexpr int polar_count=10;
struct Cell {
 std::size_t nq=0,positive_qp=0,negative_qp=0;
 double volume=0.,positive=0.,negative=0.;
 p10az::Contributions components{};
 void accumulate(double q_volume,const p10az::Contributions& c){
  ++nq;volume+=q_volume;p10az::add(components,c);
  if(c.sum()>=0.){positive+=c.sum();++positive_qp;}
  else{negative+=c.sum();++negative_qp;}
 }
};

// Uniform increments in mu=cos(theta) have equal surface area for a sphere.
inline int polar_index(double mu){
 if(!std::isfinite(mu)||mu < -1.-1.e-12||mu > 1.+1.e-12)
  throw std::runtime_error("P10BA invalid polar cosine");
 return std::clamp(int(std::floor(5.*(std::clamp(mu,-1.,1.)+1.))),0,9);
}
inline int radial_index(double distance_mm,int shell){
 const double a=shell==0?.02:.05;
 const double b=shell==0?.05:.10;
 return std::clamp(int(std::floor(radial_count*(distance_mm-a)/(b-a))),0,9);
}

// The common implementation also serves P10BD, where all backward time steps
// are recorded. The original P10BA entry point below remains unchanged.
inline void write_step_polar_impl(const std::filesystem::path& out,
    const std::string& mesh_name,const p10v::QpProbe& probe,int step,
    int dt,int first_step,const std::string& stage,
    const std::array<std::array<double,3>,2>& expected){
 if(step<1||step>first_step||dt<1||first_step<1)
  throw std::invalid_argument(stage+" invalid temporal index");
 if(!(probe.observed_volume>0.)||probe.futures==nullptr)
  throw std::runtime_error("P10BA missing QP normalization");
 std::array<std::array<std::array<Cell,polar_count>,radial_count>,2> grid{};
 std::array<std::array<Cell,radial_count>,2> direct_radial{};
 std::array<Cell,2> direct_shell{};
 double total_abs_component=0.;
 for(const auto& r:probe.records){
  if(r.bin!=1&&r.bin!=2)throw std::runtime_error("P10BA unexpected shell");
  const int s=int(r.bin)-1;
  const int i=radial_index(r.distance_mm,s);
  const int j=polar_index(r.polar_mu);
  const p10az::Contributions c{probe.weight*(r.d_numerator-
      probe.average*r.d_volume)/probe.observed_volume,
      r.equilibrium,r.history};
  if(!std::isfinite(r.volume)||!(r.volume>=0.)||
     !std::isfinite(c.explicit_shape)||!std::isfinite(c.equilibrium)||
     !std::isfinite(c.history))
   throw std::runtime_error("P10BA invalid QP data");
  grid[s][i][j].accumulate(r.volume,c);
  direct_radial[s][i].accumulate(r.volume,c);
  direct_shell[s].accumulate(r.volume,c);
  total_abs_component+=std::abs(c.explicit_shape)+
                      std::abs(c.equilibrium)+std::abs(c.history);
 }

 // Prove the new polar partition re-sums to the independently collected
 // 10 radial subbins, then to the existing analytic shell totals.
 std::array<double,2> worst_rel{};
 for(int s=0;s<2;++s){
  Cell all{};
  for(int i=0;i<radial_count;++i){
   Cell summed{};
   for(int j=0;j<polar_count;++j){
    const auto& b=grid[s][i][j];
    summed.nq+=b.nq;
    summed.positive_qp+=b.positive_qp;
    summed.negative_qp+=b.negative_qp;
    summed.volume+=b.volume;
    p10az::add(summed.components,b.components);
    summed.positive+=b.positive;summed.negative+=b.negative;
   }
   const auto& ref=direct_radial[s][i];
   if(summed.nq!=ref.nq||summed.positive_qp!=ref.positive_qp||
      summed.negative_qp!=ref.negative_qp)
    throw std::runtime_error("P10BA polar QP-count partition mismatch");
   int component_index=0;
   for(const auto pair:std::array<std::array<double,2>,5>{{
        {summed.volume,ref.volume},
        {summed.components.explicit_shape,ref.components.explicit_shape},
        {summed.components.equilibrium,ref.components.equilibrium},
        {summed.components.history,ref.components.history},
        {summed.positive+summed.negative,ref.positive+ref.negative}}}){
    const double scale=component_index++==0
         ?std::max({1e-22,std::abs(pair[0]),std::abs(pair[1])})
         :std::max({1e-12,total_abs_component,
                    std::abs(pair[0]),std::abs(pair[1])});
    const double rel=std::abs(pair[0]-pair[1])/scale;
    worst_rel[s]=std::max(worst_rel[s],rel);
    if(rel>1e-9)throw std::runtime_error("P10BA radial-polar parity failed");
   }
   all.nq+=summed.nq;
   all.volume+=summed.volume;
   p10az::add(all.components,summed.components);
  }
  if(all.nq!=direct_shell[s].nq)
   throw std::runtime_error("P10BA shell QP-count mismatch");
  p10az::check_near(all.volume,direct_shell[s].volume,total_abs_component,
                   "P10BA total QP volume");
  p10az::check_near(all.components.explicit_shape,expected[s][0],
                   total_abs_component,"P10BA explicit shell");
  p10az::check_near(all.components.equilibrium,expected[s][1],
                   total_abs_component,"P10BA equilibrium shell");
  p10az::check_near(all.components.history,expected[s][2],
                   total_abs_component,"P10BA history shell");
 }

 auto open_append=[&](const std::string& name,const char* hdr){
  const auto path=out/name;
  const bool exists=std::filesystem::exists(path);
  if((step==first_step&&exists)||(step!=first_step&&!exists))
   throw std::runtime_error(stage+" unexpected output existence: "+path.string());
  std::ofstream f(path,std::ios::app);
  if(!f)throw std::runtime_error("P10BA cannot write: "+path.string());
  f<<std::setprecision(17);
  if(!exists)f<<hdr<<'\n';
  return f;
 };
 auto rows=open_append(stage+"_QP_POLAR_RADIAL.csv",
  "mesh,time_step,time_s,shell_lower_mm,shell_upper_mm,radial_subbin,radial_lower_mm,radial_upper_mm,polar_band,mu_lower,mu_upper,qp_count,positive_qp,negative_qp,qp_volume_m3,explicit_per_m,equilibrium_per_m,history_per_m,total_mechanical_per_m,positive_mechanical_per_m,negative_mechanical_per_m");
 auto audit=open_append(stage+"_POLAR_PARTITION_AUDIT.csv",
  "mesh,time_step,time_s,shell_lower_mm,shell_upper_mm,radial_subbins,polar_bands,qp_count,qp_volume_m3,total_mechanical_per_m,max_partition_rel");
 constexpr std::array<double,2> minmm{.02,.05},maxmm{.05,.1};
 for(int s=0;s<2;++s){
  for(int i=0;i<radial_count;++i){
   const double dr=(maxmm[s]-minmm[s])/radial_count;
   for(int j=0;j<polar_count;++j){
    const Cell& b=grid[s][i][j];
    rows<<mesh_name<<','<<step<<','<<dt*step<<','<<minmm[s]<<','<<maxmm[s]<<','
        <<i<<','<<(minmm[s]+i*dr)<<','<<(minmm[s]+(i+1)*dr)<<','
        <<j<<','<<(-1.+.2*j)<<','<<(-1.+.2*(j+1))<<','
        <<b.nq<<','<<b.positive_qp<<','<<b.negative_qp<<','<<b.volume<<','
        <<b.components.explicit_shape<<','<<b.components.equilibrium<<','
        <<b.components.history<<','<<b.components.sum()<<','
        <<b.positive<<','<<b.negative<<'\n';
   }
  }
  const Cell& b=direct_shell[s];
  audit<<mesh_name<<','<<step<<','<<dt*step<<','<<minmm[s]<<','<<maxmm[s]<<','
       <<radial_count<<','<<polar_count<<','<<b.nq<<','<<b.volume<<','
       <<b.components.sum()<<','<<worst_rel[s]<<'\n';
 }
 if(!rows||!audit)throw std::runtime_error("P10BA output write failed");
}

inline void write_step_polar(const std::filesystem::path& out,
    const std::string& mesh_name,const p10v::QpProbe& probe,int step,
    const std::array<std::array<double,3>,2>& expected){
 if(step!=5&&step!=6)throw std::invalid_argument("P10BA step must be 5 or 6");
 write_step_polar_impl(out,mesh_name,probe,step,150,6,"P10BA",expected);
}

#ifdef STAGE3D10BD_TEMPORAL_AUDIT
inline void write_step_polar_temporal(const std::filesystem::path& out,
    const std::string& mesh_name,const p10v::QpProbe& probe,int step,
    int dt,int steps,const std::array<std::array<double,3>,2>& expected){
#ifdef STAGE3D10BE_TEMPORAL_AUDIT
 const bool extended_schedule=dt==25&&steps==36;
#else
 const bool extended_schedule=false;
#endif
 if(!((dt==150&&steps==6)||(dt==75&&steps==12)||
      (dt==50&&steps==18)||extended_schedule))
#ifdef STAGE3D10BE_TEMPORAL_AUDIT
  throw std::invalid_argument("P10BE permits 25 s (36 steps) plus legacy P10BD schedules");
#else
  throw std::invalid_argument("P10BD permits only 150/75/50 s for 900 s");
#endif
 write_step_polar_impl(out,mesh_name,probe,step,dt,steps,"P10BD",expected);
}
#endif
} // namespace ice3d::p10ba
