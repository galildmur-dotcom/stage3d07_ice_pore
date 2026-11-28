// P10QC: original Algoim/LAPACKE on one quadratic curved-M8 physical boundary.
// Exact reference-child Tet10 mapping from accepted M8, plus simplex plane.
// No Gmsh, mesh mutation, FEM/EDV or adjoint.
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
constexpr double pi=3.141592653589793238462643383279502884;
const V centre{0.,0.,.03};
constexpr std::array<std::array<int,2>,6> edges{{{{0,1}},{{0,2}},{{0,3}},
                                                  {{1,2}},{{1,3}},{{2,3}}}};

struct Child {
    int eid=0,ir=0,im=0,ip=0,depth=0,cut=0;
    std::array<V,4> parent_reference_vertices;
    std::array<V,10> X;
    struct Eval {V position;double det;};
    Eval at(const V& p)const{
        const std::array<double,4> l{1.-p(0)-p(1)-p(2),p(0),p(1),p(2)};
        const std::array<V,4> dl{V{-1,-1,-1},V{1,0,0},V{0,1,0},V{0,0,1}};
        V x{0,0,0},a{0,0,0},b{0,0,0},c{0,0,0};
        auto add=[&](int i,double n,const V& g){
            x+=X[i]*n;a+=X[i]*g(0);b+=X[i]*g(1);c+=X[i]*g(2);
        };
        for(int i=0;i<4;++i)add(i,l[i]*(2*l[i]-1),dl[i]*(4*l[i]-1));
        for(int i=0;i<6;++i){
            int j=edges[i][0],k=edges[i][1];
            add(i+4,4*l[j]*l[k],4*(dl[j]*l[k]+dl[k]*l[j]));
        }
        V bc{b(1)*c(2)-b(2)*c(1),b(2)*c(0)-b(0)*c(2),
             b(0)*c(1)-b(1)*c(0)};
        return {x,a(0)*bc(0)+a(1)*bc(1)+a(2)*bc(2)};
    }
};

static Child read_child(const std::string& input,int selected){
    std::ifstream f(input);if(!f)throw std::runtime_error("input missing");
    std::string marker;std::getline(f,marker);
    if(marker!="P10QB_M8_CURVED_CHILD_TET10_V1")
        throw std::runtime_error("input marker mismatch");
    int count;f>>count;
    if(selected<0||selected>=count)
        throw std::runtime_error("sample index out of range");
    Child out;
    for(int n=0;n<count;++n){
        Child c;f>>c.eid>>c.ir>>c.im>>c.ip>>c.depth>>c.cut;
        for(V& v:c.parent_reference_vertices){double x,y,z;f>>x>>y>>z;v=V{x,y,z};}
        for(V& v:c.X){double x,y,z;f>>x>>y>>z;v=V{x,y,z};}
        if(!f)throw std::runtime_error("truncated accepted M8 child");
        if(n==selected)out=c;
    }
    if(out.cut!=2&&out.cut!=4&&out.cut!=5)
        throw std::runtime_error("one quadratic boundary required");
    if(out.im!=0&&out.im!=9)throw std::runtime_error("invalid polar bin");
    if(out.ip<0||out.ip>=12)throw std::runtime_error("invalid azimuth bin");
    return out;
}

static double levelset(const Child& t,const V& u){
    V x=(t.at(u).position-centre)*1000.;
    if(t.cut==2)return (t.im==9?-1.:1.)*x(2); // inside s*z>=0
    double theta=-pi+2*pi*t.ip/12 + (t.cut==5?pi/6:0.);
    double signed_az=-std::sin(theta)*x(0)+std::cos(theta)*x(1);
    return t.cut==4?-signed_az:signed_az;  // both inside <=0
}

static double full_volume(const Child& t){
    const std::array<double,4> x{.0694318442029737,.3300094782075719,
                                 .6699905217924281,.9305681557970262};
    const std::array<double,4> w{.1739274225687269,.3260725774312731,
                                 .3260725774312731,.1739274225687269};
    double value=0;
    for(int i=0;i<4;++i)for(int j=0;j<4;++j)for(int k=0;k<4;++k){
        double a=x[i],b=x[j],c=x[k];
        V p{a,(1-a)*b,(1-a)*(1-b)*c};
        double det=t.at(p).det;
        if(!(det>0))throw std::runtime_error("negative child determinant");
        value+=w[i]*w[j]*w[k]*(1-a)*(1-a)*(1-b)*det;
    }
    return value;
}

