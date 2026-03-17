#include <functional>
#include <iostream>
#include <optional>

struct CLISettings {
    // zero args
    bool help{false};
    // one args
    std::optional<std::string> impl; // serial,omp,cuda
    std::optional<int16_t> threads; // for omp
    std::optional<int16_t> block_size; // for CUDA
    std::optional<int16_t> grid_size; // for CUDA
    std::optional<int16_t> repeats; //  for averaging
    std::optional<u_int32_t> size; // for array size
    std::optional<u_int32_t> seed; // for distribution
    std::optional<std::string> distribution; // uniform, gaussian, nearly_sorted, reversed
    std::optional<std::string> output; //for CSV/plots
};

/**
 * We can also use a function pointer here, ie:
 * typedef void (*NoArgHandle)(CLISettings&);
 *
 * If we're only ever going to use plain functions
 * or capture-less lambdas as handles, the plain
 * function pointer is good and marginally more performant.
 */

typedef std::function<void(CLISettings &)> NoArgHandle;
typedef std::function<void(CLISettings &, const std::string &)> OneArgHandle;

const std::unordered_map<std::string, NoArgHandle> NoArgs{
    {"--help", [](CLISettings &s) { s.help = true; }},
    {"-h", [](CLISettings &s) { s.help = true; }},
};
const std::unordered_map<std::string, OneArgHandle> OneArgs{
    {"--impl", [](CLISettings &s, const std::string &arg) { s.impl = arg; }},
    {"--threads", [](CLISettings &s, const std::string &arg) { s.threads = std::stoi(arg); }},
    {"--block_size", [](CLISettings &s, const std::string &arg) { s.block_size = std::stoi(arg); }},
    {"--grid_size", [](CLISettings &s, const std::string &arg) { s.grid_size = std::stoi(arg); }},
    {"--repeats", [](CLISettings &s, const std::string &arg) { s.repeats = std::stoi(arg); }},
    {"--size", [](CLISettings &s, const std::string &arg) { s.size = std::stoul(arg); }},
    {"--seed", [](CLISettings &s, const std::string &arg) { s.seed = std::stoul(arg); }},
    {"--distribution", [](CLISettings &s, const std::string &arg) { s.distribution = arg; }},
    {"--output", [](CLISettings &s, const std::string &arg) { s.output = arg; }},
};

CLISettings parse_settings(int argc, const char *argv[]) {
    CLISettings settings;
    for (int i = 1; i < argc; i++) {
        std::string opt = argv[i];

        if (auto j = NoArgs.find(opt); j != NoArgs.end())
            j->second(settings);
        else if (auto k = OneArgs.find(opt); k != OneArgs.end())
            if (++i < argc) {
                k->second(settings, {argv[i]});
            } else
                throw std::runtime_error{"missing param after " + opt};
        else
            std::cerr << "unrecognized command-line option " << opt << "\n";
    }
    return settings;
}

void validate_settings(const CLISettings &s) {
    if (s.threads && (!s.impl || *s.impl != "omp"))
        throw std::runtime_error("--threads can only be used with --impl=omp");

    if ((s.block_size || s.grid_size) && (!s.impl || *s.impl != "cuda"))
        throw std::runtime_error("--block_size and --grid_size require --impl=cuda");

    if (s.repeats && *s.repeats <= 0)
        throw std::runtime_error("--repeats must be positive");

    // add more rules here
}

int main(int argc, const char *argv[]) {
    auto settings = parse_settings(argc, argv);
    if (settings.threads) std::cout << *settings.threads << "\n";
    if (settings.impl) std::cout << *settings.impl << "\n";
    if (settings.size) std::cout << *settings.size << "\n";
    return 0;
}
