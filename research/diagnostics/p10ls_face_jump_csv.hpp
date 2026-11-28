#pragma once
// Source-only P10LS signed4D face-jump writer. Two recovery orders, one row
// per 4D bin and time step, including empty/unsupported bins as count zero.
#include "p10lr_tet10_face_jump.hpp"
#include <fstream>
#include <iomanip>
#include <stdexcept>

namespace p10ls {
inline void header(std::ofstream& output){
 output<<"mesh,step,time_end_s,recovery_degree,radial_bin,mu_bin,phi_bin,"
         "face_count,stress_frobenius_mean_pa,stress_frobenius_rms_pa,"
         "stress_frobenius_max_pa,traction_mean_pa,traction_rms_pa,"
         "traction_max_pa,shape_jvp_mean_pa_per_m,shape_jvp_rms_pa_per_m,"
         "shape_jvp_max_pa_per_m\n";
 output<<std::setprecision(17);
}
inline void write(std::ofstream& output,const std::string& mesh,int step,int dt,
                  const p10lr::Result& result,int degree){
 std::size_t counted=0;
 for(int ir=0;ir<10;++ir)for(int im=0;im<10;++im)
  for(int ip=0;ip<12;++ip){
   const auto id=std::size_t((ir*10+im)*12+ip);
   const auto& b=result.cells[id];counted+=b.faces;
   const double n=b.faces?double(b.faces):1.;
   output<<mesh<<','<<step<<','<<step*dt<<','<<degree<<','
         <<ir<<','<<im<<','<<ip<<','<<b.faces<<','
         <<b.stress_frob_sum/n<<','<<std::sqrt(b.stress_frob_square/n)<<','
         <<b.stress_frob_max<<','<<b.traction_sum/n<<','
         <<std::sqrt(b.traction_square/n)<<','<<b.traction_max<<','
         <<b.geom_jvp_frob_sum/n<<','<<std::sqrt(b.geom_jvp_square/n)<<','
         <<b.geom_jvp_max<<'\n';
  }
 if(counted!=result.observed_pairs)
  throw std::runtime_error("P10LS face-count bin closure mismatch");
 if(!output)throw std::runtime_error("P10LS face CSV output failure");
}
}
