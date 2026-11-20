# P10BY — подготовительный source gate и многократный temporal QP unit перед первым H0

**Дата:** 20.11.2026. **Статус:** завершённый source-level/native pre-H0 этап. Физические расчёты и Windows-действия не выполнялись. CMake-проект только предложен, configure не проверен.

## 1. Один исследовательский вопрос

Можно ли надёжно провести повторяемую проверку локального теплового `jpeak`-вклада за **всю временную историю** и обнаруживать случайную подмену точных исходников, *до* разрешённого H0? Исходная P10BX проверка охватывала 7 независимых операторных конфигураций и одну отрицательную проверку, но не тестировала серию сумм `n=N..1`. Сам физический `p10n::reverse_scan` всё ещё не запускался.

Целевые контракты: для каждого синтетического `n`
\[
 Q_n^{\rm all}=\sum_{i=0}^{99}(Q_{i,n}^{M}+Q_{i,n}^{K})+
 Q_n^{\rm top\ Robin}
 =\psi_n^\top\bigl[M'(\theta_n-\theta_{n-1})+
 \Delta t K'\theta_n-\Delta t b'T_{\rm amb}(n)\bigr],
\]
и `sum_n(Q_n)=sum_n(CSR_n)`. `theta_n` и `psi_n` задаются явно; **ни одно** прямое или сопряжённое тепловое уравнение в тесте не решается. Использованы exact `P10L` и прежний `P10BW/P10BX` contract, без perturbation shape FD в вычислении производной.

## 2. Сверенные исходники и изолированность

Последние проверенные remote HEAD при начале этапа: research `46702581fd01e1ac971bfbdbc976fd70cb77a5b0`, `master` `7fec72ab7353e1a876d6461d0b30e546b33ee5ee`. Сохранена отдельная source history exact `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`. Точный байтовый архив 35 `src/`+`tests/` исходников, два опубликованных review-only предложения P10BW и P10BX. Новая `P10BY_PINNED_SHA256.txt` и read-only проверяющая программа независимо сверили **35 SHA-256 оригиналов + 5 SHA-256 предложений**: `P10BY_READONLY_SHA256_GATE_OK original=35 proposal=5 total=40 negative_memory_control=1 filesystem_writes=0`, native exit 0. Отрицательный checksum контроль испортил только байты в памяти.

Важный риск выявлен при независимой проверке: простой `#include "stage3d10p_partial_audit.cpp"` при порядке `-I pinned/src -I proposal/src` компилировал **оригинальный P10P**, игнорируя исследовательский hook, хотя выдавал успешный dependency selftest. В исправленном изолированном P10BY unit-only entry используется строго `#include "src/stage3d10p_partial_audit.cpp"` относительно P10BX proposal root. Проверка `g++ -MM`: `proposal_P10P=true`, `pinned_original_P10P_used=false`, `P10BW_header=true`. Это реальный предотвращённый риск *ложной аттестации*, а не ошибка результата P10BX; физические Windows файлы не менялись.

## 3. Native результаты (первичные, без FEM)

Сборка в Linux `GNU C++ 14.2`, C++20, `-O2 -Wall -Wextra -Wpedantic`, выход 0. Отдельный `P10BY_temporal_thermal_qp_native_unit.cpp` собран без предупреждений. Для `mode=R` и отдельно искусственно движущейся удалённой Robin грани `mode=top` проверены четыре полные временные сетки `6×150`, `12×75`, `18×50`, `36×25` с фиксированным горизонтом 900 с. Во всех случаях использованы две криволинейные Tet10 и Tri6 **синтетического** unit, 64 тепловые QP на каждый Tet10 и 16 на удалённую Tri6.

