#include "p10ch_4d_partition.hpp"
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>

static void check(bool condition,const char* why) {
 if(!condition)throw std::runtime_error(why);
}

int main() {
 try {
  using namespace p10ch;
  Geometry geometry{{0.,0.,0.},.001,{0.,.02,.05,.1},10,12,3};
  Accumulator cells(geometry);
  check(cells.bin_count()==3u*10u*12u*3u,"bin count");
  const auto test=[&](Vec3 pt,int step,int mu,int phi,int radial) {
    auto i=locate(geometry,pt,step);
    check(i.has_value(),"test QP missing");
    check(i->mu==mu&&i->phi==phi&&i->radial==radial,"angular/radial sector");
  };
  // Use r=1.03 mm: d=0.03 mm, in radial bin 1.
  test({0.,0.,.00103},1,9,0,1);
  test({0.,0.,-.00103},3,0,0,1);
  test({.00103,0.,0.},1,5,0,1);
  test({0.,.00103,0.},1,5,3,1);
  test({-.00103,0.,0.},1,5,6,1);
  test({0.,-.00103,0.},1,5,9,1);
  check(!locate(geometry,{.003,0.,0.},2).has_value(),"outside support");
  double reference=0.;
  for(int step=1;step<=3;++step) {
   for(int mu=0;mu<10;++mu) {
    const double zmu=-.9+.2*mu;
    for(int az=0;az<12;++az) {
      const double phi=2.*pi*(double(az)+.25)/12.;
      const double radial=std::sqrt(1.-zmu*zmu);
      const double r=.00103;
      const Vec3 x{r*radial*std::cos(phi),
                   r*radial*std::sin(phi),r*zmu};
      const double signed_v=1e-5*std::sin(double(step+mu+az));
      const Contribution c{signed_v,-.75*signed_v,.2*signed_v,
                           .04*signed_v,-.05*signed_v,0.};
      cells.add_volume(x,step,1e-12,c);
      reference+=c.sum();
    }
   }
  }
  cells.add_volume({0.,0.,.00103},1,1e-12,
                   Contribution{1e-7,-1e-7,0.,0.,0.,0.});
  cells.add_volume({.003,0.,0.},1,1e-12,
                   Contribution{2e-7,0.,0.,0.,0.,0.});
  reference+=2e-7;
  cells.add_boundary(1,Contribution{0.,0.,0.,0.,0.,-3e-7});
  reference-=3e-7;
  check(cells.on_axis_count()==1,"axis audit");
  check(cells.outside_count()==1,"outside partition");
  check(std::abs(cells.total_signed()-reference)<1e-15,"global 4D conservation");
  std::cout<<std::setprecision(16)
           <<"P10CH_4D_SYNTHETIC_UNIT_OK bins="<<cells.bin_count()
           <<" steps=3 polar=10 phi=12 axis="<<cells.on_axis_count()
           <<" outside="<<cells.outside_count()
           <<" signed_total="<<cells.total_signed()
           <<" conservation_abs="<<std::abs(cells.total_signed()-reference)
           <<" FEM=0\n";
  return 0;
 } catch(const std::exception& e) {
  std::cerr<<"P10CH_4D_SYNTHETIC_STOP: "<<e.what()<<'\n';
  return 2;
 }
}
