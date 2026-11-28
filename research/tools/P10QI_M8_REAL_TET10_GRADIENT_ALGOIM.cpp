// P10QI: original Algoim/LAPACKE on accepted M8 curved Tet10 *FE gradient*.
// The P2 field here is the exact restriction of the parent FE interpolant,
// NOT a new interpolation of cubic nodal values on the child.
// Multiplied by det(J), the physical z-derivative is a degree-3 polynomial.
// Only one active quartic + real reference-simplex boundary is handled here.
// Pure manufactured source-only research. NO Gmsh, FEM, EDV, mesh edits.
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

using V=algoim::uvector<algoim::real,3>;
using Arr=algoim::xarray<algoim::real,3>;
using algoim::SparkStack;
constexpr double S=.0015, pore=.001;
constexpr std::array<std::array<int,2>,6> edge{{{{0,1}},{{0,2}},{{0,3}},
                                                {{1,2}},{{1,3}},{{2,3}}}};
constexpr std::array<double,10> radial_mm{0.,.02,.05,.1,.25,.5,1.,2.,5.,15.};
const V centre{0.,0.,.03};

static V cross(const V&a,const V&b){
    return V{a(1)*b(2)-a(2)*b(1),a(2)*b(0)-a(0)*b(2),a(0)*b(1)-a(1)*b(0)};
}

struct Child {
    int eid=0,ir=0,im=0,ip=0,depth=0,cut=0;
    std::array<V,10> nodes;
    std::array<double,10> field;
    double exact_gradient=0.,exact_volume=0.;
    struct Evaluation{V x;double det;double gradient_numerator;};
    Evaluation at(const V& p)const{
        const std::array<double,4> L{1.-p(0)-p(1)-p(2),p(0),p(1),p(2)};
        const std::array<V,4> dL{V{-1,-1,-1},V{1,0,0},V{0,1,0},V{0,0,1}};
        V pos{0,0,0},a{0,0,0},b{0,0,0},c{0,0,0},df{0,0,0};
        auto add=[&](int i,double shape,const V& grad){
            pos+=nodes[i]*shape;
            a+=nodes[i]*grad(0);b+=nodes[i]*grad(1);c+=nodes[i]*grad(2);
            df+=grad*field[i];
        };
        for(int i=0;i<4;++i)add(i,L[i]*(2*L[i]-1),dL[i]*(4*L[i]-1));
        for(int i=0;i<6;++i){
            int j=edge[i][0],k=edge[i][1];
            add(4+i,4*L[j]*L[k],4*(dL[j]*L[k]+dL[k]*L[j]));
        }
        const V bc=cross(b,c),ca=cross(c,a),ab=cross(a,b);
        const double det=a(0)*bc(0)+a(1)*bc(1)+a(2)*bc(2);
        const double numerator=S*(bc(2)*df(0)+ca(2)*df(1)+ab(2)*df(2));
        if(!(det>0)||!std::isfinite(numerator))
            throw std::runtime_error("negative detJ or nonfinite gradient numerator");
        return {pos,det,numerator};
    }
};

static Child read_case(const std::string&filename,int chosen){
    std::ifstream in(filename);
    if(!in)throw std::runtime_error("true M8 worker input unavailable");
    std::string header;std::getline(in,header);
    if(header!="P10QI_M8_TET10_GRADIENT_CHILD_V1")
        throw std::runtime_error("wrong true M8 P2-field restriction marker");
    int n=0;in>>n;
    if(n!=8||chosen<0||chosen>=n)throw std::runtime_error("invalid selection count/index");
    Child output;
    for(int s=0;s<n;++s){
        Child c;
        in>>c.eid>>c.ir>>c.im>>c.ip>>c.depth>>c.cut;
        for(V& x:c.nodes){double a,b,d;in>>a>>b>>d;x=V{a,b,d};}
        for(double& f:c.field)in>>f;
        in>>c.exact_gradient>>c.exact_volume;
        if(!in)throw std::runtime_error("incomplete M8 physical child and P2 field");
        if(s==chosen)output=c;
    }
    if(!(output.cut==0||output.cut==1||output.cut==3)||
       (output.im!=0&&output.im!=9)||output.exact_volume<=0)
        throw std::runtime_error("unexpected quartic geometry or exact volume");
    return output;
}

static double quartic(const Child& c,const V& u){
    V p=(c.at(u).x-centre)*(1./pore);
    double rr=p(0)*p(0)+p(1)*p(1)+p(2)*p(2);
    double lo=1.+radial_mm[c.ir],hi=1.+radial_mm[c.ir+1];
    if(c.cut==0)return lo*lo-rr;
    if(c.cut==1)return rr-hi*hi;
    return .64*(p(0)*p(0)+p(1)*p(1))-.36*p(2)*p(2);
}

