import yaml
import math

def get_prior(commits,config_file):
    with open(config_file) as f:
        config = yaml.safe_load(f)["model"]

    scores = []

    for commit in commits:
        z = config["bias"]

        for name,weight in zip(
                config["features"], config["weights"]
        ):
            z += weight*math.log1p(max(0,commit[name]))

            scores.append(math.exp(z))

    total = sum(scores)
    return [score/total for score in scores]
