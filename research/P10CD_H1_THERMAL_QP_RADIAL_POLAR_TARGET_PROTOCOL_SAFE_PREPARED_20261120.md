# P10CD — H1: адресная радиально-полярная локализация тепловой производной формы, подготовка без FEM

**Дата:** 20.11.2026. **Состояние:** `P10CD_H1_READINESS_TOOL_PREPARED_NO_FEM`, Windows readiness **PENDING**, physical H1 **NOT_AUTHORIZED**. Это научный протокол и безопасная кнопка проверки входов, а не новый результат H1.

## 1. Зачем опыт, если P10AW H1 уже существует

P10CC установил, что глобальные аналитические производные H0→H1 **уже измерены**: при `R`, `EDV_VAR`, `ξ=0`, 6×150 s, B6 cutoff 5 mm `D_R jpeak` H0 **3.167691851413873 m⁻¹**, H1 **2.506815720514308 m⁻¹**; mechanical −0.664556485, thermal +0.003680354 m⁻¹. Повторить H1 только ради нового global `D_R jpeak` **не требуется**. Однако P10AW H1 не выгружал *послойную тепловую форму* — по 10 радиальным ×10 полярным зонам на каждом шаге с отдельной верхней Robin границей. P10CA H0 уже выгружал её и показал near-wall 0–2 mm **−0.0027761 m⁻¹**, 2–5 mm **+0.06915565 m⁻¹**, за B6 5 mm support нет вклада скорости формы; интегральная thermal сумма **0.06637955208 m⁻¹**. Сеточная устойчивость такой знакопеременной локализации пока не проверена.

**Один вопрос P10CD:** при переходе на H1 сохраняются ли знак, радиально-полярное размещение и баланс локальной thermal компоненты `D_R jpeak` (не смешивая с mechanical `D_R jpeak`)? Не приписывать B6 outer zero всепространственной сходимости. Для full spatial convergence нужно дальнейшее исследование, двух сеток недостаточно.

## 2. Реальная кодовая возможность (прочитано, без изменения исходников)

В точно ранее испытанном P10CA/P10BX исходнике `stage3d10w_analytic_adjoint.cpp` CLI требует **явно** `--mesh MSH --out NEW_DIR` и читает mesh из аргумента; в `p10ca/CMakeLists.txt` H0 — только имя цели `p10ca_h0_analytic_qp`, а не жёсткая H0 фиксация в solver. P10BX opt-in define `STAGE3D10BX_THERMAL_QP_DIAGNOSTIC=1` в `stage3d10p_partial_audit.cpp` сохраняет исходную CSR сумму, собирает **один jpeak QP snapshot на каждый шаг**, формирует `P10BX_THERMAL_QP_STEP_BINS.csv` и `P10BX_THERMAL_STEP_AUDIT.csv` с жёсткой numerical CSR/QP проверкой. `stage3d10bw_thermal_qp_partition.hpp` использует 4×4×4 curved Tet10 QP, B6 radial bins 0,.02,.05,.1,.25,.5,1,2,5,15 mm и 10 polar bands; top Robin отдельно. Нет H0-specific switch внутри контракта QP. Последний реальный Windows P10CA EXE SHA 

`17c31f426245317271245e340d68fa5de1e4eb144b7be986167505e14cbed924`

и именно этот EXE прошёл P10CB R2 `--help`/`--selftest` с настоящим native exit0/0 (child-only `C:\mingw64\bin`). Это **инженерное обоснование возможности** H1, не свидетельство испытанной H1 QP физики. Перед первым H1 проверяются точные файлы и путь к существующему EXE; **новая сборка не нужна** при совпадении SHA. Старое `Start-Process.ExitCode` не использовать для нового заключения о native exit.

## 3. Точно заданный H1 и размер работы

| Поле | H0 P10CA (измерено) | H1 P10AW (существующее) / P10CD (предполагается) |
|---|---:|---:|
| Mesh | `G:\ildar\Stage3D07\meshes\H0.msh` | `G:\ildar\Stage3D07\P10M_MESHES\H1.msh` |
| Mesh SHA-256 | `e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8` | `394ee339073fe6eacfd58c549ad0b0218a9bdadf8f36a2ca435a1ca3fad0598d` |
| Nodes / Tet10 / pore Tri6 | 10845 / 7388 / 136 | 27757 / 19412 / 282 |
| Median pore edge | 0.452373 mm | 0.322666 mm |
| Thermal volume QP / step | 472832 | **1 242 368** (=19412×64) |
| Thermal volume QP, 6 steps | 2 836 992 | **7 454 208** |
| Ожидаемые local/audit rows | 606 / 6 | **606 / 6** (100 radial/polar +1 top Robin на каждый из 6 шагов) |

H1 исходный Gmsh format/счётчики, top Tri6 count (требуется >0), точная mesh SHA, original Git SHA/status и pinned EXE SHA должны быть **вновь проверены без изменения файлов** перед любым физическим разрешением. Исторические P10AV preflight и P10AR geometry согласны по H1 SHA, но raw H1 `.msh` пока недоступен для локальной перепроверки в этой среде. Запрещены автоматическая замена сетки и смешивание H0/H1 между прямой/сопряжённой задачами (P10AO).

## 4. Предварительная оценка ресурсов и будущие границы

