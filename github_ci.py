import zipfile
import io
import json
import os
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError


def get_successful_runs(repo, workflow, branch):
    """
    Success actions in github actions

    repo:     "austinkilla228-art/BayesCI"
    workflow: "ci.yml"
    branch:   "main"

    return: list SHA of success commit
    """
    params = urlencode({
        "branch": branch,
        "status": "success",
        "per_page": 100,
    })

    url = (
        f"https://api.github.com/repos/{repo}"
        f"/actions/workflows/{workflow}/runs?{params}"
    )

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "BayesCI",
    }

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)

    try:
        with urlopen(request, timeout=15) as response:
            data = json.load(response)
    except HTTPError as error:
        raise RuntimeError(
            f"GitHub API returned HTTP {error.code}"
        ) from error

    return [
        run["head_sha"]
        for run in data["workflow_runs"]
    ]

import subprocess


def is_ancestor(repo_path, good_sha, failed_sha):
    result = subprocess.run(
        [
            "git", "-C", str(repo_path),
            "merge-base", "--is-ancestor",
            good_sha, failed_sha
        ],
        capture_output=True
    )

    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False

    raise RuntimeError(result.stderr.decode())


def get_last_good(repo_path, repo, workflow, branch, failed_sha):
    successful_runs = get_successful_runs(repo, workflow, branch)

    for good_sha in successful_runs:
        if good_sha == failed_sha:
            continue

        if is_ancestor(repo_path, good_sha, failed_sha):
            return good_sha

    return None

  
def get_failed_log(repo, run_id):
    """
    repo:   "austinkilla228-art/BayesCI"
    run_id: id of github actions run

    return: text of logs 
    """
    url = (
        f"https://api.github.com/repos/{repo}"
        f"/actions/runs/{run_id}/logs"
    )

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "BayesCI",
    }

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)

    try:
        with urlopen(request, timeout=30) as response:
            archive_data = response.read()
    except HTTPError as error:
        raise RuntimeError(
            f"GitHub API returned HTTP {error.code}"
        ) from error

    logs = []

    with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
        for name in archive.namelist():
            if name.endswith(".txt"):
                content = archive.read(name).decode(
                    "utf-8", errors="replace"
                )
                logs.append(content)

    return "\n".join(logs)



if __name__ == "__main__":
    runs = get_successful_runs(
        repo="austinkilla228-art/BayesCI",
        workflow="ci.yml",
        branch="main",
    )

    for sha in runs:
        print(sha)
