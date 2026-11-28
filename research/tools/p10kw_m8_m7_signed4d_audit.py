#!/usr/bin/env python3
"""Read-only, cell-wise signed-4D comparison of genuine M7/M8 evidence ZIPs."""
import argparse
import io
import json
import zipfile

import numpy as np
import pandas as pd

FIELDS = ["mech_explicit_per_m", "mech_equilibrium_per_m", "mech_history_per_m",
          "thermal_mass_per_m", "thermal_diffusion_per_m", "thermal_robin_per_m"]
KEY = ["step", "region", "radial_bin", "mu_bin", "phi_bin"]


def read_zip(path):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None, "ZIP CRC failed"
        df = pd.read_csv(io.BytesIO(archive.read("P10DD_SIGNED_R_THETA_PHI_T.csv")))
        name = next(n for n in archive.namelist() if n.endswith("MANIFEST.json"))
        manifest = json.loads(archive.read(name))
    assert len(df) == 43236 and not df.duplicated(KEY).any()
    assert np.isfinite(df[FIELDS + ["total_per_m"]].to_numpy()).all()
    assert np.allclose(df[FIELDS].sum(axis=1), df.total_per_m, atol=1e-11, rtol=1e-12)
    return df, manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("m7")
    parser.add_argument("m8")
    parser.add_argument("--m6", help="Optional preceding mesh for increment alignment")
    parser.add_argument("--out", required=True)
    a = parser.parse_args()
    m7, man7 = read_zip(a.m7)
    m8, man8 = read_zip(a.m8)
    merged = m7.merge(m8, on=KEY, suffixes=("_7", "_8"), validate="one_to_one")
    assert len(merged) == len(m7)
    for col in ["time_start_s", "time_end_s", "r_lower_mm", "r_upper_mm",
                "theta_lower_rad", "theta_upper_rad", "phi_lower_rad", "phi_upper_rad"]:
        assert np.allclose(merged[col + "_7"], merged[col + "_8"], equal_nan=True)
    diff = merged.total_per_m_8.to_numpy() - merged.total_per_m_7.to_numpy()
    v = merged.region == "VOLUME"
    print("regions:", merged.region.value_counts().to_dict())
    summary = {
        "status": "PASS",
        "m7_manifest_status": man7.get("status"),
        "m8_manifest_status": man8.get("status"),
        "rows": len(merged),
        "m7_signed_total_per_m": float(m7.total_per_m.sum()),
        "m8_signed_total_per_m": float(m8.total_per_m.sum()),
        "delta_m8_minus_m7_per_m": float(diff.sum()),
        "relative_delta_percent": float(100 * diff.sum() / m7.total_per_m.sum()),
        "signed_l1_per_m": float(np.abs(diff).sum()),
        "signed_l2_per_m": float(np.linalg.norm(diff)),
        "cancellation_ratio": float(np.abs(diff).sum() / abs(diff.sum())),
        "components_delta_per_m": {f: float((merged[f + "_8"] - merged[f + "_7"]).sum()) for f in FIELDS},
        "late_steps_31_36_l1_fraction": float(np.abs(diff[merged.step >= 31]).sum() / np.abs(diff).sum()),
        "late_steps_31_36_signed_delta_per_m": float(diff[merged.step >= 31].sum()),
        "north_one_mu_bin_delta_per_m": float(diff[v & (merged.mu_bin == merged.loc[v, "mu_bin"].max())].sum()),
        "south_one_mu_bin_delta_per_m": float(diff[v & (merged.mu_bin == merged.loc[v, "mu_bin"].min())].sum()),
    }
    summary["nonpolar_delta_per_m"] = float(diff[v & ~merged.mu_bin.isin([merged.loc[v, "mu_bin"].max(), merged.loc[v, "mu_bin"].min()])].sum())
    summary["by_step"] = [{"step": int(step), "delta_per_m": float(x.sum()),
                           "l1_per_m": float(x.abs().sum())}
                          for step, x in merged.assign(delta=diff).groupby("step").delta]
    summary["by_radial_bin"] = [{"bin": int(radial), "delta_per_m": float(x.sum()),
                                 "l1_per_m": float(x.abs().sum())}
                                for radial, x in merged.loc[v].assign(delta=diff[v]).groupby("radial_bin").delta]
    summary["by_mu_bin"] = [{"bin": int(mu), "delta_per_m": float(x.sum()),
                             "l1_per_m": float(x.abs().sum())}
                            for mu, x in merged.loc[v].assign(delta=diff[v]).groupby("mu_bin").delta]
    if a.m6:
        m6, _ = read_zip(a.m6)
        triplet = m6[KEY + ["total_per_m"]].merge(
            m7[KEY + ["total_per_m"]], on=KEY, suffixes=("_6", "_7"), validate="one_to_one")
        triplet = triplet.merge(m8[KEY + ["total_per_m"]], on=KEY, validate="one_to_one")
        prior = (triplet.total_per_m_7 - triplet.total_per_m_6).to_numpy()
        current = (triplet.total_per_m - triplet.total_per_m_7).to_numpy()
        summary["successive_increment_correlation"] = float(np.corrcoef(prior, current)[0, 1])
        summary["successive_l1_ratio"] = float(np.abs(current).sum() / np.abs(prior).sum())
        summary["successive_l2_ratio"] = float(np.linalg.norm(current) / np.linalg.norm(prior))
        summary["successive_increment_cosine"] = float(np.dot(prior, current) / np.linalg.norm(prior) / np.linalg.norm(current))
    with open(a.out, "w", encoding="utf-8") as out:
        json.dump(summary, out, indent=2, ensure_ascii=False)
        out.write("\n")
    print(json.dumps({k: value for k, value in summary.items() if not isinstance(value, list)}, indent=2))


if __name__ == "__main__":
    main()
