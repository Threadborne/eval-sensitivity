# Evaluation Sensitivity: The Formal Statement

*September 16, 2026. Assembled from one evening's workshop.*

---

## 0. Objects

**Choice space.** Θ = Θ₁ × Θ₂ × ⋯ × Θₙ. Each Θᵢ is one dial: a decision made during evaluation that is treated as not mattering. Product structure, not sequential.

**Declared choice space.** Θ_d ⊆ Θ. The subset the evaluator commits to searching, fixed and published *before* any search. Θ_d is never complete; it is a claim that can be refuted by exhibiting an axis it omits.

**System.** s ∈ S. The thing being evaluated. Held fixed throughout.

**Measures.** M : Θ × S → ℝᴷ. All K independent measures of the same underlying target, as one vector. M(θ, s) = (M₁(θ,s), …, Mₖ(θ,s)).

**Tolerances.** ε = (ε₁, …, εₖ), one per measure, fixed at the moment each measure is introduced and never revised.

---

## 1. What is reported versus what is true

Reported: **M(θ₀, s)** for one chosen θ₀ ∈ Θ.

True object: **M(Θ_d, s)** ⊆ ℝᴷ, the image of the declared choice space.

A single reported point is a sample of size one from that image, with the sampling rule unstated.

---

## 2. Worst-case sensitivity

**Definition.**

sens(s; Θ_d) = sup { ‖M(θ,s) − M(θ',s)‖ : θ, θ' ∈ Θ_d }

**Undecidable in general** (Rice). For arbitrary M, no procedure decides whether sens(s; Θ) is below any threshold.

**Search bound.** For any finite sampled set Q ⊆ Θ_d,

ŝens(s; Q) = max { ‖M(θ,s) − M(θ',s)‖ : θ, θ' ∈ Q } ≤ sens(s; Θ_d)

with equality only if Q happens to contain the extremal pair. The reportable quantity is the pair (ŝens, |Q|, search procedure), never sens itself.

**Game form.** Reporter chooses θ₀. Adversary chooses θ' ∈ Θ_d to maximize ‖M(θ',s) − M(θ₀,s)‖. The value of this game is the sensitivity relative to θ₀. Auditor and attacker compute the same maximum; the auditor publishes the range, the attacker publishes the peak.

---

## 3. Transfer: target axes versus nuisance axes

For a move θ → θ', define the raw displacement

Δ(θ, θ'; s) = M(θ',s) − M(θ,s) ∈ ℝᴷ

### 3.1 The sign test (original form)

**Target-aligned** iff Δ lies in the closed positive or negative orthant. **Nuisance** iff Δ has mixed signs. This is a sign test only. It cannot distinguish (+10, +0.001) from (+10, +10), and it flags (+1, −0.001) as nuisance when the negative component is noise.

### 3.2 Standardization

Let Σ be the K×K covariance of M across Θ_d (or across resampling folds at fixed θ). Define the standardized displacement

Δ̃ = Σ^(−1/2) Δ

If measures are uncorrelated this reduces to Δ̃ₖ = Δₖ / σₖ, each component in units of its own noise. If measures are correlated (accuracy and macro-F1 share a confusion matrix), Σ^(−1/2) removes the shared component.

**Effective number of measures.** K_eff = rank(Σ) (or a soft rank from the eigenvalue spectrum). Two perfectly correlated measures contribute K_eff = 1. This is the answer to "what counts as an independent measure": independence is defined by Σ, not by naming.

### 3.3 The declared target

The evaluator declares a **target cone** C ⊂ ℝᴷ: the set of displacement directions that count as improvement. Two natural choices:

- **Orthant cone.** C = ℝᴷ₊ (all measures up). Recovers the sign test at the boundary.
- **Ray.** C = { t·u : t ≥ 0 } for a unit vector u encoding how much each measure *should* move under true improvement. Stricter: it penalizes movement that does not transfer.

C is declared before search. It is refutable: someone can argue the cone is wrong. Same one-sided structure as Θ_d.

### 3.4 The nuisance fraction

ν(Δ̃; C) = dist(Δ̃, C) / ‖Δ̃‖ ∈ [0, 1]

the fraction of standardized movement that lies outside the target cone.

For the orthant cone: dist(Δ̃, ℝᴷ₊) = ‖Δ̃⁻‖ where Δ̃⁻ is the vector of negative parts. So

ν_orthant = ‖Δ̃⁻‖ / ‖Δ̃‖

the fraction of movement that went the wrong way. Zero iff sign-aligned. This is the magnitude-aware sign test.

For a ray along u: dist(Δ̃, ray) = ‖Δ̃ − (Δ̃·u)₊ u‖, so

ν_ray = sin θ(Δ̃, u) when Δ̃·u > 0, and 1 otherwise

the fraction of movement off the declared improvement axis.

**Property.** A move along a single measure, with K_eff independent measures, has cos θ = 1/√K_eff against the uniform ray. So ν_ray ≥ √(1 − 1/K_eff) for any change that fails to transfer. Non-transfer is penalized automatically and the penalty grows with K_eff. That is the transfer criterion made quantitative.

### 3.5 Classification

A dial Θᵢ is a **nuisance axis at level τ** if some move along Θᵢ alone has ν > τ. The sign test is τ = 0 with the orthant cone.

**Corollary (single-measure evals).** If K_eff = 1 then Δ̃ is a scalar, every cone is a ray, and ν ∈ {0, 1} carries no information beyond sign. Transfer cannot be tested.

### 3.6 Worked instance

Sleep-EDF, dial = crop wake epochs. Raw Δ = (+11.3 pts, +0.0002, −0.0472) over (accuracy, macro-F1, N1-F1). Fold-SD for accuracy is 0.0633; taking the other two at roughly 0.05 as a placeholder, Δ̃ ≈ (1.79, 0.004, −0.94).

- ν_orthant = 0.94 / 2.02 ≈ **0.47**. Nearly half the standardized movement was in the wrong direction.
- ν_ray, uniform u: Δ̃·u ≈ 0.49, ‖Δ̃‖ ≈ 2.02, so ν_ray ≈ **0.97**. Almost none of the movement was coordinated improvement.

Both say nuisance. They answer different questions: the orthant version asks how much was *harmful*, the ray version asks how much was *transfer*. The N1 and macro-F1 fold-SDs are placeholders and should be computed from the actual folds before either number is quoted.

---

## 4. Indiscernibility and the induced geometry

**Relation.** θ Rₖ θ' iff |Mₖ(θ,s) − Mₖ(θ',s)| ≤ εₖ for all k ≤ K.

