"""Analysis for the JBB judge/parser sensitivity study. Reads results.jsonl, writes analysis/. Implements pre-reg §5 and §6."""

import argparse
import collections
import itertools
import json
import math
import os
import random
import statistics

REF_JUDGE = "llama3-70b"
REF_PARSER = "shipped"
TAU_THRESHOLD = 0.80
NU_THRESHOLD = 0.5
BOOTSTRAP_N = 1000
THIN_ENTRY = "PAIR/black_box/llama-2-7b-chat-hf"
N_BEHAVIORS = 100


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def index_rows(rows):
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r["judge"], r["entry"])][r["behavior_index"]] = r
    return by


def verdict(row, parser):
    if row["reason"] == "stored_label_absent":
        return "absent"
    if row["reason"] == "missing_response":
        return False
    if row["reason"] == "stored_label_no_raw":
        return row["shipped"] if parser == "shipped" else "not_recomputable"
    if row["reason"] == "judge_timeout":
        return None
    v = row[parser]
    return None if v is None else bool(v)


def asr(rows_for_entry, parser, behaviors=None):
    idx = behaviors if behaviors is not None else sorted(rows_for_entry)
    vs = [verdict(rows_for_entry[i], parser) for i in idx]
    if any(v == "absent" for v in vs):
        return None
    if any(v == "not_recomputable" for v in vs):
        return None
    n = len(vs)
    true_n = sum(1 for v in vs if v is True)
    null_n = sum(1 for v in vs if v is None)
    conv_a = true_n / n
    conv_b = true_n / (n - null_n) if n - null_n > 0 else None
    return {"A": conv_a, "B": conv_b, "unparseable_rate": null_n / n, "n": n, "true": true_n, "null": null_n}


def configs(by):
    judges = sorted({j for j, _ in by})
    out = []
    for j in judges:
        for p in ("shipped", "corrected"):
            out.append((j, p))
    return out


def asr_matrix(by, entries, behaviors=None):
    mat = {}
    for j, p in configs(by):
        for e in entries:
            if (j, e) not in by:
                continue
            a = asr(by[(j, e)], p, behaviors)
            if a is not None:
                mat[(j, p, e)] = a
    return mat


def ranking(mat, cfg, entries, conv):
    vals = {e: mat[(cfg[0], cfg[1], e)][conv] for e in entries if (cfg[0], cfg[1], e) in mat and mat[(cfg[0], cfg[1], e)][conv] is not None}
    return vals


def kendall_tau_b(x, y):
    n = len(x)
    if n < 2:
        return None
    conc = disc = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif (dx > 0) == (dy > 0):
                conc += 1
            else:
                disc += 1
    denom = math.sqrt((conc + disc + tx) * (conc + disc + ty))
    return (conc - disc) / denom if denom else None


def tau_vs_reference(mat, entries, conv):
    ref = ranking(mat, (REF_JUDGE, REF_PARSER), entries, conv)
    out = {}
    for cfg in configs_present(mat):
        if cfg == (REF_JUDGE, REF_PARSER):
            continue
        other = ranking(mat, cfg, entries, conv)
        common = sorted(set(ref) & set(other))
        if len(common) < 3:
            out[cfg] = {"tau": None, "n_entries": len(common)}
            continue
        out[cfg] = {"tau": kendall_tau_b([ref[e] for e in common], [other[e] for e in common]), "n_entries": len(common)}
    return out


def configs_present(mat):
    return sorted({(j, p) for j, p, _ in mat})


def spread_vs_gap(mat, entries, conv):
    ref = ranking(mat, (REF_JUDGE, REF_PARSER), entries, conv)
    ref_sorted = sorted(ref.values())
    gaps = [b - a for a, b in zip(ref_sorted, ref_sorted[1:])]
    g_min = min(g for g in gaps if g > 0) if any(g > 0 for g in gaps) else 0.0
    spreads = {}
    for e in entries:
        vals = [mat[(j, p, e)][conv] for (j, p) in configs_present(mat) if (j, p, e) in mat and mat[(j, p, e)][conv] is not None]
        if len(vals) >= 2:
            spreads[e] = max(vals) - min(vals)
    max_spread_entry = max(spreads, key=spreads.get) if spreads else None
    return {
        "g_min": g_min,
        "gaps_zero_count": sum(1 for g in gaps if g == 0),
        "spread_per_entry": spreads,
        "max_spread": spreads[max_spread_entry] if max_spread_entry else None,
        "max_spread_entry": max_spread_entry,
        "ratio_max_spread_to_g_min": (spreads[max_spread_entry] / g_min) if (max_spread_entry and g_min > 0) else None,
        "entries_with_spread_exceeding_g_min": [e for e, s in spreads.items() if g_min > 0 and s > g_min],
    }


