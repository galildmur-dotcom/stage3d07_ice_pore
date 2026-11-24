#!/usr/bin/env python3
"""P10HF: deterministic source-only NumPy RBF test, before M1 ZIP access."""
from pathlib import Path
import numpy as np
import p10hc_continuous_kappa_geo as field

HERE=Path(__file__).resolve().parent
src,v25,v36,expected25,expected36,qa=field.load_centers(
    HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',HERE/'P10HA_KAPPA_QA.json')
den=qa['mechanical_only_25_36_shared_smoothing_denominator']
actual=field.rbf_at_points(src,v25,src,den)
error=float(np.max(np.abs(actual-expected25)))
field.check(error<1e-9,'NumPy kernel mismatch at 1200 original bins')
field.check(np.isfinite(actual).all() and 0<=actual.min()<=actual.max()<=1,
            'NumPy kernel bounds')
print('P10HF_NUMPY_ONLY_1200_SOURCE_SELFTEST_PASS max_diff=',format(error,'.3g'),flush=True)
