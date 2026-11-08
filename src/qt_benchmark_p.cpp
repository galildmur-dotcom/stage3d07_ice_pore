// Qt Creator native launch target: no PowerShell, no Python, no external mesh generator.
// Assumes the already-built thermal and spatial solvers live next to this executable.
#include "qt_runner_paths.hpp"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#  define NOMINMAX
#  include <windows.h>
#else
#  include <cerrno>
#  include <cstring>
#  include <sys/types.h>
#  include <sys/wait.h>
#  include <unistd.h>
#endif
namespace fs = std::filesystem;
namespace {
struct Options {
#if defined(STAGE3D06P_P3_H4_DEFAULT)
    std::string mesh = "H4", law = "EDV", modulus = "VAR";
    int dt = 300, tend = 300;
#elif defined(STAGE3D06P_P3_H0_DEFAULT)
    std::string mesh = "H0", law = "EDV", modulus = "VAR";
    int dt = 300, tend = 300;
#elif defined(STAGE3D06_H1_QP_POST_DEFAULT)
    std::string mesh = "H1", law = "EDV", modulus = "VAR";
    int dt = 300, tend = 3600;
#elif defined(STAGE3D06_H2_QP_POST_DEFAULT)
    std::string mesh = "H2", law = "EDV", modulus = "VAR";
    int dt = 300, tend = 3600;
#elif defined(STAGE3D06_H0_DT75_DEFAULT)
    std::string mesh = "H0", law = "EDV", modulus = "VAR";
    int dt = 75, tend = 3600;
#elif defined(STAGE3D06_H0_DT150_DEFAULT)
    std::string mesh = "H0", law = "EDV", modulus = "VAR";
    int dt = 150, tend = 3600;
#elif defined(STAGE3D06_H0_DT300_DEFAULT)
    std::string mesh = "H0", law = "EDV", modulus = "VAR";
    int dt = 300, tend = 3600;
#elif defined(STAGE3D06_H1_DT75_DEFAULT)
    std::string mesh = "H1", law = "EDV", modulus = "VAR";
    int dt = 75, tend = 3600;
#elif defined(STAGE3D06_H1_DT150_DEFAULT)
    std::string mesh = "H1", law = "EDV", modulus = "VAR";
    int dt = 150, tend = 3600;
#elif defined(STAGE3D06_H2_DT150_DEFAULT)
    std::string mesh = "H2", law = "EDV", modulus = "VAR";
    int dt = 150, tend = 3600;
#elif defined(STAGE3D06_SMOKE_DEFAULT)
    std::string mesh = "H0", law = "E", modulus = "CONST";
    int dt = 300, tend = 300;
#elif defined(STAGE3D06_H1_DEFAULT)
    // Full H1 spatial-convergence run: matches H0/H2 dt, law and quadrature.
    std::string mesh = "H1", law = "EDV", modulus = "VAR";
    int dt = 300, tend = 3600;
#else
    std::string mesh = "H0", law = "EDV", modulus = "VAR";
    int dt = 300, tend = 600;
#endif
    int quad = 3;
#ifdef STAGE3D06P_NO_OPENMP
    int threads = 1;
#else
    int threads = 4;
#endif
#if defined(STAGE3D06P_P5_RUN_AS0)
    std::string pc = "as0";
#elif defined(STAGE3D06P_P5_RUN_AS1)
    std::string pc = "as1";
#elif defined(STAGE3D06P_P4_RUN_IC0)
    std::string pc = "ic0";
#elif defined(STAGE3D06P_P31_RUN_MCSGS_FAST)
    std::string pc = "mcsgs-fast";
#elif defined(STAGE3D06P_P3_RUN_MCSGS)
    std::string pc = "mcsgs";
#else
    std::string pc = "jacobi";
#endif
    int schwarzCore = 32;
    #ifdef STAGE3D06P_P2_RUN_LEGACY
    std::string spmv = "legacy";
#else
    std::string spmv = "projected";
#endif
    bool assemblyParallel = true;

