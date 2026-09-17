"""Scoring and storage only. No statistics here."""

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

JUDGES = {
    "llama3-70b": {"source": "stored", "artifact_field": "jailbroken"},
    "llama-guard-1": {"source": "stored", "artifact_field": "jailbroken_llama_guard1"},
    "llama3-8b-instruct": {"source": "local"},
    "qwen2.5-7b-instruct": {"source": "local"},
    "mistral-7b-instruct": {"source": "local"},
    "gemma-2-9b-it": {"source": "local"},
}

EXCLUDED_ARTIFACT_FILENAMES = {"attack-info.json", "evaluation.json", "submission.json"}
EXCLUDED_ARTIFACT_DIRS = {"test-artifact"}
EXPECTED_ENTRY_COUNT = 18
EXPECTED_BEHAVIOR_COUNT = 100


def discover_entries(artifacts_root):
    root = pathlib.Path(artifacts_root) / "attack-artifacts"
    if not root.is_dir():
        raise FileNotFoundError(f"no attack-artifacts/ under {artifacts_root}")
    found = []
    for path in sorted(root.rglob("*.json")):
        rel = path.relative_to(root)
        if rel.parts[0] in EXCLUDED_ARTIFACT_DIRS or path.name in EXCLUDED_ARTIFACT_FILENAMES:
            continue
        found.append((rel.with_suffix("").as_posix(), path))
    return found


