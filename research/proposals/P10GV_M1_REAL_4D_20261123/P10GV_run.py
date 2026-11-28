#!/usr/bin/env python3
"""Isolated source-pinned P10GT M1 physical 4D bridge to audited P10FN.

Preflight is read-only (except a small status text). --run creates only an
isolated M1 staging copy and consumes one P10FN native FEM marker.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = Path(r"G:\ildar\Stage3D07")
RUNS = ROOT / "LOCAL_RUNS"
STAGING = RUNS / "P10GV_M1_HXT10_IMMUTABLE_STAGING"
EVIDENCE_SHA = "7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3"
M1_SHA = "47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7"
M0_SHA = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
AUDIT_SHA = "a434e73bdebe94aa0b63fd20a16eacfc2f63e73411edd0aeefaf14cc50c09fa4"


class Mirror:
    def __init__(self, stream, file):
        self.stream, self.file = stream, file
    def write(self, s):
        self.stream.write(s)
        self.file.write(s)
        self.file.flush()
    def flush(self):
        self.stream.flush()
        self.file.flush()


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def need(ok: bool, message: str):
    if not ok:
        raise RuntimeError("P10GV_STOP: " + message)


def locate():
    choices = [HERE / "P10GT_HXT10_EVIDENCE.zip"]
    if sys.platform == "win32":
        choices += list(RUNS.glob("**/P10GT_HXT10_EVIDENCE.zip")) if RUNS.exists() else []
        choices += list((ROOT / "P10GT_TOOLS_R1").glob("**/P10GT_HXT10_EVIDENCE.zip"))
    matches = [p for p in choices if p.is_file() and digest(p.read_bytes()) == EVIDENCE_SHA]
    need(len(matches) > 0, "original P10GT_HXT10_EVIDENCE.zip not found; copy it next to 01_CMD (no old marker changes)")
    return matches[0]


def inspect(path):
    raw = path.read_bytes()
    need(digest(raw) == EVIDENCE_SHA, "evidence hash differs")
    with zipfile.ZipFile(io.BytesIO(raw)) as source:
        need(source.testzip() is None and len(source.namelist()) == 8, "ZIP CRC/8 members")
        manifest = json.loads(source.read("P10GT_MANIFEST.json"))
        need(manifest["native_3d_attempts"] == 1 and manifest["FEM_attempts"] == 0
             and manifest["native"]["native_exit_code"] == 0, "native not accepted")
        msh = source.read("P10GT_HXT10.msh")
        need(digest(msh) == M1_SHA and manifest["mesh_sha256"] == M1_SHA, "Tet10 M1 pin")
    audit = HERE / "P10GU_P10GT_INDEPENDENT_343_729_D027.json"
    need(digest(audit.read_bytes()) == AUDIT_SHA, "independent 4D entry gate audit tamper")
    verdict = json.loads(audit.read_text(encoding="utf-8"))
    need(verdict["D027_robust_mesh_gate"] is True and verdict["FEM_attempts"] == 0
         and verdict["mesh_sha256"] == M1_SHA and all(verdict["checks"].values()),
         "D-027 independent geometry GO not verified")
    a0 = json.loads((HERE / "approvals/M0.json").read_text(encoding="utf-8"))
    a1 = json.loads((HERE / "approvals/M1.json").read_text(encoding="utf-8"))
    need(a0["mesh_sha256"] == M0_SHA and a1["mesh_sha256"] == M1_SHA,
         "approval baseline/source mismatch")
    import P10FN_common
    need(P10FN_common.validate_source(), "P10FN R4 baseline source inventory")
    return msh, path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--evidence", type=Path, help="explicit original private P10GT ZIP for local QA")
    args = parser.parse_args()
    msh, path = inspect(args.evidence if args.evidence else locate())
    print("P10GV_4D_SOURCE_PASS original", path, flush=True)
    print("P10GV_M0_ALREADY_REAL_4D_PASS P10FS; M0 MSH", M0_SHA, flush=True)
    print("P10GV_M1_D027_GEOMETRY_GO M1 MSH", M1_SHA, flush=True)
    if not args.run:
        print("P10GV_PREFLIGHT_PASS_NO_FEM: next 02 is ONE new M1 forward+same-mesh adjoint 4D", flush=True)
        return 0
    need(sys.platform == "win32", "native 4D available only on researcher's Windows11")
    STAGING.mkdir(parents=True, exist_ok=True)
    target = STAGING / "M1.msh"
    if target.exists():
        need(digest(target.read_bytes()) == M1_SHA, "existing staging M1 mismatch; no overwrite")
    else:
        # exclusive create, no overwrites of user meshes/old M1 trees
        with target.open("xb") as sink:
            sink.write(msh)
    print("P10GV_M1_IMMUTABLE_COPY_SHA_PASS", target, flush=True)
    import P10FN_physics
    import P10FN_common
    P10FN_physics.MESHES = STAGING  # isolated new M1, never G:/.../meshes/M1.msh
    original = P10FN_common.capped_process

    def bounded(*a, **kwargs):
        # Tighten the inherited caps; retain the native Windows hard Job memory cap.
        kwargs["wall_s"] = min(kwargs["wall_s"], 1800)
        kwargs["memory_gib"] = min(kwargs["memory_gib"], 8)
        kwargs["output_gib"] = min(kwargs["output_gib"], 2)
        return original(*a, **kwargs)

    P10FN_physics.capped_process = bounded
    return P10FN_physics.run("M1", "R")


if __name__ == "__main__":
    # Show live progress in the persistent cmd.exe window and save an evidence
    # transcript. Never leave the user watching an empty window.
    log_name = "P10GV_02_RESULT.txt" if "--run" in sys.argv else "P10GV_01_RESULT.txt"
    transcript = (HERE / log_name).open("a", encoding="utf-8")
    sys.stdout = Mirror(sys.stdout, transcript)
    sys.stderr = Mirror(sys.stderr, transcript)
    try:
        sys.exit(main())
    except Exception as exc:
        print("P10GV_STOP_NO_AUTO_RETRY", repr(exc), flush=True)
        sys.exit(2)
