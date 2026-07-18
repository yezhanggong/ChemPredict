"""Train, calibrate and audit the ChemPredict v4.3 sparse-data model.

The primary validation unit is a chemical family. Hyperparameters and feature
blocks are selected inside each outer group holdout. Expanded RDKit/mechanism
proxy descriptors are evaluated, but only deployable manual descriptors are used
unless they improve grouped MAE by at least one percentage point without worse
RMSE and --allow-generated-descriptor-model is explicitly enabled.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from applicability_gate import gate_check


R_KCAL = 1.98720425864083e-3
TEMPERATURE_K = 298.15
MODEL_VERSION = "4.3.0"

MANUAL_CORE = [
    "aryl_rings",
    "fused_aromatic",
    "cyclic_center",
    "alpha_chain_carbons",
    "ortho_sub_count",
    "hammett_sigma_mp",
    "sidechain_polar_count",
]
MANUAL_EXPANDED = MANUAL_CORE + [
    "meta_sub_count",
    "para_sub_count",
    "halogen_count",
    "edg_count",
    "ewg_count",
]
PHYSCHEM_COMPACT = [
    "mol_logp",
    "mol_tpsa",
    "mol_fraction_csp3",
    "mol_rotatable_bonds",
    "mol_bertz_complexity",
    "mol_heteroatoms",
    "nitrile_count",
]
MECHANISM_HYBRID = [
    "hammett_sigma_mp",
    "ortho_sub_count",
    "meta_sub_count",
    "para_sub_count",
    "alpha_chain_carbons",
    "mol_logp",
    "mol_tpsa",
    "mol_fraction_csp3",
    "gasteiger_aryl_attachment_charge",
    "centre_radius2_atomic_number_sum",
    "nitrile_count",
]
INTERACTION_HYBRID = MANUAL_EXPANDED + [
    "sigma_para_interaction",
    "strong_para_ewg",
    "extra_nitrile_count",
    "mol_logp",
    "mol_tpsa",
]

FEATURE_SETS = {
    "manual_core": MANUAL_CORE,
    "manual_expanded": MANUAL_EXPANDED,
    "physchem_compact": PHYSCHEM_COMPACT,
    "mechanism_hybrid": MECHANISM_HYBRID,
    "interaction_hybrid": INTERACTION_HYBRID,
}
DEPLOYABLE_FEATURE_SETS = {"manual_core", "manual_expanded"}
ALPHAS = [0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0]
K_VALUES = [2, 3, 4, 5, 6]
KERNEL_ALPHAS = [0.1, 1.0, 10.0]
KERNEL_GAMMAS = [0.1, 0.3, 1.0]


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


def rank_correlation(observed: np.ndarray, predicted: np.ndarray) -> float:
    left = pd.Series(observed).rank(method="average").to_numpy()
    right = pd.Series(predicted).rank(method="average").to_numpy()
    if np.std(left) < 1e-12 or np.std(right) < 1e-12:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    observed = np.asarray(observed, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    residual = predicted - observed
    denominator = float(np.sum((observed - np.mean(observed)) ** 2))
    return {
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "median_ae": float(np.median(np.abs(residual))),
        "max_ae": float(np.max(np.abs(residual))),
        "bias": float(np.mean(residual)),
        "r2": float(1.0 - np.sum(residual**2) / denominator) if denominator > 0 else 0.0,
        "spearman": rank_correlation(observed, predicted),
    }


def standardize_fit(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raw_scale = np.std(x, axis=0)
    active = raw_scale >= 1e-12
    if not np.any(active):
        raise ValueError("all candidate features have zero variance in this fold")
    active_x = x[:, active]
    mean = np.mean(active_x, axis=0)
    scale = np.std(active_x, axis=0)
    return (active_x - mean) / scale, mean, scale, active


def ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> dict:
    x_scaled, mean, scale, active = standardize_fit(x)
    intercept = float(np.mean(y))
    penalty = alpha * np.eye(x_scaled.shape[1])
    coefficients = np.linalg.pinv(x_scaled.T @ x_scaled + penalty) @ x_scaled.T @ (y - intercept)
    return {"mean": mean, "scale": scale, "active": active, "coefficients": coefficients, "intercept": intercept}


def ridge_predict(model: dict, x: np.ndarray) -> np.ndarray:
    scaled = (x[:, model["active"]] - model["mean"]) / model["scale"]
    return model["intercept"] + scaled @ model["coefficients"]


def knn_fit(x: np.ndarray, y: np.ndarray) -> dict:
    scaled, mean, scale, active = standardize_fit(x)
    return {"training_x_scaled": scaled, "training_y": y, "mean": mean, "scale": scale, "active": active}


def knn_predict(model: dict, x: np.ndarray, k: int) -> np.ndarray:
    test_scaled = (x[:, model["active"]] - model["mean"]) / model["scale"]
    values: list[float] = []
    for row in test_scaled:
        distances = np.sqrt(np.mean((model["training_x_scaled"] - row) ** 2, axis=1))
        selected = np.argsort(distances)[: min(k, len(distances))]
        weights = 1.0 / np.maximum(distances[selected], 0.05)
        values.append(float(np.sum(weights * model["training_y"][selected]) / np.sum(weights)))
    return np.asarray(values)


def kernel_fit(x: np.ndarray, y: np.ndarray, alpha: float, gamma: float) -> dict:
    scaled, mean, scale, active = standardize_fit(x)
    squared = np.mean((scaled[:, None, :] - scaled[None, :, :]) ** 2, axis=2)
    kernel = np.exp(-gamma * squared)
    intercept = float(np.mean(y))
    dual = np.linalg.pinv(kernel + alpha * np.eye(len(kernel))) @ (y - intercept)
    return {
        "training_x_scaled": scaled,
        "mean": mean,
        "scale": scale,
        "active": active,
        "dual_coefficients": dual,
        "intercept": intercept,
        "gamma": gamma,
    }


def kernel_predict(model: dict, x: np.ndarray) -> np.ndarray:
    scaled = (x[:, model["active"]] - model["mean"]) / model["scale"]
    squared = np.mean((scaled[:, None, :] - model["training_x_scaled"][None, :, :]) ** 2, axis=2)
    return model["intercept"] + np.exp(-model["gamma"] * squared) @ model["dual_coefficients"]


def config_id(config: dict) -> str:
    fields = [config["algorithm"], config["feature_set"]]
    for name in ("alpha", "gamma", "k", "transformed"):
        if name in config:
            fields.append(f"{name}={config[name]}")
    return "|".join(map(str, fields))


def configurations() -> list[dict]:
    configs: list[dict] = []
    for feature_set in FEATURE_SETS:
        configs.extend({"algorithm": "ridge", "feature_set": feature_set, "alpha": alpha} for alpha in ALPHAS)
        for transformed in (False, True):
            configs.extend(
                {"algorithm": "knn", "feature_set": feature_set, "k": k, "transformed": transformed}
                for k in K_VALUES
            )
        configs.extend(
            {"algorithm": "rbf_kernel_ridge", "feature_set": feature_set, "alpha": alpha, "gamma": gamma}
            for alpha in KERNEL_ALPHAS
            for gamma in KERNEL_GAMMAS
        )
    return configs


ALL_CONFIGS = configurations()
CONFIG_LOOKUP = {config_id(config): config for config in ALL_CONFIGS}


def get_x(data: pd.DataFrame, feature_set: str) -> np.ndarray:
    return data[FEATURE_SETS[feature_set]].astype(float).to_numpy()


def predict_config(config: dict, train: pd.DataFrame, test: pd.DataFrame, target: TargetSpec) -> np.ndarray:
    x_train = get_x(train, config["feature_set"])
    x_test = get_x(test, config["feature_set"])
    original = train[target.column].astype(float).to_numpy()
    if config["algorithm"] == "ridge":
        model = ridge_fit(x_train, target.forward(original), float(config["alpha"]))
        return target.inverse(ridge_predict(model, x_test))
    if config["algorithm"] == "knn":
        transformed = bool(config["transformed"])
        values = target.forward(original) if transformed else original
        prediction = knn_predict(knn_fit(x_train, values), x_test, int(config["k"]))
        return target.inverse(prediction) if transformed else np.clip(prediction, 0.0, 100.0)
    model = kernel_fit(x_train, target.forward(original), float(config["alpha"]), float(config["gamma"]))
    return target.inverse(kernel_predict(model, x_test))


def group_predictions(data: pd.DataFrame, target: TargetSpec, config: dict) -> pd.DataFrame:
    rows: list[dict] = []
    for group in sorted(data["scope_group"].unique()):
        test = data[data["scope_group"] == group]
        train = data[data["scope_group"] != group]
        predicted = predict_config(config, train, test, target)
        for (_, record), value in zip(test.iterrows(), predicted, strict=True):
            rows.append(
                {"id": record["id"], "scope_group": group, "observed": float(record[target.column]), "predicted": float(value)}
            )
    return pd.DataFrame(rows)


def candidate_table(data: pd.DataFrame, target: TargetSpec) -> pd.DataFrame:
    rows: list[dict] = []
    for config in ALL_CONFIGS:
        prediction = group_predictions(data, target, config)
        score = metrics(prediction["observed"].to_numpy(), prediction["predicted"].to_numpy())
        rows.append(
            {
                "config_id": config_id(config),
                "algorithm": config["algorithm"],
                "feature_set": config["feature_set"],
                "deployable_from_manual_ui": config["feature_set"] in DEPLOYABLE_FEATURE_SETS,
                **{key: config.get(key, "") for key in ("alpha", "gamma", "k", "transformed")},
                **score,
            }
        )
    return pd.DataFrame(rows).sort_values(["mae", "rmse", "config_id"], ignore_index=True)


def select_config(
    data: pd.DataFrame, target: TargetSpec, allow_generated_descriptor_model: bool
) -> tuple[dict, pd.DataFrame, str]:
    table = candidate_table(data, target)
    best_all = table.iloc[0]
    best_manual = table[table["deployable_from_manual_ui"].astype(bool)].iloc[0]
    eligible_generated = (
        allow_generated_descriptor_model
        and not bool(best_all["deployable_from_manual_ui"])
        and float(best_manual["mae"] - best_all["mae"]) >= 1.0
        and float(best_all["rmse"]) <= float(best_manual["rmse"])
    )
    selected = best_all if eligible_generated else best_manual
    if selected["config_id"] == best_all["config_id"]:
        reason = "lowest grouped MAE; generated descriptors passed the predeclared >=1 point and non-worse RMSE rule"
    elif not bool(best_all["deployable_from_manual_ui"]):
        reason = "manual deployable model retained because generated descriptors failed the predeclared material-improvement rule"
    else:
        reason = "lowest grouped MAE among deployable models"
    return CONFIG_LOOKUP[str(selected["config_id"])], table, reason


def nested_group_predictions(
    data: pd.DataFrame, target: TargetSpec, allow_generated_descriptor_model: bool
) -> pd.DataFrame:
    rows: list[dict] = []
    for outer_group in sorted(data["scope_group"].unique()):
        test = data[data["scope_group"] == outer_group]
        train = data[data["scope_group"] != outer_group]
        selected, _, reason = select_config(train, target, allow_generated_descriptor_model)
        predicted = predict_config(selected, train, test, target)
        for (_, record), value in zip(test.iterrows(), predicted, strict=True):
            rows.append(
                {
                    "id": record["id"],
                    "scope_group": outer_group,
                    "observed": float(record[target.column]),
                    "predicted": float(value),
                    "selected_config": config_id(selected),
                    "selection_reason": reason,
                }
            )
    return pd.DataFrame(rows)


def mean_baseline_predictions(data: pd.DataFrame, target: TargetSpec) -> pd.DataFrame:
    rows: list[dict] = []
    for group in sorted(data["scope_group"].unique()):
        train = data[data["scope_group"] != group]
        value = float(train[target.column].mean())
        for _, record in data[data["scope_group"] == group].iterrows():
            rows.append({"id": record["id"], "scope_group": group, "observed": float(record[target.column]), "predicted": value})
    return pd.DataFrame(rows)


def fit_final_model(data: pd.DataFrame, target: TargetSpec, config: dict) -> dict:
    names = FEATURE_SETS[config["feature_set"]]
    x = get_x(data, config["feature_set"])
    original = data[target.column].astype(float).to_numpy()
    transformed = target.forward(original)
    if config["algorithm"] == "ridge":
        model = ridge_fit(x, transformed, float(config["alpha"]))
        payload = {
            "algorithm": "ridge",
            "coefficients": model["coefficients"].tolist(),
            "intercept": model["intercept"],
            "parameter": float(config["alpha"]),
        }
    elif config["algorithm"] == "knn":
        use_transform = bool(config["transformed"])
        model = knn_fit(x, transformed if use_transform else original)
        payload = {
            "algorithm": "knn",
            "training_x_scaled": model["training_x_scaled"].tolist(),
            "training_y": model["training_y"].tolist(),
            "parameter": int(config["k"]),
            "knn_uses_target_transform": use_transform,
        }
    else:
        model = kernel_fit(x, transformed, float(config["alpha"]), float(config["gamma"]))
        payload = {
            "algorithm": "rbf_kernel_ridge",
            "training_x_scaled": model["training_x_scaled"].tolist(),
            "dual_coefficients": model["dual_coefficients"].tolist(),
            "intercept": model["intercept"],
            "alpha": float(config["alpha"]),
            "gamma": float(config["gamma"]),
        }
    active_names = [name for name, active in zip(names, model["active"], strict=True) if active]
    return {
        **payload,
        "feature_set": config["feature_set"],
        "features": active_names,
        "mean": model["mean"].tolist(),
        "scale": model["scale"].tolist(),
        "target_transform": "yield_logit" if target.name == "yield" else "ee_to_ddg_kcal_mol",
    }


def finite_sample_quantile(values: np.ndarray, coverage: float) -> float:
    ordered = np.sort(np.asarray(values, dtype=float))
    rank = min(len(ordered), math.ceil((len(ordered) + 1) * coverage))
    return float(ordered[rank - 1])


def conformal_table(predictions: pd.DataFrame, coverage: float = 0.90) -> tuple[pd.DataFrame, dict]:
    output = predictions.copy()
    residual = np.abs(output["observed"].to_numpy() - output["predicted"].to_numpy())
    half_width = finite_sample_quantile(residual, coverage)
    output["nominal_coverage"] = coverage
    output["half_width"] = half_width
    output["lower"] = np.clip(output["predicted"] - half_width, 0.0, 100.0)
    output["upper"] = np.clip(output["predicted"] + half_width, 0.0, 100.0)
    output["covered"] = (output["observed"] >= output["lower"]) & (output["observed"] <= output["upper"])
    return output, {
        "method": "nested_group_cross_conformal_empirical",
        "nominal_coverage": coverage,
        "observed_internal_coverage": float(output["covered"].mean()),
        "half_width": half_width,
        "strict_split_conformal_guarantee": False,
        "limitation": "Calibration reuses nested out-of-group residuals; independent prospective coverage is not established.",
    }


def bootstrap_advantage(model: pd.DataFrame, baseline: pd.DataFrame, iterations: int = 10000) -> dict:
    merged = model[["id", "scope_group", "observed", "predicted"]].merge(
        baseline[["id", "predicted"]].rename(columns={"predicted": "baseline_predicted"}), on="id", validate="one_to_one"
    )
    groups = sorted(merged["scope_group"].unique())
    rng = np.random.default_rng(4300)
    deltas = []
    for _ in range(iterations):
        sampled = rng.choice(groups, size=len(groups), replace=True)
        frame = pd.concat([merged[merged["scope_group"] == group] for group in sampled], ignore_index=True)
        model_mae = np.mean(np.abs(frame["predicted"] - frame["observed"]))
        baseline_mae = np.mean(np.abs(frame["baseline_predicted"] - frame["observed"]))
        deltas.append(float(model_mae - baseline_mae))
    delta = np.asarray(deltas)
    return {
        "delta_definition": "model_MAE_minus_mean_baseline_MAE; negative favors model",
        "observed_delta": float(
            np.mean(np.abs(merged["predicted"] - merged["observed"]))
            - np.mean(np.abs(merged["baseline_predicted"] - merged["observed"]))
        ),
        "bootstrap_ci95_low": float(np.quantile(delta, 0.025)),
        "bootstrap_ci95_high": float(np.quantile(delta, 0.975)),
        "probability_model_better": float(np.mean(delta < 0)),
        "iterations": iterations,
        "resampling_unit": "scope_group",
    }


def loo_distances(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scaled, _, _, _ = standardize_fit(x)
    euclidean = np.sqrt(np.mean((scaled[:, None, :] - scaled[None, :, :]) ** 2, axis=2))
    np.fill_diagonal(euclidean, np.inf)
    covariance = np.cov(scaled, rowvar=False) + 1e-6 * np.eye(scaled.shape[1])
    precision = np.linalg.pinv(covariance)
    differences = scaled[:, None, :] - scaled[None, :, :]
    mahalanobis = np.sqrt(np.maximum(np.einsum("...i,ij,...j->...", differences, precision, differences), 0.0) / scaled.shape[1])
    np.fill_diagonal(mahalanobis, np.inf)
    return np.min(euclidean, axis=1), np.min(mahalanobis, axis=1)


def higher_quantile(values: np.ndarray, probability: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), probability, method="higher"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--pubchem", type=Path, required=True)
    parser.add_argument("--mechanism-descriptors", type=Path, required=True)
    parser.add_argument("--conditions", type=Path, required=True)
    parser.add_argument("--condition-descriptors", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--baseline-predictions", type=Path)
    parser.add_argument("--condition-features", choices=("off", "audit"), default="audit")
    parser.add_argument("--censoring", choices=("exclude", "tobit"), default="exclude")
    parser.add_argument("--holdout-by-date")
    parser.add_argument("--allow-generated-descriptor-model", action="store_true")
    args = parser.parse_args()

    scope = pd.read_csv(args.scope)
    pubchem = pd.read_csv(args.pubchem)
    mechanism = pd.read_csv(args.mechanism_descriptors)
    conditions = pd.read_csv(args.conditions)
    condition_descriptors = pd.read_csv(args.condition_descriptors)
    data = scope.merge(pubchem, on="id", validate="one_to_one").merge(mechanism, on="id", validate="one_to_one")
    data["sigma_para_interaction"] = data["hammett_sigma_mp"] * data["para_sub_count"]
    data["strong_para_ewg"] = ((data["hammett_sigma_mp"] >= 0.60) & (data["para_sub_count"] > 0)).astype(int)
    data["extra_nitrile_count"] = np.maximum(data["nitrile_count"] - 1, 0)
    for name in sorted({item for values in FEATURE_SETS.values() for item in values}):
        data[name] = pd.to_numeric(data[name], errors="coerce")
        if data[name].isna().any():
            raise ValueError(f"missing values in feature {name}")
    if args.holdout_by_date and "experiment_date" not in data.columns:
        raise ValueError("--holdout-by-date requires a future experiment_date column; current literature data have no dates")
    if len(condition_descriptors) != len(conditions):
        raise ValueError("condition descriptor row count does not match condition evidence")

    domain = data[data["id"].str.startswith("2")].copy()
    challenge = data[data["id"].str.startswith("3")].copy()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.censoring == "tobit":
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
        from censoring_models import build_comparison

        censoring_summary, censoring_predictions = build_comparison(condition_descriptors)
        censoring_summary.to_csv(
            args.output_dir / "censoring_comparison.csv", index=False, encoding="utf-8-sig"
        )
        censoring_predictions.to_csv(
            args.output_dir / "censoring_loo_predictions.csv", index=False, encoding="utf-8-sig"
        )

    artifact: dict = {
        "model_version": MODEL_VERSION,
        "generated_with": "04_模型源码/model/train_v43.py",
        "source_doi": "10.1021/acs.orglett.5c05116",
        "temperature_k_for_ee_transform": TEMPERATURE_K,
        "domain_definition": "Products 2a-2z under the fixed optimized NHP-ether deoxygenative asymmetric cyanation protocol",
        "training_count": int(len(domain)),
        "challenge_count": int(len(challenge)),
        "condition_record_count": int(len(conditions)),
        "condition_feature_mode": args.condition_features,
        "condition_descriptors_in_final_scope_model": False,
        "condition_descriptor_reason": "All 26 scope rows share the optimized condition; constant condition columns cannot identify condition effects.",
        "censoring_analysis_mode": args.censoring,
        "censored_rows_in_final_scope_model": False,
        "censoring_semantics": "Tobit is an exploratory condition-screen comparison only; the final scope predictors use quantitative scope outcomes.",
        "known_scope": scope.fillna("").to_dict(orient="records"),
        "condition_screen": conditions.fillna("").to_dict(orient="records"),
        "models": {},
        "fallback_models": {},
    }
    prediction_frames: list[pd.DataFrame] = []
    metric_rows: list[dict] = []
    advantage_rows: list[dict] = []
    conformal_frames: list[pd.DataFrame] = []

    for target_name, target in TARGETS.items():
        allow_generated_for_target = args.allow_generated_descriptor_model and target_name == "yield"
        selected, candidates, selection_reason = select_config(domain, target, allow_generated_for_target)
        candidates.insert(0, "target", target_name)
        candidates.to_csv(args.output_dir / f"candidate_metrics_{target_name}.csv", index=False, encoding="utf-8-sig")
        fixed = group_predictions(domain, target, selected)
        fixed["validation"] = "fixed_selected_group_holdout"
        nested = nested_group_predictions(domain, target, allow_generated_for_target)
        nested["validation"] = "nested_group_holdout"
        baseline = mean_baseline_predictions(domain, target)
        baseline["validation"] = "mean_baseline_group_holdout"
        for frame in (fixed, nested, baseline):
            frame["target"] = target_name
            prediction_frames.append(frame.copy())
        fixed_score = metrics(fixed["observed"].to_numpy(), fixed["predicted"].to_numpy())
        nested_score = metrics(nested["observed"].to_numpy(), nested["predicted"].to_numpy())
        baseline_score = metrics(baseline["observed"].to_numpy(), baseline["predicted"].to_numpy())
        for label, score in (
            ("fixed_selected_group_holdout", fixed_score),
            ("nested_group_holdout", nested_score),
            ("mean_baseline_group_holdout", baseline_score),
        ):
            metric_rows.append({"target": target_name, "validation": label, **score})
        advantage_rows.append({"target": target_name, **bootstrap_advantage(nested, baseline)})
        calibrated, calibration = conformal_table(nested)
        calibrated["target"] = target_name
        conformal_frames.append(calibrated)
        final_model = fit_final_model(domain, target, selected)
        final_model.update(
            {
                "selected_config": selected,
                "selection_reason": selection_reason,
                "fixed_group_metrics": fixed_score,
                "nested_workflow_metrics": nested_score,
                "mean_baseline_metrics": baseline_score,
                "cross_conformal": calibration,
            }
        )
        artifact["models"][target_name] = final_model
        if selected["feature_set"] not in DEPLOYABLE_FEATURE_SETS:
            fallback_row = candidates[candidates["deployable_from_manual_ui"].astype(bool)].iloc[0]
            fallback_config = CONFIG_LOOKUP[str(fallback_row["config_id"])]
            fallback_prediction = group_predictions(domain, target, fallback_config)
            fallback_model = fit_final_model(domain, target, fallback_config)
            fallback_model.update(
                {
                    "selected_config": fallback_config,
                    "selection_reason": "best fixed grouped-holdout model computable from the manual offline form",
                    "fixed_group_metrics": metrics(
                        fallback_prediction["observed"].to_numpy(), fallback_prediction["predicted"].to_numpy()
                    ),
                    "use_case": "offline manual-input fallback when generated structure descriptors are unavailable",
                }
            )
            artifact["fallback_models"][target_name] = fallback_model

    metrics_table = pd.DataFrame(metric_rows)
    predictions_table = pd.concat(prediction_frames, ignore_index=True, sort=False)
    metrics_table.to_csv(args.output_dir / "validation_metrics.csv", index=False, encoding="utf-8-sig")
    predictions_table.to_csv(args.output_dir / "group_holdout_predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(advantage_rows).to_csv(args.output_dir / "bootstrap_model_advantage.csv", index=False, encoding="utf-8-sig")
    pd.concat(conformal_frames, ignore_index=True).to_csv(
        args.output_dir / "conformal_intervals.csv", index=False, encoding="utf-8-sig"
    )

    x_core = domain[MANUAL_CORE].astype(float).to_numpy()
    euclidean, mahalanobis = loo_distances(x_core)
    _, core_mean, core_scale, active = standardize_fit(x_core)
    if not np.all(active):
        raise ValueError("manual core applicability features must all vary")
    q50, q90, q95 = (higher_quantile(euclidean, value) for value in (0.50, 0.90, 0.95))
    calibration = pd.DataFrame(
        {
            "id": domain["id"].to_numpy(),
            "scope_group": domain["scope_group"].to_numpy(),
            "loo_euclidean_distance": euclidean,
            "loo_mahalanobis_distance": mahalanobis,
            "q50": q50,
            "q90": q90,
            "q95": q95,
            "inside_q90": euclidean <= q90,
            "inside_q95": euclidean <= q95,
        }
    )
    calibration.to_csv(args.output_dir / "applicability_calibration.csv", index=False, encoding="utf-8-sig")
    applicability = {
        "metric": "standardized_euclidean_nearest_neighbor",
        "features": MANUAL_CORE,
        "mean": core_mean.tolist(),
        "scale": core_scale.tolist(),
        "training_x": x_core.tolist(),
        "loo_distance_summary": {
            "q50": q50,
            "q90": q90,
            "q95": q95,
            "inside_q90_count": int((euclidean <= q90).sum()),
            "inside_q95_count": int((euclidean <= q95).sum()),
            "training_count": len(domain),
        },
    }
    gate_config = {
        "allowed_precursor_types": ["secondary_benzylic_nhp_ether"],
        "allowed_radical_classes": ["carbon_aryl_benzylic"],
        "allowed_reaction_families": ["nhp_ether_deoxygenative_asymmetric_cyanation"],
        "max_condition_changes": 1,
        "distance_thresholds": {"q50_typical": q50, "q90_warn": q90, "q95_refuse": q95},
        "high_risk_rules": [
            {
                "id": "strong_para_ewg_low_ee_abstention",
                "minimum": {"hammett_sigma_mp": 0.60, "para_sub_count": 1},
                "action": "REFUSE",
                "message": "强对位吸电子区域仅有 2n 且其 ee 为 41%；缺少独立同类样本，模型拒绝给出新底物 ee 点预测。",
            }
        ],
    }
    artifact["applicability"] = {**applicability, "gate_config": gate_config}

    challenge_rows: list[dict] = []
    for _, record in challenge.iterrows():
        result = gate_check(
            record.to_dict(),
            "secondary_benzylic_nhp_ether",
            "carbon_aryl_benzylic" if record["radical_class"] == "benzylic" else str(record["radical_class"]),
            [],
            gate_config=gate_config,
            applicability=applicability,
        )
        challenge_rows.append(
            {
                "id": record["id"],
                "radical_class": record["radical_class"],
                "yield_pct": record["yield_pct"],
                "ee_pct": record["ee_pct"],
                "final_decision": result.status,
                "distance": result.distance,
                "reasons": " | ".join(result.reasons),
            }
        )
    pd.DataFrame(challenge_rows).to_csv(
        args.output_dir / "challenge_set_applicability.csv", index=False, encoding="utf-8-sig"
    )
    artifact["challenge_applicability"] = challenge_rows

    comparison_rows = []
    for row in metric_rows:
        if row["validation"] == "nested_group_holdout":
            comparison_rows.append(
                {
                    **row,
                    "feature_mode": "substrate_descriptors_only",
                    "condition_feature_effect": "not_identifiable_all_scope_rows_share_the_same_optimized_condition",
                }
            )
            comparison_rows.append(
                {
                    **row,
                    "feature_mode": "substrate_plus_fixed_condition_descriptors",
                    "condition_feature_effect": "identical_predictions_constant_condition_columns_removed_within_each_fold",
                }
            )
    pd.DataFrame(comparison_rows).to_csv(
        args.output_dir / "condition_feature_comparison.csv", index=False, encoding="utf-8-sig"
    )

    outlier_rows = []
    new_2n = predictions_table[
        (predictions_table["id"] == "2n") & (predictions_table["target"] == "ee")
    ][["validation", "observed", "predicted"]].copy()
    new_2n["version"] = MODEL_VERSION
    new_2n["absolute_error"] = np.abs(new_2n["predicted"] - new_2n["observed"])
    outlier_rows.extend(new_2n.to_dict(orient="records"))
    if args.baseline_predictions and args.baseline_predictions.exists():
        old = pd.read_csv(args.baseline_predictions)
        old_2n = old[(old["id"] == "2n") & (old["target"] == "ee")].copy()
        old_2n["version"] = "4.0.0"
        old_2n["absolute_error"] = np.abs(old_2n["predicted"] - old_2n["observed"])
        outlier_rows.extend(old_2n[["validation", "observed", "predicted", "version", "absolute_error"]].to_dict(orient="records"))
    pd.DataFrame(outlier_rows).to_csv(args.output_dir / "outlier_diagnosis.csv", index=False, encoding="utf-8-sig")

    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(metrics_table.to_string(index=False, float_format=lambda value: f"{value:.3f}"))
    print(f"Applicability inside q90: {(euclidean <= q90).sum()}/{len(domain)}")
    print(f"Artifact: {args.artifact}")


if __name__ == "__main__":
    main()