def parser_disagreement(by):
    out = {}
    for (j, e), recs in by.items():
        for r in recs.values():
            if r["raw"] is None:
                continue
            d = out.setdefault(j, {"scored": 0, "shipped_true": 0, "corrected_true": 0, "unparseable": 0, "disagree": 0, "shipped_false_corrected_true": 0, "shipped_true_corrected_false": 0, "timeout": 0})
            d["scored"] += 1
            if r["reason"] == "judge_timeout":
                d["timeout"] += 1
                continue
            if r["shipped"]:
                d["shipped_true"] += 1
            if r["corrected"] is None:
                d["unparseable"] += 1
                continue
            if r["corrected"]:
                d["corrected_true"] += 1
            if r["shipped"] != r["corrected"]:
                d["disagree"] += 1
                if r["corrected"] and not r["shipped"]:
                    d["shipped_false_corrected_true"] += 1
                else:
                    d["shipped_true_corrected_false"] += 1
    return out


def bootstrap_sd(by, entries, conv, n_boot, seed=0):
    rng = random.Random(seed)
    cfgs = None
    samples = collections.defaultdict(list)
    for _ in range(n_boot):
        behaviors = [rng.randrange(N_BEHAVIORS) for _ in range(N_BEHAVIORS)]
        mat = asr_matrix(by, entries, behaviors)
        if cfgs is None:
            cfgs = configs_present(mat)
        for key, a in mat.items():
            if a[conv] is not None:
                samples[key].append(a[conv])
    return {k: (statistics.pstdev(v) if len(v) > 1 else 0.0) for k, v in samples.items()}


def rough_boundary(mat, sd, entries, conv):
    cfgs = configs_present(mat)
    vec = {}
    for cfg in cfgs:
        v = {}
        for e in entries:
            k = (cfg[0], cfg[1], e)
            if k in mat and mat[k][conv] is not None:
                v[e] = mat[k][conv]
        vec[cfg] = v

    def indiscernible(a, b):
        common = set(vec[a]) & set(vec[b])
        if not common:
            return False
        for e in common:
            eps = max(sd.get((a[0], a[1], e), 0.0), sd.get((b[0], b[1], e), 0.0))
            if abs(vec[a][e] - vec[b][e]) > eps:
                return False
        return True

    nbr = {a: {b for b in cfgs if indiscernible(a, b)} for a in cfgs}
    boundary_flags = {}
    for a in cfgs:
        X = nbr[a]
        lower = {b for b in cfgs if nbr[b] <= X}
        upper = {b for b in cfgs if nbr[b] & X}
        boundary_flags[a] = {"neighborhood": sorted(map(list, X)), "lower": len(lower), "upper": len(upper), "boundary": len(upper - lower)}
    mean_boundary = sum(f["boundary"] for f in boundary_flags.values()) / (len(cfgs) * len(cfgs)) if cfgs else None
    return {"per_config": {f"{a[0]}|{a[1]}": v for a, v in boundary_flags.items()}, "mean_boundary_fraction": mean_boundary, "n_configs": len(cfgs)}


def k_eff_note():
    return {
        "K_available": 1,
        "measures_present": ["M1 ASR"],
        "measures_absent": ["M2 refusal rate (requires the refusal-judge scoring pass, not yet run)", "M3 human-label agreement (requires JBB judge_comparison dataset, not yet pulled)"],
        "consequence": "K_eff = 1. The transfer test and nu are undefined per pre-reg 3.5 corollary. H3 cannot be evaluated on this data.",
    }


def fmt_cfg(cfg):
    return f"{cfg[0]}|{cfg[1]}"


def write_matrix_csv(mat, entries, path):
    cfgs = configs_present(mat)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("entry," + ",".join(f"{fmt_cfg(c)}:A,{fmt_cfg(c)}:B,{fmt_cfg(c)}:unparseable" for c in cfgs) + "\n")
        for e in entries:
            cells = []
            for c in cfgs:
                k = (c[0], c[1], e)
                if k in mat:
                    a = mat[k]
                    cells += [f"{a['A']:.4f}", "" if a["B"] is None else f"{a['B']:.4f}", f"{a['unparseable_rate']:.4f}"]
                else:
                    cells += ["", "", ""]
            fh.write(e + "," + ",".join(cells) + "\n")


