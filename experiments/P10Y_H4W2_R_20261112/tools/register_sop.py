#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''Safely add P10Y/H4W2 evidence pointers to current SOP Markdown files and
one reported-observation record to RUN_REGISTRY.csv. No history rewritten.
Usage:
  python experiments/P10Y_H4W2_R_20261112/tools/register_sop.py --check
  python experiments/P10Y_H4W2_R_20261112/tools/register_sop.py --apply
Do NOT use --apply until git status/diff --check were reviewed.
'''
import argparse
import csv
import io
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[1]
REPOSITORY = Path(__file__).resolve().parents[3]
MARKER = 'P10Y-H4W2-R-EVIDENCE-20261112'
RUN_ID = 'P10Y_H4W2_R_20261112_REPORTED'

ENTRIES = {
 'docs/PROJECT_STATE.md': '''## Дополнение от 2026-11-12 — P10Y/H4W2/R

Зафиксированы аналитические радиальные механические вклады в производные `D_R j6`, `D_R jpeak`, `D_R jen` для `H4W2`, `EDV/VAR`, `dt=150 с`, `steps=6`. `P10Y-H4W2-R-EVIDENCE-20261112`: `docs/STAGE3D10Y_H4W2_R_EVIDENCE_20261112.md`; исходные CSV и графики находятся в `experiments/P10Y_H4W2_R_20261112/`. Аудит разбиения: `worst_partition_rel=2.80110132644e-13`. Пространственная сходимость **не установлена**, тепловые вклады по слоям не включены. SHA использованной сборки и расположение исходного каталога запуска не подтверждены; последний сообщённый ранее HEAD не подменяет паспорт исполняемого файла.
''',
 'docs/RESEARCH_LOG.md': '''## 2026-11-12 — P10Y/H4W2/R, аналитическое разложение D_RJ по слоям

**Идентификатор доказательства:** `P10Y-H4W2-R-EVIDENCE-20261112`. Завершённый расчёт по сообщению пользователя: `H4W2`, `EDV/VAR`, `R`, `6 × 150 с`, `cutoff=5 мм`, `threads=4`; метод `ANALYTIC_TET10`, `central_fd_evaluations=0`, одна прямая задача, 18 механических сопряжённых; `wall_s=11709.7812578`. Переданы `P10Y_SHELL_SUMMARY.csv` и `P10Y_PARTITION_AUDIT.csv`, данные графиков и рисунки сохранены в `experiments/P10Y_H4W2_R_20261112/`. Погрешность алгебраического восстановления механической производной по радиальным слоям `2.80110132644e-13` (максимум по функционалам). Значительные разнонаправленные вклады компенсируются. Тепловая производная по слоям не распределена. Сходимость между сетками **не доказана**; следующий контроль — аналогичная серия `H4/R`. Точный SHA исходников и бинарника, mesh SHA, RUN_MANIFEST и папка фактического запуска не подтверждены.
''',
 'docs/VALIDATION.md': '''## 2026-11-12 — P10Y/H4W2/R: контроль радиального разложения

`P10Y-H4W2-R-EVIDENCE-20261112`: `P10Y_ANALYTIC_SHELL_PARTITION_OK`, `bins=10`, `step_shell_rows=180`, `worst_partition_rel=2.80110132644e-13`; `P10W_COMPONENT_AUDIT_OK` `worst_component_partition_rel=1.01288537627e-16`; `P10W_ANALYTIC_ADJOINT_OK` `max_mechanical_equilibrium_rel=2.21540926860e-08`, `max_thermal_equilibrium_rel=4.63456046229e-11`, `checkpoint_roundtrip_bitwise=1`. Метод `ANALYTIC_TET10`, конечные разности геометрических частных не использованы. Источник и погрешности по каждому функционалу: `docs/STAGE3D10Y_H4W2_R_EVIDENCE_20261112.md` и `experiments/P10Y_H4W2_R_20261112/data/`. **Граница проверки:** алгебраическая согласованность, а не оценка сеточной ошибки, не доказательство пространственной сходимости, не проверка полного радиального теплового вклада.
''',
 'article/EVIDENCE_REGISTER_CURRENT.md': '''## P10Y/H4W2/R — промежуточное доказательство (2026-11-12)

