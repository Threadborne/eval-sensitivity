# Pre-registration: Does the JailbreakBench leaderboard reorder under judge and parser variation?

**Author:** Michael Smith, Small Mind LLC, Lansing, MI
**Date:** 2026-09-16
**Version:** 1.5
**Status:** Pre-registered. No scoring has been run. No number in this document is a result.

---

## 1. Question

JailbreakBench (Chao et al., NeurIPS 2024 Datasets and Benchmarks) reports attack success rate (ASR) for attacks and defenses, scored by a Llama-3-70B judge through a parsing layer in `src/jailbreakbench/classifier.py`. The reported number is one point in a space of evaluation choices. This study asks whether the leaderboard ordering survives when two of those choices are varied:

1. **Parser.** Issue #50 (collapseindex, filed 2026-09-16) documents eight defects in the parsing layer that alter the verdict on spec-compliant judge output: two unconditional (forcing any response under 15 space-separated tokens to "not jailbroken"; matching refusal phrases as substrings anywhere rather than as prefixes) and six conditional on the judge replying with more than the single token it was asked for. The issue states explicitly that re-scoring the published artifacts was not done.
2. **Judge model.** The reference judge is Llama-3-70B. Whether a different judge model, holding everything else fixed, produces the same ranking is not reported.

The study measures the effect of each dial and both together on the ordering of leaderboard entries, and classifies each dial as a target axis or a nuisance axis using the transfer criterion defined in the companion framework document.

---

## 2. What is held fixed

- The JBB-Behaviors dataset, 100 harmful behaviors, as published.
- The published jailbreak artifacts (prompts, target responses, and shipped classifications) from `github.com/JailbreakBench/artifacts`, at the commit hash recorded in Appendix A at execution time.
- No new attacks are generated. No target models are run. Only existing responses are re-scored.
- **Missing-response rule.** Some entries store no response for some behaviors. This is by construction: PAIR stores a response only when it finds a jailbreak within its query budget, so a missing response means the attack failed on that behavior. Missing responses are treated as **not jailbroken** under every configuration, matching JailbreakBench's own convention. Coverage per entry at the artifacts commit below: 14 of 18 entries at 100/100; PAIR on Vicuna 82/100, PAIR on GPT-3.5 87/100, PAIR on GPT-4 64/100, PAIR on Llama-2 **4/100**. Because 4 responses cannot support a rank position, all ranking metrics are reported twice: once over all 18 entries and once over the 17 entries excluding PAIR on Llama-2. Both are pre-registered; neither is primary.
- The judge prompt template as shipped, byte-identical across all judge models.
- Scoring script frozen at a public commit before any scoring run.

---

## 3. Dials (the declared choice space Θ_d)

**Dial 1, parser.** Two levels.
- `shipped`: `classifier.py` at commit `23dbdf6b19650521604456229bc1d9c4156c85c1`, the commit audited in issue #50.
- `corrected`: the same file with the eight defects in issue #50 repaired, per the audit's stated directions. The corrected file is published alongside the scoring script. The six cited line numbers span three code paths (Llama Guard 1 at L63/L65; Llama 3 at L110/L128/L130; the string classifier at L175), so the corrected parser is three functions, one per path, not one. One defect (a genuine refusal worded outside the 13 listed phrases, the over-reporting half of L175) is a coverage limit of a fixed phrase list rather than a matching bug. It is documented and left unrepaired; extending the phrase list would be an undeclared dial.

