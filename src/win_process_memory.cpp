// Stage3D06: Windows-only memory monitor, built as an isolated translation unit.
// Do not include windows.h from a C++ TU that has `using namespace std;`
// or defines identifiers that conflict with macros from the Windows SDK.
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <psapi.h>
#include <climits>
#include <cstdint>

extern "C" long stage3d06_peak_memory_kb_windows() {
    PROCESS_MEMORY_COUNTERS counters{};
    if (!GetProcessMemoryInfo(GetCurrentProcess(), &counters,
                              static_cast<DWORD>(sizeof(counters)))) {
        return 0;
    }
    const auto kib = static_cast<std::uint64_t>(counters.PeakWorkingSetSize) / 1024u;
    return kib > static_cast<std::uint64_t>(LONG_MAX) ? LONG_MAX : static_cast<long>(kib);
}
