"""Scoring and storage for the JBB judge/parser sensitivity study.

Scoring and storage ONLY. No statistic is computed here -- Kendall's tau, nu,
spreads, bootstraps, K_eff and the rough-set boundary fraction (pre-reg §5, §6
steps 4-8) belong in a separate analysis file that reads the JSONL this
produces. If you are about to add a mean to this file, stop.

Design constraints, from the work order and pre-reg v1.1:

  * The `jailbreakbench` PyPI package is never imported. Artifact JSONs are read
    directly off disk. Its parser is the object under test.
  * The judge is called ONCE per (entry, behavior, judge). Raw output is stored
    verbatim, and both parser conditions are derived from that stored string
    (pre-reg §6 step 2, §7). Parsers never see the live response.
  * Every write is append-only JSONL. A run is resumable: on restart, any
    (entry, behavior_index, judge) triple already in the output is skipped.

ROW SCHEMA
    {entry, behavior_index, judge, raw, shipped, corrected, reason, timestamp}

    raw       verbatim judge completion, or null when no judge was called
    shipped   verdict under Dial 1 `shipped`
    corrected verdict under Dial 1 `corrected`, or null where not recomputable
    reason    null on a normal scored row; otherwise one of
                missing_response          -- pre-reg §2 missing-response rule
                stored_label_no_raw       -- pre-reg §3 final paragraph
                stored_label_absent       -- stored label field not in artifact
                unparseable_judge_reply   -- issue #50: empty/absent verdict is
                                             an error, not a verdict

M2 NOTE (pre-reg §4)
    M2 is refusal rate under Llama3RefusalJudge, under the same parser
    condition. This script does not compute it: the work order fixes a row
    schema with a single verdict pair and no judge-task field. M2 therefore
    needs a second pass that reuses parsers.REFUSAL_PROMPT and writes
    judge_task="refusal" rows. Two of the eight defects in issue #50
    (L110+L146) live on that path and are unexercised until it exists.
    Flagged rather than silently designed around.
"""

import argparse
import datetime
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

import parsers

# ---------------------------------------------------------------------------
# Dial 2, pre-reg §3. Six levels.
#
# `ollama_model` is deliberately None for the four local judges. Pre-reg
# Appendix A requires the local judge model identifiers and precision to be
# recorded at execution time; inventing a tag here would put an unrecorded
# choice into a pre-registered study. --judge-models supplies them, and the
# mapping used is echoed into the run manifest.
# ---------------------------------------------------------------------------

JUDGES = {
    # Stored-label judges. Zero compute. Never called.
    "llama3-70b": {
        "source": "stored",
        "artifact_field": "jailbroken",
        "ollama_model": None,
    },
    "llama-guard-1": {
        "source": "stored",
        "artifact_field": "jailbroken_llama_guard1",
        "ollama_model": None,
    },
    # Local judges, driven by parsers.JUDGE_PROMPT.
    "llama3-8b-instruct": {"source": "local", "artifact_field": None, "ollama_model": None},
    "qwen2.5-7b-instruct": {"source": "local", "artifact_field": None, "ollama_model": None},
    "mistral-7b-instruct": {"source": "local", "artifact_field": None, "ollama_model": None},
    "gemma-2-9b-it": {"source": "local", "artifact_field": None, "ollama_model": None},
}

EXCLUDED_ARTIFACT_FILENAMES = {"attack-info.json", "evaluation.json", "submission.json"}
EXCLUDED_ARTIFACT_DIRS = {"test-artifact"}

EXPECTED_ENTRY_COUNT = 18
EXPECTED_BEHAVIOR_COUNT = 100


# ---------------------------------------------------------------------------
# Artifact loading
# ---------------------------------------------------------------------------

def discover_entries(artifacts_root: str) -> list:
    """Return sorted (entry_name, path) for the attack artifacts.

    An entry is one leaderboard row: an attack against a target model. Metadata
    files and the test artifact are excluded.
    """
    root = pathlib.Path(artifacts_root) / "attack-artifacts"
    if not root.is_dir():
        raise FileNotFoundError(f"no attack-artifacts/ under {artifacts_root}")
    found = []
    for path in sorted(root.rglob("*.json")):
        rel = path.relative_to(root)
        if rel.parts[0] in EXCLUDED_ARTIFACT_DIRS:
            continue
        if path.name in EXCLUDED_ARTIFACT_FILENAMES:
            continue
        found.append((str(rel.with_suffix("")), path))
    return found


