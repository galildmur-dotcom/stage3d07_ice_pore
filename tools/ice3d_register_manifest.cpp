// Stage3D10S M02: explicit, idempotent registration of a completed FEM run.
// Standalone C++20, no Qt, Python or third-party JSON libraries required.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <locale>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace fs = std::filesystem;

void require(bool condition, const std::string& why) {
  if (!condition) throw std::runtime_error(why);
}

struct Json {
  enum Kind { Null, Boolean, Number, String, Array, Object } kind = Null;
  bool boolean = false;
  double number = 0;
  std::string string;
  std::vector<Json> array;
  std::map<std::string, Json> object;

  const Json& at(const std::string& key) const {
    require(kind == Object, "Expected JSON object at " + key);
    const auto it = object.find(key);
    require(it != object.end(), "Missing JSON key: " + key);
    return it->second;
  }
  std::string as_string(const std::string& name) const {
    require(kind == String, "Expected JSON string: " + name);
    return string;
  }
  double as_number(const std::string& name) const {
    require(kind == Number && std::isfinite(number), "Expected finite JSON number: " + name);
    return number;
  }
  bool as_bool(const std::string& name) const {
    require(kind == Boolean, "Expected JSON boolean: " + name);
    return boolean;
  }
  const std::vector<Json>& as_array(const std::string& name) const {
    require(kind == Array, "Expected JSON array: " + name);
    return array;
  }
};

class JsonParser {
  std::string_view source_;
  std::size_t pos_ = 0;
  void spaces() {
    while (pos_ < source_.size() &&
           (source_[pos_] == ' ' || source_[pos_] == '\t' ||
            source_[pos_] == '\n' || source_[pos_] == '\r')) ++pos_;
  }
  char current() const { return pos_ < source_.size() ? source_[pos_] : '\0'; }
  void expect(char c) {
    spaces();
    require(current() == c, std::string("JSON syntax: expected '") + c + "'");
    ++pos_;
  }
  bool literal(std::string_view token) {
    if (source_.substr(pos_, token.size()) == token) {
      pos_ += token.size(); return true;
    }
    return false;
  }
  int digit4() {
    require(pos_ + 4 <= source_.size(), "Truncated JSON Unicode escape");
    int code = 0;
    for (int i = 0; i < 4; ++i) {
      char c = source_[pos_++];
      int x = c >= '0' && c <= '9' ? c - '0' :
              c >= 'a' && c <= 'f' ? c - 'a' + 10 :
              c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1;
      require(x >= 0, "Invalid JSON Unicode escape");
      code = 16 * code + x;
    }
    return code;
  }
  static void unicode_utf8(std::string& out, int code) {
    require(!(code >= 0xd800 && code <= 0xdfff),
            "Unicode surrogate escapes not supported by manifest format");
    if (code < 128) out.push_back(char(code));
    else if (code < 2048) {
      out.push_back(char(0xc0 | (code >> 6)));
      out.push_back(char(0x80 | (code & 63)));
    } else {
      out.push_back(char(0xe0 | (code >> 12)));
      out.push_back(char(0x80 | ((code >> 6) & 63)));
      out.push_back(char(0x80 | (code & 63)));
    }
  }
  std::string parse_string() {
    expect('"');
    std::string out;
    while (pos_ < source_.size()) {
      const unsigned char c = static_cast<unsigned char>(source_[pos_++]);
      if (c == '"') return out;
      require(c >= 32, "Unescaped control character in JSON string");
      if (c != '\\') { out.push_back(char(c)); continue; }
      require(pos_ < source_.size(), "Truncated JSON escape");
      switch (source_[pos_++]) {
        case '"': out.push_back('"'); break;
        case '\\': out.push_back('\\'); break;
        case '/': out.push_back('/'); break;
        case 'b': out.push_back('\b'); break;
        case 'f': out.push_back('\f'); break;
        case 'n': out.push_back('\n'); break;
        case 'r': out.push_back('\r'); break;
        case 't': out.push_back('\t'); break;
        case 'u': unicode_utf8(out, digit4()); break;
        default: throw std::runtime_error("Invalid JSON string escape");
      }
    }
    throw std::runtime_error("Unterminated JSON string");
  }
  Json parse_number() {
    const std::size_t start = pos_;
    if (current() == '-') ++pos_;
    if (current() == '0') ++pos_;
    else {
      require(current() >= '1' && current() <= '9', "Invalid JSON number");
      while (current() >= '0' && current() <= '9') ++pos_;
    }
    if (current() == '.') {
      ++pos_;
      require(current() >= '0' && current() <= '9', "Invalid JSON fraction");
      while (current() >= '0' && current() <= '9') ++pos_;
    }
    if (current() == 'e' || current() == 'E') {
      ++pos_;
      if (current() == '+' || current() == '-') ++pos_;
      require(current() >= '0' && current() <= '9', "Invalid JSON exponent");
      while (current() >= '0' && current() <= '9') ++pos_;
    }
    Json result; result.kind = Json::Number;
    result.number = std::stod(std::string(source_.substr(start, pos_ - start)));
    require(std::isfinite(result.number), "Nonfinite JSON number");
    return result;
  }
  Json value(int depth) {
    require(depth < 40, "Excessive JSON nesting");
    spaces();
    if (literal("null")) return {};
    if (literal("true")) { Json j; j.kind = Json::Boolean; j.boolean = true; return j; }
    if (literal("false")) { Json j; j.kind = Json::Boolean; return j; }
    if (current() == '"') {
      Json j; j.kind = Json::String; j.string = parse_string(); return j;
    }
    if (current() == '[') {
      ++pos_; Json j; j.kind = Json::Array;
      spaces(); if (current() == ']') { ++pos_; return j; }
      while (true) {
        j.array.push_back(value(depth+1));
        spaces(); if (current() == ']') { ++pos_; return j; }
        expect(',');
      }
    }
    if (current() == '{') {
      ++pos_; Json j; j.kind = Json::Object;
      spaces(); if (current() == '}') { ++pos_; return j; }
      while (true) {
        spaces(); require(current() == '"', "Expected JSON object key");
        const auto key = parse_string();
        expect(':');
        auto inserted = j.object.emplace(key, value(depth+1));
        require(inserted.second, "Duplicate JSON key: " + key);
        spaces(); if (current() == '}') { ++pos_; return j; }
        expect(',');
      }
    }
    if (current() == '-' || (current() >= '0' && current() <= '9')) return parse_number();
    throw std::runtime_error("Invalid JSON value");
  }
public:
  explicit JsonParser(std::string_view source) : source_(source) {}
  Json parse() {
    Json j = value(0);
    spaces(); require(pos_ == source_.size(), "Trailing JSON text");
    return j;
  }
};

