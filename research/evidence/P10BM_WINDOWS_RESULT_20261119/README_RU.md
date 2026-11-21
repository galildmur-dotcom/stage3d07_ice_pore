# P10BM — публикация локальной истории GitHub, подтверждена независимо

Дата: 19.11.2026. **Статус: полный успех.** Пользователь передал оригинальный Windows `P10BM_PUSH_RESULT.txt`; побайтовая копия сохранена в `input/P10BM_PUSH_RESULT.txt` (961 байт, SHA-256 `e29e8c9c057984425761b25b5556d4cd740e529dd6583c26ef9f0e22ce3ae9a8`). Это первичный отчёт программы, не реконструкция вывода.

## Windows P10BM

- Локальный `G:\ildar\Stage3D07`, ветка `research/p10bi-local-seven-sources-20261119`, `HEAD=90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`, родитель `c0498f6dc98628b62eff996a76844297c7a35094`.
- `COMMITS=56`, 0 staged; `UNSTAGED_PRESERVED=7`, `UNTRACKED_PRESERVED=4`. Программа не добавляла эти файлы в коммит.
- Remote: `origin=https://github.com/galildmur-dotcom/stage3d07_ice_pore.git`, цель только `refs/heads/research/p10bi-local-seven-sources-20261119`.
- До отправки `REMOTE_HEAD_BEFORE=ABSENT`, введено `CONFIRMATION=PUSH 56`, операция `GIT_PUSH_ATTEMPT=ONE_REFSPEC_NO_FORCE_NO_TAGS`.
- `GIT_PUSH_EXIT=0`, `REMOTE_HEAD_AFTER=90fd2559c0224ac0a7d2dbe2fe081a6a319080e4`, `RESULT=P10BM_REMOTE_BRANCH_PUBLISHED_AND_VERIFIED`.

## Независимая проверка GitHub (не только пользовательский отчёт)

Через GitHub выполнены отдельные читающие вызовы:

1. Поиск веток обнаружил `research/p10bi-local-seven-sources-20261119`.
2. `github_fetch_commit` вернул точный SHA `90fd2559c0224ac0a7d2dbe2fe081a6a319080e4` с сообщением `P10BI: record validated P10AZ-P10BE source worktree (7 files)` и **семью** изменёнными путями.
3. Родительский коммит `c0498f6dc98628b62eff996a76844297c7a35094`, ранее отсутствовавший в GitHub, теперь доступен через GitHub API.
4. Сравнение `base=90fd2559...`, `head=research/p10bi-local-seven-sources-20261119` вернуло `status=identical`, `ahead_by=0`, `behind_by=0`. Следовательно, GitHub-ветка действительно указывает на ожидаемый полный SHA.

Ссылки: [ветка](https://github.com/galildmur-dotcom/stage3d07_ice_pore/tree/research/p10bi-local-seven-sources-20261119), [коммит](https://github.com/galildmur-dotcom/stage3d07_ice_pore/commit/90fd2559c0224ac0a7d2dbe2fe081a6a319080e4), [родитель](https://github.com/galildmur-dotcom/stage3d07_ice_pore/commit/c0498f6dc98628b62eff996a76844297c7a35094).

## Дополнительная проверка связности P10BI ↔ P10BG

Запросы GitHub SHA Git-блобов всех семи исходников по **двум отдельным веткам** `research/p10bi-local-seven-sources-20261119` и `research/p10bg-source-integration-20261119` дали **7/7 совпадений**:

| Путь | Совпадающий SHA Git blob |
|---|---|
| `CMakeLists.txt` | `de5a375eae75e7ce24f19769deb8b819f62eb485` |
| `src/stage3d10p_partial_audit.cpp` | `b1bab7385e86928306617a4ec930d31e9b478a3f` |
| `src/stage3d10w_analytic_adjoint.cpp` | `0cf185831f82c885ca6b60ce35aa32057f6623dc` |
| `src/stage3d10v_analytic_shape.hpp` | `068ef888dc0177e6c7af245d007ad4d400a1ad32` |
| `src/stage3d10az_probe_export.hpp` | `5d8338d2bb4aeaceec8b172532df940efe1b5d95` |
| `src/stage3d10ba_polar_export.hpp` | `b2b40725f2484f24832b0ab134e217b9fff45841` |
| `tests/stage3d10v_analytic_shape.cpp` | `f5d18aba532d4014c42ebf526a54842d8d76d7a1` |

Это **побайтовое тождество содержимого Git-объектов на семи путях**, не тождество родительских коммитов, полных деревьев, конфигурации CMake, сборочных окружений или исполняемых файлов. Прежние Windows SHA-256 оригинальных CRLF-файлов остаются в P10BG/P10BJ, их не следует путать с Git blob SHA.

## Что остаётся открытым

1. На ПК остались 7 unstaged + 4 untracked записи; они не попали в опубликованный коммит. Не чистить их автоматически и не делать `git pull` поверх грязного рабочего дерева.
2. Исторические четыре Windows unit/selftest P10BH были *запусками существующих EXE*. Не доказано, что эти EXE скомпилированы из Git SHA `90fd...`: нет первичного clean compile log и нового SHA-256 EXE, связывающего двоичную сборку с коммитом.
3. Следующий инженерный шаг — **аттестация новой воспроизводимой сборки Windows** из явно фиксированного чистого дерева (отдельная директория/рабочая копия), CMake/MinGW Release compile log, SHA-256 новых EXE и повторение четырёх unit/selftest. Не запускать тяжёлый FEM до установления provenance.
4. Научная пространственно-временная сходимость **полной** геометрической производной и относительная роль тепловой части остаются недоказанными. Первичные P10BB/P10BE CSV не изменялись.
