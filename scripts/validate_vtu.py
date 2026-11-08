#!/usr/bin/env python3
"""Optional independent VTK XML verification. Requires Python VTK package."""
import glob, pathlib, vtk
root=pathlib.Path(__file__).resolve().parents[1]
items=sorted(glob.glob(str(root/'results/*/thermal_*.vtu')))
assert len(items)>=9, f'Expected 9 transient VTUs, found {len(items)}'
for path in items:
    reader=vtk.vtkXMLUnstructuredGridReader();reader.SetFileName(path);reader.Update()
    grid=reader.GetOutput();a=grid.GetPointData().GetArray('Temperature_C');b=grid.GetPointData().GetArray('Temperature_K');c=grid.GetPointData().GetArray('dT_K')
    assert grid.GetNumberOfPoints()>0 and grid.GetNumberOfCells()>0
    assert grid.GetCellType(0)==vtk.VTK_QUADRATIC_TETRA
    assert all(x is not None for x in (a,b,c))
    mn,mx=a.GetRange();assert -30 < mn <= mx < -19.9
    print(pathlib.Path(path).relative_to(root), 'points',grid.GetNumberOfPoints(),'cells',grid.GetNumberOfCells(),'T_C_range',a.GetRange())
print('PASS:',len(items),'ParaView-compatible VTU snapshots')
