#pragma once
// P09D3: exact finite-difference split of paired quadrature sums.
// No analytic shape gradient is claimed. All cases use the same topological element/QP order.
#include "stage3d09b_functionals.hpp"
#include "p09d2_local.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace ice3d::p09d3 {
namespace fs=std::filesystem;
struct Point {double dv=0, r=0, p4=0, p8=0, p12=0;};
inline Point point(double radius_mm,double dv,const std::array<double,3>&sigma,double ref){
 if(!(std::isfinite(radius_mm)&&radius_mm>0&&std::isfinite(dv)&&dv>0))throw std::runtime_error("P09D3 invalid QP weight/radius");
 return {dv,radius_mm,p09b::peak_power(sigma,ref,4),p09b::peak_power(sigma,ref,8),p09b::peak_power(sigma,ref,12)};
}
inline double rel_error(double a,double b){return std::abs(a-b)/std::max({std::abs(a),std::abs(b),1e-30});}
constexpr char magic[8]={'P','0','9','D','3','Q','0','1'};
struct Header {std::uint64_t nodes=0, elems=0, nq=0, connectivity=0, active=0;};
inline std::uint64_t mix(std::uint64_t hash,std::uint64_t v){hash^=v;return hash*1099511628211ull;}
template<class TetContainer>std::uint64_t topology_hash(std::size_t nodes,const TetContainer&tets){
 auto h=mix(mix(14695981039346656037ull,nodes),tets.size());
 for(const auto&t:tets)for(const auto v:t)h=mix(h,std::uint64_t(v));
 return h;
}
template<class T>void write(std::ofstream&out,const T&v){out.write(reinterpret_cast<const char*>(&v),sizeof(T));}
template<class T>void read(std::ifstream&in,T&v){in.read(reinterpret_cast<char*>(&v),sizeof(T));if(!in)throw std::runtime_error("P09D3 truncated/corrupt binary checkpoint diagnostic");}
inline void put_header(std::ofstream&out,const Header&h){out.write(magic,8);write(out,h.nodes);write(out,h.elems);write(out,h.nq);write(out,h.connectivity);write(out,h.active);}
inline Header get_header(std::ifstream&in){char m[8]{};in.read(m,8);if(!in||!std::equal(m,m+8,magic))throw std::runtime_error("P09D3 invalid diagnostic file magic");
 Header h;read(in,h.nodes);read(in,h.elems);read(in,h.nq);read(in,h.connectivity);read(in,h.active);
 if(!h.nodes||!h.elems||!h.nq||h.nq>64||!h.active||h.active>h.elems)throw std::runtime_error("P09D3 invalid diagnostic file dimensions");return h;}
inline void write_point(std::ofstream&out,const Point&p){write(out,p.dv);write(out,p.r);write(out,p.p4);write(out,p.p8);write(out,p.p12);}
inline Point read_point(std::ifstream&in){Point p;read(in,p.dv);read(in,p.r);read(in,p.p4);read(in,p.p8);read(in,p.p12);
 if(!(p.dv>0)||!std::isfinite(p.p8)||!std::isfinite(p.r)||!std::isfinite(p.p4)||!std::isfinite(p.p12))throw std::runtime_error("P09D3 invalid QP data");return p;}
