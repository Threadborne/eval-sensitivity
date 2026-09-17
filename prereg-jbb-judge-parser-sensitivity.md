# Pre-registration: Does the JailbreakBench leaderboard reorder under judge and parser variation?

**Author:** Michael Smith, Small Mind LLC, Lansing, MI
**Date:** 2026-09-16
**Version:** 1.1
**Status:** Pre-registered. No scoring has been run. No number in this document is a result.

---

## 1. Question

JailbreakBench (Chao et al., NeurIPS 2024 Datasets and Benchmarks) reports attack success rate (ASR) for attacks and defenses, scored by a Llama-3-70B judge through a parsing layer in `src/jailbreakbench/classifier.py`. The reported number is one point in a space of evaluation choices. This study asks whether the leaderboard ordering survives when two of those choices are varied:

1. **Parser.** Issue #50 (collapseindex, filed 2026-09-16) documents ten defects in the parsing layer that alter the verdict on spec-compliant judge output, including forcing any response under 15 space-separated tokens to "not jailbroken" and matching refusal phrases as substrings anywhere rather than as prefixes. The issue states explicitly that re-scoring the published artifacts was not done.
2. **Judge model.** The reference judge is Llama-3-70B. Whether a different judge model, holding everything else fixed, produces the same ranking is not reported.

The study measures the effect of each dial and both together on the ordering of leaderboard entries, and classifies each dial as a target axis or a nuisance axis using the transfer criterion defined in the companion framework document.

---

## 2. What is held fixed

- The JBB-Behaviors dataset, 100 harmful behaviors, as published.
- The published jailbreak artifacts (prompts, target responses, and shipped classifications) from `github.com/JailbreakBench/artifacts`, at the commit hash recorded in Appendix A at execution time.
- No new attacks are generated. No target models are run. Only existing responses are re-scored.
- **Missing-response rule.** Some entries store no response for some behaviors. This is by construction: PAIR stores a response only when it finds a jailbreak within its query budget, so a missing response means the attack failed on that behavior. Missing responses are treated as **not jailbroken** under every configuration, matching JailbreakBench's own convention. Coverage per entry at the artifacts commit below: 16 of 18 entries at 100/100; PAIR on Vicuna 82/100, PAIR on GPT-3.5 87/100, PAIR on GPT-4 64/100, PAIR on Llama-2 **4/100**. Because 4 responses cannot support a rank position, all ranking metrics are reported twice: once over all 18 entries and once over the 17 entries excluding PAIR on Llama-2. Both are pre-registered; neither is primary.
- The judge prompt template as shipped, byte-identical across all judge models.
- Scoring script frozen at a public commit before any scoring run.

---

## 3. Dials (the declared choice space Θ_d)

**Dial 1, parser.** Two levels.
- `shipped`: `classifier.py` at commit `23dbdf6b19650521604456229bc1d9c4156c85c1`, the commit audited in issue #50.
- `corrected`: the same file with the ten defects in issue #50 repaired, per the audit's stated directions. The corrected file is published alongside the scoring script.

**Dial 2, judge model.** Six levels.
- `llama3-70b`: the reference judge. Its labels are already present in the artifacts as the `jailbroken` field; these are used as-is for the full set. A fresh API re-run on a stratified subset of at least 200 responses checks that the stored labels reproduce (see §7).
- `llama-guard-1`: already present in the artifacts as the `jailbroken_llama_guard1` field. Used as-is. Zero compute. Note: Llama Guard 1 is the judge governed by the 15-token defect in issue #50, so this level interacts with the parser dial in a known way.
- `llama3-8b-instruct`
- `qwen2.5-7b-instruct` (or the current Qwen instruct model in the same size class at execution time; recorded in Appendix A)
- `mistral-7b-instruct`
- `gemma-2-9b-it`

Four families among the locals (Meta, Alibaba, Mistral AI, Google) so that same-family blind spots are not the only variation. Two Meta judges (Llama-3-70B, Llama Guard 1) are already in the data. All local judges run at the precision that fits a 16 GB GPU; precision recorded in Appendix A.

Θ_d = {shipped, corrected} × {six judges} = 12 configurations. The reference configuration θ₀ = (shipped, llama3-70b).

For the two judges whose labels are stored in the artifacts, the `shipped` parser condition is the stored label and the `corrected` condition is recomputed from the stored raw judge output where available, or flagged as not recomputable where only the parsed verdict was stored.

**Declared as out of scope for this study:** judge prompt wording, temperature, behavior subset selection, ASR aggregation rule. These are real dials. They are not turned here. Anyone can extend Θ_d; that is the point of declaring it.

---

## 4. Measures (the vector M)

For each configuration θ and each leaderboard entry e (an attack on a target model, or a defense on a target model):

