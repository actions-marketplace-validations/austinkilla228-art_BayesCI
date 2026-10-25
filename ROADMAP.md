BayesCI is an open-source project focused on diagnosing failed CI/CD builds using Bayesian reasoning.

The project is currently in early development, and contributions are welcome!

## v1.0.x — Security & Stability

- [ ] Review GitHub Actions token handling and HTTP redirects.
- [ ] Remove unnecessary shell execution.
- [ ] Add limits for downloaded CI logs.
- [ ] Improve error handling and reliability.
- [ ] Expand automated tests.

## v1.1 — Better Diagnostics

- [ ] Support structured GCC/Clang JSON diagnostics.
- [ ] Improve compiler and linker error parsing.
- [ ] Investigate macro-related diagnostic failures.
- [ ] Improve evidence extraction and commit ranking.
- [ ] Test BayesCI against real-world C/C++ repositories.

## Future Ideas

- [ ] MSVC diagnostic support.
- [ ] GitLab CI integration.
- [ ] Experimental GUI or web dashboard.
- [ ] Additional programming languages and toolchains.
- [ ] Alternative parsers written in Rust, Go, Java, or other languages.
- [ ] Optional integration with AI coding assistants.

## Project Philosophy

**KISS — Keep It Simple, Stupid.**

The C computational core should remain small, portable, understandable, and independent of unnecessary dependencies.

**Install and Forget.**

End users should be able to configure BayesCI once and let it automatically analyze supported CI failures.

## Contributions

Everyone is welcome — students, beginners, hobbyists, and experienced developers.

Feel free to open issues, submit pull requests, suggest features, or build your own integrations using the C computational engine.

See our [Good First Issues](https://github.com/austinkilla228-art/BayesCI/labels/good%20first%20issue) if you're looking for a place to start.

**Note:** This roadmap describes possible directions, not guaranteed features or release dates.

**Freedom for contributors. Simplicity for users.**
