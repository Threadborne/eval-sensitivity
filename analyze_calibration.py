"""Calibration analysis. Reads calibration.jsonl and analysis/report.json, writes analysis/calibration_report.json. Implements pre-reg v1.5 M3 and H3'."""

import argparse
import collections
import json
import os


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def verdict(row, parser):
    if row["reason"] == "stored_label_no_raw":
        return row["shipped"] if parser == "shipped" else "not_recomputable"
    if row["reason"] == "judge_timeout":
        return None
    v = row[parser]
    return None if v is None else bool(v)


def metrics(rows, parser):
    tp = fp = tn = fn = null = 0
    for r in rows:
        v = verdict(r, parser)
        if v == "not_recomputable":
            return None
        h = bool(r["human_majority"])
        if v is None:
            null += 1
            v = False
        if v and h:
            tp += 1
        elif v and not h:
            fp += 1
        elif not v and h:
            fn += 1
        else:
            tn += 1
    n = tp + fp + tn + fn
    acc = (tp + tn) / n if n else None
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    return {"n": n, "accuracy": acc, "precision": prec, "recall": rec, "tp": tp, "fp": fp, "tn": tn, "fn": fn, "unparseable": null, "unparseable_rate": null / n if n else None, "unparseable_counted_as": "not_jailbroken"}


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", default="calibration.jsonl")
    ap.add_argument("--artifact-report", default="analysis/report.json")
    ap.add_argument("--out", default="analysis/calibration_report.json")
    args = ap.parse_args()

    rows = load(args.calibration)
    by_judge = collections.defaultdict(list)
    for r in rows:
        by_judge[r["judge"]].append(r)

    m3 = {}
    for judge, jrows in sorted(by_judge.items()):
        for parser in ("shipped", "corrected"):
            m = metrics(jrows, parser)
            if m is not None:
                m3[f"{judge}|{parser}"] = m

    tau = {}
    if os.path.exists(args.artifact_report):
        rep = json.load(open(args.artifact_report))
        tau = {k: v["tau"] for k, v in rep["by_entry_set"]["all18"]["tau_vs_reference"]["A"].items() if v["tau"] is not None}

    pairs = [(k, tau[k], m3[k]["accuracy"]) for k in m3 if k in tau]
    h3p = None
    if len(pairs) >= 3:
        rho = spearman([p[1] for p in pairs], [p[2] for p in pairs])
        h3p = {"n_configs": len(pairs), "spearman_rho": rho, "supported": (rho is not None and rho > 0), "pairs": [{"config": k, "tau_vs_reference": t, "accuracy_vs_humans": a} for k, t, a in sorted(pairs, key=lambda p: -p[1])]}

    ref_acc = m3.get("llama3-70b|shipped", {}).get("accuracy")
    out = {"n_rows": len(rows), "M3_accuracy_vs_human_majority": m3, "reference_judge_accuracy": ref_acc, "H3_prime": h3p}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=2)

    print(f"{'config':32s} {'acc':>6} {'prec':>6} {'rec':>6} {'unpars':>7}")
    for k, m in sorted(m3.items(), key=lambda kv: -(kv[1]['accuracy'] or 0)):
        f = lambda x: f"{x:.3f}" if x is not None else "  -  "
        print(f"{k:32s} {f(m['accuracy']):>6} {f(m['precision']):>6} {f(m['recall']):>6} {m['unparseable']:>7}")
    if h3p:
        print(f"\nH3' Spearman rho(tau_vs_ref, acc_vs_humans) over {h3p['n_configs']} configs = {h3p['spearman_rho']:.3f}  supported={h3p['supported']}")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
