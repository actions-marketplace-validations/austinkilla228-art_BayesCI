"""Minimal evidence likelihood model for BayesCI (Python 3.10+, stdlib).

For each candidate commit, observed features are F/S/B in {0, 1, None}.
We assume one culprit among the candidates, and a simple conditional model:
P(X | H_i) = P(x_i | culprit) * product_{j != i} P(x_j | innocent).
Common innocent factors cancel, so the per-candidate likelihood is proportional
 to P(x_i | culprit) / P(x_i | innocent).

Assumptions: conditional independence of features given culprit status and of
commit observations given the culprit. These are approximations, not validated
probability estimates. Defaults are illustrative and MUST be calibrated before
reporting results as real-world probabilities.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from typing import Mapping
from git_reader import get_diff
from cmake_parser import parse_log as parse_cmake
from extract_features import extract_features
from gcc_clang import parse_log
FEATURES = ('file', 'symbol', 'build')


@dataclass(frozen=True)
class LikelihoodModel:
    # Placeholder probabilities, not measurements. Replace using real labeled CI data.
    culprit: Mapping[str, float] = field(default_factory=lambda: {
        'file': 0.65, 'symbol': 0.60, 'build': 0.35,
    })
    innocent: Mapping[str, float] = field(default_factory=lambda: {
        'file': 0.15, 'symbol': 0.10, 'build': 0.10,
    })

    def __post_init__(self) -> None:
        for label, probs in (('culprit', self.culprit), ('innocent', self.innocent)):
            if set(probs) != set(FEATURES):
                raise ValueError(f'{label} must contain exactly {FEATURES}')
            for feature, p in probs.items():
                if not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 < p < 1:
                    raise ValueError(f'{label}[{feature}] must be in (0, 1)')


def log_likelihood_ratio(observation: Mapping[str, int | None], model: LikelihoodModel) -> float:
    """log P(x_i | culprit) / P(x_i | innocent). None contributes no evidence."""
    unknown = set(observation) - set(FEATURES)
    if unknown:
        raise ValueError(f'unknown features: {sorted(unknown)}')
    score = 0.0
    for feature in FEATURES:
        value = observation.get(feature)
        if value is None:
            continue
        if type(value) is not int or value not in (0, 1):
            raise ValueError(f'{feature} must be 0, 1, or None')
        pc, pn = model.culprit[feature], model.innocent[feature]
        score += math.log(pc / pn) if value else math.log((1 - pc) / (1 - pn))
    return score


def likelihoods(features_by_commit: Mapping[str, Mapping[str, int | None]],
                model: LikelihoodModel | None = None) -> dict[str, float]:
    """Positive relative likelihood factors for libbayes; common scale cancels."""
    model = model or LikelihoodModel()
    logs = {sha: log_likelihood_ratio(obs, model) for sha, obs in features_by_commit.items()}
    if not logs:
        return {}
    offset = max(logs.values())
    return {sha: math.exp(score - offset) for sha, score in logs.items()}


def posterior(features_by_commit: Mapping[str, Mapping[str, int | None]],
              prior: Mapping[str, float] | None = None,
              model: LikelihoodModel | None = None) -> dict[str, float]:
    """Reference Python implementation; production may call C bayes_update."""
    if not features_by_commit:
        return {}
    ids = set(features_by_commit)
    if prior is None:
        prior = {sha: 1.0 / len(ids) for sha in features_by_commit}
    if set(prior) != ids:
        raise ValueError('prior must contain exactly the candidate commit IDs')
    if any(not isinstance(p, (int, float)) or not math.isfinite(p) or p < 0 for p in prior.values()):
        raise ValueError('prior values must be finite and nonnegative')
    if sum(prior.values()) <= 0:
        raise ValueError('prior must have positive total mass')
    factors = likelihoods(features_by_commit, model)
    weights = {sha: prior[sha] * factors[sha] for sha in features_by_commit}
    total = sum(weights.values())
    if total <= 0:
        raise ValueError('posterior has zero total mass')
    return {sha: weight / total for sha, weight in weights.items()}


def get_likelihoods(repo_path, commits, ci_log):
    lines = ci_log.splitlines()

    diagnostics = parse_log(lines)
    diagnostics += parse_cmake(lines)
    
    print("=== DIAGNOSTICS ===")
    print("Count:", len(diagnostics))
    for d in diagnostics[:10]:
        print(d)
    diffs = {
        commit: get_diff(repo_path, commit)
        for commit in commits
    }

    features = extract_features(diagnostics, diffs)
    factors = likelihoods(features)
    
    for commit in commits:
        print(
            f"{commit[:8]} | "
            f"evidence={features[commit]} | "
            f"likelihood={factors[commit]:.4f}"
        )
    return [float(factors[commit]) for commit in commits]
