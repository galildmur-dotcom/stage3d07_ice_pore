#pragma once
// P10DD: diagnostic-only physical QP partition of the exact P10W R/EDV_VAR
// discrete gradient. Include after stage3d10n_base_m_impl.inc and P10V.
// Mechanical: all 27 curved Tet10 QPs; thermal: all 64 Tet10 QPs.
// No extra forward/adjoint solves, no central shape finite differences.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace ice3d::p10dd {

constexpr std::array<double,10> radial_lower_mm{
  0., .02, .05, .1, .25, .5, 1., 2., 5., 15.};
constexpr int nrad=10,nmu=10,nphi=12,ncell=nrad*nmu*nphi;
constexpr double pi=3.141592653589793238462643383279502884;

struct Parts {
 double explicit_objective=0.,equilibrium=0.,history=0.;
 double mass=0.,diffusion=0.,robin=0.;
 double mechanical()const{return explicit_objective+equilibrium+history;}
 double thermal()const{return mass+diffusion+robin;}
 double total()const{return mechanical()+thermal();}
 void add(const Parts& p){
  explicit_objective+=p.explicit_objective;equilibrium+=p.equilibrium;
  history+=p.history;mass+=p.mass;diffusion+=p.diffusion;
  robin+=p.robin;
 }
};
struct Cell {
 Parts part{};
 double explicit_geometry=0.,explicit_stress=0.; // P10LG extra diagnostic only
 std::size_t mechanical_qp=0,thermal_qp=0;
 double mechanical_volume=0.,thermal_volume=0.;
};
struct Snapshot {
 std::array<Cell,ncell> cells{};
 Parts top_robin{}; // Boundary contribution never put into volume cells.
 std::size_t top_qp=0,axis_qp=0;
 double top_area=0.,observed_volume=0.,observed_dvolume=0.;
 Parts sum()const{
  Parts s=top_robin;
  for(const auto& c:cells)s.add(c.part);
  return s;
 }
 std::size_t mechanical_qps()const{
  std::size_t n=0;for(const auto& c:cells)n+=c.mechanical_qp;return n;
 }
 std::size_t thermal_qps()const{
  std::size_t n=0;for(const auto& c:cells)n+=c.thermal_qp;return n;
 }
};

inline std::size_t index(const V& x,bool* is_axis=nullptr){
 const V d=x-V{0.,0.,.03};
 const double r=norm(d);
 if(!(r>0.)||!std::isfinite(r))
  throw std::runtime_error("P10DD nonfinite or zero pore-centred QP radius");
 const double wall_mm=(r-RBASE)*1000.;
 int ir=nrad-1;
 for(int i=1;i<nrad;++i)if(wall_mm<radial_lower_mm[std::size_t(i)]){
  ir=i-1;break;
 }
 const double mu=std::clamp(d.z/r,-1.,1.);
 const int im=std::clamp(int((mu+1.)*.5*nmu),0,nmu-1);
 const double rho=std::hypot(d.x,d.y);
 const bool axis=rho<=std::numeric_limits<double>::epsilon()*r*16.;
 if(is_axis)*is_axis=axis;
 // Phi in [-pi,pi), unique wrap at +pi. The axis is assigned phi-bin 0
 // by convention, and counted separately (azimuth is undefined at axis).
 const double phi=axis?-pi:std::atan2(d.y,d.x);
 const double angle=phi>=pi?-pi:phi;
 const int ip=std::clamp(int((angle+pi)/(2*pi)*nphi),0,nphi-1);
 return std::size_t((ir*nmu+im)*nphi+ip);
}

inline void expect_close(double actual,double reference,const char* name,
                         double tolerance=2.e-8){
 const double scale=std::max({1.e-10,std::abs(actual),std::abs(reference)});
 if(!std::isfinite(actual)||!std::isfinite(reference)||
    std::abs(actual-reference)>1.e-10+tolerance*scale)
  throw std::runtime_error(std::string("P10DD QP/CSR closure mismatch: ")+name+
     " actual="+std::to_string(actual)+
     " reference="+std::to_string(reference));
}

