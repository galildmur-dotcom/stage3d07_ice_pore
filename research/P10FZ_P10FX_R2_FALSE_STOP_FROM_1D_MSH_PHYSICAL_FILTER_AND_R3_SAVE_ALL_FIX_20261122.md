# P10FZ — причина P10FX R2 STOP: фильтрация одномерного MSH2 по Physical Groups

**Дата:** 22.11.2026. **Статус:** `P10FX_R2_PREFLIGHT_FALSE_STOP_DIAGNOSED`;
исправленный пакет `P10FX_R3_SOURCE_TESTED_NATIVE_WINDOWS_PENDING`, FEM=0.

## Неизменённые первичные данные

ZIP пользователя: `P10FX_PREFLIGHT_STOP_EVIDENCE.zip`, SHA256
`33c204edfaa2031090bf106ec7e10cfbf408a153b1bfde6141ff758edf4c9ebf`.
В архиве `P10FX_1D_GATE_METRICS.json`, журналы Gmsh 1D и parse-only,
причина STOP, исходный source pin; пользовательский ZIP/MSH в GitHub
публично не выкладываются.

Фактически зафиксировано:

| Часть проверки | P10FX R2 факт |
| --- | ---: |
| Готовность Gmsh 4.15.2, parse-only | PASS |
| Native `-1` returncode | **0** |
| 1D `Done meshing` | **true** |
| `Error` в логе | **false** |
| Узлов/элементов по нативному логу | 244 / 135 |
| High-order optimization | succeeded |
| Пробный `.msh` существует | **true** |
| Размер файла | **280 bytes** |
| R2 проверка `size>1000` | **FALSE** |
| 3D mesh attempts / FEM attempts | **0 / 0** |

Это *не* ошибка C¹ MathEx: в нативной памяти Gmsh успешно построена
1D сетка; исходная двойная отрицательная запись P10FW уже устранена.
Причина остановки — контроль **выходного размера** `-1` MSH2.

## Установленный механизм

Канонический CAD `sphere_pore_B6_refined.geo` задаёт `Physical
Volume` и восемь `Physical Surface`, но **не** `Physical Curve`.
При стандартной записи Gmsh сохраняет только КЭ из существующих
Physical Groups. Во время `gmsh -1` 135 1D элементов существуют
внутри модели, но не принадлежат Physical Surface/Volume и поэтому
не попадают в MSH2: остаются секции формата и метаданные на 280 байт.

Это документированное поведение **Gmsh 4.15.2**, официальный
первичный источник:
https://gmsh.info/doc/texinfo/gmsh.html — раздел `Physical groups`,
`Mesh.SaveAll`, CLI mesh option `-save_all`. Документация предупреждает,
что SaveAll в MSH2 может убрать physical tags, поэтому **его нельзя
добавлять к настоящему FEM MSH2 -3**.

## Строго локальный ремонт P10FX R3

В исходнике `P10FX_one_click_m1v.py` изменён **только безопасный
пробный вызов**:

`gmsh M1V_CANDIDATE.geo -1 -nopopup -nt 2 -format msh2 -save_all -o P10FX_1D_FIELD_PROBE.msh`

Шлюз теперь требует: native exit0, лог без Error, строку `Done
meshing 1D`, существование MSH2, размер >1000, стандартные секции
и фактические **saved_nodes>0, saved_elements>0**. Новые численные
показатели записываются в `P10FX_1D_GATE_METRICS.json`. При STOP
автоматически собирается `P10FX_PREFLIGHT_STOP_EVIDENCE.zip` без
вмешательства пользователя.

**Нативный объёмный Gmsh `-3` НЕ ИЗМЕНЁН**, флаг `-save_all` не
добавляется; физические группы для thermal/mechanical FEM сохраняются.
Исходный M0, исходная неудачная M1, CAD, компенсационное C¹ поле
и калибровочная матрица 18 зон — побайтово прежние.

Новый кандидат по-прежнему `M1V_CANDIDATE`, требование
`0.80 ≤ Veff(M1V;Z)/Veff(M0;Z) ≤ 0.85` во всех 18 фиксированных
зонах, N/S отдельно; `κ=1` как постоянная **желаемая** фактическая
доля уменьшения. Реальный curved343/729QP GO пока не выполнен.

**Старые persistent one-shot маркеры R1/R2 специально оставлены
общими с R3**; переключение версии не даёт повторного native -3.
Gmsh4.15.2 Windows native R3 на машине пользователя **ещё не
выполнялся**, поэтому новый 1D PASS и новый M1V 3D не утверждаются.

## Автономные проверки релиза

- Семь 1D mock-сценариев (чистый PASS, nonzero exit, Error, missing
  MSH, tiny MSH, *нулевые сохранённые элементы*, missing Done): PASS.
- `-save_all` проверен строго на `-1`, не на `-3`.
- SHA 12 package files и извлечённый selftest (6018 C¹ points) PASS.
- ZIP CRC PASS, Linux-native STOP PASS, изменённый README STOP PASS.

ZIP `research/packages/P10FX_R3_ONE_M1V_NATIVE_1D_SAVE_ALL_WINDOWS_20261122.zip`

SHA256 `044100578c1d4a91ce3d2c3666a147f879302d50e6324228a26b801c3a2992b3`

Размер: 33,273 B.

## Следующий научный шаг

1. Распаковать **только R3** в новую папку
   `G:\ildar\Stage3D07\P10FX_TOOLS_R3`.
2. Запустить `01_P10FX_SAFE_PREFLIGHT_ONLY.cmd`; ни одного ручного
   символа, новый native `-1` без 3D/FEM. При STOP выслать единый
   `P10FX_PREFLIGHT_STOP_EVIDENCE.zip`, **02 НЕ запускать**.
3. Только при PASS запустить **один**
   `02_P10FX_ONE_M1V_3D_ONLY.cmd`; цель — Gmsh -3 Tet10 900s/8GiB
   и 27QP QA, без FEM; передать `P10FX_M1V_MESH_EVIDENCE.zip`.
4. Независимо проверить geometry and ratio по18 3D signed зонам при
   343 и 729QP. Только после научного GO запускать свежие forward и
   same-mesh adjoint; обычный `PHYSICS_LATEST_APPROVED_R` на старой
   отказной M1 не запускать.
