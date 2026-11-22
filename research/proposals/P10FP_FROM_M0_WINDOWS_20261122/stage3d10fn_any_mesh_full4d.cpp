// P10FN: dynamic mesh/shape guard around the unchanged production full4D adjoint.
// The launcher independently checks SHA-pinned approval, resource cap and marker.
#define STAGE3D10DD_FULL4D 1
#define STAGE3D10DK_M1_FULL4D 1  // inherited entrypoint name; NOT a mesh restriction
#define STAGE3D10DL_BOUND_PHYSICAL 1
#include "stage3d10w_analytic_adjoint.cpp"

namespace {
bool supported(int argc,char** argv) {
  if(argc != 16) return false;
  const std::string args[] = {"--p10fn-authorized", "--mesh", "", "--out", "",
    "--mode", "", "--steps", "6", "--dt", "150", "--cutoff-mm", "5",
    "--threads", "4"};
  for(int i=1;i<argc;++i)
    if(i!=3 && i!=5 && i!=7 && std::string(argv[i])!=args[i-1])return false;
  const std::string mode=argv[7];
  if(mode!="R" && mode!="tz" && mode!="y20")return false;
  const fs::path mesh(argv[3]), out(argv[5]);
  const auto basename=mesh.filename().string();
  if(mesh.extension()!=".msh" || basename.size()<6)return false;
  if(basename[0]!='M' || basename.find_first_not_of("0123456789",1)!=basename.size()-4)
    return false;
  return !out.empty() && out.filename().string().rfind("P10FN_",0)==0;
}
}

int main(int argc,char** argv) {
  if(argc==2 && std::string(argv[1])=="--selftest") {
    const int code=p10dk_inherited_main(argc,argv);
    if(code!=0)return code;
    char* good[]={(char*)"exe",(char*)"--p10fn-authorized",(char*)"--mesh",
      (char*)"M42.msh",(char*)"--out",(char*)"P10FN_SELFTEST",
      (char*)"--mode",(char*)"R",(char*)"--steps",(char*)"6",
      (char*)"--dt",(char*)"150",(char*)"--cutoff-mm",(char*)"5",
      (char*)"--threads",(char*)"4"};
    if(!supported(16,good))return 3;
    good[3]=(char*)"H0.msh";
    if(supported(16,good))return 4;
    good[3]=(char*)"M42.msh";
    good[7]=(char*)"tz";
    if(!supported(16,good))return 5;
    good[7]=(char*)"y20";
    if(!supported(16,good))return 6;
    good[11]=(char*)"300";
    if(supported(16,good))return 7;
    std::cout<<"P10FN_ANY_MESH_GUARD_SELFTEST_OK no_FEM=1\n";
    return 0;
  }
  if(argc==2 && std::string(argv[1])=="--help") {
    std::cout<<"P10FN guarded R|tz|y20: run through verified no-input launcher.\n";
    return 0;
  }
  if(!supported(argc,argv)) {
    std::cerr<<"P10FN_STOP_NO_FEM: unsupported command shape/name/parameters\n";
    return 2;
  }
  const char* marker=std::getenv("P10FN_ONE_SHOT_MARKER");
  if(!marker || !fs::is_regular_file(fs::path(marker)) ||
      fs::path(marker).filename().string()!="P10FN_ONE_SHOT_CONSUMED.json") {
    std::cerr<<"P10FN_STOP_NO_FEM: missing one-shot run marker\n";
    return 2;
  }
  std::vector<char*> filtered{argv[0]};
  for(int i=2;i<argc;++i)filtered.push_back(argv[i]);
  return p10dk_inherited_main(int(filtered.size()),filtered.data());
}