// The exact local P10V formula is recomputed on frozen states/adjoints solely
// for diagnostics. Two-pass normalized objective: d(J/V)=(dJ-J*dV/V)/V.
inline Snapshot mechanical_step(const Mesh& mesh,
                                const std::vector<GaussQ>& quad,
                                const p10c::Step& step,
                                const std::vector<V>& velocity,
                                const std::vector<std::uint8_t>& mask,
                                const std::vector<double>& lambda,
                                const std::vector<p10c::State>& futures,
                                double weight){
 const std::size_t nq=mesh.tets.size()*quad.size();
 if(quad.size()!=27||velocity.size()!=mesh.nodes.size()||
    mask.size()!=mesh.tets.size()||lambda.size()!=3*mesh.nodes.size()||
    futures.size()!=nq||step.qps.size()!=nq||!std::isfinite(weight))
  throw std::invalid_argument("P10DD mechanical shape/QP dimensions");
 Snapshot out;
 double numerator=0.;
 std::array<double,ncell> dnumerator{};
 std::array<double,ncell> dnumerator_geometry{},dnumerator_stress{};
 std::array<double,ncell> dvolume{};
 for(std::size_t e=0;e<mesh.tets.size();++e){
  const auto& ids=mesh.tets[e];
  for(std::size_t iq=0;iq<quad.size();++iq){
   const std::size_t qid=e*quad.size()+iq;
   const auto& b=quad[iq];
   const auto& qp=step.qps[qid];
   V dr{},ds{},dt{},d_dr{},d_ds{},d_dt{},x{};
   for(int a=0;a<10;++a){
    const V node=mesh.nodes[ids[a]],v=velocity[ids[a]];
    dr=dr+node*b.d[a][0];ds=ds+node*b.d[a][1];dt=dt+node*b.d[a][2];
    d_dr=d_dr+v*b.d[a][0];d_ds=d_ds+v*b.d[a][1];
    d_dt=d_dt+v*b.d[a][2];x=x+node*b.N[a];
   }
   bool axis=false;
   auto& cell=out.cells[index(x,&axis)];
   if(axis)++out.axis_qp;
   ++cell.mechanical_qp;cell.mechanical_volume+=qp.volume;
   const V c0=cross(ds,dt),c1=cross(dt,dr),c2=cross(dr,ds);
   const V dc0=cross(d_ds,dt)+cross(ds,d_dt);
   const V dc1=cross(d_dt,dr)+cross(dt,d_dr);
   const V dc2=cross(d_dr,ds)+cross(dr,d_ds);
   const double jac=dot(dr,c0),djac=dot(d_dr,c0)+dot(dr,dc0);
   if(!(jac>0.))throw std::runtime_error("P10DD negative mechanical Tet10 Jacobian");
   const double dv=b.w*djac;
   std::array<p10c::Tensor,30> dB{};
   p10c::Tensor deps{};
   for(int a=0;a<10;++a){
    const auto& d=b.d[a];
    const V grad=(c0*d[0]+c1*d[1]+c2*d[2])/jac;
    const V dgrad=(dc0*d[0]+dc1*d[1]+dc2*d[2])/jac-
                   grad*(djac/jac);
    const double xyz[3]{dgrad.x,dgrad.y,dgrad.z};
    for(int dir=0;dir<3;++dir){
     const int local=3*a+dir,global=3*ids[a]+dir;
     dB[local]=p10c::displacement_strain_basis(xyz,dir);
     if(!step.constrained[global])for(int k=0;k<6;++k)
      deps[k]+=dB[local][k]*step.u[global];
    }
   }
   const auto law=qp.law.jvp(deps,0.,p10c::State{});
   double equilibrium=0.;
   for(int a=0;a<30;++a){
    const int global=3*ids[a/3]+a%3;
    if(step.constrained[global])continue;
    const double local_change=
      dv*edv::dot(qp.B[a],qp.law.response.sigma)+
      qp.volume*(edv::dot(dB[a],qp.law.response.sigma)+
                 edv::dot(qp.B[a],law.d_sigma));
    equilibrium+=lambda[std::size_t(global)]*local_change;
   }
   cell.part.equilibrium+=equilibrium;
   double history=0.;
   for(int a=0;a<6;++a){
    history+=futures[qid].e_d[a]*law.d_new.e_d[a];
    history+=futures[qid].e_v[a]*law.d_new.e_v[a];
   }
   cell.part.history+=history;
   if(!mask[e])continue;
   const auto src=p10f::point_source(qp,p10f::Kind::PeakMoment);
   const double dpoint=p10b::euclid_dot(src.lambda_sigma,law.d_sigma)+
     p10b::euclid_dot(src.lambda_next.e_d,law.d_new.e_d)+
     p10b::euclid_dot(src.lambda_next.e_v,law.d_new.e_v)+
     p10b::euclid_dot(src.direct_strain,deps);
   numerator+=qp.volume*src.value;
   out.observed_volume+=qp.volume;
   out.observed_dvolume+=dv;
   const std::size_t cell_id=index(x);
   dnumerator[cell_id]+=dv*src.value+qp.volume*dpoint;
   dnumerator_geometry[cell_id]+=dv*src.value;
   dnumerator_stress[cell_id]+=qp.volume*dpoint;
   dvolume[cell_id]+=dv;
  }
 }
 if(!(out.observed_volume>0.))
  throw std::runtime_error("P10DD no B6 observation volume");
 const double mean=numerator/out.observed_volume;
 for(std::size_t i=0;i<ncell;++i){
  out.cells[i].part.explicit_objective=weight*
   (dnumerator[i]-mean*dvolume[i])/out.observed_volume;
  out.cells[i].explicit_geometry=weight*
   (dnumerator_geometry[i]-mean*dvolume[i])/out.observed_volume;
  out.cells[i].explicit_stress=weight*
   dnumerator_stress[i]/out.observed_volume;
  expect_close(out.cells[i].explicit_geometry+out.cells[i].explicit_stress,
    out.cells[i].part.explicit_objective,"P10LG cell explicit split",1.e-10);
 }
 if(out.mechanical_qps()!=nq)
  throw std::runtime_error("P10DD mechanical QP count mismatch");
 return out;
}

