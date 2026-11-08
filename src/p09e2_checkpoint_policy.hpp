#pragma once
// Stage 3D-09E2: completed-step, elapsed-WALL-time checkpoints and safe CSV rollback.
// No FEM/model dependencies; testable in isolation.
#include <cmath>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace ice3d::p09e2 {
namespace fs = std::filesystem;
inline bool should_checkpoint(double hours, double elapsed_seconds, bool final_step) {
 if(!std::isfinite(hours) || hours<0 || hours>240)
  throw std::runtime_error("P09E2: checkpoint hours must be 0..240");
 return final_step || hours==0 || elapsed_seconds>=hours*3600.0;
}
inline std::string first_column(const std::string&line){
 auto at=line.find(',');return line.substr(0,at);
}
inline int first_int(const std::string&line){
 const auto s=first_column(line);size_t n=0;int v=0;
 try{v=std::stoi(s,&n);}catch(...){throw std::runtime_error("P09E2: malformed CSV time: "+s);}
 if(n!=s.size())throw std::runtime_error("P09E2: malformed CSV time: "+s);
 return v;
}
inline void rewrite_csv(const fs::path&path,const std::vector<std::string>&lines) {
 const fs::path tmp=path.string()+".rollback";
 {
  std::ofstream out(tmp,std::ios::binary|std::ios::trunc);
  if(!out)throw std::runtime_error("P09E2 cannot open rollback: "+tmp.string());
  for(const auto&line:lines)out<<line<<'\n';
  out.close();if(!out)throw std::runtime_error("P09E2 cannot write rollback: "+tmp.string());
 }
 // The old file is not changed until its full replacement is ready.
 // This is not a recovery checkpoint; a failure leaves the original and .rollback.
 if(fs::exists(path))fs::remove(path);
 fs::rename(tmp,path);
}
inline void trim_step_history(const fs::path&path, const std::vector<int>&times, int complete) {
 if(complete<1 || complete>int(times.size()))throw std::runtime_error("P09E2: invalid completed steps");
 std::ifstream in(path,std::ios::binary);
 if(!in)throw std::runtime_error("P09E2: missing history for resume: "+path.string());
 std::string line;
 if(!std::getline(in,line)||line.rfind("time_s,",0)!=0)
  throw std::runtime_error("P09E2: invalid history header: "+path.string());
 std::vector<std::string> rows{line};int good=0;bool extra=false;
 while(std::getline(in,line)){
  if(line.empty())continue;
  if(good==complete){extra=true;continue;}
  const int time=first_int(line);
  if(time!=times[good])throw std::runtime_error("P09E2: history/checkpoint step mismatch: "+path.string());
  rows.push_back(line);++good;
 }
 if(good!=complete)throw std::runtime_error("P09E2: history shorter than checkpoint: "+path.string());
 // Windows cannot replace a file while this input stream is still open.
 in.close();
 if(extra)rewrite_csv(path,rows);
}
inline void trim_campaign(const fs::path&path, const std::string&law,
                          const std::string&mod, int saved_time) {
 if(!fs::exists(path))return;
 std::ifstream in(path,std::ios::binary);if(!in)throw std::runtime_error("P09E2: cannot read campaign");
 std::string line;std::vector<std::string> rows;bool extra=false;
 if(!std::getline(in,line)||line.rfind("law,modulus,time_s,",0)!=0)
  throw std::runtime_error("P09E2: bad campaign CSV header");
 rows.push_back(line);
 while(std::getline(in,line)){
  if(line.empty())continue;
  auto a=line.find(','),b=(a==std::string::npos?std::string::npos:line.find(',',a+1));
  if(b==std::string::npos)throw std::runtime_error("P09E2: bad campaign row");
  const auto oldLaw=line.substr(0,a),oldMod=line.substr(a+1,b-a-1);
  if(oldLaw==law&&oldMod==mod) {
    int time=first_int(line.substr(b+1));
    if(time>saved_time){extra=true;continue;}
  }
  rows.push_back(line);
 }
 // Windows cannot replace a file while this input stream is still open.
 in.close();
 if(extra)rewrite_csv(path,rows);
}
} // namespace ice3d::p09e2
