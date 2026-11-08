// Stage 3D-10J: read-only geometry/memory gate for the real spherical pore.
// Uses exactly the Stage08A C1 transport on the original Gmsh Tet10 mesh.
// It NEVER runs nonlinear mechanics or creates/overwrites calculation files.
#define STAGE3D06_LIBRARY
#include "mechanical.cpp"
#include "stage3d10c_tet10_global_adjoint.hpp"
#include <iomanip>
#include <set>
#include <sstream>
#include <unordered_set>

#if __has_include("qt_runner_paths.hpp")
#include "qt_runner_paths.hpp"
#define STAGE3D10J_SOURCE_ROOT STAGE3D06_ROOT_DIR
#endif
#ifndef STAGE3D10J_SOURCE_ROOT
#define STAGE3D10J_SOURCE_ROOT "."
#endif

namespace {
using std::string;
constexpr double R=0.001;
const V C{0,0,.03};

void p10j_require(bool ok,const string& message){
 if(!ok)throw std::runtime_error("P10J: "+message);
}

struct Options {
 fs::path root=STAGE3D10J_SOURCE_ROOT;
 string mesh="H0";
 string mode="ALL";
 double delta=5e-6,cutoff=.005;
 int quad=3;
 bool selftest=false;
};

Options parse(int argc,char** argv){
 Options o;
 for(int i=1;i<argc;++i){
  string key=argv[i];
  auto next=[&]()->string{
   if(i+1>=argc)throw std::runtime_error("P10J missing value for "+key);
   return argv[++i];
  };
  if(key=="--root")o.root=next();
  else if(key=="--mesh")o.mesh=next();
  else if(key=="--mode")o.mode=next();
  else if(key=="--delta-um")o.delta=std::stod(next())*1e-6;
  else if(key=="--cutoff-mm")o.cutoff=std::stod(next())*1e-3;
  else if(key=="--quad")o.quad=std::stoi(next());
  else if(key=="--selftest")o.selftest=true;
  else if(key=="--help"){
   std::cout<<"stage3d10j_h0_geometry_preflight [--root PATH] [--mesh H0] "
      <<"[--mode ALL|R|tz|y20] [--delta-um 5] [--cutoff-mm 5] "
      <<"[--quad 3|4] [--selftest]\n";
   std::exit(0);
  }else throw std::runtime_error("P10J unknown option: "+key);
 }
 p10j_require(o.mesh=="H0"||o.mesh=="H1"||o.mesh=="H2"||o.mesh=="H3"||o.mesh=="H4",
         "allowed mesh H0..H4 (HP pilot later)");
 p10j_require(o.mode=="ALL"||o.mode=="R"||o.mode=="tz"||o.mode=="y20",
         "allowed modes ALL,R,tz,y20");
 p10j_require(std::isfinite(o.delta)&&o.delta>0&&o.delta<=20e-6,
         "delta must be 0..20 um");
 p10j_require(std::isfinite(o.cutoff)&&o.cutoff>.003&&o.cutoff<.0055,
         "cutoff must be 3..5.5 mm");
 p10j_require(o.quad==3||o.quad==4,"quadrature 3 or 4");
 return o;
}

double harmonic_y20(const V& n){
 return std::sqrt(5./(16*PI))*(3*n.z*n.z-1);
}

double support(double r,double cutoff){
 if(r<=R)return 1.;
 if(r>=cutoff)return 0.;
 const double t=(r-R)/(cutoff-R);
 return 1.-t*t*(3.-2.*t);
}

V transport(V x,const string& mode,double delta,double cutoff){
 const V d=x-C;
 const double r=norm(d);
 p10j_require(r>0,"node at pore center; invalid radial coordinate");
 const double factor=support(r,cutoff);
 if(factor==0)return x;
 const V n=d/r;
 if(mode=="R")return x+n*(delta*factor);
 if(mode=="tz")return x+V{0,0,delta*factor};
 if(mode=="y20")return x+n*(delta*factor*harmonic_y20(n));
 throw std::runtime_error("P10J unknown mode");
}

double determinant(const Mesh& m,const Tet& t,const GaussQ& q){
 V dr{},ds{},dz{};
 for(int j=0;j<10;++j){
  const auto x=m.nodes[t[j]];
  dr=dr+x*q.d[j][0];
  ds=ds+x*q.d[j][1];
  dz=dz+x*q.d[j][2];
 }
 return dot(dr,cross(ds,dz));
}

struct Volume {
 double volume=0,min_jac=std::numeric_limits<double>::infinity();
};

Volume integrate(const Mesh& m,const std::vector<GaussQ>& q){
 Volume v;
 for(const auto& tet:m.tets)for(const auto& qp:q){
  const double det=determinant(m,tet,qp);
  if(!(std::isfinite(det)&&det>0))
   throw std::runtime_error("P10J nonpositive curved Tet10 Jacobian");
  v.min_jac=std::min(v.min_jac,det);
  v.volume+=qp.w*det;
 }
 return v;
}

std::vector<int> surface_nodes(const std::vector<Face>& surfaces,int tag){
 std::set<int> ids;
 for(const auto& f:surfaces)if(tag<0||f.tag==tag)
  for(int v:f.nodes)ids.insert(v);
 return {ids.begin(),ids.end()};
}

struct Probe {
 double min_jac=std::numeric_limits<double>::infinity();
 double max_wall_error=0,max_outer_shift=0,max_b6_shift=0;
 double max_volume_relative=0;
 double expected_volume_D=0,observed_volume_D=0;
 size_t modes=0;
};

Probe evaluate(const Imported& input,const Options& opts){
 const auto& nominal=input.mesh;
 const auto pore=surface_nodes(nominal.faces,8);
 // read_msh puts the pore (physical tag 8) in mesh.faces too; it is NOT an
 // exterior boundary that must stay fixed under a pore shape variation.
 std::set<int> outer_ids;
 for(const auto& face:nominal.faces)if(face.tag!=8)
  for(const int id:face.nodes)outer_ids.insert(id);
 const std::vector<int> outer(outer_ids.begin(),outer_ids.end());
 const auto b6=surface_nodes(input.internal,9);
 p10j_require(!pore.empty()&&!outer.empty()&&!b6.empty(),
         "missing pore, exterior or B6 physical surfaces");
 p10j_require(nominal.nodes.size()>=10&&nominal.tets.size()>=1,
         "empty Tet10 geometry");
 const auto bc=bc_candidate(nominal);
 const auto q=volume_q(opts.quad);
 Probe p;
 const auto base=integrate(nominal,q);
 p.min_jac=std::min(p.min_jac,base.min_jac);
 for(int id:pore){
  p.max_wall_error=std::max(p.max_wall_error,
                       std::abs(norm(nominal.nodes[size_t(id)]-C)-R));
 }
 p10j_require(p.max_wall_error<5e-9,
         "H0 pore surface not spherical to <5 nm tolerance");
 const auto actual_modes=opts.mode=="ALL"?std::vector<string>{"R","tz","y20"}
                                             :std::vector<string>{opts.mode};
 for(const auto& mode:actual_modes){
  double vol[2]{};
  for(int sign=0;sign<2;++sign){
   const double delta=sign==0?opts.delta:-opts.delta;
   Mesh displaced=nominal;
   for(auto& node:displaced.nodes)node=transport(node,mode,delta,opts.cutoff);
   for(int id:outer)
    p.max_outer_shift=std::max(p.max_outer_shift,
       norm(displaced.nodes[size_t(id)]-nominal.nodes[size_t(id)]));
   for(int id:b6)
    p.max_b6_shift=std::max(p.max_b6_shift,
       norm(displaced.nodes[size_t(id)]-nominal.nodes[size_t(id)]));
   p10j_require(bc_candidate(displaced)==bc,"Dirichlet DOF set changes with shape");
   const auto check=integrate(displaced,q);
   p.min_jac=std::min(p.min_jac,check.min_jac);
   vol[sign]=check.volume;
   for(int id:pore){
    const auto x=displaced.nodes[size_t(id)];
    double error=0;
    if(mode=="tz"){
     error=std::abs(norm(x-(C+V{0,0,delta}))-R);
    }else{
     const auto original=nominal.nodes[size_t(id)];
     const V normal=(original-C)/norm(original-C);
     const double target=R+delta*(mode=="R"?1.:harmonic_y20(normal));
     error=std::abs(norm(x-C)-target);
    }
    p.max_wall_error=std::max(p.max_wall_error,error);
   }
  }
  const double derivative=(vol[0]-vol[1])/(2*opts.delta);
  const double expected=mode=="R"?-4*PI*R*R:0;
  const double relative=std::abs(derivative-expected)/(4*PI*R*R);
  p.max_volume_relative=std::max(p.max_volume_relative,relative);
  if(mode=="R"){
   p.expected_volume_D=expected;
   p.observed_volume_D=derivative;
  }
  std::cout<<std::scientific<<std::setprecision(10)
    <<"P10J_MODE mode="<<mode
    <<" D_ice_volume_m2="<<derivative
    <<" expected_m2="<<expected
    <<" relative_to_pore_area="<<relative<<'\n';
  ++p.modes;
 }
 p10j_require(p.max_outer_shift==0&&p.max_b6_shift==0,
         "outer or B6 internal boundary moved");
 p10j_require(p.max_wall_error<5e-11,"pore wall shape transport inaccurate");
 p10j_require(p.max_volume_relative<.025,
         "shape volume derivative deviates by >2.5% pore area");
 return p;
}

void selftest(){
 const double d=5e-6,cut=.005;
 const V x=C+V{R,0,0};
 p10j_require(norm(transport(x,"R",d,cut)-(x+V{d,0,0}))<1e-14,
         "radial mode boundary displacement");
 p10j_require(norm(transport(x,"tz",d,cut)-(x+V{0,0,d}))<1e-14,
         "translation mode boundary displacement");
 p10j_require(norm(transport(x,"y20",d,cut)-
              (x+V{d*harmonic_y20(V{1,0,0}),0,0}))<1e-14,
         "quadrupole boundary displacement");
 const V out=C+V{.006,0,0};
 for(const auto& m:{"R","tz","y20"})
  p10j_require(norm(transport(out,m,d,cut)-out)==0,"outer support not compact");
 p10j_require(support(R,cut)==1&&support(cut,cut)==0,"cutoff support endpoints");
 std::cout<<"P10J_SHAPE_TRANSPORT_SELFTEST_OK modes=3 delta_um=5 cutoff_mm=5\n";
}
}