int main(int argc,char** argv){
    try{
        if(argc!=4)throw std::runtime_error("usage: WORKER sample_file index qmax");
        Child c=read_child(argv[1],std::atoi(argv[2]));
        int qmax=std::atoi(argv[3]);
        if(qmax<2||qmax>8)throw std::runtime_error("qmax must be 2..8");
        double volume=full_volume(c);
        std::cout<<std::setprecision(16)<<"P10QC_PREFLIGHT element="<<c.eid
                 <<" depth="<<c.depth<<" r="<<c.ir<<" mu="<<c.im
                 <<" phi="<<c.ip<<" quadratic="<<c.cut
                 <<" exact_volume_m3="<<volume<<std::endl;
        const algoim::uvector<int,3> e3{3,3,3},e2{2,2,2};
        Arr polynomial(nullptr,e3),simplex(nullptr,e2);
        algoim_spark_alloc(algoim::real,polynomial,simplex);
        algoim::bernstein::bernsteinInterpolate<3>(
            [&c](const V& u){return levelset(c,u);},polynomial);
        algoim::bernstein::bernsteinInterpolate<3>(
            [](const V& u){return u(0)+u(1)+u(2)-1.;},simplex);
        for(const V& p:{V{.17,.26,.32},V{.39,.24,.18}}){
            double exact=levelset(c,p);
            double interpolated=algoim::bernstein::evalBernsteinPoly<3>(polynomial,p);
            if(std::abs(exact-interpolated)>5e-12)
                throw std::runtime_error("quadratic pullback interpolation mismatch");
        }
        algoim::ImplicitPolyQuadrature<3> quadrature;
        auto mask=algoim::detail::nonzeroMask(polynomial,algoim::booluarray<3,ALGOIM_M>(true));
        auto tetmask=algoim::detail::nonzeroMask(simplex,algoim::booluarray<3,ALGOIM_M>(true));
        if(!algoim::detail::maskEmpty(mask))quadrature.phi.push_back(polynomial,mask);
        if(!algoim::detail::maskEmpty(tetmask))quadrature.phi.push_back(simplex,tetmask);
        std::cout<<"P10QC_ALGOIM_BUILD_BEGIN quadratic=1 simplex=1"<<std::endl;
        quadrature.build(true,false);
        std::cout<<"P10QC_ALGOIM_BUILD_DONE"<<std::endl;
        for(int q:{2,3,4,6,8}){
            if(q>qmax)continue;
            std::size_t points=0,active=0;
            double full=0,cut=0,minw=std::numeric_limits<double>::infinity();
            quadrature.integrate(algoim::AutoMixed,q,[&](const V& u,algoim::real w){
                if(++points>2000000)throw std::runtime_error("quadrature node guard");
                if(u(0)+u(1)+u(2)>1.+1e-12)return;
                double det=c.at(u).det;
                if(!(det>0)||!(w>0))throw std::runtime_error("bad weight or detJ");
                full+=w*det;minw=std::min(minw,double(w));
                if(levelset(c,u)<=0){cut+=w*det;++active;}
            });
            if(!(cut>0&&cut<1.001*volume&&active>0))
                throw std::runtime_error("local cut volume out of range");
            std::cout<<"P10QC_LOCAL_ALGOIM element="<<c.eid
                     <<" depth="<<c.depth<<" quadratic="<<c.cut
                     <<" q="<<q<<" cut_m3="<<cut<<" full_m3="<<full
                     <<" exact_m3="<<volume
                     <<" full_rel="<<std::abs(full-volume)/volume
                     <<" cut_frac="<<cut/volume<<" points="<<points
                     <<" active_points="<<active<<" min_weight="<<minw<<std::endl;
        }
        std::cout<<"P10QC_LOCAL_QUADRATIC_ALGOIM_PASS"<<std::endl;
    }catch(const std::exception& e){
        std::cerr<<"P10QC_STOP "<<e.what()<<std::endl;return 2;
    }
}
