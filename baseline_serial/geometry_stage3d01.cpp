// Stage3D01: independent offline cubed-sphere Tet10 geometry and integration harness.
// SI geometry, no thermal/mechanical physics. C++20 only, GPL-free internal generator.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>
using namespace std;
namespace fs=std::filesystem;
constexpr double PI=3.141592653589793238462643383279502884;
constexpr double RBASE=0.001;
constexpr double VD=0.06*0.06*0.05;
struct V { double x=0,y=0,z=0; V operator+(V a)const{return{x+a.x,y+a.y,z+a.z};} V operator-(V a)const{return{x-a.x,y-a.y,z-a.z};} V operator*(double s)const{return{x*s,y*s,z*s};} V operator/(double s)const{return{x/s,y/s,z/s};} };
V operator*(double s,V v){return v*s;}
double dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}
V cross(V a,V b){return{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
double norm(V v){return sqrt(dot(v,v));}
V unit(V v){return v/norm(v);}
using Tri=array<int,3>; using Tet=array<int,10>; using Tri6=array<int,6>;
struct Face{Tri6 nodes;int tag;};
struct Mesh{vector<V> nodes;vector<Tet> tets;vector<Face> faces; vector<int> ring; V center; double radius; int nr,innerN,nAng;};
// Tags: (1) ICE_VOLUME, (2) TOP_ROBIN, (3) BOTTOM_INSULATED,
// (4,5) X_MINUS/PLUS, (6,7) Y_MINUS/PLUS, (8) PORE_WALL.
const vector<string> names={"", "ICE_VOLUME", "TOP_ROBIN", "BOTTOM_INSULATED", "X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS", "PORE_WALL"};
struct Key {int x,y,z; bool operator<(const Key &o) const {return tie(x,y,z)<tie(o.x,o.y,o.z);} };
using Edge=pair<int,int>;
Edge edge(int a,int b){if(a>b)swap(a,b);return {a,b};}
using FKey=array<int,3>;
FKey key3(Tri q){sort(q.begin(),q.end());return q;}
V cube_to_outer(Key k,int n){double x=double(k.x)/n,y=double(k.y)/n,z=double(k.z)/n;return{.03*x,.03*y,.03+(z>0?.02:.03)*z};}
vector<Tri> angular_triangles(int n,vector<Key>& verts){
  map<Key,int> ids;vector<Tri> tri;
  auto idx=[&](Key k){auto it=ids.find(k);if(it!=ids.end())return it->second;int i=int(verts.size());ids.emplace(k,i);verts.push_back(k);return i;};
  for(int face=0;face<6;++face){
    auto point=[&](int a,int b)->Key{
      // integer coordinates on the six faces of an abstract reference cube
      if(face==0)return{n,a,b};
      if(face==1)return{-n,a,b};
      if(face==2)return{a,n,b};
      if(face==3)return{a,-n,b};
      if(face==4)return{a,b,n};
      return{a,b,-n};
    };
    for(int i=0;i<n;++i)for(int j=0;j<n;++j){
      int a=-n+2*i,b=-n+2*j,step=2;
      int p=idx(point(a,b)),q=idx(point(a+step,b)),r=idx(point(a+step,b+step)),s=idx(point(a,b+step));
      // globally consistent edge diagonals on the angular cubed-sphere
      if(edge(p,r)<edge(q,s)){tri.push_back({p,q,r});tri.push_back({p,r,s});}
      else{tri.push_back({p,q,s});tri.push_back({q,r,s});}
    }
  }
  return tri;
}
double jac_linear(V a,V b,V c,V d){return dot(b-a,cross(c-a,d-a));}
Mesh generate(int n,int innerN,int outerN,V center={0,0,.03},double rad=RBASE){
  Mesh m; m.center=center;m.radius=rad;m.innerN=innerN;m.nr=innerN+outerN;m.nAng=n;
  vector<Key> angular;vector<Tri> angularTris=angular_triangles(n,angular);
  const int N=int(angular.size());
  vector<V> outer(N),dirs(N);vector<double> rout(N),rB6(N);
  for(int i=0;i<N;++i){
    outer[i]=cube_to_outer(angular[i],n);dirs[i]=unit(outer[i]-center);rout[i]=norm(outer[i]-center);
    // Intersection with the FIXED observation sphere |x-c0|=6R0.
    V fixedC{0,0,.03},delta=center-fixedC;
    double projection=dot(dirs[i],delta),discr=projection*projection+36*RBASE*RBASE-dot(delta,delta);
    if(discr<=0)throw runtime_error("perturbed cavity centre outside observation sphere");
    rB6[i]=-projection+sqrt(discr);
    if(rB6[i]<=rad)throw runtime_error("cavity intersects observation sphere");
  }
  // The k=innerN layer is the fixed B6 observation sphere for the base geometry.
  for(int k=0;k<=m.nr;++k){
    for(int i=0;i<N;++i){
      double radius=0;
      if(k<=innerN){double s=double(k)/innerN;radius=rad+(rB6[i]-rad)*pow(s,1.4);}
      else{double s=double(k-innerN)/outerN;double blend=s;radius=rB6[i]+(rout[i]-rB6[i])*blend;}
      m.nodes.push_back(center+dirs[i]*radius);m.ring.push_back(k);
    }
  }
  auto node=[N](int l,int i){return l*N+i;};
  vector<array<int,4>> linear;
  linear.reserve(angularTris.size()*m.nr*3);
  for(int k=0;k<m.nr;++k)for(auto tri:angularTris){
    sort(tri.begin(),tri.end());int a=tri[0],b=tri[1],c=tri[2];
    array<array<int,4>,3> ts={{{node(k,a),node(k,b),node(k,c),node(k+1,c)},
                                {node(k,a),node(k,b),node(k+1,b),node(k+1,c)},
                                {node(k,a),node(k+1,a),node(k+1,b),node(k+1,c)}}};
    for(auto t:ts){
      if(jac_linear(m.nodes[t[0]],m.nodes[t[1]],m.nodes[t[2]],m.nodes[t[3]])<0)swap(t[1],t[2]);
      linear.push_back(t);
    }
  }
  map<Edge,int> middles;
  auto midpoint=[&](int a,int b)->int{
    Edge e=edge(a,b);auto it=middles.find(e);if(it!=middles.end())return it->second;
    V p=(m.nodes[a]+m.nodes[b])*.5;
    if(m.ring[a]==m.ring[b]&&(m.ring[a]==0||m.ring[a]==innerN)){
      // Hole midpoints are ON exact sphere; B6 mids are relaxed to protect Tet10 Jacobians
      const double rr=m.ring[a]==0?rad:6*RBASE;V refC=m.ring[a]==0?center:V{0,0,.03};V projected=refC+unit(p-refC)*rr;double factor=(m.ring[a]==0?1.0:0.65);p=p+(projected-p)*factor;
    }
    int id=int(m.nodes.size());m.nodes.push_back(p);m.ring.push_back(-1);middles.emplace(e,id);return id;
  };
  constexpr int E[6][2]={{0,1},{1,2},{2,0},{0,3},{1,3},{2,3}};
  m.tets.reserve(linear.size());
  for(auto t:linear){Tet ten;for(int i=0;i<4;++i)ten[i]=t[i];for(int i=0;i<6;++i)ten[4+i]=midpoint(t[E[i][0]],t[E[i][1]]);m.tets.push_back(ten);}
  // Only faces with incidence 1 are external. Other faces have exactly two incident tetrahedra.
  struct Info{array<int,3> corners;int count=0;};
  map<FKey,Info> incidence;
  constexpr int FI[4][3]={{0,1,2},{0,3,1},{0,2,3},{1,3,2}};
  for(auto& t:linear)for(auto f:FI){Tri corners={t[f[0]],t[f[1]],t[f[2]]};FKey key=key3(corners);auto& entry=incidence[key];entry.corners=corners;entry.count++;}
  for(auto const& [k,info]:incidence){
    if(info.count==2)continue;
    if(info.count!=1)throw runtime_error("non-manifold exterior facet");
    Tri q=info.corners;int tag=0;
    if(all_of(q.begin(),q.end(),[&](int id){return m.ring[id]==0;}))tag=8;
    else if(all_of(q.begin(),q.end(),[&](int id){return m.ring[id]==m.nr;})){
      V p=m.nodes[q[0]],u=m.nodes[q[1]],v=m.nodes[q[2]];
      auto all=[&](int axis,double val){auto get=[&](V p){return axis==0?p.x:(axis==1?p.y:p.z);};return abs(get(p)-val)<1e-10&&abs(get(u)-val)<1e-10&&abs(get(v)-val)<1e-10;};
      if(all(2,.05))tag=2;else if(all(2,0))tag=3;
      else if(all(0,-.03))tag=4;else if(all(0,.03))tag=5;
      else if(all(1,-.03))tag=6;else if(all(1,.03))tag=7;
    }
    if(tag==0)throw runtime_error("unclassified external facet");
    V normal=cross(m.nodes[q[1]]-m.nodes[q[0]],m.nodes[q[2]]-m.nodes[q[0]]);
    if(tag==8 && dot(normal,m.nodes[q[0]]-center)<0)swap(q[1],q[2]); // n_c -> ice
    if(tag!=8){V target{};if(tag==2)target={0,0,1};if(tag==3)target={0,0,-1};if(tag==4)target={-1,0,0};if(tag==5)target={1,0,0};if(tag==6)target={0,-1,0};if(tag==7)target={0,1,0};if(dot(normal,target)<0)swap(q[1],q[2]);}
    m.faces.push_back({{q[0],q[1],q[2],midpoint(q[0],q[1]),midpoint(q[1],q[2]),midpoint(q[2],q[0])},tag});
  }
  return m;
}
void tetshape(double r,double s,double t,array<double,10>& N,array<array<double,3>,10>& d){
  const double L[4]={1-r-s-t,r,s,t};constexpr double dl[4][3]={{-1,-1,-1},{1,0,0},{0,1,0},{0,0,1}};
  for(int i=0;i<4;++i){N[i]=L[i]*(2*L[i]-1);for(int k=0;k<3;++k)d[i][k]=(4*L[i]-1)*dl[i][k];}
  constexpr int E[6][2]={{0,1},{1,2},{2,0},{0,3},{1,3},{2,3}};
  for(int e=0;e<6;++e){int a=E[e][0],b=E[e][1];N[4+e]=4*L[a]*L[b];for(int k=0;k<3;++k)d[4+e][k]=4*(L[a]*dl[b][k]+L[b]*dl[a][k]);}
}
struct Eval{V p,dr,ds,dt;double det;};
Eval teval(const Mesh& m,const Tet& e,double r,double s,double t){
  array<double,10>N;array<array<double,3>,10>d;tetshape(r,s,t,N,d);Eval z{};
  for(int i=0;i<10;++i){V p=m.nodes[e[i]];z.p=z.p+p*N[i];z.dr=z.dr+p*d[i][0];z.ds=z.ds+p*d[i][1];z.dt=z.dt+p*d[i][2];}
  z.det=dot(z.dr,cross(z.ds,z.dt));return z;
}
struct Gauss{double x,w;};
// 4-point Gauss-Legendre on [0,1]; Duffy tetra: r=a,s=(1-a)b,t=(1-a)(1-b)c.
const array<Gauss,3> g3={{{.1127016653792583,5.0/18.0},{.5,8.0/18.0},{.8872983346207417,5.0/18.0}}};
const array<Gauss,4> g4={{{.0694318442029737,.1739274225687269},{.3300094782075719,.3260725774312731},{.6699905217924281,.3260725774312731},{.9305681557970262,.1739274225687269}}};
const array<Gauss,6> g6={{{.033765242898424,.085662246189585},{.169395306766868,.180380786524069},{.380690406958402,.233956967286346},{.619309593041598,.233956967286346},{.830604693233132,.180380786524069},{.966234757101576,.085662246189585}}};
struct Metrics{double volume=0,v6=0,poreArea=0,poreViaSurface=0,volumeQ3=0,areaQ4=0,firstX=0,firstY=0,firstZ=0,secondX=0,secondY=0,secondZ=0,minDet=1e300,minRatio=1e300,maxEdgeRatio=0,minNormalCos=1;
 V n1{};double n2[3][3]{};double gram[5][5]{};array<int,9> counts{};size_t badDet=0, tetCount=0, poreFaces=0;double minCornerDet=1e300;};
struct Surf {V p,du,dv;};
Surf seval(const Mesh& m,Tri6 e,double a,double b){
  // local L0=1-a-b,L1=a,L2=b; quadratic triangular shape, edge order 01,12,20
  double L[3]={1-a-b,a,b};constexpr double dl[3][2]={{-1,-1},{1,0},{0,1}};
  Surf out{};
  for(int i=0;i<3;++i){double N=L[i]*(2*L[i]-1);V x=m.nodes[e[i]];out.p=out.p+x*N;out.du=out.du+x*((4*L[i]-1)*dl[i][0]);out.dv=out.dv+x*((4*L[i]-1)*dl[i][1]);}
  constexpr int E[3][2]={{0,1},{1,2},{2,0}};
  for(int i=0;i<3;++i){int j=E[i][0],k=E[i][1];V x=m.nodes[e[3+i]];out.p=out.p+x*(4*L[j]*L[k]);out.du=out.du+x*(4*(dl[j][0]*L[k]+L[j]*dl[k][0]));out.dv=out.dv+x*(4*(dl[j][1]*L[k]+L[j]*dl[k][1]));}
  return out;
}
Metrics measure(const Mesh& m){
  Metrics z;z.tetCount=m.tets.size();
  for(const auto& t:m.tets){
    double mini=1e300,maxi=0;
    for(int a=0;a<4;++a)for(int b=a+1;b<4;++b){double l=norm(m.nodes[t[a]]-m.nodes[t[b]]);mini=min(mini,l);maxi=max(maxi,l);}
    z.minRatio=min(z.minRatio,mini/maxi);z.maxEdgeRatio=max(z.maxEdgeRatio,maxi/mini);
    const array<array<double,3>,9> checks={{{.25,.25,.25},{.01,.01,.01},{.97,.01,.01},{.01,.97,.01},{.01,.01,.97},{.5,.2,.2},{.2,.5,.2},{.2,.2,.5},{.1,.1,.1}}};
    for(auto p:checks){double d=teval(m,t,p[0],p[1],p[2]).det;z.minDet=min(z.minDet,d);if(d<=0)z.badDet++;}
    double vol=0;
    for(auto A:g3)for(auto B:g3)for(auto C:g3){
      double r=A.x,s=(1-r)*B.x,tloc=(1-r)*(1-B.x)*C.x;
      z.volumeQ3+=teval(m,t,r,s,tloc).det*A.w*B.w*C.w*(1-r)*(1-r)*(1-B.x);
    }
    for(auto A:g4)for(auto B:g4)for(auto C:g4){
      double r=A.x,s=(1-r)*B.x,tloc=(1-r)*(1-B.x)*C.x;
      auto ev=teval(m,t,r,s,tloc);double jac=ev.det;double weight=A.w*B.w*C.w*(1-r)*(1-r)*(1-B.x);
      z.firstX+=ev.p.x*jac*weight;z.firstY+=ev.p.y*jac*weight;z.firstZ+=ev.p.z*jac*weight;
      z.secondX+=ev.p.x*ev.p.x*jac*weight;z.secondY+=ev.p.y*ev.p.y*jac*weight;z.secondZ+=ev.p.z*ev.p.z*jac*weight;
      z.minDet=min(z.minDet,jac);if(jac<=0)z.badDet++;
      vol+=jac*weight;
    }
    z.volume+=vol;
    // All three vertices on fixed B6 radial shell or inside: base geometry only.
    bool in=true;for(int a=0;a<4;++a){int ring=m.ring[t[a]];if(ring>m.innerN)in=false;}
    if(in)z.v6+=vol;
  }
  for(auto& face:m.faces){z.counts[face.tag]++;if(face.tag!=8)continue;
    z.poreFaces++;
    for(auto A:g4)for(auto B:g4){double a=A.x,b=(1-a)*B.x;auto se=seval(m,face.nodes,a,b);z.areaQ4+=A.w*B.w*(1-a)*norm(cross(se.du,se.dv));}
    for(auto A:g6)for(auto B:g6){double a=A.x,b=(1-a)*B.x;
      auto e=seval(m,face.nodes,a,b);V vec=cross(e.du,e.dv);double w=A.w*B.w*(1-a)*norm(vec);
      V nn=unit(vec),rr=unit(e.p-m.center);
      z.minNormalCos=min(z.minNormalCos,dot(nn,rr));
      z.poreArea+=w;z.n1=z.n1+nn*w;
      z.poreViaSurface+=dot(e.p-m.center,nn)*w/3.0;
      double nx[3]={nn.x,nn.y,nn.z};for(int i=0;i<3;++i)for(int j=0;j<3;++j)z.n2[i][j]+=nx[i]*nx[j]*w;
      double Y[5]={1/sqrt(4*PI),sqrt(3/(4*PI))*rr.x,sqrt(3/(4*PI))*rr.y,sqrt(3/(4*PI))*rr.z,sqrt(5/(16*PI))*(3*rr.z*rr.z-1)};
      for(int i=0;i<5;++i)for(int j=0;j<5;++j)z.gram[i][j]+=Y[i]*Y[j]*w/(m.radius*m.radius);
    }
  }
  return z;
}
void create_parent(fs::path p){if(!p.parent_path().empty())fs::create_directories(p.parent_path());}
void msh(const Mesh&m,fs::path path){
  create_parent(path);ofstream f(path);f<<setprecision(17);
  f<<"$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$PhysicalNames\n8\n";
  for(int i=1;i<=8;++i)f<<(i==1?3:2)<<" "<<i<<" \""<<names[i]<<"\"\n";
  f<<"$EndPhysicalNames\n$Nodes\n"<<m.nodes.size()<<"\n";
  for(size_t i=0;i<m.nodes.size();++i){V p=m.nodes[i];f<<i+1<<" "<<p.x<<" "<<p.y<<" "<<p.z<<"\n";}
  f<<"$EndNodes\n$Elements\n"<<m.tets.size()+m.faces.size()<<"\n";size_t id=0;
  for(auto &t:m.tets){f<<++id<<" 11 2 1 1";for(int v:t)f<<" "<<v+1;f<<"\n";}
  for(auto &s:m.faces){f<<++id<<" 9 2 "<<s.tag<<" "<<s.tag;for(int v:s.nodes)f<<" "<<v+1;f<<"\n";}
  f<<"$EndElements\n";
}
// Re-import Gmsh v2.2 from disk to verify that no data depends on the generator's live objects.
Mesh import_msh(fs::path path,int angularN,int innerN,int outerN,V center={0,0,.03},double rad=RBASE){
  ifstream f(path);if(!f)throw runtime_error("MSH read failed");
  Mesh m;m.nAng=angularN;m.innerN=innerN;m.nr=innerN+outerN;m.center=center;m.radius=rad;
  string word;while(f>>word){
    if(word=="$Nodes"){
      size_t n;f>>n;m.nodes.resize(n);m.ring.resize(n,-1);
      int cornerN=6*angularN*angularN+2;
      for(size_t i=0;i<n;++i){size_t index;f>>index;if(index!=i+1)throw runtime_error("invalid node index in MSH");V& v=m.nodes[i];f>>v.x>>v.y>>v.z;if(i<size_t(cornerN*(m.nr+1)))m.ring[i]=int(i)/cornerN;}
    }else if(word=="$Elements"){
      size_t n;f>>n;
      for(size_t i=0;i<n;++i){size_t id;int typ,nTags;f>>id>>typ>>nTags;vector<int> tags(nTags);for(int& a:tags)f>>a;
        if(typ==11){Tet tet;for(int& a:tet){f>>a;--a;}m.tets.push_back(tet);}
        else if(typ==9){Face face;face.tag=tags.empty()?0:tags[0];for(int& a:face.nodes){f>>a;--a;}m.faces.push_back(face);}
        else throw runtime_error("unknown element type in exported MSH");
      }
    }
  }
  if(m.tets.empty()||m.faces.empty()||m.nodes.empty())throw runtime_error("incomplete MSH re-import");
  return m;
}
void vtu(const Mesh&m,fs::path path,bool surfaceOnly=false,int whichTag=0){
  create_parent(path);ofstream f(path);f<<setprecision(17);
  size_t nc=0;
  if(surfaceOnly){for(auto&s:m.faces)if(!whichTag||whichTag==s.tag){++nc;}}else{nc=m.tets.size();}
  f<<"<?xml version=\"1.0\"?>\n<VTKFile type=\"UnstructuredGrid\" version=\"0.1\" byte_order=\"LittleEndian\">\n<UnstructuredGrid><Piece NumberOfPoints=\""<<m.nodes.size()<<"\" NumberOfCells=\""<<nc<<"\">\n";
  f<<"<Points><DataArray type=\"Float64\" NumberOfComponents=\"3\" format=\"ascii\">\n";
  for(V p:m.nodes)f<<p.x<<" "<<p.y<<" "<<p.z<<"\n";
  f<<"</DataArray></Points>\n<Cells>\n<DataArray type=\"Int32\" Name=\"connectivity\" format=\"ascii\">\n";
  if(surfaceOnly){for(auto &s:m.faces)if(!whichTag||whichTag==s.tag){for(int a:s.nodes)f<<a<<" ";f<<"\n";}}
  else{for(auto &t:m.tets){for(int a:t)f<<a<<" ";f<<"\n";}}
  f<<"</DataArray><DataArray type=\"Int64\" Name=\"offsets\" format=\"ascii\">\n";
  for(size_t i=1;i<=nc;++i)f<<i*(surfaceOnly?6:10)<<" ";
  f<<"\n</DataArray><DataArray type=\"UInt8\" Name=\"types\" format=\"ascii\">\n";
  for(size_t i=0;i<nc;++i)f<<(surfaceOnly?22:24)<<" ";
  f<<"\n</DataArray></Cells>\n<CellData Scalars=\"physical_id\"><DataArray type=\"Int32\" Name=\"physical_id\" format=\"ascii\">\n";
  if(surfaceOnly){for(auto &s:m.faces)if(!whichTag||whichTag==s.tag)f<<s.tag<<" ";}else{for(size_t i=0;i<nc;++i)f<<"1 ";}
  f<<"\n</DataArray></CellData>\n</Piece></UnstructuredGrid></VTKFile>\n";
}
void mesh_summary(const Mesh&m,const Metrics&z,fs::path prefix){
  ofstream f(prefix.string()+"_stats.txt");f<<setprecision(16);
  f<<"nodes "<<m.nodes.size()<<"\ntetra10 "<<m.tets.size()<<"\nfaces "<<m.faces.size()<<"\n";
  for(int i=2;i<=8;++i)f<<names[i]<<" "<<z.counts[i]<<"\n";
  f<<"volume "<<z.volume<<"\nB6volume "<<z.v6<<"\narea "<<z.poreArea<<"\nmin_detJ "<<z.minDet<<"\nnegative_samples "<<z.badDet<<"\nmin_edge_ratio "<<z.minRatio<<"\nmin_normal_radial_cos "<<z.minNormalCos<<"\n";
}
struct Param{string id;int angular,inner,outer;};
const array<Param,3> levels={{{"H0",4,5,8},{"H1",6,8,10},{"H2",9,12,14}}};
void write_headers(fs::path out){
  ofstream f(out/"geometry_report.csv");
  f<<"level,angular_subdiv,radial_inner,radial_outer,nodes,tet10,pore_faces,pore_V_from_ice_m3,pore_V_from_surface_m3,ice_V_m3,B6_ice_V_m3,pore_A_m2,err_pore_V_rel,err_pore_surface_rel,err_ice_V_rel,err_B6_rel,err_pore_A_rel,min_detJ_m3,nonpositive_detJ_samples,min_edge_ratio,min_nc_dot_radial,normal_first_norm_m2,normal2_maxerr_rel,Y_gram_maxerr,volume_q3_vs_q4_rel,area_q4_vs_q6_rel,firstX_m4,firstY_m4,firstZ_m4,secondX_m5,secondY_m5,secondZ_m5\n";
}
void report(Mesh const&m,Metrics const&z,string id,fs::path out){
  const double vp=4*PI*pow(RBASE,3)/3,Ap=4*PI*pow(RBASE,2),v6=(216-1)*vp;
  double maxmom=0,maxgram=0;
  for(int i=0;i<3;++i)for(int j=0;j<3;++j)maxmom=max(maxmom,abs(z.n2[i][j]-(i==j?Ap/3:0))/(Ap/3));
  for(int i=0;i<5;++i)for(int j=0;j<5;++j)maxgram=max(maxgram,abs(z.gram[i][j]-(i==j?1:0)));
  ofstream f(out/"geometry_report.csv",ios::app);f<<setprecision(16);
  f<<id<<","<<m.nAng<<","<<m.innerN<<","<<m.nr-m.innerN<<","<<m.nodes.size()<<","<<m.tets.size()<<","<<z.poreFaces<<","<<(VD-z.volume)<<","<<z.poreViaSurface<<","<<z.volume<<","<<z.v6<<","<<z.poreArea<<","<<abs((VD-z.volume)/vp-1)<<","<<abs(z.poreViaSurface/vp-1)<<","<<abs(z.volume/(VD-vp)-1)<<","<<abs(z.v6/v6-1)<<","<<abs(z.poreArea/Ap-1)<<","<<z.minDet<<","<<z.badDet<<","<<z.minRatio<<","<<z.minNormalCos<<","<<norm(z.n1)<<","<<maxmom<<","<<maxgram<<","<<abs(z.volumeQ3/z.volume-1)<<","<<abs(z.areaQ4/z.poreArea-1)<<","<<z.firstX<<","<<z.firstY<<","<<z.firstZ<<","<<z.secondX<<","<<z.secondY<<","<<z.secondZ<<"\n";
  ofstream g(out/(id+"_normals_and_harmonics.csv"));g<<setprecision(16);
  g<<"row,0,1,2,3,4\n";for(int i=0;i<5;++i){g<<"Y"<<i;for(int j=0;j<5;++j)g<<","<<z.gram[i][j];g<<"\n";}
  g<<"n_first,"<<z.n1.x<<","<<z.n1.y<<","<<z.n1.z<<"\n";
  for(int i=0;i<3;++i)g<<"n_second_"<<i<<","<<z.n2[i][0]<<","<<z.n2[i][1]<<","<<z.n2[i][2]<<"\n";
  cout<<id<<" Tet10="<<m.tets.size()<<" V_pore_err="<<abs((VD-z.volume)/vp-1)<<" A_pore_err="<<abs(z.poreArea/Ap-1)<<" B6_err="<<abs(z.v6/v6-1)<<" min_detJ="<<z.minDet<<" bad="<<z.badDet<<"\n";
}
void perturbation_tests(fs::path out){
  // Test radius variations on the generated finite-element geometry, not on analytic sphere formulas.
  const double ref=4*PI*RBASE*RBASE;
  ofstream f(out/"radius_fd.csv");f<<"delta_over_R,dpore_dR_m2,dice_dR_m2,rel_error_pore,rel_error_ice\n";f<<setprecision(16);
  for(double relative:{0.01,0.005,0.0025}){
    double h=relative*RBASE;
    Mesh p=generate(6,8,10,{0,0,.03},RBASE+h),m=generate(6,8,10,{0,0,.03},RBASE-h);
    double d=(measure(m).volume-measure(p).volume)/(2*h); // pore derivative
    f<<relative<<","<<d<<","<<-d<<","<<abs(d/ref-1)<<","<<abs((-d)/(-ref)-1)<<"\n";
  }
  ofstream g(out/"translations.csv");g<<"axis,shift_m,pore_V_from_ice_m3,relative_change_vs_baseline,min_detJ_m3,nonpositive_detJ_samples,outer_tag_count,pore_tag_count\n";g<<setprecision(16);
  Mesh base=generate(4,5,8);double vb=VD-measure(base).volume;
  for(int i=0;i<3;++i)for(double h:{-.0001,.0001}){
    V c{0,0,.03};if(i==0)c.x+=h;if(i==1)c.y+=h;if(i==2)c.z+=h;
    Mesh a=generate(4,5,8,c);auto z=measure(a);
    const int angularN=6*4*4+2;
    for(int j=0;j<angularN;++j){
      V v=a.nodes[a.innerN*angularN+j];
      if(abs(norm(v-V{0,0,.03})-6*RBASE)>1e-12)throw runtime_error("B6 moved under pore-centre perturbation");
    }
    int exterior=0;for(int k=2;k<=7;++k)exterior+=z.counts[k];
    g<<(i==0?"X":(i==1?"Y":"Z"))<<","<<h<<","<<VD-z.volume<<","<<(VD-z.volume-vb)/vb<<","<<z.minDet<<","<<z.badDet<<","<<exterior<<","<<z.counts[8]<<"\n";
  }
}

#ifndef STAGE3D01_LIBRARY
int main(int argc,char**argv){
  try{
    fs::path out="results",meshdir="meshes";string filter="all";bool extras=true;
    for(int i=1;i<argc;++i){string a=argv[i];if(a=="--out"&&i+1<argc)out=argv[++i];else if(a=="--mesh-dir"&&i+1<argc)meshdir=argv[++i];else if(a=="--level"&&i+1<argc){filter=argv[++i];extras=false;}else if(a=="--no-perturb")extras=false;else throw runtime_error("unknown argument "+a);}
    fs::create_directories(out);fs::create_directories(meshdir);write_headers(out);
    ofstream rt(out/"roundtrip.csv");rt<<"level,ice_volume_relative_difference,pore_area_relative_difference,B6_volume_relative_difference,node_count_equal,tet_count_equal,face_count_equal\n";
    ofstream gc(out/"group_counts.csv");gc<<"level,ICE_VOLUME,TOP_ROBIN,BOTTOM_INSULATED,X_MINUS,X_PLUS,Y_MINUS,Y_PLUS,PORE_WALL\n";
    for(auto q:levels){if(filter!="all"&&filter!=q.id)continue;
      cout<<"Generating "<<q.id<<"..."<<flush;Mesh m=generate(q.angular,q.inner,q.outer);
      cout<<" measuring..."<<flush;Metrics z=measure(m);
      report(m,z,q.id,out);mesh_summary(m,z,meshdir/q.id);
      gc<<q.id<<","<<m.tets.size();for(int k=2;k<=8;++k)gc<<","<<z.counts[k];gc<<"\n";
      msh(m,meshdir/(q.id+".msh"));
      Mesh loaded=import_msh(meshdir/(q.id+".msh"),q.angular,q.inner,q.outer);
      Metrics zi=measure(loaded);
      double dv=abs(zi.volume/z.volume-1),da=abs(zi.poreArea/z.poreArea-1),db=abs(zi.v6/z.v6-1);
      bool same=(m.nodes.size()==loaded.nodes.size()&&m.tets.size()==loaded.tets.size()&&m.faces.size()==loaded.faces.size());
      rt<<setprecision(16)<<q.id<<","<<dv<<","<<da<<","<<db<<","<<(m.nodes.size()==loaded.nodes.size())<<","<<(m.tets.size()==loaded.tets.size())<<","<<(m.faces.size()==loaded.faces.size())<<"\n";
      if(!same||dv>1e-11||da>1e-11||db>1e-11)throw runtime_error("MSH roundtrip quadrature mismatch");
      vtu(m,meshdir/(q.id+"_volume.vtu"));vtu(m,meshdir/(q.id+"_boundary.vtu"),true);vtu(m,meshdir/(q.id+"_pore.vtu"),true,8);
      if(z.badDet||z.minNormalCos<=0)throw runtime_error("negative Tet10 Jacobian / incorrectly oriented pore normal");
    }
    if(extras&&filter=="all"){cout<<"Radius/translation perturbations..."<<flush;perturbation_tests(out);cout<<"done\n";}
    cout<<"Stage3D01 geometry generation/measurement finished\n";
  }catch(const exception&e){cerr<<"ERROR "<<e.what()<<"\n";return 2;}
}

#endif // STAGE3D01_LIBRARY
