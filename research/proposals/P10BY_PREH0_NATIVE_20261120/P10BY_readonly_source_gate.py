#!/usr/bin/env python3
"""Read-only verification of the exact 35-file P10BM source and P10BW/BX.

Local cross-check of the CMake gate, NOT a required Windows user action.
No git checkout/switch/patch, source writes, FEM, shell or network calls.
"""
import argparse
import hashlib
from pathlib import Path
import sys


COMPONENTS = (
    ("bx", "src/stage3d10p_partial_audit.cpp",
     "57754cfaa031fddb391e6b211a6f083346475611d180676c0c4987926ea54b1b"),
    ("bx", "src/stage3d10w_analytic_adjoint.cpp",
     "1d769e559aa561817685b56949bf649e6ceddb89da4cfc294cc18738d6d82df8"),
    ("bx", "stage3d10bx_thermal_step_hook.hpp",
     "79b716c389a6a9dd466d65d795ad3a67bda206bdd636eec0fb03962dc3155574"),
    ("bw", "stage3d10bw_thermal_qp_partition.hpp",
     "71992ba7e8c0b44d7832c5d8566ef8886517bbd87f953b119271746483f0fa23"),
    ("bw", "P10BW_thermal_qp_native_unit.cpp",
     "719a9db9f3c3221acdfc096a88cfbb1cdb81307ba931463f3ff62726e10a03c6"),
)


def check_bytes(data: bytes, expected: str, name: str) -> None:
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise ValueError(f"P10BY_STOP: SHA256 mismatch {name}: {actual}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pinned-root", required=True, type=Path)
    ap.add_argument("--p10bx-root", required=True, type=Path)
    ap.add_argument("--p10bw-root", required=True, type=Path)
    args = ap.parse_args()
    manifest = Path(__file__).with_name("P10BY_PINNED_SHA256.txt")
    roots = {"bx": args.p10bx_root, "bw": args.p10bw_root}
    checks = 0
    try:
        lines = [line for line in manifest.read_text(encoding="utf-8").splitlines()
                 if line and not line.startswith("#")]
        if len(lines) != 35:
            raise ValueError("P10BY_STOP: expected exactly 35 original source hashes")
        paths_seen = set()
        for line in lines:
            path, sep, expected = line.partition("|")
            if not sep or path in paths_seen or len(expected) != 64:
                raise ValueError("P10BY_STOP: invalid/duplicate source manifest row")
            paths_seen.add(path)
            data = (args.pinned_root / path).read_bytes()
            check_bytes(data, expected, path)
            checks += 1
        for root, path, expected in COMPONENTS:
            data = (roots[root] / path).read_bytes()
            check_bytes(data, expected, root + "/" + path)
            checks += 1
        # Negative detector test mutates ONLY an in-memory buffer.
        marker = b"no filesystem writes"
        digest = hashlib.sha256(marker).hexdigest()
        try:
            check_bytes(marker + b"!", digest, "negative-memory-control")
        except ValueError:
            pass
        else:
            raise ValueError("P10BY_STOP: checksum error detector disabled")
    except (OSError, ValueError) as ex:
        print(str(ex), file=sys.stderr)
        return 2
    print("P10BY_READONLY_SHA256_GATE_OK original=35 proposal=5 "
          f"total={checks} negative_memory_control=1 "
          "filesystem_writes=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