| Показатель | Результат |
|---|---:|
| Синтетических серий | **8/8** |
| Контрактов thermal step | **144** |
| Эквивалентных строк `100 radial×polar + top Robin` | **14 544** |
| Max `abs(QP−CSR)` по одному шагу | **5.107025913276e−15** |
| Max `abs(sum bins+top−QP)` | **0** (порядок суммирования одинаковый) |
| Max `abs(sum_n QP−sum_n CSR)` | **7.105427357601e−15** |
| Удалённая Robin для `R` | нуль во всех 4 сериях |
| Удалённая Robin при `top` | ненулевая, `L1≈0.199–0.252` |
| Искусственные искажения `D.mass` и `D.robinload` | **2/2 STOP** |
| Память удерживаемых `Audit` при 6/36 шагах | **29 376 / 176 256 байт** |

`P10BY_TEMPORAL_THERMAL_QP_NATIVE_UNIT_OK series=8 steps=144 qp_csv_rows=14544 corruption_stops=2/2 ... physical_FEM_runs=0 thermal_solves=0 mechanical_solves=0`. Запуск продублирован; оба stdout побайтово одинаковы.

Отдельная **полная P10P компиляция** из исправленного `P10BY_unitonly_entry.cpp` с opt-in макросом: native `g++ -O2` exit 0, `P10I_PRODUCTION_ADJOINT_OK` exit 0. Это compile/link проверка актуального `reverse_scan`, но unit-only main не предоставляет ни `--mesh`, ни `--out`, и **не вызывает** этот reverse на H0. Старые compiler warnings из не затронутых исходников остались. Повторный stdout совпал.

Дополнительный проект `CMakeLists.txt` с двумя **только unit** target и SHA-gate подготовлен, но при вызове `cmake -S ...` получен `/bin/bash: cmake: command not found`, native exit 127. Отсутствующий компилятор конфигурации — **инфраструктурный STOP на проверку самого CMake**, не провал C++ или FEM. Нельзя называть Windows/CMake clean build доказанным. Публикуемый CMake — только review proposal до отдельного теста с реальным CMake/MinGW.

Точные stdout, SHA-gate, include graph, resource plan и RESULT — `research/evidence/P10BY_PREH0_NATIVE_20261120/derived/`.

## 4. Ресурсная оценка первого H0 (план, не измерение P10BY)

Первоисточник геометрической статистики: `samples/P10M_H0_DT150.csv`, Git blob `b0fc9be2a4572609cd1ee40c4d455748d6775755`: H0 `10 845 nodes`, `7 388 Tet10`, `136 pore Tri6`; последние **не являются** числом верхних Robin Tri6. Архивный P10W/H0/R `steps=6`, `dt=150 с`, `threads=4`, `EDV/VAR`, `ξ=0` занял `109.7713738 с` (в `docs/PROJECT_STATE.md`); отдельный P10S/M04 H0/y20 занял `117.7749985 с`, но имеет иную цель.

В одном новом H0 диагностическом R:

- объёмная тепловая QP-работа: `7388 × 64 × 6 = 2 836 992` QP (ещё `96×N_topTri6` верхних, где `N_topTri6` пока **UNKNOWN**);
- ожидаемый формат: **606** `P10BX_THERMAL_QP_STEP_BINS.csv` data rows и **6** `P10BX_THERMAL_STEP_AUDIT.csv` data rows;
- удерживаемый новый массив `Audit`: `6×4896=29376` байт (измеренное `sizeof`), плюс временные вектора `O(nodes)` и full production-history memory;
- ориентир полного runtime **2–6 мин**, резерв **10 мин** — лишь *оценка низкой уверенности*, дополнительный проход на пользовательском i7-7700K **ещё не измерен**;
- предварительный лимит для согласования **8 GiB RAM** и **1 GiB нового диска**, не подтверждённые измерением peak RSS. Машина: i7-7700K 4C/8T, 64 GiB RAM. В прошлой H0 Stage10M `estimated_history_gib≈0.107`; это не peak RSS.

Никаких масштабных проб H2, сеточного анализа или переноса GH3 из детерминированного `ξ=0` не предполагается без отдельного решения. Физическая сетка H0 и historical `P10BE_H2.exe` здесь не читались.

