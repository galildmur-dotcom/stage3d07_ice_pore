// Stage3D07 P10QK: source-only Algoim for true curved M8 h-sub-Tet10.
// Build ONLY active quartic/quadratic physical cut polynomials, plus simplex.
// Reuse immutable P10QI true P2 gradient numerator implementation.
// No physics/FEM/CAD/mesh edits/Gmsh/PowerShell.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreturn-type"
#define main p10qi_prior_main_for_hybrid
#include "P10QI_M8_REAL_TET10_GRADIENT_ALGOIM.cpp"
#undef main
#pragma GCC diagnostic pop

constexpr double kPI=3.141592653589793238462643383279502884;

struct Hybrid{
    Child child;
    int source_case=-1;
    std::array<int,6> status;
};

static Hybrid fetch_hybrid(const std::string&name,int selected){
    std::ifstream f(name);
    if(!f)throw std::runtime_error("P10QK_CHILD_FILE_MISSING");
    std::string head;std::getline(f,head);
    if(head!="P10QK_M8_HYBRID_GRADIENT_CHILD_V1")
        throw std::runtime_error("P10QK_CHILD_MARKER_MISMATCH");
    int n=0;f>>n;
    if(n<1||n>500||selected<0||selected>=n)
        throw std::runtime_error("P10QK_CHILD_COUNT_OR_INDEX");
    Hybrid out;
    for(int j=0;j<n;++j){
        Hybrid h;Child&c=h.child;
        f>>h.source_case>>c.eid>>c.ir>>c.im>>c.ip>>c.depth;
        for(int& s:h.status)f>>s;
        for(V& p:c.nodes){double x,y,z;f>>x>>y>>z;p=V{x,y,z};}
        for(double& a:c.field)f>>a;
        f>>c.exact_gradient>>c.exact_volume;
        if(!f)throw std::runtime_error("P10QK_REAL_SUBTET10_TRUNCATED");
        if(j==selected)out=h;
    }
    int open=0;
    for(int s:out.status){
        if(s==-1)throw std::runtime_error("P10QK_OUTSIDE_CHILD_SENT_TO_ALGOIM");
        if(s==0)++open;
    }
    if(open<1||open>2||out.child.exact_volume<=0)
        throw std::runtime_error("P10QK_REQUIRES_ONE_OR_TWO_ACTIVE_BOUNDARIES");
    return out;
}

static double physical_levelset(const Hybrid&h,const V&u,int which){
    const Child&c=h.child;
    V p=(c.at(u).x-centre)*1000.;
    double r2=p(0)*p(0)+p(1)*p(1)+p(2)*p(2);
    if(which==0){double r=1.+radial_mm[c.ir];return r*r-r2;}
    if(which==1){double r=1.+radial_mm[c.ir+1];return r2-r*r;}
    if(which==3)return .64*(p(0)*p(0)+p(1)*p(1))-.36*p(2)*p(2);
    if(which==2)return (c.im==9?-1.:1.)*p(2);
    double angle=-kPI+2*kPI*c.ip/12;
    if(which==5)angle+=kPI/6;
    double az=-std::sin(angle)*p(0)+std::cos(angle)*p(1);
    return which==4?-az:az;
}

