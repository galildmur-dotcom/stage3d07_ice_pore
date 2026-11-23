# Stage3D07 P10GN R1 — отделить эффект ссылки на F3 от южного множителя

**23.11.2026. Релиз P10GN SOURCE/UNIT/MOCK/ZIP PASS. Реальных native Windows P10GN Gmsh `-1`=0, `-2/-3`=0, FEM=0; новая M1 не построена.**

## Научное основание

Полученное первичное P10GM native Windows evidence SHA256
`6b047f5dd485433987b1a518ad9c164f7a0fbf0747312c616dc31d84b8acfe34`
доказывает A исходное F3 `-1` PASS0.510с, B F6 с F3/F4/F5 TIMEOUT30.125с,
C полное подставление F4/F5 внутрь F7 TIMEOUT30.128с (оба на окружностях14/17,
RAM peak≈246MB). Independent audit и source pins опубликованы:
`research/P10GM_R1_REAL_WINDOWS_1D_AB_C_INDEPENDENT_AUDIT_20261123.md`.
Вариант C **по-прежнему содержит прямую ссылку на F3**; поэтому отделить
проблему вложенного MathEval от проблемы сложной локальной функции по P10GM
невозможно. Ни P10GL, ни P10GM `02` не повторять: их one-shot потрачены.

## Предварительно фиксированный P10GN 1D опыт

Сохраняются идентичные rotated OCC 3D CAD, исходное M0 C¹ F3, все физические
группы, глобальный `Mesh.MeshSizeFactor=0.9378887276834518`, Gmsh4.15.2.
Допускаются **только новые ограниченные 1D probes**, не HXT10 3D:

| Шаг | Gmsh 1D background | Дискриминирующий вопрос |
|---|---|---|
| D | `Field[7].F="F3"` | Достаточно ли повторного обращения к исходному MathEval F3 для задержки? |
| E | `Field[7].F="F3*0.94"` | Влияет ли простое умножение при уже подключённом F3? |
| F, **только D+E PASS** | Нетронутое P10GK background F6 и дополнительный `Mesh.MeshSizeMin=0.0002` м | Может ли нативный ненормально малый размер вызвать патологическое деление окружности? |

F использует 0.2 мм как **контролируемый нижний предел для диагностики**:
он меньше номинального южного размера на стенке поры
`0.0004616510070248522·0.9378887276834518·0.94≈0.000407` м.
Этот предел не является утверждённым алгоритмом M1, не имеет гарантии
семантической эквивалентности в Gmsh и не разрешает 3D.

**Ограничения исполнения:** каждый native `-1` ≤30 секунд,
≤8 GiB private RAM Windows Job, 2 потока, вывод текущего журнала и
`HEARTBEAT` каждые 2 секунды. Всего максимум 3 случая/90 секунд
native, без автоматических повторов. Если D/E имеют STOP, F не запускается.
P10GN создаёт **собственные** два независимых local/profile one-shot markers
до первого native; не изменяет P10GL/P10GM markers, M0.msh, архив P10GK,
гейты D-027, исходный CAD или FEM.

## Источники и программные проверки

- Пакет `research/packages/P10GN_R1_REFERENCE_F3_1D_DIAGNOSTIC_WINDOWS_20261123.zip`,
  SHA256 **`5fc8b50f8ed4aeb32d8628f6e49a6c947926464534e213f8a6fd3ca44d2abea2`**,
  **29 685 байт, 7 файлов**, CRC PASS и чистая распаковка + `--selftest` PASS.
- Воспроизводимая сборка `python scripts/build_p10gn_release.py`;
  source SHA manifest **`28503194e4ad3ec24fc2ba019b60e8a6249f56fb1d2d02906695bc81599a3c81`**.
- `python -m unittest scripts/test_p10gn_1d_probe.py -v`: **6/6 PASS**,
  в т.ч. byte-pin/altered ZIP STOP, тесты точных драйверов D/E/F,
  mock Gmsh `-1` exit0, 30s/8GiB/nt2, D TIMEOUT→E всё равно запускается
  без F, создание evidence ZIP, one-shot повтор STOP, D+E PASS→F выполняется.
- Встроенный исходниковый тест: 10 201 точка, B/C исходные MathEval выражения
  алгебраически совпадают (не native Gmsh), локальный множитель [0.94,1].
- Source P10GK ZIP SHA256 `4cc0390df4cc2277078ee0d8bca281bd77e3606ec4128e943cc10c243caf9d05`
  байт-в-байт; исходная M0.msh SHA `926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6`;
  Gmsh.exe SHA `317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1`.
- Никакого реального native Gmsh не запускалось в окружении ассистента:
  Windows 4.15.2 бинарник отсутствует. Реальное поле и 1D ещё не проверены.

## Следующий шаг исследователя

Новый P10GN ZIP распаковать **отдельно** в
`G:\ildar\Stage3D07\P10GN_TOOLS_R1`.
Сначала `01_P10GN_PREFLIGHT_NO_MESH.cmd`, после PASS ≤24ч
**один раз** `02_P10GN_ONE_REFERENCE_1D_DIAGNOSTIC.cmd`.
Передать **один**
`LOCAL_RUNS\P10GN_1D_REFERENCE_DIAG_*\P10GN_1D_PROBE_EVIDENCE.zip`,
при его отсутствии — `P10GN_02_RESULT.txt`/текст окна.
Дальнейшее решение только по оригинальным нативным журналам и
непредвзятой классификации D/E/F. Никакой M1 GO/FEM независимо от результата.

**Научный контракт неизменён:** global `QV729∈[0.80,0.85]`, физические
северный/южный near-polar QV≤0.98 с N_eff достаточным, sampled curved
Tet10 detJ positive27/343/729, quality/grading/surfaces hard, а индивидуальные
18 signed ratios только diagnostic; новые HXT10/FEM требуют иной санкции.
