# Stage3D07 P10GL R1 — отдельно разрешённая ОДНА новая 3D HXT10 попытка с P10GK C¹ полем

**23.11.2026. Статус SOURCE / UNIT / MOCK / ZIP INTEGRITY PASS; реальных новых P10GL Windows `gmsh -3` = 0; FEM = 0.** Исследователь после реального P10GK source + Gmsh4.15.2 `-parse_and_exit` PASS отдельно ответил «разрешаю» на одну новую строго ограниченную нативную HXT10 mesh-only попытку без FEM. Разрешение относится исключительно к этой новой P10GL попытке. Старый P10GJ one-shot израсходован и не подлежит повторению.

## Научная постановка (вся геометрия и hard-gates не меняются)

- Исходная M0: 7 992 Tet10, SHA256 `926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6`. Только тот же OCC CAD поворот P10GH, никакого изменения формы/объёма поры и физических групп 1–9.
- Ранее реально построенная P10GJ HXT10 M1: 9 710 Tet10, global QV729≈`0.823069` PASS, все sampled detJ27/343/729>0, но физический полюс поры ЮГ 0–500 µm QV729≈`1.002260 >0.98` hard D-027 STOP. Исторические M0/M1 и P10GJ evidence не перезаписываются.
- Новый P10GK C¹ source SHA256 ZIP `4cc0390df4cc2277078ee0d8bca281bd77e3606ec4128e943cc10c243caf9d05`: `F6=F3*(1−0.06*Wr(d)*Ws(mu))`, физическая южная полусфера с окном `mu≤−0.8` до `mu=−0.6`, radial plateau `d≤0.5mm`/fade `d≤1mm`, global `MeshSizeFactor=0.9378887276834518`, Gmsh4.15.2 `Mesh.Algorithm3D=10` (HXT), Tet10, MSH2 ASCII. `α=0.06` заморожена до реального результата, локальное поле математически C¹. Увеличение фактической плотности HXT не считается гарантированным.
- Реальный native Windows P10GK source-only parse архив SHA256 `6af4dac68f1335aa714b02702ef7c305624ea46622b067fd5aacee6bde89305f`, Gmsh4.15.2 exe SHA256 `317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1`, parse-only exit0, новых 3D не было.
- **Замороженные численные пороги по исходной M0 ДО P10GJ и P10GL:** неизменный `P10GJ_D027_FROZEN_GATES.json` SHA256 `2dcb1ae0444f4bcdedc427ce661c8a4c7bc1018d6a34c282f1434e3b1b378aea` в новом релизе. Никакой постфактум подгонки: global `0.80≤QV≤0.85`, полярные север/юг при `0≤d≤0.5mm` и M0 N_eff≥50 `QV≤0.98`; 27/343/729 positive sampled detJ, CAD/surface/Tet10/sliver/градация/physical macros hard; **18/18 индивидуальных signed зон только diagnostic**.

## Точный технический протокол

Релиз: `research/packages/P10GL_R1_ONE_P10GK_C1_HXT10_M1_WINDOWS_20261123.zip`.

- **SHA256 ZIP `4f4b9ee0c60ad4d664e605f5c110f4de6cc934fc8afd43f87a68a69fc77a0252`**, **59 439 байт, 15 файлов**. Внутри exact P10GK source release, exact Windows native parse-only evidence и exact M0-only numeric gate freeze, read-only QA Tet10/Tri6 и новые защищённые 01/02 Windows кнопки.
- Кнопка **01**: source manifest SHA/ZIP CRC, frozen M0-only D-027, повторная реальная read-only M0 27QP+Tri6 QA, 12 221 точек C¹ MathEval QA, установленная Gmsh.exe 4.15.2 SHA pin, native `-parse_and_exit` для финального включающего `.geo` (не `-1/-2/-3`), отдельный proof с SHA логов, действителен 24 часа. Полный PASS `P10GL_PREFLIGHT_PASS_NO_3D_D027_FROZEN` необходим для 02.
- Кнопка **02**: сначала два постоянных эксклюзивных one-shot marker файла (локальный `LOCAL_RUNS/P10GL_LOCKS` и `LOCALAPPDATA/Stage3D07/P10GL_ONE_HXT10`), потом **ровно одна** native Gmsh4.15.2 `-3 -nt 2 -format msh2`, hard watchdog **900 секунд**, Windows Job **≤8 GiB private RAM**, свободная RAM до запуска ≥12 GiB, диск ≥4 GiB, output ≤2 GiB, MSH ≤128 MiB; ни FEM, ни второй mesh. При любом STOP marker не восстанавливать и не повторять 02.
- P10GL candidate исходники/логи/мэш/27QP QA сохраняются только в новом `LOCAL_RUNS/P10GL_M1_SOUTH_C1_HXT10_*`, не в `meshes/` и не в исторических папках. При любом результате вернуть **один** `P10GL_M1_HXT10_EVIDENCE.zip`; если ZIP не создан, `P10GL_02_RESULT.txt`. При STOP 01 прислать `P10GL_01_RESULT.txt`, кнопку 02 не запускать.
- `P10GL_NATIVE_27QP_PRELIM_PASS_343_729_PENDING_NO_FEM` **не** означает M1 GO. После получения реального raw MSH независимый `scripts/p10gl_offline_343_729_adjudicate.py` (NumPy только на компьютере аналитика, не на Windows пользователя) проверит все 343/729 QP, 18 signed + полярные макрозоны и сохранит D-027 verdict; только отдельное научное решение после него, никакого автономного FEM.

## Проверено до реального 3D запуска

- `scripts/test_p10gl_one_hxt10.py` **8/8 PASS**: immutable P10GK/M0/policy/real-parse evidence; C¹ 12 221 points; exact frozen D-027 thresholds; preliminary-vs-final gate; Linux Windows STOP; полный mock preflight только native parse; **один** mock HXT10 + два постоянных marker; mock watchdog STOP также сохраняет оба marker, запрещает повтор и формирует evidence.
- `scripts/p10gl_build_one_p10gk_hxt10_release.py`: deterministic ZIP, CRC/extract/retest, Linux native STOP, tamper STOP — PASS. **Все unit/mock тесты без настоящего Gmsh -3/FEM**.
- `scripts/p10gl_offline_343_729_adjudicate.py --selftest`: унаследованные проверенные аффинные и инвертированные 27/343/729 QP + проверка pinned frozen M0 — PASS. Фактическое P10GL MSH пока **не существует**; реальные макрозоны/глобальный q неизвестны.

**Следующий фактический шаг:** исследователь распаковывает новый ZIP в `G:\ildar\Stage3D07\P10GL_TOOLS_R1`, сначала нажимает 01, только при PASS — один раз 02 в 24 часа, присылает один evidence ZIP, не запускает FEM. Ожидаемое время Gmsh на i7-7700K — секунды или несколько минут (предыдущий P10GJ native -3 ~0.5с), но максимум строго 900 секунд; дополнительный M0 QA preflight/постмэшовый 27QP audit может занять минуты.