def load_entry(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["jailbreaks"]


def coverage_report(entries):
    rows = []
    for name, path in entries:
        records = load_entry(path)
        null_n = sum(1 for r in records if r.get("response") is None)
        empty_n = sum(1 for r in records if isinstance(r.get("response"), str) and not r["response"].strip())
        rows.append({
            "entry": name,
            "behaviors": len(records),
            "with_response": len(records) - null_n - empty_n,
            "null_response": null_n,
            "empty_response": empty_n,
            "has_jailbroken_field": all("jailbroken" in r for r in records),
            "has_llama_guard1_field": all("jailbroken_llama_guard1" in r for r in records),
        })
    return rows


def git_head(path):
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def load_done(out_path):
    done = set()
    if not os.path.exists(out_path):
        return done
    with open(out_path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                sys.stderr.write(f"warning: {out_path}:{lineno} not valid JSON; ignoring for resume\n")
                continue
            done.add((row["entry"], row["behavior_index"], row["judge"]))
    return done


def append_row(out_path, row):
    with open(out_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def make_row(entry, behavior_index, judge, raw, shipped, corrected, reason):
    return {
        "entry": entry,
        "behavior_index": behavior_index,
        "judge": judge,
        "raw": raw,
        "shipped": shipped,
        "corrected": corrected,
        "reason": reason,
        "timestamp": now(),
    }


class OllamaJudge:
    def __init__(self, host, model, options, timeout=30):
        self.url = host.rstrip("/") + "/api/chat"
        self.model = model
        self.options = options
        self.timeout = timeout

    def __call__(self, prompt):
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": self.options,
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["message"]["content"]


def parse_both(raw):
    shipped = parsers.parse_shipped(raw)
    try:
        return shipped, parsers.parse_corrected(raw), None
    except parsers.JudgeParseError:
        return shipped, None, "unparseable_judge_reply"


def write_manifest(out_path, artifacts_root, judge_models, host, options, judges):
    manifest = {
        "started": now(),
        "artifacts_commit": git_head(artifacts_root),
        "script_commit": git_head(pathlib.Path(__file__).resolve().parent),
        "host": host,
        "options": options,
        "judges": judges,
        "judge_models": judge_models,
        "judge_prompt_sha256": hashlib.sha256(parsers.JUDGE_PROMPT.encode()).hexdigest(),
    }
    with open(out_path + ".manifest.json", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, indent=2) + "\n")


def score(artifacts_root, out_path, judge_models, host, judges=None,
          limit_entries=None, dry_run=False, options=None, timeout=30):
    options = options or {"temperature": 0, "num_ctx": 8192}
    entries = discover_entries(artifacts_root)
    if limit_entries:
        entries = entries[:limit_entries]
    elif len(entries) != EXPECTED_ENTRY_COUNT:
        raise SystemExit(f"expected {EXPECTED_ENTRY_COUNT} entries, found {len(entries)}")

    judge_names = judges or list(JUDGES)
    for name in judge_names:
        if name not in JUDGES:
            raise SystemExit(f"{name} is not a Dial 2 level")

    clients = {}
    for name in judge_names:
        if JUDGES[name]["source"] != "local":
            continue
        model = judge_models.get(name)
        if not model:
            raise SystemExit(f"no Ollama model pinned for judge '{name}'; pass --judge-models {name}=TAG")
        clients[name] = OllamaJudge(host, model, options, timeout)

    loaded = {}
    for entry_name, path in entries:
        records = load_entry(path)
        if len(records) != EXPECTED_BEHAVIOR_COUNT and not limit_entries:
            raise SystemExit(f"{entry_name}: {len(records)} behaviors, expected {EXPECTED_BEHAVIOR_COUNT}")
        loaded[entry_name] = records

    if not dry_run:
        write_manifest(out_path, artifacts_root, judge_models, host, options, judge_names)

    done = load_done(out_path)
    written = skipped = called = 0

    for judge_name in judge_names:
        spec = JUDGES[judge_name]
        for entry_name, _ in entries:
            for record in loaded[entry_name]:
                idx = record["index"]
                if (entry_name, idx, judge_name) in done:
                    skipped += 1
                    continue

                if spec["source"] == "stored":
                    field = spec["artifact_field"]
                    if field not in record:
                        row = make_row(entry_name, idx, judge_name, None, None, None, "stored_label_absent")
                    else:
                        row = make_row(entry_name, idx, judge_name, None, bool(record[field]), None, "stored_label_no_raw")
                    append_row(out_path, row)
                    written += 1
                    continue

                response = record.get("response")
                if response is None or not str(response).strip():
                    append_row(out_path, make_row(entry_name, idx, judge_name, None, False, False, "missing_response"))
                    written += 1
                    continue

                prompt = parsers.JUDGE_PROMPT.format(goal=record["goal"], response=response)
                if dry_run:
                    skipped += 1
                    continue
                try:
                    raw = clients[judge_name](prompt)
                except TimeoutError:
                    sys.stderr.write(f"judge timeout {entry_name} idx={idx} judge={judge_name}\n")
                    append_row(out_path, make_row(entry_name, idx, judge_name, None, None, None, "judge_timeout"))
                    written += 1
                    continue
                except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
                    if isinstance(getattr(exc, "reason", None), TimeoutError):
                        sys.stderr.write(f"judge timeout {entry_name} idx={idx} judge={judge_name}\n")
                        append_row(out_path, make_row(entry_name, idx, judge_name, None, None, None, "judge_timeout"))
                        written += 1
                        continue
                    sys.stderr.write(f"transport error {entry_name} idx={idx} judge={judge_name}: {exc!r}\n")
                    continue
                called += 1
                shipped, corrected, reason = parse_both(raw)
                append_row(out_path, make_row(entry_name, idx, judge_name, raw, shipped, corrected, reason))
                written += 1

    return {"entries": len(entries), "rows_written": written, "rows_skipped": skipped, "judge_calls": called}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--judges", nargs="*", default=None)
    ap.add_argument("--judge-models", nargs="*", default=[], metavar="NAME=TAG")
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--num-predict", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--limit-entries", type=int, default=None)
    ap.add_argument("--coverage-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    entries = discover_entries(args.artifacts)
    rows = coverage_report(entries)
    print(f"entries discovered: {len(entries)}")
    print(f"{'entry':<58}{'n':>5}{'resp':>6}{'null':>6}{'empty':>7}{'jb':>5}{'lg1':>5}")
    for r in rows:
        print(f"{r['entry']:<58}{r['behaviors']:>5}{r['with_response']:>6}{r['null_response']:>6}"
              f"{r['empty_response']:>7}{'Y' if r['has_jailbroken_field'] else 'N':>5}"
              f"{'Y' if r['has_llama_guard1_field'] else 'N':>5}")
    if args.coverage_only:
        return 0

    models = {}
    for pair in args.judge_models:
        name, _, tag = pair.partition("=")
        models[name] = tag
    options = {"temperature": 0, "num_ctx": args.num_ctx}
    if args.num_predict is not None:
        options["num_predict"] = args.num_predict
    stats = score(args.artifacts, args.out, models, args.host, judges=args.judges,
                  limit_entries=args.limit_entries, dry_run=args.dry_run,
                  options=options, timeout=args.timeout)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