inline Snapshot thermal_step(const Mesh& mesh,
                             const std::vector<V>& velocity,
                             const std::vector<double>& psi,
                             const std::vector<double>& theta,
                             const std::vector<double>& previous,
                             double dt,double ambient){
 const std::size_t nn=mesh.nodes.size();
 if(velocity.size()!=nn||psi.size()!=nn||theta.size()!=nn||
    previous.size()!=nn||!(dt>0.)||!std::isfinite(ambient))
  throw std::invalid_argument("P10DD thermal shape/QP dimensions");
 Snapshot out;
 const auto& qs=ice3d::p10l::quadrature();
 if(qs.size()!=64)throw std::runtime_error("P10DD expected 64 thermal QPs");
 for(const auto& tet:mesh.tets)for(const auto& q:qs){
  V dr{},ds{},dv{},drp{},dsp{},dvp{},x{};
  for(int i=0;i<10;++i){
   const V node=mesh.nodes[tet[i]],v=velocity[tet[i]];
   dr=dr+node*q.d[i][0];ds=ds+node*q.d[i][1];dv=dv+node*q.d[i][2];
   drp=drp+v*q.d[i][0];dsp=dsp+v*q.d[i][1];dvp=dvp+v*q.d[i][2];
   x=x+node*q.N[i];
  }
  bool axis=false;
  auto& cell=out.cells[index(x,&axis)];
  if(axis)++out.axis_qp;
  const V a=cross(ds,dv),b=cross(dv,dr),c=cross(dr,ds);
  const V da=cross(dsp,dv)+cross(ds,dvp);
  const V db=cross(dvp,dr)+cross(dv,drp);
  const V dc=cross(drp,ds)+cross(dr,dsp);
  const double det=dot(dr,a),ddet=dot(drp,a)+dot(dr,da);
  if(!(det>0.))throw std::runtime_error("P10DD negative thermal Tet10 Jacobian");
  const double w=q.w*det,dw=q.w*ddet;
  V grad_psi{},grad_theta{},dgrad_psi{},dgrad_theta{};
  double psi_q=0.,difference_q=0.;
  for(int i=0;i<10;++i){
   const std::size_t j=std::size_t(tet[i]);
   const auto& d=q.d[i];
   const V grad=(a*d[0]+b*d[1]+c*d[2])/det;
   const V dgrad=(da*d[0]+db*d[1]+dc*d[2])/det-grad*(ddet/det);
   grad_psi=grad_psi+grad*psi[j];
   grad_theta=grad_theta+grad*theta[j];
   dgrad_psi=dgrad_psi+dgrad*psi[j];
   dgrad_theta=dgrad_theta+dgrad*theta[j];
   psi_q+=q.N[i]*psi[j];
   difference_q+=q.N[i]*(theta[j]-previous[j]);
  }
  ++cell.thermal_qp;cell.thermal_volume+=w;
  cell.part.mass+=ice3d::p10l::rhocp*dw*psi_q*difference_q;
  cell.part.diffusion+=dt*ice3d::p10l::conductivity*(
      dw*dot(grad_psi,grad_theta)+
      w*(dot(dgrad_psi,grad_theta)+dot(grad_psi,dgrad_theta)));
 }
 // The top Robin term is a shape derivative of both the stiffness and load.
 // It is NOT a volumetric contribution and is kept in a distinct CSV row.
 Mesh velocity_mesh;
 velocity_mesh.nodes=velocity;
 for(const auto& face:mesh.faces)if(face.tag==2){
  for(auto ga:g4)for(auto gb:g4){
   const double r=ga.x,s=(1-r)*gb.x;
   const auto x=seval(mesh,face.nodes,r,s);
   const auto v=seval(velocity_mesh,face.nodes,r,s);
   const V normal=cross(x.du,x.dv);
   const V dnormal=cross(v.du,x.dv)+cross(x.du,v.dv);
   const double size=norm(normal);
   if(!(size>0.))throw std::runtime_error("P10DD zero top Tri6 area");
   const double weight=ga.w*gb.w*(1-r);
   const double darea=weight*dot(normal,dnormal)/size;
   const auto N=ice3d::p10l::face_shape(r,s);
   double psi_q=0.,theta_q=0.;
   for(int i=0;i<6;++i){
    const std::size_t j=std::size_t(face.nodes[i]);
    psi_q+=N[i]*psi[j];theta_q+=N[i]*theta[j];
   }
   ++out.top_qp;out.top_area+=weight*size;
   out.top_robin.robin+=dt*ice3d::p10l::robin*darea*
                       psi_q*(theta_q-ambient);
  }
 }
 if(out.thermal_qps()!=mesh.tets.size()*qs.size())
  throw std::runtime_error("P10DD thermal QP count mismatch");
 return out;
}

