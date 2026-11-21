// A synthetic-only partition regression. Does not read a mesh or solve a FEM.
#include "stage3d10n_base_m_impl.inc"
#include "stage3d10v_analytic_shape.hpp"
#include "stage3d10dd_4d_partition.hpp"

int main(){
 try{
  namespace d=ice3d::p10dd;
  // Geometric directions near the northern and southern poles, phi seam,
  // radial half-open edges and an exact zero-azimuth axis point.
  const V c{0.,0.,.03};
  auto cell=d::index(c+V{.001,0.,0.});
  if(cell!=std::size_t((0*d::nmu+5)*d::nphi+6))
   throw std::runtime_error("P10DD phi=0 mapping failed");
  cell=d::index(c+V{-.001,0.,0.});
  if(cell!=std::size_t((0*d::nmu+5)*d::nphi+0))
   throw std::runtime_error("P10DD phi seam mapping failed");
  bool axis=false;
  cell=d::index(c+V{0.,0.,.001},&axis);
  if(!axis||cell!=std::size_t((0*d::nmu+9)*d::nphi+0))
   throw std::runtime_error("P10DD pole/axis mapping failed");
  std::vector<d::Snapshot> m(6),h(6);
  for(int i=0;i<6;++i){
   auto& x=m[std::size_t(i)].cells[0];
   x.part.explicit_objective=0.1;
   x.part.equilibrium=-0.3;
   x.part.history=0.5;
   auto& y=h[std::size_t(i)].cells[0];
   y.part.mass=-0.04;
   y.part.diffusion=0.01;
   h[std::size_t(i)].top_robin.robin=0.005;
  }
  d::Parts ref;
  ref.explicit_objective=.6;ref.equilibrium=-1.8;
  ref.history=3.;ref.mass=-.24;ref.diffusion=.06;ref.robin=.03;
  // Check signed component and thermal closure before any output is written.
  d::expect_close(ref.mechanical(),1.8,"synthetic mechanical");
  d::expect_close(ref.thermal(),-.15,"synthetic thermal");
  const auto p=std::filesystem::temp_directory_path()/
    "P10DD_4D_SYNTHETIC_NOT_A_PHYSICAL_RUN";
  if(std::filesystem::exists(p))
   throw std::runtime_error("P10DD unit target exists; never overwrite");
  std::filesystem::create_directory(p);
  d::write_csv(p,"SYNTHETIC",6,150,m,h,ref);
  std::filesystem::remove(p/"P10DD_SIGNED_R_THETA_PHI_T.csv");
  std::filesystem::remove(p/"P10DD_FULL4D_CLOSURE_AUDIT.csv");
  std::filesystem::remove(p);
  bool rejected=false;
  try{d::expect_close(0.,1.,"negative closure test");}
  catch(const std::runtime_error&){rejected=true;}
  if(!rejected)throw std::runtime_error("P10DD negative closure not detected");
  std::cout<<"P10DD_4D_SYNTHETIC_UNIT_OK bins=1200 steps=6 "
              "negative_test=PASS physical_FEM=0\n";
  return 0;
 }catch(const std::exception& e){
  std::cerr<<"P10DD_4D_SYNTHETIC_UNIT_STOP: "<<e.what()<<'\n';
  return 2;
 }
}
