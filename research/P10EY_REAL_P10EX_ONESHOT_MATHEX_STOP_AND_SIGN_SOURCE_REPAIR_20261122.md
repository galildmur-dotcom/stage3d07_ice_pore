# P10EY — реальный P10EX one-shot M2 STOP в MathEx, исправление знака без нового Gmsh (22.11.2026)

## 1. Прямое доказательство и статус попытки

Исследователь передал приватный `P10EX_EVIDENCE.zip`,
**14051 Б**, SHA256
`330f1a3925be4778c295d0afbc0fc950c2f3296b4d524684f9797b303a8d2cae`,
архив CRC14/14. Первичные журналы и исходные GEO не публикуются:
только их SHA и независимые derived результаты.

`scripts/p10ey_audit_p10ex_real_math_stop_and_sign_source.py` независимо
проверил CRC и все 14 имён, M1 SHA
`ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f`,
native Gmsh4.15.2 EXE SHA317c4339..., B исправленный
P10EW `StrCat` GEO SHA
`d68570270dfb5ca2232d8fc94486e5638223b3604c933312b4036d5bb8d19b72`,
оригинальный CAD SHA8029a6ed..., manifest и точный native log.

- `native_parse_attempts=2`, обе `-parse_and_exit` — **PASS**;
- `mode=ONE_NATIVE_3D_MESH`, `native_3d_attempts=1`,
  реальный Gmsh `-3 -nt2 -format msh2` вызван после P10EX one-shot markers;
- native Gmsh exit **1** через **2.8109744 с**, пик private
  **253898752 Б**, full log **23443 Б**;
- **первичная** ошибка `Error [mathex::parse()]: Invalid expression`,
  `Field 6: invalid matheval expression`;
- далее `No elements in surface 7 8`, `HXT 3D mesh failed`,
  `No elements in volume 1 2`. Итоговый summary Gmsh:
  20 warnings, 5 errors, 3124 nodes/1584 elements;
- Gmsh *записал* `P10EA_M2_CANDIDATE.msh`, но это
  **непринятый/неполный выход**: нет volume Tet10, нет raw M2
  в доказательном ZIP, M2 SHA `UNKNOWN`; full curved27QP QA
  вообще не запускался. **Принятой новой M2 нет**;
- `physical_FEM_attempts=0`. Ни D-025, ни физические производные
  на новой M2 **неизвестны**.

**One-shot P10EX израсходован даже при STOP. Ни в коем случае
не запускать повторно `02_P10EX_ONE_M2_3D_ONLY.cmd`, не удалять
новые local/profile markers, не менять старые P10EV/P10EW markers,
raw M1, H0, forward/adjoint и другие кеши.**

## 2. Корень ошибки: настоящая MathEx-грамматика, а не GEO-парсер

Предыдущая P10EW проверка `-parse_and_exit` доказала правильность
**лексического и геометрического GEO-файла**, но не компиляцию
`Field[6].F` вычислителем размерного поля. Тот компилирует выражение
только при meshing. Предыдущие Python `ast`/7620 численных тестов
не ловили отличие грамматик: Python допускает бинарный плюс с
последующим отрицательным числом.

В оригинальном P10EX `P10EA_GMSH_FULL.log` воспроизведена
4198-символьная формула в Error line, **побайтно совпадающая**
с `Field6`. Каретка Gmsh стоит на позиции **1526** (индексация от 0),
непосредственно после **единственного** в выражении `+-`
на индексах **1524–1525**:

`...))))))+-0.0031079955054980225*(...`.

В исходном [Gmsh4.15.2 `contrib/MathEx/mathex.cpp`,
`mathex::parsearithmetic1`](https://fossies.org/dox/gmsh-4.15.2-source/mathex_8cpp_source.html)
при чтении бинарного `+` или `-` следующая лексема `+`/`-`
прямо вызывает `throw error("parse()", "Invalid expression")`
(строки 885–898). Это **не предположение о загрузке памяти**:
совпали точный текст, указатель native ошибки и исходное правило
Gmsh. Последующие 2D пустые поверхности/HXT fail — последствия
нескомпилированного целевого size field; дополнительная независимая
причина в HXT не доказана.

## 3. P10EY: однознаковая коррекция MathEx с неизменной физикой

Новый исходник:
`gmsh/P10EY_M2_C1_JOINT_STRCAT_SIGN_SOURCE_ONLY.geo`.
Из SHA-pinned старого P10EW GEO автоматический генератор заменяет
**только один токен** `+-` на `-`. В терминах размеров:

\[
  A + (-c) B \equiv A - cB,\qquad c=0.0031079955054980225.
\]

Остальные тригонометрические/радиальные зависимости,
κ0/κ1, β/α, α север/юг, C¹-стыки, CAD/physical tags,
Gmsh2D5/3D10, Tet10 и приоритеты mesh sizing не меняются.
Семь `StrCat` литералов теперь имеют длины
`[600,600,600,600,600,600,597]`, итоговая строка **4197** символов;
внутри нет смежных `+-`/`-+`/`++`/`--`/`*-`/`/-`.

Исходниковый тест:

- верные оригинальные SHA и `Field6`/каретка/CRC14/14 PASS;
- новый Python AST whitelist PASS;
- сравнение **2000** геометрических координат старой и новой
формул: max relative difference **0**;
- независимый вызов P10EU/P10ET 7620-точечного теста
  математического \(C^1\) контракта PASS;
- ни нового native `-1/-2/-3`, ни M2, ни FEM.

Вывод **только SOURCE-ONLY**. Хотя обнаруженный синтаксический
дефект исправлен, подтвердить совместимость *всего* 4197-символьного
MathEx выражения можно лишь отдельным native eval-level тестом.
**Новый полный Gmsh -3 сейчас не разрешён** и методически
нецелесообразен до проверки actual size-field evaluation.

Derived JSON и воспроизводимый script:
`research/evidence/P10EY_P10EX_REAL_MATHEX_STOP_20261122/derived/P10EY_REAL_STOP_AND_SIGN_SOURCE_AUDIT.json`,
`scripts/p10ey_audit_p10ex_real_math_stop_and_sign_source.py`.

## 4. Единственный научно оправданный следующий опыт

Предложение для **отдельного разрешения исследователя**:
ограниченная **1D** native Windows Gmsh4.15.2 `-1` проба
исправленного полного MathEval `Field6` на **нескольких
коротких отрезках** в κ≈0 и полярных κ≈1 областях. Цель:
заставить MathEx не только пройти GEO-parser, но реально
**скомпилировать и вычислить** поле, при этом не строить поверхность
поры, 3D сетку и FEM. Защитить новой версией, SHA,
новым fresh marker, ограничением wall/memory/output и небольшим
оригинальным evidence ZIP; без удаления P10EX markers.

Лишь после native 1D PASS и отдельного нового явного разрешения
обсуждать новую 3D M2 mesh-only попытку; перед FEM — реальные
curved27QP и объёмный D-025 north/south Veff ratio [0.75,0.85]
на 343→729QP. Ни оригинальная P10EX -3, ни прежние другие
закрытые попытки не повторяются. Физика FEM=0.
