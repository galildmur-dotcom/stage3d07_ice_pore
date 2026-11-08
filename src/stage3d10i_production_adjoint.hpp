// Stage 3D-10I — checkpoint-replayed, fully discrete adjoint driven by the
// ACTUAL production spatial_reology.cpp nonlinear_step and P10H snapshots.
// Inclusion contract: inside anonymous namespace of P10H production test,
// after Tiny, check, etc. This is a 2-Tet10 B6 preflight, not pore H0 yet.
#pragma once
#include <sstream>
#include <chrono>

namespace p10i {
namespace f10=ice3d::p10f;
namespace a10=ice3d::p10c;
namespace e10=ice3d::p10e;

constexpr int N=12,Window=4;
constexpr double Dt=150.;
const std::array<f10::Kind,3> kinds{f10::Kind::J6,f10::Kind::PeakMoment,f10::Kind::Energy};
const std::array<const char*,3> names{"j6","jpeak","jen"};

struct Problem {
 Tiny geometry;
 std::vector<GaussQ> quadrature;
 Setting setting;
 double temperature_param=0.;
 std::vector<uint8_t> bc;
 std::shared_ptr<const BCSRTopology> topology;
 std::shared_ptr<const e10::ReverseGraph> reverse;

 Problem(double shape,double temp,const std::string& law,const std::string& mod)
  :geometry(shape),quadrature(volume_q(3)),temperature_param(temp),
   bc(geometry.bc){
  setting.name=law;setting.mod=mod;setting.quad=3;
  setting.newtonTol=5e-11;setting.cgTol=3e-12;
  setting.extraFunctionals=true;
  topology=build_bcsr_topology(geometry.m);
  BCSR graph;graph.set_topology(topology);
  reverse=std::make_shared<const e10::ReverseGraph>(graph);
 }

