// Stage3D10AG: read-only, step-6 adjoint operator diagnostic.
// Reads P10N forward cache; NO nonlinear forward, no adjoint Krylov solve.
#define STAGE3D10W_ANALYTIC_SHAPE
#define STAGE3D10P_NO_MAIN
#include "stage3d10p_partial_audit.cpp"
#include <fstream>
#include <iomanip>
#include "stage3d10ah_nullmode_probe.inc"

namespace p10ag {
namespace E=ice3d::p10e;
namespace A=ice3d::p10c;
namespace F=ice3d::p10f;

struct Metrics{
 double jvp_rel=0, vjp_rel=0, transpose_pair_rel=0,transpose_reference_rel=0;
 double asymmetry_frobenius_rel=0, max_asymmetry_rel=0;
 double min_diag=std::numeric_limits<double>::infinity();
 double max_diag=-std::numeric_limits<double>::infinity();
 double min_rayleigh=std::numeric_limits<double>::infinity();
 double max_rayleigh=-std::numeric_limits<double>::infinity();
 double rhs_norm=0,rhs_constrained_norm=0,rhs_max_abs=0;
 std::size_t free_dofs=0,pinned_dofs=0,nonpositive_diagonal=0;
};

void require(bool b,const std::string& m){if(!b)throw std::runtime_error("P10AG: "+m);}

double difference_rel(const std::vector<double>& a,const std::vector<double>& b){
 require(a.size()==b.size(),"vector size mismatch");
 long double d=0.,sa=0.,sb=0.;
 for(std::size_t i=0;i<a.size();++i){
  const auto x=(long double)a[i],y=(long double)b[i];
  d+=(x-y)*(x-y); sa+=x*x; sb+=y*y;
 }
 return double(std::sqrt(d)/std::max({(long double)1e-300L,std::sqrt(sa),std::sqrt(sb)}));
}

std::vector<double> probe(const std::vector<uint8_t>& bc,int seed){
 std::vector<double> v(bc.size());
 for(size_t i=0;i<v.size();++i){
  if(bc[i])continue;
  const double q=double(i+1);
  v[i]=std::sin((.00091+.00003*seed)*q)+.23*std::cos((.00172+.00011*seed)*q);
 }
 const auto n=E::norm(v); require(n>0.,"zero probe");
 for(auto& z:v)z/=n;
 return v;
}

Metrics inspect_matrix(const BCSR& K,const std::vector<uint8_t>& bc){
 Metrics m;
 const auto& rows=K.rows();const auto& cols=K.cols();
 long double skew2=0.,mat2=0.;
 for(int i=0;i<K.n;++i){
  for(int p=rows[i];p<rows[i+1];++p){
   const int j=cols[p];
   const auto& A=K.a[p];
   const auto first=cols.begin()+rows[j],last=cols.begin()+rows[j+1];
   const auto it=std::lower_bound(first,last,i);
   require(it!=last&&*it==i,"BCSR transpose structure missing");
   const auto& T=K.a[std::size_t(it-cols.begin())];
   for(int r=0;r<3;++r)for(int c=0;c<3;++c){
    const size_t a=3*size_t(i)+size_t(r),b=3*size_t(j)+size_t(c);
    if(bc[a]||bc[b])continue;
    const double v=A[3*r+c],w=T[3*c+r];
    require(std::isfinite(v)&&std::isfinite(w),"nonfinite matrix coefficient");
    const double diff=v-w;
    skew2+=(long double)diff*diff;
    mat2+=(long double)v*v;
    m.max_asymmetry_rel=std::max(m.max_asymmetry_rel,
      std::abs(diff)/std::max({1.,std::abs(v),std::abs(w)}));
    if(i==j&&r==c){
     m.min_diag=std::min(m.min_diag,v);
     m.max_diag=std::max(m.max_diag,v);
     if(v<=0.)++m.nonpositive_diagonal;
    }
   }
  }
 }
 m.asymmetry_frobenius_rel=std::sqrt(double(skew2/mat2));
 for(auto v:bc) v?++m.pinned_dofs:++m.free_dofs;
 return m;
}

void verify_probe(const BCSR& K,const std::vector<uint8_t>& bc,
                  const A::Step& state,const E::ReverseGraph& graph,
                  Metrics& m){
 const size_t nq=state.qps.size();
 const auto x=probe(bc,0),y=probe(bc,1);
 std::vector<double> Kx,Kty,Ky;
 E::multiply(K,x,Kx,bc,false,&graph);
 E::multiply(K,y,Ky,bc,false,&graph);
 E::multiply(K,y,Kty,bc,true,&graph);
 const double p1=E::product(x,Kty),p2=E::product(y,Kx);
 m.transpose_pair_rel=std::abs(p1-p2)/std::max({1e-300,std::abs(p1),std::abs(p2)});
 std::vector<double> Ktx;
 E::multiply(K,x,Ktx,bc,true,&graph);
 std::vector<double> Ktx_reference;
 E::multiply_transpose(K,x,Ktx_reference,bc,nullptr);
 m.transpose_reference_rel=difference_rel(Ktx,Ktx_reference);
 A::Perturbation d;
 d.du=x; d.dtemperature.assign(state.node_count,0.);
 d.dprevious.resize(nq);
 auto jvp=state.jvp(d);
 m.jvp_rel=difference_rel(Kx,jvp.residual);
 // Release the huge JVP result before allocating the VJP result.
 jvp.next.clear(); jvp.next.shrink_to_fit();
 A::Output lambda;
 lambda.residual=x; lambda.next.resize(nq);
 auto back=state.vjp(lambda);
 m.vjp_rel=difference_rel(Ktx,back.displacement);
 for(int seed=0;seed<5;++seed){
  const auto z=probe(bc,seed+2);
  std::vector<double> Kz;
  E::multiply(K,z,Kz,bc,false,&graph);
  const double rq=E::product(z,Kz)/E::product(z,z);
  m.min_rayleigh=std::min(m.min_rayleigh,rq);
  m.max_rayleigh=std::max(m.max_rayleigh,rq);
 }
}

int run(const p10k::Config& c,const fs::path& cache){
 require(c.steps==6&&c.dt==150,"requires 6 steps of 150 s");
 require(c.mode=="R","requires shape mode R");
 require(fs::is_regular_file(c.mesh),"mesh is missing");
 require(fs::is_regular_file(cache),"forward_history.bin is missing");
 require(!fs::exists(c.out),"output folder must be NEW");
 const auto start=std::chrono::steady_clock::now();
 std::cout<<"P10AG_BEGIN step=6 functional=jen nonlinear_forward_solves=0 krylov_solves=0\n"<<std::flush;
 const auto mesh=read_msh(c.mesh).mesh;
 const auto forward=p10n::load_forward(cache,mesh,c);
 require(forward.frames.size()==6,"unexpected forward frames");
 const auto& frame=forward.frames.back();
 const auto quad=volume_q(3);
 const auto pinned=p10k::adjoint_bc(mesh);
 const auto mask=p10k::observation_elements(mesh);
 const double qp_gib=double(mesh.tets.size())*double(quad.size())*
    double(sizeof(A::QuadraturePoint))/1073741824.;
 std::cout<<"P10AG_BUILD_STATE tet10="<<mesh.tets.size()
          <<" qps="<<mesh.tets.size()*quad.size()
          <<" qp_storage_gib_estimate="<<std::fixed<<std::setprecision(3)
          <<qp_gib<<'\n'<<std::flush;
 const A::Step state(mesh,quad,frame.temperature,frame.previous,
    double(c.dt),frame.repinned_u,pinned,Modulus::VAR,
    ice3d::p10b::Controls{true,true});
 const auto topology=build_bcsr_topology(mesh);
 auto K=E::assemble_tangent_bcsr(mesh,state,topology);
 const E::ReverseGraph graph(K);
 auto m=inspect_matrix(K,pinned);
 const auto sources=p10k::evaluate_b6(state,F::Kind::Energy,mask,quad.size());
 std::vector<double> rhs(sources.displacement.size());
 for(size_t i=0;i<rhs.size();++i){
  rhs[i]=-(.5/double(c.steps))*sources.displacement[i];
  m.rhs_max_abs=std::max(m.rhs_max_abs,std::abs(rhs[i]));
  if(pinned[i])m.rhs_constrained_norm+=rhs[i]*rhs[i];
 }
 m.rhs_norm=E::norm(rhs);
 m.rhs_constrained_norm=std::sqrt(m.rhs_constrained_norm);
 std::cout<<"P10AG_MATRIX_READY blocks="<<K.a.size()
   <<" rhs_norm="<<std::scientific<<m.rhs_norm<<'\n'<<std::flush;
 verify_probe(K,pinned,state,graph,m);
 const auto null_mode=p10ah::inspect(K,pinned,rhs,m.min_rayleigh,&graph);
 fs::create_directories(c.out);
 p10ah::save(c.out/"P10AH_NULLMODE_DIAGNOSTIC.csv",c.mesh.stem().string(),null_mode);
 p10ah::report(null_mode);
 std::ofstream csv(c.out/"P10AG_STEP6_DIAGNOSTIC.csv");
 require(bool(csv),"cannot write output csv");
 csv<<"mesh,tet10,step,functional,free_dofs,pinned_dofs,rhs_norm,rhs_constrained_norm,"
      "rhs_max_abs,jvp_rel,vjp_rel,transpose_pair_rel,transpose_reference_rel,asymmetry_frobenius_rel,"
      "max_asymmetry_rel,min_diagonal,max_diagonal,nonpositive_diagonal,"
      "min_probe_rayleigh,max_probe_rayleigh\n";
 csv<<std::setprecision(17)<<c.mesh.stem().string()<<','<<mesh.tets.size()
   <<",6,jen,"<<m.free_dofs<<','<<m.pinned_dofs<<','<<m.rhs_norm<<','
   <<m.rhs_constrained_norm<<','<<m.rhs_max_abs<<','<<m.jvp_rel<<','
   <<m.vjp_rel<<','<<m.transpose_pair_rel<<','<<m.transpose_reference_rel<<','<<m.asymmetry_frobenius_rel<<','
   <<m.max_asymmetry_rel<<','<<m.min_diag<<','<<m.max_diag<<','
   <<m.nonpositive_diagonal<<','<<m.min_rayleigh<<','<<m.max_rayleigh<<'\n';
 csv.close();require(bool(csv),"csv write failed");
 std::cout<<std::scientific<<std::setprecision(11)
   <<"P10AG_RESULT jvp_rel="<<m.jvp_rel
   <<" vjp_rel="<<m.vjp_rel
   <<" transpose_pair_rel="<<m.transpose_pair_rel
   <<" transpose_reference_rel="<<m.transpose_reference_rel
   <<" asymmetry_rel="<<m.asymmetry_frobenius_rel
   <<" diag_nonpositive="<<m.nonpositive_diagonal
   <<" probe_min_rayleigh="<<m.min_rayleigh
   <<" rhs_norm="<<m.rhs_norm
   <<" wall_s="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()
   <<"\nP10AG_DIAGNOSTIC_OK\n"<<std::flush;
 return 0;
}
}

