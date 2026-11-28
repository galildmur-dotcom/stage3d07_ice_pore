# P10OW R2 launcher path fix (2026-11-27)

User observed P10OW R1 `01_P10OW_PREFLIGHT_AND_WATCHDOG_NO_FEM.cmd`:

```
P10OW_PREFLIGHT_AND_WATCHDOG_NO_FEM_START
C:\Program Files\Python313\python.exe: can't open file
'G:\Downloads\P10OW_M16_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261127\P10OW_WORK\P10OW_M16_FIRST_FULL4D.py':
[Errno 2] No such file or directory
P10OW_EXIT=2
```

**Root cause:** my packaging directory name remained `P10OP_WORK` after adapting the M15 physical archive, but both P10OW CMD launchers pointed to `P10OW_WORK`. There was no Python preflight or physical execution and no P10OW marker consumed by this failure. R1 must not be used.

**R2 fix:** rename the packaging directory to `P10OW_WORK`, matching both launchers; no change to accepted M16, numerical algorithms, 101 pinned solver sources, physics settings or one-shot guards.

**Additional actual verification:**
- Both CMD file target paths resolved to files in R2.
- Imported `P10OW_M16_FIRST_FULL4D.py` and executed its source+mesh `preflight()` on Linux with only Windows platform assertion replaced with a no-op (not a native Windows run); preflight printed PASS, 101 solver pins, exact accepted M16 SHA, Tet10 21683, dt25 ×36.
- ZIP CRC and correct entry paths verified. Native Windows watchdog selftest and FEM have **not** been executed here.

R2 ZIP: `P10OW_R2_M16_FIRST_FULL4D_WINDOWS_ONE_SHOT_FIXED_20261127.zip`
SHA-256 `a11248beb4f458b6d16672fe3e19adb2ce7a98ff64b04da9dbf213dc07114228`
[Download R2](https://chatgpt.com/library?file_id=libfile_7d11658a7af08191912b3e05fbdd80f1&account_id=personal)

User should extract R2 into a fresh folder, run 01 first, then 02 **once** only after preflight passes. On actual run failure do not retry 02, return evidence or logs.
