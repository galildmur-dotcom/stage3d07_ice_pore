// Stage 3D-07A: read-only audit of saved Stage3D06 full histories.
// NO FEM solve, delete, copy, modify, or automatic checkpoint resume.
#include "qt_runner_paths.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
struct Case {int phase;std::string mesh,model,mod;int dt,q;};
struct Sample {int t=0;double phi=0,omega=0,sigma=0;};
struct Data {
 std::vector<Sample> history;
 std::string status="MISSING", checkpoint="ABSENT";
 fs::path source;
 bool history_ok=false,checkpoint_ok=false,polar_ok=false;
 double j6=0,jomega=0,phi_end=0,sigma_end=0,top=0,bottom=0;
 int rows=0;
};
static std::string strip(std::string s){if(!s.empty()&&s.back()=='\r')s.pop_back();return s;}
static std::vector<std::string> fields(const std::string& s){std::vector<std::string> v;std::istringstream in(s);std::string p;while(std::getline(in,p,','))v.push_back(strip(p));return v;}
static bool numeric(const std::string&s,double&v){try{size_t k=0;v=std::stod(s,&k);return k==s.size()&&std::isfinite(v);}catch(...){return false;}}
static std::string escape_csv(const std::string&s){std::string o="\"";for(char c:s){if(c=='\"')o+="\"\"";else if(c=='\n'||c=='\r')o+=' ';else o+=c;}return o+'\"';}
static std::string label(const Case&c){return c.mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.q)+"/"+c.model+"_"+c.mod;}
static std::vector<Case> campaign(){return {
 {1,"H0","EDV","VAR",25,3},{1,"H1","EDV","VAR",25,3},
 {1,"H2","EDV","VAR",150,3},{1,"H2","EDV","VAR",75,3},
 {1,"H3","EDV","VAR",300,3},{1,"H3","EDV","VAR",150,3},
 {2,"H2","EDV","VAR",25,3},{2,"H3","EDV","VAR",75,3},
 {2,"H4","EDV","VAR",300,3},{2,"H4","EDV","VAR",150,3},
 {3,"H3","EDV","VAR",25,3},{3,"H4","EDV","VAR",75,3},
 {3,"H4","EDV","VAR",25,3},{3,"H3","EDV","VAR",75,4},
 {3,"H3","EDV","CONST",75,3},{3,"H4","EDV","CONST",75,3}
};}
static std::vector<Case> schedule(){auto c=campaign();std::set<std::string> seen;for(auto&k:c)seen.insert(label(k));
 for(auto m:{"H0","H1","H2"})for(int dt:{300,150,75}){Case x{0,m,"EDV","VAR",dt,3};if(seen.insert(label(x)).second)c.push_back(x);}
 return c;
}
static bool read_history(const fs::path& file, int dt,Data&out){
 std::ifstream f(file);std::string line;if(!std::getline(f,line))return false;
 bool invalid=false;
 while(std::getline(f,line)){
  line=strip(line);if(line.empty())continue;
  auto x=fields(line);double v[5]{};if(x.size()<9||!numeric(x[0],v[0])||!numeric(x[2],v[2])||!numeric(x[3],v[3])||!numeric(x[4],v[4])){invalid=true;break;}
  const int next=(int(out.history.size())+1)*dt;
  if(std::abs(v[0]-next)>1e-7||next>3600){invalid=true;break;}
  out.history.push_back({next,v[2],v[3],v[4]});
 }
 out.rows=(int)out.history.size();
 if(invalid){out.status="INVALID_HISTORY";return false;}
 if(out.rows==0)return false;
 if(out.rows!=3600/dt){out.status="PARTIAL";return false;}
 constexpr double psi0=7.5e-7;double old6=psi0,oldO=psi0;
 for(const auto&p:out.history){out.j6+=(old6+p.phi)*0.5*dt/3600.;out.jomega+=(oldO+p.omega)*0.5*dt/3600.;old6=p.phi;oldO=p.omega;}
 out.phi_end=out.history.back().phi;out.sigma_end=out.history.back().sigma;out.history_ok=true;return true;
}
static std::string checkpoint(const fs::path&file,const Case&c,bool&valid){
 std::ifstream f(file,std::ios::binary);if(!f)return "ABSENT";
 uint64_t magic=0,n=0,ng=0,sig=0;int32_t q=0,step=0;uint32_t mod=0,law=0;double time=0;
 auto rd=[&](auto &v){f.read(reinterpret_cast<char*>(&v),sizeof(v));};
 rd(magic);rd(n);rd(ng);rd(sig);rd(q);rd(step);rd(mod);rd(law);rd(time);
 if(!f)return "TRUNCATED";
 constexpr uint64_t correct=0x4943453344303602ull;
 if(magic!=correct)return "BAD_MAGIC";
 if(n==0||ng==0||sig==0||q!=c.q||step!=3600/c.dt||mod!=(c.mod=="VAR"?1u:0u)||law!=(c.model=="E"?0u:c.model=="ED"?1u:2u)||std::abs(time-3600)>1e-7)return "HEADER_MISMATCH";
 // Verify the serialized payload exists; State binary layout is intentionally not guessed.
 if(fs::file_size(file)<56+24*n)return "TRUNCATED_PAYLOAD";
 valid=true;return "HEADER_OK";
}
static void read_polar(const fs::path&file,Data&d){
 std::ifstream f(file);std::string s,last;if(!std::getline(f,s))return;
 while(std::getline(f,s))if(!s.empty())last=strip(s);
 auto x=fields(last);double t=0,a=0,b=0;if(x.size()>=5&&numeric(x[0],t)&&std::abs(t-3600)<1e-7&&numeric(x[1],a)&&numeric(x[2],b)){d.polar_ok=true;d.top=a;d.bottom=b;}
}
static Data inspect(const fs::path&base,const Case&c){
 Data d;const fs::path path=base/(c.mesh+"_dt"+std::to_string(c.dt)+"_q"+std::to_string(c.q))/"mechanics"/(c.model+"_"+c.mod);
 if(!fs::is_regular_file(path/"time_series.csv"))return d;
 d.source=path;
 if(!read_history(path/"time_series.csv",c.dt,d))return d;
 d.checkpoint=checkpoint(path/"restart.bin",c,d.checkpoint_ok);
 read_polar(path/"polar_caps_history.csv",d);
 d.status=d.checkpoint_ok?"COMPLETE":"HISTORY_ONLY";
 return d;
}
static int score(const Data&d){if(d.status=="COMPLETE")return 4;if(d.status=="HISTORY_ONLY")return 3;if(d.status=="PARTIAL")return 2;if(d.status=="INVALID_HISTORY")return 1;return 0;}
static void add_base(std::vector<fs::path>&roots,std::set<std::string>&seen,fs::path base){
 std::error_code ec;auto norm=fs::weakly_canonical(base,ec);if(ec||!fs::is_directory(norm))return;
 if(seen.insert(norm.string()).second)roots.push_back(norm);
}
static std::vector<fs::path> discover(const fs::path&root,bool siblings,const std::vector<fs::path>&extra){
 std::vector<fs::path>roots;std::set<std::string>seen;
 auto visit=[&](const fs::path&dir){
   add_base(roots,seen,dir/"LOCAL_RUNS");
   const auto optimized=dir/"LOCAL_RUNS_OPTIMIZED";
   add_base(roots,seen,optimized);
   std::error_code ec;
   if(fs::is_directory(optimized))for(auto it=fs::directory_iterator(optimized,fs::directory_options::skip_permission_denied,ec);!ec&&it!=fs::directory_iterator();it.increment(ec)){
     if(!it->is_directory(ec)||ec)continue;
     const auto name=it->path().filename().string();
     if(name.rfind("benchmark_",0)==0||name.rfind("campaign_",0)==0) add_base(roots,seen,it->path());
   }
 };
 visit(root);
 for(const auto&d:extra){visit(d);add_base(roots,seen,d);}
 if(siblings){std::error_code ec;for(auto it=fs::directory_iterator(root.parent_path(),fs::directory_options::skip_permission_denied,ec);!ec&&it!=fs::directory_iterator();it.increment(ec)){
   if(!it->is_directory(ec)||ec)continue;
   const std::string name=it->path().filename().string();
   if(name.rfind("Stage3D06",0)==0||name.rfind("Stage3D07",0)==0)visit(it->path());
 }}
 return roots;
}
static double pct(double a,double b){return std::abs(b)<1e-28?std::numeric_limits<double>::quiet_NaN():100.0*(a-b)/std::abs(b);}
static std::string number(double x){if(!std::isfinite(x))return "NA";std::ostringstream ss;ss<<std::setprecision(14)<<x;return ss.str();}
static void analyze(const fs::path&root,bool siblings,const std::vector<fs::path>&extra){
 const auto out=root/"LOCAL_RUNS"/"REFINEMENT_CAMPAIGN";fs::create_directories(out);
 const auto roots=discover(root,siblings,extra);const auto cases=schedule();
 std::map<std::string,Data> results;int ncomplete=0,nhistory=0,npartial=0,required=0;
 for(const auto&c:cases){Data best;for(const auto&base:roots){auto cur=inspect(base,c);if(score(cur)>score(best))best=std::move(cur);}
  if(c.phase>0)++required;
  if(best.status=="COMPLETE")++ncomplete;
  if(best.status=="HISTORY_ONLY")++nhistory;
  if(best.status=="PARTIAL")++npartial;
  results.emplace(label(c),std::move(best));
 }
 std::ofstream inv(out/"P07_INVENTORY.csv");
 inv<<"phase,mesh,law,modulus,dt_s,quadrature,expected_steps,verified_rows,status,checkpoint,polar,history_complete,j6,jOmega,Phi6_3600,QP_sigma1_max_3600_MPa,top_cap_MPa,bottom_cap_MPa,source\n";
 std::ofstream values(out/"P07_CONVERGENCE_DATA.csv");values<<"comparison,case_a,case_b,j6_diff_percent,Phi6_end_diff_percent,QP_sigma1_end_diff_percent,top_cap_diff_percent,bottom_cap_diff_percent,max_abs_Phi6_diff_first900,shared_first900_points\n";
 for(const auto&c:cases){const auto&d=results.at(label(c));
  inv<<c.phase<<','<<c.mesh<<','<<c.model<<','<<c.mod<<','<<c.dt<<','<<c.q<<','<<3600/c.dt<<','<<d.rows<<','<<d.status<<','<<d.checkpoint<<','<<(d.polar_ok?"YES":"NO")<<','<<(d.history_ok?"YES":"NO")<<',';
  if(d.history_ok)inv<<number(d.j6)<<','<<number(d.jomega)<<','<<number(d.phi_end)<<','<<number(d.sigma_end)<<','<<(d.polar_ok?number(d.top):"NA")<<','<<(d.polar_ok?number(d.bottom):"NA");
  else inv<<"NA,NA,NA,NA,NA,NA";
  inv<<','<<escape_csv(d.source.string())<<'\n';
 }
 int paired=0;
 for(size_t i=0;i<cases.size();++i)for(size_t j=i+1;j<cases.size();++j){
  const auto&a=cases[i],&b=cases[j];const auto&da=results.at(label(a)),&db=results.at(label(b));
  if(!da.history_ok||!db.history_ok)continue;
  std::string type;
  if(a.mesh==b.mesh&&a.model==b.model&&a.mod==b.mod&&a.q==b.q&&a.dt!=b.dt)type="temporal";
  else if(a.dt==b.dt&&a.model==b.model&&a.mod==b.mod&&a.q==b.q&&a.mesh!=b.mesh)type="spatial";
  else if(a.mesh==b.mesh&&a.dt==b.dt&&a.model==b.model&&a.mod==b.mod&&a.q!=b.q)type="quadrature";
  else if(a.mesh==b.mesh&&a.dt==b.dt&&a.model==b.model&&a.q==b.q&&a.mod!=b.mod)type="modulus";
  if(type.empty())continue;
  std::map<int,double> common;for(const auto&s:db.history)if(s.t<=900)common[s.t]=s.phi;
  double worst=0;int shared=0;for(const auto&s:da.history){if(s.t>900)break;auto it=common.find(s.t);if(it!=common.end()){worst=std::max(worst,std::abs(s.phi-it->second));++shared;}}
  values<<type<<','<<escape_csv(label(a))<<','<<escape_csv(label(b))<<','<<number(pct(da.j6,db.j6))<<','<<number(pct(da.phi_end,db.phi_end))<<','<<number(pct(da.sigma_end,db.sigma_end))<<','<<(da.polar_ok&&db.polar_ok?number(pct(da.top,db.top)):"NA")<<','<<(da.polar_ok&&db.polar_ok?number(pct(da.bottom,db.bottom)):"NA")<<','<<(shared?number(worst):"NA")<<','<<shared<<'\n';
  ++paired;
 }
 int nmain=0,nmain_hist=0;
 for(const auto&c:cases)if(c.phase>0){const auto&d=results.at(label(c));nmain+=(d.status=="COMPLETE");nmain_hist+=d.history_ok;}
 std::ofstream note(out/"P07_NEXT_ACTION_RU.md");note<<"# Stage 3D-07A — инвентаризация результатов для анализа сходимости\n\n"
 <<"Выполнена **только проверка файлов**, без FEM-расчётов, копирования и удаления данных.\n\n"
 <<"- Ожидаемых сценариев Stage 3D-06 из очередей 1–3: **"<<required<<"**.\n"
 <<"- Полные истории с совместимым заголовком checkpoint в этих очередях: **"<<nmain<<"**.\n"
 <<"- Полные временные истории (включая случаи без checkpoint): **"<<nmain_hist<<"**.\n"
 <<"- Всего найденных полных историй с checkpoint, включая H0–H2: **"<<ncomplete<<"**; без подтверждённого checkpoint: **"<<nhistory<<"**; частичных: **"<<npartial<<"**.\n"
 <<"- Количество допустимых пар для сравнения (НЕ доказательство сходимости): **"<<paired<<"**.\n"
 <<"- Проверено мест хранения: **"<<roots.size()<<"**.\n\n"
 <<"## Следующие действия\n\n";
 if(nmain_hist==0)note<<"В проверенных каталогах не найдена ни одна **полная** история из 16 сценариев. Это НЕ означает, что они никогда не рассчитывались: предыдущие расчёты могли остаться в другой папке. Найдите старый каталог `LOCAL_RUNS` (особенно H4 dt25) и запустите эту же цель с `--scan-root ПУТЬ_К_ПРОЕКТУ`. Пока **не перезапускайте** H4.\n\n";
 else note<<"Полные истории уже есть. Используйте `P07_CONVERGENCE_DATA.csv` для сопоставимых пар. Для случаев с `HISTORY_ONLY` не считать механический checkpoint подтверждённым; прежде чем продолжать такой расчёт, восстановить `restart.bin`. Не переносить автоматически checkpoint между разными каталогами и сетками.\n\n";
 note<<"## Сценарии Stage 3D-06 по очередям (доказательства — в CSV)\n\n| Очередь | Сценарий | Проверка | Статус |\n|---:|---|---|---|\n";
 for(const auto&c:cases)if(c.phase>0){const auto&d=results.at(label(c));note<<'|'<<c.phase<<'|'<<label(c)<<'|'<<d.rows<<'/'<<3600/c.dt<<'|'<<d.status<<"|\n";}
 note<<"\nОбозначения: `COMPLETE` — строгая последовательность времён до t=3600 и совместимый **заголовок** checkpoint; `HISTORY_ONLY` — история полна, но checkpoint отсутствует или не соответствует; `PARTIAL` — начало корректной истории; `MISSING` — нет time_series.csv; `INVALID_HISTORY` — нарушена последовательность или формат. Контроль заголовка **не доказывает** идентичности бинарных переменных и сигнатуры сетки; для этого нужен отдельный полный восстановительный тест.\n\n"
 <<"Для j6 применяется составная формула трапеций на [0,3600] с Phi6(0)=7.5e-7 из существующего вычислительного отчёта. Это анализ прямой задачи при ξ=0; результаты **не являются** производными формы, стохастической квадратурой GH3 или доказательством пространственной сходимости. Максимумы QP зависят от сетки и квадратуры.\n\n"
 <<"Отдельно: в исходной нумерации утверждённого плана `3D-07` посвящён функционалу; настоящий технический этап обозначен `3D-07A`, он не закрывает научные проверки G07/G12.\n";
 std::cout<<"P07 INVENTORY OK. inspected_bases="<<roots.size()<<" campaign_full_checkpoints="<<nmain<<"/"<<required<<" campaign_full_histories="<<nmain_hist<<" paired="<<paired<<"\n"
 <<(out/"P07_INVENTORY.csv")<<'\n'<<(out/"P07_CONVERGENCE_DATA.csv")<<'\n'<<(out/"P07_NEXT_ACTION_RU.md")<<'\n';
}
int main(int argc,char**argv){try{
 fs::path root=STAGE3D06_ROOT_DIR;bool siblings=true;std::vector<fs::path>extra;
 for(int i=1;i<argc;++i){std::string s=argv[i];auto arg=[&](){if(i+1>=argc)throw std::runtime_error("Missing value for "+s);return fs::path(argv[++i]);};
 if(s=="--root")root=arg();else if(s=="--scan-root")extra.push_back(arg());else if(s=="--no-siblings")siblings=false;
 else if(s=="--help"){std::cout<<"Usage: stage3d07_inventory [--root PROJECT_PATH] [--scan-root OLD_PROJECT_PATH] [--no-siblings]\nNo calculations; no copies; reads LOCAL_RUNS and LOCAL_RUNS_OPTIMIZED.\n";return 0;}
 else throw std::runtime_error("Unknown option "+s);}
 if(!fs::is_directory(root))throw std::runtime_error("Project root directory does not exist: "+root.string());
 analyze(root,siblings,extra);return 0;
 }catch(const std::exception&e){std::cerr<<"P07 INVENTORY FAILED: "<<e.what()<<'\n';return 2;}}
