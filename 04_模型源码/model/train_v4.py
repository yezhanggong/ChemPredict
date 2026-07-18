"""Train and audit the ChemPredict v4 sparse-data model.

The script deliberately uses only NumPy/Pandas. Validation is grouped by chemical
family, hyperparameters are selected inside each outer fold, and enantiomeric
excess is modeled as delta-delta-G at 298.15 K rather than as an unbounded percent.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


R_KCAL = 1.98720425864083e-3
TEMPERATURE_K = 298.15

CORE_FEATURES = [
    "aryl_rings",
    "fused_aromatic",
    "cyclic_center",
    "alpha_chain_carbons",
    "ortho_sub_count",
    "hammett_sigma_mp",
    "sidechain_polar_count",
]

EXPANDED_FEATURES = CORE_FEATURES + [
    "meta_sub_count",
    "para_sub_count",
    "halogen_count",
    "edg_count",
    "ewg_count",
]

ALPHAS = [0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0]
K_VALUES = [2, 3, 4, 5]


def ee_to_ddg(ee_pct: np.ndarray) -> np.ndarray:
    ee = np.clip(np.asarray(ee_pct, dtype=float) / 100.0, -0.999999, 0.999999)
    return R_KCAL * TEMPERATURE_K * np.log((1.0 + ee) / (1.0 - ee))


def ddg_to_ee(ddg: np.ndarray) -> np.ndarray:
    ratio = np.exp(np.asarray(ddg, dtype=float) / (R_KCAL * TEMPERATURE_K))
    return np.clip(100.0 * (ratio - 1.0) / (ratio + 1.0), 0.0, 100.0)


def yield_to_logit(yield_pct: np.ndarray) -> np.ndarray:
    probability = (np.asarray(yield_pct, dtype=float) + 0.5) / 101.0
    return np.log(probability / (1.0 - probability))


def logit_to_yield(value: np.ndarray) -> np.ndarray:
    probability = 1.0 / (1.0 + np.exp(-np.asarray(value, dtype=float)))
    return np.clip(101.0 * probability - 0.5, 0.0, 100.0)


@dataclass(frozen=True)
class TargetSpec:
    name: str
    column: str
    forward: Callable[[np.ndarray], np.ndarray]
    inverse: Callable[[np.ndarray], np.ndarray]


TARGETS = {
    "yield": TargetSpec("yield", "yield_pct", yield_to_logit, logit_to_yield),
    "ee": TargetSpec("ee", "ee_pct", ee_to_ddg, ddg_to_ee),
}


def metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    residual = np.asarray(predicted) - np.asarray(observed)
    return {
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "median_ae": float(np.median(np.abs(residual))),
        "max_ae": float(np.max(np.abs(residual))),
        "bias": float(np.mean(residual)),
    }


def standardize_fit(
    x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raw_scale = np.std(x, axis=0)
    active = raw_scale >= 1e-12
    if not np.any(active):
        raise ValueError("All candidate features have zero variance in this fold")
    active_x = x[:, active]
    mean = np.mean(active_x, axis=0)
    scale = np.std(active_x, axis=0)
    return (active_x - mean) / scale, mean, scale, active


def ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> dict[str, np.ndarray | float]:
    x_scaled, mean, scale, active = standardize_fit(x)
    y_mean = float(np.mean(y))
    centered = y - y_mean
    penalty = alpha * np.eye(x_scaled.shape[1])
    coef = np.linalg.pinv(x_scaled.T @ x_scaled + penalty) @ x_scaled.T @ centered
    return {
        "mean": mean,
        "scale": scale,
        "active": active,
        "coef": coef,
        "intercept": y_mean,
    }


def ridge_predict(model: dict, x: np.ndarray) -> np.ndarray:
    scaled = (x[:, model["active"]] - model["mean"]) / model["scale"]
    return model["intercept"] + scaled @ model["coef"]


def knn_predict(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, k: int) -> np.ndarray:
    x_scaled, mean, scale, active = standardize_fit(x_train)
    test_scaled = (x_test[:, active] - mean) / scale
    result: list[float] = []
    for row in test_scaled:
        distances = np.sqrt(np.mean((x_scaled - row) ** 2, axis=1))
        indices = np.argsort(distances)[: min(k, len(distances))]
        weights = 1.0 / np.maximum(distances[indices], 0.05)
        result.append(float(np.sum(weights * y_train[indices]) / np.sum(weights)))
    return np.asarray(result)


def get_x(data: pd.DataFrame, features: list[str]) -> np.ndarray:
    return data[features].astype(float).to_numpy()


def predict_config(
    config: dict,
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: TargetSpec,
) -> np.ndarray:
    features = CORE_FEATURES if config["features"] == "core" else EXPANDED_FEATURES
    x_train = get_x(train, features)
    x_test = get_x(test, features)
    y_original = train[target.column].astype(float).to_numpy()
    if config["algorithm"] == "ridge":
        y_transformed = target.forward(y_original)
        model = ridge_fit(x_train, y_transformed, float(config["parameter"]))
        return target.inverse(ridge_predict(model, x_test))
    return knn_predict(x_train, y_original, x_test, int(config["parameter"]))


def configurations() -> list[dict]:
    configs: list[dict] = []
    for feature_set in ("core", "expanded"):
        configs.extend(
            {"algorithm": "ridge", "features": feature_set, "parameter": alpha}
            for alpha in ALPHAS
        )
        configs.extend(
            {"algorithm": "knn", "features": feature_set, "parameter": k}
            for k in K_VALUES
        )
    return configs


def group_predictions(data: pd.DataFrame, target: TargetSpec, config: dict) -> pd.DataFrame:
    rows: list[dict] = []
    for group in sorted(data["scope_group"].unique()):
        test = data[data["scope_group"] == group]
        train = data[data["scope_group"] != group]
        predicted = predict_config(config, train, test, target)
        for (_, record), value in zip(test.iterrows(), predicted, strict=True):
            rows.append(
                {
                    "id": record["id"],
                    "scope_group": group,
                    "observed": float(record[target.column]),
                    "predicted": float(value),
                }
            )
    return pd.DataFrame(rows)


def select_config(data: pd.DataFrame, target: TargetSpec) -> tuple[dict, pd.DataFrame]:
    scores: list[dict] = []
    for config in configurations():
        predictions = group_predictions(data, target, config)
        score = metrics(predictions["observed"].to_numpy(), predictions["predicted"].to_numpy())
        scores.append({**config, **score})
    table = pd.DataFrame(scores).sort_values(["mae", "rmse", "algorithm", "features"])
    best = table.iloc[0][["algorithm", "features", "parameter"]].to_dict()
    return best, table


def nested_group_predictions(data: pd.DataFrame, target: TargetSpec) -> pd.DataFrame:
    rows: list[dict] = []
    for outer_group in sorted(data["scope_group"].unique()):
        outer_test = data[data["scope_group"] == outer_group]
        outer_train = data[data["scope_group"] != outer_group]
        best, _ = select_config(outer_train, target)
        predicted = predict_config(best, outer_train, outer_test, target)
        for (_, record), value in zip(outer_test.iterrows(), predicted, strict=True):
            rows.append(
                {
                    "id": record["id"],
                    "scope_group": outer_group,
                    "observed": float(record[target.column]),
                    "predicted": float(value),
                    "selected_algorithm": best["algorithm"],
                    "selected_features": best["features"],
                    "selected_parameter": float(best["parameter"]),
                }
            )
    return pd.DataFrame(rows)


def mean_baseline_predictions(data: pd.DataFrame, target: TargetSpec) -> pd.DataFrame:
    rows: list[dict] = []
    for group in sorted(data["scope_group"].unique()):
        train = data[data["scope_group"] != group]
        test = data[data["scope_group"] == group]
        value = float(train[target.column].mean())
        for _, record in test.iterrows():
            rows.append(
                {
                    "id": record["id"],
                    "scope_group": group,
                    "observed": float(record[target.column]),
                    "predicted": value,
                }
            )
    return pd.DataFrame(rows)


def nearest_distances(x: np.ndarray) -> np.ndarray:
    scaled, _, _, _ = standardize_fit(x)
    distances = np.sqrt(np.mean((scaled[:, None, :] - scaled[None, :, :]) ** 2, axis=2))
    np.fill_diagonal(distances, np.inf)
    return np.min(distances, axis=1)


def fit_final_model(data: pd.DataFrame, target: TargetSpec, config: dict) -> dict:
    features = CORE_FEATURES if config["features"] == "core" else EXPANDED_FEATURES
    x = get_x(data, features)
    y = data[target.column].astype(float).to_numpy()
    if config["algorithm"] == "ridge":
        model = ridge_fit(x, target.forward(y), float(config["parameter"]))
        return {
            "algorithm": "ridge",
            "feature_set": config["features"],
            "parameter": float(config["parameter"]),
            "features": [feature for feature, active in zip(features, model["active"], strict=True) if active],
            "mean": np.asarray(model["mean"]).tolist(),
            "scale": np.asarray(model["scale"]).tolist(),
            "coefficients": np.asarray(model["coef"]).tolist(),
            "intercept": float(model["intercept"]),
            "target_transform": "yield_logit" if target.name == "yield" else "ee_to_ddg_kcal_mol",
        }

    x_scaled, mean, scale, active = standardize_fit(x)
    return {
        "algorithm": "knn",
        "feature_set": config["features"],
        "parameter": int(config["parameter"]),
        "features": [feature for feature, is_active in zip(features, active, strict=True) if is_active],
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "training_x_scaled": x_scaled.tolist(),
        "training_y": y.tolist(),
        "target_transform": "none",
    }


def empirical_quantile(values: np.ndarray, probability: float) -> float:
    return float(np.quantile(np.asarray(values), probability, method="higher"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--pubchem", type=Path, required=True)
    parser.add_argument("--conditions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args()

    scope = pd.read_csv(args.scope)
    pubchem = pd.read_csv(args.pubchem)
    conditions = pd.read_csv(args.conditions)
    data = scope.merge(pubchem, on="id", validate="one_to_one")
    for feature in EXPANDED_FEATURES:
        data[feature] = pd.to_numeric(data[feature], errors="coerce")
        if data[feature].isna().any():
            data[feature] = data[feature].fillna(data[feature].median())

    # The prospective model is limited to carbon-aryl benzylic examples 2a-2z.
    # The four 3-series compounds are retained as mechanistic challenge cases.
    domain = data[data["id"].str.startswith("2")].copy()
    challenge = data[data["id"].str.startswith("3")].copy()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    artifact: dict = {
        "model_version": "4.0.0",
        "generated_with": "04_模型源码/model/train_v4.py",
        "source_doi": "10.1021/acs.orglett.5c05116",
        "temperature_k_for_ee_transform": TEMPERATURE_K,
        "domain_definition": "Products 2a-2z: carbon-aryl benzylic radicals under the fixed optimized condition",
        "training_count": int(len(domain)),
        "challenge_count": int(len(challenge)),
        "models": {},
        "known_scope": scope.fillna("").to_dict(orient="records"),
        "condition_screen": conditions.fillna("").to_dict(orient="records"),
    }
    metric_rows: list[dict] = []
    prediction_frames: list[pd.DataFrame] = []

    for target_name, target in TARGETS.items():
        best_config, candidate_table = select_config(domain, target)
        candidate_table.insert(0, "target", target_name)
        candidate_table.to_csv(
            args.output_dir / f"candidate_metrics_{target_name}.csv",
            index=False,
            encoding="utf-8-sig",
        )

        selected_predictions = group_predictions(domain, target, best_config)
        selected_predictions["validation"] = "fixed_pipeline_group_holdout"
        nested_predictions = nested_group_predictions(domain, target)
        nested_predictions["validation"] = "nested_group_holdout"
        baseline_predictions = mean_baseline_predictions(domain, target)
        baseline_predictions["validation"] = "mean_baseline_group_holdout"
        for frame in (selected_predictions, nested_predictions, baseline_predictions):
            frame["target"] = target_name
            prediction_frames.append(frame.copy())

        selected_score = metrics(
            selected_predictions["observed"].to_numpy(),
            selected_predictions["predicted"].to_numpy(),
        )
        nested_score = metrics(
            nested_predictions["observed"].to_numpy(),
            nested_predictions["predicted"].to_numpy(),
        )
        baseline_score = metrics(
            baseline_predictions["observed"].to_numpy(),
            baseline_predictions["predicted"].to_numpy(),
        )
        metric_rows.extend(
            {"target": target_name, "validation": label, **score}
            for label, score in (
                ("fixed_pipeline_group_holdout", selected_score),
                ("nested_group_holdout", nested_score),
                ("mean_baseline_group_holdout", baseline_score),
            )
        )

        final_model = fit_final_model(domain, target, best_config)
        absolute_errors = np.abs(
            selected_predictions["observed"].to_numpy()
            - selected_predictions["predicted"].to_numpy()
        )
        final_model.update(
            {
                "selected_config": best_config,
                "group_holdout_metrics": selected_score,
                "nested_workflow_metrics": nested_score,
                "mean_baseline_metrics": baseline_score,
                "absolute_error_q80": empirical_quantile(absolute_errors, 0.80),
                "absolute_error_q90": empirical_quantile(absolute_errors, 0.90),
            }
        )
        artifact["models"][target_name] = final_model

    metrics_table = pd.DataFrame(metric_rows)
    metrics_table.to_csv(args.output_dir / "validation_metrics.csv", index=False, encoding="utf-8-sig")
    all_predictions = pd.concat(prediction_frames, ignore_index=True, sort=False)
    all_predictions.to_csv(
        args.output_dir / "group_holdout_predictions.csv", index=False, encoding="utf-8-sig"
    )

    # Applicability distance is computed on the conservative core descriptor set.
    x_core = get_x(domain, CORE_FEATURES)
    nearest = nearest_distances(x_core)
    _, core_mean, core_scale, core_active = standardize_fit(x_core)
    if not np.all(core_active):
        raise ValueError("CORE_FEATURES must not contain zero-variance columns in the final domain")
    artifact["applicability"] = {
        "features": CORE_FEATURES,
        "mean": core_mean.tolist(),
        "scale": core_scale.tolist(),
        "training_x": x_core.tolist(),
        "nearest_distance_q50": empirical_quantile(nearest, 0.50),
        "nearest_distance_q90": empirical_quantile(nearest, 0.90),
        "nearest_distance_q95": empirical_quantile(nearest, 0.95),
        "refusal_rules": [
            "unactivated alcohol or tertiary benzylic precursor",
            "radical class other than carbon-aryl benzylic",
            "nearest standardized descriptor distance above q95",
            "condition combination differing in more than one screened factor",
        ],
    }

    # Predict challenge cases only to verify that the applicability gate rejects them.
    challenge_rows: list[dict] = []
    scaled_train = (x_core - core_mean) / core_scale
    for _, record in challenge.iterrows():
        row = record[CORE_FEATURES].astype(float).to_numpy()
        scaled_row = (row - core_mean) / core_scale
        distance = float(np.min(np.sqrt(np.mean((scaled_train - scaled_row) ** 2, axis=1))))
        challenge_rows.append(
            {
                "id": record["id"],
                "radical_class": record["radical_class"],
                "yield_pct": record["yield_pct"],
                "ee_pct": record["ee_pct"],
                "nearest_distance": distance,
                "distance_above_q95": distance > artifact["applicability"]["nearest_distance_q95"],
                "refused_by_class": record["radical_class"] != "benzylic",
                "final_decision": "REFUSE",
            }
        )
    pd.DataFrame(challenge_rows).to_csv(
        args.output_dir / "challenge_set_applicability.csv", index=False, encoding="utf-8-sig"
    )
    artifact["challenge_applicability"] = challenge_rows

    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(metrics_table.to_string(index=False, float_format=lambda value: f"{value:.3f}"))
    print(f"Artifact: {args.artifact}")


if __name__ == "__main__":
    main()