int main(int argc,char** argv){try{
 const auto options=parse(argc,argv);
 if(options.selftest){selftest();return 0;}
 const auto filename=options.root/"meshes"/(options.mesh+".msh");
 p10j_require(fs::is_regular_file(filename),"mesh file missing: "+filename.string());
 const auto imported=read_msh(filename);
 const auto& m=imported.mesh;
 const Probe probe=evaluate(imported,options);
 const auto q=volume_q(options.quad);
 const long double nqp=static_cast<long double>(m.tets.size())*q.size();
 const long double state_bytes=nqp*sizeof(ice3d::p10c::State);
 const long double qp_bytes=nqp*sizeof(ice3d::p10c::QuadraturePoint);
 const long double snapshot_bytes=56.L+3.L*m.nodes.size()*sizeof(double)+state_bytes;
 const long double gib=1024.L*1024.L*1024.L;
 const auto pore=surface_nodes(m.faces,8);
 const auto b6=surface_nodes(imported.internal,9);
 std::cout<<std::scientific<<std::setprecision(12)
  <<"P10J_H0_GEOMETRY_PREFLIGHT_OK mesh="<<options.mesh
  <<" nodes="<<m.nodes.size()<<" tet10="<<m.tets.size()
  <<" pore_nodes="<<pore.size()<<" b6_nodes="<<b6.size()
  <<" quad_points_per_tet="<<q.size()<<" modes_checked="<<probe.modes
  <<" delta_um="<<options.delta*1e6
  <<" min_detJ="<<probe.min_jac
  <<" max_pore_wall_error_m="<<probe.max_wall_error
  <<" max_ice_volume_D_rel="<<probe.max_volume_relative
  <<" checkpoint_gib="<<double(snapshot_bytes/gib)
  <<" qp_linearization_gib="<<double(qp_bytes/gib)
  <<" history_state_gib="<<double(state_bytes/gib)
  <<" writes=0 forward_solves=0\n";
 return 0;
}catch(const std::exception& error){
 std::cerr<<"P10J_PREFLIGHT_ERROR "<<error.what()<<'\n';return 2;
}}
