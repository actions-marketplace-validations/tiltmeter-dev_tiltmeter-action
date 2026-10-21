"""Helpers for the Tiltmeter GitHub Action. Runs inside Tiltmeter's own environment."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ICONS = {"breaking": "🔴", "warning": "🟠", "info": "🔵"}
OUTCOMES = {
    "drift": "drift",
    "changed": "info changes",
    "clean": "clean",
    "baseline": "baseline recorded",
    "error": "check failed",
}
VERDICTS = {
    0: "No drift.",
    1: "Warning-level drift.",
    2: "Breaking drift.",
    3: "A check could not run.",
    4: "Configuration or usage error. See the step log.",
}


def state_dir(config: str) -> None:
    """Print the baseline folder as a GITHUB_OUTPUT line, mirroring Tiltmeter's own rule."""
    try:
        data = yaml.safe_load(Path(config).read_text(encoding="utf-8")) or {}
        state = str(data.get("state_dir") or ".tiltmeter")
    except (OSError, yaml.YAMLError, AttributeError):
        state = ".tiltmeter"
    state = os.path.expanduser(state)
    if not os.path.isabs(state):
        state = os.path.normpath(os.path.join(os.path.dirname(config), state))
    print(f"dir={state}")


def _cell(value: Any) -> str:
    return (
        str(value).replace("|", "\\|").replace("\n", " ") if value is not None else ""
    )


def summary(results_path: str, code: str, summary_path: str) -> None:
    """Print the results to the log and, when asked, write them to the job summary."""
    try:
        results: list[dict[str, Any]] = json.loads(
            Path(results_path).read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        results = []

    verdict = VERDICTS.get(int(code), f"Exit code {code}.")
    md = ["## Tiltmeter", "", f"**{verdict}** Exit code `{code}`.", ""]
    log = [f"Tiltmeter: {verdict} (exit code {code})"]

    if results:
        md += ["| Endpoint | Status | Result | Changes |", "|---|---|---|---|"]
        for r in results:
            severity = r.get("max_severity")
            outcome = OUTCOMES.get(r.get("outcome", ""), r.get("outcome", ""))
            label = (
                f"{ICONS.get(severity, '')} {severity}".strip() if severity else outcome
            )
            status = r.get("status_code") or "—"
            md.append(
                f"| `{_cell(r['endpoint_id'])}` | {status} | {_cell(label)} | {len(r['changes'])} |"
            )
            log.append(f"  {r['endpoint_id']}: {label}, {len(r['changes'])} changes")

        for r in results:
            if not r["changes"] and not r.get("error"):
                continue
            md += ["", f"### `{_cell(r['endpoint_id'])}`", ""]
            if r.get("error"):
                md.append(f"> {_cell(r['error'])}")
                log.append(f"  {r['endpoint_id']}: {r['error']}")
            if r["changes"]:
                md += [
                    "| Severity | Change | Path | Before | After | Note |",
                    "|---|---|---|---|---|---|",
                ]
                for c in r["changes"]:
                    md.append(
                        f"| {ICONS.get(c['severity'], '')} {c['severity']} | {c['kind']} "
                        f"| `{_cell(c['path'])}` | {_cell(c.get('before'))} | {_cell(c.get('after'))} "
                        f"| {_cell(c.get('hint'))} |"
                    )
                    log.append(f"    {c['severity']:<8} {c['message']}")
            explanation = r.get("explanation")
            if explanation:
                md += [
                    "",
                    f"**What changed.** {explanation['summary']}",
                    "",
                    f"**Impact.** {explanation['impact']}",
                    "",
                    f"**Next step.** {explanation['suggested_action']}",
                ]

    print("\n".join(log))
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(md) + "\n")


def main() -> None:
    command, *args = sys.argv[1:]
    if command == "state-dir":
        state_dir(*args)
    elif command == "summary":
        summary(*args)
    else:
        raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
