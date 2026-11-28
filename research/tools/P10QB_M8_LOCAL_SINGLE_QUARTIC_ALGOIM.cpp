// Stage3D07 P10QB: true Algoim/LAPACKE on curved child Tet10 of accepted M8.
// Input generated from exact quadratic restriction of original M8, source-only.
// Only one genuinely active physical quartic; all other boundaries certified
// inside by direct Bernstein signs. Plus the reference simplex constraint.
// No CAD, Gmsh, mesh edits, FEM, EDV or adjoint.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include "quadrature_multipoly.hpp"

using V = algoim::uvector<algoim::real,3>;
using Arr = algoim::xarray<algoim::real,3>;
using algoim::SparkStack;
constexpr double pi = 3.141592653589793238462643383279502884;
constexpr double pore = .001;
const V center{0.,0.,.03};
const std::array<double,10> radial_mm{0.,.02,.05,.1,.25,.5,1.,2.,5.,15.};
constexpr std::array<std::array<int,2>,6> edges{{{{0,1}},{{0,2}},{{0,3}},
                                                 {{1,2}},{{1,3}},{{2,3}}}};

struct Child {
    int eid=0,ir=0,im=0,ip=0,depth=0,cut=0;
    std::array<V,4> parent_reference_vertices;
    std::array<V,10> X;
    struct Eval { V position; double det; };
    Eval at(const V& p) const {
        const std::array<double,4> L{1.-p(0)-p(1)-p(2),p(0),p(1),p(2)};
        const std::array<V,4> grad{V{-1.,-1.,-1.}, V{1.,0.,0.},
                                   V{0.,1.,0.},V{0.,0.,1.}};
        V x{0,0,0},a{0,0,0},b{0,0,0},c{0,0,0};
        auto add = [&](int i, double weight, const V& g) {
            x+=X[i]*weight;
            a+=X[i]*g(0);b+=X[i]*g(1);c+=X[i]*g(2);
        };
        for (int i=0;i<4;++i) add(i,L[i]*(2*L[i]-1),grad[i]*(4*L[i]-1));
        for (int i=0;i<6;++i) {
            int j=edges[i][0], k=edges[i][1];
            add(4+i,4*L[j]*L[k],4*(grad[j]*L[k]+grad[k]*L[j]));
        }
        const V cross{b(1)*c(2)-b(2)*c(1),b(2)*c(0)-b(0)*c(2),
                      b(0)*c(1)-b(1)*c(0)};
        const double det=a(0)*cross(0)+a(1)*cross(1)+a(2)*cross(2);
        return {x,det};
    }
};

static Child get_child(const std::string& filename,int wanted) {
    std::ifstream f(filename);
    if(!f) throw std::runtime_error("M8 child sample input missing");
    std::string tag;std::getline(f,tag);
    if(tag!="P10QB_M8_CURVED_CHILD_TET10_V1")
        throw std::runtime_error("sample marker mismatch");
    int count;f>>count;
    if(wanted<0||wanted>=count) throw std::runtime_error("sample index invalid");
    Child result;
    for(int i=0;i<count;++i){
        Child c;
        f>>c.eid>>c.ir>>c.im>>c.ip>>c.depth>>c.cut;
        for(V& v:c.parent_reference_vertices){double x,y,z;f>>x>>y>>z;v=V{x,y,z};}
        for(V& v:c.X){double x,y,z;f>>x>>y>>z;v=V{x,y,z};}
        if(!f) throw std::runtime_error("truncated real child coordinates");
        if(i==wanted) result=c;
    }
    if(result.cut!=0&&result.cut!=1&&result.cut!=3)
        throw std::runtime_error("only exactly one curved quartic supported");
    if(result.ir!=0&&result.ir!=4)
        throw std::runtime_error("unexpected radial bin");
    if(result.im!=0&&result.im!=9)
        throw std::runtime_error("unexpected polar bin");
    return result;
}

static double levelset(const Child& c,const V& u){
    V v=(c.at(u).position-center)*(1./pore);
    double rr=v(0)*v(0)+v(1)*v(1)+v(2)*v(2);
    double lo=1.+radial_mm[c.ir];
    double hi=1.+radial_mm[c.ir+1];
    if(c.cut==0) return lo*lo-rr;          // r >= rho_lo
    if(c.cut==1) return rr-hi*hi;          // r <= rho_hi
    return .64*(v(0)*v(0)+v(1)*v(1))-.36*v(2)*v(2);
}

