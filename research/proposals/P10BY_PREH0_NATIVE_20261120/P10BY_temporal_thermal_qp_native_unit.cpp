// P10BY: independent all-step diagnostic unit; NEVER runs physical H0/H2.
// Exact P10L operators + synthetic prescribed nodal temperature/adjoint fields.
// Deliberately no H::solve / H::solve_forward / mechanical FEM solve.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreturn-type"
#define main p10bw_fixture_entry_not_called
#include "P10BW_thermal_qp_native_unit.cpp"
#undef main
#pragma GCC diagnostic pop
#include "stage3d10bx_thermal_step_hook.hpp"
#include <limits>

struct TemporalAudit {
  int steps=0,dt=0;
  std::size_t qp_rows=0,step_rows=0,thermal_qps=0,robin_qps=0;
  double scalar_sum=0.,qp_sum=0.,max_step_error=0.,
         max_bin_error=0.,top_robin_l1=0.,memory_bytes=0.;
};

TemporalAudit test_temporal(std::string_view mode,int steps,int dt){
  if(steps*dt!=900)throw std::runtime_error("P10BY horizon not 900 s");
  const Mesh mesh=synthetic_mesh();
  const auto velocity=shape_velocity(mesh,mode);
  const auto operator_pair=H::assemble(mesh,velocity,double(dt));
  const std::size_t nn=mesh.nodes.size();
  std::vector<std::vector<double>> theta(std::size_t(steps)+1,
                                         std::vector<double>(nn));
  for(int n=0;n<=steps;++n)for(std::size_t i=0;i<nn;++i){
    const auto& x=mesh.nodes[i];
    theta[std::size_t(n)][i]=-.7+0.22*std::sin(.19*n+.11*i)+
      .08*std::cos(.07*n-.23*i)+3.7*x.z;
  }
  TemporalAudit sum;sum.steps=steps;sum.dt=dt;
  std::vector<ice3d::p10bx::Audit> retained;
  retained.reserve(std::size_t(steps));
  for(int n=steps;n>=1;--n){
    std::vector<double> psi(nn);
    for(std::size_t i=0;i<nn;++i){
      const double node_sign=(i%2==0?1.:-1.);
      psi[i]=node_sign*(.15+.06*std::sin(.31*n+.17*i));
    }
    const double ambient=H::ambient(double(n*dt));
    const auto audit=ice3d::p10bx::audit_step(mesh,velocity,
       operator_pair.shape,psi,theta[std::size_t(n)],
       theta[std::size_t(n-1)],double(dt),ambient);
    const double direct=contract_primal(operator_pair.shape,psi,
       theta[std::size_t(n)],theta[std::size_t(n-1)],double(dt),ambient);
    check_close(audit.csr_total,direct,"P10BY actual P10P CSR contraction",
                1e-10,1e-9);
    const auto parts=audit.qp.total();
    check_close(parts.total(),direct,"P10BY temporal step",1e-9,1e-9);
    W::Contributions bins;
    std::size_t count=0;
    for(const auto& cell:audit.qp.cells){
      bins.add(cell.part);count+=cell.qp_count;
      ++sum.qp_rows;
    }
    bins.add(audit.qp.top_robin);
    ++sum.qp_rows; // The separate (-1,-1) remote-top Robin row.
    check_close(bins.total(),parts.total(),"P10BY 100+1 QP bin sum",
                1e-12,1e-12);
    if(count!=mesh.tets.size()*H::quadrature().size())
       throw std::runtime_error("P10BY wrong 64-QP volume count");
    if(audit.qp.top_qp_count!=16*mesh.faces.size())
       throw std::runtime_error("P10BY wrong 16-QP top count");
    sum.max_step_error=std::max(sum.max_step_error,
          std::abs(parts.total()-direct));
    sum.max_bin_error=std::max(sum.max_bin_error,
          std::abs(bins.total()-parts.total()));
    sum.scalar_sum+=direct;sum.qp_sum+=parts.total();
    sum.thermal_qps+=count;
    sum.robin_qps+=audit.qp.top_qp_count;
    sum.top_robin_l1+=std::abs(audit.qp.top_robin.robin);
    ++sum.step_rows;
    retained.push_back(audit);
  }
  sum.memory_bytes=double(retained.capacity()*sizeof(ice3d::p10bx::Audit));
  if(sum.step_rows!=std::size_t(steps)||sum.qp_rows!=101*std::size_t(steps))
    throw std::runtime_error("P10BY CSV row count contract failed");
  check_close(sum.qp_sum,sum.scalar_sum,"P10BY time sum",1e-9,1e-9);
  if(mode=="R"){
    if(sum.top_robin_l1>1e-13)
      throw std::runtime_error("P10BY R velocity moved remote top Robin");
  }else if(mode=="top"&&!(sum.top_robin_l1>1e-9))
    throw std::runtime_error("P10BY moving Robin sensitivity missing");
  std::cout<<std::scientific<<std::setprecision(12)
    <<"P10BY_HISTORY_UNIT_OK mode="<<mode<<" steps="<<steps
    <<" dt_s="<<dt<<" max_step_abs_error="<<sum.max_step_error
    <<" max_100_plus_top_abs_error="<<sum.max_bin_error
    <<" allstep_abs_error="<<std::abs(sum.qp_sum-sum.scalar_sum)
    <<" qp_csv_rows="<<sum.qp_rows<<" top_robin_l1="<<sum.top_robin_l1
    <<" retained_audit_bytes="<<sum.memory_bytes<<'\n';
  return sum;
}

