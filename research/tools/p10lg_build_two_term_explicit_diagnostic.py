#!/usr/bin/env python3
"""Create isolated, opt-in P10LG source-only Tet10 4D diagnostic variant.

Never generate mesh, run forward/adjoint FEM, consume one-shot, or alter pins.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'p10lc_package/P10LC_WORK'
DEST=ROOT/'p10lg_source_only/P10LG_WORK'
BASE='stage3d10dd_4d_partition.hpp'
PIN='bbcb824a9fa25d7c66be54091c19c56b2a7ced40d2801071250f0b57ed4df55d'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def one(source,old,new):
    count=source.count(old)
    if count!=1:raise RuntimeError(f'P10LG expected one, got {count}: {old[:90]!r}')
    return source.replace(old,new)

def main():
    if DEST.exists():raise RuntimeError('P10LG output already exists; refuse overwrite')
    assert sha(SRC/BASE)==PIN
    shutil.copytree(SRC,DEST,ignore=shutil.ignore_patterns('__pycache__','build','*.exe'))
    s=(DEST/BASE).read_text(encoding='utf8')
    s=one(s,'struct Cell {\n Parts part{};',
        'struct Cell {\n Parts part{};\n'
        ' double explicit_geometry=0.,explicit_stress=0.; // P10LG extra diagnostic only')
    s=one(s,' std::array<double,ncell> dnumerator{};\n std::array<double,ncell> dvolume{};',
        ' std::array<double,ncell> dnumerator{};\n'
        ' std::array<double,ncell> dnumerator_geometry{},dnumerator_stress{};\n'
        ' std::array<double,ncell> dvolume{};')
    s=one(s,'   dnumerator[cell_id]+=dv*src.value+qp.volume*dpoint;\n   dvolume[cell_id]+=dv;',
        '   dnumerator[cell_id]+=dv*src.value+qp.volume*dpoint;\n'
        '   dnumerator_geometry[cell_id]+=dv*src.value;\n'
        '   dnumerator_stress[cell_id]+=qp.volume*dpoint;\n'
        '   dvolume[cell_id]+=dv;')
    s=one(s,' for(std::size_t i=0;i<ncell;++i)\n'
            '  out.cells[i].part.explicit_objective=weight*\n'
            '   (dnumerator[i]-mean*dvolume[i])/out.observed_volume;',
        ' for(std::size_t i=0;i<ncell;++i){\n'
        '  out.cells[i].part.explicit_objective=weight*\n'
        '   (dnumerator[i]-mean*dvolume[i])/out.observed_volume;\n'
        '  out.cells[i].explicit_geometry=weight*\n'
        '   (dnumerator_geometry[i]-mean*dvolume[i])/out.observed_volume;\n'
        '  out.cells[i].explicit_stress=weight*\n'
        '   dnumerator_stress[i]/out.observed_volume;\n'
        '  expect_close(out.cells[i].explicit_geometry+out.cells[i].explicit_stress,\n'
        '    out.cells[i].part.explicit_objective,"P10LG cell explicit split",1.e-10);\n'
        ' }')
    s=one(s,' std::ofstream audit(out_dir/"P10DD_FULL4D_CLOSURE_AUDIT.csv");\n'
            ' if(!data||!audit)throw std::runtime_error("P10DD CSV creation failure");',
        ' std::ofstream audit(out_dir/"P10DD_FULL4D_CLOSURE_AUDIT.csv");\n'
        ' std::ofstream split(out_dir/"P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv");\n'
        ' if(!data||!audit||!split)throw std::runtime_error("P10LG CSV creation failure");')
    s=one(s,' data<<std::setprecision(17);audit<<std::setprecision(17);',
        ''' data<<std::setprecision(17);audit<<std::setprecision(17);
 split<<std::setprecision(17);
 split<<"mesh,step,time_end_s,radial_bin,mu_bin,phi_bin,"
       "explicit_geometry_normalization_per_m,explicit_stress_chain_per_m,"
       "explicit_sum_per_m\\n";''')
    s=one(s,' Parts sum{};\n for(int step=1;step<=steps;++step){',
        ' Parts sum{};\n double split_geometry_sum=0.,split_stress_sum=0.;\n'
        ' for(int step=1;step<=steps;++step){')
    s=one(s,'    Parts p=m.cells[id].part;p.add(h.cells[id].part);',
        '''    Parts p=m.cells[id].part;p.add(h.cells[id].part);
    const auto& mc=m.cells[id];
    expect_close(mc.explicit_geometry+mc.explicit_stress,
      mc.part.explicit_objective,"P10LG writer cell closure",1.e-10);
    split<<mesh_name<<','<<step<<','<<step*dt<<','
         <<ir<<','<<im<<','<<ip<<','<<mc.explicit_geometry<<','
         <<mc.explicit_stress<<','<<mc.part.explicit_objective<<'\\n';
    split_geometry_sum+=mc.explicit_geometry;
    split_stress_sum+=mc.explicit_stress;''')
    s=one(s,' expect_close(sum.explicit_objective,reference.explicit_objective,"all-step explicit");',
        ' expect_close(split_geometry_sum+split_stress_sum,\n'
        '   sum.explicit_objective,"P10LG all-step two-term closure",1.e-10);\n'
        ' expect_close(sum.explicit_objective,reference.explicit_objective,"all-step explicit");')
    s=one(s,' data.close();audit.close();\n if(!data||!audit)',
        ' data.close();audit.close();split.close();\n if(!split)'
        '  throw std::runtime_error("P10LG incomplete split CSV write");\n if(!data||!audit)')
    s=one(s,' std::cout<<"P10DD_FULL4D_CLOSURE_OK mesh="<<mesh_name',
        ' std::cout<<"P10LG_TWO_TERM_EXPLICIT_CLOSURE_OK geometric="<<split_geometry_sum\n'
        '          <<" stress="<<split_stress_sum<<" total="<<sum.explicit_objective\n'
        '          <<" rows="<<steps*ncell<<"\\n"<<std::flush;\n'
        ' std::cout<<"P10DD_FULL4D_CLOSURE_OK mesh="<<mesh_name')
    header=DEST/BASE
    header.write_text(s,encoding='utf8')
    # Never turn this diagnostic into a solver package; recorded source must
    # remain distinct from the already-consumed P10LC native executable.
    assert not list(DEST.rglob('*.exe'))
    qa={'protocol':'P10LG_TET10_EXPLICIT_TWO_TERM_DIAGNOSTIC_SOURCE_ONLY',
        'status':'SOURCE_ONLY_PREPARED_NO_FEM_NO_GMSH',
        'base_P10DD_sha256':PIN,'instrumented_P10DD_sha256':sha(header),
        'new_sidecar':'P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv',
        'sidecar_rows_per_36x25_run':43200,
        'untouched_original_output':'P10DD_SIGNED_R_THETA_PHI_T.csv',
        'strict_closures':['cell geometry+stress equals original explicit',
                           'all-step geometry+stress equals global explicit',
                           'existing P10DD/P10V exact reference still checked'],
        'mesh_generation_attempts':0,'FEM_attempts':0,
        'caveat':'No real numbers for the two new terms until a separately approved, independently marked physical run or validated saved-state replay.'}
    (DEST.parent/'P10LG_SOURCE_ONLY_QA.json').write_text(json.dumps(qa,indent=2)+'\n',encoding='utf8')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':main()
