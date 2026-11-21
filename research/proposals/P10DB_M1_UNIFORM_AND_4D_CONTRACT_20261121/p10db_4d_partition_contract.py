#!/usr/bin/env python3
"""Reference/test for Stage3D07 signed 4D partition (NOT a FEM export).

An independent contract for upcoming solver instrumentation. It does not
claim that P10DA's already running executable emits these contributions.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import math
from typing import Mapping


PORE_CENTRE_M = (0.0, 0.0, 0.03)
R_M = 0.001
RADIAL_MM = (0.0, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 15.0)
POLAR_BANDS = 10  # mu = cos(theta), south to north
PHI_SECTORS = 12  # [0,2pi), seam at +x
KEYS = ("mech_explicit", "mech_equilibrium", "mech_history",
        "heat_mass", "heat_diffusion", "heat_robin")


def cell_index(x: float, y: float, z: float) -> tuple[int, int, int, bool]:
    """Return radial/polar/azimuth 4D cell and physical-QP CAD-inside flag."""
    rx, ry, rz = x - PORE_CENTRE_M[0], y - PORE_CENTRE_M[1], z - PORE_CENTRE_M[2]
    r = math.sqrt(rx * rx + ry * ry + rz * rz)
    if not (math.isfinite(r) and r > 0):
        raise ValueError("Invalid physical QP radius")
    dm = 1000.0 * (r - R_M)
    inside = dm < -1e-12
    radial = max(0, sum(dm >= lower for lower in RADIAL_MM) - 1)
    mu = max(-1.0, min(1.0, rz / r))
    polar = min(POLAR_BANDS - 1, int((mu + 1.0) * POLAR_BANDS / 2.0))
    phi = math.atan2(ry, rx) % (2 * math.pi)
    azimuth = min(PHI_SECTORS - 1, int(phi * PHI_SECTORS / (2 * math.pi)))
    return radial, polar, azimuth, inside


@dataclass
class Bin:
    signed: dict[str, float] = field(default_factory=lambda: {key: 0.0 for key in KEYS})
    abs_terms: dict[str, float] = field(default_factory=lambda: {key: 0.0 for key in KEYS})
    mech_qps: int = 0
    mech_volume_m3: float = 0.0
    heat_qps: int = 0
    heat_volume_m3: float = 0.0
    inside_cad_qps: int = 0


class Partition:
    """One record per (step, r, mu, phi); top Robin handled separately."""

    def __init__(self) -> None:
        self.cells: dict[tuple[int, int, int, int], Bin] = defaultdict(Bin)
        self.top_robin: dict[int, float] = defaultdict(float)

    def add(self, step: int, xyz_m: tuple[float, float, float], *,
            part: str, contribution_per_m: float, volume_m3: float) -> None:
        if step < 1 or part not in KEYS or not all(map(math.isfinite, (contribution_per_m, volume_m3))) or volume_m3 <= 0:
            raise ValueError("Invalid 4D signed contribution")
        shell, polar, azimuth, inside = cell_index(*xyz_m)
        row = self.cells[step, shell, polar, azimuth]
        row.signed[part] += contribution_per_m
        row.abs_terms[part] += abs(contribution_per_m)
        # Exactly one geometry/QP count per family, even when all three
        # components for the SAME QP are inserted consecutively.
        if part == "mech_explicit":
            row.mech_qps += 1
            row.mech_volume_m3 += volume_m3
        elif part == "heat_mass":
            row.heat_qps += 1
            row.heat_volume_m3 += volume_m3
        if part in ("mech_explicit", "heat_mass"):
            row.inside_cad_qps += int(inside)

    def add_top_robin(self, step: int, contribution_per_m: float) -> None:
        if step < 1 or not math.isfinite(contribution_per_m):
            raise ValueError("Invalid top Robin term")
        self.top_robin[step] += contribution_per_m

    def totals(self) -> dict[str, float]:
        out = {key: math.fsum(row.signed[key] for row in self.cells.values()) for key in KEYS}
        out["heat_robin"] += math.fsum(self.top_robin.values())
        return out

    def check_global(self, references: Mapping[str, float], rel_tolerance: float = 1e-7) -> None:
        totals = self.totals()
        if set(references) != set(KEYS):
            raise ValueError("Need all six global physical components")
        for key in KEYS:
            target = references[key]
            absolute_sum = math.fsum(row.abs_terms[key] for row in self.cells.values())
            if key == "heat_robin":
                absolute_sum += math.fsum(abs(x) for x in self.top_robin.values())
            scale = max(1e-10, abs(target), absolute_sum)
            if not math.isfinite(target) or abs(totals[key] - target) > rel_tolerance * scale:
                raise ValueError(f"4D_CLOSURE_STOP component={key}")


def selftest() -> None:
    # South, equator, north, seam and all azimuthal sectors are distinct.
    assert cell_index(0, 0, PORE_CENTRE_M[2] - R_M)[1] == 0
    assert cell_index(0, 0, PORE_CENTRE_M[2] + R_M)[1] == 9
    assert cell_index(R_M, 0, PORE_CENTRE_M[2])[:3] == (0, 5, 0)
    assert cell_index(R_M, -1e-12, PORE_CENTRE_M[2])[2] == 11
    assert len({cell_index(R_M * math.cos(2 * math.pi * (k+.5)/12),
                           R_M * math.sin(2 * math.pi * (k+.5)/12),
                           PORE_CENTRE_M[2])[2] for k in range(12)}) == 12
    assert cell_index(0, 0, PORE_CENTRE_M[2] + R_M - 1e-8)[3]

    p = Partition()
    a = (R_M, 0, PORE_CENTRE_M[2])
    b = (R_M * math.cos(math.pi / 3), R_M * math.sin(math.pi / 3), PORE_CENTRE_M[2])
    p.add(1, a, part="mech_explicit", contribution_per_m=2.0, volume_m3=1e-12)
    p.add(1, b, part="mech_explicit", contribution_per_m=-1.0, volume_m3=1e-12)
    p.add(2, b, part="heat_mass", contribution_per_m=0.15, volume_m3=1e-12)
    p.add_top_robin(2, 0.25)
    refs = {key: 0.0 for key in KEYS}
    refs.update(mech_explicit=1.0, heat_mass=0.15, heat_robin=0.25)
    p.check_global(refs)
    try:
        p.check_global({**refs, "mech_explicit": 1.01})
    except ValueError as e:
        assert "4D_CLOSURE_STOP" in str(e)
    else:
        raise AssertionError("Corrupted global reference was accepted")
    assert p.cells[(1, 0, 5, 0)].mech_qps == 1
    print("P10DB_4D_SYNTHETIC_PARTITION_OK cells=10x10x12 signed=6 temporal=YES FEM=0")


if __name__ == "__main__":
    selftest()
