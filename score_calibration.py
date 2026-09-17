"""Score the JBB judge_comparison calibration set with local judges. Writes calibration.jsonl. No statistics here."""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

import parsers
from score import JUDGES, OllamaJudge, append_row, git_head, load_done, now, parse_both

STORED_COLUMNS = {"llama3-70b": "llama3_cf", "llamaguard2": "llamaguard2_cf", "gpt4": "gpt4_cf", "harmbench": "harmbench_cf"}


def load_calibration(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def make_row(index, judge, raw, shipped, corrected, reason, human_majority):
    return {
        "index": index,
        "judge": judge,
        "raw": raw,
        "shipped": shipped,
        "corrected": corrected,
        "reason": reason,
        "human_majority": human_majority,
        "timestamp": now(),
    }


def write_manifest(out_path, cal_path, judge_models, host, options, judges):
    manifest = {
        "started": now(),
        "calibration_file": cal_path,
        "calibration_sha256": hashlib.sha256(open(cal_path, "rb").read()).hexdigest(),
        "script_commit": git_head(pathlib.Path(__file__).resolve().parent),
        "host": host,
        "options": options,
        "judges": judges,
        "judge_models": judge_models,
        "judge_prompt_sha256": hashlib.sha256(parsers.JUDGE_PROMPT.encode()).hexdigest(),
    }
    with open(out_path + ".manifest.json", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, indent=2) + "\n")


def load_done_cal(out_path):
    done = set()
    if not os.path.exists(out_path):
        return done
    with open(out_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            done.add((r["index"], r["judge"]))
    return done


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", default="calibration_set.jsonl")
    ap.add_argument("--out", default="calibration.jsonl")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--judges", nargs="*", default=None)
    ap.add_argument("--judge-models", nargs="*", default=[], metavar="NAME=TAG")
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--num-predict", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args(argv)

    cal = load_calibration(args.calibration)
    if len(cal) != 300:
        raise SystemExit(f"expected 300 calibration rows, found {len(cal)}")

    local = [j for j, s in JUDGES.items() if s["source"] == "local"]
    judge_names = args.judges or (list(STORED_COLUMNS) + local)
    for name in judge_names:
        if name not in JUDGES and name not in STORED_COLUMNS:
            raise SystemExit(f"{name} is not a known judge")

    models = {}
    for pair in args.judge_models:
        name, _, tag = pair.partition("=")
        models[name] = tag

    options = {"temperature": 0, "num_ctx": args.num_ctx}
    if args.num_predict is not None:
        options["num_predict"] = args.num_predict

    clients = {}
    for name in judge_names:
        if name in STORED_COLUMNS:
            continue
        model = models.get(name)
        if not model:
            raise SystemExit(f"no Ollama model pinned for judge '{name}'; pass --judge-models {name}=TAG")
        clients[name] = OllamaJudge(args.host, model, options, args.timeout)

    write_manifest(args.out, args.calibration, models, args.host, options, judge_names)
    done = load_done_cal(args.out)
    written = skipped = called = 0

    for judge in judge_names:
        for r in cal:
            idx = int(r["Index"])
            if (idx, judge) in done:
                skipped += 1
                continue
            hm = int(r["human_majority"])
            if judge in STORED_COLUMNS:
                v = bool(int(r[STORED_COLUMNS[judge]]))
                append_row(args.out, make_row(idx, judge, None, v, None, "stored_label_no_raw", hm))
                written += 1
                continue
            prompt = parsers.JUDGE_PROMPT.format(goal=r["goal"], response=r["target_response"])
            try:
                raw = clients[judge](prompt)
            except TimeoutError:
                append_row(args.out, make_row(idx, judge, None, None, None, "judge_timeout", hm))
                written += 1
                continue
            except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
                if isinstance(getattr(exc, "reason", None), TimeoutError):
                    append_row(args.out, make_row(idx, judge, None, None, None, "judge_timeout", hm))
                    written += 1
                    continue
                sys.stderr.write(f"transport error idx={idx} judge={judge}: {exc!r}\n")
                continue
            called += 1
            shipped, corrected, reason = parse_both(raw)
            append_row(args.out, make_row(idx, judge, raw, shipped, corrected, reason, hm))
            written += 1

    print(json.dumps({"rows_written": written, "rows_skipped": skipped, "judge_calls": called}, indent=2))


if __name__ == "__main__":
    main()
