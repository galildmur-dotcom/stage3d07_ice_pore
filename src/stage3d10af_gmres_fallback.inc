// Stage 3D-10AF GMRES implementation, included inside namespace ice3d::p10e.
// Only compiled by STAGE3D10W_ANALYTIC_SHAPE. Does NOT change BiCGStab.
inline IterativeResult solve_gmres_fallback(
    BCSR& K, const std::vector<std::uint8_t>& bc,
    const std::vector<double>& rhs, bool transpose,
    const ReverseGraph* graph,
    double requested_tolerance=2e-10, int max_iterations=4800,
    int restart=40) {
  const std::size_t n=rhs.size();
  if(n!=3*std::size_t(K.n) || bc.size()!=n ||
     !(requested_tolerance>0.) || max_iterations<1 || restart<2)
    throw std::invalid_argument("P10AF: GMRES invalid dimensions/settings");
  const double rhs_norm=norm(rhs);
  if(!std::isfinite(rhs_norm))
    throw std::runtime_error("P10AF: nonfinite RHS norm");
  IterativeResult answer;
  answer.x.assign(n,0.);
  if(rhs_norm==0.)return answer;
  K.build_preconditioner(bc);
  auto true_residual=[&](const std::vector<double>& x,
                         std::vector<double>& r) {
    std::vector<double> Ax;
    multiply(K,x,Ax,bc,transpose,graph);
    r.resize(n);
    for(std::size_t i=0;i<n;++i)r[i]=rhs[i]-Ax[i];
    return norm(r)/rhs_norm;
  };
  std::vector<double> residual=rhs;
  double verified=1.;
  int iterations=0;
  while(iterations<max_iterations){
    const double beta=norm(residual);
    if(!std::isfinite(beta))
      throw std::runtime_error("P10AF: nonfinite true residual");
    if(beta/rhs_norm<=requested_tolerance){
      answer.iterations=iterations;
      answer.relative_residual=beta/rhs_norm;
      return answer;
    }
    const int m=std::min(restart,max_iterations-iterations);
    std::vector<std::vector<double>> V,Z;
    V.reserve(std::size_t(m+1));
    Z.reserve(std::size_t(m));
    V.push_back(residual);
    for(double& v:V.back())v/=beta;
    std::vector<std::vector<double>> H(std::size_t(m+1),
                                       std::vector<double>(std::size_t(m),0.));
    std::vector<double> cs(std::size_t(m),0.), sn(std::size_t(m),0.);
    std::vector<double> g(std::size_t(m+1),0.);
    g[0]=beta;
    int used=0;
    for(int j=0;j<m;++j){
      Z.emplace_back();
      K.precond(V[std::size_t(j)],Z.back(),bc);
      std::vector<double> w;
      multiply(K,Z.back(),w,bc,transpose,graph);
      const double pre_orth_norm=norm(w);
      // Two-pass modified Gram-Schmidt is needed for poorly conditioned
      // tangents; storing the right-preconditioned basis allows exact updates.
      for(int pass=0;pass<2;++pass){
        for(int i=0;i<=j;++i){
          const double dot=product(V[std::size_t(i)],w);
          H[std::size_t(i)][std::size_t(j)]+=dot;
          const auto& v=V[std::size_t(i)];
          for(std::size_t k=0;k<n;++k)w[k]-=dot*v[k];
        }
      }
      const double next_norm=norm(w);
      if(!std::isfinite(next_norm))
        throw std::runtime_error("P10AF: GMRES nonfinite Arnoldi norm");
      H[std::size_t(j+1)][std::size_t(j)]=next_norm;
      const bool breakdown=next_norm <= 1e-14*std::max(1.,pre_orth_norm);
      if(!breakdown){
        for(double& x:w)x/=next_norm;
        V.push_back(std::move(w));
      }
      for(int i=0;i<j;++i){
        const double a=H[std::size_t(i)][std::size_t(j)];
        const double b=H[std::size_t(i+1)][std::size_t(j)];
        H[std::size_t(i)][std::size_t(j)]=cs[std::size_t(i)]*a+sn[std::size_t(i)]*b;
        H[std::size_t(i+1)][std::size_t(j)]=-sn[std::size_t(i)]*a+cs[std::size_t(i)]*b;
      }
      const double diag=H[std::size_t(j)][std::size_t(j)];
      const double lower=H[std::size_t(j+1)][std::size_t(j)];
      const double hyp=std::hypot(diag,lower);
      if(!(hyp>0.) || !std::isfinite(hyp))
        throw std::runtime_error("P10AF: GMRES singular Hessenberg column");
      cs[std::size_t(j)]=diag/hyp;
      sn[std::size_t(j)]=lower/hyp;
      H[std::size_t(j)][std::size_t(j)]=hyp;
      H[std::size_t(j+1)][std::size_t(j)]=0.;
      const double old_g=g[std::size_t(j)];
      g[std::size_t(j)]=cs[std::size_t(j)]*old_g;
      g[std::size_t(j+1)]=-sn[std::size_t(j)]*old_g;
      ++iterations;
      used=j+1;
      if(breakdown || std::abs(g[std::size_t(j+1)])/rhs_norm<=requested_tolerance)
        break;
    }
    std::vector<double> y(std::size_t(used),0.);
    for(int i=used-1;i>=0;--i){
      double value=g[std::size_t(i)];
      for(int j=i+1;j<used;++j)
        value-=H[std::size_t(i)][std::size_t(j)]*y[std::size_t(j)];
      const double diag=H[std::size_t(i)][std::size_t(i)];
      if(!(std::abs(diag)>0.) || !std::isfinite(diag))
        throw std::runtime_error("P10AF: GMRES singular triangular solve");
      y[std::size_t(i)]=value/diag;
    }
    for(int j=0;j<used;++j){
      const double weight=y[std::size_t(j)];
      const auto& z=Z[std::size_t(j)];
      for(std::size_t k=0;k<n;++k)answer.x[k]+=weight*z[k];
    }
    verified=true_residual(answer.x,residual);
    if(!std::isfinite(verified))
      throw std::runtime_error("P10AF: GMRES nonfinite verified residual");
    std::cout<<"P10AF_GMRES_CYCLE iterations="<<iterations
             <<" verified_relative_residual="<<std::scientific
             <<std::setprecision(11)<<verified<<'\n'<<std::flush;
    if(verified<=requested_tolerance){
      answer.iterations=iterations;
      answer.relative_residual=verified;
      return answer;
    }
  }
  // A bounded attempt is never accepted based only on an Arnoldi estimate.
  // Report the actual verified residual, not an opaque "failed residual".
  throw std::runtime_error("P10AF: GMRES exhausted iterations; verified_relative_residual="+
                           std::to_string(verified)+
                           " requested_tolerance="+std::to_string(requested_tolerance));
}
