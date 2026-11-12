// Independent small-element verification of Stage3D10V geometry derivatives.
// The production Step is evaluated at X +/- hV only as a reference, never
// by the directional() implementation under test.
#define STAGE3D06_LIBRARY
#include "mechanical.cpp"
#include "stage3d10v_analytic_shape.hpp"
#include <iomanip>
#include <random>

namespace {
using ice3d::p10c::Step;
using ice3d::p10c::State;
using ice3d::p10f::Kind;

void check(bool ok,const char* what){
 if(!ok)throw std::runtime_error(std::string("P10V: ")+what);
}
double norm_vector(const std::vector<double>& x){
 double v=0.;for(double a:x)v+=a*a;return std::sqrt(v);
}
double error_vector(const std::vector<double>& a,const std::vector<double>& b){
 check(a.size()==b.size(),"vector size mismatch");
 auto d=a;
 for(size_t i=0;i<d.size();++i)d[i]-=b[i];
 return norm_vector(d)/std::max({1e-12,norm_vector(a),norm_vector(b)});
}
double error_state(const std::vector<State>& a,const std::vector<State>& b){
 check(a.size()==b.size(),"history size mismatch");
 double e=0.,refa=0.,refb=0.;
 for(size_t i=0;i<a.size();++i)for(int j=0;j<6;++j){
  for(const auto& v:std::array<std::pair<double,double>,2>{{
        {a[i].e_d[j],b[i].e_d[j]},{a[i].e_v[j],b[i].e_v[j]}}}){
   e+=(v.first-v.second)*(v.first-v.second);
   refa+=v.first*v.first;refb+=v.second*v.second;
  }
 }
 return std::sqrt(e)/std::max({1e-12,std::sqrt(refa),std::sqrt(refb)});
}
double relative(double a,double b){
 return std::abs(a-b)/std::max({1e-9,std::abs(a),std::abs(b)});
}
double random_value(std::mt19937_64& gen,double a){
 return std::uniform_real_distribution<double>(-a,a)(gen);
}
Mesh curved_tet(){
 Mesh m;
 m.nodes={V{0.,0.,0.},V{.0035,0.,0.},V{0.,.003,0.},V{0.,0.,.0037},
   V{.00175,.00002,0.},V{.00175,.0015,.00003},
   V{0.,.0015,-.00002},V{-.00003,0.,.00185},
   V{.00175,.00001,.00185},V{.00002,.0015,.00185}};
 m.tets.push_back(Tet{0,1,2,3,4,5,6,7,8,9});
 // The second element is deliberately outside the observation mask, so the
 // test also exercises B6 normalization rather than full-domain averaging.
 const Tet first=m.tets.front();
 for(int a=0;a<10;++a)m.nodes.push_back(m.nodes[a]+V{.005,0,0});
 Tet second{};
 for(int a=0;a<10;++a)second[a]=first[a]+10;
 m.tets.push_back(second);
 return m;
}
Mesh shifted(const Mesh& mesh,const std::vector<V>& vel,double h){
 Mesh result=mesh;
 for(size_t j=0;j<vel.size();++j)result.nodes[j]=result.nodes[j]+vel[j]*h;
 return result;
}
double masked_objective(const Step& step,Kind kind,
                        const std::vector<uint8_t>& mask,size_t nquad){
 double numerator=0.,volume=0.;
 for(size_t q=0;q<step.qps.size();++q)if(mask[q/nquad]){
  const auto& qp=step.qps[q];
  volume+=qp.volume;
  numerator+=qp.volume*ice3d::p10f::point_source(qp,kind).value;
 }
 check(volume>0.,"empty observation in numerical reference");
 return numerator/volume;
}
void test_velocity(){
 constexpr double r=.001;
 const V centre{0.,0.,.03};
 const auto R=ice3d::p10v::velocity_at(centre+V{r,0,0},"R",.005);
 const auto tz=ice3d::p10v::velocity_at(centre+V{r,0,0},"tz",.005);
 const auto y20=ice3d::p10v::velocity_at(centre+V{r,0,0},"y20",.005);
 const double Y=-std::sqrt(5./(16.*PI));
 check(norm(R-V{1,0,0})<1e-13,"radius speed at pore wall");
 check(norm(tz-V{0,0,1})<1e-13,"translation speed at pore wall");
 check(norm(y20-V{Y,0,0})<1e-13,"y20 speed at equator");
 const auto half=ice3d::p10v::velocity_at(centre+V{.003,0,0},"R",.005);
 check(norm(half-V{.5,0,0})<1e-13,"smoothstep support midpoint");
 const auto outside=ice3d::p10v::velocity_at(centre+V{.006,0,0},"R",.005);
 check(norm(outside)==0.,"no outer velocity");
}
}