int main(int argc,char** argv){
 try{
  if(argc==2&&std::string(argv[1])=="--selftest"){
    BCSR K;K.n=2;K.row={0,2,4};K.col={0,1,0,1};
    K.a.resize(4);
    K.a[0]={5.,.2,0.,.2,4.,0.,0.,0.,3.};
    K.a[1]={.1,0.,0.,0.,.2,0.,0.,0.,.3};
    K.a[2]={.1,0.,0.,0.,.2,0.,0.,0.,.3};
    K.a[3]={6.,.4,0.,.4,5.,0.,0.,0.,4.};
    const std::vector<uint8_t> bc{1,0,0,0,0,0};
    const p10ag::E::ReverseGraph graph(K);
    const auto x=p10ag::probe(bc,0),y=p10ag::probe(bc,1);
    std::vector<double> Kx,Kty,Ktx_reference;
    p10ag::E::multiply(K,x,Kx,bc,false,&graph);
    p10ag::E::multiply(K,y,Kty,bc,true,&graph);
    p10ag::E::multiply_transpose(K,y,Ktx_reference,bc,nullptr);
    p10ag::require(p10ag::difference_rel(Kty,Ktx_reference)<1e-13,
      "small transpose SpMV disagreement");
    p10ag::require(std::abs(p10ag::E::product(y,Kx)-p10ag::E::product(x,Kty))<1e-12,
      "small matrix bilinear pairing disagreement");
    const auto m=p10ag::inspect_matrix(K,bc);
    p10ag::require(m.nonpositive_diagonal==0&&m.asymmetry_frobenius_rel<1e-13,
      "small matrix symmetry test failed");
    p10i::Problem small(0.,0.,"EDV","VAR");
    const std::vector<State> previous(small.geometry.m.tets.size()*small.quadrature.size());
    const std::vector<double> displacement(3*small.geometry.m.nodes.size());
    const auto temperature=small.thermal(6);
    const auto step=small.make_step(temperature,previous,displacement);
    auto tangent=p10ag::E::assemble_tangent_bcsr(small.geometry.m,step);
    const p10ag::E::ReverseGraph gr(tangent);
    p10ag::Metrics check;
    p10ag::verify_probe(tangent,small.bc,step,gr,check);
    p10ag::require(check.jvp_rel<1e-10&&check.vjp_rel<1e-10,
      "small P10C JVP/VJP vs P10E tangent failed");
    p10ah::selftest();
    std::cout<<"P10AG_SELFTEST_OK transpose=1 constraints=1 symmetry=1"
      <<" jvp_rel="<<check.jvp_rel<<" vjp_rel="<<check.vjp_rel<<'\n';
    return 0;
  }
  fs::path reuse;
  std::vector<char*> filtered{argv[0]};
  for(int i=1;i<argc;++i){
   if(std::string(argv[i])=="--reuse-forward"){
    if(++i>=argc)throw std::runtime_error("missing --reuse-forward value");
    reuse=argv[i];
   }else filtered.push_back(argv[i]);
  }
  const auto c=p10k::parse(int(filtered.size()),filtered.data());
#ifdef _OPENMP
  omp_set_dynamic(0); omp_set_num_threads(c.threads);
#endif
  return p10ag::run(c,reuse);
 }catch(const std::exception& e){
  std::cerr<<"P10AG_ERROR "<<e.what()<<'\n';return 2;
 }
}
