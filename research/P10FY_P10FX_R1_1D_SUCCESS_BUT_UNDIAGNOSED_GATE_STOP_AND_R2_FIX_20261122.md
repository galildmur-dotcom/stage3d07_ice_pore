# P10FY — P10FX R1 1D нативно успешен, но объединённый шлюз выдал STOP

**Дата:** 22.11.2026. **Статус:** `P10FX_R1_NATIVE_1D_LOG_SUCCESS_GATE_UNRESOLVED`;
новый пакет `P10FX_R2_NATIVE_1D_METRICS_PREPARED_NO_FEM`.

## Полученные первичные свидетельства

- `P10FX_CHECK_RESULT.txt`, SHA256
  `2ae93010494857d9247136b611bdec0a94023b6f9c2f6e2c815fc4e7f5594b8c`:
  `P10FX_STOP: native Gmsh 1D MathEx evaluation FAILED`, `CHECK_EXIT_CODE=2`.
- `P10FX_GMSH_1D_FIELD_PROBE.txt`, SHA256
  `c01bc28c2ebccad0dd8d3c0103b0c3171ec53d517151bc292d37a3f1be01473c`:
  Gmsh 4.15.2, 1D `Done meshing 1D`, 244 nodes, 135 elements,
  1D wall 0.112657 s, full wall 0.187907 s, `Done writing`, high-order
  optimization succeeded, **0 text-line `Error`**.

В P10FW первый нативный `-3` останавливался ошибкой парсера
`mu--0.8` **именно во время Meshing 1D**. P10FX R1 после ремонта
завершил тот же этап до конца без MathEx ошибок. Таким образом,
**native 1D MathEx blocker устранён** по наблюдаемому журналу.

## Почему R1 выдал STOP

R1 проверял объединённое условие:

`returncode==0 AND "Error" not in log AND "Done meshing 1D" in log AND
probe.is_file() AND probe.stat().st_size>1000`.

По журналу выполнены текстовые пункты `Error` и `Done meshing 1D`;
он сообщает, что Gmsh записывал файл. Однако R1 **не сохранил**
проверенный код возврата процесса, фактическое существование файла
в момент Python-проверки и его размер. Временный `.msh` был удалён
вместе с `TemporaryDirectory`. **Нельзя доказать точную причину STOP**:
даже отсутствие `Error` не доказывает `returncode==0`. Поэтому
принудительно обходить STOP или разрешать `-3` нельзя.

## P10FX R2: исправление наблюдаемости без ослабления защиты

Релиз `P10FX_R2_ONE_M1V_NATIVE_1D_METRICS_WINDOWS_20261122.zip`
в новой папке `G:\ildar\Stage3D07\P10FX_TOOLS_R2`.

Без изменений: исходные M0, M1, CAD, физическая цель `0.80 ≤
Veff(M1V,Z)/Veff(M0,Z) ≤ 0.85` **в каждой** из 18 фиксированных 3D
зон, C¹ компенсационное поле (6018 точек, математика P10FW=P10FX,
разница 0), ограничение `one -3`, 900 s, private 8 GiB, output 2 GiB,
27QP, **FEM=0**.

Изменено: `01_P10FX_SAFE_PREFLIGHT_ONLY.cmd` теперь после нативного
`gmsh -1` сохраняет `P10FX_1D_GATE_METRICS.json` с **пятью раздельными
результатами**: native exit code, наличие `Error`, `Done meshing 1D`,
факт существования файла MSH, точный размер и сигнатуры MSH2.2.
При отказе автоматически формирует
`LOCAL_RUNS/P10FX_PREFLIGHT_.../P10FX_PREFLIGHT_STOP_EVIDENCE.zip`.
Состояние `PASS` выдаётся только если **все** проверки выполнены.
Только после PASS разрешена одна защищённая 3D-генерация.

R2 **использует те же `LOCAL_RUNS/P10FX_LOCKS/M1V_FROM_<M0>.json`
и `%LOCALAPPDATA%/Stage3D07/P10FX_R1_M1V_<M0>.json`, что R1**.
Иначе смена выпуска могла бы обойти ранее израсходованный one-shot.
M1V никогда не перезаписывается; новую `.geo` и `.msh` создают только
если пути отсутствуют.

Проверено автономно:

- Шесть mock-режимов 1D: PASS, ненулевой exit при чистом логе,
  `Error`, отсутствие MSH, слишком маленький MSH, отсутствие Done;
  всё верно и без вызова `-3`/FEM.
- Исходное C¹ поле: 6018 точек max diff `0.0` от P10FW.
- SHA-pin 12 файлов, ZIP CRC, извлечённый `--selftest`, Linux-native STOP,
  tamper STOP — все PASS.
- Содержимое пользовательских логов публично **не опубликовано**;
  опубликованы только дайджесты и научные диагностические выводы.

ZIP SHA256:
`01a1f5a24e15f28c0c37af8c42c5ad167b49318dde7732176f7d79e17a403b46`,
32,296 B.

**Следующий эксперимент:** в новую папку распаковать R2, запустить
`01` (нативный Gmsh `-1` безопасен; 3D=0). При `STOP` выслать **один**
`P10FX_PREFLIGHT_STOP_EVIDENCE.zip`; до его анализа `02` запрещён.
При `PASS` разрешён строго один `02`, затем прислать
`P10FX_M1V_MESH_EVIDENCE.zip`, независимый curved343/729QP аудит
18 зон и только после GO свежий forward+same-mesh adjoint.