struct Stats {double vol=0,p4=0,p8=0,p12=0;std::uint64_t active=0,nqp=0;};
template<class TetContainer,class NodeContainer>Stats write_points(const fs::path&dest,std::size_t nodecount,const TetContainer&tets,
 const std::vector<std::uint8_t>&b6,const NodeContainer&nodes,std::size_t nq,const std::vector<Point>&points){
 if(points.size()!=tets.size()*nq||(!b6.empty()&&b6.size()!=tets.size()))throw std::runtime_error("P09D3 data shape mismatch");
 Header h;h.nodes=nodecount;h.elems=tets.size();h.nq=nq;h.connectivity=topology_hash(nodecount,tets);
 for(std::size_t e=0;e<tets.size();++e){bool in6=false;
  if(b6.empty()){double x=0,y=0,z=0;for(int j=0;j<4;++j){const auto&v=nodes[tets[e][j]];x+=v.x*.25;y+=v.y*.25;z+=v.z*.25;}
   in6=std::sqrt(x*x+y*y+(z-.03)*(z-.03))<.006;
  }else in6=bool(b6[e]);
  if(in6)++h.active;
 }
 if(!h.active)throw std::runtime_error("P09D3 B6 is empty");
 std::ofstream out(dest,std::ios::binary|std::ios::trunc);if(!out)throw std::runtime_error("P09D3 cannot open "+dest.string());put_header(out,h);
 Stats s;s.active=h.active;
 for(std::size_t e=0;e<tets.size();++e){bool in6=false;
  if(b6.empty()){double x=0,y=0,z=0;for(int j=0;j<4;++j){const auto&v=nodes[tets[e][j]];x+=v.x*.25;y+=v.y*.25;z+=v.z*.25;}
   in6=std::sqrt(x*x+y*y+(z-.03)*(z-.03))<.006;
  }else in6=bool(b6[e]);
  const std::uint8_t active=std::uint8_t(in6);write(out,active);
  if(!in6)continue;
  for(std::size_t q=0;q<nq;++q){const auto&p=points[e*nq+q];if(!(p.dv>0&&std::isfinite(p.dv)&&std::isfinite(p.p8)))throw std::runtime_error("P09D3 missing active QP");
   write_point(out,p);s.vol+=p.dv;s.p4+=p.dv*p.p4;s.p8+=p.dv*p.p8;s.p12+=p.dv*p.p12;++s.nqp;
  }
 }
 out.close();if(!out)throw std::runtime_error("P09D3 failed writing "+dest.string());return s;
}
struct Split {double field=0,geom=0,full=0,plus=0,minus=0;};
inline Split split(double fp,double fm,double wp,double wm,double denom){
 const double field=((fp-fm)/denom)*(.5*(wp+wm));
 const double geom=((wp-wm)/denom)*(.5*(fp+fm));
 return {field,geom,field+geom,fp*wp,fm*wm};
}
struct Moment {Split p4,p8,p12;double volume_plus=0,volume_minus=0;std::uint64_t nqp=0;};
inline void add(Moment&m,const Point&p,const Point&n,double denom){
 auto grow=[](Split&v,const Split&d){v.field+=d.field;v.geom+=d.geom;v.full+=d.full;v.plus+=d.plus;v.minus+=d.minus;};
 grow(m.p4,split(p.p4,n.p4,p.dv,n.dv,denom));grow(m.p8,split(p.p8,n.p8,p.dv,n.dv,denom));grow(m.p12,split(p.p12,n.p12,p.dv,n.dv,denom));
 m.volume_plus+=p.dv;m.volume_minus+=n.dv;++m.nqp;
}
inline void accumulate(Moment&a,const Moment&b){
 for(int k=0;k<3;++k){Split *d=k==0?&a.p4:k==1?&a.p8:&a.p12;const Split&s=k==0?b.p4:k==1?b.p8:b.p12;
  d->field+=s.field;d->geom+=s.geom;d->full+=s.full;d->plus+=s.plus;d->minus+=s.minus;}
 a.volume_plus+=b.volume_plus;a.volume_minus+=b.volume_minus;a.nqp+=b.nqp;
}
struct Paired {Header h;std::array<Moment,p09d2::nbin> bins{};Moment all{};};
inline Paired pair_files(const fs::path&plus,const fs::path&minus,double delta){
 if(!(delta>0))throw std::runtime_error("P09D3 invalid delta");
 std::ifstream p(plus,std::ios::binary),m(minus,std::ios::binary);
 if(!p||!m)throw std::runtime_error("P09D3 missing diagnostic QP binaries: "+plus.string()+" or "+minus.string());
 auto a=get_header(p),b=get_header(m);
 if(a.nodes!=b.nodes||a.elems!=b.elems||a.nq!=b.nq||a.connectivity!=b.connectivity||a.active!=b.active)
  throw std::runtime_error("P09D3 paired mesh connectivity/dimensions disagree; QP pairing is not safe");
 Paired out;out.h=a;const double denom=2*delta;
 std::uint64_t n=0,active=0;
 for(std::uint64_t e=0;e<a.elems;++e){std::uint8_t flagp=0,flagm=0;read(p,flagp);read(m,flagm);
  if(flagp!=flagm||flagp>1)throw std::runtime_error("P09D3 plus/minus B6 element masks disagree");
  if(!flagp)continue;++active;
  for(std::uint64_t q=0;q<a.nq;++q){Point u=read_point(p),v=read_point(m);
   const double r=.5*(u.r+v.r);const auto bin=p09d2::hard_bin(r);
   add(out.bins[bin],u,v,denom);add(out.all,u,v,denom);++n;
  }
 }
 if(n!=a.active*a.nq||active!=a.active)throw std::runtime_error("P09D3 QP count mismatch");
 if(p.peek()!=std::char_traits<char>::eof()||m.peek()!=std::char_traits<char>::eof())throw std::runtime_error("P09D3 trailing QP records");
 for(const auto&sp:{out.all.p4,out.all.p8,out.all.p12}){
  const double direct=(sp.plus-sp.minus)/denom;
  if(rel_error(direct,sp.full)>2e-8)throw std::runtime_error("P09D3 decomposition failed: field+geometry != direct FD");
 }
 return out;
}
inline void selftest(){
 Point p{2.,1.01,2.,3.,5.},m{4.,1.02,7.,11.,13.};const double d=.000005;
 Moment x;add(x,p,m,2*d);
 for(const auto&v:{x.p4,x.p8,x.p12})if(rel_error(v.full,(v.plus-v.minus)/(2*d))>1e-14)throw std::runtime_error("P09D3 identity failed");
 if(rel_error(x.p8.field,(-8*3)/(2*d))>1e-13||rel_error(x.p8.geom,((-2)*7)/(2*d))>1e-13)throw std::runtime_error("P09D3 split terms incorrect");
 if(p09d2::hard_bin((p.r+m.r)*.5)!=0)throw std::runtime_error("P09D3 binning failed");
}
}
