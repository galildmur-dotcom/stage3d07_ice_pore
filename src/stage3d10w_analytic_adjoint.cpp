// Stage3D-10W: full transient discrete adjoint with analytic Tet10 geometric
// partials. Stage3D10N/P/S remain the independent finite-difference reference.
#define STAGE3D10W_ANALYTIC_SHAPE
#define STAGE3D10P_NO_MAIN
#include "stage3d10p_partial_audit.cpp"

int main(int argc,char** argv){
 try{
  std::vector<char*> filtered{argv[0]};
  fs::path reuse,cache;
  bool explicit_mesh=false,explicit_out=false;
  for(int i=1;i<argc;++i){
   const std::string arg=argv[i];
   if(arg=="--help"){
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
   const int result=p10i::run_tests();
   // This tests the inherited reverse solver, not the new analytic coupling.
   // P10V has its own directional-derivative unit test.  Full-gradient
   // verification still requires independent H0 P10N finite differences.
   if(result==0)std::cout<<"P10W_DEPENDENCY_SELFTEST_OK"
                          " analytic_coupling_verified=0\n";
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
