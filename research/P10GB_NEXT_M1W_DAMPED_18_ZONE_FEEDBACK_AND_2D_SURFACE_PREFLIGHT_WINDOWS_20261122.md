# P10GB — следующий кандидат M1W после реальной M1V STOP

**Дата:** 22.11.2026. **Статус:** `M1W_SOURCE_ONLY_PACKAGE_READY`,
native Windows `-1/-2/-3` пока **не выполнялись**, FEM0,
scientific mesh GO **не выдан**.

## Исходный воспроизводимый результат P10GA

Реальная raw M0 SHA `926a9c90...` и M1V SHA `c3f69d3d...`:
M1V Gmsh exit0, 9687 Tet10, 14169 nodes, curved detJ>0
при 27/343/729QP. Глобальное `Veff(M1V)/Veff(M0)=0.825023`
(уменьшение на17.50%). Строгий 18-zone fixed 3D тест:
**7 PASS, 11 FAIL**, q729 min0.640695 max1.080229,
max |q343−q729|=0.007347. Предыдущая исходная M1 — 5/18 PASS.

Северный полюс в 0–100 мкм: ratio1.080 и Tri6 polar north
17 (M0:18). Южный polar taper 0–100 мкм: ratio0.641.
Прямая (недемпфированная) инверсия прошлой локальной q под Gmsh
оказалась недостаточно надёжной из-за нелинейной топологии и
северо-южной связи через поверхность. Подробности:
`research/P10GA_REAL_M1V_27_343_729QP_ALL_VOLUME_UNIFORM_STOP_20261122.md`.

## Новый источник поля M1W (от канонической M0)

Пакет `P10GB_R1_DAMPED_C1_M1W_SURFACE_GATE_WINDOWS_20261122.zip`
сохраняет полную геометрию M0 и размерный канонический Field3.
Вход — **реальные 18 signed физические зоны 729QP M1V**, старый
независимый M1 источник, с SHA-pin обоих наборов и M0/M1/M1V GEO+MSH.

Схема обновления математической функции без использования FEM:

`L_new(r,mu) = C1_interp_18[log(0.825/q_M1_old) + beta*log(0.825/q_M1V_real)]`

`h_new(x) = h_M0(x)*exp((log(0.8)+L_new(x))/3)`, `beta=0.40`.

Два индекса signed mu/радиальных зон упорядочены от south к north,
радиальные узлы прежние (0.1,0.3,0.5 мм), угловые `mu` прежние
(-0.8,-0.6,-0.2,+0.2,+0.6,+0.8). При `C1_interp` производные
не имеют скачков на границах интерполяционных полос.

**Проверено математически:** 6018 точек source field, max abs/rel
diff2.29×10⁻¹⁶; maximum `|h_M1W/h_M1V−1|=0.035301` (3.53%)
по проверочным точкам, то есть шаг обратной связи демпфирован;
номинальная `h³_M1W/h³_M0` в тестовой выборке0.604..0.897.

Принцип: фактический желаемый коэффициент объёма **0.825 ВЕЗДЕ**;
`κ=1` везде, пространственная компенсация относится только к
неточности Gmsh remeshing. **Не утверждается, что M1W достигнет
0.80–0.85**: единственный способ — 18-zone raw MSH 729QP после
реального Gmsh. Никакие физические производные или `κ(x)`
из реального forward/adjoint пока не использованы.

## Двухступенчатая защита до единственного Gmsh -3

Новая `01_P10GB_PREFLIGHT_1D_2D_ONLY.cmd`:

1. Контроль immutable source SHA, canonical M0/M1/M1V/CAD, 6018 точек.
2. Gmsh4.15.2 `-parse_and_exit`, затем native `-1 -save_all`
   для фактической компиляции MathEx и 1D MSH2 с >0 узлов/элементов.
3. Native `-2` **без** `-save_all` для проверки *физических* Tri6
   поры. Предохранительный (не достаточный для объёма) критерий:
   pore Tri6≥160, северная полярная часть≥18, южная≥20,
   не хуже исходной M0 по количеству поверхностных элементов.
4. При STOP создаётся один ZIP с 1D/2D metric JSON, логами, PIN,
   reason. **3D marker НЕ расходуется**; 02 запрещён.
5. При PASS записывается 24h proof, привязанный к SHA source,
   M0 и M1V и логам 1D/2D, затем только возможно `02`.

`02_P10GB_ONE_M1W_3D_ONLY.cmd` создаёт два постоянных **новых**
локальный/profile one-shot marker до native Gmsh `-3`, отдельный
кандидат `M1W_CANDIDATE`, max900s/8GiB/2GiB, nt2, 27QP QA,
FEM0. Реальная 3D сетка сохраняет Physical Groups (без -save_all).
Прежние M0/M1/M1V не перезаписываются, их markers не трогаются.

Синтетические local source tests: five 2D surface scenarios
(18N20S PASS, old17N22S STOP, south19 STOP, overall159 STOP,
Gmsh exit1 STOP), strict -save_all only at 1D, zero -3/FEM:
**PASS**. Source package SHA+ZIP CRC+extracted math selftest+Linux
STOP+README tamper STOP: **PASS**.

ZIP SHA256:
`e318f6c6197d37c1ffd63fb63b53ec65da13ab68a77eb46ab69fd320059f545b`

ZIP bytes: **40920**, 14 files.

## Следующий пользовательский шаг и приёмка

1. Новый каталог `G:\ildar\Stage3D07\P10GB_TOOLS_R1`.
2. Двойным щелчком запустить только
   `01_P10GB_PREFLIGHT_1D_2D_ONLY.cmd`; без ввода символов.
3. При STOP прислать **один** `P10GB_PREFLIGHT_STOP_EVIDENCE.zip`
   из нового LOCAL_RUNS/P10GB_PREFLIGHT_...; ни `02`, ни старые
   физические программы не запускать.
4. При PASS **один раз** запустить
   `02_P10GB_ONE_M1W_3D_ONLY.cmd`; прислать **один**
   `P10GB_M1W_MESH_EVIDENCE.zip`.
5. Ассистент независимо проверяет geometry27+343/729QP и 18
   подписанных fixed 3D зон; только если **каждая** зона
   `0.80≤Veff(M1W)/Veff(M0)≤0.85`, выдавать научный GO для
   нового forward и same-mesh adjoint.