int main(int argc,char**argv){
    try{
        if(argc!=4 && argc!=5)
            throw std::runtime_error("usage: WORKER FILE INDEX QMAX [auto|gl|ts]");
        const int k=std::atoi(argv[2]),qmax=std::atoi(argv[3]);
        if(qmax<2||qmax>8)throw std::runtime_error("P10QK_QMAX_NOT_2..8");
        const std::string strategy=argc==5?argv[4]:"auto";
        const algoim::QuadStrategy method=(strategy=="auto"?algoim::AutoMixed:
           (strategy=="gl"?algoim::AlwaysGL:algoim::AlwaysTS));
        if(strategy!="auto" && strategy!="gl" && strategy!="ts")
            throw std::runtime_error("P10QK_UNKNOWN_QUADRATURE_STRATEGY");
        const Hybrid h=fetch_hybrid(argv[1],k);
        const Child&c=h.child;
        int active=0;for(int s:h.status)active+=(s==0);
        std::cout<<std::setprecision(17)
                 <<"P10QK_PREFLIGHT child="<<k<<" source="<<h.source_case
                 <<" element="<<c.eid<<" h_depth="<<c.depth
                 <<" strategy="<<strategy
                 <<" active_boundaries="<<active
                 <<" exact_full_gradient_m3="<<c.exact_gradient
                 <<" exact_full_volume_m3="<<c.exact_volume<<std::endl;
        const algoim::uvector<int,3> d4{5,5,5},d2{3,3,3},ds{2,2,2};
        std::array<Arr,6> functions={Arr(nullptr,d4),Arr(nullptr,d4),Arr(nullptr,d2),
                                     Arr(nullptr,d4),Arr(nullptr,d2),Arr(nullptr,d2)};
        Arr simplex(nullptr,ds);
        for(int id=0;id<6;++id)if(h.status[id]==0){
            algoim_spark_alloc(algoim::real,functions[id]);
            algoim::bernstein::bernsteinInterpolate<3>(
                [&h,id](const V&u){return physical_levelset(h,u,id);},functions[id]);
            for(const V&u:{V{.17,.26,.32},V{.39,.24,.18}}){
                if(std::abs(algoim::bernstein::evalBernsteinPoly<3>(functions[id],u)-
                           physical_levelset(h,u,id))>3e-10)
                    throw std::runtime_error("P10QK_PHYSICAL_POLYNOMIAL_REPRODUCTION_ERROR");
            }
        }
        algoim_spark_alloc(algoim::real,simplex);
        algoim::bernstein::bernsteinInterpolate<3>(
            [](const V&u){return u(0)+u(1)+u(2)-1.;},simplex);
        algoim::ImplicitPolyQuadrature<3> q;
        auto register_phi=[&q](Arr&v){
            auto mask=algoim::detail::nonzeroMask(v,algoim::booluarray<3,ALGOIM_M>(true));
            if(!algoim::detail::maskEmpty(mask))q.phi.push_back(v,mask);
        };
        for(int id=0;id<6;++id)if(h.status[id]==0)register_phi(functions[id]);
        register_phi(simplex);
        std::cout<<"P10QK_BUILD_BEGIN active="<<active<<std::endl;
        q.build(true,false);
        std::cout<<"P10QK_BUILD_DONE"<<std::endl;
        for(int order:{2,3,4,6,8}){
            if(order>qmax)continue;
            double cutg=0,cutv=0,fullg=0,fullv=0;
            std::size_t n=0,inside=0;
            double minw=std::numeric_limits<double>::infinity();
            q.integrate(method,order,[&](const V&u,algoim::real w){
                if(++n>1000000)throw std::runtime_error("P10QK_1M_POINT_CAP");
                if(u(0)+u(1)+u(2)>1.+1e-12)return;
                Child::Evaluation value=c.at(u);
                if(!(w>0))throw std::runtime_error("P10QK_NEGATIVE_WEIGHT");
                fullg+=w*value.gradient_numerator;fullv+=w*value.det;
                minw=std::min(minw,double(w));
                bool cut=true;
                for(int id=0;id<6;++id)if(h.status[id]==0&&physical_levelset(h,u,id)>0){
                    cut=false;break;
                }
                if(cut){cutg+=w*value.gradient_numerator;cutv+=w*value.det;++inside;}
            });
            std::cout<<"P10QK_CUT child="<<k<<" q="<<order
                     <<" cut_gradient_m3="<<cutg<<" cut_volume_m3="<<cutv
                     <<" full_gradient_relative="<<std::abs(fullg-c.exact_gradient)/
                         std::max(std::abs(c.exact_gradient),1e-25)
                     <<" full_volume_relative="<<std::abs(fullv-c.exact_volume)/c.exact_volume
                     <<" points="<<n<<" inside="<<inside
                     <<" min_weight="<<minw<<std::endl;
        }
        std::cout<<"P10QK_HYBRID_ONE_OR_TWO_REAL_M8_ALGOIM_PASS"<<std::endl;
    }catch(const std::exception&ex){
        std::cerr<<"P10QK_STOP "<<ex.what()<<std::endl;return 2;
    }
}
