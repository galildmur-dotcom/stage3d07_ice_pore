// Stage3D-10S. Adds a QP/shell decomposition to the ORIGINAL P10P adjoint
// sweep using a compile-time flag; P10P itself retains its old behaviour.
#define STAGE3D10S_SPATIAL_AUDIT
#define STAGE3D10P_NO_MAIN
#include "stage3d10p_partial_audit.cpp"

int main(int argc,char**argv){
 try{
  ice3d::stage3d10s_manifest::set_arguments(argc,argv);
  std::string delta_csv;
  fs::path reuse,cache;
  std::vector<char*> filtered{argv[0]};
  bool explicit_mesh=false,explicit_out=false;
  for(int i=1;i<argc;++i){
   const std::string flag=argv[i];
   if(flag=="--help"){
    std::cout<<"stage3d10s_spatial_partial --mesh MSH --out NEW_DIR "
       "--steps 6 --dt 150 --mode y20 --delta-scan-um 2.5 "
       "--reuse-forward EXISTING_FORWARD_CACHE --threads 4 "
       "[--preflight] [--geometry-exe EXE] [--cutoff-mm 5] [--selftest]\n";
    return 0;
   }
   if(flag=="--delta-scan-um"||flag=="--reuse-forward"||
      flag=="--forward-cache"){
    p10k::require(i+1<argc,"P10S missing value after "+flag);
    const std::string value=argv[++i];
    if(flag=="--delta-scan-um")delta_csv=value;
    else if(flag=="--reuse-forward")reuse=value;
    else cache=value;
   }else{
    if(flag=="--mesh")explicit_mesh=true;
    if(flag=="--out")explicit_out=true;
    filtered.push_back(argv[i]);
   }
  }
  auto c=p10k::parse(int(filtered.size()),filtered.data());
#ifdef _OPENMP
  omp_set_dynamic(0);omp_set_num_threads(c.threads);
#endif
  if(c.selftest){
   p10k::require(p10n::spatial::shell(-1.e-5)==0,
      "P10S negative roundoff at sphere");
   p10k::require(p10n::spatial::shell(.019999)==0&&
       p10n::spatial::shell(.02)==1&&
       p10n::spatial::shell(.1)==3&&
       p10n::spatial::shell(15.)==9,
      "P10S radial shell mapping");
   std::cout<<"P10S_SPATIAL_BINS_SELFTEST_OK bins="
            <<p10n::spatial::bins<<'\n';
   return 0;
  }
  p10k::require(explicit_mesh&&explicit_out,
                 "P10S requires --mesh and --out");
  p10k::require(!delta_csv.empty(),"P10S requires --delta-scan-um");
  return p10n::run(c,p10n::parse_deltas(delta_csv),reuse,cache);
 }catch(const std::exception& e){
  std::cerr<<"P10S_ERROR: "<<e.what()<<'\n';
  return 2;
 }
}
