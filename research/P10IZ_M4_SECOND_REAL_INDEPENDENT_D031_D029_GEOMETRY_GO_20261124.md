# P10IZ — независимая D031/D029 проверка второй реальной M4: GEOMETRY GO (24.11.2026)

## Происхождение и ограничения

Приватный возврат исследователя: `P10IY_R1_M4_REPAIR_UNVERIFIED_EVIDENCE.zip` (содержит one-shot marker, guard/worker JSON, Gmsh log и mesh). Модель/PDE/FEM не запускались в рамках этой проверки; расчёт исключительно read-only. Сырая сетка и ZIP не публикуются в GitHub.

Guard: `WORKER_FINISHED`, exit 0, wall 12.09 s, native Gmsh 4.15.2, one-shot consumed=true, one new mesh3D attempt, FEM=0, accepted_M4=false в исходном отчёте исполнителя (до независимой проверки). Worker: 10,399 Tet10, 310 pore Tri6, 10 embedded CAD points. Mesh SHA-256 совпадает с guard и worker: `a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c`.

Pinned accepted M3 SHA-256: `3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a`. Первая неудачная M4 P10IV (`00244c5f...`) не заменяется задним числом: это новая отдельная P10IY попытка.

## D031 — all curved Tet10, фиксированные ранее пороги

| Test | Actual M4 | Gate | Result |
|---|---:|---:|---|
| Gmsh minSICN minimum | 0.27864492231308763 | ≥0.20 | PASS |
| Gmsh minSJ minimum | 0.4424872180114679 | ≥0.40 | PASS |
| Gmsh gamma minimum | 0.18671604742264758 | ≥0.15 | PASS |
| Gmsh minDetJac minimum | 3.900696960316687e−12 | >0 | PASS |
| Independent min detJ (27 QP) | 4.061288199266704e−12 | >0 | PASS |
| Independent min detJ (343 QP) | 3.940148984443223e−12 | >0 | PASS |
| Independent min detJ (729 QP) | 3.925605751092635e−12 | >0 | PASS |
| CAD volume relative closure, 729QP | +8.57013149335728e−9 | abs ≤1e−6 | PASS |
| Surface physical tags | [2,3,4,5,6,7,8,9] | [2..9] | PASS |

Pore Tri6=310. All quality arrays have zero nonpositive elements. Neighbour q is a D030 *diagnostic*, not a geometry gate: all pairs p95=2.4823, max=6.9593; near polar pairs p95=2.4265, max=4.5213.

## D029 — реальные физические приполюсные объёмы по 729QP

На идентичных заданных физических областях `near_p0_N` и `near_p0_S` (d≤0.5 mm, |μ|≥0.8), отношение Veff(M4)/Veff(M3):

| Region | M3 Neff | M4 Neff | Ratio 729QP | Ratio 343QP | Reduction | Target |
|---|---:|---:|---:|---:|---:|---|
| N | 140.08608702945 | 216.05094342048 | 0.64811944865 | 0.64673588559 | 35.1881% | PASS [.50,.75] |
| S | 185.59445668277 | 279.18015011967 | 0.66508663152 | 0.66502957182 | 33.4913% | PASS [.50,.75] |

QP 343→729 ratio drift N≈0.2135%, S≈0.0086%; Neff≥30 обеих областей. Independent max relative 343/729 Veff drift over supported groups 0.7627% (diagnostic). Both target regions PASS.

## Формальное решение

**P10IY M4 GEOMETRY_QUALITY_GO (D031 PASS), ADAPTATION_TARGET_GO (D029 N/S PASS).** Новая M4 геометрически принята для подготовки следующего этапа. Это **не** физический результат, не оценка пространственной сходимости D_R J_peak, и не разрешение автоматически запускать FEM. Нельзя повторять израсходованный P10IY one-shot marker; не запускать Gmsh вновь ради этого статуса. Следующий этап: pinned source-only preflight для одного M4 direct+adjoint 4D FEM на Windows, затем отдельное решение исследователя о запуске, после получения evidence независимая проверка signed 4D closure и M3→M4 (особенно полярная компенсация). Прежние M2/M3 данные неизменны.

Повторяемость: независимый сканер `p10hv_independent_scan.py` (MSH2 Tet10, 27/343/729 QP, CAD volume, supported physical regions); аудит `p10ic_tet10_quality_audit.py` + Gmsh Python 4.15.2 `getElementQualities`. Нет новых сеточных генераций и FEM в независимой проверке.
