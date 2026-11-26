# P10NX — независимая приёмка сохранённой оптимизированной M13 (26.11.2026)

**РЕШЕНИЕ: `SERIALIZED_M13_GEOMETRY_ACCEPTED_NO_FEM`.** Файл MSH физически создан, сохранён, повторно открыт и независимо проверен. Пространственная сходимость и результаты FEM по M13 остаются PENDING.

## Первичный one-shot P10NW

Исследователь передал `P10NW_M13_SERIALIZED_EVIDENCE.zip` SHA256 `13640e1605e6e768efc8ac0d47c16092dafae70c6fa2e424f7d9e9bd7c66d855`, ZIP CRC3/3 PASS, внутри JSON SHA `1fd555c6145cad3eb8e0fc7c8a2d1555d13ebe55bdadcc9b432b6673aea9e7c7`, native log SHA `0b5ccb807ac6eae090e021c8436a7e671ddbee46958d9f643d97b8cc776c23d1`, exact optimized MSH2.2 `P10NW_M13_OPTIMIZED_CANDIDATE.msh` size3,166,692 B / SHA256 `cf4ff4872b82fe3fd854d0ddcb31144eb69f42e8ddce8b1954f064243cf9f4ca`.

Gmsh4.15.2 source M13 R2 pin `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`. Native exit success (`SERIALIZED_M13_REIMPORT_PASS_NO_FEM`), optimizer2.914s, `reload_pass=true`, one-shot consumed (local/global markers), FEM0, new mesh generation0 (optimizer was in-memory then MSH write). **Никогда не повторять P10NW 01; маркеры не удалять.**

## После записи/повторного открытия: канонический D-031

| Критерий | Порог | После reimport | Verdict |
|---|---:|---:|---|
| minSICN | ≥0.20 | 0.31771662817536805 | PASS |
| minSJ | ≥0.40 | 0.6418251241754643 | PASS |
| gamma | ≥0.15 | 0.24465223465436664 | PASS |
| minDetJac | >0 | 1.7448925464535246e−13 | PASS |

Все 18004 Tet10 PASS. Относительная разница между minima in-memory/reimport ≤1.04e−13; графовая биекция reimport `UNIQUE_GRAPH_LABEL_BIJECTION`, matching tetrahedra 18004/18004, missing0, extra0, edge association errors0. Max reimport coordinate residual corner8.68e−15 mm, midside9.34e−15 mm; boundary Tri6 unchanged. Пора 2338 surface nodes, radial error5.204e−18m.

## Независимый source-free Gmsh MSH2 аудит

Я распаковал оригинальные 3 файла и **самостоятельно** пересчитал SHA256 MSH — совпало с manifest. Текстовый parser (без вызова Gmsh) нашёл 26099 nodes, 18004 Tet10, 2512 Tri6; physical group1 volume18004 и поверхности2–9: 184,182,156,156,156,156,1168,354 элементов. Все group tags на месте.

Независимые аналитические Tet10 Jacobians из координат записанного MSH:
- 27QP×18004: min1.7454418527263432e−13, nonpositive0;
- 343QP×18004: min1.7449421327037438e−13, nonpositive0;
- 729QP×18004: min1.7449190754790203e−13, nonpositive0.

Пора: 1168 Tri6, 586 угловых +1752 midside nodes, 1752 edges, Euler2; каждое ребро ровно в 2 гранях, nonmanifold0, midside-edge mismatch0, максимальная радиальная ошибка5.204e−18m. Машиночитаемый паспорт `research/evidence/P10NX_M13_SERIALIZED_GEOMETRY_PASSPORT_20261126.json` независимым сравнением с native JSON PASS.

## Научные границы и следующий этап

Это **первый принятый записанный optimized M13 mesh** с точной SHA и geometry-only PASS. Не объявлять spatial convergence, shape derivative convergence, GH3/EDV физическую аттестацию или FEM GO. Следующий P10NY: подготовить source-only QA+ограниченный Windows пакет первого физического comparison M13 против M9 на **этой точной SHA**, R/EDV_VAR/ξ0/jpeak/B6=5mm/36×25s/same-mesh analytic Tet10/полное signed 4D, с новым one-shot marker и независимой проверкой FEM source, только после нужного ресурсного допуска. Не модифицировать принятую M13 и старые M9/M13 markers.
