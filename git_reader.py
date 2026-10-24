import subprocess
from pathlib import Path
import re
import yaml

def get_commits(repo_path):
    result = subprocess.check_output(["git","-C",str(repo_path),"log", "--format=%H"],text=True)
    return result.splitlines()


def get_changed_files(repo,commit):
    result = subprocess.check_output(
            [
                "git", "-C", str(repo),
                "diff-tree","--root","--no-commit-id",
                "--name-only","-r",commit
            ],
            text = True,
    )
    return result.splitlines()

def get_diff(repo_path:str, commit:str) -> str:
    return subprocess.check_output(
            [
                "git","-C",repo_path,
                "show", "--format=","--no-ext-diff",
                commit
            ],
            text = True,
            errors = "replace"
    )

def get_ci_log(config_path):
    with open(config_path,encoding="utf-8") as f:
        config = yaml.safe_load(f)

    command = config["build"]["command"]
    repo_path = config["project"]["path"]

    result = subprocess.run(
            command,
            cwd = repo_path,
            shell=True,
            capture_output=True,
            text=True,
            errors = "replace"
    )
    ci_log =result.stdout + "\n" + result.stderr

    return ci_log,result.returncode,repo_path

def get_commits_since(repo_path, last_good, bad_commit="HEAD"):
    """
    returns commits from last_good till bad_commit
    """
    subprocess.run(
        ["git", "-C", str(repo_path), "merge-base",
         "--is-ancestor", last_good, bad_commit],
        check=True
    )

    result = subprocess.check_output(
        [
            "git", "-C", str(repo_path),
            "rev-list",
            "--reverse",
            f"{last_good}..{bad_commit}"
        ],
        text=True
    )

    return result.splitlines()


def gtet_commits_since(repo,path,last_good,failed_sha):
    result = subprocess.chek_output(
            ["git", "-C", str(repo_path),
             "rev-list", "--reverse",
             f"{last_good}..{failed_sha}"
             ],
            text=True
    )
    return result.splitlines()
