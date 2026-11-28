// P10QJ real accepted-M8 Tet10, TWO active physical polynomial cuts:
// one true quartic (radial/polar) + one true quadratic (azimuth/hemisphere).
// Keep all old P10QI FE-numerator geometry code unchanged and reuse it,
// selecting a different entry point. Original C++20 Algoim + LAPACKE.
// No Gmsh, mesh modification, physical FEM, EDV, adjoint, PowerShell.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreturn-type"
#define main p10qi_prior_single_boundary_main
#include "P10QI_M8_REAL_TET10_GRADIENT_ALGOIM.cpp"
#undef main
#pragma GCC diagnostic pop

constexpr double pi_double_cut=3.141592653589793238462643383279502884;

struct DoubleCase{Child element;int quadratic=-1;};

static DoubleCase read_double(const std::string&filename,int selected){
    std::ifstream in(filename);
    if(!in)throw std::runtime_error("P10QJ worker input not available");
    std::string marker;std::getline(in,marker);
    if(marker!="P10QJ_M8_TRUE_TWO_ACTIVE_GRADIENT_CHILD_V1")
        throw std::runtime_error("incorrect double-cut real M8 marker");
    int n=0;in>>n;
    if(n!=8||selected<0||selected>=n)
        throw std::runtime_error("wrong double-cut number of cases");
    DoubleCase result;
    for(int k=0;k<n;++k){
        DoubleCase sample;
        Child& c=sample.element;
        in>>c.eid>>c.ir>>c.im>>c.ip>>c.depth>>c.cut>>sample.quadratic;
        for(V& x:c.nodes){double a,b,d;in>>a>>b>>d;x=V{a,b,d};}
        for(double& a:c.field)in>>a;
        in>>c.exact_gradient>>c.exact_volume;
        if(!in)throw std::runtime_error("incomplete real double-cut M8 node/field data");
        if(k==selected)result=sample;
    }
    if(!(result.element.cut==0||result.element.cut==1||result.element.cut==3) ||
       !(result.quadratic==2||result.quadratic==4||result.quadratic==5))
        throw std::runtime_error("requires one quartic plus one quadratic");
    return result;
}

static double quadratic(const DoubleCase& c,const V& u){
    V x=(c.element.at(u).x-centre)*1000.;
    if(c.quadratic==2)return (c.element.im==9?-1.:1.)*x(2);
    double angle=-pi_double_cut+2*pi_double_cut*c.element.ip/12;
    if(c.quadratic==5)angle+=pi_double_cut/6;
    double az=-std::sin(angle)*x(0)+std::cos(angle)*x(1);
    return c.quadratic==4?-az:az;
}

int main(int argc,char**argv){
    try{
        if(argc!=4)throw std::runtime_error("usage: WORKER INPUT CASE QMAX");
        int sample=std::atoi(argv[2]),qmax=std::atoi(argv[3]);
        if(qmax<2||qmax>8)throw std::runtime_error("q out of 2..8");
        const DoubleCase dc=read_double(argv[1],sample);
        const Child& c=dc.element;
        std::cout<<std::setprecision(17)
                 <<"P10QJ_PREFLIGHT sample="<<sample<<" element="<<c.eid
                 <<" r="<<c.ir<<" mu="<<c.im<<" phi="<<c.ip
                 <<" depth="<<c.depth<<" quartic="<<c.cut
                 <<" quadratic="<<dc.quadratic
                 <<" exact_full_gradient_m3="<<c.exact_gradient
                 <<" exact_full_volume_m3="<<c.exact_volume<<std::endl;
        const algoim::uvector<int,3> quartic_deg{5,5,5};
        const algoim::uvector<int,3> quadratic_deg{3,3,3};
        const algoim::uvector<int,3> simplex_deg{2,2,2};
        Arr radial(nullptr,quartic_deg),azimuth(nullptr,quadratic_deg),simplex(nullptr,simplex_deg);
        algoim_spark_alloc(algoim::real,radial,azimuth,simplex);
        algoim::bernstein::bernsteinInterpolate<3>(
            [&c](const V& u){return quartic(c,u);},radial);
        algoim::bernstein::bernsteinInterpolate<3>(
            [&dc](const V&u){return quadratic(dc,u);},azimuth);
        algoim::bernstein::bernsteinInterpolate<3>(
            [](const V&u){return u(0)+u(1)+u(2)-1.;},simplex);
        for(const V&u:{V{.17,.26,.32},V{.39,.24,.18},V{.14,.19,.21}}){
            if(std::abs(algoim::bernstein::evalBernsteinPoly<3>(radial,u)-quartic(c,u))>3e-10 ||
               std::abs(algoim::bernstein::evalBernsteinPoly<3>(azimuth,u)-quadratic(dc,u))>1e-10)
                throw std::runtime_error("double-cut Bernstein polynomial mismatch");
        }
        algoim::ImplicitPolyQuadrature<3> q;
        auto add=[&q](Arr&v){
            auto mask=algoim::detail::nonzeroMask(v,algoim::booluarray<3,ALGOIM_M>(true));
            if(!algoim::detail::maskEmpty(mask))q.phi.push_back(v,mask);
        };
        add(radial);add(azimuth);add(simplex);
        std::cout<<"P10QJ_ALGOIM_BUILD_BEGIN 1_quartic_plus_1_quadratic_plus_1_simplex"
                 <<" Bernstein_degrees=5x5x5,3x3x3,2x2x2"<<std::endl;
        q.build(true,false);
        std::cout<<"P10QJ_ALGOIM_BUILD_DONE"<<std::endl;
        for(int degree:{2,3,4,6,8}){
            if(degree>qmax)continue;
            double totalvol=0,cutvol=0,totalgrad=0,cutgrad=0;
            std::size_t points=0,active=0;
            double smallest=std::numeric_limits<double>::infinity();
            q.integrate(algoim::AutoMixed,degree,[&](const V&u,algoim::real w){
                if(++points>2000000)throw std::runtime_error("P10QJ_2M_POINT_CAP");
                if(u(0)+u(1)+u(2)>1.+1e-12)return;
                Child::Evaluation p=c.at(u);
                if(!(w>0))throw std::runtime_error("P10QJ_nonpositive_weight");
                smallest=std::min(smallest,double(w));
                totalvol+=w*p.det;totalgrad+=w*p.gradient_numerator;
                if(quartic(c,u)<=0&&quadratic(dc,u)<=0){
                    cutvol+=w*p.det;cutgrad+=w*p.gradient_numerator;
                    ++active;
                }
            });
            if(!(cutvol>0&&cutvol<c.exact_volume&&active>0))
                throw std::runtime_error("P10QJ_ZERO_OR_INVALID_REAL_DOUBLE_CUT_VOLUME");
            std::cout<<"P10QJ_DOUBLE_CUT sample="<<sample<<" q="<<degree
                     <<" cut_gradient_m3="<<cutgrad<<" cut_volume_m3="<<cutvol
                     <<" full_gradient_relative="<<std::abs(totalgrad-c.exact_gradient)/
                           std::max(std::abs(c.exact_gradient),1e-25)
                     <<" full_volume_relative="<<std::abs(totalvol-c.exact_volume)/c.exact_volume
                     <<" total_points="<<points<<" active_points="<<active
                     <<" min_weight="<<smallest<<std::endl;
        }
        std::cout<<"P10QJ_TRUE_REAL_M8_TWO_BOUNDARY_ALGOIM_PASS"<<std::endl;
    }catch(const std::exception&ex){
        std::cerr<<"P10QJ_STOP "<<ex.what()<<std::endl;
        return 2;
    }
}
