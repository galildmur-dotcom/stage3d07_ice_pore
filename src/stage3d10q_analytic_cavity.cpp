#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>

// Independent Stage3D-10Q benchmark. No FEM solve and no dependence on project internals.
// References: Southwell & Gough (1926), Goodier (1933),
// https://www.solids4foam.com/tutorials/more-tutorials/solid-mechanics/linearElasticity/sphericalCavity.html

namespace fs = std::filesystem;

struct Config {
    double a_mm = 1.0;
    double nu = 0.3;
    double s_mpa = 1.0;
    double rmax_mm = 3.0;
    double dr_mm = 0.005;
    double h4_mm = 0.1753978957801;
    double h4w2_mm = 0.088512585913179;
    fs::path out = ".";
};

// Cylindrical coordinates (rho,phi,z), rho=sqrt(x*x+y*y).
struct Stress {
    double rrho = 0.0;
    double pphi = 0.0;
    double zz = 0.0;
    double zrho = 0.0;
};

static Stress uniaxial(double rho, double z, double a, double nu, double s) {
    const double R = std::hypot(rho, z);
    if (!(R >= a * (1.0 - 1e-13)) || !(a > 0.0)) {
        throw std::runtime_error("Stress requested inside pore or invalid radius");
    }
    const double D = 14.0 - 10.0 * nu;
    const double x = a / R;
    const double x2 = x * x;
    const double x3 = x2 * x;
    const double q = rho * rho / (R * R);
    const double p = s * x3 / D;
    const double rrho = p * (9.0 - 15.0 * nu - 12.0 * x2
        - q * (72.0 - 15.0 * nu - 105.0 * x2)
        + 15.0 * q * q * (5.0 - 7.0 * x2));
    const double pphi = p * (9.0 - 15.0 * nu - 12.0 * x2
        - 15.0 * q * (1.0 - 2.0 * nu - x2));
    const double zz = s - p * (38.0 - 10.0 * nu - 24.0 * x2
        - q * (117.0 - 15.0 * nu - 120.0 * x2)
        + 15.0 * q * q * (5.0 - 7.0 * x2));
    const double zrho = p * (rho / R) * (z / R)
        * (-3.0 * (19.0 - 5.0 * nu) + 60.0 * x2
        + 15.0 * q * (5.0 - 7.0 * x2));
    return {rrho, pphi, zz, zrho};
}

static Stress hydrostatic(double r, double a, double s) {
    if (!(r >= a) || !(a > 0.0)) {
        throw std::runtime_error("Hydrostatic stress requested inside pore");
    }
    const double x3 = std::pow(a / r, 3);
    // In spherical coordinates: rrho -> sigma_rr, pphi -> sigma_tangential.
    return {s * (1.0 - x3), s * (1.0 + 0.5 * x3),
            s * (1.0 + 0.5 * x3), 0.0};
}

// On the equator z=0, sigma_zz is the largest principal tensile stress.
static double sigma_peak_equator(double r, double a, double nu, double s) {
    const double D = 14.0 - 10.0 * nu;
    const double x = a / r;
    const double x3 = x * x * x;
    return s * (1.0 + (4.0 - 5.0 * nu) / D * x3
        + 9.0 / D * x3 * x * x);
}

static double d_sigma_dr(double r, double a, double nu, double s) {
    const double D = 14.0 - 10.0 * nu;
    const double x = a / r;
    const double x2 = x * x;
    const double x4 = x2 * x2;
    return -s / a * (3.0 * (4.0 - 5.0 * nu) / D * x4
        + 45.0 / D * x4 * x2);
}

static double d_sigma_da_fixed_r(double r, double a, double nu, double s) {
    const double D = 14.0 - 10.0 * nu;
    const double x = a / r;
    const double x3 = x * x * x;
    return s / a * (3.0 * (4.0 - 5.0 * nu) / D * x3
        + 45.0 / D * x3 * x * x);
}

static void require(bool ok, const std::string& reason) {
    if (!ok) throw std::runtime_error("SELFTEST FAILED: " + reason);
}