## 5. Минимальный будущий H0-протокол — только после отдельного согласования

**Цель:** получить `D_R jpeak` thermal radial/polar shape по времени для одной H0 на *той же* сетке прямой/сопряжённой задачи (D-012). Сравнить локальную `100+top` сумму с original CSR по каждому шагу и total `jpeak`. Пока это **проект эксперимента**, не команда пользователю.

1. Непосредственно перед любым Windows-действием получить новый `git branch/HEAD/index/status`, имя/хеш точной H0.msh, CMake generator/GNU13.1 flags, SHA-256 строящегося binary; сохранить 7/4 dirty files. Не `git switch/pull/merge/clean/reset/stash`. Изолированный source checkout и build **вне** `G:\ildar\Stage3D07`, с checksum 35+5.
2. На изолированном Windows MinGW проверить только два unit target P10BY, затем source-level CMake и `--selftest` диагностической P10W цели. Даже `stage3d10w_analytic_adjoint --preflight` в текущем исходнике вычисляет `H::solve_forward`, поэтому **не запускать** его до разрешения физического FEM.
3. После отдельного явного утверждения времени/ресурса/точной цели/аргументов выполнить ровно один `H0, R, EDV/VAR, ξ=0, dt=150, steps=6, cutoff=5 mm, threads=4`. Не модифицировать историю, вычислять аналитические Tet10 shape derivatives, никакой центральной FD в production. Каталог `--out` создать новый; проверить, что не существует заранее.
4. Критерии приёмки: штатный `P10W_ANALYTIC_ADJOINT_OK` exit0 с невязками `mech<1e−6`, `thermal<1e−7`; P10BX step audit (6) и QP rows (606), 64 QP/Tet10, 16 QP/top Tri6, `abs(QP−CSR) <= 1e−10+1e−8 scale` по шагам, allstep к исходной `thermal`. `top Robin` для R ожидать ≈0, но **проверить на реальной сетке**; ненуль не «обнулять», разбирать mesh/velocity. Не делать научный вывод из неподтверждённого STOP.
5. Вернуть минимально 4 файла: `P10BX_THERMAL_STEP_AUDIT.csv`, `P10BX_THERMAL_QP_STEP_BINS.csv`, `P10W_ANALYTIC_ADJOINT.csv`, один `P10BZ_RESULT.txt` с фактическими SHA, native exit, стендовыми resource/time данными и манифестом/вложениями при наличии. Не запрашивать полный `.msh`, `.exe`, `.bin`, checkpoint.

Точная Qt цель и командная строка физического runner **пока не объявлены**: P10BY поставляет только безопасные unit targets, а P10BX не интегрирован в пользовательскую CMake/Windows ветку. Перед её выпуском нужен actual Windows SHA и тест новой clean компиляции. В доступном окружении нет физической H0 mesh, поэтому этот эксперимент нельзя считать завершённым.

## 6. Научная граница и следующий вопрос

Положительный P10BY показывает *алгебраическую* устойчивость многократного QP/CSR контракта к четырём дискретизациям времени на заданных synthetic `theta_n,psi_n`, работу detector STOP и точную защиту source include-графа. **Он не измеряет порядок временной сходимости физической задачи** и не обосновывает перенос синтетического разбиения на реальные напряжения/температуры. В полной физической `D_R jpeak` остаются механическая/EDV история, стохастика и mesh dependence. `SPATIAL_CONVERGENCE_NOT_PROVEN`; исторический P10BE_H2 EXE SHA `UNKNOWN`.

**Следующий P10BZ:** после новой отдельной санкции исследователя — сначала безопасная Windows clean source/MinGW **unit-only** проверка с текущим SHA/index, затем отдельное решение об одном H0 physical diagnostic. Никаких H2/многосеточных запусков, Windows patch/One Click или изменений `DECISIONS.md` P10BY не выполнял.
