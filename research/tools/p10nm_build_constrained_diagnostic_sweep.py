#!/usr/bin/env python3
"""P10NM: guarded source-only radial sweep; independent native Gmsh evaluation later."""
import hashlib, json, shutil, sys, zipfile
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/tools'))
from p10nf_m13_pore_tri6_face_audit_readonly import read
from p10hv_independent_scan import EDGE,rule

SOURCE=ROOT/'p10na_m13_r2_evidence/P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
SHA='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
DEST=ROOT/'p10nm_m13_diagnostic_sweep'
ZIP=ROOT/'P10NM_M13_CONSTRAINED_DIAGNOSTIC_SWEEP_WINDOWS_20261126.zip'
C=np.array([0.,0.,.03])
PIVOTS=(8680,8681,9115)
# Variants centered on measured P10NL success, with local extension of pivot.
TRIALS=((.0075,.005,.005),(.010,.005,.005),(.0125,.005,.005),
        (.015,.005,.005),(.0175,.005,.005),(.020,.005,.005))

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if DEST.exists() or ZIP.exists():raise RuntimeError('P10NM_STOP: output exists; no overwrite')
    if sha(SOURCE)!=SHA:raise RuntimeError('P10NM_STOP: original source SHA mismatch')
    nodes,tets,surface=read(SOURCE)
    pore={n for _,conn in surface.values() for n in conn}
    affected={tag:cn for tag,cn in tets.items() if set(PIVOTS)&set(cn[:4])}
    assert len(affected)==67 and not set(PIVOTS)&pore
    dirs={n:(nodes[n]-C)/np.linalg.norm(nodes[n]-C) for n in PIVOTS}
    face=np.mean([nodes[n] for n in tets[9478][:4] if n in pore],axis=0)
    dirs[8680]=(face-C)/np.linalg.norm(face-C)
    _,D,W=rule(9)
    tags=sorted(affected)
    base=np.asarray([[nodes[n] for n in affected[tag]] for tag in tags])
    def geometry(arr):
        J=np.einsum('nic,qij->nqcj',arr,D,optimize=True)
        s=np.linalg.svd(J,compute_uv=False)
        det=np.linalg.det(J)
        return np.min(s[:,:,-1]/s[:,:,0],axis=1),det.min(axis=1),(det*W[None,:]).sum(axis=1)
    sigma0,det0,vol0=geometry(base)
    assert np.all(det0>0)
    source_lines=SOURCE.read_text(encoding='ascii').splitlines(keepends=True)
    start=next(i for i,l in enumerate(source_lines) if l.strip()=='$Nodes')
    count=int(source_lines[start+1])
    line_index={int(source_lines[i].split()[0]):i for i in range(start+2,start+2+count)}
    assert len(line_index)==len(nodes)
    DEST.mkdir()
    shutil.copy2(SOURCE,DEST/SOURCE.name)
    experiments=[]
    for trial_id,distances in enumerate(TRIALS,1):
        move={n:dirs[n]*(d*.001) for n,d in zip(PIVOTS,distances)}
        for cn in affected.values():
            for edge,(a,b) in enumerate(EDGE):
                middle=cn[4+edge]
                vector=(move.get(cn[a],np.zeros(3))+move.get(cn[b],np.zeros(3)))/2
                if np.any(vector):
                    if middle in move and not np.allclose(move[middle],vector,rtol=0,atol=1e-18):
                        raise RuntimeError('P10NM_STOP: non-conforming shared midside')
                    move[middle]=vector
        assert len(move)==47 and not move.keys()&pore
        assert not [tag for tag,cn in tets.items() if tag not in affected and move.keys()&set(cn)]
        new=base.copy()
        for row,tag in enumerate(tags):
            for local,n in enumerate(affected[tag]):
                if n in move:new[row,local]+=move[n]
        sigma,det,vol=geometry(new)
        ratios=vol/vol0
        feasible=bool(np.all(det>0) and ratios.min()>=.9 and ratios.max()<=1.1)
        record={'id':trial_id,'pivot_displacements_mm':dict(zip(map(str,PIVOTS),distances)),
            'source_729qp_min_sigma_ratio':float(sigma.min()),
            'source_729qp_min_detJ':float(det.min()),
            'individual_curved_volume_ratio_min_max':[float(ratios.min()),float(ratios.max())],
            'total_star_volume_ratio':float(vol.sum()/vol0.sum()),
            'local_sigma_worsened_count':int(np.count_nonzero(sigma<sigma0-1e-12)),
            'worst_relative_local_sigma_loss':float(np.maximum(0,1-sigma/sigma0).max()),
            'feasible_729qp_volume_bounds':feasible}
        # Failed candidates are documented but do not enter the Windows package.
        if feasible:
            lines=list(source_lines)
            for n,v in move.items():
                xyz=nodes[n]+v
                lines[line_index[n]]=f'{n} {xyz[0]:.17g} {xyz[1]:.17g} {xyz[2]:.17g}\n'
            name=f'P10NM_DIAGNOSTIC_{trial_id:02d}_NOT_R3.msh'
            path=DEST/name
            path.write_text(''.join(lines),encoding='ascii',newline='')
            new_nodes,new_tets,new_surface=read(path)
            assert new_tets==tets and new_surface==surface
            assert all(np.array_equal(nodes[n],new_nodes[n]) for n in pore)
            assert all(np.array_equal(nodes[n],new_nodes[n]) for n in nodes.keys()-move.keys())
            record.update({'file':name,'sha256':sha(path),'changed_nodes':len(move)})
        experiments.append(record)
    assert len([r for r in experiments if r['feasible_729qp_volume_bounds']])>=2
    manifest={'protocol':'P10NM_SOURCE_ONLY_CONSTRAINED_DIAGNOSTIC_SWEEP',
        'status':'DIAGNOSTICS_NOT_M13_R3_NOT_FEM_AUTHORIZED',
        'original_file':SOURCE.name,'original_sha256':SHA,'Tet10':len(tets),
        'pore_Tri6':len(surface),'affected_Tet10':len(affected),
        'source_sigma_min':float(sigma0.min()),'experiments':experiments,
        'gmsh_generation_attempts':0,'FEM_attempts':0,'marker_uses':0}
    (DEST/'P10NM_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copy2(ROOT/'research/tools/p10nm_native_quality_sweep_windows.py',DEST/'P10NM_NATIVE_QUALITY_SWEEP.py')
    shutil.copy2(ROOT/'research/tools/P10NM_RUN_NATIVE_QUALITY_SWEEP.cmd',DEST/'P10NM_RUN_NATIVE_QUALITY_SWEEP.cmd')
    shutil.copy2(ROOT/'research/P10NM_M13_CONSTRAINED_DIAGNOSTIC_PROTOCOL_20261126.md',DEST/'README_RU.md')
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(DEST.iterdir()):z.write(path,arcname=path.name)
    print(json.dumps({'zip':str(ZIP),'trials':experiments},indent=2))

if __name__=='__main__':main()
