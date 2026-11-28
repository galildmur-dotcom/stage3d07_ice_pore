// P10DL R1: separately approved one-shot physical M1, same production 4D code.
// Guard this binary too: the Python launcher pins mesh SHA and resources.
// Include the production code DIRECTLY: older nested sources redefine 'main'.
#define STAGE3D10DD_FULL4D 1
#define STAGE3D10DK_M1_FULL4D 1
#define STAGE3D10DL_BOUND_PHYSICAL 1
#include "stage3d10w_analytic_adjoint.cpp"

namespace {
bool valid_physical_arguments(int argc, char** argv) {
 // There is deliberately exactly ONE supported physical command shape.
 if (argc != 16) return false;
 const std::string args[] = {
  "--p10dk-authorized-fresh-m1", "--mesh", "", "--out", "", "--mode",
  "R", "--steps", "6", "--dt", "150", "--cutoff-mm", "5",
  "--threads", "4"};
 for (int i=1;i<argc;++i)
  if (i!=3 && i!=5 && std::string(argv[i])!=args[i-1]) return false;
 const fs::path mesh(argv[3]), out(argv[5]);
 return mesh.filename().string()=="P10DG_M1_CANDIDATE.msh" &&
        !out.empty() && out.filename().string().rfind("P10DL_M1_",0)==0;
}
}

int main(int argc, char** argv) {
 if (argc==2 && std::string(argv[1])=="--help") {
  std::cout<<"P10DL_ONE_SHOT_PHYSICAL_GUARD: use ONLY the verified "
   "01_RUN_ONE_P10DL_M1.cmd after source, mesh SHA, MinGW, one-shot "
   "marker and resource checks. Never use --preflight.\n";
  return p10dk_inherited_main(argc,argv);
 }
 if (argc==2 && std::string(argv[1])=="--selftest") {
  const int result=p10dk_inherited_main(argc,argv);
  if (result==0) {
   char* good[] = {(char*)"exe",(char*)"--p10dk-authorized-fresh-m1",
    (char*)"--mesh",(char*)"P10DG_M1_CANDIDATE.msh",(char*)"--out",
    (char*)"P10DL_M1_UNIT",(char*)"--mode",(char*)"R",
    (char*)"--steps",(char*)"6",(char*)"--dt",(char*)"150",
    (char*)"--cutoff-mm",(char*)"5",(char*)"--threads",(char*)"4"};
   const bool accepted=valid_physical_arguments(16,good);
   good[3]=(char*)"H0.msh";
   const bool rejects_h0=!valid_physical_arguments(16,good);
   good[3]=(char*)"P10DG_M1_CANDIDATE.msh";
   good[11]=(char*)"300";
   const bool rejects_wrong_dt=!valid_physical_arguments(16,good);
   if (!accepted || !rejects_h0 || !rejects_wrong_dt) return 3;
   std::cout<<"P10DL_EXE_PHYSICAL_GUARD_SELFTEST_OK exact_M1_name=PASS "
    "wrong_H0=REJECTED wrong_dt=REJECTED physical_FEM=0\n";
  }
  return result;
 }
 if (!valid_physical_arguments(argc,argv)) {
  std::cerr<<"P10DL_STOP_NO_FEM: unexpected physical arguments or "
   "M1 mesh name; H0 replay/preflight/other steps are prohibited\n";
  return 2;
 }
 const char* marker=std::getenv("P10DL_ONE_SHOT_MARKER");
 if (!marker || !fs::is_regular_file(fs::path(marker)) ||
     fs::path(marker).filename().string()!="P10DL_ONE_SHOT_CONSUMED.json") {
  std::cerr<<"P10DL_STOP_NO_FEM: no launcher-created one-shot marker\n";
  return 2;
 }
 // The private launcher-only opt-in must never reach the production parser.
 std::vector<char*> physical_args{argv[0]};
 for (int i=2;i<argc;++i) physical_args.push_back(argv[i]);
 return p10dk_inherited_main(int(physical_args.size()),physical_args.data());
}
