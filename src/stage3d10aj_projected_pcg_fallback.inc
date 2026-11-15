// P10AJ: verified gauge-projected PCG fallback for P10W only.
// Inclusion contract: inside ice3d::p10e after IterativeResult and multiply().
// Based on the successfully tested P10AI diagnostic, not a new physical model.
inline IterativeResult solve_projected_pcg_fallback(
    BCSR& K,const std::vector<uint8_t>& original_bc,
    const std::vector<double>& rhs,bool transpose,const ReverseGraph* graph,
    double projected_tol=2e-10,int maxiter=2000){
 const size_t n=rhs.size();
 auto require=[](bool ok,const std::string& why){
  if(!ok)throw std::runtime_error("P10AJ: "+why);
 };
 require(n==3*size_t(K.n)&&original_bc.size()==n,"dimension mismatch");
 require(maxiter>0&&projected_tol>0.,"invalid solver controls");
 const double base=norm(rhs);
 require(base>0.&&std::isfinite(base),"zero or nonfinite RHS norm");
 std::vector<uint8_t> free_bc=original_bc;
 size_t pin=size_t(-1);int pins=0;
 for(size_t node=0;node<size_t(K.n);++node){
  if(original_bc[3*node+2]){++pins;pin=3*node+2;}
 }
 require(pins==1,"expected exactly one vertical pin");
 for(size_t i=0;i<n;++i)
  if(original_bc[i])require(rhs[i]==0.,"constrained RHS is nonzero");
 free_bc[pin]=0;
 auto project=[&](std::vector<double>& a){
  long double sum=0.;size_t count=0;
  for(size_t node=0;node<size_t(K.n);++node)
   if(!free_bc[3*node+2]){sum+=(long double)a[3*node+2];++count;}
  require(count>1,"too few free vertical DOFs");
  const double mean=double(sum/(long double)count);
  for(size_t node=0;node<size_t(K.n);++node)
   if(!free_bc[3*node+2])a[3*node+2]-=mean;
  for(size_t i=0;i<n;++i)if(free_bc[i])a[i]=0.;
 };
 std::vector<double> rigid(n,0.);
 const double amp=1./std::sqrt(double(K.n));
 for(size_t node=0;node<size_t(K.n);++node)rigid[3*node+2]=amp;
 std::vector<double> Arigid;
 multiply(K,rigid,Arigid,free_bc,transpose,graph);
 double maxdiag=0.;
 const auto& row=K.rows();const auto& col=K.cols();
 for(int i=0;i<K.n;++i){
  const auto it=std::lower_bound(col.begin()+row[i],col.begin()+row[i+1],i);
  require(it!=col.begin()+row[i+1]&&*it==i,"missing diagonal block");
  const auto& D=K.a[size_t(it-col.begin())];
  for(int c=0;c<3;++c)maxdiag=std::max(maxdiag,std::abs(D[3*c+c]));
 }
 const double null_rel=norm(Arigid)/std::max(maxdiag,1.);
 const double compatibility=std::abs(product(rigid,rhs))/base;
 std::cout<<std::scientific<<std::setprecision(12)
  <<"P10AJ_GAUGE null_action_diag_scaled="<<null_rel
  <<" rhs_compatibility="<<compatibility
  <<" pin_node="<<(pin/3)<<'\n'<<std::flush;
 require(null_rel<1e-9,"vertical translation not a null mode");
 require(compatibility<1e-10,"RHS incompatible with vertical translation");
 K.build_preconditioner(free_bc);
 std::vector<double> x(n,0.),r=rhs,z,p,Ap,Ax;
 project(r);
 K.precond(r,z,free_bc);project(z);
 p=z;
 double rz=product(r,z);
 require(rz>0.&&std::isfinite(rz),"initial preconditioned energy nonpositive");
 IterativeResult result;
 bool projected_converged=false;
 double projected_true_rel=1.,internal_rel=1.;
 for(int iter=1;iter<=maxiter;++iter){
  multiply(K,p,Ap,free_bc,transpose,graph);project(Ap);
  const double curvature=product(p,Ap);
  if(!(curvature>0.)||!std::isfinite(curvature))
   throw std::runtime_error("P10AJ: nonpositive/nonfinite projected curvature");
  const double alpha=rz/curvature;
  for(size_t i=0;i<n;++i){x[i]+=alpha*p[i];r[i]-=alpha*Ap[i];}
  result.iterations=iter;
  internal_rel=norm(r)/base;
  if(iter%100==0||iter==1||iter==maxiter||internal_rel<projected_tol){
   multiply(K,x,Ax,free_bc,transpose,graph);
   for(size_t i=0;i<n;++i)Ax[i]=rhs[i]-Ax[i];
   project(Ax);
   projected_true_rel=norm(Ax)/base;
   std::cout<<"P10AJ_PCG_PROGRESS iterations="<<iter
    <<" internal_rel="<<internal_rel
    <<" projected_verified_rel="<<projected_true_rel<<'\n'<<std::flush;
   if(projected_true_rel<projected_tol){projected_converged=true;break;}
  }
  K.precond(r,z,free_bc);project(z);
  const double rz_new=product(r,z);
  if(!(rz_new>0.)||!std::isfinite(rz_new))
   throw std::runtime_error("P10AJ: nonpositive/nonfinite preconditioned energy");
  const double beta=rz_new/rz;
  for(size_t i=0;i<n;++i)p[i]=z[i]+beta*p[i];
  project(p);rz=rz_new;
 }
 require(projected_converged,"projected PCG exhausted iterations; verified_rel="+
         std::to_string(projected_true_rel));
 // Shift only along the verified rigid null mode to restore the original pin.
 const double pin_shift=x[pin];
 for(size_t node=0;node<size_t(K.n);++node)x[3*node+2]-=pin_shift;
 for(size_t i=0;i<n;++i)if(original_bc[i])x[i]=0.;
 multiply(K,x,Ax,original_bc,transpose,graph);
 for(size_t i=0;i<n;++i)Ax[i]-=rhs[i];
 result.relative_residual=norm(Ax)/base;
 std::cout<<"P10AJ_PINNED_CHECK iterations="<<result.iterations
   <<" verified_relative_residual="<<result.relative_residual
   <<" pin_shift="<<pin_shift<<'\n'<<std::flush;
 require(std::isfinite(result.relative_residual)&&result.relative_residual<1e-9,
    "reconstructed ORIGINAL pinned system did not pass residual check");
 result.x=std::move(x);
 return result;
}