**Dial 2, judge model.** Six levels.
- `llama3-70b`: the reference judge. Its labels are already present in the artifacts as the `jailbroken` field; these are used as-is for the full set. A fresh API re-run on a stratified subset of at least 200 responses checks that the stored labels reproduce (see §7).
- `llama-guard-1`: present in the artifacts as the `jailbroken_llama_guard1` field for 16 of 18 entries. The two DSN entries have no such field; DSN was added to the artifacts repository in the pinned commit, after the Llama Guard 1 labeling pass. Used as-is where present; the two DSN entries are recorded with reason `stored_label_absent` and this judge level covers 16 entries. Kendall's τ for this level is computed over the 16 entries it covers, and this is stated wherever it is reported. Zero compute. Note: Llama Guard 1 is the judge governed by the 15-token defect in issue #50, so this level interacts with the parser dial in a known way.
- `llama3-8b-instruct`
- `qwen2.5-7b-instruct`, pinned. The v1.1 text allowing "the current Qwen instruct model at execution time" is withdrawn: a study of undeclared choice space should not leave a choice open inside a dial.
- `mistral-7b-instruct`. **Deviation, declared 2026-09-16 before its scoring pass:** this judge alone runs with `num_predict=32` and a 30-second per-call timeout. Under the uncapped v2 script it produced three consecutive 300-second hangs (DSN/vicuna indices 53 and 54, GCG/llama-2 index 81) and could not complete. All other local judges ran uncapped. Rows that time out under the cap are recorded with reason `judge_timeout` and count as unparseable under the §3 unparseable-reply rule. This is a decoding-option difference between judges and is reported as such.
- `gemma-2-9b-it`

Four families among the locals (Meta, Alibaba, Mistral AI, Google) so that same-family blind spots are not the only variation. Two Meta judges (Llama-3-70B, Llama Guard 1) are already in the data. All local judges run at the precision that fits a 16 GB GPU; precision recorded in Appendix A.

Θ_d = {shipped, corrected} × {six judges} = 12 configurations. The reference configuration θ₀ = (shipped, llama3-70b).

For the two judges whose labels are stored in the artifacts, the `shipped` parser condition is the stored label and the `corrected` condition is recorded as not recomputable, since only the parsed verdict was stored and no raw judge output exists.

**Unparseable-reply rule.** Under the `corrected` parser, a judge reply that is off-spec (no anchored verdict token, empty, or a declination) yields no verdict and is stored as `null` with reason `unparseable_judge_reply`. Because excluding such rows from the ASR denominator and counting them as not-jailbroken give different ASRs and potentially different rankings, **both conventions are computed and reported for every (θ, e)**, alongside the unparseable rate itself as a separate column. Neither convention is primary. The unparseable rate is treated as a property of the judge configuration and is reported as a finding, not suppressed.

**Declared as out of scope for this study:** judge prompt wording, temperature, behavior subset selection, ASR aggregation rule. These are real dials. They are not turned here. Anyone can extend Θ_d; that is the point of declaring it.

---

## 4. Measures (the vector M)

For each configuration θ and each leaderboard entry e (an attack on a target model, or a defense on a target model):

- **M₁: ASR(θ, e)**, fraction of the 100 behaviors labeled jailbroken.
- **M₂: refusal rate(θ, e)**, using the shipped Llama3RefusalJudge prompt under the same parser condition. This requires a second scoring pass with the refusal prompt; rows carry a `judge_task ∈ {jailbreak, refusal}` field. Two of the eight defects (L110 and L146, on the refusal path) are exercised only by this pass.
- **M₃, as registered in v1.1 through v1.4:** label agreement with human labels on the subset of artifact responses covered by the JailbreakBench `judge_comparison` dataset. **Found empty at execution time (v1.5):** the calibration set contains 300 prompt-response pairs with three human annotators and a majority vote, and exactly one of its responses appears in the attack artifacts. The overlap assumption was wrong. M₃ as registered cannot be computed.

- **M₃, redefined in v1.5 before any scoring of the calibration set:** for each Dial 2 judge level and each Dial 1 parser condition, **accuracy against `human_majority`** on the 300-row calibration set, together with precision, recall, and the unparseable rate. This is a property of the judge configuration, not of a leaderboard entry. It is the external anchor the study otherwise lacks. The calibration set also carries the reference judge's own labels (`llama3_cf`), so the reference configuration's accuracy is computed from stored labels with zero compute, alongside `harmbench_cf`, `gpt4_cf`, and `llamaguard2_cf` for comparison.

