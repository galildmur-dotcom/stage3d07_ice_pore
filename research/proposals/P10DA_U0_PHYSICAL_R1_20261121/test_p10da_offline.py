"""Offline regression against the archived H0 thermal-QP CSV; NO FEM/Gmsh."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import shutil


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("p10da", HERE / "P10DA_run_one_u0.py")
assert spec and spec.loader
p10da = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p10da)
SOURCE = ROOT / "research/evidence/P10CA_R1_WINDOWS_EXITCODE_STOP_20261120/input"
FILENAMES = ["P10W_ANALYTIC_ADJOINT.csv", "P10W_COMPONENTS.csv", "P10W_STEP_COMPONENTS.csv",
             "P10BX_THERMAL_QP_STEP_BINS.csv", "P10BX_THERMAL_STEP_AUDIT.csv"]
STDOUT = ("P10W_ANALYTIC_ADJOINT_OK geometry_partial=ANALYTIC_TET10 central_fd_evaluations=0\n"
          "P10BX_THERMAL_QP_INTEGRATED_OK steps=6 exported_rows=606 original_gradient_unchanged=1\n")


def main():
    assert SOURCE.is_dir(), SOURCE
    p10da.EXPECTED_QP_PER_STEP = 7388 * 64  # H0 regression, not physical U0.
    with tempfile.TemporaryDirectory(prefix="p10da_synthetic_") as tmp:
        dst = Path(tmp)
        for name in FILENAMES:
            shutil.copyfile(SOURCE / name, dst / name)
        ok = p10da.audit_csv(dst, STDOUT)
        assert abs(ok["full_D_R_jpeak_per_m"] - 3.1676918514138728) < 1e-12
        assert abs(ok["thermal_total_per_m"] - 0.066379552082746485) < 1e-12
        assert ok["max_thermal_closure_error_per_m"] < 1e-9
        print("P10DA_H0_ARCHIVED_CSV_REGRESSION_OK FEM=0 GMSH=0")

        step = dst / "P10BX_THERMAL_STEP_AUDIT.csv"
        altered = step.read_text(encoding="utf-8").replace(",472832,", ",472831,", 1)
        assert altered != step.read_text(encoding="utf-8")
        step.write_text(altered, encoding="utf-8")
        try:
            p10da.audit_csv(dst, STDOUT)
        except RuntimeError as e:
            assert "VOLUME_QP_COUNT_MISMATCH" in str(e), str(e)
        else:
            raise AssertionError("Corrupted volume QP count accepted")
        print("P10DA_NEGATIVE_QP_COUNT_TEST_OK")


if __name__ == "__main__":
    main()