static double d4_full_volume(const Child& t){
    const std::array<double,4> nodes{.0694318442029737,.3300094782075719,
                                     .6699905217924281,.9305681557970262};
    const std::array<double,4> wg{.1739274225687269,.3260725774312731,
                                  .3260725774312731,.1739274225687269};
    double volume=0;
    for(int i=0;i<4;++i)for(int j=0;j<4;++j)for(int k=0;k<4;++k){
        double a=nodes[i],b=nodes[j],c=nodes[k];
        V u{a,(1-a)*b,(1-a)*(1-b)*c};
        double det=t.at(u).det;
        if(!(det>0))throw std::runtime_error("negative Jacobian on real curved child");
        volume+=wg[i]*wg[j]*wg[k]*(1-a)*(1-a)*(1-b)*det;
    }
    return volume;
}

int main(int argc,char** argv){
    try {
        if(argc!=4)throw std::runtime_error("usage: WORKER input sample_index qmax");
        Child c=get_child(argv[1],std::atoi(argv[2]));
        int qmax=std::atoi(argv[3]);
        if(qmax<2||qmax>8)throw std::runtime_error("qmax must be in [2,8]");
        double full=d4_full_volume(c);
        std::cout<<std::setprecision(16)
                 <<"P10QB_PREFLIGHT element="<<c.eid<<" depth="<<c.depth
                 <<" r="<<c.ir<<" mu="<<c.im<<" phi="<<c.ip
                 <<" quartic="<<c.cut<<" physical_full_m3="<<full<<std::endl;
        const algoim::uvector<int,3> e5{5,5,5},e2{2,2,2};
        Arr polynomial(nullptr,e5),simplex(nullptr,e2);
        algoim_spark_alloc(algoim::real,polynomial,simplex);
        algoim::bernstein::bernsteinInterpolate<3>(
            [&c](const V& x){return levelset(c,x);},polynomial);
        algoim::bernstein::bernsteinInterpolate<3>(
            [](const V& x){return x(0)+x(1)+x(2)-1.;},simplex);
        for(const V& p:{V{.17,.26,.32},V{.39,.24,.18}}){
            double exact=levelset(c,p);
            double tab=algoim::bernstein::evalBernsteinPoly<3>(polynomial,p);
            if(std::abs(exact-tab)>2e-10)
                throw std::runtime_error("quartic polynomial interpolation inaccurate");
        }
        algoim::ImplicitPolyQuadrature<3> quad;
        auto mask0=algoim::detail::nonzeroMask(
            polynomial,algoim::booluarray<3,ALGOIM_M>(true));
        auto mask1=algoim::detail::nonzeroMask(
            simplex,algoim::booluarray<3,ALGOIM_M>(true));
        if(!algoim::detail::maskEmpty(mask0))quad.phi.push_back(polynomial,mask0);
        if(!algoim::detail::maskEmpty(mask1))quad.phi.push_back(simplex,mask1);
        std::cout<<"P10QB_ALGOIM_BUILD_BEGIN active_physical_quartic=1 "+
                   std::string("simplex_constraint=1")<<std::endl;
        quad.build(true,false);
        std::cout<<"P10QB_ALGOIM_BUILD_DONE"<<std::endl;
        for(int q:{2,3,4,6,8}){
            if(q>qmax) continue;
            double full_algoim=0,cut_algoim=0;
            std::size_t points=0,active=0;
            double minweight=std::numeric_limits<double>::infinity();
            quad.integrate(algoim::AutoMixed,q,[&](const V& x,algoim::real weight){
                ++points;
                if(points>4000000)
                    throw std::runtime_error("P10QB_POINT_BUDGET_EXCEEDED");
                if(x(0)+x(1)+x(2)>1.+1e-12)return;
                double det=c.at(x).det;
                if(!(det>0))throw std::runtime_error("negative Jacobian at Algoim node");
                if(!(weight>0))throw std::runtime_error("nonpositive quadrature weight");
                full_algoim+=weight*det;
                minweight=std::min(minweight,double(weight));
                if(levelset(c,x)<=0.){cut_algoim+=weight*det;++active;}
            });
            if(points==0 || active==0 || !(cut_algoim>0) ||
               cut_algoim>1.02*full || !std::isfinite(cut_algoim))
                throw std::runtime_error("invalid local physical cut volume");
            std::cout<<"P10QB_LOCAL_ALGOIM element="<<c.eid
                     <<" depth="<<c.depth<<" quartic="<<c.cut<<" q="<<q
                     <<" cut_m3="<<cut_algoim<<" full_m3="<<full_algoim
                     <<" exact_full_m3="<<full
                     <<" full_rel="<<std::abs(full_algoim-full)/full
                     <<" cut_frac="<<cut_algoim/full
                     <<" points="<<points<<" active_points="<<active
                     <<" min_weight="<<minweight<<std::endl;
        }
        std::cout<<"P10QB_LOCAL_ALGOIM_PASS"<<std::endl;
    }catch(const std::exception& e){
        std::cerr<<"P10QB_STOP "<<e.what()<<std::endl;
        return 2;
    }
}