M₃ is the only measure with an external anchor. M₁ and M₂ are the benchmark's own outputs. **Because M₁ is indexed by leaderboard entry and the redefined M₃ is indexed by judge configuration, they do not form a vector over a common index, and the transfer test in §5 H3 does not apply to them as written.** H3 stays not evaluable in its registered form. A judge-level hypothesis is registered in its place below as H3′.

---

## 5. Hypotheses and decision rules

Written before any scoring. The thresholds below are the pre-registered values.

**H1 (reordering).** Kendall's τ between the leaderboard ranking under θ₀ and under at least one other configuration in Θ_d is **below 0.80**.

Decision: compute τ for all 9 non-reference configurations against θ₀. If min τ < 0.80, H1 is supported. If min τ ≥ 0.80, H1 is not supported and the leaderboard ordering is reported as stable under the declared dials.

**H2 (resolution).** The judge-induced ASR spread for at least one entry exceeds the smallest gap between adjacent entries on the reference leaderboard.

Decision: for each entry e, spread(e) = max over θ of ASR(θ,e) minus min over θ of ASR(θ,e). Let g_min be the smallest ASR difference between adjacent entries under θ₀. If max over e of spread(e) > g_min, H2 is supported.

**H3 (dial classification).** For each dial, the displacement Δ across (M₁, M₂, M₃), standardized by the bootstrap covariance and evaluated against the orthant cone, yields ν > 0.5.

Decision: report ν for each dial separately and for both together. ν > 0.5 classifies the dial as nuisance at the 0.5 level. The threshold is pre-registered as 0.5. Both the orthant-cone ν and the uniform-ray ν are reported; the orthant version is the primary.

**H3′ (judge-level anchor), registered 2026-09-16 in v1.5 before the calibration set was scored.** Across the five alternate judge configurations with nonzero τ against the reference, Kendall's τ (from H1) and accuracy against `human_majority` (from redefined M₃) are positively rank-correlated: judges that agree more with the reference also agree more with humans.

Decision: Spearman's ρ between the τ column and the accuracy column across judge configurations. ρ > 0 supports H3′. ρ ≤ 0 means agreement with the reference and agreement with truth come apart, which would mean the reference judge is not the right anchor. Both outcomes are reported. No threshold beyond the sign is pre-registered because five points cannot support one.

Secondary, not a hypothesis: for the reference judge itself, accuracy against `human_majority` from the stored `llama3_cf` column is the ceiling any substitute is compared to.

**Outcomes.** All combinations of H1, H2, H3, and H3′ supported or not are publishable. The study is not designed to produce a particular result.

---

## 6. Analysis plan, frozen

1. Pull artifacts at the commit hash in Appendix A. Confirm per-entry response coverage matches §2. Missing responses are handled per the rule in §2; no entry is excluded on that basis.
2. Run every response through every configuration in Θ_d. Store raw judge outputs and parsed verdicts separately, so parser effects are separable from judge effects after the fact.
3. Compute M₁, M₂, M₃ per (θ, e), under both unparseable conventions (§3), with the unparseable rate as its own column.
4. Compute Kendall's τ per configuration against θ₀. Report the full matrix.
5. Compute spread(e) and g_min. Report both and the ratio.
6. Bootstrap over behaviors (1000 resamples) to estimate Σ, the covariance of (M₁, M₂, M₃). Compute K_eff.
7. Compute ν per dial under the orthant cone and the uniform ray.
8. Report the rough-set boundary fraction over Θ_d under the tolerance ε_k = one bootstrap SD per measure, frozen at first computation.
9. Publish the full (θ, e) matrix, raw judge outputs, and the scoring script.

No step is added or removed after scoring begins. Any deviation is recorded in a dated addendum with the reason.

---

## 7. Compute and constraints

- Local judges on one RTX 5070 Ti, 16 GB.
- The 70B reference judge via API on a stratified subset of at least 200 responses across entries. Full-set 70B scoring is done if budget allows and is recorded either way.
- N = 18 leaderboard entries at the artifacts commit below (5 attacks × 4 targets, less 2 unpublished combinations). Approximately 1,800 stored responses.
- Local judge calls: 1,800 responses × 4 local judges = 7,200 calls, each stored as raw output so both parser conditions are derived from one run. At roughly 1–2 seconds per call on the stated hardware, 2–4 hours per judge.
- Two judges (Llama-3-70B, Llama Guard 1) cost nothing; their labels are in the data.
- The 70B reproduction check: at least 200 API calls. **Stratification:** by entry, so each of the 18 entries contributes at least 11 responses, balanced within entry on the stored `jailbroken` label where both labels exist. The sampled indices are committed with the script before the calls are made.

