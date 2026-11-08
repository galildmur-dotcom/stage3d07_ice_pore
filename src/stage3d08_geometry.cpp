// Stage 3D-08A: compatible Gmsh MSH2.2 Tet10 geometric perturbations.
// Does NOT solve temperature/mechanics or claim to compute a shape derivative of j6.
// Boundary convention: n points from cavity into ice. Positive radius delta enlarges cavity.
#include "tet10_shared.hpp"
#include "qt_runner_paths.hpp"
#include <unordered_set>
#include <cstdlib>
#include <limits>
using namespace std;
namespace {
constexpr double R=RBASE;
const V C{0,0,.03};
struct Options {
 fs::path mesh=fs::path(STAGE3D06_ROOT_DIR)/"meshes"/"H0.msh";
 fs::path out=fs::path(STAGE3D06_ROOT_DIR)/"LOCAL_RUNS"/"SHAPE_STAGE08"/"GEOMETRY_H0";
 string mode="radius", steps="10,5,2.5";double cutoff=.005;int q=3;bool dry=false;
};
string mode_label(const string& s){
 if(s=="radius"||s=="tx"||s=="ty"||s=="tz"||s=="y20"||s=="y21c"||s=="y21s"||s=="y22c"||s=="y22s")return s;
 throw runtime_error("Invalid --mode; use radius|tx|ty|tz|y20|y21c|y21s|y22c|y22s");
}
Options parse(int argc,char**argv){
 Options o;
 for(int i=1;i<argc;++i){string f=argv[i];auto val=[&](){if(i+1>=argc)throw runtime_error("Missing value after "+f);return string(argv[++i]);};
  if(f=="--mesh")o.mesh=val();else if(f=="--out")o.out=val();else if(f=="--mode")o.mode=mode_label(val());
  else if(f=="--delta-um")o.steps=val();else if(f=="--cutoff-mm")o.cutoff=stod(val())*.001;
  else if(f=="--quad")o.q=stoi(val());else if(f=="--dry-run")o.dry=true;
  else if(f=="--help"||f=="-h"){
    cout<<"Stage3D08A: geometric shape perturbations of Gmsh 2.2 Tet10 mesh\n"
          "--mesh H0.msh --out DIRECTORY --mode radius|tx|ty|tz|y20|y21c|y21s|y22c|y22s\n"
          "--delta-um 10,5,2.5 --cutoff-mm 5 --quad 3|4 --dry-run\n"
          "Positive radius displacement expands cavity; no mechanical solve.\n";exit(0);}
  else throw runtime_error("Unknown argument "+f);
 }
 if(o.q!=3&&o.q!=4)throw runtime_error("--quad 3|4");
 if(o.cutoff<=.003||o.cutoff>=.0055)throw runtime_error("cutoff must be >3mm and <5.5mm to preserve B6");
 if(!fs::is_regular_file(o.mesh))throw runtime_error("Mesh not found: "+o.mesh.string());
 return o;
}
vector<double> deltas(const string& s){
 istringstream in(s);vector<double>d;string x;
 while(getline(in,x,',')){size_t end=0;double um=stod(x,&end);if(end!=x.size()||!(um>0&&um<=20))throw runtime_error("delta must be (0,20] um");d.push_back(um*1e-6);}
 if(d.empty())throw runtime_error("no deltas");
 return d;
}
double harmonic(const string&m,const V&n){
 if(m=="y20")return sqrt(5./(16*PI))*(3*n.z*n.z-1);
 if(m=="y21c")return sqrt(15./(4*PI))*n.x*n.z;
 if(m=="y21s")return sqrt(15./(4*PI))*n.y*n.z;
 if(m=="y22c")return sqrt(15./(16*PI))*(n.x*n.x-n.y*n.y);
 if(m=="y22s")return sqrt(15./(4*PI))*n.x*n.y;
 throw runtime_error("not a harmonic: "+m);
}
double support(double r,double cutoff){
 if(r<=R)return 1.;
 if(r>=cutoff)return 0.;
 double t=(r-R)/(cutoff-R);
 return 1.-t*t*(3-2*t); // C1 at inner sphere and outer cut-off
}
V perturb(V x,const string&mode,double delta,double cutoff){
 const V d=x-C;double r=norm(d);if(!(r>0))throw runtime_error("zero radial coordinate");
 double f=support(r,cutoff);if(f==0)return x;
 V n=d/r;
 if(mode=="radius")return x+n*(delta*f);
 if(mode=="tx")return x+V{delta*f,0,0};
 if(mode=="ty")return x+V{0,delta*f,0};
 if(mode=="tz")return x+V{0,0,delta*f};
 return x+n*(delta*f*harmonic(mode,n));
}
struct GeometryStats {double minDet=numeric_limits<double>::infinity(),iceVolume=0,maxWallError=0,maxOuterMove=0,maxB6Move=0,maxNodeShift=0;
 size_t nqp=0,bad=0,wallNodes=0,outerNodes=0,b6Nodes=0;};
vector<array<double,3>> qpoints(int quad){
 vector<array<double,3>> q;
 if(quad==3){for(auto a:g3)for(auto b:g3)for(auto c:g3)q.push_back({a.x,(1-a.x)*b.x,(1-a.x)*(1-b.x)*c.x});}
 else {for(auto a:g4)for(auto b:g4)for(auto c:g4)q.push_back({a.x,(1-a.x)*b.x,(1-a.x)*(1-b.x)*c.x});}
 return q;
}
GeometryStats inspect(const Mesh&original,const Mesh&mod,const Imported& imp,const string&mode,double delta,int quad){
 GeometryStats st;const auto Q=qpoints(quad);
 for(const auto& tet:mod.tets)for(const auto&q:Q){const double det=teval(mod,tet,q[0],q[1],q[2]).det;
   st.minDet=min(st.minDet,det);++st.nqp;if(!(det>0)||!isfinite(det))++st.bad;}
 // Numerical 3x Gauss Duffy quadrature of curved-Tet10 volume.
 for(const auto&t:mod.tets){
  if(quad==3){for(auto a:g3)for(auto b:g3)for(auto c:g3){double r=a.x,s=(1-r)*b.x,z=(1-r)*(1-b.x)*c.x;
      st.iceVolume+=a.w*b.w*c.w*(1-r)*(1-r)*(1-b.x)*teval(mod,t,r,s,z).det;}}
  else{for(auto a:g4)for(auto b:g4)for(auto c:g4){double r=a.x,s=(1-r)*b.x,z=(1-r)*(1-b.x)*c.x;
      st.iceVolume+=a.w*b.w*c.w*(1-r)*(1-r)*(1-b.x)*teval(mod,t,r,s,z).det;}}
 }
 unordered_set<int> wall,outer,b6;
 for(const auto& face:mod.faces)for(int idx:face.nodes)(face.tag==8?wall:outer).insert(idx);
 for(const auto& face:imp.internal)for(int idx:face.nodes)b6.insert(idx);
 st.wallNodes=wall.size();st.outerNodes=outer.size();st.b6Nodes=b6.size();
 for(int idx:wall){const auto&x=mod.nodes.at(idx);double target=R;
   if(mode=="radius")target+=delta;
   else if(mode=="tx"||mode=="ty"||mode=="tz"){
     V ctr=C;
     if(mode=="tx")ctr.x+=delta;
     if(mode=="ty")ctr.y+=delta;
     if(mode=="tz")ctr.z+=delta;
     st.maxWallError=max(st.maxWallError,abs(norm(x-ctr)-R));continue;
   } else {auto n=unit(original.nodes.at(idx)-C);target+=delta*harmonic(mode,n);}
   st.maxWallError=max(st.maxWallError,abs(norm(x-C)-target));
 }
 for(int idx:outer)st.maxOuterMove=max(st.maxOuterMove,norm(mod.nodes[idx]-original.nodes[idx]));
 for(int idx:b6)st.maxB6Move=max(st.maxB6Move,norm(mod.nodes[idx]-original.nodes[idx]));
 for(size_t i=0;i<mod.nodes.size();++i)st.maxNodeShift=max(st.maxNodeShift,norm(mod.nodes[i]-original.nodes[i]));
 if(st.bad||!(st.minDet>0))throw runtime_error("Tet10 nonpositive detJ in "+to_string(st.bad)+" quadrature points");
 if(st.maxWallError>5e-11)throw runtime_error("pore geometry consistency failure: "+to_string(st.maxWallError));
 if(st.maxOuterMove>0||st.maxB6Move>0)throw runtime_error("outer boundary or fixed B6 moved");
 if(st.wallNodes<10||st.outerNodes<10||st.b6Nodes<10)throw runtime_error("missing pore/outer/B6 tags");
 return st;
}
// Keep ALL MSH records, tags, local ordering and node IDs intact. Only node coordinates change.
void write_msh(const fs::path&source,const fs::path&destination,const vector<V>&newNodes){
 ifstream in(source);if(!in)throw runtime_error("failed to open original mesh");
 fs::create_directories(destination.parent_path());ofstream out(destination,ios::trunc);
 if(!out)throw runtime_error("failed to create generated mesh: "+destination.string());
 string line;bool seen=false;size_t k=0;
 while(getline(in,line)){
  out<<line<<'\n';
  if(line=="$Nodes"){
   if(seen)throw runtime_error("duplicate nodes section");
   seen=true;
   if(!getline(in,line))throw runtime_error("missing $Nodes count");
   out<<line<<'\n';
   size_t n=stoull(line);if(n!=newNodes.size())throw runtime_error("original and transformed mesh node count mismatch");
   out<<setprecision(17);
   for(k=0;k<n;++k){if(!getline(in,line))throw runtime_error("truncated nodes");
    istringstream rec(line);int id=0;double x,y,z;if(!(rec>>id>>x>>y>>z)||id<1)throw runtime_error("invalid node line");
    string extra;if(rec>>extra)throw runtime_error("unexpected node columns");
    const V v=newNodes[k];out<<id<<' '<<v.x<<' '<<v.y<<' '<<v.z<<'\n';
   }
  }
 }
 if(!seen||!out)throw runtime_error("failed to export Gmsh mesh");
}
string fmt_um(double v){ostringstream s;s<<fixed<<setprecision(3)<<v*1e6;string t=s.str();for(char &c:t)if(c=='.')c='p';return t;}
}
int main(int argc,char** argv){try{
 const Options opt=parse(argc,argv);const auto dd=deltas(opt.steps);
 cout<<"Stage3D08A, mesh="<<opt.mesh<<" mode="<<opt.mode<<" q="<<opt.q<<" cutoff="<<opt.cutoff*1000<<" mm\n";
 if(opt.dry){cout<<"DRY_RUN_OK; no files changed\n";return 0;}
 auto imp=read_msh(opt.mesh);const Mesh&baseline=imp.mesh;
 fs::create_directories(opt.out);ofstream table(opt.out/"P08_GEOMETRY_REPORT.csv",ios::trunc);
 table<<"mode,delta_um,sign,nodes,tet10,qp_count,min_detJ,ice_volume_m3,pore_wall_nodes,pore_max_radius_error_m,outer_max_move_m,B6_max_move_m,max_node_shift_m,mesh_file\n"<<setprecision(16);
 vector<tuple<double,double,double>> pairs;
 const auto B=inspect(baseline,baseline,imp,opt.mode,0,opt.q);
 table<<opt.mode<<",0,0,"<<baseline.nodes.size()<<','<<baseline.tets.size()<<','<<B.nqp<<','<<B.minDet<<','<<B.iceVolume<<','<<B.wallNodes<<','<<B.maxWallError<<','<<B.maxOuterMove<<','<<B.maxB6Move<<","<<B.maxNodeShift<<','<<opt.mesh.filename().string()<<"\n";
 for(double a:dd){double volumes[2]{};
  for(int k=0;k<2;++k){const double d=(k==0? a:-a);Mesh changed=baseline;
   for(auto& x:changed.nodes)x=perturb(x,opt.mode,d,opt.cutoff);
   const GeometryStats s=inspect(baseline,changed,imp,opt.mode,d,opt.q);
   string name=opt.mesh.stem().string()+"_P08_"+opt.mode+"_"+(d>0?"plus":"minus")+"_"+fmt_um(a)+"um.msh";
   write_msh(opt.mesh,opt.out/name,changed.nodes);volumes[k]=s.iceVolume;
   table<<opt.mode<<','<<a*1e6<<','<<(d>0?1:-1)<<','<<changed.nodes.size()<<','<<changed.tets.size()<<','<<s.nqp<<','<<s.minDet<<','<<s.iceVolume<<','<<s.wallNodes<<','<<s.maxWallError<<','<<s.maxOuterMove<<','<<s.maxB6Move<<','<<s.maxNodeShift<<','<<name<<'\n';
   cout<<name<<" minDet="<<s.minDet<<" wall_error="<<s.maxWallError<<" m\n"<<flush;
  }
  pairs.emplace_back(a,(volumes[0]-volumes[1])/(2*a),volumes[0]-volumes[1]);
 }
 ofstream check(opt.out/"P08_GEOMETRIC_DERIVATIVE.csv");check<<setprecision(16)<<"mode,delta_um,dV_ice_damplitude_m2,exact_dV_radial_m2,relative_error_radial,expected_zero_nonradial\n";
 for(auto [d,D,span]:pairs){double analytic=-4*PI*R*R;
  check<<opt.mode<<','<<d*1e6<<','<<D<<','<<(opt.mode=="radius"?analytic:0)<<','<<(opt.mode=="radius"?abs(D-analytic)/abs(analytic):0)<<','<<(opt.mode!="radius"?1:0)<<'\n';
  if(opt.mode=="radius"&&abs(D-analytic)/abs(analytic)>.02)throw runtime_error("radius volume derivative more than 2% from analytic sphere; inspect geometry");
  if(opt.mode!="radius"&&abs(D)>.02*4*PI*R*R)throw runtime_error("nonradial first-order volume derivative unexpectedly large");
 }
 cout<<"GEOMETRY_OK; preserved Gmsh physical tags and both B6 and exterior; no FEM re-solve\n";
 return 0;
 }catch(const exception&e){cerr<<"P08_GEOMETRY_ERROR: "<<e.what()<<'\n';return 2;}}