def decide(tau_a, tau_b, sg_a, sg_b):
    def h1(t):
        vals = [v["tau"] for v in t.values() if v["tau"] is not None]
        return {"supported": any(v < TAU_THRESHOLD for v in vals), "min_tau": min(vals) if vals else None, "min_tau_config": min((v["tau"], fmt_cfg(c)) for c, v in t.items() if v["tau"] is not None)[1] if vals else None}

    def h2(sg):
        return {"supported": bool(sg["entries_with_spread_exceeding_g_min"]), "g_min": sg["g_min"], "max_spread": sg["max_spread"], "ratio": sg["ratio_max_spread_to_g_min"], "n_entries_exceeding": len(sg["entries_with_spread_exceeding_g_min"])}

    return {
        "H1_reordering": {"threshold": TAU_THRESHOLD, "convention_A": h1(tau_a), "convention_B": h1(tau_b)},
        "H2_resolution": {"convention_A": h2(sg_a), "convention_B": h2(sg_b)},
        "H3_dial_classification": {"threshold": NU_THRESHOLD, "status": "NOT EVALUABLE", "reason": k_eff_note()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results.jsonl")
    ap.add_argument("--out", default="analysis")
    ap.add_argument("--bootstrap", type=int, default=BOOTSTRAP_N)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rows = load(args.results)
    by = index_rows(rows)
    all_entries = sorted({e for _, e in by})
    entry_sets = {"all18": all_entries, "excl_thin17": [e for e in all_entries if e != THIN_ENTRY]}

    report = {"n_rows": len(rows), "entries": all_entries, "reference": fmt_cfg((REF_JUDGE, REF_PARSER)), "K_eff": k_eff_note(), "parser_disagreement": parser_disagreement(by), "by_entry_set": {}}

    for set_name, entries in entry_sets.items():
        mat = asr_matrix(by, entries)
        write_matrix_csv(mat, entries, os.path.join(args.out, f"asr_matrix_{set_name}.csv"))
        tau_a = tau_vs_reference(mat, entries, "A")
        tau_b = tau_vs_reference(mat, entries, "B")
        sg_a = spread_vs_gap(mat, entries, "A")
        sg_b = spread_vs_gap(mat, entries, "B")
        sd_a = bootstrap_sd(by, entries, "A", args.bootstrap, args.seed)
        rb_a = rough_boundary(mat, sd_a, entries, "A")
        report["by_entry_set"][set_name] = {
            "n_entries": len(entries),
            "configs": [fmt_cfg(c) for c in configs_present(mat)],
            "tau_vs_reference": {"A": {fmt_cfg(c): v for c, v in tau_a.items()}, "B": {fmt_cfg(c): v for c, v in tau_b.items()}},
            "spread_vs_gap": {"A": sg_a, "B": sg_b},
            "rough_boundary_A": rb_a,
            "decisions": decide(tau_a, tau_b, sg_a, sg_b),
        }

    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    d = report["by_entry_set"]["all18"]["decisions"]
    print(f"rows={report['n_rows']}  entries={len(all_entries)}  configs={len(report['by_entry_set']['all18']['configs'])}")
    print(f"H1 (tau<{TAU_THRESHOLD}): A supported={d['H1_reordering']['convention_A']['supported']} min_tau={d['H1_reordering']['convention_A']['min_tau']} at {d['H1_reordering']['convention_A']['min_tau_config']} | B supported={d['H1_reordering']['convention_B']['supported']} min_tau={d['H1_reordering']['convention_B']['min_tau']}")
    print(f"H2 (spread>g_min): A supported={d['H2_resolution']['convention_A']['supported']} g_min={d['H2_resolution']['convention_A']['g_min']:.4f} max_spread={d['H2_resolution']['convention_A']['max_spread']:.4f} n_exceeding={d['H2_resolution']['convention_A']['n_entries_exceeding']} | B supported={d['H2_resolution']['convention_B']['supported']}")
    print(f"H3: {d['H3_dial_classification']['status']} ({d['H3_dial_classification']['reason']['consequence']})")
    print("parser disagreement per local judge:")
    for j, v in sorted(report["parser_disagreement"].items()):
        print(f"  {j:22s} scored={v['scored']:4d} disagree={v['disagree']:4d} shipF_corrT={v['shipped_false_corrected_true']:4d} shipT_corrF={v['shipped_true_corrected_false']:4d} unparseable={v['unparseable']:4d} timeout={v['timeout']:3d}")
    print(f"rough boundary mean fraction (A, all18): {report['by_entry_set']['all18']['rough_boundary_A']['mean_boundary_fraction']:.3f}")
    print(f"written to {args.out}/")


if __name__ == "__main__":
    main()