def load_entry(path) -> list:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["jailbreaks"]


def coverage_report(entries: list) -> list:
    """Per-entry response coverage. Compared against pre-reg §2 before scoring."""
    rows = []
    for name, path in entries:
        records = load_entry(path)
        null_n = sum(1 for r in records if r.get("response") is None)
        empty_n = sum(
            1 for r in records
            if isinstance(r.get("response"), str) and not r["response"].strip()
        )
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


# ---------------------------------------------------------------------------
# Append-only store
# ---------------------------------------------------------------------------

def load_done(out_path: str) -> set:
    """Triples already written. Tolerates a truncated final line from a kill."""
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
                sys.stderr.write(
                    f"warning: {out_path}:{lineno} is not valid JSON "
                    f"(truncated write?); ignoring for resume\n"
                )
                continue
            done.add((row["entry"], row["behavior_index"], row["judge"]))
    return done


def append_row(out_path: str, row: dict) -> None:
    """One row, one line, flushed and fsynced. Append-only: nothing is rewritten."""
    with open(out_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def now() -> str:
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


# ---------------------------------------------------------------------------
# Judge transport
# ---------------------------------------------------------------------------

class OllamaJudge:
    """Ollama HTTP chat API, temperature 0.

    Mirrors Llama3Classifier._build_classifier_input (classifier.py L86-L91):
    one user message carrying the formatted prompt, no system message.
    """

    def __init__(self, host: str, model: str, timeout: int = 300):
        self.url = host.rstrip("/") + "/api/chat"
        self.model = model
        self.timeout = timeout

    def __call__(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0},
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        # Verbatim. No strip, no normalisation -- the parsers do that, and the
        # difference between them is the measurement.
        return body["message"]["content"]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def parse_both(raw: str):
    """(shipped, corrected, reason) from one stored judge completion."""
    shipped = parsers.parse_shipped(raw)
    try:
        corrected = parsers.parse_corrected(raw)
        reason = None
    except parsers.JudgeParseError:
        # issue #50 L63/L110: an absent verdict is an error, not a verdict. The
        # shipped parser has no error channel and still returns a bool; that
        # asymmetry is a finding, so it is recorded rather than smoothed over.
        corrected = None
        reason = "unparseable_judge_reply"
    return shipped, corrected, reason


def score(artifacts_root, out_path, judge_models, host, judges=None,
          limit_entries=None, dry_run=False):
    entries = discover_entries(artifacts_root)

    if limit_entries:
        entries = entries[:limit_entries]
    elif len(entries) != EXPECTED_ENTRY_COUNT:
        raise SystemExit(
            f"expected {EXPECTED_ENTRY_COUNT} entries, found {len(entries)}. "
            "Artifacts commit drift. Stop and reconcile with pre-reg Appendix A."
        )

    judge_names = judges or list(JUDGES)
    for name in judge_names:
        if name not in JUDGES:
            raise SystemExit(f"{name} is not a Dial 2 level in the pre-registration")

    clients = {}
    for name in judge_names:
        spec = JUDGES[name]
        if spec["source"] != "local":
            continue
        model = judge_models.get(name) or spec["ollama_model"]
        if not model:
            raise SystemExit(
                f"no Ollama model pinned for judge '{name}'. Pre-reg Appendix A "
                "requires local judge identifiers to be recorded before the run. "
                "Pass --judge-models name=tag."
            )
        clients[name] = OllamaJudge(host, model)

    done = load_done(out_path)
    written = skipped = called = 0

    for entry_name, path in entries:
        records = load_entry(path)
        if len(records) != EXPECTED_BEHAVIOR_COUNT and not limit_entries:
            raise SystemExit(
                f"{entry_name}: {len(records)} behaviors, expected "
                f"{EXPECTED_BEHAVIOR_COUNT}. Stop and reconcile."
            )

        for record in records:
            idx = record["index"]
            goal = record["goal"]
            response = record.get("response")

            for judge_name in judge_names:
                if (entry_name, idx, judge_name) in done:
                    skipped += 1
                    continue
                spec = JUDGES[judge_name]

                # --- Step 5: stored-label judges. Nothing is called. ---------
                if spec["source"] == "stored":
                    field = spec["artifact_field"]
                    if field not in record:
                        # Not every artifact carries every stored label. Pre-reg
                        # §3 asserts both are present for all entries; for
                        # jailbroken_llama_guard1 that is false. Recorded as an
                        # absence, not backfilled and not recomputed.
                        row = make_row(entry_name, idx, judge_name,
                                       None, None, None, "stored_label_absent")
                    else:
                        # Pre-reg §3 final paragraph: shipped condition IS the
                        # stored label; corrected is not recomputable because
                        # only the parsed verdict was ever stored, never raw.
                        row = make_row(entry_name, idx, judge_name,
                                       None, bool(record[field]), None,
                                       "stored_label_no_raw")
                    append_row(out_path, row)
                    written += 1
                    continue

                # --- Step 4: missing response. Judge is not called. ----------
                if response is None or not str(response).strip():
                    # Pre-reg §2 missing-response rule: not jailbroken under
                    # every configuration, matching JBB's own convention.
                    row = make_row(entry_name, idx, judge_name,
                                   None, False, False, "missing_response")
                    append_row(out_path, row)
                    written += 1
                    continue

                # --- Step 4: one judge call, both parsers off stored raw -----
                prompt = parsers.JUDGE_PROMPT.format(goal=goal, response=response)
                if dry_run:
                    skipped += 1
                    continue
                try:
                    raw = clients[judge_name](prompt)
                except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
                    # A transport failure is not a verdict. Nothing is written,
                    # so the resume pass retries this triple.
                    sys.stderr.write(
                        f"transport error {entry_name} idx={idx} "
                        f"judge={judge_name}: {exc!r}\n"
                    )
                    continue
                called += 1
                shipped, corrected, reason = parse_both(raw)
                append_row(out_path, make_row(entry_name, idx, judge_name,
                                              raw, shipped, corrected, reason))
                written += 1

    return {"entries": len(entries), "rows_written": written,
            "rows_skipped": skipped, "judge_calls": called}


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artifacts", required=True, help="clone of JailbreakBench/artifacts")
    ap.add_argument("--out", required=True, help="append-only JSONL output")
    ap.add_argument("--host", default="http://127.0.0.1:11434", help="Ollama base URL")
    ap.add_argument("--judges", nargs="*", default=None, help="Dial 2 levels to run")
    ap.add_argument("--judge-models", nargs="*", default=[], metavar="NAME=TAG",
                    help="pin local judges to Ollama tags (pre-reg Appendix A)")
    ap.add_argument("--limit-entries", type=int, default=None,
                    help="first N entries only; for stub runs")
    ap.add_argument("--coverage-only", action="store_true",
                    help="print the coverage table and exit without scoring")
    ap.add_argument("--dry-run", action="store_true",
                    help="walk the work without calling any judge")
    args = ap.parse_args(argv)

    entries = discover_entries(args.artifacts)
    rows = coverage_report(entries)
    print(f"entries discovered: {len(entries)}")
    print(f"{'entry':<58}{'n':>5}{'resp':>6}{'null':>6}{'empty':>7}{'jb':>5}{'lg1':>5}")
    for r in rows:
        print(f"{r['entry']:<58}{r['behaviors']:>5}{r['with_response']:>6}"
              f"{r['null_response']:>6}{r['empty_response']:>7}"
              f"{'Y' if r['has_jailbroken_field'] else 'N':>5}"
              f"{'Y' if r['has_llama_guard1_field'] else 'N':>5}")
    if args.coverage_only:
        return 0

    models = {}
    for pair in args.judge_models:
        name, _, tag = pair.partition("=")
        models[name] = tag

    stats = score(args.artifacts, args.out, models, args.host,
                  judges=args.judges, limit_entries=args.limit_entries,
                  dry_run=args.dry_run)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
