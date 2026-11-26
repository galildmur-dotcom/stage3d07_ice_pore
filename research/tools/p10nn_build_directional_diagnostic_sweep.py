#!/usr/bin/env python3
"""P10NN: source-only 729QP tangential displacement scan with conforming Tet10 edges."""
import hashlib,itertools,json,shutil,sys,zipfile
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/tools'))
from p10nf_m13_pore_tri6_face_audit_readonly import read
from p10hv_independent_scan import EDGE,rule

SOURCE=ROOT/'p10na_m13_r2_evidence/P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
SHA='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
DEST=ROOT/'p10nn_m13_directional_diagnostics'
ZIP=ROOT/'P10NN_M13_DIRECTIONAL_DIAGNOSTIC_WINDOWS_20261126.zip'
C=np.array([0.,0.,.03]); PIVOTS=(8680,8681,9115)
SCAN_MM=(-.006,-.003,0.,.003,.006)

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if DEST.exists() or ZIP.exists():raise RuntimeError('P10NN_STOP: output already exists; no overwrite')
    if digest(SOURCE)!=SHA:raise RuntimeError('P10NN_STOP: source SHA mismatch')
    nodes,tets,surface=read(SOURCE)
    pore={n for _,cn in surface.values() for n in cn}
    affected={k:cn for k,cn in tets.items() if set(PIVOTS)&set(cn[:4])}
    tags=sorted(affected)
    assert len(tags)==67 and not set(PIVOTS)&pore
    radial={n:(nodes[n]-C)/np.linalg.norm(nodes[n]-C) for n in PIVOTS}
    face=np.mean([nodes[n] for n in tets[9478][:4] if n in pore],axis=0)
    radial[8680]=(face-C)/np.linalg.norm(face-C)
    e1=nodes[8681]-nodes[8680]
    e1=e1-np.dot(e1,radial[8680])*radial[8680]
    e1=e1/np.linalg.norm(e1)
    e2=np.cross(radial[8680],e1)
    e2=e2/np.linalg.norm(e2)
    assert abs(np.dot(radial[8680],e1))<1e-12
    assert abs(np.dot(radial[8680],e2))<1e-12
    _,D,W=rule(9)
    base=np.asarray([[nodes[n] for n in affected[k]] for k in tags])
    def measure(pos):
        J=np.einsum('nic,qij->nqcj',pos,D,optimize=True)
        singular=np.linalg.svd(J,compute_uv=False)
        det=np.linalg.det(J)
        return np.min(singular[:,:,-1]/singular[:,:,0],axis=1),det.min(axis=1),(det*W[None,:]).sum(axis=1)
    s0,d0,v0=measure(base)
    assert np.all(d0>0)
    pre={}
    allresults=[]
    for a,b in itertools.product(SCAN_MM,repeat=2):
        move={8680:(.0125*radial[8680]+a*e1+b*e2)*.001,
              8681:.005*radial[8681]*.001, 9115:.005*radial[9115]*.001}
        for cn in affected.values():
            for edge,(i,j) in enumerate(EDGE):
                mid=cn[4+edge]
                vec=(move.get(cn[i],np.zeros(3))+move.get(cn[j],np.zeros(3)))/2
                if np.any(vec):
                    if mid in move and not np.allclose(move[mid],vec,atol=1e-18,rtol=0):
                        raise RuntimeError('P10NN_STOP: shared midnode displacement mismatch')
                    move[mid]=vec
        assert len(move)==47 and not move.keys()&pore
        assert not [k for k,cn in tets.items() if k not in affected and move.keys()&set(cn)]
        new=base.copy()
        for row,k in enumerate(tags):
            for local,n in enumerate(affected[k]):
                if n in move:new[row,local]+=move[n]
        sigma,det,vol=measure(new)
        ratios=vol/v0
        feasible=bool(np.all(det>0) and ratios.min()>=.9 and ratios.max()<=1.1)
        record={'tangent_t1_mm':a,'tangent_t2_mm':b,'radial_pivot_mm':.0125,
            'sigma_min_729qp':float(sigma.min()), 'worst_tet':int(tags[int(np.argmin(sigma))]),
            'min_detJ_729qp':float(det.min()),
            'volume_ratio_min_max':[float(ratios.min()),float(ratios.max())],
            'total_star_volume_ratio':float(vol.sum()/v0.sum()),
            'worsened_local_elements':int(np.count_nonzero(sigma<s0-1e-12)),
            'worst_relative_sigma_loss':float(np.maximum(0,1-sigma/s0).max()),
            'feasible':feasible}
        allresults.append(record)
        if feasible:pre[(a,b)]=move
    feasible=[r for r in allresults if r['feasible']]
    if not feasible:raise RuntimeError('P10NN_STOP: no feasible candidate')
    baseline=next(r for r in feasible if r['tangent_t1_mm']==r['tangent_t2_mm']==0.)
    ranked=sorted(feasible,key=lambda r:(-r['sigma_min_729qp'],r['worst_relative_sigma_loss']))
    # Include the known radial-only control and at most 4 nonduplicate leaders.
    selected=[baseline]
    selected.extend(r for r in ranked if r is not baseline and len(selected)<5)
    lines=SOURCE.read_text(encoding='ascii').splitlines(keepends=True)
    start=next(i for i,x in enumerate(lines) if x.strip()=='$Nodes')
    count=int(lines[start+1]); offsets={int(lines[i].split()[0]):i for i in range(start+2,start+2+count)}
    DEST.mkdir();shutil.copy2(SOURCE,DEST/SOURCE.name)
    for idx,r in enumerate(selected,1):
        move=pre[(r['tangent_t1_mm'],r['tangent_t2_mm'])]
        updated=list(lines)
        for n,v in move.items():
            xyz=nodes[n]+v
            updated[offsets[n]]=f'{n} {xyz[0]:.17g} {xyz[1]:.17g} {xyz[2]:.17g}\n'
        fname=f'P10NN_DIAGNOSTIC_{idx:02d}_NOT_R3.msh'
        path=DEST/fname;path.write_text(''.join(updated),encoding='ascii',newline='')
        revised,tnew,snew=read(path)
        assert tnew==tets and snew==surface
        assert all(np.array_equal(revised[n],nodes[n]) for n in pore)
        assert all(np.array_equal(revised[n],nodes[n]) for n in nodes.keys()-move.keys())
        r.update({'file':fname,'sha256':digest(path),'changed_node_count':len(move)})
    manifest={'protocol':'P10NN_SOURCE_ONLY_2D_TANGENT_SCAN_729QP',
        'status':'DIAGNOSTIC_ONLY_NOT_M13_R3_NOT_FEM_AUTHORIZED',
        'original_file':SOURCE.name,'original_sha256':SHA,
        'Tet10':len(tets),'affected_Tet10':len(tags),'pore_Tri6':len(surface),
        'scan_count':len(allresults),'feasible_count':len(feasible),
        'fixed_pivot_radial_mm':.0125,'fixed_neighbors_radial_mm':.005,
        'tangent_basis_t1':e1.tolist(),'tangent_basis_t2':e2.tolist(),
        'source_sigma_min':float(s0.min()),'scan':allresults,
        'selected':selected,'gmsh_generation_attempts':0,'FEM_attempts':0,'marker_uses':0}
    (DEST/'P10NN_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copy2(ROOT/'research/tools/p10nn_native_quality_windows.py',DEST/'P10NN_NATIVE_QUALITY.py')
    shutil.copy2(ROOT/'research/tools/P10NN_RUN_NATIVE_QUALITY.cmd',DEST/'P10NN_RUN_NATIVE_QUALITY.cmd')
    shutil.copy2(ROOT/'research/P10NN_M13_DIRECTIONAL_DIAGNOSTICS_20261126.md',DEST/'README_RU.md')
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(DEST.iterdir()):z.write(path,arcname=path.name)
    print(json.dumps({'all':len(allresults),'feasible':len(feasible),'selected':selected},indent=2))

if __name__=='__main__':main()
