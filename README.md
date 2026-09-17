# eval-sensitivity

A reported metric is one point in a space of evaluation choices. This repository holds the framework for measuring how far that point moves, and a pre-registered experiment applying it to JailbreakBench.

Michael Smith, Small Mind LLC. September 2026.

## Contents

| File | What it is | SHA-256 |
|---|---|---|
| `prereg-jbb-judge-parser-sensitivity.md` | Pre-registered experimental design, v1.3. Hypotheses, thresholds, and analysis plan frozen before any scoring. Changelog inside. | `4e8f5ae0cbea84dbc51eaa9f6a9e82985f619b6b5a7cb3236872d84031b4dc88` |
| `evaluation-sensitivity-formal.md` | The formal framework: choice space, worst-case and expected-case sensitivity, the transfer test and nuisance fraction ν, rough-set treatment of the choice space, the refinement theorem, verified lineage, and prior work. | `433d27fed72188e595811fe58a1831be3aef7dceb4c4431ea0190df48e718dde` |
| `the-number-is-a-point.md` | The same material, written to be taught from. | `b7fedfa656a8b81574372f038aec1eb0962e5f87d08738b6fa663ad7b8ea8d3c` |

Verify any file with `sha256sum <file>` or `certutil -hashfile <file> SHA256`.

## The experiment

Does the JailbreakBench leaderboard reorder when the judge model or the judge's output parser is varied? The parser defects are documented in [JailbreakBench/jailbreakbench#50](https://github.com/JailbreakBench/jailbreakbench/issues/50). That audit explicitly scoped out re-scoring the published artifacts. This experiment runs it, adds judge-model substitution across four model families, and compares rankings against leaderboard gaps.

Design is frozen at the pre-registration commit. The scoring script will be committed separately, before the first scoring run, so the gap between design and execution is visible in the history.

## Status

- 2026-09-16: Pre-registration v1.1 committed (`c44d9211`). No scoring has been run.
- 2026-09-16: Pre-registration v1.2 committed. Nine corrections found by reading v1.1 against the pinned sources while writing the scoring script; none change a hypothesis or threshold. Changelog in the document. Still no scoring run.
- 2026-09-16: Pre-registration v1.3: Appendix A filled with the four local judge tags and digests. No other change.
- 2026-09-16: Script v2 committed (loop order, posix names, run manifest, num_ctx, comments stripped). Stub re-run clean.
- 2026-09-16: Stored-label run complete: 3,600 rows, 0 judge calls.
- 2026-09-16: Scoring script frozen (`parsers.py`, `score.py`, `stub_judge.py`, `stub_results.jsonl`, `classifier_pinned_23dbdf6.py`). Not yet run against live judges.

Prior versions remain in history. `v1.1` is at commit `c44d9211`.

## Prior instance

The same method, run by hand on one dial: [The Number Moved, the Model Didn't](https://smallmind.net/writing/the-number-moved.html), on Sleep-EDF sleep staging. Accuracy moved 11.3 points on a preprocessing choice; macro-F1 moved 0.0002.

## License

Documents: CC BY 4.0. Code, when added: MIT.