static void selftest(const Config& c) {
    const double a = c.a_mm;
    const double s = c.s_mpa;
    // Check full 3D analytical solution: traction of spherical wall vanishes.
    double max_boundary_traction = 0.0;
    for (int i = 0; i <= 80; ++i) {
        const double theta = std::acos(-1.0) * static_cast<double>(i) / 80.0;
        const double rho = a * std::sin(theta);
        const double z = a * std::cos(theta);
        const auto t = uniaxial(rho, z, a, c.nu, s);
        const double tr = t.rrho * std::sin(theta) + t.zrho * std::cos(theta);
        const double tz = t.zrho * std::sin(theta) + t.zz * std::cos(theta);
        max_boundary_traction = std::max(max_boundary_traction, std::hypot(tr, tz));
    }
    require(max_boundary_traction / s < 1e-12, "uniaxial wall traction");

    const auto ueq = uniaxial(a, 0.0, a, c.nu, s);
    require(std::abs(ueq.rrho) / s < 1e-12, "uniaxial equator sigma_rr");
    require(std::abs(ueq.zz - sigma_peak_equator(a, a, c.nu, s)) / s < 1e-12,
        "uniaxial equator simplification");
    require(std::abs(hydrostatic(a, a, s).rrho) / s < 1e-12,
        "hydrostatic wall traction");

    for (double ratio : {1.001, 1.05, 1.1, 1.5, 2.0}) {
        const double r = a * ratio;
        const auto t = uniaxial(r, 0.0, a, c.nu, s);
        require(std::abs(t.zz - sigma_peak_equator(r, a, c.nu, s)) / s < 1e-12,
            "uniaxial equator stress profile");
        const double h = a * 1e-5;
        const double fd_r = (sigma_peak_equator(r+h, a, c.nu, s)
            - sigma_peak_equator(r-h, a, c.nu, s)) / (2.0*h);
        const double fd_a = (sigma_peak_equator(r, a+h, c.nu, s)
            - sigma_peak_equator(r, a-h, c.nu, s)) / (2.0*h);
        require(std::abs(fd_r - d_sigma_dr(r, a, c.nu, s)) < 1e-8 * s/a,
            "radial derivative FD");
        require(std::abs(fd_a - d_sigma_da_fixed_r(r, a, c.nu, s)) < 1e-8 * s/a,
            "shape partial FD");
    }

    const double grad_sum = d_sigma_da_fixed_r(a, a, c.nu, s)
        + d_sigma_dr(a, a, c.nu, s);
    require(std::abs(grad_sum) < 1e-12 * s/a, "moving wall derivative cancellation");
    const double h = a * 1e-4;
    const double moving_fd = (sigma_peak_equator(a+h, a+h, c.nu, s)
        - sigma_peak_equator(a-h, a-h, c.nu, s)) / (2.0*h);
    require(std::abs(moving_fd) < 1e-12 * s/a, "moving wall total derivative FD");
    std::cout << std::scientific << std::setprecision(12)
              << "P10Q_ANALYTIC_SELFTEST_OK wall_traction_rel="
              << max_boundary_traction / s
              << " equator_wall_concentration="
              << sigma_peak_equator(a,a,c.nu,s)/s
              << " d_sigma_dr_wall_MPa_per_mm=" << d_sigma_dr(a,a,c.nu,s)
              << " moving_wall_dsigma_da=" << grad_sum << '\n';
}

static double read_value(int& i, int argc, char** argv, const std::string& key) {
    if (i + 1 >= argc) throw std::runtime_error("Missing value for " + key);
    const double x = std::stod(argv[++i]);
    if (!std::isfinite(x)) throw std::runtime_error("Non-finite value for " + key);
    return x;
}

