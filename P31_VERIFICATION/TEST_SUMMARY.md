# P3.1 verification (14 October 2026)

- GCC 14.2 Linux Release C++20 with OpenMP: 4/4 selected tests PASS (three MC-SGS bitwise parity/unit tests + Qt dry-run).
- Full physical H0 E/ED/EDV × CONST/VAR regression, *reference mcsgs vs mcsgs-fast*, 6/6 model cases PASS; both full checkpoints compare at tolerance 1e-6; single CTest target P31_H0_all6_reference_fast_checkpoint PASS.
- Linux Release without OpenMP: 4/4 selected tests PASS.
- Native Qt Creator-equivalent launcher P3.1 H0 no arguments: SUCCESS, EDV/VAR 347 CG iterations.
- The complete 47-test P3 baseline certification is inherited from P3_VERIFICATION but **has not been rerun for the P3.1 branch**.
- Windows MinGW was **not** built here. No speed claims for Windows.
