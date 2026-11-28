# P10NS R1 AUDIT_ERROR, исправлен P10NS R2 (26.11.2026)

## Первичное исполнение R1

Получены оригинальные `P10NS_VOLUME_TOPOLOGY_QUALITY_RESULT.json` и `P10NS_GMSH_VOLUME_LOG.txt`. Source M13 R2 SHA256 `57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c`. Статус **AUDIT_ERROR**, не mesh FAIL. R1 в Gmsh4.15.2 оптимизировал strictly in-memory HighOrderElastic за 2.7630s, подтвердил boundary Tri6 preserved, затем остановился на `ValueError('nonunique coordinate match: old node 5031, candidates 0')`. До/после анализ Jacobian НЕ завершился; FEM0, mesh generation0, M13 R3 no, markers0.

Показанные в R1 before_quality отрицательные `min_detJ~-3.877e-6`, `nonpositive_qps=2,385,133` **НЕ ПРИМЕНИМЫ К ГЕОМЕТРИИ** из-за ошибки аналитического анализатора: Gmsh MSH2 Tet10 элемент11 использует последовательность midsides `01,12,20,03,23,13`, тогда как наш R1 ошибочно пользовался `01,12,20,03,13,23`. Перепутаны последние два узла. Это конкретный диагностический дефект, не доказанный дефект сетки. Original R1 сохраняется, его кнопку не запускать повторно.

## Независимое подтверждение исправления на той же исходной M13

Новый отдельный source-only текстовый MSH2-parser `research/tools/p10ns_msh2_source_preflight.py` загрузил точный raw M13 R2: 26 099 nodes, 18 004 Tet10, все six edge mappings nearest midpoint agree (mismatch0; max curved offset1.5767865e-4m, поэтому **нельзя** требовать совпадения midside с точным аффинным midpoint).

После исправления edge ordering независимый исходный Jacobian audit:
- 27 QPs: min detJ = `1.6528481910907702e-13` m³, nonpositive0;
- 343 QPs: min detJ = `1.6522055662689835e-13` m³, nonpositive0;
- 729 QPs: min detJ = `1.6521875341449308e-13` m³, nonpositive0.

Source synthetic affine detJ1/injected negative, coordinate-remapped corner topology PASS. Это **не after-optimization** и не математическая гарантия положительности во всём объёме.

## Второе методическое ограничение: внутренние угловые узлы

R1 точная биекция corner coordinates с допуском 1e−12m не смогла сопоставить старый node5031 после HighOrderElastic. Возможны перемещение внутренних угловых узлов и/или изменение перенумерации. Нельзя объявить volume topology broken без дальнейшего доказательства. R2 не навязывает однозначную карту: отдельно измеряет closest-point distribution старых/новых угловых узлов; если строгая биекция недоступна, volume topology маркируется `INDETERMINATE`, а корректная sampled quality before/after всё равно выдаётся.

## Новый ограниченный R2 Windows пакет

Новый `P10NS_R2_M13_TET10_VOLUME_AUDIT_WINDOWS_20261126.zip`, seven files, SHA-pinned M13 R2, separate folder, CMD `01_P10NS_R2_RUN_VOLUME_AUDIT.cmd` без PowerShell и ввода. Перед native запуском выполняет независимый MSH2+27/343/729 source preflight (при отрицательном detJ STOP). Далее Gmsh HighOrderElastic strictly in-memory, source/after detJ, corner-cloud movement, boundary Tri6, volume topology if provable. ZIP CRC7/7, local source preflight PASS, synthetic selftest PASS. Native Windows R2 **PENDING**, FEM0, M13 R3 no.

Вернуть `P10NS_VOLUME_TOPOLOGY_QUALITY_RESULT.json` и `P10NS_R2_GMSH_VOLUME_LOG.txt` (при STOP хотя бы лог). Ни старые marker ни R1 outputs не изменять. По результатам отдельно оценивать D-031 Gmsh minSJ/minSICN/gamma и доказательность объёмной топологии.
