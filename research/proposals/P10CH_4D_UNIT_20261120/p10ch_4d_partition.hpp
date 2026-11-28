#pragma once
// P10CH: standalone proposal for a compact, conservative 4D signed partition.
// No FEM solver or Windows project linkage. Physical kernels are supplied by
// an independently verified discrete-adjoint caller, already time-weighted.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <limits>
#include <optional>
#include <stdexcept>
#include <vector>

namespace p10ch {

constexpr double pi = 3.1415926535897932384626433832795;

struct Vec3 { double x{}, y{}, z{}; };

struct Contribution {
  double geom{}, equilibrium{}, history{}, thermal_mass{},
         thermal_diffusion{}, thermal_robin{};
  double sum() const {
    return geom+equilibrium+history+thermal_mass+
           thermal_diffusion+thermal_robin;
  }
  Contribution& operator+=(const Contribution& other) {
    geom+=other.geom; equilibrium+=other.equilibrium;
    history+=other.history; thermal_mass+=other.thermal_mass;
    thermal_diffusion+=other.thermal_diffusion;
    thermal_robin+=other.thermal_robin;
    return *this;
  }
};

struct Geometry {
  Vec3 pore_center{};
  double pore_radius_m{};
  std::vector<double> radial_edges_mm;
  int mu_bands=10;
  int phi_sectors=12;
  int time_steps=6;
};

struct CellIndex {
  int radial{}, mu{}, phi{}, step{};
  bool axis_coordinate=false;
};

inline void validate(const Geometry& g) {
  if(!(g.pore_radius_m>0.)|| !std::isfinite(g.pore_radius_m) ||
     g.radial_edges_mm.size()<2 || g.mu_bands<1 ||
     g.phi_sectors<1 || g.time_steps<1)
    throw std::invalid_argument("P10CH invalid geometry");
  for(std::size_t j=0;j<g.radial_edges_mm.size();++j) {
    if(!std::isfinite(g.radial_edges_mm[j]) ||
       (j==0 && g.radial_edges_mm[j]<0.) ||
       (j>0 && g.radial_edges_mm[j]<=g.radial_edges_mm[j-1]))
      throw std::invalid_argument("P10CH invalid radial edges");
  }
}

// For QP exactly on the polar axis phi is undefined mathematically. Place it
// deterministically into sector zero, and count it for the audit. This is not
// evidence of azimuthal symmetry; actual QP on axis have zero angular volume.
inline std::optional<CellIndex> locate(const Geometry& g,Vec3 x,int step) {
  if(step<1 || step>g.time_steps)throw std::out_of_range("P10CH step");
  const Vec3 d{x.x-g.pore_center.x,x.y-g.pore_center.y,
               x.z-g.pore_center.z};
  if(!std::isfinite(d.x)||!std::isfinite(d.y)||!std::isfinite(d.z))
    throw std::invalid_argument("P10CH nonfinite coordinates");
  const double r=std::hypot(d.x,d.y,d.z);
  if(!(r>0.))throw std::invalid_argument("P10CH undefined radius");
  const double wall_mm=(r-g.pore_radius_m)*1000.;
  if(wall_mm < -1.e-9)throw std::out_of_range("P10CH QP inside pore");
  if(wall_mm>=g.radial_edges_mm.back())return std::nullopt;
  auto iter=std::upper_bound(g.radial_edges_mm.begin(),
      g.radial_edges_mm.end(),std::max(0.,wall_mm));
  const int radial=int(iter-g.radial_edges_mm.begin())-1;
  if(radial<0||radial>=int(g.radial_edges_mm.size()-1))
    throw std::runtime_error("P10CH radial index");
  const double mu=std::clamp(d.z/r,-1.,1.);
  const int mu_band=std::clamp(int(std::floor((mu+1.)*g.mu_bands/2.)),
                               0,g.mu_bands-1);
  const bool axis=(d.x==0. && d.y==0.);
  double phi=axis?0.:std::atan2(d.y,d.x);
  if(phi<0.)phi+=2.*pi;
  if(phi>=2.*pi)phi=0.;
  const int azimuth=std::clamp(int(std::floor(phi*g.phi_sectors/(2.*pi))),
                               0,g.phi_sectors-1);
  return CellIndex{radial,mu_band,azimuth,step-1,axis};
}

struct Bin {
  Contribution value{};
  std::size_t qp_count=0;
  double volume_m3=0.;
};

class Accumulator {
 public:
  explicit Accumulator(Geometry g):g_(std::move(g)) {
    validate(g_);
    const std::size_t count=(g_.radial_edges_mm.size()-1)*
        std::size_t(g_.mu_bands)*std::size_t(g_.phi_sectors)*
        std::size_t(g_.time_steps);
    if(count>5000000)throw std::length_error("P10CH bins over limit");
    bins_.resize(count);boundary_.resize(std::size_t(g_.time_steps));
  }
  void add_volume(Vec3 point,int step,double qp_volume,
                  const Contribution& already_weighted) {
    if(!std::isfinite(qp_volume)||qp_volume<0.)
      throw std::invalid_argument("P10CH QP volume");
    if(!finite(already_weighted))throw std::invalid_argument("P10CH QP contribution");
    const auto k=locate(g_,point,step);
    if(!k) {
      // Outer QP kept separately rather than silently dropped from the audit.
      outside_+=already_weighted; ++outside_count_; return;
    }
    auto& bin=bins_[flatten(*k)];
    bin.value+=already_weighted;bin.volume_m3+=qp_volume;++bin.qp_count;
    if(k->axis_coordinate)++on_axis_count_;
  }
  void add_boundary(int step,const Contribution& already_weighted) {
    if(step<1||step>g_.time_steps || !finite(already_weighted))
      throw std::invalid_argument("P10CH boundary entry");
    boundary_[std::size_t(step-1)]+=already_weighted;
  }
  [[nodiscard]] Contribution total() const {
    Contribution result=outside_;
    for(const auto& bin:bins_)result+=bin.value;
    for(const auto& c:boundary_)result+=c;
    return result;
  }
  [[nodiscard]] double total_signed() const {return total().sum();}
  [[nodiscard]] std::size_t bin_count() const {return bins_.size();}
  [[nodiscard]] std::size_t on_axis_count() const {return on_axis_count_;}
  [[nodiscard]] std::size_t outside_count() const {return outside_count_;}
  [[nodiscard]] const std::vector<Bin>& bins() const {return bins_;}
 private:
  static bool finite(const Contribution& c) {
    return std::isfinite(c.geom)&&std::isfinite(c.equilibrium)&&
           std::isfinite(c.history)&&std::isfinite(c.thermal_mass)&&
           std::isfinite(c.thermal_diffusion)&&std::isfinite(c.thermal_robin);
  }
  std::size_t flatten(const CellIndex& k) const {
    return (((std::size_t(k.step)*(g_.radial_edges_mm.size()-1)+
              std::size_t(k.radial))*std::size_t(g_.mu_bands)+
             std::size_t(k.mu))*std::size_t(g_.phi_sectors)+
            std::size_t(k.phi));
  }
  Geometry g_;
  std::vector<Bin> bins_;
  std::vector<Contribution> boundary_;
  Contribution outside_{};
  std::size_t on_axis_count_=0,outside_count_=0;
};

} // namespace p10ch