    bool dry_run = false, clean = false;
#if defined(STAGE3D06_H1_QP_POST_DEFAULT) || defined(STAGE3D06_H2_QP_POST_DEFAULT)
    bool diag_only = true;
#else
    bool diag_only = false;
#endif
};
int get_integer(const std::string& text, const std::string& flag) {
    std::size_t consumed = 0;
    int n = 0;
    try { n = std::stoi(text, &consumed); }
    catch (...) { throw std::runtime_error("Invalid integer for " + flag + ": " + text); }
    if (consumed != text.size()) throw std::runtime_error("Invalid integer for " + flag + ": " + text);
    return n;
}
Options parse(int argc, char** argv) {
    Options c;
    for (int i = 1; i < argc; ++i) {
        const std::string flag = argv[i];
        auto val = [&]() -> std::string {
            if (i + 1 >= argc) throw std::runtime_error("Missing value after " + flag);
            return argv[++i];
        };
        if (flag == "--mesh") c.mesh = val();
        else if (flag == "--law") c.law = val();
        else if (flag == "--modulus") c.modulus = val();
        else if (flag == "--dt") c.dt = get_integer(val(), flag);
        else if (flag == "--tend") c.tend = get_integer(val(), flag);
        else if (flag == "--quad") c.quad = get_integer(val(), flag);
        else if (flag == "--threads") c.threads = get_integer(val(), flag);
        else if (flag == "--preconditioner") c.pc = val();
        else if (flag == "--schwarz-core") c.schwarzCore = get_integer(val(),flag);
        else if (flag == "--spmv") c.spmv = val();
        else if (flag == "--assembly-serial") c.assemblyParallel = false;
        else if (flag == "--dry-run") c.dry_run = true;
        else if (flag == "--clean") c.clean = true;
        else if (flag == "--diagnose-only") c.diag_only = true;
        else if (flag == "--help" || flag == "-h") {
            std::cout << "Stage3D06 Qt Creator runner (CPU).\n"
                << "  Qt-run defaults: H2, EDV, VAR, dt=300, tend=3600.\n"
                << "  Qt-check defaults: H0, E, CONST, dt=300, tend=300.\n"
                << "  Qt-H1 defaults: H1, EDV, VAR, dt=300, tend=3600.\n"
                << "  Convergence targets: H0 dt300/150/75, H1 dt150/75, H2 dt150.\n"
                << "  --mesh H0|H1|H2|H3|H4 --law E|ED|EDV|ALL --modulus CONST|VAR|ALL\n"
                << "  --dt 300 --tend 3600 --quad 3|4 --dry-run --clean --diagnose-only\n"
                << "  --threads 1|2|4|8 --preconditioner jacobi|sgs|mcsgs|mcsgs-fast|ic0|as0|as1 --schwarz-core 32 --spmv legacy|projected\n"
                << "  --assembly-serial\n"
                "  Output in project/LOCAL_RUNS_OPTIMIZED/. No PowerShell required.\n";
            std::exit(0);
        }
        else throw std::runtime_error("Unknown argument: " + flag);
    }
    if (c.mesh != "H0" && c.mesh != "H1" && c.mesh != "H2" && c.mesh != "H3" && c.mesh != "H4")
        throw std::runtime_error("Expected --mesh H0|H1|H2|H3|H4");
    if (c.law != "E" && c.law != "ED" && c.law != "EDV" && c.law != "ALL")
        throw std::runtime_error("Expected --law E|ED|EDV|ALL");
    if (c.modulus != "CONST" && c.modulus != "VAR" && c.modulus != "ALL")
        throw std::runtime_error("Expected --modulus CONST|VAR|ALL");
    if (c.dt <= 0 || c.tend <= 0 || c.tend % c.dt)
        throw std::runtime_error("Positive integral dt and tend with tend divisible by dt required");
    if(c.threads<1||c.threads>32)throw std::runtime_error("threads must be 1..32");
    if(c.pc!="jacobi"&&c.pc!="sgs"&&c.pc!="mcsgs"&&c.pc!="mcsgs-fast"&&c.pc!="ic0"&&c.pc!="as0"&&c.pc!="as1")throw std::runtime_error("preconditioner jacobi|sgs|mcsgs|mcsgs-fast");
    if(c.schwarzCore<1||c.schwarzCore>1024)throw std::runtime_error("--schwarz-core must be 1..1024");
    if(c.spmv!="legacy"&&c.spmv!="projected")throw std::runtime_error("spmv legacy|projected");
    if (c.quad != 3 && c.quad != 4) throw std::runtime_error("Expected --quad 3|4");
    if (c.clean && c.dry_run) throw std::runtime_error("--clean cannot be combined with --dry-run");
    if (c.clean && c.diag_only) throw std::runtime_error("--clean prohibited in diagnostic-only mode");
    return c;
}
#ifdef _WIN32
std::wstring windows_quote(const std::wstring& s) {
    // Windows CRT quoting rules: quote whitespace, escape backslashes before quotes/end.
    std::wstring out = L"\"";
    std::size_t slash = 0;
    for (wchar_t ch : s) {
        if (ch == L'\\') { ++slash; continue; }
        if (ch == L'"') { out.append(slash * 2 + 1, L'\\'); out += L'"'; slash = 0; continue; }
        out.append(slash, L'\\'); slash = 0; out += ch;
    }
    out.append(slash * 2, L'\\');
    return out + L'"';
}
int run_process(const fs::path& exe, const std::vector<fs::path>& args) {
    std::wstring cmd = windows_quote(exe.wstring());
    for (const auto& a : args) cmd += L" " + windows_quote(a.wstring());
    std::vector<wchar_t> buffer(cmd.begin(), cmd.end()); buffer.push_back(L'\0');
    STARTUPINFOW si{}; si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    // No shell, powershell.exe, cmd.exe, or PATH lookup is needed.
    if (!CreateProcessW(exe.c_str(), buffer.data(), nullptr, nullptr, TRUE, 0,
                        nullptr, nullptr, &si, &pi)) {
        throw std::runtime_error("CreateProcessW failed (code " + std::to_string(GetLastError()) +
                                 "): " + exe.string());
    }
    CloseHandle(pi.hThread);
    DWORD wait = WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD result = 1;
    const BOOL ok = GetExitCodeProcess(pi.hProcess, &result);
    CloseHandle(pi.hProcess);
    if (wait != WAIT_OBJECT_0 || !ok)
        throw std::runtime_error("Cannot wait for child process " + exe.string());
    return static_cast<int>(result);
}
#else
int run_process(const fs::path& exe, const std::vector<fs::path>& args) {
    const pid_t child = fork();
    if (child < 0) throw std::runtime_error("fork failed: " + std::string(std::strerror(errno)));
    if (child == 0) {
        std::vector<std::string> argv_storage; argv_storage.reserve(args.size() + 1);
        argv_storage.push_back(exe.string());
        for (const auto& a : args) argv_storage.push_back(a.string());
        std::vector<char*> raw; raw.reserve(argv_storage.size() + 1);
        for (auto& a : argv_storage) raw.push_back(a.data());
        raw.push_back(nullptr);
        execv(exe.c_str(), raw.data());
        std::cerr << "execv failed: " << exe << ": " << std::strerror(errno) << '\n';
        _exit(127);
    }
    int status = 0;
    while (waitpid(child, &status, 0) < 0) {
        if (errno == EINTR) continue;
        throw std::runtime_error("waitpid failed");
    }
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    return 128;
}
#endif
void checked_run(const fs::path& exe, const std::vector<fs::path>& args) {
    std::cout << "\n[RUN] " << exe.filename().string() << '\n' << std::flush;
    const int code = run_process(exe, args);
    if (code != 0) throw std::runtime_error(exe.filename().string() + " returned exit code " + std::to_string(code));
}
std::string csv_times(int dt, int tend) {
    std::string out;
    for (int t = dt; t <= tend; t += dt) {
        if (!out.empty()) out += ',';
        out += std::to_string(t);
    }
    return out;
}
bool thermal_complete(const fs::path& dir, int dt, int tend) {
    if (!fs::is_regular_file(dir / "summary.csv")) return false;
    for (int t = dt; t <= tend; t += dt) {
        const fs::path f = dir / ("thermal_" + std::to_string(t) + "s.vtu");
        if (!fs::is_regular_file(f) || fs::file_size(f) == 0) return false;
    }
    return true;
}
fs::path sibling_executable(const fs::path& self, const std::string& stem) {
#ifdef _WIN32
    return self.parent_path() / (stem + ".exe");
#else
    return self.parent_path() / stem;
#endif
}
}
int main(int argc, char** argv) {
    fs::path status_file;
    try {
        const auto opts = parse(argc, argv);
        const fs::path root = fs::path(STAGE3D06_ROOT_DIR);
        const fs::path self = fs::absolute(fs::path(argv[0]));
        const fs::path mesh = root / "meshes" / (opts.mesh + ".msh");
        const fs::path heat = sibling_executable(self, "stage3d02_thermal");
#ifdef STAGE3D06P_RUN_BASELINE
        const fs::path mech = sibling_executable(self, "stage3d06_baseline_serial");
        const std::string category = "benchmark_baseline";
#elif defined(STAGE3D06P_P2_RUN_LEGACY)
        const fs::path mech = sibling_executable(self, "stage3d06_spatial");
        const std::string category = "benchmark_p2_legacy";
#elif defined(STAGE3D06P_P5_RUN_AS0)
        const fs::path mech = sibling_executable(self, "stage3d06_spatial");
        const std::string category = "benchmark_p5_as0";
#elif defined(STAGE3D06P_P5_RUN_AS1)
        const fs::path mech = sibling_executable(self, "stage3d06_spatial");
        const std::string category = "benchmark_p5_as1";
#elif defined(STAGE3D06P_P4_RUN_IC0)
        const fs::path mech = sibling_executable(self, "stage3d06_spatial");
        const std::string category = "benchmark_p4_ic0";
#elif defined(STAGE3D06P_P31_RUN_MCSGS_FAST)
        const fs::path mech = sibling_executable(self, "stage3d06_spatial");
        const std::string category = "benchmark_p31_mcsgs_fast";
#elif defined(STAGE3D06P_P3_RUN_MCSGS)
        const fs::path mech = sibling_executable(self, "stage3d06_spatial");
        const std::string category = "benchmark_p3_mcsgs";
#elif defined(STAGE3D06P_P2_RUN_PROJECTED)
        const fs::path mech = sibling_executable(self, "stage3d06_spatial");
        const std::string category = "benchmark_p2_projected";
#elif defined(STAGE3D06P_RUN_CAMPAIGN)
        const fs::path mech = sibling_executable(self, "stage3d06_spatial");
        const std::string category = "campaign_optimized";
#else
        const fs::path mech = sibling_executable(self, "stage3d06_spatial");
        const std::string category = "benchmark_optimized";
#endif
        const fs::path out = root / "LOCAL_RUNS_OPTIMIZED" / category /
            (opts.mesh + "_dt" + std::to_string(opts.dt) + "_q" + std::to_string(opts.quad));
        const fs::path thermal_dir = out / "thermal";
        const fs::path mechanics_dir = out / "mechanics";
        std::cout << "\n=== Stage3D06: Qt Creator native FEM run ===\n"
                  << "Mesh: " << opts.mesh << ", model: " << opts.law << '_' << opts.modulus
                  << ", dt=" << opts.dt << " s, tend=" << opts.tend
                  << " s, quadrature=" << opts.quad << "\n"
                  << "SpMV: " << opts.spmv << ", preconditioner: " << opts.pc << ", threads: " << opts.threads << "\n"
                  << "Source: " << root << '\n' << "Output: " << out << "\n"
                  << "Thermal exe: " << heat << '\n' << "Mechanical exe: " << mech << '\n'
                  << std::flush;
        for (const auto& p : {mesh, heat, mech})
            if (!fs::is_regular_file(p)) throw std::runtime_error("Missing file: " + p.string());
        if (opts.dry_run) {
            std::cout << "DRY RUN PASS: inputs and binaries exist; solvers were not executed.\n";
            return 0;
        }
        if (opts.diag_only) {
            if (opts.law == "ALL" || opts.modulus == "ALL")
                throw std::runtime_error("diagnose-only expects a single law and modulus");
            const auto dest = mechanics_dir / (opts.law + "_" + opts.modulus);
            for(const auto& req:{dest / "restart.bin",
                                 thermal_dir / ("thermal_" + std::to_string(opts.tend) + "s.vtu")})
                if (!fs::is_regular_file(req))throw std::runtime_error("Required finished H1/H2 data missing: " + req.string());
            std::cout << "[DIAGNOSTICS] No thermal or mechanical timestepping. Reconstructing final QP stresses from checkpoint.\n" << std::flush;
            checked_run(mech, {"--mesh",mesh,"--temp-dir",thermal_dir,"--out",mechanics_dir,
                               "--law",opts.law,"--modulus",opts.modulus,
                               "--times",csv_times(opts.dt,opts.tend),"--quad",std::to_string(opts.quad),
                               "--postprocess-only"});
            std::cout << "SUCCESS: QP diagnostics placed alongside existing result, original checkpoint unchanged.\n";
            return 0;
        }
        if (opts.clean) {
            std::cout << "Requested clean: remove previous scenario " << out << '\n';
            fs::remove_all(out);
        }
        fs::create_directories(out);
        const fs::path report = out / "QT_RUN_STATUS.txt";
        status_file = report;
        auto write_status = [&](const std::string& status) {
            std::ofstream stream(report, std::ios::trunc);
            stream << "status=" << status << '\n' << "mesh=" << opts.mesh << '\n'
                   << "law=" << opts.law << '\n' << "modulus=" << opts.modulus << '\n'
                   << "dt_s=" << opts.dt << '\n' << "tend_s=" << opts.tend << '\n'
                   << "quad=" << opts.quad << '\n' << "preconditioner=" << opts.pc << '\n' << "schwarz_core=" << opts.schwarzCore << '\n' << "spmv=" << opts.spmv << '\n' << "threads=" << opts.threads << '\n' << "output=" << out.string() << '\n';
        };
        write_status("RUNNING");
        // --every-step is required: the spatial solver loads one VTU per time step.
        if (!thermal_complete(thermal_dir, opts.dt, opts.tend)) {
            std::cout << "[1/2] Calculating full thermal history...\n" << std::flush;
            checked_run(heat, {"--mesh", mesh, "--out", thermal_dir,
                               "--dt", std::to_string(opts.dt), "--tend", std::to_string(opts.tend),
                               "--xi", "0", "--every-step"});
            if (!thermal_complete(thermal_dir, opts.dt, opts.tend))
                throw std::runtime_error("Thermal run exited successfully but not all VTU files exist");
        } else {
            std::cout << "[1/2] Reusing existing complete thermal history.\n" << std::flush;
        }
        std::cout << "[2/2] Solving 3D quasistatic equilibrium (checkpoint resume ON)...\n" << std::flush;
        std::vector<fs::path> mechArgs={"--mesh", mesh, "--temp-dir", thermal_dir,
                           "--out", mechanics_dir, "--law", opts.law,
                           "--modulus", opts.modulus, "--times", csv_times(opts.dt, opts.tend),
                           "--quad", std::to_string(opts.quad), "--cg-tol", "2e-7", "--resume"};
#ifndef STAGE3D06P_RUN_BASELINE
        mechArgs.insert(mechArgs.end(),{"--profile","--optimization","on","--preconditioner",opts.pc,
             "--threads",std::to_string(opts.threads),"--schwarz-core",std::to_string(opts.schwarzCore),"--spmv",opts.spmv,"--parallel-assembly",opts.assemblyParallel?"on":"off",
             "--geometry-cache","off"});
#endif
        if(opts.dt<=75)mechArgs.emplace_back("--final-vtu-only");
        checked_run(mech,mechArgs);
        write_status("SUCCESS");
        std::cout << "\nSUCCESS. Mechanical data: " << mechanics_dir << '\n'
                  << "CSV summary: " << mechanics_dir / "G06_campaign.csv" << '\n'
                  << "ParaView VTU: " << mechanics_dir / (opts.law + "_" + opts.modulus) << '\n'
                  << "Qt Creator: close run or press Run again to resume/check completion.\n" << std::flush;
        return 0;
    } catch (const std::exception& e) {
        if (!status_file.empty()) {
            std::ofstream status(status_file, std::ios::trunc);
            if (status) status << "status=FAILED\nreason=" << e.what() << "\n";
        }
        std::cerr << "\nSTAGE 3D-06 RUN FAILED: " << e.what() << '\n'
                  << "See Qt Creator Application Output. Finished checkpoints are preserved.\n";
        return 2;
    }
}
