#pragma once
// Stage3D07 P10RE: shared A/B quadrature-routing contract for accepted M8.
// This file does not implement Algoim or falsely substitute a high-order Gauss rule.
#include <array>
#include <cstddef>
#include <stdexcept>
#include <vector>

namespace stage3d07::m8ab {
constexpr std::size_t mesh_tets = 12546;
constexpr std::size_t gauss_qp_per_tet = 27;
constexpr int steps = 36;
constexpr int dt_seconds = 25;
constexpr double cutoff_mm = 5.0;

enum class Rule { Gauss27, AlgoimCut };
enum class Variant { A, B };

// This is the immutable ordinal list from P10RA selection, not Gmsh element IDs.
struct Pilot {
    std::vector<std::size_t> polar_core;
    std::vector<std::size_t> controls;
};

class Routing {
public:
    explicit Routing(const Pilot& pilot): is_core_(mesh_tets, false),
                                            is_control_(mesh_tets, false) {
        if (pilot.polar_core.size() != 44 || pilot.controls.size() != 4)
            throw std::invalid_argument("P10RE requires exactly 44+4 P10RA Tet10");
        for (auto id: pilot.polar_core) {
            if (id >= mesh_tets || is_core_[id])
                throw std::invalid_argument("duplicate/out-of-range core Tet10");
            is_core_[id] = true;
        }
        for (auto id: pilot.controls) {
            if (id >= mesh_tets || is_core_[id] || is_control_[id])
                throw std::invalid_argument("duplicate/overlapping control Tet10");
            is_control_[id] = true;
        }
    }

    [[nodiscard]] Rule rule(Variant v, std::size_t tet_ordinal,
                            bool actually_intersects_cut) const {
        if (tet_ordinal >= mesh_tets) throw std::out_of_range("Tet10 ordinal");
        return v == Variant::B && is_core_[tet_ordinal] && actually_intersects_cut
            ? Rule::AlgoimCut : Rule::Gauss27;
    }

    [[nodiscard]] bool is_pilot(std::size_t id) const {
        if (id >= mesh_tets) throw std::out_of_range("Tet10 ordinal");
        return is_core_[id] || is_control_[id];
    }

private:
    std::vector<bool> is_core_, is_control_;
};

// The physics runner must supply concrete quadrature points and weights,
// constitutive replay at *each* new point, and consistent forward/adjoint
// assembly. The interface intentionally has NO silent Gauss fallback.
template<class Gauss, class Algoim>
decltype(auto) dispatch(const Routing& routing, Variant variant, std::size_t id,
                        bool actually_intersects_cut,
                        Gauss&& gauss, Algoim&& algoim) {
    if (routing.rule(variant, id, actually_intersects_cut) == Rule::AlgoimCut)
        return algoim(id);
    return gauss(id);
}
} // namespace stage3d07::m8ab
