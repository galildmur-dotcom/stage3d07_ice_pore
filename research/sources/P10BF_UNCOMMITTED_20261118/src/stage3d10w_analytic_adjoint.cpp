// Stage3D-10W: full transient discrete adjoint with analytic Tet10 geometric
// partials. Stage3D10N/P/S remain the independent finite-difference reference.
#define STAGE3D10W_ANALYTIC_SHAPE
#define STAGE3D10P_NO_MAIN
#include "stage3d10p_partial_audit.cpp"

int main(int argc,char** argv){
 try{
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
  ice3d::stage3d10s_manifest::set_arguments(argc,argv);
#endif
  std::vector<char*> filtered{argv[0]};
#ifdef STAGE3D10BD_TEMPORAL_AUDIT
  // The shared legacy P10K parser caps steps at 12. Only the independent
  // P10BD/P10BE targets may exceed that cap. Parse a legal placeholder,
  // then restore the requested count BEFORE the preflight/forward/adjoint.
  char parser_steps_12[]="12";
  int requested_steps_override=0;
#endif
  fs::path reuse,cache;
  bool explicit_mesh=false,explicit_out=false;
  for(int i=1;i<argc;++i){
   const std::string arg=argv[i];
   if(arg=="--help"){
#ifdef STAGE3D10BD_TEMPORAL_AUDIT
#ifdef STAGE3D10BE_TEMPORAL_AUDIT
    std::cout<<"P10BE temporal pilot: steps=36 dt=25 s,"
     " fixed horizon 900 s, identical H2, all-step polar QP contributions.\n";
#else
    std::cout<<"P10BD temporal pilot: (steps,dt)=(6,150),(12,75),"
     "(18,50), fixed horizon 900 s, polar QP contributions for ALL steps.\n";
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
#ifdef STAGE3D10BD_TEMPORAL_AUDIT
   if(arg=="--steps" && i+1<argc &&
      (std::string(argv[i+1])=="18"
#ifdef STAGE3D10BE_TEMPORAL_AUDIT
        ||std::string(argv[i+1])=="36"
#endif
       )){
    requested_steps_override=std::stoi(argv[i+1]);
    filtered.push_back(argv[i]);
    filtered.push_back(parser_steps_12);
    ++i;
    continue;
   }
#endif
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
  auto c=p10k::parse(int(filtered.size()),filtered.data());
#ifdef STAGE3D10BD_TEMPORAL_AUDIT
  if(requested_steps_override)c.steps=requested_steps_override;
#endif
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
#ifdef STAGE3D10Y_ANALYTIC_SHELL_AUDIT
   if(result==0)std::cout<<"P10Y_SHELL_BINS_SELFTEST_OK bins="
                          <<p10n::spatial::bins<<'\n';
#endif
#ifdef STAGE3D10BD_TEMPORAL_AUDIT
   p10k::require(ice3d::p10ba::radial_count==10&&
                 ice3d::p10ba::polar_count==10&&
                 ice3d::p10ba::polar_index(-1.)==0&&
                 ice3d::p10ba::polar_index(1.)==9,
                 "P10BD polar bins selftest failed");
   if(result==0)std::cout<<"P10BD_TEMPORAL_BINS_SELFTEST_OK"
       " allowed_dt=150,75,50 horizon_s=900\n";
#ifdef STAGE3D10BE_TEMPORAL_AUDIT
   if(result==0)std::cout<<"P10BE_TEMPORAL_BINS_SELFTEST_OK"
       " allowed_dt=25 steps=36 horizon_s=900\n";
#endif
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
