// Stage 3D-06-P2: standalone matrix-vector benchmark on REAL mesh topology.
// Does not change E/ED/EDV constitutive laws or j6.
#define STAGE3D06_LIBRARY
#include "../src/mechanical.cpp"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#ifdef _OPENMP
#include <omp.h>
#endif

int main(int argc,char**argv){try{
 std::string mesh,report;int repeats=8,threads=1;double tol=1e-12;
 for(int i=1;i<argc;++i){std::string arg=argv[i];
  auto val=[&](){if(i+1>=argc)throw std::runtime_error("missing value after "+arg);return std::string(argv[++i]);};
  if(arg=="--mesh")mesh=val();
  else if(arg=="--repeats")repeats=std::stoi(val());
  else if(arg=="--threads")threads=std::stoi(val());
  else if(arg=="--tolerance")tol=std::stod(val());
  else if(arg=="--csv")report=val();
  else if(arg=="--help"){std::cout<<"--mesh H0.msh --repeats 10 --threads 1|2|4|8 --tolerance 1e-12 --csv report.csv\n";return 0;}
  else throw std::runtime_error("unknown option: "+arg);
 }
 if(mesh.empty()||repeats<=0||threads<=0||threads>32||tol<0)throw std::runtime_error("invalid options");
 #ifdef _OPENMP
 omp_set_dynamic(0);omp_set_num_threads(threads);
 #else
 if(threads!=1)throw std::runtime_error("OpenMP not enabled");
 #endif
 const auto imported=read_msh(mesh);
 const Mesh&m=imported.mesh;
 const auto topo=build_bcsr_topology(m);
 BCSR A;A.set_topology(topo);
 const size_t n=m.nodes.size(),nnz=A.a.size();
 std::vector<uint8_t>bc(3*n,0);
 // Deliberately stress all three possible component combinations.
 for(size_t i=0;i<n;++i){
  if(i%37==0)bc[3*i]=1;
  if(i%71==0)bc[3*i+1]=1;
  if(i%113==0)bc[3*i+2]=1;
 }
 std::vector<double>x(3*n);
 for(size_t i=0;i<3*n;++i){
  x[i]=bc[i]?0.0:std::sin(double(i)*0.0047)+std::cos(double(i)*0.0011);
 }
 for(size_t p=0;p<nnz;++p)for(int j=0;j<9;++j)
  A.a[p][j]=double(int((p*13+size_t(j)*7)%97)-48)*0.00013;
 std::vector<double>out_ref,out_opt;
 // Semantic regression: verify outputs under the projected-vector precondition.
 A.mul_legacy(x,out_ref,bc);
 A.mul_projected(x,out_opt,bc);
 double maxref=0,maxdiff=0,diff2=0;
 for(size_t i=0;i<out_ref.size();++i){
  maxref=std::max(maxref,std::abs(out_ref[i]));
  maxdiff=std::max(maxdiff,std::abs(out_opt[i]-out_ref[i]));
  diff2+=(out_opt[i]-out_ref[i])*(out_opt[i]-out_ref[i]);
 }
 const double error=(maxref?maxdiff/maxref:maxdiff);
 if(error>tol || !std::isfinite(error))throw std::runtime_error("SpMV mismatch: "+std::to_string(error));
 // Safety regression: the reference operator MUST still exclude constrained
 // input DOFs even if the caller supplies nonzero values at these entries.
 const auto first=std::find(bc.begin(),bc.end(),uint8_t{1});
 if(first!=bc.end()){
  auto xnonzero=x; xnonzero[size_t(first-bc.begin())]=1000.0;
  std::vector<double>legacyNonzero;
  A.mul_legacy(xnonzero,legacyNonzero,bc);
  for(size_t k=0;k<legacyNonzero.size();++k){
   if(!bc[k] && legacyNonzero[k]!=out_ref[k])
    throw std::runtime_error("legacy operator changed for a constrained input");
  }
 }
 // Force output to be observed; measurements exclude matrix construction.
 auto benchmark=[&](bool projected){
  std::vector<double>out;double sum=0;
  const auto start=Clock::now();
  for(int k=0;k<repeats;++k){
   if(projected)A.mul_projected(x,out,bc);else A.mul_legacy(x,out,bc);
   sum+=out[size_t((k*131)%out.size())];
  }
  const double seconds=std::chrono::duration<double>(Clock::now()-start).count();
  if(!std::isfinite(sum))throw std::runtime_error("benchmark nonfinite sum");
  return seconds/repeats;
 };
 // Warm both kernels to reduce page fault bias, interleave measurements.
 A.mul_legacy(x,out_ref,bc);A.mul_projected(x,out_opt,bc);
 const double legacy0=benchmark(false),projected0=benchmark(true);
 const double projected1=benchmark(true),legacy1=benchmark(false);
 const double legacy=(legacy0+legacy1)/2, projected=(projected0+projected1)/2;
 const double speedup=legacy/projected;
 std::cout<<std::setprecision(12)
          <<"P2 SpMV "<<std::filesystem::path(mesh).filename().string()
          <<" nodes="<<n<<" blocks="<<nnz<<" threads="<<threads
          <<" repeats="<<repeats<<"\n"
          <<"  normalized_max_diff="<<error<<" (limit "<<tol<<") PASS\n"
          <<"  legacy_s_per_spmv="<<legacy<<" projected_s_per_spmv="<<projected
          <<" speedup="<<speedup<<"x\n";
 if(!report.empty()){
  const bool exists=std::filesystem::is_regular_file(report)&&std::filesystem::file_size(report)>0;
  std::ofstream csv(report,std::ios::app);
  if(!exists)csv<<"mesh,nodes,blocks,threads,repeats,legacy_s,projected_s,speedup,max_normalized_difference,status\n";
  csv<<std::setprecision(17)<<std::filesystem::path(mesh).stem().string()<<','<<n<<','<<nnz<<','<<threads<<','<<repeats<<','<<legacy<<','<<projected<<','<<speedup<<','<<error<<",PASS\n";
 }
 return 0;
 }catch(const std::exception&e){std::cerr<<"P2 SpMV FAILED: "<<e.what()<<'\n';return 2;}
}
