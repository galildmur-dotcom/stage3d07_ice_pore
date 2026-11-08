// Stage 3D-10O: generate a locally graded pore-wall Tet10 mesh in Gmsh,
// then independently audit *volumetric* near-wall and far-field element sizes.
// Standalone C++20 executable: no FEM libraries or Python required.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#include <process.h>
#else
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace fs=std::filesystem;
namespace p10o {

void require(bool ok,const std::string& reason){
 if(!ok)throw std::runtime_error("P10O: "+reason);
}
struct Point{double x=0,y=0,z=0;};
Point operator-(Point a,Point b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
Point cross(Point a,Point b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
double dot(Point a,Point b){return a.x*b.x+a.y*b.y+a.z*b.z;}
double length(Point a){return std::sqrt(dot(a,a));}
constexpr Point center{0,0,0.03};
constexpr double a=0.001,r6=0.006;
constexpr std::array<double,7> bounds_mm{0.02,0.25,0.5,1,2,5,15};
constexpr std::array<const char*,8> bins{
 "first_wall_layer_0_0p02mm", "wall_0p02_0p25mm",
 "wall_0p25_0p5mm", "wall_0p5_1mm", "wall_1_2mm",
 "wall_2_5mm", "intermediate_5_15mm", "far_over_15mm"};

struct Mesh{
 std::vector<Point> nodes;
 std::vector<std::array<int,10>> tets;
 std::vector<std::array<int,6>> pore,b6;
 std::array<std::uint64_t,10> tags{};
};

Mesh read_msh(const fs::path& path){
 std::ifstream in(path);
 require(bool(in),"cannot read mesh "+path.string());
 Mesh mesh;
 std::string token;
 while(in>>token){
  if(token=="$MeshFormat"){
   double ver=0;int binary=1,width=0;
   in>>ver>>binary>>width;
   require(ver>=2.2&&ver<3&&binary==0&&width==8,
           "requires Gmsh MSH2.2 ASCII");
   in>>token;require(token=="$EndMeshFormat","bad MeshFormat terminator");
  }else if(token=="$Nodes"){
   std::size_t n=0;in>>n;
   require(n>100&&n<50000000,"implausible node count");
   mesh.nodes.resize(n+1);
   std::vector<uint8_t> seen(n+1,0);
   for(std::size_t i=0;i<n;++i){
    std::size_t id=0;Point p;in>>id>>p.x>>p.y>>p.z;
    require(bool(in)&&id>0&&id<=n&&!seen[id],"bad/duplicate node ID");
    require(std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z),
            "nonfinite coordinates");
    seen[id]=1;mesh.nodes[id]=p;
   }
   in>>token;require(token=="$EndNodes","bad Nodes terminator");
  }else if(token=="$Elements"){
   std::size_t count=0;in>>count;
   require(!mesh.nodes.empty()&&count>100&&count<70000000,
           "implausible element count or no nodes");
   for(std::size_t i=0;i<count;++i){
    std::uint64_t id=0;int type=0,ntags=0;
    in>>id>>type>>ntags;
    require(bool(in)&&ntags>=1&&ntags<32,"bad element record");
    int physical=0;
    for(int k=0;k<ntags;++k){int value=0;in>>value;if(!k)physical=value;}
    require(physical>=1&&physical<=9,"unexpected physical tag");
    if(type==11){
     require(physical==1,"Tet10 must belong to ICE_VOLUME tag 1");
     std::array<int,10> t{};
     for(int& node:t){in>>node;require(node>0&&std::size_t(node)<mesh.nodes.size(),"bad Tet10 node");}
     mesh.tets.push_back(t);
    }else if(type==9){
     require(physical>=2&&physical<=9,"Tri6 surface physical tag missing");
     std::array<int,6> t{};
     for(int& node:t){in>>node;require(node>0&&std::size_t(node)<mesh.nodes.size(),"bad Tri6 node");}
     ++mesh.tags[std::size_t(physical)];
     if(physical==8)mesh.pore.push_back(t);
     if(physical==9)mesh.b6.push_back(t);
    }else throw std::runtime_error("P10O: requires Tri6+Tet10, found type="+
                                  std::to_string(type));
   }
   in>>token;require(token=="$EndElements","bad Elements terminator");
  }else if(!token.empty()&&token[0]=='$'&&token.rfind("$End",0)!=0){
   const auto end="$End"+token.substr(1);
   std::string line;std::getline(in,line);
   bool done=false;
   while(std::getline(in,line))if(line==end){done=true;break;}
   require(done,"unterminated Gmsh section "+token);
  }else require(false,"unexpected token in Gmsh file: "+token);
 }
 require(mesh.tets.size()>100&&mesh.pore.size()>10&&mesh.b6.size()>10,
         "missing Tet10, pore Tri6 or B6 Tri6");
 for(int k=2;k<=9;++k)require(mesh.tags[std::size_t(k)]>0,
                            "missing physical surface tag "+std::to_string(k));
 const auto radial=[&](Point p){return length(p-center);};
 for(const auto& tri:mesh.pore)for(int id:tri)
  require(std::abs(radial(mesh.nodes[std::size_t(id)])-a)<5e-9,
          "pore Tri6 node does not lie on radius 1 mm sphere");
 for(const auto& tri:mesh.b6)for(int id:tri)
  require(std::abs(radial(mesh.nodes[std::size_t(id)])-r6)<5e-8,
          "B6 Tri6 node does not lie on radius 6 mm sphere");
 return mesh;
}

double percentile(std::vector<double>& values,double q){
 require(!values.empty(),"empty quantile population");
 const auto idx=std::min(values.size()-1,
        std::size_t(std::llround(q*double(values.size()-1))));
 std::nth_element(values.begin(),values.begin()+idx,values.end());
 return values[idx];
}
struct Band{
 std::vector<double> h_mm,edge_ratio;
 double median=0,p10=0,p90=0,median_ratio=0;
};
struct Audit{
 std::string label;
 std::size_t nodes=0,tets=0,pore=0,b6=0;
 std::array<Band,8> band;
 double pore_median_mm=0,min_det6=std::numeric_limits<double>::infinity();
 double near_bulk_mm=0,far_bulk_mm=0;
 double history_gib=0,buffers_gib=0;
};

Audit analyze(const fs::path& file,const std::string& name){
 const Mesh mesh=read_msh(file);
 Audit out;
 out.label=name;
 out.nodes=mesh.nodes.size()-1;
 out.tets=mesh.tets.size();
 out.pore=mesh.pore.size();out.b6=mesh.b6.size();
 std::vector<double> pore_edges;
 pore_edges.reserve(mesh.pore.size()*3);
 const auto edge=[&](int i,int j){return length(mesh.nodes[std::size_t(i)]-
                                          mesh.nodes[std::size_t(j)]);};
 for(const auto& t:mesh.pore){
  pore_edges.push_back(edge(t[0],t[1])*1000);
  pore_edges.push_back(edge(t[1],t[2])*1000);
  pore_edges.push_back(edge(t[2],t[0])*1000);
 }
 out.pore_median_mm=percentile(pore_edges,.5);
 constexpr int ends[6][2]={{0,1},{0,2},{0,3},{1,2},{1,3},{2,3}};
 for(const auto& t:mesh.tets){
  const Point x0=mesh.nodes[std::size_t(t[0])];
  const Point x1=mesh.nodes[std::size_t(t[1])];
  const Point x2=mesh.nodes[std::size_t(t[2])];
  const Point x3=mesh.nodes[std::size_t(t[3])];
  const double det=dot(x1-x0,cross(x2-x0,x3-x0));
  out.min_det6=std::min(out.min_det6,det);
  require(std::isfinite(det)&&det>0,
          "inverted or degenerate linear corner tetrahedron");
  std::array<double,6> lengths{};
  for(int k=0;k<6;++k)
   lengths[std::size_t(k)]=edge(t[ends[k][0]],t[ends[k][1]])*1000;
  std::sort(lengths.begin(),lengths.end());
  const double h=.5*(lengths[2]+lengths[3]);
  const double ratio=lengths[5]/lengths[0];
  double distance=std::numeric_limits<double>::infinity();
  for(int k=0;k<4;++k)
   distance=std::min(distance,length(mesh.nodes[std::size_t(t[k])]-center)-a);
  const double dmm=std::max(0.,distance*1000.);
  const std::size_t bin=std::size_t(std::upper_bound(
       bounds_mm.begin(),bounds_mm.end(),dmm)-bounds_mm.begin());
  out.band[bin].h_mm.push_back(h);
  out.band[bin].edge_ratio.push_back(ratio);
 }
 for(auto& b:out.band){
  if(b.h_mm.empty())continue;
  b.p10=percentile(b.h_mm,.1);
  b.p90=percentile(b.h_mm,.9);
  b.median=percentile(b.h_mm,.5);
  b.median_ratio=percentile(b.edge_ratio,.5);
 }
 require(!out.band.front().h_mm.empty()&&!out.band.back().h_mm.empty(),
         "no near-wall or far-field volume elements");
 out.near_bulk_mm=out.band.front().median;
 out.far_bulk_mm=out.band.back().median;
 // P10N original limit: (steps+4) * nq * sizeof(State) < 8 GiB.
 // For current EDV_VAR P10N: 6 steps, 27 quadrature points, 96 bytes/State.
 constexpr double gib=1073741824.;
 out.history_gib=double(out.tets)*27*96*6/gib;
 out.buffers_gib=double(out.tets)*27*96*10/gib;
 return out;
}

void save(const fs::path& path,const std::vector<Audit>& data){
 std::ofstream f(path);
 require(bool(f),"cannot create audit CSV");
 f<<"mesh,region,distance_lower_mm,distance_upper_mm,tet10_count,"
    "median_volume_corner_edge_mm,p10_volume_corner_edge_mm,"
    "p90_volume_corner_edge_mm,median_max_min_edge_ratio,"
    "nodes_total,tet10_total,pore_tri6_total,b6_tri6_total,"
    "pore_surface_median_edge_mm,near_bulk_edge_mm,far_bulk_edge_mm,"
    "far_to_near_ratio,min_linear_det6,estimated_held_history_gib,"
    "estimated_state_buffers_gib\n";
 f<<std::setprecision(14);
 for(const auto& v:data){
  for(size_t i=0;i<v.band.size();++i){
   const auto& b=v.band[i];
   const double lo=i==0?0:bounds_mm[i-1];
   const double hi=i==7?std::numeric_limits<double>::infinity():bounds_mm[i];
   f<<v.label<<','<<bins[i]<<','<<lo<<',';
   if(std::isfinite(hi))f<<hi;
   f<<','<<b.h_mm.size()<<','<<b.median<<','<<b.p10<<','<<b.p90
    <<','<<b.median_ratio<<','<<v.nodes<<','<<v.tets<<','<<v.pore
    <<','<<v.b6<<','<<v.pore_median_mm<<','<<v.near_bulk_mm
    <<','<<v.far_bulk_mm<<','<<v.far_bulk_mm/v.near_bulk_mm
    <<','<<v.min_det6<<','<<v.history_gib<<','<<v.buffers_gib<<'\n';
  }
 }
 f.close();require(bool(f),"failed closing audit CSV");
}

void spawn(const fs::path& executable,const std::vector<std::string>& args){
 require(fs::is_regular_file(executable),"gmsh.exe missing: "+executable.string());
#ifdef _WIN32
 std::vector<std::wstring> values{executable.wstring()};
 for(const auto& arg:args)values.push_back(fs::path(arg).wstring());
 std::vector<const wchar_t*> argv;
 for(const auto& item:values)argv.push_back(item.c_str());
 argv.push_back(nullptr);
 const auto status=_wspawnv(_P_WAIT,values.front().c_str(),argv.data());
 require(status==0,"Gmsh subprocess returned status "+std::to_string(status));
#else
 std::vector<std::string> values{executable.string()};
 values.insert(values.end(),args.begin(),args.end());
 std::vector<char*> argv;
 for(auto& item:values)argv.push_back(item.data());
 argv.push_back(nullptr);
 const pid_t pid=fork();
 require(pid>=0,"fork failed");
 if(pid==0){execv(executable.c_str(),argv.data());_exit(127);}
 int status=0;
 require(waitpid(pid,&status,0)==pid,"Gmsh waitpid failed");
 require(WIFEXITED(status)&&WEXITSTATUS(status)==0,
         "Gmsh child process failed");
#endif
}

struct Settings{
 fs::path gmsh,geo,mesh,baseline,out;
 int threads=4;
 bool audit_only=false;
};

Settings parse(int argc,char** argv){
 Settings c;
 for(int i=1;i<argc;++i){
  const std::string flag=argv[i];
  auto value=[&](){require(i+1<argc,"missing value after "+flag);
                   return std::string(argv[++i]);};
  if(flag=="--gmsh")c.gmsh=value();
  else if(flag=="--geo")c.geo=value();
  else if(flag=="--mesh")c.mesh=value();
  else if(flag=="--baseline")c.baseline=value();
  else if(flag=="--out")c.out=value();
  else if(flag=="--threads")c.threads=std::stoi(value());
  else if(flag=="--audit-only")c.audit_only=true;
  else if(flag=="--help"){
   std::cout<<"stage3d10o_mesh_prepare --gmsh GMSH_EXE --geo GEO "
    "--mesh NEW_MSH --baseline H4_MSH --out NEW_AUDIT_DIR "
    "[--threads 4] [--audit-only (existing mesh)]\n";
   std::exit(0);
  }else require(false,"unknown argument: "+flag);
 }
 require(!c.mesh.empty()&&!c.out.empty(),"--mesh and --out required");
 require(c.threads>=1&&c.threads<=8,"threads outside 1..8");
 require(!fs::exists(c.out),"--out exists; choose a new audit folder");
 if(c.audit_only)require(fs::is_regular_file(c.mesh),"audit mesh missing");
 else{
  require(fs::is_regular_file(c.gmsh),"--gmsh executable missing");
  require(fs::is_regular_file(c.geo),"--geo file missing");
  require(!fs::exists(c.mesh),"target mesh already exists; will not overwrite");
 }
 if(!c.baseline.empty())require(fs::is_regular_file(c.baseline),
                                "baseline mesh missing");
 return c;
}

int run(const Settings& c){
 if(!c.audit_only){
  const auto mesh=fs::absolute(c.mesh);
  const auto geo=fs::absolute(c.geo);
  const auto gmsh=fs::absolute(c.gmsh);
  fs::create_directories(mesh.parent_path());
  const auto original=fs::current_path();
  fs::current_path(geo.parent_path());
  try{
   spawn(gmsh,{"-3",geo.string(),"-format","msh2","-nt",
               std::to_string(c.threads),"-v","2","-nopopup",
               "-o",mesh.string()});
  }catch(...){fs::current_path(original);throw;}
  fs::current_path(original);
 }
 std::vector<Audit> data;
 if(!c.baseline.empty())data.push_back(analyze(c.baseline,
                                                c.baseline.stem().string()+"_baseline"));
 data.push_back(analyze(c.mesh,c.mesh.stem().string()));
 fs::create_directories(c.out);
 save(c.out/"P10O_MESH_AUDIT.csv",data);
 for(const auto& v:data){
  std::cout<<std::scientific<<std::setprecision(10)
   <<"P10O_MESH mesh="<<v.label<<" nodes="<<v.nodes<<" tet10="<<v.tets
   <<" pore_tri6="<<v.pore<<" b6_tri6="<<v.b6
   <<" pore_surface_mm="<<v.pore_median_mm
   <<" bulk_first_layer_mm="<<v.near_bulk_mm
   <<" bulk_far_mm="<<v.far_bulk_mm
   <<" bulk_far_to_near_ratio="<<v.far_bulk_mm/v.near_bulk_mm
   <<" estimated_P10N_state_buffers_gib="<<v.buffers_gib<<'\n';
 }
 bool good=true;
 const auto& candidate=data.back();
 if(data.size()==2){
  const auto& baseline=data.front();
  const double near_ratio=candidate.near_bulk_mm/baseline.near_bulk_mm;
  const double far_ratio=candidate.far_bulk_mm/baseline.far_bulk_mm;
  std::cout<<"P10O_COMPARE near_bulk_ratio="<<near_ratio
           <<" far_bulk_ratio="<<far_ratio
           <<" pore_surface_ratio="<<candidate.pore_median_mm/
                                         baseline.pore_median_mm<<'\n';
  good &= near_ratio<0.90&&far_ratio>0.75&&far_ratio<1.25;
  good &= candidate.pore_median_mm<0.90*baseline.pore_median_mm;
 }
 const bool memory_ok=candidate.buffers_gib<8.0;
 if(!memory_ok){
  std::cout<<"P10O_BUDGET_EXCEEDED P10N would reject this mesh; "
              "choose a milder wallSize before FEM\n";
  good=false;
 }
 std::cout<<(good?"P10O_MESH_AUDIT_OK":"P10O_MESH_AUDIT_REVIEW")
          <<" mesh="<<c.mesh.stem().string()
          <<" P10N_estimated_history_gib="<<candidate.history_gib
          <<" P10N_estimated_state_buffers_gib="<<candidate.buffers_gib
          <<" curved_Tet10_check=NOT_DONE_RUN_P10N_PREFLIGHT\n";
 return good?0:3;
}
} // namespace p10o

int main(int argc,char** argv){
 try{return p10o::run(p10o::parse(argc,argv));}
 catch(const std::exception& e){std::cerr<<"P10O_ERROR: "<<e.what()<<'\n';return 2;}
}
