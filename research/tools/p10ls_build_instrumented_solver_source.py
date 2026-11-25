#!/usr/bin/env python3
"""Create isolated P10LS source only; no compilation, FEM, or marker writes."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10lm_package/P10LM_WORK'
DEST=ROOT/'p10ls_source_only/P10LS_WORK'
OLD_HEADER_SHA='0a470e43668a751dc0514f94e8e33ad2b8615c9d56c633579dd7112fafcec2b3'
NEW_REV='P10LS_M9_EDV_P1_P2_FACE_JUMP_PHYSICAL_DIAGNOSTIC_V1'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def once(text,old,new):
    if text.count(old)!=1:raise RuntimeError(f'P10LS source anchor mismatch {text.count(old)}: {old[:85]}')
    return text.replace(old,new)

def main():
    if DEST.exists():raise RuntimeError('P10LS output exists, refusing overwrite')
    pin=json.loads((OLD/'P10FN_SOURCE_SHA256.json').read_text())
    assert len(pin['files'])==101
    for name,digest in pin['files'].items():
        if sha(OLD/name)!=digest:raise RuntimeError('old pinned source mismatch '+name)
    assert sha(OLD/'stage3d10dd_4d_partition.hpp')==OLD_HEADER_SHA
    shutil.copytree(OLD,DEST,ignore=shutil.ignore_patterns('build','__pycache__','*.exe'))
    header=DEST/'stage3d10dd_4d_partition.hpp'
    s=header.read_text(encoding='utf8')
    s=once(s,'struct Snapshot {',
        'struct StressProbe {\n'
        ' std::vector<p10c::Tensor> sigma,geometric_dsigma;\n'
        '};\nstruct Snapshot {')
    s=once(s,'                                double weight){\n const std::size_t nq=',
        '                                double weight,StressProbe* probe=nullptr){\n'
        ' const std::size_t nq=')
    s=once(s,' Snapshot out;\n double numerator=0.;',
        ' Snapshot out;\n'
        ' if(probe){probe->sigma.resize(nq);probe->geometric_dsigma.resize(nq);}\n'
        ' double numerator=0.;')
    s=once(s,'   const auto law=qp.law.jvp(deps,0.,p10c::State{});',
        '   const auto law=qp.law.jvp(deps,0.,p10c::State{});\n'
        '   if(probe){\n'
        '    probe->sigma[qid]=qp.law.response.sigma;\n'
        '    probe->geometric_dsigma[qid]=law.d_sigma;\n'
        '   }')
    header.write_text(s,encoding='utf8')

    src=DEST/'src/stage3d10p_partial_audit.cpp'
    s=src.read_text(encoding='utf8')
    s=once(s,'#include "stage3d10dd_4d_partition.hpp"',
        '#include "stage3d10dd_4d_partition.hpp"\n'
        '#include "p10ls_face_jump_csv.hpp"')
    s=once(s,' mech4d.resize(std::size_t(c.steps));heat4d.resize(std::size_t(c.steps));',
        ' mech4d.resize(std::size_t(c.steps));heat4d.resize(std::size_t(c.steps));\n'
        ' std::ofstream face_jumps(c.out/"P10LS_FACE_JUMP_4D.csv");\n'
        ' if(!face_jumps)throw std::runtime_error("P10LS face-jump CSV creation");\n'
        ' p10ls::header(face_jumps);')
    s=once(s,'  auto local4d=ice3d::p10dd::mechanical_step(base.mesh,quad,state,\n'
             '       pairs.front().velocity,mask,adjoints[1].residual,\n'
             '       futures[1],weights[1]);',
        '  ice3d::p10dd::StressProbe qp_stress;\n'
        '  auto local4d=ice3d::p10dd::mechanical_step(base.mesh,quad,state,\n'
        '       pairs.front().velocity,mask,adjoints[1].residual,\n'
        '       futures[1],weights[1],&qp_stress);\n'
        '  const auto recovered_p1=p10lr::evaluate(base.mesh,quad,qp_stress.sigma,\n'
        '       qp_stress.geometric_dsigma,mask,1);\n'
        '  const auto recovered_p2=p10lr::evaluate(base.mesh,quad,qp_stress.sigma,\n'
        '       qp_stress.geometric_dsigma,mask,2);\n'
        '  if(recovered_p1.observed_pairs!=recovered_p2.observed_pairs)\n'
        '   throw std::runtime_error("P10LS P1/P2 face count parity");\n'
        '  p10ls::write(face_jumps,base.mesh.tets.size()==13166?"M9":"OTHER",\n'
        '               n,c.dt,recovered_p1,1);\n'
        '  p10ls::write(face_jumps,base.mesh.tets.size()==13166?"M9":"OTHER",\n'
        '               n,c.dt,recovered_p2,2);')
    src.write_text(s,encoding='utf8')
    for name in ('p10lq_tet10_face_recovery.hpp','p10lr_tet10_face_jump.hpp','p10ls_face_jump_csv.hpp'):
        shutil.copy2(ROOT/'research/diagnostics'/name,DEST/name)
    pin['revision']=NEW_REV
    pin['origin']='P10LM pinned source; P10LS opt-in QP collection and face-jump CSV'
    for name in ('stage3d10dd_4d_partition.hpp','src/stage3d10p_partial_audit.cpp'):
        pin['files'][name]=sha(DEST/name)
    (DEST/'P10FN_SOURCE_SHA256.json').write_text(json.dumps(pin,indent=2)+'\n',encoding='utf8')
    qa={'protocol':'P10LS_INSTRUMENTED_SOURCE_ONLY','status':'PREPARED_NO_FEM',
        'revision':NEW_REV,'source_count':len(pin['files']),
        'modified_pinned_sources':{
            'stage3d10dd_4d_partition.hpp':sha(header),
            'src/stage3d10p_partial_audit.cpp':sha(src)},
        'added_header_shas':{name:sha(DEST/name) for name in
          ('p10lq_tet10_face_recovery.hpp','p10lr_tet10_face_jump.hpp','p10ls_face_jump_csv.hpp')},
        'FEM_attempts':0,'mesh_generation_attempts':0}
    (ROOT/'research/P10LS_SOURCE_INTEGRATION_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':main()