int main(){try{
 test_velocity();
 const Mesh mesh=curved_tet();
 const auto quad=volume_q(3);
 const std::vector<uint8_t> mask{1,0};
 const std::vector<Kind> kinds{Kind::J6,Kind::PeakMoment,
                               Kind::Energy,Kind::SafetySmooth};
 std::mt19937_64 gen(20261110);
 std::vector<double> u(mesh.nodes.size()*3),T(mesh.nodes.size());
 std::vector<uint8_t> bc(u.size(),0);
 for(int dir=0;dir<3;++dir)bc[dir]=1;
 for(double& x:u)x=random_value(gen,3.e-8);
 for(double& x:T)x=-5.+random_value(gen,1.5);
 std::vector<V> vel(mesh.nodes.size());
 for(auto& v:vel)v=V{random_value(gen,.15),random_value(gen,.15),
                        random_value(gen,.15)};
 double max_r=0.,max_h=0.,max_j=0.;
 for(const auto flags:std::array{ice3d::p10b::Controls{false,false},
                                  ice3d::p10b::Controls{true,false},
                                  ice3d::p10b::Controls{true,true}}){
  std::vector<State> old(mesh.tets.size()*quad.size());
  for(auto& q:old){
   for(int i=0;i<6;++i){
    q.e_d[i]=flags.delayed?random_value(gen,2.e-7):0.;
    q.e_v[i]=flags.viscous?random_value(gen,2.e-7):0.;
   }
   q.e_d=ice3d::edv::deviator(q.e_d);
   q.e_v=ice3d::edv::deviator(q.e_v);
  }
  for(const auto modulus:std::array{ice3d::p10b::Modulus::CONST,
                                      ice3d::p10b::Modulus::VAR}){
   const Step baseline(mesh,quad,T,old,150.,u,bc,modulus,flags);
   const auto exact=ice3d::p10v::directional(mesh,quad,baseline,vel,mask,kinds);
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
   // Verify exact QP shell reconstruction independently of the production
   // transient solver. Alternate bins within each curved Tet10 element.
   std::vector<std::uint8_t> shells(baseline.qps.size());
   for(std::size_t q=0;q<shells.size();++q)shells[q]=q%2;
   std::vector<std::vector<double>> lambdas(kinds.size(),
                                      std::vector<double>(u.size()));
   std::vector<const std::vector<double>*> adjoints;
   for(std::size_t k=0;k<kinds.size();++k){
    for(std::size_t i=0;i<u.size();++i)
     lambdas[k][i]=1.e4*std::sin(.4*double(i+1)+double(k));
    adjoints.push_back(&lambdas[k]);
   }
   const ice3d::p10v::ShellAudit audit{shells,adjoints,2};
   const auto split=ice3d::p10v::directional(mesh,quad,baseline,
                                              vel,mask,kinds,&audit);
   check(error_vector(split.operator_change.residual,
                      exact.operator_change.residual)<1.e-13,
         "shell audit modified global residual derivative");
   for(std::size_t k=0;k<kinds.size();++k){
    const auto& obj=split.objective_by_shell[k];
    const auto& eq=split.equilibrium_by_shell[k];
    const double reconstructed=obj[0]+obj[1];
    check(std::abs(reconstructed-exact.objective[k])<=
          1.e-8*std::max({1.e-12,std::abs(obj[0]),std::abs(obj[1]),
                           std::abs(exact.objective[k])}),
          "normalized objective shell partition");
    double global_eq=0.;
    for(std::size_t i=0;i<u.size();++i)
     global_eq+=lambdas[k][i]*exact.operator_change.residual[i];
    check(std::abs(eq[0]+eq[1]-global_eq)<=
          1.e-12*std::max({1.e-12,std::abs(eq[0]),std::abs(eq[1]),
                           std::abs(global_eq)}),
          "adjoint equilibrium shell partition");
   }
#endif
   for(const double h:std::array{2.e-6,1.e-6,5.e-7}){
    const auto mp=shifted(mesh,vel,h),mm=shifted(mesh,vel,-h);
    const Step plus(mp,quad,T,old,150.,u,bc,modulus,flags);
    const Step minus(mm,quad,T,old,150.,u,bc,modulus,flags);
    const auto op=plus.evaluate(),om=minus.evaluate();
    auto fdr=op.residual;
    auto fdh=op.next;
    for(size_t i=0;i<fdr.size();++i)
     fdr[i]=(op.residual[i]-om.residual[i])/(2*h);
    for(size_t iq=0;iq<fdh.size();++iq)for(int j=0;j<6;++j){
     fdh[iq].e_d[j]=(op.next[iq].e_d[j]-om.next[iq].e_d[j])/(2*h);
     fdh[iq].e_v[j]=(op.next[iq].e_v[j]-om.next[iq].e_v[j])/(2*h);
    }
    const auto er=error_vector(exact.operator_change.residual,fdr);
    const auto eh=error_state(exact.operator_change.next,fdh);
    max_r=std::max(max_r,er);max_h=std::max(max_h,eh);
    for(size_t k=0;k<kinds.size();++k){
     const double jp=masked_objective(plus,kinds[k],mask,quad.size());
     const double jm=masked_objective(minus,kinds[k],mask,quad.size());
     max_j=std::max(max_j,relative(exact.objective[k],(jp-jm)/(2*h)));
    }
   }
  }
 }
 std::cout<<std::scientific<<std::setprecision(10)
   <<"P10V_ANALYTIC_SHAPE_UNIT residual_rel="<<max_r
   <<" history_rel="<<max_h<<" functional_rel="<<max_j
   <<" models=6 functionals=4 quadrature_points="<<quad.size()<<'\n';
 check(max_r<2e-4,"analytic mechanical residual vs independent FD");
 check(max_h<2e-4,"analytic EDV history vs independent FD");
 check(max_j<2e-4,"analytic normalized functional vs independent FD");
 std::cout<<"P10V_ANALYTIC_SHAPE_UNIT_OK\n";
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
 std::cout<<"P10Y_ANALYTIC_SHELL_UNIT_OK models=6 functionals=4 bins=2\n";
#endif
 return 0;
}catch(const std::exception& e){
 std::cerr<<"P10V_ANALYTIC_SHAPE_UNIT_FAIL "<<e.what()<<'\n';
 return 2;
}}
