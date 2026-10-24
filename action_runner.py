"""Entry point for the composite GitHub Action (not the local CLI)."""
from __future__ import annotations

import os
import math
from pathlib import Path

from github_ci import get_failed_log, get_last_good
from git_reader import get_commits_since
from main import get_probs,get_likelihoods


def _write_summary(markdown: str) -> None:
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as stream:
            stream.write(markdown + "\n")
    print(markdown)


def run() -> dict[str, float] | None:
    # A preceding checkout step supplies the repository to inspect. Do not
    # execute any scripts or build commands from that (possibly faulty) tree.
    repo_path = os.environ["GITHUB_WORKSPACE"]
    repository = os.environ["BAYESCI_REPOSITORY"]
    workflow = os.environ["BAYESCI_WORKFLOW"]
    branch = os.environ["BAYESCI_BRANCH"]
    sha = os.environ["BAYESCI_FAILED_SHA"]
    run_id = int(os.environ["BAYESCI_RUN_ID"])

    last_good = get_last_good(repo_path, repository, workflow, branch, sha)
    if last_good is None:
        _write_summary("## BayesCI\n\nNo prior successful run was found among the 100 most recent successful workflow runs on this branch. No ranking was produced.")
        return None

    commits = get_commits_since(repo_path, last_good, sha)
    if not commits:
        _write_summary("## BayesCI\n\nNo commits between the last successful run and this failed run.")
        return None

    log = get_failed_log(repository, run_id)
    scores = get_likelihoods(repo_path, commits, log)

    # Equal likelihoods contain no evidence that distinguishes commits.
    # Do not publish a misleading, arbitrary Top-3 (e.g. Count: 0).
    if (len(scores) != len(commits) or not scores
            or any(not math.isfinite(v) or v < 0 for v in scores)):
        _write_summary("## BayesCI — failed CI analysis\n\nInvalid likelihood values; no ranking was produced.")
        return None
    if all(math.isclose(v, scores[0], rel_tol=1e-12, abs_tol=1e-12)
           for v in scores[1:]):
        _write_summary(
            "## BayesCI — failed CI analysis\n\n"
            f"Last successful commit: `{last_good[:12]}`\n\n"
            f"Failed commit: `{sha[:12]}`\n\n"
            f"Candidates: **{len(commits)}**\n\n"
            "No distinguishing evidence was found in the build log and Git diffs. "
            "BayesCI cannot identify a likely culprit from these inputs."
        )
        return None

    prior = [1 / len(commits)] * len(commits)
    ranking = get_probs(prior, scores, commits)

    # Markdown links use validated full hexadecimal SHAs from git rev-list.
    rows = [
        "## BayesCI — failed CI analysis",
        "",
        f"Last successful commit: `{last_good[:12]}`",
        f"Failed commit: `{sha[:12]}`",
        f"Candidates: **{len(commits)}**",
        "",
        "| Rank | Commit | Relative score |",
        "| ---: | --- | ---: |",
    ]
    for index, (commit, value) in enumerate(list(ranking.items())[:3], 1):
        rows.append(f"| {index} | [`{commit[:12]}`](https://github.com/{repository}/commit/{commit}) | {value:.1%} |")
    rows.extend([
        "",
        "> Scores are normalized heuristic rankings, not calibrated probabilities of fault.",
        "> If log diagnostics cannot be parsed, equal scores may reflect lack of evidence.",
    ])
    _write_summary("\n".join(rows))
    return ranking


if __name__ == "__main__":
    run()
