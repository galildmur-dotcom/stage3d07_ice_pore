# P10FA — независимый разбор двух оригинальных P10EZ evidence (22.11.2026)

## Первичные файлы и контроль целостности

- `P10EZ_EVIDENCE.zip` SHA256 `0ebeb155eddf05a470d36e86c97ff68211afded98cb2416a33cd37bb2f49b03d`; 3/3 CRC PASS; безопасный preflight.
- `P10EZ_EVIDENCE(1).zip` SHA256 `d4da0b31a5487f349f400d03933fcb116c333933fc4ff96c8e687ba3695557ee`; 5/5 CRC PASS; единственный native Gmsh -1.

По manifest в обоих архивах pinned P10EY SHA256
`2aec3e2626b3500388954e428d880c702a4bb820116af93924b8d590bf9b26f1`,
Gmsh4.15.2 EXE SHA256
`317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1`.
Одинаковый generated GEO SHA256
`38197074e7eade4174ee213f37cb73ed366ae7cc02a6cf4366a85af183e9cd32`.
Эти SHA записаны в Windows manifest; сам EXE в архиве отсутствует,
его байты не были независимо перепроверены на нашей машине.

## Реальный Windows native результат

Manifest `mode=one-1d`, `native_1d_attempts=1`, `native_2d_3d_attempts=0`,
`FEM_attempts=0`; native exit0, runtime0.2054995s, peak private
7266304B, kill_reason=null. Журнал Gmsh сообщает 1D meshing curves1/2/3,
`18 nodes 21 elements` (включая отдельные элементы точек, которые
не экспортированы из-за Physical Curve); исходный MSH2 реально содержит
18 узлов и 15 элементов типа1 по пять на каждый физический тег
NORTH=101, SOUTH=102, EQUATOR=103. Raw MSH SHA256
`6b06224f27cafd51cd29674e4c26c4579dd0a5e0efa2bd1a6e677dcc89f6d72f`.
В логе Gmsh нет Error, MSH2 корректно замкнут $EndElements.

**Вывод:** P10EZ native Windows **PASS в ограниченном 1D smoke test**;
раньше выявленный MathEx `+-` STOP не повторился. Размерность и теговая
проверка подтвердили применимость поля к трём кривым. Однако численная
проверка всех значений field h(x), чувствительность при реальном 3D
remeshing и полярный D-025 **не установлены**. Никакой M2 нет.

P10EZ разрешение израсходовано; кнопку02 нельзя повторять, локальные
и пользовательские markers сохраняются. Следующий возможный этап —
только после **нового отдельного разрешения** одна защищённая 3D M2
mesh-only попытка с последующим независимым curved27QP north/south
Veff ratio [0.75,0.85], κ0 и плавностью; FEM отдельно после GO.

Первичные пользовательские ZIP и MSH не публиковать без новой санкции.
