"""Small-sample left-censored regression diagnostics for condition screens."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd


def normal_logcdf(value: float) -> float:
    probability = 0.5 * math.erfc(-value / math.sqrt(2.0))
    return math.log(max(probability, 1e-300))


def tobit_objective(
    parameters: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    censored: np.ndarray,
    limits: np.ndarray,
    ridge_alpha: float,
) -> float:
    beta = parameters[:-1]
    sigma = math.exp(float(parameters[-1]))
    mean = x @ beta
    result = ridge_alpha * float(np.sum(beta[1:] ** 2))
    for index in range(len(y)):
        if censored[index]:
            result -= normal_logcdf(float((limits[index] - mean[index]) / sigma))
        else:
            z = float((y[index] - mean[index]) / sigma)
            result += math.log(sigma) + 0.5 * z * z + 0.5 * math.log(2.0 * math.pi)
    return result


def tobit_fit(
    x: np.ndarray,
    y: np.ndarray,
    censored: np.ndarray,
    limits: np.ndarray,
    ridge_alpha: float = 0.3,
) -> dict:
    """Fit a left-censored Gaussian model with deterministic coordinate search."""
    substituted = np.where(censored, limits / 2.0, y)
    penalty = ridge_alpha * np.eye(x.shape[1])
    penalty[0, 0] = 0.0
    beta = np.linalg.pinv(x.T @ x + penalty) @ x.T @ substituted
    sigma = max(float(np.std(substituted - x @ beta)), 5.0)
    parameters = np.concatenate([beta, [math.log(sigma)]])
    steps = np.concatenate([np.maximum(np.abs(beta) * 0.25, 0.25), [0.25]])
    best = tobit_objective(parameters, x, y, censored, limits, ridge_alpha)
    for _ in range(1000):
        improved = False
        for index in range(len(parameters)):
            for direction in (-1.0, 1.0):
                candidate = parameters.copy()
                candidate[index] += direction * steps[index]
                score = tobit_objective(candidate, x, y, censored, limits, ridge_alpha)
                if score + 1e-10 < best:
                    parameters, best, improved = candidate, score, True
        if not improved:
            steps *= 0.6
            if float(np.max(steps)) < 1e-6:
                break
    return {
        "coefficients": parameters[:-1],
        "sigma": math.exp(float(parameters[-1])),
        "negative_log_likelihood": best,
        "converged": float(np.max(steps)) < 1e-4,
    }


def ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float = 0.3) -> np.ndarray:
    penalty = alpha * np.eye(x.shape[1])
    penalty[0, 0] = 0.0
    return np.linalg.pinv(x.T @ x + penalty) @ x.T @ y


def solvent_design(data: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, float, float]:
    et30 = data["solvent_reichardt_et30_kcal_mol"].astype(float).to_numpy()
    center, scale = float(np.mean(et30)), float(np.std(et30))
    x = np.column_stack([np.ones(len(data)), (et30 - center) / max(scale, 1e-12)])
    return x, et30, center, scale


def measured_loo(
    data: pd.DataFrame, detection_limit: float, method: str
) -> tuple[float, list[dict]]:
    measured_indices = data.index[data["yield_status"] == "measured"].tolist()
    rows: list[dict] = []
    for held_index in measured_indices:
        train = data.drop(index=held_index).reset_index(drop=True)
        test = data.loc[held_index]
        x_train, _, center, scale = solvent_design(train)
        x_test = np.asarray([1.0, (float(test["solvent_reichardt_et30_kcal_mol"]) - center) / max(scale, 1e-12)])
        measured = train["yield_status"] == "measured"
        if method == "exclude_censored_ridge":
            coefficients = ridge_fit(
                x_train[measured.to_numpy()],
                train.loc[measured, "yield_pct"].astype(float).to_numpy(),
            )
        else:
            censored = train["yield_status"].isin(["trace", "not_detected"]).to_numpy()
            y = train["yield_pct"].fillna(detection_limit).astype(float).to_numpy()
            limits = np.full(len(train), detection_limit, dtype=float)
            coefficients = tobit_fit(x_train, y, censored, limits)["coefficients"]
        predicted = float(np.clip(x_test @ coefficients, 0.0, 100.0))
        observed = float(test["yield_pct"])
        rows.append(
            {
                "record_id": test["record_id"],
                "method": method,
                "detection_limit_pct": detection_limit,
                "observed": observed,
                "predicted": predicted,
                "absolute_error": abs(predicted - observed),
            }
        )
    return float(np.mean([row["absolute_error"] for row in rows])), rows


def build_comparison(condition_descriptors: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    solvent = condition_descriptors[condition_descriptors["screen_axis"] == "solvent"].copy()
    summaries: list[dict] = []
    predictions: list[dict] = []
    for detection_limit in (2.0, 5.0):
        for method in ("exclude_censored_ridge", "left_censored_tobit_ridge"):
            mae, rows = measured_loo(solvent, detection_limit, method)
            predictions.extend(rows)
            summaries.append(
                {
                    "screen_axis": "solvent",
                    "method": method,
                    "detection_limit_pct": detection_limit,
                    "measured_loo_mae": mae,
                    "total_rows_used": int(
                        (solvent["yield_status"] == "measured").sum()
                        if method == "exclude_censored_ridge"
                        else len(solvent)
                    ),
                    "quantitative_rows": int((solvent["yield_status"] == "measured").sum()),
                    "censored_rows": int(solvent["yield_status"].isin(["trace", "not_detected"]).sum()),
                    "identifiability": "exploratory_only_n_equals_7",
                }
            )
    summaries.append(
        {
            "screen_axis": "photocatalyst",
            "method": "tobit_not_fitted",
            "detection_limit_pct": "",
            "measured_loo_mae": "",
            "total_rows_used": 6,
            "quantitative_rows": 1,
            "censored_rows": 5,
            "identifiability": "not_identifiable_only_one_quantitative_observation",
        }
    )
    return pd.DataFrame(summaries), pd.DataFrame(predictions)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    summary, predictions = build_comparison(data)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_dir / "censoring_comparison.csv", index=False, encoding="utf-8-sig")
    predictions.to_csv(args.output_dir / "censoring_loo_predictions.csv", index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