**Наблюдаемое:** прежний P10AW H1 375.357 s (**6 мин 15 с**), history 0.281 GiB и preflight state buffers 0.469 GiB; прежний P10CA H0 104.424 s, наблюдаемая память процесса 0.895 GiB, размер результатов 0.145 GiB. H1 имеет 2.63× Tet10 и 2.56× узлов, прошлый H1 runtime ~3.60× H0. Память именно нового H1 QP-процесса **не измерена**.

**Оценка, не гарантия** для будущего единственного H1 QP: ориентировочно **8–15 минут**, память **до 6–8 GiB** (ориентир), новые выходы **около 0.4–1.0 GiB**. Предлагаемые *будущие* guard limits (только для согласования, ещё не внедрены и не утверждены): 20 минут wall, 8 GiB наблюдаемого private process memory, 1.5 GiB новых файлов; требовать перед запуском минимум 4 GiB свободного диска и 16 GiB свободной RAM, 4 OpenMP threads. Опрос памяти и диска не является строгим мгновенным аппаратным пределом. Нельзя приписывать этот прогноз кнопке readiness, которая ничего не решает.

Предполагаемый **только будущий** ввод EXE после отдельной физической санкции (сейчас НЕ запускать):

```text
Qt/CMake target: p10ca_h0_analytic_qp (существующий ранее собранный EXE)
--mesh "G:\ildar\Stage3D07\P10M_MESHES\H1.msh" --out "<NEW_ISOLATED_OUTPUT>" --steps 6 --dt 150 --mode R --cutoff-mm 5 --threads 4
```

Существующий EXE расположен по ранее проверенному пути `G:\Downloads\P10CA_H0_ONE_RUN_R1_20261120\P10CA_RESULTS_20261120_151200_8420\build\p10ca_h0_analytic_qp.exe`. Точная новая output директория и реальная команда с лимитами будут заданы только после получения safe readiness и отдельного разрешения. Никакой `--preflight` solver, повтор H0, H2 или новая GH3 кампания сейчас не предусмотрены.

## 5. Подготовленная безопасная проверка P10CD R1

Архив `tools/P10CD_H1_READINESS_R1_20261120.zip`, SHA-256 **`929098e2c20c1fa360087c9c923df1ef8210c45961d90a1743a14c762c02a2f3`**, ZIP 4/4 PASS, contains three files under one root. PS1 **ASCII CRLF без BOM**, SHA-256 **`1e2bda6becfa03480c646bf9d1a4c34815f85ce7f615bc3730143fa257f64db9`**. Стартовый файл `01_P10CD_H1_SAFE_READINESS.cmd`, одна кнопка.

Эта кнопка **только читает** original Git HEAD/status/fingerprint (ожидаемые `90fd2559…`, 0/7/4, `bb376579…`), H1 mesh SHA+счётчики Gmsh 2.2 ASCII, existing EXE SHA, существование MinGW runtime directory, ожидаемое число QP/rows; повторно проверяет исходные хеши и Git после. Создаёт **только** отдельный рядом с кнопкой `P10CD_RESULTS_*/P10CD_RESULT.txt` + `P10CD_EVIDENCE.zip` (1 текст внутри). Никакого запуска EXE, safe selftest, CMake, FEM, preflight, Git write или изменения host PATH. При любом mismatch — `P10CD_STOPPED_NO_FEM`, заменить файлы нельзя. Оценка safe проверки **10–60 секунд**, менее 1MB нового диска, низкий объём ОЗУ.

Локально подтверждено: точный исходный инструмент и C++ интерфейс просмотрены, forbidden-solver static gate PASS, ZIP CRC 4/4 PASS, PS1 и CMD ASCII CRLF, hashes выше. **PowerShell 5.1/реальный H1 Windows здесь не запускались**; P10CD Windows readiness **PENDING**. Один вход от исследователя: **один `P10CD_EVIDENCE.zip`** либо STOP. Ни при каких результатах readiness не запускает физический H1.

## 6. Что будет считаться доказательством после отдельного разрешения H1

Будущая единственная физическая попытка только для локальной thermal QP диагонали требует: exact original git SHA/status, mesh/exe hashes до/после, isolated output, child-only MinGW PATH, bounded `.NET Process` с **native ExitCode=0 до Dispose**, complete `P10W_ANALYTIC_ADJOINT_OK`, `P10BX_THERMAL_QP_INTEGRATED_OK mesh=H1 ... steps=6 bins_per_step=100 top_robin_rows=6 exported_rows=606 original_gradient_unchanged=1`, 606 step bins +6 audit и global components 3+3+18; независимые row counts, per-step QP/CSR tolerance, per-shell signs, zone integrals, polar cancellation, per-step and all-step sums. Сравнить с ранее опубликованным H1 `D_R jpeak=2.5068157205143082 m⁻¹` и thermal `0.070059905957975052 m⁻¹` **не приписывая побайтовую идентичность старому EXE**. Результат без проверенного native exit0 именовать числовым аудиторским свидетельством со статусом STOP, не completed native run.

Наконец, двухсеточный H0–H1 thermal radial/polar audit не докажет асимптотической spatial convergence; полный temporal convergence остаётся открытым. **До новой санкции physical FEM runs=0.**