Rₖ is reflexive and symmetric. It is **not** transitive: a tolerance relation, not an equivalence.

**Neighborhood.** Rₖ(θ) = { θ' ∈ Θ_d : θ Rₖ θ' }.

**Rough approximations** (Pawlak). For any X ⊆ Θ_d:

- Lower: Lₖ(X) = { θ : Rₖ(θ) ⊆ X }
- Upper: Uₖ(X) = { θ : Rₖ(θ) ∩ X ≠ ∅ }
- Boundary: Bₖ(X) = Uₖ(X) ∖ Lₖ(X)

Two choices are in the same class only if they are in each other's lower approximation. The boundary is the region where the measures at hand cannot decide.

**Induced distance.** d(θ, θ') is not given by Θ; it is induced by M. Two choices are close iff no measure separates them. This is Myhill-Nerode with measures playing the role of distinguishing suffixes.

**Reportable quantity.** |Bₖ| / |Θ_d|, the fraction of the declared choice space that is ambiguous under the current measures.

---

## 5. Refinement theorem

**Theorem.** Let Rₖ₊₁ be Rₖ intersected with the tolerance constraint of a new measure Mₖ₊₁, with all εₖ for k ≤ K unchanged. Then for every X ⊆ Θ_d:

 Lₖ(X) ⊆ Lₖ₊₁(X), Uₖ₊₁(X) ⊆ Uₖ(X), Bₖ₊₁(X) ⊆ Bₖ(X).

**Proof.** Rₖ₊₁ ⊆ Rₖ, hence Rₖ₊₁(θ) ⊆ Rₖ(θ) for every θ. A neighborhood inside X stays inside X when it shrinks (lower grows). A neighborhood disjoint from X stays disjoint when it shrinks (upper shrinks). Boundary is the difference. ∎

**Corollary.** Classes only split, never merge. This is the refinement property of L\*, recovered for tolerance relations.

**What the theorem does not say.** Bₖ₊₁ ⊆ Bₖ guarantees the boundary *shrinks*, not that it shrinks *toward the true structure*. A measure with εₖ₊₁ below its noise floor produces spurious splits. The boundary contracts; the classes are false. Refinement is provable; convergence is not.

**Two protocol requirements** are forced by the proof:
1. Each εₖ is frozen at introduction. Retuning any εₖ breaks Rₖ₊₁ ⊆ Rₖ.
2. Aggregation is intersection. "Close in every measure." Any weaker rule breaks the inclusion.

---

## 6. Expected-case sensitivity

Given a prior π on Θ_d, the Sobol decomposition:

Var_π[M] = Σᵢ Vᵢ + Σᵢ<ⱼ Vᵢⱼ + ⋯

First-order index Sᵢ = Vᵢ / Var_π[M]: the fraction of variance attributable to dial i alone. Total-effect index Sᵀᵢ: including all interactions involving i.

**The prior is not given.** Defensible choices:
- π_uniform over each dial's options (what multiverse analysis does implicitly; transparent, arbitrary)
- π_class, uniform over discovered lower-approximation classes (less arbitrary; classes are found, not assumed)
- π_emp, the empirical distribution of configurations in the published literature (the only prior that answers a question anyone asks: how much of the *field's* reported variance is nuisance)

**Observation.** "Which π" and "how large is Θ_d" are the same question. The prior problem is the ambiguity-set problem. Not a second hole; the first one, in different notation.

Worst-case (§2) and expected-case (§6) are distinct quantities answering distinct questions. Both are reported. The expected-case reports its prior.

---

## 7. The algorithm

**Input.** System s. Declared choice space Θ_d with dials Θ₁ … Θₙ. Measures M₁ … Mₖ with frozen tolerances ε. Search budget β.

**Refine.**
1. Initialize one class: all of Θ_d.
2. For each measure Mₖ in order: split every class wherever Mₖ separates members beyond εₖ, using intersection.
3. Compute lower and upper approximations of each resulting class; record the boundary fraction.
4. Stop when no measure splits any class. Output the quotient Q = Θ_d / Rₖ, represented by one element per lower-approximation class.

**Search.**
5. Run adversarial maximization of ‖M(θ,s) − M(θ₀,s)‖ over class representatives in Q, not over Θ_d, within budget β. Record ŝens and the extremal configuration θ*.

**Classify.**
6. For each dial i, compute Δ along that dial alone. Orthant-aligned → target axis. Mixed → nuisance axis.

**Decompose.**
7. Under a stated prior π, compute Sobol first-order and total-effect indices per dial.

**Validate.**
8. Hold out a subset of Θ_d. Check that the lower-approximation classes found on the rest reproduce on the held-out set. This is the only defense against spurious refinement (§5).

---

## 8. The report

What accompanies any published metric M(θ₀, s):

| Quantity | Symbol | Meaning |
|---|---|---|
| Declared choice space | Θ_d | What was searched. Refutable by omission. |
| Worst-case sensitivity | ŝens, |Q|, method | Floor on how far the number moves. Never a ceiling. |
| Extremal configuration | θ* | The choice that moved it most. |
| Transfer table | {i : nuisance} | Which dials split the measures. |
| Boundary fraction | |B| / |Θ_d| | How much of the choice space the measures can't resolve. |
| Sobol indices | Sᵢ, Sᵀᵢ under π | Expected-case attribution, with the prior named. |
| Held-out class stability | | Whether the refinement survived a fresh sample. |

---

## 9. What is provable and what is not

**Provable.**
- ŝens ≤ sens. Always. (§2)
- Boundary is monotone non-increasing under intersection-aggregated measures with frozen ε. (§5)
- Classes only split. (§5, corollary)
- K_eff = 1 evals cannot be transfer-tested. (§3.5, corollary)
- ν_ray ≥ √(1 − 1/K_eff) for any non-transferring change. (§3.4)

**Not provable, structurally.**
- That Θ_d is complete.
- That sens is small.
- That refinement converges to true structure.
- That a chosen π is correct.
- That the declared target cone C is the right cone.

Every unprovable item has the same shape: it can be refuted by a counterexample and never confirmed. This is Rice's theorem at the top, Popper in the middle, and the equivalence query at the bottom. The framework does not close these gaps. It makes each one a stated, refutable claim instead of an unstated assumption.

---

## 10. Lineage

All entries verified 2026-09-16 against primary sources (✓) or against a primary source's reference list (✓s).

| Piece | Source | Status | What it contributes |
|---|---|---|---|
| One-sidedness | Rice, "Classes of recursively enumerable sets and their decision problems," *Trans. AMS* 74(2), 358–366, 1953 | ✓ | Why robustness can only be refuted |
| Membership / equivalence asymmetry | Angluin, "Learning regular sets from queries and counterexamples," *Information and Computation* 75(2), 87–106, 1987. DOI 10.1016/0890-5401(87)90052-6 | ✓ | The query structure; L\* |
| Multiverse analysis | Steegen, Tuerlinckx, Gelman, Vanpaemel, *Perspectives on Psychological Science* 11(5), 702–712, 2016. DOI 10.1177/1745691616658637 | ✓ | Enumerate every defensible analysis |
| Specification curve | Simonsohn, Simmons, Nelson, *Nature Human Behaviour* 4(11), 1208–1214, 2020 | ✓s | Plot the whole distribution |
| Garden of forking paths | Gelman & Loken, "The garden of forking paths: Why multiple comparisons can be a problem, even when there is no 'fishing expedition' or 'p-hacking' and the research hypothesis was posited ahead of time," Columbia Dept. of Statistics, 2013 | ✓s | Why one analysis misleads |
| Variance attribution | Sobol', *Matem. Mod.* 2(1), 112–118, 1990; tr. *Math. Model. Comp. Exp.* 1(4), 407–414, 1993; Saltelli et al., *Global Sensitivity Analysis: The Primer*, Wiley 2008 | ✓ | §6 |
| Prior sensitivity of Sobol indices | Hart & Gremaud, arXiv 1812.07042 | ✓ | The §6 open problem is already studied |
| Rough approximation, equivalence case | Pawlak, "Rough sets," *Int. J. Computer and Information Sciences* 11(5), 341–356, 1982. DOI 10.1007/BF01001956 | ✓ | Lower/upper approximation |
| Rough approximation, tolerance case | Skowron & Stepaniuk, "Tolerance approximation spaces," *Fundamenta Informaticae* 27(2–3), 245–253, 1996. DOI 10.3233/FI-1996-272311 | ✓ | §4–5 rest on this |
| Tolerance on quantitative attributes | Słowiński, *Foundations of Computing and Decision Sciences* 18, 361–369, 1993 | ✓s | ε-indiscernibility on continuous measures |
| Tolerance spaces | Zeeman, "The topology of the brain and visual perception," in *Topology of 3-Manifolds*, 1962 | ✓s (cited by Pawlak 1982) | Origin of the non-transitive relation |

**Correction from verification.** Pawlak 1982 uses an equivalence relation. The tolerance generalization that §4–5 require is Skowron & Stepaniuk 1996. Pawlak's paper explicitly positions rough sets as an alternative to tolerance theory and cites Zeeman, so the lineage §4 claims is the historical one.

---

## 11. Prior work in ML, and where the gap actually is

Searched 2026-09-16. The claim "multiverse analysis has never been imported into ML" is **false**. Found:

| Work | What it does | What it doesn't |
|---|---|---|
| Simson, Pfisterer, Kern (?), "One Model Many Scores," *FAccT* 2024. DOI 10.1145/3630106.3658974 | Multiverse over model design *and evaluation* decisions, targeted at fairness metrics. Modular code released. | Fairness-specific. Reports distributions; no target/nuisance classifier, no adversarial search. **Closest prior work. Read in full before claiming novelty.** |
| Bouthillier, Laurent, Vincent, "Accounting for variance in machine learning benchmarks," *MLSys* 2021 | Formal variance accounting across benchmark runs. | Variance from randomness (seeds, splits), not from defensible methodological choices. |
| D'Amour et al., "Underspecification presents challenges for credibility in modern ML," *JMLR* 23, 2022 | Pipelines meeting identical training criteria diverge under shift. | Training-side, not evaluation-side. |
| Raitses, "On decision-valued maps and representational dependence," arXiv 2602.11295, Feb 2026 | Maps representation families to discrete outcomes; names persistence regions, boundaries, fractures. Content-addressed provenance. | Discrete outcomes only. Four-point demo. States it does not explain *why* a boundary exists. No measure vector, no transfer test. |
| Approximation algorithms for multiverse sensitivity (found via ResearchGate, authors not confirmed) | Sampling-based estimation of decision sensitivity using ~20% of the multiverse. | Estimates *ranking* of sensitive decisions by sampling. Not adversarial maximization. |
| 2021 position paper, arXiv 2104.08878 | Proposes multiverse for hyperparameter analysis. | Position only. |
| AutoML-Multiverse (medRxiv 2026); EDM 2025 student-success multiverse | Applied multiverse in clinical ML and education. | Domain applications; no framework. |

**What survives as unclaimed, after the search:**

1. **A vector of independent measures as Nerode distinguishers.** Prior work reports one metric's distribution, or several metrics side by side. None uses the joint movement of K measures to *classify* a choice as target or nuisance.
2. **The target cone and ν.** No prior work defines a magnitude-aware, noise-standardized nuisance fraction with a declared improvement cone.
3. **K_eff = rank(Σ) as the definition of measure independence.**
4. **Adversarial search over the choice space** as distinct from exhaustive enumeration or random sampling. The security posture.
5. **Rough-set treatment of the choice space** with the boundary fraction as a reportable quantity and the refinement theorem.
6. **Application to LLM safety benchmarks** (jailbreak ASR, judge sensitivity). No multiverse work found in this domain.

Items 1–3 are one contribution. Items 4–5 are one contribution. Item 6 is the empirical paper.

**What was overstated last night:** "nobody has imported multiverse analysis into ML." Corrected above.
