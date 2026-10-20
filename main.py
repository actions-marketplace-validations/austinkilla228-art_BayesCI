import ctypes
from pathlib import Path
from git_reader import get_commits,get_changed_files,get_ci_log
from likelihood import get_likelihoods
from prior_net import get_prior



path = Path(__file__).resolve().parent/"bayes_engine.dll"
lib = ctypes.CDLL(str(path))

class BayesModel(ctypes.Structure):
    _fields_ = [
            ("count",ctypes.c_size_t),
            ("probabilities",ctypes.POINTER(ctypes.c_double))
    ]

lib.bayes_create.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_size_t
]
lib.bayes_create.restype = ctypes.POINTER(BayesModel)

lib.bayes_update.argtypes = [
        ctypes.POINTER(BayesModel),
        ctypes.POINTER(ctypes.c_double)
]

lib.bayes_update.restype = ctypes.c_int

lib.bayes_predict.argtypes = [
        ctypes.POINTER(BayesModel),
        ctypes.POINTER(ctypes.c_size_t)
]
lib.bayes_predict.restype = ctypes.c_size_t

lib.bayes_free.argtypes = [ctypes.POINTER(BayesModel)]
lib.bayes_free.restype = None

lib.print_topk.argtypes = [
        ctypes.POINTER(BayesModel),
        ctypes.POINTER(ctypes.c_size_t)
]

def get_probs(prior,likelihood,commits): 
    n = len(commits)
    prior = (ctypes.c_double *n)(*prior)
    likelihood = (ctypes.c_double *n)(*likelihood)
    ranking = (ctypes.c_size_t*n)()
    model = lib.bayes_create(prior,n)

    commit_prob_dict = dict()
    if not model:
        raise RuntimeError("Failed create model")
    try:
        status = lib.bayes_update(model,likelihood)
        if status != 0:
            print(status)
            raise RuntimeError("Bayes Update failed")
        val = lib.bayes_predict(model,ranking)
        for i in range(len(ranking)):
            prob_id = ranking[i]

            probability = model.contents.probabilities[prob_id]

            commit_prob_dict.update({commits[prob_id] : probability})
    finally:
        lib.bayes_free(model)
    return commit_prob_dict


    for sha in commits:
        files = get_changed_files(repo,sha)
        if "CMakeLists.txt" in files:
            likelihood.append(0.9)
        elif any(f.endswith(".c") for f in files):
            likelihood.append(0.3)
        else:
            likelihood.append(0.1)
    return likelihood

if __name__ == "__main__":
    ci_log,exit_code,repo = get_ci_log("configs/config_ci.yaml")

    if exit_code != 0:
        commits = get_commits(repo)
        n = len(commits)
        prior = [1.0/n]*n


        #prior = get_prior(commits,"configs/prior_vals.yaml")
        likelihood = get_likelihoods(repo,commits,ci_log)
        #print(likelihood)
        result = get_probs(prior,likelihood,commits)
        #for sha,p in zip(commits,likelihood):
         #   print(sha[:8],get_changed_files(repo,sha),p)

        for sha, probability in result.items():
            print(f"{sha[:8]}: {probability:.2%}")
    else:
        print("BUILD SUCCESS")
