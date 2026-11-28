// P10BX integration-wrapper unit: exact P10L CSR and P10BW QP comparison.
// No forward FEM, no thermal adjoint solve, no Windows invocation.
// Reuse the already vetted P10BW synthetic mesh/test fixture unchanged.
// Its original implicit `return 0` applies only to the real main name.
// The renamed, never-called fixture entry would otherwise emit a false
// -Wreturn-type warning; scope the suppression to this inclusion only.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreturn-type"
#define main p10bw_reference_unit_entry_not_called
#include "P10BW_thermal_qp_native_unit.cpp"
#undef main
#pragma GCC diagnostic pop
#include "stage3d10bx_thermal_step_hook.hpp"

int main(){
 try{
  const Mesh mesh=synthetic_mesh();
  int tests=0;double max_abs_error=0.,max_relative=0.;
  for(const auto& [mode,dt]:
     std::array<std::pair<std::string_view,int>,7>{{
       {"R",150},{"R",75},{"R",50},{"R",25},
       {"tz",150},{"y20",150},{"top",75}}}){
   const auto velocity=shape_velocity(mesh,mode);
   std::vector<double> theta(mesh.nodes.size()),previous(mesh.nodes.size()),
                       psi(mesh.nodes.size());
   for(std::size_t i=0;i<mesh.nodes.size();++i){
    const V& x=mesh.nodes[i];
    theta[i]=-.9+2.2*x.z+0.17*std::sin(double(i)*.41);
    previous[i]=-.5+1.3*x.z+0.11*std::cos(double(i)*.23);
    psi[i]=.3+0.08*std::cos(double(i)*.37);
   }
   const auto operator_pair=H::assemble(mesh,velocity,double(dt));
   const auto audit=ice3d::p10bx::audit_step(mesh,velocity,
      operator_pair.shape,psi,theta,previous,double(dt),-2.1);
   const double reference=contract_primal(operator_pair.shape,psi,theta,
                                          previous,double(dt),-2.1);
   check_close(reference,audit.csr_total,"P10BX P10P-style CSR sum",1e-11,1e-9);
   check_close(audit.csr_total,audit.qp.total().total(),
               "P10BX QP versus exact CSR",1e-10,1e-9);
   if(audit.qp.thermal_qp_count()!=mesh.tets.size()*H::quadrature().size())
    throw std::runtime_error("P10BX synthetic thermal QP count mismatch");
   max_abs_error=std::max(max_abs_error,audit.absolute_error);
   max_relative=std::max(max_relative,audit.relative_scaled);
   std::cout<<std::scientific<<std::setprecision(12)
    <<"P10BX_STEP_UNIT_OK mode="<<mode<<" dt_s="<<dt
    <<" csr_total="<<audit.csr_total
    <<" qp_total="<<audit.qp.total().total()
    <<" abs_error="<<audit.absolute_error
    <<" tolerance="<<audit.tolerance<<'\n';
   ++tests;
  }
  bool rejected=false;
  try{
   std::vector<double> wrong(mesh.nodes.size()-1,0.);
   const auto velocity=shape_velocity(mesh,"R");
   const auto op=H::assemble(mesh,velocity,150.);
   (void)ice3d::p10bx::audit_step(mesh,velocity,op.shape,wrong,
       std::vector<double>(mesh.nodes.size(),0.),
       std::vector<double>(mesh.nodes.size(),0.),150.,-2.1);
  }catch(const std::invalid_argument&){rejected=true;}
  if(!rejected)throw std::runtime_error("P10BX failed negative input check");
  ++tests;
  std::cout<<"P10BX_THERMAL_STEP_NATIVE_UNIT_OK tests="<<tests
           <<" max_abs_error="<<max_abs_error
           <<" max_scaled_rel="<<max_relative
           <<" reference_operator=EXACT_P10L"
           <<" physical_FEM_runs=0\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P10BX_NATIVE_STOP reason="<<e.what()<<'\n';
  return 2;
 }
}
