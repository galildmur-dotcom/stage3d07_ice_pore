// Stage3D06 checkpoint validator, streaming, C++20, no Qt or Python dependency.
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace fs=std::filesystem;
using u64=std::uint64_t;
struct Stats{
 u64 n=0,badA=0,badB=0;
 long double maxA=0,maxDiff=0,sumsqA=0,sumsqDiff=0;
 void add(double a,double b){
  ++n;
  if(!std::isfinite(a)){++badA;}
  if(!std::isfinite(b)){++badB;}
  if(!std::isfinite(a)||!std::isfinite(b))return;
  const long double x=a,y=b,d=x-y;
  maxA=std::max(maxA,std::abs(x));
  maxDiff=std::max(maxDiff,std::abs(d));
  sumsqA+=x*x;sumsqDiff+=d*d;
 }
 long double delta()const{return maxA>0?maxDiff/maxA:(maxDiff==0?0:std::numeric_limits<long double>::infinity());}
 long double rms()const{return n?std::sqrt(sumsqDiff/n):0;}
 long double relative_rms()const{return sumsqA>0?std::sqrt(sumsqDiff/sumsqA):(sumsqDiff==0?0:std::numeric_limits<long double>::infinity());}
 bool pass(long double tol)const{return n && !badA && !badB && delta()<=tol;}
};
using Header=std::array<unsigned char,56>;
u64 read64(const Header&h,unsigned offset){u64 v=0;for(unsigned i=0;i<8;++i)v|=u64(h[offset+i])<<(8*i);return v;}
void read(std::ifstream&f,void*dst,size_t size){f.read(static_cast<char*>(dst),std::streamsize(size));if(!f)throw std::runtime_error("truncated checkpoint");}
void row(std::ofstream&f,const std::string&name,const Stats&s,long double tol){
 f<<name<<','<<s.n<<','<<s.maxA<<','<<s.maxDiff<<','<<s.delta()<<','<<s.rms()<<','<<s.relative_rms()<<','<<s.badA<<','<<s.badB<<','<<(s.pass(tol)?"PASS":"FAIL")<<'\n';
}
int main(int argc,char**argv){try{
 static_assert(sizeof(double)==8 && std::numeric_limits<double>::is_iec559);
 if(std::endian::native!=std::endian::little)throw std::runtime_error("little endian required");
 fs::path baseline,optimized,output="checkpoint_compare.csv";long double tol=1e-6L;
 for(int i=1;i<argc;++i){std::string flag=argv[i];
  if(flag=="--help"){
   std::cout<<"--baseline FILE --optimized FILE [--output CSV] [--tol 1e-6]\n";return 0;}
  if(i+1>=argc)throw std::runtime_error("missing argument value: "+flag);
  std::string val=argv[++i];
  if(flag=="--baseline")baseline=val;
  else if(flag=="--optimized")optimized=val;
  else if(flag=="--output")output=val;
  else if(flag=="--tol")tol=std::stold(val);
  else throw std::runtime_error("unknown argument: "+flag);
 }
 if(baseline.empty()||optimized.empty()||!std::isfinite(tol)||tol<0)throw std::runtime_error("invalid arguments");
 std::ifstream a(baseline,std::ios::binary),b(optimized,std::ios::binary);
 if(!a||!b)throw std::runtime_error("cannot open input checkpoint");
 Header ha{},hb{};read(a,ha.data(),ha.size());read(b,hb.data(),hb.size());
 if(!output.parent_path().empty())fs::create_directories(output.parent_path());
 std::ofstream csv(output);if(!csv)throw std::runtime_error("cannot create CSV");
 csv<<std::setprecision(18)<<"field,components,max_abs_baseline,max_abs_diff,normalized_max_diff,rms_abs_diff,normalized_rms_diff,nonfinite_baseline,nonfinite_optimized,status\n";
 bool headers_equal=ha==hb;
 csv<<"header,0,0,0,0,0,0,0,0,"<<(headers_equal?"PASS":"FAIL")<<'\n';
 if(!headers_equal){std::cout<<"FAIL: header mismatch\n";return 1;}
 const u64 magic=read64(ha,0),n=read64(ha,8),nq=read64(ha,16);
 const double time=std::bit_cast<double>(read64(ha,48));
 const u64 max=std::numeric_limits<u64>::max();
 if(magic!=0x4943453344303602ULL||!n||!nq||!std::isfinite(time)||n>(max-56)/24||nq>(max-56-24*n)/96)
  throw std::runtime_error("invalid checkpoint header/dimensions");
 const u64 expected=56+24*n+96*nq;
 const bool size_pass=fs::file_size(baseline)==expected && fs::file_size(optimized)==expected;
 csv<<"file_size,0,0,0,0,0,0,0,0,"<<(size_pass?"PASS":"FAIL")<<'\n';
 if(!size_pass){std::cout<<"FAIL: size mismatch (expected "<<expected<<")\n";return 1;}
 Stats su,sd,sv;
 std::array<double,4096>ua{},ub{};
 for(u64 pos=0;pos<3*n;){size_t count=size_t(std::min<u64>(ua.size(),3*n-pos));
  read(a,ua.data(),count*sizeof(double));read(b,ub.data(),count*sizeof(double));
  for(size_t i=0;i<count;++i)su.add(ua[i],ub[i]);
  pos+=count;
 }
 std::array<double,12*256>qa{},qb{};
 for(u64 pos=0;pos<nq;){size_t count=size_t(std::min<u64>(256,nq-pos));
  const size_t bytes=count*12*sizeof(double);
  read(a,qa.data(),bytes);read(b,qb.data(),bytes);
  for(size_t k=0;k<count;++k)for(size_t j=0;j<6;++j){
   sd.add(qa[12*k+j],qb[12*k+j]);sv.add(qa[12*k+6+j],qb[12*k+6+j]);
  }
  pos+=count;
 }
 row(csv,"u",su,tol);row(csv,"ed",sd,tol);row(csv,"ev",sv,tol);
 const bool pass=su.pass(tol)&&sd.pass(tol)&&sv.pass(tol);
 csv<<"overall,0,0,0,0,0,0,0,0,"<<(pass?"PASS":"FAIL")<<'\n';
 std::cout<<std::setprecision(15)<<"Nodes="<<n<<" QP="<<nq<<" time="<<time
          <<" delta_u="<<su.delta()<<" delta_ed="<<sd.delta()<<" delta_ev="<<sv.delta()
          <<" RESULT: "<<(pass?"PASS":"FAIL")<<"\n";
 return pass?0:1;
 }catch(const std::exception&e){std::cerr<<"COMPARE FAILED: "<<e.what()<<'\n';return 2;}
}
