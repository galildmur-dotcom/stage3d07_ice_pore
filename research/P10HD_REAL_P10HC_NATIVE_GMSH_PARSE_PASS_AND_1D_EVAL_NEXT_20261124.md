# P10HD — реальный P10HC Gmsh4.15.2 parse-only PASS; переход к bounded 1D evaluation

**24.11.2026. `P10HC_REAL_GMSH_PARSE_ONLY_PASS`; `NATIVE_FIELD_EVALUATION_UNTESTED`; `P10HD_ONE_1D_TEST_PREPARED`; `M2 2D=0,3D=0,FEM=0`.**

Пользователь передал первичный `P10HC_01_PARSE_EVIDENCE.zip`, SHA256 `490c8c4d7d56d069a7fe3dc94f689ebadef8d6e483a7a981ade654357ab23363`, 4 файла, ZIP CRC PASS.

Независимо сравнены два опубликованных canonical файла внутри evidence: `P10HC_SOURCE_FIELD_QA.json` SHA256 `5ecdd7b55872da666facdff2c8c063ae547ad28e9265fe702264a4fdc3e0c0e7`, и `P10HC_M2_SOURCE_ONLY.geo` SHA256 `33278d94dc103e9000350fbc9bee8cb6756fd786af7be63c42c3ef738c36ceb9`, **байт-в-байт** соответствуют опубликованным исходникам. Остальные включения проверялись исходным Windows launch-кодом по SHA перед native.

Реальный native Windows Gmsh4.15.2 вызов — `-parse_and_exit -nopopup -nt 2`, exit0, wall0.375с, log «Done reading» для `P10GT_HXT10.geo`, `M0_ROTATED.geo`, `sphere_pore_B6_refined_rotated.geo`, `P10HC_CONTINUOUS_KAPPA_FIELDS.geo`, `P10HC_M2_SOURCE_ONLY.geo`. Никаких `Error :` и нет STOP. 1 native parse, 0 mesh 2D, 0 mesh 3D, 0 FEM. Нельзя принимать в M2 на основании одного parse: `Field[40]` и `[41]` длиной около 0.5/0.6 млн символов могли только сохраниться как strings, а реальная функция MathEval ещё не вычислялась при mesh.

**Следующий ограниченный источник P10HD:** независимый микропробник Gmsh `-1` на нескольких отдельных 1D линиях в физических направлениях от центра поры с `Field[7]=constant` и включённой **точной неизменной** `P10HC_CONTINUOUS_KAPPA_FIELDS.geo`; целью является вызов численного оценщика Field[42/43] при 1D построении, оценка времени/ресурса и выявление ошибок muParser. Отдельный M1 F7 не тестируется: это отдельный ранее подтверждённый компонент P10GT. Это НЕ физическая 2D/3D CAD, НЕ Tet10 M2, НЕ оценка D-025 и НЕ FEM.

Если native 1D PASS, далее нужен 3D CAD field-evaluation/QA и поверхностный mesh-only с независимым подтверждением performance и D-025; никакой автоматический переход к M2 запрещён. Старые P10HC/P10GT markers не менять, новые P10HD one-shot отдельно.

## Выпущенный пакет P10HD R1

`research/proposals/P10HD_GMSH_1D_FIELD_EVAL_20261124/P10HD_R1_BOUNDED_ONE_1D_FIELD_EVAL_WINDOWS_20261124.zip`, SHA256 **`a8044f08ef91bc98e23f59ea46e4bb7aac5b172491604fda484c94b572ad4a72`**; 8 файлов, ZIP CRC/source consistency PASS. Исходный P10HC field source pinned SHA `98ce03ed4a656dd6c3e9fc69f5c9711d7d8bbdc6bf61ddaceed9e656a918a85a`. Пакет состоит из отдельного GEO четырёх пробных физических лучей, ровно одного исходного continuous MathEval P10HC, отдельного драйвера, QA-манифеста с SHA, двух `.cmd` и локального ограничителя Windows Job.

На пользовательском Windows запускать последовательно `01_P10HD_PREFLIGHT_NO_MESH.cmd`, после PASS — один раз `02_P10HD_ONE_NATIVE_1D_ONLY.cmd`. Встроенные пределы native `-1`: максимум300с, **жёсткий Windows Job 4GiB private**, max log6MiB, max MSH16MiB, `-nt2`; никаких `-2/-3` и FEM, исходные M1/M0 физические поля не трогаются. Два новых independent P10HD one-shot markers записываются только перед 1D. При PASS прислать `P10HD_ONE_1D_EVIDENCE.zip`; при 01 STOP — `P10HD_PREFLIGHT_EVIDENCE.zip`.

В 1D тесте `Field[7]` намеренно заменён константой, а для лучшей диагностической контрастности `Field[44] = 0.0001 + 0.0009*(1-F42)`; он вызывает тот же исходный `Field[42]`, но **не является новым целевым полем M2**. Даже успешный 1D тест пока не даёт права на `2D/3D mesh GO`. Сохранить обе схемы D-025/027 и нетронутые физические результаты.