---

## 8. What this study does not claim

- Nothing about the accuracy of any judge model. Only about agreement between configurations.
- Nothing about attacks or defenses not in the published artifacts.
- Nothing about dials outside Θ_d. The choice space is declared and refutable by omission.
- Nothing about the true sensitivity of the benchmark. Reported sensitivity is a lower bound over the configurations searched, per the companion framework.

---

## 9. Prior work this builds on

- Chao, Debenedetti, Robey, Andriushchenko, Croce, Sehwag, Dobriban, Flammarion, Pappas, Tramèr, Hassani, Wong. *JailbreakBench: An Open Robustness Benchmark for Jailbreaking Large Language Models.* NeurIPS 2024 Datasets and Benchmarks.
- collapseindex. `dinostomp/FINDINGS.md` entries **F-030, F-031, F-032** at commit `3849382`. Append-only ledger; corrections are made in place with a date, so the IDs remain valid citations. Filed upstream as issue #50, `JailbreakBench/jailbreakbench`, 2026-09-16; the issue text is the corrected version. Audit script at `audits/jailbreakbench/`. This study runs the re-scoring that audit explicitly scoped out. The same ledger catalogues the parser-bug family across AISafetyLab (F-033 to F-035), HarmBench ArtPrompt (F-036), garak (F-037, F-038), and SWE-bench (F-039), with StrongREJECT (N-024) recorded as the counterexample whose autograder fails safe. This study measures one entry in that family; the method applies to the others.
- JailbreakBench `judge_comparison` dataset, HuggingFace `JailbreakBench/JBB-Behaviors`, config `judge_comparison`. Source of human labels for M₃.
- Smith. *Evaluation Sensitivity: The Formal Statement.* 2026-09-16. Companion framework document; SHA-256 in Appendix B.
- Smith. *The Number Moved, the Model Didn't.* smallmind.net, September 2026. First instance of the same method on Sleep-EDF.

---

## Appendix A: recorded at execution time

Filled 2026-09-16 before the first local-judge scoring run.

