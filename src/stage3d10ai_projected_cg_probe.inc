// Stage3D10AI: projected PCG diagnostic for a single vertical translation gauge.
// This is a diagnostic only: it does not change production P10W or primal states.
// Operates on the same assembled tangent K but unpins the single vertical DOF,
// removes its rigid-translation nullspace, then checks the ORIGINAL pinned system.
namespace p10ai {
namespace E=ice3d::p10e;
struct Result {
 int iterations=0;
 bool converged=false;
 double null_action_rel=0.,compatibility=0.;
 double internal_rel=1., projected_true_rel=1., pinned_true_rel=1.;
 double pin_shift=0.,min_curvature=std::numeric_limits<double>::infinity();
 double wall_seconds=0.;
};

void require(bool good,const std::string& reason){
 if(!good)throw std::runtime_error("P10AI: "+reason);
}
// Remove constant z-displacement from any vector; respect x/y Dirichlet.
void project(std::vector<double>& a,const std::vector<uint8_t>& bc){
 const std::size_t n=bc.size()/3;
 long double sum=0.;
 std::size_t count=0;
 for(std::size_t node=0;node<n;++node)
  if(!bc[3*node+2]){sum+=(long double)a[3*node+2];++count;}
 require(count>1,"too few free vertical DOFs");
 const double mean=double(sum/(long double)count);
 for(std::size_t node=0;node<n;++node)
  if(!bc[3*node+2])a[3*node+2]-=mean;
 for(std::size_t i=0;i<bc.size();++i)if(bc[i])a[i]=0.;
}

Result solve_probe(BCSR& K,const std::vector<uint8_t>& original_bc,
    const std::vector<double>& b, const E::ReverseGraph* graph,
    int maxiter,std::ostream& progress){
 const auto start=std::chrono::steady_clock::now();
 const std::size_t n=b.size();
 require(n==3*std::size_t(K.n)&&original_bc.size()==n,"bad dimensions");
 std::vector<uint8_t> bc=original_bc;
 std::size_t pin=std::size_t(-1); int pins=0;
 for(std::size_t node=0;node<std::size_t(K.n);++node)
  if(bc[3*node+2]){++pins;pin=3*node+2;}
 require(pins==1,"expected exactly one vertical pin");
 for(std::size_t i=0;i<n;++i)
  if(original_bc[i])require(b[i]==0.,"RHS has nonzero constrained DOF");
 bc[pin]=0;
 const double base=E::norm(b);
 require(base>0.&&std::isfinite(base),"zero or nonfinite RHS norm");
 std::vector<double> rigid(n,0.);
 const double v=1./std::sqrt(double(K.n));
 for(std::size_t node=0;node<std::size_t(K.n);++node)rigid[3*node+2]=v;
 std::vector<double> Arigid;
 E::multiply(K,rigid,Arigid,bc,true,graph);
 double maxdiag=0.;
 const auto& r=K.rows();const auto& c=K.cols();
 for(int i=0;i<K.n;++i){
  const auto it=std::lower_bound(c.begin()+r[i],c.begin()+r[i+1],i);
  require(it!=c.begin()+r[i+1]&&*it==i,"missing diagonal");
  const auto& d=K.a[std::size_t(it-c.begin())];
  for(int j=0;j<3;++j)maxdiag=std::max(maxdiag,std::abs(d[3*j+j]));
 }
 Result out;
 out.null_action_rel=E::norm(Arigid)/std::max(maxdiag,1.);
 out.compatibility=std::abs(E::product(rigid,b))/base;
 progress<<std::scientific<<std::setprecision(12)
   <<"P10AI_UNPINNED_GAUGE null_action_diag_scaled="<<out.null_action_rel
   <<" rhs_vertical_compatibility="<<out.compatibility
   <<" pin_node="<<pin/3<<'\n'<<std::flush;
 // If free translation is not (numerically) a true null mode, this is not
 // the intended gauge-invariant problem: stop rather than solving another one.
 require(out.null_action_rel<1e-9,"unpinning does not create a translation nullspace");
 require(out.compatibility<1e-10,"RHS is not translation-invariant");
 K.build_preconditioner(bc); // existing 3x3 block-Jacobi, no new solver dependency
 std::vector<double> x(n,0.),res=b,z,p,Ap,Ax;
 project(res,bc);
 K.precond(res,z,bc); project(z,bc);
 p=z;
 double rz=E::product(res,z);
 require(rz>0.&&std::isfinite(rz),"nonpositive initial preconditioned energy");
 const double target=2e-10;
 for(int iter=1;iter<=maxiter;++iter){
  E::multiply(K,p,Ap,bc,true,graph);
  project(Ap,bc);
  const double denom=E::product(p,Ap);
  if(!(denom>0.)||!std::isfinite(denom)){
   progress<<"P10AI_CG_BREAKDOWN iteration="<<iter<<" curvature="<<denom<<'\n';
   break;
  }
  out.min_curvature=std::min(out.min_curvature,denom/std::max(E::product(p,p),1e-300));
  const double alpha=rz/denom;
  for(std::size_t i=0;i<n;++i){x[i]+=alpha*p[i];res[i]-=alpha*Ap[i];}
  out.iterations=iter;
  const double recursive_rel=E::norm(res)/base;
  if(iter%100==0||iter==1||iter==maxiter||recursive_rel<target){
   E::multiply(K,x,Ax,bc,true,graph);
   for(std::size_t i=0;i<n;++i)Ax[i]=b[i]-Ax[i];
   project(Ax,bc);
   out.projected_true_rel=E::norm(Ax)/base;
   out.internal_rel=recursive_rel;
   progress<<"P10AI_CG_PROGRESS iteration="<<iter
    <<" internal_rel="<<out.internal_rel
    <<" projected_verified_rel="<<out.projected_true_rel<<'\n'<<std::flush;
   if(out.projected_true_rel<target){out.converged=true;break;}
  }
  K.precond(res,z,bc); project(z,bc);
  const double rz_new=E::product(res,z);
  if(!(rz_new>0.)||!std::isfinite(rz_new)){
   progress<<"P10AI_CG_BREAKDOWN iteration="<<iter
    <<" preconditioned_energy="<<rz_new<<'\n';break;
  }
  const double beta=rz_new/rz;
  for(std::size_t i=0;i<n;++i)p[i]=z[i]+beta*p[i];
  project(p,bc);
  rz=rz_new;
 }
 // Translate the solution of the unpinned quotient problem back into the
 // original point-pin gauge. Pure translations do not change deformation.
 out.pin_shift=x[pin];
 for(std::size_t node=0;node<std::size_t(K.n);++node)x[3*node+2]-=out.pin_shift;
 for(std::size_t i=0;i<n;++i)if(original_bc[i])x[i]=0.;
 E::multiply(K,x,Ax,original_bc,true,graph);
 for(std::size_t i=0;i<n;++i)Ax[i]-=b[i];
 out.pinned_true_rel=E::norm(Ax)/base;
 out.converged=out.converged&&out.pinned_true_rel<1e-9;
 out.wall_seconds=std::chrono::duration<double>(
    std::chrono::steady_clock::now()-start).count();
 progress<<"P10AI_PROJECTED_CG_RESULT converged="<<int(out.converged)
   <<" iterations="<<out.iterations
   <<" projected_verified_rel="<<out.projected_true_rel
   <<" pinned_verified_rel="<<out.pinned_true_rel
   <<" null_action_diag_scaled="<<out.null_action_rel
   <<" compatibility="<<out.compatibility
   <<" wall_s="<<out.wall_seconds<<'\n'<<std::flush;
 return out;
}

void save(const std::filesystem::path& path,const Result& r){
 std::ofstream f(path);
 require(bool(f),"cannot write CSV");
 f<<"solver,converged,iterations,null_action_diag_scaled,rhs_compatibility,"
  "internal_rel,projected_verified_rel,pinned_verified_rel,pin_shift,"
  "min_curvature,wall_seconds\n";
 f<<std::setprecision(17)<<"projected_pcg_jacobi,"<<int(r.converged)<<','
  <<r.iterations<<','<<r.null_action_rel<<','<<r.compatibility<<','
  <<r.internal_rel<<','<<r.projected_true_rel<<','<<r.pinned_true_rel<<','
  <<r.pin_shift<<','<<r.min_curvature<<','<<r.wall_seconds<<'\n';
 f.close();require(bool(f),"CSV write failed");
}
void selftest(){
 // Three nodes linked by two springs (vertical), x/y frozen. One z pin.
 BCSR K; K.n=3; K.row={0,3,6,9}; K.col={0,1,2,0,1,2,0,1,2};
 K.a.assign(9,{});
 const double s[3][3]={{2.,-1.,-1.},{-1.,1.,0.},{-1.,0.,1.}};
 for(int i=0;i<3;++i)for(int j=0;j<3;++j){
  auto& q=K.a[3*i+j];q[8]=s[i][j];
  if(i==j){q[0]=4.;q[4]=5.;}
 }
 std::vector<uint8_t> bc(9,0); for(int i=0;i<3;++i){bc[3*i]=1;bc[3*i+1]=1;}
 bc[2]=1;
 std::vector<double> b(9,0.);b[5]=1.;b[8]=-1.;
 E::ReverseGraph graph(K);
 std::ostringstream sink;
 const auto r=solve_probe(K,bc,b,&graph,100,sink);
 require(r.converged,"toy projected-PCG did not converge");
 require(r.pinned_true_rel<1e-12,"toy original pinned residual mismatch");
 require(r.null_action_rel<1e-12&&r.compatibility<1e-12,"toy gauge mismatch");
 std::cout<<"P10AI_SELFTEST_OK projected_pcg=1 pin_reconstruction=1"
   <<" verified_rel="<<r.pinned_true_rel<<'\n';
}
} // namespace p10ai