void test_corruption_stops(){
  const Mesh mesh=synthetic_mesh();
  const auto velocity=shape_velocity(mesh,"top");
  const auto base=H::assemble(mesh,velocity,75.);
  std::vector<double> psi(mesh.nodes.size(),.4),
       temp(mesh.nodes.size(),-.6),previous(mesh.nodes.size(),-.2);
  const auto valid=ice3d::p10bx::audit_step(mesh,velocity,base.shape,
                                            psi,temp,previous,75.,-2.1);
  if(!std::isfinite(valid.csr_total))throw std::runtime_error("P10BY invalid control");
  auto mass_broken=base.shape;
  mass_broken.mass.at(0)+=1.;
  bool mass_stopped=false,robin_stopped=false;
  try{(void)ice3d::p10bx::audit_step(mesh,velocity,mass_broken,
       psi,temp,previous,75.,-2.1);
  }catch(const std::runtime_error&){mass_stopped=true;}
  auto robin_broken=base.shape;
  robin_broken.robinload.at(std::size_t(mesh.faces.at(0).nodes[0]))+=1.;
  try{(void)ice3d::p10bx::audit_step(mesh,velocity,robin_broken,
       psi,temp,previous,75.,-2.1);
  }catch(const std::runtime_error&){robin_stopped=true;}
  if(!mass_stopped||!robin_stopped)
    throw std::runtime_error("P10BY error detector missed changed CSR component");
  std::cout<<"P10BY_CORRUPTION_STOP_UNIT_OK matrix_mass=1 robin_load=1\n";
}

int main(){
 try{
  int series=0,total_steps=0;std::size_t rows=0;
  double max_error=0.,max_retained=0.;
  for(std::string_view mode:{"R","top"})
    for(const auto& [steps,dt]:
       std::array<std::pair<int,int>,4>{{{6,150},{12,75},{18,50},{36,25}}}){
      const auto s=test_temporal(mode,steps,dt);
      ++series;total_steps+=steps;rows+=s.qp_rows;
      max_error=std::max(max_error,s.max_step_error);
      max_retained=std::max(max_retained,s.memory_bytes);
    }
  test_corruption_stops();
  std::cout<<std::scientific<<std::setprecision(12)
    <<"P10BY_TEMPORAL_THERMAL_QP_NATIVE_UNIT_OK series="<<series
    <<" steps="<<total_steps<<" qp_csv_rows="<<rows
    <<" corruption_stops=2/2 max_step_abs_error="<<max_error
    <<" max_retained_audit_bytes="<<max_retained
    <<" physical_FEM_runs=0 thermal_solves=0 mechanical_solves=0\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P10BY_STOP reason="<<e.what()<<'\n';return 2;
 }
}