int main(int argc,char**argv){
    try{
        if(argc!=4)throw std::runtime_error("usage: WORKER CHILDREN_FILE INDEX QMAX");
        const int index=std::atoi(argv[2]);
        const Child c=read_case(argv[1],index);
        int qmax=std::atoi(argv[3]);
        if(qmax<2||qmax>8)throw std::runtime_error("qmax out of 2..8");
        std::cout<<std::setprecision(17)
                 <<"P10QI_REAL_M8_PREFLIGHT case="<<index<<" element="<<c.eid
                 <<" depth="<<c.depth<<" quartic="<<c.cut
                 <<" exact_full_gradient_m3="<<c.exact_gradient
                 <<" exact_full_volume_m3="<<c.exact_volume<<std::endl;
        const algoim::uvector<int,3> d4{5,5,5},linear{2,2,2};
        Arr cut(nullptr,d4),simplex(nullptr,linear);
        algoim_spark_alloc(algoim::real,cut,simplex);
        algoim::bernstein::bernsteinInterpolate<3>(
            [&c](const V&u){return quartic(c,u);},cut);
        algoim::bernstein::bernsteinInterpolate<3>(
            [](const V&u){return u(0)+u(1)+u(2)-1.;},simplex);
        for(const V& p:{V{.17,.26,.32},V{.39,.24,.18},V{.14,.19,.21}}){
            double truth=quartic(c,p),b=algoim::bernstein::evalBernsteinPoly<3>(cut,p);
            if(std::abs(truth-b)>2e-10)
                throw std::runtime_error("curved quartic Bernstein identity failed");
        }
        algoim::ImplicitPolyQuadrature<3> quadrature;
        auto cmask=algoim::detail::nonzeroMask(cut,algoim::booluarray<3,ALGOIM_M>(true));
        auto tmask=algoim::detail::nonzeroMask(simplex,algoim::booluarray<3,ALGOIM_M>(true));
        if(!algoim::detail::maskEmpty(cmask))quadrature.phi.push_back(cut,cmask);
        if(!algoim::detail::maskEmpty(tmask))quadrature.phi.push_back(simplex,tmask);
        std::cout<<"P10QI_ALGOIM_BUILD_BEGIN real_quartic=1 simplex=1"<<std::endl;
        quadrature.build(true,false);
        std::cout<<"P10QI_ALGOIM_BUILD_DONE"<<std::endl;
        for(int q:{2,3,4,6,8}){
            if(q>qmax)continue;
            double volume=0,cut_volume=0,gradient=0,cut_gradient=0;
            double min_weight=std::numeric_limits<double>::infinity();
            std::size_t points=0,active=0;
            quadrature.integrate(algoim::AutoMixed,q,[&](const V&u,algoim::real w){
                if(++points>4000000)throw std::runtime_error("P10QI_NODE_LIMIT_4M");
                if(u(0)+u(1)+u(2)>1.+1e-12)return;
                Child::Evaluation ev=c.at(u);
                if(!(w>0))throw std::runtime_error("Algoim nonpositive weight");
                min_weight=std::min(min_weight,double(w));
                volume+=w*ev.det;gradient+=w*ev.gradient_numerator;
                if(quartic(c,u)<=0){
                    cut_volume+=w*ev.det;cut_gradient+=w*ev.gradient_numerator;
                    ++active;
                }
            });
            if(!(cut_volume>0&&cut_volume<1.001*c.exact_volume&&active>0))
                throw std::runtime_error("real M8 cut fraction out of bounds");
            double e_volume=std::abs(volume-c.exact_volume)/c.exact_volume;
            double e_gradient=std::abs(gradient-c.exact_gradient)/
                               std::max(std::abs(c.exact_gradient),1e-25);
            std::cout<<"P10QI_REAL_GRADIENT case="<<index<<" q="<<q
                     <<" cut_gradient_m3="<<cut_gradient
                     <<" full_gradient_m3="<<gradient
                     <<" exact_full_gradient_m3="<<c.exact_gradient
                     <<" full_gradient_rel="<<e_gradient
                     <<" cut_volume_m3="<<cut_volume
                     <<" full_volume_rel="<<e_volume
                     <<" points="<<points<<" active="<<active
                     <<" min_weight="<<min_weight<<std::endl;
        }
        std::cout<<"P10QI_REAL_TET10_GRADIENT_ALGOIM_PASS"<<std::endl;
    }catch(const std::exception&ex){
        std::cerr<<"P10QI_STOP "<<ex.what()<<std::endl;
        return 2;
    }
}
