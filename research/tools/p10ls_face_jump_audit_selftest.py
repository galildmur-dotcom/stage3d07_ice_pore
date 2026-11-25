#!/usr/bin/env python3
"""Synthetic 6-step positive and deliberately corrupt negative QA; no FEM."""
import csv
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from p10ls_face_jump_independent_audit import audit,NAME,FIELDS

def main():
    with tempfile.TemporaryDirectory(prefix='p10ls_face_selftest_') as tmp:
        path=Path(tmp)/NAME
        with path.open('w',newline='') as file:
            writer=csv.writer(file);writer.writerow(FIELDS)
            for s in range(1,7):
                for d in (1,2):
                    for ir in range(10):
                        for im in range(10):
                            for ip in range(12):
                                n=1 if (ir,im,ip)==(1,9,0) else 0
                                value=1 if n else 0
                                writer.writerow(['M9',s,s*150,d,ir,im,ip,n,
                                                 *([value]*9)])
        got=audit(tmp,steps=6,dt=150)
        assert got['rows']==14400 and got['face_pairs_per_step']==1
        lines=path.read_text().splitlines(keepends=True)
        fields=lines[3].strip().split(',')
        fields[7]='2'
        lines[3]=','.join(fields)+'\n'
        path.write_text(''.join(lines))
        stop=False
        try:audit(tmp,steps=6,dt=150)
        except RuntimeError:stop=True
        assert stop,'corrupt face count not rejected'
    print('P10LS_INDEPENDENT_FACE_QA_SYNTHETIC_PASS rows=14400 corrupt=REJECTED no_FEM=1')

if __name__=='__main__':main()
