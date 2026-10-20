from git_reader import extract_features,get_diff

def get_likelihood(features: dict) -> float:
    return (
            1.0
            +2.0 * features["file_match"]
            +4.0 * features["symbol_match"]
            +2.0 * features["build_match"]
            +2.0 * features["test_match"]
            )

def get_likelihoods(repo_path, commits,ci_log):
    result = []

    for commit in commits:
        diff = get_diff(repo_path,commit)
        features = extract_features(ci_log,diff)
        result.append(float(get_likelihood(features)))
    return result


