#include <chrono>
#include <cstdint>
#include <functional>
#include <iostream>
#include <optional>
#include <unordered_map>
#include <utils.h>

#include "cuda_bitonic_sort.h"
#include "omp_sort.h"
#include "serial_bitonic_sort.h"
#include "serial_sort.h"

struct CLISettings {
    bool help{false};
    std::optional<std::string> impl;
    std::optional<int16_t> threads;
    std::optional<int16_t> block_size;
    std::optional<int16_t> grid_size;
    std::optional<int16_t> repeats;
    std::optional<u_int32_t> size;
    std::optional<u_int32_t> seed;
    std::optional<std::string> distribution;
    std::optional<std::string> output;
};

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
            if (++i < argc)
                k->second(settings, {argv[i]});
            else
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
}

int main(int argc, const char *argv[]) {
    auto settings = parse_settings(argc, argv);
    validate_settings(settings);

    if (!settings.size || !settings.seed || !settings.distribution) {
        std::cerr << "Usage: --size N --seed S --distribution D [--impl {serial,serial_bitonic,omp,cuda}] "
                     "[--threads T] [--block_size B] [--grid_size G]\n";
        return 1;
    }

    auto v = utils::generate(*settings.size, *settings.seed, *settings.distribution);
    int repeats = settings.repeats.value_or(1);
    std::string impl = settings.impl.value_or("serial");
    int threads = settings.threads.value_or(4);
    const int cuda_threads_per_block = settings.block_size.value_or(512);

    double total_ms = 0.0;
    for (int r = 0; r < repeats; r++) {
        auto arr = v;
        auto t0 = std::chrono::high_resolution_clock::now();

        if (impl == "omp") {
            ompMergeSort(arr, threads);
        } else if (impl == "serial_bitonic") {
            serialBitonicSort(arr);
        } else if (impl == "cuda") {
            cudaBitonicSort(arr, cuda_threads_per_block);
        } else {
            mergeSort(arr);
        }

        auto t1 = std::chrono::high_resolution_clock::now();
        total_ms += std::chrono::duration<double, std::milli>(t1 - t0).count();
    }

    std::cout << "impl=" << impl
              << " size=" << *settings.size
              << " dist=" << *settings.distribution
              << " threads=" << (impl == "omp" ? threads : 1);
    if (impl == "cuda")
        std::cout << " block_size=" << cuda_threads_per_block;
    if (impl == "cuda" && settings.grid_size)
        std::cout << " grid_size=" << *settings.grid_size;
    std::cout << " avg_ms=" << (total_ms / repeats) << "\n";

    return 0;
}
