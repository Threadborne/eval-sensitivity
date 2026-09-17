# eval-sensitivity

A reported metric is one point in a space of evaluation choices. This repository holds the framework for measuring how far that point moves, and a pre-registered experiment applying it to JailbreakBench.

Michael Smith, Small Mind LLC. September 2026.

## Contents

| File | What it is | SHA-256 |
|---|---|---|
| `prereg-jbb-judge-parser-sensitivity.md` | Pre-registered experimental design, v1.1. Hypotheses, thresholds, and analysis plan frozen before any scoring. | `a3a965f48e8bbbe40530527bb05e813500be4ccf5472feeeccb9037a2d7afbe0` |
| `evaluation-sensitivity-formal.md` | The formal framework: choice space, worst-case and expected-case sensitivity, the transfer test and nuisance fraction ν, rough-set treatment of the choice space, the refinement theorem, verified lineage, and prior work. | `433d27fed72188e595811fe58a1831be3aef7dceb4c4431ea0190df48e718dde` |
| `the-number-is-a-point.md` | The same material, written to be taught from. | `b7fedfa656a8b81574372f038aec1eb0962e5f87d08738b6fa663ad7b8ea8d3c` |

Verify any file with `sha256sum <file>` or `certutil -hashfile <file> SHA256`.

## The experiment

Does the JailbreakBench leaderboard reorder when the judge model or the judge's output parser is varied? The parser defects are documented in [JailbreakBench/jailbreakbench#50](https://github.com/JailbreakBench/jailbreakbench/issues/50). That audit explicitly scoped out re-scoring the published artifacts. This experiment runs it, adds judge-model substitution across four model families, and compares rankings against leaderboard gaps.

Design is frozen at the pre-registration commit. The scoring script will be committed separately, before the first scoring run, so the gap between design and execution is visible in the history.

## Status

- 2026-09-16: Pre-registration v1.1 committed. No scoring has been run.

## Prior instance

The same method, run by hand on one dial: [The Number Moved, the Model Didn't](https://smallmind.net/writing/the-number-moved.html), on Sleep-EDF sleep staging. Accuracy moved 11.3 points on a preprocessing choice; macro-F1 moved 0.0002.

## License

Documents: CC BY 4.0. Code, when added: MIT.
