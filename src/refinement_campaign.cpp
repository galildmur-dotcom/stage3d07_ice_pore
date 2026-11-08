// Native cross-platform Qt Creator launcher for systematic H0..H4 temporal/spatial study.
// No Python, PowerShell or external tools are required after CMake compilation.
#include "qt_runner_paths.hpp"
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <cmath>
#ifdef _WIN32
# define NOMINMAX
# include <windows.h>
#else
# include <sys/types.h>
# include <sys/wait.h>
# include <unistd.h>
# include <cerrno>
# include <cstring>
#endif
namespace fs=std::filesystem;
struct Case {int stage;std::string mesh,law,mod;int dt,quad;};
static std::vector<Case> jobs(){
 // Phases are ordered by cost and scientific priority. Existing completed time histories are re-used.
 return {
 {1,"H0","EDV","VAR",25,3}, {1,"H1","EDV","VAR",25,3},
 {1,"H2","EDV","VAR",150,3}, {1,"H2","EDV","VAR",75,3},
 {1,"H3","EDV","VAR",300,3}, {1,"H3","EDV","VAR",150,3},
 {2,"H2","EDV","VAR",25,3}, {2,"H3","EDV","VAR",75,3},
 {2,"H4","EDV","VAR",300,3}, {2,"H4","EDV","VAR",150,3},
 {3,"H3","EDV","VAR",25,3}, {3,"H4","EDV","VAR",75,3},
 {3,"H4","EDV","VAR",25,3},
 {3,"H3","EDV","VAR",75,4}, // quadrature sensitivity of local peaks
 {3,"H3","EDV","CONST",75,3}, // controlled E_CONST vs E_VAR
 {3,"H4","EDV","CONST",75,3}
 };
}
#ifdef _WIN32
std::wstring quote(const std::wstring&s){std::wstring out=L"\"";size_t bs=0;for(wchar_t c:s){if(c==L'\\'){++bs;continue;}if(c==L'"'){out.append(2*bs+1,L'\\');out+=L'"';bs=0;continue;}out.append(bs,L'\\');bs=0;out+=c;}out.append(2*bs,L'\\');return out+L'"';}
int spawn(const fs::path&ex,const std::vector<std::string>&args){
 std::wstring cmd=quote(ex.wstring());for(const auto&arg:args){const auto w=fs::path(arg).wstring();cmd+=L" "+quote(w);}
 std::vector<wchar_t>line(cmd.begin(),cmd.end());line.push_back(0);
 STARTUPINFOW si{};si.cb=sizeof(si);PROCESS_INFORMATION pi{};
 if(!CreateProcessW(ex.c_str(),line.data(),nullptr,nullptr,TRUE,0,nullptr,nullptr,&si,&pi))throw std::runtime_error("CreateProcessW failed: "+std::to_string(GetLastError()));
 CloseHandle(pi.hThread);auto code=WaitForSingleObject(pi.hProcess,INFINITE);DWORD result=999;auto ok=GetExitCodeProcess(pi.hProcess,&result);CloseHandle(pi.hProcess);if(code!=WAIT_OBJECT_0||!ok)throw std::runtime_error("Failed waiting for child process");return int(result);
}
#else
int spawn(const fs::path&ex,const std::vector<std::string>&args){pid_t pid=fork();if(pid<0)throw std::runtime_error("fork failed");if(!pid){
 std::vector<std::string> v;v.push_back(ex.string());for(auto&s:args)v.push_back(s);std::vector<char*>a;for(auto&item:v)a.push_back(item.data());a.push_back(nullptr);execv(ex.c_str(),a.data());_exit(127);}
 int status=0;while(waitpid(pid,&status,0)<0){if(errno==EINTR)continue;throw std::runtime_error("waitpid failed");}return WIFEXITED(status)?WEXITSTATUS(status):128;
}
#endif
static bool complete(const fs::path&dest,int dt){
 const auto f=dest/"time_series.csv";if(!fs::is_regular_file(f))return false;
 std::ifstream in(f);std::string line;std::getline(in,line);
 int unique=0;double last=-1;while(std::getline(in,line)){
  if(line.empty())continue;auto end=line.find(',');if(end==std::string::npos)return false;
  double t=std::stod(line.substr(0,end));if(t>last+1e-7){last=t;++unique;}
 }
 return std::abs(last-3600.)<1e-7 && unique==3600/dt && fs::is_regular_file(dest/"restart.bin");
}
static std::string tag(const Case&c){return c.mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.quad)+"/"+c.law+"_"+c.mod;}
int main(int argc,char**argv){
 try {
 int phase=0;
#ifdef STAGE3D06_CAMPAIGN_PHASE
 phase=STAGE3D06_CAMPAIGN_PHASE;
#endif
 bool plan=false;
#ifdef STAGE3D06_CAMPAIGN_PLAN
 plan=true;
#endif
 for(int i=1;i<argc;++i){std::string arg=argv[i];if(arg=="--plan"||arg=="--dry-run")plan=true;
 else if(arg=="--phase"&&i+1<argc){phase=std::stoi(argv[++i]);}else throw std::runtime_error("Usage: [--plan] [--phase 1|2|3]");}
 if(phase<0||phase>3)throw std::runtime_error("Phase 0(all), 1, 2 or 3 expected");
 const auto root=fs::path(STAGE3D06_ROOT_DIR), out=root/"LOCAL_RUNS";
 const auto exe=fs::absolute(fs::path(argv[0]));
#ifdef _WIN32
 const auto run=exe.parent_path()/"stage3d06_qt_run.exe";
#else
 const auto run=exe.parent_path()/"stage3d06_qt_run";
#endif
 if(!fs::is_regular_file(run))throw std::runtime_error("Missing Qt native launcher "+run.string());
 fs::create_directories(out/"REFINEMENT_CAMPAIGN");
 std::ofstream manifest(out/"REFINEMENT_CAMPAIGN"/"CAMPAIGN_PLAN.csv");
 manifest<<"phase,mesh,law,modulus,dt_s,quad,t_end_s,n_timestep,output_folder\n";
 size_t n=0;for(const auto&c:jobs()){if(phase&&c.stage!=phase)continue;++n;
 const auto mesh=root/"meshes"/(c.mesh+".msh");if(!fs::is_regular_file(mesh))throw std::runtime_error("Mesh missing: "+mesh.string());
 manifest<<c.stage<<','<<c.mesh<<','<<c.law<<','<<c.mod<<','<<c.dt<<','<<c.quad<<",3600,"<<3600/c.dt<<','<<tag(c)<<'\n';}
 manifest.close();
 std::cout<<"\nStage 3D-06 REFINEMENT CAMPAIGN (CPU, no shell)\n"
          <<"Root: "<<root<<"\nCases: "<<n<<" Phase: "<<(phase?std::to_string(phase):"ALL")<<"\n"
          <<"Manifest: "<<(out/"REFINEMENT_CAMPAIGN"/"CAMPAIGN_PLAN.csv")<<"\n"
          <<"Results are checkpointed per timestep. Existing completed runs will be skipped.\n"<<std::flush;
 if(plan){std::cout<<"PLAN CHECK PASS: All meshes and program dependencies exist; no solves performed.\n";return 0;}
 const auto history=out/"REFINEMENT_CAMPAIGN"/"CAMPAIGN_STATUS.csv";
 if(!fs::exists(history)){std::ofstream f(history);f<<"phase,mesh,law,modulus,dt_s,quad,status,elapsed_wall_s\n";}
 size_t done=0;for(const auto&c:jobs()){
 if(phase&&c.stage!=phase)continue;
 const auto dest=out/(c.mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.quad))/"mechanics"/(c.law+"_"+c.mod);
 bool isdone=complete(dest,c.dt);auto start=std::chrono::steady_clock::now();int err=0;
 std::cout<<"\n["<<(++done)<<"/"<<n<<"] "<<tag(c)<<" ";
 if(isdone)std::cout<<"ALREADY FINISHED; SKIP\n"<<std::flush;
 else {
  std::cout<<"START\n"<<std::flush;
  err=spawn(run,{"--mesh",c.mesh,"--law",c.law,"--modulus",c.mod,"--dt",std::to_string(c.dt),"--tend","3600","--quad",std::to_string(c.quad)});
  if(!err && !complete(dest,c.dt))err=3;
 }
 auto seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 std::ofstream f(history,std::ios::app);f<<c.stage<<','<<c.mesh<<','<<c.law<<','<<c.mod<<','<<c.dt<<','<<c.quad<<','<<(err?"FAILED":(isdone?"SKIPPED":"PASS"))<<','<<seconds<<'\n';f.close();
 if(err){std::cerr<<"STOPPED: "<<tag(c)<<" exit "<<err<<"; successful checkpoints retained. Restart same Qt Creator target to resume.\n";return err;}
 }
 std::cout<<"\nCAMPAIGN PASS: "<<n<<" scenarios complete or verified. See LOCAL_RUNS and convergence report target.\n";return 0;
 }catch(const std::exception&e){std::cerr<<"CAMPAIGN ERROR: "<<e.what()<<"\n";return 2;}
}
