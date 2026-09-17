# The Number Is a Point. The Truth Is a Range.

*A research program, assembled September 16, 2026.*

---

## The problem in one sentence

When someone reports a test result, they made a dozen decisions along the way that they've decided don't matter, and they report the number as though those decisions were invisible. They aren't.

---

## 1. Every number hides a range

Which data to trim. Which grader to use. Where to draw the threshold. Each of these is a dial. Turn any dial and the number moves.

So a test result isn't a number. It's one point on a surface, and the surface is the metric as a function over every defensible choice you could have made. You published the height at one coordinate. Someone equally careful, at a different coordinate, gets a different height.

Honest reporting means saying how wide that surface is.

**Worked instance.** Sleep-EDF sleep staging. One dial: crop the long wake periods at the recording edges, or leave them in. Leaving them in moved accuracy 11.3 points. Model family, RF versus HGB, moved it 0.0005. The nuisance dial moved the number twenty thousand times more than the choice everyone argues about.

---

## 2. You can never close the range

There is always a dial you didn't think of. Another preprocessing step, another judge, another split.

This isn't a limitation of method. It's a theorem. Rice's theorem says any non-trivial property of what a program does is undecidable in general. "Is this metric robust" is a property of a function. You cannot decide it. You can only refute it.

So the honest shape of any robustness claim is a floor, never a ceiling:

> This number moves **at least** N points under choices that shouldn't matter, given a search of this size.

Lower bound only. Forever. Same structure as cryptanalysis: no cipher is proven secure, you report how much effort failed to break it.

---

## 3. What you can do instead

Three moves, in order.

**Declare the choice space before you search.** Pre-register which dials you'll turn. Publish the list. This doesn't close the hole; someone can always say you missed an axis. But it converts "trust me" into "here's what I checked, add to it."

**Search adversarially.** Don't sample the choice space, attack it. Find the configuration that moves the number the most. This is a maximization problem, and every tool for running one applies: random restarts, coordinate search, gradient-free methods for discrete axes.

**Report worst-found plus coverage.** Two tiers. Enumerable axes get exhaustive search and a true range. Non-enumerable axes get the search method and the worst configuration found, labeled as unbounded. Never mix the tiers into one number.

---

## 4. Telling inflation from improvement

The hard case: someone turns a dial and the number goes up. Did the system get better, or did the metric get gamed? The number itself cannot tell you.

**The test is transfer.** A dial is on a *target* axis if the improvement it produces shows up in an independent measure of the same underlying thing. It's a *nuisance* axis if the improvement doesn't transfer.

Sleep-EDF again. Cropping raised accuracy. Macro-F1 didn't move. F1 on the hardest class went down. Three measures of the same classifier disagreed about one change. That disagreement is the signature. When independent measures split, you've found a nuisance axis.

**Corollary.** A test with only one way of measuring cannot be checked this way. You can see how much it wobbles but never distinguish wobble from improvement. Single-measure evals are structurally unauditable. That's not a weakness in the method, it's a category, and knowing which benchmarks fall into it is worth something on its own.

---

## 5. The geometry of the choice space

The obvious objection: the choice space is infinite and unstructured. "Crop" and "don't crop" are adjacent in language and produce an 11-point jump. There's no distance between methodological decisions, so "I searched a neighborhood" means nothing.

The answer is that the geometry isn't given. It's induced.

Two choices are close if nothing you can measure distinguishes their effects. Far if something does. Distance is a property of what you've tested against, not of the choices themselves.

This is the Myhill-Nerode relation from automata theory. Two prefixes are equivalent iff no suffix separates them. Two evaluation choices are equivalent iff no independent measure separates them. You learn the metric by running distinguishing experiments, and every counterexample adds a dimension.

So "how big is the choice space" has an answer: how many equivalence classes does it have under the measures you've got. RF and HGB are in the same class (nothing separated them). Crop and don't-crop are in different classes (macro-F1 and accuracy split them). The space isn't infinite in any way that matters. It collapses to a handful of classes once you have enough measures to sort it.

---

## 6. Three ways the same failure appears

The number moving while the model doesn't is one shape wearing three faces. They don't unify under one detection method, and they shouldn't.

**No agent.** The metric is sensitive to something orthogonal to what it claims to measure. Nobody did anything wrong. Sleep-EDF. This is the scariest one because there's nobody to catch.

**Honest agent.** Someone optimizes the proxy in good faith and drifts from the target without noticing. Most quality programs.

**Strategic agent.** Someone optimizes the appearance of the proxy. Reports filed, not problems caught.

On the landscape from section 1, these are three trajectories: standing on a steep face without knowing it, walking uphill on the wrong axis, and deliberately searching the wrong axis for its peak.

---

## 7. The lineage

None of this is new in pieces. The pieces don't cite each other.

- **Falsification** (Popper). Theories aren't proven; they survive attempts to kill them.
- **Query learning** (Angluin). Membership queries you can answer; equivalence queries you can only refute. L\* lives here.
- **Multiverse analysis** (Steegen et al. 2016; Simonsohn's specification curve; Gelman's garden of forking paths). Social psychology's response to the replication crisis: run every defensible analysis and plot the distribution. A decade old. Never imported into ML benchmarking.
- **Global sensitivity analysis** (Saltelli, Sobol indices). Decompose output variance into contributions from each input. This is "how much of this number is nuisance," formalized.
- **Certified vs empirical robustness** (adversarial ML). Proven-safe versus attacked-and-held. The two-tier coverage distinction, already named.
- **Distributionally robust optimization.** The "ambiguity set" problem: how big should the choice space be. Genuinely unsolved.

The gap is narrow and specific: multiverse analysis plus Sobol decomposition plus adversarial search, applied to ML evaluation. Nobody has done it.

---

## 8. The tool

Not a formula. A thing you point at an eval.

Input: a benchmark, a declared list of dials, a search budget.

Process: adversarial search over the dials for the configuration that moves the headline number most. For each move, check whether it transfers to every independent measure available.

Output:
- Worst-found configuration and how far it moved the number
- Coverage: exhaustive range for enumerable axes, method and budget for the rest
- Transfer table: which dials moved all measures together (target), which split them (nuisance)
- Equivalence classes: which dials turned out to be the same dial

The search the tool runs is the same search a cheater would run to inflate the number. Same algorithm. The difference is what you publish: the range or the peak. That's the security-research posture, and it's why this belongs in that lane.

---

## 9. Three papers, one program

**"The Number Moved, the Model Didn't."** One dial, hand-turned. Cropping moved accuracy 11.3 points; macro-F1 moved 0.0002; N1 got worse. The transfer test, run before there was a name for it.

**"Six Ways an Eval Lies."** The taxonomy. Probably has a seventh way now: single-measure evals are unauditable.

**The JailbreakBench judge-sensitivity paper.** Same move, different domain. Attack success rate as a function of judge choice. If judges disagree on ranking, judge is a nuisance axis and the leaderboard is measuring graders. If they agree on ranking but not level, judge is a calibration offset and the leaderboard survives. Two distinguishable outcomes, testable with published artifacts, no new attacks needed.

Two instances is a pattern. Three is a program.

---

## 10. Why this shape

Every piece of this is the same operation: hand the thing to something that can break it, and report what broke.

Red teaming does it to systems. Cryptanalysis does it to ciphers. Break-and-fix does it to yourself. L\* does it to a black box one query at a time. The equivalence query is the only kind of learning that escapes your own priors, because the counterexample comes from outside the space of questions you knew how to ask.

That's what the tool is. An adversary you can point at a number.
