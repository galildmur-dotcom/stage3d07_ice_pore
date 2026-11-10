#include "stage3d10s_run_manifest.hpp"
#include <iostream>
#include <iterator>

using namespace ice3d::stage3d10s_manifest;
int main(int argc, char** argv) {
  set_arguments(argc, argv);
  const auto require = [](bool ok, const char* name) {
    if (!ok) throw std::runtime_error(std::string("Manifest unit failed: ") + name);
  };
  const auto hash_text = [](const std::string& text) {
    Sha256 sha;
    sha.update(reinterpret_cast<const std::uint8_t*>(text.data()), text.size());
    return sha.finish_hex();
  };
  require(hash_text("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "SHA256 empty");
  require(hash_text("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "SHA256 abc");
  require(hash_text(std::string(1000000, 'a')) ==
         "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0", "SHA256 million a");
  const auto output = fs::temp_directory_path() /
    ("ice3d_manifest_selftest_" + std::to_string(
      std::chrono::steady_clock::now().time_since_epoch().count()));
  fs::create_directory(output);
  const auto mesh = output / "mesh.msh";
  { std::ofstream f(mesh, std::ios::binary); f << "abc"; }
  {
    RunManifest guard(output, mesh, {2.5}, 150, 6, "y20", 4, 5.,
                      false, {}, {});
    guard.complete(0);
  }
  const auto failed_output = output / "failed";
  fs::create_directory(failed_output);
  try {
    RunManifest guard(failed_output, mesh, {2.5}, 150, 6, "y20", 4, 5.,
                      false, {}, {});
    throw std::runtime_error("Simulated compute error");
  } catch (const std::runtime_error&) {
    // The guard must write failed_exception without replacing the original error.
  }
  const auto read = [](const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(input), {});
  };
  const auto success = read(output / "RUN_MANIFEST.json");
  const auto failure = read(failed_output / "RUN_MANIFEST.json");
  require(success.find("\"status\": \"completed\"") != std::string::npos, "completed status");
  require(success.find("\"mesh_sha256\": \"ba7816bf") != std::string::npos, "SHA256 in JSON");
  require(failure.find("\"status\": \"failed_exception\"") != std::string::npos, "exception status");
  std::cout << "P10S_MANIFEST_UNIT_OK " << output.string() << '\n';
}
