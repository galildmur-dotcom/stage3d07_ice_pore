# P10FB — новая M2 на исправленном P10EY: Windows пакет подготовлен (22.11.2026)

## Разрешение и научный предел

После независимого P10FA аудита реального P10EZ native 1D PASS исследователь
разрешил публикацию проверенных P10EZ/P10FA и **подготовку программы**
следующего этапа. Реальный `Gmsh -3` в P10FB ещё **не выполнен**;
новую 3D попытку не считать израсходованной до настоящего вызова.
Старый P10EX one-shot исчерпан и не должен повторяться.

## Новая точная версия

Используется неизменная исходная M1 P10DG SHA256
`ca6b6b6588dc72c5dd3ed2e92e24794560ee2407e350c8a44858e9c3c7d0360f`.
Геометрия OCC и CAD наследуются от SHA-pinned P10EX цепочки,
а `Field[6]` **в точности** взят из P10EY SHA256
`2aec3e2626b3500388954e428d880c702a4bb820116af93924b8d590bf9b26f1`.
Source gate восстанавливает предыдущую 4198-символьную P10EW формулу
и побайтно проверяет единственную MathEx замену `+-c` → `-c`
в полной восстановленной строке длины4197, не сравнивая искусственные
границы семи StrCat фрагментов.

Изолированное семейство источников предыдущего P10EX закреплено по
ZIP SHA256 `84a0570cfc61a4fcd3084e5eed3d5926ad6cce88e2dad81a769d8ee92039ba70`.
Новый локальный ZIP:
`research/packages/P10FB_R1_ONE_P10EY_SIGN_M2_WINDOWS_20261122.zip`
SHA256 `543edf1edeff93596bb2ebadc682eda06031a193dc95ea262c103f5587a1a6bc`,
70 членов ZIP включая каталоги, CRC PASS.

## Исполнитель и остановки

- 01: source/M1/native Gmsh EXE SHA, настоящие два GEO `-parse_and_exit`,
  24h proof, **без -3**;
- 02: только после proof и точной фразы `RUN ONE P10FB M2 3D MESH`,
  два **новых** эксклюзивных permanent local/profile marker до одного `-3`;
- Gmsh `-nt2`, wall≤900s, polled private≤8GiB, raw MSH≤750MiB,
  full log≤16MiB, independent geometry QA≤300s, FEM0;
- MSH2 geometry curved27QP QA PASS ещё **не** значит D025 GO;
  север/юг fixed3D curved Tet10 Veff ratio [0.75,0.85] и κ0/плавность
  оцениваются отдельно, по реальным M1/M2 на 343→729QP;
- raw M2 включать в evidence при ≤32MiB; иначе потребовать raw отдельно;
  не публиковать приватные raw MSH/FEM cache.

## Выполненные проверки и ограничения доказательства

- exact source SHA и MathEx single-sign parity PASS;
- inherited source gates PASS;
- isolated extracted ZIP Python selftest PASS;
- synthetic two-marker first-create/second-attempt STOP PASS;
- Linux native preflight STOP до Gmsh PASS;
- 70-entry ZIP archive CRC PASS.

**Реального нового Windows Gmsh -3 не было.** M2 отсутствует;
D025 UNKNOWN; physical forward/adjoint/FEM=0. Результат будущего
Windows запуска передать одним оригинальным `P10FB_EVIDENCE.zip`.

Публикация GitHub была отдельно разрешена, но обычный Git HTTPS push
остановился на отсутствии учётных данных (`could not read Username`),
поэтому до постпроверки удалённого HEAD новые локальные коммиты
**не следует называть опубликованными**.
