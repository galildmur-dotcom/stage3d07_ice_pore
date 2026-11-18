PORE ONE CLICK — P10Z edition (2026-11-13)
=======================================
This updates your original 2026-11-12 tools and preserves the established workflow.
It does NOT change the Stage3D07 Git repository during installation.

INSTALL ONCE (UPGRADE)
1. Unpack this ZIP into a temporary folder.
2. Double-click 00_INSTALL_ONCE.cmd.
3. Files are copied to G:\ildar\PORE_GIT_TOOLS and 4 desktop shortcuts created.

BUTTON 1: PORE - 1 Apply patch and push
The needed patch Stage3D07_P10Z_MESH_SHELL_AUDIT_ONECLICK_20261113.patch
is included in THIS ZIP alongside the helper scripts (in the extracted folder).
Double-click the desktop shortcut, select that .patch, confirm the operation.
If TRACKED edits exist, the program displays their names and asks permission to
preserve them in Git stash. On YES, only tracked edits are stashed, the patch
alone is committed/pushed, then previous edits are restored (when tracked
worktree/index is clean). Git stash backup is intentionally retained even
when restoration succeeded. NO means abort without changing edits.
If remote/local master differ, or there are staged edits, the program stops.
NO reset, clean, rebase, pull, force-push or deletion of source/results.
For failures: send G:\ildar\PORE_GIT_TOOLS\logs\import_*.log; do not retry blindly.

BUTTON 4: PORE - 4 Run P10Z mesh audit
After patch application, double-click the shortcut. It checks Python/NumPy,
asks you before offering to install NumPy, runs selftest, reads the existing
G:\ildar\Stage3D07\P10M_MESHES\H4.msh and H4W2.msh, and computes the
27-/64-QP geometric diagnostics. If mesh paths differ, it opens file dialogs.
Results: new timestamped folder under G:\ildar\Stage3D07\P10Z_RUNS.
Then it calls the updated packaging script for the 3 diagnostic CSV/TXT files.
It never writes the input meshes or replaces existing outputs.
This is a LIGHT geometry-only diagnostic, not a coupled FEM calculation.

BUTTON 3: PORE - 3 Package run results
Now also recognizes P10Z_MESH_QP_SHELL_METRICS.csv,
P10Z_RADIAL_CUMULATIVE.csv, P10Z_MESH_AUDIT_LOG.txt. Use this if automatic
packaging was interrupted. Output ZIP in G:\ildar\PORE_CHATGPT_EXPORTS.

BUTTON 2: PORE - 2 Export source snapshot
Unchanged. Exports COMMITTED sources only, plus HEAD and tracked status.
Tracked uncommitted work is not included in the source ZIP itself.

Important from supplied source snapshot 2026-11-13:
HEAD=4ce1d3ed75434fe6620e75d61e86d09dfbc9ea2a.
Two SVG files were marked modified at the moment of export:
 experiments/P10Y_H4_H4W2_COMPARE_20261112/figures/P10Y_H4_vs_H4W2_jpeak_COMPONENT_DIFF.svg
 experiments/P10Y_H4_H4W2_COMPARE_20261112/figures/P10Y_H4_vs_H4W2_jpeak_RADIAL.svg
Do not discard these changes. The updated Button 1 can preserve them separately.

Original tool version: 2026-11-12; updated edition: 2026-11-13.


FIX 2026-11-13: POWERSHELL #requires / param ERROR
---------------------------------------------------
Previous P10Z-edition package contained DOUBLE UTF-8 BOM at the beginning
of Apply-Patch.ps1, Install.ps1, Package-Run-Results.ps1. This made Windows
PowerShell parse the invisible extra BOM as a command, and then reject param().
All five .ps1 files in THIS fixed edition have exactly ONE UTF-8 BOM.
The installer additionally checks startup bytes and parses each installed
PowerShell script with PowerShell's built-in parser BEFORE creating shortcuts.

RECOVERY (no PowerShell/Git Bash typing):
1. Unpack THIS ZIP to a NEW folder (not directly into the Git repo).
2. Double-click 00_INSTALL_ONCE.cmd.
3. Confirm 'Verified PowerShell scripts: 5' and 'INSTALLED'.
4. Use desktop shortcut 'PORE - 1 Apply patch and push' normally.
5. Select Stage3D07_P10Z_MESH_SHELL_AUDIT_ONECLICK_20261113.patch
   from the extracted folder; do not apply it twice if already committed.
Existing repo, local edits, Git history and calculation results are untouched
by the installer. On any failure please send a screenshot of the FULL error.

FIX 2026-11-13: Python NumPy probe / PowerShell 5.1 quoting
--------------------------------------------------------
The former Run-P10Z.ps1 probe used an embedded quoted Python string,
which Windows PowerShell 5.1 removed during native argument passing.
Python then raised NameError (P10Z_NUMPY_OK). NumPy was already installed.
This release checks NumPy by printing numpy.__version__ without quoted strings.
Unpack to a new folder, double-click 00_INSTALL_ONCE.cmd, then use ONLY
PORE - 4 Run P10Z mesh audit. P10Z Git patch was already applied and
pushed at commit 623ed568eca8fe8a64a4177cedf360e127807d33.
Do NOT reapply it. This fix touches tool scripts outside the Git repository.


UPDATE 2026-11-13 — PORE - 5 Audit refined H4W4B2

Новый ярлык создается повторным запуском 00_INSTALL_ONCE.cmd.
PORE - 1/2/3/4 не меняются.
PORE - 5: выберите H4W4B2.msh (обязательно); при наличии выберите
H4W2B20.msh (необязательно). Текущий FEM-код не запускается.
Используются уже установленные Python, NumPy и tools/p10z_mesh_shell_audit.py
из коммита 623ed568... и выше. Скрипт создаёт новую папку P10Z_RUNS
и архив RUN_H4W4B2...zip в G:\ildar\PORE_CHATGPT_EXPORTS.
Передать ChatGPT только новый архив ZIP; повторно исходники не нужны.
Ориентир: несколько минут, память ~1 GiB; зависит от локального диска.
Если закрыли окно, см. logs/P10Z_REFINED_*.log.
Если сетка не существует — отмените выбор; не создавайте новую сетку
без отдельного решения и не изменяйте исходные .msh.

Важно: этот архив только обновляет PORE ONE CLICK. НОВЫЙ Git-патч здесь не требуется.
Не применяйте ранее зарегистрированный P10Z-патч повторно.