std::string read_text(const fs::path& path, std::uintmax_t limit = 64ULL*1024*1024) {
  std::ifstream file(path, std::ios::binary);
  require(bool(file), "Cannot open file: " + path.string());
  const auto size = fs::file_size(path);
  require(size <= limit, "Input file unexpectedly large: " + path.string());
  return std::string(std::istreambuf_iterator<char>(file), {});
}

std::string csv_field(const std::string& input) {
  if (input.find_first_of(",\r\n\"") == std::string::npos) return input;
  std::string result = "\"";
  for (char c : input) {
    if (c == '"') result += "\"\"";
    else result.push_back(c);
  }
  return result + '"';
}

std::string decimal(double value) {
  require(std::isfinite(value), "Nonfinite numeric registry field");
  std::ostringstream out; out.imbue(std::locale::classic());
  out << std::setprecision(17) << value; return out.str();
}

std::string command_line(const std::vector<Json>& argv) {
  std::string result;
  for (const auto& item : argv) {
    std::string arg = item.as_string("argv[]");
    require(arg.find_first_of("\n\r\0", 0, 3) == std::string::npos,
            "Multiline/NUL argument cannot enter registry");
    if (!result.empty()) result += ' ';
    if (arg.find_first_of(" \t\"") == std::string::npos) result += arg;
    else {
      result += '"';
      for (char c : arg) { if (c == '"') result += '\\'; result += c; }
      result += '"';
    }
  }
  return result;
}

constexpr std::array<std::string_view, 20> registry_columns{{
  "run_id", "run_date", "stage", "mesh", "model", "temperature_model",
  "gh_rule", "dt_s", "steps", "geometry_mode", "delta_um", "git_commit",
  "command_line", "raw_path_G", "archive_path_F", "mesh_sha256",
  "execution_status", "verification_status", "wall_s", "notes"}};

std::string expected_header() {
  std::string result;
  for (auto key : registry_columns) { if (!result.empty()) result += ','; result += key; }
  return result;
}

