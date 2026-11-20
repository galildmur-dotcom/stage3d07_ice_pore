// P10BY restricted executable: compiles the exact P10P reverse code with
// P10BX opt-in hook, but does NOT expose any physical --mesh/--out runner.
#define STAGE3D10W_ANALYTIC_SHAPE
#define STAGE3D10BX_THERMAL_QP_DIAGNOSTIC
#define STAGE3D10P_NO_MAIN
// Qualified relative-to-P10BX-root include: prevents the clean pinned/src
// P10P from silently shadowing the diagnostic review source on -I ordering.
#include "src/stage3d10p_partial_audit.cpp"

int main(){
  // Inherited P10I tiny adjoint tests: not a physical H0/H2 FEM run.
  return p10i::run_tests();
}