inline void write_csv(const fs::path& out_dir,const std::string& mesh_name,
                      int steps,int dt,const std::vector<Snapshot>& mechanics,
                      const std::vector<Snapshot>& thermals,
                      const Parts& reference){
 if(steps<6||steps>36||steps*dt!=900||mechanics.size()!=std::size_t(steps)||
    thermals.size()!=std::size_t(steps))
  throw std::invalid_argument("P10DD requires 6x150s and every step populated");
 std::ofstream data(out_dir/"P10DD_SIGNED_R_THETA_PHI_T.csv");
 std::ofstream audit(out_dir/"P10DD_FULL4D_CLOSURE_AUDIT.csv");
 std::ofstream split(out_dir/"P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv");
 if(!data||!audit||!split)throw std::runtime_error("P10LG CSV creation failure");
 data<<std::setprecision(17);audit<<std::setprecision(17);
 split<<std::setprecision(17);
 split<<"mesh,step,time_end_s,radial_bin,mu_bin,phi_bin,"
       "explicit_geometry_normalization_per_m,explicit_stress_chain_per_m,"
       "explicit_sum_per_m\n";
 data<<"mesh,mode,functional,step,time_start_s,time_end_s,region,"
       "radial_bin,mu_bin,phi_bin,r_lower_mm,r_upper_mm,"
       "theta_lower_rad,theta_upper_rad,phi_lower_rad,phi_upper_rad,"
       "mech_explicit_per_m,mech_equilibrium_per_m,mech_history_per_m,"
       "thermal_mass_per_m,thermal_diffusion_per_m,thermal_robin_per_m,"
       "mechanical_total_per_m,thermal_total_per_m,total_per_m,"
       "mechanical_qp,thermal_qp,mechanical_volume_m3,thermal_volume_m3,"
       "top_robin_qp,top_robin_area_m2\n";
 audit<<"mesh,step,time_end_s,mechanical_qp,thermal_qp,axis_mech_qp,"
        "axis_thermal_qp,top_qp,top_area_m2,"
        "mech_explicit_per_m,mech_equilibrium_per_m,mech_history_per_m,"
        "thermal_mass_per_m,thermal_diffusion_per_m,thermal_robin_per_m,"
        "mechanical_total_per_m,thermal_total_per_m,total_per_m\n";
 Parts sum{};
 double split_geometry_sum=0.,split_stress_sum=0.;
 for(int step=1;step<=steps;++step){
  const auto& m=mechanics[std::size_t(step-1)];
  const auto& h=thermals[std::size_t(step-1)];
  const auto cm=m.sum(),ct=h.sum();
  if(m.top_qp||h.mechanical_qps()||m.thermal_qps()||
     h.top_robin.mechanical()!=0.||m.top_robin.total()!=0.)
   throw std::runtime_error("P10DD mixed mechanical/thermal partitions");
  const auto combined=[&](const Parts& p,const char* region,
      int ir,int im,int ip,double rlo,double rhi,double tlo,double thi,
      double plo,double phi,std::size_t mqp,std::size_t hqp,double mv,double hv,
      std::size_t top_qp,double area){
   data<<mesh_name<<",R,jpeak,"<<step<<','<<(step-1)*dt<<','<<step*dt
       <<','<<region<<','<<ir<<','<<im<<','<<ip<<','<<rlo<<',';
   if(ir>=0&&ir<nrad-1)data<<rhi;
   data<<','<<tlo<<','<<thi<<','<<plo<<','<<phi<<','
       <<p.explicit_objective<<','<<p.equilibrium<<','<<p.history<<','
       <<p.mass<<','<<p.diffusion<<','<<p.robin<<','<<p.mechanical()
       <<','<<p.thermal()<<','<<p.total()<<','<<mqp<<','<<hqp<<','
       <<mv<<','<<hv<<','<<top_qp<<','<<area<<'\n';
  };
  for(int ir=0;ir<nrad;++ir)for(int im=0;im<nmu;++im)
   for(int ip=0;ip<nphi;++ip){
    const std::size_t id=std::size_t((ir*nmu+im)*nphi+ip);
    Parts p=m.cells[id].part;p.add(h.cells[id].part);
    const auto& mc=m.cells[id];
    expect_close(mc.explicit_geometry+mc.explicit_stress,
      mc.part.explicit_objective,"P10LG writer cell closure",1.e-10);
    split<<mesh_name<<','<<step<<','<<step*dt<<','
         <<ir<<','<<im<<','<<ip<<','<<mc.explicit_geometry<<','
         <<mc.explicit_stress<<','<<mc.part.explicit_objective<<'\n';
    split_geometry_sum+=mc.explicit_geometry;
    split_stress_sum+=mc.explicit_stress;
    const double mu_low=-1.+2.*im/nmu,mu_high=-1.+2.*(im+1)/nmu;
    combined(p,"VOLUME",ir,im,ip,radial_lower_mm[std::size_t(ir)],
      ir+1<nrad?radial_lower_mm[std::size_t(ir+1)]:0.,
      std::acos(mu_high),std::acos(mu_low),
      -pi+2.*pi*ip/nphi,-pi+2.*pi*(ip+1)/nphi,
      m.cells[id].mechanical_qp,h.cells[id].thermal_qp,
      m.cells[id].mechanical_volume,h.cells[id].thermal_volume,0,0.);
   }
  combined(h.top_robin,"TOP_ROBIN",-1,-1,-1,0.,0.,0.,0.,0.,0.,
           0,0,0.,0.,h.top_qp,h.top_area);
  Parts step_sum=cm;step_sum.add(ct);sum.add(step_sum);
  audit<<mesh_name<<','<<step<<','<<step*dt<<','<<m.mechanical_qps()
       <<','<<h.thermal_qps()<<','<<m.axis_qp<<','<<h.axis_qp<<','
       <<h.top_qp<<','<<h.top_area<<','<<step_sum.explicit_objective
       <<','<<step_sum.equilibrium<<','<<step_sum.history<<','
       <<step_sum.mass<<','<<step_sum.diffusion<<','<<step_sum.robin<<','
       <<step_sum.mechanical()<<','<<step_sum.thermal()<<','
       <<step_sum.total()<<'\n';
 }
 expect_close(split_geometry_sum+split_stress_sum,
   sum.explicit_objective,"P10LG all-step two-term closure",1.e-10);
 expect_close(sum.explicit_objective,reference.explicit_objective,"all-step explicit");
 expect_close(sum.equilibrium,reference.equilibrium,"all-step equilibrium");
 expect_close(sum.history,reference.history,"all-step history");
 expect_close(sum.thermal(),reference.thermal(),"all-step thermal");
 expect_close(sum.total(),reference.total(),"all-step total");
 data.close();audit.close();split.close();
 if(!split)  throw std::runtime_error("P10LG incomplete split CSV write");
 if(!data||!audit)throw std::runtime_error("P10DD incomplete CSV write");
 std::cout<<"P10LG_TWO_TERM_EXPLICIT_CLOSURE_OK geometric="<<split_geometry_sum
          <<" stress="<<split_stress_sum<<" total="<<sum.explicit_objective
          <<" rows="<<steps*ncell<<"\n"<<std::flush;
 std::cout<<"P10DD_FULL4D_CLOSURE_OK mesh="<<mesh_name
          <<" steps="<<steps<<" bins_per_step="<<ncell
          <<" top_rows="<<steps<<" output_rows="<<steps*(ncell+1)
          <<" mechanical="<<sum.mechanical()<<" thermal="<<sum.thermal()
          <<" total="<<sum.total()<<" exact_global_reference=1\n"<<std::flush;
}
} // namespace ice3d::p10dd