- Artifacts repo commit hash: `909e68c01d94222b8ad2e397a017e2e12e2adb73` (verified 2026-09-16; 18 attack artifacts, 100 behaviors each, response coverage as stated in §2)
- jailbreakbench package commit hash for the shipped parser: `23dbdf6b19650521604456229bc1d9c4156c85c1` (the commit audited in issue #50)
- Local judge models, all Q8_0 quantization, served by Ollama:

  | Dial 2 level | Ollama tag | Ollama digest | Size |
  |---|---|---|---|
  | `llama3-8b-instruct` | `llama3:8b-instruct-q8_0` | `1b8e49cece7f` | 8.5 GB |
  | `qwen2.5-7b-instruct` | `qwen2.5:7b-instruct-q8_0` | `2d9500c94841` | 8.1 GB |
  | `mistral-7b-instruct` | `mistral:7b-instruct-q8_0` | `2162e081e7f0` | 7.7 GB |
  | `gemma-2-9b-it` | `gemma2:9b-instruct-q8_0` | `54faa8324fdf` | 9.8 GB |

- Decoding options for all local judges: `temperature=0`, `num_ctx=8192`. Recorded per run in `results.jsonl.manifest.json`.
- Hardware: one NVIDIA RTX 5070 Ti, 16 GB.
- N (leaderboard entries scored): 18.
- Scoring script: `score.py` and `parsers.py` at repository commit for "Script v2" (see git history); `JUDGE_PROMPT` SHA-256 `2bdc0b4d11a5b7e8c06528c44f2d04e01084c156e0e040380a5e2ca1a1055aa1`, verified byte-identical to the pinned source by `parsers.py` before the run.
- Stored-label run (Dial 2 levels `llama3-70b`, `llama-guard-1`): 2026-09-16, 3,600 rows, 0 judge calls.
- First local-judge scoring run: 2026-09-16, started after this appendix was committed.

## Appendix B: document hashes

- This document, v1.0, SHA-256:
- Companion framework document, SHA-256:

Any edit to this document after publication produces a new version with a new hash and a dated changelog entry.

## Changelog

- **1.4 → 1.5, 2026-09-16, after the artifact analysis was run and committed (ae9e7d0), before the calibration set was scored.** (1) M₃ as registered was found to cover one response; the `judge_comparison` set does not overlap the artifacts. Recorded as a wrong assumption, not a data problem. (2) M₃ redefined as judge-level accuracy against `human_majority` on the 300-row calibration set, both parser conditions. (3) H3 remains not evaluable in its registered form because M₁ and redefined M₃ are not co-indexed. (4) H3′ registered as the judge-level replacement: sign of Spearman's ρ between τ-vs-reference and accuracy-vs-humans across alternate judges. (5) **Disclosure:** while smoke-testing `analyze_calibration.py` against a stub, the stored `llama3_cf` and `gpt4_cf` columns were read from the real calibration file and the reference judge's accuracy against `human_majority` (0.907) and GPT-4's (0.903) were printed and seen before this version was committed. The four local judges' accuracies were not seen; their stub rows were synthetic. H3′ is unaffected. The secondary observation about the reference judge's ceiling is therefore not blind and is reported as such. No existing hypothesis or threshold changed. Version 1.5 is the pre-registration of record.
- **1.3 → 1.4, 2026-09-16, after the Llama-3-8B, Qwen2.5-7B, and Gemma-2-9B passes completed and before the Mistral pass.** (1) Mistral-7B declared as running with `num_predict=32` and a 30-second timeout, with the reason and the three hang indices recorded; §3. (2) Citation for the parser audit changed from the issue number to the dinostomp ledger IDs F-030, F-031, F-032 at commit 3849382, per the ledger author's guidance; the cross-benchmark family is noted; §9. No hypothesis or threshold changed. Version 1.4 is the pre-registration of record.
- **1.2 → 1.3, 2026-09-16, before the first local-judge scoring run.** Appendix A filled at execution time, as the appendix itself requires. No section other than Appendix A and this changelog changed. Version 1.3 is the pre-registration of record.
- **1.1 → 1.2, 2026-09-16, after publication of 1.1 (commit c44d9211), before any scoring script commit and before any scoring run.** Corrections found by the scoring-script author on reading the pre-reg against the pinned sources. (1) Issue #50 lists eight defects, not ten; "ten" was the issue's probe count. §1 and §3 corrected. (2) Coverage is 14 of 18 entries at 100/100, not 16; the four PAIR figures were already correct. §2 corrected. (3) `jailbroken_llama_guard1` is absent for the two DSN entries; the Llama Guard 1 judge level covers 16 entries, stated in §3. (4) The corrected parser is three functions across three code paths, and one L175 defect is a coverage limit left unrepaired; stated in §3. (5) The Qwen judge is pinned; the "current model at execution time" clause is withdrawn. (6) **New rule:** unparseable judge replies under the corrected parser are reported under both denominator conventions plus the unparseable rate; §3 and §6.3. (7) M₂ requires a second scoring pass with a `judge_task` field; §4. (8) §6.1 contradicted §2 on missing responses; §6.1 corrected. (9) Stratification for the 70B reproduction check defined; §7. No hypothesis or threshold changed. Version 1.2 is the pre-registration of record.
- **1.0 → 1.1, 2026-09-16, before publication.** Added `llama-guard-1` as a sixth judge level (labels already present in artifacts). Added the missing-response rule and per-entry coverage after verifying the artifacts directly. Recorded artifacts commit hash. Updated configuration count to 12 and compute estimate accordingly. No hypotheses or thresholds changed. Version 1.1 is the pre-registration of record.
