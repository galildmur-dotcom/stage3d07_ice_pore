// P10LI C++ integration fixture: compile against the P10LG opt-in full4D
// header and call the actual P10DD/P10LG writer, never its physical main.
// No FEM invocation, mesh generation, state solve or one-shot marker.
#define STAGE3D10DD_FULL4D 1
#define STAGE3D10DK_M1_FULL4D 1
#include "stage3d10w_analytic_adjoint.cpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace {
namespace fs=std::filesystem;
using ice3d::p10dd::Snapshot;
using ice3d::p10dd::Parts;

void require(bool yes,const char* reason){
 if(!yes)throw std::runtime_error(reason);
}
std::vector<std::string> columns(const std::string& line){
 std::vector<std::string> out;
 std::stringstream stream(line);std::string part;
 while(std::getline(stream,part,','))out.push_back(part);
 return out;
}
void scenario(const fs::path& dir,int steps,int dt){
 fs::create_directories(dir);
 std::vector<Snapshot> mechanical{std::size_t(steps)};
 std::vector<Snapshot> thermal{std::size_t(steps)};
 Parts ref{};
 double expected_geometry=0.,expected_stress=0.;
 for(int i=0;i<steps;++i){
  // Every step has two occupied bins and two nonzero signed contributions.
  const double scale=double(i+1)/double(steps);
  auto& a=mechanical[std::size_t(i)].cells[0];
  auto& b=mechanical[std::size_t(i)].cells[1];
  a.explicit_geometry=.30*scale;a.explicit_stress=-.10*scale;
  b.explicit_geometry=-.20*scale;b.explicit_stress=.05*scale;
  for(auto* cell:{&a,&b})
   cell->part.explicit_objective=cell->explicit_geometry+cell->explicit_stress;
  expected_geometry+=a.explicit_geometry+b.explicit_geometry;
  expected_stress+=a.explicit_stress+b.explicit_stress;
  ref.explicit_objective+=a.part.explicit_objective+b.part.explicit_objective;
 }
 ice3d::p10dd::write_csv(dir,"P10LI_SYNTH",steps,dt,mechanical,thermal,ref);

 std::ifstream file(dir/"P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv");
 require(bool(file),"missing P10LG split CSV");
 std::string line;std::getline(file,line);
 require(line=="mesh,step,time_end_s,radial_bin,mu_bin,phi_bin,"
                "explicit_geometry_normalization_per_m,explicit_stress_chain_per_m,"
                "explicit_sum_per_m","split CSV schema changed");
 std::size_t rows=0,nonzero_bins=0;
 double geometry=0.,stress=0.,original=0.;
 while(std::getline(file,line)){
  const auto cells=columns(line);
  require(cells.size()==9,"split CSV wrong number of columns");
  require(cells[0]=="P10LI_SYNTH","split CSV wrong mesh label");
  const int step=std::stoi(cells[1]);
  require(step>=1&&step<=steps,"invalid step index");
  require(std::stoi(cells[2])==step*dt,"wrong time stamp");
  const int ir=std::stoi(cells[3]),im=std::stoi(cells[4]),ip=std::stoi(cells[5]);
  require(ir>=0&&ir<10&&im>=0&&im<10&&ip>=0&&ip<12,"invalid bin index");
  const double g=std::stod(cells[6]),s=std::stod(cells[7]),o=std::stod(cells[8]);
  require(std::abs((g+s)-o)<1e-14,"split row lost closure");
  if(g!=0.||s!=0.)++nonzero_bins;
  geometry+=g;stress+=s;original+=o;++rows;
 }
 require(rows==std::size_t(steps)*1200,"split CSV incomplete");
 require(nonzero_bins==std::size_t(steps)*2,"nonzero bin count incorrect");
 require(std::abs(geometry-expected_geometry)<1e-12,"wrong geometry column");
 require(std::abs(stress-expected_stress)<1e-12,"wrong stress column");
 require(std::abs(original-ref.explicit_objective)<1e-12,"wrong explicit total");
 std::ifstream base(dir/"P10DD_SIGNED_R_THETA_PHI_T.csv");
 require(bool(base),"original P10DD CSV missing");
 std::size_t lines=0;
 while(std::getline(base,line))++lines;
 require(lines==std::size_t(steps)*1201+1,"original P10DD row count changed");
 std::cout<<"P10LI_CPP_WRITER_PASS grid="<<steps<<'x'<<dt
          <<" rows="<<rows<<" nonzero_bins="<<nonzero_bins
          <<" geometry="<<geometry<<" stress="<<stress<<'\n';

 // Negative test: this MUST throw in the real writer; it ensures that
 // corruption in a cell is not silently accepted in sidecar serialization.
 auto corrupt=mechanical;
 corrupt[0].cells[1].explicit_stress+=.125;
 bool stopped=false;
 try{ice3d::p10dd::write_csv(dir,"P10LI_BAD",steps,dt,corrupt,thermal,ref);}
 catch(const std::runtime_error&){stopped=true;}
 require(stopped,"writer failed to reject corrupt cell closure");
 std::cout<<"P10LI_CPP_NEGATIVE_CLOSURE_STOP_PASS grid="<<steps<<'x'<<dt<<'\n';
}
}

int main(){
 const auto root=fs::temp_directory_path()/"p10li_cpp_writer_csv_output";
 // Distinct subdirectories contain only test-produced CSVs. Never touch
 // any physical data, mesh, run markers or native production executable.
 try{
  scenario(root/"6x150",6,150);
  scenario(root/"36x25",36,25);
  std::cout<<"P10LI_CPP_SOURCE_ONLY_ALL_PASS no_FEM=1\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P10LI_CPP_SOURCE_ONLY_FAIL "<<e.what()<<'\n';return 1;
 }
}
