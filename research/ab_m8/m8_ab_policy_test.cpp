#include "m8_ab_quadrature_policy.hpp"
#include <cassert>
#include <iostream>

int main() {
    using namespace stage3d07::m8ab;
    // Real accepted M8/P10RA zero-based Tet10 ordinals, not manufactured IDs.
    const Pilot p{{3773,3846,3935,3945,3967,4042,4095,4333,4737,4756,5046,
                   5069,5147,6135,7326,7329,7330,8115,8116,9926,9928,11737,
                   11740,4265,4723,5125,5128,5234,6885,7616,7643,7644,7662,
                   7665,8386,9013,9025,9026,9681,10916,11025,11026,11028,11965},
                  {6143,6705,4378,9712}};
    const Routing r(p);
    std::size_t gauss_a=0, gauss_b=0, algoim_b=0;
    for (std::size_t id=0; id<mesh_tets; ++id) {
        // Synthetic "all-core-is-cut" classifier is a routing test ONLY.
        gauss_a += r.rule(Variant::A,id,true)==Rule::Gauss27;
        gauss_b += r.rule(Variant::B,id,true)==Rule::Gauss27;
        algoim_b += r.rule(Variant::B,id,true)==Rule::AlgoimCut;
    }
    assert(gauss_a==12546 && gauss_b==12502 && algoim_b==44);
    int chosen=-1;
    dispatch(r,Variant::B,3773,true,[&](auto){chosen=0;return 0;},
             [&](auto){chosen=1;return 0;});
    assert(chosen==1);
    dispatch(r,Variant::B,6143,true,[&](auto){chosen=0;return 0;},
             [&](auto){chosen=1;return 0;});
    assert(chosen==0);
    dispatch(r,Variant::B,3773,false,[&](auto){chosen=0;return 0;},
             [&](auto){chosen=1;return 0;});
    assert(chosen==0);
    std::cout<<"P10RE_M8_ROUTING_SELFTEST_PASS A_GAUSS="<<gauss_a
             <<" B_GAUSS="<<gauss_b<<" B_ALGOIM="<<algoim_b
             <<" TEST_ONLY_ALL_CORE_CUT=1 NO_FEM=1 NO_PHYSICAL_AB=1\n";
}