bool hex_sha256(const std::string& source) {
  return source.size() == 64 && std::all_of(source.begin(), source.end(), [](char c) {
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
           (c >= 'A' && c <= 'F');
  });
}

struct Record {
  std::string run_id;
  std::string csv_line;
  fs::path output_dir;
};

// The registered results are the six outputs of the P10S completed branch.
constexpr std::array<std::string_view, 6> required_outputs{{
  "P10N_DELTA_SCAN.csv", "P10P_PARTIAL_COMPONENTS.csv", "P10P_STEP_COMPONENTS.csv",
  "P10S_PARTITION_AUDIT.csv", "P10S_SHELL_SUMMARY.csv", "P10S_STEP_SHELL_COMPONENTS.csv"}};

Record make_record(const Json& manifest, const fs::path& manifest_path) {
  require(manifest.at("schema_version").as_number("schema_version") == 1,
          "Unsupported RUN_MANIFEST schema version");
  require(manifest.at("program").as_string("program") == "stage3d10s_spatial_partial",
          "Only Stage3D10S manifests are supported");
  const auto status = manifest.at("status").as_string("status");
  require(status == "completed", "NOT_REGISTERED: status=" + status);
  require(manifest.at("exit_code").as_number("exit_code") == 0,
          "NOT_REGISTERED: nonzero exit code");
  const auto& input = manifest.at("input");
  require(!input.at("preflight").as_bool("preflight"),
          "NOT_REGISTERED: preflight is not a scientific run");
  const std::string run_id = manifest.at("run_id").as_string("run_id");
  require(!run_id.empty() && run_id.size() <= 150 &&
          std::all_of(run_id.begin(), run_id.end(), [](unsigned char c) {
            return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                   (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.';
          }), "Invalid run_id");
  const fs::path output_dir(input.at("output_dir").as_string("output_dir"));
  require(fs::is_directory(output_dir), "Output directory missing: " + output_dir.string());
  require(output_dir.filename() == fs::path(run_id), "run_id != output folder name");
  require(fs::equivalent(fs::absolute(output_dir), fs::absolute(manifest_path.parent_path())),
          "Manifest must be read from its own output folder");
  const auto& products = manifest.at("produced_files").as_array("produced_files");
  for (const auto required : required_outputs) {
    const std::string filename(required);
    const bool listed = std::any_of(products.begin(), products.end(), [&](const Json& j) {
      return j.as_string("produced_files[]") == filename;
    });
    require(listed, "Missing output in manifest: " + filename);
    require(fs::is_regular_file(output_dir / filename),
            "Missing recorded output file: " + filename);
  }

  const auto& code = manifest.at("code");
  const auto git_at_config = code.at("git_commit_at_cmake_configure").as_string("git SHA");
  const auto exe_hash = code.at("executable_sha256");
  const auto mesh_hash = input.at("mesh_sha256").as_string("mesh_sha256");
  require(hex_sha256(mesh_hash), "Missing/invalid mesh SHA256");
  std::string executable_hash;
  if (exe_hash.kind != Json::Null) {
    executable_hash = exe_hash.as_string("executable_sha256");
    require(hex_sha256(executable_hash), "Invalid executable SHA256");
  }

  const auto& deltas = input.at("delta_um").as_array("delta_um");
  require(!deltas.empty(), "Empty delta_um list");
  std::vector<std::string> delta_strings;
  for (const auto& x : deltas) delta_strings.push_back(decimal(x.as_number("delta_um[]")));
  const std::string delta_column = deltas.size() == 1 ? delta_strings.front() : "";
  std::string delta_note;
  if (deltas.size() != 1) {
    delta_note = "delta_scan_um=";
    for (std::size_t i = 0; i < delta_strings.size(); ++i) {
      if (i) delta_note += '|';
      delta_note += delta_strings[i];
    }
    delta_note += "; ";
  }

  const std::string started = manifest.at("started_at_utc").as_string("started_at_utc");
  require(started.size() >= 20 && started[4] == '-' && started[7] == '-' &&
          started[10] == 'T' && started.back() == 'Z', "Invalid UTC start time");
  const auto mesh_path = fs::path(input.at("mesh").as_string("mesh"));
  const auto model = input.at("model").as_string("model");
  const auto temp_model = input.at("temperature_model").as_string("temperature_model");
  require(model == "EDV" && temp_model == "VAR", "Unexpected P10S material model");
  std::string gh_rule;
  const auto& gh = input.at("stochastic_quadrature");
  if (gh.kind != Json::Null) gh_rule = gh.as_string("stochastic_quadrature");

  std::string notes = "auto_registered_from_MANIFEST_v1; UTC_start; " + delta_note;
  notes += "wall_s=elapsed_after_output_directory; ";
  notes += "git_configure_sha=" + git_at_config + " (not verified as clean build); ";
  if (!executable_hash.empty()) notes += "exe_sha256=" + executable_hash + "; ";
  notes += "archive_F_unverified; scientific_convergence_not_established";

  const std::array<std::string,20> columns{{
    run_id, started.substr(0,10), "P10S", mesh_path.stem().string(), model,
    temp_model, gh_rule, decimal(input.at("dt_s").as_number("dt_s")),
    decimal(input.at("steps").as_number("steps")),
    input.at("geometry_mode").as_string("geometry_mode"), delta_column,
    "", // Git commit field is intentionally blank: configure-time SHA may be stale.
    command_line(manifest.at("argv").as_array("argv")), output_dir.string(),
    "", mesh_hash, "COMPLETED", "P10N_P10P_P10S_BUILTIN_AUDITS_OK;INDEPENDENT_NOT_DONE",
    decimal(manifest.at("elapsed_manifest_wall_s").as_number("elapsed_manifest_wall_s")),
    notes}};
  std::string line;
  for (const auto& value : columns) {
    if (!line.empty()) line += ',';
    line += csv_field(value);
  }
  return {run_id, line, output_dir};
}

struct RegistryLock {
  fs::path path;
  explicit RegistryLock(const fs::path& registry) : path(registry.string() + ".lock") {
    require(fs::create_directory(path),
            "Registry lock already exists: " + path.string());
  }
  ~RegistryLock() { std::error_code ec; fs::remove(path,ec); }
  RegistryLock(const RegistryLock&) = delete;
  RegistryLock& operator=(const RegistryLock&) = delete;
};

enum class Registration { Added, AlreadyExists, DryRun };

Registration register_record(const Record& record, const fs::path& registry,
                             bool dry_run) {
  require(fs::is_regular_file(registry), "Registry CSV does not exist: " + registry.string());
  std::optional<RegistryLock> lock;
  if (!dry_run) lock.emplace(registry);
  const std::string original = read_text(registry);
  const std::size_t eol = original.find('\n');
  require(eol != std::string::npos, "Registry must contain a header with newline");
  std::string header = original.substr(0, eol);
  if (!header.empty() && header.back() == '\r') header.pop_back();
  require(header == expected_header(), "RUN_REGISTRY.csv has a different column schema");
  require(original.back() == '\n', "Registry must end with a newline");
  std::istringstream in(original);
  std::string line;
  std::getline(in,line); // skip header
  while (std::getline(in,line)) {
    if (!line.empty() && line.substr(0,line.find(',')) == record.run_id)
      return Registration::AlreadyExists;
  }
  if (dry_run) return Registration::DryRun;
  const fs::path pending = registry.string() + ".pending";
  require(!fs::exists(pending), "Stale registry .pending exists: " + pending.string());
  std::ofstream out(pending,std::ios::binary);
  require(bool(out), "Cannot write temporary registry");
  const bool crlf = eol > 0 && original[eol-1] == '\r';
  out.write(original.data(), static_cast<std::streamsize>(original.size()));
  out << record.csv_line << (crlf ? "\r\n" : "\n");
  out.close();
  require(bool(out), "Incomplete registry write");
  fs::rename(pending,registry);
  return Registration::Added;
}

void selftest() {
  const fs::path parent = fs::temp_directory_path() / ("ice3d_registry_selftest_" +
     std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
  require(fs::create_directory(parent), "Test folder creation failed");
  const fs::path run = parent / "P10S_TEST";
  fs::create_directory(run);
  const auto registry = parent / "RUN_REGISTRY.csv";
  { std::ofstream f(registry); f << expected_header() << '\n'; }
  for (auto name : required_outputs) {
    std::ofstream f(run / std::string(name)); f << "test\n";
  }
  const std::string original = R"({"schema_version":1,"run_id":"P10S_TEST","program":"stage3d10s_spatial_partial","status":"completed","started_at_utc":"2026-11-10T09:00:00Z","exit_code":0,"elapsed_manifest_wall_s":2.5,"code":{"git_commit_at_cmake_configure":"UNKNOWN","executable_sha256":null},"input":{"mesh":"G:/meshes/H0.msh","mesh_sha256":"e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8","output_dir":"OUTPUT_PATH","model":"EDV","temperature_model":"VAR","stochastic_quadrature":null,"dt_s":150,"steps":6,"geometry_mode":"y20","delta_um":[2.5],"preflight":false},"argv":["G:/Program Files/prog.exe","--mesh","G:/meshes/H0.msh"],"produced_files":["P10N_DELTA_SCAN.csv","P10P_PARTIAL_COMPONENTS.csv","P10P_STEP_COMPONENTS.csv","P10S_PARTITION_AUDIT.csv","P10S_SHELL_SUMMARY.csv","P10S_STEP_SHELL_COMPONENTS.csv"]})";
  const std::string token="OUTPUT_PATH";
  std::string sample=original;
  const auto pos=sample.find(token);
  require(pos!=std::string::npos,"Selftest missing placeholder");
  sample.replace(pos,token.size(),run.generic_string());
  const auto manifest_path = run / "RUN_MANIFEST.json";
  { std::ofstream f(manifest_path); f << sample; }
  const auto parsed=JsonParser(read_text(manifest_path)).parse();
  const auto row=make_record(parsed,manifest_path);
  require(register_record(row,registry,true)==Registration::DryRun,"dry run");
  require(register_record(row,registry,false)==Registration::Added,"first insertion");
  const auto after=read_text(registry);
  require(after.find("P10S_TEST,")!=std::string::npos,"registry row missing");
  require(register_record(row,registry,false)==Registration::AlreadyExists,"idempotence");
  require(read_text(registry)==after,"duplicate changed registry bytes");
  Json preflight=parsed;
  preflight.object["status"].string="preflight_ok";
  try { (void)make_record(preflight,manifest_path); throw std::runtime_error("preflight incorrectly accepted"); }
  catch(const std::runtime_error& e) {
    require(std::string(e.what()).find("NOT_REGISTERED")!=std::string::npos,
            "preflight rejection");
  }
  Json missing=parsed;
  missing.object["produced_files"].array.pop_back();
  try { (void)make_record(missing,manifest_path); throw std::runtime_error("missing output accepted"); }
  catch(const std::runtime_error& e) {
    require(std::string(e.what()).find("Missing output")!=std::string::npos,
            "missing diagnostic rejection");
  }
  std::cout << "ICE3D_REGISTRY_UNIT_OK " << parent.string() << '\n';
}

int main(int argc,char** argv) {
  try {
    fs::path manifest,registry;
    bool dry_run=false,self_test=false;
    for (int i=1;i<argc;++i) {
      const std::string arg=argv[i];
      if(arg=="--help") {
        std::cout << "ice3d_register_manifest --manifest PATH --registry PATH [--dry-run]\n"
                     "ice3d_register_manifest --selftest\n";
        return 0;
      }
      if(arg=="--selftest") self_test=true;
      else if(arg=="--dry-run") dry_run=true;
      else if(arg=="--manifest"||arg=="--registry") {
        require(i+1<argc,"Missing path after "+arg);
        (arg=="--manifest"?manifest:registry)=argv[++i];
      } else throw std::runtime_error("Unexpected option: "+arg);
    }
    if (self_test) { selftest(); return 0; }
    require(!manifest.empty()&&!registry.empty(),"Both --manifest and --registry are required");
    require(fs::is_regular_file(manifest),"RUN_MANIFEST.json not found");
    const auto data=JsonParser(read_text(manifest, 1024 * 1024)).parse();
    if (data.at("status").as_string("status") == "preflight_ok") {
      std::cout << "ICE3D_REGISTRY_SKIPPED_PREFLIGHT (registry unchanged)\n";
      return 0;
    }
    const auto record=make_record(data,manifest);
    const auto state=register_record(record,registry,dry_run);
    std::cout << (state==Registration::Added ? "ICE3D_REGISTRY_ADDED " :
                  state==Registration::AlreadyExists ? "ICE3D_REGISTRY_ALREADY_EXISTS " :
                  "ICE3D_REGISTRY_DRY_RUN_OK ") << record.run_id << '\n';
    return 0;
  } catch(const std::exception& e) {
    std::cerr << "ICE3D_REGISTRY_ERROR: " << e.what() << '\n';
    return 2;
  }
}