- **M₁: ASR(θ, e)**, fraction of the 100 behaviors labeled jailbroken.
- **M₂: refusal rate(θ, e)**, using the shipped Llama3RefusalJudge under the same parser condition.
- **M₃: label agreement with human labels**, on the subset of responses covered by the JailbreakBench `judge_comparison` dataset on HuggingFace, where human labels exist.

M₃ is the only measure with an external anchor. M₁ and M₂ are the benchmark's own outputs. K = 3. K_eff will be computed as the rank of the covariance of (M₁, M₂, M₃) across Θ_d and reported; if K_eff < 3, the transfer test is weakened accordingly and this is stated.

---

## 5. Hypotheses and decision rules

Written before any scoring. The thresholds below are the pre-registered values.

**H1 (reordering).** Kendall's τ between the leaderboard ranking under θ₀ and under at least one other configuration in Θ_d is **below 0.80**.

Decision: compute τ for all 9 non-reference configurations against θ₀. If min τ < 0.80, H1 is supported. If min τ ≥ 0.80, H1 is not supported and the leaderboard ordering is reported as stable under the declared dials.

**H2 (resolution).** The judge-induced ASR spread for at least one entry exceeds the smallest gap between adjacent entries on the reference leaderboard.

Decision: for each entry e, spread(e) = max over θ of ASR(θ,e) minus min over θ of ASR(θ,e). Let g_min be the smallest ASR difference between adjacent entries under θ₀. If max over e of spread(e) > g_min, H2 is supported.

**H3 (dial classification).** For each dial, the displacement Δ across (M₁, M₂, M₃), standardized by the bootstrap covariance and evaluated against the orthant cone, yields ν > 0.5.

Decision: report ν for each dial separately and for both together. ν > 0.5 classifies the dial as nuisance at the 0.5 level. The threshold is pre-registered as 0.5. Both the orthant-cone ν and the uniform-ray ν are reported; the orthant version is the primary.

**Outcomes.** All combinations of H1, H2, H3 supported or not are publishable. The study is not designed to produce a particular result.

---

## 6. Analysis plan, frozen

1. Pull artifacts at the commit hash in Appendix A. Confirm `response` fields are populated for every entry used. Any entry with a missing or redacted response is excluded and listed.
2. Run every response through every configuration in Θ_d. Store raw judge outputs and parsed verdicts separately, so parser effects are separable from judge effects after the fact.
3. Compute M₁, M₂, M₃ per (θ, e).
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
- The 70B reproduction check: at least 200 API calls.

---

## 8. What this study does not claim

- Nothing about the accuracy of any judge model. Only about agreement between configurations.
- Nothing about attacks or defenses not in the published artifacts.
- Nothing about dials outside Θ_d. The choice space is declared and refutable by omission.
- Nothing about the true sensitivity of the benchmark. Reported sensitivity is a lower bound over the configurations searched, per the companion framework.

---

## 9. Prior work this builds on

- Chao, Debenedetti, Robey, Andriushchenko, Croce, Sehwag, Dobriban, Flammarion, Pappas, Tramèr, Hassani, Wong. *JailbreakBench: An Open Robustness Benchmark for Jailbreaking Large Language Models.* NeurIPS 2024 Datasets and Benchmarks.
- collapseindex. Issue #50, `JailbreakBench/jailbreakbench`, 2026-09-16. Audit at `github.com/collapseindex/dinostomp/tree/main/audits/jailbreakbench`. This study runs the re-scoring that audit explicitly scoped out.
- JailbreakBench `judge_comparison` dataset, HuggingFace `JailbreakBench/JBB-Behaviors`, config `judge_comparison`. Source of human labels for M₃.
- Smith. *Evaluation Sensitivity: The Formal Statement.* 2026-09-16. Companion framework document; SHA-256 in Appendix B.
- Smith. *The Number Moved, the Model Didn't.* smallmind.net, September 2026. First instance of the same method on Sleep-EDF.

---

## Appendix A: recorded at execution time

To be filled in before the first scoring run and committed with the script.

- Artifacts repo commit hash: `909e68c01d94222b8ad2e397a017e2e12e2adb73` (verified 2026-09-16; 18 attack artifacts, 100 behaviors each, response coverage as stated in §2)
- jailbreakbench package commit hash for the shipped parser: `23dbdf6b19650521604456229bc1d9c4156c85c1` (the commit audited in issue #50)
- Local judge model identifiers and precision:
- N (number of leaderboard entries scored):
- Date of first scoring run:

## Appendix B: document hashes

- This document, v1.0, SHA-256:
- Companion framework document, SHA-256:

Any edit to this document after publication produces a new version with a new hash and a dated changelog entry.

## Changelog

- **1.0 → 1.1, 2026-09-16, before publication.** Added `llama-guard-1` as a sixth judge level (labels already present in artifacts). Added the missing-response rule and per-entry coverage after verifying the artifacts directly. Recorded artifacts commit hash. Updated configuration count to 12 and compute estimate accordingly. No hypotheses or thresholds changed. Version 1.1 is the pre-registration of record.
