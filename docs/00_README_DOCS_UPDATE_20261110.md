# Обновление научных документов Stage3D07 после резервирования

Дата: 2026-11-10. Этот пакет обновляет **четыре файла** первоначального пакета организации проекта.

## На компьютере пользователя

1. Убедитесь, что все четыре файла уже существуют в `G:\ildar\Stage3D07\docs\` и что после последнего Git-коммита вы их самостоятельно не редактировали. При наличии собственных правок **не заменяйте** файлы, сначала сравним и объединим изменения.
2. Скопируйте из этого пакета файлы `PROJECT_STATE.md`, `DECISIONS.md`, `RESEARCH_LOG.md`, `F_ARCHIVE_PLAN.md` в `G:\ildar\Stage3D07\docs\` с заменой их ранних версий. Остальное в проекте не изменять.
3. В Git Bash проверьте изменения:

   ```bash
   git -C "G:/ildar/Stage3D07" diff --stat
   git -C "G:/ildar/Stage3D07" diff -- docs/PROJECT_STATE.md docs/DECISIONS.md docs/RESEARCH_LOG.md docs/F_ARCHIVE_PLAN.md
   ```

4. Если соответствуют этому обновлению, сохраните и отправьте:

   ```bash
   git -C "G:/ildar/Stage3D07" add -- docs/PROJECT_STATE.md docs/DECISIONS.md docs/RESEARCH_LOG.md docs/F_ARCHIVE_PLAN.md
   git -C "G:/ildar/Stage3D07" commit -m "Project: record verified Git bundle and F archive"
   git -C "G:/ildar/Stage3D07" push origin master
   git -C "G:/ildar/Stage3D07" rev-parse HEAD
   ```

Проверенный автономный Git bundle на F относится к предыдущему состоянию `9e79fcbbb6c5d31564c7f7e0b9e01864900f7c86`. Создание нового коммита не делает тот архив недействительным; просто следующие изменения появятся в нём только после создания нового bundle.

## Следующий шаг

Выявить точный путь хотя бы одного фактического запуска P10N/P10P/P10S и начать заполнять `experiments/RUN_REGISTRY.csv` реальными параметрами, без приписывания старому запуску неподтверждённого Git SHA.
