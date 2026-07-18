"""Reference Python inference path for ChemPredict v4.3."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from applicability_gate import gate_check


R_KCAL = 1.98720425864083e-3


def inverse_target(model: Mapping[str, Any], value: np.ndarray, temperature_k: float) -> np.ndarray:
    if model["target_transform"] == "ee_to_ddg_kcal_mol":
        ratio = np.exp(value / (R_KCAL * temperature_k))
        return np.clip(100.0 * (ratio - 1.0) / (ratio + 1.0), 0.0, 100.0)
    if model["target_transform"] == "yield_logit":
        probability = 1.0 / (1.0 + np.exp(-value))
        return np.clip(101.0 * probability - 0.5, 0.0, 100.0)
    return np.clip(value, 0.0, 100.0)


def model_prediction(model: Mapping[str, Any], features: Mapping[str, float], temperature_k: float) -> float:
    vector = np.asarray([float(features[name]) for name in model["features"]], dtype=float)
    scaled = (vector - np.asarray(model["mean"], dtype=float)) / np.asarray(model["scale"], dtype=float)
    if model["algorithm"] == "ridge":
        transformed = float(model["intercept"] + scaled @ np.asarray(model["coefficients"], dtype=float))
        return float(inverse_target(model, np.asarray([transformed]), temperature_k)[0])
    if model["algorithm"] == "knn":
        training_x = np.asarray(model["training_x_scaled"], dtype=float)
        distances = np.sqrt(np.mean((training_x - scaled) ** 2, axis=1))
        selected = np.argsort(distances)[: min(int(model["parameter"]), len(distances))]
        weights = 1.0 / np.maximum(distances[selected], 0.05)
        value = float(np.sum(weights * np.asarray(model["training_y"], dtype=float)[selected]) / np.sum(weights))
        if model.get("knn_uses_target_transform", False):
            return float(inverse_target(model, np.asarray([value]), temperature_k)[0])
        return float(np.clip(value, 0.0, 100.0))
    training_x = np.asarray(model["training_x_scaled"], dtype=float)
    squared = np.mean((training_x - scaled) ** 2, axis=1)
    kernel = np.exp(-float(model["gamma"]) * squared)
    transformed = float(model["intercept"] + kernel @ np.asarray(model["dual_coefficients"], dtype=float))
    return float(inverse_target(model, np.asarray([transformed]), temperature_k)[0])


def choose_model(artifact: Mapping[str, Any], target: str, features: Mapping[str, float]) -> tuple[Mapping[str, Any], str]:
    primary = artifact["models"][target]
    if all(name in features and features[name] not in (None, "") for name in primary["features"]):
        return primary, "primary"
    fallback = artifact.get("fallback_models", {}).get(target)
    if fallback and all(name in features and features[name] not in (None, "") for name in fallback["features"]):
        return fallback, "manual_fallback"
    missing = [name for name in primary["features"] if name not in features or features[name] in (None, "")]
    raise ValueError(f"missing model features for {target}: {missing}")


def predict(artifact: Mapping[str, Any], request: Mapping[str, Any]) -> dict:
    if request.get("known_id"):
        known = next((row for row in artifact["known_scope"] if row["id"] == request["known_id"]), None)
        if known is None:
            return {"status": "REFUSE", "reasons": ["Unknown known_id"]}
        return {
            "status": "KNOWN_LOOKUP",
            "evidence_grade": "A",
            "yield": {"point": float(known["yield_pct"]), "source": "reported_observation"},
            "ee": {"point": float(known["ee_pct"]), "source": "reported_observation"},
        }
    features = request["features"]
    applicability = artifact["applicability"]
    gate = gate_check(
        features,
        request.get("precursor_type", ""),
        request.get("radical_class", ""),
        request.get("condition_changes", []),
        reaction_family=request.get("reaction_family", ""),
        gate_config=applicability["gate_config"],
        applicability=applicability,
    )
    if gate.status == "REFUSE":
        return {**gate.to_dict(), "prediction_emitted": False}
    temperature = float(artifact.get("temperature_k_for_ee_transform", 298.15))
    result = {**gate.to_dict(), "prediction_emitted": True, "targets": {}}
    for target in ("yield", "ee"):
        model, source = choose_model(artifact, target, features)
        point = model_prediction(model, features, temperature)
        calibration = artifact["models"][target]["cross_conformal"]
        half_width = float(calibration["half_width"])
        result["targets"][target] = {
            "point": point,
            "low": max(0.0, point - half_width),
            "high": min(100.0, point + half_width),
            "model_source": source,
            "algorithm": model["algorithm"],
            "feature_set": model["feature_set"],
            "interval_method": calibration["method"],
            "strict_coverage_guarantee": bool(calibration["strict_split_conformal_guarantee"]),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("request", type=Path, help="JSON request")
    args = parser.parse_args()
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    request = json.loads(args.request.read_text(encoding="utf-8"))
    print(json.dumps(predict(artifact, request), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
