// P10DK: exact P10W/P10DD production equations, with a source-only default.
// Physical execution is compiled OFF until a separately approved resource gate.
#define STAGE3D10DD_FULL4D 1
#define STAGE3D10DK_M1_FULL4D 1
#include "stage3d10w_analytic_adjoint.cpp"

int main(int argc, char** argv) {
 try {
  if (argc == 2 && std::string(argv[1]) == "--help") {
   std::cout << "P10DK_M1_FULL4D: exact M1, fresh forward + same-M1 "
     "analytic adjoint, signed mechanical+thermal (r,theta,phi,t), "
     "6x150s R/EDV_VAR xi=0 jpeak, 27/64 Tet10 QP. "
     "SOURCE_ONLY_NO_PHYSICAL_RUN_BY_DEFAULT.\n";
   return p10dk_inherited_main(argc, argv);
  }
  if (argc == 2 && std::string(argv[1]) == "--selftest") {
   const int status = p10dk_inherited_main(argc, argv);
   if (status == 0)
    std::cout << "P10DK_M1_SOURCE_SELFTEST_OK physical_FEM=0\n";
   return status;
  }
#ifndef STAGE3D10DK_PHYSICAL_ENABLED
  std::cerr << "P10DK_SOURCE_ONLY_STOP_NO_FEM: full physical M1 "
     "execution requires a separate scientific authorization, "
     "new Windows resource gate and PHYSICAL_ENABLED rebuild.\n";
  return 2;
#else
  // Even an explicitly enabled build requires a separately authorized
  // launcher to supply this opt-in. It must independently pin M1.msh SHA.
  bool opt_in = false;
  std::vector<char*> filtered{argv[0]};
  for (int i = 1; i < argc; ++i) {
   if (std::string(argv[i]) == "--p10dk-authorized-fresh-m1")
    opt_in = true;
   else
    filtered.push_back(argv[i]);
  }
  if (!opt_in) {
   std::cerr << "P10DK_STOP_NO_FEM: missing separate fresh-M1 opt-in\n";
   return 2;
  }
  for (std::size_t i = 1; i < filtered.size(); ++i)
   if (std::string(filtered[i]) == "--reuse-forward") {
    std::cerr << "P10DK_STOP_NO_FEM: H0/other forward replay "
       "is forbidden in the first M1 run\n";
    return 2;
   }
  return p10dk_inherited_main(int(filtered.size()), filtered.data());
#endif
 } catch (const std::exception& e) {
  std::cerr << "P10DK_SOURCE_STOP: " << e.what() << '\n';
  return 2;
 }
}
