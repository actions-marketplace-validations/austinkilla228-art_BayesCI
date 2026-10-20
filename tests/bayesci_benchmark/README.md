# BayesCI benchmark — 20 synthetic Git repositories

Each case is a complete Git repository with its own `.git` directory, a working initial commit, a deliberately breaking commit, and several subsequent benign commits. All cases use CMake and C.

## Run one case

```bash
cd case_01_missing_source
cmake -S . -B build && cmake --build build
```

The build should fail. Set your BayesCI repository path to the case folder and use the captured build log. Each case also includes `config_ci.yaml` with the build command. Paths are relative to each case directory.

## Ground truth

`answers.csv` contains the SHA of the deliberately breaking commit in every case. Use it to evaluate your ranking **after** running BayesCI.

## Caveats

These are synthetic deterministic C/CMake failures, not representative of all real-world CI failures. The culprit is known, but a heuristic ranker may not find it. Use fresh build directories or delete `build/` between runs. The ZIP includes `.git` history.