static Config parse_args(int argc, char** argv) {
    Config c;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--a-mm") c.a_mm = read_value(i, argc, argv, arg);
        else if (arg == "--nu") c.nu = read_value(i, argc, argv, arg);
        else if (arg == "--s-mpa") c.s_mpa = read_value(i, argc, argv, arg);
        else if (arg == "--rmax-mm") c.rmax_mm = read_value(i, argc, argv, arg);
        else if (arg == "--dr-mm") c.dr_mm = read_value(i, argc, argv, arg);
        else if (arg == "--h4-mm") c.h4_mm = read_value(i, argc, argv, arg);
        else if (arg == "--h4w2-mm") c.h4w2_mm = read_value(i, argc, argv, arg);
        else if (arg == "--out") {
            if (i + 1 >= argc) throw std::runtime_error("Missing value for --out");
            c.out = argv[++i];
        } else if (arg == "--help") {
            std::cout << "stage3d10q_analytic_cavity --a-mm 1 --nu 0.3 --s-mpa 1 "
              << "--rmax-mm 3 --dr-mm 0.005 --out <folder>\n";
            std::exit(0);
        } else throw std::runtime_error("Unknown argument: " + arg);
    }
    if (!(c.a_mm > 0.0 && c.s_mpa > 0.0 && c.rmax_mm >= c.a_mm
        && c.dr_mm > 0.0 && c.nu > -0.9 && c.nu < 0.5
        && c.h4_mm > 0.0 && c.h4w2_mm > 0.0)) {
        throw std::runtime_error("Invalid physical or sampling parameters");
    }
    if ((c.rmax_mm - c.a_mm)/c.dr_mm > 1000000.0)
        throw std::runtime_error("More than one million profile samples requested");
    return c;
}

static void export_profile(const Config& c) {
    const fs::path name = c.out / "P10Q_ANALYTIC_PROFILE.csv";
    std::ofstream o(name);
    if (!o) throw std::runtime_error("Could not create " + name.string());
    o << std::scientific << std::setprecision(14);
    o << "r_mm,distance_from_pore_mm,r_over_a,sigma1_equator_MPa," 
      << "sigma1_over_S,d_sigma1_dr_MPa_per_mm,d_sigma1_da_fixed_r_MPa_per_mm," 
      << "hydro_sigma_rr_MPa,hydro_sigma_tangential_MPa,p8_relative_wall_weight\n";
    const int n = static_cast<int>(std::ceil((c.rmax_mm - c.a_mm) / c.dr_mm));
    const double wall_sigma = sigma_peak_equator(c.a_mm, c.a_mm, c.nu, c.s_mpa);
    for (int i = 0; i <= n; ++i) {
        const double r = std::min(c.rmax_mm, c.a_mm + i * c.dr_mm);
        const double sig = sigma_peak_equator(r, c.a_mm, c.nu, c.s_mpa);
        const auto hs = hydrostatic(r, c.a_mm, c.s_mpa);
        o << r << ',' << r-c.a_mm << ',' << r/c.a_mm << ',' << sig << ','
          << sig/c.s_mpa << ',' << d_sigma_dr(r,c.a_mm,c.nu,c.s_mpa) << ','
          << d_sigma_da_fixed_r(r,c.a_mm,c.nu,c.s_mpa) << ','
          << hs.rrho << ',' << hs.pphi << ',' << std::pow(wall_sigma/sig,7) << '\n';
    }
}

static void export_mesh_scale(const Config& c) {
    const fs::path name = c.out / "P10Q_MESH_SCALE.csv";
    std::ofstream o(name);
    if (!o) throw std::runtime_error("Could not create " + name.string());
    o << std::scientific << std::setprecision(14);
    o << "mesh,median_near_wall_edge_mm,h_over_a,radial_distance_proxy_mm," 
      << "sigma1_at_a_plus_h_over_S,loss_vs_wall_percent,p8_weight_wall_to_a_plus_h\n";
    const double sw = sigma_peak_equator(c.a_mm,c.a_mm,c.nu,c.s_mpa);
    for (const auto& [name,h] : std::array<std::pair<const char*,double>,2>{
            {{"H4",c.h4_mm},{"H4W2",c.h4w2_mm}}}) {
        const double sh = sigma_peak_equator(c.a_mm+h,c.a_mm,c.nu,c.s_mpa);
        o << name << ',' << h << ',' << h/c.a_mm << ',' << h << ','
          << sh/c.s_mpa << ',' << 100.0*(sw-sh)/sw << ','
          << std::pow(sw/sh,7) << '\n';
    }
}

int main(int argc, char** argv) {
    try {
        const Config c = parse_args(argc, argv);
        selftest(c);
        fs::create_directories(c.out);
        export_profile(c);
        export_mesh_scale(c);
        std::cout << "P10Q_ANALYTIC_BENCHMARK_OK output=" << c.out.string()
                  << " finite_difference_forward_solves=0 fem_solves=0\n";
    } catch (const std::exception& e) {
        std::cerr << "P10Q_ERROR: " << e.what() << '\n';
        return 2;
    }
}