 std::vector<double> thermal(int n)const{
  auto t=temperatures(geometry.m,n);
  const auto d=temperature_direction(n);
  for(size_t i=0;i<t.size();++i)t[i]+=temperature_param*d[i];
  return t;
 }
 std::vector<double> temperature_direction(int n)const{
  std::vector<double> d(geometry.m.nodes.size());
  for(size_t i=0;i<d.size();++i)
   d[i]=(.9+.12*std::cos(.27*double(i)))*(.6+.4*std::sin(.2*n));
  return d;
 }
 a10::Step make_step(const std::vector<double>& T,
                    const std::vector<State>& old,
                    const std::vector<double>& u)const{
  return a10::Step(geometry.m,quadrature,T,old,Dt,u,bc,
                   setting.mod=="VAR"?Modulus::VAR:Modulus::CONST,
                   ice3d::p10b::Controls{setting.name!="E",setting.name=="EDV"});
 }
};

struct Silent {
 struct NullStream:std::streambuf {
  int overflow(int c)override{return traits_type::not_eof(c);}
 } nullbuf;
 std::streambuf* old;
 Silent():old(std::cerr.rdbuf(&nullbuf)){}
 ~Silent(){std::cerr.rdbuf(old);}
};

void configure_production(){
 p06.optimized=false;p06.parallelAssembly=false;
 p06.graph.reset();p06.geometry.clear();p06.inB6.clear();
 p06.gaugeMass.clear();p06.gaugeVolume=0.;
}

Field initial(const Problem& p){
 Field field;
 field.u.assign(p.geometry.m.nodes.size()*3,0.);
 field.qstate.resize(p.geometry.m.tets.size()*p.quadrature.size());
 return field;
}

// The zero-mean gauge is a rigid translation. Re-pin the whole u-field by
// ONE uniform z shift before constructing P10C, whose Dirichlet DOFs are zero.
// For a constant z shift, the strain and all three functionals are invariant.
std::vector<double> repin(const std::vector<double>& u,const Problem& p){
 std::vector<double> copy=u;
 const double offset=u[2];
 for(size_t i=0;i<p.geometry.m.nodes.size();++i)copy[3*i+2]-=offset;
 for(size_t i=0;i<p.bc.size();++i)if(p.bc[i])
  check(std::abs(copy[i])<5e-12,"P10I unexpected nonzero constrained DOF after gauge removal");
 return copy;
}

struct Frame {
 std::vector<double> u,T;
 std::vector<State> previous;
};
Frame one_step(const Problem& p,int n,Field& field,bool with_gauge,
               std::array<double,3>* instant=nullptr){
 p06.clear_step();
 const auto T=p.thermal(n);
 Frame frame;
 frame.T=T;frame.previous=field.qstate;
 Work w;
 (void)nonlinear_step(p.geometry.m,p.quadrature,T,field,Dt,
                       p.setting,p.bc,w);
 frame.u=repin(field.u,p);
 if(instant){
  (*instant)[0]=w.j6;
  (*instant)[1]=w.peakPower6;
  (*instant)[2]=w.energy6/ice3d::p09b::energy_ref_pa;
 }
 if(with_gauge)(void)zeroMeanZ(p.geometry.m,p.quadrature,field);
 field.lastTime=n*Dt;
 return frame;
}

struct Forward{
 std::array<double,3> objective{};
 std::array<fs::path,N/Window+1> snapshots;
};

Forward forward(const Problem& p,bool with_gauge,const fs::path& directory={}){
 configure_production();
 const bool store=!directory.empty();
 Field field=initial(p);
 Forward out;
 std::array<double,3> moment{};
 for(size_t j=0;j<kinds.size();++j)
  moment[j]=.5/N*f10::initial_time_value(kinds[j]);
 if(store){
  ice3d::p10h::retain(directory,p.geometry.m,p.setting,field,0);
  out.snapshots[0]=ice3d::p10h::named_file(directory,0);
 }
 for(int n=1;n<=N;++n){
  std::array<double,3> instant{};
  (void)one_step(p,n,field,with_gauge,&instant);
  for(size_t j=0;j<kinds.size();++j)
   moment[j]+=(n==N?.5:1.)/N*instant[j];
  if(store&&n%Window==0){
   ice3d::p10h::retain(directory,p.geometry.m,p.setting,field,n);
   out.snapshots[size_t(n/Window)]=ice3d::p10h::named_file(directory,n);
  }
 }
 for(size_t j=0;j<kinds.size();++j)
  out.objective[j]=(kinds[j]==f10::Kind::PeakMoment)
          ?std::pow(moment[j],1./f10::Parameters{}.peak_p):moment[j];
 return out;
}

double rel(double x,double y){
 return std::abs(x-y)/std::max({1e-7,std::abs(x),std::abs(y)});
}

struct Gradients {
 double temperature=0,shape=0,maximum_equilibrium=0;
 int replayed_steps=0,max_window=0;
};

Gradients backward(const Problem& p,const Forward& data,
                   f10::Kind kind,double J,bool propagate_history=true){
 configure_production();
 Gradients grad;
 const size_t nq=p.geometry.m.tets.size()*p.quadrature.size();
 std::vector<State> future(nq);
 constexpr double geom_step=2e-4;
 const Tiny gp(geom_step),gm(-geom_step);
 const double power=f10::Parameters{}.peak_p;
 const double moment=kind==f10::Kind::PeakMoment?std::pow(J,power):1.;
 const double chain=kind==f10::Kind::PeakMoment
     ?std::pow(moment,1./power-1.)/power:1.;
 for(int segment=N/Window-1;segment>=0;--segment){
  const int first=segment*Window,last=first+Window;
  Field field=ice3d::p10h::recover(data.snapshots[size_t(segment)].parent_path().parent_path(),
      p.geometry.m,p.setting,first,first*Dt,p.quadrature.size());
  std::vector<Frame> frames;
  frames.reserve(Window);
  for(int n=first+1;n<=last;++n){
   frames.push_back(one_step(p,n,field,true));
   ++grad.replayed_steps;
  }
  grad.max_window=std::max(grad.max_window,int(frames.size()));
  const Field endpoint=ice3d::p10h::recover(
     data.snapshots[size_t(segment+1)].parent_path().parent_path(),
     p.geometry.m,p.setting,last,last*Dt,p.quadrature.size());
  identical_field(field,endpoint);
  for(int j=int(frames.size())-1;j>=0;--j){
   const int n=first+j+1;
   const auto& frame=frames[size_t(j)];
   const auto step=p.make_step(frame.T,frame.previous,frame.u);
   const auto src=f10::evaluate(step,kind);
   const double coefficient=chain*((n==N)?.5:1.)/N;
   a10::Output lambda;
   lambda.residual.assign(frame.u.size(),0.);
   lambda.next=future;
   const auto memory=step.vjp(lambda);
   std::vector<double> rhs(frame.u.size());
   for(size_t i=0;i<rhs.size();++i)
    rhs[i]=-(coefficient*src.displacement[i]+memory.displacement[i]);
   auto K=e10::assemble_tangent_bcsr(p.geometry.m,step,p.topology);
   const auto linear=e10::solve_bicgstab(K,p.bc,rhs,true,2e-13,400,p.reverse.get());
   lambda.residual=linear.x;
   const auto back=step.vjp(lambda);
   double square=0,reference=0;
   for(size_t i=0;i<rhs.size();++i){
    const double source=coefficient*src.displacement[i];
    square+=std::pow(back.displacement[i]+source,2);
    reference+=source*source;
   }
   grad.maximum_equilibrium=std::max(grad.maximum_equilibrium,
      std::sqrt(square)/std::max(1.,std::sqrt(reference)));
   const auto dT=p.temperature_direction(n);
   for(size_t i=0;i<dT.size();++i)
    grad.temperature+=(back.temperature[i]+coefficient*src.temperature[i])*dT[i];

   // Shape partial at FROZEN (u,T,z_old), including residual, implicit EDV
   // state update, and explicit volume-normalized functional value.
   const a10::Step sp(gp.m,p.quadrature,frame.T,frame.previous,Dt,frame.u,
                p.bc,p.setting.mod=="VAR"?Modulus::VAR:Modulus::CONST,
                ice3d::p10b::Controls{p.setting.name!="E",p.setting.name=="EDV"});
   const a10::Step sm(gm.m,p.quadrature,frame.T,frame.previous,Dt,frame.u,
                p.bc,p.setting.mod=="VAR"?Modulus::VAR:Modulus::CONST,
                ice3d::p10b::Controls{p.setting.name!="E",p.setting.name=="EDV"});
   const auto op=sp.evaluate(),om=sm.evaluate();
   const double fp=f10::evaluate(sp,kind).value,fm=f10::evaluate(sm,kind).value;
   grad.shape+=coefficient*(fp-fm)/(2*geom_step);
   for(size_t i=0;i<lambda.residual.size();++i)
    grad.shape+=lambda.residual[i]*(op.residual[i]-om.residual[i])/(2*geom_step);
   for(size_t i=0;i<nq;++i)for(int k=0;k<6;++k){
    grad.shape+=future[i].e_d[k]*(op.next[i].e_d[k]-om.next[i].e_d[k])/(2*geom_step);
    grad.shape+=future[i].e_v[k]*(op.next[i].e_v[k]-om.next[i].e_v[k])/(2*geom_step);
   }
   for(size_t i=0;i<nq;++i)for(int k=0;k<6;++k){
    future[i].e_d[k]=back.previous[i].e_d[k]+coefficient*src.previous[i].e_d[k];
    future[i].e_v[k]=back.previous[i].e_v[k]+coefficient*src.previous[i].e_v[k];
   }
   if(!propagate_history)std::fill(future.begin(),future.end(),State{});
  }
 }
 return grad;
}

int run_tests(){
 Silent silence;
 const auto timestamp=std::chrono::steady_clock::now().time_since_epoch().count();
 const fs::path root=fs::temp_directory_path()/
       ("ice3d_p10i_prod_"+std::to_string(timestamp));
 check(fs::create_directory(root),"P10I temporary directory collision");
 struct Cleanup {
  fs::path path;
  ~Cleanup(){std::error_code error;fs::remove_all(path,error);}
 } cleanup{root};
 const std::array<std::pair<std::string,std::string>,6> models{{
  {"E","CONST"},{"E","VAR"},{"ED","CONST"},{"ED","VAR"},
  {"EDV","CONST"},{"EDV","VAR"}
 }};
 constexpr double temp_fd=2e-4,shape_fd=5e-4;
 std::array<double,3> max_T{},max_shape{};
 double max_gauge=0,max_adjoint_equilibrium=0,ablation_difference=0;
 int comparisons=0,replayed=0,max_window=0;
 for(size_t i=0;i<models.size();++i){
  const auto& [law,mod]=models[i];
  const Problem normal(0,0,law,mod),
   tp(0,+temp_fd,law,mod),tm(0,-temp_fd,law,mod),
   gp(+shape_fd,0,law,mod),gm(-shape_fd,0,law,mod);
  const auto folder=root/("model_"+std::to_string(i));
  fs::create_directory(folder);
  const auto path=forward(normal,true,folder);
  const auto without_gauge=forward(normal,false);
  const auto Jtp=forward(tp,true),Jtm=forward(tm,true);
  const auto Jgp=forward(gp,true),Jgm=forward(gm,true);
  for(size_t j=0;j<kinds.size();++j){
   max_gauge=std::max(max_gauge,rel(path.objective[j],without_gauge.objective[j]));
   const auto gradient=backward(normal,path,kinds[j],path.objective[j]);
   const double dTfd=(Jtp.objective[j]-Jtm.objective[j])/(2*temp_fd);
   const double dSfd=(Jgp.objective[j]-Jgm.objective[j])/(2*shape_fd);
   const double T_error=rel(gradient.temperature,dTfd);
   const double S_error=rel(gradient.shape,dSfd);
   max_T[j]=std::max(max_T[j],T_error);
   max_shape[j]=std::max(max_shape[j],S_error);
   max_adjoint_equilibrium=std::max(max_adjoint_equilibrium,
                                    gradient.maximum_equilibrium);
   replayed+=gradient.replayed_steps;
   max_window=std::max(max_window,gradient.max_window);
   check(T_error<2e-4,"P10I production temperature adjoint/FD failed "+
                         std::string(names[j])+" "+law+"_"+mod);
   check(S_error<2e-4,"P10I production geometry adjoint/FD failed "+
                         std::string(names[j])+" "+law+"_"+mod);
   if(i==5&&j==0){
    const auto missing_history=backward(normal,path,kinds[j],path.objective[j],false);
    ablation_difference=std::max(
       rel(missing_history.temperature,dTfd),
       rel(missing_history.shape,dSfd));
   }
   ++comparisons;
  }
 }
 check(max_gauge<1e-10,"P10I zeroMeanZ changed physical functionals");
 check(replayed==int(models.size()*kinds.size()*N),"P10I replay count mismatch");
 check(max_window==Window,"P10I window bound failed");
 check(max_adjoint_equilibrium<1e-8,"P10I adjoint equilibrium residual failed");
 check(ablation_difference>1e-3,"P10I history ablation had no measurable effect");
 std::cout<<std::scientific<<std::setprecision(12)
  <<"P10I_PRODUCTION_ADJOINT_OK models="<<models.size()
  <<" functionals="<<kinds.size()<<" cases="<<comparisons
  <<" replayed_steps="<<replayed<<" max_window="<<max_window
  <<" j6_temp_FD_rel="<<max_T[0]<<" j6_shape_FD_rel="<<max_shape[0]
  <<" jpeak_temp_FD_rel="<<max_T[1]<<" jpeak_shape_FD_rel="<<max_shape[1]
  <<" jen_temp_FD_rel="<<max_T[2]<<" jen_shape_FD_rel="<<max_shape[2]
  <<" gauge_functional_rel="<<max_gauge
  <<" dropped_history_rel="<<ablation_difference
  <<" adjoint_equilibrium_rel="<<max_adjoint_equilibrium<<'\n';
 return 0;
}
} // namespace p10i
