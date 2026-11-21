# P10CX R1 — ограниченная Windows Gmsh4.15.2 поверхность U1_geo, ПОДГОТОВЛЕНО

21.11.2026. Уровень доказательства: **исходники + Python synthetic + воспроизведение прошлой Linux 2D + ZIP CRC; реальный Windows Gmsh4.15.2 пока НЕ запускался.** Без 3D/FEM.

## Новый вопрос / STOP_DUPLICATE

P10CW впервые получил реальную 2D-поверхность поры на Gmsh4.13.1, 74592 Tri6, медиана hmax 20.015 мкм и ровно один крайне плохой Tri6 quality0.0747478437 в southern μ0 φ3. Это **не** физическое объяснение полярных производных на старых H4W*. Новый P10CX различает версионный/построительный артефакт Gmsh4.13.1 и воспроизводимый приполюсный дефект на **канонической пользовательской Gmsh4.15.2**. Уже завершённые P10CJ–P10CR и P10CT R1/R2 не повторяются.

## Артефакт и допуски

- Пакет `research/packages/P10CX_R1_2D_SURFACE_GMSH4152_WINDOWS_20261121.zip`, SHA-256 `ad7ee12ab0e7be2f878ae9517d7a8ebdd9d04d6b9123a5fed920f50ee2be9e21`, 6 членов, ZIP CRC **6/6 PASS**.
- Один CMD запускает PowerShell 5.1; точные source SHA gates: GEO `85ee63351ff8e7c1b7720f8ba360aac1d4e6c381f776e3fa66f130e73f17aca7`, OCC include `8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0`, stdlib Python QA `165d59ff1b05f45478008c6498a0b5ddfde19ca4538816439a3a530f70cc0f50`. Исходный Windows `gmsh.exe` SHA записывается при запуске, перед сеткой принудительно проверяется версия `4.15.2`.
- Параметры: `-2 -nt 2 -format msh2`, target стенки20мкм/band200мкм/far2мм, в исходном GEO `ElementOrder=2`, MSH2 ASCII; никаких `-3`, FEM, Windows C++ или Git-операций. Изолированная директория вне `G:\ildar\Stage3D07`.
- Лимиты: **180 с, 2ГиБ private bytes процесса, 150МиБ MSH**, предварительно 4ГиБ свободной RAM и 1ГиБ места на диске. Прогноз на i7-7700K: ~5–90 c, низкая уверенность; при STOP архив сохранить и **не повторять** тот же One Click.
- Результаты: SHA MSH, native Gmsh exit и Python exit, полные stdout/stderr, 120 `(μ,φ)` ячеек, corner q distribution, положение худшего Tri6 и split polar/mid. Отправлять **только `P10CX_EVIDENCE.zip`**, не MSH/EXE/VTU.

## Проверки подготовки в окружении ассистента

1. `P10CX_surface_audit.py --selftest` → `P10CX_SYNTHETIC_UNIT_OK`, exit0.
2. Независимый stdlib Python parser прочитал исходную MSH2 P10CW на Gmsh4.13.1 (SHA `3e71273ce32c700d63d453c697bacbaa938e12f3a915b79defb14c8c1269f2a4`) → `P10CX_SURFACE_QA_OK`, **74592** pore Tri6, qmin **0.07474784370275221**, below0.1=**1**, polar/mid median hmax **1.0020310882597714**, 120/120 контрольных ячеек. Совпало с опубликованным P10CW Gmsh-API/NumPy анализом. Это replay старого 2D, не новый mesh.
3. `unzip -p ZIP P10CX_surface_audit.py | python - --selftest` → PASS; ZIP CRC6/6, CMD CRLF. Полная runtime аттестация **PowerShell 5.1 и Gmsh4.15.2 на Windows PENDING** — их в данной среде нет. Не объявлять пакет проверенным на Windows.

## GO/STOP и следующий единственный вход

**P10CX_R1_PREPARED_NO_WINDOWS_MESH_NO_3D_NO_FEM.** Исследователь один раз запускает `01_RUN_P10CX_SURFACE_ONLY.cmd` из нового распакованного каталога. При qmin<0.1 результат `P10CX_STOP_SURFACE_POLE_SLIVER_NO_3D_NO_FEM`; при отсутствии такого элемента — лишь локальная 2D geometry-PASS, не лицензия на 3D. В любом случае сначала независимый аудит исходного ZIP и совместное решение о следующей ограниченной 3D mesh-only проверке. Причина полярного механического эффекта всё ещё UNKNOWN.
