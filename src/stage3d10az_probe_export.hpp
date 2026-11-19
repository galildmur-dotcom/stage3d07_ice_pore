#pragma once
// P10AZ: targeted QP audit ONLY; this file is included by the P10AZ target.
// Exact signed terms are captured during P10V analytic differentiation after
// mechanical adjoints are solved. No independent field projection is used.
#include "stage3d10v_analytic_shape.hpp"
#include <array>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <map>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <sstream>
#include <vector>

namespace ice3d::p10az {
struct Contributions {
 double explicit_shape=0,equilibrium=0,history=0;
 double sum()const{return explicit_shape+equilibrium+history;}
};
struct Signed {
 Contributions positive{},negative{};
 void add(const Contributions& c){
  auto addone=[](double value,double& plus,double& minus){
   (value>=0?plus:minus)+=value;
  };
  addone(c.explicit_shape,positive.explicit_shape,negative.explicit_shape);
  addone(c.equilibrium,positive.equilibrium,negative.equilibrium);
  addone(c.history,positive.history,negative.history);
 }
};
struct Element {
 std::size_t id=0,nq=0;
 double volume=0,min_mm=1e100,max_mm=-1e100,max_abs_qp_mech=0;
 Contributions sum{};
 double sum_positive_mech=0,sum_negative_mech=0;
};
struct RadialSubbin {
 std::size_t qp_count=0;
 double volume=0;
 Contributions components{};
 double pos_mechanical=0,neg_mechanical=0;
};
inline void add(Contributions& dst,const Contributions& a){
 dst.explicit_shape+=a.explicit_shape;
 dst.equilibrium+=a.equilibrium;
 dst.history+=a.history;
}
inline void check_near(double a,double b,double abs_terms,const char* where){
 // The production shell pass and the independent QP collector sum in a
 // different order; scale roundoff by the absolute QP contributions when
 // positive/negative values nearly cancel.
 const double tol=1e-9*std::max({1.e-5,std::abs(a),std::abs(b),abs_terms});
 if(!(std::abs(a-b)<=tol))
  throw std::runtime_error(std::string("P10AZ QP partition mismatch: ")+where+
       " got="+std::to_string(a)+" expected="+std::to_string(b));
}
// Append files one time per selected reverse-adjoint step (900s then 750s).
inline void write_step_probe(const std::filesystem::path& out,
      const std::string& mesh_name,const Mesh& mesh,
      const p10v::QpProbe& probe,int step,
      const std::array<std::array<double,3>,2>& expected){
 if(step!=5&&step!=6)throw std::invalid_argument("P10AZ unexpected step");
 if(!(probe.observed_volume>0.)||probe.futures==nullptr)
  throw std::runtime_error("P10AZ invalid objective probe normalization");
 std::array<std::vector<Element>,2> per_element;
 for(auto& v:per_element)v.resize(mesh.tets.size());
 std::array<Signed,2> signed_qp{};
 std::array<std::size_t,2> qp_count{};
 std::array<double,2> selected_volume{};
 std::array<std::array<RadialSubbin,10>,2> subbins{};
 const std::array<double,2> minmm{.02,.05},maxmm{.05,.1};
 std::array<Contributions,2> totals{};
 for(const auto& r:probe.records){
  if(r.bin!=1&&r.bin!=2)throw std::runtime_error("P10AZ unexpected bin");
  const std::size_t k=r.bin-1;
  const Contributions c{probe.weight*(r.d_numerator-
       probe.average*r.d_volume)/probe.observed_volume,
       r.equilibrium,r.history};
  if(!std::isfinite(c.sum())||r.element>=mesh.tets.size())
   throw std::runtime_error("P10AZ invalid QP record");
  Element& e=per_element[k][r.element];
  e.id=r.element;e.nq++;
  e.volume+=r.volume;
  e.min_mm=std::min(e.min_mm,r.distance_mm);
  e.max_mm=std::max(e.max_mm,r.distance_mm);
  e.max_abs_qp_mech=std::max(e.max_abs_qp_mech,std::abs(c.sum()));
  add(e.sum,c);
  if(c.sum()>=0)e.sum_positive_mech+=c.sum();
  else e.sum_negative_mech+=c.sum();
  signed_qp[k].add(c);
  add(totals[k],c);
  selected_volume[k]+=r.volume;qp_count[k]++;
  int sub=int(std::floor(10*(r.distance_mm-minmm[k])/(maxmm[k]-minmm[k])));
  sub=std::clamp(sub,0,9);
  RadialSubbin& sb=subbins[k][static_cast<std::size_t>(sub)];
  sb.qp_count++;sb.volume+=r.volume;add(sb.components,c);
  if(c.sum()>=0)sb.pos_mechanical+=c.sum();
  else sb.neg_mechanical+=c.sum();
 }
 for(std::size_t k=0;k<2;++k){
  check_near(totals[k].explicit_shape,expected[k][0],
    signed_qp[k].positive.explicit_shape-signed_qp[k].negative.explicit_shape,
    "objective");
  check_near(totals[k].equilibrium,expected[k][1],
    signed_qp[k].positive.equilibrium-signed_qp[k].negative.equilibrium,
    "equilibrium");
  check_near(totals[k].history,expected[k][2],
    signed_qp[k].positive.history-signed_qp[k].negative.history,
    "EDV history");
 }
 auto open_append=[&](const char* name,const char* hdr){
  const auto path=out/name;
  const bool exists=std::filesystem::exists(path);
  if(!exists&&step!=6)
   throw std::runtime_error("P10AZ expected new output at step 6: "+path.string());
  std::ofstream f(path,std::ios::app);
  if(!f)throw std::runtime_error("P10AZ cannot open "+path.string());
  f<<std::setprecision(17);
  if(!exists)f<<hdr<<'\n';
  return f;
 };
 auto sig=open_append("P10AZ_QP_SIGN_AUDIT.csv",
  "mesh,time_step,time_s,shell_lower_mm,shell_upper_mm,nq,positive_qp,negative_qp,observed_volume_m3,qp_volume_m3,explicit_per_m,equilibrium_per_m,history_per_m,total_mechanical_per_m,positive_explicit_per_m,negative_explicit_per_m,positive_equilibrium_per_m,negative_equilibrium_per_m,positive_history_per_m,negative_history_per_m,positive_mechanical_qp_per_m,negative_mechanical_qp_per_m,positive_mechanical_element_per_m,negative_mechanical_element_per_m");
 auto top=open_append("P10AZ_TOP_ELEMENTS.csv",
  "mesh,time_step,time_s,shell_lower_mm,shell_upper_mm,rank,element_id,centroid_x_m,centroid_y_m,centroid_z_m,centroid_distance_from_wall_mm,qp_count,qp_volume_m3,qp_min_distance_mm,qp_max_distance_mm,explicit_per_m,equilibrium_per_m,history_per_m,total_mechanical_per_m,positive_mechanical_qp_per_m,negative_mechanical_qp_per_m,max_abs_qp_mechanical_per_m");
 auto sub=open_append("P10AZ_QP_RADIAL_SUBBINS.csv",
  "mesh,time_step,time_s,shell_lower_mm,shell_upper_mm,subbin,sub_lower_mm,sub_upper_mm,qp_count,qp_volume_m3,explicit_per_m,equilibrium_per_m,history_per_m,total_mechanical_per_m,positive_mechanical_per_m,negative_mechanical_per_m");
 const V centre{0,0,.03};
 for(std::size_t k=0;k<2;++k){
  std::vector<const Element*> selected;
  for(auto& e:per_element[k])if(e.nq>0)
   selected.push_back(&e);
  std::stable_sort(selected.begin(),selected.end(),
   [](const auto* a,const auto* b){
    const double aa=std::abs(a->sum.sum()),bb=std::abs(b->sum.sum());
    return aa==bb?a->id<b->id:aa>bb;
   });
  double positiveQpMech=0,negativeQpMech=0,positiveElem=0,negativeElem=0;
  std::size_t positive_qp_count=0,negative_qp_count=0;
  for(const auto& r:probe.records)if(r.bin==k+1){
   const double objective=probe.weight*(r.d_numerator-
       probe.average*r.d_volume)/probe.observed_volume;
   const double mech=objective+r.equilibrium+r.history;
   if(mech>=0)++positive_qp_count;else ++negative_qp_count;
  }
  for(const auto& e:per_element[k])if(e.nq){
   positiveQpMech+=e.sum_positive_mech;
   negativeQpMech+=e.sum_negative_mech;
   if(e.sum.sum()>0)positiveElem+=e.sum.sum();else negativeElem+=e.sum.sum();
  }
  if(positive_qp_count+negative_qp_count!=qp_count[k])
   throw std::runtime_error("P10AZ signed QP count mismatch");
  sig<<mesh_name<<','<<step<<','<<150*step<<','<<minmm[k]<<','<<maxmm[k]<<','
     <<qp_count[k]<<','<<positive_qp_count<<','<<negative_qp_count<<','
     <<probe.observed_volume<<','<<selected_volume[k]<<','
     <<totals[k].explicit_shape<<','<<totals[k].equilibrium<<','
     <<totals[k].history<<','<<totals[k].sum()<<','
     <<signed_qp[k].positive.explicit_shape<<','<<signed_qp[k].negative.explicit_shape<<','
     <<signed_qp[k].positive.equilibrium<<','<<signed_qp[k].negative.equilibrium<<','
     <<signed_qp[k].positive.history<<','<<signed_qp[k].negative.history<<','
     <<positiveQpMech<<','<<negativeQpMech<<','<<positiveElem<<','<<negativeElem<<'\n';
  for(std::size_t i=0;i<std::min(std::size_t(30),selected.size());++i){
   const auto& e=*selected[i];
   V centroid{};
   for(int a=0;a<4;++a)centroid=centroid+mesh.nodes[mesh.tets[e.id][a]]*.25;
   const double dist_mm=(norm(centroid-centre)-.001)*1000.;
   top<<mesh_name<<','<<step<<','<<150*step<<','<<minmm[k]<<','<<maxmm[k]<<','
      <<(i+1)<<','<<e.id<<','<<centroid.x<<','<<centroid.y<<','<<centroid.z<<','<<dist_mm<<','
      <<e.nq<<','<<e.volume<<','<<e.min_mm<<','<<e.max_mm<<','
      <<e.sum.explicit_shape<<','<<e.sum.equilibrium<<','<<e.sum.history<<','<<e.sum.sum()<<','
      <<e.sum_positive_mech<<','<<e.sum_negative_mech<<','<<e.max_abs_qp_mech<<'\n';
  }
  for(std::size_t i=0;i<10;++i){
   const auto& b=subbins[k][i];
   const double width=(maxmm[k]-minmm[k])/10.;
   sub<<mesh_name<<','<<step<<','<<150*step<<','<<minmm[k]<<','<<maxmm[k]<<','
      <<i<<','<<(minmm[k]+i*width)<<','<<(minmm[k]+(i+1)*width)<<','
      <<b.qp_count<<','<<b.volume<<','<<b.components.explicit_shape<<','
      <<b.components.equilibrium<<','<<b.components.history<<','<<b.components.sum()<<','
      <<b.pos_mechanical<<','<<b.neg_mechanical<<'\n';
  }
 }
 if(!sig||!top||!sub)throw std::runtime_error("P10AZ output write failed");
}
} // namespace ice3d::p10az
