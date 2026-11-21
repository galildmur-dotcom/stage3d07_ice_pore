// Stage3D-10W: full transient discrete adjoint with analytic Tet10 geometric
// partials. Stage3D10N/P/S remain the independent finite-difference reference.
#define STAGE3D10W_ANALYTIC_SHAPE
#define STAGE3D10P_NO_MAIN
#include "stage3d10p_partial_audit.cpp"

#ifdef STAGE3D10DK_M1_FULL4D
int p10dk_inherited_main(int argc,char** argv){
#else
int main(int argc,char** argv){
#endif
 try{
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
  ice3d::stage3d10s_manifest::set_arguments(argc,argv);
#endif
  std::vector<char*> filtered{argv[0]};
  fs::path reuse,cache;
  bool explicit_mesh=false,explicit_out=false;
  for(int i=1;i<argc;++i){
   const std::string arg=argv[i];
   if(arg=="--help"){
#ifdef STAGE3D10DD_FULL4D
#ifdef STAGE3D10DK_M1_FULL4D
    std::cout<<"P10DK_FULL4D: accepted M1 R/EDV_VAR xi=0 jpeak physical signed "
      "(r,theta,phi,t) QP partition; requires a NEW M1 forward history "
      "and the SAME M1 for the analytic adjoint. "
      "6x150s only; --help/--selftest never execute physical FEM.\n";
#else
    std::cout<<"P10DD_FULL4D: H0 R/EDV_VAR xi=0 jpeak physical signed "
      "(r,theta,phi,t) QP partition; mechanical explicit/equilibrium/history "
      "and thermal mass/diffusion/top Robin; 1200 volume bins per step. "
      "6x150s only; no FEM is launched by --help or --selftest.\n";
#endif
#endif
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
    std::cout<<"stage3d10y_analytic_shell_audit: exact P10W derivative"
     " by physical radial Gauss-point shells. Thermal partial remains global.\n";
#endif
    std::cout<<"stage3d10w_analytic_adjoint --mesh MSH --out NEW_DIR "
     "--steps 6 --dt 150 --mode R|tz|y20 --cutoff-mm 5 "
     "[--threads 4] [--preflight] [--reuse-forward BIN] "
     "[--forward-cache NEW_BIN] [--selftest]\n"
     "Geometric partials are exact discrete Tet10 derivatives; "
     "no --delta-scan-um is accepted.\n";
    return 0;
   }
   if(arg=="--delta-um" || arg=="--delta-scan-um" ||
      arg=="--geometry-exe")
    throw std::invalid_argument(
      "P10W: finite-difference geometry options are forbidden");
   if(arg=="--reuse-forward"||arg=="--forward-cache"){
    p10k::require(i+1<argc,"P10W missing value after "+arg);
    const fs::path path=argv[++i];
    if(arg=="--reuse-forward")reuse=path;
    else cache=path;
   }else{
    if(arg=="--mesh")explicit_mesh=true;
    if(arg=="--out")explicit_out=true;
    filtered.push_back(argv[i]);
   }
  }
  const auto c=p10k::parse(int(filtered.size()),filtered.data());
#ifdef _OPENMP
  omp_set_dynamic(0);omp_set_num_threads(c.threads);
#endif
  if(c.selftest){
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
   p10k::require(p10n::spatial::shell(-1.e-6)==0 &&
     p10n::spatial::shell(.019999)==0 &&
     p10n::spatial::shell(.02)==1 &&
     p10n::spatial::shell(.1)==3 &&
     p10n::spatial::shell(15.)==9,
     "P10Y radial shell boundaries");
#endif
   const int result=p10i::run_tests();
   // This tests the inherited reverse solver, not the new analytic coupling.
   // P10V has its own directional-derivative unit test.  Full-gradient
   // verification still requires independent H0 P10N finite differences.
   if(result==0)std::cout<<"P10W_DEPENDENCY_SELFTEST_OK"
                          " analytic_coupling_verified=0\n";
#ifdef STAGE3D10DD_FULL4D
   if(result==0){
    p10k::require(ice3d::p10dd::ncell==1200&&
      ice3d::p10dd::nrad==10&&ice3d::p10dd::nmu==10&&
      ice3d::p10dd::nphi==12,
      "P10DD 4D bin dimensions changed");
    std::cout<<"P10DD_FULL4D_BINS_SELFTEST_OK bins=1200 "
      "physical_integration_verified=0\n";
   }
#endif
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
   if(result==0)std::cout<<"P10Y_SHELL_BINS_SELFTEST_OK bins="
                          <<p10n::spatial::bins<<'\n';
#endif
   return result;
  }
  p10k::require(explicit_mesh&&explicit_out,
                "P10W requires explicit --mesh and --out");
  return p10n::run(c,{0.},reuse,cache);
 }catch(const std::exception& e){
  std::cerr<<"P10W_ERROR: "<<e.what()<<'\n';
  return 2;
 }
}