`P10Y-H4W2-R-EVIDENCE-20261112`: механическое пространственное разложение аналитической геометрической производной `D_RJ` для `H4W2` по 10 радиальным слоям, функционалы `j6`, `jpeak`, `jen`. Статус **проверен встроенным алгебраическим аудитом для одной сетки**, `worst_partition_rel=2.80110132644e-13`. Результат даёт профиль вклада и показывает компенсацию знаков; **не** доказывает пространственную сходимость и **не** даёт полного радиального профиля термомеханической производной (thermal shape by shell отсутствует). Источники: `docs/STAGE3D10Y_H4W2_R_EVIDENCE_20261112.md`, `experiments/P10Y_H4W2_R_20261112/data/P10Y_SHELL_SUMMARY.csv`, `P10Y_PARTITION_AUDIT.csv`, `figures/`. Номер в сквозной нумерации N не присвоен во избежание конфликта с существующим реестром.
''',
}


def newline_for(blob):
    return b'\r\n' if b'\r\n' in blob else b'\n'


def prepare_document(rel, text):
    p = REPOSITORY / rel
    if not p.is_file():
        raise ValueError('Отсутствует ожидаемый файл СОП: ' + str(p))
    old = p.read_bytes()
    if MARKER.encode('utf-8') in old:
        return p, None, 'уже зарегистрировано'
    eol = newline_for(old)
    extra = ('' if old.endswith((b'\n',b'\r')) else '\n') + '\n' + text.strip() + '\n'
    blob = extra.replace('\n', eol.decode('ascii')).encode('utf-8')
    return p, blob, 'дополнить'


def prepare_registry():
    target=REPOSITORY/'experiments/RUN_REGISTRY.csv'
    if not target.is_file():
        raise ValueError('Отсутствует общий реестр: '+str(target))
    source=EXPERIMENT/'RUN_REGISTRY_ENTRY.csv'
    with source.open('r',newline='',encoding='utf-8-sig') as f:
        row_reader=csv.DictReader(f)
        fields=row_reader.fieldnames
        vals=list(row_reader)
    if len(vals)!=1 or vals[0]['run_id']!=RUN_ID:
        raise ValueError('Ожидается ровно одна заранее определённая строка RUN_REGISTRY_ENTRY')
    with target.open('r',newline='',encoding='utf-8-sig') as f:
        existing=csv.DictReader(f)
        if existing.fieldnames != fields:
            raise ValueError('Схема RUN_REGISTRY.csv изменилась: автоматическое добавление отменено')
        ids={r['run_id'] for r in existing}
    if RUN_ID in ids:
        return target,None,'уже зарегистрировано'
    old=target.read_bytes()
    eol=newline_for(old).decode('ascii')
    output=io.StringIO(newline='')
    writer=csv.DictWriter(output,fieldnames=fields,lineterminator=eol)
    writer.writerow(vals[0])
    prefix='' if old.endswith((b'\n',b'\r')) else eol
    return target, (prefix+output.getvalue()).encode('utf-8'), 'добавить запись'


def main():
    ap=argparse.ArgumentParser(description='Безопасная регистрация P10Y/H4W2 в текущей СОП')
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true',help='проверка без записи')
    mode.add_argument('--apply',action='store_true',help='только добавить отсутствующие записи')
    args=ap.parse_args()
    changes=[prepare_document(p,txt) for p,txt in ENTRIES.items()]
    changes.append(prepare_registry())
    for p,extra,status in changes:
        print(('ADD ' if extra is not None else 'SKIP ') + str(p.relative_to(REPOSITORY)) + ' : ' + status)
    if args.check:
        print('P10Y_SOP_CHECK_OK planned_additions='+str(sum(blob is not None for _,blob,_ in changes)))
        return
    for p,blob,_ in changes:
        if blob is None: continue
        with p.open('ab') as f:
            f.write(blob)
    print('P10Y_SOP_REGISTERED_OK added='+str(sum(blob is not None for _,blob,_ in changes)))

if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError) as error:
        raise SystemExit('P10Y_SOP_ERROR: '+str(error))
