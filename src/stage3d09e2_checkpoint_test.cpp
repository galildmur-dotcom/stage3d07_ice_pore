#include "p09e2_checkpoint_policy.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
namespace fs=std::filesystem;
int main(){try{
 using namespace ice3d::p09e2;
 if(should_checkpoint(6,21599,false)||!should_checkpoint(6,21600,false)||
   !should_checkpoint(6,0,true)||!should_checkpoint(0,0,false))throw std::runtime_error("policy mismatch");
 fs::path root=fs::temp_directory_path()/"p09e2_checkpoint_unit_test";
 fs::create_directories(root);
 auto make=[&](const std::string&name){std::ofstream f(root/name);f<<"time_s,dt_s,value\n";for(int i=1;i<=6;++i)f<<i*300<<",300,"<<i<<"\n";};
 for(auto n:{"time_series.csv","P09B_functionals_history.csv","polar_caps_history.csv","max_location.csv"})make(n);
 std::vector<int> times{300,600,900,1200,1500,1800};
 for(auto n:{"time_series.csv","P09B_functionals_history.csv","polar_caps_history.csv","max_location.csv"}){
  trim_step_history(root/n,times,4);trim_step_history(root/n,times,4);
  std::ifstream f(root/n);std::string line;int cnt=0;while(std::getline(f,line))++cnt;
  if(cnt!=5)throw std::runtime_error("rollback lost rows");
 }
 {std::ofstream f(root/"G06_campaign.csv");f<<"law,modulus,time_s,x\n";
  f<<"E,CONST,600,1\n";
  for(int i=1;i<=6;++i)f<<"EDV,VAR,"<<i*300<<",1\n";}
 trim_campaign(root/"G06_campaign.csv","EDV","VAR",1200);
 {std::ifstream f(root/"G06_campaign.csv");std::string line;int n=0;while(std::getline(f,line))++n;
  if(n!=6)throw std::runtime_error("campaign rollback lost other models");}
 fs::remove_all(root);
 std::cout<<"P09E2_CHECKPOINT_TEST_OK policy=6h rollback=4/6 final=always\n";
 return 0;
 }catch(const std::exception&e){std::cerr<<"P09E2 TEST FAILED: "<<e.what()<<"\n";return 2;}}
